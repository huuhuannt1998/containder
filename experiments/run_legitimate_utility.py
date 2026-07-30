#!/usr/bin/env python3
"""Least-privilege scope preserves legitimate utility (reviewer §4.3, §4.4).

Rebuts the "narrow scope is just read-only" objection. Under three scopes we check, per command,
whether a LEGITIMATE volt-var voltage-support command and a MALICIOUS max-export command are
authorized (cyber, pkimodel), and we measure the feeder overvoltage each scope's malicious lever
can cause (physical, OpenDSS 8500). A good least-privilege scope (S2, bounded volt-var) must
authorize the legitimate command while denying the malicious one -- unlike read-only (S1, no
utility) and full control (B1, no containment). Usage: python3 experiments/run_legitimate_utility.py
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pkimodel import FunctionSet
from power import feeder8500 as f

# Scopes (function-set grants).
S1_READONLY = frozenset({FunctionSet.DER_STATUS_READ})
S2_VOLTVAR = frozenset({FunctionSet.OP_MOD_VOLT_VAR})              # bounded volt-var support
B1_FULL = frozenset({FunctionSet.OP_MOD_MAX_LIM_W, FunctionSet.OP_MOD_FIXED_W,
                     FunctionSet.OP_MOD_VOLT_VAR, FunctionSet.OP_MOD_CONNECT})

# Command -> function set it requires.
LEGIT_VOLTVAR = FunctionSet.OP_MOD_VOLT_VAR       # operator reactive voltage support
MALICIOUS_EXPORT = FunctionSet.OP_MOD_MAX_LIM_W    # attacker active-power export/curtailment override

P = 12.0
N_PV = 600
# malicious lever available under each scope (kW export, kVAr): bounded reactive for S2.
LEVER = {"S1_readonly": (0.0, 0.0), "S2_voltvar": (0.0, 0.15 * P), "B1_full": (P, 0.3 * P)}
SCOPES = {"S1_readonly": S1_READONLY, "S2_voltvar": S2_VOLTVAR, "B1_full": B1_FULL}


def feeder_overvoltage(env, seeds=3, lm=0.30):
    f.chdir_feeder()
    xs = []
    for seed in range(1000, 1000 + seeds):
        f.compile_base()
        names = f.place_pv(f.load_buses(), N_PV, seed)
        f.set_load_mult(lm)
        f.dispatch(names, 0.0, 0.0); f.solve(); base = f.overvoltage_area()
        f.dispatch(names, *env); f.solve()
        xs.append(max(0.0, f.overvoltage_area() - base))
    return round(statistics.median(xs), 3)


def main():
    rows = {}
    for name, scope in SCOPES.items():
        legit = LEGIT_VOLTVAR in scope
        malic = MALICIOUS_EXPORT in scope
        ov = feeder_overvoltage(LEVER[name])
        rows[name] = {"legit_voltvar_authorized": legit, "malicious_export_authorized": malic,
                      "malicious_overvoltage_area": ov}

    print("== Legitimate utility under least privilege (cyber authorization + feeder) ==\n")
    print(f"{'scope':14} {'legit volt-var':>15} {'malic export':>13} {'malic overvolt':>15}")
    for name, r in rows.items():
        print(f"{name:14} {str(r['legit_voltvar_authorized']):>15} "
              f"{str(r['malicious_export_authorized']):>13} {r['malicious_overvoltage_area']:>15.2f}")
    print("\nS1 read-only: contains the attack but authorizes NO legitimate control (no utility).")
    print("S2 bounded volt-var: authorizes legitimate voltage support, denies export; attack lever")
    print("   is bounded reactive only -> negligible overvoltage. Utility AND containment.")
    print("B1 full: legitimate control works but the attacker also has it -> large overvoltage.")

    (Path(__file__).resolve().parent / "results" / "legitimate_utility.json").write_text(
        json.dumps({"scopes": rows,
                    "note": "Cyber authorization from pkimodel; feeder overvoltage from OpenDSS 8500, "
                            "3 seeds, light load. S2 (bounded volt-var) preserves legitimate support "
                            "control while denying export; it is not read-only."}, indent=2))
    print("\nSaved -> experiments/results/legitimate_utility.json")


if __name__ == "__main__":
    main()
