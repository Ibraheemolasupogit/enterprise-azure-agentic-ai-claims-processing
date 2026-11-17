# M23 B2D-R3 — replacement base metadata review

Observed **2026-11-17 UTC**. **CONDITIONAL GO to request separately authorised acquisition of the primary candidate for non-executing inspection only; NO-GO for B1 admission, builds, runtime or Azure.** No binary was downloaded. No scanner result, reviewer identity, approval or signature was created. Existing artifacts, database, thresholds and unconditional build refusal are unchanged.

## Frozen metadata packet

[Machine inventory](r3-replacement-base-metadata.json) and [SHA-256](r3-replacement-base-metadata.sha256):

`c134c3eab5626d3879f460b82642f5fc652802a4dff2514f35c1438669422d96`

The inventory is a metadata selection, not a completed B1 build manifest or acquisition approval. [Raw responses, endpoint ledgers, failed attempts and validation](../../../outputs/deployment/m23-b2d-r3/) remain separately retained. All 1,548 prior B2D evidence files, both frozen inventory pins and all 43 acquired binary hashes/sizes were reverified unchanged. HEAD remains `1ca15877360c0b5af44f6c5c09a351c81c790711`; existing uncommitted work is preserved.

## Official variants and candidates

The pinned official Python versions/catalog metadata lists exactly two Debian slim variants for 3.12: `slim-trixie` and `slim-bookworm`. Both resolve to **CPython 3.12.16 / Linux AMD64**. The official catalog and subject-bound SBOM also identify `3.12-slim` as the Trixie variant; use the platform digest rather than that mutable alias.

| Role | Candidate | Linux AMD64 platform manifest SHA-256 | OS declared by publisher SBOM | Declared glibc |
| --- | --- | --- | --- | --- |
| Primary inspection candidate | `3.12.16-slim-trixie` | `05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177` | Debian 13 / Trixie; `base-files` 13.8+deb13u7 | libc6 2.41-12+deb13u4 |
| Fallback compatibility/reference candidate | `3.12.16-slim-bookworm` | `0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4` | Debian 12 / Bookworm; `base-files` 12.4+deb12u15 | libc6 2.36-9+deb12u14 |

The fallback is **byte-identical to the frozen B2B selection**, not a remediated replacement. No second independently promising remediated official slim candidate was established. Current Debian release pages identify Trixie as 13.7 with full support until August 2028/LTS until June 2030, and Bookworm as superseded, with AMD64 LTS until June 2028. These are current release facts, not measurements of `/etc/os-release` inside an executed candidate. Runtime Python/OS/glibc observations remain NOT_TESTED.

Config SHA-256 values: Trixie `78976a69c067520ef8be34cde307ef9f6fea6dcefa50edb57039773d241ca0db`; Bookworm `313cf8f190a1abab00472c1f0c950c10486c22114bcd8aef2a8198fb587a6d18`.

Both official Dockerfiles, catalog entries and SLSA provenance link to `docker-library/python` revision `3d7e95597e56a415d9e4abc0f15877e005d2cb2e`, respective `3.12/slim-*` directories. Each index/platform manifest/config/attestation descriptor and JSON statement digest/size was checked; SPDX 2.3 and SLSA v0.2 subjects match the selected image. SLSA materials also match the declared Debian base digest. These establish hash/source consistency through TLS-authenticated official endpoints, **not independently verified upstream signatures or truthful build contents**. No signer authentication was fabricated.

## Vendor advisory comparison

All 31 original Critical/High CVE pages and nine relevant source-package pages were captured from Debian Security Tracker with TLS verification. Their exact response hashes and source-package status rows are in the inventory. This is authenticated transport to Debian's service; no detached advisory signature or signed Debian repository metadata was independently verified.

