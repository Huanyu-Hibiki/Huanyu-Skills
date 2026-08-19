#!/usr/bin/env python3
"""oracle-bone link_resolver — 发布链接解析 + 作品自动匹配。

给 oracle-publish 用：用户粘一堆平台链接 → 解析出 平台/内容ID/标题 →
模糊匹配到项目内待发布的作品（shoots 队列 / 无 published_at 的 prediction）→
一张确认表，用户点头即完成登记，不再手动对号。

标题抓取策略（按可靠性排序）：
  B站  → 公开 view API（无需登录）
  其他 → 跟随短链重定向 → 抓 HTML <title> / og:title
  失败 → 优雅降级：返回平台+ID（URL 模式解析不需要网络），标题留给用户补

用法:
  python link_resolver.py resolve "https://v.douyin.com/xxx" "https://b23.tv/yyy"
  python link_resolver.py match --title "古人怎么审合同" --project <项目根>
  python link_resolver.py auto  "https://v.douyin.com/xxx" --project <项目根>
"""

import argparse
import difflib
import json
import re
import sys
import urllib.request
from pathlib import Path

UA_DESKTOP = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
UA_MOBILE = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
FETCH_TIMEOUT = 10

# 分享短链域是移动端场景——手机 UA 命中率高得多
MOBILE_UA_PLATFORMS = {"douyin", "kuaishou", "xiaohongshu"}

REFERER_BY_PLATFORM = {
    "douyin": "https://www.douyin.com/",
    "xiaohongshu": "https://www.xiaohongshu.com/",
    "bilibili": "https://www.bilibili.com/",
    "kuaishou": "https://www.kuaishou.com/",
    "wechat": "https://channels.weixin.qq.com/",
}


def _headers(platform: str, referer: str = "") -> dict:
    ua = UA_MOBILE if platform in MOBILE_UA_PLATFORMS else UA_DESKTOP
    h = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer or platform in REFERER_BY_PLATFORM:
        h["Referer"] = referer or REFERER_BY_PLATFORM[platform]
        h["Sec-Fetch-Site"] = "same-origin" if not referer else "cross-site"
    return h

PLATFORM_PATTERNS = [
    (r"(?:v\.douyin\.com|douyin\.com|iesdouyin\.com)", "douyin"),
    (r"(?:xhslink\.com|xiaohongshu\.com)", "xiaohongshu"),
    (r"(?:b23\.tv|bilibili\.com|bili2233\.cn)", "bilibili"),
    (r"(?:v\.kuaishou\.com|kuaishou\.com|chenzhongtech\.com)", "kuaishou"),
    (r"(?:channels\.weixin\.qq\.com|sph\.weixin\.qq\.com)", "wechat"),
]

CONTENT_ID_PATTERNS = {
    "douyin": [r"/video/(\d{6,})", r"modal_id=(\d{6,})", r"item_ids?=(\d{6,})", r"/note/(\d{6,})"],
    "xiaohongshu": [r"/explore/([0-9a-f]{16,})", r"/discovery/item/([0-9a-f]{16,})", r"/item/([0-9a-f]{16,})"],
    "bilibili": [r"(BV[0-9A-Za-z]{10})"],
    "kuaishou": [r"/short-video/([\w]{8,})", r"/(?:f|v)/([\w]{8,})"],
    "wechat": [r"finder_stream_id=([\w]+)", r"/finder/([\w]+)"],
}

# 标题里的平台后缀清理（可能带多层："- 哔哩哔哩_bilibili"）
TITLE_SUFFIX_RE = re.compile(
    r"[\s]*[-_|#·：:]?\s*(?:抖音|哔哩哔哩|bilibili|B站|小红书|快手|微信视频号|视频号|西瓜视频|今日头条)[\s]*(?:[-_|#·]\s*(?:抖音|哔哩哔哩|bilibili|B站|小红书|快手|微信视频号|视频号|西瓜视频|今日头条))*\s*$",
    re.IGNORECASE,
)


def detect_platform(url: str) -> str:
    for pattern, platform in PLATFORM_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "unknown"


def extract_content_id(url: str, platform: str) -> str:
    for pat in CONTENT_ID_PATTERNS.get(platform, []):
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return ""


def _http_get(url: str, platform: str = "", referer: str = ""):
    req = urllib.request.Request(url, headers=_headers(platform or detect_platform(url), referer))
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read(512 * 1024).decode("utf-8", errors="replace")
        return getattr(resp, "geturl", lambda: url)(), data


def _http_get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA_DESKTOP, "Referer": "https://www.bilibili.com/"})
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _clean_title(t: str) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    t = TITLE_SUFFIX_RE.sub("", t)
    # HTML 实体
    for a, b in (("&amp;", "&"), ("&quot;", '"'), ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
        t = t.replace(a, b)
    return t.strip()


def _title_from_html(html: str) -> str:
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if not m:
        m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html, re.I)
    if not m:
        m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return _clean_title(m.group(1)) if m else ""


