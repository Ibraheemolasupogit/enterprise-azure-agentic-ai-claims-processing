# M23 B1-P2 — Security acceptance plan for the minimal runtime

**Status: PLAN ONLY — NOTHING EXECUTED.** Prepared 2026-11-19 at baseline `9b93b5a` for the
published [B1-P1 design](b1-p1-minimal-runtime-design.md) (SHA-256
`f41822f047911e55a53b8f571fa506c013ac7d12ded386b4840a1a6d533e23dd`). No source, Dockerfile,
build input, template, gate or evidence file was changed. Nothing was downloaded, installed,
built, scanned, traced or run in a container.

**M23 remains DEFERRED — SECURITY GATE NO-GO.** B1's unconditional build refusal, the
zero-unresolved-Critical/High threshold, the 1 GiB / seven-day database rules, M22's
independent-review restrictions and M24's six NOT_TESTED demonstrations are unchanged. This
plan defines what evidence would be required. It grants no approval and changes no
threshold.

## 1. Conventions for all evidence

- **Reuse B1 admission.** Every item below is a report file whose SHA-256 enters the
  existing `m23-linux-build-inputs-v2` evidence set and is covered by the reviewer's
  Ed25519 signature ([B1 contract](stage-b1-supply-chain.md)). That means an enrolled,
  current, non-revoked key, a trust-store pin obtained through an independent channel, and
  review validity of at most seven days. No parallel trust mechanism is introduced.
- **Subject binding.** Each report names the final OCI image manifest digest, config digest,
  every layer digest, the runtime allow-list manifest SHA-256, the builder platform digest
  and the exact CVE IDs it addresses. Any rebuild or manifest change invalidates all
  dependent reports.
- **Vocabulary.** `PASS`, `FAIL` or `NOT_TESTED` only. Missing evidence is `NOT_TESTED`,
  never `PASS`. Scanner silence is never evidence of absence or safety.
- **Positive controls.** Every detection method must first be shown to **detect** the target
  in the original `3.12.16-slim-trixie` image (the control). A check that can't find the
  component where it's known to exist proves nothing about its absence.
- **Raw retention.** Raw outputs, commands, tool versions and hashes are retained alongside
  summaries, consistent with M24 gap G07: local-only archives must be made reviewable,
  not just summarised.

## 2. Absence evidence for the five removable families

Targets: CVE-2025-69720 (ncurses), CVE-2026-9538 (perl-base), CVE-2026-54369 (acl),
CVE-2026-78410 (util-linux, including `libuuid1`) and CVE-2026-16742 (systemd libraries).

| ID | Evidence | Method (specified, not executed) | Final image | Control image |
| --- | --- | --- | --- | --- |
| ABS-01 | Image identity | Export the final image to an OCI layout; record all digests | Recorded | Recorded |
| ABS-02 | Complete file inventory | Walk every layer tar (including whiteouts): path, type, mode, uid/gid, size, SHA-256, link target, using R4's inspection method | Equals the allow-list manifest exactly | Recorded |
| ABS-03 | Package ownership | Map every final path to an owning package using the builder's `/var/lib/dpkg/info/*.list` (evidence artifact, not shipped) | **0** paths owned by any of the 14 packages (`ncurses-base`, `ncurses-bin`, `libncursesw6`, `libtinfo6`, `perl-base`, `libacl1`, `util-linux`, `mount`, `bsdutils`, `libmount1`, `libblkid1`, `libuuid1`, `libsystemd0`, `libudev1`) | ≥1 path per family |
| ABS-04 | Name patterns | Match the B1-P1 section 5 pattern list over all paths | 0 matches | ≥1 per family |
| ABS-05 | Dynamic linkage | `DT_NEEDED`, `RPATH`/`RUNPATH` of every ELF object, including wheel members | No reference to `libncursesw`, `libtinfo`, `libpanelw`, `libreadline`, `libperl`, `libacl`, `libmount`, `libblkid`, `libuuid`, `libsystemd`, `libudev` | References present |
| ABS-06 | Runtime loading by name | Search all ELF and Python files for `dlopen`/`ctypes`/`find_library` targets naming those sonames | 0 matches, or each match reviewed as unreachable because the library is absent | Recorded |
| ABS-07 | Static/vendored copies | Repeat R4's complete static inventory: version and identifying strings for each family in every ELF (e.g. ncurses version banner, `acl_get_file`, `X-mount.owner`, `systemd-homed`, `Archive::Tar`) | 0 unexplained matches | Matches present |
| ABS-08 | Privileges | Every file's mode bits and `security.capability` attributes in layer metadata | 0 SUID, 0 SGID, 0 file capabilities | `/usr/bin/mount` 04755 detected |
| ABS-09 | Package metadata | Curated dpkg status and `/etc/os-release` contents | None of the 14 packages listed; the retained set matches the allow-list | Recorded |
| ABS-10 | Import behaviour | Inside the container under approved isolation: `curses`, `readline`, `_uuid` fail with `ModuleNotFoundError`; `uuid.uuid4()`/`uuid5()` work | PASS | Imports succeed |
| ABS-11 | Scanner corroboration | Approved scanner (section 6) | None of the five IDs reported | All five reported |

