"""Behavioral tests for the synthesized-template render quality gate."""

from __future__ import annotations

import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from lib.broll_registry import (  # noqa: E402
    _issue_probe_receipt,
    get_template,
    register_dynamic_template,
    unregister_dynamic_template,
)
from motion_analyzer.render_probe import (  # noqa: E402
    _probe_synthesized_template_for_tests as probe_synthesized_template,
    ProbeError,
    ProbeExecution,
    ProbeResult,
)
from motion_analyzer.motion_ir import MotionIR  # noqa: E402
from motion_analyzer.template_synthesizer import SynthesizedTemplate, TemplateSynthesizer  # noqa: E402


def _template(tmp_path: Path, template_id: str) -> SynthesizedTemplate:
    source = tmp_path / f"{template_id}.tsx"
    source.write_text("export default function Template() { return null; }\n", encoding="utf-8")
    return SynthesizedTemplate(
        template_id=template_id,
        style_pack="test_style",
        path=source,
        source=source.read_text(encoding="utf-8"),
    )


def _runner_with_frames(request) -> ProbeExecution:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(30):
        frame = request.output_dir / f"frame-{index:02d}.png"
        image = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        image.putpixel((index % 8, index // 8), (255, 64, 32, 255))
        image.save(frame)
        frames.append(frame)
    return ProbeExecution(frame_paths=tuple(frames), stdout="ok", stderr="")


def _transparent_runner(request) -> ProbeExecution:
    request.output_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index in range(30):
        frame = request.output_dir / f"frame-{index:02d}.png"
        Image.new("RGBA", (8, 8), (0, 0, 0, 0)).save(frame)
        frames.append(frame)
    return ProbeExecution(frame_paths=tuple(frames), stdout="ok", stderr="")


def test_concurrent_duplicate_probe_keeps_approved_receipt(tmp_path: Path) -> None:
    template_id = "remotion-viral-concurrent-probe-receipt-v1"
    template = _template(tmp_path, template_id)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(
                lambda _: probe_synthesized_template(
                    template,
                    runner=_runner_with_frames,
                    trusted_root=tmp_path,
                    allow_injected_runner=True,
                ),
                range(2),
            ))

        assert all(result.status == "approved" for result in results)
        assert get_template(template_id)["status"] == "approved"
        assert '"status": "approved"' in template.path.with_name(
            template.path.name + ".probe.json"
        ).read_text(encoding="utf-8")
    finally:
        unregister_dynamic_template(template_id)


def test_successful_probe_approves_and_registers_template(tmp_path: Path) -> None:
    template_id = "remotion-viral-test-style-probe-pass-v1"
    template = _template(tmp_path, template_id)
    try:
        result = probe_synthesized_template(
            template,
            runner=_runner_with_frames,
            trusted_root=tmp_path,
            allow_injected_runner=True,
        )

        assert isinstance(result, ProbeResult)
        assert result.status == "approved"
        assert result.frame_count == 30
        assert result.status_file is not None and result.status_file.exists()
        assert get_template(template_id)["status"] == "approved"
    finally:
        unregister_dynamic_template(template_id)


def test_failed_probe_persists_log_and_never_registers_template(tmp_path: Path) -> None:
    template_id = "remotion-viral-test-style-probe-fail-v1"
    template = _template(tmp_path, template_id)

    result = probe_synthesized_template(
        template,
        runner=_transparent_runner,
        trusted_root=tmp_path,
        allow_injected_runner=True,
    )

    assert result.status == "draft_failed"
    assert result.error_log is not None and result.error_log.exists()
    assert get_template(template_id) is None
    assert "non-transparent" in result.error


def test_each_probe_gets_an_empty_isolated_output_directory(tmp_path: Path) -> None:
    template = _template(tmp_path, "remotion-viral-test-style-isolated-v1")
    observed: list[tuple[Path, int]] = []

    def runner(request) -> ProbeExecution:
        observed.append((request.output_dir, len(tuple(request.output_dir.iterdir()))))
        return _runner_with_frames(request)

    first = probe_synthesized_template(template, runner=runner, trusted_root=tmp_path, register=False)
    second = probe_synthesized_template(template, runner=runner, trusted_root=tmp_path, register=False)
    assert first.status == second.status == "approved"
    assert len(observed) == 2
    assert observed[0][1] == observed[1][1] == 0
    assert observed[0][0] != observed[1][0]


def test_command_output_is_rejected_at_bounded_reader(tmp_path: Path) -> None:
    command = [sys.executable, "-c", "print('x' * 20000)"]
    from motion_analyzer.render_probe import _run_command

    try:
        _run_command(command, cwd=tmp_path, timeout=5)
    except ProbeError as exc:
        assert "output exceeded" in str(exc)
    else:
        raise AssertionError("oversized command output was accepted")


def test_dynamic_registry_rejects_duplicate_concurrent_registration() -> None:
    template_id = "remotion-viral-concurrent-v1"
    entry = {
        "id": template_id,
        "name": "Concurrent",
        "engine": "remotion",
        "engine_version": "local-generated",
        "source": "templates/synthesized/test/concurrent.tsx",
        "source_hash": "0" * 64,
        "license": "Proprietary-Generated",
        "aspect_ratios": ["16:9"],
        "duration_range": [1.0, 60.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": ["test"],
        "shot_grammar": {
            "visual_role": "generated_motion",
            "camera_motion": "parameterized",
            "motion_dynamics": "frame_interpolated",
            "narrative_focus": "generated_template",
        },
        "props_schema": {},
        "status": "approved",
        "registry_source": "render_probe",
    }
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda _: _try_register(entry), range(8)))
        assert outcomes.count(True) == 1
        stored = get_template(template_id)
        assert stored is not None
        stored["shot_grammar"]["visual_role"] = "mutated"
        assert get_template(template_id)["shot_grammar"]["visual_role"] == "generated_motion"
    finally:
        unregister_dynamic_template(template_id)


