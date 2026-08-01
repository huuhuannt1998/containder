"""Two-sided physical endpoints and service-quality metrics for the confirmatory evaluation.

The pilot harness (:mod:`power.feeder8500v2`) reports a *one-sided* overvoltage area. That
endpoint credits an attack for lifting sagging nodes and cannot price the undervoltage that
forced over-absorption causes, so it cannot support a claim that an absorption-floor
authorization "still delivers volt-var". This module supplies the endpoints the confirmatory
protocol declares:

* :func:`band_stats` -- the two-sided ANSI C84.1 Range A violation area

  .. math:: J_{band} = \\sum_n [\\max(0, V_n - V_{max}) + \\max(0, V_{min} - V_n)]

  reported alongside its one-sided components so the attack-specific secondary endpoint
  remains recoverable from the same run.

* :func:`service_error` -- how far the reactive output of the fleet departs from the reactive
  output the conformant IEEE 1547-2018 Category B characteristic would have produced *at the
  voltages actually observed*. This is the legitimate-service metric: an authorization that
  contains the attack but destroys volt-var support is not a usable authorization.

* :func:`fleet_power` -- aggregate real and reactive output, for curtailment accounting.

All functions read the live OpenDSS circuit and are feeder-agnostic; they are shared by the
IEEE 8500 and IEEE 123 harnesses so the two feeders are measured identically.
"""
from __future__ import annotations

import opendssdirect as dss

#: ANSI C84.1-2020 Range A service-voltage limits, per unit.
V_MAX_PU = 1.05
V_MIN_PU = 0.95


def bus_pu() -> "list[float]":
    """Per-unit magnitudes of every energized node (the 0.01 filter drops unenergized phases)."""
    return [x for x in dss.Circuit.AllBusMagPu() if x > 0.01]


def band_stats(v_max: float = V_MAX_PU, v_min: float = V_MIN_PU) -> dict:
    """Two-sided ANSI band statistics for the current solution.

    ``j_band`` is the declared primary endpoint. ``area_over`` is the one-sided overvoltage
    term retained as the attack-specific secondary endpoint; ``area_under`` is the term the
    one-sided endpoint omits, which is what prices over-absorption.
    """
    v = bus_pu()
    if not v:
        return {"j_band": 0.0, "area_over": 0.0, "area_under": 0.0, "n_over": 0,
                "n_under": 0, "n_out": 0, "vmax": 0.0, "vmin": 0.0, "n_nodes": 0}
    over = sum(max(0.0, x - v_max) for x in v)
    under = sum(max(0.0, v_min - x) for x in v)
    n_over = sum(1 for x in v if x > v_max)
    n_under = sum(1 for x in v if x < v_min)
    return {"j_band": over + under,
            "area_over": over,
            "area_under": under,
            "n_over": n_over,
            "n_under": n_under,
            "n_out": n_over + n_under,
            "vmax": round(max(v), 4),
            "vmin": round(min(v), 4),
            "n_nodes": len(v)}


def _pv_voltage_pu(name: str) -> float:
    """Terminal voltage of one PVSystem, per unit of its own base."""
    dss.Circuit.SetActiveElement("PVSystem." + name)
    vs = dss.CktElement.VoltagesMagAng()[0::2]
    dss.Circuit.SetActiveElement("PVSystem." + name)
    bus = dss.CktElement.BusNames()[0].split(".")[0]
    dss.Circuit.SetActiveBus(bus)
    kvbase = dss.Bus.kVBase() * 1000.0
    if kvbase <= 0:
        return 0.0
    phases = [x for x in vs if x > 1.0]
    if not phases:
        return 0.0
    return (sum(phases) / len(phases)) / kvbase


