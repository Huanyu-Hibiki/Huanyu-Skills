"""B 站创作者中心采集器（2026-08-19 实机校准）。

实测要点：
  - 稿件管理页 URL：member.bilibili.com/platform/upload-manager/article
  - 卡片容器 .article-card；BV 号 + 标题挂在 <a href="/video/BVxxx"> 链接上
  - headless 模式会被 B站风控给空壳页——采集必须 headed（默认已是）
"""

import re

LIST_URL = "https://member.bilibili.com/platform/upload-manager/article"

ENDPOINTS = [
    "/platform/upload-manager/arclist",
    "/x/member/archives",
    "/platform/web/archives",
]

AUTH_MARKERS = {
    "login_hint": ["扫码登录", "登录", "大会员"],
    "ok_hint": ["稿件管理", "内容管理", "创作中心"],
}

SELECTORS = {
    # 实测（2026-08-19 授权账号校准）：稿件管理页卡片容器 = .article-card
    "video_card": ".article-card",
    "export_button": "text=导出",
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
    page_info = (payload or {}).get("data", {}).get("page") or {}
    total = page_info.get("count") or data.get("total") or len(rows)
    return {"items": rows, "total": total}


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


def detail_steps(page):
    """B 站采用官方整表导出优先——列表页"导出"按钮（listener 先建再点）。
    若按钮存在则触发下载并返回标记；下载文件由调用方归档后走 normalizer。
    """
    try:
        btn = page.locator(SELECTORS["export_button"]).first
        btn.scroll_into_view_if_ok if hasattr(btn, "scroll_into_view_if_ok") else None
        with page.expect_download(timeout=20000) as dl:
            btn.click(force=True, timeout=5000)
        download = dl.value
        out = {"_official_export": download.suggested_filename}
        target = Path.home() / ".oracle-cache" / "collections" / download.suggested_filename
        target.parent.mkdir(parents=True, exist_ok=True)
        download.save_as(str(target))
        out["_official_export_path"] = str(target)
        return out
    except Exception:
        return {}


from pathlib import Path  # noqa: E402
