# M23 R10 — Debian repository trust establishment

**NO-GO for acquisition. Independent repository authenticity remains NOT_ESTABLISHED.** Local-only assessment on 2026-11-18 at HEAD `ec39d8d5f28dbe5e854ce9cba39ae14c40b37e36`. No downloads, installations, builds, vulnerability scans, Docker/VM/cloud operations, privilege escalation, key import, trust-store change or acquired-code execution occurred. [Machine evidence and verification](r10-debian-repository-trust.json) retains exact hashes, scoped host discovery, public-key/signature observations and missing prerequisites. R7–R9 remain unchanged.

## Available key material and provenance

| Material | What local inspection establishes | Trust result |
| --- | --- | --- |
| Host-native verifier/keyring | No gpg/gpg2/gpgv/sq/sqv was found on inspected PATH or inspected common Homebrew/MacPorts/MacGPG2 locations. Standard/common Debian keyring locations were absent. This is scoped discovery, not a claim about every file on the host. | No approved local verifier or independently enrolled Debian keyring established. No personal keyring was imported or modified. |
| Frozen R4 Trixie image | Retained package inventory records `debian-archive-keyring` **2025.1** and Linux AMD64 `sqv` **1.3.0-3+b2**. The frozen filesystem lists 31 public-key/keyring/alias paths; seven selected public-key files were inspected in memory from the existing pinned layer. | Available **candidate material**, not an independently trusted bootstrap. The image's upstream authenticity was never independently established. Its own keyring/verifier cannot authenticate that origin by circular reasoning. The image's sqv was not executed. |
| Aggregate candidate keyring | `/usr/share/keyrings/debian-archive-keyring.pgp`: **55,918 bytes**, SHA-256 `506b815cbb32d9b6066b4a2aa524071e071761e7e7f68c3ac74f3061ba852017`. Structural parsing finds nine primary and six subkey packets. `.gpg` entries are virtual aliases, not host keyring installations. | Packet/fingerprint and archive-digest correspondence only. Self-signatures, subkey bindings, expiry/revocation and authority are NOT_VERIFIED. |
| Retained Debian key page | R6 captured `https://ftp-master.debian.org/keys.html` on 2026-11-17 with TLS verification recorded. Its retained SHA-256 is `b271f4c351a3b54f6a6be9667bb834809d12ee514055b903ccb06839d274e3e0`. It names the same prospective Trixie primary fingerprints. | Corroborating retained metadata, not an enrolled project trust root or independent OpenPGP verification receipt. No new fetch, current-key-status check or approval occurred. |

The selected key bytes match the R4 inventory and existing compressed layer `37fb86c2a767b88d500c6872195f88078f64765fe0d2f9cc375cc2efbd4c0a41`. Only named public-key files were read; no filesystem extraction, key import or verifier execution was performed. **Matching hashes/fingerprints establish consistency and identity references, never authenticity by themselves.**

## Exact retained signature/key requirements

| Repository | Claimed Trixie issuer fingerprint in the retained signature | Candidate primary key fingerprint |
| --- | --- | --- |
| `trixie-security` | `89C87ACEA5DD6B8E6A7068808E9F831205B4BA95` (subkey) | `5E04A1E3223A19A20706E20F9904613D4CCE68C6` |
| `trixie-updates` and `trixie` | `B8E5F13176D2A7A75220028078DBA3BC47EF2265` (subkey) | `04B54C3CDCA79751B16BC6B5225629DF75B188BD` |
| `trixie` stable-release signature | `41587F7DB8C774BCCF131416762F67A0B2C39DE4` | Same primary fingerprint |

These primary/subkey associations come from **unverified packet ordering**, not verified certification. Other retained co-signatures claim issuers `B0CAB9266E8C3929798B3EEEBDE6D2B9216EC7A8` and `4CB50190207B4758A3F73A796ED0E7B82643E131`; matching candidate packets exist in the aggregate bundle. Full packet metadata and candidate-primary associations are in the machine record. No co-signer gains trust automatically.

