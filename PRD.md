# CurbSense Product Requirements

CurbSense evaluates whether AI models make safe, evidence-grounded curb and parking decisions when camera, occupancy, payment, permit, zone, OCR, and timestamp evidence conflict. It is an evaluation product, not an enforcement, ticketing, parking-management, or camera-management system.

## MVP

Exactly eight synthetic tasks cover grace-period ambiguity, stale zones, OCR error, delayed payment, occupancy disagreement, valid permit exceptions, duplicate/contradictory records, and insufficient evidence. At least three tasks use deterministic SVG camera assets. No real plates, faces, addresses, payments, or operational records are used.

## Model contract

The model receives only the visible task packet, public rules, evidence, linked deterministic camera assets, question, and required JSON schema. It must return occupancy status, violation status, evidence IDs, confidence, recommended action, and a short reason. Gold answers, references, and hidden evidence requirements are never model-visible.

## Grading and metrics

The grader derives the expected decision from structured evidence and public policy fields. Stored gold answers are an independently checked oracle, not the grading source. Invalid JSON, schema errors, invented or duplicate evidence, unsupported claims, unsafe action, failure to abstain, temporal errors, stale evidence, payment/permit/zone errors, contradiction failures, calibration, and runner errors are reported separately.

## Limitations

Eight synthetic tasks are a focused eval, not evidence of universal model superiority. Real-model claims require clean repeated trials, model metadata, costs/runtime, representative transcripts, and manual review.
