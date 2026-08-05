#!/usr/bin/env python3
"""Is the physics layer right? Three independent checks. (post-hoc validation)

Why this exists
---------------
Every physical number in the manuscript comes from one solver and, worse, from one *component*
of it: OpenDSS's ``InvControl`` object, which realises the IEEE 1547-2018 Category B volt-var
characteristic that defines the legitimate baseline. If that component behaves differently from
the standard it implements, every contrast in the paper inherits the error silently, because the
attacker arms and the baseline arm are produced by the same object.

A second solver would be the textbook answer, and it is not available here: neither GridLAB-D nor
pandapower ingests these feeders without a hand-written converter whose own bugs would be
indistinguishable from a solver disagreement. So this file does the thing that is actually
diagnostic rather than the thing that merely sounds authoritative --- it re-implements the parts
that could be wrong and checks the solver against them.

Three checks, each a different failure mode:

1. **Conservation.** Does the converged solution satisfy power balance? Source injection plus
   fleet generation must equal load plus losses. This catches a misconfigured circuit, a
   mis-specified PV element, or a solution accepted before convergence.

2. **The control, re-implemented.** The Category B characteristic is a piecewise-linear map from
   local voltage to reactive power. We implement it here in Python, in physical kvar, and drive
   it to a fixed point by hand: solve, read each unit's terminal voltage, evaluate the
   characteristic, write plain ``kvar`` on the PVSystem, re-solve, repeat. ``InvControl`` is
   disabled throughout, so this path shares no control code with the harness. If the harness's
   endpoint --- the two-sided band integral ``J_band`` --- agrees between the two, the endpoint
   does not depend on the vendor's controller. This is the check that matters.

3. **Solution algorithm.** OpenDSS offers a fixed-point ("Normal") and a Newton algorithm. Both
   are run at the same operating point. Agreement is weak evidence, but disagreement would be
   strong evidence of a badly conditioned solution being reported as converged.

This tests no hypothesis and is excluded from every confirmatory contrast.

Usage: python3 experiments/run_solver_validation.py [n_seeds]
"""
import json
import statistics
import sys
from math import sqrt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from experiments._runner import run_tasks, ensure_feeder

OUT = Path(__file__).resolve().parent / "results" / "solver_validation.json"

SEEDS = [1001, 1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049, 1051]

#: Rungs drawn from the confirmatory ladder itself, two per feeder: the top rung, where the
#: solution is hardest, and the one below it, so a disagreement at the top can be told apart from
#: a disagreement everywhere.
STATES = {
    "ieee8500": {"load_mult": 0.50, "fleet": 600, "penetrations": [1.00, 1.50]},
    "ieee123": {"load_mult": 1.00, "fleet": 46, "penetrations": [6.00, 10.00]},
}

#: Fixed-point iteration controls for the re-implemented characteristic. The relaxation factor
#: mirrors InvControl's ``deltaQ_factor``; without damping the volt-var loop oscillates on a stiff
#: feeder rather than converging, which is a property of the control problem and not of either
#: implementation.
RELAX = 0.1
MAX_ITER = 400
Q_TOL_KVAR = 1e-3
#: When the iterate stops improving the loop is oscillating rather than converging, and the cure
#: is more damping, not more iterations. The relaxation is halved after a stagnant window.
STALL_WINDOW = 25


def _pu_voltage(dss, name, kv=None, nph=None):
    """Local per-unit voltage at one unit, taken from the bus the unit is connected to.

    Deriving the base from the element's own rated ``kv`` requires replicating OpenDSS's
    connection-dependent line-to-line/line-to-neutral rule, and two attempts to do that were
    wrong in two different ways. IEEE~8500's two-phase 120/240\,V secondaries declare
    ``kv=0.208`` line-to-line, so a line-to-neutral reading normalised against 208\,V came out at
    $0.61$ p.u. rather than $1.06$. IEEE~123 then supplied the mirror case: its line-to-line
    connected single-phase units at buses such as ``65.3.1`` declare ``kv=4.16``, which *is* the
    phase-to-phase base, while ``VoltagesMagAng`` reports conductor-to-ground. Each error made the
    re-implementation command full reactive injection on an over-voltage feeder, and each showed
    up as a disagreement that looked like a solver finding.

    Both are avoided by not deriving a base at all. The bus per-unit voltage is what OpenDSS
    itself assigns from the circuit's declared voltage bases, and it is the same quantity the
    band-integral endpoint is computed from, so the re-implementation and the metric agree on
    what "local voltage" means. ``kv`` and ``nph`` are accepted and ignored so the call sites and
    the base-agreement audit keep a common signature.
    """
    dss.Circuit.SetActiveElement(f"PVSystem.{name}")
    busfull = dss.CktElement.BusNames()[0]
    parts = busfull.split(".")
    dss.Circuit.SetActiveBus(parts[0])
    nodes = list(dss.Bus.Nodes())
    pu = dss.Bus.puVmagAngle()
    mags = {n: pu[2 * k] for k, n in enumerate(nodes) if 2 * k < len(pu)}
    want = [int(x) for x in parts[1:] if x not in ("", "0")] or nodes
    vals = [mags[n] for n in want if n in mags]
    return sum(vals) / len(vals) if vals else 1.0