| Component | Frozen Bookworm | Trixie publisher SBOM | Vendor evidence relevant to original findings |
| --- | --- | --- | --- |
| SQLite | 3.40.1-2+deb12u2 | 3.46.1-7+deb13u2 | Trixie fixed for Critical CVE-2025-7458 and High CVE-2026-11822/11824. Still vulnerable for CVE-2026-119373/119374/119379. Backports, not upstream version-number assumptions, underpin the fixed statuses. |
| zlib | 1:1.2.13.dfsg-1 | 1:1.3.dfsg+really1.3.1-1+b1 | Trixie source marked fixed for Critical CVE-2023-45853. Still vulnerable for High CVE-2026-85091; Debian security fix is `1:1.3.dfsg+really1.3.1-1+deb13u1`, absent from this SBOM. |
| util-linux family | 2.38.1-5+deb12u3 | 2.41.5-0+deb13u1 | Fixed for High CVE-2026-53613/53615; still vulnerable for CVE-2026-78410. Mount API, `/proc`, privilege and fstab conditions still require review. |
| gzip | 1.12-1 | 1.13-1+deb13u1 | Fixed for High CVE-2026-41992. |
| ncurses | 6.4-4 | 6.5+20250216-2 | Still vulnerable for High CVE-2025-69720. |
| systemd libraries | 252.39-1~deb12u2 | 257.13-1~deb13u1 | Source still vulnerable for High CVE-2026-16742; actual systemd-homed inclusion/reachability requires qualification. |
| ACL | 2.3.1-3 | 2.3.2-2+b1 | Source still vulnerable for High CVE-2026-54369. |
| perl-base | 5.36.0-7+deb12u4 | 5.40.1-6+deb13u1 | Source still vulnerable for High CVE-2026-9538; Archive::Tar inclusion remains a component-specific question. |
| Kerberos | Four affected binary packages 1.20.1-2+deb12u5 | No krb5-named component in publisher SBOM | Potential removal of the component association for 14 original High IDs. Absence is a publisher declaration, pending independent layer/native inspection; Trixie's available krb5 package is itself vendor-marked vulnerable for those IDs. |

Two material advisory corrections must be independently reconciled without rewriting historical evidence:

- Current Debian CVE-2026-76844 concerns **webpack-dev-middleware**, not zlib. This conflicts with the frozen scanner description. It is not counted as a proven remediation or silently suppressed.
- Current CVE-2026-85091 describes affected zlib 1.2.11–1.3.2, resolving the earlier description's narrow-range contradiction in favour of continuing investigation. The candidate lacks the listed Debian security update.
- Debian's CVE-2023-45853 notes explicitly state that older Bookworm zlib does not build the vulnerable MiniZip contribution. This strengthens the R1 component-applicability challenge but is not a project risk acceptance or scanner suppression.

The metadata supports potential resolution of **two original Critical and five High IDs**, plus potential Kerberos removal. **Nine original High IDs** remain vendor-vulnerable for present declared package families; the tenth unresolved comparison is the CVE-2026-76844 identity conflict. These are comparisons against the historical set, **not a new image scan or a complete current CVE count**. CPython, bundled OpenSSL/Cargo/native components, base pip 25.0.1 and new OS findings still need assessment. The unchanged dependency wheels can retain issues independently of the OS choice.

## Vulnerability database investigation

Official `ghcr.io/aquasecurity/trivy-db:2` manifest:

- Digest `sha256:28c258aa558d97b8a9aa6afdc452747dcd41ddea7fda6367fd4735296f284b59`.
- Manifest creation annotation `2026-11-17T07:07:29Z` (not independently observed DB UpdatedAt).
- Declares one `db.tar.gz` layer: **140,196,293 compressed bytes**, digest `sha256:e759b1b3171c69fffe995d047d8385662298573dcc2c8d3fe64b6dead8b69d4f`.
- **No database/archive bytes fetched. Expanded database size and advisory completeness cannot be established from this descriptor.**

The pinned upstream source revision `6748d2315661109443d7b1eb20d616b5f303242a` documents compaction. Its Makefile uses bbolt compact and preserves metadata; the publishing workflow already invokes compaction before compression. Therefore an additional compaction must not be assumed to solve the cap. No compaction was executed.

