"""DER model and the CSIP function-set -> commandable-capacity kernel.

Implements ``c(d, A_pi(d))`` from the M1 formalism: given a DER and the set of authorized
CSIP function sets, return the commandable active (kW) and reactive (kVAr) authority.

Function-set identifiers follow base IEEE 2030.5-2018 / CSIP ``DERControlBase``.
``opModExpLimW`` is deliberately absent: it is a CSIP-AUS (AS/NZS 4777.2) extension, not a
base-profile mode. Base-profile active-power/export capping is ``opModMaxLimW``; hard
connect authority is ``opModConnect`` / ``opModEnergize``; BESS charge/discharge is the
sign of ``opModFixedW``. (See M1 corrections note.)
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DERType(str, Enum):
    PV = "pv"
    BESS = "bess"
    EV = "ev"
    OTHER = "other"


class FunctionSet(str, Enum):
    """CSIP DERControlBase control modes (base IEEE 2030.5-2018 / CSIP)."""

    OP_MOD_MAX_LIM_W = "opModMaxLimW"      # active-power cap (curtailment authority)
    OP_MOD_FIXED_W = "opModFixedW"         # fixed active power, signed (BESS charge/discharge)
    OP_MOD_FIXED_VAR = "opModFixedVar"     # fixed reactive power
    OP_MOD_VOLT_VAR = "opModVoltVar"       # volt-var curve (reactive)
    OP_MOD_VOLT_WATT = "opModVoltWatt"     # volt-watt curve (active reduction)
    OP_MOD_FREQ_WATT = "opModFreqWatt"     # frequency-watt (active)
    OP_MOD_CONNECT = "opModConnect"        # connect/disconnect (hard active authority)
    OP_MOD_ENERGIZE = "opModEnergize"      # energize/de-energize (hard active authority)
    DER_STATUS_READ = "derStatusRead"      # read-only status; NO physical authority


# Which function sets confer active vs. reactive physical authority.
ACTIVE_POWER_MODES = frozenset({
    FunctionSet.OP_MOD_MAX_LIM_W,
    FunctionSet.OP_MOD_FIXED_W,
    FunctionSet.OP_MOD_VOLT_WATT,
    FunctionSet.OP_MOD_FREQ_WATT,
    FunctionSet.OP_MOD_CONNECT,
    FunctionSet.OP_MOD_ENERGIZE,
})
REACTIVE_POWER_MODES = frozenset({
    FunctionSet.OP_MOD_FIXED_VAR,
    FunctionSet.OP_MOD_VOLT_VAR,
})


@dataclass(frozen=True)
class DER:
    der_id: str
    der_type: DERType
    host_node: str
    nameplate_kw: float
    nameplate_kvar: float
    max_charge_kw: float = 0.0
    max_discharge_kw: float = 0.0

    def active_swing_kw(self) -> float:
        """Magnitude of commandable active-power swing when active authority is held.

        A storage device can be swung from full charge to full discharge; a PV/other DER's
        commandable swing is curtailment from nameplate to zero.
        """
        if self.der_type == DERType.BESS:
            swing = self.max_charge_kw + self.max_discharge_kw
            return swing if swing > 0 else self.nameplate_kw
        return self.nameplate_kw

    def reactive_swing_kvar(self) -> float:
        return self.nameplate_kvar


@dataclass(frozen=True)
class Capability:
    """Aggregate commandable authority: controllable real and reactive power."""

    controllable_kw: float
    controllable_kvar: float

    def __add__(self, other: "Capability") -> "Capability":
        return Capability(
            self.controllable_kw + other.controllable_kw,
            self.controllable_kvar + other.controllable_kvar,
        )

    @property
    def apparent_kva(self) -> float:
        return (self.controllable_kw ** 2 + self.controllable_kvar ** 2) ** 0.5


ZERO_CAPABILITY = Capability(0.0, 0.0)


def commandable_capacity(der: DER, authorized: "frozenset[FunctionSet]") -> Capability:
    """``c(d, A_pi(d))``: commandable capacity of DER ``d`` under authorized function sets.

    Read-only or empty scope confers zero physical authority. The two authority classes are
    independent: a credential authorized for volt-var but not any active-power mode can
    command reactive but not real power at that DER.
    """
    kw = der.active_swing_kw() if (authorized & ACTIVE_POWER_MODES) else 0.0
    kvar = der.reactive_swing_kvar() if (authorized & REACTIVE_POWER_MODES) else 0.0
    return Capability(kw, kvar)


# --- State-dependent flexibility (BR_flex) -------------------------------------------------
# Capacity above is a nameplate special case. The paper's BR_flex dimension is state dependent:
# the feasible command interval depends on device and grid operating state u_t (SoC, irradiance,
# present set-point, apparent-power limit), not only on the authorized scope.

@dataclass(frozen=True)
class DeviceState:
    """Operating state u_t that bounds commandable flexibility."""

    soc: float = 0.5              # state of charge in [0,1] (storage)
    irradiance: float = 1.0       # available fraction of PV nameplate in [0,1]
    present_kw: float = 0.0       # present active output (reference for the swing)
    s_rating_kva: "float | None" = None   # apparent-power limit; default from nameplate


@dataclass(frozen=True)
class FlexInterval:
    """Achievable active/reactive command intervals relative to present operation (kW, kVAr)."""

    dP_minus: float = 0.0
    dP_plus: float = 0.0
    dQ_minus: float = 0.0
    dQ_plus: float = 0.0

    def __add__(self, o: "FlexInterval") -> "FlexInterval":
        return FlexInterval(
            self.dP_minus + o.dP_minus, self.dP_plus + o.dP_plus,
            self.dQ_minus + o.dQ_minus, self.dQ_plus + o.dQ_plus,
        )

    @property
    def p_swing(self) -> float:
        return self.dP_plus - self.dP_minus

    @property
    def q_swing(self) -> float:
        return self.dQ_plus - self.dQ_minus

    def scalar(self, w_P: float = 1.0, w_Q: float = 1.0) -> float:
        """Conservative scalarization BR_flex = w_P*Pswing + w_Q*Qswing (weights stated)."""
        return w_P * self.p_swing + w_Q * self.q_swing


ZERO_FLEX = FlexInterval()


def commandable_flexibility(
    der: DER, authorized: "frozenset[FunctionSet]", state: "DeviceState | None" = None
) -> FlexInterval:
    """C_d(t; u_t, A_pi(d)): feasible command interval given scope and device state."""
    st = state if state is not None else DeviceState()
    dP_minus = dP_plus = dQ_minus = dQ_plus = 0.0

    if authorized & ACTIVE_POWER_MODES:
        if der.der_type == DERType.BESS:
            soc = max(0.0, min(1.0, st.soc))
            dischargeable = (der.max_discharge_kw or der.nameplate_kw) * soc
            chargeable = (der.max_charge_kw or der.nameplate_kw) * (1.0 - soc)
            dP_plus = dischargeable - st.present_kw
            dP_minus = -chargeable - st.present_kw
        else:
            available = der.nameplate_kw * max(0.0, min(1.0, st.irradiance))
            dP_plus = available - st.present_kw
            dP_minus = 0.0 - st.present_kw

    if authorized & REACTIVE_POWER_MODES:
        s_rating = st.s_rating_kva if st.s_rating_kva is not None else (
            (der.nameplate_kw ** 2 + der.nameplate_kvar ** 2) ** 0.5)
        q_cap = max(0.0, s_rating ** 2 - st.present_kw ** 2) ** 0.5
        if der.nameplate_kvar > 0:
            q_cap = min(q_cap, der.nameplate_kvar)
        dQ_plus = q_cap
        dQ_minus = -q_cap

    return FlexInterval(dP_minus, dP_plus, dQ_minus, dQ_plus)
