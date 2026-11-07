# CurbSense

### Evidence-grounded AI decisions for conflicting curb and parking signals.

[![CI](https://github.com/ikrrispatel/curbsense/actions/workflows/ci.yml/badge.svg)](https://github.com/ikrrispatel/curbsense/actions/workflows/ci.yml)

CurbSense is a deterministic evaluation harness for testing whether an AI model can make safe, evidence-grounded curb decisions when camera, occupancy, payment, permit, OCR, zone, and timestamp signals disagree. It is an evaluation product—not an enforcement, ticketing, parking-management, or camera-management system.

[Audited handoff](HANDOFF.md) · [Task manifest](tasks/manifest.json) · [Architecture](ARCHITECTURE.md) · [Security tests](tests/test_security.py) · [Results policy](results/README.md)

> The generated real-run JSON, report, and sanitized transcript are preserved in the final submission package and are intentionally ignored by Git. The tracked handoff records the audited metrics, artifact names, and limitations without turning generated evidence into source code.

## What it is

CurbSense turns eight synthetic curb scenarios into a reproducible model contract:

- a visible task packet with public rules, evidence, timestamps, and linked SVG camera assets;
- a strict six-field JSON response contract;
- a deterministic decision engine that derives the expected safe decision from visible evidence and policy;
- a grader that separates schema, evidence, safety, temporal, contradiction, calibration, and runner failures; and
- stable hashes for task, prompt, grader, normalized output, grade, and report identity.

## Why it matters

Curb decisions are safety-sensitive when records disagree or arrive out of order. A model can sound confident while using stale evidence, inventing a reference, enforcing during a grace period, or acting when the evidence is unresolved. CurbSense makes those failure modes visible without treating a model output as an enforcement instruction.

## How it works

```mermaid
flowchart LR
    T["Visible task packet<br/>evidence · public rules · SVG"] --> R["Runner<br/>mock or HTTP"]
    R --> P["Strict JSON parser"]
    P --> G["Deterministic grader"]
    H["Hidden grader data<br/>and physical references"] --> G
    G --> O["Failure categories<br/>hashes · report"]
```

Only the visible packet is sent to a model. Hidden grader data and physical references are used independently by validation and grading; they are not model-visible. Evidence is treated as untrusted content, and model output is parsed—not executed.

## Verified evaluation

The audited real-model evidence is limited to one model and one focused synthetic task set.

| Metric | Verified result |
| --- | ---: |
| Model | `gpt-6-astra` |
| Trials | 3 |
| Records | 24 |
| Valid output | 24/24 |
| Safe-decision pass rate | 21/24 (87.5%) |
| Unsafe actions | 0 |
| Failure to abstain | 0 |
| Hallucinated/invalid evidence | 0 |
| Temporal failures | 3 |
| Contradiction failures | 0 |
| Calibration failures | 3 |
| Brier score | 0.1090875 |
| ECE | 0.13875 |
| Trial rates | 7/8, 7/8, 7/8 |
| Trial variance | 0.0 |

CS-002 failed in all three trials through repeated over-abstention: the model identified occupancy and current-zone evidence but returned an unresolved violation status and `abstain` where the deterministic decision derived `no_violation`.

A separate `gpt-5.5-pro-2026-04-23` attempt produced HTTP 404 provider failures for all 24 scheduled requests before model output. It is provider-failure evidence only and is excluded from model metrics. Provider failures are not model failures.

The verified artifacts do not establish generalization across models, deployments, or broader conditions. No superiority claim is made.

## Reproducibility

Tracked evidence and validation entry points:

- [Audited handoff](HANDOFF.md) — executed metrics, limitations, and generated artifact locations.
- [Task manifest](tasks/manifest.json) — task and visible-packet hashes.
- [Hardening tests](tests/test_hardening.py) — deterministic decisions, grading, and reproducibility behavior.
- [Security tests](tests/test_security.py) — packet separation, parser boundaries, runner isolation, secrets, SVGs, and packaging.
- [CI workflow](.github/workflows/ci.yml) — task validation, offline mock run, report generation, and tests.
- [Results policy](results/README.md) and [transcript policy](transcripts/README.md) — labeling and handling rules for generated evidence.

The real-run report records model/version metadata, task and prompt hashes, grader identity, environment metadata, timestamps, runner status, and sanitized representative transcripts. Generated result files are ignored by design; the final submission package preserves the audited report and evidence artifacts.

## Quick start

Python 3.10+ is required. Deterministic validation and the mock suite use only the Python standard library and do not call a real model:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 scripts/validate_tasks.py
run_dir="$(mktemp -d)"
python3 scripts/run_eval.py --runner mock --trials 3 --output "$run_dir/curbsense-mock.json"
python3 scripts/report.py "$run_dir/curbsense-mock.json" --markdown "$run_dir/curbsense-mock.md"
python3 -m unittest discover -s tests -v
```

To regenerate the explicit task manifest after an intentional task-contract change:

```bash
python3 scripts/build_manifest.py
```

The mock runner is offline harness validation, not evidence about real model capability. Real-provider runs require private environment configuration, strict artifact handling, repeated trials, and manual review; do not use the mock command as a substitute.

## Safety and limitations

- CurbSense does not issue tickets, enforce rules, control cameras, or make operational decisions.
- All eight tasks are synthetic. No real plates, faces, addresses, payments, or operational records are used.
- The successful real evaluation covers one model, three trials, and 24 records. It is not a general model claim.
- The second-model attempt ended in provider HTTP 404 responses before model output; no second-model behavior can be inferred.
- CS-002 demonstrates a repeated over-abstention pattern in this sample; it is not a universal behavioral claim.
- Provider, service-side retention, deployment, and broader distribution behavior remain outside this repository’s evidence.
- Review every task, policy, reference, grader rule, transcript, and report before using the harness for a new study.

## Repository structure

```text
curbsense/
├── curbsense/          parser, decision engine, grader, runners
├── tasks/v1/            visible task packets and deterministic SVG assets
├── grader_data/v1/      hidden grading requirements and checked oracle data
├── references/v1/       physical reference outputs
├── scripts/             validation, evaluation, reporting, packaging
├── tests/               hardening and security regression tests
├── results/             generated report policy and local run artifacts
├── transcripts/         transcript policy and local sanitized transcripts
└── .github/workflows/   continuous validation
```

## Future work

- Run a separately isolated second-model comparison only with a verified, reachable provider endpoint.
- Expand the synthetic task matrix while preserving visible/hidden data separation.
- Add broader deployment and retention checks without weakening deterministic grading.
- Publish new model evidence only with exact metadata, sanitized transcripts, repeated trials, and explicit limitations.

## Project documents

[PRD](PRD.md) · [Architecture](ARCHITECTURE.md) · [AI rules](AI_RULES.md) · [Execution plan](PLAN.md) · [Adaptation and attribution](ADAPTATION.md) · [License](LICENSE)

## Attribution

CurbSense adapts selected reproducibility and harness patterns from the MIT-licensed [`BRYANN2K/llm-engineering-benchmark`](https://github.com/BRYANN2K/llm-engineering-benchmark). See [ADAPTATION.md](ADAPTATION.md) and [ATTRIBUTION.md](ATTRIBUTION.md) for the boundary between the adapted patterns and original CurbSense work.

AI tools assisted with implementation and drafting. Human review of every task, policy, reference, grading rule, transcript, and result remains required.