def _bilibili_title(bvid: str) -> str:
    try:
        payload = _http_get_json(f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
        return _clean_title((payload.get("data") or {}).get("title") or "")
    except Exception:
        return ""


# ── 第 3 层：真浏览器抓取（复用 auto-collect 已授权 Profile）──────────
# 原理：抖音/小红书/快手/视频号的分享页对"无 Cookie 的裸请求"极不友好，
# 但对"带着你自己登录态的真实 Chromium"基本不设防——因为那就是正常用户。
# 只用于你自己的作品链接；不装 playwright 时自动跳过。

AUTO_COLLECT_DIR = Path(__file__).parent.parent / "adapters" / "perf-data" / "auto-collect"


def _browser_fetch(url: str, platform: str, headless: bool = True):
    """真 Chromium 打开链接 → (final_url, title)。失败抛异常（调用方降级）。

    Profile 复用 auto-collect 的授权态（~/oracle-bone-profiles/<platform>/）——
    跑过 collect.py <platform> --auth-only 之后，这里就是"你本人浏览器"。
    """
    if platform not in ("douyin", "xiaohongshu", "bilibili", "kuaishou", "wechat"):
        raise RuntimeError(f"platform {platform} 无授权 Profile，浏览器层不适用")
    if not AUTO_COLLECT_DIR.exists():
        raise RuntimeError("未找到 auto-collect 目录")
    sys.path.insert(0, str(AUTO_COLLECT_DIR))
    try:
        from core.browser import BrowserSession
    except ImportError as e:
        raise RuntimeError(f"playwright 未安装（{e}）——跳过浏览器层") from e

    with BrowserSession(platform, headless=headless) as session:
        page = session.navigate(url, timeout_ms=20000)
        page.wait_for_timeout(2500)
        title = _clean_title(page.title() or "")
        if not title:
            try:
                title = _title_from_html(page.content())
            except Exception:
                pass
        return page.url, title


def resolve_one(url: str, use_browser: bool = False) -> dict:
    """三层升级解析：完整浏览器头 HTTP →（失败/无标题且 use_browser）→ 真浏览器授权态。"""
    import time as _time
    out = {"url": url, "platform": detect_platform(url), "content_id": "", "title": "",
           "resolved_url": "", "tier": "", "ok": True, "error": ""}

    # ── 第 1-2 层：HTTP（带完整浏览器指纹头 + 移动端 UA + 退避重试）──
    last_err = None
    for attempt in range(2):
        try:
            referer = REFERER_BY_PLATFORM.get(out["platform"], "")
            final_url, html = _http_get(url, out["platform"], referer)
            out["tier"] = "http"
            out["resolved_url"] = final_url
            if not out["content_id"]:
                out["content_id"] = (extract_content_id(final_url, out["platform"])
                                     or extract_content_id(url, out["platform"]))
            if out["platform"] == "bilibili" and out["content_id"].startswith("BV"):
                out["title"] = _bilibili_title(out["content_id"]) or _title_from_html(html)
            else:
                out["title"] = _title_from_html(html)
            if out["title"]:
                return out
            # 有响应但无任何标题线索 → JS 挑战页（WAF 空壳，重试无意义）
            last_err = "js_challenge_page"
            break
        except Exception as e:
            last_err = str(e)[:100]
            out["content_id"] = extract_content_id(url, out["platform"])
            if attempt == 0:
                _time.sleep(2)  # 退避后重试一次（429/网络抖动）

    # ── 第 3 层：真浏览器（你自己的授权 Profile）──
    if use_browser:
        try:
            final_url, title = _browser_fetch(url, out["platform"])
            out["tier"] = "browser"
            out["resolved_url"] = final_url
            if not out["content_id"]:
                out["content_id"] = extract_content_id(final_url, out["platform"])
            out["title"] = title
            if out["title"]:
                return out
            last_err = "browser_title_empty"
        except Exception as e:
            last_err = f"{last_err} | browser: {str(e)[:80]}"

    # ── 全层失败：URL 模式解析保底（平台+ID 通常仍有）──
    out["ok"] = False
    out["error"] = f"{last_err}（平台和 ID 已解析，标题请手动补）" if out["content_id"] else f"fetch_failed: {last_err}"
    return out


# ── 作品模糊匹配 ──────────────────────────────────────────

def _norm(s: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", (s or "").lower())


def load_candidates(project: Path) -> list[dict]:
    """待发布候选：shoots 队列 + 无 Published at 的 prediction + 未发布作品目录。"""
    candidates = []
    state_file = project / ".oracle-state.json"
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
            for s in state.get("shoots", []):
                candidates.append({
                    "source": "shoots",
                    "work_folder": s.get("work_folder", ""),
                    "prediction_file": s.get("prediction_file", ""),
                    "title": Path(s.get("work_folder", "")).name.split("_", 1)[-1],
                    "track": s.get("track", ""),
                })
        except Exception:
            pass
    for pred in project.glob("[0-9][0-9][0-9]_*/predictions/*.md"):
        try:
            text = pred.read_text(encoding="utf-8", errors="replace")[:2000]
            if re.search(r"^\*\*Published at\*\*", text, re.M):
                continue  # 已发布
            m = re.search(r"^\*\*Title\*\*:\s*(.+)$", text, re.M)
            candidates.append({
                "source": "prediction",
                "work_folder": pred.parent.parent.name,
                "prediction_file": str(pred.relative_to(project)),
                "title": (m.group(1).strip() if m else pred.stem),
                "track": (re.search(r"^\*\*Track\*\*:\s*(.+)$", text, re.M) or [None, ""])[1] if re.search(r"^\*\*Track\*\*:", text, re.M) else "",
            })
        except Exception:
            continue
    # 去重（同一作品 prediction 和 shoots 都命中时保 prediction——带完整标题）
    seen, out = set(), []
    for c in sorted(candidates, key=lambda x: 0 if x["source"] == "prediction" else 1):
        key = c["work_folder"]
        if key and key not in seen:
            seen.add(key)
            out.append(c)
    return out


def match_title(title: str, candidates: list[dict], top_n=3) -> list[dict]:
    if not title:
        return []
    scores = []
    for c in candidates:
        s1 = difflib.SequenceMatcher(None, _norm(title), _norm(c["title"])).ratio()
        # 包含关系加分（解析标题常是完整标题，作品名是短版）
        a, b = _norm(title), _norm(c["title"])
        s2 = min(len(a), len(b)) / max(len(a), len(b)) if (a and b and (a in b or b in a)) else 0
        scores.append({**c, "score": round(max(s1, s2 * 0.95), 3)})
    scores.sort(key=lambda x: x["score"], reverse=True)
    return scores[:top_n]


def auto_flow(urls: list[str], project: Path, use_browser: bool = False) -> dict:
    results = []
    for url in urls:
        r = resolve_one(url, use_browser=use_browser)
        # HTTP 层没拿到标题且允许浏览器层 → 单链接升级重试（auto 模式自动升层）
        if use_browser and not r["title"]:
            try:
                final_url, title = _browser_fetch(url, r["platform"])
                r.update({"tier": "browser", "resolved_url": final_url, "title": title, "ok": bool(title)})
                if title and not r["content_id"]:
                    r["content_id"] = extract_content_id(final_url, r["platform"])
                if title:
                    r["error"] = ""
            except Exception as e:
                r["error"] = f"{r['error']} | browser: {str(e)[:60]}"
        r["matches"] = match_title(r["title"], load_candidates(project)) if r["title"] else []
        results.append(r)
    return {"count": len(results), "results": results}


def render_table(payload: dict) -> str:
    lines = ["🔗 链接解析 + 作品匹配", ""]
    for i, r in enumerate(payload["results"], 1):
        flag = "✅" if r["title"] else "⚠️ "
        tier = {"http": "HTTP", "browser": "浏览器"}.get(r.get("tier", ""), "")
        lines.append(f"{flag} [{i}] {r['platform']} · ID={r['content_id'] or 'pending'}" + (f" · {tier}层" if tier else ""))
        lines.append(f"     标题: {r['title'] or '（未取到——' + r['error'] + '）'}")
        for m in r.get("matches", []):
            star = " ⭐" if m["score"] >= 0.55 else ""
            lines.append(f"     → 匹配: {m['work_folder']}（{m['source']}，score={m['score']}）{star}")
        lines.append("")
    lines.append("确认匹配请回编号+作品名（如 '1 003_古人审合同'）；匹配错请纠正；标题缺失请补一句。")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_r = sub.add_parser("resolve")
    p_r.add_argument("urls", nargs="+")
    p_r.add_argument("--browser", action="store_true", help="HTTP 失败时升层：真浏览器（复用 auto-collect 授权 Profile）")
    p_m = sub.add_parser("match")
    p_m.add_argument("--title", required=True)
    p_m.add_argument("--project", default=".")
    p_a = sub.add_parser("auto")
    p_a.add_argument("urls", nargs="+")
    p_a.add_argument("--project", default=".")
    p_a.add_argument("--browser", action="store_true", help="失败自动升层到真浏览器（需先跑过对应平台 --auth-only）")
    args = ap.parse_args()

    if args.cmd == "resolve":
        print(json.dumps([resolve_one(u, use_browser=args.browser) for u in args.urls], ensure_ascii=False, indent=2))
    elif args.cmd == "match":
        print(json.dumps(match_title(args.title, load_candidates(Path(args.project))), ensure_ascii=False, indent=2))
    else:
        print(render_table(auto_flow(args.urls, Path(args.project), use_browser=args.browser)))


if __name__ == "__main__":
    main()
