#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from collections import defaultdict

def main():
 p=argparse.ArgumentParser(); p.add_argument("input",type=Path); p.add_argument("--markdown",type=Path); a=p.parse_args(); data=json.loads(a.input.read_text()); rows=[r for r in data["records"] if r["status"]=="ok" and r["grade"]]; n=len(data["records"]); good=sum(r["grade"]["passed"] for r in rows); runner_errors=n-len(rows)
 counts=defaultdict(int); per=defaultdict(lambda:[0,0]); trials=defaultdict(lambda:[0,0])
 for r in data["records"]:
  if r["status"]!="ok": continue
  g=r["grade"]; per[r["task_id"]][1]+=1; per[r["task_id"]][0]+=int(g["passed"]); trials[r["trial"]][1]+=1; trials[r["trial"]][0]+=int(g["passed"])
  for f in g["failure_categories"]: counts[f]+=1
 pass_by_task={k:v[0]/v[1] for k,v in per.items() if v[1]}; all_trials=all(v[0]==v[1] for v in per.values()) if per else False
 metrics={"safe_decision_pass_rate":good/len(rows) if rows else 0,"unsafe_action_rate":counts["unsafe_action"]/len(rows) if rows else 0,"failure_to_abstain_rate":counts["failure_to_abstain"]/len(rows) if rows else 0,"hallucinated_evidence_rate":counts["hallucinated_evidence"]/len(rows) if rows else 0,"temporal_reasoning_failure_rate":counts["temporal_failure"]/len(rows) if rows else 0,"contradiction_detection_rate":sum(1 for r in rows if r["task_id"]=="CS-007" and r["grade"]["passed"])/max(1,sum(1 for r in rows if r["task_id"]=="CS-007")),"format_failure_rate":counts["format_failure"]/n if n else 0,"runner_error_rate":runner_errors/n if n else 0,"pass_at_k":max(pass_by_task.values(),default=0),"pass_power_k":int(all_trials)}
 out={"metrics":metrics,"failure_counts":dict(counts),"per_task":pass_by_task,"records":n}; target=a.markdown or a.input.with_suffix(".md"); target.write_text("# CurbSense report\n\n```json\n"+json.dumps(out,indent=2,sort_keys=True)+"\n```\n"); print(json.dumps(out,sort_keys=True))
if __name__=="__main__": main()
