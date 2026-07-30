"""Identity / delegation graph (M2 T2.1).

Node types: manufacturer CA, device, gateway, aggregator, utility server, operational
role. Typed edges: issuance (bootstrap identity), delegation (acts-on-behalf-of), and
authorization grant. Credentials are bound to nodes and carry a per-DER scope grant plus
lifecycle metadata consumed by the policy engine and the lifecycle simulator.

Key modeling choice matching the M1 formalism: a credential's *reach* (which DERs it can
address) is separate from its *scope* (which function sets are authorized at each DER).
Two credentials can therefore share an addressable DER set (identical topological reach)
yet differ in commandable capacity. This is what makes the M1 counterexample expressible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .der import DER, FunctionSet


class NodeType(str, Enum):
    MANUFACTURER_CA = "manufacturer_ca"
    DEVICE = "device"
    GATEWAY = "gateway"
    AGGREGATOR = "aggregator"
    UTILITY_SERVER = "utility_server"
    OPERATIONAL_ROLE = "operational_role"


class EdgeType(str, Enum):
    ISSUANCE = "issuance"            # issuer -> subject (bootstrap identity)
    DELEGATION = "delegation"        # aggregator -> subordinate device (acts-on-behalf-of)
    AUTHORIZATION = "authorization"  # grant of a DERProgram / FSA scope


class CredType(str, Enum):
    BOOTSTRAP_DEVICE = "bootstrap_device"   # long-lived hardware identity (L1)
    OPERATIONAL = "operational"             # ephemeral scope-bound op cert (L2, CONTAINDER)
    LEGACY_LONGLIVED = "legacy_longlived"   # baseline 2030.5 device cert == op cert (L1==L2)


@dataclass
class Node:
    node_id: str
    node_type: NodeType
    feeder: "str | None" = None
    site: "str | None" = None
    aggregator: "str | None" = None   # aggregator this node belongs to (fleet key)


@dataclass
class Edge:
    src: str
    dst: str
    edge_type: EdgeType


@dataclass
class Credential:
    cred_id: str
    cred_type: CredType
    bound_node: str                                    # node this credential authenticates as
    issuer: "str | None" = None
    ttl_seconds: "float | None" = None                 # None = indefinite (baseline device cert)
    attestation_gated: bool = False                    # renewal gated on attestation (CONTAINDER)
    # per-DER authorized function sets; '*' key = default for every addressed DER.
    scope: "dict[str, frozenset[FunctionSet]]" = field(default_factory=dict)

    def scope_for(self, der_id: str) -> "frozenset[FunctionSet]":
        if der_id in self.scope:
            return self.scope[der_id]
        return self.scope.get("*", frozenset())


@dataclass
class IdentityGraph:
    nodes: "dict[str, Node]" = field(default_factory=dict)
    edges: "list[Edge]" = field(default_factory=list)
    creds: "dict[str, Credential]" = field(default_factory=dict)
    ders: "dict[str, DER]" = field(default_factory=dict)

    # --- construction -----------------------------------------------------------------
    def add_node(self, node: Node) -> Node:
        self.nodes[node.node_id] = node
        return node

    def add_edge(self, src: str, dst: str, edge_type: EdgeType) -> Edge:
        e = Edge(src, dst, edge_type)
        self.edges.append(e)
        return e

    def add_credential(self, cred: Credential) -> Credential:
        self.creds[cred.cred_id] = cred
        return cred

    def add_der(self, der: DER) -> DER:
        self.ders[der.der_id] = der
        return der

    # --- topology queries -------------------------------------------------------------
    def ders_of_device(self, node_id: str) -> "set[str]":
        return {d.der_id for d in self.ders.values() if d.host_node == node_id}

    def devices_behind(self, node_id: str) -> "set[str]":
        """Nodes reachable by following DELEGATION edges from ``node_id`` (BFS)."""
        seen: "set[str]" = set()
        frontier = [node_id]
        while frontier:
            cur = frontier.pop()
            for e in self.edges:
                if e.edge_type == EdgeType.DELEGATION and e.src == cur and e.dst not in seen:
                    seen.add(e.dst)
                    frontier.append(e.dst)
        return seen

    def ders_in_site(self, site: str) -> "set[str]":
        node_ids = {n.node_id for n in self.nodes.values() if n.site == site}
        return {d.der_id for d in self.ders.values() if d.host_node in node_ids}

    def ders_in_feeder(self, feeder: str) -> "set[str]":
        node_ids = {n.node_id for n in self.nodes.values() if n.feeder == feeder}
        return {d.der_id for d in self.ders.values() if d.host_node in node_ids}

    def ders_in_fleet(self, aggregator: str) -> "set[str]":
        node_ids = {n.node_id for n in self.nodes.values() if n.aggregator == aggregator}
        return {d.der_id for d in self.ders.values() if d.host_node in node_ids}
