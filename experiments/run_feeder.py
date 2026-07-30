#!/usr/bin/env python3
"""Feeder-consequence campaign (C5) on a small OpenDSS feeder --- REAL power flow.

Translates the authorized malicious DER envelope under each policy into an OpenDSS dispatch
and measures the voltage-violation area J_V, across feeder operating states. Legacy full
authorization (B1) vs CONTAINDER narrowed scope (B5); B3 (ephemeral-only) has the same
physical envelope as B1 (short certs do not narrow scope), so its physical J_V equals B1 --
the reduction from B5 is scope, and the additional B3-vs-B1 gap is temporal (exposure), not
snapshot J_V. Small illustrative feeder, single solver; IEEE 8500 / PNNL 9500 remain.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder

# Authorized malicious DER envelope (kW export, kVAr) by baseline.
POLICIES = {
    "B1_legacy_full": (4000.0, 3000.0),
    "B3_ephemeral":   (4000.0, 3000.0),   # same scope as B1; differs only in persistence
    "B5_containder":  (0.0, 300.0),        # narrowed: no active override, narrow volt-var band
}
STATES = {"light_load_high_pv": 0.15, "normal": 1.0, "heavy_load": 1.7}


def main():
    rows = []
    for state, ls in STATES.items():
        feeder.build(load_scale=ls)
        base = feeder.dispatch_and_solve(0.0, 0.0)
        rows.append({"state": state, "policy": "clean_base",
                     "J_V": round(feeder.violation_area(base), 5),
                     "max_dev_pu": round(feeder.max_deviation(base), 4),
                     "n_violating": feeder.n_violating(base),
                     "converged": feeder.converged()})
        for pol, (kw, kvar) in POLICIES.items():
            v = feeder.dispatch_and_solve(kw, kvar)
            rows.append({"state": state, "policy": pol,
                         "J_V": round(feeder.violation_area(v), 5),
                         "max_dev_pu": round(feeder.max_deviation(v), 4),
                         "n_violating": feeder.n_violating(v),
                         "converged": feeder.converged()})

    print("== C5 feeder consequence (small OpenDSS feeder, real power flow) ==")
    print(f"{'state':20} {'policy':16} {'J_V':>9} {'max_dev':>8} {'n_viol':>7} conv")
    for r in rows:
        print(f"{r['state']:20} {r['policy']:16} {r['J_V']:>9.4f} {r['max_dev_pu']:>8.4f} "
              f"{r['n_violating']:>7} {r['converged']}")

    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "feeder.json").write_text(json.dumps({"rows": rows,
        "note": "Small illustrative feeder, OpenDSS single solver; IEEE 8500 / PNNL 9500 and "
                "GridLAB-D cross-check remain for the full evaluation."}, indent=2))
    print("\nSaved -> experiments/results/feeder.json")


if __name__ == "__main__":
    main()