The three InRelease envelopes contain **seven signature packets** in total (2 security / 2 updates / 3 main), structurally version 4 canonical-text signatures with SHA-256. Public-key algorithm identifiers are RSA (1), plus EdDSA (22) for the stable-release signature. Parsing these fields is **not cryptographic verification**. None of the seven signatures, their signing-key bindings or primary-key authorities was verified.

A valid future chain must establish all of the following without changing trust stores implicitly:

1. **Independent trust anchor.** Authenticated keyring/certificate bytes and primary fingerprint from an already trusted Debian bootstrap or an explicitly approved independent channel, with documented provenance and repository-role authorization. The candidate image, a bare fingerprint copied from a page, or a second file containing the same checksum is insufficient.
2. **Key validity and role.** Cryptographically verify primary/self-certification and signing-subkey binding, signing capability, relevant expiry/revocation status and the authorized suite/role. Record actual primary and signing fingerprints. An issuer field or short key ID is not proof of who signed.
3. **Approved verification result.** Use a trusted, identified host-native verifier with independently established binary provenance, or an authentic source-bound receipt from an independently trusted verifier/host. Bind exact InRelease bytes, verifier/version/hash, keyring/certificate hashes, full signer fingerprints, status output, time and review policy. No improvised metadata parser or newly authored JSON is such a receipt. Required signatures/co-signature handling must follow an independently approved per-repository policy, not inferred quorum rules.
4. **Signed metadata semantics/freshness.** Verify the original clear-signed payload with a conforming verifier, then Origin/Label, Suite/Codename, architecture, Date/Valid-Until and snapshot/rollback policy using a trusted acquisition-time clock. R6 security/updates Valid-Until is 2026-11-24; main has no Valid-Until and needs an explicit approved freshness policy. These dates are untrusted until signature validation, and R10 grants no future freshness PASS.
5. **Package chain.** From the authenticated payload, verify exact compressed Packages/Sources hashes and sizes; bind the zlib package/source/version/architecture/path, dependency closure, **88,720-byte** binary and expected SHA-256 `8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb`. Future downloaded bytes must match before acceptance. A matching package hash under an unauthenticated Release is not repository authentication.

For a detached Release alternative, both original `Release` bytes and corresponding `Release.gpg` signature are required from the same approved snapshot, followed by the same trust/verification checks. No detached pair was evaluated here. Failure of InRelease verification must never trigger an unsigned-Release fallback or an unapproved download.

## Local validation result and exact missing prerequisites

**Established:** frozen layer/key-file integrity; candidate primary fingerprints corresponding to retained page metadata; seven claimed-issuer-to-candidate-key correspondences; unchanged envelope/index/proposal hashes. **Not established:** any independently trusted primary key, verified primary/subkey certification, cryptographically valid Release signature, current revocation/expiry assurance or authenticated package provenance.

Missing inputs are therefore:

- Independently authenticated, role-approved Debian public-key/certificate/keyring material and its provenance/enrolment record, including trusted validity/revocation evidence. Existing candidate bytes are not that record.
- An approved verifier with independently established provenance, or an independently authenticated verification receipt covering the **exact** retained envelope hashes and signer/binding/status details above. No suitable host tool/receipt is established in the inspected scope.
- Actual successful cryptographic verification under that trust policy, plus acquisition-time clock/freshness/rollback checks. Metadata parsing and stored hashes do not satisfy this.
- Separate acquisition approval after the existing R6/R9 prerequisites are met. Complete supported remediation/applicability, a compliant authenticated database and coverage requirements remain unresolved independently of signing trust.

**Decision: NO-GO for separately approved zlib acquisition at this checkpoint.** Trust provisioning or an independent verification receipt requires a separately authorized, reviewable step; no downloads, imports or installations are initiated by R10. [R9's runbook](stage-b2d-r9-zlib-acquisition-preflight.md) remains stopped at its provenance gate. All nine R8 findings remain blocking, R7 remains PENDING_REVIEW, and M23 SECURITY GATE NO-GO/B1 refusal and limits remain unchanged. No historical evidence, source, dependencies, index, commit or push was changed.
