"""B 站创作者中心采集器（2026-08-19 实机校准）。

实测要点：
  - 稿件管理页 URL：member.bilibili.com/platform/upload-manager/article
  - 卡片容器 .article-card；BV 号 + 标题挂在 <a href="/video/BVxxx"> 链接上
  - headless 模式会被 B站风控给空壳页——采集必须 headed（默认已是）
"""

import re

LIST_URL = "https://member.bilibili.com/platform/upload-manager/article"
# 详情入口：稿件管理页本卡片「数据」弹窗（wid 以 query 参数随页携带，弹窗内刮五维）
DETAIL_URL = "https://member.bilibili.com/platform/upload-manager/article?bvid={wid}"

ENDPOINTS = [
    "/platform/upload-manager/arclist",
    "/x/member/archives",
    "/platform/web/archives",
    # 单稿件数据弹窗的候选 API（首跑 --debug 校准，命中即由监听层自动补五维）
    "/platform/upload-manager/view",
    "/creative-web/rank/archive",
]

AUTH_MARKERS = {
    "login_hint": ["扫码登录", "登录", "大会员"],
    "ok_hint": ["稿件管理", "内容管理", "创作中心"],
}

SELECTORS = {
    # 实测（2026-08-19 授权账号校准）：稿件管理页卡片容器 = .article-card
    "video_card": ".article-card",
}


def parse_list_response(payload: dict) -> dict:
    data = (payload or {}).get("data") or {}
    arc_audits = []
    for container in ("arc_audits", "list", "items", "rows"):
        v = data.get(container)
        if isinstance(v, list) and v:
            arc_audits = v
            break
    rows = []
    for a in arc_audits:
        arc = a.get("Archive") or a.get("archive") or a
        stat = arc.get("stat") or a.get("stat") or {}
        row = {
            "作品ID": str(arc.get("bvid") or arc.get("aid") or a.get("aid") or ""),
            "标题": arc.get("title") or "",
            "发布日期": arc.get("ptime") or arc.get("created_at") or "",
            "播放量": stat.get("view") or stat.get("click") or 0,
            "点赞量": stat.get("like") or 0,
            "硬币/投币量": stat.get("coin") or 0,
            "收藏量": stat.get("fav") or 0,
            "分享量": stat.get("share") or 0,
            "弹幕量": stat.get("danmaku") or stat.get("dm") or 0,
            "评论量": stat.get("reply") or 0,
        }
        if "硬币/投币量" in row:
            row["投币量"] = row.pop("硬币/投币量")
        if row["作品ID"]:
            rows.append(row)
    rows.extend(_five_dim_rows(payload, id_keys=("bvid", "aid", "archive_id")))  # 详情/分析载荷分支
    page_info = (payload or {}).get("data", {}).get("page") or {}
    total = page_info.get("count") or data.get("total") or len(rows)
    return {"items": rows, "total": total}


# ── 五维增量指标（参照 douyin 统一键；B站无跳出率/5s完播——留空不硬凑）──

_JSON_TERMS = {
    "完播率": ("completion_rate", "finish_rate", "completionRate", "finishRate"),
    "5s完播率": ("completion_rate_5s", "five_second_completion_rate"),
    "平均播放时长": ("avg_view_second", "avg_play_duration", "avg_watch_duration",
                  "avgPlayDuration", "average_play_time", "avg_play_time"),
    "封面点击率": ("cover_click_rate", "click_rate", "ctr", "clickRate"),
    "跳出率": ("bounce_rate_2s", "bounce_rate_3s", "bounce_rate", "bounceRate"),
}
_BOUNCE_CALIBER = {"bounce_rate_2s": "2s", "bounce_rate_3s": "3s"}
_DOM_TERMS = {
    "完播率": ("完播率", "播放完成率"),
    "平均播放时长": ("平均播放时长", "人均播放时长"),
    "封面点击率": ("点击率",),
}


def _fmt_pct(v):
    """容错百分数：'45.2%' 原样 / 0.452 → '45.2%' / 45.2 → '45.2%'"""
    s = str(v).strip()
    if not s:
        return ""
    if "%" in s:
        return s.replace(" ", "")
    try:
        f = float(s)
    except ValueError:
        return s
    return f"{f * 100:.1f}%" if 0 < f <= 1 else f"{f:.1f}%"


def _fmt_sec(v):
    """容错时长：秒数值（>36000 视为毫秒）/ '83' → '83.0s'"""
    try:
        f = float(str(v).strip())
        if f > 36000:
            f /= 1000
        return f"{f:.1f}s"
    except (TypeError, ValueError):
        return str(v)


def _five_dim_from_obj(o: dict) -> dict:
    hits, caliber = {}, ""
    for key, names in _JSON_TERMS.items():
        for n in names:
            v = o.get(n)
            if v not in (None, "", 0, "0"):
                hits[key] = _fmt_sec(v) if key == "平均播放时长" else _fmt_pct(v)
                if n in _BOUNCE_CALIBER:
                    caliber = _BOUNCE_CALIBER[n]
                break
    if caliber:
        hits["跳出率口径"] = caliber
    return hits if len([k for k in hits if k != "跳出率口径"]) >= 2 else {}


