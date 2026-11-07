#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curbsense import GRADER_VERSION
from curbsense.decision import derive_decision
from curbsense.grader import grade_reference
from curbsense.schema import load_grader_data, load_references, load_tasks, sha256, validate_task, visible_packet


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tasks = load_tasks(root)
    hidden = load_grader_data(root)
    references = load_references(root)
    failures = []
    manifest = []
    for task in tasks:
        task_id = task["task_id"]
        errors = validate_task(task, root)
        if task_id not in hidden or task_id not in references:
            errors.append("missing_hidden_or_reference")
            failures.append({"task_id": task_id, "errors": sorted(set(errors))})
            continue
        derived = derive_decision(task)
        gold = hidden[task_id].get("gold_answer", {})
        for key in ("occupancy_status", "violation_status", "recommended_action"):
            if gold.get(key) != derived[key]:
                errors.append(f"gold_disagrees_with_derived:{key}")
        reference_grade = grade_reference(task, hidden[task_id], references[task_id])
        if not reference_grade["passed"]:
            errors.append("reference_does_not_pass:" + ",".join(reference_grade["failure_categories"]))
        if "gold_answer" in visible_packet(task, root) or "reference_solution" in visible_packet(task, root):
            errors.append("hidden_data_leak")
        manifest.append({"task_id": task_id, "task_hash": sha256(task), "prompt_hash": sha256(visible_packet(task, root))})
        if errors:
            failures.append({"task_id": task_id, "errors": sorted(set(errors))})
    out = {"schema_version": "2.0", "grader_version": GRADER_VERSION, "task_count": len(tasks), "passed": not failures, "manifest": manifest, "failures": failures}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
