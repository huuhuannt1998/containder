"""Feeder-agnostic confirmatory harness: authorization *sets*, matched primitives, real attackers.

This module supersedes the arm-by-arm construction in :mod:`power.feeder8500v2` for every
confirmatory experiment. It exists because the pilot harness contains two defects that
invalidate the comparison the manuscript's central claim rests on. Both were found by
re-measuring the pilot arms and both are corrected here.

**Defect 1 -- the two "matched magnitude" primitives were not matched.**
``feeder8500v2.distort_voltvar_curve(y)`` writes ``y`` into an ``XYCurve`` consumed by an
``InvControl`` declared ``RefReactivePower=VARMAX``, so ``y`` is per unit of *kvarmax*
(5.28 kvar). ``feeder8500v2.dispatch(names, P, q_high * KVA_PV)`` commands kvar in per unit of
*apparent power* (13.11 kVA). At the nominally identical point ``q_high = -0.44`` the curve arm
delivers -2.15 kvar per DER and the setpoint arm -5.28 kvar per DER, a factor of 2.46. Any
row-wise comparison of those two columns compares two different physical absorptions, which is
exactly the mismatched-feasible-set confound that makes a primitive look causal when only the
bound differs.

**Defect 2 -- the legitimate counterfactual under-delivers volt-var.**
The conformant IEEE 1547-2018 Category B characteristic absorbs 44% of the nameplate rating at
V4 = 1.08 p.u., i.e. 5.28 kvar for a 12 kW / 13.11 kVA unit. Against a ``VARMAX`` reference of
5.28 kvar that is ``y = -1.0``, but the pilot harness writes ``y = -0.44`` and absorbs 2.15
kvar. The legitimate baseline against which every induced quantity is differenced was therefore
a *degraded* volt-var service, which inflates the base overvoltage area (46.1 vs 57.1 p.u.-node
at light load, seed 1001).

Both are fixed by expressing every reactive quantity in **physical kvar per DER** and by
converting to whichever per-unit reference the OpenDSS object actually consumes at the point of
use. :meth:`Session.apply` is the single conversion site.

**Penetration is controlled by unit rating, not fleet count.** IEEE 123 has 91 load buses and
IEEE 8500 has 1177, so a fleet-count sweep saturates on the smaller feeder (every fleet size
above 91 yields an identical circuit). :class:`DER` carries the per-unit rating and the
experiments sweep it, so both feeders reach comparable penetrations.

The organising idea is that an authorization is a **set**, not a setpoint. An adversary holding
a credential scoped to a set plays the worst admissible point in it, so the experiments search
the authorized set rather than evaluating one arbitrary member. That is what lets *shape* (does
the set contain zero absorption?) be separated from *width*.
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from pathlib import Path

import opendssdirect as dss

from . import metrics as m

FEEDERS_DIR = Path(__file__).resolve().parent / "feeders"

#: IEEE 1547-2018 Cl. 5.2 Category B reactive capability: 44% of the nameplate active rating.
Q_1547_FRAC = 0.44

#: IEEE 1547-2018 Table 8 Category B default volt-var breakpoint voltages (p.u.).
VV_V = (0.92, 0.98, 1.02, 1.08)

#: IEEE 1547-2018 Table 16 Category II overvoltage thresholds. Crossing these is a *screen*:
#: the model has no persistence timer, no disconnection and no post-disconnection state update,
#: so a crossing means "a DER at this node would be required to cease to energize", not that a
#: trip was simulated. The manuscript uses the word "screen" for this outcome throughout.
OV2_PU, OV2_S = 1.20, 0.16
OV1_PU, OV1_S = 1.10, 2.0

CONTROL_MODE = "static"


@dataclass(frozen=True)
class DER:
    """Per-unit DER rating. Penetration is swept through ``p_kw``."""
    p_kw: float = 12.0

    @property
    def q_cat_b(self) -> float:
        """Category B reactive capability in kvar, injection and absorption alike."""
        return Q_1547_FRAC * self.p_kw

    @property
    def kva(self) -> float:
        """Inverter rating sized to deliver full Category B reactive range at Pmpp."""
        return round((self.p_kw ** 2 + self.q_cat_b ** 2) ** 0.5, 4)

    @property
    def vv_q_kvar(self) -> tuple:
        """Conformant Category B characteristic in physical kvar (+ = injection)."""
        return (+self.q_cat_b, 0.0, 0.0, -self.q_cat_b)


DER_DEFAULT = DER()


@dataclass(frozen=True)
class FeederSpec:
    key: str
    directory: str
    master: str
    #: Fleet size at which the feeder is populated; capped by its load-bus count.
    n_pv_nominal: int
    label: str


FEEDER_8500 = FeederSpec("ieee8500", "ieee8500", "Master.dss", 600, "IEEE 8500-node")
FEEDER_123 = FeederSpec("ieee123", "ieee123", "IEEE123Master.dss", 91, "IEEE 123-bus")
FEEDERS = {f.key: f for f in (FEEDER_8500, FEEDER_123)}


def chdir_feeder(spec: FeederSpec) -> None:
    os.chdir(FEEDERS_DIR / spec.directory)


def compile_base(spec: FeederSpec, control_mode: str = CONTROL_MODE) -> None:
    """Compile from source. Called before *every* arm so no solver state leaks between arms."""
    dss.Command("Clear")
    dss.Command(f"Compile {spec.master}")
    dss.Command(f"Set controlmode={control_mode}")
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


def total_load_kw() -> float:
    tot = 0.0
    i = dss.Loads.First()
    while i:
        tot += dss.Loads.kW()
        i = dss.Loads.Next()
    return tot


def set_load_mult(lm: float) -> None:
    dss.Command(f"Set LoadMult={lm}")


# --------------------------------------------------------------------------- solving ---------

NONCONVERGED = {"n": 0, "n_retried": 0}


def reset_convergence_counters() -> None:
    NONCONVERGED["n"] = 0
    NONCONVERGED["n_retried"] = 0


def solve(max_retries: int = 2) -> bool:
    """Solve; treat control-iteration exhaustion as a recorded outcome, never a dropped run."""
    budget = 500
    for attempt in range(max_retries + 1):
        try:
            dss.Solution.Solve()
            if budget != 500:
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


# --------------------------------------------------------------------------- metrics ---------

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
    return sum(abs(after.get(k, 0) - v) for k, v in before.items())


def count_cap_operations(before: dict, after: dict) -> int:
    return sum(1 for k, v in before.items() if after.get(k) != v)


def screen_state() -> dict:
    v = m.bus_pu()
    n_ov2 = sum(1 for x in v if x >= OV2_PU)
    n_ov1 = sum(1 for x in v if x >= OV1_PU)
    return {"n_ov2": n_ov2, "n_ov1": n_ov1,
            "screen": bool(n_ov2 or n_ov1),
            "screen_class": "OV2" if n_ov2 else ("OV1" if n_ov1 else None),
            "clearing_s": OV2_S if n_ov2 else (OV1_S if n_ov1 else None),
            **m.substation_power()}


# --------------------------------------------------------------------------- session ---------

@dataclass
class Session:
    """One independent, fully isolated feeder arm. Guarantees a fresh compile.

    All reactive quantities crossing this boundary are **physical kvar per DER**, positive =
    injection into the circuit.
    """
    spec: FeederSpec
    seed: int
    n_pv: int
    load_mult: float
    der: DER = DER_DEFAULT
    volt_var: bool = True
    control_mode: str = CONTROL_MODE
    names: list = field(default_factory=list)
    base_load_kw: float = 0.0

    # -- construction ---------------------------------------------------------------------
    def __enter__(self) -> "Session":
        compile_base(self.spec, self.control_mode)
        self.base_load_kw = total_load_kw()
        self.names = self._place_pv(load_buses())
        if self.volt_var:
            self._add_invcontrol()
        set_load_mult(self.load_mult)
        return self

    def __exit__(self, *exc) -> bool:
        return False

    def _place_pv(self, buses) -> list:
        rng = random.Random(self.seed)
        chosen = rng.sample(buses, min(self.n_pv, len(buses)))
        d = self.der
        names = []
        for j, (busfull, ph, kv) in enumerate(chosen):
            nm = f"pvatk_{j}"
            dss.Command(
                f"New PVSystem.{nm} bus1={busfull} phases={ph} kv={kv} "
                f"kVA={d.kva} Pmpp={d.p_kw} irradiance=1.0 "
                f"%cutin=0 %cutout=0 kvarmax={d.q_cat_b} kvarmaxabs={d.q_cat_b} "
                # varfollowinverter=no keeps the inverter energised for reactive support when
                # active power is zero; without it the unit cuts out at irradiance 0 and the
                # whole reactive axis is silently inert.
                f"wattpriority=no varfollowinverter=no"
            )
            names.append(nm)
        return names

    # -- volt-var characteristic ----------------------------------------------------------
    def _kvar_to_varmax_pu(self, q_kvar: float) -> float:
        """Convert physical kvar to the per-unit reference an ``InvControl`` VARMAX curve reads.

        This is the single reference-base conversion site; Defect 1 was its absence.
        """
        return q_kvar / self.der.q_cat_b

    def write_curve(self, q_kvar_points, v_points=VV_V) -> None:
        ys = ",".join(f"{self._kvar_to_varmax_pu(q):.6f}" for q in q_kvar_points)
        xs = ",".join(str(v) for v in v_points)
        dss.Command(f"Edit XYCurve.vv1547b npts={len(v_points)} Yarray=({ys}) Xarray=({xs})")

    def _add_invcontrol(self) -> None:
        if not self.names:
            return
        ys = ",".join(f"{self._kvar_to_varmax_pu(q):.6f}" for q in self.der.vv_q_kvar)
        xs = ",".join(str(v) for v in VV_V)
        dss.Command(f"New XYCurve.vv1547b npts=4 Yarray=({ys}) Xarray=({xs})")
        dss.Command(
            "New InvControl.der1547 mode=VOLTVAR voltage_curvex_ref=rated "
            "vvc_curve1=vv1547b deltaQ_factor=0.1 varchangetolerance=0.05 "
            "voltagechangetolerance=0.001 RefReactivePower=VARMAX"
        )

    # -- dispatch -------------------------------------------------------------------------
    def dispatch_legitimate(self, irradiance: float = 1.0) -> None:
        """Legitimate operation: PV at scheduled output, Q under the conformant Cat B curve."""
        self.write_curve(self.der.vv_q_kvar)
        for nm in self.names:
            dss.Command(f"Edit PVSystem.{nm} irradiance={irradiance} kvar=0")
        dss.Command("Edit InvControl.der1547 enabled=yes")

    def apply(self, q_kvar: float, primitive: str, p_kw: float = None) -> None:
        """Realise one admissible reactive operating point through the named control primitive.

        ``q_kvar`` is the *physical* reactive output commanded at high voltage, + = injection.
        Both primitives receive the identical physical quantity, which is what makes the two
        arms a matched-feasible-set comparison.

        ``setpoint`` -- ``opModFixedVar`` semantics: the autonomous function is superseded and a
                        fixed kvar is written at every unit irrespective of local voltage.
        ``curve``    -- ``opModVoltVar`` semantics: the controller stays enabled and only the
                        high-voltage end of the characteristic moves; the low-voltage end keeps
                        its conformant injection.
        """
        p = self.der.p_kw if p_kw is None else p_kw
        if primitive == "setpoint":
            dss.Command("Edit InvControl.der1547 enabled=no")
            irr = p / self.der.p_kw if self.der.p_kw else 0.0
            for nm in self.names:
                dss.Command(f"Edit PVSystem.{nm} irradiance={irr} kvar={q_kvar}")
        elif primitive == "curve":
            dss.Command("Edit InvControl.der1547 enabled=yes")
            q = self.der.vv_q_kvar
            self.write_curve((q[0], q[1], q[2], q_kvar))
            if p_kw is not None:
                self.set_active_power(p)
        else:
            raise ValueError(f"unknown primitive {primitive!r}")

    def set_active_power(self, p_kw: float) -> None:
        irr = p_kw / self.der.p_kw if self.der.p_kw else 0.0
        for nm in self.names:
            dss.Command(f"Edit PVSystem.{nm} irradiance={irr}")

    # -- measurement ----------------------------------------------------------------------
    def state(self) -> dict:
        """Every declared endpoint for the current solution, in one pass."""
        st = m.band_stats()
        st.update(screen_state())
        st.update(m.fleet_power(self.names))
        st.update(m.service_error(self.names, VV_V, self.der.vv_q_kvar, self.der.q_cat_b))
        return st

    @property
    def pv_kw(self) -> float:
        return len(self.names) * self.der.p_kw

    @property
    def penetration(self) -> float:
        denom = self.base_load_kw * self.load_mult
        return (self.pv_kw / denom) if denom > 0 else float("inf")
