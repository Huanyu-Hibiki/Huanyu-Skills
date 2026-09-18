"""Unit tests for motion_reverse_agent.py (Task 3: Motion Reverse Reasoning & Decomposition Report Generator)."""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any, Dict
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer.media_extractor import MediaExtractionResult  # noqa: E402
from motion_analyzer.motion_ir import AudioAnchors, MotionIR  # noqa: E402
from motion_analyzer.motion_reverse_agent import (  # noqa: E402
    MotionReverseAgent,
    _encode_image_to_base64,
    build_motion_decomposition_prompt,
    extract_clean_json_payload,
    generate_decomposition_report,
)


@pytest.fixture
def mock_extraction_result(tmp_path: Path) -> MediaExtractionResult:
    """Fixture providing a deterministic MediaExtractionResult."""
    contact_sheet = tmp_path / "contact_sheet.png"
    contact_sheet.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes")
    return MediaExtractionResult(
        video_path=str(tmp_path / "sample_clip.mp4"),
        start_time=0.0,
        end_time=2.5,
        duration=2.5,
        has_audio=True,
        contact_sheet_path=str(contact_sheet),
        keyframe_timestamps=[0.0, 0.5, 1.25, 2.0, 2.5],
        audio_anchors=AudioAnchors(
            tempo_bpm=120.0,
            beats=[0.0, 0.5, 1.0, 1.5, 2.0, 2.5],
            onsets=[0.5, 1.25, 2.0],
            sync_strategy="snap_entrance_to_nearest_beat",
        ),
    )


@pytest.fixture
def valid_motion_ir_dict() -> Dict[str, Any]:
    """Fixture providing a valid Motion IR dictionary payload."""
    return {
        "$schema": "motion-ir-v1",
        "meta": {
            "source_name": "sample_clip.mp4",
            "duration_frames": 75,
            "fps": 30.0,
            "style_archetype": "vox_explainer",
            "dominant_mood": "analytical_high_tempo",
        },
        "visual_language": {
            "color_palette": ["#1A1A1A", "#F4F0EA", "#E63946"],
            "texture": "paper_tear_with_halftone",
            "spatial_layout": "split_column_emphasis",
        },
        "audio_anchors": {
            "tempo_bpm": 120.0,
            "beats": [0.0, 0.5, 1.0, 1.5, 2.0, 2.5],
            "onsets": [0.5, 1.25, 2.0],
            "sync_strategy": "snap_entrance_to_nearest_beat",
        },
        "layers": [
            {
                "layer_id": "bg-canvas",
                "type": "background",
                "z_index": 0,
                "motion_dynamics": "subtle_drift_scale_1.0_to_1.05",
            },
            {
                "layer_id": "headline-text",
                "type": "typography",
                "z_index": 1,
                "phases": {
                    "entrance": {
                        "start_time": 0.5,
                        "duration": 0.4,
                        "easing": "spring(damping: 12, stiffness: 180, mass: 0.8)",
                        "transforms": ["scale(0 -> 1.0)"],
                    },
                    "sustain": {
                        "duration": 1.1,
                        "dynamics": "breathing_float",
                    },
                    "exit": {
                        "start_time": 2.0,
                        "duration": 0.3,
                        "easing": "power2.in",
                    },
                },
            },
        ],
        "engine_affinity": {
            "recommended_primary": "remotion",
            "fallback": "hyperframes",
            "rationale": "High frame-level spring math and React multi-layer composition.",
        },
    }


# =========================================================================
# 1. Base64 编码与 MIME 类型检测测试
# =========================================================================

def test_encode_image_to_base64_mime_types(tmp_path: Path):
    """测试不同格式图片的 MIME 识别与 base64 编码"""
    png_file = tmp_path / "test.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    mime, b64 = _encode_image_to_base64(png_file)
    assert mime == "image/png"
    assert len(b64) > 0

    jpg_file = tmp_path / "test.jpg"
    jpg_file.write_bytes(b"\xff\xd8\xfffake")
    mime_jpg, _ = _encode_image_to_base64(jpg_file)
    assert mime_jpg == "image/jpeg"

    webp_file = tmp_path / "test.webp"
    webp_file.write_bytes(b"RIFFfakeWEBP")
    mime_webp, _ = _encode_image_to_base64(webp_file)
    assert mime_webp == "image/webp"


