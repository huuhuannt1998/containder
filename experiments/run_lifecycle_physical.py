#!/usr/bin/env python3
"""RQ3/RQ5/RQ6 (confirmatory): what each containment layer is worth, physically.

Three questions in one horizon experiment, because they share a harness:

* **RQ6 mechanism decomposition (H4).** Are session enforcement and command cleanup
  *independently* necessary? The pilot's ablations were withdrawn because its activity predicate
  mapped three lifecycles onto one arm, so three labels named a single arm and their per-seed
  series were byte-identical. :mod:`credsvc.lifecycle` separates credential, session and
  command-effect authority, which makes S0-S3 four genuinely different timelines.
* **RQ3 lifetime (H4).** How does integrated harm depend on retained-authority duration?
* **RQ5 denial versus non-renewal.** How far does a local denylist actually reach, given that
  denying an identity refuses future authorization but neither closes an open session nor
  retracts an issued control?

Two design choices matter.

**The exogenous state moves.** The pilot held load and irradiance constant across its horizon, so
the attacked and unattacked cases were each a single fixed power flow and integrated harm was
exactly (accrual rate) x (minutes honoured). The pilot reported this honestly, but under a static
profile no lifetime experiment can say anything a multiplication could not. Here irradiance
follows a midday arc with a cloud transient placed deliberately *inside* the post-expiry window,
and load rises toward evening, so recovery has to be demonstrated against a moving baseline
rather than inferred from a return to a constant.

**Each arm is one continuous session.** Within an arm the circuit is stepped forward without
recompiling, so regulator taps and capacitor states carry over from minute to minute. That is the
whole point: whether a regulator left in an excursion-driven position holds voltage up after the
credential dies is the question, and recompiling each step would answer it by construction. Arms
remain independent of each other -- each is its own compile -- which is the isolation the pilot's
predecessor lacked.

Recovery criterion, declared before running: the feeder has recovered at the first step after the
adversarial control ceases at which

    J_band(step) <= J_legit(step) + max(0.05, 0.10 * J_legit(step))

against the *paired legitimate arm at the same seed and step*. The relative term is what the
pilot lacked: its fixed 0.05 p.u.-node threshold sat inside the normal-load baseline's own
variation, so the criterion failed for a reason that had nothing to do with the mechanism.

Usage: python3 experiments/run_lifecycle_physical.py [n_seeds]
"""
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "lifecycle_physical.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051,
         1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117]

HORIZON_MIN = 60
STEP_S = 60.0
COMPROMISE_MIN = 5

#: Operating states at which the lifecycle matters, i.e. where the attack has consequence.
#: Both are rungs of the ladder in run_authz_shape.py.
STATES = {
    "ieee8500_stress": {"feeder": "ieee8500", "load_mult": 0.50, "penetration": 1.50,
                        "fleet": 600},
    "ieee123_stress": {"feeder": "ieee123", "load_mult": 1.00, "penetration": 10.0,
                       "fleet": 91},
}

#: Command duration and session cache, in seconds. A 15-minute DERControl is the overhang that
#: session enforcement alone cannot remove.
LC_KW = dict(session_max_age_s=3600.0, command_duration_s=900.0, cleanup_latency_s=60.0)

TTLS_MIN = [5, 10, 15, 25, 40, 55]
DETECT_MIN = [5, 15]
RESPONSES = ["none", "denylist", "denylist+session", "denylist+session+cancel"]


def build_arms():
    """Every lifecycle arm, as (arm_id, policy_kwargs, incident_kwargs)."""
    from credsvc import lifecycle as L
    arms = []
    t0 = COMPROMISE_MIN * 60.0

    # Baseline: long-lived credential, no mechanism, no detection.
    arms.append(("legacy", L.legacy_policy(**LC_KW), L.Incident(t_compromise_s=t0)))

    # RQ6: mechanism ablation at a common lifetime.
    for name, pol in L.ablation_arms(25 * 60.0, **LC_KW).items():
        arms.append((f"mech_{name}", pol, L.Incident(t_compromise_s=t0)))

    # RQ3: lifetime sweep with both mechanisms present.
    for ttl in TTLS_MIN:
        arms.append((f"ttl_{ttl}",
                     L.LifecyclePolicy(f"S3 ttl={ttl}m", ttl * 60.0, True, True, **LC_KW),
                     L.Incident(t_compromise_s=t0)))

    # RQ5: local denial against a long-lived credential, at two detection delays.
    for d in DETECT_MIN:
        for resp in RESPONSES:
            arms.append((f"deny_{resp}_d{d}", L.legacy_policy(**LC_KW),
                         L.Incident(t_compromise_s=t0, t_detect_s=(COMPROMISE_MIN + d) * 60.0,
                                    response=resp)))
    return arms


