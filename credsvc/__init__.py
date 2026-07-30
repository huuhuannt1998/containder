"""credsvc: CONTAINDER attested ephemeral-credential service (M3, real crypto).

A working Python realization of the CONTAINDER credential lifecycle using real X.509
certificates (cryptography) and an EAT-style attestation token: bootstrap identity,
attested issuance with fresh-key binding, renewal-or-contain, and session/command
enforcement. This is the prototype the functional (C1), containment (C2), and overhead
(C3) experiments run against. It substitutes a Python 2030.5-style client/server for the
EPRI C client (a documented deviation); the credential-lifecycle semantics are the same.
"""
from .ca import CA, new_ca, gen_key, issue_cert, pubkey_digest, cert_not_after, SCOPE_OID
from .attestation import Attestation, Verifier, build_attestation
from .service import CredentialService, IssuanceResult, accept_command

__all__ = [
    "CA", "new_ca", "gen_key", "issue_cert", "pubkey_digest", "cert_not_after", "SCOPE_OID",
    "Attestation", "Verifier", "build_attestation",
    "CredentialService", "IssuanceResult", "accept_command",
]
__version__ = "0.1.0"
