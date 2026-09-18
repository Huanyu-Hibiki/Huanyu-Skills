"""Generate isolated, parameterized Remotion components from Motion IR.

The synthesizer intentionally emits plain TSX instead of depending on a
Remotion project at generation time.  A later render probe can compile the
component in the consumer's Remotion project while this module remains a
small, deterministic compiler from the validated Motion IR contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
import signal
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Mapping

from .motion_ir import Layer, MotionIR


_SPRING_CALL_RE = re.compile(r"^spring\s*\(\s*(?P<body>.*?)\s*\)$", re.IGNORECASE)
_SPRING_PARAM_RE = re.compile(
    r"(?P<name>damping|stiffness|mass)\s*:\s*"
    r"(?P<value>-?(?:\d+(?:\.\d*)?|\.\d+))",
    re.IGNORECASE,
)
_TRANSFORM_RE = re.compile(r"(?P<name>[A-Za-z][A-Za-z0-9]*)\((?P<values>[^)]*)\)")
_NUMBER_RE = re.compile(r"-?(?:\d+(?:\.\d*)?|\.\d+)")
_VERSION_RE = re.compile(r"-v(?P<version>\d+)$", re.IGNORECASE)
_SAFE_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?(?:[0-9A-Fa-f]{2})?$")
_COLOR_NAME_RE = re.compile(r"^[A-Za-z]+$")
_CUBIC_BEZIER_RE = re.compile(
    r"^cubic-bezier\(\s*(?P<x1>-?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*"
    r"(?P<y1>-?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*"
    r"(?P<x2>-?(?:\d+(?:\.\d*)?|\.\d+))\s*,\s*"
    r"(?P<y2>-?(?:\d+(?:\.\d*)?|\.\d+))\s*\)$",
    re.IGNORECASE,
)

DEFAULT_PROPS: tuple[str, ...] = ("title", "value", "accentColor", "imageSrc")
TYPESCRIPT_VALIDATION_TIMEOUT_SECONDS = 10.0
TYPESCRIPT_VALIDATION_MAX_OUTPUT_BYTES = 16 * 1024
MAX_TYPESCRIPT_SOURCE_BYTES = 1024 * 1024
_NODE_EXECUTABLE: str | None = None


def _trusted_node_executable() -> str | None:
    """Resolve Node once to an absolute, non-reparse executable path."""
    global _NODE_EXECUTABLE
    if _NODE_EXECUTABLE is not None:
        return _NODE_EXECUTABLE
    configured = os.environ.get("HUANYU_NODE_PATH")
    located = configured or shutil.which("node")
    if not located:
        return None
    candidate = Path(located)
    if candidate.is_symlink():
        return None
    try:
        candidate = candidate.resolve(strict=True)
    except OSError:
        return None
    if not candidate.is_file():
        return None
    _NODE_EXECUTABLE = str(candidate)
    return _NODE_EXECUTABLE


@dataclass(frozen=True)
class SynthesizedTemplate:
    """Metadata and source for one immutable generated template file."""

    template_id: str
    style_pack: str
    path: Path
    source: str
    props: tuple[str, ...] = DEFAULT_PROPS
    engine: str = "remotion"
    status: str = "draft"
    probe_result: Any | None = None

    @property
    def output_path(self) -> Path:
        """Compatibility alias used by pipeline callers."""
        return self.path

    @property
    def code(self) -> str:
        """Compatibility alias for the generated TSX source."""
        return self.source


def _coerce_motion_ir(value: MotionIR | Mapping[str, Any] | str | Path) -> MotionIR:
    if isinstance(value, MotionIR):
        return value
    if isinstance(value, Mapping):
        return MotionIR.model_validate(value)
    if not isinstance(value, (str, Path)):
        raise ValueError("motion_ir must be a MotionIR object, mapping, JSON string, or JSON file")
    raw_value = str(value)
    try:
        candidate = Path(value)
        if candidate.exists():
            return MotionIR.model_validate_json(candidate.read_text(encoding="utf-8"))
    except (OSError, TypeError):
        # A long JSON string can itself be rejected by Path.exists() on some
        # platforms; it still deserves one attempt through the JSON seam.
        pass
    try:
        return MotionIR.model_validate_json(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("motion_ir must be a MotionIR object, mapping, JSON string, or JSON file") from exc


def _safe_segment(value: str, label: str) -> str:
    """Validate a user-controlled directory/name segment before path joining."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty safe path segment")
    value = value.strip()
    if value in {".", ".."} or "/" in value or "\\" in value or ".." in value:
        raise ValueError(f"{label} must be a safe path segment")
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-_")
    if not normalized or not _SAFE_SEGMENT_RE.fullmatch(normalized):
        raise ValueError(f"{label} must be a safe path segment")
    return normalized


