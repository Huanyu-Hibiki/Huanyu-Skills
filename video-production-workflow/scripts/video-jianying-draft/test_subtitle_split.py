#!/usr/bin/env python3
"""Deterministic tests for subtitle_split.py.

Run:
    python scripts/video-jianying-draft/test_subtitle_split.py
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("subtitle_split", SCRIPT_DIR / "subtitle_split.py")
assert spec and spec.loader
subtitle_split = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subtitle_split)

MAX_UNITS = 18.0


class SubtitleSplitTest(unittest.TestCase):
    def test_short_cue_unchanged(self) -> None:
        out, stats = subtitle_split.split_srt(
            "1\n00:00:01,000 --> 00:00:03,000\n今天我们聊话题\n", MAX_UNITS, 6)
        self.assertEqual(stats["cues_out"], 1)
        self.assertIn("今天我们聊话题", out)

    def test_long_cue_split_within_limit(self) -> None:
        long_text = "大家好今天我们要聊一个关于人工智能如何改变视频制作流程的话题"
        out, stats = subtitle_split.split_srt(
            f"1\n00:00:00,000 --> 00:00:08,000\n{long_text}\n", MAX_UNITS, 6)
        self.assertGreater(stats["cues_out"], 1)
        for cue in subtitle_split.parse_srt(out):
            self.assertLessEqual(subtitle_split.display_units(cue[2]), MAX_UNITS + 6,
                                  f"chunk too long: {cue[2]}")

    def test_no_orphan_chunks(self) -> None:
        long_text = "这是一段非常长的中文句子用来验证切分之后不会产生只有两三个字的孤块"
        out, _ = subtitle_split.split_srt(
            f"1\n00:00:00,000 --> 00:00:10,000\n{long_text}\n", MAX_UNITS, 6)
        cues = subtitle_split.parse_srt(out)
        self.assertGreater(len(cues), 1)
        for cue in cues:
            self.assertGreaterEqual(subtitle_display_floor(cue[2]), 3,
                                    f"orphan chunk: {cue[2]}")

    def test_split_prefers_punctuation(self) -> None:
        text = "第一部分讲概念，第二部分讲实操，第三部分讲复盘"
        out, _ = subtitle_split.split_srt(
            f"1\n00:00:00,000 --> 00:00:09,000\n{text}\n", MAX_UNITS, 6)
        cues = subtitle_split.parse_srt(out)
        self.assertGreaterEqual(len(cues), 2)
        # Chunks should end at commas (natural phrase boundaries).
        for cue in cues[:-1]:
            self.assertIn(cue[2][-1], "，。！？；、", f"chunk not cut at punctuation: {cue[2]!r}")

    def test_timing_contiguous(self) -> None:
        text = "这一句话足够长需要被切成几条短字幕来验证时间轴是连续的而且首尾要闭合"
        start, end = 12.3, 21.7
        out, _ = subtitle_split.split_srt(
            f"1\n00:00:12,300 --> 00:00:21,700\n{text}\n", MAX_UNITS, 6)
        cues = subtitle_split.parse_srt(out)
        self.assertGreater(len(cues), 1)
        for a, b in zip(cues, cues[1:]):
            self.assertAlmostEqual(a[1], b[0], delta=0.0011)
        self.assertAlmostEqual(cues[0][0], start, delta=0.0011)
        self.assertAlmostEqual(cues[-1][1], end, delta=0.0011)

    def test_ascii_mixed(self) -> None:
        text = "我们用 FFmpeg 和 Whisper 两个工具完成转录与粗剪的自动化流水线搭建"
        out, stats = subtitle_split.split_srt(
            f"1\n00:00:00,000 --> 00:00:08,000\n{text}\n", MAX_UNITS, 6)
        self.assertGreaterEqual(stats["cues_out"], 2)
        joined = "".join(c[2] for c in subtitle_split.parse_srt(out))
        # No visible character may be dropped.
        for ch in "FFmpegWhisper自动化流水线":
            self.assertIn(ch, joined)

    def test_multi_cue_srt(self) -> None:
        content = (
            "1\n00:00:00,000 --> 00:00:02,000\n短句一条\n\n"
            "2\n00:00:02,500 --> 00:00:09,000\n这是一条很长的句子因为它包含了很多内容所以必须被切分成多条短字幕才能在剪映里获得原生字幕的观感\n\n"
            "3\n00:00:09,500 --> 00:00:11,000\n收尾\n"
        )
        out, stats = subtitle_split.split_srt(content, MAX_UNITS, 6)
        self.assertEqual(stats["cues_in"], 3)
        self.assertGreater(stats["cues_out"], 3)
        cues = subtitle_split.parse_srt(out)
        # No overlap between original different cues.
        self.assertLess(cues[0][1], 2.001)
        self.assertGreater(cues[-1][0], 9.499)


def subtitle_display_floor(text: str) -> int:
    return int(subtitle_split.display_units(text))


if __name__ == "__main__":
    unittest.main(verbosity=2)
