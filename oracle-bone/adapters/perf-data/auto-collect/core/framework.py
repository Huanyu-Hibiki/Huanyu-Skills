"""auto-collect core/framework — 监听 + DOM 双源扫描框架 + 断点续跑。

模式：后台页面自己会请求作品列表 API → 我们监听响应拿结构化数据（主源）；
DOM 扫描兜底（API 变了还能拿到基本信息）。两源按作品 ID 合并。
每处理完一个作品就写 checkpoint——中断重跑自动跳过已完成的。
"""

import json
import re
import time
from pathlib import Path
from typing import Callable

from playwright.sync_api import Page

# DOM 兜底行的作品 ID 必须长得像真实 ID（纯数字≥6 位 / BV 号 / 十六进制串），
# 防"时长/标题冒充 ID"的垃圾行污染合并（2026-08-19 抖音实测教训）
VALID_ID_RE = re.compile(r"^(?:\d{6,}|BV[0-9A-Za-z]{10}|[0-9a-f]{16,})$", re.IGNORECASE)


def is_valid_work_id(wid: str) -> bool:
    return bool(VALID_ID_RE.match(str(wid or "").strip()))

STABLE_ROUNDS_LIMIT = 3
STALL_ROUNDS_LIMIT = 8
SCROLL_WAIT_MS = 1500
WORK_INTERVAL_MS = 1500


class ResponseCollector:
    """page.on('response') 监听器：按 URL 子串过滤，收集 JSON 响应。"""

    def __init__(self, page: Page, url_patterns: list[str], parse_fn: Callable):
        self.page = page
        self.url_patterns = url_patterns
        self.parse_fn = parse_fn
        self.items: dict[str, dict] = {}
        self.api_total = 0
        self._pending = 0
        page.on("response", self._on_response)

    def _on_response(self, response):
        try:
            url = response.url
            if not any(p in url for p in self.url_patterns):
                return
            # 注意：微信视频号后台业务响应状态码是 201（非错误）——200/201 都收
            if response.status not in (200, 201):
                return
            self._pending += 1
            try:
                payload = response.json()
            except Exception:
                self._pending -= 1
                return
            parsed = self.parse_fn(payload) or {}
            notes = parsed.get("items", [])
            self.api_total = max(self.api_total, parsed.get("total", 0))
            for row in notes:
                wid = str(row.get("作品ID", ""))
                if wid:
                    self.items[wid] = row
            self._pending -= 1
        except Exception:
            try:
                self._pending -= 1
            except Exception:
                pass

    def settle(self):
        deadline = time.time() + 10
        while self._pending > 0 and time.time() < deadline:
            self.page.wait_for_timeout(200)

    def merge_into(self, dom_items: dict[str, dict]) -> dict[str, dict]:
        """API 主源 + DOM 兜底合并：API 字段优先，DOM 只补缺 + 补 API 没有的条目。
        DOM 侧的垃圾 ID（不满足 is_valid_work_id）在入口就被丢弃。"""
        merged = {wid: row for wid, row in dom_items.items() if is_valid_work_id(wid)}
        for wid, api_row in self.items.items():
            if wid in merged:
                for k, v in api_row.items():
                    if v and not merged[wid].get(k):
                        merged[wid][k] = v
            else:
                merged[wid] = api_row
        return merged


def scan_list(page: Page, collector: ResponseCollector, *,
              card_selector: str, extract_card: Callable,
              scroll_rounds: int = 60, min_items: int = 1,
              on_progress: Callable | None = None) -> dict[str, dict]:
    """滚动扫描列表页：DOM 抓卡片 + 监听并行收，直到稳定或达上限。"""
    dom_items: dict[str, dict] = {}
    stable = 0
    stall = 0
    last_count = 0

    for round_no in range(1, scroll_rounds + 1):
        cards = page.locator(card_selector)
        count = cards.count()
        new = 0
        for i in range(count):
            try:
                raw = extract_card(cards.nth(i))
            except Exception:
                continue
            if not raw:
                continue
            wid = str(raw.get("作品ID", ""))
            if not wid or not is_valid_work_id(wid):
                continue
            if wid not in dom_items:
                new += 1
            dom_items[wid] = {**dom_items.get(wid, {}), **raw}

        merged = collector.merge_into(dom_items)
        discovered = len(merged)

        if new == 0 and count == last_count:
            stable += 1
            stall += 1
        else:
            stable = 0
            stall = 0
        last_count = count

        if on_progress:
            on_progress(round_no, discovered, collector.api_total)

        if discovered >= min_items and (stable >= STABLE_ROUNDS_LIMIT or stall >= STALL_ROUNDS_LIMIT):
            break
        if collector.api_total and discovered >= collector.api_total and stable >= 1:
            break

        page.mouse.wheel(0, 4000)
        page.wait_for_timeout(SCROLL_WAIT_MS)

    collector.settle()
    return collector.merge_into(dom_items)


class Checkpoint:
    """断点续跑：processed_ids 持久化。"""

    def __init__(self, path: Path):
        self.path = path
        self.data: dict = {}
        if path.exists():
            try:
                self.data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                self.data = {}

    def done(self, work_id: str) -> bool:
        return work_id in self.data.get("processed", {})

    def mark(self, work_id: str, status: str = "ok"):
        self.data.setdefault("processed", {})[work_id] = {"status": status, "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")

    @property
    def processed_count(self):
        return len(self.data.get("processed", {}))


def save_run_artifacts(out_dir: Path, unified_rows: list, raw_items: dict, meta: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "unified.json").write_text(
        json.dumps({"count": len(unified_rows), "rows": unified_rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    raw_dir = out_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / "items.json").write_text(
        json.dumps(raw_items, ensure_ascii=False, indent=2), encoding="utf-8")
    meta["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out_dir / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
