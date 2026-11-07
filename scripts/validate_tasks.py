#!/usr/bin/env python3
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curbsense.schema import load_tasks, validate_task, sha256, visible_packet
from curbsense.grader import grade_reference

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tasks = load_tasks(root)
    failures = []
    manifest = []
    for task in tasks:
        errors = validate_task(task)
        ref = grade_reference(task)
        if not ref["passed"]: errors.append("reference_does_not_pass:" + ",".join(ref["failure_categories"]))
        if "gold_answer" in visible_packet(task): errors.append("gold_leak")
        manifest.append({"task_id": task["task_id"], "task_hash": sha256(task), "prompt_hash": sha256(visible_packet(task))})
        if errors: failures.append({"task_id": task["task_id"], "errors": sorted(set(errors))})
    out = {"schema_version":"1.0","task_count":len(tasks),"passed":not failures,"manifest":manifest,"failures":failures}
    (root / "tasks" / "manifest.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"passed":out["passed"],"task_count":len(tasks),"failures":failures}, sort_keys=True))
    return 0 if out["passed"] else 1
if __name__ == "__main__": raise SystemExit(main())
