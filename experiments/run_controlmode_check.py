#!/usr/bin/env python3
"""Control-mode diagnostic: evidence for the claim in Section VI that feeder controls are live.

Section VI states that we solve with ``controlmode=static``, which does *not* disable the
regulator, LTC and capacitor controls, and quantifies what turning them off would do. Those
numbers were previously reported without a released artifact. This script regenerates them.

Emits ``results/controlmode.json``.

Usage: python3 experiments/run_controlmode_check.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500v2 as f

SEED = 1000
N_PV = 600
LM = 0.30


def arm(control_mode: str) -> dict:
    """Base solve then a full-scope attack solve, under one control mode.

    Control activity is measured twice: from the as-compiled state to the converged base case
    (what the feeder's own regulation does to serve legitimate PV), and from the base case to the
    attack case (what it does in response to the compromise).
    """
    import opendssdirect as dss
    with f.Session(seed=SEED, n_pv=N_PV, load_mult=LM, control_mode=control_mode) as s:
        cold_taps, cold_caps = f.tap_positions(), f.cap_states()
        f.dispatch_legitimate(s.names)
        f.solve()
        base_iters = dss.Solution.ControlIterations()
        base_taps, base_caps = f.tap_positions(), f.cap_states()
        base_area, base_vmax = f.overvoltage_area(), max(f.bus_pu())

        f.dispatch(s.names, f.P_PV_KW, 0.30 * f.P_PV_KW)
        f.solve()
        atk_iters = dss.Solution.ControlIterations()
        atk_taps, atk_caps = f.tap_positions(), f.cap_states()
        atk_area, atk_vmax = f.overvoltage_area(), max(f.bus_pu())

    return {"control_mode": control_mode,
            "base": {"overvoltage_area": round(base_area, 4), "vmax": round(base_vmax, 4),
                     "control_iterations": base_iters,
                     "tap_operations_from_cold": f.count_tap_operations(cold_taps, base_taps),
                     "capacitor_changes_from_cold": f.count_cap_operations(cold_caps, base_caps)},
            "attack_full_scope": {"overvoltage_area": round(atk_area, 4),
                                  "vmax": round(atk_vmax, 4),
                                  "control_iterations": atk_iters},
            "tap_operations_base_to_attack": f.count_tap_operations(base_taps, atk_taps),
            "capacitor_changes_base_to_attack": f.count_cap_operations(base_caps, atk_caps),
            "regulators_moved_from_cold": sum(1 for k, v in cold_taps.items()
                                              if base_taps.get(k) != v),
            "regulators_moved_base_to_attack": sum(1 for k, v in base_taps.items()
                                                   if atk_taps.get(k) != v),
            "regulator_count": len(base_taps), "capacitor_count": len(base_caps),
            "definitions": {
                "tap_operations": "sum of |delta tap position| over all regulators",
                "regulators_moved": "count of regulators whose tap position changed at all",
                "control_iterations": "OpenDSS Solution.ControlIterations() for that solve"}}


def main():
    f.chdir_feeder()
    out = {"seed": SEED, "n_pv": N_PV, "load_mult": LM,
           "attack_scope_kw_kvar": [f.P_PV_KW, 0.30 * f.P_PV_KW],
           "arms": {cm: arm(cm) for cm in ("static", "off")},
           "note": "Single seed, light load. 'static' is the mode used for every result in the "
                   "paper; feeder regulator/LTC/capacitor controls operate under it. 'off' is "
                   "shown only to quantify how much the controls absorb, and is not used "
                   "anywhere else."}
    st, of = out["arms"]["static"], out["arms"]["off"]
    out["controls_absorb_ratio"] = round(
        of["attack_full_scope"]["overvoltage_area"]
        / max(st["attack_full_scope"]["overvoltage_area"], 1e-9), 3)
    for cm, a in out["arms"].items():
        print(f"controlmode={cm:6} base area {a['base']['overvoltage_area']:9.4f} "
              f"vmax {a['base']['vmax']:.4f} | attack area "
              f"{a['attack_full_scope']['overvoltage_area']:9.4f} "
              f"vmax {a['attack_full_scope']['vmax']:.4f} | "
              f"taps {a['tap_operations_base_to_attack']} caps "
              f"{a['capacitor_changes_base_to_attack']}")
    print(f"controls absorb a factor of {out['controls_absorb_ratio']}")
    (Path(__file__).resolve().parent / "results" / "controlmode.json").write_text(
        json.dumps(out, indent=2))
    print("Saved -> experiments/results/controlmode.json")


if __name__ == "__main__":
    main()