def _slug(value: str, label: str) -> str:
    return _safe_segment(value.replace(" ", "-").replace("_", "-"), label).lower()


def _component_name(template_id: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", template_id)
    name = "".join(word[:1].upper() + word[1:] for word in words) or "GeneratedMotion"
    if name[0].isdigit():
        name = f"Template{name}"
    return name


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6g}"


def _parse_spring(easing: str) -> dict[str, float] | None:
    match = _SPRING_CALL_RE.fullmatch(easing.strip())
    if not match:
        return None
    params = list(_SPRING_PARAM_RE.finditer(match.group("body")))
    if len(params) != 3 or {item.group("name").lower() for item in params} != {"damping", "stiffness", "mass"}:
        return None
    remainder = _SPRING_PARAM_RE.sub("", match.group("body")).strip(" ,")
    if remainder:
        return None
    return {item.group("name").lower(): float(item.group("value")) for item in params}


def _safe_color(value: Any, fallback: str) -> str:
    """Allow only conservative CSS color tokens in generated source."""
    if not isinstance(value, str):
        return fallback
    candidate = value.strip()
    if _HEX_COLOR_RE.fullmatch(candidate) or _COLOR_NAME_RE.fullmatch(candidate):
        return candidate
    return fallback


def _tsx_string(value: str) -> str:
    """Encode a runtime string as a safe TSX string literal."""
    return json.dumps(value, ensure_ascii=False)


def _normalize_template_id(template_id: str) -> str:
    safe_id = _safe_segment(template_id, "template_id")
    if not safe_id.lower().startswith("remotion-viral-"):
        safe_id = f"remotion-viral-{safe_id}"
    return safe_id


def _remotion_easing(easing: str) -> str:
    """Map the IR's named curves to a valid Remotion Easing expression."""
    normalized = easing.strip().lower()
    if normalized == "linear":
        return "Easing.linear"
    if normalized in {"ease", "ease-in-out", "cubic-bezier(0.42, 0, 0.58, 1)"}:
        return "Easing.inOut(Easing.quad)"
    if normalized.endswith(".in"):
        return "Easing.in(Easing.quad)"
    if normalized.endswith(".out"):
        return "Easing.out(Easing.quad)"
    if normalized.endswith(".inout"):
        return "Easing.inOut(Easing.quad)"
    return "Easing.inOut(Easing.quad)"


def _phase_frame(seconds: float, fps: float) -> int:
    return max(0, round(seconds * fps))


def _parse_transform(transform: str) -> tuple[str, list[float], str] | None:
    """Parse a simple IR transform such as ``scale(0 -> 1.05 -> 1)``."""
    match = _TRANSFORM_RE.fullmatch(transform.strip())
    if not match:
        return None
    raw_values = [part.strip() for part in match.group("values").split("->")]
    values: list[float] = []
    unit = ""
    for raw in raw_values:
        number = _NUMBER_RE.search(raw)
        if not number:
            return None
        values.append(float(number.group(0)))
        suffix = raw[number.end() :].strip()
        if suffix and not unit:
            unit = suffix
    return match.group("name"), values, unit


def extract_props(motion_ir: MotionIR | Mapping[str, Any] | str | Path) -> tuple[str, ...]:
    """Return the stable set of open template parameters exposed to callers."""
    _coerce_motion_ir(motion_ir)
    # Keep the public contract stable even when a clip has no typography or
    # image layer: callers can always supply the same parameter object.
    return DEFAULT_PROPS


