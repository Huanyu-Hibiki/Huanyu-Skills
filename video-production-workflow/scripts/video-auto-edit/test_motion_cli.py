from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

from PIL import Image, ImageDraw
import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer import cli  # noqa: E402
from motion_analyzer.motion_reverse_agent import MotionReverseAgent as RealMotionReverseAgent  # noqa: E402
from motion_analyzer.render_probe import ProbeExecution  # noqa: E402
from motion_analyzer.template_synthesizer import TemplateSynthesizer as RealTemplateSynthesizer  # noqa: E402
from lib.broll_registry import get_template, unregister_dynamic_template  # noqa: E402


def test_parser_exposes_pipeline_arguments() -> None:
    args = cli.build_parser().parse_args(
        [
            "synthesize",
            "--input",
            "motion_ir.json",
            "--start",
            "00:01",
            "--end",
            "00:02",
            "--engine",
            "gsap",
            "--output-dir",
            "out",
        ]
    )

    assert args.command == "synthesize"
    assert args.input == Path("motion_ir.json")
    assert args.start == "00:01"
    assert args.end == "00:02"
    assert args.engine == "gsap"
    assert args.output_dir == Path("out")


def test_analyze_writes_extraction_and_agent_artifacts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"sample")
    output_dir = tmp_path / "analysis"
    extraction = SimpleNamespace(
        video_path=str(input_path),
        start_time=1.0,
        end_time=2.0,
        duration=1.0,
        has_audio=False,
        contact_sheet_path=str(output_dir / "contact_sheet.png"),
        audio_wav_path=None,
        keyframe_timestamps=[1.0, 1.2, 1.5, 1.8, 2.0],
        audio_anchors=SimpleNamespace(onsets=[], beats=[]),
    )

    class FakeExtractor:
        def __init__(self, output_dir: Path) -> None:
            self.output_dir = output_dir

        def extract(self, **kwargs: object) -> SimpleNamespace:
            assert kwargs == {
                "video_path": input_path,
                "start_time": "1",
                "end_time": "2",
            }
            return extraction

    class FakeAgent:
        def __init__(self, mode: str) -> None:
            assert mode == "offline_adapter"

        def run(self, extraction_result: object, output_dir: Path) -> tuple[object, str]:
            assert extraction_result is extraction
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "motion_ir.json").write_text("{}", encoding="utf-8")
            (output_dir / "motion_analysis_report.md").write_text("# report", encoding="utf-8")
            return SimpleNamespace(meta=SimpleNamespace(source_name="clip.mp4")), "# report"

    monkeypatch.setattr(cli, "MediaExtractor", FakeExtractor)
    monkeypatch.setattr(cli, "MotionReverseAgent", FakeAgent)

    assert (
        cli.main(
            [
                "analyze",
                "--input",
                str(input_path),
                "--start",
                "1",
                "--end",
                "2",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)
    assert summary["command"] == "analyze"
    assert summary["status"] == "completed"
    assert (output_dir / "motion_ir.json").exists()
    assert (output_dir / "motion_analysis_report.md").exists()


def test_synthesize_loads_ir_and_returns_probe_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ir_path = tmp_path / "motion_ir.json"
    ir_path.write_text('{"$schema":"motion-ir-v1"}', encoding="utf-8")
    output_dir = tmp_path / "synthesis"
    template_path = output_dir / "templates" / "remotion-viral-v1.tsx"

    class FakeTemplate:
        template_id = "remotion-viral-demo-v1"
        style_pack = "demo"
        path = template_path
        engine = "remotion"
        status = "approved"
        probe_result = SimpleNamespace(status="approved", passed=True, status_file=output_dir / "probe.json")

    class FakeSynthesizer:
        def __init__(self, output_root: Path) -> None:
            assert output_root == output_dir / "templates"

        def synthesize(self, motion_ir: Path, **kwargs: object) -> FakeTemplate:
            assert motion_ir == ir_path
            assert kwargs == {"engine": "remotion", "style_pack": None}
            return FakeTemplate()

    monkeypatch.setattr(cli, "TemplateSynthesizer", FakeSynthesizer)

    assert (
        cli.main(
            [
                "synthesize",
                "--input",
                str(ir_path),
                "--engine",
                "remotion",
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )

    summary = json.loads(capsys.readouterr().out)
    assert summary["command"] == "synthesize"
    assert summary["status"] == "approved"
    assert summary["template_id"] == "remotion-viral-demo-v1"


def test_analyze_falls_back_to_collaborative_prompt_without_api_keys(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"sample")
    output_dir = tmp_path / "analysis"
    extraction = SimpleNamespace(video_path=str(input_path), contact_sheet_path="sheet.png")

    class FakeExtractor:
        def __init__(self, output_dir: Path) -> None:
            pass

        def extract(self, **kwargs: object) -> object:
            return extraction

    class FakeAgent:
        def __init__(self, mode: str) -> None:
            assert mode == "offline_adapter"

        def run(self, **kwargs: object) -> object:
            raise RuntimeError("no LLM caller or API keys are configured")

        def prepare_collaborative_prompt(self, extraction_result: object) -> dict[str, object]:
            assert extraction_result is extraction
            return {"prompt": "analyze this", "contact_sheet_path": "sheet.png"}

    monkeypatch.setattr(cli, "MediaExtractor", FakeExtractor)
    monkeypatch.setattr(cli, "MotionReverseAgent", FakeAgent)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert cli.main(["analyze", "--input", str(input_path), "--output-dir", str(output_dir)]) == 0

    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "awaiting_agent"
    assert (output_dir / "motion_analysis_prompt.json").exists()


def test_analyze_does_not_hide_agent_processing_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    input_path = tmp_path / "clip.mp4"
    input_path.write_bytes(b"sample")
    output_dir = tmp_path / "analysis"
    extraction = SimpleNamespace(video_path=str(input_path), contact_sheet_path="sheet.png")

    class FakeExtractor:
        def __init__(self, output_dir: Path) -> None:
            pass

        def extract(self, **kwargs: object) -> object:
            return extraction

    class FailingAgent:
        def __init__(self, mode: str) -> None:
            pass

        def run(self, **kwargs: object) -> object:
            raise RuntimeError("invalid Motion IR returned by the provider")

    monkeypatch.setattr(cli, "MediaExtractor", FakeExtractor)
    monkeypatch.setattr(cli, "MotionReverseAgent", FailingAgent)

    assert cli.main(["analyze", "--input", str(input_path), "--output-dir", str(output_dir)]) == 2
    error_summary = json.loads(capsys.readouterr().err)
    assert error_summary["status"] == "error"
    assert "invalid Motion IR" in error_summary["error"]


def test_main_serializes_subprocess_failures_as_structured_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        cli,
        "_run_synthesize",
        lambda _args: (_ for _ in ()).throw(subprocess.CalledProcessError(1, ["ffmpeg"])),
    )

    assert (
        cli.main(
            [
                "synthesize",
                "--input",
                str(tmp_path / "motion_ir.json"),
                "--output-dir",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )
    error_summary = json.loads(capsys.readouterr().err)
    assert error_summary["status"] == "error"


def _valid_motion_ir_response() -> str:
    return json.dumps(
        {
            "$schema": "motion-ir-v1",
            "meta": {
                "source_name": "short-sample.mp4",
                "duration_frames": 75,
                "fps": 30,
                "style_archetype": "vox_explainer",
                "dominant_mood": "analytical_high_tempo",
            },
            "visual_language": {
                "color_palette": ["#111111", "#F4F0EA", "#E63946"],
                "texture": "clean",
                "spatial_layout": "centered",
            },
            "audio_anchors": {
                "tempo_bpm": None,
                "beats": [],
                "onsets": [],
                "sync_strategy": "uniform_visual_cadence",
            },
            "layers": [
                {"layer_id": "background", "type": "background", "z_index": 0},
                {
                    "layer_id": "headline",
                    "type": "typography",
                    "z_index": 1,
                    "phases": {
                        "entrance": {
                            "start_time": 0.0,
                            "duration": 0.3,
                            "easing": "power2.out",
                        },
                        "sustain": {"duration": 1.0, "dynamics": "breathing_float"},
                        "exit": {"start_time": 2.0, "duration": 0.3, "easing": "power2.in"},
                    },
                },
            ],
            "engine_affinity": {
                "recommended_primary": "remotion",
                "fallback": "gsap",
                "rationale": "Frame-level parameterized motion.",
            },
        }
    )


def test_short_video_cli_pipeline_reaches_real_template_probe_and_registry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exercise FFmpeg extraction, real IR/report/TSX generation, probe gating, and registration.

    The probe runner is the explicit test seam for environments without a local
    Remotion installation.  The CLI, extractor, agent parser/report writer,
    template synthesizer, quality gate, and registry remain real code paths.
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg is required for the short-video integration test")

    video_path = tmp_path / "short-sample.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=64x36:r=30:d=1",
            "-vf",
            "drawbox=x='10+20*t':y=8:w=12:h=12:color=white:t=fill",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    analysis_dir = tmp_path / "analysis"
    synthesis_dir = tmp_path / "synthesis"

    monkeypatch.setattr(
        cli,
        "MotionReverseAgent",
        lambda mode: RealMotionReverseAgent(
            mode=mode,
            llm_caller=lambda _prompt, _image: _valid_motion_ir_response(),
        ),
    )
    assert (
        cli.main(
            [
                "analyze",
                "--input",
                str(video_path),
                "--start",
                "0",
                "--end",
                "1",
                "--output-dir",
                str(analysis_dir),
            ]
        )
        == 0
    )
    analysis_summary = json.loads(capsys.readouterr().out)
    assert analysis_summary["status"] == "completed"
    assert (analysis_dir / "contact_sheet.png").stat().st_size > 0
    assert (analysis_dir / "motion_ir.json").exists()
    assert (analysis_dir / "motion_analysis_report.md").exists()

    def render_probe(request: object) -> ProbeExecution:
        output_dir = request.output_dir  # type: ignore[attr-defined]
        output_dir.mkdir(parents=True, exist_ok=True)
        frames: list[Path] = []
        for frame_number in range(30):
            frame_path = output_dir / f"frame-{frame_number:02d}.png"
            image = Image.new("RGB", (64, 36), "#101010")
            draw = ImageDraw.Draw(image)
            x = 4 + frame_number
            draw.rectangle((x, 10, x + 12, 22), fill="#E63946")
            image.save(frame_path)
            frames.append(frame_path)
        return ProbeExecution(frame_paths=tuple(frames), command=("integration-probe",))

    real_synthesizer = RealTemplateSynthesizer

    class IntegrationSynthesizer:
        def __init__(self, output_root: Path) -> None:
            self._delegate = real_synthesizer(output_root=output_root)

        def synthesize(self, motion_ir: Path, **kwargs: object) -> object:
            return self._delegate.synthesize(
                motion_ir,
                _probe_runner=render_probe,
                _probe_allow_injected_runner=True,
                **kwargs,
            )

    monkeypatch.setattr(cli, "TemplateSynthesizer", IntegrationSynthesizer)
    try:
        assert (
            cli.main(
                [
                    "synthesize",
                    "--input",
                    str(analysis_dir / "motion_ir.json"),
                    "--engine",
                    "remotion",
                    "--output-dir",
                    str(synthesis_dir),
                ]
            )
            == 0
        )
        synthesis_summary = json.loads(capsys.readouterr().out)
        assert synthesis_summary["status"] == "approved"
        assert synthesis_summary["probe_status"] == "approved"
        template_path = Path(synthesis_summary["template"])
        assert template_path.suffix == ".tsx"
        assert template_path.exists()
        registered = get_template(synthesis_summary["template_id"])
        assert registered is not None
        assert registered["status"] == "approved"
        assert registered["registry_source"] == "render_probe"
    finally:
        if "synthesis_summary" in locals():
            unregister_dynamic_template(synthesis_summary["template_id"])
