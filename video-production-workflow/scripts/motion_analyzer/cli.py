"""Unified command-line entrypoint for motion analysis and synthesis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import subprocess
from typing import Any, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer.media_extractor import MediaExtractor  # noqa: E402
from motion_analyzer.motion_reverse_agent import MotionReverseAgent  # noqa: E402
from motion_analyzer.template_synthesizer import TemplateSynthesizer  # noqa: E402


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return {key: _jsonable(item) for key, item in vars(value).items() if not key.startswith("_")}
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _is_missing_agent_configuration_error(error: RuntimeError) -> bool:
    """Return whether an agent error is safe to downgrade to collaboration mode.

    Runtime errors raised while parsing an LLM response, calling an API, or
    exporting Motion IR must remain failures.  Only the explicit offline-agent
    configuration error is recoverable because the extraction artifacts and a
    human/agent prompt can still be handed off.
    """
    message = str(error).lower()
    return (
        "no llm caller or api keys are configured" in message
        or "gemini_api_key / openai_api_key" in message
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze motion clips and synthesize parameterized templates.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(command: argparse.ArgumentParser) -> None:
        command.add_argument("--input", type=Path, required=True, help="video clip or Motion IR JSON input")
        command.add_argument("--start", default=None, help="analysis start time (seconds or MM:SS)")
        command.add_argument("--end", default=None, help="analysis end time (seconds or MM:SS)")
        command.add_argument("--output-dir", type=Path, required=True, help="artifact output directory")

    analyze = subparsers.add_parser("analyze", help="extract media features and write Motion IR/report artifacts")
    add_common(analyze)
    analyze.add_argument("--engine", choices=("remotion", "gsap"), default="remotion")

    synthesize = subparsers.add_parser("synthesize", help="analyze/load Motion IR and synthesize a template")
    add_common(synthesize)
    synthesize.add_argument("--engine", choices=("remotion", "gsap"), default="remotion")
    return parser


def _run_analyze(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    extractor = MediaExtractor(output_dir=args.output_dir)
    extraction_kwargs: dict[str, Any] = {"video_path": args.input}
    if args.start is not None:
        extraction_kwargs["start_time"] = args.start
    if args.end is not None:
        extraction_kwargs["end_time"] = args.end
    extraction = extractor.extract(**extraction_kwargs)
    _write_json(args.output_dir / "media_extraction.json", extraction)

    agent = MotionReverseAgent(mode="offline_adapter")
    try:
        _motion_ir, _report = agent.run(extraction_result=extraction, output_dir=args.output_dir)
    except RuntimeError as error:
        # Collaborative/offline environments may not have an LLM configured.
        # Preserve the prompt and a machine-readable status instead of losing
        # the successful media extraction step.
        if not _is_missing_agent_configuration_error(error):
            raise
        prompt_payload = agent.prepare_collaborative_prompt(extraction)
        _write_json(args.output_dir / "motion_analysis_prompt.json", prompt_payload)
        summary = {"command": "analyze", "status": "awaiting_agent", "error": str(error)}
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    summary = {
        "command": "analyze",
        "status": "completed",
        "output_dir": str(args.output_dir.resolve()),
        "motion_ir": str(args.output_dir / "motion_ir.json"),
        "report": str(args.output_dir / "motion_analysis_report.md"),
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _run_synthesize(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    input_path = args.input
    if input_path.suffix.lower() != ".json":
        analyze_args = argparse.Namespace(
            command="analyze",
            input=input_path,
            start=args.start,
            end=args.end,
            engine=args.engine,
            output_dir=args.output_dir,
        )
        if _run_analyze(analyze_args) != 0:
            return 1
        input_path = args.output_dir / "motion_ir.json"
        if not input_path.exists():
            print(json.dumps({"command": "synthesize", "status": "awaiting_agent"}, ensure_ascii=False))
            return 0

    synthesizer = TemplateSynthesizer(output_root=args.output_dir / "templates")
    template = synthesizer.synthesize(input_path, engine=args.engine, style_pack=None)
    probe = getattr(template, "probe_result", None)
    summary = {
        "command": "synthesize",
        "status": template.status,
        "template_id": template.template_id,
        "engine": template.engine,
        "template": str(template.path),
        "probe_status": getattr(probe, "status", None),
        "probe_status_file": str(getattr(probe, "status_file", "")) if probe else None,
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if template.status in {"approved", "draft"} else 1


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze":
            return _run_analyze(args)
        if args.command == "synthesize":
            return _run_synthesize(args)
        raise ValueError(f"unsupported command: {args.command}")
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"command": args.command, "status": "error", "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