def _progress_source(
    variable: str,
    *,
    frame_start: int,
    duration_frames: int,
    easing: str,
    is_spring: bool,
    spring_config: dict[str, float] | None,
) -> str:
    duration_frames = max(1, duration_frames)
    if is_spring and spring_config:
        config = ", ".join(f"{key}: {_format_number(value)}" for key, value in spring_config.items())
        return (
            f"const {variable} = spring({{\n"
            f"  frame: Math.max(0, frame - {frame_start}),\n"
            "  fps,\n"
            f"  config: {{{config}}},\n"
            f"  durationInFrames: {duration_frames},\n"
            "});"
        )
    return (
        f"const {variable} = interpolate(frame, [{frame_start}, {frame_start + duration_frames}], [0, 1], {{\n"
        f"  easing: {_remotion_easing(easing)},\n"
        '  extrapolateLeft: "clamp",\n'
        '  extrapolateRight: "clamp",\n'
        "});"
    )


def _layer_content(layer: Layer) -> str:
    if layer.type == "typography":
        return "<span>{title}</span>"
    if layer.type in {"background", "graphic", "vector_or_illustration", "footage"}:
        return '<>{imageSrc ? <img src={imageSrc} alt="" style={{width: "100%", height: "100%", objectFit: "contain"}} /> : null}<span>{value}</span></>'
    return "<span>{value}</span>"


