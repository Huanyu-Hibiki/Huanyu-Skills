"""Tests for scripts/inventory.py — agent/skill enumeration (task 6).

Covers: mini-yaml parsing of the frozen agents.yaml schema subset,
installed detection, skill enumeration, description reading, size_kb,
--agent filtering, CLI stdout-as-JSON contract, and failure exit codes.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures" / "agents-tree"
FIXTURE_YAML = FIXTURES_DIR / "agents-tree.yaml"

sys.path.insert(0, str(SCRIPTS_DIR))

import inventory  # noqa: E402


def run_cli(yaml_path, *extra_args):
    """Run inventory.py as a subprocess and return the completed process."""
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "inventory.py"), "--agents", str(yaml_path), *extra_args],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )


def build(yaml_path=FIXTURE_YAML, agent_filter=None):
    """Build the inventory dict in-process."""
    return inventory.build_inventory(Path(yaml_path), agent_filter=agent_filter)


def agent_entry(result, name):
    return next(a for a in result["agents"] if a["name"] == name)


def skill_entry(result, agent_name, skill_name):
    agent = agent_entry(result, agent_name)
    return next(s for s in agent["skills"] if s["name"] == skill_name)


def test_fake_agents_enumerated_with_expected_skills():
    result = build()

    opencode = agent_entry(result, "fake-opencode")
    assert opencode["installed"] is True
    assert [s["name"] for s in opencode["skills"]] == ["alpha-skill", "beta-skill"]

    claude = agent_entry(result, "fake-claude")
    assert claude["installed"] is True
    assert sorted(s["name"] for s in claude["skills"]) == [
        "alpha-skill",
        "broken-frontmatter",
        "good-skill",
        "long-desc",
        "name-mismatch",
        "no-manifest",
    ]


def test_not_installed_agent_marked_with_empty_skills():
    result = build()

    missing = agent_entry(result, "not-installed-agent")
    assert missing["installed"] is False
    assert missing["skills"] == []
    assert missing["path"]  # still reports the expected path
    # Not an error: the other agents are still enumerated.
    assert len(result["agents"]) == 3


def test_agent_filter_cli_returns_only_named_agent():
    proc = run_cli(FIXTURE_YAML, "--agent", "fake-claude")

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert [a["name"] for a in payload["agents"]] == ["fake-claude"]
    assert len(payload["agents"][0]["skills"]) == 6


def test_description_and_desc_len_reading():
    result = build()

    alpha = skill_entry(result, "fake-opencode", "alpha-skill")
    expected = (
        "Healthy fixture skill in the fake-opencode tree, used to verify "
        "inventory enumeration and cross-agent duplicate detection."
    )
    assert alpha["description"] == expected
    assert alpha["desc_len"] == len(expected)

    # No SKILL.md at all -> nulls.
    no_manifest = skill_entry(result, "fake-claude", "no-manifest")
    assert no_manifest["description"] is None
    assert no_manifest["desc_len"] is None

    # SKILL.md exists but frontmatter is unterminated -> nulls.
    broken = skill_entry(result, "fake-claude", "broken-frontmatter")
    assert broken["description"] is None
    assert broken["desc_len"] is None


def test_size_kb_positive_and_one_decimal():
    result = build()

    for agent_name in ("fake-opencode", "fake-claude"):
        for skill in agent_entry(result, agent_name)["skills"]:
            assert isinstance(skill["size_kb"], (int, float))
            assert skill["size_kb"] > 0
            assert round(skill["size_kb"], 1) == skill["size_kb"]


def test_bad_yaml_schema_violation_fails(tmp_path):
    # CLI contract: unknown top-level key -> non-zero exit + error JSON.
    bad = tmp_path / "bad.yaml"
    bad.write_text("foo: bar\n", encoding="utf-8")
    proc = run_cli(bad)

    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert "error" in payload

    # Unit level: unsupported key inside an entry -> parse error.
    nested = tmp_path / "nested.yaml"
    nested.write_text(
        "agents:\n"
        "  - name: x\n"
        "    enabled: true\n"
        "    extra: 1\n"
        "    paths:\n"
        "      - ./x\n",
        encoding="utf-8",
    )
    with pytest.raises(inventory.YamlParseError):
        inventory.parse_agents_yaml(nested.read_text(encoding="utf-8"))


def test_missing_yaml_path_fails():
    proc = run_cli(PROJECT_ROOT / "tests" / "fixtures" / "agents-tree" / "no-such.yaml")

    assert proc.returncode != 0
    payload = json.loads(proc.stdout)
    assert "error" in payload


def test_cli_smoke_stdout_is_single_json_object():
    proc = run_cli(FIXTURE_YAML)

    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert set(payload) == {"agents", "duplicates", "health_issues"}
    assert len(payload["agents"]) == 3
    # Task 6 scope: placeholders for task 7.
    assert payload["duplicates"] == []
    assert payload["health_issues"] == []


def test_home_prefix_paths_expanded_to_absolute(tmp_path, monkeypatch):
    """`~/...` and `%USERPROFILE%/...` path prefixes must expand to absolute paths
    (via USERPROFILE), with existence detection still correct."""
    home = tmp_path / "home"
    agent_dir = home / "agent-a"
    skill_dir = agent_dir / "skill-one"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: skill-one\ndescription: tmp skill under a fake home.\n---\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("USERPROFILE", str(home))

    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "agents:\n"
        "  - name: tilde-agent\n"
        "    enabled: true\n"
        "    paths:\n"
        "      - ~/agent-a\n"
        "  - name: envvar-agent\n"
        "    enabled: true\n"
        "    paths:\n"
        "      - %USERPROFILE%/agent-a\n"
        "  - name: envvar-backslash-missing\n"
        "    enabled: true\n"
        "    paths:\n"
        "      - %USERPROFILE%\\no-such-dir\n",
        encoding="utf-8",
    )

    result = build(registry)

    for agent_name in ("tilde-agent", "envvar-agent"):
        entry = agent_entry(result, agent_name)
        assert entry["installed"] is True
        assert Path(entry["path"]).is_absolute()
        assert Path(entry["path"]).exists()
        assert [s["name"] for s in entry["skills"]] == ["skill-one"]

    missing = agent_entry(result, "envvar-backslash-missing")
    assert missing["installed"] is False
    # Expanded even though the directory does not exist.
    assert Path(missing["path"]).is_absolute()
    assert missing["path"] == (home / "no-such-dir").resolve().as_posix()
    assert not Path(missing["path"]).exists()


def test_disabled_agent_skipped(tmp_path):
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "agents:\n"
        f"  - name: ghost\n"
        "    enabled: false\n"
        "    paths:\n"
        f"      - {FIXTURES_DIR.as_posix()}/fake-opencode\n"
        f"  - name: live\n"
        "    enabled: true\n"
        "    paths:\n"
        f"      - {FIXTURES_DIR.as_posix()}/fake-claude\n",
        encoding="utf-8",
    )

    result = build(registry)
    assert [a["name"] for a in result["agents"]] == ["live"]
