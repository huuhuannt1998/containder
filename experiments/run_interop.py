#!/usr/bin/env python3
"""RQ7: what does a real IEEE 2030.5 server actually do when an identity is withdrawn?

Why this exists
---------------
The paper's motivating claim rests on a *modelled* semantics: that local denial refuses new
sessions while leaving an established session and an already-issued control untouched. That model
was chosen because the accessible standards material does not specify the behaviour, but a model
is not an implementation, and until now nothing here tested one.

This experiment runs against the GridAPPS-D IEEE 2030.5 server, an independent open-source
implementation of the Common Smart Inverter Profile, over real mutual TLS with real
certificate-derived LFDI identities. It is not our client talking to our server: the server is
third-party code, and the only thing we supply is the test sequence.

The sequence is the one the review specified:

  1. establish mutual TLS and confirm the certificate-derived identity resolves;
  2. read the resource tree the identity is authorized to see;
  3. hold the connection open (HTTP keep-alive) and confirm it keeps serving;
  4. withdraw the identity server-side, by the only means the implementation offers;
  5. issue a further request over the *same, already-established* connection;
  6. attempt a *new* connection with the same certificate;
  7. observe whether previously published control content survives the withdrawal.

Each step records the HTTP status, whether the TCP connection was reused, and the server's
behaviour, so the resulting semantics are a measurement rather than an assumption.

**What withdrawal means here.** The implementation provides no allow/deny list: an audit of its
request path shows identity resolved per request from the TLS peer certificate, and the only
authorization gate is whether the derived SFDI is a registered device. Withdrawal is therefore
performed the only way the implementation permits -- removing the device from the registry the
gate consults. That is itself a finding, and the manuscript reports it as one.

Usage: python3 experiments/run_interop.py [--server URL] [--tls DIR]
"""
import argparse
import json
import socket
import ssl
import sys
import time
from http.client import HTTPSConnection
from pathlib import Path

OUT = Path(__file__).resolve().parent / "results" / "interop.json"



def sfdi_of(path: Path):
    """SFDI the server derives from a certificate file, or None if unreadable."""
    try:
        import hashlib
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes
        cert = x509.load_pem_x509_certificate(path.read_bytes())
        fp = cert.fingerprint(hashes.SHA256()).hex()
        # lfdi = first 160 bits of the fingerprint; sfdi = first 36 bits + check digit,
        # matching ieee_2030_5.certs.lfdi_from_fingerprint / sfdi_from_lfdi.
        lfdi = fp[:40]
        sfdi_no_check = int(lfdi[:9], 16)
        check = (10 - sum(int(d) for d in str(sfdi_no_check)) % 10) % 10
        return int(str(sfdi_no_check) + str(check))
    except Exception:
        return None


def make_context(tls_dir: Path, name: str) -> ssl.SSLContext:
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.load_cert_chain(certfile=str(tls_dir / "certs" / f"{name}.pem"),
                        keyfile=str(tls_dir / "private" / f"{name}.pem"))
    return ctx


