"""Safe one-second render gate for synthesized Remotion templates.

The probe has a small injectable runner seam so Python-only test environments
can exercise the quality gate.  The default runner uses the local Remotion CLI
when a project with the required packages is available; missing dependencies
are reported as a failed draft instead of escaping as a process error.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable, Mapping, Sequence

from PIL import Image

from .template_synthesizer import SynthesizedTemplate, validate_typescript_source


FRAME_COUNT = 30
FPS = 30
PROBE_DURATION_SECONDS = 1.0
MAX_OUTPUT_BYTES = 128 * 1024 * 1024
MAX_LOG_BYTES = 16 * 1024
MAX_PROBE_FILES = 64
MAX_RETAINED_PROBE_DIRS = 8
MAX_FRAME_WIDTH = 4096
MAX_FRAME_HEIGHT = 4096
MAX_FRAME_PIXELS = 16_777_216
MAX_TOTAL_FRAME_PIXELS = 67_108_864
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
DEFAULT_TRUSTED_ROOT = Path(__file__).resolve().parents[2] / "templates" / "synthesized"
TRUSTED_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TRUSTED_EXECUTABLES: dict[str, str | None] = {}
_PROBE_LOCKS: dict[str, threading.RLock] = {}
_PROBE_LOCKS_GUARD = threading.RLock()


def _probe_lock(template_id: str) -> threading.RLock:
    with _PROBE_LOCKS_GUARD:
        return _PROBE_LOCKS.setdefault(template_id, threading.RLock())


def _is_test_process() -> bool:
    """Return true only while pytest is actively executing a test."""
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))


@dataclass(frozen=True)
class ProbeRequest:
    """Bounded render request passed to an injected or real runner."""

    template_path: Path
    template_id: str
    output_dir: Path
    frame_count: int = FRAME_COUNT
    fps: int = FPS
    source_bytes: bytes | None = None


@dataclass(frozen=True)
class ProbeExecution:
    """Runner output consumed by the public quality gate."""

    frame_paths: tuple[Path, ...] = ()
    output_path: Path | None = None
    command: tuple[str, ...] = ()
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class ProbeResult:
    """Durable result of a synthesized-template probe."""

    template_id: str
    status: str
    passed: bool
    frame_count: int
    moving_pixels: int
    output_dir: Path
    source: str = ""
    source_hash: str = ""
    error: str = ""
    error_log: Path | None = None
    status_file: Path | None = None
    command: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()


class ProbeError(RuntimeError):
    """An expected, user-visible probe failure."""


def _bounded_text(value: Any, limit: int = MAX_LOG_BYTES) -> str:
    if isinstance(value, bytes):
        text = value.decode("utf-8", errors="replace")
    else:
        text = str(value or "")
    if len(text.encode("utf-8", errors="replace")) <= limit:
        return text
    encoded = text.encode("utf-8", errors="replace")[:limit]
    return encoded.decode("utf-8", errors="ignore") + "\n[truncated]"


def _sanitized_error(value: Any, *, template_path: Path, output_dir: Path) -> str:
    text = _bounded_text(value)
    for sensitive in (str(template_path), str(output_dir)):
        text = text.replace(sensitive, f"<{Path(sensitive).name}>")
    return text


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        import stat

        return bool(getattr(path.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    except OSError:
        return False


def _assert_safe_template(template: SynthesizedTemplate, trusted_root: Path) -> tuple[Path, str]:
    template_id = getattr(template, "template_id", None)
    if not isinstance(template_id, str) or not _SAFE_ID_RE.fullmatch(template_id):
        raise ValueError("unsafe template_id")
    path_value = getattr(template, "path", None)
    if not isinstance(path_value, (str, Path)):
        raise ValueError("template path is required")
    path = Path(path_value)
    if _is_link_like(path):
        raise ValueError("template path may not be a symlink or reparse point")
    unresolved = path.absolute()
    for parent in (unresolved, *unresolved.parents):
        if _is_link_like(parent):
            raise ValueError("template path may not contain a symlink or reparse point")
        if parent.parent == parent:
            break
    path = path.resolve(strict=True)
    if not path.is_file() or path.suffix.lower() not in {".tsx", ".ts"}:
        raise ValueError("template path must be a TypeScript source file")
    if path != trusted_root and trusted_root not in path.parents:
        raise ValueError("template path is outside the trusted synthesized-template root")
    return path, template_id


def _assert_safe_output_dir(output_dir: Path, template_dir: Path) -> Path:
    candidate = output_dir if output_dir.is_absolute() else template_dir / output_dir
    unresolved = candidate.absolute()
    for parent in (unresolved, *unresolved.parents):
        if _is_link_like(parent):
            raise ValueError("probe output directory may not contain a symlink or reparse point")
        if parent == template_dir or parent.parent == parent:
            break
    candidate = candidate.resolve(strict=False)
    if template_dir != candidate and template_dir not in candidate.parents:
        raise ValueError("probe output directory must stay inside the template sandbox")
    current = candidate
    while current != template_dir:
        if current.exists() and _is_link_like(current):
            raise ValueError("probe output directory may not contain a symlink or reparse point")
        current = current.parent
    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


def _terminate_process_tree(process: subprocess.Popen[Any]) -> None:
    """Terminate a command and descendants without relying on shell parsing."""
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
            process.terminate()
        except OSError:
            pass
    deadline = time.monotonic() + 0.5
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.01)
    if process.poll() is None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except OSError:
            try:
                process.kill()
            except OSError:
                pass


def _run_command(command: Sequence[str], *, cwd: Path, timeout: float) -> tuple[str, str]:
    """Run an argv-only command with bounded captured output."""
    if not command or any(not isinstance(item, str) or not item for item in command):
        raise ProbeError("invalid probe command")
    try:
        popen_kwargs: dict[str, Any] = {
            "cwd": str(cwd),
            "stdin": subprocess.DEVNULL,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "shell": False,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        else:
            popen_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            list(command),
            **popen_kwargs,
        )
    except OSError as exc:
        raise ProbeError(f"probe command unavailable: {exc}") from exc

    def read_limited(stream: Any) -> tuple[bytes, bool]:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return b"".join(chunks), total > MAX_LOG_BYTES
            total += len(chunk)
            if total <= MAX_LOG_BYTES:
                chunks.append(chunk)
            else:
                _terminate_process_tree(process)
                return b"".join(chunks), True

    from threading import Thread

    streams: dict[str, tuple[bytes, bool]] = {}

    def capture(name: str, stream: Any) -> None:
        streams[name] = read_limited(stream)

    threads = [
        Thread(target=capture, args=("stdout", process.stdout), daemon=True),
        Thread(target=capture, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_process_tree(process)
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
        for thread in threads:
            thread.join(timeout=1)
        raise ProbeError(f"probe command timed out after {timeout:g}s") from exc
    for thread in threads:
        thread.join(timeout=1)
    if any(thread.is_alive() for thread in threads):
        _terminate_process_tree(process)
        for thread in threads:
            thread.join(timeout=1)
        raise ProbeError("probe command output reader did not terminate")
    stdout_raw, stdout_over = streams.get("stdout", (b"", False))
    stderr_raw, stderr_over = streams.get("stderr", (b"", False))
    if stdout_over or stderr_over or len(stdout_raw) + len(stderr_raw) > MAX_LOG_BYTES:
        raise ProbeError("probe command output exceeded the safety limit")
    stdout = _bounded_text(stdout_raw)
    stderr = _bounded_text(stderr_raw)
    if process.returncode != 0:
        detail = stderr or stdout or f"exit code {process.returncode}"
        raise ProbeError(f"probe command failed: {_bounded_text(detail)}")
    return stdout, stderr


def _find_node_project(start: Path) -> Path | None:
    try:
        current = start.resolve(strict=True)
    except OSError:
        return None
    if TRUSTED_PROJECT_ROOT not in (current, *current.parents):
        return None
    while True:
        remotion = current / "node_modules" / "remotion"
        scoped_remotion = current / "node_modules" / "@remotion"
        if (
            (remotion.exists() and not _is_link_like(remotion))
            or (scoped_remotion.exists() and not _is_link_like(scoped_remotion))
        ):
            return current
        if current == TRUSTED_PROJECT_ROOT or current.parent == current:
            return None
        current = current.parent


def _trusted_executable(name: str) -> str | None:
    if name in _TRUSTED_EXECUTABLES:
        return _TRUSTED_EXECUTABLES[name]
    configured = os.environ.get(f"HUANYU_{name.upper().replace('.', '_')}_PATH")
    located = configured or shutil.which(name)
    if not located:
        _TRUSTED_EXECUTABLES[name] = None
        return None
    candidate = Path(located)
    if _is_link_like(candidate):
        return None
    try:
        candidate = candidate.resolve(strict=True)
    except OSError:
        _TRUSTED_EXECUTABLES[name] = None
        return None
    value = str(candidate) if candidate.is_file() else None
    _TRUSTED_EXECUTABLES[name] = value
    return value


def _real_render_runner(request: ProbeRequest, *, timeout: float) -> ProbeExecution:
    """Render a generated component through the local Remotion CLI."""
    project_root = _find_node_project(request.template_path.parent)
    npx = _trusted_executable("npx") or _trusted_executable("npx.cmd")
    if project_root is None or npx is None:
        raise ProbeError("Remotion dependencies are unavailable for headless probe")

    source_copy = request.output_dir / "template.tsx"
    entry = request.output_dir / "entry.tsx"
    output = request.output_dir / "probe.mp4"
    if _is_link_like(source_copy) or _is_link_like(entry) or _is_link_like(output):
        raise ProbeError("probe output path is unsafe")
    if request.source_bytes is None:
        raise ProbeError("probe request is missing the validated template source")
    source_copy.write_bytes(request.source_bytes)
    entry.write_text(
        'import React from "react";\n'
        'import { Composition, registerRoot } from "remotion";\n'
        'import Template from "./template";\n\n'
        'const Root: React.FC = () => (\n'
        '  <Composition id="Probe" component={Template} durationInFrames={30} fps={30} width={320} height={180} />\n'
        ');\n\n'
        'registerRoot(Root);\n',
        encoding="utf-8",
    )
    command = (
        npx,
        "--no-install",
        "remotion",
        "render",
        str(entry),
        "Probe",
        str(output),
        "--frames=0-29",
        "--overwrite",
    )
    stdout, stderr = _run_command(command, cwd=project_root, timeout=timeout)
    if not output.is_file():
        raise ProbeError("Remotion completed without producing a video")
    if output.stat().st_size > MAX_OUTPUT_BYTES:
        raise ProbeError("render output exceeded the safety limit")
    ffmpeg = _trusted_executable("ffmpeg")
    if not ffmpeg:
        raise ProbeError("ffmpeg is unavailable to inspect rendered frames")
    extract_command = (
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(output),
        "-frames:v",
        str(FRAME_COUNT),
        str(request.output_dir / "frame-%02d.png"),
    )
    extract_stdout, extract_stderr = _run_command(extract_command, cwd=request.output_dir, timeout=timeout)
    frame_paths = tuple(sorted(request.output_dir.glob("frame-*.png")))
    return ProbeExecution(
        frame_paths=frame_paths,
        output_path=output,
        command=command + ("--extract-frames",),
        stdout=_bounded_text(stdout + extract_stdout),
        stderr=_bounded_text(stderr + extract_stderr),
    )


def _coerce_execution(value: Any) -> ProbeExecution:
    if isinstance(value, ProbeExecution):
        return value
    if isinstance(value, Mapping):
        raw_frames = value.get("frame_paths", ())
        return ProbeExecution(
            frame_paths=tuple(Path(item) for item in raw_frames),
            output_path=Path(value["output_path"]) if value.get("output_path") else None,
            command=tuple(value.get("command", ())),
            stdout=_bounded_text(value.get("stdout", "")),
            stderr=_bounded_text(value.get("stderr", "")),
        )
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return ProbeExecution(frame_paths=tuple(Path(item) for item in value))
    raise ProbeError("render runner returned an invalid execution result")


def _visible_and_motion(frame_paths: Sequence[Path]) -> tuple[int, int]:
    if len(frame_paths) != FRAME_COUNT:
        raise ProbeError(f"probe must produce exactly {FRAME_COUNT} frames")
    visible_counts: list[int] = []
    previous_bytes: bytes | None = None
    previous_size: tuple[int, int] | None = None
    total_pixels = 0
    moving_pixels = 0
    for path in frame_paths:
        if _is_link_like(path) or not path.is_file():
            raise ProbeError("probe frame path is missing or unsafe")
        if path.stat().st_size > MAX_OUTPUT_BYTES // FRAME_COUNT:
            raise ProbeError("probe frame exceeded the safety limit")
        try:
            with Image.open(path) as image:
                width, height = image.size
                if width <= 0 or height <= 0 or width > MAX_FRAME_WIDTH or height > MAX_FRAME_HEIGHT:
                    raise ProbeError("probe frame dimensions exceed safety limits")
                frame_pixels = width * height
                if frame_pixels > MAX_FRAME_PIXELS:
                    raise ProbeError("probe frame pixel count exceeds safety limits")
                total_pixels += frame_pixels
                if total_pixels > MAX_TOTAL_FRAME_PIXELS:
                    raise ProbeError("total probe frame pixels exceed safety limits")
                rgba = image.convert("RGBA")
                visible = sum(
                    1
                    for red, green, blue, alpha in rgba.getdata()
                    if alpha > 0 and (red or green or blue)
                )
                current_bytes = rgba.tobytes()
                if previous_bytes is not None:
                    if previous_size != (width, height):
                        raise ProbeError("probe frames have inconsistent dimensions")
                    moving_pixels += sum(
                        previous_bytes[offset : offset + 4] != current_bytes[offset : offset + 4]
                        for offset in range(0, len(current_bytes), 4)
                    )
                previous_bytes = current_bytes
                previous_size = (width, height)
                visible_counts.append(visible)
        except ProbeError:
            raise
        except (OSError, ValueError) as exc:
            raise ProbeError(f"probe frame is not a valid image: {path.name}") from exc
    if not any(visible_counts):
        raise ProbeError("rendered frames are all black or transparent; no non-transparent pixels found")
    if any(count == 0 for count in visible_counts):
        raise ProbeError("rendered frames contain an empty or fully transparent frame")
    if moving_pixels == 0:
        raise ProbeError("rendered frames contain no valid motion pixels")
    return sum(visible_counts), moving_pixels


def _safe_frame_paths(frame_paths: Sequence[Path], output_dir: Path) -> tuple[Path, ...]:
    if len(frame_paths) > FRAME_COUNT:
        raise ProbeError(f"probe produced more than {FRAME_COUNT} frames")
    safe: list[Path] = []
    for raw_path in frame_paths:
        path = Path(raw_path)
        if _is_link_like(path):
            raise ProbeError("probe frame path may not be a symlink or reparse point")
        resolved = path.resolve(strict=False)
        if resolved != output_dir and output_dir not in resolved.parents:
            raise ProbeError("probe frame path escaped the output directory")
        safe.append(resolved)
    return tuple(safe)


def _new_probe_output_dir(base_dir: Path, template_id: str) -> Path:
    try:
        created = Path(tempfile.mkdtemp(prefix=f".{template_id}-", dir=base_dir))
    except OSError as exc:
        raise ProbeError(f"unable to create isolated probe directory: {exc}") from exc
    return _assert_safe_output_dir(created, base_dir)


def _prune_probe_outputs(base_dir: Path, template_id: str) -> None:
    """Keep a small diagnostic history so repeated probes cannot fill disk."""
    try:
        candidates = [
            item for item in base_dir.iterdir()
            if item.is_dir() and item.name.startswith(f".{template_id}-") and not _is_link_like(item)
        ]
        candidates.sort(key=lambda item: item.stat().st_mtime, reverse=True)
        for stale in candidates[MAX_RETAINED_PROBE_DIRS:]:
            if _is_link_like(stale):
                continue
            shutil.rmtree(stale, ignore_errors=False)
    except OSError:
        # Retention is hygiene only; never turn a completed probe into a
        # failure because an old diagnostic directory is busy.
        return


def _audit_probe_output(output_dir: Path) -> None:
    file_count = 0
    total_bytes = 0
    try:
        for entry in output_dir.rglob("*"):
            if _is_link_like(entry):
                raise ProbeError("probe output contains a symlink or reparse point")
            if not entry.is_file():
                continue
            file_count += 1
            if file_count > MAX_PROBE_FILES:
                raise ProbeError("probe output contains too many files")
            total_bytes += entry.stat().st_size
            if total_bytes > MAX_OUTPUT_BYTES:
                raise ProbeError("probe output exceeded the safety limit")
    except OSError as exc:
        raise ProbeError(f"unable to inspect probe output: {exc}") from exc


def _state_paths(template_path: Path) -> tuple[Path, Path]:
    status_file = template_path.with_name(template_path.name + ".probe.json")
    error_log = template_path.with_name(template_path.stem + ".probe-error.log")
    return status_file, error_log


def _assert_safe_state_path(path: Path) -> None:
    if _is_link_like(path):
        raise ProbeError("probe state path may not be a symlink or reparse point")
    unresolved = path.absolute()
    for parent in (unresolved, *unresolved.parents):
        if _is_link_like(parent):
            raise ProbeError("probe state path may not contain a symlink or reparse point")
        if parent.parent == parent:
            break


def _write_probe_state(result: ProbeResult) -> None:
    if result.status_file is None:
        return
    _assert_safe_state_path(result.status_file)
    payload = {
        "template_id": result.template_id,
        "status": result.status,
        "passed": result.passed,
        "frame_count": result.frame_count,
        "moving_pixels": result.moving_pixels,
        "source": result.source,
        "source_hash": result.source_hash,
        "error": _bounded_text(result.error),
        # Persist only an artifact name; absolute workspace paths can disclose
        # usernames and repository layout through the sidecar.
        "error_log": result.error_log.name if result.error_log else None,
        "diagnostics": list(result.diagnostics),
    }
    _atomic_write_text(result.status_file, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _atomic_write_text(path: Path, content: str) -> None:
    """Publish bounded probe metadata without leaving a partial sidecar."""
    _assert_safe_state_path(path)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _persist_failure(error_log: Path, status_file: Path, result: ProbeResult) -> tuple[str, ...]:
    """Best-effort failure receipt; report persistence errors without escaping."""
    diagnostics: list[str] = []
    try:
        _assert_safe_state_path(error_log)
        _atomic_write_text(error_log, result.error + "\n")
    except Exception as exc:
        diagnostics.append(f"failure error-log persistence failed: {_bounded_text(exc)}")
    try:
        _write_probe_state(result)
    except Exception as exc:
        diagnostics.append(f"failure status persistence failed: {_bounded_text(exc)}")
    return tuple(diagnostics)


def _source_reference(path: Path, trusted_root: Path) -> str:
    relative = path.relative_to(trusted_root).as_posix()
    prefix = "templates/synthesized" if trusted_root == DEFAULT_TRUSTED_ROOT else "generated"
    return f"{prefix}/{relative}"


def _registry_entry(template: SynthesizedTemplate, *, source_hash: str, source: str) -> dict[str, Any]:
    props = {name: {"type": "string"} for name in template.props}
    return {
        "id": template.template_id,
        "name": template.template_id,
        "engine": template.engine,
        "engine_version": "local-generated",
        "source": source,
        "source_hash": source_hash,
        "license": "Proprietary-Generated",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [1.0, 60.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": [template.style_pack],
        "shot_grammar": {
            "visual_role": "generated_motion",
            "camera_motion": "parameterized",
            "motion_dynamics": "frame_interpolated",
            "narrative_focus": "generated_template",
        },
        "props_schema": props,
        "status": "approved",
        "registry_source": "render_probe",
    }


class RenderProbe:
    """Execute and gate a bounded 30-frame render."""

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        register: bool = True,
    ) -> None:
        if timeout <= 0 or timeout > 300:
            raise ValueError("timeout must be between 0 and 300 seconds")
        self._runner: Callable[[ProbeRequest], Any] | None = None
        self._timeout = timeout
        self._register = register
        self._trusted_root = DEFAULT_TRUSTED_ROOT

    def probe(self, template: SynthesizedTemplate, *, output_dir: str | Path | None = None) -> ProbeResult:
        template_id = getattr(template, "template_id", "")
        if not isinstance(template_id, str):
            return self._probe_unlocked(template, output_dir=output_dir)
        with _probe_lock(template_id):
            return self._probe_unlocked(template, output_dir=output_dir)

    def _probe_unlocked(self, template: SynthesizedTemplate, *, output_dir: str | Path | None = None) -> ProbeResult:
        path, template_id = _assert_safe_template(template, self._trusted_root)
        default_output = path.parent / ".render-probe" / template_id
        output_base = _assert_safe_output_dir(Path(output_dir) if output_dir is not None else default_output, path.parent)
        destination = _new_probe_output_dir(output_base, template_id)
        status_file, error_log = _state_paths(path)
        command: tuple[str, ...] = ()
        execution: ProbeExecution | None = None
        diagnostics: list[str] = []
        source_hash = ""
        source_reference = _source_reference(path, self._trusted_root)
        try:
            # Read and hash the exact file that the Remotion runner will copy.
            # The generated object's cached source is not a trusted execution
            # input and may have diverged from the file on disk.
            before_stat = path.stat()
            source_bytes = path.read_bytes()
            after_stat = path.stat()
            if _is_link_like(path) or (before_stat.st_ino, before_stat.st_size) != (after_stat.st_ino, after_stat.st_size):
                raise ProbeError("template changed while it was being read")
            source_hash = hashlib.sha256(source_bytes).hexdigest()
            request = ProbeRequest(path, template_id, destination, source_bytes=source_bytes)
            if getattr(template, "engine", "remotion").lower() != "remotion":
                raise ProbeError("render probe supports Remotion templates only")
            if self._runner is None:
                try:
                    validate_typescript_source(source_bytes.decode("utf-8"), filename=path.name)
                except RuntimeError as exc:
                    parser_error = _bounded_text(exc)
                    if "unavailable" in parser_error.lower() or "not found" in parser_error.lower():
                        diagnostics.append(f"TypeScript parser unavailable: {parser_error}")
                    else:
                        raise ProbeError(f"TypeScript validation failed: {parser_error}") from exc
                except (TypeError, ValueError) as exc:
                    raise ProbeError(f"TypeScript validation failed: {_bounded_text(exc)}") from exc
                execution = _real_render_runner(request, timeout=self._timeout)
            else:
                execution = _coerce_execution(self._runner(request))
            command = execution.command
            _audit_probe_output(destination)
            safe_frames = _safe_frame_paths(execution.frame_paths, destination)
            _visible_pixels, moving_pixels = _visible_and_motion(safe_frames)
            latest_bytes = path.read_bytes()
            latest_hash = hashlib.sha256(latest_bytes).hexdigest()
            if _is_link_like(path) or latest_hash != source_hash:
                raise ProbeError("template changed during probe")
            result = ProbeResult(
                template_id=template_id,
                status="approved",
                passed=True,
                frame_count=FRAME_COUNT,
                moving_pixels=moving_pixels,
                output_dir=destination,
                source=source_reference,
                source_hash=source_hash,
                status_file=status_file,
                command=command,
                diagnostics=tuple(diagnostics),
            )
            # Persist the approved receipt before changing the registry.  If
            # persistence fails, control reaches the failure path and no
            # production entry can be created.
            _write_probe_state(result)
            if self._register:
                from lib.broll_registry import _issue_probe_receipt, get_template, register_dynamic_template

                try:
                    entry = _registry_entry(template, source_hash=source_hash, source=source_reference)
                    register_dynamic_template(
                        entry,
                        receipt=_issue_probe_receipt(entry),
                    )
                except ValueError:
                    existing = get_template(template_id)
                    if (
                        not existing
                        or existing.get("status") != "approved"
                        or existing.get("registry_source") != "render_probe"
                        or existing.get("source") != entry["source"]
                        or existing.get("source_hash") != source_hash
                    ):
                        raise
            _prune_probe_outputs(output_base, template_id)
            return result
        except Exception as exc:
            error = _sanitized_error(exc, template_path=path, output_dir=destination)
            result = ProbeResult(
                template_id=template_id,
                status="draft_failed",
                passed=False,
                frame_count=len(execution.frame_paths) if execution is not None else 0,
                moving_pixels=0,
                output_dir=destination,
                source=source_reference,
                source_hash=source_hash,
                error=error,
                error_log=error_log,
                status_file=status_file,
                command=command,
                diagnostics=tuple(diagnostics),
            )
            persistence_diagnostics = _persist_failure(error_log, status_file, result)
            if persistence_diagnostics:
                result = replace(result, diagnostics=tuple(diagnostics) + persistence_diagnostics)
            _prune_probe_outputs(output_base, template_id)
            return result


def run_render_probe(
    template: SynthesizedTemplate,
    *,
    output_dir: str | Path | None = None,
    timeout: float = 60.0,
    register: bool = True,
) -> ProbeResult:
    """Run the quality gate for one synthesized template."""
    return RenderProbe(
        timeout=timeout,
        register=register,
    ).probe(template, output_dir=output_dir)


def probe_synthesized_template(
    template: SynthesizedTemplate,
    *,
    output_dir: str | Path | None = None,
    timeout: float = 60.0,
    register: bool = True,
) -> ProbeResult:
    """Run a production probe using the fixed synthesized-template root."""
    return run_render_probe(
        template,
        output_dir=output_dir,
        timeout=timeout,
        register=register,
    )


def _probe_synthesized_template_for_tests(
    template: SynthesizedTemplate,
    *,
    runner: Callable[[ProbeRequest], Any] | None = None,
    output_dir: str | Path | None = None,
    timeout: float = 60.0,
    register: bool = True,
    trusted_root: str | Path | None = None,
    allow_injected_runner: bool = False,
) -> ProbeResult:
    """Test-only seam; production callers cannot inject a fake renderer."""
    if not _is_test_process():
        raise RuntimeError("injected render probes are available only from the test runner")
    if runner is not None and register and not allow_injected_runner:
        raise ValueError("injected runner cannot register templates without explicit allow_injected_runner")
    probe = RenderProbe(
        timeout=timeout,
        register=register,
    )
    probe._runner = runner
    probe._trusted_root = Path(trusted_root or DEFAULT_TRUSTED_ROOT).resolve()
    return probe.probe(template, output_dir=output_dir)


def _probe_synthesized_template_internal(
    template: SynthesizedTemplate,
    *,
    runner: Callable[[ProbeRequest], Any] | None = None,
    output_dir: str | Path | None = None,
    timeout: float = 60.0,
    register: bool = True,
    trusted_root: str | Path | None = None,
) -> ProbeResult:
    """Trusted integration seam used by TemplateSynthesizer."""
    probe = RenderProbe(
        timeout=timeout,
        register=register,
    )
    probe._runner = runner
    probe._trusted_root = Path(trusted_root or DEFAULT_TRUSTED_ROOT).resolve()
    return probe.probe(template, output_dir=output_dir)


__all__ = [
    "FRAME_COUNT",
    "FPS",
    "ProbeError",
    "ProbeExecution",
    "ProbeRequest",
    "ProbeResult",
    "RenderProbe",
    "probe_synthesized_template",
    "run_render_probe",
]
