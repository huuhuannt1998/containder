#!/usr/bin/env python3
"""Does the sequential grid sweep bias the worst admissible point it selects? (post-hoc validation)

Why this exists
---------------
:mod:`experiments.run_authz_shape` evaluates an authorization set by walking its grid in order
inside one OpenDSS session: it establishes the legitimate equilibrium, then applies each candidate
reactive point in turn without resetting. Regulator taps are discrete and carry across, so each
grid point inherits the tap state the previous point left. The oracle-adversary framing the
manuscript uses is different --- an adversary holding a credential scoped to a set plays *one*
point against the running feeder --- and the two coincide only if tap state does not carry.

The solver-validation study found that it does carry: pinning the taps collapses a large
disagreement between two implementations of the same control law. That makes this a question about
the harness's own numbers rather than about a modelling choice, so it is measured here.

Two evaluations of the identical grid:

  ``sequential``  -- exactly as ``run_authz_shape`` sweeps it, one session, no reset;
  ``independent`` -- each candidate applied to a freshly established legitimate equilibrium.

What matters is not whether the two agree point-for-point but whether they select the same worst
admissible point and report a comparable maximum, because that maximum is the reported endpoint.

This tests no hypothesis and is excluded from every confirmatory contrast.

Usage: python3 experiments/run_sweep_path.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "sweep_path.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039]

#: Top rung of each feeder's confirmatory ladder, where the contrast is largest.
STATES = {
    "ieee8500": {"load_mult": 0.50, "fleet": 600, "penetration": 1.50},
    "ieee123": {"load_mult": 1.00, "fleet": 46, "penetration": 10.00},
}

GRID_N = 7          # the confirmatory grid resolution
PRIMITIVES = ("curve", "setpoint")


def one_arm(task):
    from power import confirmatory as C

    cfg = STATES[task["feeder"]]
    spec = ensure_feeder(task["feeder"])
    n, lm, pen = cfg["fleet"], cfg["load_mult"], cfg["penetration"]
    with C.Session(spec, seed=task["seed"], n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    der = C.DER(p_kw=(pen * base_load * lm) / n)
    qb = der.q_cat_b
    grid = [-qb + 2 * qb * i / (GRID_N - 1) for i in range(GRID_N)]
    prim = task["primitive"]

    C.reset_convergence_counters()
    # --- sequential: one session, no reset between candidates (what the harness does) --------
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s:
        s.dispatch_legitimate()
        C.solve()
        base = s.state()["j_band"]
        base_taps = C.tap_positions()
        seq = []
        for q in grid:
            s.apply(q, prim)
            C.solve()
            seq.append(round(s.state()["j_band"] - base, 6))
        seq_taps_moved = C.count_tap_operations(base_taps, C.tap_positions())

    # --- independent: each candidate from a freshly established legitimate equilibrium ------
    ind = []
    for q in grid:
        with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s2:
            s2.dispatch_legitimate()
            C.solve()
            b = s2.state()["j_band"]
            s2.apply(q, prim)
            C.solve()
            ind.append(round(s2.state()["j_band"] - b, 6))

    ia = max(range(GRID_N), key=lambda i: seq[i])
    ib = max(range(GRID_N), key=lambda i: ind[i])
    mx_s, mx_i = seq[ia], ind[ib]
    return {
        "feeder": task["feeder"], "seed": task["seed"], "primitive": prim,
        "grid_q_frac_qb": [round(q / qb, 4) for q in grid],
        "sequential_dJ": seq, "independent_dJ": ind,
        "sequential_argmax_idx": ia, "independent_argmax_idx": ib,
        "argmax_agrees": ia == ib,
        "sequential_max_dJ": round(mx_s, 6), "independent_max_dJ": round(mx_i, 6),
        "max_rel_diff": round(abs(mx_i - mx_s) / abs(mx_s), 6) if mx_s else None,
        "sign_agrees": bool((mx_s > 0) == (mx_i > 0)),
        "sequential_taps_moved_over_sweep": seq_taps_moved,
        "nonconverged": dict(C.NONCONVERGED),
    }


def main(n_seeds: int = 8):
    tasks = [{"feeder": f, "primitive": p, "seed": s}
             for f in STATES for p in PRIMITIVES for s in SEEDS[:n_seeds]]
    rows = run_tasks(one_arm, tasks, label="sweep-path", every=8)

    summary = []
    for f in STATES:
        for p in PRIMITIVES:
            g = [r for r in rows if "error" not in r
                 and r["feeder"] == f and r["primitive"] == p]
            if not g:
                continue
            summary.append({
                "feeder": f, "primitive": p, "n": len(g),
                "n_argmax_agrees": sum(1 for r in g if r["argmax_agrees"]),
                "n_sign_agrees": sum(1 for r in g if r["sign_agrees"]),
                "median_max_rel_diff": round(
                    statistics.median([r["max_rel_diff"] for r in g if r["max_rel_diff"]
                                       is not None]), 4),
                "max_max_rel_diff": round(
                    max(r["max_rel_diff"] for r in g if r["max_rel_diff"] is not None), 4),
                "median_sequential_max_dJ": round(
                    statistics.median([r["sequential_max_dJ"] for r in g]), 4),
                "median_independent_max_dJ": round(
                    statistics.median([r["independent_max_dJ"] for r in g]), 4),
                "median_taps_moved_over_sweep": statistics.median(
                    [r["sequential_taps_moved_over_sweep"] for r in g]),
            })

    OUT.write_text(json.dumps({
        "status": "post-hoc validation; tests no hypothesis",
        "question": "does sweeping the authorized grid sequentially, without resetting the "
                    "discrete device state between candidates, change which admissible point is "
                    "selected as worst or what harm it is credited with?",
        "states": STATES, "grid_n": GRID_N, "primitives": list(PRIMITIVES),
        "seeds": SEEDS[:n_seeds], "rows": rows, "summary": summary}, indent=2))
    print(f"\nwrote {OUT}\n")
    hdr = "%-9s %-9s %4s %9s %9s %11s %11s %9s" % (
        "feeder", "primitive", "n", "argmax=", "sign=", "seq max dJ", "indep max", "rel diff")
    print(hdr); print("-" * len(hdr))
    for s_ in summary:
        print("%-9s %-9s %4d %5d/%-3d %5d/%-3d %11.3f %11.3f %8.1f%%" % (
            s_["feeder"], s_["primitive"], s_["n"],
            s_["n_argmax_agrees"], s_["n"], s_["n_sign_agrees"], s_["n"],
            s_["median_sequential_max_dJ"], s_["median_independent_max_dJ"],
            100 * s_["median_max_rel_diff"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
