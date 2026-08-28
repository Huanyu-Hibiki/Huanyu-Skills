"""inventory.py — enumerate agents and their installed skills as JSON.

CLI: python scripts/inventory.py --agents <yaml> [--agent <name>] [--json]
stdout is always a single JSON object; exit code 0 on success, non-zero with
an {"error": "..."} JSON body on failure.

Task 6 scope: enumeration only (duplicates/health_issues are placeholder
empty arrays; health analysis lands in task 7).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class InventoryError(Exception):
    """Unrecoverable inventory failure (missing yaml, unreadable file)."""


class YamlParseError(InventoryError):
    """agents.yaml violates the supported fixed-schema subset."""


def parse_agents_yaml(text: str) -> list[dict]:
    """Parse the agents.yaml schema subset.

    Supported grammar (anything else raises YamlParseError):
        agents:
          - name: <string>          (2-space indent)
            enabled: true|false     (4-space indent)
            paths:                  (4-space indent)
              - <path>              (6-space indent)

    Blank lines and standalone '#' comment lines (any indent) are skipped.
    """
    agents: list[dict] = []
    entry: dict | None = None
    in_paths = False
    saw_agents_key = False

    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))

        if indent == 0:
            if saw_agents_key or stripped != "agents:":
                raise YamlParseError(
                    f"line {lineno}: expected a single top-level 'agents:' key, got {stripped!r}"
                )
            saw_agents_key = True
            entry = None
            in_paths = False
        elif not saw_agents_key:
            raise YamlParseError(f"line {lineno}: content before 'agents:' key: {stripped!r}")
        elif indent == 2:
            if not stripped.startswith("- ") or not stripped[2:].startswith("name:"):
                raise YamlParseError(
                    f"line {lineno}: agent entry must start with '- name: <value>', got {stripped!r}"
                )
            if entry is not None:
                _finalize_entry(entry, f"line {lineno}")
                agents.append(entry)
            entry = {"name": stripped[2:][len("name:"):].strip(), "enabled": None, "paths": []}
            in_paths = False
        elif indent == 4:
            if entry is None:
                raise YamlParseError(f"line {lineno}: key outside of an agent entry: {stripped!r}")
            key, sep, value = stripped.partition(":")
            value = value.strip()
            if key == "enabled":
                if value not in ("true", "false"):
                    raise YamlParseError(f"line {lineno}: 'enabled' must be true/false, got {value!r}")
                entry["enabled"] = value == "true"
                in_paths = False
            elif key == "paths":
                if value:
                    raise YamlParseError(f"line {lineno}: 'paths:' must be a nested list, got {value!r}")
                in_paths = True
            else:
                raise YamlParseError(
                    f"line {lineno}: unsupported key {key!r} (only name/enabled/paths)"
                )
        elif indent == 6:
            if entry is None or not in_paths:
                raise YamlParseError(f"line {lineno}: list item outside a 'paths:' block: {stripped!r}")
            if not stripped.startswith("- "):
                raise YamlParseError(f"line {lineno}: expected '- <path>', got {stripped!r}")
            entry["paths"].append(stripped[2:].strip())
        else:
            raise YamlParseError(f"line {lineno}: unsupported indentation ({indent} spaces): {stripped!r}")

    if entry is not None:
        _finalize_entry(entry, "end of file")
        agents.append(entry)
    return agents


def _finalize_entry(entry: dict, where: str) -> None:
    if not entry["name"]:
        raise YamlParseError(f"agent entry near {where}: 'name' must not be empty")
    if entry["enabled"] is None:
        raise YamlParseError(f"agent {entry['name']!r} near {where}: missing 'enabled' key")
    if not entry["paths"]:
        raise YamlParseError(f"agent {entry['name']!r} near {where}: 'paths' must list at least one path")


def build_inventory(yaml_path: Path, agent_filter: str | None = None) -> dict:
    """Build the full inventory payload from an agents.yaml registry file."""
    try:
        text = yaml_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InventoryError(f"cannot read agents yaml {yaml_path}: {exc}") from exc
    specs = parse_agents_yaml(text)
    if agent_filter is not None:
        specs = [s for s in specs if s["name"] == agent_filter]

    agents_out = [
        _enumerate_agent(spec, yaml_path.parent) for spec in specs if spec["enabled"]
    ]
    return {"agents": agents_out, "duplicates": [], "health_issues": []}


def _enumerate_agent(spec: dict, base_dir: Path) -> dict:
    candidates = [
        Path(p) if Path(p).is_absolute() else (base_dir / p) for p in spec["paths"]
    ]
    existing = [p for p in candidates if p.is_dir()]
    root = (existing[0] if existing else candidates[0]).resolve()
    return {
        "name": spec["name"],
        "path": root.as_posix(),
        "installed": bool(existing),
        "skills": _enumerate_skills(root) if existing else [],
    }


def _enumerate_skills(agent_dir: Path) -> list[dict]:
    skills = []
    for child in sorted(agent_dir.iterdir()):
        if not child.is_dir():
            continue
        description = _read_description(child)
        skills.append(
            {
                "name": child.name,
                "path": child.resolve().as_posix(),
                "description": description,
                "size_kb": _dir_size_kb(child),
                "desc_len": len(description) if description is not None else None,
            }
        )
    return skills


def _read_description(skill_dir: Path) -> str | None:
    """Best-effort read of `description:` from SKILL.md frontmatter; None if unreadable."""
    manifest = skill_dir / "SKILL.md"
    if not manifest.is_file():
        return None
    try:
        lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    body: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        body.append(line)
    else:  # no closing delimiter -> frontmatter unterminated, nothing parseable
        return None
    for line in body:
        if line.strip().startswith("description:"):
            return line.strip()[len("description:"):].strip() or None
    return None


def _dir_size_kb(path: Path) -> float:
    total = 0
    for item in path.rglob("*"):
        if item.is_file():
            try:
                total += item.stat().st_size
            except OSError:
                pass
    return round(total / 1024, 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enumerate agents and their installed skills as JSON."
    )
    parser.add_argument("--agents", required=True, help="path to the agents.yaml registry")
    parser.add_argument("--agent", help="only enumerate the named agent")
    parser.add_argument(
        "--json", action="store_true", help="JSON output (always on; kept for CLI compatibility)"
    )
    args = parser.parse_args(argv)

    yaml_path = Path(args.agents)
    try:
        if not yaml_path.is_file():
            raise InventoryError(f"agents yaml not found: {args.agents}")
        payload = build_inventory(yaml_path, agent_filter=args.agent)
    except InventoryError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
