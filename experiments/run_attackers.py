#!/usr/bin/env python3
"""RQ4 (confirmatory): when is credential lifetime the binding containment mechanism?

The pilot evaluated one loud attacker and said plainly that this was its most significant gap:
an excursion that puts 82% of a feeder's nodes above band would be surfaced by AMI voltage
reporting, regulator counts and customer calls within a metering interval, so the operative
containment latency is the utility's detection-and-response time, not the credential lifetime.
Bounded lifetime only binds when detection does not.

This experiment supplies the attacker that makes lifetime matter, and measures the crossover
rather than asserting it. Five attackers share one authorized set and one operating state and
differ only in what they optimise and what they must stay below:

* **A1 oracle** -- maximise the primary endpoint. Full feeder state. Loud by construction.
* **A2 telemetry-limited** -- no feeder state; play the extreme of the authorized set in the
  injection direction. This is what an adversary who can read only its own authorized telemetry
  can do.
* **A3 stealth-constrained** -- maximise the primary endpoint subject to the *detection
  constraint*: cross no IEEE 1547 screen threshold, and add no more than DETECT_MARGIN nodes
  above the ANSI upper limit relative to the paired legitimate baseline.
* **A4 wear** -- maximise regulator tap operations subject to the same detection constraint.
  Harm the operator pays for in equipment life rather than in voltage.
* **A5 curtailment** -- maximise curtailed active energy subject to the same detection
  constraint. Harm the operator pays for in lost generation.

The action space is two-dimensional -- the reactive point in the authorized set and the active
power fraction -- because a stealth attacker trades one against the other: withdrawing absorption
raises voltage, curtailing active power lowers it, and a mixture can hold voltage inside the band
while still doing damage.

**Detection model, declared before running.** An attack is *voltage-detectable* in the metering
interval in which it adds more than DETECT_MARGIN nodes above 1.05 p.u. over the paired
legitimate baseline, or crosses any IEEE 1547 Category II screen threshold. This is a proxy for
AMI-based operational detection and nothing more: it is not a claim about any particular
utility's monitoring, and the manuscript reports it as an assumption with its sensitivity.

Usage: python3 experiments/run_attackers.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "attackers.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051,
         1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117]

STATES = {
    "ieee8500_stress": {"feeder": "ieee8500", "load_mult": 0.50, "penetration": 1.50,
                        "fleet": 600},
    "ieee8500_compliant": {"feeder": "ieee8500", "load_mult": 0.50, "penetration": 0.50,
                           "fleet": 600},
    "ieee123_stress": {"feeder": "ieee123", "load_mult": 1.00, "penetration": 10.0,
                       "fleet": 46},
}

#: Nodes above 1.05 p.u. an attacker may add over the legitimate baseline before an
#: AMI-based operational detector is assumed to see it within one metering interval.
DETECT_MARGIN = 10

#: Reactive grid, as a fraction of Category B capability (+ = injection), and active-power grid.
Q_FRACS = [-1.00, -0.75, -0.50, -0.25, 0.00, 0.25, 0.50, 0.75, 1.00]
SIGMAS = [0.0, 0.25, 0.50, 0.75, 1.00]

PRIMITIVE = "curve"


def one_arm(task):
    """Scan the joint action space once, then read each attacker's optimum off the same scan."""
    from power import confirmatory as C

    cfg = STATES[task["state"]]
    spec = ensure_feeder(cfg["feeder"])
    seed, lm, n = task["seed"], cfg["load_mult"], cfg["fleet"]

    with C.Session(spec, seed=seed, n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    p_kw = (cfg["penetration"] * base_load * lm) / n
    der = C.DER(p_kw=p_kw)
    p_available = n * p_kw

    C.reset_convergence_counters()
    pts = []
    with C.Session(spec, seed=seed, n_pv=n, load_mult=lm, der=der) as s:
        s.dispatch_legitimate()
        C.solve()
        base = s.state()
        base_taps = C.tap_positions()

        for qf in Q_FRACS:
            for sig in SIGMAS:
                s.apply(qf * der.q_cat_b, PRIMITIVE, p_kw=der.p_kw * sig)
                conv = C.solve()
                st = s.state()
                taps = C.count_tap_operations(base_taps, C.tap_positions())
                d_nout = st["n_over"] - base["n_over"]
                pts.append({
                    "q_frac": qf, "sigma": sig,
                    "dJ_band": round(st["j_band"] - base["j_band"], 6),
                    "d_n_over": d_nout,
                    "screen": st["screen"],
                    "induced_screen": bool(st["screen"] and not base["screen"]),
                    "tap_ops": taps,
                    "curtailed_kw": round(max(0.0, p_available - st["p_fleet_kw"]), 3),
                    "vmax": st["vmax"], "vmin": st["vmin"],
                    "deficit_frac": st["deficit_frac"],
                    "detectable": bool(st["screen"] or d_nout > DETECT_MARGIN),
                    "converged": conv,
                })

    stealthy = [p for p in pts if not p["detectable"]]

    def pick(cands, keyfn):
        return max(cands, key=keyfn) if cands else None

    attackers = {
        "A1_oracle": pick(pts, lambda p: p["dJ_band"]),
        # A2 knows nothing about the feeder: it plays maximum injection at full output.
        "A2_telemetry_limited": next(
            (p for p in pts if p["q_frac"] == 1.00 and p["sigma"] == 1.00), None),
        "A3_stealth": pick(stealthy, lambda p: p["dJ_band"]),
        "A4_wear": pick(stealthy, lambda p: p["tap_ops"]),
        "A5_curtailment": pick(stealthy, lambda p: p["curtailed_kw"]),
    }
    return {
        "state": task["state"], "seed": seed, "unit_kw": round(p_kw, 4),
        "penetration": cfg["penetration"], "load_mult": lm,
        "p_available_kw": round(p_available, 2),
        "base_j_band": round(base["j_band"], 6), "base_n_over": base["n_over"],
        "base_screen": base["screen"],
        "n_points": len(pts), "n_stealthy": len(stealthy),
        # The full scan is retained so that a detector declared later can be applied to the same
        # action space without re-simulating; analyze_attackers.py depends on it.
        "points": pts,
        "attackers": {k: v for k, v in attackers.items() if v is not None},
        "missing": [k for k, v in attackers.items() if v is None],
        "nonconverged": dict(C.NONCONVERGED),
    }


def summarize(rows):
    out = []
    for stn in sorted({r["state"] for r in rows if "error" not in r}):
        g = [r for r in rows if "error" not in r and r["state"] == stn]
        for a in ("A1_oracle", "A2_telemetry_limited", "A3_stealth", "A4_wear", "A5_curtailment"):
            vals = [r["attackers"][a] for r in g if a in r["attackers"]]
            if not vals:
                continue
            out.append({
                "state": stn, "attacker": a, "n": len(vals),
                "median_dJ_band": round(statistics.median([v["dJ_band"] for v in vals]), 4),
                "median_d_n_over": statistics.median([v["d_n_over"] for v in vals]),
                "frac_detectable": round(
                    sum(1 for v in vals if v["detectable"]) / len(vals), 3),
                "frac_induced_screen": round(
                    sum(1 for v in vals if v["induced_screen"]) / len(vals), 3),
                "median_tap_ops": statistics.median([v["tap_ops"] for v in vals]),
                "median_curtailed_kw": round(
                    statistics.median([v["curtailed_kw"] for v in vals]), 2),
                "median_curtailed_frac": round(statistics.median(
                    [v["curtailed_kw"] / r["p_available_kw"]
                     for v, r in zip(vals, g) if r["p_available_kw"]]), 4),
                "modal_q_frac": statistics.median([v["q_frac"] for v in vals]),
                "modal_sigma": statistics.median([v["sigma"] for v in vals]),
                "median_stealthy_points": statistics.median([r["n_stealthy"] for r in g]),
            })
    return out


def main(n_seeds: int = 20):
    tasks = [{"state": s, "seed": sd} for s in STATES for sd in SEEDS[:n_seeds]]
    rows = run_tasks(one_arm, tasks, label="attackers", every=10)
    out = {"status": "confirmatory",
           "hypothesis": "H5 stealth interaction: bounded lifetime binds where detection does not",
           "detect_margin_nodes": DETECT_MARGIN,
           "detection_model": "voltage-detectable within one metering interval if the attack "
                              "crosses any IEEE 1547 Cat II screen threshold or adds more than "
                              "DETECT_MARGIN nodes above 1.05 p.u. over the paired legitimate "
                              "baseline",
           "q_fracs": Q_FRACS, "sigmas": SIGMAS, "primitive": PRIMITIVE,
           "states": STATES, "seeds": SEEDS[:n_seeds],
           "rows": rows, "summary": summarize(rows)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}  ({len(rows)} arms, {sum(1 for r in rows if 'error' in r)} failed)")

    print("\n%-20s %-22s %10s %9s %8s %8s %10s %7s %6s" %
          ("state", "attacker", "medDJband", "d_n_over", "detect%", "screen%", "curtail%",
           "taps", "q,sig"))
    for s in out["summary"]:
        print("%-20s %-22s %10.3f %9.0f %8.2f %8.2f %10.4f %7.0f %3.2f,%3.2f" %
              (s["state"], s["attacker"], s["median_dJ_band"], s["median_d_n_over"],
               s["frac_detectable"], s["frac_induced_screen"], s["median_curtailed_frac"],
               s["median_tap_ops"], s["modal_q_frac"], s["modal_sigma"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
