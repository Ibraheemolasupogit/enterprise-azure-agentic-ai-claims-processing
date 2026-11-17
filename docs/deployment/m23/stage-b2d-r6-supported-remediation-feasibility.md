# M23 B2D-R6 — supported remediation feasibility

**Decision: NO-GO for a binary acquisition phase. STOP: no complete supported, authenticated remediation route was established.** The bounded public-metadata investigation completed on **2026-11-17 UTC**. Network requests stopped after the planned batch; no package, image, source archive or vulnerability database payload was acquired. No installations, acquired-code execution, Docker, builds, runtime tests, scanners or Azure operations occurred.

[Machine decision](../../../outputs/deployment/m23-b2d-r6/assessment.json), [corrected repository records](../../../outputs/deployment/m23-b2d-r6/corrected-package-records.json), [partial zlib proposal](../../../outputs/deployment/m23-b2d-r6/zlib-update-proposal.json), [raw responses and endpoint ledger](../../../outputs/deployment/m23-b2d-r6/), and [validation](../../../outputs/deployment/m23-b2d-r6/validation.json) retain the evidence. This is not an approval or a signed acquisition inventory.

## Supported-remediation decision matrix

Current Debian tracker responses and main/security/updates AMD64 binary/source indexes were compared to the verified R4 inventory. Trixie-updates contains no relevant update. The eight unavailable fixes are pending supported Debian integration/release in this evidence; several already have upstream/unstable fixes, so they must not all be labelled "upstream unfixed".

| CVE | Exact R4 installed packages/version | Current supported Trixie evidence | Classification |
| --- | --- | --- | --- |
| CVE-2025-69720 | libncursesw6, libtinfo6, ncurses-base, ncurses-bin **6.5+20250216-2** | Still vendor-vulnerable; no fixed version in the checked supported repositories | PENDING_SUPPORTED_TRIXIE_FIX; infocmp/caller reachability unresolved |
| CVE-2026-119373 | libsqlite3-0 **3.46.1-7+deb13u2** | Still vendor-vulnerable; no supported fixed update established | PENDING_SUPPORTED_TRIXIE_FIX; FTS5 code present |
| CVE-2026-119374 | Same SQLite package/version | Same | PENDING_SUPPORTED_TRIXIE_FIX; corrupted-FTS5/delete path unresolved |
| CVE-2026-119379 | Same SQLite package/version | Same | PENDING_SUPPORTED_TRIXIE_FIX; session APIs present, application invocation unverified |
| CVE-2026-16742 | libsystemd0, libudev1 **257.13-1~deb13u1** | Source remains vendor-vulnerable; no supported fixed update established | PENDING_SUPPORTED_TRIXIE_FIX / DISPUTED_COMPONENT_APPLICABILITY; named systemd-homed absent in R4, no formal disposition |
| CVE-2026-54369 | libacl1 **2.3.2-2+b1** | Source **2.3.2-2** remains vulnerable; planned point-release handling is not a published fix | PENDING_SUPPORTED_TRIXIE_FIX; new ACL APIs/caller compatibility need review |
| CVE-2026-78410 | bsdutils **1:2.41.5-0+deb13u1**; libblkid1, libmount1, libsmartcols1, libuuid1, mount, util-linux **2.41.5-0+deb13u1** | Current security and main package version still vendor-vulnerable | PENDING_SUPPORTED_TRIXIE_FIX; SUID mount present, required fstab configuration absent in base |
| CVE-2026-85091 | zlib1g **1:1.3.dfsg+really1.3.1-1+b1** | Security source/binary **1:1.3.dfsg+really1.3.1-1+deb13u1** listed, tracker fixed | SUPPORTED_REMEDIATION_LISTED / REPOSITORY_AUTHENTICATION_BLOCKED |
| CVE-2026-9538 | perl-base **5.40.1-6+deb13u1** | Still vendor-vulnerable; no supported fixed update established | PENDING_SUPPORTED_TRIXIE_FIX / DISPUTED_COMPONENT_APPLICABILITY; Archive::Tar path absent in R4 |

All nine current CVE responses are retained as raw HTML with response hashes. A Debian "minor", no-dsa or postponed classification does not change B1's inherited High finding gate. Component absence and unverified exploit reachability are not waivers. No suppressions or signed not-affected determinations were created.

Python 3.12 can remain unchanged for the listed zlib update. No evidence establishes that eight other supported updates are currently available. Unstable/forky packages are outside the supported Trixie route; no cross-suite mixing or custom backport is proposed as an accepted solution.

