"""卡顿/重复检测与剪除：把口播里"说得不流畅再读一遍"的首次尝试从保留段中剪掉。

三类目标（词级时间戳上检测，字幕文本以文稿为准，这里只管音频剪辑决策）：
  1. 词级结巴   相邻同词连读（"我们我们来看"）——自动剪首次，保留最后一次
  2. 前缀废弃   说一半停住、从头说全（"我觉得这个——我觉得这个方案"）——
                后文以首次尝试为真前缀且停顿 ≥0.08s，自动剪首次
  3. 相似重说   说错一两个字再重说——与排比句在文本上无法区分
                （"非常实用 / 非常好用"），一律列 needs_review 待确认；
                间隔 >2s 的整句重读原则上是 select_takes 的领域，同样只标记

处置原则与既有纪律一致：字幕不改（文稿拼写），只从 keeps 中减去首次尝试
的时间段（即剪辑决策），needs_review 等用户逐条确认（🔴 句级删除 diff 确认）。

用法:
    python detect_repeats.py <subtitles_words.json> \
        [--keeps finalKeeps_<stem>.json] [--output-dir <Rough>] \
        [--review-sim 0.65] [--source-name 实拍]
输出（--output-dir，默认 words 所在目录的上两级，即 Rough/）:
    keeps_dedup_<source>.json  剪除重复首次尝试后的保留段（喂给 tighten_pauses/render）
    repeats_report.json / repeats_report.md
退出码: 0=完成（有 needs_review 也算 0）
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

# 阈值（native 口径，调参前先看 repeats_report 的误报样本）
ADJ_GAP_MAX = 0.5      # 词级结巴：两次之间的间隔上限
SIM_REVIEW = 0.65      # 相似重说：达到此相似度才进待确认清单
FUZZ_MIN_CHARS = 4     # 相似匹配的最短首次尝试（字符）；更短的只有精确重复管
LONG_GAP = 2.0         # 超过此间隔按整句重读处理，只标记不自动剪
RESTART_GAP = 0.08     # 重说起点前至少有这么大的停顿（区分"往下说"与"重说"）
CUT_PAD = 0.02         # 剪除段两侧各留的余量


def _norm(text: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", text, flags=re.UNICODE)


def load_speech_words(words: list) -> list:
    return [w for w in words if not w.get("isGap") and w.get("text", "").strip()]


def detect_repeats(speech: list, sim_review: float = SIM_REVIEW) -> list:
    """返回重复候选列表，每项：
    {kind, cut:[w0,w1], keep:[w0,w1], sim, gap_s, auto, note}
    索引基于 speech 数组。候选按位置排序且互不重叠。
    """
    n = len(speech)
    cands = []
    i = 0
    while i < n:
        # ── 1) 词级结巴：maximal run of identical adjacent words ──
        j = i
        while j + 1 < n and speech[j + 1]["text"] == speech[i]["text"] \
                and speech[j + 1]["start"] - speech[j]["end"] <= ADJ_GAP_MAX:
            j += 1
        if j > i:
            gap = speech[i + 1]["start"] - speech[i]["end"]
            cands.append({
                "kind": "stutter", "cut": (i, j - 1), "keep": (j, j),
                "sim": 1.0, "gap_s": round(gap, 3), "auto": True,
                "note": f"同词连读 ×{j - i + 1}，保留最后一次",
            })
            i = j + 1
            continue

        # ── 2) 改口重说：以 i 为"第二次尝试"起点，向左找相似窗口 ──
        best = None
        for L in range(min(14, i), 0, -1):
            w0, w1 = i - L, i - 1
            a_text = _norm("".join(w["text"] for w in speech[w0:w1 + 1]))
            if len(a_text) < 1:
                continue
            gap = speech[i]["start"] - speech[w1]["end"]
            # 注意：L 从大到小遍历，gap 随 L 减小而减小——不能 break，
            # 否则大窗口超长间隔时小窗口（真改口）全被跳过
            # 第二次尝试取等长窗口（允许向右吃到 gap/句尾截断前）
            j2 = min(i + L - 1, n - 1)
            b_text = _norm("".join(w["text"] for w in speech[i:j2 + 1]))
            if not b_text:
                continue
            # 前缀废弃：A 是 B 的开头（说一半停住重说）——唯一可自动剪的模糊类；
            # 非前缀的高相似（说错一两个字再重说 vs 排比句）文本上无法区分，一律待确认
            prefix = b_text.startswith(a_text)
            sim = difflib.SequenceMatcher(None, a_text, b_text).ratio()
            hit = (prefix and gap >= RESTART_GAP) or \
                  (len(a_text) >= FUZZ_MIN_CHARS and sim >= sim_review and gap >= RESTART_GAP)
            if hit:
                score = (1.0 if prefix else 0.0) + sim + (0.1 if len(b_text) >= len(a_text) else 0.0)
                if best is None or score > best[0]:
                    auto = prefix and gap <= LONG_GAP
                    if prefix and gap > LONG_GAP:
                        note = "前缀重合但间隔过大（整句重读？），留人工确认"
                    elif prefix:
                        note = "前缀废弃：说一半停住重说"
                    else:
                        note = "非前缀相似重说（与排比句无法区分），待人工确认"
                    best = (score, {
                        "kind": "restart_prefix" if prefix else "restart_sim",
                        "cut": (w0, w1), "keep": (i, j2),
                        "sim": round(sim, 3), "gap_s": round(gap, 3),
                        "auto": bool(auto), "note": note,
                    })
        if best:
            cands.append(best[1])
            i = best[1]["keep"][1] + 1  # 消费掉保留段，防止重叠
            continue

        i += 1
    return cands


def subtract_from_keeps(keeps: list, spans: list) -> list:
    """从 [{start,end}] 保留段中减去 (s,e) 时间区间列表。"""
    out = []
    for seg in sorted(keeps, key=lambda k: k["start"]):
        pieces = [(seg["start"], seg["end"])]
        for s, e in sorted(spans):
            nxt = []
            for ps, pe in pieces:
                if e <= ps or s >= pe:
                    nxt.append((ps, pe))
                    continue
                if s > ps:
                    nxt.append((ps, s))
                if e < pe:
                    nxt.append((e, pe))
            pieces = nxt
        for ps, pe in pieces:
            if pe - ps > 0.05:  # 碎片低于 50ms 丢弃
                out.append({"start": round(ps, 3), "end": round(pe, 3)})
    return out


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("words_json", type=Path, help="subtitles_words.json（词级，含 isGap）")
    ap.add_argument("--keeps", type=Path, default=None,
                    help="finalKeeps_<stem>.json（select_takes 产物）；缺省在全片上检测")
    ap.add_argument("--output-dir", type=Path, default=None, help="默认 words 上两级（Rough/）")
    ap.add_argument("--source-name", default=None, help="输出文件名用的素材名（默认 words stem）")
    ap.add_argument("--review-sim", type=float, default=SIM_REVIEW)
    args = ap.parse_args()

    words = json.loads(args.words_json.read_text(encoding="utf-8-sig"))
    speech = load_speech_words(words)
    if len(speech) < 4:
        print("[X] 词太少，无从检测")
        sys.exit(1)

    source = args.source_name or args.words_json.stem
    out_dir = args.output_dir or args.words_json.parent.parent

    cands = detect_repeats(speech, sim_review=args.review_sim)
    auto_c, review_c = [], []
    for c in cands:
        w = f"{speech[c['cut'][0]]['text']}…{speech[c['cut'][1]]['text']}"
        k = f"{speech[c['keep'][0]]['text']}…{speech[c['keep'][1]]['text']}"
        c["cut_text"] = "".join(x["text"] for x in speech[c["cut"][0]:c["cut"][1] + 1])
        c["keep_text"] = "".join(x["text"] for x in speech[c["keep"][0]:c["keep"][1] + 1])
        # 方向保险：剪掉的一定不能比保留的长（等长窗口报告只覆盖保留段前缀，
        # 实际保留的第二次尝试通常更长）——不满足即降级为待确认
        if c["auto"] and len(_norm(c["cut_text"])) > len(_norm(c["keep_text"])):
            c["auto"] = False
            c["note"] += "；异常：删除段长于保留段，降级待确认"
        (auto_c if c["auto"] else review_c).append(c)

    # 时间跨度（词索引 → 源时间轴），剪除段含中间的 gap
    cut_spans = []
    for c in auto_c:
        w0, w1 = c["cut"]
        s = max(0.0, speech[w0]["start"] - CUT_PAD)
        e = min(speech[w1]["end"] + CUT_PAD,
                speech[w1 + 1]["start"] if w1 + 1 < len(speech) else speech[w1]["end"] + CUT_PAD)
        cut_spans.append((s, e))
        c["cut_time"] = [round(s, 3), round(e, 3)]

    keeps_in = None
    if args.keeps and args.keeps.exists():
        keeps_in = json.loads(args.keeps.read_text(encoding="utf-8-sig"))
    report = {
        "source": source,
        "auto_cut": [{k: c[k] for k in ("kind", "cut_text", "cut_time", "keep_text",
                                        "sim", "gap_s", "note")} for c in auto_c],
        "needs_review": [{k: c[k] for k in ("kind", "cut_text", "keep_text",
                                            "sim", "gap_s", "note")} for c in review_c],
        "note": "auto_cut 已从 keeps 减除；needs_review 仅供人工确认，确认后手工调整 keeps",
    }
    if keeps_in is not None:
        dedup = subtract_from_keeps(keeps_in, cut_spans)
        out_keeps = out_dir / f"keeps_dedup_{source}.json"
        out_keeps.write_text(json.dumps(dedup, ensure_ascii=False, indent=2), encoding="utf-8")
        report["keeps_in"] = len(keeps_in)
        report["keeps_out"] = len(dedup)
        report["keeps_dedup_file"] = str(out_keeps)

    (out_dir / "repeats_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"# 重复/卡顿检测报告 — {source}", "",
             f"自动剪除 {len(auto_c)} 处，待人工确认 {len(review_c)} 处。", ""]
    if auto_c:
        lines += ["## 自动剪除（首次尝试不进时间线）", "",
                  "| 类型 | 删除（首次） | 保留（重说） | 相似度 | 间隔 |", "|---|---|---|---|---|"]
        lines += [f"| {c['kind']} | {c['cut_text'][:24]} | {c['keep_text'][:24]} | {c['sim']:.0%} | {c['gap_s']}s |"
                  for c in auto_c]
        lines.append("")
    if review_c:
        lines += ["## 待人工确认（不自动剪）", "",
                  "| 类型 | 疑似删除 | 疑似保留 | 相似度 | 间隔 |", "|---|---|---|---|---|"]
        lines += [f"| {c['kind']} | {c['cut_text'][:24]} | {c['keep_text'][:24]} | {c['sim']:.0%} | {c['gap_s']}s |"
                  for c in review_c]
    (out_dir / "repeats_report.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"🔁 重复检测: 自动剪除 {len(auto_c)} 处 / 待确认 {len(review_c)} 处")
    for c in auto_c[:8]:
        print(f"  ✂ [{c['kind']}] 删「{c['cut_text'][:20]}」 留「{c['keep_text'][:20]}」 ({c['note']})")
    for c in review_c[:5]:
        print(f"  ？ [{c['kind']}] 「{c['cut_text'][:20]}」≈「{c['keep_text'][:20]}」 ({c['note']})")
    if keeps_in is not None:
        print(f"  keeps: {len(keeps_in)} → {report['keeps_out']} 段（keeps_dedup_{source}.json）")
    sys.exit(0)


if __name__ == "__main__":
    main()
