#!/usr/bin/env python3
"""oracle-bone data_normalizer — 四平台作品数据统一归一器。

设计参考 data-scientist-community（AGPL-3.0）的字段对齐思路，本实现为 clean-room 重写。
统一 schema 以中文键为准（与平台后台导出一致，便于 report.md 直接呈现）。

用法:
  python data_normalizer.py --input all_videos.xlsx --platform douyin [--output unified.json]
  或作为库: from data_normalizer import normalize_rows
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

# ── 统一字段（canonical schema）────────────────────────────────
CANONICAL_FIELDS = [
    "平台作品键", "平台", "作品ID", "标题", "发布日期", "内容类型",
    "曝光量", "播放量", "阅读量", "点赞量", "收藏量", "评论量", "分享量",
    "涨粉量", "投币量", "弹幕量", "时长", "链接", "来源文件",
]

# 五维增量 + 平台特有比率字段（保留字符串，含 % / s 单位）
METRIC_FIELDS = [
    "完播率", "跳出率", "跳出率口径", "5s完播率",
    "平均播放时长", "平均播放进度", "封面点击率", "粉丝播放占比",
    "点赞率", "评论率", "分享率", "收藏率",
    "来源占比_推荐页", "来源占比_搜索", "来源占比_个人主页", "来源占比_关注页",
]

PLATFORMS = {"douyin", "xiaohongshu", "bilibili", "kuaishou", "wechat", "unknown"}

# ── 字段别名映射（平台口径 → 统一口径）────────────────────────
FIELD_ALIASES = {
    # 计数字段
    "曝光数": "曝光量", "展现量": "曝光量",
    "观看数": "阅读量", "观看量": "阅读量", "阅读数": "阅读量",
    "点赞数": "点赞量", "喜欢": "点赞量",
    "收藏数": "收藏量", "推荐": "收藏量",
    "评论数": "评论量",     "转发量": "分享量", "分享数": "分享量", "转发": "分享量", "推荐量": "收藏量",
    "涨粉数": "涨粉量", "新增粉丝": "涨粉量", "关注": "涨粉量",
    "投币": "投币量", "弹幕数": "弹幕量", "弹幕": "弹幕量",
    "播放": "播放量", "播放数": "播放量",
    # 比率/指标字段
    "封面点击率": "封面点击率", "封标点击率": "封面点击率",
    "平均观看时长": "平均播放时长",
    "3秒跳出率": "跳出率", "3s跳出率": "跳出率",
    "2秒退出率": "跳出率", "2s跳出率": "跳出率", "2s退出率": "跳出率",
    "平均播放占比": "平均播放进度",
    # 身份字段
    "作品id": "作品ID", "视频ID": "作品ID", "笔记ID": "作品ID", "稿件ID": "作品ID",
    "发布时间": "发布日期",
}

BOUNCE_CALIBER = {"3秒跳出率": "3s", "3s跳出率": "3s", "2秒退出率": "2s", "2s跳出率": "2s", "2s退出率": "2s"}

_UNIT_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*([万亿])\s*$")


def clean_value(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd is not None and pd.isna(value):
        return ""
    text = str(value).strip()
    if text.lower() in {"nan", "none", "null", "-"}:
        return ""
    return re.sub(r"\s+", " ", text)


def parse_number(value):
    """'1.2万'→12000；'3,500'→3500；'45%'→'45%'（比率保留原文）；解析失败返回 0。"""
    text = clean_value(value).replace(",", "")
    if not text:
        return 0
    if text.endswith("%") or text.lower().endswith("s"):
        return text  # 比率/时长类保留带单位原文
    m = _UNIT_RE.match(text)
    if m:
        n = float(m.group(1))
        mult = 10_000 if m.group(2) == "万" else 100_000_000
        result = n * mult
        return int(result) if result.is_integer() else result
    try:
        n = float(text)
    except ValueError:
        return 0
    return int(n) if n.is_integer() else n


def to_date_text(value):
    text = clean_value(value)
    if not text:
        return ""
    if re.match(r"^\d{10}$", text):
        import datetime as _dt
        return _dt.datetime.fromtimestamp(int(text)).strftime("%Y-%m-%d")
    if re.match(r"^\d{13}$", text):
        import datetime as _dt
        return _dt.datetime.fromtimestamp(int(text) / 1000).strftime("%Y-%m-%d")
    if pd is not None:
        ts = pd.to_datetime(text, errors="coerce")
        if ts is not None and not pd.isna(ts):
            return ts.strftime("%Y-%m-%d")
    return text


def normalize_title(value):
    text = clean_value(value).replace("\n", " ")
    text = re.sub(r"[\u200b-\u200d\ufeff\xa0]+", " ", text)
    text = text.replace("＃", "#")
    text = " ".join(text.split())
    if text.startswith("#"):
        return text
    return re.sub(r"\s+#.*$", "", text).strip()


def _alias_key(key):
    k = clean_value(key)
    return FIELD_ALIASES.get(k, FIELD_ALIASES.get(k.replace(" ", ""), k))


def _pick(row, keys):
    for k in keys:
        v = clean_value(row.get(k))
        if v:
            return v
    return ""


def normalize_row(platform, raw, source_file=""):
    row = {_alias_key(k): v for k, v in raw.items()}
    work_id = clean_value(row.get("作品ID"))
    if not work_id:
        work_id = clean_value(raw.get("作品ID") or raw.get("作品id"))
    if not work_id:
        return None

    item = {
        "平台作品键": f"{platform}:{work_id}",
        "平台": platform,
        "作品ID": work_id,
        "标题": normalize_title(row.get("标题")),
        "发布日期": to_date_text(row.get("发布日期")),
        "内容类型": clean_value(row.get("内容类型")) or "video",
        "曝光量": parse_number(row.get("曝光量")),
        "播放量": parse_number(row.get("播放量")),
        "阅读量": parse_number(_pick(row, ["阅读量", "观看量"])),
        "点赞量": parse_number(_pick(row, ["点赞量", "喜欢"])),
        "收藏量": parse_number(_pick(row, ["收藏量", "推荐"])),
        "评论量": parse_number(row.get("评论量")),
        "分享量": parse_number(_pick(row, ["分享量", "转发量"])),
        "涨粉量": parse_number(_pick(row, ["涨粉量", "关注"])),
        "投币量": parse_number(row.get("投币量")),
        "弹幕量": parse_number(row.get("弹幕量")),
        "时长": parse_number(row.get("时长")),
        "链接": clean_value(row.get("链接")),
        "来源文件": source_file,
    }

    # 指标字段：跳出率带口径标注（3s/2s 平台不一，不硬统一）
    bounce = ""
    caliber = ""
    for alias, cal in BOUNCE_CALIBER.items():
        if clean_value(raw.get(alias)):
            bounce = clean_value(raw.get(alias))
            caliber = cal
            break
    item["跳出率"] = bounce or clean_value(row.get("跳出率"))
    item["跳出率口径"] = caliber
    for f in METRIC_FIELDS:
        if f in {"跳出率", "跳出率口径"}:
            continue
        item[f] = _pick_metric(row, f)

    return item


def _pick_metric(row, field):
    keys = [field]
    if field == "封面点击率":
        keys += ["封标点击率"]
    if field == "平均播放时长":
        keys += ["平均观看时长"]
    return clean_value(row.get(keys[0])) or clean_value(row.get(keys[1])) if len(keys) > 1 else clean_value(row.get(field))


def filter_invalid_rows(rows):
    """播放=0 且阅读=0 的记录过滤（隐藏作品/无效数据）。"""
    out = []
    for r in rows:
        plays = parse_number(r.get("播放量"))
        reads = parse_number(r.get("阅读量"))
        if plays <= 0 and reads <= 0:
            continue
        out.append(r)
    return out


def filter_by_date(rows, min_date="", max_date=""):
    if not min_date and not max_date:
        return rows
    out = []
    for r in rows:
        d = clean_value(r.get("发布日期"))
        if not re.match(r"^\d{4}-\d{2}-\d{2}", d):
            continue  # 日期不可解析不放行（防旧缓存混入）
        if min_date and d < min_date:
            continue
        if max_date and d > max_date:
            continue
        out.append(r)
    return out


def normalize_rows(platform, raw_rows, source_file="", drop_invalid=True):
    rows = [normalize_row(platform, r, source_file) for r in raw_rows]
    rows = [r for r in rows if r]
    if drop_invalid:
        rows = filter_invalid_rows(rows)
    return rows


# ── 输入读取 ──────────────────────────────────────────────

def read_rows(path: Path):
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        if pd is None:
            raise RuntimeError("读取 Excel 需要 pandas + openpyxl：pip install pandas openpyxl")
        df = pd.read_excel(path, dtype=str).fillna("")
        return df.to_dict(orient="records")
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            rows = data.get("rows") or data.get("data") or []
            if isinstance(rows, list):
                return rows
        return []
    if suffix == ".csv":
        if pd is None:
            raise RuntimeError("读取 CSV 需要 pandas")
        return pd.read_csv(path, dtype=str).fillna("").to_dict(orient="records")
    raise ValueError(f"不支持的输入格式：{suffix}")


def detect_platform(path: Path, hint=""):
    if hint:
        return hint
    name = path.name.lower()
    for p in PLATFORMS:
        if p in name:
            return p
    for p, kw in {"douyin": ["抖音"], "xiaohongshu": ["小红书", "xhs"], "bilibili": ["b站", "bili"],
                  "kuaishou": ["快手", "ks"], "wechat": ["视频号", "wechat", "channels", "微信"]}.items():
        if kw and any(k in name for k in kw):
            return p
    return "unknown"


def main():
    ap = argparse.ArgumentParser(description="四平台作品数据统一归一")
    ap.add_argument("--input", required=True, help="平台导出文件（xlsx/json/csv）或目录")
    ap.add_argument("--platform", default="", help="强制指定平台（缺省按文件名猜）")
    ap.add_argument("--output", default="", help="输出 json 路径（缺省打印）")
    ap.add_argument("--min-date", default="")
    ap.add_argument("--max-date", default="")
    ap.add_argument("--keep-invalid", action="store_true")
    args = ap.parse_args()

    src = Path(args.input)
    files = [src] if src.is_file() else sorted([*src.glob("*.xlsx"), *src.glob("*.json"), *src.glob("*.csv")])
    if not files:
        print(f"❌ 未找到输入文件：{src}", file=sys.stderr)
        sys.exit(1)

    all_rows = []
    for f in files:
        platform = detect_platform(f, args.platform)
        raw = read_rows(f)
        rows = normalize_rows(platform, raw, source_file=f.name, drop_invalid=not args.keep_invalid)
        rows = filter_by_date(rows, args.min_date, args.max_date)
        print(f"✓ {f.name} [{platform}]：{len(raw)} 行 → 归一后 {len(rows)} 行")
        all_rows.extend(rows)

    payload = {"count": len(all_rows), "rows": all_rows}
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✅ 归一完成：{len(all_rows)} 条 → {args.output}")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
