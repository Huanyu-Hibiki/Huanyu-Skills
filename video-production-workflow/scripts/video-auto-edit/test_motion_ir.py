import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer.motion_ir import MotionIR  # noqa: E402


def test_motion_ir_valid_full_spec():
    """测试一个合法的全字段 Motion IR 样本反序列化与字段契约"""
    sample_data = {
        "$schema": "motion-ir-v1",
        "meta": {
            "source_name": "viral_clip_01.mp4",
            "duration_frames": 90,
            "fps": 30.0,
            "style_archetype": "vox_explainer",
            "dominant_mood": "analytical_high_tempo",
        },
        "visual_language": {
            "color_palette": ["#1A1A1A", "#F4F0EA", "#E63946", "#F1FAEE"],
            "texture": "paper_tear_with_halftone",
            "spatial_layout": "split_column_emphasis",
        },
        "audio_anchors": {
            "tempo_bpm": 128.0,
            "beats": [0.0, 0.468, 0.937, 1.406, 1.875],
            "onsets": [0.468, 1.120, 1.875],
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
                "layer_id": "main-graphic",
                "type": "vector_or_illustration",
                "z_index": 1,
                "phases": {
                    "entrance": {
                        "start_time": 0.468,
                        "duration": 0.35,
                        "easing": "spring(damping: 12, stiffness: 180, mass: 0.8)",
                        "transforms": ["scale(0 -> 1.05 -> 1.0)", "rotate(-6deg -> 0deg)"],
                    },
                    "sustain": {"duration": 1.2, "dynamics": "breathing_float"},
                    "exit": {"start_time": 2.0, "duration": 0.25, "easing": "power2.in"},
                },
            },
            {
                "layer_id": "headline-text",
                "type": "typography",
                "z_index": 2,
                "typography": {"font_weight": "heavy", "style": "editorial_box"},
                "phases": {
                    "entrance": {"start_time": 0.55, "type": "stagger_words_slide_up"}
                },
            },
        ],
        "engine_affinity": {
            "recommended_primary": "remotion",
            "fallback": "hyperframes",
            "rationale": "High frame-level spring math and multi-layer React composition.",
        },
    }

    ir = MotionIR.model_validate(sample_data)
    assert ir.schema_version == "motion-ir-v1"
    assert ir.meta.duration_frames == 90
    assert ir.meta.fps == 30.0
    assert ir.total_duration_seconds == 3.0
    assert len(ir.layers) == 3
    assert ir.engine_affinity.recommended_primary == "remotion"

    # JSON 序列化与 Schema 导出互转测试
    json_str = ir.model_dump_json()
    assert "viral_clip_01.mp4" in json_str
    reloaded = MotionIR.model_validate_json(json_str)
    assert reloaded == ir

    schema_dict = MotionIR.model_json_schema()
    assert "properties" in schema_dict
    assert "meta" in schema_dict["properties"]


def test_motion_ir_defaults_and_minimal_spec():
    """测试缺损字段默认值填充与最小化规范"""
    minimal_data = {
        "meta": {
            "duration_frames": 60,
        }
    }
    ir = MotionIR.model_validate(minimal_data)
    assert ir.meta.fps == 30.0
    assert ir.meta.source_name == ""
    assert ir.visual_language.color_palette == []
    assert ir.audio_anchors.beats == []
    assert ir.audio_anchors.onsets == []
    assert ir.layers == []
    assert ir.engine_affinity.recommended_primary == "remotion"


