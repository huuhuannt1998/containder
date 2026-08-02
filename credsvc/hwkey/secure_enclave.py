"""Hardware-backed operational key via the Apple Secure Enclave, through ctypes.

Why this exists
---------------
The pilot's issuance figures are software-path timings: an ECDSA keypair generated in process
memory and signed by an in-process CA. They establish that the protocol arithmetic is cheap, but
they say nothing about the cost of a key an adversary cannot copy -- and non-exportability is the
property CONTAINDER's fresh-key containment actually rests on. A key sitting in ordinary process
memory is extractable, so "a copied operational key is contained at the next epoch" is only as
strong as the storage underneath it.

This module generates a P-256 keypair *inside the Secure Enclave*, where the private key is
non-exportable by construction, and measures generation and signing latency against a software
keypair on the same machine.

**Scope restriction, stated because it bounds what the manuscript may claim.** This is a
hardware-backed *key* measurement and nothing more. The Secure Enclave provides no TPM-style
quote over a measured boot chain, so none of these numbers support any claim about
attestation-gated issuance on real hardware. The manuscript reports the attestation path as
software-emulated throughout.

The Swift toolchain on the evaluation machine has an SDK/compiler version mismatch that prevents
compiling against Security.framework, so the framework is called directly through ctypes.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import statistics
import time

_CF = ctypes.CDLL(ctypes.util.find_library("CoreFoundation"))
_SEC = ctypes.CDLL(ctypes.util.find_library("Security"))

CFTypeRef = ctypes.c_void_p
CFIndex = ctypes.c_long

_CF.CFStringCreateWithCString.restype = CFTypeRef
_CF.CFStringCreateWithCString.argtypes = [CFTypeRef, ctypes.c_char_p, ctypes.c_uint32]
_CF.CFNumberCreate.restype = CFTypeRef
_CF.CFNumberCreate.argtypes = [CFTypeRef, ctypes.c_int, ctypes.c_void_p]
_CF.CFDictionaryCreateMutable.restype = CFTypeRef
_CF.CFDictionaryCreateMutable.argtypes = [CFTypeRef, CFIndex, ctypes.c_void_p, ctypes.c_void_p]
_CF.CFDictionarySetValue.argtypes = [CFTypeRef, CFTypeRef, CFTypeRef]
_CF.CFDataCreate.restype = CFTypeRef
_CF.CFDataCreate.argtypes = [CFTypeRef, ctypes.c_char_p, CFIndex]
_CF.CFDataGetLength.restype = CFIndex
_CF.CFDataGetLength.argtypes = [CFTypeRef]
_CF.CFRelease.argtypes = [CFTypeRef]
_CF.CFBooleanGetTypeID.restype = ctypes.c_ulong

kCFStringEncodingUTF8 = 0x08000100
kCFNumberIntType = 9

_SEC.SecKeyCreateRandomKey.restype = CFTypeRef
_SEC.SecKeyCreateRandomKey.argtypes = [CFTypeRef, ctypes.POINTER(CFTypeRef)]
_SEC.SecKeyCreateSignature.restype = CFTypeRef
_SEC.SecKeyCreateSignature.argtypes = [CFTypeRef, CFTypeRef, CFTypeRef,
                                       ctypes.POINTER(CFTypeRef)]
_SEC.SecAccessControlCreateWithFlags.restype = CFTypeRef
_SEC.SecAccessControlCreateWithFlags.argtypes = [CFTypeRef, CFTypeRef, ctypes.c_uint32,
                                                 ctypes.POINTER(CFTypeRef)]
_SEC.SecCopyErrorMessageString.restype = CFTypeRef
_SEC.SecCopyErrorMessageString.argtypes = [ctypes.c_int32, ctypes.c_void_p]


def _cfstr(s: str) -> CFTypeRef:
    return _CF.CFStringCreateWithCString(None, s.encode(), kCFStringEncodingUTF8)


def _const(name: str) -> CFTypeRef:
    """Dereference an exported CFStringRef constant from Security.framework."""
    return CFTypeRef.in_dll(_SEC, name)


def _cfbool(v: bool) -> CFTypeRef:
    return CFTypeRef.in_dll(_CF, "kCFBooleanTrue" if v else "kCFBooleanFalse")


def _cfnum(v: int) -> CFTypeRef:
    n = ctypes.c_int(v)
    return _CF.CFNumberCreate(None, kCFNumberIntType, ctypes.byref(n))


def _cfdict(pairs) -> CFTypeRef:
    d = _CF.CFDictionaryCreateMutable(
        None, 0,
        ctypes.c_void_p.in_dll(_CF, "kCFTypeDictionaryKeyCallBacks"),
        ctypes.c_void_p.in_dll(_CF, "kCFTypeDictionaryValueCallBacks"))
    for k, v in pairs:
        _CF.CFDictionarySetValue(d, k, v)
    return d


#: kSecAccessControlPrivateKeyUsage
_PRIVATE_KEY_USAGE = 1 << 30


def _se_attrs():
    access = _SEC.SecAccessControlCreateWithFlags(
        None, _const("kSecAttrAccessibleWhenUnlockedThisDeviceOnly"),
        _PRIVATE_KEY_USAGE, None)
    if not access:
        raise RuntimeError("SecAccessControlCreateWithFlags failed")
    priv = _cfdict([
        (_const("kSecAttrIsPermanent"), _cfbool(False)),
        (_const("kSecAttrAccessControl"), access),
    ])
    return _cfdict([
        (_const("kSecAttrKeyType"), _const("kSecAttrKeyTypeECSECPrimeRandom")),
        (_const("kSecAttrKeySizeInBits"), _cfnum(256)),
        (_const("kSecAttrTokenID"), _const("kSecAttrTokenIDSecureEnclave")),
        (_const("kSecPrivateKeyAttrs"), priv),
    ])


def _stats(label: str, xs) -> dict:
    if not xs:
        return {"op": label, "n": 0}
    s = sorted(xs)
    return {"op": label, "n": len(xs),
            "median_ms": round(s[len(s) // 2], 5),
            "mean_ms": round(statistics.fmean(s), 5),
            "min_ms": round(s[0], 5),
            "p95_ms": round(s[min(len(s) - 1, int(0.95 * len(s)))], 5),
            "p99_ms": round(s[min(len(s) - 1, int(0.99 * len(s)))], 5),
            "max_ms": round(s[-1], 5)}


def benchmark(iterations: int = 100) -> dict:
    """Measure Secure Enclave key generation and signing, with a software comparison."""
    digest = bytes(range(32))
    cfdigest = _CF.CFDataCreate(None, digest, 32)
    algo = _const("kSecKeyAlgorithmECDSASignatureDigestX962SHA256")

    gen_ms, sign_ms, err = [], [], None
    key = None
    try:
        attrs = _se_attrs()
        for _ in range(iterations):
            e = CFTypeRef()
            t0 = time.perf_counter()
            k = _SEC.SecKeyCreateRandomKey(attrs, ctypes.byref(e))
            dt = (time.perf_counter() - t0) * 1000.0
            if not k:
                err = "SecKeyCreateRandomKey returned NULL (no Secure Enclave entitlement?)"
                break
            gen_ms.append(dt)
            if key:
                _CF.CFRelease(key)
            key = k
        if key and not err:
            for _ in range(iterations):
                e = CFTypeRef()
                t0 = time.perf_counter()
                sig = _SEC.SecKeyCreateSignature(key, algo, cfdigest, ctypes.byref(e))
                dt = (time.perf_counter() - t0) * 1000.0
                if not sig:
                    err = "SecKeyCreateSignature returned NULL"
                    break
                sign_ms.append(dt)
                _CF.CFRelease(sig)
    except Exception as exc:                                  # noqa: BLE001
        err = f"{type(exc).__name__}: {exc}"

    # Software comparison on the same machine, same curve, same digest.
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
    from cryptography.hazmat.primitives import hashes

    sw_gen, sw_sign = [], []
    for _ in range(iterations):
        t0 = time.perf_counter()
        ec.generate_private_key(ec.SECP256R1())
        sw_gen.append((time.perf_counter() - t0) * 1000.0)
    sk = ec.generate_private_key(ec.SECP256R1())
    for _ in range(iterations):
        t0 = time.perf_counter()
        sk.sign(digest, ec.ECDSA(Prehashed(hashes.SHA256())))
        sw_sign.append((time.perf_counter() - t0) * 1000.0)

    out = {
        "platform": "Apple Secure Enclave (arm64, M4)",
        "iterations": iterations,
        "scope_restriction":
            "Hardware-backed non-exportable P-256 key only. The Secure Enclave provides no "
            "TPM-style measured-boot quote, so these numbers support no claim about "
            "attestation-gated issuance on hardware; the attestation path remains "
            "software-emulated.",
        "software": [_stats("sw_keygen", sw_gen), _stats("sw_sign", sw_sign)],
        "secure_enclave_available": bool(gen_ms and sign_ms),
    }
    if gen_ms or sign_ms:
        out["secure_enclave"] = [_stats("se_keygen", gen_ms), _stats("se_sign", sign_ms)]
    if err:
        out["secure_enclave_error"] = err
    return out


if __name__ == "__main__":
    import json
    import sys
    print(json.dumps(benchmark(int(sys.argv[1]) if len(sys.argv) > 1 else 100), indent=2))
