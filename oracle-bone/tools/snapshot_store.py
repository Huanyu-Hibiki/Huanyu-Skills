#!/usr/bin/env python3
"""oracle-bone snapshot_store — 采集快照库（runs + snapshots 时序模型）。

每次采集 = 一个 run 快照；latest vs prev diff 出增量。
设计参考 data-scientist-community（AGPL-3.0）的 run-snapshot 思路，clean-room 重写。

用法:
  python snapshot_store.py archive --db content-analytics.db --input unified.json
  python snapshot_store.py diff --db content-analytics.db
  或作为库: from snapshot_store import archive_rows, latest_diff
"""

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SNAP_COLS = [
    "平台作品键", "平台", "作品ID", "标题", "发布日期",
    "曝光量", "播放量", "阅读量", "点赞量", "收藏量", "评论量", "分享量", "涨粉量",
]


def _num(v):
    try:
        return int(float(str(v).replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _connect(db_path):
    conn = sqlite3.connect(str(db_path), timeout=8)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def ensure_db(db_path):
    conn = _connect(db_path)
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS runs (run_id INTEGER PRIMARY KEY, run_at TEXT NOT NULL, platforms TEXT, row_count INTEGER)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
              run_id INTEGER NOT NULL,
              平台作品键 TEXT NOT NULL,
              平台 TEXT NOT NULL, 作品ID TEXT, 标题 TEXT, 发布日期 TEXT,
              曝光量 INTEGER, 播放量 INTEGER, 阅读量 INTEGER,
              点赞量 INTEGER, 收藏量 INTEGER, 评论量 INTEGER, 分享量 INTEGER, 涨粉量 INTEGER,
              PRIMARY KEY (run_id, 平台作品键)
            )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_key ON snapshots(平台作品键)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_run_platform ON snapshots(run_id, 平台)")
        conn.commit()
    finally:
        conn.close()


def archive_rows(db_path, rows: List[Dict[str, Any]]) -> Optional[int]:
    """把一次归一结果存为 run 快照。返回 run_id；空数据返回 None。"""
    if not rows:
        return None
    ensure_db(db_path)
    run_id = int(time.time() * 1000)
    run_at = time.strftime("%Y-%m-%d %H:%M:%S")
    platforms = sorted({str(r.get("平台", "")) for r in rows})
    conn = _connect(db_path)
    try:
        conn.execute("INSERT INTO runs(run_id, run_at, platforms, row_count) VALUES (?,?,?,?)",
                     (run_id, run_at, ",".join(platforms), len(rows)))
        snap_rows = []
        for r in rows:
            key = str(r.get("平台作品键", ""))
            if not key or ":" not in key:
                continue
            snap_rows.append((run_id, key, str(r.get("平台", "")),
                              str(r.get("作品ID", "")), str(r.get("标题", "")), str(r.get("发布日期", "")),
                              _num(r.get("曝光量")), _num(r.get("播放量")), _num(r.get("阅读量")),
                              _num(r.get("点赞量")), _num(r.get("收藏量")), _num(r.get("评论量")),
                              _num(r.get("分享量")), _num(r.get("涨粉量"))))
        conn.executemany("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", snap_rows)
        conn.commit()
        return run_id
    finally:
        conn.close()


def _run_rows(conn, run_id):
    out = []
    cols = ", ".join(SNAP_COLS)
    for r in conn.execute(f"SELECT {cols} FROM snapshots WHERE run_id = ?", (run_id,)):
        d = dict(zip(SNAP_COLS, r))
        d["互动量"] = _num(d.get("点赞量")) + _num(d.get("收藏量")) + _num(d.get("评论量")) + _num(d.get("分享量"))
        plays = max(_num(d.get("播放量")), _num(d.get("阅读量")))
        d["有效播放"] = plays
        d["互动率"] = round(d["互动量"] / plays, 4) if plays > 0 else 0.0
        out.append(d)
    return out


def latest_diff(db_path, top_n=10):
    """latest vs prev run 的作品级 diff。"""
    ensure_db(db_path)
    conn = _connect(db_path)
    try:
        runs = conn.execute("SELECT run_id, run_at FROM runs ORDER BY run_id DESC LIMIT 2").fetchall()
        if not runs:
            return {"ok": False, "message": "no_runs"}
        latest_id, latest_at = runs[0]
        latest = _run_rows(conn, latest_id)
        if len(runs) < 2:
            return {"ok": True, "latest_run": {"run_id": latest_id, "run_at": latest_at}, "prev_run": None,
                    "rows": latest, "is_full_baseline": True}

        prev_id, prev_at = runs[1]
        prev = _run_rows(conn, prev_id)
        prev_by_key = {r["平台作品键"]: r for r in prev}

        merged = []
        for r in latest:
            p = prev_by_key.get(r["平台作品键"])
            if p:
                r["is_new"] = False
                r["播放增量"] = r["有效播放"] - p["有效播放"]
                r["互动增量"] = r["互动量"] - p["互动量"]
                r["互动率变化"] = round(r["互动率"] - p["互动率"], 4)
            else:
                r["is_new"] = True
                r["播放增量"] = r["有效播放"]
                r["互动增量"] = r["互动量"]
                r["互动率变化"] = r["互动率"]
            merged.append(r)
        return {"ok": True,
                "latest_run": {"run_id": latest_id, "run_at": latest_at},
                "prev_run": {"run_id": prev_id, "run_at": prev_at},
                "rows": merged, "is_full_baseline": False}
    finally:
        conn.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["archive", "diff"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--input", help="unified.json（archive 用）")
    args = ap.parse_args()

    if args.cmd == "archive":
        if not args.input:
            print("❌ archive 需要 --input", file=sys.stderr)
            sys.exit(1)
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        rows = payload.get("rows", payload if isinstance(payload, list) else [])
        run_id = archive_rows(args.db, rows)
        print(f"✅ 已存快照 run_id={run_id}（{len(rows)} 条）→ {args.db}" if run_id else "⚠️ 无数据可存")
    else:
        result = latest_diff(args.db)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