def conformant_q_pu(v_pu: float, curve_v, curve_q) -> float:
    """Reactive output the conformant volt-var characteristic prescribes at voltage ``v_pu``.

    Piecewise-linear interpolation on the same (V, Q) breakpoints the legitimate InvControl
    uses, in per unit of nameplate apparent power, positive = injection.
    """
    if v_pu <= curve_v[0]:
        return curve_q[0]
    if v_pu >= curve_v[-1]:
        return curve_q[-1]
    for i in range(len(curve_v) - 1):
        v0, v1 = curve_v[i], curve_v[i + 1]
        if v0 <= v_pu <= v1:
            if v1 == v0:
                return curve_q[i]
            t = (v_pu - v0) / (v1 - v0)
            return curve_q[i] + t * (curve_q[i + 1] - curve_q[i])
    return curve_q[-1]


def service_error(names, curve_v, curve_q, kva: float) -> dict:
    """Departure of realised reactive output from the conformant characteristic.

    For each DER the realised Q (kvar, + = injection) is compared with the Q the conformant
    IEEE 1547 Category B curve prescribes at that unit's *observed* terminal voltage. Returned
    in kvar and normalised by the fleet's conformant reactive demand, so a value of 1.0 means
    the authorization delivered none of the support the curve asked for.

    ``support_deficit`` counts only the signed shortfall in the direction the curve asked for
    (failing to absorb when absorption is prescribed), which is the quantity an operator cares
    about; ``rmse_kvar`` is the two-sided tracking error.
    """
    n = 0
    sq_err = 0.0
    abs_err = 0.0
    deficit = 0.0
    demand = 0.0
    q_actual_total = 0.0
    for nm in names:
        v_pu = _pv_voltage_pu(nm)
        if v_pu <= 0.0:
            continue
        dss.Circuit.SetActiveElement("PVSystem." + nm)
        # OpenDSS reports load convention at the element terminal: positive Q drawn from the
        # circuit. A PV absorbing vars therefore reports positive Q here, so negate to put
        # injection positive, matching the curve convention.
        q_kvar = -sum(dss.CktElement.Powers()[1::2])
        q_ref = conformant_q_pu(v_pu, curve_v, curve_q) * kva
        err = q_kvar - q_ref
        sq_err += err * err
        abs_err += abs(err)
        demand += abs(q_ref)
        q_actual_total += q_kvar
        # Shortfall in the prescribed direction only.
        if q_ref < 0.0:                      # absorption prescribed
            deficit += max(0.0, q_kvar - q_ref)
        elif q_ref > 0.0:                    # injection prescribed
            deficit += max(0.0, q_ref - q_kvar)
        n += 1
    if n == 0:
        return {"rmse_kvar": 0.0, "mae_kvar": 0.0, "support_deficit_kvar": 0.0,
                "conformant_demand_kvar": 0.0, "deficit_frac": 0.0,
                "q_fleet_kvar": 0.0, "n_der": 0}
    return {"rmse_kvar": round((sq_err / n) ** 0.5, 4),
            "mae_kvar": round(abs_err / n, 4),
            "support_deficit_kvar": round(deficit, 3),
            "conformant_demand_kvar": round(demand, 3),
            "deficit_frac": round(deficit / demand, 4) if demand > 0 else 0.0,
            "q_fleet_kvar": round(q_actual_total, 3),
            "n_der": n}


def fleet_power(names) -> dict:
    """Aggregate fleet real and reactive output (kW / kvar, + = injection to the circuit)."""
    p = q = 0.0
    for nm in names:
        dss.Circuit.SetActiveElement("PVSystem." + nm)
        pw = dss.CktElement.Powers()
        p -= sum(pw[0::2])
        q -= sum(pw[1::2])
    return {"p_fleet_kw": round(p, 3), "q_fleet_kvar": round(q, 3)}


def substation_power() -> dict:
    dss.Circuit.SetActiveElement("Vsource.source")
    pw = dss.CktElement.Powers()
    p = sum(pw[0::2])
    return {"p_substation_kw": round(p, 2), "reverse_power": bool(p < 0.0)}
