// Hardware-backed operational key benchmark (Apple Secure Enclave).
//
// Why this exists
// ---------------
// The pilot's issuance figures are software-path timings on a workstation: an ECDSA keypair in
// OpenSSL, signed by an in-process CA. They establish that the protocol arithmetic is cheap,
// but they say nothing about the cost of a key the attacker cannot copy, which is the property
// CONTAINDER's fresh-key containment actually depends on. A key held in ordinary process memory
// is extractable, so "a copied operational key is contained at the next epoch" is only as strong
// as the storage.
//
// This tool generates a P-256 keypair *inside the Secure Enclave*, where the private key is
// non-exportable by construction, and measures generation and signing latency. It is a
// hardware-backed **key** measurement. It is deliberately NOT an attestation measurement: the
// Secure Enclave gives no TPM-style quote over a measured boot chain, so nothing here supports a
// claim about attestation-gated issuance on real hardware. The manuscript reports it under that
// restriction.
//
// Build:  swiftc -O -o sekey sekey.swift -framework Security -framework CryptoKit
// Run:    ./sekey <iterations>

import Foundation
import Security
import CryptoKit

func nowMs() -> Double { Double(DispatchTime.now().uptimeNanoseconds) / 1_000_000.0 }

func percentile(_ xs: [Double], _ p: Double) -> Double {
    if xs.isEmpty { return 0 }
    let s = xs.sorted()
    let i = min(s.count - 1, max(0, Int((p / 100.0) * Double(s.count - 1).rounded())))
    return s[i]
}

func stats(_ label: String, _ xs: [Double]) -> [String: Any] {
    let s = xs.sorted()
    return ["op": label,
            "n": xs.count,
            "median_ms": s.isEmpty ? 0 : s[s.count / 2],
            "mean_ms": xs.isEmpty ? 0 : xs.reduce(0, +) / Double(xs.count),
            "min_ms": s.first ?? 0,
            "p95_ms": percentile(xs, 95),
            "p99_ms": percentile(xs, 99),
            "max_ms": s.last ?? 0]
}

let iterations = CommandLine.arguments.count > 1 ? Int(CommandLine.arguments[1]) ?? 200 : 200
let digest = Data((0..<32).map { _ in UInt8.random(in: 0...255) })

// --- Secure Enclave path -------------------------------------------------------------------
var genMs: [Double] = []
var signMs: [Double] = []
var seError: String? = nil

// Non-permanent keys avoid needing a keychain access group / signed entitlement, which a plain
// command-line tool does not have. The key still lives in the Secure Enclave.
guard let access = SecAccessControlCreateWithFlags(
    kCFAllocatorDefault,
    kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
    [.privateKeyUsage],
    nil) else {
    print("{\"error\":\"SecAccessControlCreateWithFlags failed\"}")
    exit(1)
}

let attrs: [String: Any] = [
    kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
    kSecAttrKeySizeInBits as String: 256,
    kSecAttrTokenID as String: kSecAttrTokenIDSecureEnclave,
    kSecPrivateKeyAttrs as String: [
        kSecAttrIsPermanent as String: false,
        kSecAttrAccessControl as String: access,
    ],
]

var lastKey: SecKey? = nil
for _ in 0..<iterations {
    var err: Unmanaged<CFError>?
    let t0 = nowMs()
    guard let key = SecKeyCreateRandomKey(attrs as CFDictionary, &err) else {
        seError = (err?.takeRetainedValue() as Error?)?.localizedDescription ?? "unknown"
        break
    }
    genMs.append(nowMs() - t0)
    lastKey = key
}

if let key = lastKey, seError == nil {
    for _ in 0..<iterations {
        var err: Unmanaged<CFError>?
        let t0 = nowMs()
        let sig = SecKeyCreateSignature(key, .ecdsaSignatureDigestX962SHA256,
                                        digest as CFData, &err)
        if sig == nil {
            seError = (err?.takeRetainedValue() as Error?)?.localizedDescription ?? "sign failed"
            break
        }
        signMs.append(nowMs() - t0)
    }
}

// --- Software comparison on the same machine ------------------------------------------------
var swGenMs: [Double] = []
var swSignMs: [Double] = []
for _ in 0..<iterations {
    let t0 = nowMs()
    _ = P256.Signing.PrivateKey()
    swGenMs.append(nowMs() - t0)
}
let swKey = P256.Signing.PrivateKey()
for _ in 0..<iterations {
    let t0 = nowMs()
    _ = try? swKey.signature(for: digest)
    swSignMs.append(nowMs() - t0)
}

var out: [String: Any] = [
    "platform": "Apple Secure Enclave (arm64)",
    "iterations": iterations,
    "note": "Hardware-backed non-exportable P-256 key. NOT an attestation quote: the Secure "
          + "Enclave provides no TPM-style measured-boot quote, so no claim about "
          + "attestation-gated issuance on hardware is supported by these numbers.",
    "software": [stats("sw_keygen", swGenMs), stats("sw_sign", swSignMs)],
]
if let e = seError, genMs.isEmpty {
    out["secure_enclave_available"] = false
    out["secure_enclave_error"] = e
} else {
    out["secure_enclave_available"] = true
    out["secure_enclave"] = [stats("se_keygen", genMs), stats("se_sign", signMs)]
    if let e = seError { out["secure_enclave_partial_error"] = e }
}

let data = try! JSONSerialization.data(withJSONObject: out, options: [.prettyPrinted, .sortedKeys])
print(String(data: data, encoding: .utf8)!)
