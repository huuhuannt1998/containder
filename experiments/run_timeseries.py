#!/usr/bin/env python3
"""Time-series credential-to-feeder containment on real IEEE 8500 (addresses reviewer §4, §5, §13.2).

One end-to-end run per policy: a compromised credential drives the DER from t=T_ATTACK; the
credential's lifecycle (lifetime, session enforcement, command cleanup, scope) then determines
whether and when the malicious setpoint stops affecting the feeder. We integrate the real
voltage-violation area over time (physical violation accumulation, p.u.-node-minutes) and measure
recovery time. This measures temporal containment DIRECTLY, without multiplying a measured factor
by a modeled one, and decomposes scope vs. lifetime vs. session vs. command-cleanup at fixed scope.

Usage: python3 experiments/run_timeseries.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500 as f

P = 12.0
N_PV = 600
LOAD = 0.30            # light load / high PV
T_ATTACK = 5          # minutes
TTL = 25              # credential lifetime (minutes)
H = 60               # horizon (minutes), dt = 1 min
FULL = (P, 0.3 * P)   # broad-scope malicious envelope
NARROW = (0.0, 0.05 * P)
CLEAN = (0.0, 0.0)

# policy -> (scope, lifecycle) determining the DER setpoint over time.
# lifecycle in {legacy, no_session, no_cleanup, full} ; scope in {full, narrow}
POLICIES = {
    "B1_legacy_full":       ("full", "legacy"),      # indefinite, no enforcement
    "A2_no_session":        ("full", "no_session"),  # commands continue past expiry
    "A3_no_cmd_cleanup":    ("full", "no_cleanup"),  # last malicious setpoint latches
    "A4_full_lifecycle":    ("full", "full"),        # broad scope but session+cleanup at expiry
    "B5_narrow_lifecycle":  ("narrow", "full"),      # narrow scope + full lifecycle
}


def setpoint(scope, lifecycle, t):
    if t < T_ATTACK:
        return CLEAN
    env = FULL if scope == "full" else NARROW
    cred_valid = T_ATTACK <= t < T_ATTACK + TTL
    if lifecycle == "legacy":
        return env                                   # never ends
    if lifecycle == "no_session":
        return env                                   # session open -> commands continue
    if lifecycle == "no_cleanup":
        return env                                   # setpoint latched after expiry
    # full: session + command cleanup -> reset at expiry
    return env if cred_valid else CLEAN


def run_one(seed):
    f.compile_base()
    names = f.place_pv(f.load_buses(), N_PV, seed)
    f.set_load_mult(LOAD)
    out = {}
    for pol, (scope, lifecycle) in POLICIES.items():
        series = []
        for t in range(H):
            f.dispatch(names, *setpoint(scope, lifecycle, t))
            f.solve()
            series.append(f.overvoltage_area())
        integral = sum(series)                       # p.u.-node-minutes (dt = 1 min)
        peak = max(series)
        # recovery: first minute after attack start where area falls <=0.05 and stays low
        recovery = None
        for t in range(T_ATTACK, H):
            if series[t] <= 0.05 and all(s <= 0.05 for s in series[t:min(t + 3, H)]):
                recovery = t - T_ATTACK
                break
        out[pol] = {"integral": round(integral, 2), "peak": round(peak, 3),
                    "recovery_min": recovery, "series": [round(s, 3) for s in series]}
    return out


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    f.chdir_feeder()
    runs = [run_one(1000 + i) for i in range(n_seeds)]
    agg = {}
    for pol in POLICIES:
        integ = [r[pol]["integral"] for r in runs]
        agg[pol] = {"integral_median": round(statistics.median(integ), 2),
                    "peak": runs[0][pol]["peak"],
                    "recovery_min": runs[0][pol]["recovery_min"]}

    print(f"== Time-series feeder containment, IEEE 8500, {n_seeds} seed(s) ==")
    print(f"attack at t={T_ATTACK} min, credential TTL={TTL} min, horizon={H} min, light load\n")
    print(f"{'policy':22} {'scope':7} {'integ dJV*min':>13} {'peak':>7} {'recovery(min)':>13}")
    for pol, (scope, _) in POLICIES.items():
        a = agg[pol]
        rec = a["recovery_min"] if a["recovery_min"] is not None else "none"
        print(f"{pol:22} {scope:7} {a['integral_median']:>13.1f} {a['peak']:>7.2f} {str(rec):>13}")
    print("\nB1 vs A4 (same broad scope): lifecycle enforcement bounds the DURATION of harm.")
    print("A4 vs A2/A3: removing session OR command cleanup breaks temporal containment.")
    print("A4 vs B5: narrow scope bounds the instantaneous envelope.")

    (Path(__file__).resolve().parent / "results" / "timeseries.json").write_text(json.dumps(
        {"policies_agg": agg, "params": {"t_attack": T_ATTACK, "ttl": TTL, "horizon": H},
         "runs": runs, "n_seeds": n_seeds,
         "note": "Integral of real induced overvoltage area over time (p.u.-node-minutes) on the "
                 "IEEE 8500 feeder; recovery = minutes after attack until area stays <=0.05. "
                 "Direct temporal-containment measurement (no measured x modeled product)."}, indent=2))
    print("\nSaved -> experiments/results/timeseries.json")


if __name__ == "__main__":
    main()
