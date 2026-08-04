#!/usr/bin/env python3
"""Does the attacker's optimum stabilise as its search grid is refined? (post-hoc sensitivity)

The confirmatory experiments search each authorization set on a seven-point grid and report the
maximum. That identifies the worst *tested* admissible point, not the continuous optimum, and the
manuscript says so. Whether the distinction matters is an empirical question: if the selected
maximum stabilises between seven and thirty-one points, the coarse grid is not hiding a worse
adversary and the reported contrast is safe.

This sweep re-runs one representative arm per feeder at grid resolutions 7, 15 and 31, holding
everything else fixed. It tests no hypothesis and is excluded from every confirmatory contrast.

Usage: python3 experiments/run_grid_resolution.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "grid_resolution.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051,
         1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117]

GRIDS = [7, 15, 31]

#: One rung per feeder, at the stressed state where the contrast is largest and a hidden worse
#: point would matter most.
STATES = {
    "ieee8500": {"load_mult": 0.50, "penetration": 1.50, "fleet": 600},
    "ieee123": {"load_mult": 1.00, "penetration": 10.0, "fleet": 46},
}

#: The full-width symmetric cap: the widest set, so the largest space for a finer grid to find
#: something the coarse grid missed.
PRIMITIVE = "curve"


def one_arm(task):
    from power import confirmatory as C

    cfg = STATES[task["feeder"]]
    spec = ensure_feeder(task["feeder"])
    n, lm = cfg["fleet"], cfg["load_mult"]
    with C.Session(spec, seed=task["seed"], n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    p_kw = (cfg["penetration"] * base_load * lm) / n
    der = C.DER(p_kw=p_kw)
    qb = der.q_cat_b
    k = task["grid_n"]
    grid = [-qb + 2 * qb * i / (k - 1) for i in range(k)]

    C.reset_convergence_counters()
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s:
        s.dispatch_legitimate()
        C.solve()
        base = s.state()
        best, best_q = None, None
        for q in grid:
            s.apply(q, PRIMITIVE)
            C.solve()
            dj = s.state()["j_band"] - base["j_band"]
            if best is None or dj > best:
                best, best_q = dj, q
    return {"feeder": task["feeder"], "grid_n": k, "seed": task["seed"],
            "max_dJ_band": round(best, 6),
            "argmax_q_frac_qb": round(best_q / qb, 4) if qb else 0.0,
            "nonconverged": dict(C.NONCONVERGED)}


def main(n_seeds: int = 20):
    tasks = [{"feeder": f, "grid_n": k, "seed": s}
             for f in STATES for k in GRIDS for s in SEEDS[:n_seeds]]
    rows = run_tasks(one_arm, tasks, label="grid-resolution", every=30)

    summary = []
    for f in STATES:
        ref = None
        for k in GRIDS:
            g = [r for r in rows if "error" not in r and r["feeder"] == f and r["grid_n"] == k]
            if not g:
                continue
            med = statistics.median([r["max_dJ_band"] for r in g])
            if ref is None:
                ref = med
            summary.append({
                "feeder": f, "grid_n": k, "n": len(g),
                "median_max_dJ_band": round(med, 4),
                "pct_above_grid7": round(100.0 * (med - ref) / ref, 2) if ref else None,
                "median_argmax_q_frac_qb": round(
                    statistics.median([r["argmax_q_frac_qb"] for r in g]), 4),
            })

    OUT.write_text(json.dumps({
        "status": "post-hoc sensitivity; tests no hypothesis",
        "question": "does the worst tested admissible point stabilise as the grid is refined?",
        "grids": GRIDS, "states": STATES, "primitive": PRIMITIVE,
        "seeds": SEEDS[:n_seeds], "rows": rows, "summary": summary}, indent=2))
    print(f"\nwrote {OUT}\n")
    print("%-9s %7s %5s %16s %14s %10s" %
          ("feeder", "grid", "n", "median max dJ", "vs 7-point", "argmax q/Qb"))
    for s in summary:
        print("%-9s %7d %5d %16.3f %13.2f%% %10.2f" %
              (s["feeder"], s["grid_n"], s["n"], s["median_max_dJ_band"],
               s["pct_above_grid7"], s["median_argmax_q_frac_qb"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
