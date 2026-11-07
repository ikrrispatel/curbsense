# CurbSense Architecture

The visible task packet, hidden grader data, and reference solution are separate immutable inputs:

```text
tasks/v1/       visible evidence, public policy, question, schema, asset paths
grader_data/v1/ hidden required/relevant evidence and independently checked gold
references/v1/  physically stored reference outputs
curbsense/decision.py  deterministic evidence-to-decision derivation
curbsense/grader.py    parser, support checks, safety checks, derived-decision grading
curbsense/runners.py   offline fixture and one HTTP-compatible adapter
```

The runner sends only `visible_packet(task, root)` to a model. The decision engine uses timezone-aware event times, freshness/effective windows, grace boundaries, payment event time, permit validity, OCR confidence, sensor lag, duplicate event IDs, contradiction policy, and missing-evidence policy. The grader compares model output to the derived decision and records raw output on every failure.

Hashes are separated into task hash, prompt hash, grader-version hash, normalized-output hash, deterministic-grade hash, and report hash. Execution timestamps and latency are volatile metadata and never enter deterministic hashes.

Validation is side-effect-free. `scripts/build_manifest.py` is the explicit manifest-writing command. The mock runner is offline; provider and timeout failures are runner errors and are excluded from model pass rates.
