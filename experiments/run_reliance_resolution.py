#!/usr/bin/env python3
"""Post-hoc resolution sweep for the reliance curve (RQ2, H2). **Not a confirmatory test.**

Why this exists
---------------
The confirmatory ladder places three rungs on each feeder, which is enough to test the
pre-registered hypotheses but thin for the *shape* of the relationship between the reactive
support a feeder draws and the harm available from withdrawing it. Three points do not establish
a curve.

This sweep adds intermediate rungs on the same feeders, under the same harness and the same
paired seeds, evaluating only the arm the reliance figure actually plots: the worst admissible
point of the full-width symmetric cap under the curve primitive. It changes no hypothesis, no
endpoint and no interpretation rule, and it is excluded from every confirmatory contrast.

**Status: post-hoc, declared.** Its points are plotted with open markers and are never used to
support a hypothesis test. It was written after the confirmatory results were seen, for the sole
purpose of resolving a curve whose endpoints were already known.

Usage: python3 experiments/run_reliance_resolution.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "reliance_resolution.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051,
         1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117]

#: Intermediate rungs, interleaved with the confirmatory ones (which are not repeated here).
LADDER = {
    "ieee8500": {"load_mult": 0.50, "penetrations": [0.25, 0.75, 1.25, 1.75], "fleet": 600},
    "ieee123": {"load_mult": 1.00, "penetrations": [1.00, 4.00, 8.00, 12.00], "fleet": 46},
}

GRID_N = 7


def one_arm(task):
    from power import confirmatory as C

    spec = ensure_feeder(task["feeder"])
    n, lm = task["fleet"], task["load_mult"]
    with C.Session(spec, seed=task["seed"], n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    p_kw = (task["penetration"] * base_load * lm) / n
    der = C.DER(p_kw=p_kw)
    qb = der.q_cat_b
    grid = [-qb + 2 * qb * i / (GRID_N - 1) for i in range(GRID_N)]

    C.reset_convergence_counters()
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s:
        s.dispatch_legitimate()
        base_conv = C.solve()
        base = s.state()
        pts = []
        for q in grid:
            s.apply(q, "curve")
            conv = C.solve()
            st = s.state()
            pts.append({"q_kvar": round(q, 6),
                        "dJ_band": round(st["j_band"] - base["j_band"], 6),
                        "induced_screen": bool(st["screen"] and not base["screen"]),
                        "converged": conv})
    worst = max(pts, key=lambda p: p["dJ_band"])
    return {"feeder": task["feeder"], "penetration": task["penetration"], "load_mult": lm,
            "seed": task["seed"], "unit_kw": round(p_kw, 4),
            "base_j_band": round(base["j_band"], 6),
            "base_area_over": round(base["area_over"], 6),
            "base_converged": base_conv,
            "legit_q_fleet_kvar": round(base["q_fleet_kvar"], 3),
            "dJ_band": worst["dJ_band"], "induced_screen": worst["induced_screen"],
            "nonconverged": dict(C.NONCONVERGED)}


def main(n_seeds: int = 20):
    tasks = [{"feeder": k, "penetration": p, "load_mult": c["load_mult"],
              "fleet": c["fleet"], "seed": s}
             for k, c in LADDER.items() for p in c["penetrations"] for s in SEEDS[:n_seeds]]
    rows = run_tasks(one_arm, tasks, label="reliance-resolution", every=40)

    summary = []
    for k in LADDER:
        for p in LADDER[k]["penetrations"]:
            g = [r for r in rows if "error" not in r and r["feeder"] == k
                 and r["penetration"] == p]
            if not g:
                continue
            summary.append({
                "feeder": k, "penetration": p, "n": len(g),
                "median_dJ_band": round(statistics.median([r["dJ_band"] for r in g]), 4),
                "legit_q_fleet_kvar": round(statistics.median(
                    [r["legit_q_fleet_kvar"] for r in g]), 2),
                "median_base_area_over": round(statistics.median(
                    [r["base_area_over"] for r in g]), 4),
                "legit_compliant": bool(statistics.median(
                    [r["base_area_over"] for r in g]) <= 0.10),
                "frac_induced_screen": round(
                    sum(1 for r in g if r["induced_screen"]) / len(g), 3),
            })

    OUT.write_text(json.dumps(
        {"status": "post-hoc resolution sweep; NOT a confirmatory test",
         "arm": "worst admissible point of the full-width symmetric cap, curve primitive",
         "seeds": SEEDS[:n_seeds], "ladder": LADDER,
         "rows": rows, "summary": summary}, indent=2))
    print(f"\nwrote {OUT}")
    print("\n%-9s %6s %10s %12s %8s %8s" %
          ("feeder", "pen", "medDJ", "legitQ_kvar", "compl", "screen"))
    for s in summary:
        print("%-9s %6.2f %10.3f %12.1f %8s %8.2f" %
              (s["feeder"], s["penetration"], s["median_dJ_band"],
               s["legit_q_fleet_kvar"], s["legit_compliant"], s["frac_induced_screen"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
