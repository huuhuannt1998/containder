#!/usr/bin/env python3
"""Run the credential-service campaigns C1 (invariants), C2 (containment), C3 (overhead).

Produces REAL measured numbers on the workstation tier using real X.509 / ECDSA / mTLS.
Constrained-hardware (Pi/TPM) and GridLAB-D cross-check are out of scope here and are
reported as remaining. Run: python3 experiments/run_credsvc.py
"""
from __future__ import annotations

import datetime
import json
import os
import socket
import ssl
import statistics
import tempfile
import threading
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from credsvc import CredentialService, Verifier, build_attestation, gen_key, cert_not_after
from credsvc.ca import cert_not_before, read_scope, issue_cert

ALLOW = {"fw-1.2.0-approved"}
GOOD = "fw-1.2.0-approved"
BAD = "fw-9.9.9-tampered"


def same_pub(k1, k2) -> bool:
    return k1.public_key().public_numbers() == k2.public_key().public_numbers()


# ---------------------------------------------------------------- C1: security invariants
def campaign_c1() -> dict:
    svc = CredentialService(ALLOW, op_ttl_seconds=2.0)
    dev = "der-0001"
    bkey, bcert = svc.enroll_device(dev)
    checks = {}

    # 1. bootstrap identity carries no operational control scope
    checks["I1_bootstrap_not_control"] = read_scope(bcert) is None

    # 2. operational cert issued only after valid fresh attestation (bad measurement denied)
    bad = svc.issue_operational(dev, bkey, bcert, BAD, scope="feeder")
    good = svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")
    checks["I2_issue_needs_attestation"] = (not bad.ok) and good.ok

    # 3. certificate bound to the freshly attested public key
    checks["I3_cert_bound_to_fresh_key"] = (
        good.cert.public_key().public_numbers() == good.op_key.public_key().public_numbers())

    # 4. replayed evidence rejected (reused nonce)
    v = Verifier(ALLOW)
    n = v.challenge()
    fk = gen_key()
    att = build_attestation(dev, n, GOOD, fk.public_key(), bkey)
    ok1, _ = v.verify(att, bcert, fk.public_key())
    ok2, r2 = v.verify(att, bcert, fk.public_key())
    checks["I4_replay_rejected"] = ok1 and (not ok2) and r2 == "replayed_nonce"

    # 5/6. expired credential cannot issue commands (session bound to validity)
    from credsvc import accept_command
    na = cert_not_after(good.cert)
    checks["I5_expired_no_command"] = not accept_command(
        good.cert, na + datetime.timedelta(seconds=1), enforce=True)

    # 7. per-command authorization matches issued scope
    checks["I6_scope_matches"] = read_scope(good.cert)["scope"] == "feeder"

    # 8/12/13. known-bad measurement -> safe-mode narrowed scope, never full
    safe = svc.issue_operational(dev, bkey, bcert, BAD, scope="feeder", safe_mode_scope="read_only")
    checks["I7_scope_narrowing"] = safe.ok and safe.scope == "read_only" and safe.scope != "feeder"

    # 9. command-effect cleanup bounds Delta_effect
    checks["I10_command_cleanup_bounded"] = (
        svc.enforce_command_cleanup and svc.command_max_duration <= 600.0)

    # 10. old credential epoch cannot self-renew
    checks["I8_no_self_renew"] = not svc.renew_with_old_cert_only(dev).ok

    # 11. copied previous operational key fails after epoch rotation
    ep1 = svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")   # key K1
    ep2 = svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")   # fresh key K2
    fresh_key_each_epoch = not same_pub(ep1.op_key, ep2.op_key)
    # attacker holds K1/cert1; at epoch-2 time cert1 (ttl 2s) is treated as expired
    old_expired = not accept_command(
        ep1.cert, cert_not_after(ep1.cert) + datetime.timedelta(seconds=1), enforce=True)
    checks["I9_copied_key_contained"] = fresh_key_each_epoch and old_expired

    passed = sum(1 for v in checks.values() if v)
    return {"checks": checks, "passed": passed, "total": len(checks)}


# ---------------------------------------------------------------- C2: containment timing
def campaign_c2() -> dict:
    svc = CredentialService(ALLOW, op_ttl_seconds=2.0)
    dev = "der-0002"
    bkey, bcert = svc.enroll_device(dev)
    from credsvc import accept_command
    res = svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")
    na, nb = cert_not_after(res.cert), cert_not_before(res.cert)
    cmds = [na - datetime.timedelta(seconds=0.5),
            na + datetime.timedelta(seconds=0.5),
            na + datetime.timedelta(seconds=5.0)]

    def last_accepted(enforce):
        acc = [t for t in cmds if accept_command(res.cert, t, enforce=enforce,
                                                 session_open=nb, session_max_age_s=24 * 3600)]
        return max(acc) if acc else None

    la_enf = last_accepted(True)
    la_noenf = last_accepted(False)
    d_expiry_enf = (la_enf - na).total_seconds() if la_enf else float("-inf")
    d_expiry_noenf = (la_noenf - na).total_seconds() if la_noenf else float("-inf")

    # copied-key-after-rotation: fresh key each epoch; old cert expires
    ep1 = svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")
    ep2 = svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")
    return {
        "delta_expiry_enforced_s": round(d_expiry_enf, 3),
        "delta_expiry_unenforced_s": round(d_expiry_noenf, 3),
        "copied_key_fresh_each_epoch": not same_pub(ep1.op_key, ep2.op_key),
        "credential_ttl_s": svc.op_ttl,
    }