def _rated_base_agrees(dss, name, kv, nph, tol=0.01):
    """Does the element's rated base match the bus base OpenDSS assigns it?

    Recorded, not enforced. Where they disagree --- the line-to-line connected units --- the two
    plausible readings of ``voltage_curvex_ref=rated`` differ, and that ambiguity is a property of
    the model rather than of either implementation. The count is reported with the results.
    """
    dss.Circuit.SetActiveElement(f"PVSystem.{name}")
    bus = dss.CktElement.BusNames()[0].split(".")[0]
    dss.Circuit.SetActiveBus(bus)
    bus_base_v = dss.Bus.kVBase() * 1000.0
    mine = (kv * 1000.0 / sqrt(3.0)) if nph > 1 else (kv * 1000.0)
    return abs(mine - bus_base_v) / bus_base_v <= tol


def _cat_b_kvar(vpu, v_points, q_points):
    """IEEE 1547-2018 Table 8 Category B characteristic, evaluated in physical kvar.

    Piecewise linear through the four breakpoints and flat outside them. Written out rather than
    delegated so that it shares no code with the harness under test.
    """
    if vpu <= v_points[0]:
        return q_points[0]
    if vpu >= v_points[-1]:
        return q_points[-1]
    for i in range(len(v_points) - 1):
        v0, v1 = v_points[i], v_points[i + 1]
        if v0 <= vpu <= v1:
            if v1 == v0:
                return q_points[i]
            t = (vpu - v0) / (v1 - v0)
            return q_points[i] + t * (q_points[i + 1] - q_points[i])
    return q_points[-1]


def _power_balance(dss):
    """Relative residual of the real-power balance on the converged solution."""
    p_src = -dss.Circuit.TotalPower()[0]                 # kW delivered into the circuit
    p_loss = dss.Circuit.Losses()[0] / 1000.0            # Losses() is in watts

    # Summed over every conductor of the first terminal, not every *phase*. A delta-connected
    # single-phase load reports NumPhases()=1 but NumConductors()=2, and its terminal power is
    # the sum over both; counting only the first leaves a residual that looks like a
    # conservation failure. On IEEE~123, whose model is full of line-to-line single-phase loads,
    # that error alone accounted for a 3.7% apparent imbalance at zero PV.
    def _terminal_p(elem):
        dss.Circuit.SetActiveElement(elem)
        pw = dss.CktElement.Powers()
        return sum(pw[2 * k] for k in range(dss.CktElement.NumConductors()))

    p_load = 0.0
    i = dss.Loads.First()
    while i > 0:
        p_load += _terminal_p(f"Load.{dss.Loads.Name()}")          # + = consumed
        i = dss.Loads.Next()

    p_gen = 0.0
    i = dss.PVsystems.First()
    while i > 0:
        p_gen += -_terminal_p(f"PVSystem.{dss.PVsystems.Name()}")  # - = generated, so negate
        i = dss.PVsystems.Next()

    resid = p_src + p_gen - p_load - p_loss
    scale = max(abs(p_load) + abs(p_loss), 1e-9)
    return {"p_source_kw": round(p_src, 4), "p_gen_kw": round(p_gen, 4),
            "p_load_kw": round(p_load, 4), "p_loss_kw": round(p_loss, 4),
            "residual_kw": round(resid, 6), "residual_rel": round(abs(resid) / scale, 10)}


def _node_voltages(dss):
    return dict(zip(dss.Circuit.AllNodeNames(), dss.Circuit.AllBusMagPu()))


