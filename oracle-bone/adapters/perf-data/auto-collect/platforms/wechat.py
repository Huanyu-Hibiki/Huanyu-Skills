"""微信视频号助手采集器（2026-08-19 实机校准）。

实测要点：
  - 列表页 URL：channels.weixin.qq.com/platform/post/list（进入后需点"内容管理→视频"触发加载）
  - 列表 API：/micro/content/cgi-bin/mmfinderassistant-bin/post/post_list（状态码 201 是正常业务响应）
  - 结构：data.list[] = {objectId, createTime(unix), readCount, likeCount,
          forwardCount, favCount, commentCount, desc.description(首行=标题)}
    data.totalCount = 总数
  - 登录态：微信扫码，会话时效短，过期重跑 --auth-only
"""

LIST_URL = "https://channels.weixin.qq.com/platform/post/list"

ENDPOINTS = ["post/post_list"]

AUTH_MARKERS = {
    "login_hint": ["扫码登录", "微信扫码", "登录视频号"],
    "ok_hint": ["内容管理", "视频号助手", "数据中心"],
}

SELECTORS = {
    "video_card": "[class*=finder] [class*=item]",
}


def parse_list_response(payload: dict) -> dict:
    import time as _t

    data = (payload or {}).get("data") or {}
    rows = []
    for it in data.get("list") or []:
        wid = str(it.get("objectId") or it.get("id") or "")
        if not wid:
            continue
        desc = it.get("desc") or {}
        title = str(desc.get("description") or desc.get("shortTitle") or "").split("\n")[0][:80]
        ct = it.get("createTime")
        try:
            pub = _t.strftime("%Y-%m-%d", _t.localtime(int(ct))) if ct else ""
        except (TypeError, ValueError):
            pub = ""
        rows.append({
            "作品ID": wid.split("/")[-1][:40] if "/" in wid else wid[:40],  # export/UzFf... → 尾段做 ID
            "标题": title,
            "发布日期": pub,
            "播放量": _n(it.get("readCount")),
            "点赞量": _n(it.get("likeCount")),
            "评论量": _n(it.get("commentCount")),
            "分享量": _n(it.get("forwardCount")),
            "收藏量": _n(it.get("favCount")),
        })
    total = data.get("totalCount") or len(rows)
    return {"items": rows, "total": total}


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
        row = {"作品ID": "", "标题": lines[0][:60]}
        for l in lines:
            for label, key in (("播放", "播放量"), ("阅读", "播放量"), ("点赞", "点赞量"),
                               ("推荐", "收藏量"), ("转发", "分享量"), ("评论", "评论量")):
                if l.startswith(label):
                    digits = "".join(ch for ch in l if ch.isdigit() or ch in ".万亿,")
                    if digits:
                        row[key] = digits
        # DOM 兜底无真实 ID 时由框架过滤（is_valid_work_id），监听层补齐
        return row if len(lines) > 2 else None
    except Exception:
        return None


def detail_steps(page):
    return {}


def post_navigate(page):
    """进入列表页后触发作品列表加载：点"内容管理 → 视频"（SPA 路由，不点不发 post_list 请求）。"""
    try:
        page.get_by_text("内容管理", exact=True).first.click(timeout=6000)
        page.wait_for_timeout(1500)
    except Exception:
        pass
    try:
        page.get_by_text("视频", exact=True).first.click(timeout=6000)
        page.wait_for_timeout(2000)
    except Exception:
        pass
