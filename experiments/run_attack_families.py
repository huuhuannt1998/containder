#!/usr/bin/env python3
"""Multiple attack families on the real IEEE 8500 feeder (OpenDSS).

Three overvoltage-type families measured by induced overvoltage area (export-limit, volt-var,
volt-watt), plus curtailment-spam measured by voltage variability across a toggled dispatch.
For each, legacy-full authorization scope vs CONTAINDER-narrowed scope, light-load state,
median over seeds. Shows the containment holds across families, not just the export attack.
Usage: python3 experiments/run_attack_families.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500 as f
import opendssdirect as dss

P = 12.0
STATE_LM = 0.30  # light load / high PV: worst for overvoltage
N_PV = 600
NARROW = (0.0, 0.05 * P)
FAMILIES_OV = {              # full-scope malicious envelope (kW, kVAr)
    "export_limit": (P, 0.3 * P),   # active export dominant
    "volt_var":     (0.0, P),        # reactive injection only
    "volt_watt":    (P, 0.0),        # active injection only
}


def run_overvolt(n_seeds):
    res = {fam: {"full": [], "narrow": []} for fam in FAMILIES_OV}
    for seed in range(1000, 1000 + n_seeds):
        f.compile_base()
        names = f.place_pv(f.load_buses(), N_PV, seed)
        f.set_load_mult(STATE_LM)
        f.dispatch(names, 0.0, 0.0); f.solve(); base = f.overvoltage_area()
        for fam, env in FAMILIES_OV.items():
            f.dispatch(names, *env); f.solve()
            res[fam]["full"].append(max(0.0, f.overvoltage_area() - base))
            f.dispatch(names, *NARROW); f.solve()
            res[fam]["narrow"].append(max(0.0, f.overvoltage_area() - base))
    return {fam: {k: round(statistics.median(v), 3) for k, v in d.items()} for fam, d in res.items()}


def variability(names, env_on, steps=6):
    """Mean per-node voltage std across a dispatch toggled on/off (curtailment-spam proxy)."""
    vecs = []
    for step in range(steps):
        f.dispatch(names, *(env_on if step % 2 == 0 else (0.0, 0.0)))
        f.solve()
        vecs.append([x for x in dss.Circuit.AllBusMagPu() if x > 0.01])
    n = min(len(v) for v in vecs)
    return statistics.mean(statistics.pstdev([v[i] for v in vecs]) for i in range(n))


def run_curtailment_spam(n_seeds):
    full, narrow = [], []
    for seed in range(1000, 1000 + n_seeds):
        f.compile_base()
        names = f.place_pv(f.load_buses(), N_PV, seed)
        f.set_load_mult(STATE_LM)
        full.append(variability(names, (P, 0.0)))
        narrow.append(variability(names, NARROW))
    return round(statistics.median(full), 5), round(statistics.median(narrow), 5)


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    f.chdir_feeder()
    ov = run_overvolt(n_seeds)
    spam_full, spam_narrow = run_curtailment_spam(n_seeds)

    print(f"== IEEE 8500 attack families, {n_seeds} seeds, light load (real OpenDSS) ==\n")
    print(f"{'family':16} {'metric':22} {'legacy-full':>12} {'CONTAINDER':>12}")
    for fam, d in ov.items():
        print(f"{fam:16} {'overvoltage area':22} {d['full']:>12.2f} {d['narrow']:>12.3f}")
    print(f"{'curtailment_spam':16} {'volt.variability (pu)':22} {spam_full:>12.5f} {spam_narrow:>12.5f}")

    out = {"overvoltage_families": ov,
           "curtailment_spam": {"full": spam_full, "narrow": spam_narrow},
           "n_seeds": n_seeds, "state": "light_load",
           "note": "Real IEEE 8500, OpenDSS single solver. Overvoltage families use induced "
                   "overvoltage area; curtailment-spam uses per-node voltage std across a toggled "
                   "dispatch. GridLAB-D cross-check and constrained hardware remain."}
    (Path(__file__).resolve().parent / "results" / "attack_families.json").write_text(json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/attack_families.json")


if __name__ == "__main__":
    main()