def test_dynamic_registry_rejects_forged_approved_entry() -> None:
    with pytest.raises(ValueError, match="receipt"):
        register_dynamic_template({
            "id": "remotion-viral-forged-v1",
            "name": "Forged",
            "engine": "remotion",
            "engine_version": "local-generated",
            "source": "templates/synthesized/test/forged.tsx",
            "source_hash": "0" * 64,
            "license": "Proprietary-Generated",
            "aspect_ratios": ["16:9"],
            "duration_range": [1.0, 60.0],
            "transparency": "opaque",
            "overlay_mode": "full_frame",
            "style_packs": ["test"],
            "shot_grammar": {
                "visual_role": "generated_motion",
                "camera_motion": "parameterized",
                "motion_dynamics": "frame_interpolated",
                "narrative_focus": "generated_template",
            },
            "props_schema": {},
            "status": "approved",
            "registry_source": "render_probe",
        })


def _try_register(entry: dict[str, Any]) -> bool:
    try:
        register_dynamic_template(
            entry,
            receipt=_issue_probe_receipt(entry),
        )
    except ValueError:
        return False
    return True


def test_static_visible_frames_fail_motion_gate(tmp_path: Path) -> None:
    template = _template(tmp_path, "remotion-viral-test-style-probe-static-v1")

    def runner(request) -> ProbeExecution:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        frames = []
        for index in range(30):
            frame = request.output_dir / f"frame-{index:02d}.png"
            Image.new("RGBA", (8, 8), (255, 64, 32, 255)).save(frame)
            frames.append(frame)
        return ProbeExecution(frame_paths=tuple(frames))

    result = probe_synthesized_template(
        template,
        runner=runner,
        trusted_root=tmp_path,
        allow_injected_runner=True,
    )

    assert result.status == "draft_failed"
    assert "no valid motion pixels" in result.error


def test_probe_rejects_frames_outside_output_sandbox(tmp_path: Path) -> None:
    template = _template(tmp_path, "remotion-viral-test-style-probe-escape-v1")
    outside = tmp_path / "outside.png"
    Image.new("RGBA", (8, 8), (255, 64, 32, 255)).save(outside)

    def runner(request) -> ProbeExecution:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        return ProbeExecution(frame_paths=tuple(outside for _ in range(30)))

    result = probe_synthesized_template(
        template,
        runner=runner,
        trusted_root=tmp_path,
        allow_injected_runner=True,
    )

    assert result.status == "draft_failed"
    assert "escaped" in result.error


