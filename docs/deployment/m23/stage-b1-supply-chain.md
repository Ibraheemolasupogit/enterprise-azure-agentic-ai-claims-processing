# M23 Stage B1: offline container supply-chain readiness

B1 hardens **input admission**, not Linux execution or Azure hosting. Build/run, network isolation in a real builder, image CVE results and reproducible OCI output remain NOT_TESTED. Azure stays prohibited and AZU-0058 remains unresolved. Application runtime, Dockerfile/entrypoint, Stage A infrastructure/workflows, frozen M22 labels and historical outputs are unchanged.

## Admission contract

[`deployment/build_container.py`](../../../deployment/build_container.py) accepts only the new `m23-linux-build-inputs-v2` contract for reviewed inputs. Original v1 pending inputs are preserved and still refused. All manifest keys are required, unknown keys rejected, booleans cannot substitute for epochs, and the fixed build epoch must precede signature time. Exact 39 runtime pins remain unchanged; no source build, dependency resolution or upgrade is allowed.

The independently pinned manifest SHA-256 protects its serialized bytes. **It is not reviewer authentication.** Admission also requires a separately pinned trust-store SHA-256 and an Ed25519 signature from an enrolled, current, non-revoked key. Trust keys bind key ID, reviewer identity, public key, validity window and revocation status. Review validity is at most seven days. Self-supplied manifest keys, empty review dictionaries, untrusted keys, wrong identities, expired/future reviews, mismatched signatures and changed evidence are rejected. Existing pinned `cryptography` supplies Ed25519; no dependency is added.

The authorised operator must obtain the current trust-store pin through an independent authenticated channel and check actual reviewer enrolment/revocation. A supplied trust-store file or a name in JSON is not self-authenticating. B1 cannot discover offline trust-store rollback, a compromised reviewer/host, or a dishonest authorised review. Build-review trust is separate from M21 application identities and grants no application/cloud authority. No real reviewer, key, approval or signature is provisioned here.

The signed payload is exactly:

```text
b"m23-offline-build-review-v2\0" + canonical_json({
  "manifest": manifest with the entire "review" member omitted,
  "attestation": review with only "signature_hex" omitted
})
```

Canonical JSON uses UTF-8, sorted keys, separators `(',', ':')`, no NaN/Infinity and default JSON ASCII escaping. The lowercase signature hex encodes an Ed25519 signature. `review_bytes()` exposes these bytes, not a signing operation. Signing must occur through the real reviewer's approved process; no private-key material belongs in the repository.

`source_files` must equal `source_inventory(root)`: `pyproject.toml`, `MANIFEST.in`, `README.md`, all application Python files and `py.typed`, all deployment Python tooling, every requirements `.txt`, Dockerfile/ignore file, entrypoint/smoke and the three M9 smoke fixtures. `expected_application_source_sha256` separately binds the existing application fingerprint. Changed, missing or additional source inputs invalidate admission. This binds actual input bytes, rather than treating a Git revision alone as proof. The operator also records the actual Git checkpoint/dirty state in provenance. The allowlisted context helper remains available, but no B1 API invokes a builder.

## Base and wheel verification

Use an official `docker.io/library/python@sha256:…` reference to the **Linux AMD64 platform manifest**, not a multi-platform index. A complete local artifact directory must contain the exact OCI/Docker v2 manifest, config and compressed layer blobs; each filename, SHA-256 and declared size is checked, and the image reference must equal the actual manifest hash. Config must declare Linux/amd64.

A source-bound base-runtime report must identify that same manifest/config, CPython `3.12.patch`, Linux/amd64, a concrete `2.minor` glibc version and a genuine observation time before review. The reviewer authenticates the report through the signed manifest. Checking this report does not itself execute Python or independently prove a runtime observation; obtaining that observation needs separately authorised base verification. No report is fabricated by B1.

