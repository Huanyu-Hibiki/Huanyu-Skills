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
# 详情入口：留在助手平台，detail_steps 点「数据中心」触发详情 API（监听层收五维）
DETAIL_URL = "https://channels.weixin.qq.com/platform/post/list"

ENDPOINTS = [
    "post/post_list",
    # 详情/数据 API 候选：finderassistant-bin 家族全收（parse 对未知形状返回空，无害）
    "finderassistant-bin",
]

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
    rows.extend(_five_dim_rows(payload))  # 详情/数据中心载荷分支（五维）
    return {"items": rows, "total": total}


# ── 五维增量指标（参照 douyin 统一键；视频号叫法：完播率/平均播放时长）──

_JSON_TERMS = {
    "完播率": ("completionRate", "completion_rate", "finishRate", "finish_rate"),
    "5s完播率": ("fiveSecondCompletionRate", "completion_rate_5s"),
    "平均播放时长": ("avgPlayDuration", "avg_play_duration", "avgViewSecond",
                  "avg_view_second", "averagePlayTime"),
    "封面点击率": ("coverClickRate", "cover_click_rate", "clickRate", "click_rate"),
    "跳出率": ("bounceRate", "bounce_rate_2s", "bounce_rate_3s"),
}
_BOUNCE_CALIBER = {"bounce_rate_2s": "2s", "bounce_rate_3s": "3s"}
_ID_KEYS = ("objectId", "object_id", "finderId", "id")
_DOM_TERMS = {
    "完播率": ("完播率", "完整播放率"),
    "平均播放时长": ("平均播放时长", "人均播放时长"),
    "跳出率": ("跳出率",),
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
                        # 与列表行同规则：export/UzFf... 取尾段做 ID
                        if "/" in wid:
                            wid = wid.split("/")[-1][:40]
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


def detail_steps(page, wid=None):
    """点「数据中心」触发详情/数据 API——监听层收五维（collect 统一回流）+ 页面文本双保险刮取。"""
    out = {}
    try:
        page.get_by_text("数据中心", exact=True).first.click(timeout=6000)
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
