#!/usr/bin/env python3
"""Explicitly build the checked-in manifest; validation itself is side-effect-free."""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curbsense.schema import load_tasks, sha256, visible_packet

root = Path(__file__).resolve().parents[1]
tasks = load_tasks(root)
manifest = {"schema_version": "2.0", "manifest": [{"task_id": t["task_id"], "task_hash": sha256(t), "prompt_hash": sha256(visible_packet(t, root))} for t in tasks]}
(root / "tasks" / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"written": "tasks/manifest.json", "task_count": len(tasks)}))
