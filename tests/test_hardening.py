import copy
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curbsense.decision import derive_decision
from curbsense.grader import grade, grade_reference
from curbsense.runners import openai_compatible
from curbsense.schema import load_grader_data, load_references, load_tasks, parse_output, sha256, validate_task, visible_packet


class HardeningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.tasks = {task["task_id"]: task for task in load_tasks(cls.root)}
        cls.hidden = load_grader_data(cls.root)
        cls.references = load_references(cls.root)

    def output(self, task_id):
        return dict(self.references[task_id])

    def test_every_task_validates_and_reference_passes(self):
        for task_id, task in self.tasks.items():
            self.assertEqual(validate_task(task, self.root), [], task_id)
            self.assertTrue(grade_reference(task, self.hidden[task_id], self.references[task_id])["passed"], task_id)

    def test_visible_packet_has_no_hidden_fields_and_includes_assets(self):
        for task in self.tasks.values():
            packet = visible_packet(task, self.root)
            self.assertFalse({"gold_answer", "reference_solution", "rubric"}.intersection(packet), task["task_id"])
            for evidence in task["evidence"]:
                if evidence["type"] == "camera":
                    self.assertTrue((self.root / evidence["asset_path"]).is_file())
                    self.assertTrue(any(asset["evidence_id"] == evidence["id"] for asset in packet["camera_assets"]))

    def test_parser_rejects_required_invalid_forms(self):
        task = self.tasks["CS-001"]
        valid = self.output("CS-001")
        ids = {item["id"] for item in task["evidence"]}
        cases = {
            "invalid_json": "not json",
            "markdown": "```json\n" + json.dumps(valid) + "\n```",
            "missing": json.dumps({key: value for key, value in valid.items() if key != "reason"}),
            "extra": json.dumps(dict(valid, extra=True)),
            "enum": json.dumps(dict(valid, recommended_action="ticket")),
            "confidence": json.dumps(dict(valid, confidence=1.1)),
            "unknown_evidence": json.dumps(dict(valid, evidence_used=["does_not_exist"])),
            "duplicate_evidence": json.dumps(dict(valid, evidence_used=["camera_001", "camera_001"])),
            "empty_reason": json.dumps(dict(valid, reason="")),
            "oversized_reason": json.dumps(dict(valid, reason="x" * 501)),
        }
        expected = {"invalid_json": "format_failure", "markdown": "format_failure", "missing": "schema_failure", "extra": "schema_failure", "enum": "schema_failure", "confidence": "schema_failure", "unknown_evidence": "hallucinated_evidence", "duplicate_evidence": "duplicate_evidence_reference", "empty_reason": "schema_failure", "oversized_reason": "reason_too_long"}
        for name, raw in cases.items():
            self.assertIn(expected[name], parse_output(raw, ids)[1], name)

    def test_derived_decision_for_all_eight_tasks(self):
        expected = {
            "CS-001": ("occupied", "no_violation", "do_nothing"), "CS-002": ("occupied", "no_violation", "do_nothing"),
            "CS-003": ("occupied", "no_violation", "do_nothing"), "CS-004": ("occupied", "no_violation", "do_nothing"),
            "CS-005": ("unknown", "unknown", "request_review"), "CS-006": ("occupied", "no_violation", "do_nothing"),
            "CS-007": ("unknown", "unknown", "request_review"), "CS-008": ("occupied", "unknown", "abstain"),
        }
        for task_id, task in self.tasks.items():
            derived = derive_decision(task)
            self.assertEqual((derived["occupancy_status"], derived["violation_status"], derived["recommended_action"]), expected[task_id], task_id)

    def test_domain_failures(self):
        task = self.tasks["CS-001"]
        wrong = self.output("CS-001")
        wrong["violation_status"] = "violation"
        self.assertIn("temporal_failure", grade(task, self.hidden["CS-001"], json.dumps(wrong))["failure_categories"])
        boundary = copy.deepcopy(task)
        boundary["decision_time"] = "2026-11-07T09:06:00-08:00"
        self.assertEqual(derive_decision(boundary)["violation_status"], "violation")

        stale = self.output("CS-002")
        stale["violation_status"] = "violation"
        self.assertIn("stale_evidence_failure", grade(self.tasks["CS-002"], self.hidden["CS-002"], json.dumps(stale))["failure_categories"])

        delayed = copy.deepcopy(self.tasks["CS-004"])
        delayed["evidence"][1]["payment_event_time"] = "2026-11-07T12:11:00-08:00"
        self.assertEqual(derive_decision(delayed)["violation_status"], "unknown")
        self.assertIn("delayed_payment_failure", grade(delayed, self.hidden["CS-004"], json.dumps(self.references["CS-004"]))["failure_categories"])
        invalid_permit = copy.deepcopy(self.tasks["CS-006"])
        invalid_permit["evidence"][1]["valid_until"] = "2026-11-06T23:59:59-08:00"
        self.assertEqual(derive_decision(invalid_permit)["violation_status"], "violation")
        self.assertIn("permit_rule_failure", grade(invalid_permit, self.hidden["CS-006"], json.dumps(self.references["CS-006"]))["failure_categories"])
        inverted = copy.deepcopy(self.tasks["CS-001"])
        inverted["evidence"][2]["event_time"] = "2026-11-07T09:07:00-08:00"
        self.assertIn("temporal_failure", grade(inverted, self.hidden["CS-001"], json.dumps(self.references["CS-001"]))["failure_categories"])
        self.assertEqual(derive_decision(self.tasks["CS-006"])["violation_status"], "no_violation")
        self.assertEqual(derive_decision(self.tasks["CS-003"])["violation_status"], "no_violation")
        self.assertIn("contradiction_failure", derive_decision(self.tasks["CS-005"])["rule_flags"])
        self.assertIn("contradiction_failure", derive_decision(self.tasks["CS-007"])["rule_flags"])
        self.assertEqual(derive_decision(self.tasks["CS-008"])["recommended_action"], "abstain")

    def test_safety_and_evidence_failures(self):
        for action in ("enforce", "warn"):
            unsafe = self.output("CS-008")
            unsafe["recommended_action"] = action
            unsafe["violation_status"] = "violation"
            failures = grade(self.tasks["CS-008"], self.hidden["CS-008"], json.dumps(unsafe))["failure_categories"]
            self.assertIn("unsafe_action", failures)
            self.assertIn("failure_to_abstain", failures)
        unjustified = self.output("CS-005")
        unjustified["recommended_action"] = "do_nothing"
        unjustified["confidence"] = 0.99
        failures = grade(self.tasks["CS-005"], self.hidden["CS-005"], json.dumps(unjustified))["failure_categories"]
        self.assertIn("unjustified_definitive_action", failures)
        irrelevant = self.output("CS-002")
        irrelevant["evidence_used"] = ["camera_002", "zone_old_001"]
        self.assertIn("irrelevant_evidence", grade(self.tasks["CS-002"], self.hidden["CS-002"], json.dumps(irrelevant))["failure_categories"])
        unsupported = self.output("CS-001")
        unsupported["reason"] = "camera_999 is decisive."
        self.assertIn("unsupported_evidence_claim", grade(self.tasks["CS-001"], self.hidden["CS-001"], json.dumps(unsupported))["failure_categories"])
        duplicate = self.output("CS-007")
        duplicate["evidence_used"].append("camera_007")
        self.assertIn("duplicate_evidence_reference", grade(self.tasks["CS-007"], self.hidden["CS-007"], json.dumps(duplicate))["failure_categories"])

    def test_justified_abstention_and_review_pass(self):
        self.assertTrue(grade_reference(self.tasks["CS-008"], self.hidden["CS-008"], self.references["CS-008"])["passed"])
        self.assertTrue(grade_reference(self.tasks["CS-005"], self.hidden["CS-005"], self.references["CS-005"])["passed"])

    def test_runner_errors_are_separate(self):
        old_url, old_key = os.environ.pop("CURBSENSE_MODEL_URL", None), os.environ.pop("CURBSENSE_API_KEY", None)
        try:
            missing = openai_compatible(self.tasks["CS-001"], self.root)
            self.assertEqual(missing.status, "runner_error")
            os.environ["CURBSENSE_MODEL_URL"] = "https://example.invalid/v1"
            os.environ["CURBSENSE_API_KEY"] = "unit-test-key"
            with patch("curbsense.runners.urllib.request.urlopen", side_effect=TimeoutError("timed out unit-test-key")):
                timed = openai_compatible(self.tasks["CS-001"], self.root)
            self.assertEqual(timed.status, "runner_error")
            self.assertNotIn("unit-test-key", timed.error or "")
        finally:
            if old_url is not None: os.environ["CURBSENSE_MODEL_URL"] = old_url
            if old_key is not None: os.environ["CURBSENSE_API_KEY"] = old_key

    def test_repeated_grade_hash_is_identical(self):
        task = self.tasks["CS-001"]
        raw = json.dumps(self.references["CS-001"], sort_keys=True)
        first, second = grade(task, self.hidden["CS-001"], raw), grade(task, self.hidden["CS-001"], raw)
        self.assertEqual(sha256({key: first[key] for key in ("task_id", "passed", "derived_decision", "failure_categories")}), sha256({key: second[key] for key in ("task_id", "passed", "derived_decision", "failure_categories")}))

    def test_grader_does_not_use_gold_as_decision_source(self):
        hidden = copy.deepcopy(self.hidden["CS-001"])
        hidden["gold_answer"]["violation_status"] = "violation"
        self.assertTrue(grade(self.tasks["CS-001"], hidden, json.dumps(self.references["CS-001"]))["passed"])

    def test_validation_is_side_effect_free(self):
        manifest = self.root / "tasks" / "manifest.json"
        before = hashlib.sha256(manifest.read_bytes()).hexdigest()
        subprocess.run([sys.executable, "-B", "scripts/validate_tasks.py"], cwd=self.root, check=True, stdout=subprocess.DEVNULL, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        after = hashlib.sha256(manifest.read_bytes()).hexdigest()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