def test_encode_image_to_base64_nonexistent_raises(tmp_path: Path):
    """测试不存在的文件抛出 FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        _encode_image_to_base64(tmp_path / "nonexistent.png")


# =========================================================================
# 2. Prompt 编排契约测试
# =========================================================================

def test_build_motion_decomposition_prompt_contains_spec_and_anchors(
    mock_extraction_result: MediaExtractionResult,
):
    """测试多模态解构 Prompt 编排包含时序帧、音频锚点、规范指引与 JSON Schema 约定"""
    prompt = build_motion_decomposition_prompt(mock_extraction_result)

    assert "sample_clip.mp4" in prompt
    assert "2.5" in prompt
    assert "0.0, 0.5, 1.25, 2.0, 2.5" in prompt
    assert "120.0" in prompt
    assert "0.5, 1.25, 2.0" in prompt
    assert "motion-ir-v1" in prompt
    assert "spring(" in prompt
    assert "phases" in prompt
    assert "contact_sheet.png" in prompt


def test_build_motion_decomposition_prompt_silent_degrade(
    mock_extraction_result: MediaExtractionResult,
):
    """测试无音频流场景下的 Prompt 优雅降级说明"""
    mock_extraction_result.has_audio = False
    mock_extraction_result.audio_anchors.tempo_bpm = None
    mock_extraction_result.audio_anchors.onsets = []
    mock_extraction_result.audio_anchors.beats = []

    prompt = build_motion_decomposition_prompt(mock_extraction_result)
    assert "无音频流" in prompt or "Silent" in prompt or "no audio" in prompt.lower()


# =========================================================================
# 3. JSON 自愈与鲁棒清洗机制测试
# =========================================================================

def test_extract_clean_json_payload_markdown_code_block(valid_motion_ir_dict: Dict[str, Any]):
    """测试从带 ```json 代码块的 LLM 原始文本中提取出干净的 JSON"""
    raw_response = f"""Here is the decomposed motion analysis:
```json
{json.dumps(valid_motion_ir_dict, indent=2)}
```
Hope this helps!"""

    payload = extract_clean_json_payload(raw_response)
    assert payload["$schema"] == "motion-ir-v1"
    assert len(payload["layers"]) == 2


def test_extract_clean_json_payload_dirty_surrounding_text(valid_motion_ir_dict: Dict[str, Any]):
    """测试在无显式 markdown 标记但有前后文本时利用大括号平衡定位提取"""
    raw_response = f"Prefix explanation text...\n{json.dumps(valid_motion_ir_dict)}\nSuffix remarks..."

    payload = extract_clean_json_payload(raw_response)
    assert payload["meta"]["source_name"] == "sample_clip.mp4"


def test_extract_clean_json_payload_trailing_commas(valid_motion_ir_dict: Dict[str, Any]):
    """测试自愈轻微 JSON 语法瑕疵（例如尾随逗号）"""
    bad_json_str = """
    {
      "$schema": "motion-ir-v1",
      "meta": {
        "source_name": "sample.mp4",
        "duration_frames": 60,
        "fps": 30.0,
      },
      "layers": [],
    }
    """
    payload = extract_clean_json_payload(bad_json_str)
    assert payload["meta"]["duration_frames"] == 60


def test_extract_clean_json_payload_invalid_raises():
    """测试完全非法的内容抛出 ValueError"""
    with pytest.raises(ValueError, match="Failed to extract valid JSON payload"):
        extract_clean_json_payload("This is pure text with no valid json: { broken ")


# =========================================================================
# 4. 结构化 Markdown 报告生成测试
# =========================================================================

def test_generate_decomposition_report_format(valid_motion_ir_dict: Dict[str, Any]):
    """测试生成的 Markdown 报告包含规范视听特征、逐图层五相位与伪代码"""
    motion_ir = MotionIR.model_validate(valid_motion_ir_dict)
    report_md = generate_decomposition_report(motion_ir)

    assert "爆款动效逆向解构报告" in report_md
    assert "sample_clip.mp4" in report_md
    assert "vox_explainer" in report_md
    assert "120.0" in report_md
    assert "bg-canvas" in report_md
    assert "headline-text" in report_md
    assert "spring(" in report_md
    assert "REMOTION" in report_md or "remotion" in report_md
    assert "```json" in report_md


# =========================================================================
# 5. Agent 执行器模式 (协作模式 & Mock 适配器)
# =========================================================================

def test_motion_reverse_agent_collaborative_mode(
    mock_extraction_result: MediaExtractionResult,
):
    """测试 Agent 协作模式：输出提示词给会话环境驱动原生视觉能力"""
    agent = MotionReverseAgent(mode="collaborative")
    output = agent.prepare_collaborative_prompt(mock_extraction_result)

    assert "prompt" in output
    assert "contact_sheet_path" in output
    assert output["contact_sheet_path"] == mock_extraction_result.contact_sheet_path
    assert "sample_clip.mp4" in output["prompt"]


def test_motion_reverse_agent_ingest_response_and_export(
    mock_extraction_result: MediaExtractionResult,
    valid_motion_ir_dict: Dict[str, Any],
    tmp_path: Path,
):
    """测试 Agent 接收多模态响应文本，完成自愈校验并导出 motion_ir.json 与 Markdown 报告"""
    agent = MotionReverseAgent(mode="collaborative")

    raw_llm_response = f"""```json
{json.dumps(valid_motion_ir_dict)}
```"""

    output_dir = tmp_path / "output_test"
    motion_ir, report_md = agent.process_response_and_export(
        raw_response=raw_llm_response,
        output_dir=output_dir,
    )

    assert isinstance(motion_ir, MotionIR)
    assert motion_ir.meta.source_name == "sample_clip.mp4"

    # 验证导出的文件实体
    ir_file = output_dir / "motion_ir.json"
    report_file = output_dir / "motion_analysis_report.md"

    assert ir_file.exists()
    assert report_file.exists()

    loaded_json = json.loads(ir_file.read_text(encoding="utf-8"))
    assert loaded_json["meta"]["duration_frames"] == 75
    assert "爆款动效逆向解构报告" in report_file.read_text(encoding="utf-8")


def test_motion_reverse_agent_offline_mock_adapter(
    mock_extraction_result: MediaExtractionResult,
    valid_motion_ir_dict: Dict[str, Any],
    tmp_path: Path,
):
    """测试离线适配器模式（通过 mock LLM 回调函数）完成端到端推理闭环"""
    def mock_llm_caller(prompt: str, image_path: str) -> str:
        assert Path(image_path).exists()
        assert "sample_clip.mp4" in prompt
        return f"```json\n{json.dumps(valid_motion_ir_dict)}\n```"

    agent = MotionReverseAgent(mode="offline_adapter", llm_caller=mock_llm_caller)
    output_dir = tmp_path / "offline_output"

    motion_ir, report_md = agent.run(
        extraction_result=mock_extraction_result,
        output_dir=output_dir,
    )

    assert isinstance(motion_ir, MotionIR)
    assert (output_dir / "motion_ir.json").exists()
    assert (output_dir / "motion_analysis_report.md").exists()
