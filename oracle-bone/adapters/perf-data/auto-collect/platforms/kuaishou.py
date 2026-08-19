"""快手创作者中心采集器。

已知后台：
  作品数据: cp.kuaishou.com 统计页（API 响应含作品行）
"""

LIST_URL = "https://cp.kuaishou.com/article/manage/video"

ENDPOINTS = [
    "/rest/kp/query/video/info",
    "/rest/kp/statistic/video",
    "/api/video/list",
]

AUTH_MARKERS = {
    "login_hint": ["扫码登录", "登录", "手机号"],
    "ok_hint": ["作品管理", "数据统计", "创作者中心"],
}

SELECTORS = {
    "video_card": "[class*='video-item'], tr[class*='row'], [class*='work-item']",
}


def parse_list_response(payload: dict) -> dict:
    data = (payload or {}).get("data") or payload or {}
    items = data.get("list") or data.get("items") or data.get("rows") or data.get("videos") or []
    rows = []
    for v in items:
        stat = v.get("stat") or v.get("statistics") or v
        row = {
            "作品ID": str(v.get("photoId") or v.get("id") or v.get("workId") or ""),
            "标题": v.get("name") or v.get("title") or v.get("caption") or "",
            "发布日期": v.get("createTime") or v.get("create_time") or "",
            "播放量": stat.get("viewCount") or stat.get("play") or 0,
            "点赞量": stat.get("likeCount") or 0,
            "评论量": stat.get("commentCount") or 0,
            "分享量": stat.get("shareCount") or 0,
            "收藏量": stat.get.get("collectCount", 0) if isinstance(stat, dict) else 0,
        }
        try:
            row["收藏量"] = stat.get("collectCount") or 0
        except Exception:
            row["收藏量"] = 0
        if row["作品ID"]:
            rows.append(row)
    total = data.get("total") or len(rows)
    return {"items": rows, "total": total}


def extract_dom_card(card) -> dict | None:
    try:
        text = card.inner_text(timeout=2000)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return None
        return {"作品ID": lines[0][:40], "标题": lines[0][:60]}
    except Exception:
        return None


def detail_steps(page):
    """快手详情指标由 API 监听覆盖；无额外页面动作。"""
    return {}
