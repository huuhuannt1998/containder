"""Certificate authorities and X.509 issuance (real crypto via `cryptography`).

Bootstrap CA issues long-lived device identities; the operational issuer mints short-lived
scope-bound operational certificates for a freshly attested key. EC P-256 keys match the
ECC posture of IEEE 2030.5.
"""
from __future__ import annotations

import datetime
import json
from dataclasses import dataclass

from cryptography import x509
from cryptography.x509.oid import NameOID, ObjectIdentifier
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

# Private-arc OID carrying the CONTAINDER operational scope (illustrative).
SCOPE_OID = ObjectIdentifier("1.3.6.1.4.1.99999.1")


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def gen_key() -> ec.EllipticCurvePrivateKey:
    return ec.generate_private_key(ec.SECP256R1())


def pubkey_digest(pub: ec.EllipticCurvePublicKey) -> bytes:
    raw = pub.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    h = hashes.Hash(hashes.SHA256())
    h.update(raw)
    return h.finalize()


def cert_not_after(cert: x509.Certificate) -> datetime.datetime:
    """Aware-UTC notAfter, robust across cryptography versions."""
    try:
        return cert.not_valid_after_utc
    except AttributeError:  # pragma: no cover - older cryptography
        return cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)


def cert_not_before(cert: x509.Certificate) -> datetime.datetime:
    try:
        return cert.not_valid_before_utc
    except AttributeError:  # pragma: no cover
        return cert.not_valid_before.replace(tzinfo=datetime.timezone.utc)


@dataclass
class CA:
    key: ec.EllipticCurvePrivateKey
    cert: x509.Certificate


def new_ca(cn: str) -> CA:
    key = gen_key()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = _utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    return CA(key, cert)


def issue_cert(ca: CA, subject_pub, cn: str, ttl_seconds: float,
               scope: "dict | None" = None,
               not_before: "datetime.datetime | None" = None) -> x509.Certificate:
    now = not_before or _utcnow()
    builder = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)]))
        .issuer_name(ca.cert.subject)
        .public_key(subject_pub)
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(seconds=1))
        .not_valid_after(now + datetime.timedelta(seconds=ttl_seconds))
    )
    if scope is not None:
        builder = builder.add_extension(
            x509.UnrecognizedExtension(SCOPE_OID, json.dumps(scope, sort_keys=True).encode()),
            critical=False,
        )
    return builder.sign(ca.key, hashes.SHA256())


def read_scope(cert: x509.Certificate) -> "dict | None":
    try:
        ext = cert.extensions.get_extension_for_oid(SCOPE_OID)
        return json.loads(ext.value.value)
    except x509.ExtensionNotFound:
        return None
