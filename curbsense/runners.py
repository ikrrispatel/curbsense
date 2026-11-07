from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import visible_packet

MAX_RESPONSE_BYTES = 1_048_576

MODEL_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "occupancy_status",
        "violation_status",
        "evidence_used",
        "confidence",
        "recommended_action",
        "reason",
    ],
    "properties": {
        "occupancy_status": {"type": "string", "enum": ["occupied", "vacant", "unknown"]},
        "violation_status": {"type": "string", "enum": ["violation", "no_violation", "unknown"]},
        "evidence_used": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
        "recommended_action": {"type": "string", "enum": ["enforce", "warn", "do_nothing", "request_review", "abstain"]},
        "reason": {"type": "string"},
    },
}


def _chat_completions_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("model URL must be an HTTP(S) URL without credentials, query, or fragment")
    path = parsed.path.rstrip("/")
    if not path.endswith("/chat/completions"):
        path += "/chat/completions"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))


@dataclass
class RunnerResult:
    raw_output: str | None
    status: str
    latency_ms: int
    error: str | None = None
    model: str = "unknown"
    model_version: str = "unknown"
    settings: dict[str, Any] | None = None
    tokens: dict[str, int] | None = None


def mock(task: dict[str, Any], reference: dict[str, Any], _root: Path) -> RunnerResult:
    answer = dict(reference)
    # Harness fixture only: one controlled calibration miss proves reports can
    # expose a failing trial; it is not real-model evidence.
    if task["task_id"] == "CS-003":
        answer["confidence"] = 0.61
    return RunnerResult(json.dumps(answer, sort_keys=True), "ok", 0, model="mock-v1", model_version="fixture", settings={"temperature": 0}, tokens={"input": 0, "output": 0})


def _safe_error(message: str, key: str | None, url: str | None) -> str:
    value = message
    if url:
        parsed = urllib.parse.urlsplit(url)
        safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
        value = value.replace(url, safe_url)
    value = value.replace(key or "__never__", "[REDACTED]")
    return value[:500]


def openai_compatible(task: dict[str, Any], root: Path) -> RunnerResult:
    url = os.environ.get("CURBSENSE_MODEL_URL")
    key = os.environ.get("CURBSENSE_API_KEY")
    model = os.environ.get("CURBSENSE_MODEL_NAME", "unconfigured")
    settings = {"temperature": "provider_default", "response_format": "json_schema", "timeout_seconds": 60}
    if not url or not key:
        return RunnerResult(None, "runner_error", 0, "model URL and API key are required", model, model, settings)
    started = time.monotonic()
    try:
        endpoint = _chat_completions_url(url)
        # Some reasoning models reject an explicit temperature, so the request
        # intentionally uses the provider default while keeping strict grader validation.
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "Return only the requested JSON object."},
                {"role": "user", "content": json.dumps(visible_packet(task, root), sort_keys=True)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "curbsense_decision", "strict": True, "schema": MODEL_OUTPUT_SCHEMA},
            },
        }
        request = urllib.request.Request(endpoint, data=json.dumps(body).encode("utf-8"), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            content_length = response.headers.get("Content-Length") if hasattr(response, "headers") else None
            if content_length and int(content_length) > MAX_RESPONSE_BYTES:
                raise ValueError("provider response exceeds size limit")
            body_bytes = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body_bytes) > MAX_RESPONSE_BYTES:
                raise ValueError("provider response exceeds size limit")
            payload = json.loads(body_bytes)
        content = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        return RunnerResult(content, "ok", int((time.monotonic() - started) * 1000), model=model, model_version=model, settings=settings, tokens={"input": usage.get("prompt_tokens", 0), "output": usage.get("completion_tokens", 0)})
    except Exception as exc:
        return RunnerResult(None, "runner_error", int((time.monotonic() - started) * 1000), _safe_error(f"{type(exc).__name__}: {exc}", key, url), model, model, settings)
