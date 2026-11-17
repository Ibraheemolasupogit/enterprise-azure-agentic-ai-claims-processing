# M23 Stage B2C — controlled binary acquisition

Date: **2026-11-13**. HEAD remains `1ca15877360c0b5af44f6c5c09a351c81c790711`; the pre-existing uncommitted B1/B2B work is preserved. This stage downloads/verifies only the frozen objects and inspects them as data. It does not install packages, run Python from the image, load native modules, use Docker, scan CVEs, or authorise deployment.

## Preflight and exact artifact set

Frozen B2B inventory SHA-256 verified before network activity and again on closeout:

```text
818ec99db7e67488b58b1d01b7a84267e5b607fd6c3324b19b0f4f25f5285d7b
```

Expected counts were exactly **35 wheel downloads, four image filesystem-layer downloads and four reused local wheels**. Counts and expected new binary size matched; no alternative version, URL selection or source build occurred.

The [exact acquired-artifact inventory](b2c-artifact-inventory.json) records all **43** binary files, actual SHA-256/size, filename, local path, frozen source URL/reuse origin and inspection status. [Catalog SHA-256](b2c-artifact-inventory.sha256):

```text
becdc3ffadff4f869e78f04c8c0d7491fe7b81c1373e3bfee5f60903533e2ab1
```

Isolated artifact directory:

```text
/Users/privilege/Desktop/GitHub_repository/enterprise-azure-agentic-ai-claims-processing/artifacts/m23-b2c-sdnhdt5a
```

It contains 39 dependency wheels, four layer blobs and three reverified copies of already acquired base metadata JSON. Layer filenames are explicitly local content-addressed names, not fabricated upstream filenames. Binary files are non-executable/read-only (`0444`) inside a newly created private directory (`0700`). The partial directory is empty. No project wheel was newly downloaded or staged beyond the specifically authorised set.

## Integrity, limits and receipts

- **39 downloads verified / four reused wheels verified / zero rejected or incomplete artifacts**. Every binary matches the frozen SHA-256 and byte size; wheel filenames are unchanged. All 39 actual wheel identities, WHEEL/filename tags, Requires-Python and B1 archive/ELF-header checks pass.
- New binary bytes: **57,776,873**. Measured HTTP response bodies: **57,782,362** bytes, including the anonymous token response; this is not a packet-level traffic measurement. All payloads are far below the 2 GiB ceiling. Every wheel is below 64 MiB and every layer below 1 GiB.
- Maximum two acquisition workers/transfers; **zero retries**, no unexpected redirect, hash mismatch or limit violation. Forty successful HTTP responses comprise 35 wheels, four layer CDN responses and one anonymous token exchange; four expected digest-scoped registry-to-CDN redirects are recorded.
- Only frozen wheel URLs, frozen layer digest URLs, the anonymous public pull-token endpoint and the previously reviewed `production.cloudfront.docker.com` digest paths were used. TLS verification stayed enabled through the existing native trust store; no account/cloud credentials or ambient proxy credentials were used. Tokens and signed redirect query values were never retained or forwarded as registry Authorization headers to the CDN.
- The acquisition process enforced the 60-minute deadline measured from preflight, streaming byte caps, at most two workers and at most one retry per object. Independent integrity/preservation verification completed **1546 seconds** after preflight; all network acquisition had already completed. No retry allowance was consumed.

[Acquisition receipts](../../../outputs/deployment/m23-b2c/acquisition-receipts.json), [preflight/limits](../../../outputs/deployment/m23-b2c/preflight.json) and [independent validation](../../../outputs/deployment/m23-b2c/validation.json) retain the exact outcomes. Analysis and acquisition scripts are retained with the evidence. They are not application/runtime changes or a new executable build path.

## Static compatibility and licence findings

All seven native extension members are **ELF64 little-endian AMD64** with matching CPython 3.12 or stable-ABI declarations. A bounded section-table parser inspected actual GNU version-need entries and DT_NEEDED/RPATH declarations; it never invoked `ldd`, a loader or any downloaded code.