**Pass condition per CVE:** ABS-01 to ABS-10 all PASS on the final image, every positive
control detects its target, ABS-11 agrees, and the reviewer records
`COMPONENT_ABSENT_IN_FINAL_IMAGE` (section 4). Any single FAIL or NOT_TESTED leaves the CVE
**BLOCKING**.

## 3. SQLite applicability checks (specified only; nothing executed)

Targets: CVE-2026-119379 (session/changeset), CVE-2026-119373 and CVE-2026-119374 (FTS5).
These checks apply only if the owner chooses B1-P1 option **S1**.

### 3.1 Common binding

| ID | Evidence |
| --- | --- |
| SQ-00 | Exact `libsqlite3.so.0` path, SHA-256, package version (`3.46.1-7+deb13u2` or later) and authenticated Debian source/patch mapping. `PRAGMA compile_options` captured inside the container, confirming whether `ENABLE_FTS5` and `ENABLE_SESSION` are compiled in. |
| SQ-01 | Inventory of every importer of `sqlite3`/`_sqlite3` in application and dependency code. At baseline these are `outcomes/store.py`, `outcomes/evidence.py`, `security_hardening/lifecycle.py` and `quality_ops/operations.py`. Each is labelled as in or out of the deployed service surface. |

### 3.2 Session extension (CVE-2026-119379)

| ID | Check | Pass criterion |
| --- | --- | --- |
| SQ-S1 | Python API surface: enumerate `_sqlite3` module, `Connection`, `Cursor` and `Blob` attributes in the exact CPython 3.12.16 build | No session or changeset entry point (pre-assessment on local CPython 3.12.8 found none; must be re-observed on the final build) |
| SQ-S2 | ELF symbol imports: undefined dynamic symbols of every ELF object except `libsqlite3` itself | No import of any `sqlite3session_*`, `sqlite3changeset_*`, `sqlite3changegroup_*` or `sqlite3rebaser_*` symbol |
| SQ-S3 | Foreign-function routes: search application and all dependency code for `ctypes`/`cffi` loading of `libsqlite3` or naming those symbols | 0 routes |
| SQ-S4 | Extension loading: search for `enable_load_extension`/`load_extension` calls; record whether the build exposes them | 0 calls; extensions never enabled |
| SQ-S5 | Bundled copies: confirm no wheel embeds SQLite (R4 recorded empty `sqlite_compile_strings`; recheck on final wheels) | 0 embedded copies |

All five PASS allows the reviewer to propose `NOT_APPLICABLE_NO_CALLER`.

### 3.3 FTS5 (CVE-2026-119373 / -119374)

The vulnerable FTS5 code is reachable in principle through SQL text or through a crafted
database file. Both routes must be closed.

