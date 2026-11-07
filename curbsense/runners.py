from __future__ import annotations
import json, os, time, urllib.request
from dataclasses import dataclass
from typing import Any
from .schema import visible_packet

@dataclass
class RunnerResult:
    raw_output: str | None
    status: str
    latency_ms: int
    error: str | None = None
    model: str = "unknown"
    tokens: dict[str, int] | None = None

def mock(task: dict[str, Any]) -> RunnerResult:
    # Deliberately imperfect but deterministic: one safe error exposes the metric taxonomy.
    answer = task["reference_solution"].copy()
    if task["task_id"] == "CS-003": answer["confidence"] = 0.61
    return RunnerResult(json.dumps(answer, sort_keys=True), "ok", 0, model="mock-v1", tokens={"input": 0, "output": 0})

def openai_compatible(task: dict[str, Any]) -> RunnerResult:
    url, key = os.environ.get("CURBSENSE_MODEL_URL"), os.environ.get("CURBSENSE_API_KEY")
    if not url or not key: return RunnerResult(None, "runner_error", 0, "CURBSENSE_MODEL_URL and CURBSENSE_API_KEY are required", os.environ.get("CURBSENSE_MODEL_NAME", "unconfigured"))
    body = {"model": os.environ.get("CURBSENSE_MODEL_NAME", "unknown"), "temperature": 0, "messages": [{"role": "system", "content": "Return only the requested JSON object."}, {"role": "user", "content": json.dumps(visible_packet(task), sort_keys=True)}]}
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as response:
            payload = json.loads(response.read())
        content = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        return RunnerResult(content, "ok", int((time.monotonic() - started) * 1000), model=body["model"], tokens={"input": usage.get("prompt_tokens", 0), "output": usage.get("completion_tokens", 0)})
    except Exception as exc:
        return RunnerResult(None, "runner_error", int((time.monotonic() - started) * 1000), f"{type(exc).__name__}: {exc}", body["model"])
