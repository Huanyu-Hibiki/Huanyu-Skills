"""小红书创作服务平台采集器（2026-08-19 实机校准）。

实测：笔记管理页 = /new/note-manager（SPA 路由，侧栏菜单进入）；
列表 API = /api/galaxy/v2/creator/note/user/posted?tab=0&page=0；
笔记详情数据 = /api/galaxy/creator/data/note_detail_new 与 /datacenter/note/base?note_id=...
首页入口 /new/home 已登录会自动跳转；直接进 note-manager 即可。
"""

LIST_URL = "https://creator.xiaohongshu.com/new/note-manager"

ENDPOINTS = [
    "/api/galaxy/v2/creator/note/user/posted",
    "/api/galaxy/creator/datacenter/note/analyze/list",
    "/api/galaxy/creator/data/note_detail_new",
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
    return {"items": rows, "total": total or len(rows)}


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


def detail_steps(page):
    """小红书详情指标以数据分析 API 监听为主，无需额外页面动作。"""
    return {}
