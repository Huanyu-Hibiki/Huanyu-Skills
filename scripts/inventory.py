"""inventory.py — enumerate agents and their installed skills as JSON.

CLI: python scripts/inventory.py --agents <yaml> [--agent <name>] [--json]
stdout is always a single JSON object; exit code 0 on success, non-zero with
an {"error": "..."} JSON body on failure.

Task 7 scope: per-skill health checks (has_skill_md / frontmatter_ok /
health_issues, codes frozen in shared-references/skill-anatomy.md §3) and
cross-agent duplicate detection (duplicates).
"""

from __future__ import annotations

import argparse
import json
import os
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

    agents_out: list[dict] = []
    health_issues: list[dict] = []
    for spec in specs:
        if not spec["enabled"]:
            continue
        agent, issues = _enumerate_agent(spec, yaml_path.parent)
        agents_out.append(agent)
        health_issues.extend(issues)
    return {
        "agents": agents_out,
        "duplicates": _find_duplicates(agents_out),
        "health_issues": health_issues,
    }


def _expand_path(raw: str) -> str:
    """Expand `~/...` and `%USERPROFILE%/...` (any `%VAR%`) prefixes; other
    absolute/relative paths pass through unchanged."""
    return os.path.expanduser(os.path.expandvars(raw))


def _enumerate_agent(spec: dict, base_dir: Path) -> tuple[dict, list[dict]]:
    candidates = []
    for p in spec["paths"]:
        expanded = _expand_path(p)
        candidates.append(
            Path(expanded) if Path(expanded).is_absolute() else (base_dir / expanded)
        )
    existing = [p for p in candidates if p.is_dir()]
    root = (existing[0] if existing else candidates[0]).resolve()
    skills, issues = _enumerate_skills(root) if existing else ([], [])
    agent = {
        "name": spec["name"],
        "path": root.as_posix(),
        "installed": bool(existing),
        "skills": skills,
    }
    return agent, issues


def _enumerate_skills(agent_dir: Path) -> tuple[list[dict], list[dict]]:
    skills: list[dict] = []
    issues: list[dict] = []
    for child in sorted(agent_dir.iterdir()):
        if not child.is_dir():
            continue
        fm = _parse_frontmatter(child)
        description = fm["description"]
        entry = {
            "name": child.name,
            "path": child.resolve().as_posix(),
            "description": description,
            "size_kb": _dir_size_kb(child),
            "desc_len": len(description) if description is not None else None,
            "has_skill_md": fm["has_skill_md"],
            "frontmatter_ok": fm["frontmatter_ok"],
        }
        skills.append(entry)
        issues.extend(_health_issues(child.name, entry, fm))
    return skills, issues


def _parse_frontmatter(skill_dir: Path) -> dict:
    """Inspect SKILL.md frontmatter health.

    Returns a dict with:
        has_skill_md:   SKILL.md exists
        frontmatter_ok: SKILL.md exists, fences closed, name+description keys present
        fm_name:        frontmatter `name` value (None if absent/unparseable)
        description:    frontmatter `description` value (None if absent/unparseable)
    """
    manifest = skill_dir / "SKILL.md"
    info = {
        "has_skill_md": manifest.is_file(),
        "frontmatter_ok": False,
        "fm_name": None,
        "description": None,
    }
    if not info["has_skill_md"]:
        return info
    try:
        lines = manifest.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return info
    if not lines or lines[0].strip() != "---":
        return info
    body: list[str] = []
    closed = False
    for line in lines[1:]:
        if line.strip() == "---":
            closed = True
            break
        body.append(line)
    if not closed:  # unterminated fence -> nothing parseable
        return info
    keys: dict[str, str] = {}
    for line in body:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, sep, value = stripped.partition(":")
        if sep:
            keys[key.strip()] = value.strip()
    info["fm_name"] = keys.get("name") or None
    info["description"] = keys.get("description") or None
    if "name" not in keys or "description" not in keys:
        return info  # required key(s) missing
    info["frontmatter_ok"] = True
    return info


def _health_issues(skill_name: str, entry: dict, fm: dict) -> list[dict]:
    """Health issues for one skill entry; codes frozen in skill-anatomy.md §3."""

    def issue(code: str, detail: str) -> dict:
        return {"skill": skill_name, "issue": code, "detail": detail}

    if not entry["has_skill_md"]:
        return [issue("missing_skill_md", "目录缺 SKILL.md")]
    if not fm["frontmatter_ok"]:
        return [issue("frontmatter_broken", "frontmatter 围栏未闭合或缺少 name/description 键")]
    issues: list[dict] = []
    if entry["desc_len"] is not None and entry["desc_len"] > 1024:
        issues.append(
            issue("desc_too_long", f"description 长度 {entry['desc_len']} 字符，超过 1024 上限")
        )
    if fm["fm_name"] is not None and fm["fm_name"] != skill_name:
        issues.append(
            issue(
                "name_mismatch",
                f"frontmatter name 为 {fm['fm_name']!r}，与目录名 {skill_name!r} 不一致",
            )
        )
    return issues


def _find_duplicates(agents: list[dict]) -> list[dict]:
    """Group every enumerated skill by name; names installed in >=2 places."""
    by_name: dict[str, list[str]] = {}
    for agent in agents:
        for skill in agent["skills"]:
            by_name.setdefault(skill["name"], []).append(skill["path"])
    return [
        {"name": name, "locations": locations}
        for name, locations in sorted(by_name.items())
        if len(locations) >= 2
    ]


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