def render_remotion_tsx(
    motion_ir: MotionIR | Mapping[str, Any] | str | Path,
    *,
    template_id: str = "remotion-viral-generated-motion-v1",
) -> str:
    """Render one validated Motion IR as a standalone Remotion TSX component."""
    ir = _coerce_motion_ir(motion_ir)
    template_id = _normalize_template_id(template_id)
    component = _component_name(template_id)
    fps = ir.meta.fps
    total_frames = ir.meta.duration_frames
    palette = ir.visual_language.color_palette
    background = _safe_color(palette[0] if palette else None, "#111111")
    accent_candidate = palette[2] if len(palette) > 2 else (palette[-1] if palette else None)
    accent = _safe_color(accent_candidate, "#E63946")

    declarations: list[str] = []
    layer_markup: list[str] = []
    for index, layer in enumerate(sorted(ir.layers, key=lambda item: item.z_index)):
        identifier = re.sub(r"[^A-Za-z0-9]", "", layer.layer_id.title()) or f"Layer{index + 1}"
        prefix = f"layer{index + 1}{identifier}"
        phases = layer.phases
        entrance = phases.entrance
        sustain_phase = phases.sustain
        exit_phase = phases.exit
        entrance_start = _phase_frame(entrance.start_time, fps) if entrance else 0
        entrance_duration = _phase_frame(entrance.duration, fps) if entrance else 1
        exit_start = _phase_frame(exit_phase.start_time, fps) if exit_phase else total_frames
        exit_duration = _phase_frame(exit_phase.duration, fps) if exit_phase else 1
        sustain_start = entrance_start + entrance_duration if entrance else 0
        sustain_end = min(
            total_frames,
            sustain_start + (_phase_frame(sustain_phase.duration, fps) if sustain_phase else 0),
            exit_start if exit_phase else total_frames,
        )

        if entrance:
            spring_config = _parse_spring(entrance.easing)
            declarations.append(
                _progress_source(
                    f"{prefix}EntranceProgress",
                    frame_start=entrance_start,
                    duration_frames=entrance_duration,
                    easing=entrance.easing,
                    is_spring=spring_config is not None,
                    spring_config=spring_config,
                )
            )
            entrance_progress = f"{prefix}EntranceProgress"
        else:
            declarations.append(f"const {prefix}EntranceProgress = 1;")
            entrance_progress = f"{prefix}EntranceProgress"

        if exit_phase:
            declarations.append(
                _progress_source(
                    f"{prefix}ExitProgress",
                    frame_start=exit_start,
                    duration_frames=exit_duration,
                    easing=exit_phase.easing,
                    is_spring=False,
                    spring_config=None,
                )
            )
            exit_progress = f"{prefix}ExitProgress"
        else:
            declarations.append(f"const {prefix}ExitProgress = 0;")
            exit_progress = f"{prefix}ExitProgress"

        opacity_name = f"{prefix}Opacity"
        declarations.append(
            f"const {opacity_name} = interpolate({exit_progress}, [0, 1], [1, 0], {{"
            ' extrapolateLeft: "clamp", extrapolateRight: "clamp" });'
        )

        sustain_offset_name = f"{prefix}SustainOffset"
        dynamics = sustain_phase.dynamics.lower() if sustain_phase else ""
        if sustain_phase:
            sustain_progress_name = f"{prefix}SustainProgress"
            sustain_progress_duration = max(1, sustain_end - sustain_start)
            declarations.append(
                f"const {sustain_progress_name} = interpolate(frame, [{sustain_start}, {sustain_start + sustain_progress_duration}], [0, 1], {{"
                ' extrapolateLeft: "clamp", extrapolateRight: "clamp" });'
            )
        else:
            sustain_progress_name = "0"
        if dynamics in {"breathing_float", "subtle_drift"}:
            wave = "Math.sin" if dynamics == "breathing_float" else "Math.cos"
            declarations.append(
                f"const {sustain_offset_name} = {wave}({sustain_progress_name} * Math.PI * 2) * 2;"
            )
        elif dynamics == "idle":
            declarations.append(
                f"const {sustain_offset_name} = Math.sin({sustain_progress_name} * Math.PI * 2) * 0.5;"
            )
        elif sustain_phase:
            # Unknown dynamics remain deterministic and visibly static instead
            # of silently inventing a different animation contract.
            declarations.append(
                f"const {sustain_offset_name} = 0; // Unsupported sustain dynamics; falling back to idle."
            )
        else:
            declarations.append(f"const {sustain_offset_name} = 0;")

        transforms: list[str] = []
        for transform, progress in (
            [(item, entrance_progress) for item in (entrance.transforms if entrance else [])]
            + [(item, exit_progress) for item in (exit_phase.transforms if exit_phase else [])]
        ):
            parsed = _parse_transform(transform)
            if parsed is None:
                continue
            name, values, unit = parsed
            points = ", ".join(_format_number(index / max(1, len(values) - 1)) for index in range(len(values)))
            outputs = ", ".join(_format_number(value) for value in values)
            expression = (
                f"interpolate({progress}, [{points}], [{outputs}], "
                '{ extrapolateLeft: "clamp", extrapolateRight: "extend" })'
            )
            transforms.append(f"{name}(${{{expression}}}{unit})")
        transforms.append(f"translateY(${{{sustain_offset_name}}}px)")
        transform_value = " ".join(transforms)
        layer_markup.append(
            "      <div\n"
            f"        key={{{_tsx_string(layer.layer_id)}}}\n"
            f"        style={{{{\n"
            '          position: "absolute",\n'
            "          top: 0,\n"
            "          left: 0,\n"
            '          width: "100%",\n'
            '          height: "100%",\n'
            f"          zIndex: {layer.z_index},\n"
            '          color: accentColor,\n'
            f"          opacity: Math.min({opacity_name} * phaseVisibility, 1),\n"
            f'          transform: `{transform_value}`,\n'
            "        }}\n"
            f"      >{_layer_content(layer)}</div>"
        )

    declaration_block = "\n\n".join(declarations)
    markup_block = "\n".join(layer_markup)
    return f'''import React from "react";
import {{ AbsoluteFill, Easing, interpolate, spring, useCurrentFrame, useVideoConfig }} from "remotion";

export interface Props {{
  title?: string;
  value?: string | number;
  accentColor?: string;
  imageSrc?: string;
}}

export const {component} = ({{
  title = "Your title",
  value = "0",
  accentColor = "{accent}",
  imageSrc,
}}: Props): React.ReactElement => {{
  const frame = useCurrentFrame();
  const {{ fps, durationInFrames }} = useVideoConfig();
  // Five timeline anchors preserve the 0/20/50/80/100% analysis grid.
  const phaseAnchors = [0, 0.2, 0.5, 0.8, 1].map((point) => point * durationInFrames);
  const phaseVisibility = frame >= phaseAnchors[0] && frame <= phaseAnchors[4] ? 1 : 0;

{_indent(declaration_block, 2)}

  return (
    <AbsoluteFill style={{{{ backgroundColor: "{background}" }}}}>
{markup_block}
    </AbsoluteFill>
  );
}};

export default {component};
'''


