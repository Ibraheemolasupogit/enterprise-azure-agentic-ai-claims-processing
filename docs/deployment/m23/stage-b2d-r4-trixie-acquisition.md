# M23 B2D-R4 — Trixie base acquisition and static verification

**Four layers acquired and verified. NO-GO for security acceptance, B1 admission, builds, runtime or Azure.** This stage establishes byte integrity and static contents, not a new vulnerability scan, working Linux runtime or independent approval.

[Exact artifact inventory](r4-trixie-artifact-inventory.json), [inventory hash](r4-trixie-artifact-inventory.sha256), and [receipts/inspection/validation](../../../outputs/deployment/m23-b2d-r4/) retain the new evidence. All earlier artifacts and reports remain intact. HEAD is `1ca15877360c0b5af44f6c5c09a351c81c790711`; no staging, commits or pushes.

## Authorised inputs and integrity

Preflight verified the exact R3 packet SHA-256 **`c134c3eab5626d3879f460b82642f5fc652802a4dff2514f35c1438669422d96`**, Linux AMD64 platform manifest SHA-256 **`05a994d2344eb364cc186910f4fc8786a38215f39f00d0acc25bff33a08f4177`**, selected descriptors and exactly four filesystem layers. No mutable tag was re-resolved.

New private directory: `artifacts/m23-b2d-r4-_p7rg8ny` (0700); verified layer files are 0444. The directory from the earlier sandbox DNS failure is preserved, empty of downloaded layers; no historical directory was reused.

| Compressed layer SHA-256 | Exact bytes | Result |
| --- | ---: | --- |
| `37fb86c2a767b88d500c6872195f88078f64765fe0d2f9cc375cc2efbd4c0a41` | 29,856,132 | MATCH |
| `68bced9e0afa4479df17c3646e27c7c7e9ce9ba70c0e6c73b6826487b89037d9` | 1,289,792 | MATCH |
| `2dc99d2d0a39fce31e37615eb4c932e16dcc4c2b0ce9993714280081b5dbe085` | 12,122,550 | MATCH |
| `05e0eee5572e9c9f50408a2132590133b830a668a1cf2ff2b150f19c57707e2b` | 248 | MATCH |
| **Total** | **43,268,722** | **4/4 verified** |

All four uncompressed layer hashes also match the original config's rootfs diff IDs. No hash/size/host mismatch occurred. Successful acquisition used one transfer at a time, one attempt per layer, nine HTTP requests and **43,274,211 response-body bytes**, including the memory-only anonymous token response. Acquisition took 8.319 seconds after repeated preflight; the original 30-minute deadline was retained across the sandbox DNS retry. Limits stayed at two concurrent transfers maximum, 128 MiB total, 64 MiB per layer and one retry per layer. No layer retry was needed.

Only `auth.docker.io`, `registry-1.docker.io` and `production.cloudfront.docker.com` were contacted. Registry 307 redirects were checked against the exact digest path and signed-query parameter names. No automatic or second redirect, credential forwarding to CDN, registry tag lookup, database request, user credential or Azure operation occurred. Tokens and signed query values were not retained.

## Static contents and baseline comparison

Gzip/tar streams were read as data, with bounded member/file/expanded capacities. No root filesystem was extracted or executed. Whiteout-aware in-memory inventory contains **5,573 paths**; selected metadata and licence text files are retained in the new evidence directory only. Symlinks/hardlinks were resolved against that virtual inventory, never followed into the host filesystem.

Actual archived `/etc/os-release` declares **Debian 13 (Trixie), DEBIAN_VERSION_FULL=13.7**. Archived CPython `patchlevel.h` declares **3.12.16**, matching config/source metadata. Runtime observations remain NOT_TESTED.

There are **87 dpkg-installed packages**, versus **105** in Bookworm: 31 removed package names and 13 added (including ABI-transition replacements). All 87 installed names/versions match the R3 publisher SPDX inventory. Its 35 additional Debian records correspond to actual source-package mappings/versions; they are not 35 extra installed binaries. Detailed additions/removals/changes are retained.

| Component | Bookworm baseline | Actual acquired Trixie |
| --- | --- | --- |
| libc6 | 2.36-9+deb12u14 | 2.41-12+deb13u4 |
| libsqlite3-0 | 3.40.1-2+deb12u2 | 3.46.1-7+deb13u2 |
| zlib1g | 1:1.2.13.dfsg-1 | 1:1.3.dfsg+really1.3.1-1+b1 |
| util-linux / mount | 2.38.1-5+deb12u3 | 2.41.5-0+deb13u1 |
| gzip | 1.12-1 | 1.13-1+deb13u1 |
| libncursesw6 | 6.4-4 | 6.5+20250216-2 |
| libsystemd0 | 252.39-1~deb12u2 | 257.13-1~deb13u1 |
| libacl1 | 2.3.1-3 | 2.3.2-2+b1 |
| perl-base | 5.36.0-7+deb12u4 | 5.40.1-6+deb13u1 |
| OS OpenSSL library | libssl3 3.0.22-1~deb12u2 | libssl3t64 3.5.7-1~deb13u3 |
| Kerberos binaries | Four installed affected packages | Absent from dpkg inventory and named filesystem paths |

All **2,653 publisher SPDX file records match actual SHA-256 bytes**: 2,605 direct paths and 48 paths reconstructed from Docker Scout's base64 JSON `virtual_path` annotations (e.g. colon/architecture-qualified dpkg filenames). The original conservative direct-path result and explanatory addendum are both preserved. No remaining package/version/file-checksum discrepancy was found in this checked scope; the publisher SBOM is not claimed to inventory every native/static component completely.