def test_motion_ir_timestamp_out_of_bounds_validation():
    """测试图层关键帧时间戳超过总时长时被正确拦截"""
    invalid_data = {
        "meta": {
            "duration_frames": 60,
            "fps": 30.0,  # 总时长为 2.0 秒
        },
        "layers": [
            {
                "layer_id": "late-layer",
                "type": "graphic",
                "phases": {
                    "entrance": {
                        "start_time": 2.5,  # 超出 2.0 秒
                        "duration": 0.5,
                    }
                },
            }
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        MotionIR.model_validate(invalid_data)
    assert "exceeds total duration" in str(exc_info.value).lower()


def test_motion_ir_invalid_easing_syntax_validation():
    """测试非法缓动参数语法拦截"""
    invalid_data = {
        "meta": {
            "duration_frames": 90,
            "fps": 30.0,
        },
        "layers": [
            {
                "layer_id": "bad-easing-layer",
                "type": "graphic",
                "phases": {
                    "entrance": {
                        "start_time": 0.1,
                        "duration": 0.5,
                        "easing": "invalid_func(foo: bar)",
                    }
                },
            }
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        MotionIR.model_validate(invalid_data)
    assert "easing" in str(exc_info.value).lower()


def test_motion_ir_chronological_phase_validation():
    """测试图层生命周期相位时序错乱拦截（例如 exit 时间早于 entrance 时间）"""
    invalid_data = {
        "meta": {
            "duration_frames": 90,
            "fps": 30.0,
        },
        "layers": [
            {
                "layer_id": "unordered-layer",
                "type": "graphic",
                "phases": {
                    "entrance": {
                        "start_time": 1.5,
                        "duration": 0.5,
                    },
                    "exit": {
                        "start_time": 1.0,  # 早于 entrance
                        "duration": 0.3,
                    },
                },
            }
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        MotionIR.model_validate(invalid_data)
    assert "exit start_time" in str(exc_info.value).lower()


def test_motion_ir_meta_invalid_numbers():
    """测试负数或非法帧率、时长帧数拦截"""
    with pytest.raises(ValidationError):
        MotionIR.model_validate({"meta": {"duration_frames": -10, "fps": 30}})

    with pytest.raises(ValidationError):
        MotionIR.model_validate({"meta": {"duration_frames": 60, "fps": 0}})


def test_motion_ir_exit_out_of_bounds():
    """测试 exit start_time 超出总时长的拦截"""
    invalid_data = {
        "meta": {"duration_frames": 30, "fps": 30.0},  # 1.0s
        "layers": [
            {
                "layer_id": "late-exit",
                "phases": {
                    "exit": {"start_time": 1.5, "duration": 0.2}
                }
            }
        ]
    }
    with pytest.raises(ValidationError) as exc_info:
        MotionIR.model_validate(invalid_data)
    assert "exceeds total duration" in str(exc_info.value).lower()


def test_motion_ir_design_doc_spec_exact_json():
    """测试直接引入设计文档第 3 节原始 JSON，验证顶层 entrance 自动折叠与 $schema 完整保留"""
    design_doc_json = {
        "$schema": "motion-ir-v1",
        "meta": {
            "source_name": "viral_clip_01.mp4",
            "duration_frames": 90,
            "fps": 30,
            "style_archetype": "vox_explainer",
            "dominant_mood": "analytical_high_tempo",
        },
        "visual_language": {
            "color_palette": ["#1A1A1A", "#F4F0EA", "#E63946", "#F1FAEE"],
            "texture": "paper_tear_with_halftone",
            "spatial_layout": "split_column_emphasis",
        },
        "audio_anchors": {
            "tempo_bpm": 128.0,
            "beats": [0.0, 0.468, 0.937, 1.406, 1.875],
            "onsets": [0.468, 1.120, 1.875],
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
                "layer_id": "main-graphic",
                "type": "vector_or_illustration",
                "z_index": 1,
                "phases": {
                    "entrance": {
                        "start_time": 0.468,
                        "duration": 0.35,
                        "easing": "spring(damping: 12, stiffness: 180, mass: 0.8)",
                        "transforms": ["scale(0 -> 1.05 -> 1.0)", "rotate(-6deg -> 0deg)"],
                    },
                    "sustain": {"duration": 1.2, "dynamics": "breathing_float"},
                    "exit": {"start_time": 2.0, "duration": 0.25, "easing": "power2.in"},
                },
            },
            {
                "layer_id": "headline-text",
                "type": "typography",
                "z_index": 2,
                "typography": {"font_weight": "heavy", "style": "editorial_box"},
                "entrance": {"start_time": 0.55, "type": "stagger_words_slide_up"},
            },
        ],
        "engine_affinity": {
            "recommended_primary": "remotion",
            "fallback": "hyperframes",
            "rationale": "High frame-level spring math and multi-layer React composition.",
        },
    }

    ir = MotionIR.model_validate(design_doc_json)

    # 验证第三个图层 headline-text 的顶层 entrance 被成功折叠入 phases
    headline_layer = ir.layers[2]
    assert headline_layer.layer_id == "headline-text"
    assert headline_layer.phases.entrance is not None
    assert headline_layer.phases.entrance.start_time == 0.55
    assert headline_layer.phases.entrance.type == "stagger_words_slide_up"

    # 验证序列化输出保留 $schema 键且无损
    dumped = ir.model_dump()
    assert "$schema" in dumped
    assert dumped["$schema"] == "motion-ir-v1"

    dumped_json = ir.model_dump_json()
    assert '"$schema":"motion-ir-v1"' in dumped_json or '"$schema": "motion-ir-v1"' in dumped_json

    # 重新反序列化验证数据闭环无损
    reloaded = MotionIR.model_validate_json(dumped_json)
    assert reloaded.schema_version == "motion-ir-v1"
    assert reloaded.layers[2].phases.entrance.start_time == 0.55


def test_motion_ir_phase_duration_overflow_intercepted():
    """测试入场或退场 phase 的持续时间跨度 (start_time + duration) 超出总时长的防御拦截"""
    # 1. entrance end time 溢出
    invalid_entrance_overflow = {
        "meta": {"duration_frames": 60, "fps": 30.0},  # 2.0s
        "layers": [
            {
                "layer_id": "overflow-entrance",
                "phases": {
                    "entrance": {"start_time": 1.5, "duration": 0.8}  # 2.3s > 2.0s
                },
            }
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        MotionIR.model_validate(invalid_entrance_overflow)
    assert "entrance end time" in str(exc_info.value).lower()

    # 2. exit end time 溢出
    invalid_exit_overflow = {
        "meta": {"duration_frames": 60, "fps": 30.0},  # 2.0s
        "layers": [
            {
                "layer_id": "overflow-exit",
                "phases": {
                    "exit": {"start_time": 1.8, "duration": 0.5}  # 2.3s > 2.0s
                },
            }
        ],
    }
    with pytest.raises(ValidationError) as exc_info:
        MotionIR.model_validate(invalid_exit_overflow)
    assert "exit end time" in str(exc_info.value).lower()
