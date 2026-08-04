#!/usr/bin/env python3
"""Verify Elsevier Highlights: 3-5 bullets, each <=85 characters including spaces.

The manuscript sources are not part of the public repository, which ships code and results only.
Set ``CONTAINDER_MANUSCRIPT`` to their location to run this check against them.
"""
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
MANUSCRIPT = pathlib.Path(os.environ.get(
    "CONTAINDER_MANUSCRIPT", ROOT / "manuscripts" / "CONTAINDER")).resolve()
src = MANUSCRIPT / "highlights.tex"

if not src.is_file():
    print(f"highlights.tex not found at {src}.\n"
          "The public repository ships code and results; the manuscript sources are in the\n"
          "archived release. Set CONTAINDER_MANUSCRIPT to their location to run this check.")
    sys.exit(0)

items = re.findall(r"\\item\s+(.*)", src.read_text())
ok = True
for t in items:
    n = len(t.strip())
    if n > 85:
        ok = False
    print(f"{'OK ' if n <= 85 else 'OVER'} {n:>3} chars | {t.strip()}")
if not (3 <= len(items) <= 5):
    print(f"FAIL: {len(items)} bullets (need 3-5)")
    ok = False
else:
    print(f"OK  {len(items)} bullets (need 3-5)")
sys.exit(0 if ok else 1)
