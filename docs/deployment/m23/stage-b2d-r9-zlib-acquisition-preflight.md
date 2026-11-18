# M23 R9 — Zlib remediation acquisition preflight

**STOP / NO-GO — trustworthy repository provenance is not established.** Documentation-only preflight on 2026-11-18 at HEAD `ec39d8d5f28dbe5e854ce9cba39ae14c40b37e36`. No download, verifier installation, package execution, Docker/build, scan or cloud operation occurred. R7/R8 and all historical evidence remain unchanged. [Machine preflight and exact input bindings](r9-zlib-acquisition-preflight.json) records this stop; nothing below authorizes acquisition or execution.

## Exact proposed remediation

| Input | Retained R6 value, not newly acquired bytes |
| --- | --- |
| Source / binary / architecture | `zlib` / `zlib1g` / `amd64` |
| Frozen R4 installed version | `1:1.3.dfsg+really1.3.1-1+b1` |
| Proposed security version | **`1:1.3.dfsg+really1.3.1-1+deb13u1`** |
| Package filename | `zlib1g_1.3.dfsg+really1.3.1-1+deb13u1_amd64.deb` |
| Expected bytes | **88,720** |
| Expected SHA-256 | `8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb` |
| Exact URL | `https://security.debian.org/debian-security/pool/updates/main/z/zlib/zlib1g_1.3.dfsg+really1.3.1-1+deb13u1_amd64.deb` |

The retained [CVE-2026-85091 advisory](../../../outputs/deployment/m23-b2d-r6/raw/CVE-2026-85091.html) lists that Trixie security source version as fixed. The flaw concerns stale caller-buffer state after a failed gz* write, followed by a later write; the older installed line also requires the described `gzclearerr()` sequence. This is distinct from MiniZip's CVE-2023-45853. [R8](stage-b2d-r8-high-cve-applicability.md) still records applicability UNKNOWN/blocking; version metadata is not proof that a patch was applied or tested.

