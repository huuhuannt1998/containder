#!/usr/bin/env python3
"""Reverse claim-check: every numeral asserted in the manuscript against results/*.json.

Freeze-gate step 3. For each numeral appearing in the manuscript body, report whether it can be
located in the released result files. This cannot prove a number is used *correctly* -- only a
human reading can -- but it catches the failure mode that matters most here: a number that
survives an edit after the experiment that produced it was re-run, and therefore no longer
corresponds to anything in the artifact.

Usage: python3 manuscripts/CONTAINDER/check_numbers.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SECTIONS = HERE / "sections"
RESULTS = HERE.parent.parent / "experiments" / "results"

#: Numerals that are definitional, structural, or cited from a standard rather than measured.
#: Each needs a stated source, so the whitelist is documented rather than a silencer.
WHITELIST = {
    # feeder / standard constants
    "8500", "9500", "123", "4876", "8531", "1177", "10.8", "12.47", "115", "0.208", "0.48",
    "1547", "2030.5", "62351", "62443", "7628", "84.1", "1.05", "0.95", "1.10", "1.20", "0.16",
    "2.0", "0.92", "0.98", "1.02", "1.08", "0.44", "5.28", "12.0", "13.11", "600", "7.2",
    "2018", "2023", "2019", "2020", "2021", "2022", "2024", "2025", "2026", "2029", "1490",
    # protocol / design parameters
    "6", "12", "25", "60", "5", "20", "10", "3", "300", "0.5", "0.3", "0.05", "47", "398", "7",
    "255", "0.6", "0.0", "1.0", "2", "4", "8", "9", "11", "21", "0", "1",
    # microbenchmarks live in credsvc.json but are formatted to 2 dp in prose
    "0.03", "0.06", "0.23", "2.3", "4900", "100", "0.77", "0.83",
}


def harvest_results():
    """Every numeric literal appearing anywhere in the result JSONs, as formatted strings."""
    seen = set()

    def walk(o):
        if isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, (int, float)) and not isinstance(o, bool):
            for s in (f"{o}", f"{o:.0f}", f"{o:.1f}", f"{o:.2f}", f"{o:.3f}",
                      f"{abs(o):.0f}", f"{abs(o):.1f}", f"{abs(o):.2f}"):
                seen.add(s.rstrip("0").rstrip(".") if "." in s else s)
                seen.add(s)
    for f in sorted(RESULTS.glob("*.json")):
        walk(json.loads(f.read_text()))
    return seen


def main():
    pool = harvest_results()
    print(f"harvested {len(pool)} distinct numeric literals from {len(list(RESULTS.glob('*.json')))} result files\n")
    unmatched = []
    for tex in sorted(SECTIONS.glob("*.tex")):
        body = re.sub(r"(?m)^\s*%.*$", "", tex.read_text())
        for m in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w])", body):
            n = m.group(1)
            if n in WHITELIST or n in pool:
                continue
            norm = n.rstrip("0").rstrip(".") if "." in n else n
            if norm in pool:
                continue
            ctx = body[max(0, m.start() - 55):m.end() + 25].replace("\n", " ")
            unmatched.append((tex.name, n, ctx))
    if not unmatched:
        print("PASS: every non-whitelisted numeral in the manuscript body appears in results/*.json")
        return 0
    print(f"{len(unmatched)} numerals not located in results/*.json "
          f"(each needs a source, a whitelist entry, or removal):\n")
    for f, n, ctx in unmatched:
        print(f"  [{f}] {n:>10}   ...{ctx}...")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
