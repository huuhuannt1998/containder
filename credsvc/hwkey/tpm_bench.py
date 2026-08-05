#!/usr/bin/env python3
"""TPM 2.0 measurements for CONTAINDER's fresh-key containment claim.

Runs against a software TPM 2.0 (swtpm) driven through the real tpm2-tools command layer, so the
TPM 2.0 *protocol path* is exercised end to end: storage-root derivation, per-epoch key creation,
loading, signing, quote generation, and an explicit non-exportability check.

The root of trust is emulated, so these are protocol-path timings, not silicon timings. What they
establish, and what a pure software path could not, is that the operations the design depends on
exist, compose, and cost what they cost -- and that a key created with the standard restrictions
cannot be duplicated off the TPM, which is the property fresh-key containment actually rests on.

A TPM holds only a few transient object slots, so the storage root is made persistent and
transients are flushed between operations; both are outside the timed regions.
"""
import json, os, statistics, subprocess, sys, tempfile, time

WORK = tempfile.mkdtemp()
STATE = os.path.join(WORK, "tpmstate"); os.makedirs(STATE, exist_ok=True)
ENV = dict(os.environ, TPM2TOOLS_TCTI="swtpm:host=127.0.0.1,port=2321")
SRK = "0x81010001"


def sh(cmd, check=True):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, env=ENV)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r


def flush():
    subprocess.run("tpm2_flushcontext -t", shell=True, capture_output=True, env=ENV)


