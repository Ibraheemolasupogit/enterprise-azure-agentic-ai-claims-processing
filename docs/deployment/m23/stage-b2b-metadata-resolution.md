# M23 Stage B2B — public metadata resolution

Resolved **2026-11-13** against HEAD `1ca15877360c0b5af44f6c5c09a351c81c790711` plus unchanged, uncommitted B1 work. No application/IaC/dependency/workflow change or binary acquisition occurred. B1's unconditional build refusal and all Azure prohibitions remain intact.

## Frozen candidate inventory

[Exact acquisition inventory](b2b-acquisition-inventory.json), format `m23-b2b-metadata-acquisition-inventory-v1`, is **FROZEN_METADATA_ONLY_PENDING_BINARY_APPROVAL**. [SHA-256 record](b2b-acquisition-inventory.sha256):

```text
818ec99db7e67488b58b1d01b7a84267e5b607fd6c3324b19b0f4f25f5285d7b
```

This content hash freezes the observed selection; it is not a reviewer signature or an independently authenticated approval. All approval fields remain null/false. The inventory is deliberately not a completed B1 build manifest. Do not replace its selections by re-resolving a mutable tag during later acquisition.

The JSON records exact upstream wheel filenames, URLs, SHA-256, byte sizes, Requires-Python, Python/ABI/platform tags, yank status, source metadata hashes and eligible alternatives. **35/35 missing pinned releases resolved**, with one selected non-yanked wheel each and no unavailable candidate. The four previously local wheels were rehashed against retained receipts; they remain reuse candidates, not new downloads. Their current PyPI yank status was not re-queried in this 35-release scope.

## Base image and provenance

