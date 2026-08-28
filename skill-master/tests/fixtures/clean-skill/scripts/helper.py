"""Small helpers for the notes skill: JSON index read/write."""

import json
from pathlib import Path

NOTES_DIR = Path(__file__).resolve().parent.parent / "notes"
INDEX_PATH = NOTES_DIR / "index.json"


def load_index() -> dict:
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    return {"entries": []}


def save_index(index: dict) -> None:
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def add_entry(title: str, filename: str) -> dict:
    index = load_index()
    entry = {"title": title, "filename": filename}
    index["entries"].append(entry)
    save_index(index)
    return entry