| ID | Check | Pass criterion |
| --- | --- | --- |
| SQ-F1 | **SQL text provenance.** Catalogue every `execute`/`executescript` site and trace each statement's text origin | All SQL is static, or interpolates only fixed internal identifiers (e.g. the fixed table tuples behind `store.py` lines 312/315). No caller-, request- or file-derived SQL text. No `fts5`, `fts4`, `VIRTUAL TABLE` or `MATCH` use |
| SQ-F2 | **Open-path ordering (static).** For each open path, record the exact statements run before schema validation. At baseline: M20 and M21 both open the file in read-write mode, set `PRAGMA trusted_schema=OFF`, check `journal_mode`, run `BEGIN IMMEDIATE`, then compare `sqlite_master` with an in-memory reference **before** `quick_check` (M20) or `integrity_check` (M21), short-circuiting on mismatch | Documented sequence. Every pre-validation statement listed for SQ-F3 |
| SQ-F3 | **Crafted-file behaviour (dynamic; execution needs approval A9 under M24 isolation).** Disposable copies only: (a) valid store schema plus an extra `detail=none` FTS5 table holding negative rowids; (b) the same with a corrupted FTS5 index/footer and `secure-delete` enabled; (c) an expected table name replaced by an FTS5 table. Open each through the real M20 `OutcomeStore` and M21 `Lifecycle` paths | Each open rejected (`incompatible_schema`, `corrupt_storage` or `LifecycleError`) with **zero FTS5 code execution** before rejection, observed by the oracle below |
| SQ-F4 | **Execution oracle.** Instrumentation able to observe FTS5 internal functions, e.g. breakpoints or uprobes using authenticated Debian debug symbols matching SQ-00, in the isolated test VM. Positive control: the same oracle **does** observe FTS5 execution when a crafted table is deliberately queried | Oracle validated by its positive control; zero hits in SQ-F3 |
| SQ-F5 | **Threat preconditions.** Record who can write each database file (0600 files in private directories; restore/rollback anchor paths) and any import, restore or replication path for externally supplied database files | Reviewed and bound to the deployment design |

**Key open question for SQ-F3:** whether parsing a schema that contains a `CREATE VIRTUAL
TABLE … USING fts5` statement, or running `PRAGMA trusted_schema`, `journal_mode` or `BEGIN
IMMEDIATE`, runs FTS5 code before the `sqlite_master` comparison rejects the file. The
static ordering is favourable, but it isn't proof. This plan doesn't assume the answer.

**Pass:** SQ-F1, F2, F4 and F5 PASS and SQ-F3 shows rejection with no FTS5 execution. The
reviewer may then propose `NOT_APPLICABLE_UNREACHABLE`.

**Fail:** both FTS5 CVEs remain BLOCKING; fall back to B1-P1 option S3, or a separately
approved S2/S4. Code-level hardening (for example SQLite defensive configuration) would be a
new, separately approved change, not part of this plan.

## 4. Independent reviewer acceptance criteria

| ID | Criterion |
| --- | --- |
| RV-01 | **Independence.** Not an author of B1-P1/B1-P2, the Dockerfile/manifest change, the evidence tooling or the reports under review. Not an M20 producer or approver for the artifacts concerned. Conflicts declared in writing |
| RV-02 | **Competence.** Demonstrated container and Debian packaging security knowledge. For SQ-F, competence in SQLite internals. Owner records the basis |
| RV-03 | **Enrolment.** Key enrolled in the B1 reviewer trust store with identity, validity window and revocation status, obtained through independent trust governance. Template or test keys never count |
| RV-04 | **Primary evidence.** Decisions rest on the raw receipts and hashes in sections 2, 3, 5 and 6, independently re-verified, not on author summaries |
| RV-05 | **Positive controls.** Reviewer confirms every check's positive control detected its target before accepting any absence or unreachability claim |
| RV-06 | **Per-CVE decisions** use exactly one of: `COMPONENT_ABSENT_IN_FINAL_IMAGE`, `NOT_APPLICABLE_NO_CALLER`, `NOT_APPLICABLE_UNREACHABLE`, `FIXED_VERSION_VERIFIED` (zlib `deb13u1` or later), `BLOCKING`. **Default and fallback: `BLOCKING`.** UNKNOWN never becomes a pass |
| RV-07 | Each decision binds the CVE ID, exact package/library version and hash, image and manifest digests, and the evidence report hashes it relied on |
| RV-08 | **Second reviewer** for every `NOT_APPLICABLE_*` decision, recommended because these accept code that remains present. Adoption is an owner decision |
| RV-09 | Validity at most seven days for admission; any rebuild, dependency or database change invalidates it |
| RV-10 | **Separation of decisions.** The reviewer recommends; the owner separately decides whether reviewed dispositions are accepted for the gate. A review is never a deployment approval |

