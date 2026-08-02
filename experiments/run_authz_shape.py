#!/usr/bin/env python3
"""RQ2 (confirmatory): does authorization *shape* contain, and at which operating states?

Hypotheses tested (frozen in ``PREREGISTRATION_CONFIRMATORY.md`` before this ran):

* **H1 (shape, not width).** At a fixed operating tier, the worst admissible point of a
  symmetric cap Q1 -- which contains zero absorption at every width -- produces more harm than
  the worst admissible point of an absorption floor Q2 of the same width, and the Q1 excess does
  not diminish as the cap narrows.
* **H2 (reliance conditionality).** The withdrawal-of-absorption effect is governed by the
  reactive absorption the fleet actually delivers under the conformant characteristic, not by
  penetration as such, and is not materially different from zero at every rung where legitimate
  operation is compliant. *Not blind; see §0 of the pre-registration.*
* **H3 (primitive versus feasible set).** Given matched feasible sets, ``opModFixedVar`` and
  ``opModVoltVar`` semantics do not differ materially on the primary endpoint.

Three things distinguish this from the pilot's reactive sweep.

1. **An authorization is a set and the adversary plays its worst point.** The pilot fixed one
   setpoint per arm and reported the harm at that point, which measures a setpoint, not an
   authorization. Here each set carries an explicit grid of admissible points, declared in code
   before the run, and the reported harm is the maximum over that grid -- with the argmax
   retained, because *where in its authorized set the adversary ends up* is the whole content of
   the shape claim.

2. **Both primitives receive the identical physical bound.** The pilot's two arms differed by a
   factor of 2.46 in commanded kvar at nominally identical labels, so its cross-primitive
   comparison confounded the bound with the function set carrying it.

3. **The endpoint is two-sided.** A one-sided overvoltage endpoint cannot price the undervoltage
   that a forced absorption floor causes, and the service-deficit endpoint decides whether an
   authorization that contains also still delivers volt-var.

Usage: python3 experiments/run_authz_shape.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "authz_shape.json"
CAL = Path(__file__).resolve().parent / "results" / "hosting_capacity.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051,
         1061, 1063, 1069, 1087, 1091, 1093, 1097, 1103, 1109, 1117]

#: Explicit penetration ladder per feeder, straddling each feeder's compliance transition.
#: A ladder defined as fractions of the calibrated limit is not usable because IEEE 123's limit
#: is right-censored: that feeder holds the band at every penetration tested, since its voltages
#: stay inside the volt-var deadband and the fleet therefore delivers almost no absorption.
#: See PREREGISTRATION_CONFIRMATORY.md §3.
#:
#: Amendment, recorded before any result of this sweep was seen: the top rung of each ladder
#: (IEEE 8500 at 2.00, IEEE 123 at 14.00) was removed and the attacker grid reduced from 9 to 7
#: points. At those rungs the strong-injection points exhaust the pre-registered retry ladder --
#: 500 -> 1500 -> 4500 control iterations, about 60 s per arm -- and the sweep projected 4.5
#: hours. The removed rungs are stress cases well beyond each feeder's compliance transition;
#: every rung supporting a primary claim is retained, as is the 20-seed count. The retry policy
#: itself is unchanged.
LADDER = {
    "ieee8500": {"load_mult": 0.50, "penetrations": [0.50, 1.00, 1.50],
                 "calibrated_limit": 0.50},
    "ieee123": {"load_mult": 1.00, "penetrations": [2.00, 6.00, 10.00],
                "calibrated_limit": None},   # right-censored above 12.0
}

FLEET = {"ieee8500": 600, "ieee123": 91}

PRIMITIVES = ["setpoint", "curve"]

GRID_N = 7


def _linspace(a, b, n):
    if n <= 1 or a == b:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def authorization_sets(qb: float):
    """Every authorization set, as (family, label, width, admissible-grid in kvar).

    ``qb`` is the DER's Category B reactive capability in kvar. Positive = injection.
    """
    sets = []
    # Q1: symmetric magnitude cap. Contains zero absorption at every width.
    for frac in (1.00, 0.75, 0.50, 0.25):
        c = frac * qb
        sets.append(("Q1", f"Q1 cap |q|<={frac:.2f}Qb", round(2 * c, 4),
                     [round(x, 6) for x in _linspace(-c, c, GRID_N)]))
    # Q2: absorption floor. Excludes zero absorption by construction.
    for frac in (0.25, 0.50, 0.75, 1.00):
        lo, hi = -qb, -frac * qb
        width = round(hi - lo, 4)
        sets.append(("Q2", f"Q2 floor q<=-{frac:.2f}Qb", width,
                     [round(x, 6) for x in _linspace(lo, hi, GRID_N)]))
    # Q3: tube around the conformant characteristic's high-voltage point (-Qb), clipped to
    # the inverter's capability.
    for frac in (0.25, 0.50):
        eps = frac * qb
        lo, hi = max(-qb, -qb - eps), min(qb, -qb + eps)
        sets.append(("Q3", f"Q3 tube eps={frac:.2f}Qb", round(hi - lo, 4),
                     [round(x, 6) for x in _linspace(lo, hi, GRID_N)]))
    # Q5: no remote reactive authority at all; the conformant curve stands.
    sets.append(("Q5", "Q5 read-only", 0.0, [round(-qb, 6)]))
    return sets


def one_arm(task):
    """Evaluate every admissible point of one authorization set and return the worst."""
    from power import confirmatory as C

    key = task["feeder"]
    spec = ensure_feeder(key)
    n = FLEET[key]
    lm = task["load_mult"]

    # Unit rating that realises the tier's penetration.
    with C.Session(spec, seed=task["seed"], n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    p_kw = (task["penetration"] * base_load * lm) / n
    der = C.DER(p_kw=p_kw)

    C.reset_convergence_counters()
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s:
        s.dispatch_legitimate()
        base_conv = C.solve()
        base = s.state()
        base_taps = C.tap_positions()
        base_caps = C.cap_states()

        pts = []
        for q in task["grid"]:
            s.apply(q, task["primitive"])
            conv = C.solve()
            st = s.state()
            pts.append({
                "q_kvar": q,
                "dJ_band": round(st["j_band"] - base["j_band"], 6),
                "dArea_over": round(st["area_over"] - base["area_over"], 6),
                "dArea_under": round(st["area_under"] - base["area_under"], 6),
                "j_band": round(st["j_band"], 6),
                "vmax": st["vmax"], "vmin": st["vmin"],
                "n_out": st["n_out"],
                "screen": st["screen"],
                "induced_screen": bool(st["screen"] and not base["screen"]),
                "tap_ops": C.count_tap_operations(base_taps, C.tap_positions()),
                "cap_ops": C.count_cap_operations(base_caps, C.cap_states()),
                "deficit_frac": st["deficit_frac"],
                "support_deficit_kvar": st["support_deficit_kvar"],
                "q_fleet_kvar": st["q_fleet_kvar"],
                "converged": conv,
            })

    # The oracle adversary plays the admissible point maximising the primary endpoint.
    worst = max(pts, key=lambda p: p["dJ_band"])
    return {
        "feeder": key, "tier": task["tier"], "penetration": task["penetration"],
        "load_mult": lm, "family": task["family"], "set_label": task["set_label"],
        "width_kvar": task["width"], "primitive": task["primitive"], "seed": task["seed"],
        "unit_kw": round(p_kw, 4), "qb_kvar": round(der.q_cat_b, 4),
        "base_j_band": round(base["j_band"], 6),
        "base_area_over": round(base["area_over"], 6),
        "base_screen": base["screen"], "base_converged": base_conv,
        "base_deficit_frac": base["deficit_frac"],
        "worst": worst,
        "argmax_q_kvar": worst["q_kvar"],
        "argmax_q_frac_qb": round(worst["q_kvar"] / der.q_cat_b, 4) if der.q_cat_b else 0.0,
        "points": pts,
        "nonconverged": dict(C.NONCONVERGED),
    }


def build_tasks(n_seeds):
    tasks = []
    for key, cfg in LADDER.items():
        lm = cfg["load_mult"]
        for pen in cfg["penetrations"]:
            for seed in SEEDS[:n_seeds]:
                tasks.append({"feeder": key, "tier": f"pen{pen:g}", "penetration": pen,
                              "load_mult": lm, "seed": seed})
    return tasks


def expand_sets(tasks):
    """Attach each authorization set and primitive to each (feeder, tier, seed) task."""
    from power import confirmatory as C
    out = []
    # qb scales with the unit rating, so it must be computed per (feeder, tier). One probe per
    # distinct (feeder, tier) is enough since the base load does not depend on the seed.
    cache = {}
    for t in tasks:
        ck = (t["feeder"], t["tier"])
        if ck not in cache:
            spec = C.FEEDERS[t["feeder"]]
            C.chdir_feeder(spec)
            with C.Session(spec, seed=t["seed"], n_pv=0, load_mult=t["load_mult"]) as p:
                bl = p.base_load_kw
            p_kw = (t["penetration"] * bl * t["load_mult"]) / FLEET[t["feeder"]]
            cache[ck] = C.DER(p_kw=p_kw).q_cat_b
        qb = cache[ck]
        for family, label, width, grid in authorization_sets(qb):
            for prim in PRIMITIVES:
                if family == "Q5" and prim == "setpoint":
                    continue          # read-only has no setpoint realisation
                out.append({**t, "family": family, "set_label": label,
                            "width": width, "grid": grid, "primitive": prim})
    return out


def summarize(rows):
    """Paired-by-seed summaries for the declared contrasts."""
    def key(r):
        return (r["feeder"], r["tier"], r["set_label"], r["primitive"])

    groups = {}
    for r in rows:
        if "error" in r:
            continue
        groups.setdefault(key(r), []).append(r)

    summary = []
    for k, g in sorted(groups.items()):
        dj = [x["worst"]["dJ_band"] for x in g]
        summary.append({
            "feeder": k[0], "tier": k[1], "set_label": k[2], "primitive": k[3],
            "family": g[0]["family"], "penetration": g[0]["penetration"],
            "n": len(g),
            "median_dJ_band": round(statistics.median(dj), 4),
            "mean_dJ_band": round(statistics.fmean(dj), 4),
            "min_dJ_band": round(min(dj), 4), "max_dJ_band": round(max(dj), 4),
            "frac_induced_screen": round(
                sum(1 for x in g if x["worst"]["induced_screen"]) / len(g), 3),
            "median_argmax_q_frac_qb": round(
                statistics.median([x["argmax_q_frac_qb"] for x in g]), 4),
            "median_deficit_frac": round(
                statistics.median([x["worst"]["deficit_frac"] for x in g]), 4),
            "median_tap_ops": statistics.median([x["worst"]["tap_ops"] for x in g]),
            "median_dArea_under": round(
                statistics.median([x["worst"]["dArea_under"] for x in g]), 4),
            "median_base_j_band": round(
                statistics.median([x["base_j_band"] for x in g]), 4),
            "n_nonconverged": sum(x["nonconverged"]["n"] for x in g),
        })
    return summary


def main(n_seeds: int = 20):
    if not CAL.exists():
        sys.exit(f"calibration not found: {CAL}. Run run_hosting_capacity.py first.")
    cal = json.loads(CAL.read_text())
    limits = {k: v["limits"] for k, v in cal["feeders"].items()}

    tasks = expand_sets(build_tasks(n_seeds))
    rows = run_tasks(one_arm, tasks, label="authz-shape", every=100)

    out = {"status": "confirmatory",
           "hypotheses": ["H1 shape-not-width", "H2 reliance conditionality (not blind)",
                          "H3 primitive vs feasible set"],
           "primary_endpoint": "dJ_band (two-sided ANSI Range A violation area, p.u.-node)",
           "ladder": LADDER, "calibrated_limits": limits,
           "seeds": SEEDS[:n_seeds], "grid_n": GRID_N,
           "rows": rows, "summary": summarize(rows)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {OUT}  ({len(rows)} arms, {sum(1 for r in rows if 'error' in r)} failed)")

    print("\n%-9s %-5s %-22s %-9s %8s %8s %7s %8s" %
          ("feeder", "tier", "set", "primitive", "medDJ", "screen", "argmaxQ", "deficit"))
    for s in out["summary"]:
        print("%-9s %-5s %-22s %-9s %8.3f %8.2f %7.2f %8.3f" %
              (s["feeder"], s["tier"], s["set_label"], s["primitive"],
               s["median_dJ_band"], s["frac_induced_screen"],
               s["median_argmax_q_frac_qb"], s["median_deficit_frac"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 20)
