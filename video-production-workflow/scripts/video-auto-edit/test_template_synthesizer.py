"""Contract tests for the Motion IR -> Remotion TSX synthesizer."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer.motion_ir import MotionIR  # noqa: E402
from motion_analyzer.template_synthesizer import (  # noqa: E402
    SynthesizedTemplate,
    TemplateSynthesizer,
    render_gsap_script,
    render_remotion_tsx,
    validate_typescript_source,
)


@pytest.fixture
def sample_ir() -> MotionIR:
    return MotionIR.model_validate(
        {
            "$schema": "motion-ir-v1",
            "meta": {
                "source_name": "editorial-card.mp4",
                "duration_frames": 90,
                "fps": 30,
                "style_archetype": "vox_explainer",
            },
            "visual_language": {
                "color_palette": ["#111111", "#F4F0EA", "#E63946"],
                "texture": "paper",
                "spatial_layout": "split_column",
            },
            "layers": [
                {
                    "layer_id": "bg-canvas",
                    "type": "background",
                    "z_index": 0,
                },
                {
                    "layer_id": "headline-text",
                    "type": "typography",
                    "z_index": 2,
                    "phases": {
                        "entrance": {
                            "start_time": 0.5,
                            "duration": 0.4,
                            "easing": "spring(damping: 12, stiffness: 180, mass: 0.8)",
                            "transforms": ["scale(0 -> 1.05 -> 1.0)", "rotate(-6deg -> 0deg)"],
                        },
                        "sustain": {"duration": 1.1, "dynamics": "breathing_float"},
                        "exit": {
                            "start_time": 2.0,
                            "duration": 0.3,
                            "easing": "power2.in",
                        },
                    },
                },
            ],
        }
    )


def test_render_remotion_tsx_contains_valid_component_shape_and_motion_math(sample_ir: MotionIR):
    """The renderer emits a self-contained Remotion component with frame math.

    The repository does not ship a TypeScript/TSX parser, so this is a
    dependency-free static guard for delimiters, required exports, and the
    generated Remotion seam. Full compiler validation remains the render
    probe's responsibility.
    """
    source = render_remotion_tsx(sample_ir, template_id="remotion-viral-vox-explainer-editorial-card-v1")

    assert 'from "remotion"' in source
    assert "export interface Props" in source
    assert "useCurrentFrame()" in source
    assert "useVideoConfig()" in source
    assert "spring({" in source
    assert "interpolate(" in source
    assert "position: \"absolute\"" in source
    assert "damping: 12" in source
    assert "stiffness: 180" in source
    assert "mass: 0.8" in source
    assert source.count("<AbsoluteFill") >= 1
    assert source.count("{") == source.count("}")
    assert source.count("(") == source.count(")")


def test_render_remotion_tsx_static_syntax_guard(sample_ir: MotionIR):
    source = render_remotion_tsx(sample_ir)

    assert source.lstrip().startswith('import React from "react";')
    assert re.search(r"export const [A-Za-z][A-Za-z0-9]* =", source)
    assert source.rstrip().endswith(";")
    assert "style={{" in source and "}}" in source


def test_render_remotion_tsx_extracts_open_props(sample_ir: MotionIR):
    source = render_remotion_tsx(sample_ir)

    props_block = re.search(r"export interface Props \{(?P<body>.*?)\}", source, re.DOTALL)
    assert props_block is not None
    props = props_block.group("body")
    assert "title" in props
    assert "value" in props
    assert "accentColor" in props
    assert "imageSrc" in props


def test_synthesizer_writes_isolated_incrementing_versions(sample_ir: MotionIR, tmp_path: Path):
    synthesizer = TemplateSynthesizer(output_root=tmp_path)

    first = synthesizer.synthesize(sample_ir, style_pack="vox_explainer", template_name="editorial-card")
    second = synthesizer.synthesize(sample_ir, style_pack="vox_explainer", template_name="editorial-card")

    assert isinstance(first, SynthesizedTemplate)
    assert first.path.parent == tmp_path / "vox-explainer"
    assert first.path.name == "remotion-viral-vox-explainer-editorial-card-v1.tsx"
    assert second.path.name == "remotion-viral-vox-explainer-editorial-card-v2.tsx"
    assert first.path.read_text(encoding="utf-8") != second.path.read_text(encoding="utf-8") or first.path != second.path
    assert first.path.exists() and second.path.exists()
    assert not (tmp_path / "outside.tsx").exists()


def test_synthesizer_rejects_path_traversal(sample_ir: MotionIR, tmp_path: Path):
    synthesizer = TemplateSynthesizer(output_root=tmp_path)

    with pytest.raises(ValueError, match="safe|path|segment"):
        synthesizer.synthesize(sample_ir, style_pack="../escape", template_name="card")


def _ir_with_changes(sample_ir: MotionIR, **changes: object) -> MotionIR:
    payload = sample_ir.model_dump(by_alias=True)
    for key, value in changes.items():
        payload["layers"][1]["phases"][key] = value
    return MotionIR.model_validate(payload)


def test_spring_parser_accepts_parameter_order_whitespace_and_leading_dot(sample_ir: MotionIR):
    ir = _ir_with_changes(
        sample_ir,
        entrance={
            "start_time": 0.5,
            "duration": 0.4,
            "easing": " spring( mass: .8, stiffness : 180 , damping: 12 ) ",
            "transforms": ["scale(0 -> 1)"],
        },
    )

    source = render_remotion_tsx(ir)

    assert "config: {mass: 0.8, stiffness: 180, damping: 12}" in source


def test_incomplete_spring_safely_falls_back_to_interpolate(sample_ir: MotionIR):
    ir = _ir_with_changes(
        sample_ir,
        entrance={
            "start_time": 0.5,
            "duration": 0.4,
            "easing": "spring(damping: 12, stiffness: 180)",
        },
    )

    source = render_remotion_tsx(ir)

    assert "layer2HeadlineTextEntranceProgress = interpolate(" in source
    assert "config: {" not in source


def test_exit_transforms_are_frame_interpolated(sample_ir: MotionIR):
    ir = _ir_with_changes(
        sample_ir,
        exit={
            "start_time": 2.0,
            "duration": 0.3,
            "easing": "power2.in",
            "transforms": ["scale(1 -> 0)", "translateX(0px -> -120px)", "rotate(0deg -> 8deg)"],
        },
    )

    source = render_remotion_tsx(ir)

    assert "interpolate(layer2HeadlineTextExitProgress" in source
    assert "scale(${interpolate(layer2HeadlineTextExitProgress" in source
    assert "translateX(${interpolate(layer2HeadlineTextExitProgress" in source
    assert "rotate(${interpolate(layer2HeadlineTextExitProgress" in source


def test_props_are_used_by_visible_markup_and_styles(sample_ir: MotionIR):
    payload = sample_ir.model_dump(by_alias=True)
    payload["layers"].append({"layer_id": "metric", "type": "counter", "z_index": 3})
    source = render_remotion_tsx(MotionIR.model_validate(payload))

    assert "void value" not in source
    assert "void accentColor" not in source
    assert "color: accentColor" in source
    assert ">{value}</span>" in source


def test_sustain_dynamics_generate_visible_micro_motion(sample_ir: MotionIR):
    source = render_remotion_tsx(sample_ir)

    assert "phaseAnchors" in source
    assert "phaseVisibility" in source
    assert "Math.sin" in source
    assert "void phaseAnchors" not in source


def test_sustain_motion_is_bounded_by_layer_phase_frames(sample_ir: MotionIR):
    source = render_remotion_tsx(sample_ir)

    assert "const layer2HeadlineTextSustainProgress = interpolate(frame, [27, 60]" in source
    assert "layer2HeadlineTextSustainProgress" in source
    assert "phaseAnchors[2]" not in source.split("layer2HeadlineTextSustainOffset", 1)[1].split("\n\n", 1)[0]


def test_layers_without_exit_do_not_use_global_fade(sample_ir: MotionIR):
    payload = sample_ir.model_dump(by_alias=True)
    payload["layers"][1]["phases"].pop("exit")

    source = render_remotion_tsx(MotionIR.model_validate(payload))

    assert "phaseBoundaryOpacity" not in source
    assert "opacity: Math.min(layer2HeadlineTextOpacity * phaseVisibility, 1)," in source


def test_unknown_sustain_dynamics_have_explicit_idle_fallback(sample_ir: MotionIR):
    ir = _ir_with_changes(sample_ir, sustain={"duration": 1.1, "dynamics": "unlisted_motion"})

    source = render_remotion_tsx(ir)

    assert "Unsupported sustain dynamics; falling back to idle" in source


def test_gsap_script_contains_timeline_duration_positions_and_easing(sample_ir: MotionIR):
    source = render_gsap_script(
        sample_ir,
        template_id="remotion-viral-vox-explainer-editorial-card-v1",
    )

    assert "gsap.timeline()" in source
    assert "duration: 0.4" in source
    assert "}, 0.5);" in source
    assert "power2.in" in source
    assert "remotion-viral-vox-explainer-editorial-card-v1" in source


def test_gsap_script_preserves_cubic_bezier_control_points(sample_ir: MotionIR):
    ir = _ir_with_changes(
        sample_ir,
        entrance={
            "start_time": 0.5,
            "duration": 0.4,
            "easing": "cubic-bezier(0.1, 0.2, 0.3, 0.4)",
        },
    )

    source = render_gsap_script(ir)

    assert "CustomEase.create" in source
    assert "C0.1,0.2 0.3,0.4 1,1" in source
    assert "ease: CustomEase.create" in source


def test_synthesizer_supports_gsap_versions_in_same_sandbox(sample_ir: MotionIR, tmp_path: Path):
    synthesizer = TemplateSynthesizer(output_root=tmp_path)

    first = synthesizer.synthesize(
        sample_ir,
        style_pack="vox_explainer",
        template_name="editorial-card",
        engine="gsap",
    )
    second = synthesizer.synthesize(
        sample_ir,
        style_pack="vox_explainer",
        template_name="editorial-card",
        engine="gsap",
    )

    assert first.path.suffix == ".ts"
    assert first.engine == "gsap"
    assert first.path.name == "remotion-viral-vox-explainer-editorial-card-v1.ts"
    assert second.path.name == "remotion-viral-vox-explainer-editorial-card-v2.ts"
    assert "gsap.timeline()" in first.source


def test_remotion_and_gsap_share_template_version_space(sample_ir: MotionIR, tmp_path: Path):
    synthesizer = TemplateSynthesizer(output_root=tmp_path)

    remotion = synthesizer.synthesize(sample_ir, style_pack="vox_explainer", template_name="shared")
    gsap = synthesizer.synthesize(sample_ir, style_pack="vox_explainer", template_name="shared", engine="gsap")

    assert remotion.template_id.endswith("-v1")
    assert gsap.template_id.endswith("-v2")
    assert remotion.template_id.rsplit("-v", 1)[0] == gsap.template_id.rsplit("-v", 1)[0]


def test_untrusted_layer_and_palette_values_do_not_break_tsx(sample_ir: MotionIR):
    payload = sample_ir.model_dump(by_alias=True)
    payload["visual_language"]["color_palette"] = ['#111111"; color: red; /*']
    payload["layers"][0]["layer_id"] = 'evil"; alert("xss"); //'

    source = render_remotion_tsx(MotionIR.model_validate(payload))

    assert 'key="evil"; alert' not in source
    assert 'backgroundColor: "#111111"; color: red' not in source


def test_invalid_input_types_are_normalized_to_value_error():
    with pytest.raises(ValueError, match="motion_ir"):
        render_remotion_tsx(123)  # type: ignore[arg-type]


def test_typescript_parser_probe_is_explicitly_available_or_skipped(sample_ir: MotionIR):
    source = render_remotion_tsx(sample_ir)

    try:
        valid = validate_typescript_source(source, filename="generated.tsx")
    except RuntimeError as exc:
        pytest.skip(str(exc))
    assert valid is True


def test_typescript_parser_probe_times_out_bounded_node_process(monkeypatch: Any):
    import subprocess

    original_popen = subprocess.Popen

    def hanging_popen(*args: Any, **kwargs: Any) -> Any:
        command = args[0] if args else kwargs.get("args", [])
        if command and str(command[0]).lower() == "taskkill":
            return original_popen(*args, **kwargs)
        return original_popen(
            [sys.executable, "-c", "import time; time.sleep(60)"],
            stdin=kwargs.get("stdin"),
            stdout=kwargs.get("stdout"),
            stderr=kwargs.get("stderr"),
            shell=False,
        )

    monkeypatch.setattr("motion_analyzer.template_synthesizer.TYPESCRIPT_VALIDATION_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr("motion_analyzer.template_synthesizer.subprocess.Popen", hanging_popen)
    with pytest.raises(RuntimeError, match="timed out"):
        validate_typescript_source("export default function Template() { return null; }")
