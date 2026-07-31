#!/usr/bin/env python3
"""M9: credential-lifetime dose-response on IEEE 8500, and the scope-label audit.

Motivation
----------
``run_timeseries2.py`` reports a single lifetime contrast (2.16x at n=20). That number is
**not an independently measured effect size**: the induced overvoltage area accrues at a rate
that is constant while the malicious setpoint is applied, so the integrated harm is
proportional to the number of minutes the credential is honoured. With ``t_attack=5``,
``horizon=60`` and ``ttl=25`` the ratio is forced to at most ``(60-5)/25 = 2.20``, and the
measured 2.159 is that ceiling net of a one-minute recovery tail. Reporting 2.16x as a result
would be reporting the experiment's own parameter choice.

This script measures the underlying relation instead: integrated harm as a function of
credential lifetime, over a TTL grid, at three authorization envelopes and two operating
states. The quantity of interest is the **slope** (harm accrued per minute of retained
credential validity) and the **saturation point** (the exposure window), from which any
containment ratio an operator wants can be derived and, crucially, seen to be a design choice.

Scope-label audit
-----------------
``run_timeseries2.py`` defines ``full = (P_PV_KW, 0.3 * P_PV_KW) = (12.0 kW, 3.6 kvar)`` and
``vv1547 = (P_PV_KW, Q_1547_KVAR) = (12.0 kW, 5.28 kvar)``, while its docstring describes
``full`` as commanding "both P and Q to the inverter's limits". The inverter's reactive limit
in ``feeder8500v2.place_pv`` is ``kvarmax = Q_1547_KVAR = 5.28``. The ``full`` arm therefore
commands **less** reactive power than the arm labelled "narrow ACL", i.e. the envelope named
``full`` is a strict subset of the envelope named ``vv1547``. This is why B2 (5656) exceeds
B1 (3851) in ``timeseries2.json``: not because narrowing increases harm, but because the
labels are inverted. This script evaluates all three envelopes by their numeric value and
names them after that value, so the ordering is auditable.

Usage: python3 experiments/run_ttl_sweep.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500v2 as f

N_PV = 600
T_ATTACK = 5
H = 60
STATES = {"light_load": 0.30, "normal": 1.00}

#: Authorization envelopes as commanded (P kW, Q kvar), named by their numeric value.
#: ``q44_conformant`` is simultaneously (a) the IEEE 1547-2018 Category B reactive capability an
#: operator must authorize to receive volt-var and (b) the inverter's own ``kvarmax``. No larger
#: reactive envelope exists on this DER model, so it is the maximal envelope, not a narrowing.
SCOPES = {
    "q44_conformant": (f.P_PV_KW, f.Q_1547_KVAR),        # (12.0, 5.28)  44% of nameplate
    "q30_partial":    (f.P_PV_KW, 0.30 * f.P_PV_KW),     # (12.0, 3.60)  timeseries2 "full"
    "q5_inert":       (0.0, 0.05 * f.P_PV_KW),           # ( 0.0, 0.60)  timeseries2 "narrow"
}

#: Credential lifetimes in minutes. 55 == H - T_ATTACK, i.e. the credential outlives the
#: exposure window and the arm is behaviourally identical to a legacy long-lived credential;
#: it is included as an internal consistency check, not as a policy.
TTL_GRID = [5, 10, 15, 25, 40, 55]


def run_arm(seed: int, lm: float, scope: str, ttl: int) -> dict:
    """One fully isolated arm: fresh compile, fresh PV fleet, fresh regulator/capacitor state."""
    kw, kvar = SCOPES[scope]
    series, trips = [], []
    nonconv = 0
    with f.Session(seed=seed, n_pv=N_PV, load_mult=lm) as s:
        prev_taps = f.tap_positions()
        tap_ops = 0
        for t in range(H):
            if T_ATTACK <= t < T_ATTACK + ttl:
                f.dispatch(s.names, kw, kvar)
            else:
                f.dispatch_legitimate(s.names)
            if not f.solve():
                nonconv += 1
            cur = f.tap_positions()
            tap_ops += f.count_tap_operations(prev_taps, cur)
            prev_taps = cur
            series.append(f.overvoltage_area())
            trips.append(f.protection_state()["trip"])
    base = statistics.median(series[:T_ATTACK])
    excess = [max(0.0, v - base) for v in series]
    recovery = None
    for t in range(T_ATTACK, H):
        if excess[t] <= 0.05 and all(e <= 0.05 for e in excess[t:min(t + 3, H)]):
            recovery = t - T_ATTACK
            break
    active = excess[T_ATTACK:T_ATTACK + ttl]
    return {"nonconverged_steps": nonconv,
            "integral": round(sum(excess), 3),
            "baseline_area": round(base, 4),
            "mean_excess_per_active_min": round(statistics.mean(active), 4) if active else 0.0,
            "tail_after_expiry": round(sum(excess[T_ATTACK + ttl:]), 3),
            "peak": round(max(series), 3),
            "recovery_min": recovery,
            "tap_ops": tap_ops,
            "trip_minutes": sum(trips)}


def ols(xs, ys):
    """Least-squares slope/intercept and R^2 of y on x."""
    n = len(xs)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    b = sxy / sxx
    a = my - b * mx
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys))
    ss_tot = sum((y - my) ** 2 for y in ys)
    return round(b, 4), round(a, 4), round(1 - ss_res / ss_tot, 6)


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    seeds = list(range(1000, 1000 + n_seeds))
    f.chdir_feeder()

    runs = {}
    total = len(STATES) * len(SCOPES) * len(TTL_GRID) * n_seeds
    i = 0
    for st, lm in STATES.items():
        for sc in SCOPES:
            for ttl in TTL_GRID:
                for sd in seeds:
                    runs[f"{st}|{sc}|{ttl}|{sd}"] = run_arm(sd, lm, sc, ttl)
                    i += 1
                print(f"  .. {st} {sc} ttl={ttl} done ({i}/{total})", flush=True)

    agg, fits = {}, {}
    for st in STATES:
        for sc in SCOPES:
            xs_all, ys_all = [], []
            for ttl in TTL_GRID:
                xs = [runs[f"{st}|{sc}|{ttl}|{s}"]["integral"] for s in seeds]
                rate = [runs[f"{st}|{sc}|{ttl}|{s}"]["mean_excess_per_active_min"] for s in seeds]
                rec = [runs[f"{st}|{sc}|{ttl}|{s}"]["recovery_min"] for s in seeds]
                tap = [runs[f"{st}|{sc}|{ttl}|{s}"]["tap_ops"] for s in seeds]
                agg[f"{st}|{sc}|{ttl}"] = {
                    "integral_mean": round(statistics.mean(xs), 3),
                    "integral_median": round(statistics.median(xs), 3),
                    "integral_min": round(min(xs), 3), "integral_max": round(max(xs), 3),
                    "rate_per_active_min_mean": round(statistics.mean(rate), 4),
                    "tap_ops_median": statistics.median(tap),
                    "recovery_min_median": (statistics.median([r for r in rec if r is not None])
                                            if any(r is not None for r in rec) else None),
                    "n_no_recovery": sum(1 for r in rec if r is None), "n": len(xs)}
                xs_all += [ttl] * len(xs)
                ys_all += xs
            b, a, r2 = ols(xs_all, ys_all)
            fits[f"{st}|{sc}"] = {"slope_per_min": b, "intercept": a, "r2": r2,
                                  "ttl_grid": TTL_GRID, "n_per_ttl": n_seeds}

    print("\n== credential-lifetime dose-response, IEEE 8500, "
          f"n={n_seeds} paired seeds, horizon {H} min ==")
    for st in STATES:
        for sc in SCOPES:
            fit = fits[f'{st}|{sc}']
            print(f"\n-- {st} / {sc} (P={SCOPES[sc][0]} kW, Q={SCOPES[sc][1]} kvar) --")
            print(f"{'ttl':>5} {'integral':>10} {'rate/min':>9} {'taps':>6} {'recov':>7}")
            for ttl in TTL_GRID:
                A = agg[f"{st}|{sc}|{ttl}"]
                rec = A["recovery_min_median"] if A["n_no_recovery"] == 0 else "none"
                print(f"{ttl:>5} {A['integral_mean']:>10.1f} "
                      f"{A['rate_per_active_min_mean']:>9.2f} {A['tap_ops_median']:>6.0f} "
                      f"{str(rec):>7}")
            print(f"   OLS integral ~ ttl: slope {fit['slope_per_min']:.2f} "
                  f"p.u.-node-min per min, intercept {fit['intercept']:.2f}, R2 {fit['r2']:.5f}")

    out = {"agg": agg, "fits": fits,
           "params": {"t_attack": T_ATTACK, "horizon": H, "n_seeds": n_seeds, "n_pv": N_PV,
                      "ttl_grid": TTL_GRID, "states": STATES,
                      "scopes": {k: list(v) for k, v in SCOPES.items()},
                      "q_1547_kvar": f.Q_1547_KVAR, "kva_pv": f.KVA_PV},
           "runs": runs,
           "nonconvergence": {"solves_flagged": f.NONCONVERGED["n"],
                              "solves_retried": f.NONCONVERGED["n_retried"],
                              "policy": "retry cap 2, control-iteration budget tripled on "
                                        "each retry (500 -> 1500 -> 4500); unsettled solves "
                                        "retained and flagged, never dropped"},
           "note": "Integrated induced overvoltage area versus credential lifetime, at three "
                   "authorization envelopes named by their commanded (P kW, Q kvar). Every "
                   "(state, scope, ttl, seed) arm is an independent feeder compile with a fresh "
                   "PV fleet and fresh regulator/capacitor state. The q44_conformant envelope is "
                   "the inverter's own kvarmax and the IEEE 1547-2018 Category B capability, so "
                   "it is the maximal reactive envelope, not a narrowing; q30_partial is the "
                   "envelope run_timeseries2.py labelled 'full', which is a strict subset of it. "
                   "ttl=55 equals horizon minus t_attack and reproduces a legacy long-lived "
                   "credential as an internal consistency check."}
    (Path(__file__).resolve().parent / "results" / "ttl_sweep.json").write_text(
        json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/ttl_sweep.json")


if __name__ == "__main__":
    main()