def _freeze_regulators(dss, taps):
    """Pin every regulator to a recorded tap position and stop it moving.

    The fourth check. If the two control implementations disagree mainly because they drove the
    discrete devices to different positions, then holding those positions identical arm-by-arm
    should collapse the disagreement -- and if it does, the residual model-dependence is
    attributable to tap path, not to the control law or the solver.
    """
    dss.Command("Set ControlMode=OFF")
    i = dss.RegControls.First()
    while i:
        nm = dss.RegControls.Name()
        if nm in taps:
            dss.RegControls.TapNumber(taps[nm])
        i = dss.RegControls.Next()


def _fixed_point(dss, ratings, v_pts, q_pts):
    """Drive the re-implemented characteristic to a fixed point with InvControl disabled.

    Returns the iteration count, the final per-iteration change, and whether it converged. The
    relaxation is halved whenever the change fails to improve over a window, because a volt-var
    loop on a stiff feeder oscillates rather than diverging and the remedy is damping.
    """
    q_now = {nm: 0.0 for nm, _, _ in ratings}
    relax, best, stall, delta = RELAX, float("inf"), 0, None
    for it in range(MAX_ITER):
        C_solve()
        delta = 0.0
        for nm, kv, nph in ratings:
            vpu = _pu_voltage(dss, nm, kv, nph)
            q_target = _cat_b_kvar(vpu, v_pts, q_pts)
            q_new = q_now[nm] + relax * (q_target - q_now[nm])
            delta = max(delta, abs(q_new - q_now[nm]))
            q_now[nm] = q_new
        for nm, _, _ in ratings:
            dss.Command(f"Edit PVSystem.{nm} kvar={q_now[nm]:.6f}")
        if delta < Q_TOL_KVAR:
            C_solve()
            return it + 1, delta, True
        if delta < best * 0.99:
            best, stall = delta, 0
        else:
            stall += 1
            if stall >= STALL_WINDOW:
                relax, stall = relax / 2.0, 0
    C_solve()
    return MAX_ITER, delta, False


def C_solve():
    from power import confirmatory as C
    return C.solve()