def one_seed(task):
    """Run every lifecycle arm for one (state, seed), plus the paired legitimate arm."""
    from power import confirmatory as C
    from power import profiles as P
    from credsvc import lifecycle as L

    st_cfg = STATES[task["state"]]
    spec = ensure_feeder(st_cfg["feeder"])
    seed, lm, n = task["seed"], st_cfg["load_mult"], st_cfg["fleet"]

    with C.Session(spec, seed=seed, n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    p_kw = (st_cfg["penetration"] * base_load * lm) / n
    der = C.DER(p_kw=p_kw)
    prof = P.horizon_profile(HORIZON_MIN, load_mult=lm)

    def step_arm(effect):
        """Step one arm across the horizon; ``effect[k]`` selects the adversarial point."""
        C.reset_convergence_counters()
        series = []
        with C.Session(spec, seed=seed, n_pv=n, load_mult=lm, der=der) as s:
            prev_taps = None
            taps_total = 0
            for k in range(HORIZON_MIN):
                C.set_load_mult(prof[k]["load_mult"])
                if effect is not None and effect[k]:
                    # Adversary withdraws the reactive absorption the feeder relies on, while
                    # legitimate active power continues to follow irradiance.
                    s.apply(0.0, "curve", p_kw=der.p_kw * prof[k]["irradiance"])
                else:
                    s.dispatch_legitimate(irradiance=prof[k]["irradiance"])
                conv = C.solve()
                stt = s.state()
                taps = C.tap_positions()
                if prev_taps is not None:
                    taps_total += C.count_tap_operations(prev_taps, taps)
                prev_taps = taps
                series.append({"k": k, "j_band": round(stt["j_band"], 6),
                               "area_over": round(stt["area_over"], 6),
                               "vmax": stt["vmax"], "screen": stt["screen"],
                               "q_fleet_kvar": round(stt["q_fleet_kvar"], 2),
                               "converged": conv})
            return series, taps_total, dict(C.NONCONVERGED)

    legit_series, legit_taps, legit_nc = step_arm(None)
    legit_j = [x["j_band"] for x in legit_series]

    out_arms = {}
    for arm_id, pol, inc in build_arms():
        sim = L.simulate(pol, inc, HORIZON_MIN * 60.0, STEP_S)
        series, taps, nc = step_arm(sim["effect"])
        j = [x["j_band"] for x in series]
        dj = [j[k] - legit_j[k] for k in range(HORIZON_MIN)]

        # Post-effect recovery against the paired legitimate arm at the same step.
        eff_idx = [k for k, e in enumerate(sim["effect"]) if e]
        last_eff = eff_idx[-1] if eff_idx else None
        recovery_step = None
        if last_eff is not None:
            for k in range(last_eff + 1, HORIZON_MIN):
                if j[k] <= legit_j[k] + max(0.05, 0.10 * legit_j[k]):
                    recovery_step = k - last_eff
                    break
        post = dj[last_eff + 1:] if last_eff is not None and last_eff + 1 < HORIZON_MIN else []
        integral = sum(dj)
        out_arms[arm_id] = {
            "policy": pol.name,
            "T_cred_min": (sim["T_cred"] / 60.0) if math.isfinite(sim["T_cred"]) else None,
            "T_sess_min": sim["T_sess"] / 60.0,
            "T_cmd_min": sim["T_cmd"] / 60.0,
            "n_commands_accepted": sim["n_commands_accepted"],
            "effect_minutes": len(eff_idx),
            "integral_dJ_band": round(integral, 4),
            "peak_dJ_band": round(max(dj), 4),
            "mean_accrual_while_active": round(
                statistics.fmean([dj[k] for k in eff_idx]), 4) if eff_idx else 0.0,
            "post_effect_integral": round(sum(post), 4),
            "post_effect_frac": round(sum(post) / integral, 4) if integral > 0 else 0.0,
            "recovery_steps": recovery_step,
            "recovered": recovery_step is not None,
            "screen_minutes": sum(1 for x in series if x["screen"]),
            "tap_ops": taps,
            "n_nonconverged": nc["n"],
            "series_dj": [round(x, 4) for x in dj],
        }

    return {"state": task["state"], "seed": seed, "unit_kw": round(p_kw, 4),
            "penetration": st_cfg["penetration"], "load_mult": lm,
            "legit_integral_j_band": round(sum(legit_j), 4),
            "legit_tap_ops": legit_taps, "legit_nonconverged": legit_nc["n"],
            "legit_series_j": [round(x, 4) for x in legit_j],
            "arms": out_arms}


def _boot_ci(xs, n=10000, seed=12345):
    """Bias-corrected percentile bootstrap CI of the median."""
    import random
    if not xs:
        return (None, None)
    rng = random.Random(seed)
    meds = []
    k = len(xs)
    for _ in range(n):
        meds.append(statistics.median([xs[rng.randrange(k)] for _ in range(k)]))
    meds.sort()
    return (round(meds[int(0.025 * n)], 4), round(meds[int(0.975 * n) - 1], 4))


def summarize(rows):
    out = []
    states = sorted({r["state"] for r in rows if "error" not in r})
    arm_ids = [a for a, _, _ in build_arms()]
    for stn in states:
        g = [r for r in rows if "error" not in r and r["state"] == stn]
        for arm in arm_ids:
            vals = [r["arms"][arm] for r in g if arm in r["arms"]]
            if not vals:
                continue
            integ = [v["integral_dJ_band"] for v in vals]
            lo, hi = _boot_ci(integ)
            out.append({
                "state": stn, "arm": arm, "n": len(vals),
                "T_cred_min": vals[0]["T_cred_min"], "T_sess_min": vals[0]["T_sess_min"],
                "T_cmd_min": vals[0]["T_cmd_min"],
                "n_commands_accepted": vals[0]["n_commands_accepted"],
                "effect_minutes": vals[0]["effect_minutes"],
                "median_integral": round(statistics.median(integ), 4),
                "ci_lo": lo, "ci_hi": hi,
                "median_peak": round(statistics.median([v["peak_dJ_band"] for v in vals]), 4),
                "median_post_frac": round(
                    statistics.median([v["post_effect_frac"] for v in vals]), 4),
                "frac_recovered": round(sum(1 for v in vals if v["recovered"]) / len(vals), 3),
                "median_recovery_steps": (
                    statistics.median([v["recovery_steps"] for v in vals if v["recovered"]])
                    if any(v["recovered"] for v in vals) else None),
                "median_tap_ops": statistics.median([v["tap_ops"] for v in vals]),
                "median_screen_minutes": statistics.median(
                    [v["screen_minutes"] for v in vals]),
                "n_nonconverged": sum(v["n_nonconverged"] for v in vals),
            })
    return out


def main(n_seeds: int = 20):
    tasks = [{"state": s, "seed": sd} for s in STATES for sd in SEEDS[:n_seeds]]
    rows = run_tasks(one_seed, tasks, label="lifecycle-physical", every=4)
    out = {"status": "confirmatory",
           "hypotheses": ["H4 lifetime truncation + mechanism decomposition",
                          "RQ5 local denial vs non-renewal"],
           "horizon_min": HORIZON_MIN, "compromise_min": COMPROMISE_MIN,
           "lifecycle_kw": LC_KW, "states": STATES, "ttls_min": TTLS_MIN,
           "detect_min": DETECT_MIN, "responses": RESPONSES,
           "recovery_criterion": "J_band <= J_legit + max(0.05, 0.10*J_legit), paired by step",
           "seeds": SEEDS[:n_seeds], "rows": rows, "summary": summarize(rows)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}  ({len(rows)} seed-arms, "
          f"{sum(1 for r in rows if 'error' in r)} failed)")

    print("\n%-16s %-26s %6s %6s %6s %5s %10s %9s %6s %6s" %
          ("state", "arm", "Tcred", "Tsess", "Tcmd", "eff", "medIntegral", "recov%",
           "taps", "scrMin"))
    for s in out["summary"]:
        print("%-16s %-26s %6s %6.0f %6.0f %5d %10.2f %9.2f %6.0f %6.0f" %
              (s["state"], s["arm"],
               "inf" if s["T_cred_min"] is None else f"{s['T_cred_min']:.0f}",
               s["T_sess_min"], s["T_cmd_min"], s["effect_minutes"],
               s["median_integral"], s["frac_recovered"], s["median_tap_ops"],
               s["median_screen_minutes"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
