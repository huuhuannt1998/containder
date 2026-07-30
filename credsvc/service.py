"""Credential service: attested issuance, renewal-or-contain, session/command enforcement.

Puts the pieces together. Issuance requires a fresh attestation over a freshly generated
operational key (fresh-key binding). Renewal requires a new fresh attestation; presenting
only a prior certificate is refused, and a bad measurement is denied or narrowed to a safe
scope. Session and command acceptance are enforced against certificate validity, which is
what bounds Delta_expiry and Delta_effect.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from .ca import CA, new_ca, gen_key, issue_cert, cert_not_after, cert_not_before
from .attestation import Verifier, build_attestation


@dataclass
class IssuanceResult:
    ok: bool
    reason: str
    cert: object = None
    op_key: object = None
    scope: "dict | None" = None


def accept_command(cert, at_time: datetime.datetime, *, enforce: bool,
                   session_open: "datetime.datetime | None" = None,
                   session_max_age_s: float = 24 * 3600.0) -> bool:
    """Whether a command at `at_time` on `cert` is accepted.

    With enforcement, acceptance requires the command time to fall inside the certificate
    validity window (per-command revalidation). Without enforcement, a cached session accepts
    commands until the session ages out, ignoring certificate expiry.
    """
    if enforce:
        return cert_not_before(cert) <= at_time <= cert_not_after(cert)
    base = session_open if session_open is not None else cert_not_before(cert)
    return base <= at_time <= base + datetime.timedelta(seconds=session_max_age_s)


class CredentialService:
    def __init__(self, allowlist, *, op_ttl_seconds: float = 21600.0,
                 enforce_session: bool = True, enforce_command_cleanup: bool = True,
                 command_max_duration_seconds: float = 300.0):
        self.bootstrap_ca = new_ca("bootstrap-ca")
        self.op_issuer = new_ca("op-issuer")
        self.verifier = Verifier(allowlist)
        self.op_ttl = op_ttl_seconds
        self.enforce_session = enforce_session
        self.enforce_command_cleanup = enforce_command_cleanup
        self.command_max_duration = command_max_duration_seconds

    def enroll_device(self, device_id: str):
        """Long-lived bootstrap identity, used only for attestation, never for DER control."""
        bkey = gen_key()
        bcert = issue_cert(self.bootstrap_ca, bkey.public_key(), device_id,
                           ttl_seconds=10 * 365 * 24 * 3600)
        return bkey, bcert

    def issue_operational(self, device_id, bootstrap_key, bootstrap_cert, measurement,
                          scope, role="der", ttl=None, safe_mode_scope=None) -> IssuanceResult:
        """Attested issuance with a FRESH operational key each epoch."""
        nonce = self.verifier.challenge()
        fresh_key = gen_key()
        att = build_attestation(device_id, nonce, measurement, fresh_key.public_key(), bootstrap_key)
        ok, reason = self.verifier.verify(att, bootstrap_cert, fresh_key.public_key())
        if not ok:
            # renewal-or-contain: on some failures a safe (narrowed) scope may still issue.
            if reason == "measurement_not_allowlisted" and safe_mode_scope is not None:
                cert = issue_cert(self.op_issuer, fresh_key.public_key(),
                                  f"{device_id}:{role}:safe",
                                  ttl_seconds=ttl or self.op_ttl,
                                  scope={"role": role, "scope": safe_mode_scope, "safe_mode": True})
                return IssuanceResult(True, "safe_mode", cert, fresh_key, safe_mode_scope)
            return IssuanceResult(False, reason)
        cert = issue_cert(self.op_issuer, fresh_key.public_key(), f"{device_id}:{role}",
                          ttl_seconds=ttl or self.op_ttl, scope={"role": role, "scope": scope})
        return IssuanceResult(True, "ok", cert, fresh_key, scope)

    def renew_with_old_cert_only(self, device_id) -> IssuanceResult:
        """Renewal that presents only a prior certificate (no fresh attestation) is refused."""
        return IssuanceResult(False, "renewal_requires_fresh_attestation")
