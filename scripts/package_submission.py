#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import zipfile
from pathlib import Path

EXCLUDE = {".git", ".venv", "__pycache__", "submission.zip"}
SECRET_PATTERNS = (re.compile(r"BEGIN [A-Z ]+ PRIVATE KEY"), re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"))
VIDEO_SUFFIXES = {".mp4", ".mov", ".webm", ".mkv"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("submission.zip"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    files = []
    for path in root.rglob("*"):
        if path.is_symlink():
            raise SystemExit(f"symlinks are not allowed in the code package: {path}")
        if not path.is_file() or any(part in EXCLUDE for part in path.parts) or path.suffix == ".pyc" or path.suffix == ".zip":
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        if path.suffix.lower() in VIDEO_SUFFIXES:
            raise SystemExit(f"video files are not allowed in the code package: {path}")
        if path.name != ".env.example":
            text = path.read_text(encoding="utf-8", errors="ignore")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                raise SystemExit(f"secret-like content found: {path}")
        files.append(path)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(root))
    size = args.output.stat().st_size
    print(f"{args.output} {size} bytes {len(files)} files")
    return 0 if size < 50 * 1024 * 1024 else 1


if __name__ == "__main__":
    raise SystemExit(main())
