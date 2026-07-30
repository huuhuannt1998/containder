"""Helpers for the IEEE 123-bus test feeder (OpenDSS). Second feeder for generality (reviewer §13.5)."""
from __future__ import annotations

import os
from pathlib import Path

import opendssdirect as dss

FEEDER = Path(__file__).resolve().parent / "feeders" / "ieee123"


def chdir_feeder():
    os.chdir(FEEDER)


def compile_base():
    dss.Command("Compile IEEE123Master.dss")
    dss.Command("Set controlmode=static")
    dss.Command("Set maxcontroliter=100")
    dss.Command("Set maxiterations=100")


def load_buses():
    buses = []
    i = dss.Loads.First()
    while i:
        name = dss.Loads.Name()
        dss.Circuit.SetActiveElement("Load." + name)
        buses.append((dss.CktElement.BusNames()[0], dss.CktElement.NumPhases(), dss.Loads.kV()))
        i = dss.Loads.Next()
    return buses


def place_pv(buses, n, seed):
    import random
    rng = random.Random(seed)
    chosen = rng.sample(buses, min(n, len(buses)))
    names = []
    for j, (b, ph, kv) in enumerate(chosen):
        nm = f"pvatk_{j}"
        dss.Command(f"New Generator.{nm} bus1={b} phases={ph} kv={kv} kw=0 kvar=0 model=1")
        names.append(nm)
    return names


def dispatch(names, kw, kvar):
    for nm in names:
        dss.Command(f"Edit Generator.{nm} kw={kw} kvar={kvar}")


def set_load_mult(lm):
    dss.Command(f"Set LoadMult={lm}")


def solve():
    dss.Solution.Solve()
    return bool(dss.Solution.Converged())


def overvoltage_area(vmax=1.05):
    return sum(max(0.0, x - vmax) for x in dss.Circuit.AllBusMagPu() if x > 0.01)
