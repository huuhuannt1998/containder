"""EAT-style attestation token and verifier (RATS Attester/Verifier roles).

The attester signs claims (device id, nonce, software measurement, and the digest of a
freshly generated operational public key) with the device bootstrap key. The verifier
checks nonce freshness and single use (replay resistance), device-id match against the
bootstrap certificate, measurement allowlisting, fresh-key binding, and the signature.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from .ca import pubkey_digest


@dataclass
class Attestation:
    device_id: str
    nonce: str
    measurement: str
    fresh_pubkey_digest_hex: str
    signature: bytes


def _payload(device_id: str, nonce: str, measurement: str, fpk_hex: str) -> bytes:
    return json.dumps(
        {"device_id": device_id, "nonce": nonce, "measurement": measurement, "fpk": fpk_hex},
        sort_keys=True,
    ).encode()


def build_attestation(device_id, nonce, measurement, fresh_pub, bootstrap_key) -> Attestation:
    fpk = pubkey_digest(fresh_pub).hex()
    sig = bootstrap_key.sign(_payload(device_id, nonce, measurement, fpk),
                             ec.ECDSA(hashes.SHA256()))
    return Attestation(device_id, nonce, measurement, fpk, sig)


class Verifier:
    """RATS Verifier: issues nonces and validates attestation evidence."""

    def __init__(self, allowlist):
        self.allowlist = set(allowlist)
        self._nonces: "dict[str, bool]" = {}   # nonce -> consumed

    def challenge(self) -> str:
        n = os.urandom(16).hex()
        self._nonces[n] = False
        return n

    def verify(self, att: Attestation, bootstrap_cert, expected_fresh_pub) -> "tuple[bool, str]":
        if att.nonce not in self._nonces:
            return (False, "unknown_nonce")
        if self._nonces[att.nonce]:
            return (False, "replayed_nonce")
        cn = bootstrap_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        if cn != att.device_id:
            return (False, "device_id_mismatch")
        if att.measurement not in self.allowlist:
            return (False, "measurement_not_allowlisted")
        if att.fresh_pubkey_digest_hex != pubkey_digest(expected_fresh_pub).hex():
            return (False, "fresh_key_not_bound")
        try:
            bootstrap_cert.public_key().verify(
                att.signature,
                _payload(att.device_id, att.nonce, att.measurement, att.fresh_pubkey_digest_hex),
                ec.ECDSA(hashes.SHA256()),
            )
        except Exception:
            return (False, "bad_signature")
        self._nonces[att.nonce] = True   # consume nonce (single use)
        return (True, "ok")
