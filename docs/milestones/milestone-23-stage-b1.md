# M23 Stage B1 — offline container supply-chain readiness hardening

Date: **2026-11-13**. Baseline HEAD: `1ca15877360c0b5af44f6c5c09a351c81c790711`, clean at entry. This is offline input admission hardening, not Linux/container execution, deployment enablement, a production security approval or M24 implementation. AZU-0058 remains unresolved; M22 candidates remain PENDING_REVIEW and independent quality remains NOT_TESTED.

## Delivered

- [Artifact/evidence checker](../../deployment/supply_chain.py) and [admission CLI](../../deployment/build_container.py) enforce a complete source-bound v2 manifest, exact local artifact filenames/hashes, current independently pinned Ed25519 reviewer trust, signed evidence, Linux AMD64/CPython 3.12 base metadata/runtime-report bindings, actual OCI manifest/config/layer digests and sizes, wheel filename/metadata tags, Requires-Python, manylinux glibc floors and ELF AMD64/CPython headers. Sources include package/build metadata, runtime, tooling, constraints and actual context fixtures. Original v1 pending inputs remain byte-identical and refused.
- The former Docker executor is removed. Every B1 `build()` invocation refuses before subprocess/daemon/network access, **even with valid signed inputs**. An admitted signed disconnected-builder plan does not authorise or prove physical isolation. No actual isolated builder has been implemented or exercised. The required future boundary covers daemon, frontend/base resolution, RUN, caches/exporters and registry access beyond `--pull=false`.
- [Nine review templates](../../deployment/containers/evidence-templates/) remain pending, with absent hashes, signatures, identities, scan results and enrolled keys. They cover v2 inputs, reviewer trust, base-runtime observation, provenance, licences, prebuild SBOM, vulnerabilities, reproducibility and builder isolation. Real source/review trust and report semantics are not inferred from a filename or a supplied JSON name.
- [Contract, signature format, review procedure and outstanding acquisitions](../deployment/m23/stage-b1-supply-chain.md) distinguish cryptographically authenticated declarations from independently recomputed report semantics, prebuild versus final-image evidence, and readiness admission versus execution. README/tooling/deployment index references point to B1; historical Stage A records remain unchanged.
- New tests use only ephemeral, explicitly synthetic keys, ZIPs, base blobs and reports under pytest temporary directories. They test positive signature admission and negative missing/malformed/mismatched/untrusted/expired/revoked evidence, target/ABI/glibc incompatibility, local artifact/source tampering, incomplete report coverage, stale vulnerability databases and permissive builder plans. Synthetic test assertions are not actual approvals, licences, SBOMs or security findings.

## Verified results

New receipts: [outputs/deployment/m23-b1](../../outputs/deployment/m23-b1/). Earlier reports were not regenerated or overwritten.

| Check | Result |
| --- | --- |
| Focused source tests | **434 passed in 53.93s**: 123 new B1 cases, 82 foundation, 20 APIM, 111 M21, 98 M22 |
| Ruff lint / formatting | PASS; **183 files** formatted according to the checker |
| Strict mypy | PASS; **182 source files** |
| Dependency verification | `pip check` PASS; **39 runtime pins / 52 installed distributions** unchanged, no installation or new dependency |
| Existing foundation/static gates | PASS; cloud execution remains DISABLED, adapters NOT_IMPLEMENTED |
| Retained compiled template guards | All **nine** checked locally; zero enabled resources. Bicep/ARM scanner **not rerun** because no IaC change |
| Candidate project wheel | Existing source-era wheel hash/metadata verified, no rebuild: `2c286c30f7051bc69882844d08f345a9800e729cbe821185f54ccda2e9404b9c` |
| Runtime fingerprint | Unchanged: `130da6825a1ef233a6d394847e3fe80979c060d9c7e513d1acab6b2983f86d81` |
| Historical preservation | All **319 outputs**, **184 data files**, **150 source-tree files** (including package metadata), **13 requirements**, **17 infra** and **two workflow** files unchanged |
| Full source / independent-wheel pytest | Not rerun; no new full-suite or installed-wheel result claimed |
| Image acquisition/build/run / SBOM/CVE/reproducibility | **NOT_TESTED**; no downloads, image operations, scanner updates, source builds, container execution or real approvals |
| Azure and Git | No Azure operation, staging, commit or push. HEAD unchanged; deployment gates unmodified |

Only five baseline files change: root README, deployment README, build checker, deployment documentation index and existing foundation test fixtures. Thirteen new source/document/template files are added. [Exact file/hash inventory](../../outputs/deployment/m23-b1/files.json) and [baseline preservation receipt](../../outputs/deployment/m23-b1/preservation.json) distinguish changes from retained historical evidence.

## Limits and required next approval

No official base digest/patch/variant, compatible native wheel inventory, source-bound real review, project distribution licence evidence, current prebuild scanner results or verified disconnected builder exists in the packet. Signed fields authenticate an enrolled reviewer's assertions; they do not establish truthful observations, complete upstream signature verification or full ELF symbol/glibc dependency analysis. Current reviewer trust pins must be obtained independently; offline trust-store rollback and compromised trusted hosts/reviewers are outside this checker. Native imports, final-image SBOM/CVE scanning, two clean reproducibility builds and runtime/security/recovery checks need separate authorisation and execution.

Acquire exact reviewed artifacts only after explicit download/acquisition approval; do not source-build or upgrade dependencies to fill gaps. Review actual licence/provenance/report evidence, enrol genuine reviewer trust and pin/sign the complete packet. A future approved implementation must establish real daemon/frontend/RUN network isolation before replacing B1's unconditional build refusal. Current Dockerfile, non-root entrypoint, intentional health/startup refusal and API/UI/MCP application behaviour are unchanged.

**Recommendation: GO for B1 offline engineering acceptance; NO-GO for Linux build/run or Azure execution.** B1 closes the weak admission and accidental-execution paths within its scope. It does not complete artifact acquisition, live isolation, container readiness or M23 deployment acceptance. Stop after B1.
