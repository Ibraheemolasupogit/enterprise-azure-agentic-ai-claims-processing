# M23 — Security remediation blocked-state handoff

**M23 SECURITY GATE NO-GO. Acquisition remains blocked.** Consolidated 2026-11-18 at HEAD `ec39d8d5f28dbe5e854ce9cba39ae14c40b37e36` from retained R6–R10 decisions only. This handoff starts no new assessment phase and accepts no remediation, trust anchor, licence approval or non-applicability disposition. [Source bindings and preservation checks](security-remediation-blocked-handoff.json).

## Unresolved High findings

All nine retain **UNKNOWN applicability / PENDING_REVIEW / BLOCKING** under [R8's individual assessments](stage-b2d-r8-high-cve-applicability.md). Component/path observations are not approved non-applicability decisions; no new vulnerability scan or exploit-path result exists.

| CVE | Frozen Trixie package/version |
| --- | --- |
| CVE-2025-69720 | ncurses family **6.5+20250216-2** |
| CVE-2026-119373 | libsqlite3-0 **3.46.1-7+deb13u2** |
| CVE-2026-119374 | libsqlite3-0 **3.46.1-7+deb13u2** |
| CVE-2026-119379 | libsqlite3-0 **3.46.1-7+deb13u2** |
| CVE-2026-16742 | libsystemd0/libudev1 **257.13-1~deb13u1** |
| CVE-2026-54369 | libacl1 **2.3.2-2+b1** |
| CVE-2026-78410 | util-linux family **2.41.5-0+deb13u1**; bsdutils epoch **1:** |
| CVE-2026-85091 | zlib1g **1:1.3.dfsg+really1.3.1-1+b1** |
| CVE-2026-9538 | perl-base **5.40.1-6+deb13u1** |

R6 established no supported Trixie fixed version for eight of these IDs. The historical CVE-2026-76844 attribution discrepancy remains separate and unresolved. Original Bookworm findings and all later static comparisons remain intact.

## Zlib proposal and trust stop

The **2026-11-17 retained metadata** identifies `zlib1g=1:1.3.dfsg+really1.3.1-1+deb13u1` (AMD64) for CVE-2026-85091. Exact binary: `zlib1g_1.3.dfsg+really1.3.1-1+deb13u1_amd64.deb`, **88,720 bytes**, expected SHA-256 `8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb`. [R6 proposal](../../../outputs/deployment/m23-b2d-r6/zlib-update-proposal.json) and [R9 runbook](stage-b2d-r9-zlib-acquisition-preflight.md) retain the exact URL/dependency closure. Only zlib1g is incrementally listed; Python 3.12 need not change. **Not acquired, installed or tested; current availability and repository authenticity are not established.**

[R10](stage-b2d-r10-debian-repository-trust.md) found candidate key bytes in the same unverified image (`debian-archive-keyring` 2025.1), with seven claimed-signature/key correspondences. **Zero signatures or primary/subkey certifications were cryptographically verified; zero independently trusted primaries were established.** No approved host verifier, independently enrolled keyring or authentic independent verification receipt is established. The image's own keyring cannot independently authenticate its origin. A matching checksum, fingerprint, issuer field or retained TLS-page statement is not signing-chain authenticity.

## Reopening acquisition — all prerequisites required

1. **Independent key provenance:** supply authenticated, role-approved Debian primary/certificate/keyring material, its independent provenance/enrolment record and trusted validity/revocation evidence. Bind actual signing subkeys to approved primaries cryptographically; candidate key bytes or names alone are insufficient.
2. **Real signature verification:** establish an approved verifier with independently evidenced provenance, or an authentic independent receipt from a trusted verification host. Bind exact InRelease bytes/hashes, keyring hash, full primary/signing fingerprints, verified certifications/signatures, status output, verifier/version, time and per-repository/co-signer policy. A self-authored verification JSON is not that receipt.
3. **Freshness and rollback verification:** validate signed origin/label, suite/codename, architecture, Date/Valid-Until at the actual acquisition time using a trusted clock. Retained security/updates metadata expires **2026-11-24**; this is not a future freshness approval. Main has no Valid-Until and needs an explicit independently approved snapshot/freshness/rollback policy. Do not fall back to unsigned metadata or an unapproved older snapshot.
4. **Authenticated package chain:** verify the relevant signed Packages/Sources descriptors, exact compressed hashes/sizes, source/binary version/architecture/path/dependency records, then actual acquired bytes against the expected package size/hash. Recheck current availability only under separate authorization; there is no automatic mirror/redirect/version substitution.
5. **Existing R6 security prerequisites:** establish a complete supported remediation/applicability route for the other eight findings, a complete authenticated compatible vulnerability database within **1 GiB** and **seven days** at admission, and the required source-aware CPython/bundled OpenSSL/Cargo/native coverage plan. Complete provenance/licence/reviewer requirements remain. A partial zlib proposal does not waive these conditions; actual zero-unresolved-Critical/High acceptance remains a later gate.
6. **Separate bounded acquisition approval:** review the exact inventory, trusted evidence and R9 limits; obtain genuine explicit approval before any download, verifier/key provisioning or metadata refresh. Use fresh exclusive private paths and preserve all frozen bytes/failures. Approval to acquire would not authorize installation, scans, builds, runtime tests or deployment. B1 still unconditionally refuses builds; further implementation/execution needs separate approval.

## Retained evidence and unchanged decisions

- [R6](stage-b2d-r6-supported-remediation-feasibility.md): no complete supported/authenticated route; one partial zlib listing.
- [R7](stage-b2d-r7-agent-framework-licence.md): proposed MIT mapping remains **PENDING_REVIEW / NOASSERTION**; omission cause UNKNOWN, not licence approval.
- [R8](stage-b2d-r8-high-cve-applicability.md): all nine applicability decisions remain UNKNOWN and blocking.
- [R9](stage-b2d-r9-zlib-acquisition-preflight.md): stopped at provenance; conditional runbook, not acquisition authority.
- [R10](stage-b2d-r10-debian-repository-trust.md): candidate key material exists, independent trust/cryptographic verification does not.

**M23 remains DEFERRED — SECURITY GATE NO-GO**, under the existing [deferral/reopening record](../../milestones/milestone-23.md). Zero-unresolved-Critical/High requirements, database cap/freshness, B1 refusal and disabled deployment gates are unchanged. No historical result or evidence is replaced by this handoff.

**M24 remains OFFLINE DOCUMENTATION COMPLETE / EXECUTION BLOCKED / DEPLOYMENT NO-GO**, with all six demonstrations NOT_TESTED under its [consolidated decision](../../milestones/milestone-24.md). No isolation implementation or demonstration is initiated.

Only this handoff and its source-binding JSON are new. No downloads, installations, builds, scanners, runtime/deployment/application changes, trust-store changes, staging, commits or pushes occurred. **Stop here; no further assessment or acquisition phase is started.**