def _indent(value: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in value.splitlines())


def _gsap_easing(easing: str) -> str:
    bezier = _CUBIC_BEZIER_RE.fullmatch(easing.strip())
    if bezier:
        x1, y1, x2, y2 = (bezier.group(name) for name in ("x1", "y1", "x2", "y2"))
        return (
            'CustomEase.create("remotionViralBezier", '
            f'"M0,0 C{_format_number(float(x1))},{_format_number(float(y1))} '
            f'{_format_number(float(x2))},{_format_number(float(y2))} 1,1")'
        )
    spring = _parse_spring(easing)
    if spring:
        return "back.out(1.7)"
    normalized = easing.strip().lower()
    if normalized in {"linear", "none"}:
        return "none"
    if normalized.startswith(("power", "sine", "quad", "cubic", "quart", "quint", "expo", "circ", "back", "elastic", "bounce")):
        return easing.strip()
    return "power2.out"


def _gsap_transform_values(transforms: list[str]) -> dict[str, float]:
    values: dict[str, float] = {}
    names = {"translateX": "x", "translateY": "y", "rotate": "rotation", "scale": "scale"}
    for transform in transforms:
        parsed = _parse_transform(transform)
        if parsed is None:
            continue
        name, parsed_values, _unit = parsed
        if name in names and parsed_values:
            values[names[name]] = parsed_values[-1]
    return values


def render_gsap_script(
    motion_ir: MotionIR | Mapping[str, Any] | str | Path,
    *,
    template_id: str = "remotion-viral-generated-motion-v1",
) -> str:
    """Render a GSAP timeline script from the same Motion IR contract."""
    ir = _coerce_motion_ir(motion_ir)
    template_id = _normalize_template_id(template_id)
    palette = ir.visual_language.color_palette
    accent = _safe_color(palette[2] if len(palette) > 2 else (palette[-1] if palette else None), "#E63946")
    lines = [
        'import { gsap } from "gsap";',
        'import { CustomEase } from "gsap/CustomEase";',
        "",
        "gsap.registerPlugin(CustomEase);",
        f"export const TEMPLATE_ID = {_tsx_string(template_id)};",
        "export interface Props {",
        '  title?: string;',
        '  value?: string | number;',
        '  accentColor?: string;',
        '  imageSrc?: string;',
        "}",
        "",
        "export function createMotionTimeline(targets: Record<string, HTMLElement>, props: Props = {}): gsap.core.Timeline {",
        "  const timeline = gsap.timeline();",
        f'  gsap.set(targets.container, {{ color: props.accentColor ?? {_tsx_string(accent)} }});',
    ]
    for index, layer in enumerate(sorted(ir.layers, key=lambda item: item.z_index), start=1):
        target_key = layer.layer_id
        target_literal = _tsx_string(target_key)
        phases = layer.phases
        entrance = phases.entrance
        sustain = phases.sustain
        exit_phase = phases.exit
        target_name = f"target{index}"
        lines.extend([
            f"  const {target_name} = targets[{target_literal}];",
            f"  if ({target_name}) {{",
        ])
        if entrance:
            transform_values = _gsap_transform_values(entrance.transforms)
            to_values = {"opacity": 1, **transform_values}
            values = ", ".join(f"{key}: {_format_number(value)}" for key, value in to_values.items())
            easing = _gsap_easing(entrance.easing)
            easing_literal = easing if easing.startswith("CustomEase.create(") else _tsx_string(easing)
            lines.append(
                f'    timeline.fromTo({target_name}, {{ opacity: 0 }}, {{ {values}, duration: {_format_number(entrance.duration)}, ease: {easing_literal} }}, {_format_number(entrance.start_time)});'
            )
        if sustain:
            if sustain.dynamics.lower() in {"breathing_float", "subtle_drift", "idle"}:
                lines.append(
                    f'    timeline.to({target_name}, {{ y: 2, duration: {_format_number(max(sustain.duration, 0.01))}, repeat: -1, yoyo: true, ease: "sine.inOut" }}, ">0");'
                )
        if exit_phase:
            transform_values = _gsap_transform_values(exit_phase.transforms)
            to_values = {"opacity": 0, **transform_values}
            values = ", ".join(f"{key}: {_format_number(value)}" for key, value in to_values.items())
            easing = _gsap_easing(exit_phase.easing)
            easing_literal = easing if easing.startswith("CustomEase.create(") else _tsx_string(easing)
            lines.append(
                f'    timeline.to({target_name}, {{ {values}, duration: {_format_number(exit_phase.duration)}, ease: {easing_literal} }}, {_format_number(exit_phase.start_time)});'
            )
        lines.append("  }")
    lines.extend(["  return timeline;", "}", ""])
    return "\n".join(lines)


