#!/usr/bin/env bash
# Build the Drive folder described in the problem statement.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/dist/StackSense26_Aman_Tebriwal"
rm -rf "$DEST"
mkdir -p "$DEST/source" "$DEST/outputs"

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
"$PY" -m stacksense recommend "$ROOT/scenarios/public.json" "$ROOT/outputs"

"$PY" - << PY
import shutil
from pathlib import Path
root = Path("$ROOT")
dest = Path("$DEST") / "source"
skip_dirs = {".git", "dist", ".venv", "venv", "__pycache__", ".chrome-profile", "demo", "outputs"}
skip_suffixes = {".mp4"}
for path in root.rglob("*"):
    rel = path.relative_to(root)
    if any(part in skip_dirs for part in rel.parts):
        continue
    if path.suffix in skip_suffixes or path.name == ".env":
        continue
    target = dest / rel
    if path.is_dir():
        target.mkdir(parents=True, exist_ok=True)
    elif path.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
print("copied source")
PY

cp "$ROOT/outputs/"P*_output.json "$DEST/outputs/"
cp "$ROOT/report/Report_Aman_Tebriwal.pdf" "$DEST/Report_Aman_Tebriwal.pdf"
rm -rf "$DEST/source/dist"

"$PY" - << PY
import os
root = "$DEST"
total = 0
for dirpath, _, files in os.walk(root):
    for name in files:
        total += os.path.getsize(os.path.join(dirpath, name))
print(f"folder bytes: {total}")
if total > 1_000_000_000:
    raise SystemExit("submission folder is over 1 GB")
PY

mkdir -p "$ROOT/dist"
rm -f "$ROOT/dist/StackSense26_Aman_Tebriwal.zip"
( cd "$ROOT/dist" && zip -qr StackSense26_Aman_Tebriwal.zip StackSense26_Aman_Tebriwal )
echo "wrote $ROOT/dist/StackSense26_Aman_Tebriwal.zip"
