# CurbSense AI and Engineering Rules

1. CurbSense is an evaluation product, never an enforcement system.
2. The primary grader never calls an LLM.
3. The grader is deterministic for identical inputs.
4. Gold, references, and hidden rubric data never enter model-visible context.
5. Invalid JSON is never silently repaired.
6. Invented and duplicate evidence are detected.
7. Unsafe recommendations and failure to abstain are separate categories.
8. Runner failures are never model failures.
9. Gold labels cannot be changed to improve results.
10. Synthetic or properly licensed data only; no secrets or personal data.
11. Every task has a physical reference solution and independent derived decision.
12. Every grading rule has passing and failing tests.
13. Every result records task, prompt, grader, model, environment, and deterministic identity hashes.
14. Mock results are harness validation only; no model limitation claim exists without real transcripts.