def _write_atomically_exclusive(path: Path, source: str) -> None:
    """Write through a temporary sibling and publish without overwriting."""
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(source)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary_path, path)
        except FileExistsError:
            raise
        finally:
            temporary_path.unlink(missing_ok=True)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _terminate_typescript_process(process: subprocess.Popen[Any]) -> None:
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                shell=False,
            )
        except OSError:
            try:
                process.kill()
            except OSError:
                pass
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except OSError:
        try:
            process.kill()
        except OSError:
            pass


def _run_typescript_parser(node: str, probe: str, filename: str, source: str) -> tuple[int, str]:
    """Run the optional parser with bounded streams and a hard timeout."""
    try:
        process = subprocess.Popen(
            [node, "-e", probe, filename],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=os.name != "nt",
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) if os.name == "nt" else 0,
        )
    except OSError as exc:
        raise RuntimeError(f"TypeScript parser unavailable: {exc}") from exc

    streams: dict[str, tuple[bytes, bool]] = {}
    output_limit = TYPESCRIPT_VALIDATION_MAX_OUTPUT_BYTES

    def read_limited(name: str, stream: Any) -> None:
        chunks: list[bytes] = []
        total = 0
        exceeded = False
        while True:
            chunk = stream.read(4096)
            if not chunk:
                streams[name] = (b"".join(chunks), exceeded)
                return
            total += len(chunk)
            if total <= output_limit:
                chunks.append(chunk)
            else:
                exceeded = True
                _terminate_typescript_process(process)
                streams[name] = (b"".join(chunks), exceeded)
                return

    threads = [
        threading.Thread(target=read_limited, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=read_limited, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + TYPESCRIPT_VALIDATION_TIMEOUT_SECONDS
    timed_out = False
    writer_error: list[BaseException] = []

    def write_input() -> None:
        try:
            assert process.stdin is not None
            process.stdin.write(source.encode("utf-8"))
            process.stdin.close()
        except (BrokenPipeError, OSError) as exc:
            writer_error.append(exc)

    writer = threading.Thread(target=write_input, daemon=True)
    writer.start()
    while process.poll() is None:
        if any(exceeded for _, exceeded in streams.values()):
            _terminate_typescript_process(process)
            break
        if time.monotonic() >= deadline:
            timed_out = True
            _terminate_typescript_process(process)
            break
        time.sleep(0.01)
    if writer.is_alive():
        timed_out = True
        _terminate_typescript_process(process)
        writer.join(timeout=1)
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
    for thread in threads:
        thread.join(timeout=1)
    for stream in (process.stdout, process.stderr):
        try:
            if stream is not None:
                stream.close()
        except OSError:
            pass
    if any(thread.is_alive() for thread in threads):
        raise RuntimeError("TypeScript parser output reader did not terminate")
    if timed_out:
        raise RuntimeError(f"TypeScript parser timed out after {TYPESCRIPT_VALIDATION_TIMEOUT_SECONDS:g}s")
    if any(exceeded for _, exceeded in streams.values()):
        raise RuntimeError("TypeScript parser output exceeded the safety limit")
    stderr = streams.get("stderr", (b"", False))[0].decode("utf-8", errors="replace")
    return process.returncode or 0, stderr[:output_limit]


def validate_typescript_source(source: str, *, filename: str = "generated.tsx") -> bool:
    """Parse generated TS/TSX when the optional Node TypeScript parser exists.

    This seam deliberately reports an unavailable parser instead of claiming
    delimiter checks prove syntax.  CI environments with the ``typescript``
    npm package get a real ``transpileModule`` parse; minimal Python-only
    environments can mark the corresponding test as skipped.
    """
    if not isinstance(source, str) or not source.strip():
        raise ValueError("source must be a non-empty TypeScript string")
    if len(source.encode("utf-8")) > MAX_TYPESCRIPT_SOURCE_BYTES:
        raise ValueError("source exceeds the TypeScript validation limit")
    node = _trusted_node_executable()
    if not node:
        raise RuntimeError("TypeScript parser unavailable: node executable not found")
    probe = r'''
const fs = require("fs");
let ts;
try { ts = require("typescript"); } catch (error) {
  process.stderr.write("typescript package unavailable");
  process.exit(2);
}
const filename = process.argv[1] || "generated.tsx";
const input = fs.readFileSync(0, "utf8");
const result = ts.transpileModule(input, {
  fileName: filename,
  reportDiagnostics: true,
  compilerOptions: { jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
});
const diagnostics = (result.diagnostics || []).filter((item) => item.category === ts.DiagnosticCategory.Error);
if (diagnostics.length) {
  process.stderr.write(ts.formatDiagnosticsWithColorAndContext(diagnostics, {
    getCurrentLine: () => "",
    getCanonicalFileName: (value) => value,
    getNewLine: () => "\n",
  }));
  process.exit(1);
}
'''
    returncode, stderr = _run_typescript_parser(node, probe, filename, source)
    if returncode == 2:
        raise RuntimeError("TypeScript parser unavailable: install the typescript npm package")
    if returncode != 0:
        raise ValueError(f"TypeScript syntax validation failed: {stderr.strip()}")
    return True


class TemplateSynthesizer:
    """Persist generated templates under an isolated style-pack directory.

    Remotion components use ``.tsx``; GSAP timeline modules use ``.ts``
    because they contain no JSX. Both engines share the same template ID and
    version namespace within a style pack.
    """

    def __init__(self, output_root: str | Path | None = None) -> None:
        self.output_root = (
            Path(output_root)
            if output_root is not None
            else Path(__file__).resolve().parents[2] / "templates" / "synthesized"
        ).resolve()

    def synthesize(
        self,
        motion_ir: MotionIR | Mapping[str, Any] | str | Path,
        *,
        style_pack: str | None = None,
        template_name: str | None = None,
        engine: str = "remotion",
        probe: bool = True,
        _probe_runner: Callable[[Any], Any] | None = None,
        probe_output_dir: str | Path | None = None,
        probe_timeout: float = 60.0,
        register: bool = True,
        _probe_allow_injected_runner: bool = False,
    ) -> SynthesizedTemplate:
        normalized_engine = engine.lower()
        if normalized_engine not in {"remotion", "gsap"}:
            raise ValueError("engine must be remotion or gsap")
        ir = _coerce_motion_ir(motion_ir)
        style_value = style_pack or ir.meta.style_archetype or "default"
        name_value = template_name or Path(ir.meta.source_name or "generated-motion").stem
        style = _slug(style_value, "style_pack")
        name = _slug(name_value, "template_name")
        if name.startswith("remotion-viral-"):
            name = name.removeprefix("remotion-viral-")
        name = _VERSION_RE.sub("", name)
        base_id = f"remotion-viral-{style}-{name}"
        target_dir = (self.output_root / style).resolve()
        if self.output_root not in target_dir.parents and target_dir != self.output_root:
            raise ValueError("style_pack resolves outside the synthesis sandbox")
        target_dir.mkdir(parents=True, exist_ok=True)

        version = 1
        while True:
            if any(
                (target_dir / f"{base_id}-v{version}{extension}").exists()
                for extension in (".tsx", ".ts")
            ):
                version += 1
                continue
            template_id = f"{base_id}-v{version}"
            extension = ".tsx" if normalized_engine == "remotion" else ".ts"
            path = target_dir / f"{template_id}{extension}"
            source = (
                render_remotion_tsx(ir, template_id=template_id)
                if normalized_engine == "remotion"
                else render_gsap_script(ir, template_id=template_id)
            )
            try:
                _write_atomically_exclusive(path, source)
                break
            except FileExistsError:
                version += 1

        template = SynthesizedTemplate(
            template_id=template_id,
            style_pack=style,
            path=path,
            source=source,
            props=extract_props(ir),
            engine=normalized_engine,
        )
        if normalized_engine != "remotion" or not probe:
            return template

        # Import lazily so the deterministic source compiler remains usable in
        # Python-only environments.  Fake runners are accepted only through
        # the private test seam; production synthesis always uses the fixed
        # headless Remotion runner.
        if _probe_runner is None:
            from .render_probe import _probe_synthesized_template_internal

            result = _probe_synthesized_template_internal(
                template,
                output_dir=probe_output_dir,
                timeout=probe_timeout,
                register=register,
                trusted_root=self.output_root,
            )
        else:
            from .render_probe import _probe_synthesized_template_for_tests

            if not _probe_allow_injected_runner:
                raise ValueError("_probe_runner is test-only; set _probe_allow_injected_runner for tests")
            result = _probe_synthesized_template_for_tests(
                template,
                runner=_probe_runner,
                output_dir=probe_output_dir,
                timeout=probe_timeout,
                register=register,
                trusted_root=self.output_root,
                allow_injected_runner=True,
            )
        return SynthesizedTemplate(
            template_id=template.template_id,
            style_pack=template.style_pack,
            path=template.path,
            source=template.source,
            props=template.props,
            engine=template.engine,
            status=result.status,
            probe_result=result,
        )

    def synthesize_remotion(
        self,
        motion_ir: MotionIR | Mapping[str, Any] | str | Path,
        **kwargs: Any,
    ) -> SynthesizedTemplate:
        return self.synthesize(motion_ir, engine="remotion", **kwargs)

    def synthesize_gsap(
        self,
        motion_ir: MotionIR | Mapping[str, Any] | str | Path,
        **kwargs: Any,
    ) -> SynthesizedTemplate:
        return self.synthesize(motion_ir, engine="gsap", **kwargs)


def synthesize_remotion_template(
    motion_ir: MotionIR | Mapping[str, Any] | str | Path,
    *,
    output_root: str | Path | None = None,
    style_pack: str | None = None,
    template_name: str | None = None,
    probe: bool = True,
    _probe_runner: Callable[[Any], Any] | None = None,
    probe_output_dir: str | Path | None = None,
    probe_timeout: float = 60.0,
    register: bool = True,
    _probe_allow_injected_runner: bool = False,
) -> SynthesizedTemplate:
    """Functional convenience API for CLI and pipeline callers."""
    return TemplateSynthesizer(output_root).synthesize(
        motion_ir,
        style_pack=style_pack,
        template_name=template_name,
        probe=probe,
        _probe_runner=_probe_runner,
        probe_output_dir=probe_output_dir,
        probe_timeout=probe_timeout,
        register=register,
        _probe_allow_injected_runner=_probe_allow_injected_runner,
    )


def synthesize_gsap_template(
    motion_ir: MotionIR | Mapping[str, Any] | str | Path,
    *,
    output_root: str | Path | None = None,
    style_pack: str | None = None,
    template_name: str | None = None,
    probe: bool = False,
) -> SynthesizedTemplate:
    """Functional convenience API for GSAP pipeline callers."""
    return TemplateSynthesizer(output_root).synthesize(
        motion_ir,
        style_pack=style_pack,
        template_name=template_name,
        engine="gsap",
        probe=probe,
    )


__all__ = [
    "DEFAULT_PROPS",
    "SynthesizedTemplate",
    "TemplateSynthesizer",
    "extract_props",
    "render_gsap_script",
    "render_remotion_tsx",
    "synthesize_gsap_template",
    "synthesize_remotion_template",
    "validate_typescript_source",
]
