#!/usr/bin/env python3
"""Full baseline + ablation sweep on IEEE 8500: capacity-time EXPOSURE = J_V x retained authority.

Physical J_V comes from real OpenDSS power flow per authorization SCOPE (full/reference/narrow);
retained authority BR_auth comes from the pkimodel lifecycle model per BASELINE lifecycle. Their
product is the capacity-time exposure where all six baselines and the mechanism ablations
separate, and it exposes the persistence x scope interaction (H1): broad scope is dangerous only
when persistence is long. Usage: python3 experiments/run_full_sweep.py [n_seeds]
"""
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from power import feeder8500 as f
from pkimodel import Credential, CredType, Policy
from pkimodel.lifecycle_sim import decompose_persistence

P_PV = 12.0
N_PV = 600
# authorized malicious envelope (kW export, kVAr) per authorization scope; oracle = max within scope.
SCOPES = {"full": (P_PV, 0.3 * P_PV), "reference": (0.5 * P_PV, 0.15 * P_PV), "narrow": (0.0, 0.05 * P_PV)}
STATES = {"light_load": 0.30, "normal": 1.00, "heavy_load": 1.50}
# baseline -> (authorization scope, lifecycle regime)
BASELINES = {
    "B1_legacy_full": ("full", "legacy_long"),
    "B2_acl_narrow":  ("narrow", "legacy_long"),
    "B3_ephemeral":   ("full", "ephemeral"),
    "B4_attest_only": ("reference", "attest_long"),
    "B5_containder":  ("narrow", "containder"),
    "B6_safe_mode":   ("narrow", "containder"),
}
# ablations on B5: (scope, lifecycle) -- which mechanism is removed
ABLATIONS = {
    "A2_no_session":   ("narrow", "no_session"),
    "A3_no_command":   ("narrow", "no_command"),
    "A4_no_narrowing": ("full", "containder"),
    "A7_fail_open":    ("narrow", "fail_open"),
}


def br_auth_hours(regime: str) -> float:
    if regime == "legacy_long":
        c = Credential("c", CredType.LEGACY_LONGLIVED, "n", ttl_seconds=None, attestation_gated=False)
        p = Policy(enforce_session=False, enforce_command_cleanup=False, revocation_enabled=False)
    elif regime == "ephemeral":
        c = Credential("c", CredType.OPERATIONAL, "n", ttl_seconds=21600, attestation_gated=False)
        p = Policy(enforce_session=True, enforce_command_cleanup=False, revocation_enabled=False)
    elif regime == "attest_long":
        c = Credential("c", CredType.OPERATIONAL, "n", ttl_seconds=7 * 24 * 3600, attestation_gated=True)
        p = Policy(attestation_detect_prob=0.5, enforce_session=False, enforce_command_cleanup=False)
    elif regime == "containder":
        c = Credential("c", CredType.OPERATIONAL, "n", ttl_seconds=21600, attestation_gated=True)
        p = Policy(attestation_detect_prob=0.5, enforce_session=True, enforce_command_cleanup=True,
                   command_max_duration_seconds=300)
    elif regime == "no_session":
        c = Credential("c", CredType.OPERATIONAL, "n", ttl_seconds=21600, attestation_gated=True)
        p = Policy(attestation_detect_prob=0.5, enforce_session=False, enforce_command_cleanup=True,
                   command_max_duration_seconds=300)
    elif regime == "no_command":
        c = Credential("c", CredType.OPERATIONAL, "n", ttl_seconds=21600, attestation_gated=True)
        p = Policy(attestation_detect_prob=0.5, enforce_session=True, enforce_command_cleanup=False)
    elif regime == "fail_open":  # renewal never denies -> behaves un-gated
        c = Credential("c", CredType.OPERATIONAL, "n", ttl_seconds=21600, attestation_gated=True)
        p = Policy(attestation_detect_prob=0.0, enforce_session=True, enforce_command_cleanup=True,
                   command_max_duration_seconds=300)
    else:
        raise ValueError(regime)
    return decompose_persistence(c, p, seed=1).br_auth_hours


def jv_by_scope(n_seeds):
    f.chdir_feeder()
    acc = {}
    for seed in range(1000, 1000 + n_seeds):
        f.compile_base()
        names = f.place_pv(f.load_buses(), N_PV, seed)
        for st, lm in STATES.items():
            f.set_load_mult(lm)
            f.dispatch(names, 0.0, 0.0); f.solve(); base = f.overvoltage_area()
            for sc, (kw, kvar) in SCOPES.items():
                f.dispatch(names, kw, kvar); f.solve()
                acc.setdefault((sc, st), []).append(f.overvoltage_area() - base)
    return {k: max(0.0, statistics.median(v)) for k, v in acc.items()}


def main():
    n_seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    jvm = jv_by_scope(n_seeds)
    regimes = {r for _, r in list(BASELINES.values()) + list(ABLATIONS.values())}
    ba = {r: br_auth_hours(r) for r in regimes}

    def exposure(scope, state, regime):
        return jvm[(scope, state)] * ba[regime]

    print(f"== IEEE 8500 full sweep: capacity-time exposure = J_V x BR_auth ({n_seeds} seeds) ==\n")
    print(f"{'baseline':16} {'scope':10} {'BR_auth(h)':>11} " +
          " ".join(f"{'exp_' + s:>12}" for s in STATES))
    for b, (sc, rg) in BASELINES.items():
        exps = [exposure(sc, st, rg) for st in STATES]
        print(f"{b:16} {sc:10} {ba[rg]:>11.1f} " + " ".join(f"{e:>12.1f}" for e in exps))

    print("\n-- mechanism ablations on B5 --  (BR_auth = temporal containment; exp = physical, light_load)")
    print(f"{'B5_containder':16} BR_auth={ba['containder']:>9.1f}h  exp_light={exposure('narrow','light_load','containder'):>10.1f}  (reference)")
    for a, (sc, rg) in ABLATIONS.items():
        print(f"{a:16} BR_auth={ba[rg]:>9.1f}h  exp_light={exposure(sc, 'light_load', rg):>10.1f}")
    print("(scope narrowing bounds PHYSICAL exposure; session/command/renewal bound TEMPORAL BR_auth,\n which contains the copied-key / session-theft attacks measured in C2)")

    out = {"jv_by_scope": {f"{k[0]}|{k[1]}": round(v, 4) for k, v in jvm.items()},
           "br_auth_hours": {k: round(v, 2) for k, v in ba.items()},
           "n_seeds": n_seeds,
           "note": "Exposure = median induced overvoltage area (OpenDSS 8500, real) x modeled "
                   "retained authority (pkimodel). Single solver; per-state oracle = max within "
                   "scope for the export attack family; GridLAB-D and constrained HW remain."}
    (Path(__file__).resolve().parent / "results" / "full_sweep.json").write_text(json.dumps(out, indent=2))
    print("\nSaved -> experiments/results/full_sweep.json")


if __name__ == "__main__":
    main()