def _sample_ir() -> MotionIR:
    return MotionIR.model_validate(
        {
            "$schema": "motion-ir-v1",
            "meta": {"source_name": "probe.mp4", "duration_frames": 30, "fps": 30, "style_archetype": "test_style"},
            "visual_language": {"color_palette": ["#111111", "#ffffff"], "texture": "paper", "spatial_layout": "center"},
            "layers": [{"layer_id": "headline", "type": "typography", "z_index": 1}],
        }
    )


def test_synthesize_runs_approved_probe_by_default_and_can_disable_it(tmp_path: Path) -> None:
    synthesizer = TemplateSynthesizer(output_root=tmp_path)
    first = synthesizer.synthesize(
        _sample_ir(),
        template_name="auto",
        _probe_runner=_runner_with_frames,
        _probe_allow_injected_runner=True,
    )
    assert first.status == "approved"
    assert first.probe_result is not None

    second = synthesizer.synthesize(_sample_ir(), template_name="disabled", probe=False)
    assert second.status == "draft"
    assert second.probe_result is None


def test_real_probe_runs_typescript_validation_before_renderer(tmp_path: Path, monkeypatch: Any) -> None:
    template = _template(tmp_path, "remotion-viral-test-style-tsx-invalid-v1")
    calls: list[str] = []

    def invalid_parser(source: str, *, filename: str = "generated.tsx") -> bool:
        calls.append(filename)
        raise ValueError("TypeScript syntax validation failed")

    def unexpected_renderer(request) -> ProbeExecution:
        raise AssertionError("renderer must not run after a syntax failure")

    monkeypatch.setattr("motion_analyzer.render_probe.validate_typescript_source", invalid_parser)
    result = probe_synthesized_template(template, runner=None, trusted_root=tmp_path)
    assert result.status == "draft_failed"
    assert "TypeScript syntax validation failed" in result.error
    assert calls == [template.path.name]


def test_external_template_path_requires_explicit_trusted_root(tmp_path: Path) -> None:
    template = _template(tmp_path, "remotion-viral-external-v1")

    try:
        probe_synthesized_template(template, runner=_runner_with_frames, allow_injected_runner=True)
    except ValueError as exc:
        assert "trusted" in str(exc)
    else:
        raise AssertionError("external template path was accepted")


def test_injected_runner_cannot_register_without_explicit_test_flag(tmp_path: Path) -> None:
    template = _template(tmp_path, "remotion-viral-test-style-injected-v1")

    try:
        probe_synthesized_template(template, runner=_runner_with_frames, trusted_root=tmp_path)
    except ValueError as exc:
        assert "runner" in str(exc)
    else:
        raise AssertionError("injected runner was allowed to register")


def test_probe_rejects_oversized_frame_before_decode(tmp_path: Path) -> None:
    template = _template(tmp_path, "remotion-viral-test-style-huge-v1")

    def runner(request) -> ProbeExecution:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        frame = request.output_dir / "frame-00.png"
        Image.new("RGBA", (5000, 5000), (255, 64, 32, 255)).save(frame)
        return ProbeExecution(frame_paths=tuple(frame for _ in range(30)))

    result = probe_synthesized_template(
        template,
        runner=runner,
        trusted_root=tmp_path,
        allow_injected_runner=True,
    )
    assert result.status == "draft_failed"
    assert "dimensions" in result.error or "pixels" in result.error


def test_probe_state_write_failure_does_not_register(tmp_path: Path, monkeypatch: Any) -> None:
    template_id = "remotion-viral-test-style-state-failure-v1"
    template = _template(tmp_path, template_id)

    def fail_write(*args: Any, **kwargs: Any) -> None:
        raise OSError("state storage unavailable")

    monkeypatch.setattr("motion_analyzer.render_probe._atomic_write_text", fail_write)
    result = probe_synthesized_template(
        template,
        runner=_runner_with_frames,
        trusted_root=tmp_path,
        allow_injected_runner=True,
    )
    assert result.status == "draft_failed"
    assert get_template(template_id) is None
