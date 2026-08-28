#!/usr/bin/env python3
"""Deterministic tests for select_takes.py + tighten_pauses.py.

Builds a synthetic word-level transcript where the speaker reads sentence 1
twice (hesitant then clean), sentence 2 once with a long interior pause, and
sentence 3 twice (complete then a partial false start), then verifies the
decision and the pause tightening.

Run:
    python scripts/video-rough-cut/test_select_takes.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


select_takes = _load("select_takes")
tighten_pauses = _load("tighten_pauses")


def w(text: str, start: float, end: float) -> dict:
    return {"text": text, "start": start, "end": end, "isGap": False}


FIXTURE_WORDS = [
    # -- S1 take 1: substitution ("大驾好") + 0.7s hesitation ----------
    w("大驾好", 1.0, 1.5), w("今天", 1.6, 2.0), w("我们", 2.1, 2.5),
    w("来聊", 2.6, 3.0),  # silence 3.0 - 3.7
    w("一个", 3.7, 4.1), w("话题", 4.2, 4.7),
    # silence 4.7 - 8.0 (>= 1.2s → chunk boundary)
    # -- S1 take 2: clean, faster ------------------------------------
    w("大家好", 8.0, 8.4), w("今天", 8.5, 8.9), w("我们", 9.0, 9.3),
    w("来聊", 9.4, 9.7), w("一个", 9.8, 10.1), w("话题", 10.2, 10.6),
    # silence 10.6 - 11.5
    # -- S2 take 1: clean but with 1.0s interior pause ----------------
    w("这个", 11.5, 11.9), w("视频", 12.0, 12.4), w("有", 12.5, 12.7),
    w("三句话", 12.8, 13.3),  # silence 13.3 - 14.3
    w("组成", 14.3, 14.9),
    # silence 14.9 - 16.5
    # -- S3 take 1: complete ------------------------------------------
    w("最后一句", 16.5, 17.2), w("用来", 17.3, 17.7), w("测试", 17.8, 18.2),
    w("不完整的", 18.3, 18.9), w("take", 19.0, 19.4),
    # silence 19.4 - 20.0 (< 1.2s, same chunk window but size filter applies)
    # -- S3 take 2: partial false start -------------------------------
    w("最后一句", 20.0, 20.6), w("用来", 20.7, 21.0),
]

MANUSCRIPT = """# 测试文稿

大家好今天我们来聊一个话题。

这个视频有三句话组成。

最后一句用来测试不完整的take。
"""


class SelectTakesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        scripts_dir = self.root / "video scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "manuscript.md").write_text(MANUSCRIPT, encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _run(self) -> dict:
        words_path = self.root / "subtitles_words.json"
        words_path.write_text(json.dumps(FIXTURE_WORDS, ensure_ascii=False), encoding="utf-8")
        sys.argv = [
            "select_takes.py", str(self.root), str(words_path),
            "--output-dir", str(self.root / "Rough"),
        ]
        select_takes.main()
        return json.loads((self.root / "Rough" / "takes_decision.json").read_text(encoding="utf-8"))

    def test_best_take_chosen_per_sentence(self) -> None:
        decision = self._run()
        s = decision["sentences"]
        self.assertEqual(len(s), 3)

        # S1: two takes detected, clean take 2 wins (starts ≈ 8.0).
        self.assertEqual(len(s[0]["rejected"]), 1)
        chosen1 = s[0]["chosen"]
        self.assertIsNotNone(chosen1)
        self.assertAlmostEqual(chosen1["start"], 7.92, delta=0.05)

        # S2: single take around 11.5.
        chosen2 = s[1]["chosen"]
        self.assertAlmostEqual(chosen2["start"], 11.42, delta=0.05)

        # S3: complete take wins; the partial false start must NOT be chosen
        # (complete take starts ≈ 16.42; the partial one would start ≈ 19.92).
        chosen3 = s[2]["chosen"]
        self.assertLess(chosen3["start"], 17.0)
        self.assertGreater(chosen3["end"], 19.0)

    def test_summary_counts(self) -> None:
        decision = self._run()
        summary = decision["summary"]
        self.assertEqual(summary["sentences"], 3)
        self.assertEqual(summary["matched"], 3)
        self.assertEqual(summary["unmatched"], 0)

    def test_keeps_sorted_and_non_overlapping(self) -> None:
        self._run()
        keeps = json.loads(
            (self.root / "Rough" / "finalKeeps_subtitles_words.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(keeps), 3)
        for a, b in zip(keeps, keeps[1:]):
            self.assertLessEqual(a["end"], b["start"] + 1e-6)

    def test_tighten_removes_interior_pause(self) -> None:
        self._run()
        keeps_path = self.root / "Rough" / "finalKeeps_subtitles_words.json"
        words_path = self.root / "subtitles_words.json"
        sys.argv = [
            "tighten_pauses.py", str(words_path),
            "--keeps", str(keeps_path),
            "--output-dir", str(self.root / "Rough"),
        ]
        tighten_pauses.main()

        tightened = json.loads(
            (self.root / "Rough" / "keeps_tightened_subtitles_words.json").read_text(encoding="utf-8")
        )
        # S2 (sentence_idx 1) had one 1.0s pause → split into 2 sub-segments.
        s2_subs = [t for t in tightened if t["sentence_idx"] == 1]
        self.assertEqual(len(s2_subs), 2)
        # First sub ends ~13.55 (13.3 + 0.25s kept breath).
        self.assertAlmostEqual(s2_subs[0]["end"], 13.55, delta=0.02)
        # Second sub starts at the pause end.
        self.assertAlmostEqual(s2_subs[1]["start"], 14.3, delta=0.02)

        report = (self.root / "Rough" / "pauses_report.md").read_text(encoding="utf-8")
        self.assertIn("0.75", report)

        # Segments without long pauses pass through untouched.
        s1_subs = [t for t in tightened if t["sentence_idx"] == 0]
        self.assertEqual(len(s1_subs), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
