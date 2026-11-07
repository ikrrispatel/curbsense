from __future__ import annotations

from datetime import timedelta
from typing import Any

from .schema import parse_timestamp


def _evidence(task: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [item for item in task["evidence"] if item.get("type") == kind]


def _record_time(record: dict[str, Any]) -> str:
    return record.get("observed_at") or record.get("event_time") or record.get("ingested_at")


def _active(record: dict[str, Any], decision_time) -> bool:
    start = parse_timestamp(record.get("valid_from", record.get("effective_at", _record_time(record))))
    end = record.get("valid_until")
    return start <= decision_time and (not end or decision_time <= parse_timestamp(end))


def _fresh(record: dict[str, Any], decision_time, limit_seconds: int) -> bool:
    observed = record.get("observed_at", record.get("effective_at", _record_time(record)))
    return decision_time - parse_timestamp(observed) <= timedelta(seconds=limit_seconds)


def derive_decision(task: dict[str, Any]) -> dict[str, Any]:
    decision_time = parse_timestamp(task["decision_time"])
    rules = task["public_rules"]
    flags: set[str] = set()

    camera = _evidence(task, "camera")
    sensors = _evidence(task, "occupancy_sensor")
    events = _evidence(task, "occupancy_event")
    occupancy = "unknown"
    freshness_limit = int(rules.get("freshness_limit_seconds", 0))
    camera_statuses = {item.get("occupancy") for item in camera if item.get("occupancy") in {"occupied", "vacant"} and _active(item, decision_time) and _fresh(item, decision_time, freshness_limit)}
    duplicate_values: dict[str, set[str]] = {}
    for item in events:
        duplicate_values.setdefault(item.get("event_id", item["id"]), set()).add(item.get("occupancy", "unknown"))
    if any(len(values) > 1 for values in duplicate_values.values()):
        flags.add("contradiction_failure")
        occupancy = "unknown"
    elif camera_statuses:
        occupancy = next(iter(camera_statuses))
        sensor_statuses = {item.get("occupancy") for item in sensors if item.get("occupancy") in {"occupied", "vacant"} and _active(item, decision_time) and _fresh(item, decision_time, freshness_limit)}
        if sensor_statuses and sensor_statuses != camera_statuses:
            lag = int(rules.get("sensor_lag_seconds", 0))
            newest = max(parse_timestamp(item.get("observed_at", _record_time(item))) for item in sensors)
            if decision_time - newest <= timedelta(seconds=lag):
                flags.add("contradiction_failure")
                occupancy = "unknown"
    elif sensors:
        statuses = {item.get("occupancy") for item in sensors if item.get("occupancy") in {"occupied", "vacant"} and _fresh(item, decision_time, freshness_limit)}
        occupancy = next(iter(statuses)) if len(statuses) == 1 else "unknown"

    violation = "unknown"
    action = rules.get("required_action_if_unresolved", "abstain")
    if occupancy == "occupied":
        zone_records = _evidence(task, "zone_rule")
        active_zones = [item for item in zone_records if _active(item, decision_time) and _fresh(item, decision_time, freshness_limit)]
        if not active_zones:
            flags.add("stale_evidence_failure" if zone_records else "zone_rule_failure")
        else:
            zone = max(active_zones, key=lambda item: parse_timestamp(item.get("effective_at", item.get("observed_at"))))
            grace = int(rules.get("grace_period_seconds", 0))
            arrivals = [item for item in _evidence(task, "arrival") if item.get("event_time")]
            if arrivals and grace:
                arrival = min(parse_timestamp(item["event_time"]) for item in arrivals)
                if decision_time < arrival:
                    flags.add("temporal_failure")
                    violation = "unknown"
                elif decision_time < arrival + timedelta(seconds=grace):
                    violation = "no_violation"
                else:
                    violation = "violation"
            else:
                permit = [item for item in _evidence(task, "permit") if _active(item, decision_time) and item.get("permit_exception")]
                if permit:
                    violation = "no_violation"
                else:
                    payments = [item for item in _evidence(task, "payment") if item.get("payment_event_time") and parse_timestamp(item["payment_event_time"]) <= decision_time and (not item.get("valid_until") or decision_time <= parse_timestamp(item["valid_until"]))]
                    if payments:
                        violation = "no_violation"
                    elif any(item.get("ocr_confidence", 1) < rules.get("ocr_confidence_threshold", 0) for item in _evidence(task, "ocr")) and camera:
                        violation = "no_violation"
                    elif zone.get("zone_status") == "passenger_loading" and int(zone.get("limit_seconds", 0)) > 0:
                        violation = "no_violation"
                    elif zone.get("prohibits_parking"):
                        violation = "violation"
                    else:
                        flags.add("zone_rule_failure")
    elif occupancy == "vacant":
        violation = "no_violation"

    if "contradiction_failure" in flags or violation == "unknown":
        action = rules.get("required_action_if_unresolved", "abstain")
    elif violation == "violation":
        action = "enforce"
    else:
        action = "do_nothing"
    confidence_policy = rules["confidence_policy"]
    confidence = confidence_policy["unresolved_max"] if occupancy == "unknown" or violation == "unknown" else confidence_policy["resolved_confidence"]
    return {"occupancy_status": occupancy, "violation_status": violation, "recommended_action": action, "confidence": confidence, "rule_flags": sorted(flags)}
