"""Small radial distribution feeder in OpenDSS (real power flow).

This is a SMALL, self-authored illustrative feeder used to produce real physical-consequence
numbers in the authoring environment. It is NOT the IEEE 8500-node or PNNL 9500-node system;
those remain for the full evaluation. The point here is a genuine OpenDSS power-flow solve that
translates an authorized malicious DER dispatch into a measured voltage-violation area, and
that shows the outcome depends on feeder operating state (Proposition 3, physical).
"""
from __future__ import annotations

import opendssdirect as dss

CMD = dss.Command


def build(load_scale: float = 1.0) -> None:
    CMD("Clear")
    CMD("New Circuit.small basekv=12.47 pu=1.00 phases=3 bus1=sourcebus")
    CMD("New Line.l1 bus1=sourcebus bus2=b1 length=2 units=km r1=0.30 x1=0.60 c1=0")
    CMD("New Line.l2 bus1=b1 bus2=b2 length=2 units=km r1=0.30 x1=0.60 c1=0")
    CMD("New Line.l3 bus1=b2 bus2=b3 length=2 units=km r1=0.30 x1=0.60 c1=0")
    CMD(f"New Load.ld1 bus1=b1 phases=3 kv=12.47 kw={500 * load_scale:.1f} kvar={200 * load_scale:.1f} model=1")
    CMD(f"New Load.ld2 bus1=b2 phases=3 kv=12.47 kw={400 * load_scale:.1f} kvar={150 * load_scale:.1f} model=1")
    CMD(f"New Load.ld3 bus1=b3 phases=3 kv=12.47 kw={300 * load_scale:.1f} kvar={120 * load_scale:.1f} model=1")
    # adversary-controllable DER at the far bus (worst location for voltage rise).
    CMD("New Generator.der1 bus1=b3 phases=3 kv=12.47 kw=0 kvar=0 model=1")
    CMD("Set voltagebases=[12.47]")
    CMD("Calcv")
    CMD("Set mode=snapshot")


def dispatch_and_solve(der_kw: float, der_kvar: float) -> "list[float]":
    CMD(f"Edit Generator.der1 kw={der_kw:.1f} kvar={der_kvar:.1f}")
    CMD("Solve")
    return list(dss.Circuit.AllBusMagPu())


def violation_area(vpu, vmin: float = 0.95, vmax: float = 1.05) -> float:
    """J_V (snapshot): sum over nodes of the per-unit excursion beyond the ANSI band."""
    return sum(max(0.0, v - vmax) + max(0.0, vmin - v) for v in vpu)


def max_deviation(vpu) -> float:
    return max(abs(v - 1.0) for v in vpu)


def n_violating(vpu, vmin: float = 0.95, vmax: float = 1.05) -> int:
    return sum(1 for v in vpu if v > vmax or v < vmin)


def converged() -> bool:
    return bool(dss.Solution.Converged())
