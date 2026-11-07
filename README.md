# CurbSense

CurbSense evaluates whether AI models make safe, evidence-grounded curb and parking decisions when camera, occupancy, payment, permit, OCR, zone, and timestamp evidence conflict. It is an evaluation product, not an enforcement or ticketing system.

## Quick start

Python 3.10+ is required. Deterministic validation and the mock suite use only the standard library and no network.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/validate_tasks.py
python scripts/build_manifest.py
python scripts/run_eval.py --runner mock --trials 3 --output /tmp/curbsense-mock.json
python scripts/report.py /tmp/curbsense-mock.json --markdown /tmp/curbsense-mock.md
python -m unittest discover -s tests -v
```

Validation is read-only. The manifest is written only by the explicit build command.

## Data separation

- `tasks/v1/` contains only model-visible packets: question, public structured rules, evidence, timezone, output schema, and linked deterministic SVG assets.
- `grader_data/v1/` contains hidden evidence requirements and gold answers used to audit the derived oracle.
- `references/v1/` contains physical reference outputs.

The model never receives hidden grader data or reference files. The deterministic decision engine independently derives occupancy, violation status, and safe action from visible evidence and policy fields. Validation fails if hidden gold disagrees with that derivation. Grading does not compare model output directly to gold.

## Task families

1. Grace-period ambiguity.
2. Wrong or stale zone.
3. OCR error.
4. Delayed payment record.
5. Occupancy disagreement.
6. Valid permit with conflicting visual evidence.
7. Duplicate or contradictory records.
8. Insufficient evidence requiring abstention.

Every camera evidence record has an explicit asset path, and all eight deterministic SVG assets are included in the visible packet when running.

## Output schema

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

The parser rejects malformed or markdown-wrapped JSON, unknown fields, invalid enums, invalid confidence, duplicate or invented evidence, empty or oversized reasons, and unsupported evidence claims. Raw output remains in the run record on every failure.

## Metrics and reproducibility

Reports include pass rate, unsafe-action rate, failure-to-abstain rate, hallucinated-evidence rate, temporal-failure rate, stale/payment/permit/zone/contradiction failures, format-failure rate, runner-error rate, per-task/model results, trial variance, pass@k, pass^k, Brier calibration, ECE, and a deterministic report hash.

Each record separates deterministic identity hashes—task, prompt, grader version, normalized output, and grade—from volatile timestamp and latency metadata. The mock runner is labeled `mock_harness_validation`; it is not real-model evidence. Real-model trials require environment variables from `.env.example`, clean repeated runs, transcripts, cost/runtime reporting, and manual review.

## Attribution and limitations

CurbSense adapts selected harness and reproducibility patterns from the MIT-licensed [`BRYANN2K/llm-engineering-benchmark`](https://github.com/BRYANN2K/llm-engineering-benchmark) by Bryan N. See [ADAPTATION.md](ADAPTATION.md), [ARCHITECTURE.md](ARCHITECTURE.md), [AI_RULES.md](AI_RULES.md), [PLAN.md](PLAN.md), and [PRD.md](PRD.md).

AI tools assisted with implementation and drafting. Human review of every task, policy, reference, grading rule, transcript, and result is required. Eight synthetic tasks cannot establish universal model superiority.
