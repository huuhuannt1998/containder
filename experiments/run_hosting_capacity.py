#!/usr/bin/env python3
"""C1 (calibration): locate each feeder's compliant hosting limit under legitimate operation.

Why this experiment exists
--------------------------
Every physical result in the pilot was measured at a single "light load / high PV" point that
places 7.2 MW of PV against 3.24 MW of load -- 222% penetration -- at which the *legitimate*
feeder, unattacked and under the conformant IEEE 1547 Category B characteristic, is already far
outside the ANSI C84.1 upper band. A containment result demonstrated only there is a result
about an overstressed feeder, and a reviewer is entitled to ask whether it survives at a state
an operator would actually run.

This script finds, for each feeder and load multiplier, the highest PV penetration at which
legitimate operation still holds the upper band across every seed. That limit defines the
operating tiers at which the confirmatory experiments are then run.

**Penetration, not fleet count, is the independent variable.** IEEE 123 has 91 load buses, so a
fleet-count sweep saturates there: every fleet above 91 produces an identical circuit and an
identical voltage profile. The fleet is therefore fixed at the feeder's load-bus population and
the per-unit rating is solved from the target penetration, which makes the two feeders directly
comparable.

Status: **calibration, not confirmatory.** Its output fixes the operating tiers the frozen
scenario matrix refers to; it tests no hypothesis and applies no treatment. The compliance
criterion is declared here before the sweep runs:

    compliant  <=>  in every seed, legitimate operation adds no more than TAU = 0.10 p.u.-node
                    of overvoltage area above the same feeder's own zero-PV base case.

The tolerance is relative to the zero-PV base because the IEEE 8500 base case is itself
marginally outside the band (9 of 8531 nodes above 1.05 p.u., area 0.015 p.u.-node, at light
load with no PV present). An absolute "no node above 1.05" criterion would therefore report a
hosting capacity of zero on that feeder for reasons that have nothing to do with PV. TAU
isolates the PV-attributable part, which is what hosting capacity means.

Usage: python3 experiments/run_hosting_capacity.py [n_seeds]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "hosting_capacity.json"

#: PV-attributable overvoltage tolerance defining compliance, p.u.-node. Declared before the run.
TAU = 0.10

LOAD_MULTS = [0.30, 0.50, 0.75, 1.00]

#: Target penetrations (PV nameplate kW / connected load kW at the multiplier in force).
#: Capped at 2.5: on IEEE 8500 the legitimate case at 300% penetration exhausts the full
#: pre-registered retry ladder (500 -> 1500 -> 4500 control iterations, ~60 s) and is retained as
#: a flagged non-convergence rather than a measurement. The hosting limit lies far below this on
#: both feeders, so the cap does not truncate the quantity being estimated.
PENETRATIONS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.75, 0.90, 1.00,
                1.25, 1.50, 2.00, 2.50]

#: Fleet size per feeder: the feeder's full load-bus population, so unit rating carries the sweep.
FLEET = {"ieee8500": 600, "ieee123": 91}

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051]


def unit_kw(pen: float, base_load_kw: float, lm: float, n: int) -> float:
    """Per-unit rating that realises the target penetration with an ``n``-unit fleet."""
    return (pen * base_load_kw * lm) / n if n else 0.0


def measure(task):
    """One legitimate (unattacked) arm at the requested penetration. Runs in a pool worker."""
    from power import confirmatory as C

    spec = ensure_feeder(task["feeder"])
    seed, pen, lm, n = task["seed"], task["penetration"], task["load_mult"], task["fleet"]
    # Two-pass: connected load is only known after compiling, so probe once, then rebuild at
    # the unit rating that realises the target penetration.
    with C.Session(spec, seed=seed, n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    p_kw = unit_kw(pen, base_load, lm, n)
    n_eff = n if p_kw > 0.0 else 0
    C.reset_convergence_counters()
    with C.Session(spec, seed=seed, n_pv=n_eff, load_mult=lm,
                   der=C.DER(p_kw=p_kw if p_kw > 0 else 12.0)) as s:
        s.dispatch_legitimate()
        converged = C.solve()
        st = s.state()
        st["penetration_actual"] = round(s.penetration, 4) if n_eff else 0.0
        st["pv_kw"] = round(s.pv_kw, 2)
        st["unit_kw"] = round(p_kw, 4)
    st["converged"] = converged
    st["base_load_kw"] = round(base_load, 2)
    st.update({k: task[k] for k in ("feeder", "seed", "penetration", "load_mult")})
    return st


def main(n_seeds: int = 5):
    seeds = SEEDS[:n_seeds]
    out = {"criterion": f"legitimate PV-attributable overvoltage area <= TAU={TAU} p.u.-node "
                        f"above the same feeder's zero-PV base, in every seed",
           "tau": TAU,
           "status": "calibration (not confirmatory)",
           "seeds": seeds, "load_mults": LOAD_MULTS, "penetrations": PENETRATIONS,
           "fleet": FLEET, "feeders": {}}

    tasks = [{"feeder": key, "seed": sd, "penetration": pen, "load_mult": lm,
              "fleet": FLEET[key]}
             for key in FLEET for lm in LOAD_MULTS for pen in PENETRATIONS for sd in seeds]
    results = run_tasks(measure, tasks, label="hosting-capacity", every=50)

    for key in FLEET:
        rows = []
        for lm in LOAD_MULTS:
            for pen in PENETRATIONS:
                per = [r for r in results if "error" not in r and r["feeder"] == key
                       and r["load_mult"] == lm and r["penetration"] == pen]
                if not per:
                    continue
                rows.append({
                    "load_mult": lm, "penetration": pen,
                    "penetration_actual": per[0]["penetration_actual"],
                    "unit_kw": per[0]["unit_kw"], "pv_kw": per[0]["pv_kw"],
                    "max_area_over": round(max(r["area_over"] for r in per), 4),
                    "med_area_over": round(sorted(r["area_over"] for r in per)[len(per)//2], 4),
                    "max_n_over": max(r["n_over"] for r in per),
                    "max_vmax": round(max(r["vmax"] for r in per), 4),
                    "min_vmin": round(min(r["vmin"] for r in per), 4),
                    "max_area_under": round(max(r["area_under"] for r in per), 4),
                    "any_screen": any(r["screen"] for r in per),
                    "med_q_fleet_kvar": round(
                        sorted(r["q_fleet_kvar"] for r in per)[len(per)//2], 2),
                    "n_nonconverged": sum(1 for r in per if not r["converged"]),
                })

        limits = {}
        for lm in LOAD_MULTS:
            sub = sorted([r for r in rows if r["load_mult"] == lm], key=lambda r: r["penetration"])
            base = next(r["max_area_over"] for r in sub if r["penetration"] == 0.0)
            # The limit is the last penetration before the first violation, so that the tiers
            # below it are contiguous rather than reaching past an intervening violation.
            limit = 0.0
            for r in sub:
                if r["penetration"] == 0.0:
                    continue
                if (r["max_area_over"] - base) <= TAU:
                    limit = r["penetration"]
                else:
                    break
            limits[str(lm)] = {"base_area_over": base, "penetration_limit": limit}
        out["feeders"][key] = {
            "label": key, "rows": rows, "limits": limits,
            "n_nonconverged": sum(1 for r in results
                                  if "error" not in r and r["feeder"] == key
                                  and not r["converged"]),
            "n_failed": sum(1 for r in results if "error" in r
                            and r.get("task", {}).get("feeder") == key)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}")
    for key, f in out["feeders"].items():
        print(f"\n{f['label']}: compliant hosting limit (legitimate operation, TAU={TAU})")
        for lm, lim in f["limits"].items():
            print(f"  load_mult {lm}: penetration <= {lim['penetration_limit']:.2f} "
                  f"(zero-PV base overvoltage area {lim['base_area_over']:.4f})")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