Exactly one local wheel is required for each of the 39 pinned dependencies, plus `northstar-claims-ai==0.1.0`. Filenames, bytes/hashes, filename tags, WHEEL tags, distribution/version, `.dist-info` identity, Requires-Python and source members are checked. CPython 3.12 native and supported CPython `abi3` tags must target x86-64 manylinux, with the declared glibc floor no higher than the reviewed base. Legacy floors are manylinux1=2.5, manylinux2010=2.12, manylinux2014=2.17. Raw `linux_x86_64`, musllinux, other architectures, future CPython ABI and unknown manylinux forms are refused. Native `.so` payloads additionally require ELF64 little-endian AMD64 headers and compatible CPython suffixes; they cannot hide under universal-only tags.

Requires-Python supports an intentionally restricted numeric comparison subset (`>=`, `<=`, `==`, `!=`, `>`, `<`, comma intersection); unsupported syntax is rejected for explicit checker review. Header checks and declared manylinux floors are not a full auditwheel/ELF symbol-dependency audit. Real native import/runtime checks remain mandatory later. ZIP traversal, duplicate members, symlinks/special files, encrypted entries, `.pth` injection and excess declared archive capacity are rejected. Local artifact paths are basenames, confined to the chosen directory; symlink files, missing files and altered bytes fail closed. The project wheel must match the complete application member inventory and source bytes.

## Reviewable evidence packet

[Nine pending JSON templates](../../../deployment/containers/evidence-templates/) contain no approvals or invented hashes. Copy them into a **new** review directory. Never overwrite Stage A evidence or the original pending manifest. Every artifact/evidence record is `{ "file": actual_basename, "sha256": actual_lowercase_sha256 }`, pointing to actual local bytes. Required files cannot be replaced by URLs or summary prose alone.

To avoid circular hashes, `subject_sha256` is the SHA-256 of canonical JSON of the manifest with **both** `evidence` and `review` omitted (`subject()`). Populate base, wheels and source fields first, then evidence reports. Each report must cover the exact set of base-manifest plus 39 dependency plus project-wheel hashes. The base manifest transitively binds its config/layers. Hash each report, put its record in `evidence`, and then obtain the manifest signature and independent manifest pin. Do not change source/inputs after review.

| Evidence | Required review content | Admission status after genuine review |
| --- | --- | --- |
| Provenance | Per-artifact origin, reviewed upstream digest/attestation method or source-matched project provenance, local hashed verification receipts and review notes | VERIFIED_FOR_LOCAL_BUILD |
| Licence | Per-artifact SPDX expression and hashed notice/licence files; include base OS, bundled native libraries, Python packages and project distribution rights | VERIFIED_FOR_LOCAL_BUILD |
| SBOM | Actual prebuild base/wheel inventory report, SPDX 2.3 or CycloneDX 1.6, tool/version, OS/Python/native coverage | VERIFIED_FOR_LOCAL_BUILD |
| Vulnerability | Actual report, scanner/version, locally retained database bytes/hash/update time; unresolved Critical/High both zero; database at most seven days old at admission | VERIFIED_FOR_LOCAL_BUILD |
| Reproducibility | Reviewed two-independent-clean-build plan comparing source, wheel inventory, SBOM, image config and OCI manifest; result stays NOT_TESTED | PLAN_REVIEWED |
| Builder isolation | Reviewed disconnected Linux VM plan, pinned builder identity/version and hashed policy; no external interfaces/remote builder/registry access, preloaded inputs only, daemon/frontend/run egress DENY_ALL, execution_allowed=false | PLAN_REVIEWED |

All templates remain PENDING. Policy checks authenticate and structurally bind reviewer declarations and actual referenced report bytes; B1 does **not** recompute SBOM/vulnerability/licence findings or implement an upstream attestation verifier. The reviewer must verify that underlying receipts support those declarations, disposition other findings in retained reports, and obtain distribution rights. The zero-unresolved-Critical/High gate is a B1 artifact gate, not a change to frozen M22 evaluation gates or production security acceptance. Current native wheels, base licences and project licence evidence remain incomplete. No supplied report or risk acceptance is invented.