- Discovery tag: `python:3.12-slim-bookworm`; resolved version **3.12.16-slim-bookworm**, Linux AMD64. CPython `3.12.16` agrees between config ENV, pinned source Dockerfile and official image catalog.
- Immutable platform reference: `docker.io/library/python@sha256:0f086103b026048cc50cb5da25ec435c023c5241a83fc44daea593377abc61c4`.
- Config JSON: SHA-256 `313cf8f190a1abab00472c1f0c950c10486c22114bcd8aef2a8198fb587a6d18`, **5,681 bytes**. Actual received JSON bytes match the manifest descriptor's digest/size and declare Linux/amd64. The received platform manifest matches the index descriptor's digest/size.
- Source revision: `3d7e95597e56a415d9e4abc0f15877e005d2cb2e`, directory `3.12/slim-bookworm`; pinned [Dockerfile](https://raw.githubusercontent.com/docker-library/python/3d7e95597e56a415d9e4abc0f15877e005d2cb2e/3.12/slim-bookworm/Dockerfile). The [official image catalog](https://raw.githubusercontent.com/docker-library/official-images/7a0bcc4d1d7c52afa279a8bb10a6c98c67591963/library/python) agrees on tags, revision, directory and AMD64 support.
- Linked in-toto/SLSA v0.2 **JSON metadata** was retained. Its attestation-manifest and statement hashes match their descriptors; its image subject and Git material/config-source match the selected image/revision. **No upstream signer/signature was independently verified.** The named upstream builder is a declaration, not an enrolled B1 reviewer.
- Four filesystem layers total **45,269,504 bytes**. Their exact digests, registry URLs, media types and sizes are recorded, but **none was downloaded**. The upstream Dockerfile was read only; its build commands were never executed.

## Declared compatibility

Debian's [Bookworm libc6 metadata](https://packages.debian.org/bookworm/libc6) reports `2.36-9+deb12u14`. This supports a **nominal glibc 2.36** selection target; it does not measure the library installed in this image. All chosen native wheels declare a usable glibc **2.17** tag. Compressed multiple-platform tags are treated as alternatives, not cumulative glibc requirements.

| Distribution | Exact chosen native wheel | Minimum compatible declared glibc |
| --- | --- | --- |
| cffi | `cffi-2.1.1-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 2.17 |
| cryptography | `cryptography-50.0.2-cp311-abi3-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 2.17 |
| msgspec | `msgspec-0.22.0-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | 2.17 |
| pydantic-core | `pydantic_core-2.50.2-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 2.17 |
| pyyaml | `pyyaml-6.0.3-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | 2.17 |
| regex | `regex-2026.9.29-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.manylinux_2_28_x86_64.whl` | 2.17 |
| rpds-py | `rpds_py-2026.9.1-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | 2.17 |

CPython 3.12.16 satisfies all 35 selected Requires-Python declarations under both packaging and B1's restricted numeric checker; declared tags pass B1's AMD64/ABI/glibc checks against the nominal target. A Linux release-metadata dependency audit of all 39 pins found **zero conflicts**, using local METADATA for the four reused wheels. This is not a Linux install/pip-check result. Actual WHEEL metadata, SHA-256, ELF headers/symbol dependencies and native imports remain unverified for the unacquired candidates. No wheel code was imported or executed.

All twenty previously retained universal-wheel receipts applicable to the 35 resolved candidates match the newly observed filename/hash records. Public PyPI metadata reported no advisories for these releases; that is **not** a vulnerability scan, and licences have not been accepted.

## Endpoints, redirects and transport evidence

[Endpoint summary](../../../outputs/deployment/m23-b2b/endpoints-summary.json) and per-attempt ledgers retain requested URLs, statuses, timestamps, safe response headers and raw metadata response hashes. Contacted hosts: `pypi.org`, `auth.docker.io`, `registry-1.docker.io`, `production.cloudfront.docker.com`, `api.github.com`, `raw.githubusercontent.com`, `packages.debian.org`. **No request was made to files.pythonhosted.org or to any filesystem-layer digest.**

The resolver recorded **86 attempts**: **47 HTTP 200**, **three HTTP 307**, **36 initial network errors**. Two earlier diagnostic attempts are recorded separately: sandbox DNS failure and a successful public PyPI curl request, with uncaptured timestamps/body hashes explicitly absent. The first external Python run failed certificate validation; its ledgers are retained. The successful retry used existing `truststore==0.10.5` with native OS roots and full TLS verification, never an insecure TLS bypass. No dependency/CA installation occurred.

Docker redirected config/provenance JSON to its CloudFront hostname. Redirects were not followed automatically: the initial config redirect was left unfollowed; subsequent config/provenance redirects were manually admitted only for the already declared JSON digest/path, with strict size and final hash checks. No registry Authorization header was forwarded to the CDN. Anonymous registry tokens and temporary signed redirect query values were memory-only/not retained; ledger queries are redacted. No user/account/cloud credentials, Docker daemon or Azure service was used.

## Validation and approval boundary

[Local validation](../../../outputs/deployment/m23-b2b/validation.json) cross-checks frozen hash, all 39 pins, 35 selected source records, four local wheel hashes/sizes, base metadata hash chain, provenance/source bindings, declared compatibility, dependency metadata, endpoint restrictions and **840 pre-existing file/evidence hashes**. All passed; B1 refusal remains byte-identical. Application tests/scans/builds were not rerun: no application change occurred. This stage has no binary, ELF, live runtime, licence, SBOM, CVE or reproducibility result.

**Recommendation: CONDITIONAL GO for separately approved exact binary acquisition/hash verification only.** The proposed next stage comprises **35 wheel files (12,507,369 bytes) plus four filesystem layers (45,269,504 bytes): 39 binary objects / 57,776,873 bytes total**, with the exact URLs/digests in the frozen inventory. Copy/reverify the four cached wheels and already captured metadata into a new acquisition directory; never overwrite earlier artifacts. Registry/CDN redirects must remain restricted to the approved digests and no anonymous token/query should be logged. Stop on changed metadata, digest/size mismatch, unexpected host or unavailable object; no alternate version or source build.

No binary download is authorised by B2B itself. Licence/provenance review, actual binary/ELF checks, SBOM/CVE evidence, genuine base-runtime observation, reviewer enrolment/signature and verified physical BuildKit isolation remain pending. B1 `build()` must continue refusing even after acquisition. Builds, container execution, deployment gates, Azure, M24, staging, commits and pushes remain out of scope.