## 5. Debian trust anchor and signing verifier

| ID | Requirement |
| --- | --- |
| TA-01 | **Independent anchor.** Debian archive primary-key material and full fingerprints for the relevant roles (Trixie archive, Trixie security, Trixie stable release) obtained through **at least two independent authenticated channels, neither derived from the candidate image**. The image's own `debian-archive-keyring` (55,918 bytes, R10) and verifier are circular and are excluded as anchors. The owner names the channels; provenance is recorded |
| TA-02 | **Key validation.** Verify the primary self-signatures and subkey binding signatures cryptographically. Record creation, expiry and revocation status at verification time against a trusted clock. R10's packet-order associations (e.g. subkey `89C87ACE…4BA95` with primary `5E04A1E3…4CCE68C6`) must be proven, not assumed |
| TA-03 | **Verifier provenance.** `sqv` or `gpgv` from a source whose own provenance is independently established, at a pinned version and SHA-256, running on an approved isolated host. The candidate image's `sqv 1.3.0-3+b2` is excluded unless separately authenticated through TA-01 |
| TA-04 | **Signature receipts.** For each `InRelease`: exact bytes and hash, keyring hash, full primary and signing fingerprints, verifier output and exit status, verifier version, time, and per-repository co-signer policy. A self-authored JSON summary isn't a receipt |
| TA-05 | **Freshness and rollback.** Origin, label, suite/codename, architecture, `Date` and `Valid-Until` validated at use time. Expired metadata stops the process (the retained security metadata expires **2026-11-24**). Trixie main has no `Valid-Until` and needs an owner-approved snapshot/freshness policy. No unsigned or older-snapshot fallback |
| TA-06 | **Package chain.** Signed `InRelease`, then `Packages` hash and size, then the package record (name, version, architecture, path, size, SHA-256), then the acquired `.deb` bytes. For zlib: `zlib1g_1.3.dfsg+really1.3.1-1+deb13u1_amd64.deb`, 88,720 bytes, SHA-256 `8c27c342…5ceb`. No mirror, redirect or version substitution |
| TA-07 | **Builder image provenance.** The official builder digest (`05a994d2…4177`) needs either verification of its publisher signature/attestation against an independently established trust root, or an owner-recorded acceptance of hash-pinned, TLS-retrieved provenance with that limitation stated. Silent acceptance isn't allowed |

## 6. Vulnerability database and scanner acceptance

| ID | Requirement |
| --- | --- |
| VS-01 | **Scanner identity.** Exact scanner name, version, binary SHA-256 and independently established provenance, running offline on an approved isolated host |
| VS-02 | **Database authenticity.** Origin authenticated by signature or an independent hash channel; bytes and SHA-256 retained |
| VS-03 | **Size.** The database **as used** (expanded) is ≤ **1,073,741,824 bytes**. Compressed size doesn't count. The historical Trivy database (1,764,941,824 bytes) fails; no compliant source is established yet |
| VS-04 | **Freshness.** The internal update timestamp, verified inside the database rather than taken from registry annotations, is at most seven days old at admission |
| VS-05 | **Completeness.** Covers Debian 13 OS packages, PyPI packages, and runtime components outside dpkg: CPython 3.12.16, cryptography's vendored OpenSSL and Rust crates. Any component the scanner can't evaluate gets a separate reviewed advisory assessment; uncovered ≠ clean |
| VS-06 | **Positive control.** On the control image the scanner must report all nine recorded Highs (and none of the R3-fixed ones), proving database coverage and correct OS detection |
| VS-07 | **Final-image result.** Zero unresolved Critical and zero unresolved High, where "resolved" means only an owner-accepted reviewer decision under RV-06. All other findings recorded |
| VS-08 | **Prohibited without separate owner approval.** Changing the cap, deleting or splitting advisories, substituting summaries, switching scanner/database format, or compacting outside the supported upstream process (R6). Switching scanner is allowed only as an explicitly approved decision meeting VS-01 to VS-07 |

