"""Hand-verified capacity-aggregation cases (acceptance #5)."""
from pkimodel import DER, DERType, FunctionSet, Capability, commandable_capacity


def test_pv_active_only():
    pv = DER("pv", DERType.PV, "n", nameplate_kw=100.0, nameplate_kvar=40.0)
    cap = commandable_capacity(pv, frozenset({FunctionSet.OP_MOD_MAX_LIM_W}))
    assert cap == Capability(100.0, 0.0)


def test_pv_reactive_only():
    pv = DER("pv", DERType.PV, "n", nameplate_kw=100.0, nameplate_kvar=40.0)
    cap = commandable_capacity(pv, frozenset({FunctionSet.OP_MOD_VOLT_VAR}))
    assert cap == Capability(0.0, 40.0)


def test_read_only_is_zero_authority():
    pv = DER("pv", DERType.PV, "n", nameplate_kw=100.0, nameplate_kvar=40.0)
    cap = commandable_capacity(pv, frozenset({FunctionSet.DER_STATUS_READ}))
    assert cap == Capability(0.0, 0.0)


def test_empty_scope_is_zero_authority():
    pv = DER("pv", DERType.PV, "n", nameplate_kw=100.0, nameplate_kvar=40.0)
    assert commandable_capacity(pv, frozenset()) == Capability(0.0, 0.0)


def test_both_modes():
    pv = DER("pv", DERType.PV, "n", nameplate_kw=100.0, nameplate_kvar=40.0)
    cap = commandable_capacity(
        pv, frozenset({FunctionSet.OP_MOD_MAX_LIM_W, FunctionSet.OP_MOD_VOLT_VAR})
    )
    assert cap == Capability(100.0, 40.0)


def test_bess_active_swing_is_charge_plus_discharge():
    bess = DER("b", DERType.BESS, "n", nameplate_kw=1000.0, nameplate_kvar=500.0,
               max_charge_kw=1000.0, max_discharge_kw=1000.0)
    cap = commandable_capacity(bess, frozenset({FunctionSet.OP_MOD_FIXED_W}))
    assert cap == Capability(2000.0, 0.0)  # full charge-to-discharge swing


def test_capability_addition():
    a = Capability(10.0, 5.0)
    b = Capability(1.0, 2.0)
    assert a + b == Capability(11.0, 7.0)
