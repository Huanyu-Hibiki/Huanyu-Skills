#!/usr/bin/env python3
"""Local evidence ledger and validation gate for video workflow skill edits."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / ".skillopt-video"
KINDS = {
    "user_correction", "task_failure", "rework", "missing_guardrail",
    "successful_pattern", "tool_friction", "handoff_gap", "scope_error",
}
SEVERITIES = {"low", "medium", "high", "critical"}
CASE_TYPES = {"normal", "risk", "neighbor"}
SUPPORTED_SUFFIXES = {".md", ".json", ".py"}
MIN_CASES = 3
MAX_CHANGED_LINES = 120
SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\b(?:sk|key)-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"),
    re.compile(r"(?i)(cookie|session)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"\bAKIA[A-Z0-9]{16}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
]


def now() -> datetime:
    return datetime.now().astimezone()


def stamp(prefix: str) -> str:
    return f"{prefix}-{now().strftime('%Y%m%d-%H%M%S-%f')[:-3]}"


def redact(text: str) -> str:
    value = text.strip()
    for pattern in SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value[:2000]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bytes_sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as handle:
        temporary = Path(handle.name)
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def state_dir(args: argparse.Namespace) -> Path:
    return args.state_dir.resolve() if args.state_dir else DEFAULT_STATE


@contextmanager
def exclusive_lock(path: Path):
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise SystemExit(f"operation locked by another process: {path}") from exc
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


def safe_target(value: str) -> Path:
    raw = Path(value)
    target = raw.resolve() if raw.is_absolute() else (ROOT / raw).resolve()
    try:
        target.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit("target must be inside video-production-workflow") from exc
    optimizer = (ROOT / "skills" / "video-skill-optimize").resolve()
    optimizer_script = (ROOT / "scripts" / "video-skill-optimize").resolve()
    if target in {optimizer, optimizer_script} or optimizer in target.parents or optimizer_script in target.parents:
        raise SystemExit("the optimizer cannot optimize itself")
    relative = target.relative_to(ROOT)
    allowed_roots = {"skills", "scripts", "templates", "shared-references", "references"}
    if relative.parts[0] not in allowed_roots or target.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise SystemExit("target must be a supported Markdown, JSON, or Python file in an approved workflow directory")
    if any(part.startswith(".") for part in relative.parts) or target.name.lower().startswith((".env", "cookie")):
        raise SystemExit("sensitive or hidden targets are not allowed")
    return target


def load_evidence(directory: Path) -> list[dict]:
    path = directory / "evidence.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def validate_candidate_text(text: str, target: str) -> list[str]:
    errors: list[str] = []
    if "[TODO" in text:
        errors.append("candidate contains TODO placeholder")
    target_path = Path(target)
    if target_path.name == "SKILL.md":
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
        if not match:
            errors.append("SKILL.md frontmatter is missing")
        else:
            frontmatter = match.group(1)
            if not re.search(r"(?m)^name:\s*\S+", frontmatter):
                errors.append("frontmatter name is missing")
            if not re.search(r"(?m)^description:\s*\S+", frontmatter):
                errors.append("frontmatter description is missing")
    if target_path.name == "SKILL.md" and len(text.splitlines()) > 500:
        errors.append("candidate exceeds 500 lines; move detail to references")
    if target_path.suffix.lower() == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON: {exc}")
    if target_path.suffix.lower() == ".py":
        try:
            compile(text, target, "exec")
        except SyntaxError as exc:
            errors.append(f"invalid Python: {exc}")
    return errors


def decode_candidate(value: bytes) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit("candidate must be UTF-8 text") from exc


def command_record(args: argparse.Namespace) -> None:
    item = {
        "evidence_id": stamp("EVID"),
        "recorded_at": now().isoformat(timespec="seconds"),
        "source": args.source,
        "task_id": redact(args.task_id),
        "skill": redact(args.skill),
        "kind": args.kind,
        "severity": args.severity,
        "summary": redact(args.summary),
        "expected": redact(args.expected),
        "observed": redact(args.observed),
        "project_path": redact(args.project_path or ""),
    }
    append_jsonl(state_dir(args) / "evidence.jsonl", item)
    print(json.dumps(item, ensure_ascii=False, indent=2))


def command_propose(args: argparse.Namespace) -> None:
    directory = state_dir(args)
    target = safe_target(args.target)
    candidate = args.candidate.resolve()
    if not target.is_file() or not candidate.is_file():
        raise SystemExit("target and candidate must be existing files")
    evidence = {item["evidence_id"] for item in load_evidence(directory)}
    missing = sorted(set(args.evidence) - evidence)
    if missing:
        raise SystemExit(f"unknown evidence ids: {', '.join(missing)}")
    selected = [item for item in load_evidence(directory) if item["evidence_id"] in set(args.evidence)]
    has_high_risk = any(item["severity"] in {"high", "critical"} for item in selected)
    if len(selected) < 2 and not has_high_risk and not args.explicit_user_request:
        raise SystemExit("proposal requires repeated evidence, high-risk evidence, or --explicit-user-request")
    proposal_id = stamp("PROP")
    proposal_dir = directory / "proposals" / proposal_id
    proposal_dir.mkdir(parents=True, exist_ok=False)
    baseline_copy = proposal_dir / "baseline.md"
    candidate_copy = proposal_dir / "candidate.md"
    with exclusive_lock(target.with_name(target.name + ".skillopt.lock")):
        baseline_bytes = target.read_bytes()
        baseline_copy.write_bytes(baseline_bytes)
        candidate_copy.write_bytes(candidate.read_bytes())
    baseline_lines = baseline_copy.read_text(encoding="utf-8").splitlines()
    candidate_lines = candidate_copy.read_text(encoding="utf-8").splitlines()
    diff = list(difflib.unified_diff(baseline_lines, candidate_lines, fromfile=str(target), tofile="candidate"))
    changed = sum(1 for line in diff if (line.startswith("+") or line.startswith("-")) and not line.startswith(("+++", "---")))
    (proposal_dir / "change.diff").write_text("\n".join(diff) + "\n", encoding="utf-8")
    payload = {
        "proposal_id": proposal_id,
        "created_at": now().isoformat(timespec="seconds"),
        "status": "staged",
        "target": str(target.relative_to(ROOT)).replace("\\", "/"),
        "baseline_sha256": bytes_sha256(baseline_bytes),
        "candidate_sha256": sha256(candidate_copy),
        "changed_lines": changed,
        "summary": redact(args.summary),
        "evidence_ids": args.evidence,
        "explicit_user_request": args.explicit_user_request,
        "gate": None,
    }
    write_json(proposal_dir / "proposal.json", payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def proposal_paths(directory: Path, proposal_id: str) -> tuple[Path, Path, Path]:
    base = directory / "proposals" / proposal_id
    return base, base / "proposal.json", base / "candidate.md"


def recover_adoption(transaction: Path, proposal_path: Path, proposal: dict, target: Path) -> bool:
    if not transaction.exists():
        return False
    record = read_json(transaction)
    if record.get("proposal_id") != proposal.get("proposal_id"):
        raise SystemExit("transaction does not match proposal")
    target_hash = sha256(target)
    if target_hash == proposal["candidate_sha256"]:
        proposal["status"] = "adopted"
        proposal["adopted_at"] = now().isoformat(timespec="seconds")
        proposal["adopted_sha256"] = target_hash
        proposal["recovered_transaction"] = True
        write_json(proposal_path, proposal)
        transaction.unlink(missing_ok=True)
        return True
    if target_hash != proposal["baseline_sha256"]:
        raise SystemExit("interrupted adoption found an unknown target state; inspect transaction and backup")
    return False


def command_gate(args: argparse.Namespace) -> None:
    directory = state_dir(args)
    base, proposal_path, candidate = proposal_paths(directory, args.proposal)
    if not proposal_path.exists():
        raise SystemExit("proposal not found")
    proposal = read_json(proposal_path)
    evaluation = read_json(args.evaluation.resolve())
    cases = evaluation.get("cases", [])
    candidate_bytes = candidate.read_bytes()
    current_candidate_hash = bytes_sha256(candidate_bytes)
    reasons = validate_candidate_text(decode_candidate(candidate_bytes), proposal["target"])
    if current_candidate_hash != proposal.get("candidate_sha256"):
        reasons.append("candidate changed after proposal creation")
    if evaluation.get("proposal_id") != args.proposal:
        reasons.append("evaluation proposal_id mismatch")
    if not isinstance(cases, list) or len(cases) < MIN_CASES:
        reasons.append(f"requires at least {MIN_CASES} held-out cases")
    training = set(proposal.get("evidence_ids", []))
    baseline_score = 0
    candidate_score = 0
    regressions: list[str] = []
    case_ids: set[str] = set()
    case_types: set[str] = set()
    critical_risk_count = 0
    for case in cases:
        if not isinstance(case, dict):
            reasons.append("each evaluation case must be an object")
            continue
        case_id = str(case.get("case_id", "unnamed"))
        case_type = case.get("case_type")
        if case_id in case_ids:
            reasons.append(f"duplicate case_id: {case_id}")
        case_ids.add(case_id)
        if case_type not in CASE_TYPES:
            reasons.append(f"invalid case_type for {case_id}")
        else:
            case_types.add(case_type)
        if type(case.get("held_out")) is not bool:
            reasons.append(f"held_out must be boolean for {case_id}")
        if type(case.get("critical")) is not bool:
            reasons.append(f"critical must be boolean for {case_id}")
        if type(case.get("baseline_pass")) is not bool:
            reasons.append(f"baseline_pass must be boolean for {case_id}")
        if type(case.get("candidate_pass")) is not bool:
            reasons.append(f"candidate_pass must be boolean for {case_id}")
        source_ids = case.get("source_evidence_ids")
        if not isinstance(source_ids, list) or not all(isinstance(item, str) for item in source_ids):
            reasons.append(f"source_evidence_ids must be a string list for {case_id}")
            source_ids = []
        if not isinstance(case.get("prompt"), str) or not case["prompt"].strip():
            reasons.append(f"missing prompt for {case_id}")
        if not isinstance(case.get("check"), str) or not case["check"].strip():
            reasons.append(f"missing check for {case_id}")
        if case.get("held_out") is not True:
            reasons.append(f"{case_id} is not marked held_out")
        if training.intersection(source_ids):
            reasons.append(f"{case_id} overlaps training evidence")
        baseline_pass = case.get("baseline_pass") is True
        candidate_pass = case.get("candidate_pass") is True
        baseline_score += int(baseline_pass)
        candidate_score += int(candidate_pass)
        if baseline_pass and not candidate_pass:
            regressions.append(case_id)
        if case.get("critical") is True and not candidate_pass:
            reasons.append(f"critical case failed: {case_id}")
        if case_type == "risk" and case.get("critical") is True:
            critical_risk_count += 1
    if candidate_score <= baseline_score:
        reasons.append("candidate does not strictly improve held-out score")
    if regressions:
        reasons.append("regressions: " + ", ".join(regressions))
    missing_types = sorted(CASE_TYPES - case_types)
    if missing_types:
        reasons.append("missing case types: " + ", ".join(missing_types))
    if critical_risk_count == 0:
        reasons.append("at least one risk case must be critical")
    if proposal.get("changed_lines", 0) > MAX_CHANGED_LINES:
        reasons.append(f"changed lines exceed budget {MAX_CHANGED_LINES}")
    passed = not reasons
    gate = {
        "evaluated_at": now().isoformat(timespec="seconds"),
        "passed": passed,
        "baseline_score": baseline_score,
        "candidate_score": candidate_score,
        "case_count": len(cases),
        "reasons": reasons,
        "evaluation_file": str(args.evaluation.resolve()),
        "candidate_sha256": current_candidate_hash,
    }
    proposal["status"] = "gate_passed" if passed else "rejected"
    proposal["gate"] = gate
    shutil.copy2(args.evaluation.resolve(), base / "evaluation.json")
    write_json(proposal_path, proposal)
    print(json.dumps(gate, ensure_ascii=False, indent=2))
    if not passed:
        raise SystemExit(2)


def command_adopt(args: argparse.Namespace) -> None:
    directory = state_dir(args)
    _, proposal_path, candidate = proposal_paths(directory, args.proposal)
    if not proposal_path.exists():
        raise SystemExit("proposal not found")
    proposal = read_json(proposal_path)
    if proposal.get("status") != "gate_passed" or not proposal.get("gate", {}).get("passed"):
        raise SystemExit("proposal has not passed the gate")
    expected_confirmation = f"ADOPT:{args.proposal}:{proposal['candidate_sha256'][:12]}"
    if args.confirm != expected_confirmation:
        raise SystemExit(f"adoption requires --confirm {expected_confirmation} after explicit user approval")
    target = safe_target(proposal["target"])
    candidate_bytes = candidate.read_bytes()
    if bytes_sha256(candidate_bytes) != proposal["candidate_sha256"] or proposal.get("gate", {}).get("candidate_sha256") != proposal["candidate_sha256"]:
        raise SystemExit("candidate changed after gate; rebuild proposal")
    validation_errors = validate_candidate_text(decode_candidate(candidate_bytes), proposal["target"])
    if validation_errors:
        raise SystemExit("candidate validation failed: " + "; ".join(validation_errors))
    backup_dir = directory / "adopted" / args.proposal
    transaction = directory / "transactions" / f"{args.proposal}.json"
    with exclusive_lock(target.with_name(target.name + ".skillopt.lock")):
        if recover_adoption(transaction, proposal_path, proposal, target):
            print(json.dumps({"proposal_id": args.proposal, "target": str(target), "recovered": True}, ensure_ascii=False, indent=2))
            return
        if sha256(target) != proposal["baseline_sha256"]:
            raise SystemExit("target changed after proposal creation; rebuild candidate")
        backup_dir.mkdir(parents=True, exist_ok=transaction.exists())
        backup = backup_dir / target.name
        if not backup.exists():
            shutil.copy2(target, backup)
        write_json(transaction, {
            "proposal_id": args.proposal,
            "status": "replacing",
            "target": str(target),
            "backup": str(backup),
            "baseline_sha256": proposal["baseline_sha256"],
            "candidate_sha256": proposal["candidate_sha256"],
        })
        previous_proposal = json.loads(json.dumps(proposal))
        try:
            with tempfile.NamedTemporaryFile("wb", delete=False, dir=target.parent) as handle:
                temporary = Path(handle.name)
                handle.write(candidate_bytes)
            shutil.copystat(target, temporary)
            if sha256(target) != proposal["baseline_sha256"]:
                temporary.unlink(missing_ok=True)
                raise SystemExit("target changed immediately before replacement; rebuild candidate")
            os.replace(temporary, target)
            if sha256(target) != proposal["candidate_sha256"]:
                raise RuntimeError("installed target hash does not match approved candidate")
            proposal["status"] = "adopted"
            proposal["adopted_at"] = now().isoformat(timespec="seconds")
            proposal["adopted_sha256"] = sha256(target)
            write_json(proposal_path, proposal)
        except Exception:
            shutil.copy2(backup, target)
            write_json(proposal_path, previous_proposal)
            raise
        transaction.unlink(missing_ok=True)
    print(json.dumps({"proposal_id": args.proposal, "target": str(target), "backup": str(backup_dir)}, ensure_ascii=False, indent=2))


def command_status(args: argparse.Namespace) -> None:
    directory = state_dir(args)
    evidence = load_evidence(directory)
    proposals = []
    proposal_root = directory / "proposals"
    if proposal_root.exists():
        for path in sorted(proposal_root.glob("*/proposal.json")):
            item = read_json(path)
            proposals.append({key: item.get(key) for key in ("proposal_id", "status", "target", "summary", "changed_lines")})
    counts: dict[str, int] = {}
    for item in evidence:
        counts[item["kind"]] = counts.get(item["kind"], 0) + 1
    print(json.dumps({"state_dir": str(directory), "evidence_count": len(evidence), "evidence_by_kind": counts, "proposals": proposals}, ensure_ascii=False, indent=2))


def command_mine(args: argparse.Namespace) -> None:
    evidence = load_evidence(state_dir(args))
    groups: dict[tuple[str, str], list[dict]] = {}
    for item in evidence:
        groups.setdefault((item["skill"], item["kind"]), []).append(item)
    patterns = []
    for (skill, kind), items in sorted(groups.items()):
        high_risk = any(item["severity"] in {"high", "critical"} for item in items)
        patterns.append({
            "skill": skill,
            "kind": kind,
            "count": len(items),
            "eligible_for_proposal": len(items) >= args.min_count or high_risk,
            "high_risk": high_risk,
            "evidence_ids": [item["evidence_id"] for item in items],
            "summaries": [item["summary"] for item in items[-args.max_examples:]],
        })
    print(json.dumps({"patterns": patterns}, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validation-gated optimizer for video workflow skills")
    parser.add_argument("--state-dir", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--source", choices=["task", "dialogue", "qa", "user"], required=True)
    record.add_argument("--task-id", required=True)
    record.add_argument("--skill", required=True)
    record.add_argument("--kind", choices=sorted(KINDS), required=True)
    record.add_argument("--severity", choices=sorted(SEVERITIES), default="medium")
    record.add_argument("--summary", required=True)
    record.add_argument("--expected", required=True)
    record.add_argument("--observed", required=True)
    record.add_argument("--project-path")
    record.set_defaults(func=command_record)
    propose = sub.add_parser("propose")
    propose.add_argument("--target", required=True)
    propose.add_argument("--candidate", type=Path, required=True)
    propose.add_argument("--summary", required=True)
    propose.add_argument("--evidence", nargs="+", required=True)
    propose.add_argument("--explicit-user-request", action="store_true")
    propose.set_defaults(func=command_propose)
    gate = sub.add_parser("gate")
    gate.add_argument("--proposal", required=True)
    gate.add_argument("--evaluation", type=Path, required=True)
    gate.set_defaults(func=command_gate)
    adopt = sub.add_parser("adopt")
    adopt.add_argument("--proposal", required=True)
    adopt.add_argument("--confirm", required=True)
    adopt.set_defaults(func=command_adopt)
    status = sub.add_parser("status")
    status.set_defaults(func=command_status)
    mine = sub.add_parser("mine")
    mine.add_argument("--min-count", type=int, default=2)
    mine.add_argument("--max-examples", type=int, default=3)
    mine.set_defaults(func=command_mine)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