## Signed repository metadata and exact partial update

The following clear-signed InRelease files were retained byte-for-byte over verified TLS:

| Repository | InRelease URL | SHA-256 |
| --- | --- | --- |
| Security | https://security.debian.org/debian-security/dists/trixie-security/InRelease | `04571365972ce858df6d8e69808899bbd3eb2c9888669eaf3d825e79216a3576` |
| Updates | https://deb.debian.org/debian/dists/trixie-updates/InRelease | `72859cf437bc59ec21baebaef3838981a68a5beae8d0adf4bfcc8726d1f4158f` |
| Main | https://deb.debian.org/debian/dists/trixie/InRelease | `0584fba32e13e0ab8285fb16c27adea1ec03a73669c18702821094fd6ca86675` |

Security metadata is dated **2026-11-17 05:44:28 UTC**, valid until **2026-11-24 05:44:28 UTC**. Updates is dated **2026-11-17 08:11:15 UTC**, valid until **2026-11-24 08:11:15 UTC**. Main identifies Debian 13.7, dated September 12, and has no Valid-Until field. Expiry fields were checked, but no independent rollback/latest guarantee is claimed.

For each repository, `main/binary-amd64/Packages.xz` and `main/source/Sources.xz` were fetched as **repository metadata only**, and their actual sizes/SHA-256 values match the InRelease descriptors. Main/security/updates index records, all relevant binary filenames/dependencies/hashes, source versions and source Checksums-Sha256 are retained. No `/pool/` URL was requested.

**Authentication limit:** no host gpg/gpgv/sq/sqv or independently trusted Debian archive keyring is available. Signatures are PRESENT but **NOT_VERIFIED**; hash consistency with an unverified InRelease is not independent repository authentication. No verifier was installed or improvised, and acquired Trixie sqv/gpg tooling was not executed. Debian's TLS-authenticated key page identifies these prospective trust anchors, which still require independent enrolment/verification:

- Trixie archive: `04B54C3CDCA79751B16BC6B5225629DF75B188BD`.
- Trixie security archive: `5E04A1E3223A19A20706E20F9904613D4CCE68C6`.
- Trixie stable release: `41587F7DB8C774BCCF131416762F67A0B2C39DE4`.

Partial zlib binary record (not downloaded):

- Source/binary version: **1:1.3.dfsg+really1.3.1-1+deb13u1**.
- Filename: `pool/updates/main/z/zlib/zlib1g_1.3.dfsg+really1.3.1-1+deb13u1_amd64.deb`.
- URL: `https://security.debian.org/debian-security/` plus that exact filename.
- Bytes: **88,720**; SHA-256 **`8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb`**.
- Depends: **libc6 (>= 2.14)**; no Pre-Depends. R4 already has libc6 **2.41-12+deb13u4**. Its declared dependency is libgcc-s1 **14.2.0-19**, which depends on existing gcc-14-base **14.2.0-19** and libc6 >=2.35. The cycle and equality/minimum constraints are satisfied by the existing baseline; listed zlib conflict/break package names are absent. Thus the metadata-level incremental runtime dependency closure adds **only zlib1g**, conditional on signature authentication. No package solver, installation or maintainer-script/runtime compatibility check ran.

Source metadata also lists the exact `.dsc` (3,271 bytes), `.orig.tar.gz` (1,325,737 bytes) and `.debian.tar.xz` (17,836 bytes) hashes/URLs in the partial proposal. These are references, not downloaded source inputs or permission to build them. The initial capture's control-field parser omitted empty-valued multiline checksum headers; its diagnostic output was preserved, and offline reparsing of the original raw indexes produced the corrected source hashes/dependency records. No network retry or historical overwrite was used to fix this derivation.

The current tracker still supports the broader zlib affected-range interpretation retained in R3. Installed `+b1` is not `+deb13u1`. The old CVE-2026-76844 attribution conflict remains historical unresolved evidence; no CVE is renamed or silently suppressed. The DSA shortcut redirected to a Debian announcement URL, which was recorded but not followed; package-index and tracker evidence are the basis for the partial update.

## Trivy database feasibility

Current official `ghcr.io/aquasecurity/trivy-db:2` metadata resolves to:

- Manifest digest **`sha256:bbf8b6c36b22c693d7fda6ad2cb10603de9ee3784d038fd8d4e2be6b00351a72`**.
- Archive descriptor **140,224,767 compressed bytes**, digest **`sha256:5cec441103dc00cb88dbf99b3f17ffdd8f7edb925414ddcf888be9ee7cd91359`**; creation annotation **2026-11-17T13:08:54Z**.
- No archive/database blob requested. Expanded byte size, internal UpdatedAt, logical completeness and cap compliance remain **NOT_ESTABLISHED**. Manifest creation time is not a verified database update timestamp.

