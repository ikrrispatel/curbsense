# HANDOFF

## Goal

Maintain a deterministic, evidence-grounded CurbSense evaluation harness and complete the final security milestone before any real-model trials.

## Current State

The hardened deterministic grader is pushed on `origin/main`. Eight tasks and their physical reference outputs are validated. The starting commit for this milestone is `3707bb47f7dc6280e5c89d96f71f34b7b608ee5b`; the repository was clean at that point. Mock validation is harness validation only, not real-model evidence. No real-model trials or limitation claims exist yet.

## Current Task

Complete security verification, document the handoff, run reproducibility and package checks, and push the verified documentation/security commit. Real-model trials are explicitly out of scope for this task.

## Files Being Edited

`HANDOFF.md`, `README.md`, `tests/test_security.py`, `curbsense/schema.py`, `curbsense/runners.py`, and `scripts/package_submission.py`.

## Decisions Made

Visible task packets remain separate from hidden grader data and physical references. Grading derives the expected decision independently from visible evidence and public policy. Evidence is untrusted content, model output is parsed but never executed, asset and provider responses are bounded, API keys stay out of prompts and artifacts, mock grading is offline, and packaging excludes sensitive or transient files.

## Failed Attempts

The first direct invocation of `scripts/test_all` lacked an executable bit and was rerun with `sh`; it passed. One security-test fixture was corrected because its first version did not force a semantic grade failure, and one hash-comparison helper was corrected to use the actual `deterministic_grade_hash` field; the final checks pass.

## Known Bugs

No known deterministic grader or packaging bug is blocking the handoff. Real-provider behavior, credential handling outside this repository, service-side retention, and deployment controls remain unverified until real-model trials and provider review.

## Next Step

The exact next step is security verification followed by real-model trials. Security verification must finish first; this task runs no real-model trials and makes no submission-readiness claim.