OCI referrer and conventional Cosign signature-tag checks both returned 404. The checked publishing workflow does not establish an independently verified DB signature. A 404 does not prove that no authentication method exists elsewhere. Trivy binary signature documentation does not by itself authenticate its database. Registry TLS and descriptor digests are retained, but independent publisher authentication remains unresolved.

The retained database is **1,764,941,824 bytes**, exceeding B1's **1,073,741,824-byte** cap. No authenticated, complete replacement proven within that cap was found. The new archive's compressed size is not a compliant substitute for expanded DB bytes. Splitting, deleting advisories, changing thresholds or substituting a summary remains prohibited. A separately reviewed, complete, supported smaller DB or proven lossless compaction may be investigated; freshness and OS/Python/native coverage remain mandatory. Other database formats/scanners would require separate compatibility and coverage assessment, not a drop-in claim.

## Capture bounds and limitations

Capture helpers used HTTPS with OS trust roots, no user credentials, no Docker or Azure, no automatic redirects, sequential requests, 25-second per-request timeout, a maximum 4 MiB metadata response and 20 MiB per-run response budget. Image blobs were admitted only as descriptor-bound JSON config/SPDX/SLSA metadata, never filesystem layers. Final aggregate capture: **115 ledger entries**, **6,194,951 response bytes**, statuses **98 HTTP 200 / 12 HTTP 307 / 3 errors / 2 HTTP 404**. Failed attempts remain preserved, including sandbox DNS failure, a redirect-guard refusal and metadata size refusals before reading oversized JSON bodies. R3's metadata response bound is unrelated to B1's unchanged database cap.

Contacted ledger hosts: `api.github.com`, `raw.githubusercontent.com`, `auth.docker.io`, `registry-1.docker.io`, `production.cloudfront.docker.com`, `ghcr.io`, `security-tracker.debian.org`, `www.debian.org`, `trivy.dev`. Docker's 307 redirects were admitted only to digest-bound JSON paths on its CDN; bearer tokens were not forwarded. Anonymous token bodies and signed redirect query values were not retained. No user/account/cloud credentials were used. An initial successful bounded curl probe of official Python versions.json preceded capture; its raw response/hash was not retained. Additional web-search requests are visible in conversation but are not represented as locally hashed captures.

## Recommendation and exact next approval boundary

**Primary:** acquire only the four declared Linux AMD64 Trixie filesystem layers for `docker.io/library/python@sha256:05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177`, **43,268,722 compressed bytes total**, into a new isolated directory, under a separately authorised bounded acquisition/hash/static-inspection stage. The exact layer digests, sizes and metadata are frozen in the inventory; registry blob URLs are derived from those digests. Reuse/reverify the existing 39 wheels rather than replacing their pins. A changed tag is not authority to substitute another digest.

**Fallback:** preserve Bookworm as compatibility/control evidence; defer selection of a remediated Bookworm replacement until a genuinely new official digest and sufficient vendor fixes are established. Do not reacquire identical frozen layers or describe this fallback as a security pass.

The next approval may authorise new Trixie layer acquisition and static verification only, with maximum two transfers, 128 MiB total response-body budget, 64 MiB per layer, one retry per artifact, a 30-minute deadline, approved registry/CDN digest paths, no account credentials, and immediate stop on unexpected redirects/digests/sizes. No build, import, installation or runtime execution. DB acquisition/authentication needs a separately explicit proposal; it is not included in the four-layer boundary.

After acquisition: compare actual package/rootfs/native contents to publisher SBOM, verify licences and provenance, run complete offline scans with admissible authenticated fresh DB evidence, resolve all remaining Critical/High findings, obtain independent reviewer enrolment/signatures, and separately approve physical builder isolation and runtime testing. None of these future steps is marked complete. B1 refusal and all deployment prohibitions remain intact.