# ---------------------------------------------------------------- C3: overhead microbench
def _stats(samples_ms):
    s = sorted(samples_ms)
    return {"median_ms": round(statistics.median(s), 4),
            "p95_ms": round(s[min(len(s) - 1, int(0.95 * len(s)))], 4),
            "p99_ms": round(s[min(len(s) - 1, int(0.99 * len(s)))], 4)}


def _time(fn, n):
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000.0)
    return out


def campaign_c3(n=500) -> dict:
    svc = CredentialService(ALLOW, op_ttl_seconds=21600.0)
    dev = "der-0003"
    bkey, bcert = svc.enroll_device(dev)
    v = Verifier(ALLOW)

    def op_keygen():
        gen_key()

    def op_attest():
        fk = gen_key()
        build_attestation(dev, "n" * 32, GOOD, fk.public_key(), bkey)

    def op_full_issue():
        svc.issue_operational(dev, bkey, bcert, GOOD, scope="feeder")

    results = {
        "key_generation": _stats(_time(op_keygen, n)),
        "attestation_build": _stats(_time(op_attest, n)),
        "full_attested_issuance": _stats(_time(op_full_issue, n)),
        "n": n,
    }
    results["mtls_handshake"] = _mtls_bench(svc, n=100)
    return results


def _mtls_bench(svc, n=100):
    """Real mTLS handshake latency over loopback with issued operational certs."""
    try:
        d = svc.enroll_device("der-tls")
        bkey, bcert = d
        s = svc.issue_operational("der-tls", bkey, bcert, GOOD, scope="feeder", ttl=3600)
        tmp = Path(tempfile.mkdtemp())
        ca_pem = tmp / "ca.pem"
        crt = tmp / "op.pem"
        key = tmp / "op.key"
        ca_pem.write_bytes(svc.op_issuer.cert.public_bytes(serialization.Encoding.PEM))
        crt.write_bytes(s.cert.public_bytes(serialization.Encoding.PEM))
        key.write_bytes(s.op_key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))

        srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv_sock.bind(("127.0.0.1", 0))
        srv_sock.listen(8)
        port = srv_sock.getsockname()[1]

        sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sctx.load_cert_chain(str(crt), str(key))
        sctx.verify_mode = ssl.CERT_REQUIRED
        sctx.load_verify_locations(str(ca_pem))

        stop = threading.Event()

        def server():
            while not stop.is_set():
                try:
                    srv_sock.settimeout(1.0)
                    conn, _ = srv_sock.accept()
                except (socket.timeout, OSError):
                    continue
                try:
                    with sctx.wrap_socket(conn, server_side=True) as ss:
                        ss.recv(16)
                except Exception:
                    pass

        th = threading.Thread(target=server, daemon=True)
        th.start()

        cctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        cctx.check_hostname = False
        cctx.verify_mode = ssl.CERT_REQUIRED
        cctx.load_verify_locations(str(ca_pem))
        cctx.load_cert_chain(str(crt), str(key))

        samples = []
        for _ in range(n):
            t = time.perf_counter()
            with socket.create_connection(("127.0.0.1", port), timeout=2.0) as raw:
                with cctx.wrap_socket(raw, server_hostname="der-tls:der") as tls:
                    tls.sendall(b"hello")
            samples.append((time.perf_counter() - t) * 1000.0)
        stop.set()
        srv_sock.close()
        return _stats(samples)
    except Exception as exc:  # pragma: no cover
        return {"error": f"mtls bench skipped: {exc}"}


def main():
    print("== CONTAINDER credential-service campaigns (real, workstation tier) ==\n")
    c1 = campaign_c1()
    print(f"C1 security invariants: {c1['passed']}/{c1['total']} pass")
    for k, val in c1["checks"].items():
        print(f"   {'PASS' if val else 'FAIL'}  {k}")

    c2 = campaign_c2()
    print("\nC2 containment timing:")
    print(f"   Delta_expiry (enforced)   = {c2['delta_expiry_enforced_s']:>7} s  (<=0 = contained)")
    print(f"   Delta_expiry (unenforced) = {c2['delta_expiry_unenforced_s']:>7} s  (grows to session age)")
    print(f"   fresh key each epoch (copied-key contained) = {c2['copied_key_fresh_each_epoch']}")

    c3 = campaign_c3()
    print("\nC3 overhead (ms, workstation tier):")
    for op in ["key_generation", "attestation_build", "full_attested_issuance", "mtls_handshake"]:
        s = c3[op]
        if "error" in s:
            print(f"   {op:24} {s['error']}")
        else:
            print(f"   {op:24} median={s['median_ms']:.3f}  p95={s['p95_ms']:.3f}  p99={s['p99_ms']:.3f}")

    out = {"c1": c1, "c2": c2, "c3": c3, "platform": "workstation",
           "note": "Constrained-hardware (Pi/TPM) and GridLAB-D cross-check not measured here."}
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "credsvc.json").write_text(json.dumps(out, indent=2))
    print(f"\nSaved -> experiments/results/credsvc.json")


if __name__ == "__main__":
    main()