The retained original DB is **1,764,941,824 bytes**, above B1's **1,073,741,824-byte** cap. Current upstream Makefile/workflow at pinned source revision `6748d2315661109443d7b1eb20d616b5f303242a` still compacts before compressing, so another compaction is not assumed to fit. Checked referrer and conventional signature-tag metadata endpoints returned 404; the workflow does not establish independent signed DB provenance. Those checks do not prove that every possible authentication method is absent.

**EVIDENCE_BLOCKED:** no supported, independently authenticated, complete Trivy database proven within the cap is established. A compressed archive under 1 GiB is insufficient. No cap increase, advisory deletion, splitting, waiver, summary substitution, scanner-format change or compaction execution occurred. Full OS/Python/native coverage and the unchanged seven-day freshness check remain mandatory even if size/authenticity are later resolved.

## Feasible coverage sources and remaining authentication work

| Coverage | Sources identified/checked | Evidence still required |
| --- | --- | --- |
| CPython 3.12.16 | Official python/cpython public advisory API over TLS returned **zero records** for the requested page; attempted python.org security page returned 404 | Neither result establishes no CVEs. Obtain the correct PSRT/official advisory history and CVE records, authenticated source-release/patch evidence and exact build-feature/version mapping. No complete CPython target/report exists. |
| Bundled OpenSSL 4.0.3 | Official `openssl-library.org/news/vulnerabilities/` retrieved over verified TLS, with advisory/fix links | Bind advisories to the wheel's exact bundled OpenSSL source/build flags and verify release signatures/provenance. OS libssl3t64 3.5.7 is separate. Supported scanner mapping or independently reviewed offline mapping remains required. |
| Cargo components | RustSec site and advisory-db head metadata captured; head **233155b4025b854c68a4b199c0e32d7fd53291a2** is reported **unsigned** by GitHub | Authenticate the selected advisory snapshot through approved trust/reviewer governance; bind all 156 declarations to Cargo locks/features/target and actual linked code, including build-only/runtime distinctions. No complete advisory DB snapshot was acquired. |
| Other native components | Existing wheel RECORD hashes, R4 ELF inventory, producer SPDX/SLSA and source/version declarations | Complete recursive ELF and statically bundled versions, then authenticate vendor advisories and upstream source/build/notice correspondence. TLS/hash consistency alone does not verify publisher signatures or linkage. Unsupported zero-target scans remain NOT_TESTED. |

These sources are feasible inputs to later authenticated reviews, not completed coverage or replacements for B1's database contract. No missing signatures, reviewer identities, licences or security results were fabricated.

## Bounds, preservation and final boundary

The resolver used an exact URL allowlist, verified TLS, sequential requests, no automatic redirects, 25-second request timeouts, at most **45 requests / 48 MiB aggregate / 16 MiB per response / 600 seconds**. Repository index decompression was bounded to 96 MiB each. Actual capture: **33 requests**, **22,187,813 response-body bytes**, **19.901 seconds**. All binary-looking `.xz` responses were the six descriptor-listed repository indexes, not package/source/image/database archives. Anonymous GHCR token data stayed memory-only; no account/cloud credentials were used. Endpoint records retain response hashes/statuses, failed/404 paths and the unfollowed DSA redirect. Preliminary web searches are visible in conversation and are not falsely represented as locally hashed captures.

Offline validation reverified **2,463 preservation records**, both R3/R4 pins, metadata response hashes, all six index descriptor hashes, the nine advisory classifications, partial zlib dependency constraints, unchanged B1 unconditional refusal, unchanged HEAD `1ca15877360c0b5af44f6c5c09a351c81c790711` and an empty staged diff. Existing uncommitted work remains intact. No application source/dependency/workflow changes or test execution occurred.

**Stop here. No acquisition phase is recommended.** Resume only when a complete supported Trixie fix/component-applicability route exists, repository signatures can be genuinely verified with independently trusted keys/verifier or an authentic independent verification receipt, and an authenticated complete database within the cap plus coverage plan is established. Any later key/tool provisioning, metadata refresh or binary acquisition needs separate explicit authorisation. A partial zlib record is not authority to download it or to alter frozen R4 layers. B1 refusal and all deployment prohibitions remain unchanged.
