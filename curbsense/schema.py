from __future__ import annotations

import hashlib, json
from pathlib import Path
from typing import Any

OUTPUT_FIELDS = ("occupancy_status", "violation_status", "evidence_used", "confidence", "recommended_action", "reason")
ENUMS = {
    "occupancy_status": {"occupied", "vacant", "unknown"},
    "violation_status": {"violation", "no_violation", "unknown"},
    "recommended_action": {"enforce", "warn", "do_nothing", "request_review", "abstain"},
}

def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)

def sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode()
    return hashlib.sha256(raw).hexdigest()

def parse_output(raw: str, evidence_ids: set[str]) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None, ["format_failure"]
    errors: list[str] = []
    if not isinstance(value, dict):
        return None, ["schema_failure"]
    if set(value) != set(OUTPUT_FIELDS):
        errors.append("schema_failure")
    for field, allowed in ENUMS.items():
        if value.get(field) not in allowed:
            errors.append("schema_failure")
    refs = value.get("evidence_used")
    if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
        errors.append("schema_failure")
    elif any(x not in evidence_ids for x in refs):
        errors.append("hallucinated_evidence")
    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("schema_failure")
    if not isinstance(value.get("reason"), str) or not value.get("reason", "").strip():
        errors.append("schema_failure")
    return (value if not errors else value), sorted(set(errors))

def validate_task(task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {"task_id", "version", "family", "question", "timezone", "evidence", "visible_schema", "gold_answer", "acceptable_alternatives", "rubric", "reference_solution"}
    errors.extend(f"missing:{k}" for k in sorted(required - set(task)))
    if not task.get("task_id", "").startswith("CS-"): errors.append("invalid_task_id")
    if len(task.get("evidence", [])) == 0: errors.append("empty_evidence")
    if "gold_answer" in task and not isinstance(task["gold_answer"], dict): errors.append("invalid_gold")
    evidence_ids = [e.get("id") for e in task.get("evidence", [])]
    if any(not x for x in evidence_ids) or len(evidence_ids) != len(set(evidence_ids)): errors.append("duplicate_evidence_ids")
    if task.get("gold_answer", {}).get("recommended_action") == "enforce" and task.get("gold_answer", {}).get("violation_status") != "violation": errors.append("unsafe_gold")
    return sorted(set(errors))

def visible_packet(task: dict[str, Any]) -> dict[str, Any]:
    return {"task_id": task["task_id"], "version": task["version"], "family": task["family"], "question": task["question"], "timezone": task["timezone"], "evidence": task["evidence"], "output_schema": task["visible_schema"]}

def load_tasks(root: Path) -> list[dict[str, Any]]:
    tasks = [json.loads(p.read_text()) for p in sorted((root / "tasks" / "v1").glob("*.json"))]
    # The checked-in packet keeps the gold answer in its hidden section; loading
    # materializes the separately named reference solution used by the oracle.
    for task in tasks:
        task.setdefault("reference_solution", dict(task.get("gold_answer", {})))
    if len(tasks) != 8: raise ValueError(f"expected exactly 8 tasks, got {len(tasks)}")
    return tasks