def one_arm(task):
    """One (feeder, rung, seed): the paired attacker-minus-legitimate contrast, computed twice.

    The manuscript never reports an absolute band integral; every claim is a paired difference
    between an attacker arm and the legitimate arm at the same seed. So the quantity that has to
    survive an independent control implementation is that *difference*, and a common-mode offset
    in the controller's own convergence tolerance is expected to cancel out of it. Both arms are
    therefore computed under InvControl and again under the re-implemented characteristic, and
    the two differences are compared.

    The attacker point is the worst admissible member of the widest set on the ``curve``
    primitive --- full reactive *injection* at the high-voltage breakpoint, which inverts the
    characteristic --- so no search is needed and the arm is deterministic.
    """
    import opendssdirect as dss
    from power import confirmatory as C

    cfg = STATES[task["feeder"]]
    spec = ensure_feeder(task["feeder"])
    n, lm, pen = cfg["fleet"], cfg["load_mult"], task["penetration"]
    with C.Session(spec, seed=task["seed"], n_pv=0, load_mult=lm) as probe:
        base_load = probe.base_load_kw
    der = C.DER(p_kw=(pen * base_load * lm) / n)
    v_pts = C.VV_V
    q_leg = der.vv_q_kvar                                   # conformant Category B
    q_atk = (q_leg[0], q_leg[1], q_leg[2], +der.q_cat_b)    # inverted high-voltage end

    # ---- path A: the harness as the paper runs it -------------------------------------------
    C.reset_convergence_counters()
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s:
        s.dispatch_legitimate()
        C.solve()
        j_leg_inv = s.state()["j_band"]
        taps_leg = C.tap_positions()
        balance = _power_balance(dss)
        ratings = []
        for nm in s.names:
            dss.Circuit.SetActiveElement(f"PVSystem.{nm}")
            ratings.append((nm, float(dss.Properties.Value("kv")), dss.CktElement.NumPhases()))
        n_base_ambiguous = sum(1 for nm, kv, nph in ratings
                               if not _rated_base_agrees(dss, nm, kv, nph))

        s.apply(+der.q_cat_b, "curve")
        C.solve()
        j_atk_inv = s.state()["j_band"]
        taps_atk = C.tap_positions()
        n_taps_moved = C.count_tap_operations(taps_leg, taps_atk)

        # ---- check 3: the other solution algorithm at the same operating point ---------------
        dss.Command("Set Algorithm=Newton")
        newton_ok = C.solve()
        j_atk_newton = s.state()["j_band"]
        v_atk_newton = _node_voltages(dss)
        dss.Command("Set Algorithm=Normal")
        C.solve()
        v_atk_inv = _node_voltages(dss)
    nonconv_inv = dict(C.NONCONVERGED)

    # ---- path B: the control re-implemented, both arms ---------------------------------------
    C.reset_convergence_counters()
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s2:
        dss.Command("Edit InvControl.der1547 enabled=no")
        for nm in s2.names:
            dss.Command(f"Edit PVSystem.{nm} irradiance=1.0 kvar=0")
        it_l, dq_l, ok_l = _fixed_point(dss, ratings, v_pts, q_leg)
        j_leg_ind = s2.state()["j_band"]
        for nm in s2.names:
            dss.Command(f"Edit PVSystem.{nm} kvar=0")
        it_a, dq_a, ok_a = _fixed_point(dss, ratings, v_pts, q_atk)
        j_atk_ind = s2.state()["j_band"]
        taps_ind = C.tap_positions()
    nonconv_ind = dict(C.NONCONVERGED)
    taps_differing = sum(1 for k, v in taps_atk.items() if taps_ind.get(k) != v)

    # ---- check 4: same comparison with the discrete state held identical arm-by-arm -----------
    with C.Session(spec, seed=task["seed"], n_pv=n, load_mult=lm, der=der) as s3:
        dss.Command("Edit InvControl.der1547 enabled=no")
        for nm in s3.names:
            dss.Command(f"Edit PVSystem.{nm} irradiance=1.0 kvar=0")
        _freeze_regulators(dss, taps_leg)
        _fixed_point(dss, ratings, v_pts, q_leg)
        j_leg_frozen = s3.state()["j_band"]
        for nm in s3.names:
            dss.Command(f"Edit PVSystem.{nm} kvar=0")
        _freeze_regulators(dss, taps_atk)
        _fixed_point(dss, ratings, v_pts, q_atk)
        j_atk_frozen = s3.state()["j_band"]

    d_inv = j_atk_inv - j_leg_inv
    d_ind = j_atk_ind - j_leg_ind
    d_frozen = j_atk_frozen - j_leg_frozen
    d_newton = j_atk_newton - j_leg_inv

    def rel(a, b):
        return abs(a - b) / abs(b) if b else (0.0 if a == b else None)

    common = [k for k in v_atk_inv if k in v_atk_newton]
    dv_newton = max((abs(v_atk_inv[k] - v_atk_newton[k]) for k in common), default=None)

    return {
        "feeder": task["feeder"], "penetration": pen, "seed": task["seed"],
        "balance": balance, "rated_base_ambiguous_units": n_base_ambiguous, "n_units": len(ratings),
        # the paired contrast, computed twice
        "delta_j_invcontrol": round(d_inv, 6),
        "delta_j_independent": round(d_ind, 6),
        "delta_j_rel_err": round(rel(d_ind, d_inv), 6),
        "delta_j_abs_err": round(abs(d_ind - d_inv), 6),
        # the absolutes, kept so the common-mode offset is visible rather than hidden
        "j_leg_invcontrol": round(j_leg_inv, 6), "j_atk_invcontrol": round(j_atk_inv, 6),
        "j_leg_independent": round(j_leg_ind, 6), "j_atk_independent": round(j_atk_ind, 6),
        "j_leg_rel_offset": round(rel(j_leg_ind, j_leg_inv), 6),
        "delta_j_frozen_taps": round(d_frozen, 6),
        "delta_j_frozen_rel_err": round(rel(d_frozen, d_inv), 6),
        "regulator_taps_differing": taps_differing,
        "regulator_taps_moved_by_attack": n_taps_moved,
        "independent_converged": bool(ok_l and ok_a),
        "independent_iters": [it_l, it_a], "independent_final_dq": [round(dq_l, 8),
                                                                    round(dq_a, 8)],
        # solution algorithm
        "newton_converged": bool(newton_ok),
        "delta_j_newton": round(d_newton, 6),
        "newton_rel_err": round(rel(d_newton, d_inv), 6),
        "newton_max_dv_pu": round(dv_newton, 8) if dv_newton is not None else None,
        "nonconverged_invcontrol": nonconv_inv, "nonconverged_independent": nonconv_ind,
    }


