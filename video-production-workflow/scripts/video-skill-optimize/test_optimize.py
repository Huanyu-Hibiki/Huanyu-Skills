#!/usr/bin/env python3
"""Deterministic tests for the local video skill optimizer."""

from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("optimize.py")
SPEC = importlib.util.spec_from_file_location("video_skill_optimize", MODULE_PATH)
assert SPEC and SPEC.loader
optimizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(optimizer)


class OptimizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / ".state"
        self.target = self.root / "skills" / "demo" / "SKILL.md"
        self.target.parent.mkdir(parents=True)
        self.target.write_text(
            "---\nname: demo\ndescription: Demo skill.\n---\n\n# Demo\n\nOld rule.\n",
            encoding="utf-8",
        )
        optimizer.ROOT = self.root
        optimizer.DEFAULT_STATE = self.state

    def tearDown(self) -> None:
        self.temp.cleanup()

    def record(self) -> str:
        args = argparse.Namespace(
            state_dir=self.state,
            source="dialogue",
            task_id="task-1",
            skill="demo",
            kind="user_correction",
            severity="high",
            summary="token=secret-value should be hidden",
            expected="Use the safe rule",
            observed="Used the old rule",
            project_path="",
        )
        optimizer.command_record(args)
        item = optimizer.load_evidence(self.state)[0]
        self.assertNotIn("secret-value", item["summary"])
        return item["evidence_id"]

    def propose(self, evidence_id: str) -> str:
        candidate = self.root / "candidate.md"
        candidate.write_text(
            "---\nname: demo\ndescription: Demo skill.\n---\n\n# Demo\n\nNew safe rule.\n",
            encoding="utf-8",
        )
        args = argparse.Namespace(
            state_dir=self.state,
            target="skills/demo/SKILL.md",
            candidate=candidate,
            summary="Replace unsafe rule",
            evidence=[evidence_id],
            explicit_user_request=False,
        )
        optimizer.command_propose(args)
        proposals = list((self.state / "proposals").glob("*/proposal.json"))
        proposal = optimizer.read_json(proposals[0])
        self.assertEqual("Old rule.", self.target.read_text(encoding="utf-8").splitlines()[-1])
        return proposal["proposal_id"]

    def evaluation(self, proposal_id: str, overlap: str | None = None) -> Path:
        path = self.root / "evaluation.json"
        payload = {
            "proposal_id": proposal_id,
            "cases": [
                {"case_id": "new-rule", "case_type": "normal", "held_out": True, "critical": False, "source_evidence_ids": [overlap] if overlap else [], "prompt": "Use new rule", "check": "Candidate applies rule", "baseline_pass": False, "candidate_pass": True},
                {"case_id": "risk", "case_type": "risk", "held_out": True, "critical": True, "source_evidence_ids": [], "prompt": "Keep safety", "check": "Safety remains", "baseline_pass": True, "candidate_pass": True},
                {"case_id": "neighbor", "case_type": "neighbor", "held_out": True, "critical": False, "source_evidence_ids": [], "prompt": "Neighbor task", "check": "No regression", "baseline_pass": True, "candidate_pass": True},
            ],
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_full_gate_and_adopt(self) -> None:
        evidence_id = self.record()
        proposal_id = self.propose(evidence_id)
        gate_args = argparse.Namespace(
            state_dir=self.state,
            proposal=proposal_id,
            evaluation=self.evaluation(proposal_id),
        )
        optimizer.command_gate(gate_args)
        with self.assertRaises(SystemExit):
            optimizer.command_adopt(argparse.Namespace(state_dir=self.state, proposal=proposal_id, confirm="no"))
        proposal_path = self.state / "proposals" / proposal_id / "proposal.json"
        proposal = optimizer.read_json(proposal_path)
        confirmation = f"ADOPT:{proposal_id}:{proposal['candidate_sha256'][:12]}"
        optimizer.command_adopt(argparse.Namespace(state_dir=self.state, proposal=proposal_id, confirm=confirmation))
        self.assertIn("New safe rule.", self.target.read_text(encoding="utf-8"))
        self.assertTrue((self.state / "adopted" / proposal_id / "SKILL.md").exists())

    def test_gate_rejects_training_overlap(self) -> None:
        evidence_id = self.record()
        proposal_id = self.propose(evidence_id)
        args = argparse.Namespace(
            state_dir=self.state,
            proposal=proposal_id,
            evaluation=self.evaluation(proposal_id, overlap=evidence_id),
        )
        with self.assertRaises(SystemExit) as raised:
            optimizer.command_gate(args)
        self.assertEqual(2, raised.exception.code)

    def test_gate_rejects_invalid_case_schema(self) -> None:
        evidence_id = self.record()
        proposal_id = self.propose(evidence_id)
        evaluation = self.evaluation(proposal_id)
        payload = json.loads(evaluation.read_text(encoding="utf-8"))
        payload["cases"][0]["source_evidence_ids"] = evidence_id
        payload["cases"][1]["critical"] = False
        evaluation.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(SystemExit) as raised:
            optimizer.command_gate(argparse.Namespace(state_dir=self.state, proposal=proposal_id, evaluation=evaluation))
        self.assertEqual(2, raised.exception.code)

    def test_propose_rejects_single_medium_signal(self) -> None:
        evidence_id = self.record()
        evidence_path = self.state / "evidence.jsonl"
        item = json.loads(evidence_path.read_text(encoding="utf-8").strip())
        item["severity"] = "medium"
        evidence_path.write_text(json.dumps(item) + "\n", encoding="utf-8")
        candidate = self.root / "candidate.md"
        candidate.write_text(self.target.read_text(encoding="utf-8") + "New rule.\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            optimizer.command_propose(argparse.Namespace(
                state_dir=self.state,
                target="skills/demo/SKILL.md",
                candidate=candidate,
                summary="Insufficient evidence",
                evidence=[evidence_id],
                explicit_user_request=False,
            ))

    def test_adopt_rejects_target_drift(self) -> None:
        evidence_id = self.record()
        proposal_id = self.propose(evidence_id)
        optimizer.command_gate(argparse.Namespace(
            state_dir=self.state,
            proposal=proposal_id,
            evaluation=self.evaluation(proposal_id),
        ))
        self.target.write_text(self.target.read_text(encoding="utf-8") + "Concurrent edit.\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            proposal_path = self.state / "proposals" / proposal_id / "proposal.json"
            proposal = optimizer.read_json(proposal_path)
            confirmation = f"ADOPT:{proposal_id}:{proposal['candidate_sha256'][:12]}"
            optimizer.command_adopt(argparse.Namespace(state_dir=self.state, proposal=proposal_id, confirm=confirmation))

    def test_adopt_rejects_candidate_tampering_after_gate(self) -> None:
        evidence_id = self.record()
        proposal_id = self.propose(evidence_id)
        optimizer.command_gate(argparse.Namespace(
            state_dir=self.state,
            proposal=proposal_id,
            evaluation=self.evaluation(proposal_id),
        ))
        proposal_path = self.state / "proposals" / proposal_id / "proposal.json"
        proposal = optimizer.read_json(proposal_path)
        candidate = self.state / "proposals" / proposal_id / "candidate.md"
        candidate.write_text("tampered", encoding="utf-8")
        confirmation = f"ADOPT:{proposal_id}:{proposal['candidate_sha256'][:12]}"
        with self.assertRaises(SystemExit):
            optimizer.command_adopt(argparse.Namespace(state_dir=self.state, proposal=proposal_id, confirm=confirmation))

    def test_adopt_recovers_interrupted_replacement(self) -> None:
        evidence_id = self.record()
        proposal_id = self.propose(evidence_id)
        optimizer.command_gate(argparse.Namespace(state_dir=self.state, proposal=proposal_id, evaluation=self.evaluation(proposal_id)))
        proposal_path = self.state / "proposals" / proposal_id / "proposal.json"
        proposal = optimizer.read_json(proposal_path)
        candidate = self.state / "proposals" / proposal_id / "candidate.md"
        backup_dir = self.state / "adopted" / proposal_id
        backup_dir.mkdir(parents=True)
        backup = backup_dir / "SKILL.md"
        backup.write_bytes(self.target.read_bytes())
        self.target.write_bytes(candidate.read_bytes())
        transaction = self.state / "transactions" / f"{proposal_id}.json"
        optimizer.write_json(transaction, {"proposal_id": proposal_id, "target": str(self.target), "backup": str(backup)})
        confirmation = f"ADOPT:{proposal_id}:{proposal['candidate_sha256'][:12]}"
        optimizer.command_adopt(argparse.Namespace(state_dir=self.state, proposal=proposal_id, confirm=confirmation))
        self.assertEqual("adopted", optimizer.read_json(proposal_path)["status"])
        self.assertFalse(transaction.exists())

    def test_safe_target_rejects_optimizer_and_sensitive_files(self) -> None:
        optimizer_dir = self.root / "scripts" / "video-skill-optimize"
        optimizer_dir.mkdir(parents=True)
        optimizer_file = optimizer_dir / "optimize.py"
        optimizer_file.write_text("pass", encoding="utf-8")
        sensitive = self.root / ".env"
        sensitive.write_text("SECRET=x", encoding="utf-8")
        with self.assertRaises(SystemExit):
            optimizer.safe_target(str(optimizer_file))
        with self.assertRaises(SystemExit):
            optimizer.safe_target(str(sensitive))

    def test_mine_marks_high_risk_signal_eligible(self) -> None:
        self.record()
        evidence = optimizer.load_evidence(self.state)
        groups = {}
        for item in evidence:
            groups.setdefault((item["skill"], item["kind"]), []).append(item)
        items = groups[("demo", "user_correction")]
        self.assertEqual(1, len(items))
        self.assertIn(items[0]["severity"], {"high", "critical"})


if __name__ == "__main__":
    unittest.main()
