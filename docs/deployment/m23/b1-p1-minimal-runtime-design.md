# M23 B1-P1 — Minimal runtime architecture design (Option B)

**Status: DESIGN ONLY — NOT IMPLEMENTED.** Prepared 2026-11-19 at baseline `b389f42` under the
owner's approval of Option B for detailed design. Nothing was downloaded, installed, built,
scanned or deployed. No code, Dockerfile, build input, gate or evidence file was changed.
**M23 remains DEFERRED — SECURITY GATE NO-GO**; B1's unconditional build refusal, the
zero-unresolved-Critical/High threshold, the 1 GiB / seven-day database rules, M22's
independent-review restrictions and M24's six NOT_TESTED demonstrations are unchanged.
This document requests no deployment approval.

## 1. Inputs and derivation

All closure facts below are derived offline from retained static inspection of the
already-acquired official image. Nothing was re-executed or re-fetched.

| Input | SHA-256 | Availability |
| --- | --- | --- |
| `outputs/deployment/m23-b2d-r4/native-inspection.json` (ELF `DT_NEEDED`, symbol versions, wheel ELF data) | `fefc316f542f924a2b32b5aba6d6ae921d4df62ad4f18e855b9bec5a06cc967d` | Ignored, local only (M24 gap G07) |
| `outputs/deployment/m23-b2d-r4/component-comparison.json` (87 installed dpkg packages) | `1679f907449c8272b84d3e99121527acc43342e4c44c5fdffd6c8de7dafa903f` | Ignored, local only |
| `outputs/deployment/m23-b2d-r4/filesystem-inventory.json` | `6f7518df238c6227ba815f149b6af6a378290d41246500140079213e07d11f33` | Ignored, local only |
| [R3 replacement-base metadata](r3-replacement-base-metadata.json) | `c134c3eab5626d3879f460b82642f5fc652802a4dff2514f35c1438669422d96` (matches its recorded pin) | Tracked |
| `deployment/containers/Dockerfile` | `a3ed8ac1b6f3db22f3e83324f5f3b275a47caab5ba80e5aa2109453b9a5c4727` | Tracked |
| `deployment/containers/build-inputs.pending.json` | `dc6fe46ce5a0a603c76771b9b36f5c501e451ccc4e841a68c52d2bb81369f041` | Tracked |

Static `DT_NEEDED` analysis is not loader execution. Every closure claim must be
re-proven against the final image (section 8).

## 2. Architecture

```text
Stage 1  builder   FROM python:3.12.16-slim-trixie@<R3 platform digest 05a994d2…4177>
         - offline only (--network=none); B1-admitted artifacts only
         - (zlib pathway, section 6) install the authenticated zlib1g deb13u1 package
         - create /opt/venv; pip install --no-index --require-hashes --only-binary=:all:
         - remove pip/setuptools/wheel from /opt/venv
         - assemble /rootfs strictly from the allow-list manifest (section 3)
         - emit an evidence-only ownership map from the builder's dpkg database (not shipped)

Stage 2  runtime   FROM scratch
         - COPY --from=builder /rootfs /
         - USER 10001:10001; exec-form ENTRYPOINT/HEALTHCHECK (already shell-free)
         - no shell, package manager, compiler, SUID/SGID file or network tool
```

Design rules:

- **Allow-list, not deny-list.** The runtime contains only paths named in a versioned
  runtime manifest. Each entry records owning package, version, mode and expected SHA-256.
  Components are absent by construction, not by deletion from the slim image.
- **Same CPython build.** `/usr/local` comes from the official 3.12.16 image, so the
  interpreter, `libpython3.12.so.1.0` and the venv home path (`/usr/local/bin`) are unchanged.