[R6's proposal](../../../outputs/deployment/m23-b2d-r6/zlib-update-proposal.json) gives `Depends: libc6 (>= 2.14)`, no Pre-Depends, and only **zlib1g** as an incremental package. Existing libc6 **2.41-12+deb13u4**, libgcc-s1 **14.2.0-19** and gcc-14-base **14.2.0-19** satisfy its declared closure; the listed conflict/break package names are absent in that retained baseline. Python need not change. This is metadata-level closure, not a solver/maintainer-script/runtime result.

## Provenance gate — failed prerequisite

R9 rechecked three retained InRelease envelope hashes and all six compressed Packages/Sources index hashes/sizes against their recorded descriptors. That proves internal byte consistency only. Signatures are present but **NOT_VERIFIED**. No gpg/gpgv/sq/sqv executable was found on the inspected PATH, and retained evidence contains no independently enrolled Debian keyring or authentic independent signature-verification receipt. No acquired image verifier was executed or improvised. **Processing stops at this gate; downstream steps are a conditional runbook, not performed work.**

The exact retained repositories are:

| Repository | Metadata endpoint | Retained expiry information |
| --- | --- | --- |
| Security | `https://security.debian.org/debian-security/dists/trixie-security/InRelease` | Date 2026-11-17 05:44:28 UTC; Valid-Until 2026-11-24 05:44:28 UTC |
| Updates | `https://deb.debian.org/debian/dists/trixie-updates/InRelease` | Date 2026-11-17 08:11:15 UTC; Valid-Until 2026-11-24 08:11:15 UTC |
| Main | `https://deb.debian.org/debian/dists/trixie/InRelease` | Debian 13.7; no Valid-Until. Requires an independently approved snapshot/freshness/rollback policy, not an inferred expiry PASS. |

Before any future GO, an approved existing verifier or independently authenticated verification receipt must bind **actual envelope bytes** to independently trusted, role-appropriate primary keys/subkeys, with valid signatures and reviewed expiry/revocation. R6 records prospective fingerprints `5E04A1E3223A19A20706E20F9904613D4CCE68C6` (security), `04B54C3CDCA79751B16BC6B5225629DF75B188BD` (archive) and `41587F7DB8C774BCCF131416762F67A0B2C39DE4` (stable release). These strings are **not enrolled trust anchors**; a TLS page or key shipped inside the untrusted candidate is not independent enrolment.

Verify origin/label, suite/codename, architecture, signed Date/Valid-Until at the actual acquisition time, approved key role and rollback/latest policy. Use only authenticated signed payloads to bind `main/binary-amd64/Packages.xz` and `main/source/Sources.xz` by exact size/SHA-256. Recheck the exact zlib Package/Source/Version/Architecture/Filename/Depends/Breaks/Conflicts/Size/SHA256 and source-record correspondence. Six exact index descriptors and three envelope hashes are in the machine record. Signed metadata, approved trust and acquisition approval are all required; none substitutes for another.

## Conditional bounded runbook

| Phase | Required actions and limits | GO / NO-GO condition |
| --- | --- | --- |
| **0 — provenance / approval** | Independently establish the trust chain above, bind then-current HEAD/dirty state and an immutable exact one-package inventory. Recheck R6's complete supported-route, compliant database and coverage prerequisites. Obtain explicit bounded binary-acquisition approval with real reviewer authority. | **NO-GO now.** No trusted signature result, no complete R6 route, and no acquisition approval. A zlib-only proposal does not waive the other eight findings or authorize acquisition by itself. Any metadata refresh or key/verifier provisioning needs separate approval. |
| **1 — acquisition only** | After Phase 0 passes, create an exclusive private artifact/receipt directory outside frozen evidence; reject existing paths/aliases. Use only the exact HTTPS URL/host above, no credentials, cookies, proxy fallback, redirects, dependency resolver or alternate mirrors. One active transfer; at most two GET attempts (one retry for transient transport failure only), 30 s per attempt, 5 min overall; total application-read body budget 1 MiB. Stop reading at expected size + 1 byte; accept only exactly 88,720 bytes and the expected hash. Limit each stdout/stderr capture to 64 KiB. | Stop on unexpected host/redirect/status, TLS failure, size/hash mismatch, timeout or budget breach. No retry after integrity/identity failure. Hash/close a new partial file before publishing its receipt; no historical path overwrite. Wire-level protocol overhead is not claimed to be measured by the application body budget. **NOT_AUTHORIZED / NOT_RUN.** |
| **2 — non-executing inspection** | Verify Debian ar/control/data format and exact control fields; inspect maintainer scripts/triggers as data. Bound archive expansion to 8 MiB and 20,000 members; reject traversal, special files and host-followed links. Require existing supported decoders; never install one automatically. Compare payload ownership, modes, SONAME/ELF AMD64, symbol requirements, licences, expected file inventory and declared closure with R4. No package installation, script execution or `.so` loading. | Unknown format, unsupported decoder, unexpected scripts/files/dependencies or missing evidence means stop for review. A hash match alone cannot mark compatibility/fix semantics PASS. Source `.dsc`, orig/debian tarballs are **not** in the one-binary allowlist; any later need requires separate acquisition approval. **NOT_RUN.** |
| **3 — isolated execution / regression** | A separate reviewed new-candidate plan and explicit Linux execution/build/test approvals are required. Use original frozen inputs read-only, a new disposable candidate and independently verified builder/runtime isolation. Never execute the `.deb` on the macOS host or patch R4 layers in place. | **NO-GO / NOT_AUTHORIZED.** B1 unconditionally refuses builds, even with valid signed evidence. This runbook supplies no override or build/install command. Complete security/admission prerequisites and separate builder implementation/execution approval remain required. |

## Compatibility and regression acceptance, after separate approval

Retain CPython **3.12.16**, Linux AMD64 and the exact 39 dependency pins. Verify zlib package/source/patch correspondence and complete installed closure, actual libz.so.1 loading/ABI/symbol compatibility, and absence of additional package or maintainer-script effects. Debian backports may retain an upstream version string: `ZLIB_VERSION`/`ZLIB_RUNTIME_VERSION` alone cannot prove this CVE fixed.

Require bounded gz* write-failure/clearerr/retry regression coverage, including EPIPE on a blocking descriptor, plus normal gzip/zlib round trips and applicable CPython/native-wheel imports. Retain exact test source/inputs/results and actual runtime identities. Preserve startup fail-closed behaviour, synthetic API/UI/MCP boundaries, M20 atomic audit/lost-ack recovery, M21 revoked-duplicate denial and M22 telemetry/redaction controls. No live model, provider or quality scoring is implied.

Then require complete source-aware final-candidate SBOM/CVE coverage, independently approved licences/provenance and the unchanged zero-unresolved-Critical/High gate, authenticated complete database **at most 1 GiB / seven days old**, and separately approved reproducibility/runtime checks. Patching this one CVE would leave eight reviewed High findings and other blockers; no security acceptance follows automatically. **Every check in this section is NOT_TESTED by R9.**

## Rollback, preservation and decision

Keep frozen R3/R4/R6 inventories, all original layers/packages/reports, R7/R8 decisions and M20/M21 historical stores untouched. Bind pre/post hashes, exact input/command/tool/trust records, actual transfer counters, failure categories and reviewer receipts to a new candidate identity. Never relabel an original report, mutate old manifests/anchors, suppress the finding, or fabricate an approval.

On any failure, stop the owned transfer/test process, retain private partial/failure evidence, mark the candidate rejected and keep B1/deployment closed. Any cleanup is limited to the exact newly approved directory after review. Rollback here means **rejecting the new disposable candidate while retaining the frozen baseline as evidence**; it is not permission to deploy an older vulnerable image, downgrade packages in place or repair historical stores. No cloud rollback exists in this offline stage.

**R9 result: NO-GO — provenance not established; stop before acquisition/execution.** Only the new preflight documentation and machine record are produced. M23 SECURITY GATE NO-GO, all nine blocking applicability findings, R7 PENDING_REVIEW and existing B1/deployment/quality restrictions remain unchanged.
