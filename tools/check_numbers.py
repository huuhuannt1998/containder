#!/usr/bin/env python3
"""Reverse claim-check: every numeral asserted in any submitted file against results/*.json.

Freeze-gate step 3. For each numeral appearing in the manuscript body, report whether it can be
located in the released result files. This cannot prove a number is used *correctly* -- only a
human reading can -- but it catches the failure mode that matters most here: a number that
survives an edit after the experiment that produced it was re-run, and therefore no longer
corresponds to anything in the artifact.

Usage: python3 manuscripts/CONTAINDER/check_numbers.py
"""
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results"
#: Manuscript sources are not part of the public repository, which ships code and results only.
#: Override with CONTAINDER_MANUSCRIPT to point at them wherever they live.
HERE = Path(os.environ.get("CONTAINDER_MANUSCRIPT",
                           ROOT / "manuscripts" / "CONTAINDER")).resolve()
SECTIONS = HERE / "sections"

#: Numerals that are definitional, structural, or cited from a standard rather than measured.
#: Each needs a stated source, so the whitelist is documented rather than a silencer.
WHITELIST = {
    # feeder / standard constants
    "8500", "9500", "123", "4876", "8531", "1177", "10.8", "12.47", "115", "0.208", "0.48",
    "1547", "1547.3", "2030.5", "62351", "62443", "7628", "84.1", "1.05", "0.95", "1.10",
    "1.20", "0.16", "4.16",
    "2.0", "0.92", "0.98", "1.02", "1.08", "0.44", "5.28", "12.0", "13.11", "600", "7.2",
    "2015", "2018", "2023", "2019", "2020", "2021", "2022", "2024", "2025", "2026", "2029",
    "1490",
    # protocol / design parameters
    "6", "12", "25", "60", "5", "20", "10", "3", "300", "0.5", "0.3", "0.05", "47", "398", "7",
    "255", "0.6", "0.0", "1.0", "2", "4", "8", "9", "11", "21", "0", "1",
    # microbenchmarks live in credsvc.json but are formatted to 2 dp in prose
    "0.03", "0.06", "0.23", "2.3", "4900", "100", "0.77", "0.83",
}

#: Numerals that appear ONLY inside an explicit withdrawal, i.e. the manuscript quotes them in
#: order to retract them. They must NOT resolve against a live result file -- that is the point:
#: the experiments that produced them were superseded and their outputs were moved to
#: ``experiments/results/superseded/``. Each entry names what withdrew it. Leaving these off the
#: whitelist would make the gate fail; putting them in the ordinary whitelist would let a *live*
#: claim quietly reuse a dead number. So they are tracked separately and their context is checked.
WITHDRAWN = {
    "6956":   "legacy time-series integral, superseded by timeseries2.json (solver-state leak)",
    "7030":   "A2/A3 ablation integral, superseded; those arms are aliases of B1 in the harness",
    "3196":   "A4 integral, superseded by timeseries2.json",
    "1700":   "'multiplies exposure roughly 1700x', withdrawn as a quotient of assumed lifetimes",
    "1752.4": "17524/10, the arithmetic behind the withdrawn 1700x figure",
    "17524":  "assumed 2-year lifetime in hours; numerator of the withdrawn 1700x quotient",
    "1750":   "restatement of the same withdrawn quotient",
}

#: Every WITHDRAWN numeral must occur within this many characters of a withdrawal cue, so that a
#: stale number cannot re-enter the paper as a live claim under cover of this exemption.
WITHDRAWAL_CUES = ("withdraw", "superseded", "earlier version", "no longer", "stale",
                   "does not stand", "not stand")
WITHDRAWAL_WINDOW = 700


def harvest_results():
    """Every numeric literal appearing anywhere in the result JSONs, as formatted strings."""
    seen = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                # Result files key by numeric value in several places (fleet sizes, TTLs,
                # outage durations), so the keys are data and must be harvested too.
                if isinstance(k, str):
                    try:
                        walk(float(k) if "." in k else int(k))
                    except ValueError:
                        pass
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
    if not SECTIONS.is_dir():
        print(f"manuscript sources not found at {HERE}.\n"
              "The public repository ships code and results; the manuscript sources are in the\n"
              "archived release. Set CONTAINDER_MANUSCRIPT to their location to run this check.")
        return 0

    pool = harvest_results()
    print(f"harvested {len(pool)} distinct numeric literals from {len(list(RESULTS.glob('*.json')))} result files\n")
    unmatched, escaped = [], []
    # main.tex carries the abstract inline, which is where the headline numerals live; it was
    # previously unchecked, so a stale abstract could pass the gate while every section passed.
    # supplementary.tex holds detail moved out of the body under the length recommendation --
    # moving a number out of the body must not move it out of the gate. highlights.tex is the
    # Elsevier front-matter file and is a claim surface of its own: it carried a superseded
    # headline once already because nothing checked it.
    targets = (sorted(SECTIONS.glob("*.tex"))
               + [HERE / "main.tex", HERE / "supplementary.tex", HERE / "highlights.tex"])
    for tex in targets:
        body = re.sub(r"(?m)^\s*%.*$", "", tex.read_text())
        # Structural notation that is not a measurement: thousands separators (100{,}000),
        # ISO dates (2026-07-30), DOIs, and LaTeX length/column specifiers (0.70\columnwidth).
        body = re.sub(r"(\d)\{,\}(\d)", r"\1\2", body)
        body = re.sub(r"\d{4}-\d{2}-\d{2}", " ", body)
        # A DOI is an identifier, not a quantity: its registrant prefix (10.5281) would otherwise
        # be demanded of the result files. The suffix is already excluded by the lookbehind.
        body = re.sub(r"doi:\s*10\.\d{4,9}/\S+", " ", body)
        body = re.sub(r"0?\.\d+\\(?:column|text|line)width", " ", body)
        for m in re.finditer(r"(?<![\w.])(\d+(?:\.\d+)?)(?![\w])", body):
            n = m.group(1)
            if n in WHITELIST or n in pool:
                continue
            norm = n.rstrip("0").rstrip(".") if "." in n else n
            if norm in pool:
                continue
            ctx = body[max(0, m.start() - 55):m.end() + 25].replace("\n", " ")
            if n in WITHDRAWN:
                win = body[max(0, m.start() - WITHDRAWAL_WINDOW):m.end() + WITHDRAWAL_WINDOW]
                if any(c in win.lower() for c in WITHDRAWAL_CUES):
                    escaped.append((tex.name, n, WITHDRAWN[n]))
                    continue
                unmatched.append((tex.name, n, "WITHDRAWN NUMBER OUTSIDE A WITHDRAWAL: " + ctx))
                continue
            unmatched.append((tex.name, n, ctx))

    if escaped:
        print(f"{len(escaped)} withdrawn numeral(s) quoted inside an explicit withdrawal "
              f"(permitted; each is retracted in the text):")
        for f, n, why in sorted(set(escaped)):
            print(f"  [{f}] {n:>10}   {why}")
        print()
    if not unmatched:
        print("PASS: every non-whitelisted numeral in the manuscript body, abstract, Highlights "
              "and supplementary material appears in results/*.json")
        return 0
    print(f"{len(unmatched)} numerals not located in results/*.json "
          f"(each needs a source, a whitelist entry, or removal):\n")
    for f, n, ctx in unmatched:
        print(f"  [{f}] {n:>10}   ...{ctx}...")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
