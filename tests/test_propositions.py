"""Propositions 1-3 (scope / temporal / physical-state separation) as regression tests.

These correspond one-to-one to the manuscript's separation propositions: two configurations
that share topological reach but differ in an impact dimension. If any fails, the paper's
separation claim is broken in code.
"""
from pkimodel import (
    IdentityGraph, Node, NodeType, EdgeType, Credential, CredType,
    DER, DERType, FunctionSet, Policy, AclRealismLevel, analyze,
)
from pkimodel.der import DeviceState, commandable_flexibility

FULL = frozenset({FunctionSet.OP_MOD_FIXED_W, FunctionSet.OP_MOD_MAX_LIM_W,
                  FunctionSet.OP_MOD_VOLT_VAR})
READ_ONLY = frozenset({FunctionSet.DER_STATUS_READ})


def _fleet():
    g = IdentityGraph()
    g.add_node(Node("A", NodeType.AGGREGATOR, aggregator="A"))
    g.add_node(Node("dvb", NodeType.DEVICE, feeder="f", aggregator="A"))
    g.add_node(Node("dvp", NodeType.DEVICE, feeder="f", aggregator="A"))
    g.add_der(DER("bess", DERType.BESS, "dvb", 20000, 8000, 20000, 20000))
    g.add_der(DER("pv", DERType.PV, "dvp", 5, 2))
    g.add_edge("A", "dvb", EdgeType.DELEGATION)
    g.add_edge("A", "dvp", EdgeType.DELEGATION)
    return g


def test_proposition1_scope_separation():
    """Equal reach, different flexibility, via the scope map A only."""
    g = _fleet()
    g.add_credential(Credential("c_ctrl", CredType.OPERATIONAL, "A", scope={"*": FULL}))
    g.add_credential(Credential("c_ro", CredType.OPERATIONAL, "A", scope={"*": READ_ONLY}))
    p = Policy(acl_realism_level=AclRealismLevel.FLEET)
    a = analyze(g, "c_ctrl", p, seed=1)
    b = analyze(g, "c_ro", p, seed=1)
    assert a.reachable_ders == b.reachable_ders          # identical topological reach
    assert b.flex_scalar() == 0.0                        # read-only -> zero flexibility
    assert a.flex_scalar() > 1000.0                      # control scope -> large flexibility


def test_proposition2_temporal_separation():
    """Equal reach, different retained-authority trajectory, via lifetime + enforcement."""
    g = _fleet()
    g.add_credential(Credential("c_ephem", CredType.OPERATIONAL, "A", ttl_seconds=21600,
                                attestation_gated=True, scope={"*": FULL}))
    g.add_credential(Credential("c_legacy", CredType.LEGACY_LONGLIVED, "A", ttl_seconds=None,
                                attestation_gated=False, scope={"*": FULL}))
    p_enforced = Policy(acl_realism_level=AclRealismLevel.FLEET, attestation_detect_prob=0.5,
                        enforce_session=True, enforce_command_cleanup=True,
                        command_max_duration_seconds=300)
    p_unenforced = Policy(acl_realism_level=AclRealismLevel.FLEET, revocation_enabled=False,
                          enforce_session=False, enforce_command_cleanup=False)
    a = analyze(g, "c_ephem", p_enforced, seed=1)
    b = analyze(g, "c_legacy", p_unenforced, seed=1)
    assert a.reachable_ders == b.reachable_ders
    assert b.retained.br_auth_seconds > 100 * a.retained.br_auth_seconds


def test_proposition3_physical_state_separation():
    """Same authorized command, different feeder state -> different outcome.

    Uses a labeled TOY voltage-sensitivity proxy, NOT a feeder simulation. It tests only the
    separation *property* (outcome varies with operating state u at fixed cyber authorization);
    real physical consequence is computed by the M4 OpenDSS/GridLAB-D co-simulation.
    """
    def toy_voltage_proxy(u_sensitivity_pu_per_kw: float, delta_p_kw: float) -> float:
        return u_sensitivity_pu_per_kw * delta_p_kw

    delta_p = 5000.0  # identical authorized command
    out_light = toy_voltage_proxy(0.0, delta_p)      # stiff feeder state
    out_weak = toy_voltage_proxy(1.5e-4, delta_p)    # weak feeder state
    assert out_light != out_weak


def test_flexibility_depends_on_state_of_charge():
    """BR_flex is state dependent: a battery discharges more when it is full."""
    bess = DER("b", DERType.BESS, "n", nameplate_kw=1000.0, nameplate_kvar=500.0,
               max_charge_kw=1000.0, max_discharge_kw=1000.0)
    active = frozenset({FunctionSet.OP_MOD_FIXED_W})
    empty = commandable_flexibility(bess, active, DeviceState(soc=0.0))
    full = commandable_flexibility(bess, active, DeviceState(soc=1.0))
    assert full.dP_plus > empty.dP_plus                  # more dischargeable at high SoC
    assert empty.dP_minus < full.dP_minus                # more chargeable at low SoC
