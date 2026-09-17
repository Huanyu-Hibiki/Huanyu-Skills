"""keeps 回读校验（保险丝）：剪出来的成片文本 vs 文稿逐句核对。

上游任何环节（take 评分、重复剪除、停顿收紧、ASR 幻觉）出了错，最终都会
体现在 keeps 覆盖的转录文本上——本脚本把 keeps 覆盖的词拼回成"成片文本"，
对文稿逐句检查，在 EDL 之前拦住三类事故：

  1. 句子截断   文稿句的尾段（最后 3 个有效字符）在成片文本中无匹配
                （例："……做出来的学习引擎" 被剪成 "……成本做"）
  2. 重复未剪   同一句在成片文本中出现两次以上（重读的首次尝试还在时间线里）
  3. 幻觉词     keeps 内词级置信度 <0.5 的占比 >30%（Whisper 停顿处幻觉补尾，
                转录有字、音频是静音——旧转录无 confidence 字段时此项跳过）

用法:
    python verify_keeps.py <项目根> <subtitles_words.json> <keeps.json> \
        [--tail-chars 3] [--lowconf 0.3] [--max-repeat 1]
退出码: 0=pass 1=fail（🔴 finding 列表交用户裁决，不得带 fail 进 EDL）
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from align_to_manuscript import find_manuscripts, parse_manuscript  # noqa: E402


def _norm(t: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", t).lower()


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", type=Path)
    ap.add_argument("words_json", type=Path)
    ap.add_argument("keeps_json", type=Path)
    ap.add_argument("--tail-chars", type=int, default=3)
    ap.add_argument("--lowconf", type=float, default=0.3)
    ap.add_argument("--max-repeat", type=int, default=1)
    args = ap.parse_args()

    words = json.loads(args.words_json.read_text(encoding="utf-8-sig"))
    keeps = json.loads(args.keeps_json.read_text(encoding="utf-8-sig"))
    mss = find_manuscripts(args.project)
    if not mss:
        print(json.dumps({"verdict": "skip", "reason": "无文稿，无法回读校验"}, ensure_ascii=False))
        sys.exit(0)
    sentences = [_norm(s["text"]) for s in parse_manuscript(mss[0])]
    sentences = [s for s in sentences if s]

    # keeps → 成片词序列（含词级置信度）
    kept_words = [
        w for w in words
        if not w.get("isGap") and any(k["start"] - 0.09 <= w["start"] and w["end"] <= k["end"] + 0.31 for k in keeps)
    ]
    cut_text = _norm("".join(w["text"] for w in kept_words))

    confs = [w.get("confidence") for w in kept_words]
    confs = [c for c in confs if isinstance(c, (int, float))]
    lowconf_ratio = (sum(1 for c in confs if c < 0.5) / len(confs)) if confs else None

    findings = []
    for sent in sentences:
        # 1) 句子截断：整句与成片文本匹配度尚可，但句尾 N 字无匹配
        whole = difflib.SequenceMatcher(None, sent, cut_text).ratio()
        if whole >= 0.55:
            tail = sent[-args.tail_chars:]
            if tail and tail not in cut_text:
                findings.append({
                    "type": "句子截断", "sentence": sent[:24],
                    "detail": f"文稿句尾「{tail}」在成片中不存在——take 可能选了截断版或边界被剪",
                })
                continue
            # 2) 重复未剪：句主干（去尾）在成片文本中出现次数
            body = sent[:-args.tail_chars] if len(sent) > args.tail_chars else sent
            occurrences = cut_text.count(body[:12]) if len(body) >= 12 else cut_text.count(body)
            if occurrences > args.max_repeat:
                findings.append({
                    "type": "重复未剪", "sentence": sent[:24],
                    "detail": f"同一句在成片中出现 {occurrences} 次——重读的首次尝试还在时间线里",
                })

    # 3) 幻觉词
    if lowconf_ratio is not None and lowconf_ratio > args.lowconf:
        findings.append({
            "type": "疑似幻觉词", "sentence": "-",
            "detail": f"成片内 {lowconf_ratio:.0%} 的词 ASR 置信度 <0.5——可能包含 Whisper 停顿幻觉（转录有字、音频静音）",
        })

    verdict = "fail" if findings else "pass"
    result = {
        "verdict": verdict,
        "kept_text_chars": len(cut_text),
        "sentences_checked": len(sentences),
        "lowconf_ratio": round(lowconf_ratio, 3) if lowconf_ratio is not None else None,
        "findings": findings,
        "note": "fail 时不得进入 EDL——findings 逐条交用户裁决（🔴 句级删除 diff 确认）",
    }
    out = args.keeps_json.parent / "keeps_verify_report.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"报告: {out}")
    sys.exit(0 if verdict == "pass" else 1)


if __name__ == "__main__":
    main()
