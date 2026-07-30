#!/usr/bin/env python3
"""Availability campaign (C6 / RQ4): renewal cost (measured) + outage control-success (modeled).

Renewal latency and issuer throughput are MEASURED on the real credential service. The
control-success under a verifier/issuer outage is MODELED as a deterministic function of the
credential TTL, the grace period, and the outage duration, for three renewal policies
(fail-closed deny, bounded grace, degraded safe-mode). This quantifies the security-availability
tradeoff of short-lived attested credentials. Usage: python3 experiments/run_availability.py
"""
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from credsvc import CredentialService

GOOD = "fw-1.2.0-approved"


def measure_issuer(n=2000):
    """Measured: renewal = full attested issuance (fresh nonce, key, attestation, mint)."""
    svc = CredentialService({GOOD}, op_ttl_seconds=3600)
    bkey, bcert = svc.enroll_device("d")
    lat = []
    t0 = time.perf_counter()
    for _ in range(n):
        t = time.perf_counter()
        svc.issue_operational("d", bkey, bcert, GOOD, scope="feeder")
        lat.append((time.perf_counter() - t) * 1000.0)
    total = time.perf_counter() - t0
    lat.sort()
    return {"throughput_per_s": round(n / total, 1),
            "renew_median_ms": round(statistics.median(lat), 3),
            "renew_p99_ms": round(lat[min(n - 1, int(0.99 * n))], 3)}


def renewal_margin(iss, ttls_s, net_s=1.0):
    """M_renew = TTL - (renew_p99 + network allowance). Positive = operationally safe."""
    p99_s = iss["renew_p99_ms"] / 1000.0
    return {ttl: round(ttl - (p99_s + net_s), 1) for ttl in ttls_s}


def outage_control_success(ttl_s, grace_s, outages_s):
    """Modeled: fraction of an outage window during which DER control stays available."""
    out = {}
    for D in outages_s:
        out[D] = {"deny": round(min(ttl_s, D) / D, 3),
                  "grace": round(min(ttl_s + grace_s, D) / D, 3),
                  "safe_mode": 1.0}   # available throughout, at degraded scope
    return out


def fleet_renewal_time(iss, fleets):
    T = iss["throughput_per_s"]
    return {n: round(n / T, 2) for n in fleets}


def main():
    iss = measure_issuer()
    ttls = [300, 3600, 21600, 86400]           # 5 min, 1 h, 6 h, 24 h
    margin = renewal_margin(iss, ttls)
    ttl, grace = 3600, 1800                     # 1 h TTL, 30 min grace
    outages = [1800, 3600, 7200, 14400]         # 0.5x, 1x, 2x, 4x TTL
    control = outage_control_success(ttl, grace, outages)
    fleet = fleet_renewal_time(iss, [1000, 10000, 100000])

    print("== Availability (C6/RQ4): renewal MEASURED, outage MODELED ==\n")
    print(f"renewal: median {iss['renew_median_ms']} ms, p99 {iss['renew_p99_ms']} ms, "
          f"throughput {iss['throughput_per_s']}/s (single thread)")
    print(f"renewal safety margin M_renew (s): " +
          ", ".join(f"TTL={t}s -> {m}" for t, m in margin.items()))
    print(f"fleet renewal time (s): " + ", ".join(f"{n}->{v}" for n, v in fleet.items()))
    print(f"\ncontrol-success under outage (TTL={ttl}s, grace={grace}s):")
    print(f"  {'outage':>8} {'deny':>7} {'grace':>7} {'safe_mode':>10}")
    for D, r in control.items():
        print(f"  {D:>8} {r['deny']:>7} {r['grace']:>7} {r['safe_mode']:>10}")

    out = {"renewal_measured": iss, "renewal_margin_s": margin,
           "fleet_renewal_time_s": fleet, "ttl_s": ttl, "grace_s": grace,
           "control_success_modeled": control,
           "note": "Renewal latency/throughput measured on the credential service (single "
                   "thread, workstation). Control-success under outage is modeled from TTL, "
                   "grace, and outage duration for three renewal policies."}
    (Path(__file__).resolve().parent / "results" / "availability.json").write_text(json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/availability.json")


if __name__ == "__main__":
    main()
