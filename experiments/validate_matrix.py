#!/usr/bin/env python3
"""Validate and hash the pre-registered experiment matrix.

Emits the SHA-256 of ``scenario_matrix.yaml`` (the pre-registration anchor) and, if PyYAML
is available, a structural summary + cell counts. The hash is computed over the raw file
bytes, so it works with or without PyYAML.

Usage:  python3 experiments/validate_matrix.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

MATRIX = Path(__file__).resolve().parent / "scenario_matrix.yaml"


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if not MATRIX.exists():
        print(f"ERROR: {MATRIX} not found", file=sys.stderr)
        return 1

    digest = sha256_of(MATRIX)
    print(f"scenario_matrix.yaml SHA-256: {digest}")

    try:
        import yaml
    except ImportError:
        print("(PyYAML not installed; skipping structural enumeration. Hash above is the "
              "pre-registration anchor.)")
        return 0

    m = yaml.safe_load(MATRIX.read_text())
    baselines = m.get("baselines", {})
    factors = m.get("factors", {})
    pf = m.get("design", {}).get("primary_factorial", {})

    print(f"baselines: {len(baselines)}  ({', '.join(baselines)})")
    for name, levels in factors.items():
        print(f"  factor {name}: {len(levels)} levels")

    fa = factors.get(pf.get("factor_a"), [])
    fb = factors.get(pf.get("factor_b"), [])
    primary_cells = len(fa) * len(fb)
    print(f"primary factorial ({pf.get('factor_a')} x {pf.get('factor_b')}): "
          f"{len(fa)} x {len(fb)} = {primary_cells} cells")

    ofat = sum(len(factors[f]) for f in m.get("core_ablations", []) if f in factors)
    sb = m.get("seed_budget", {})
    seeds = sb.get("seeds_per_family", 0)
    days = sb.get("feeder_days_per_season", 0) * len(sb.get("seasons", []))
    print(f"primary-factorial runs (x{len(baselines)} baselines, {seeds} seeds, {days} days): "
          f"{primary_cells * len(baselines) * seeds * days}")
    print(f"core OFAT cells (one-factor-at-a-time around B5 reference): {ofat}")
    print("OK: matrix is structurally well-formed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
