#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curbsense.schema import sha256


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    eligible = [row for row in rows if row["status"] == "ok" and row["grade"] is not None]
    failures = defaultdict(int)
    for row in eligible:
        for category in row["grade"]["failure_categories"]:
            failures[category] += 1
    passed = sum(int(row["grade"]["passed"]) for row in eligible)
    per_task_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_model_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    per_trial: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in eligible:
        per_task_rows[row["task_id"]].append(row)
        per_model_rows[row["model"]].append(row)
        per_trial[row["trial"]].append(row)

    def group_stats(group: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        return {key: {"attempts": len(values), "passes": sum(int(item["grade"]["passed"]) for item in values), "pass_rate": sum(int(item["grade"]["passed"]) for item in values) / len(values) if values else 0} for key, values in sorted(group.items())}

    trial_rates = [sum(int(item["grade"]["passed"]) for item in values) / len(values) for _, values in sorted(per_trial.items()) if values]
    calibration_values = [row["grade"]["normalized_output"]["confidence"] for row in eligible]
    calibration_targets = [int(row["grade"]["passed"]) for row in eligible]
    brier = sum((confidence - target) ** 2 for confidence, target in zip(calibration_values, calibration_targets)) / len(eligible) if eligible else 0
    ece = 0.0
    for lower in (0.0, 0.2, 0.4, 0.6, 0.8):
        bucket = [(confidence, target) for confidence, target in zip(calibration_values, calibration_targets) if lower <= confidence < lower + 0.2 or (lower == 0.8 and confidence == 1.0)]
        if bucket:
            ece += len(bucket) / len(eligible) * abs(sum(x[0] for x in bucket) / len(bucket) - sum(x[1] for x in bucket) / len(bucket))
    per_task = group_stats(per_task_rows)
    pass_at_k = sum(any(item["grade"]["passed"] for item in values) for values in per_task_rows.values()) / len(per_task_rows) if per_task_rows else 0
    pass_power_k = sum(all(item["grade"]["passed"] for item in values) for values in per_task_rows.values()) / len(per_task_rows) if per_task_rows else 0
    total = len(rows)
    return {
        "evidence_label": "mock_harness_validation" if rows and rows[0]["model"] == "mock-v1" else "model_trial",
        "records": total, "eligible_records": len(eligible), "runner_errors": total - len(eligible),
        "metrics": {
            "pass_rate": passed / len(eligible) if eligible else 0,
            "unsafe_action_rate": failures["unsafe_action"] / len(eligible) if eligible else 0,
            "failure_to_abstain_rate": failures["failure_to_abstain"] / len(eligible) if eligible else 0,
            "hallucinated_evidence_rate": failures["hallucinated_evidence"] / len(eligible) if eligible else 0,
            "temporal_failure_rate": failures["temporal_failure"] / len(eligible) if eligible else 0,
            "format_failure_rate": failures["format_failure"] / total if total else 0,
            "runner_error_rate": (total - len(eligible)) / total if total else 0,
            "pass_at_k": pass_at_k, "pass_power_k": pass_power_k,
            "trial_variance": statistics.pvariance(trial_rates) if len(trial_rates) > 1 else 0,
            "calibration_brier": brier, "calibration_ece": ece,
        },
        "failure_counts": dict(sorted(failures.items())),
        "per_task": per_task,
        "per_model": {key: group_stats({key: value})[key] for key, value in sorted(per_model_rows.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    report = _summary(data["records"])
    report["report_hash"] = sha256(report)
    target = args.markdown or args.input.with_suffix(".md")
    target.write_text("# CurbSense report\n\nEvidence label: `" + report["evidence_label"] + "`\n\n```json\n" + json.dumps(report, indent=2, sort_keys=True) + "\n```\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