## ELF dependencies and permissions

Static section/program-header analysis covers **745 final ELF executables/shared files**, all parsed as ELF64 little-endian AMD64. A further CPython `python.o` produced a program-header diagnostic: independent header inspection confirms valid ET_REL/AMD64 with zero program headers, a parser limitation for a relocatable build object rather than evidence of a corrupt runtime executable. No acquired code or loader (`ldd` included) was run.

- CPython `_sqlite3` links to the installed `libsqlite3.so.0`. SQLite exports FTS5/session APIs and contains ENABLE_FTS5/ENABLE_SESSION strings. Function presence does not prove whether a vulnerability's implementation is patched or reachable.
- Main libz exports gzwrite/gzprintf/gzvprintf/gzclearerr; no selected MiniZip export or named MiniZip/pyminizip path was found. No named Kerberos/KDC/kadmind/systemd-homed/Archive::Tar path was found. Hidden/static bundling is not excluded by path absence.
- All seven existing native-wheel ELF payloads were read without import. Each DT_NEEDED name has a static base-library candidate; their previously verified CPython ABI/glibc floors remain compatible with the declared target. This is not full loader/symbol-version, dlopen/plugin or import verification.
- The optional CPython `_tkinter` extension has **no static candidates for libtcl8.6.so/libtk8.6.so**. This is a real runtime-readiness limitation of that extension. The existing application smoke scope does not demonstrate Tk use; no dependency was added and no functionality was claimed working.
- No parsed ELF requests an executable stack. GNU RELRO/stack observations are retained per file and do not establish complete exploit mitigation.
- **Eight SUID and three SGID executables** remain, including SUID mount/umount/su; `var/mail` is an additional SGID directory. Three world-writable directories (`run/lock`, `tmp`, `var/tmp`) have sticky bit 1777. No files are owned by UID10001 or group-writable by GID10001.
- The base config has no non-root USER. The unchanged application Dockerfile specifies USER10001:10001, but its effective final-image configuration is NOT_TESTED. Retain read-only root, dropped capabilities/no-new-privileges and bounded writable volumes in any future authorised runtime. These controls do not waive CVEs. Base fstab remains unconfigured.

## Licences and provenance

Copyright/notice mappings are available for **87/87 installed Debian packages**, with 23 common licence files and CPython/bootstrap notices retained. Availability is not licence approval. SQLite's notice distinguishes public-domain core from GPL-2+ Debian packaging; zlib uses Zlib, OS OpenSSL includes Apache-2.0 plus component-specific notices, and glibc has mixed LGPL/GPL/other terms. Publisher aggregate licence expressions are not sufficient to conclude that every file has the same obligations. Bundled wheel/Cargo/OpenSSL and project-distribution review remains pending.

Layer/config/SBOM/provenance hash consistency is verified. Independent upstream signature/authenticity, full source/build correspondence and genuine reviewer enrolment/signatures remain NOT_VERIFIED/PENDING. Acquisition did not repair these gaps.

## Outstanding vulnerability evidence

No network advisory refresh, scanner/database download or new vulnerability scan occurred. The comparison uses the frozen R3 vendor pages, not fabricated current CVE totals:

- Actual package versions correspond to R3 vendor-fixed statuses for both original Critical IDs (CVE-2025-7458/CVE-2023-45853) and five High IDs (CVE-2026-11822/11824/41992/53613/53615). No exploit/patch-specific runtime tests were performed.
- Nine original High IDs remain vendor-vulnerable for installed source families: **CVE-2025-69720; CVE-2026-119373, -119374, -119379; CVE-2026-16742; CVE-2026-54369; CVE-2026-78410; CVE-2026-85091; CVE-2026-9538**. Presence of a source family is not demonstrated exploit reachability; absent named subcomponents require real applicability review.
- In particular, zlib lacks R3's listed security version **1:1.3.dfsg+really1.3.1-1+deb13u1**. Do not label the acquired image fully patched.
- Four Kerberos binary packages underlying 14 original High IDs are removed. No current suppression or formal risk disposition is created; complete native coverage remains incomplete.
- The historical CVE-2026-76844 zlib association conflicts with R3's live vendor record naming webpack-dev-middleware. Preserve both and reconcile independently.
- New Trixie findings have not been scanned. CPython, base pip, bundled OpenSSL 4.0.3, Cargo linkage and other native coverage remain incomplete. Changing the OS does not fix software bundled in unchanged wheels.
- The existing vulnerability DB remains **1,764,941,824 bytes**, above the unchanged 1 GiB evidence cap; authenticity/completeness/freshness requirements remain unresolved. No DB bytes were downloaded or modified.

## Validation and decision

Independent verification confirms both pins, four compressed hashes/sizes and diff IDs, publisher package/file comparisons, private artifact modes, limits, absence of partial downloads, and **2,218 preserved baseline records** (including all prior B2D/R3 evidence, source/document files and earlier acquired objects). B1's unconditional raise and an empty staged diff are verified. No dependency change, package installation/execution, Docker pull/build/run or Azure call occurred. Application tests were not rerun because no application/runtime source changed.

**Acquisition/static-integrity stage: complete. Security/build/runtime decision: NO-GO.** Next work requires separately authorised remediation and complete offline vulnerability/applicability evidence, an admissible authenticated DB, licence/provenance review and genuine independent approval. Physical builder isolation and runtime testing remain separately gated. No permission to alter this frozen candidate, suppress findings, enable build execution or deploy is implied.