def _five_dim_rows(payload, id_keys) -> list:
    """递归扫详情/分析载荷：找带 ≥2 个五维候选字段且含作品 id 的对象 → 行。"""
    rows = []

    def walk(o):
        if isinstance(o, dict):
            dim = _five_dim_from_obj(o)
            if dim:
                wid = ""
                for ik in id_keys:
                    for cand in (o.get(ik), (o.get("archive") or {}).get("bvid") if isinstance(o.get("archive"), dict) else None):
                        if cand:
                            wid = str(cand)
                            break
                    if wid:
                        break
                if wid:
                    rows.append({"作品ID": wid, **dim})
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(payload)
    return rows


def extract_dom_card(card) -> dict | None:
    """DOM 提取（2026-08-19 实测校准）。

    卡片结构：BV 和标题分别挂在 <a href="/video/BVxxx"> 链接上（不在主文本流）；
    文本流是 竖线分隔的元数据：时长 | 标题 | 发布时间 | 编辑 | 数据 | 计数列...。
    """
    try:
        # BV 号：卡片内第一个指向 /video/BV 的链接
        link = card.locator('a[href*="/video/BV"]').first
        href = link.get_attribute("href", timeout=2000) or ""
        m = re.search(r"(BV[0-9A-Za-z]{10})", href)
        if not m:
            return None
        wid = m.group(1)

        # 标题：同类链接中取 inner_text 非空的那个（一个挂时长一个挂标题）
        title = ""
        links = card.locator('a[href*="/video/BV"]')
        for i in range(min(links.count(), 3)):
            t = (links.nth(i).inner_text(timeout=1000) or "").strip()
            if t and not re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", t):  # 排除时长行
                title = t
                break

        # 元数据行：时长 | 标题 | 日期 | 编辑 | 数据 | 计数...
        text = card.inner_text(timeout=2000)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        duration = ""
        pub_date = ""
        numbers = []
        for l in lines:
            if re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", l):
                duration = l
            elif re.match(r"^\d{4}年\d{2}月\d{2}日", l):
                pub_date = l
            elif re.match(r"^[\d.,万亿]+$", l):
                numbers.append(l)
        # 日期转 ISO
        dm = re.match(r"(\d{4})年(\d{2})月(\d{2})日", pub_date)
        pub_iso = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else ""

        row = {
            "作品ID": wid,
            "标题": title,
            "发布日期": pub_iso,
            "时长": duration,
        }
        # 计数列按 B站稿件管理顺序：播放 点赞 投币 收藏 分享 弹幕 评论（部分账号只有前几列，保守只取播放）
        if numbers:
            row["播放量"] = numbers[0]
        return row if row["作品ID"] else None
    except Exception:
        return None


def detail_steps(page, wid=None):
    """单稿件五维：稿件管理页定位本 BV 卡片 → 点「数据」→ 弹窗文本刮取。

    B站指标叫法映射：完播率(播放完成率) / 平均播放时长(人均播放时长) /
    封面点击率(点击率)。无 2s/3s 跳出率与 5s完播——留空不硬凑。
    弹窗数据同时会发 XHR——若命中 ENDPOINTS 由监听层兜底（双保险）。
    """
    if not wid:
        return {}
    out = {}
    try:
        card = page.locator(SELECTORS["video_card"], has=page.locator(f'a[href*="{wid}"]')).first
        card.scroll_into_view_if_needed(timeout=4000)
        card.get_by_text("数据", exact=True).first.click(timeout=4000)
        page.wait_for_timeout(2500)  # 等弹窗渲染 + XHR 回包
        out = _scrape_five_dim_text(page.inner_text("body", timeout=8000))
    except Exception:
        pass
    finally:
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        except Exception:
            pass
    return out


_PCT_RE = r"(\d+(?:\.\d+)?\s*%)"
_DUR_RE = r"(\d+(?:\.\d+)?\s*(?:秒|s\b)|\d+分\d+秒|\d{1,2}:\d{2}(?::\d{2})?)"


def _dur_norm(v: str) -> str:
    v = v.strip()
    m = re.match(r"^(\d+)分(\d+)秒$", v)
    if m:
        return f"{int(m.group(1)) * 60 + int(m.group(2))}s"
    m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", v)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        return f"{h * 3600 + mi * 60 + s}s"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(?:秒|s)$", v, re.IGNORECASE)
    if m:
        return f"{float(m.group(1)):.1f}s"
    return v


def _scrape_five_dim_text(text: str) -> dict:
    """按平台叫法从页面文本刮五维（label → 紧随的百分比/时长值）。"""
    out = {}
    for key, labels in _DOM_TERMS.items():
        vre = _DUR_RE if key == "平均播放时长" else _PCT_RE
        for lab in labels:
            m = re.search(re.escape(lab) + r"[\s:：]*" + vre, text)
            if m:
                out[key] = _dur_norm(m.group(1)) if key == "平均播放时长" else m.group(1).replace(" ", "")
                break
    return out
