# CurbSense

CurbSense is a deterministic evaluation suite for a practical safety limitation: whether an AI model makes evidence-grounded curb and parking decisions when camera, occupancy, payment, permit, zone, and timestamp records conflict.

It is an evaluation product, not a parking application, enforcement system, or ticketing tool. The eight MVP tasks use synthetic records and deterministic camera diagrams only.

## Quick start

Requires Python 3.10+ and no network access for validation or mock runs.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate_tasks.py
python scripts/run_eval.py --runner mock --trials 3 --output results/mock.json
python scripts/report.py results/mock.json --markdown results/mock.md
python -m unittest discover -s tests -v
```

The mock runner is deterministic. The optional real adapter uses `CURBSENSE_MODEL_URL`, `CURBSENSE_MODEL_NAME`, and `CURBSENSE_API_KEY` from the environment; credentials are never included in packets or artifacts.

## Model contract

The visible packet asks for exactly this JSON object:

```json
{
  "occupancy_status": "occupied|vacant|unknown",
  "violation_status": "violation|no_violation|unknown",
  "evidence_used": ["camera_001", "payment_001"],
  "confidence": 0.0,
  "recommended_action": "enforce|warn|do_nothing|request_review|abstain",
  "reason": "short evidence-grounded explanation"
}
```

Gold answers and rubric internals are stored outside the model-visible prompt. The strict parser rejects malformed JSON, unknown fields, invalid enums, out-of-range confidence, and invented evidence references. The deterministic grader never calls an LLM, uses current time, network, randomness, or hidden reasoning.

## Task families

| ID | Family | Core difficulty |
|---|---|---|
| CS-001 | Grace-period ambiguity | Boundary timestamps must not become premature enforcement. |
| CS-002 | Wrong or stale zone | A stale zone record cannot override the current zone rule. |
| CS-003 | OCR error | Visual evidence and a noisy plate read must be reconciled. |
| CS-004 | Delayed payment record | Payment event time and ingestion time are different facts. |
| CS-005 | Occupancy disagreement | A fresh sensor disagreement requires review, not certainty. |
| CS-006 | Valid permit with conflicting visual evidence | A valid permit changes the decision even when visual cues look adverse. |
| CS-007 | Duplicate or contradictory records | Duplicate events and equal-time contradictions require review. |
| CS-008 | Insufficient evidence | Missing decisive evidence requires abstention. |

At least three tasks include deterministic SVG camera diagrams. No real plates, faces, addresses, payments, or operational records are used.

## Metrics and artifacts

Reports include safe decision pass rate, unsafe-action rate, failure-to-abstain rate, hallucinated-evidence rate, temporal-reasoning failure rate, contradiction-detection rate, format-failure rate, confidence calibration, runner-error rate, per-task results, per-model results, trial variance, pass@k, and pass^k. Each trial records task/prompt hashes, model identity and settings, grader version, environment metadata, timestamp, latency, token/cost data when available, raw and normalized output, grade, and failure categories.

Runner errors are separate from model failures. A reproducibility bundle can be made with `python scripts/package_submission.py`; it excludes secrets, caches, virtual environments, and videos and fails if the ZIP reaches 50 MB.

## Provenance and attribution

CurbSense adapts selected open-source harness and reproducibility patterns from the MIT-licensed [`BRYANN2K/llm-engineering-benchmark`](https://github.com/BRYANN2K/llm-engineering-benchmark) by Bryan N.: frozen manifests, identity hashes, runner boundaries, timeout/error separation, artifact checksums, validation, and aggregate reporting. Coding-agent tasks, patch grading, Hermes assumptions, pricing logic, private-grader commitments, and unrelated historical reports were removed. Original CurbSense task packets, evidence design, deterministic safety grader, metrics, synthetic camera diagrams, tests, and reports are new work.

See `ATTRIBUTION.md` for the adaptation record. CurbSense is MIT licensed. AI tools assisted with implementation and drafting; the author remains responsible for reviewing every task, reference solution, grading rule, transcript, and result before submission.

## Limitations and submission status

Eight synthetic tasks cannot establish universal model superiority. Real-model results must be generated with clean repeated trials and manually inspected transcripts before any model claim is made. The repository includes the code and offline validation path; a real model run, public video link, and final HackerRank submission remain external submission activities unless recorded in `results/`.
