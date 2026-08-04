#!/usr/bin/env python3
"""RQ4 sensitivity: does the stealth result survive a detector that watches generation?

Why this exists
---------------
The confirmatory attacker analysis declared a single detector, and it watches voltage: an attack
is flagged if it crosses an IEEE 1547 screen threshold or adds more than ten nodes above the ANSI
upper limit. Under that detector the wear and curtailment attackers are invisible while curtailing
the entire fleet, which is the paper's stealth result.

That result is only as strong as the detector is representative, and a voltage-only detector is a
weak adversary for it: an operator with any generation telemetry sees a fleet at zero output
immediately. Reporting the stealth finding against the weak detector alone would overstate it.

This script therefore applies a **second declared detector** to the same stored scan --- every
attacker arm recorded all 45 points of the joint action space, so no new simulation is needed ---
and reports where each attacker lands under both:

* **D1 voltage** (confirmatory): screen crossing, or more than DETECT_MARGIN nodes added above
  1.05 p.u. against the paired legitimate case.
* **D2 generation** (post-hoc, declared here): fleet active output departs from the legitimate
  scheduled output by more than GEN_TOL of available power. This is the telemetry an aggregator
  already collects for settlement.

**Status: post-hoc sensitivity analysis.** D2 was specified after the confirmatory results were
seen. It is reported as a bound on the stealth claim, not as a confirmatory test, and the
manuscript states which detector each statement is made against.

Usage: python3 experiments/analyze_attackers.py
"""
import json
import statistics
import sys
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"
OUT = RES / "attacker_detectors.json"

#: Fractional departure of fleet active output from schedule that generation telemetry flags.
GEN_TOL = 0.10


