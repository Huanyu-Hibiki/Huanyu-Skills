"""抖音创作者中心采集器（2026-08-19 实机校准）。

实测结构（creator.douyin.com 内容管理页 work_list API）：
  - 列表在响应顶层 items[]（非 data.aweme_list）；total 同层
  - 每条：id / description(标题) / create_time(unix) / video_info.duration(ms)
  - metrics{} 直接带五维增量指标：
      cover_click_rate(封面点击率) / bounce_rate_2s(跳出率) /
      completion_rate_5s(5s完播) / completion_rate(完播) / avg_view_second(平均播放秒)
  - 互动计数：metrics.{like,comment,share,collect}_count 等字符串字段
  - aweme_list[] 同响应也在（另一个视图），去重靠 items 优先

headless 会被风控给空壳——采集用 headed（默认）。
"""

LIST_URL = "https://creator.douyin.com/creator-micro/content/manage"
DETAIL_URL = "https://creator.douyin.com/creator-micro/work-management/work-detail/{wid}?enter_from=content"

ENDPOINTS = ["/janus/douyin/creator/pc/work_list"]

AUTH_MARKERS = {
    "login_hint": ["扫码登录", "登录抖音创作者平台", "验证码"],
    "ok_hint": ["作品管理", "内容管理", "数据中心"],
}

SELECTORS = {
    # DOM 兜底只保底：卡片区文本（监听层是主源）
    "video_card": "div[class*='video-card']",
}


def _pct(v):
    """'0.451613' → '45%'（抖音比率是小数串，转百分数展示）"""
    try:
        return f"{float(v) * 100:.1f}%"
    except (TypeError, ValueError):
        return ""


def _sec(v):
    """'14.645161' / 毫秒时长 → '14.6s'"""
    try:
        return f"{float(v):.1f}s"
    except (TypeError, ValueError):
        return ""


def _num(v):
    try:
        return int(float(str(v)))
    except (TypeError, ValueError):
        return 0


def parse_list_response(payload: dict) -> dict:
    data = payload or {}
    items_raw = data.get("items") or data.get("aweme_list") or []
    rows = []
    for it in items_raw:
        wid = str(it.get("id") or it.get("aweme_id") or it.get("item_id") or "")
        if not wid or wid in {r["作品ID"] for r in rows}:
            continue
        m = it.get("metrics") or {}
        stats = it.get("statistics") or {}
        # 互动计数（2026-08-19 实测 metrics 字段名）：view/like/comment/share/favorite/subscribe
        like = _num(m.get("like_count") or stats.get("digg_count"))
        share = _num(m.get("share_count") or stats.get("share_count"))
        comment = _num(m.get("comment_count") or stats.get("comment_count"))
        collect = _num(m.get("favorite_count") or stats.get("collect_count"))

        import time as _t
        ct = it.get("create_time")
        try:
            pub = _t.strftime("%Y-%m-%d", _t.localtime(int(ct))) if ct else ""
        except (TypeError, ValueError):
            pub = ""

        row = {
            "作品ID": wid,
            "标题": (it.get("description") or it.get("caption") or "").split("\n")[0][:80],
            "发布日期": pub,
            "时长": _num((it.get("video_info") or {}).get("duration")) // 1000,
            "播放量": _num(m.get("view_count") or stats.get("play_count")),
            "点赞量": like,
            "评论量": comment,
            "分享量": share,
            "收藏量": collect,
            "弹幕量": _num(m.get("danmaku_count")),
            "涨粉量": _num(m.get("subscribe_count")),
            # ── 五维增量指标（compass-retro 五维闸门直接消费）──
            "封面点击率": _pct(m.get("cover_click_rate")),
            "跳出率": _pct(m.get("bounce_rate_2s")),
            "跳出率口径": "2s" if m.get("bounce_rate_2s") else "",
            "5s完播率": _pct(m.get("completion_rate_5s")),
            "完播率": _pct(m.get("completion_rate")),
            "平均播放时长": _sec(m.get("avg_view_second")),
        }
        rows.append(row)
    total = data.get("total") or len(rows)
    return {"items": rows, "total": total}


def extract_dom_card(card) -> dict | None:
    """DOM 兜底：只认得出具体卡片链接/id 的元素，防垃圾行（时长冒充 ID 的教训）。"""
    try:
        # 抖音卡片有 data 属性或链接挂 id
        wid = card.get_attribute("data-id") or ""
        if not wid or not wid.isdigit():
            # 从卡片内链接挖 /video/<id>
            link = card.locator("a[href*='/video/']").first
            href = link.get_attribute("href", timeout=1000) or ""
            import re
            m = re.search(r"/video/(\d{6,})", href)
            wid = m.group(1) if m else ""
        if not wid:
            return None
        text = card.inner_text(timeout=2000)
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        title = next((l for l in lines if len(l) >= 4 and not l[:2].replace(":", "").isdigit()), "")
        return {"作品ID": wid, "标题": title[:80]}
    except Exception:
        return None


def detail_steps(page, wid=None):
    """详情页数据已由监听层 metrics 覆盖（五维直接在列表响应里），无需逐作品进详情页。"""
    return {}
