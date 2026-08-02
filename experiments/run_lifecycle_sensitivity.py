#!/usr/bin/env python3
"""How far do the containment percentages depend on the lifecycle parameters that produce them?

Why this exists
---------------
The reported reductions -- 50.0% for adding session termination, 69.5% for adding command
cancellation -- are measured at one setting of three parameters that the model, not the feeder,
supplies: the control duration an adversary installs (15 min), the age at which an unenforced
session lapses (60 min), and the latency of a cleanup sweep (1 min). A reviewer is entitled to ask
whether those percentages are properties of the mechanisms or of the settings, and the honest
answer requires measuring it rather than asserting robustness.

The exposure window is the quantity the mechanisms actually control, and integrated harm is
accrued over it, so the sensitivity of the window bounds the sensitivity of the percentages. This
sweep computes the window directly from :mod:`credsvc.lifecycle` across the parameter grid. It
needs no power flow: the feeder maps a window onto harm, and that mapping is what
``run_lifecycle_physical.py`` measures at the nominal setting.

Reported as **effect minutes** and as the reduction in effect minutes against the long-lived
baseline, which is the model-side counterpart of the physical percentage.

Status: post-hoc sensitivity analysis, declared. It tests no hypothesis.

Usage: python3 experiments/run_lifecycle_sensitivity.py
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from credsvc import lifecycle as L

OUT = Path(__file__).resolve().parent / "results" / "lifecycle_sensitivity.json"

HORIZON_MIN = 60
STEP_S = 60.0
COMPROMISE_MIN = 5
TTL_MIN = 25
DETECT_MIN = 5

#: Nominal values used by the physical experiment, and the grid swept around them.
CMD_DURATION_MIN = [5, 10, 15, 30, 60]
SESSION_AGE_MIN = [30, 60, 120, 1440]
CLEANUP_LATENCY_S = [10, 60, 300]

NOMINAL = {"command_duration_min": 15, "session_age_min": 60, "cleanup_latency_s": 60}


def effect_minutes(policy, incident):
    sim = L.simulate(policy, incident, HORIZON_MIN * 60.0, STEP_S)
    return sum(1 for e in sim["effect"] if e), sim


def evaluate(cmd_min, sess_min, cleanup_s):
    kw = dict(session_max_age_s=sess_min * 60.0,
              command_duration_s=cmd_min * 60.0,
              cleanup_latency_s=float(cleanup_s))
    t0 = COMPROMISE_MIN * 60.0
    base_pol = L.legacy_policy(**kw)
    base_inc = L.Incident(t_compromise_s=t0)
    base_min, _ = effect_minutes(base_pol, base_inc)

    arms = {}
    for name, pol in L.ablation_arms(TTL_MIN * 60.0, **kw).items():
        m, sim = effect_minutes(pol, base_inc)
        arms[f"mech_{name}"] = (m, sim)
    for resp in L.RESPONSES:
        inc = L.Incident(t_compromise_s=t0,
                         t_detect_s=(COMPROMISE_MIN + DETECT_MIN) * 60.0, response=resp)
        m, sim = effect_minutes(base_pol, inc)
        arms[f"deny_{resp}"] = (m, sim)

    out = {"command_duration_min": cmd_min, "session_age_min": sess_min,
           "cleanup_latency_s": cleanup_s, "baseline_effect_min": base_min, "arms": {}}
    for k, (m, sim) in arms.items():
        out["arms"][k] = {
            "effect_min": m,
            "reduction_pct": round(100.0 * (base_min - m) / base_min, 2) if base_min else None,
            "T_cmd_min": round(sim["T_cmd"] / 60.0, 2),
            "identical_to_baseline": m == base_min,
        }
    return out


def main():
    grid = [evaluate(c, s, cl)
            for c in CMD_DURATION_MIN for s in SESSION_AGE_MIN for cl in CLEANUP_LATENCY_S]

    key_arms = ["mech_S1", "mech_S3", "deny_denylist",
                "deny_denylist+session", "deny_denylist+session+cancel"]
    ranges = {}
    for a in key_arms:
        vals = [g["arms"][a]["reduction_pct"] for g in grid if a in g["arms"]]
        ranges[a] = {"n_settings": len(vals),
                     "min_reduction_pct": round(min(vals), 2),
                     "median_reduction_pct": round(statistics.median(vals), 2),
                     "max_reduction_pct": round(max(vals), 2),
                     "always_zero": all(v == 0 for v in vals)}

    nominal = next(g for g in grid
                   if g["command_duration_min"] == NOMINAL["command_duration_min"]
                   and g["session_age_min"] == NOMINAL["session_age_min"]
                   and g["cleanup_latency_s"] == NOMINAL["cleanup_latency_s"])

    OUT.write_text(json.dumps({
        "status": "post-hoc sensitivity of the exposure window; tests no hypothesis",
        "horizon_min": HORIZON_MIN, "ttl_min": TTL_MIN, "detect_min": DETECT_MIN,
        "nominal": NOMINAL, "grid_size": len(grid),
        "ranges": ranges, "nominal_point": nominal, "grid": grid}, indent=2))
    print(f"wrote {OUT}\n")
    print(f"{len(grid)} parameter settings "
          f"(command duration x session age x cleanup latency)\n")
    print("%-32s %10s %10s %10s %8s" %
          ("arm", "min red%", "median", "max red%", "always 0"))
    for a, r in ranges.items():
        print("%-32s %10.1f %10.1f %10.1f %8s" %
              (a, r["min_reduction_pct"], r["median_reduction_pct"],
               r["max_reduction_pct"], r["always_zero"]))
    print("\nAt the nominal setting used by the physical experiment:")
    for a in key_arms:
        print(f"  {a:<32} {nominal['arms'][a]['reduction_pct']:6.1f}% "
              f"(effect {nominal['arms'][a]['effect_min']} of "
              f"{nominal['baseline_effect_min']} min)")


if __name__ == "__main__":
    main()