| Distribution | Native member | Highest required GLIBC symbol version found |
| --- | --- | --- |
| cffi | `_cffi_backend.cpython-312-x86_64-linux-gnu.so` | 2.14 |
| cryptography | `cryptography/hazmat/bindings/_rust.abi3.so` | 2.17 |
| msgspec | `msgspec/_core.cpython-312-x86_64-linux-gnu.so` | 2.14 |
| pydantic-core | `pydantic_core/_pydantic_core.cpython-312-x86_64-linux-gnu.so` | 2.14 |
| pyyaml | `yaml/_yaml.cpython-312-x86_64-linux-gnu.so` | 2.14 |
| regex | `regex/_regex.cpython-312-x86_64-linux-gnu.so` | 2.14 |
| rpds-py | `rpds/rpds.cpython-312-x86_64-linux-gnu.so` | 2.14 |

Every observed GLIBC requirement is at or below its declared manylinux 2.17-compatible tag and below the base's static package declaration. Actual archived wheel Requires-Dist metadata, evaluated for Linux AMD64/CPython 3.12.16 without optional extras, has **zero conflicts** with the 39 pins. This is not a package installation/pip-check, full dynamic-linker validation or runtime import result.

Layer archives were streamed without extracting a root filesystem or following links on the host. The selected final view accounts for known whiteouts; it is not a complete merged rootfs. Static `/var/lib/dpkg/status` declares **libc6 2.36-9+deb12u14 / amd64 / install ok installed**. Archived libc and `python3.12` headers are AMD64. This is static evidence, not the genuine CPython/glibc runtime observation required by B1.

All **39 wheels contain available licence notices**: **41 notice files** were retained with member names, hashes and metadata declarations. Base review retained **119 final notice paths**, including **14 common licence texts**; mapped copyright notices were located for **105 dpkg-installed packages**, using archive link metadata only. Python's licence and a `pip-25.0.1.dist-info` licence are present in the base. The embedded/bootstrap Python packages therefore also require inventory and scanning; the 39 application pins are not the entire base software inventory.

[Wheel/base static inspection](../../../outputs/deployment/m23-b2c/acquisition-receipts.json), [base selected view](../../../outputs/deployment/m23-b2c/base-static-view.json) and [common-licence/package mapping supplement](../../../outputs/deployment/m23-b2c/base-licence-supplement.json) distinguish notice availability from approval. Actual notice bytes are retained under the new evidence directory.

## Remaining evidence and B2D recommendation

No licence acceptance or security result is fabricated. Remaining work includes:

- Per-artifact SPDX/notice review and full bundled/static/native dependency obligations; project distribution licence/source binding remains separate and incomplete.
- Independently authenticated upstream provenance/attestation review. Hashes match the frozen public records, but B2B's upstream signer was not verified and no real reviewer trust/signature has been created.
- Complete prebuild OS/Python/native SBOM and current, pinned offline vulnerability report/database, including base bootstrap/vendored components; **no CVE scan or SBOM generation was performed in B2C**.
- Genuine base-runtime observation, complete shared-library/runtime compatibility tests and any later image-specific checks, all requiring separate authorisation.
- A source-bound reviewed B1 manifest, independently pinned reviewer trust, authenticated evidence and actual physical BuildKit network-isolation verification. B1 `build()` still unconditionally refuses, even with otherwise valid evidence. None of the acquired files grants execution authority.

**Recommendation: GO to separately authorised Stage B2D for non-executing security-evidence review; NO-GO for builds, container/package execution or Azure.** Acquisition and bounded static verification are complete, with no rejected artifacts. The full container/production acceptance remains blocked by the evidence above; AZU-0058 remains unresolved. Stop after B2C.

All **914 pre-existing files** in the preflight preservation snapshot remain byte-identical, including frozen B2B inventory, historical outputs/data and uncommitted B1 work. Application/runtime, dependencies, infrastructure, workflows, M20/M21 controls and M22 holdout status are unchanged. No staging, commit, push, model call, Azure operation or M24 work occurred. Existing full-suite results were not regenerated; no new full pytest or installed-wheel execution is claimed.
