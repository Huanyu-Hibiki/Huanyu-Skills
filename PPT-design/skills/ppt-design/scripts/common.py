"""Shared boundary validation and rendering helpers for PPT design modes."""

from __future__ import annotations

import os
import re
from pathlib import Path
import tempfile


CONFIRMATION_PHRASES = frozenset(
    {
        "确认", "确认设计", "确认并生成", "同意", "批准", "可以制作", "开始制作",
        "confirm", "confirm design", "approve", "approve design",
    }
)


def is_explicit_confirmation(message: str) -> bool:
    if not isinstance(message, str):
        raise TypeError("confirmation must be a string")
    return re.sub(r"\s+", " ", message.strip().lower()) in CONFIRMATION_PHRASES


def clean_text(value: str, label: str, limit: int) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{label} must be a string")
    if any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError(f"{label} contains unsupported control characters")
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} must not be blank")
    if len(cleaned) > limit:
        raise ValueError(f"{label} exceeds the {limit}-character limit")
    return cleaned


def markdown_inline(value: str) -> str:
    value = re.sub(r"[\r\n]+", " ", value)
    return re.sub(r"([\\`*_[\]<>|#])", r"\\\1", value)


def safe_output_dir(output_dir: Path, *, allowed_root: Path | None = None) -> Path:
    if not isinstance(output_dir, Path):
        raise TypeError("output_dir must be a pathlib.Path")
    if ".." in output_dir.parts:
        raise ValueError("output_dir must not contain parent traversal")
    absolute = output_dir.absolute()
    cursor = absolute
    while True:
        if cursor.is_symlink() or _is_reparse_point(cursor):
            raise ValueError("output_dir must not contain symbolic links or junctions")
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    if allowed_root is not None:
        root = safe_output_dir(allowed_root)
        try:
            absolute.relative_to(root)
        except ValueError as exc:
            raise ValueError("output_dir must be within allowed_root") from exc
    return absolute


def _is_reparse_point(path: Path) -> bool:
    """Detect Windows junctions/reparse points without requiring Windows APIs."""

    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except (FileNotFoundError, OSError):
        return False
    return bool(attributes & 0x40000000)  # FILE_ATTRIBUTE_REPARSE_POINT


def persist_design_status(design_path: Path, status: str) -> None:
    """Update only the status field in an already-written design contract."""

    if not isinstance(design_path, Path) or not design_path.is_file() or design_path.is_symlink():
        raise ValueError("design document must be a regular file")
    text = design_path.read_text(encoding="utf-8")
    updated, count = re.subn(
        r"(?m)^status:\s*[^\r\n]+$",
        f"status: {status}",
        text,
        count=1,
    )
    if count != 1:
        raise ValueError("design document has no status field")
    atomic_write_text(design_path, updated)


def atomic_write_text(path: Path, content: str) -> None:
    """Write UTF-8 text through a same-directory temporary file and replace."""

    if not isinstance(path, Path):
        raise TypeError("path must be a pathlib.Path")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