def request(conn: HTTPSConnection, path: str) -> dict:
    """One request on a (possibly reused) connection. Records the socket identity."""
    t0 = time.perf_counter()
    try:
        conn.request("GET", path)
        r = conn.getresponse()
        body = r.read()
        sock = conn.sock
        return {"path": path, "status": r.status, "bytes": len(body),
                "ms": round((time.perf_counter() - t0) * 1000, 2),
                "socket": f"{sock.getsockname()[1]}" if sock else None,
                "error": None,
                "snippet": body[:120].decode("utf-8", "replace").replace("\n", " ")}
    except Exception as exc:                                     # noqa: BLE001
        return {"path": path, "status": None, "bytes": 0,
                "ms": round((time.perf_counter() - t0) * 1000, 2),
                "socket": None, "error": f"{type(exc).__name__}: {exc}", "snippet": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=7443)
    ap.add_argument("--tls", default="/private/tmp/sep_test/tls")
    ap.add_argument("--identity", default="der_adversary")
    args = ap.parse_args()

    tls = Path(args.tls)
    # Any credential left withdrawn by an interrupted run is restored before starting, so the
    # experiment is idempotent rather than destructive.
    for stale in list((tls / "certs").glob("*.withdrawn")) + \
                 list((tls / "combined").glob("*.withdrawn")):
        stale.rename(stale.with_name(stale.name[:-len(".withdrawn")]))
    ctx = make_context(tls, args.identity)
    steps = []

    def new_conn():
        c = HTTPSConnection(args.host, args.port, context=ctx, timeout=15)
        c.connect()
        return c

    # --- 1-3: establish, read, and confirm the connection is genuinely reused ---------------
    conn = new_conn()
    first_port = conn.sock.getsockname()[1]
    for path in ("/dcap", "/edev", "/dcap"):
        steps.append({"phase": "established_session", **request(conn, path)})
    reused = all(s["socket"] == str(first_port) for s in steps if s["socket"])

    # --- 3b: snapshot the control tree with a second, uninvolved identity -------------------
    control_paths_pre = ("/derp", "/derp_0", "/derp_0_derc", "/derp_0_derca", "/derp_0_dderc")
    ctx_other = make_context(tls, "der_victim")
    c_other = HTTPSConnection(args.host, args.port, context=ctx_other, timeout=15)
    c_other.connect()
    before, before_status = {}, {}
    for path in control_paths_pre:
        r = request(c_other, path)
        steps.append({"phase": "control_before_withdrawal", **r})
        before[path] = r.get("snippet")
        before_status[path] = r.get("status")

    # --- 4: withdraw the identity by the only means the implementation offers ---------------
    # The registry the authorization gate consults is the TLS repository's device set. Removing
    # the combined credential file is the closest analogue to a deny-list entry available.
    # The registry is globbed live on each request, but it holds CA-issued duplicates that carry
    # the SAME derived SFDI as the named credential. Withdrawing only the named file leaves a
    # duplicate behind and the identity still resolves -- an error the first run of this
    # experiment made. Every file whose derived SFDI matches is therefore withdrawn.
    target_sfdi = sfdi_of(tls / "certs" / f"{args.identity}.pem")
    withdrawn = {}
    for p in sorted((tls / "certs").glob("*.pem")):
        if sfdi_of(p) == target_sfdi:
            backup = p.with_name(p.name + ".withdrawn")
            p.rename(backup)
            withdrawn[p.name] = backup.name
    combined = tls / "combined" / f"{args.identity}-combined.pem"
    if combined.exists():
        b = combined.with_name(combined.name + ".withdrawn")
        combined.rename(b)
        withdrawn[combined.name] = b.name
    steps.append({"phase": "withdrawal", "action": "removed identity from server registry",
                  "files": withdrawn})
    time.sleep(2)

    # --- 5: same, already-established connection ---------------------------------------------
    steps.append({"phase": "after_withdrawal_same_connection", **request(conn, "/dcap")})

    # --- 6: a brand-new connection with the same certificate ---------------------------------
    try:
        conn2 = new_conn()
        steps.append({"phase": "after_withdrawal_new_connection", **request(conn2, "/dcap")})
        conn2.close()
    except Exception as exc:                                     # noqa: BLE001
        steps.append({"phase": "after_withdrawal_new_connection", "path": "/dcap",
                      "status": None, "error": f"{type(exc).__name__}: {exc}"})

    # --- 7: does an already-installed DERControl survive the withdrawal? ---------------------
    # This is the half of the motivating claim the session result does not settle. The control
    # tree is read with a *different* still-valid identity, so what is observed is the server's
    # own state and not the withdrawn identity's access to it. The control bodies are compared
    # before and after: if the scheduled control is still served, withdrawal did not retract it.
    control_paths = ("/derp", "/derp_0", "/derp_0_derc", "/derp_0_derca", "/derp_0_dderc")
    for path in control_paths:
        steps.append({"phase": "control_after_withdrawal", **request(c_other, path)})

    after = {s["path"]: s.get("snippet") for s in steps
             if s["phase"] == "control_after_withdrawal"}
    after_status = {s["path"]: s.get("status") for s in steps
                    if s["phase"] == "control_after_withdrawal"}
    control_survived = {
        pth: {"before_status": before_status.get(pth), "after_status": after_status.get(pth),
              "body_identical": before.get(pth) == after.get(pth)}
        for pth in control_paths}

    for c in (conn, c_other):
        try:
            c.close()
        except Exception:
            pass

    # --- restore, so the experiment is repeatable --------------------------------------------
    for orig, back in withdrawn.items():
        src = (tls / "combined" / back) if "combined" in back else (tls / "certs" / back)
        if src.exists():
            src.rename(src.with_name(orig))

    same = [s for s in steps if s["phase"] == "after_withdrawal_same_connection"]
    new = [s for s in steps if s["phase"] == "after_withdrawal_new_connection"]
    out = {
        "implementation": "GridAPPS-D IEEE 2030.5 server (open-source CSIP implementation)",
        "transport": "real mutual TLS, certificate-derived LFDI identity",
        "withdrawal_mechanism": "removal from the server's device registry; the implementation "
                                "provides no allow/deny list",
        "connection_reused_across_requests": reused,
        "established_session_survives_withdrawal": bool(same and same[0].get("status") == 200),
        "new_session_survives_withdrawal": bool(new and new[0].get("status") == 200),
        "installed_control_survives_withdrawal": all(
            v["after_status"] == 200 and v["body_identical"]
            for v in control_survived.values() if v["before_status"] == 200),
        "control_resources": control_survived,
        "steps": steps,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2))
    print(f"wrote {OUT}\n")
    print(f"connection genuinely reused across requests : {reused}")
    for s in steps:
        if "status" in s:
            print(f"  {s['phase']:38} {s.get('path','') :8} "
                  f"status={s.get('status')} {s.get('error') or ''}")
        else:
            print(f"  {s['phase']:38} {s.get('action','')}")
    print("\ncontrol resources across withdrawal (read by a second valid identity):")
    for k, v in control_survived.items():
        print(f"  {k:18} before={v['before_status']} after={v['after_status']} "
              f"body_identical={v['body_identical']}")
    print(f"\nestablished session survives withdrawal : "
          f"{out['established_session_survives_withdrawal']}")
    print(f"new session survives withdrawal         : "
          f"{out['new_session_survives_withdrawal']}")
    print(f"installed control survives withdrawal   : "
          f"{out['installed_control_survives_withdrawal']}")


if __name__ == "__main__":
    main()
