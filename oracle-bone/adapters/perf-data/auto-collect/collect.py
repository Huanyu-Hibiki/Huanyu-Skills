"""auto-collect collect.py — CLI 入口。

用法:
  python collect.py douyin --auth-only          # 首次授权（可见浏览器本人登录）
  python collect.py all --days 30               # 四平台连采
  python collect.py bilibili --limit 20 --debug
产物: <project>/.oracle-cache/collections/<ts>/{unified.json, raw/, run.json}
"""

import argparse
import importlib
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent.parent / "tools"))

from core.browser import BrowserSession  # noqa: E402
from core.framework import ResponseCollector, Checkpoint, save_run_artifacts  # noqa: E402
from data_normalizer import normalize_rows, filter_by_date  # noqa: E402

PLATFORM_MODULES = {
    "douyin": "platforms.douyin",
    "xiaohongshu": "platforms.xiaohongshu",
    "bilibili": "platforms.bilibili",
    "kuaishou": "platforms.kuaishou",
    "wechat": "platforms.wechat",
}
PLATFORM_INTERVAL_S = 120  # 多平台连采的间隔（防频控纪律）


def load_platform(name):
    return importlib.import_module(PLATFORM_MODULES[name])


def output_dir(project_root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    d = project_root / ".oracle-cache" / "collections" / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def find_project_root() -> Path:
    cur = Path.cwd()
    for p in [cur, *cur.parents]:
        if (p / ".oracle-state.json").exists():
            return p
    return cur


def collect_one(name: str, args, out_dir: Path) -> dict:
    mod = load_platform(name)
    meta = {"platform": name, "started_at": time.strftime("%Y-%m-%d %H:%M:%S"), "errors": []}

    with BrowserSession(name, headless=args.headless, slow_mo=args.slow_mo) as session:
        # 先建监听再导航——首屏 API（列表数据）在页面加载时就发出，
        # 晚挂监听会整段错过（2026-08-19 小红书实测教训）
        page = session.page
        page.wait_for_timeout(500)
        from core.framework import ResponseCollector
        collector = ResponseCollector(page, mod.ENDPOINTS, mod.parse_list_response)
        if args.debug:
            url_log = out_dir / f"{name}-urls.log"

            def _log_resp(resp):
                try:
                    with url_log.open("a", encoding="utf-8") as f:
                        f.write(f"{resp.status} {resp.url}\n")
                except Exception:
                    pass

            page.on("response", _log_resp)

        page = session.navigate(mod.LIST_URL)
        # 平台特定加载动作（如视频号需点菜单触发 SPA 路由）
        if hasattr(mod, "post_navigate"):
            mod.post_navigate(page)
        meta["auth"] = session.auth_status(mod.AUTH_MARKERS)
        if meta["auth"] in ("unauthorized", "unknown"):
            # 登录态失效/不确定——分模式处理，绝不闪关窗口
            if args.headless:
                meta["errors"].append(
                    f"未授权（headless 模式，无法展示扫码）——恢复命令："
                    f"{sys.executable} collect.py {name} --auth-only（会弹浏览器等你扫码）")
                meta["needs_auth"] = True
                return meta
            # headful：浏览器已开着登录页——大声提示 + 轮询等待扫码
            print(f"\n🔔 [{name}] 登录态已过期（网页登录通常 1-2 周失效，正常现象）。"
                  f"\n🔔 浏览器窗口已打开登录页——请现在用手机{name}App扫码，"
                  f"我在这等你（最长 3 分钟）：")
            ok = session.wait_for_login(mod.AUTH_MARKERS, timeout_s=180, platform=name)
            if not ok:
                meta["errors"].append(
                    f"等待登录超时——恢复命令：{sys.executable} collect.py {name} --auth-only")
                meta["needs_auth"] = True
                return meta
            meta["auth"] = "authorized"
        if args.debug:
            session.screenshot_debug(out_dir / f"{name}-list.png")

        def on_progress(rd, found, total):
            print(f"  [{name}] 轮 {rd}：已发现 {found}" + (f"/{total}" if total else ""))

        from core.framework import scan_list
        card_sel = mod.SELECTORS.get("video_card") or mod.SELECTORS.get("note_card", "div")
        items = scan_list(page, collector, card_selector=card_sel,
                          extract_card=mod.extract_dom_card,
                          scroll_rounds=args.rounds, on_progress=on_progress)

        min_date = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d") if args.days else ""
        if args.limit and len(items) > args.limit:
            items = dict(list(items.items())[: args.limit])

        cp = Checkpoint(out_dir / f"{name}-checkpoint.json")
        detail_rows = {}
        if args.details and hasattr(mod, "detail_steps") and hasattr(mod, "DETAIL_URL"):
            detail_url_tpl = getattr(mod, "DETAIL_URL", "")
            for i, (wid, row) in enumerate(items.items()):
                if cp.done(wid):
                    continue
                try:
                    dp = session.navigate(detail_url_tpl.format(wid=wid), timeout_ms=30000)
                    extra = mod.detail_steps(dp) or {}
                    if extra.get("_official_export_path"):
                        meta.setdefault("official_exports", []).append(extra["_official_export_path"])
                        extra = {k: v for k, v in extra.items() if not k.startswith("_")}
                    if extra:
                        detail_rows[wid] = extra
                    cp.mark(wid, "ok")
                except Exception as e:
                    cp.mark(wid, f"error:{str(e)[:80]}")
                    meta["errors"].append(f"detail {wid}: {str(e)[:120]}")
                session.page.wait_for_timeout(1200)
                if i + 1 >= args.details:
                    break

        for wid, extra in detail_rows.items():
            if wid in items:
                items[wid] = {**extra, **{k: v for k, v in items[wid].items() if v}}

        unified = normalize_rows(name, list(items.values()), source_file=f"{name}-live")
        unified = filter_by_date(unified, min_date=min_date)
        meta["collected"] = len(items)
        meta["unified"] = len(unified)

        (out_dir / "raw" / f"{name}-items.json").parent.mkdir(parents=True, exist_ok=True)
        (out_dir / "raw" / f"{name}-items.json").write_text(
            json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"meta": meta, "unified": unified, "raw": items}


def main():
    ap = argparse.ArgumentParser(description="四平台创作者数据一键采集")
    ap.add_argument("platform", choices=[*PLATFORM_MODULES, "all"])
    ap.add_argument("--days", type=int, default=30, help="只保留最近 N 天作品（0=全部）")
    ap.add_argument("--limit", type=int, default=0, help="每平台最多采集 N 条（0=全部）")
    ap.add_argument("--auth-only", action="store_true", help="只开浏览器授权，不采集")
    ap.add_argument("--details", type=int, default=0, help="逐作品进详情页取增量指标的条数（0=跳过，慢）")
    ap.add_argument("--rounds", type=int, default=60, help="列表滚动轮数上限")
    ap.add_argument("--headless", action="store_true", help="无头模式（授权后日常采集可用）")
    ap.add_argument("--slow-mo", type=int, default=0)
    ap.add_argument("--debug", action="store_true", help="截图 + 打印响应 URL 便于校准选择器")
    args = ap.parse_args()

    project = find_project_root()
    out_dir = output_dir(project)

    names = list(PLATFORM_MODULES) if args.platform == "all" else [args.platform]

    if args.auth_only:
        auth_failed = []
        for name in names:
            mod = load_platform(name)
            print(f"\n[{name}] 打开授权页：{mod.LIST_URL}")
            print(f"[{name}] 🔔 请现在在弹出的浏览器窗口里扫码/登录（最长等 10 分钟）——我在这等你。")
            with BrowserSession(name, headless=False) as session:
                session.navigate(mod.LIST_URL)
                ok = session.wait_for_login(mod.AUTH_MARKERS, timeout_s=600, platform=name)
                if ok:
                    print(f"[{name}] ✅ 授权完成，登录态已存入 ~/oracle-bone-profiles/{name}")
                else:
                    print(f"[{name}] ❌ 10 分钟内未完成登录——跳过（登录态未保存）")
                    auth_failed.append(name)
        if auth_failed:
            print(f"\nAUTH_FAILED={','.join(auth_failed)}（可单独重跑：collect.py <平台> --auth-only）")
            sys.exit(2)
        print("\n全部平台授权完成。以后日常采集可加 --headless 后台跑。")
        return

    all_unified = []
    needs_auth = []
    for idx, name in enumerate(names):
        if idx and args.platform == "all":
            print(f"⏳ 平台间隔 {PLATFORM_INTERVAL_S}s（防频控）...")
            time.sleep(PLATFORM_INTERVAL_S)
        print(f"▶ 采集 {name} ...")
        try:
            result = collect_one(name, args, out_dir)
            all_unified.extend(result["unified"])
            print(json.dumps(result["meta"], ensure_ascii=False, indent=2))
            if result["meta"].get("needs_auth"):
                needs_auth.append(name)
        except Exception as e:
            print(f"❌ [{name}] 采集失败：{e}")
            (out_dir / f"{name}-error.txt").write_text(str(e), encoding="utf-8")

    save_run_artifacts(out_dir, all_unified, {}, {"platforms": names, "total_unified": len(all_unified)})
    print(f"\n✅ 完成：{len(all_unified)} 条统一数据 → {out_dir / 'unified.json'}")
    if needs_auth:
        print(f"\n⚠️ {len(needs_auth)} 个平台登录态失效未采集：{'、'.join(needs_auth)}")
        print("恢复（一次一条，弹浏览器扫码，脚本会等你）：")
        for n in needs_auth:
            print(f"  {sys.executable} {Path(__file__).resolve()} {n} --auth-only")
        print(f"NEEDS_AUTH={','.join(needs_auth)}")
        print("下一步：")
        print(f"  python tools/snapshot_store.py archive --db {project / 'content-analytics.db'} --input {out_dir / 'unified.json'}")
        print(f"  python tools/dashboard.py --db {project / 'content-analytics.db'} --markdown")
        sys.exit(2)
    print("下一步：")
    print(f"  python tools/snapshot_store.py archive --db {project / 'content-analytics.db'} --input {out_dir / 'unified.json'}")
    print(f"  python tools/dashboard.py --db {project / 'content-analytics.db'} --markdown")


if __name__ == "__main__":
    main()
