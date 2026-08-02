#!/usr/bin/env python3
"""Emit the run inventory the supplement reports, so its counts are checkable like any other.

The supplement tabulates how many seeds, arms and power-flow solves stand behind each experiment.
Those are derived counts: they exist nowhere in the result files, which store outcomes rather than
census data. Quoting them in the paper without emitting them would put two numerals outside the
freeze gate that checks every other one, so this script derives them from the result files and
writes them where `check_numbers.py` can find them.

Usage: python3 experiments/build_inventory.py
"""
import json
from pathlib import Path

RES = Path(__file__).resolve().parent / "results"
OUT = RES / "run_inventory.json"


def load(name):
    p = RES / name
    return json.loads(p.read_text()) if p.exists() else None


def ok_rows(d, key="rows"):
    return [r for r in (d or {}).get(key, []) if "error" not in r]


def main():
    inv = {}

    cal = load("hosting_capacity.json")
    if cal:
        arms = sum(len(v["rows"]) for v in cal["feeders"].values()) * len(cal["seeds"])
        inv["hosting_capacity"] = {
            "seeds": len(cal["seeds"]),
            "arms": arms,
            # One legitimate solve per arm, plus the zero-PV probe that precedes it.
            "solves": arms * 2,
            "status": "calibration",
        }

    shape = load("authz_shape.json")
    if shape:
        rows = ok_rows(shape)
        inv["authz_shape"] = {
            "seeds": len(shape["seeds"]),
            "arms": len(rows),
            "solves": sum(len(r["points"]) + 1 for r in rows),
            "feeders": len({r["feeder"] for r in rows}),
            "rungs_per_feeder": len({r["penetration"] for r in rows}) // 2,
            "sets": len({r["set_label"] for r in rows}),
            "status": "confirmatory",
        }

    lc = load("lifecycle_physical.json")
    if lc:
        rows = ok_rows(lc)
        n_arms = len(rows[0]["arms"]) if rows else 0
        inv["lifecycle_physical"] = {
            "seeds": len(lc["seeds"]),
            "arms": len(rows),
            "lifecycle_arms_per_seed": n_arms,
            # Each seed-arm steps the horizon once per lifecycle arm plus once legitimate.
            "solves": len(rows) * (n_arms + 1) * lc["horizon_min"],
            "horizon_min": lc["horizon_min"],
            "status": "confirmatory",
        }

    at = load("attackers.json")
    if at:
        rows = ok_rows(at)
        inv["attackers"] = {
            "seeds": len(at["seeds"]),
            "arms": len(rows),
            "solves": sum(len(r.get("points", [])) + 1 for r in rows),
            "status": "confirmatory",
        }

    rr = load("reliance_resolution.json")
    if rr:
        rows = ok_rows(rr)
        inv["reliance_resolution"] = {
            "seeds": len(rr["seeds"]),
            "arms": len(rows),
            "solves": len(rows) * 8,     # 7 admissible points plus the legitimate base
            "status": "post-hoc",
        }

    sv = load("lifecycle_sensitivity.json")
    if sv:
        inv["lifecycle_sensitivity"] = {
            "settings": sv["grid_size"], "solves": 0,
            "status": "post-hoc, model only",
        }

    OUT.write_text(json.dumps({"note": "derived counts quoted in the supplement's inventory "
                                       "table; emitted so they fall inside the freeze gate",
                               "experiments": inv}, indent=2))
    print(f"wrote {OUT}\n")
    print("%-28s %7s %7s %9s  %s" % ("experiment", "seeds", "arms", "solves", "status"))
    for k, v in inv.items():
        print("%-28s %7s %7s %9s  %s" % (k, v.get("seeds", v.get("settings", "-")),
                                         v.get("arms", "-"), v.get("solves", "-"),
                                         v["status"]))


if __name__ == "__main__":
    main()
