#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from curbsense import GRADER_VERSION
from curbsense.grader import grade
from curbsense.runners import mock, openai_compatible
from curbsense.schema import load_grader_data, load_references, load_tasks, sha256, visible_packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runner", choices=["mock", "openai_compatible"], default="mock")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path, default=Path("results/run.json"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    tasks = load_tasks(root)
    hidden = load_grader_data(root)
    references = load_references(root)
    runner = mock if args.runner == "mock" else openai_compatible
    grader_hash = sha256((root / "curbsense" / "grader.py").read_bytes() + (root / "curbsense" / "decision.py").read_bytes())
    records = []
    for trial in range(1, args.trials + 1):
        for task in tasks:
            started = time.monotonic()
            runner_result = runner(task, references[task["task_id"]], root) if args.runner == "mock" else runner(task, root)
            latency = runner_result.latency_ms or int((time.monotonic() - started) * 1000)
            grade_result = None if runner_result.status != "ok" else grade(task, hidden[task["task_id"]], runner_result.raw_output or "")
            normalized = grade_result.get("normalized_output") if grade_result else None
            deterministic_grade = None
            if grade_result:
                deterministic_grade = sha256({key: grade_result[key] for key in ("task_id", "passed", "derived_decision", "failure_categories")})
            records.append({
                "task_id": task["task_id"], "trial": trial,
                "task_hash": sha256(task), "prompt_hash": sha256(visible_packet(task, root)),
                "grader_version": GRADER_VERSION, "grader_version_hash": grader_hash,
                "model": runner_result.model, "model_version": runner_result.model_version,
                "settings": runner_result.settings,
                "normalized_output_hash": sha256(normalized) if normalized is not None else None,
                "deterministic_grade_hash": deterministic_grade,
                "volatile_execution": {"timestamp": dt.datetime.now(dt.timezone.utc).isoformat(), "latency_ms": latency},
                "environment": {"python": platform.python_version(), "platform": platform.platform()},
                "tokens": runner_result.tokens, "status": runner_result.status,
                "runner_error": runner_result.error, "raw_output": runner_result.raw_output,
                "grade": grade_result,
            })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"schema_version": "2.0", "runner": args.runner, "trials": args.trials, "records": records}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "records": len(records), "runner_errors": sum(row["status"] != "ok" for row in records)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