def main(n_seeds: int = 10):
    tasks = [{"feeder": f, "penetration": p, "seed": s}
             for f, c in STATES.items() for p in c["penetrations"] for s in SEEDS[:n_seeds]]
    rows = run_tasks(one_arm, tasks, label="solver-validation", every=8)

    summary = []
    for f, c in STATES.items():
        for pen in c["penetrations"]:
            g = [r for r in rows if "error" not in r
                 and r["feeder"] == f and r["penetration"] == pen]
            if not g:
                continue
            conv = [r for r in g if r["independent_converged"]]
            summary.append({
                "feeder": f, "penetration": pen, "n": len(g),
                "max_power_balance_residual_rel": max(r["balance"]["residual_rel"] for r in g),
                "rated_base_ambiguous_units": max(r["rated_base_ambiguous_units"] for r in g),
                "n_independent_converged": len(conv),
                "median_delta_j_invcontrol": round(
                    statistics.median([r["delta_j_invcontrol"] for r in g]), 4),
                "median_delta_j_independent": round(
                    statistics.median([r["delta_j_independent"] for r in conv]), 4) if conv else None,
                "median_delta_j_rel_err": round(
                    statistics.median([r["delta_j_rel_err"] for r in conv]), 4) if conv else None,
                "max_delta_j_rel_err": round(
                    max(r["delta_j_rel_err"] for r in conv), 4) if conv else None,
                "median_delta_j_frozen_rel_err": round(
                    statistics.median([r["delta_j_frozen_rel_err"] for r in g]), 4),
                "median_regulator_taps_differing": statistics.median(
                    [r["regulator_taps_differing"] for r in g]),
                "median_taps_moved_by_attack": statistics.median(
                    [r["regulator_taps_moved_by_attack"] for r in g]),
                "median_j_leg_rel_offset": round(
                    statistics.median([r["j_leg_rel_offset"] for r in conv]), 4) if conv else None,
                "n_newton_converged": sum(1 for r in g if r["newton_converged"]),
                "median_newton_rel_err": round(
                    statistics.median([r["newton_rel_err"] for r in g]), 4),
                "max_newton_max_dv_pu": max(r["newton_max_dv_pu"] for r in g),
            })

    OUT.write_text(json.dumps({
        "status": "post-hoc validation; tests no hypothesis",
        "question": "does the reported paired contrast depend on the vendor controller "
                    "or the solution algorithm?",
        "checks": ["power balance on every converged solution",
                   "IEEE 1547-2018 Cat B characteristic re-implemented and driven to a fixed "
                   "point with InvControl disabled, both arms, contrast compared",
                   "OpenDSS Normal vs Newton solution algorithm",
                   "the same contrast with regulator taps pinned identically arm-by-arm, to "
                   "attribute any residual disagreement to discrete device path-dependence"],
        "attacker_point": "curve primitive, full reactive injection at the high-voltage "
                          "breakpoint (worst admissible member of the widest set)",
        "states": STATES, "relaxation": RELAX, "q_tol_kvar": Q_TOL_KVAR,
        "max_iter": MAX_ITER, "seeds": SEEDS[:n_seeds], "rows": rows, "summary": summary},
        indent=2))
    print(f"\nwrote {OUT}\n")
    hdr = ("%-9s %5s %4s %10s %9s %9s %9s %9s %7s %7s" %
           ("feeder", "pen", "n", "balance", "dJ inv", "dJ indep", "rel err",
            "frozen err", "taps", "newton"))
    print(hdr); print("-" * len(hdr))
    for s_ in summary:
        print("%-9s %5.1f %4d %10.2e %9.2f %9s %9s %9s %7.0f %3d/%-3d" % (
            s_["feeder"], s_["penetration"], s_["n"], s_["max_power_balance_residual_rel"],
            s_["median_delta_j_invcontrol"],
            "n/a" if s_["median_delta_j_independent"] is None
            else "%.2f" % s_["median_delta_j_independent"],
            "n/a" if s_["median_delta_j_rel_err"] is None
            else "%.0f%%" % (100 * s_["median_delta_j_rel_err"]),
            "%.0f%%" % (100 * s_["median_delta_j_frozen_rel_err"]),
            s_["median_regulator_taps_differing"],
            s_["n_newton_converged"], s_["n"]))


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10)
