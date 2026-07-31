#!/usr/bin/env python3
"""Verify Elsevier Highlights: 3-5 bullets, each <=85 characters including spaces."""
import re, sys, pathlib
src = pathlib.Path(__file__).parent / "highlights.tex"
items = re.findall(r"\\item\s+(.*)", src.read_text())
ok = True
for i, t in enumerate(items, 1):
    n = len(t.strip())
    flag = "OK " if n <= 85 else "OVER"
    if n > 85: ok = False
    print(f"{flag} {n:>3} chars | {t.strip()}")
if not (3 <= len(items) <= 5):
    print(f"FAIL: {len(items)} bullets (need 3-5)"); ok = False
else:
    print(f"OK  {len(items)} bullets (need 3-5)")
sys.exit(0 if ok else 1)
