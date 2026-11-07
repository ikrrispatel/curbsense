#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, json, platform, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from curbsense import GRADER_VERSION
from curbsense.grader import grade
from curbsense.runners import mock, openai_compatible
from curbsense.schema import load_tasks, sha256, visible_packet

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--runner",choices=["mock","openai_compatible"],default="mock"); p.add_argument("--trials",type=int,default=3); p.add_argument("--output",type=Path,default=Path("results/run.json")); args=p.parse_args()
    root=Path(__file__).resolve().parents[1]; tasks=load_tasks(root); records=[]
    runner=mock if args.runner=="mock" else openai_compatible
    for trial in range(1,args.trials+1):
      for task in tasks:
        started=time.monotonic(); rr=runner(task); latency=rr.latency_ms or int((time.monotonic()-started)*1000)
        grade = None if rr.status != "ok" else __import__("curbsense.grader",fromlist=["grade"]).grade(task,rr.raw_output or "")
        records.append({"task_id":task["task_id"],"trial":trial,"task_hash":sha256(task),"prompt_hash":sha256(visible_packet(task)),"model":rr.model,"model_version":rr.model,"settings":{"temperature":0},"grader_version":GRADER_VERSION,"environment":{"python":platform.python_version(),"platform":platform.platform()},"timestamp":dt.datetime.now(dt.timezone.utc).isoformat(),"latency_ms":latency,"tokens":rr.tokens,"status":rr.status,"runner_error":rr.error,"raw_output":rr.raw_output,"grade":grade})
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(json.dumps({"schema_version":"1.0","runner":args.runner,"trials":args.trials,"records":records},indent=2,sort_keys=True)+"\n")
    print(json.dumps({"output":str(args.output),"records":len(records),"runner_errors":sum(x["status"]!="ok" for x in records)}))
if __name__ == "__main__": raise SystemExit(main())
