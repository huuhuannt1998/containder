"""The M1 counterexample as a regression test (M2 T2.7, acceptance criterion 3).

Two compromises with IDENTICAL topological reach must be ranked differently by the engine:
same reachable DER set, but materially larger capacity and persistence for the legacy
credential. If this ever fails, the separation the paper rests on has been broken in code.
"""
import json
import pathlib

from pkimodel import analyze
from pkimodel.scenario import build_scenario

_SPEC_PATH = pathlib.Path(__file__).resolve().parent.parent / "scenarios" / "counterexample.json"
SPEC = json.loads(_SPEC_PATH.read_text())


def test_identical_reach_divergent_capacity_and_persistence():
    sc = build_scenario(SPEC)
    ba = analyze(sc.graph, "cred_alpha", sc.policy, seed=1)
    bb = analyze(sc.graph, "cred_beta", sc.policy, seed=1)

    # (1) identical topological reach -- the whole point of the counterexample.
    assert ba.reachable_ders == bb.reachable_ders
    assert ba.reach == bb.reach == 11

    # (2) divergent capacity: alpha commands only reactive on the small PV; beta swings the BESS.
    assert ba.cap_kw == 0.0
    assert ba.cap_kvar == 20.0            # 10 PV * 2 kVAr volt-var
    assert bb.cap_kw == 40050.0           # BESS 20000+20000 swing + 10 PV * 5 kW
    assert bb.cap_kvar == 8020.0          # BESS 8000 + 10 PV * 2
    assert bb.cap_kw > ba.cap_kw          # materially larger active authority
    assert bb.capacity.apparent_kva > 100 * ba.capacity.apparent_kva

    # (3) divergent persistence: alpha evaporates at attestation; beta persists to the horizon.
    assert bb.persistence.mean_seconds > 100 * ba.persistence.mean_seconds
    assert ba.persistence.mean_hours < 100.0        # attestation-gated: short retention
    assert bb.persistence.mean_seconds == sc.policy.analysis_horizon_seconds


def test_persistence_is_a_distribution_not_a_point():
    sc = build_scenario(SPEC)
    ba = analyze(sc.graph, "cred_alpha", sc.policy, seed=1)
    # attestation-gated retention varies across samples (geometric # of surviving cycles).
    assert len(set(ba.persistence.samples)) > 1
    assert ba.persistence.quantile(0.95) >= ba.persistence.median_seconds