def main():
    src = RES / "attackers.json"
    if not src.exists():
        sys.exit(f"missing {src}")
    d = json.loads(src.read_text())
    rows = [r for r in d["rows"] if "error" not in r]
    margin = d["detect_margin_nodes"]

    out = {"status": "post-hoc sensitivity; D2 declared after seeing confirmatory results",
           "d1": f"voltage: screen crossing or > {margin} nodes added above 1.05 p.u.",
           "d2": f"generation: |fleet P - scheduled P| > {GEN_TOL:.0%} of available power",
           "gen_tol": GEN_TOL, "states": {}}

    for state in sorted({r["state"] for r in rows}):
        g = [r for r in rows if r["state"] == state]
        per_attacker = {}
        for a in ("A1_oracle", "A2_telemetry_limited", "A3_stealth", "A4_wear",
                  "A5_curtailment"):
            vals = [r["attackers"][a] for r in g if a in r["attackers"]]
            if not vals:
                continue
            avail = [r["p_available_kw"] for r in g if a in r["attackers"]]
            d1 = [bool(v["detectable"]) for v in vals]
            d2 = [bool(v["curtailed_kw"] > GEN_TOL * p) for v, p in zip(vals, avail)]
            per_attacker[a] = {
                "n": len(vals),
                "median_dJ_band": round(statistics.median(
                    [v["dJ_band"] for v in vals]), 4),
                "median_curtailed_frac": round(statistics.median(
                    [v["curtailed_kw"] / p for v, p in zip(vals, avail) if p]), 4),
                "frac_flagged_d1_voltage": round(sum(d1) / len(d1), 3),
                "frac_flagged_d2_generation": round(sum(d2) / len(d2), 3),
                "frac_flagged_either": round(
                    sum(1 for x, y in zip(d1, d2) if x or y) / len(d1), 3),
                "frac_evading_both": round(
                    sum(1 for x, y in zip(d1, d2) if not x and not y) / len(d1), 3),
            }

        # The attacker that matters for the lifetime argument: the best harm available to an
        # adversary that evades BOTH detectors. Recomputed from the full stored scan.
        best = []
        missing_scan = sum(1 for r in g if not r.get("points"))
        for r in g:
            cands = []
            for p in r.get("points", []):
                if p["detectable"]:
                    continue
                if p["curtailed_kw"] > GEN_TOL * r["p_available_kw"]:
                    continue
                cands.append(p)
            if cands:
                best.append(max(cands, key=lambda p: p["dJ_band"]))
        out["states"][state] = {
            "attackers": per_attacker,
            "scan_missing_for_n_arms": missing_scan,
            "dual_evading_best": ({
                "n": len(best),
                "median_dJ_band": round(statistics.median(
                    [p["dJ_band"] for p in best]), 4),
                "median_curtailed_frac": round(statistics.median(
                    [p["curtailed_kw"] for p in best]), 3),
                "median_tap_ops": statistics.median([p["tap_ops"] for p in best]),
            } if best else None),
        }

    # --- Detector-threshold sensitivity ------------------------------------------------------
    # Both detectors are proxies with declared thresholds. The crossover between lifetime-bound
    # and detection-bound containment moves with them, so the thresholds are swept rather than
    # asserted. Computed from the same stored scan; no re-simulation.
    sens = []
    for state in sorted({r["state"] for r in rows}):
        g = [r for r in rows if r["state"] == state and r.get("points")]
        if not g:
            continue
        for vmargin in (0, 5, 10, 25, 50):
            for gtol in (0.02, 0.05, 0.10, 0.25, 0.50):
                best = []
                for r in g:
                    cands = [p for p in r["points"]
                             if not (p["screen"] or p["d_n_over"] > vmargin)
                             and p["curtailed_kw"] <= gtol * r["p_available_kw"]]
                    if cands:
                        best.append(max(c["dJ_band"] for c in cands))
                sens.append({
                    "state": state, "voltage_margin_nodes": vmargin, "generation_tol": gtol,
                    "n_seeds_with_evading_point": len(best), "n_seeds": len(g),
                    "median_best_dJ_band": round(statistics.median(best), 4) if best else None,
                })
    out["threshold_sensitivity"] = sens

    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}\n")
    print("%-20s %-22s %9s %9s %9s %9s %9s" %
          ("state", "attacker", "medDJ", "curtail", "D1 volt", "D2 gen", "evade both"))
    for state, v in out["states"].items():
        for a, s in v["attackers"].items():
            print("%-20s %-22s %9.3f %9.3f %9.2f %9.2f %9.2f" %
                  (state, a, s["median_dJ_band"], s["median_curtailed_frac"],
                   s["frac_flagged_d1_voltage"], s["frac_flagged_d2_generation"],
                   s["frac_evading_both"]))
    print("\nThreshold sensitivity: best dJ_band for an adversary evading both detectors")
    print("%-20s %8s %8s %10s %12s" % ("state","volt(N)","gen(tol)","seeds","med best dJ"))
    for r in out["threshold_sensitivity"]:
        if r["state"] != "ieee8500_stress":
            continue
        print("%-20s %8d %8.2f %5d/%-5d %12s" % (r["state"], r["voltage_margin_nodes"],
              r["generation_tol"], r["n_seeds_with_evading_point"], r["n_seeds"],
              "none" if r["median_best_dJ_band"] is None else f"{r['median_best_dJ_band']:.3f}"))

    print("\nBest harm available to an adversary evading BOTH detectors:")
    for state, v in out["states"].items():
        b = v["dual_evading_best"]
        miss = out["states"][state]["scan_missing_for_n_arms"]
        if miss:
            print(f"  {state:<20} NOT COMPUTABLE: {miss} arms stored no scan; re-run "
                  f"run_attackers.py")
            continue
        print(f"  {state:<20} " + ("none exists" if not b else
              f"dJ_band {b['median_dJ_band']:.3f}, curtailed {b['median_curtailed_frac']:.1f} kW, "
              f"taps {b['median_tap_ops']:.0f}  (n={b['n']})"))


if __name__ == "__main__":
    main()
