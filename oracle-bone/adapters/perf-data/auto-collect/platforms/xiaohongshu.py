"""小红书创作服务平台采集器（2026-08-19 实机校准）。

实测：笔记管理页 = /new/note-manager（SPA 路由，侧栏菜单进入）；
列表 API = /api/galaxy/v2/creator/note/user/posted?tab=0&page=0；
笔记详情数据 = /api/galaxy/creator/data/note_detail_new 与 /datacenter/note/base?note_id=...
首页入口 /new/home 已登录会自动跳转；直接进 note-manager 即可。
"""

LIST_URL = "https://creator.xiaohongshu.com/new/note-manager"
# 详情入口：留在笔记管理页，detail_steps 点侧栏「数据分析」触发 analyze API（监听层收五维）
DETAIL_URL = "https://creator.xiaohongshu.com/new/note-manager"

ENDPOINTS = [
    "/api/galaxy/v2/creator/note/user/posted",
    "/api/galaxy/creator/datacenter/note/analyze/list",
    "/api/galaxy/creator/data/note_detail_new",
    "/api/galaxy/creator/datacenter/note/base",
]

AUTH_MARKERS = {
    "login_hint": ["扫码登录", "登录", "手机号登录"],
    "ok_hint": ["笔记管理", "数据分析", "创作者中心"],
}

SELECTORS = {
    "note_card": "[class*='note-item'], [class*='note_card'], div[class*='card']",
}


def parse_list_response(payload: dict) -> dict:
    """posted API 实测结构（2026-08-19）：
    data.notes[] = {id, display_title, likes, view_count, shared_count,
                    comments_count, time('2026-08-17 23:30'), visible_time(unix), type}
    data.tags[0].notes_count = 总数
    """
    data = (payload or {}).get("data") or {}
    notes = data.get("notes") or []
    rows = []
    for n in notes:
        wid = str(n.get("id") or "")
        if not wid:
            continue
        pub = str(n.get("time") or "")[:10]  # '2026-08-17 23:30' → '2026-08-17'
        row = {
            "作品ID": wid,
            "标题": n.get("display_title") or "",
            "发布日期": pub,
            "内容类型": "note",
            "阅读量": _n(n.get("view_count")),
            "点赞量": _n(n.get("likes")),
            "评论量": _n(n.get("comments_count")),
            "分享量": _n(n.get("shared_count")),
        }
        rows.append(row)
    tags = data.get("tags") or []
    total = tags[0].get("notes_count") if tags and isinstance(tags[0], dict) else len(rows)
    rows.extend(_five_dim_rows(payload))  # 数据分析/note_detail 载荷分支（五维）
    return {"items": rows, "total": total or len(rows)}


# ── 五维增量指标（参照 douyin 统一键；小红书叫法：完播率/平均观看时长/点击率）──

_JSON_TERMS = {
    "完播率": ("completion_rate", "finish_rate", "completionRate", "finishRate"),
    "5s完播率": ("completion_rate_5s", "five_second_completion_rate"),
    "平均播放时长": ("avg_view_second", "avg_watch_duration", "avg_watch_time",
                  "avgWatchDuration", "average_watch_duration"),
    "封面点击率": ("cover_click_rate", "click_rate", "ctr", "clickRate"),
    "跳出率": ("bounce_rate_2s", "bounce_rate_3s", "bounce_rate", "bounceRate"),
}
_BOUNCE_CALIBER = {"bounce_rate_2s": "2s", "bounce_rate_3s": "3s"}
_ID_KEYS = ("note_id", "noteId", "id")
_DOM_TERMS = {
    "完播率": ("完播率",),
    "平均播放时长": ("平均观看时长", "平均播放时长"),
    "封面点击率": ("点击率",),
    "5s完播率": ("5秒完播率", "5s完播率"),
}


def _fmt_pct(v):
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


def _five_dim_rows(payload) -> list:
    rows = []

    def walk(o):
        if isinstance(o, dict):
            dim = _five_dim_from_obj(o)
            if dim:
                wid = ""
                for ik in _ID_KEYS:
                    if o.get(ik):
                        wid = str(o.get(ik))
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


def _n(v):
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return 0


def extract_dom_card(card) -> dict | None:
    try:
        text = card.inner_text(timeout=2000)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return None
        return {"作品ID": lines[0][:60], "标题": lines[0][:60]}
    except Exception:
        return None


def detail_steps(page, wid=None):
    """点侧栏「数据分析」触发 analyze/note_detail API——监听层收五维（collect 统一回流）。

    一次点击全量笔记的数据分析表都会回包，逐作品重复触发幂等无害；
    页面文本同时按 DOM 叫法刮一遍作双保险。
    """
    out = {}
    try:
        page.get_by_text("数据分析", exact=True).first.click(timeout=6000)
        page.wait_for_timeout(3000)
        out = _scrape_five_dim_text(page.inner_text("body", timeout=8000))
    except Exception:
        pass
    return out


_PCT_RE = r"(\d+(?:\.\d+)?\s*%)"
_DUR_RE = r"(\d+(?:\.\d+)?\s*(?:秒|s\b)|\d+分\d+秒|\d{1,2}:\d{2}(?::\d{2})?)"


def _dur_norm(v: str) -> str:
    import re as _re
    v = v.strip()
    m = _re.match(r"^(\d+)分(\d+)秒$", v)
    if m:
        return f"{int(m.group(1)) * 60 + int(m.group(2))}s"
    m = _re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", v)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)
        return f"{h * 3600 + mi * 60 + s}s"
    m = _re.match(r"^(\d+(?:\.\d+)?)\s*(?:秒|s)$", v, _re.IGNORECASE)
    if m:
        return f"{float(m.group(1)):.1f}s"
    return v


def _scrape_five_dim_text(text: str) -> dict:
    import re as _re
    out = {}
    for key, labels in _DOM_TERMS.items():
        vre = _DUR_RE if key == "平均播放时长" else _PCT_RE
        for lab in labels:
            m = _re.search(_re.escape(lab) + r"[\s:：]*" + vre, text)
            if m:
                out[key] = _dur_norm(m.group(1)) if key == "平均播放时长" else m.group(1).replace(" ", "")
                break
    return out
