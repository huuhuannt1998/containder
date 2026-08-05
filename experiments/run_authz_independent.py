#!/usr/bin/env python3
"""The H1 shape contrast, re-searched with every candidate evaluated independently. (validation)

Why this exists
---------------
:mod:`experiments.run_sweep_path` found that the confirmatory harness's sequential grid walk --
which evaluates an authorized set inside one session, so each candidate inherits the regulator
state the previous one left -- selects a different worst admissible point from independent
evaluation in twelve of thirty-two arms, and that independent evaluation finds a *higher* maximum
in eleven of them, by over 100% in two. The manuscript therefore had to report its optima as
lower bounds with a sweep-order-dependent slack, which is weaker than the claim the experiment was
designed to make.

This removes that slack for the contrast the claim actually rests on. The exact matched-width H1
pair -- Q1 at ``c = 0.25 Qb`` against Q2 at ``phi = 0.50 Qb``, both of width ``0.50 Qb`` -- is
re-searched with every one of the seven candidates in each set applied to a *freshly established
legitimate equilibrium*, which is the oracle-adversary model the manuscript describes: an
adversary holding a credential scoped to a set plays one point against the running feeder.

The comparison of interest is not whether the absolute optima move -- they do, and by how much is
reported -- but whether the *contrast* between the two set shapes survives, since that is H1.

This tests no pre-registered hypothesis. It is reported as a validation of the confirmatory
result, not as a replacement for it.

Usage: python3 experiments/run_authz_independent.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder
from experiments.stats import paired_contrast, holm

OUT = Path(__file__).resolve().parent / "results" / "authz_independent.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051,
         1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117]

GRID_N = 7
FLEET = {"ieee8500": 600, "ieee123": 46}
LOAD_MULT = {"ieee8500": 0.50, "ieee123": 1.00}

#: Exactly the cells the manuscript's H1 table reports.
CELLS = [("ieee123", 2.0, "curve"), ("ieee123", 6.0, "curve"), ("ieee123", 10.0, "curve"),
         ("ieee123", 6.0, "setpoint"), ("ieee8500", 0.5, "curve"), ("ieee8500", 1.0, "curve"),
         ("ieee8500", 1.5, "curve"), ("ieee8500", 1.5, "setpoint")]


def _linspace(a, b, n):
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def one_arm(task):
    """One (feeder, penetration, primitive, seed): both sets, every candidate evaluated fresh."""
    from power import confirmatory as C

    key, pen, prim, seed = task["feeder"], task["penetration"], task["primitive"], task["seed"]
    spec = ensure_feeder(key)
    n, lm = FLEET[key], LOAD_MULT[key]
    with C.Session(spec, seed=seed, n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    der = C.DER(p_kw=(pen * base_load * lm) / n)
    qb = der.q_cat_b

    grids = {
        "Q1 cap |q|<=0.25Qb": [round(x, 6) for x in _linspace(-0.25 * qb, 0.25 * qb, GRID_N)],
        "Q2 floor q<=-0.50Qb": [round(x, 6) for x in _linspace(-qb, -0.50 * qb, GRID_N)],
    }

    C.reset_convergence_counters()
    out = {"feeder": key, "penetration": pen, "primitive": prim, "seed": seed, "sets": {}}
    for label, grid in grids.items():
        pts = []
        for q in grid:
            # A fresh compile per candidate: the discrete device state is re-established from the
            # legitimate equilibrium rather than inherited from the previous candidate.
            with C.Session(spec, seed=seed, n_pv=n, load_mult=lm, der=der) as s:
                s.dispatch_legitimate()
                C.solve()
                base = s.state()["j_band"]
                s.apply(q, prim)
                C.solve()
                pts.append({"q_kvar": q, "q_frac_qb": round(q / qb, 4) if qb else 0.0,
                            "dJ_band": round(s.state()["j_band"] - base, 6)})
        worst = max(pts, key=lambda p: p["dJ_band"])
        out["sets"][label] = {"points": pts, "max_dJ_band": worst["dJ_band"],
                              "argmax_q_frac_qb": worst["q_frac_qb"]}
    out["nonconverged"] = dict(C.NONCONVERGED)
    return out


def main(n_seeds: int = 20):
    tasks = [{"feeder": f, "penetration": p, "primitive": pr, "seed": s}
             for (f, p, pr) in CELLS for s in SEEDS[:n_seeds]]
    rows = run_tasks(one_arm, tasks, label="authz-independent", every=16)

    Q1, Q2 = "Q1 cap |q|<=0.25Qb", "Q2 floor q<=-0.50Qb"
    contrasts = []
    for (f, p, pr) in CELLS:
        g = sorted([r for r in rows if "error" not in r and r["feeder"] == f
                    and abs(r["penetration"] - p) < 1e-9 and r["primitive"] == pr],
                   key=lambda r: r["seed"])
        if not g:
            continue
        a = [r["sets"][Q1]["max_dJ_band"] for r in g]
        b = [r["sets"][Q2]["max_dJ_band"] for r in g]
        # paired_contrast(treat, base) reports treat - base; H1 asks whether Q1 exceeds Q2.
        c = paired_contrast(a, b, label=f"{f} pen{p:g} {pr}")
        c.update({"feeder": f, "penetration": p, "primitive": pr,
                  "median_max_Q1": round(statistics.median(a), 4),
                  "median_max_Q2": round(statistics.median(b), 4),
                  "median_argmax_Q1_frac_qb": round(
                      statistics.median([r["sets"][Q1]["argmax_q_frac_qb"] for r in g]), 4),
                  "median_argmax_Q2_frac_qb": round(
                      statistics.median([r["sets"][Q2]["argmax_q_frac_qb"] for r in g]), 4),
                  "h1_supported": bool(c["ci_lo"] is not None and c["ci_lo"] > 0)})
        contrasts.append(c)
    holm(contrasts, key="p_sign")

    OUT.write_text(json.dumps({
        "status": "post-hoc validation; tests no hypothesis",
        "question": "does the H1 shape contrast survive when every admissible point is evaluated "
                    "from a freshly established legitimate equilibrium rather than swept "
                    "sequentially?",
        "pair": {"Q1": Q1, "Q2": Q2, "matched_width_qb": 0.50},
        "grid_n": GRID_N, "cells": [list(c) for c in CELLS], "seeds": SEEDS[:n_seeds],
        "rows": rows, "contrasts": contrasts}, indent=2))
    print(f"\nwrote {OUT}\n")
    hdr = "%-9s %5s %-9s %4s %10s %10s %11s %-20s %s" % (
        "feeder", "pen", "primitive", "n", "max Q1", "max Q2", "Q1-Q2", "95% CI", "H1")
    print(hdr); print("-" * len(hdr))
    for c in contrasts:
        print("%-9s %5.1f %-9s %4d %10.2f %10.2f %11.2f [%7.2f,%7.2f] %s" % (
            c["feeder"], c["penetration"], c["primitive"], c["n"],
            c["median_max_Q1"], c["median_max_Q2"], c["median_paired_diff"],
            c["ci_lo"], c["ci_hi"], "yes" if c["h1_supported"] else "NO"))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
