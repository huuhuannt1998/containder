"""pkimodel: CONTAINDER cyber-side blast-radius analysis engine (M2).

Turns the M1 four-radius formalism into executable code:

  * an identity/delegation graph (:mod:`pkimodel.cert_graph`),
  * a parameterized authorization policy engine (:mod:`pkimodel.policy_scope`),
  * a credential-lifecycle simulator (:mod:`pkimodel.lifecycle_sim`), and
  * the blast-radius engine computing BR_reach, BR_cap, BR_time
    (:mod:`pkimodel.blast_radius`).

Scope boundary (per the M2 mission): cyber side only. No power-flow, no OpenDSS, no
certificate cryptography. BR_phys (physical consequence) is owned by M4; this engine
produces the commandable-capacity input BR_phys consumes.
"""
from .der import (
    DER,
    DERType,
    FunctionSet,
    Capability,
    commandable_capacity,
    ACTIVE_POWER_MODES,
    REACTIVE_POWER_MODES,
)
from .cert_graph import (
    IdentityGraph,
    Node,
    NodeType,
    Edge,
    EdgeType,
    Credential,
    CredType,
)
from .policy_scope import Policy, AclRealismLevel, resolve_addressable_ders
from .lifecycle_sim import estimate_persistence, PersistenceDistribution
from .blast_radius import (
    BlastRadius,
    analyze,
    traverse_identity_graph,
    sum_der_capability,
)

__version__ = "0.1.0"

__all__ = [
    "DER",
    "DERType",
    "FunctionSet",
    "Capability",
    "commandable_capacity",
    "ACTIVE_POWER_MODES",
    "REACTIVE_POWER_MODES",
    "IdentityGraph",
    "Node",
    "NodeType",
    "Edge",
    "EdgeType",
    "Credential",
    "CredType",
    "Policy",
    "AclRealismLevel",
    "resolve_addressable_ders",
    "estimate_persistence",
    "PersistenceDistribution",
    "BlastRadius",
    "analyze",
    "traverse_identity_graph",
    "sum_der_capability",
]
