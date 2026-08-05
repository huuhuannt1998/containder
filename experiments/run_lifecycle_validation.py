#!/usr/bin/env python3
"""Do the headline lifecycle RATIOS survive an independent control implementation? (validation)

Why this exists
---------------
:mod:`experiments.run_solver_validation` re-implemented the IEEE 1547-2018 Category B
characteristic and found that the *direction* of every contrast survives but the *magnitude* does
not. It tested absolute paired contrasts at one attacker point. The manuscript's headline numbers
are not absolute -- they are ratios, percentage reductions of one lifecycle arm against another
within a single model -- and a common-mode modelling error cancels from a ratio in a way it does
not from a difference. How much cancels was not measured, so the manuscript could claim neither
that those percentages inherit the full sensitivity nor that they escape it.

This measures it. The same three arms that produce the headline -- the long-lived baseline, denial
with session termination, and denial with session termination plus command cancellation -- are
stepped across the same horizon twice: once with OpenDSS's ``InvControl`` doing the volt-var
control, and once with the characteristic re-implemented here and driven to a fixed point by hand
with ``InvControl`` disabled. The comparison is between the two *percentage reductions*, which is
the quantity the paper reports.

Two things make this tractable and faithful at once. The fixed point is **warm-started** from the
previous minute's reactive dispatch, which is both far cheaper and the physically correct model:
a real controller carries its state across the minute rather than restarting from zero. And the
circuit is stepped without recompiling, so regulator taps and capacitor states carry forward
exactly as they do in the confirmatory harness -- which matters, because tap path is what the
solver validation identified as the dominant source of magnitude disagreement.

This tests no pre-registered hypothesis and is excluded from every confirmatory contrast.

Usage: python3 experiments/run_lifecycle_validation.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder
from experiments.stats import boot_ci, paired_contrast

OUT = Path(__file__).resolve().parent / "results" / "lifecycle_validation.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039]

HORIZON_MIN = 60
STEP_S = 60.0
COMPROMISE_MIN = 5
DETECT_MIN = 5
LC_KW = dict(session_max_age_s=3600.0, command_duration_s=900.0, cleanup_latency_s=60.0)

#: The arms behind the manuscript's headline: legacy baseline, and the two cumulative
#: configurations credited with the 50.0% and 69.5% reductions.
HEADLINE = ["denylist+session", "denylist+session+cancel"]

STATES = {
    "ieee8500_stress": {"feeder": "ieee8500", "load_mult": 0.50, "penetration": 1.50,
                        "fleet": 600},
    "ieee123_stress": {"feeder": "ieee123", "load_mult": 1.00, "penetration": 10.0,
                       "fleet": 46},
}

RELAX = 0.1
#: Per-step iteration cap. Warm-starting from the previous minute means the gap to the new fixed
#: point is small, and thirty damped steps at RELAX close 96% of whatever gap remains. An earlier
#: cap of 150 let one arm spend over three hours on a single seed, oscillating rather than
#: converging at a few steps and burning the full budget at each of them, for no fidelity a
#: comparison against a controller with a 5%-of-kvarmax tolerance could use.
MAX_ITER = 30
#: A volt-var loop on a stiff feeder oscillates rather than diverging. When the iterate stops
#: improving there is nothing left to gain, so the step ends and records that it stalled.
STALL_WINDOW = 8
#: Convergence tolerance on the per-iteration reactive change, in kvar. The comparison here is
#: against OpenDSS's ``InvControl``, which stops at its own declared ``varchangetolerance=0.05``
#: -- five per cent of kvarmax, about 0.3 kvar for these units. An earlier version of this file
#: demanded 1e-3 kvar, some three hundred times tighter than the controller it is being compared
#: with, which bought no fidelity and cost more than an hour per seed on IEEE 8500. 0.01 kvar is
#: still an order of magnitude tighter than the vendor criterion.
Q_TOL_KVAR = 1e-2


def _pu_voltage(dss, name):
    """Local per-unit voltage from the bus OpenDSS assigns the unit.

    The bus base rather than a base derived from the element's rating, for the reason recorded in
    ``run_solver_validation._pu_voltage``: deriving it requires replicating a connection-dependent
    line-to-line/line-to-neutral rule that is wrong in opposite directions on the two feeders.
    """
    dss.Circuit.SetActiveElement(f"PVSystem.{name}")
    parts = dss.CktElement.BusNames()[0].split(".")
    dss.Circuit.SetActiveBus(parts[0])
    nodes = list(dss.Bus.Nodes())
    pu = dss.Bus.puVmagAngle()
    mags = {n: pu[2 * k] for k, n in enumerate(nodes) if 2 * k < len(pu)}
    want = [int(x) for x in parts[1:] if x not in ("", "0")] or nodes
    vals = [mags[n] for n in want if n in mags]
    return sum(vals) / len(vals) if vals else 1.0


def _cat_b_kvar(vpu, v_pts, q_pts):
    """The Category B characteristic in physical kvar, written out independently of the harness."""
    if vpu <= v_pts[0]:
        return q_pts[0]
    if vpu >= v_pts[-1]:
        return q_pts[-1]
    for i in range(len(v_pts) - 1):
        v0, v1 = v_pts[i], v_pts[i + 1]
        if v0 <= vpu <= v1:
            if v1 == v0:
                return q_pts[i]
            t = (vpu - v0) / (v1 - v0)
            return q_pts[i] + t * (q_pts[i + 1] - q_pts[i])
    return q_pts[-1]


def one_seed(task):
    import opendssdirect as dss
    from power import confirmatory as C
    from power import profiles as P
    from credsvc import lifecycle as L

    cfg = STATES[task["state"]]
    spec = ensure_feeder(cfg["feeder"])
    seed, lm, n = task["seed"], cfg["load_mult"], cfg["fleet"]
    with C.Session(spec, seed=seed, n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    der = C.DER(p_kw=(cfg["penetration"] * base_load * lm) / n)
    prof = P.horizon_profile(HORIZON_MIN, load_mult=lm)
    v_pts = C.VV_V
    q_legit = der.vv_q_kvar                                   # conformant Category B
    q_attack = (q_legit[0], q_legit[1], q_legit[2], 0.0)      # withdrawal at the high-V end

    # ---------- path A: the harness, InvControl doing the control ---------------------------
    def step_invcontrol(effect):
        C.reset_convergence_counters()
        with C.Session(spec, seed=seed, n_pv=n, load_mult=lm, der=der) as s:
            j = []
            for k in range(HORIZON_MIN):
                C.set_load_mult(prof[k]["load_mult"])
                if effect is not None and effect[k]:
                    s.apply(0.0, "curve", p_kw=der.p_kw * prof[k]["irradiance"])
                else:
                    s.dispatch_legitimate(irradiance=prof[k]["irradiance"])
                C.solve()
                j.append(s.state()["j_band"])
            return j, dict(C.NONCONVERGED)

    # ---------- path B: the characteristic re-implemented, driven by hand -------------------
    def step_independent(effect):
        C.reset_convergence_counters()
        iters, unconverged, residuals = [], 0, []
        with C.Session(spec, seed=seed, n_pv=n, load_mult=lm, der=der) as s:
            dss.Command("Edit InvControl.der1547 enabled=no")
            names = list(s.names)
            q_now = {nm: 0.0 for nm in names}          # warm-started across the horizon
            j = []
            for k in range(HORIZON_MIN):
                C.set_load_mult(prof[k]["load_mult"])
                irr = prof[k]["irradiance"]
                s.set_active_power(der.p_kw * irr)
                q_pts = q_attack if (effect is not None and effect[k]) else q_legit
                it, best, stall, delta = 0, float("inf"), 0, None
                for it in range(1, MAX_ITER + 1):
                    C.solve()
                    delta = 0.0
                    for nm in names:
                        tgt = _cat_b_kvar(_pu_voltage(dss, nm), v_pts, q_pts)
                        new = q_now[nm] + RELAX * (tgt - q_now[nm])
                        delta = max(delta, abs(new - q_now[nm]))
                        q_now[nm] = new
                    for nm in names:
                        dss.Command(f"Edit PVSystem.{nm} kvar={q_now[nm]:.6f}")
                    if delta < Q_TOL_KVAR:
                        break
                    if delta < best * 0.99:
                        best, stall = delta, 0
                    else:
                        stall += 1
                        if stall >= STALL_WINDOW:
                            break
                residuals.append(round(delta, 6) if delta is not None else None)
                C.solve()
                iters.append(it)
                unconverged += int(it >= MAX_ITER)
                j.append(s.state()["j_band"])
            return j, dict(C.NONCONVERGED), iters, unconverged, residuals

    t0 = COMPROMISE_MIN * 60.0
    arms = {"legacy": L.Incident(t_compromise_s=t0)}
    for r in HEADLINE:
        arms[r] = L.Incident(t_compromise_s=t0,
                             t_detect_s=(COMPROMISE_MIN + DETECT_MIN) * 60.0, response=r)

    pol = L.legacy_policy(**LC_KW)
    legit_inv, _ = step_invcontrol(None)
    legit_ind, _, it_legit, unconv_legit, _res_legit = step_independent(None)

    res = {}
    for arm, inc in arms.items():
        sim = L.simulate(pol, inc, HORIZON_MIN * 60.0, STEP_S)
        j_inv, nc_i = step_invcontrol(sim["effect"])
        j_ind, nc_d, its, unconv, step_res = step_independent(sim["effect"])
        res[arm] = {
            "integral_inv": round(sum(j_inv[k] - legit_inv[k] for k in range(HORIZON_MIN)), 6),
            "integral_ind": round(sum(j_ind[k] - legit_ind[k] for k in range(HORIZON_MIN)), 6),
            "nonconverged_inv": nc_i, "nonconverged_ind": nc_d,
            "median_fixed_point_iters": statistics.median(its),
            "max_fixed_point_iters": max(its),
            "steps_hitting_iter_cap": unconv,
            "median_step_residual_kvar": statistics.median(step_res) if step_res else None,
            "max_step_residual_kvar": max(step_res) if step_res else None,
        }

    base_i = res["legacy"]["integral_inv"]
    base_d = res["legacy"]["integral_ind"]
    out = {"state": task["state"], "seed": seed,
           "legacy_integral_inv": base_i, "legacy_integral_ind": base_d,
           "median_fixed_point_iters_legit": statistics.median(it_legit),
           "legit_steps_hitting_iter_cap": unconv_legit}
    for r in HEADLINE:
        ri = res[r]["integral_inv"]
        rd = res[r]["integral_ind"]
        out[f"{r}__pct_inv"] = round(100.0 * (ri - base_i) / base_i, 4) if base_i else None
        out[f"{r}__pct_ind"] = round(100.0 * (rd - base_d) / base_d, 4) if base_d else None
        out[f"{r}__integral_inv"] = ri
        out[f"{r}__integral_ind"] = rd
    out["arms"] = res
    return out


def main(n_seeds: int = 8):
    tasks = [{"state": s, "seed": sd} for s in STATES for sd in SEEDS[:n_seeds]]
    rows = run_tasks(one_seed, tasks, label="lifecycle-validation", every=4)

    summary = []
    for st in STATES:
        g = [r for r in rows if "error" not in r and r["state"] == st]
        if not g:
            continue
        for r in HEADLINE:
            inv = [x[f"{r}__pct_inv"] for x in g if x.get(f"{r}__pct_inv") is not None]
            ind = [x[f"{r}__pct_ind"] for x in g if x.get(f"{r}__pct_ind") is not None]
            if not inv or len(inv) != len(ind):
                continue
            diff = [a - b for a, b in zip(ind, inv)]
            lo, hi = boot_ci(diff)
            summary.append({
                "state": st, "arm": r, "n": len(inv),
                "median_pct_invcontrol": round(statistics.median(inv), 3),
                "median_pct_independent": round(statistics.median(ind), 3),
                "median_pct_point_difference": round(statistics.median(diff), 3),
                "pct_point_diff_ci_lo": lo, "pct_point_diff_ci_hi": hi,
                "sign_agrees": all((a < 0) == (b < 0) for a, b in zip(inv, ind)),
            })

    OUT.write_text(json.dumps({
        "status": "post-hoc validation; tests no hypothesis",
        "question": "do the headline lifecycle percentage reductions survive an independent "
                    "implementation of the volt-var control law?",
        "note": "the solver validation tested absolute contrasts; these are ratios, from which a "
                "common-mode modelling error partly cancels. This measures how much.",
        "states": STATES, "arms": HEADLINE, "detect_min": DETECT_MIN,
        "relaxation": RELAX, "q_tol_kvar": Q_TOL_KVAR, "warm_started": True,
        "seeds": SEEDS[:n_seeds], "rows": rows, "summary": summary}, indent=2))
    print(f"\nwrote {OUT}\n")
    hdr = "%-16s %-26s %4s %12s %12s %12s" % ("state", "arm", "n", "InvControl", "independent",
                                              "difference")
    print(hdr); print("-" * len(hdr))
    for s_ in summary:
        print("%-16s %-26s %4d %11.2f%% %11.2f%% %+11.2f pp" % (
            s_["state"], s_["arm"], s_["n"], s_["median_pct_invcontrol"],
            s_["median_pct_independent"], s_["median_pct_point_difference"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
