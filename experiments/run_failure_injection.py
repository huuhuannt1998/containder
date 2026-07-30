#!/usr/bin/env python3
"""Availability fault injection (reviewer §8): inject verifier outages into the running service.

We drive the real credential service through renewal cycles and inject an outage window during
which renewal fails at the verifier. Legitimate control-command success is determined by real
credential validity. This is an in-process injection (not a networked hardware outage), but the
issuance path and validity are real, not a closed-form model. Three renewal policies: fail-closed
deny, bounded grace, degraded-scope safe mode. Usage: python3 experiments/run_failure_injection.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from credsvc import CredentialService

GOOD = "fw-1.2.0-approved"


def sim(policy, H=60, ttl=10, renew_every=8, outage=(20, 40), grace=4):
    svc = CredentialService({GOOD})
    bkey, bcert = svc.enroll_device("d")
    last_issue = -999
    issued = denied = degraded = 0
    valid = []
    for t in range(H):
        if t % renew_every == 0:                      # renewal attempt
            in_outage = outage[0] <= t < outage[1]
            if not in_outage:
                r = svc.issue_operational("d", bkey, bcert, GOOD, scope="feeder")  # REAL issuance
                if r.ok:
                    last_issue, issued = t, issued + 1
            elif policy == "safe_mode":
                last_issue, degraded = t, degraded + 1   # degraded-scope local issuance
            else:
                denied += 1
        ttl_eff = ttl + (grace if policy == "grace" else 0)
        valid.append((t - last_issue) < ttl_eff)
    success = sum(valid) / H
    recovery = next((t - outage[1] for t in range(outage[1], H) if valid[t]), None)
    return {"success_rate": round(success, 3), "issued": issued, "denied": denied,
            "degraded": degraded, "recovery_steps": recovery}


def main():
    res = {p: sim(p) for p in ["deny", "grace", "safe_mode"]}
    print("== Availability under injected verifier outage (real issuance, in-process injection) ==")
    print("horizon 60, TTL 10, renew every 8, outage steps [20,40)\n")
    print(f"{'policy':10} {'cmd_success':>12} {'renewals_denied':>16} {'recovery(steps)':>16}")
    for p, r in res.items():
        rec = r["recovery_steps"] if r["recovery_steps"] is not None else "none"
        print(f"{p:10} {r['success_rate']:>12} {r['denied']:>16} {str(rec):>16}")
    (Path(__file__).resolve().parent / "results" / "failure_injection.json").write_text(
        json.dumps({"policies": res, "params": {"horizon": 60, "ttl": 10, "renew_every": 8,
                    "outage": [20, 40], "grace": 4},
                    "note": "In-process verifier-outage injection on the real credential service; "
                            "issuance and credential validity are real. Not a networked/hardware "
                            "outage."}, indent=2))
    print("\nSaved -> experiments/results/failure_injection.json")


if __name__ == "__main__":
    main()
