"""Helpers for the real IEEE 8500-node feeder (OpenDSS). Shared by the sweep scripts."""
from __future__ import annotations

import os
from pathlib import Path

import opendssdirect as dss

FEEDER = Path(__file__).resolve().parent / "feeders" / "ieee8500"


def chdir_feeder() -> None:
    os.chdir(FEEDER)


def compile_base() -> None:
    dss.Command("Compile Master.dss")
    dss.Command("Set controlmode=static")
    dss.Command("Set maxcontroliter=100")
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


def place_pv(buses, n, seed) -> "list[str]":
    import random
    rng = random.Random(seed)
    chosen = rng.sample(buses, min(n, len(buses)))
    names = []
    for j, (busfull, ph, kv) in enumerate(chosen):
        nm = f"pvatk_{j}"
        dss.Command(f"New Generator.{nm} bus1={busfull} phases={ph} kv={kv} kw=0 kvar=0 model=1")
        names.append(nm)
    return names


def dispatch(names, kw, kvar) -> None:
    for nm in names:
        dss.Command(f"Edit Generator.{nm} kw={kw} kvar={kvar}")


def set_load_mult(lm: float) -> None:
    dss.Command(f"Set LoadMult={lm}")


def solve() -> bool:
    dss.Solution.Solve()
    return bool(dss.Solution.Converged())


def overvoltage_area(vmax: float = 1.05) -> float:
    """Induced-overvoltage metric: sum over nodes of max(0, V - vmax)."""
    return sum(max(0.0, x - vmax) for x in dss.Circuit.AllBusMagPu() if x > 0.01)