def timed(fn, n):
    ts = []
    for i in range(n):
        flush()                       # outside the timed region
        t0 = time.perf_counter()
        fn(i)
        ts.append((time.perf_counter() - t0) * 1000.0)
    s = sorted(ts)
    return {"n": n, "median_ms": round(s[len(s)//2], 3), "mean_ms": round(statistics.fmean(s), 3),
            "min_ms": round(s[0], 3), "p95_ms": round(s[min(len(s)-1, int(.95*len(s)))], 3),
            "p99_ms": round(s[min(len(s)-1, int(.99*len(s)))], 3), "max_ms": round(s[-1], 3)}


out = {"platform": "swtpm 2.0 emulator driven through tpm2-tools",
       "scope": "TPM 2.0 protocol path with an emulated root of trust; not silicon timings"}

subprocess.Popen(["swtpm", "socket", "--tpm2", "--server", "type=tcp,port=2321",
                  "--ctrl", "type=tcp,port=2322", "--tpmstate", f"dir={STATE}",
                  "--flags", "not-need-init,startup-clear"],
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(3)
try:
    sh("tpm2_getcap properties-fixed > /dev/null")
    out["tpm_reachable"] = True
except Exception as e:
    out["tpm_reachable"] = False; out["error"] = str(e)[:300]
    print(json.dumps(out, indent=2)); sys.exit(0)

N = 30
# --- persistent storage root, so per-epoch keys do not exhaust transient slots ---------------
sh(f"tpm2_createprimary -C o -g sha256 -G ecc256 -c {WORK}/pri.ctx")
sh(f"tpm2_evictcontrol -C o -c {WORK}/pri.ctx {SRK}", check=False)
flush()
out["srk_persistent_handle"] = SRK

ATTRS = "fixedtpm|fixedparent|sensitivedataorigin|userwithauth|sign"

def create_key(i):
    sh(f"tpm2_create -C {SRK} -g sha256 -G ecc256 -u {WORK}/k.pub -r {WORK}/k.priv -a '{ATTRS}'")

def load_key(i):
    sh(f"tpm2_load -C {SRK} -u {WORK}/k.pub -r {WORK}/k.priv -c {WORK}/k.ctx")

out["key_create"] = timed(create_key, N)
create_key(0)
out["key_load"] = timed(load_key, N)

flush(); create_key(0); load_key(0)
with open(f"{WORK}/msg", "wb") as f:
    f.write(b"containder-operational-credential-request")
out["sign"] = timed(lambda i: sh(f"tpm2_sign -c {WORK}/k.ctx -g sha256 -o {WORK}/sig.raw {WORK}/msg"), N)

# --- attestation key + quote -------------------------------------------------------------------
# Quote requires a restricted signing key. The supported path is the standard EK -> AK flow;
# creating a restricted signer directly under the storage root is rejected by the TPM
# (0x2D6, symmetric algorithm not appropriate). If the AK cannot be created the quote is
# reported as not measured rather than approximated.
flush()
ak_ok = True
try:
    sh(f"tpm2_createek -c {WORK}/ek.ctx -G ecc -u {WORK}/ek.pub")
    sh(f"tpm2_createak -C {WORK}/ek.ctx -c {WORK}/ak.ctx -G ecc -g sha256 -s ecdsa "
       f"-u {WORK}/ak.pub -n {WORK}/ak.name")
except Exception as exc:
    ak_ok = False
    out["quote"] = {"measured": False, "reason": str(exc).splitlines()[-1][:200]}
flush()

if ak_ok:
    out["quote"] = timed(lambda i: sh(
        f"tpm2_quote -c {WORK}/ak.ctx -l sha256:0,1,2,3 -q deadbeef "
        f"-m {WORK}/q.msg -s {WORK}/q.sig -o {WORK}/q.pcr"), N)

# --- non-exportability: the property fresh-key containment rests on --------------------------
# Duplication is gated by BOTH the object attributes and an authorization policy. A naive
# tpm2_duplicate is refused for *any* key because no policy session authorises the command, so it
# cannot distinguish "refused because fixedtpm" from "refused because unauthorised" -- an earlier
# version of this benchmark made exactly that error, and its positive control caught it.
#
# The discriminating test builds a TPM2_CC_Duplicate policy, creates two keys that differ ONLY in
# the fixed attributes, and attempts duplication of each under that policy:
#   key D (duplicable, no fixedtpm/fixedparent) must SUCCEED  -- the positive control
#   key F (fixedtpm|fixedparent, as CONTAINDER requires)  must FAIL
# Only if both hold is the refusal attributable to the attributes.
flush()
sh(f"tpm2_startauthsession -S {WORK}/s.ctx")
sh(f"tpm2_policycommandcode -S {WORK}/s.ctx -L {WORK}/dup.policy TPM2_CC_Duplicate")
sh(f"tpm2_flushcontext {WORK}/s.ctx")

DUP_ATTRS = "sensitivedataorigin|userwithauth|sign"
sh(f"tpm2_create -C {SRK} -g sha256 -G ecc256 -u {WORK}/d.pub -r {WORK}/d.priv "
   f"-L {WORK}/dup.policy -a '{DUP_ATTRS}'")
sh(f"tpm2_create -C {SRK} -g sha256 -G ecc256 -u {WORK}/f.pub -r {WORK}/f.priv "
   f"-L {WORK}/dup.policy -a '{ATTRS}'")

def try_duplicate(pub, priv, tag):
    flush()
    sh(f"tpm2_load -C {SRK} -u {pub} -r {priv} -c {WORK}/{tag}.ctx")
    sh(f"tpm2_startauthsession --policy-session -S {WORK}/ps.ctx")
    sh(f"tpm2_policycommandcode -S {WORK}/ps.ctx TPM2_CC_Duplicate")
    r = sh(f"tpm2_duplicate -C {SRK} -c {WORK}/{tag}.ctx -G null "
           f"-p 'session:{WORK}/ps.ctx' -r {WORK}/{tag}.dup -s {WORK}/{tag}.seed", check=False)
    subprocess.run(f"tpm2_flushcontext {WORK}/ps.ctx", shell=True, capture_output=True, env=ENV)
    err = (r.stderr or "").strip()
    return {"returncode": r.returncode, "exported": r.returncode == 0,
            "stderr_last": err.splitlines()[-1][:200] if err else ""}

dup_res = try_duplicate(f"{WORK}/d.pub", f"{WORK}/d.priv", "d")
fix_res = try_duplicate(f"{WORK}/f.pub", f"{WORK}/f.priv", "f")
discriminates = dup_res["exported"] and not fix_res["exported"]
out["non_exportability"] = {
    "method": "TPM2_CC_Duplicate policy session; two keys differing only in fixed attributes",
    "duplicable_key": {"attributes": DUP_ATTRS, **dup_res},
    "fixed_key": {"attributes": ATTRS, **fix_res},
    "test_discriminates": discriminates,
    "interpretation": (
        "the TPM exported the duplicable key and refused the fixed key, so non-exportability is "
        "attributable to fixedtpm|fixedparent" if discriminates else
        "INCONCLUSIVE: the positive control did not export, so refusal is not attributable to "
        "the attributes")}

# --- end-to-end per-epoch renewal: fresh key + load + quote ------------------------------------
def renewal(i):
    create_key(i); load_key(i)
    if ak_ok:
        sh(f"tpm2_quote -c {WORK}/ak.ctx -l sha256:0,1,2,3 -q cafe "
           f"-m {WORK}/r.msg -s {WORK}/r.sig -o {WORK}/r.pcr")

out["end_to_end_renewal"] = timed(renewal, 15)
out["end_to_end_renewal"]["note"] = ("fresh operational key + load"
    + (" + quote" if ak_ok else " (quote unavailable)") + ", one credential epoch")
print(json.dumps(out, indent=2))
