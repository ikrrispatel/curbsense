#!/usr/bin/env python3
from __future__ import annotations
import argparse, zipfile
from pathlib import Path
EXCLUDE={".git",".venv","__pycache__","submission.zip"}
def main():
 p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=Path("submission.zip")); a=p.parse_args(); root=Path(__file__).resolve().parents[1]
 with zipfile.ZipFile(a.output,"w",zipfile.ZIP_DEFLATED) as z:
  for f in root.rglob("*"):
   if not f.is_file() or any(x in EXCLUDE for x in f.parts) or f.name.endswith((".pyc",".zip")): continue
   z.write(f,f.relative_to(root))
 size=a.output.stat().st_size
 print(f"{a.output} {size} bytes"); return 0 if size < 50*1024*1024 else 1
if __name__=="__main__": raise SystemExit(main())
