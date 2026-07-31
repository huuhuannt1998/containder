#!/usr/bin/env python3
"""M1 + M2 + M8: corrected time-series containment on IEEE 8500, with paired inference.

This supersedes ``run_timeseries.py``. Three defects are fixed.

**M2 -- solver-state leak.** The predecessor called ``compile_base()`` once per seed and then
iterated policies against the same live circuit. OpenDSS warm-starts each solution from the
previous converged voltage vector *and* from the current regulator tap and capacitor switch
positions, so every arm after the first inherited the previous arm's attack excursion. The
signature was visible before the attack even began: policies with identical scope and identical
pre-attack trajectory reported 0.015 (first arm) versus 0.025-0.026 (later arms). Measured
directly: an identical clean dispatch yields area 0.014560 from a cold compile and 0.026424
immediately after a full-scope excursion, and recompiling restores 0.014560 exactly. Here every
(seed, state, policy) arm is a fresh compile.

**M1 -- B2 versus B5.** The predecessor's "narrow" envelope was ``(0 kW, 0.6 kvar)``, about 5% of
a 12 kW unit's nameplate and roughly 11% of the +/-44% reactive capability IEEE 1547-2018
Category B mandates. That envelope is physically inert on this feeder -- it induces exactly zero
overvoltage area -- so *any* lifecycle multiplied by it is zero, and a legacy long-lived
credential with a narrow ACL (B2) tied full CONTAINDER (B5) at zero. That tie was an artifact of a
non-conformant envelope, not evidence that scope alone suffices. This script evaluates scope at
the envelope an operator must actually authorize to receive the volt-var service, at which the
instantaneous harm is decidedly non-zero, and the two designs separate on *persistence*.

**M8 -- inference.** Contrasts are computed per seed and aggregated as paired differences with
bootstrap confidence intervals, over at least two operating states, rather than as medians of
independent integrals at n=3.

Usage: python3 experiments/run_timeseries2.py [n_seeds] [horizon_min]
"""
import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500v2 as f

N_PV = 600
T_ATTACK = 5
TTL = 25
H = 60
STATES = {"light_load": 0.30, "normal": 1.00}

#: Authorization scopes as (P command, Q command) worst case within the authorized function set.
#: ``full``  -- adversary holds DERControl: commands both P and Q to the inverter's limits.
#: ``vv1547`` -- adversary confined to the volt-var function set. Active power stays at its
#:              legitimate schedule (the PV goes on generating; the adversary need not touch it)
#:              and only Q is driven, to the IEEE 1547-2018 Category B limit.
#: ``vv_legacy5`` -- the manuscript's original "narrow" envelope, retained for contrast. It does
#:              not deliver volt-var and is shown to be physically inert.
SCOPES = {
    "full":        (f.P_PV_KW, 0.3 * f.P_PV_KW),
    "vv1547":      (f.P_PV_KW, f.Q_1547_KVAR),
    "vv_legacy5":  (0.0, 0.05 * f.P_PV_KW),
}
CLEAN = None   # sentinel: restore legitimate scheduled operation

#: policy -> (scope, lifecycle)
POLICIES = {
    "B1_legacy_full":      ("full",       "legacy"),
    "B2_acl_narrow_1547":  ("vv1547",     "legacy"),
    "B2b_acl_narrow_5pct": ("vv_legacy5", "legacy"),
    "B3_ephemeral_full":   ("full",       "full"),
    "B5_containder_1547":  ("vv1547",     "full"),
    "B5b_containder_5pct": ("vv_legacy5", "full"),
    "A2_no_session":       ("full",       "no_session"),
    "A3_no_cmd_cleanup":   ("full",       "no_cleanup"),
    "A4_full_lifecycle":   ("full",       "full"),
}


def active(lifecycle: str, t: int) -> bool:
    """Is the malicious setpoint still driving the feeder at minute t?"""
    if t < T_ATTACK:
        return False
    if lifecycle in ("legacy", "no_session", "no_cleanup"):
        return True                      # never ends within the horizon
    return t < T_ATTACK + TTL            # full lifecycle: session + cleanup reset at expiry


def run_arm(seed: int, lm: float, scope: str, lifecycle: str) -> dict:
    """One fully isolated policy arm: fresh compile, fresh PV fleet, fresh controls."""
    kw, kvar = SCOPES[scope]
    series, taps_series, trips = [], [], []
    with f.Session(seed=seed, n_pv=N_PV, load_mult=lm) as s:
        prev_taps = f.tap_positions()
        tap_ops = 0
        for t in range(H):
            if active(lifecycle, t):
                f.dispatch(s.names, kw, kvar)
            else:
                f.dispatch_legitimate(s.names)
            f.solve()
            cur = f.tap_positions()
            tap_ops += f.count_tap_operations(prev_taps, cur)
            prev_taps = cur
            series.append(f.overvoltage_area())
            trips.append(f.protection_state()["trip"])
            taps_series.append(tap_ops)
    base = statistics.median(series[:T_ATTACK])
    excess = [max(0.0, v - base) for v in series]
    recovery = None
    for t in range(T_ATTACK, H):
        if excess[t] <= 0.05 and all(e <= 0.05 for e in excess[t:min(t + 3, H)]):
            recovery = t - T_ATTACK
            break
    return {"integral": round(sum(excess), 3),
            "integral_raw": round(sum(series), 3),
            "baseline_area": round(base, 4),
            "peak": round(max(series), 3),
            "recovery_min": recovery,
            "tap_ops": tap_ops,
            "trip_minutes": sum(trips),
            "series": [round(v, 3) for v in series]}


