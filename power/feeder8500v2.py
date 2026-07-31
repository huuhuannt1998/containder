"""Corrected IEEE 8500-node feeder harness (revision 2) for the CONTAINDER major revision.

This module supersedes :mod:`power.feeder8500` for every experiment reported in the revised
manuscript. It fixes four defects identified in review:

* **Solver-state leak (M2).** :func:`compile_base` must be called before *every* policy arm, not
  once per seed. OpenDSS warm-starts each ``Solve`` from the previous converged voltage vector and
  from the current regulator tap / capacitor switch positions, so an arm evaluated after another
  arm's attack excursion inherits that state. Measured: the identical clean dispatch yields
  overvoltage area 0.014560 from a cold compile and 0.026424 immediately after a full-scope attack
  excursion; recompiling restores 0.014560 exactly. :func:`Session` makes the recompile explicit.

* **Missing legitimate counterfactual (M4).** The original base case dispatched every PV unit at
  ``kw=0 kvar=0``, i.e. the counterfactual feeder had no DER at all, so the reported
  :math:`\\Delta J_V` conflated "connect unconstrained generation" with "a credential was stolen".
  :func:`place_pv` can now instantiate ``PVSystem`` objects at a legitimate scheduled output under
  an IEEE 1547-2018 Category B volt-var curve (:func:`add_invcontrol`), which is the correct
  counterfactual: the adversary displaces *legitimate* DER operation.

* **Unmodelled protection (M5).** The feeder had no protection model, so the trip outcome named in
  the metric list and in Proposition 3's construction could never fire. :func:`protection_state`
  implements IEEE 1547-2018 Table 16 Category II overvoltage trip thresholds and a substation
  reverse-power flag.

* **Unreported control action (M5).** Regulator tap positions and capacitor switch states are now
  observable via :func:`tap_positions` / :func:`cap_states` and :func:`count_tap_operations`, so
  the declared "regulator tap operations" metric can actually be reported.

An empirical note on control mode, recorded because review asserted the opposite. Under OpenDSS
``Set controlmode=static`` the regulator, LTC and capacitor controls **do** operate: a base solve
at ``LoadMult=0.30`` executes 10 tap changes and 6 capacitor switching operations over 15 control
iterations, and a full-scope attack drives 12 further tap changes. Controls are disabled only by
``Set controlmode=off``, under which the same attack produces overvoltage area 998.0 (vmax 1.3145)
rather than 126.4 (vmax 1.1281). The feeder's native mitigation was therefore active throughout;
``static`` is the correct snapshot control mode and is retained, now with taps reported.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import opendssdirect as dss

FEEDER = Path(__file__).resolve().parent / "feeders" / "ieee8500"

# --- DER nameplate and IEEE 1547-2018 Category B reactive capability -------------------------
P_PV_KW = 12.0
#: IEEE 1547-2018 Cl. 5.2 Category B: reactive capability >= 44% of nameplate active power rating.
Q_1547_FRAC = 0.44
Q_1547_KVAR = Q_1547_FRAC * P_PV_KW          # 5.28 kvar
#: Inverter apparent-power rating sized to deliver the full 1547 Category B reactive range at Pmpp.
KVA_PV = round((P_PV_KW ** 2 + Q_1547_KVAR ** 2) ** 0.5, 3)   # 13.111 kVA

#: IEEE 1547-2018 Table 8, Category B default volt-var characteristic
#: (voltage in p.u. of nominal; Q in p.u. of nameplate apparent power, + = injection).
VV_CURVE_V = (0.92, 0.98, 1.02, 1.08)
VV_CURVE_Q = (Q_1547_FRAC, 0.0, 0.0, -Q_1547_FRAC)

#: IEEE 1547-2018 Table 16, Category II overvoltage trip settings.
OV2_PU, OV2_S = 1.20, 0.16
OV1_PU, OV1_S = 1.10, 2.0

CONTROL_MODE = "static"


def chdir_feeder() -> None:
    os.chdir(FEEDER)


# ------------------------------------------------------------------ circuit construction ----

def compile_base(control_mode: str = CONTROL_MODE) -> None:
    """Compile the feeder from source. MUST be called before every independent policy arm.

    Recompiling is the only reliable way to clear the warm-start voltage vector *and* the
    regulator tap / capacitor switch positions, which otherwise leak across arms (M2).
    """
    dss.Command("Clear")
    dss.Command("Compile Master.dss")
    dss.Command(f"Set controlmode={control_mode}")
    # 600 volt-var inverters interacting with 12 regulators and 10 cap banks need a generous
    # control-iteration budget; at 100 the InvControl loop aborts with "Max Control Iterations
    # Exceeded". 500 converges every arm reported here (max observed 254).
    dss.Command("Set maxcontroliter=500")
    dss.Command("Set maxiterations=100")


def load_buses() -> "list[tuple[str, int, float]]":
    buses = []
    i = dss.Loads.First()
    while i:
        name = dss.Loads.Name()
        dss.Circuit.SetActiveElement("Load." + name)
        buses.append((dss.CktElement.BusNames()[0], dss.CktElement.NumPhases(), dss.Loads.kV()))
        i = dss.Loads.Next()
    return buses


def add_invcontrol(names: "list[str]", mode: str = "voltvar") -> None:
    """Attach an IEEE 1547-2018 Category B volt-var controller to the given PVSystem set."""
    if not names:
        return
    xs = ",".join(str(v) for v in VV_CURVE_V)
    ys = ",".join(str(q) for q in VV_CURVE_Q)
    dss.Command(f"New XYCurve.vv1547b npts=4 Yarray=({ys}) Xarray=({xs})")
    dss.Command(
        "New InvControl.der1547 mode=VOLTVAR voltage_curvex_ref=rated "
        "vvc_curve1=vv1547b deltaQ_factor=0.1 varchangetolerance=0.05 "
        "voltagechangetolerance=0.001 RefReactivePower=VARMAX"
    )


def distort_voltvar_curve(q_at_high_v: float) -> None:
    """Adversarial *curve distortion*: rewrite the live volt-var characteristic.

    ``q_at_high_v`` is the reactive output (p.u. of nameplate apparent power, + = injection)
    commanded at the top of the voltage range. The 1547 Category B curve absorbs
    ``-0.44`` there; an adversary who inverts the sign injects vars into an already-high
    voltage, which is the genuine volt-var curve-distortion attack. This is a real change to
    the controller characteristic, not a static setpoint delta.
    """
    ys = f"{q_at_high_v},{q_at_high_v},{q_at_high_v},{q_at_high_v}"
    xs = ",".join(str(v) for v in VV_CURVE_V)
    dss.Command(f"Edit XYCurve.vv1547b npts=4 Yarray=({ys}) Xarray=({xs})")


def place_pv(buses, n: int, seed: int, *, kind: str = "pvsystem",
             pmpp_kw: float = P_PV_KW, irradiance: float = 1.0) -> "list[str]":
    """Instantiate the rooftop-PV fleet at seeded load buses.

    ``kind='pvsystem'`` builds real ``PVSystem`` objects with an inverter rating, a Pmpp and an
    irradiance, so a volt-var / volt-watt curve can be attached and genuinely distorted.
    ``kind='generator'`` reproduces the original ``Generator model=1`` fleet for back-comparison.
    """
    rng = random.Random(seed)
    chosen = rng.sample(buses, min(n, len(buses)))
    names = []
    for j, (busfull, ph, kv) in enumerate(chosen):
        nm = f"pvatk_{j}"
        if kind == "pvsystem":
            dss.Command(
                f"New PVSystem.{nm} bus1={busfull} phases={ph} kv={kv} "
                f"kVA={KVA_PV} Pmpp={pmpp_kw} irradiance={irradiance} "
                f"%cutin=0 %cutout=0 kvarmax={Q_1547_KVAR} kvarmaxabs={Q_1547_KVAR} "
                # varfollowinverter=no keeps the inverter energised for reactive support when
                # active power is zero. Without it the unit cuts out at irradiance=0 and the
                # entire reactive-scope axis is silently inert (measured: flat at every Q).
                f"wattpriority=no varfollowinverter=no"
            )
        else:
            dss.Command(
                f"New Generator.{nm} bus1={busfull} phases={ph} kv={kv} kw=0 kvar=0 model=1")
        names.append(nm)
    return names


# ------------------------------------------------------------------------- dispatch ---------

def dispatch(names, kw: float, kvar: float, *, kind: str = "pvsystem",
             pmpp_kw: float = P_PV_KW) -> None:
    """Force an explicit (P,Q) setpoint on every DER, overriding autonomous control.

    This is the *adversarial setpoint-override* path: an attacker holding a credential with
    ``DERControl`` scope writes explicit setpoints, which take precedence over the autonomous
    volt-var function. A ``PVSystem``'s active power is ``Pmpp x irradiance``, so P is commanded
    through irradiance; Q is commanded directly and the InvControl loop is suspended for the
    duration of the override. Legitimate operation is restored by :func:`dispatch_legitimate`.
    """
    if kind == "pvsystem":
        dss.Command("Edit InvControl.der1547 enabled=no")
        irr = (kw / pmpp_kw) if pmpp_kw else 0.0
        for nm in names:
            dss.Command(f"Edit PVSystem.{nm} irradiance={irr} kvar={kvar}")
    else:
        for nm in names:
            dss.Command(f"Edit Generator.{nm} kw={kw} kvar={kvar}")


def dispatch_legitimate(names, irradiance: float = 1.0, *, kind: str = "pvsystem") -> None:
    """Restore legitimate scheduled operation: PV at available power, Q under volt-var control."""
    if kind != "pvsystem":
        for nm in names:
            dss.Command(f"Edit Generator.{nm} kw=0 kvar=0")
        return
    for nm in names:
        dss.Command(f"Edit PVSystem.{nm} irradiance={irradiance} kvar=0")
    dss.Command("Edit InvControl.der1547 enabled=yes")


def set_load_mult(lm: float) -> None:
    dss.Command(f"Set LoadMult={lm}")


#: Count of solves that exhausted the control-iteration budget, recorded rather than dropped.
NONCONVERGED = {"n": 0, "n_retried": 0}


def solve(max_retries: int = 2) -> bool:
    """Solve, handling control-iteration exhaustion as a recorded outcome rather than a crash.

    With 600 volt-var inverters the InvControl loop can fail to settle, most often at higher load
    multipliers where regulator and inverter control interact. OpenDSS raises on
    ``Max Control Iterations Exceeded``. The pre-registered protocol requires a retry cap of two,
    treating failure as an outcome and never dropping severe runs, so we retry with a progressively
    larger control budget and, if it still will not settle, keep the last iterate and flag it.

    Returns True if the solution converged, False if it was retained as a non-converged outcome.
    """
    budget = 500
    for attempt in range(max_retries + 1):
        try:
            dss.Solution.Solve()
            if budget != 500:
                # Restore the default budget so one hard step does not slow every later step
                # in the same arm; a raised budget otherwise persists for the whole session.
                dss.Command("Set maxcontroliter=500")
            return bool(dss.Solution.Converged())
        except Exception:
            if attempt == max_retries:
                NONCONVERGED["n"] += 1
                dss.Command("Set maxcontroliter=500")
                return False
            budget *= 3
            NONCONVERGED["n_retried"] += 1
            dss.Command(f"Set maxcontroliter={budget}")
    return False


# --------------------------------------------------------------------------- metrics --------

def bus_pu() -> "list[float]":
    return [x for x in dss.Circuit.AllBusMagPu() if x > 0.01]


def overvoltage_area(vmax: float = 1.05) -> float:
    """Induced-overvoltage metric: sum over nodes of max(0, V - vmax), in p.u.-node."""
    return sum(max(0.0, x - vmax) for x in bus_pu())


def voltage_stats(limit: float = 1.05) -> dict:
    v = bus_pu()
    return {"area": sum(max(0.0, x - limit) for x in v),
            "n_over": sum(1 for x in v if x > limit),
            "vmax": round(max(v), 4) if v else 0.0,
            "n_nodes": len(v)}


def tap_positions() -> dict:
    out = {}
    i = dss.RegControls.First()
    while i:
        out[dss.RegControls.Name()] = dss.RegControls.TapNumber()
        i = dss.RegControls.Next()
    return out


def cap_states() -> dict:
    out = {}
    i = dss.Capacitors.First()
    while i:
        out[dss.Capacitors.Name()] = tuple(dss.Capacitors.States())
        i = dss.Capacitors.Next()
    return out


def count_tap_operations(before: dict, after: dict) -> int:
    """Total tap movements (sum of |Delta tap| across all regulators)."""
    return sum(abs(after.get(k, 0) - v) for k, v in before.items())


def count_cap_operations(before: dict, after: dict) -> int:
    return sum(1 for k, v in before.items() if after.get(k) != v)


def protection_state() -> dict:
    """IEEE 1547-2018 Table 16 Category II overvoltage trip screen + substation reverse power.

    Returns the count of nodes above each overvoltage trip threshold and the corresponding
    clearing time, plus a reverse-power flag at the substation. A ``trip`` is declared when any
    node exceeds an overvoltage threshold, since a DER at that node would be required to cease to
    energize within the stated clearing time.
    """
    v = bus_pu()
    n_ov2 = sum(1 for x in v if x >= OV2_PU)
    n_ov1 = sum(1 for x in v if x >= OV1_PU)
    dss.Circuit.SetActiveElement("Vsource.source")
    p_sub = dss.CktElement.Powers()
    p_total = sum(p_sub[0::2])
    return {"n_ov2": n_ov2, "n_ov1": n_ov1,
            "trip": bool(n_ov2 or n_ov1),
            "trip_class": "OV2" if n_ov2 else ("OV1" if n_ov1 else None),
            "clearing_s": OV2_S if n_ov2 else (OV1_S if n_ov1 else None),
            "p_substation_kw": round(p_total, 2),
            "reverse_power": bool(p_total < 0.0)}


# ------------------------------------------------------------------------- session ----------

@dataclass
class Session:
    """One independent, fully isolated feeder arm. Guarantees the M2 recompile."""
    seed: int
    n_pv: int = 600
    load_mult: float = 0.30
    kind: str = "pvsystem"
    volt_var: bool = True
    control_mode: str = CONTROL_MODE
    names: list = field(default_factory=list)

    def __enter__(self) -> "Session":
        compile_base(self.control_mode)
        self.names = place_pv(load_buses(), self.n_pv, self.seed, kind=self.kind)
        if self.kind == "pvsystem" and self.volt_var:
            add_invcontrol(self.names)
        set_load_mult(self.load_mult)
        return self

    def __exit__(self, *exc) -> bool:
        return False