- **Scanner visibility.** The runtime carries a curated dpkg status (one record per retained
  package, generated from the builder's database) and `/etc/os-release`. Without them, OS
  scanners would silently report nothing. Absence evidence must never rest on scanner
  silence.
- **Dockerfile impact (later implementation).** Only the runtime stage changes, from
  `FROM ${PYTHON_BASE}` to `FROM scratch`, plus manifest assembly in the builder. Network,
  hash, non-root and healthcheck rules are unchanged.

## 3. Runtime contents

### 3.1 Native-library closure (derived)

The 81 ELF objects under `/usr/local` resolve to 19 system libraries. Stdlib extension
modules map to libraries as follows:

| Extension module | Needs | Decision |
| --- | --- | --- |
| `_ssl`, `_hashlib` | `libssl.so.3`, `libcrypto.so.3` (OpenSSL 3.5.7) | **Retain** |
| (transitive via `libcrypto`) | `libz.so.1`, `libzstd.so.1` | **Retain**; zlib must be the fixed version |
| `zlib`, `binascii` | `libz.so.1` | **Retain** |
| `_ctypes` | `libffi.so.8` | **Retain** (third-party code may use it) |
| `_lzma`, `_bz2` | `liblzma.so.5`, `libbz2.so.1.0` | **Retain** (lazy stdlib use by archive modules; no recorded finding) |
| `_sqlite3` | `libsqlite3.so.0` | **Conditional** on the SQLite decision (section 7) |
| `_uuid` | `libuuid.so.1` (**util-linux source**) | **Exclude**: no `uuid1()` use; `uuid4`/`uuid5` are pure Python |
| `_curses`, `_curses_panel`, `readline` | `libncursesw`, `libpanelw`, `libtinfo`, `libreadline` (**ncurses**) | **Exclude**: never imported |
| `_dbm`, `_gdbm`, `_crypt` | `libdb-5.3`, `libgdbm`, `libcrypt` | **Exclude**: never imported |
| `_tkinter` | `libtcl8.6`, `libtk8.6` (absent from the image already) | **Exclude** |

The native wheels (cffi, cryptography, msgspec, pydantic_core, pyyaml, regex, rpds_py)
additionally need **`libgcc_s.so.1`**, used by the Rust-based cryptography, pydantic_core
and rpds. They require at most **GLIBC_2.17**, against glibc 2.41.

### 3.2 Retained packages (allow-list scope)

| Package | Reason |
| --- | --- |
| `libc6` (glibc 2.41) | Loader, libc, libm and compatibility stubs |
| `libgcc-s1` (plus its `gcc-14-base` status record, if dpkg consistency needs it) | Rust-based wheels |
| `zlib1g` **1:1.3.dfsg+really1.3.1-1+deb13u1** | libcrypto, `zlib`, `binascii` (section 6) |
| `libssl3t64` 3.5.7 (libraries only) | TLS and hashing |
| `libzstd1`, `libffi8`, `liblzma5`, `libbz2-1.0` | Closure above |
| `libsqlite3-0` | **Only if** the SQLite decision retains it |
| `ca-certificates` (bundle file only), `tzdata`, `netbase` | Outbound TLS, zone data, services/protocols |
| `base-files` (`/etc/os-release` only) | OS identification for scanners |
| `/usr/local` CPython subset; `/opt/venv` without pip; `/app`; minimal `/etc/passwd`/`group` for 10001 | Application |

Excluded: everything else. That includes shells (`bash`, `dash`), `coreutils`, `apt`/`dpkg`
binaries, `tar`, `gzip`, the `openssl` CLI and `openssl-provider-legacy`, `login`/`passwd`,
`readline`, `libdb5.3t64`, `libgdbm6t64`, `libcrypt1`, and the base image's own pip,
setuptools, `ensurepip`, `idlelib`, `tkinter`, `turtledemo` and `test` trees.

## 4. Python module policy

- Start-up must import only allow-listed modules. A missing module fails closed with
  `ImportError`; there is no fallback install.
- Required imports for acceptance include `ssl`, `hashlib`, `zlib`, `ctypes`, `lzma`, `bz2`,
  `json`, `uuid` (`uuid4`, `uuid5`), `zoneinfo`, `asyncio`, all pinned dependencies, and
  `sqlite3` if retained.
- Required import failures: `curses`, `readline`, `_uuid`, `dbm.gnu`, `dbm.ndbm`, `crypt`,
  `tkinter`, and `sqlite3` if excluded.

## 5. Excluding the five removable High-CVE components

| CVE | Package family | Why it's removable | How it's excluded |
| --- | --- | --- | --- |
| CVE-2025-69720 | ncurses (`ncurses-base`, `ncurses-bin`, `libncursesw6`, `libtinfo6`) | Only `_curses`, `_curses_panel` and `readline` need it | Drop those modules and every ncurses path, including `infocmp`/`tic` and terminfo data |
| CVE-2026-9538 | `perl-base` | Not in the closure | Not on the allow-list |
| CVE-2026-54369 | `libacl1` | Not in the closure (was a `tar` dependency) | Not on the allow-list |
| CVE-2026-78410 | util-linux (`mount`, `bsdutils`, `util-linux`, `libmount1`, `libblkid1`, **`libuuid1`**) | Only `_uuid` needs `libuuid1` | Drop `_uuid` so **no util-linux-source package remains** |
| CVE-2026-16742 | systemd (`libsystemd0`, `libudev1`) | Not in the closure (`apt` dependency) | Not on the allow-list |

Absence verification against the **final image** (all must pass; scanner output alone is
never sufficient):

1. **Ownership:** zero final-image paths owned, per the builder's
   `/var/lib/dpkg/info/*.list`, by any package of the five families.
2. **Name patterns:** zero paths matching `libncurses*`, `libtinfo*`, `libpanel*`,
   `terminfo`, `infocmp`, `tic`, `perl*`, `libperl*`, `libacl*`, `mount`, `umount`,
   `libmount*`, `libblkid*`, `libuuid*`, `libsystemd*`, `libudev*`.
3. **ELF linkage:** no ELF object (including wheel members) has a `DT_NEEDED` entry for those
   sonames. A static/vendored-string sweep repeats R4's complete static inventory method.
4. **Privileges:** zero SUID/SGID files and zero file capabilities in the final image.
5. **Package metadata:** the curated dpkg status contains none of those packages.
6. **Runtime:** section 4's import-failure checks pass inside the container.
7. **Disposition:** an independent reviewer records **COMPONENT_ABSENT_IN_FINAL_IMAGE** per
   CVE, bound to the image digest, layer digests and these receipts. That's the
   disposition basis the owner must approve as gate policy (approval A2).

## 6. zlib approved-fix pathway (CVE-2026-85091)

zlib cannot be excluded: `libcrypto.so.3` itself needs `libz.so.1`. Two routes, in order
of preference:

1. **Vendor-built image (preferred if available at implementation time).** Adopt a newer
   official `3.12.x-slim-trixie` digest whose publisher SBOM already contains
   `zlib1g 1:1.3.dfsg+really1.3.1-1+deb13u1` or later, after an R3-style metadata review.
   The vendor build then carries the fix; this design otherwise applies unchanged.
2. **Builder-installed security update.** Install the exact retained binary
   `zlib1g_1.3.dfsg+really1.3.1-1+deb13u1_amd64.deb` (**88,720 bytes**, SHA-256
   `8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb`) in the builder,
   offline, from B1-admitted artifacts. Then verify `dpkg-query` version, `libz.so.1`
   bytes against the package data, and its presence in the runtime manifest.

Either route requires all six reopening prerequisites in the
[remediation handoff](security-remediation-blocked-handoff.md): independent key
provenance, real signature verification, freshness and rollback checks, an authenticated
package chain, the R6 prerequisites, and separate bounded acquisition approval.

The retained security metadata **expires 2026-11-24**. Any later acquisition needs fresh
authenticated metadata; nothing here authorises a refresh.

Regression checks: `zlib`/`gzip` round trips, a TLS loopback handshake through libcrypto,
and the full test suite inside the container.

## 7. SQLite architecture decision paper (CVE-2026-119373, -119374, -119379)

**Facts established by this design:**

- **SQLite is a real runtime dependency of security controls.** `_sqlite3` links
  `libsqlite3.so.0` (3.46.1-7+deb13u2). M20's outcome store and M21's grant lifecycle
  (`security_hardening/lifecycle.py`, imported by `security_hardening/bindings.py` for
  identity binding) use it.
- Today's container API/UI/MCP import surface does not load `sqlite3`, but any deployment
  enforcing M21 durable revocation would.
- **Session/changeset (-119379):** Python 3.12's `_sqlite3` exposes **no** session or
  changeset API. No pinned wheel embeds or links SQLite (R4 `sqlite_compile_strings` empty).
  The source never calls `load_extension`.
- **FTS5 (-119373, -119374):** this is reachable in principle through SQL or a crafted
  database file. The source contains no FTS, virtual-table or extension use. Statements are
  static schema text or fixed internal table names. M20 verifies the exact schema and
  integrity at open.

| Criterion | S1 Reviewer-assessed non-applicability | S2 Exclude SQLite from the deployed service | S3 Wait for an upstream/Debian fix | S4 Custom SQLite without FTS5/session (not recommended) |
| --- | --- | --- | --- | --- |
| Security outcome | Code stays present; risk accepted on proven unreachability | Code absent by construction | Code fixed by vendor | Code absent by construction |
| -119379 (session) | **Strong**: no API exposure, no native caller | Resolved | Resolved when shipped | Resolved |
| -119373/-119374 (FTS5) | **Moderate**: needs proof that crafted or restored files can't reach FTS5 before schema rejection | Resolved | Resolved when shipped | Resolved |
| Effect on controls | None | **Removes M21 durable revocation and M20 outcomes** from the image unless replaced, a security regression for any authenticated deployment | None | None |
| Engineering effort | Low (evidence pack); reviewer time | **High**: managed-persistence redesign with authority, audit and recovery | None (monitoring) | High: source build, toolchain provenance, upkeep |
| Schedule control | Owner and reviewer | Owner | **None** (vendor timeline unknown) | Owner |
| Gate fit | Needs owner policy accepting reviewed non-applicability | Clean | Clean | Clean, but adds a new supply chain |
| Key evidence | Caller inventory; proof the stdlib exposes no session API; a crafted FTS5-file test on disposable copies showing rejection before FTS5 execution; defensive DB configuration | Import-failure proof; replacement revocation design | Authenticated advisory showing the fixed version | Reproducible build provenance |

**Recommendation for the owner:**

- **S1 now, in two tiers:**
  - -119379 on the API-exposure and no-caller evidence;
  - -119373/-119374 only after the crafted-file test proves rejection before any FTS5 code
    executes.
- **S3 as continuous monitoring,** adopting a fix through the section 6 route-1 mechanism as
  soon as it ships.
- **S2 as the long-term production direction** (managed persistence), as its own approved
  architecture phase, never as a shortcut that drops revocation.

If the FTS5 test fails, the SQLite findings stay blocking: choose S3, or approve S2/S4
explicitly.

## 8. Acceptance tests (implementation phase)

| ID | Test | Pass criterion |
| --- | --- | --- |
| AT-01 | Allow-list manifest | Final file inventory equals the manifest exactly (path, mode, owner, SHA-256); no extra paths |
| AT-02 | Library closure | `readelf` closure of every ELF resolves only to manifest libraries; no unresolved needs except excluded modules' (absent) libraries |
| AT-03 | Five CVE families absent | Section 5 checks 1–6 all pass |
| AT-04 | zlib fixed | Installed version deb13u1 or later; library hash matches the authenticated package |
| AT-05 | SQLite per decision | S1: version and evidence pack bound; S2: import fails and no `libsqlite3` path |
| AT-06 | Hardening | No shell, package manager or SUID/SGID; UID 10001; works with a read-only root filesystem and `tmpfs` `/tmp` |
| AT-07 | Python behaviour | Section 4 import matrix; `ssl` default context verifies a local test CA; `zoneinfo` UTC |
| AT-08 | Application | Existing container smoke checks; health check fails closed while cloud execution is disabled; **full offline test suite inside the container** (first Linux evidence) |
| AT-09 | Scanner | Approved, authenticated database within 1 GiB and at most 7 days old; zero unresolved Critical/High except approved dispositions; scanner sees the curated dpkg status |
| AT-10 | Reproducibility | Two independent builds give identical image config and layer digests (section 10) |
| AT-11 | Negative | Tampered manifest, hash, missing artifact or network attempt aborts the build before the runtime assembles |

## 9. Supply-chain requirements

- Builder pinned by platform digest only; no mutable tags. SLSA/SBOM bindings re-verified
  against an independent trust root (Docker Official Images signing, plus Debian archive
  keys for any `.deb`).
- B1 admission for every artifact: wheels (hash-pinned manylinux), zlib `.deb`, licence
  review (R7 Agent Framework mapping still **PENDING_REVIEW / NOASSERTION**).
- SBOM of the **final runtime** covering:
  - dpkg packages;
  - CPython 3.12.16 (source-built, not a dpkg package);
  - every wheel, including cryptography's vendored OpenSSL and Rust crates.

  This addresses R6's CPython / bundled OpenSSL / Cargo / native coverage requirement; it
  isn't satisfied by OS scanning alone.
- Provenance attestation for the built image binding builder digest, manifest hash, artifact
  hashes and `SOURCE_DATE_EPOCH`.
- Vulnerability database: unchanged rules. The historical Trivy database (1,764,941,824
  bytes) exceeds the cap; a compliant source is still an open prerequisite.

## 10. Reproducibility

- Fixed `SOURCE_DATE_EPOCH`; normalised mtimes, ownership and ordering in `/rootfs`; no
  timestamps or random data in generated dpkg status, manifest or `.pyc`
  (`PYTHONDONTWRITEBYTECODE=1`; precompile deterministically or not at all).
- `--network=none` for every `RUN`; all inputs content-addressed.
- Two builds on separate clean builders must give identical config and layer digests;
  differences block admission and are retained as evidence.

## 11. Rollback strategy

- **Before deployment:** nothing is deployed and `registry_push_allowed` stays false.
  "Rollback" means keeping the last admitted manifest, image digests and evidence immutable
  and rejecting any candidate that fails AT-01 to AT-11.
- **Design fallback:** if the minimal runtime can't pass acceptance, for example an
  unsatisfiable closure or reproducibility, fall back to Option C (a vendor-minimal image)
  after its own metadata assessment. Don't loosen the allow-list ad hoc.
- **Runtime fallback (future, if ever approved for deployment):** promote by immutable
  digest only. Rollback means re-pointing to the previous approved digest; there are no
  in-place patches.
- **Missing-module discovery:** an `ImportError` in testing is fixed by a reviewed manifest
  amendment and full re-acceptance, never by adding a shell or package manager.
- **Data:** the image change doesn't alter store formats; SQLite file compatibility is
  unchanged for the same library version. No migration, replay or rehash of historical
  stores.

## 12. Approvals needed for implementation (each separate)

| # | Approval | Owner decision |
| --- | --- | --- |
| A1 | Adopt this design as the implementation target, with Option C as fallback | Strategy |
| A2 | Accept **COMPONENT_ABSENT_IN_FINAL_IMAGE** (independently reviewed) as a gate-disposition basis | Gate policy, recorded without changing thresholds |
| A3 | SQLite decision (S1/S2/S3/S4) and, for S1, acceptance of reviewer non-applicability as a disposition type | Architecture and gate policy |
| A4 | Independent reviewer appointment for dispositions and evidence | Governance |
| A5 | Trust anchors: Docker Official Images signing and Debian archive keys with independent provenance; an approved verifier | Security |
| A6 | Scanner database source compliant with the 1 GiB / seven-day rules, or a documented owner decision | Security |
| A7 | Bounded metadata refresh and acquisition (builder digest, zlib `.deb`, wheels) | Supply chain |
| A8 | Dockerfile/manifest code change and lifting B1's build refusal for this target only | Engineering and security |
| A9 | Build, scan and in-container test execution under approved isolation (M24 rules) | Execution |

Deployment is **not** requested and stays out of scope.

## 13. Remaining blockers and readiness

Base-agnostic blockers still open:

- independent trust anchors and verifier (R10);
- a compliant vulnerability database;
- an independent reviewer;
- the R7 licence decision;
- CPython / vendored-OpenSSL / Cargo SBOM coverage;
- the B1 build refusal;
- an approved isolation mechanism for in-container execution.

| Readiness item | Status |
| --- | --- |
| Architecture specified | **COMPLETE** (this document) |
| Closure derived | **COMPLETE (static)**; runtime proof NOT_TESTED |
| 5 removable High findings | **DESIGNED FOR ABSENCE**; verification NOT_TESTED |
| zlib | **PATHWAY DEFINED**; blocked on trust and acquisition approvals |
| SQLite (3 Highs) | **DECISION REQUIRED** (A3) |
| Implementation | **NOT READY**: needs A1–A9; M23 SECURITY GATE NO-GO unchanged |