Prebuild evidence does not replace a later **final-image** SBOM/CVE scan. Keep actual image config ID separate from OCI manifest digest; neither is currently available. SOURCE_DATE_EPOCH is only an input contract: timestamp normalization, builder reproducibility and byte-identical images remain unproven until exercised.

## Offline builder boundary

B1 removes the old Docker executor. **`build()` unconditionally refuses even valid signed inputs**, before subprocess, daemon or network access. CLI without `--validate-only` also refuses. There is no environment-variable override, deployment switch, shell command, image pull or container-run path. This enforces no execution now rather than treating `--pull=false` or a signed plan as physical isolation.

A later, separately approved implementation must verify an actual disconnected Linux VM/air-gapped builder with no non-loopback interfaces, DNS/HTTP/registry egress or network-forwarding host sockets. Denial must cover BuildKit daemon, frontend/base resolution, RUN steps, telemetry, caches and exporters, not just container networking. Pin the actual builder/frontend/toolchain and preload all required images/blobs/wheels/databases. No remote builders, automatic plugins, remote cache or registry/SBOM/provenance uploads. Exercise positive local operations and denied egress with real evidence before replacing B1's unconditional refusal. Nothing in a reviewed JSON plan enables that future execution.

For admission only, after real review and acquisitions are separately authorised:

```sh
.venv/bin/python -B -m deployment.build_container --validate-only --root . \
  --manifest /absolute/review/build-inputs.json \
  --artifacts /absolute/review/artifacts \
  --trusted-manifest-sha256 ACTUAL_INDEPENDENT_MANIFEST_SHA256 \
  --trust-store /absolute/trust/reviewers.json \
  --trusted-trust-sha256 ACTUAL_INDEPENDENT_TRUST_STORE_SHA256
```

This command does not sign, acquire or execute anything. PASS means authenticated input admission only; output explicitly reports build execution DISABLED_B1 and reproducibility NOT_TESTED. Templates and v1 pending inputs exit 78. The real image entrypoint/health remain unchanged and refuse hosting with exit 78.

## Outstanding acquisition and approval sequence

1. Obtain separate permission to acquire a chosen, maintained CPython 3.12 glibc-based AMD64 official image, its actual platform manifest/config/layers, provenance and licence evidence. No base digest or patch version is selected by this change. Obtain an authentic base-runtime report under separately approved verification; execution is not authorised by B1.
2. Acquire exact compatible Linux wheels for cffi 2.1.1, cryptography 50.0.2, msgspec 0.22.0, pydantic-core 2.50.2, PyYAML 6.0.3, regex 2026.9.29 and rpds-py 2026.9.1. Reuse verified universal artifacts where present; complete all 39 filename/hash/provenance/licence records. Existing M13/M16/M22 universal receipts are partial and do not prove local availability. No fallback source builds/upgrades.
3. Bind the existing source-matching project wheel; resolve actual project licence/notice evidence. Obtain reviewed source/epoch/toolchain inventory, prebuild SBOM, current vulnerability database/report, provenance and notices in a new packet. Acquisitions/scans are not performed here.
4. Enrol genuine reviewer keys through independent trust governance; obtain authenticated current pins and signed review. No template identity/key is an enrolled reviewer. Test-only keys/signatures are ephemeral synthetic fixtures, never acceptance evidence.
5. Separately approve and implement actual builder isolation/execution, then perform two clean local builds, final-image SBOM/CVE checks and bounded Linux runtime/security/recovery tests. Preserve UID 10001, read-only root, bounded tmpfs/resources, no network, dropped capabilities and default startup refusal. Do not enable Azure hosting or promote M22 held-out labels.

Until those steps are completed, **NO-GO for Linux build/run and Azure execution**. B1 can be accepted as offline readiness hardening only, not an acquired supply chain, proven isolated builder or container runtime acceptance.