## 7. Approvals, dependencies and stop conditions

### 7.1 External approvals and dependencies

| # | Approval or dependency | Needed for | Depends on |
| --- | --- | --- | --- |
| A1 | Adopt B1-P1 as the implementation target | Everything below | — |
| A2 | Accept `COMPONENT_ABSENT_IN_FINAL_IMAGE` as a gate-disposition basis | Section 2 | A1 |
| A3 | SQLite strategy (S1/S2/S3/S4); for S1, accept `NOT_APPLICABLE_*` decisions and decide on RV-08 | Section 3 | A1 |
| A4 | Reviewer appointment and B1 trust-store enrolment (RV-01 to RV-03) | Sections 2–6 | Independent governance |
| A5 | Trust-anchor channels and verifier (TA-01 to TA-03); builder provenance decision (TA-07) | Section 5 | A4 |
| A6 | Compliant scanner and database (VS-01 to VS-05), or an explicit VS-08 decision | Section 6 | A5 for authenticity |
| A7 | Bounded metadata refresh and acquisition (builder digest, zlib `.deb`, wheels, debug symbols for SQ-F4) | Sections 3, 5, 6 | A5 |
| A8 | Dockerfile/manifest change and lifting the B1 build refusal for this target only | Building the image | A1, A7 |
| A9 | Isolated execution: build, scan, in-container checks and SQ-F3/F4 under the M24 reopening conditions | ABS-10, SQ-S1, SQ-F3/F4, VS-06/07 | M24 isolation prerequisites, A8 |

Recommended order: A1 → A2/A3 → A4 → A5 → A6/A7 → A8 → A9 → review → owner gate decision.

### 7.2 Explicit stop conditions

Stop and report; do not work around:

- **STOP-01** Any trust-anchor channel is derived from the candidate image, or two
  independent channels disagree.
- **STOP-02** Any signature, certification, freshness, `Valid-Until` or package-chain check
  fails, or metadata is expired.
- **STOP-03** Any acquired byte, size or hash differs from the approved record.
- **STOP-04** Any positive control fails to detect its target.
- **STOP-05** ABS-02 shows a path outside the allow-list, or ABS-03 to ABS-09 show any target
  family.
- **STOP-06** SQ-F3/F4 observes FTS5 execution before rejection, or the oracle can't be
  validated.
- **STOP-07** No database meets VS-03/VS-04, or meeting them would need a VS-08 action
  without approval.
- **STOP-08** Any unresolved Critical or High remains without an owner-accepted decision.
- **STOP-09** Reviewer independence, competence or enrolment can't be established, or the
  review has expired.
- **STOP-10** Execution would need network access, elevated privileges or isolation outside
  the approved M24 conditions.
- **STOP-11** Any step would modify historical evidence, frozen layers, existing gates or the
  build-refusal contract beyond A8's scope.

## 8. Assessment

| Item | Status |
| --- | --- |
| Absence evidence specification (ABS-01 to ABS-11) | **COMPLETE (plan)**; NOT_TESTED |
| SQLite applicability specification (SQ-00 to SQ-F5) | **COMPLETE (plan)**; NOT_TESTED; FTS5 outcome genuinely open |
| Reviewer criteria (RV-01 to RV-10) | **COMPLETE (plan)**; no reviewer appointed |
| Trust anchor and verifier (TA-01 to TA-07) | **COMPLETE (plan)**; no independent anchor established |
| Scanner and database (VS-01 to VS-08) | **COMPLETE (plan)**; no compliant database established |
| Implementation or execution | **NO-GO**: needs A1–A9; M23 SECURITY GATE NO-GO unchanged |