def boot_ci(xs, n=10000, alpha=0.05, seed=7):
    if not xs:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(xs)
    means = sorted(sum(rng.choice(xs) for _ in range(k)) / k for _ in range(n))
    return (round(means[int(alpha / 2 * n)], 3), round(means[int((1 - alpha / 2) * n)], 3))


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    global H
    if len(sys.argv) > 2:
        H = int(sys.argv[2])
    f.chdir_feeder()

    runs = {}   # (state, seed, policy) -> arm
    for st, lm in STATES.items():
        for seed in range(1000, 1000 + n_seeds):
            for pol, (scope, life) in POLICIES.items():
                runs[(st, seed, pol)] = run_arm(seed, lm, scope, life)
            print(f"  .. {st} seed {seed} done", flush=True)

    # ---- paired contrasts, per seed, with bootstrap CIs ------------------------------------
    CONTRASTS = [
        ("A4_full_lifecycle", "A3_no_cmd_cleanup", "lifecycle vs no-command-cleanup (equal scope)"),
        ("A4_full_lifecycle", "A2_no_session", "lifecycle vs no-session (equal scope)"),
        ("A4_full_lifecycle", "B1_legacy_full", "lifecycle vs legacy (equal scope)"),
        ("B5_containder_1547", "B2_acl_narrow_1547", "CONTAINDER vs legacy+narrow ACL @ IEEE 1547 scope"),
        ("B5b_containder_5pct", "B2b_acl_narrow_5pct", "CONTAINDER vs legacy+narrow ACL @ 5% scope"),
        ("B5_containder_1547", "B3_ephemeral_full", "narrow+lifecycle vs ephemeral-only"),
    ]
    contrasts = {}
    for st in STATES:
        for a, b, label in CONTRASTS:
            diffs = [runs[(st, s, b)]["integral"] - runs[(st, s, a)]["integral"]
                     for s in range(1000, 1000 + n_seeds)]
            ratios = [(runs[(st, s, b)]["integral"] / runs[(st, s, a)]["integral"])
                      for s in range(1000, 1000 + n_seeds)
                      if runs[(st, s, a)]["integral"] > 1e-9]
            contrasts[f"{st}|{a}|{b}"] = {
                "label": label,
                "mean_paired_reduction": round(statistics.mean(diffs), 3),
                "median_paired_reduction": round(statistics.median(diffs), 3),
                "ci95_paired_reduction": boot_ci(diffs),
                "mean_ratio": round(statistics.mean(ratios), 3) if ratios else None,
                "ci95_ratio": boot_ci(ratios) if ratios else None,
                "n_seeds_favouring_a": sum(1 for d in diffs if d > 0), "n": len(diffs)}

    agg = {}
    for st in STATES:
        for pol in POLICIES:
            xs = [runs[(st, s, pol)]["integral"] for s in range(1000, 1000 + n_seeds)]
            tp = [runs[(st, s, pol)]["tap_ops"] for s in range(1000, 1000 + n_seeds)]
            tm = [runs[(st, s, pol)]["trip_minutes"] for s in range(1000, 1000 + n_seeds)]
            rc = [runs[(st, s, pol)]["recovery_min"] for s in range(1000, 1000 + n_seeds)]
            agg[f"{st}|{pol}"] = {
                "integral_mean": round(statistics.mean(xs), 3),
                "integral_median": round(statistics.median(xs), 3),
                "integral_ci95": boot_ci(xs),
                "tap_ops_median": statistics.median(tp),
                "trip_minutes_median": statistics.median(tm),
                "recovery_min_median": (statistics.median([r for r in rc if r is not None])
                                        if any(r is not None for r in rc) else None),
                "n_no_recovery": sum(1 for r in rc if r is None)}

    print(f"\n== M2-corrected time series, IEEE 8500, n={n_seeds} paired seeds, horizon {H} min ==")
    for st in STATES:
        print(f"\n-- {st} --")
        print(f"{'policy':22} {'integral':>10} {'ci95':>20} {'taps':>6} {'trip-min':>9} {'recov':>7}")
        for pol in POLICIES:
            a = agg[f"{st}|{pol}"]
            rec = a["recovery_min_median"] if a["n_no_recovery"] == 0 else "none"
            print(f"{pol:22} {a['integral_mean']:>10.1f} {str(a['integral_ci95']):>20} "
                  f"{a['tap_ops_median']:>6.0f} {a['trip_minutes_median']:>9.0f} {str(rec):>7}")
    print("\n-- paired contrasts (positive = the CONTAINDER arm reduces integrated harm) --")
    for k, v in contrasts.items():
        print(f"{k}\n    {v['label']}: mean {v['mean_paired_reduction']:.1f} "
              f"CI95 {v['ci95_paired_reduction']} ratio {v['mean_ratio']} "
              f"({v['n_seeds_favouring_a']}/{v['n']} seeds favour)")

    out = {"agg": agg, "contrasts": contrasts,
           "params": {"t_attack": T_ATTACK, "ttl": TTL, "horizon": H, "n_seeds": n_seeds,
                      "n_pv": N_PV, "scopes": {k: list(v) for k, v in SCOPES.items()},
                      "q_1547_kvar": f.Q_1547_KVAR, "states": STATES},
           "runs": {f"{st}|{s}|{p}": v for (st, s, p), v in runs.items()},
           "note": "Every (state, seed, policy) arm is an independent compile of the IEEE 8500 "
                   "feeder with a fresh PV fleet and fresh regulator/capacitor state, fixing the "
                   "warm-start leak in run_timeseries.py. Integral is of excess overvoltage area "
                   "above each arm's own pre-attack baseline, in p.u.-node-minutes. Base case is "
                   "legitimate PV under an IEEE 1547-2018 Cat B volt-var curve."}
    (Path(__file__).resolve().parent / "results" / "timeseries2.json").write_text(
        json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/timeseries2.json")


if __name__ == "__main__":
    main()
