"""inventory.py — enumerate agents and their installed skills as JSON.

CLI: python scripts/inventory.py --agents <yaml> [--agent <name>] [--json]
stdout is always a single JSON object; exit code 0 on success, non-zero with
an {"error": "..."} JSON body on failure.

Task 7 scope: per-skill health checks (has_skill_md / frontmatter_ok /
health_issues, codes frozen in shared-references/skill-anatomy.md §3) and
cross-agent duplicate detection (duplicates).

Enumeration is two-level (v1 cap): a first-level dir with SKILL.md is the
skill; one without is a collection dir whose second-level SKILL.md-bearing
subdirs are the skills (collection itself exempt — skill-anatomy.md §3.1);
only when no SKILL.md exists within two levels is the dir itself reported
as missing_skill_md.
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


# description length cap, frozen in shared-references/skill-anatomy.md §3.3
# (desc_too_long is raised when len(description) > DESC_MAX_CHARS).
DESC_MAX_CHARS = 1024


def _unquote(value: str) -> str:
    """Strip one pair of matching surrounding quotes from a yaml scalar value
    (e.g. `name: "opencode"` must be stored as opencode, not "opencode")."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


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
            entry = {
                "name": _unquote(stripped[2:][len("name:"):].strip()),
                "enabled": None,
                "paths": [],
            }
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
            entry["paths"].append(_unquote(stripped[2:].strip()))
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
        # utf-8-sig: tolerate (and strip) a leading BOM; plain utf-8 unaffected.
        text = yaml_path.read_text(encoding="utf-8-sig")
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
        for skill_dir in _resolve_skill_dirs(child):
            fm = _parse_frontmatter(skill_dir)
            description = fm["description"]
            entry = {
                "name": skill_dir.name,
                "path": skill_dir.resolve().as_posix(),
                "description": description,
                "size_kb": _dir_size_kb(skill_dir),
                "desc_len": len(description) if description is not None else None,
                "has_skill_md": fm["has_skill_md"],
                "frontmatter_ok": fm["frontmatter_ok"],
            }
            skills.append(entry)
            issues.extend(_health_issues(skill_dir.name, entry, fm))
    return skills, issues


def _resolve_skill_dirs(first_level_dir: Path) -> list[Path]:
    """Two-level enumeration rule (collection exemption frozen in
    shared-references/skill-anatomy.md §3.1):

    - first_level_dir has SKILL.md -> it is the skill (no descent);
    - no SKILL.md but second-level dirs have them -> first_level_dir is a
      collection dir (category-style or step-style): those second-level dirs
      are the skills, the collection itself is exempt (not enumerated, no
      issue);
    - no SKILL.md anywhere within two levels -> first_level_dir stays a
      skill entry reported as missing_skill_md;
    - second-level dirs without SKILL.md are never descended (v1 cap: two
      levels).
    """
    if (first_level_dir / "SKILL.md").is_file():
        return [first_level_dir]
    nested = [
        sub
        for sub in sorted(first_level_dir.iterdir())
        if sub.is_dir() and (sub / "SKILL.md").is_file()
    ]
    return nested if nested else [first_level_dir]


def _parse_frontmatter(skill_dir: Path) -> dict:
    """Inspect SKILL.md frontmatter health.

    Returns a dict with:
        has_skill_md:   SKILL.md exists
        frontmatter_ok: SKILL.md exists, fences closed, name+description keys
                        present with non-empty values
        fm_name:        frontmatter `name` value (None if absent/empty/unparseable)
        description:    frontmatter `description` value (None if absent/empty/unparseable)
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
        # utf-8-sig: tolerate (and strip) a leading BOM before the '---' fence.
        lines = manifest.read_text(encoding="utf-8-sig", errors="replace").splitlines()
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
    # Required key missing OR present with an empty value: either way the
    # skill cannot be routed on (name) or described (description) -> broken.
    if not keys.get("name") or not keys.get("description"):
        return info
    info["frontmatter_ok"] = True
    return info


def _health_issues(skill_name: str, entry: dict, fm: dict) -> list[dict]:
    """Health issues for one skill entry; codes frozen in skill-anatomy.md §3."""

    def issue(code: str, detail: str) -> dict:
        return {"skill": skill_name, "issue": code, "detail": detail}

    if not entry["has_skill_md"]:
        return [issue("missing_skill_md", "目录缺 SKILL.md")]
    if not fm["frontmatter_ok"]:
        return [
            issue(
                "frontmatter_broken",
                "frontmatter 围栏未闭合或 name/description 键缺失/值为空",
            )
        ]
    issues: list[dict] = []
    if entry["desc_len"] is not None and entry["desc_len"] > DESC_MAX_CHARS:
        issues.append(
            issue(
                "desc_too_long",
                f"description 长度 {entry['desc_len']} 字符，超过 {DESC_MAX_CHARS} 上限",
            )
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
    """Group every enumerated skill by name; names installed in >=2 places.

    Locations are deduped first: two agents whose paths resolve to the same
    directory describe one install location, not a duplicate."""
    by_name: dict[str, list[str]] = {}
    for agent in agents:
        for skill in agent["skills"]:
            by_name.setdefault(skill["name"], []).append(skill["path"])
    duplicates: list[dict] = []
    for name, paths in sorted(by_name.items()):
        locations = list(dict.fromkeys(paths))  # dedup, preserve first-seen order
        if len(locations) >= 2:
            duplicates.append({"name": name, "locations": locations})
    return duplicates


def _dir_size_kb(path: Path) -> float:
    """Sum file sizes under `path` without following junctions.

    On Windows (Python 3.12) `Path.is_symlink()` is False for junctions, so
    glob/walk helpers silently descend into them; a junction cycle would then
    double-count sizes or hang. Junction targets are skipped entirely.
    """
    total = 0
    stack: list[str] = [str(path)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if os.path.isjunction(entry.path):
                        continue  # never descend into a junction target
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(entry.path)
                    elif entry.is_file():
                        try:
                            total += entry.stat().st_size
                        except OSError:
                            pass
        except OSError:
            continue  # unreadable subtree: skip, keep the total conservative
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
    except Exception as exc:  # script boundary: any failure -> single error JSON
        print(json.dumps({"error": str(exc) or exc.__class__.__name__}))
        return 1
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
