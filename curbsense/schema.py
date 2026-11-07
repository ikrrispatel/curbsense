from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_FIELDS = (
    "occupancy_status",
    "violation_status",
    "evidence_used",
    "confidence",
    "recommended_action",
    "reason",
)
ENUMS = {
    "occupancy_status": {"occupied", "vacant", "unknown"},
    "violation_status": {"violation", "no_violation", "unknown"},
    "recommended_action": {"enforce", "warn", "do_nothing", "request_review", "abstain"},
}
MAX_REASON_LENGTH = 500


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed


def parse_output(raw: str, evidence_ids: set[str]) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return None, ["format_failure"]
    if not isinstance(value, dict):
        return None, ["schema_failure"]
    errors: list[str] = []
    if set(value) != set(OUTPUT_FIELDS):
        errors.append("schema_failure")
    for field, allowed in ENUMS.items():
        if value.get(field) not in allowed:
            errors.append("schema_failure")
    refs = value.get("evidence_used")
    if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
        errors.append("schema_failure")
    else:
        if len(refs) != len(set(refs)):
            errors.append("duplicate_evidence_reference")
        if any(item not in evidence_ids for item in refs):
            errors.append("hallucinated_evidence")
    confidence = value.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("schema_failure")
    reason = value.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        errors.append("schema_failure")
    elif len(reason) > MAX_REASON_LENGTH:
        errors.append("reason_too_long")
    return value, sorted(set(errors))


def validate_task(task: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    required = {"task_id", "version", "family", "question", "timezone", "decision_time", "public_rules", "evidence", "visible_schema"}
    errors.extend(f"missing:{key}" for key in sorted(required - set(task)))
    forbidden = {"gold_answer", "reference_solution", "acceptable_alternatives", "rubric", "hidden_rubric"}
    errors.extend(f"hidden_field:{key}" for key in sorted(forbidden & set(task)))
    if not task.get("task_id", "").startswith("CS-"):
        errors.append("invalid_task_id")
    if task.get("version") != "1.0":
        errors.append("unsupported_version")
    try:
        parse_timestamp(task["decision_time"])
    except (KeyError, ValueError) as exc:
        errors.append(f"invalid_decision_time:{exc}")
    evidence = task.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        errors.append("empty_evidence")
        evidence = []
    ids = [item.get("id") for item in evidence if isinstance(item, dict)]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        errors.append("duplicate_evidence_ids")
    for item in evidence:
        if not isinstance(item, dict):
            errors.append("invalid_evidence")
            continue
        if not item.get("type") or not item.get("supports"):
            errors.append(f"incomplete_evidence:{item.get('id')}")
        for key in ("observed_at", "effective_at", "valid_from", "valid_until", "event_time", "ingested_at"):
            if key in item:
                try:
                    parse_timestamp(item[key])
                except ValueError as exc:
                    errors.append(f"invalid_timestamp:{item.get('id')}:{exc}")
        if item.get("asset_path"):
            asset = root / item["asset_path"]
            if not asset.is_file():
                errors.append(f"missing_asset:{item.get('id')}:{item['asset_path']}")
    rules = task.get("public_rules", {})
    for key in ("required_action_if_unresolved", "contradiction_policy", "evidence_priority"):
        if key not in rules:
            errors.append(f"missing_public_rule:{key}")
    confidence = rules.get("confidence_policy", {})
    if not 0 <= confidence.get("unresolved_max", -1) <= 1 or not 0 <= confidence.get("resolved_min", -1) <= confidence.get("resolved_confidence", -1) <= 1:
        errors.append("invalid_confidence_policy")
    return sorted(set(errors))


def visible_packet(task: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    packet = dict(task)
    if root is not None:
        assets = []
        for evidence in task.get("evidence", []):
            asset_path = evidence.get("asset_path")
            if asset_path:
                path = root / asset_path
                assets.append({"evidence_id": evidence["id"], "asset_path": asset_path, "svg": path.read_text(encoding="utf-8")})
        if assets:
            packet["camera_assets"] = assets
    return packet


def load_tasks(root: Path) -> list[dict[str, Any]]:
    paths = sorted((root / "tasks" / "v1").glob("CS-*.json"))
    tasks = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    if len(tasks) != 8:
        raise ValueError(f"expected exactly 8 visible tasks, got {len(tasks)}")
    return tasks


def load_grader_data(root: Path) -> dict[str, dict[str, Any]]:
    paths = sorted((root / "grader_data" / "v1").glob("CS-*.json"))
    values = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in paths}
    if len(values) != 8:
        raise ValueError(f"expected exactly 8 grader-data files, got {len(values)}")
    return values


def load_references(root: Path) -> dict[str, dict[str, Any]]:
    paths = sorted((root / "references" / "v1").glob("CS-*.json"))
    values = {path.stem: json.loads(path.read_text(encoding="utf-8")) for path in paths}
    if len(values) != 8:
        raise ValueError(f"expected exactly 8 reference files, got {len(values)}")
    return values
