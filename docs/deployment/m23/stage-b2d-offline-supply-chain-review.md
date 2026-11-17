# M23 Stage B2D — offline supply-chain security review

**Decision: NO-GO for security acceptance, builds, package/container execution and Azure.** The offline review completed; the frozen base fails B1's zero-unresolved-Critical/High gate and material coverage/approval gaps remain. This is an engineering assessment, not an independent security or licence approval. No risk owner, signature or acceptance was invented.

## Scope and verified inputs

HEAD remains `1ca15877360c0b5af44f6c5c09a351c81c790711`, with earlier uncommitted B1/B2B/B2C work preserved. Both frozen inventory pins and **all 43 B2C binary hashes/sizes** were reverified: 39 dependency wheels and four base layers. A new local OCI layout packages the **unchanged upstream** manifest/config/layers for static scanners; no image was built, imported, pulled or run. Wheel files were unpacked as read-only analysis data, not installed or placed on Python's import path. No downloaded code was imported, loaded or executed.

[SBOM manifest](b2d-sbom-manifest.json), [machine security decision](b2d-security-decision.json) and [new raw evidence](../../../outputs/deployment/m23-b2d/) retain exact formats, inputs, hashes, commands, configuration, scanner logs and findings. Earlier reports/artifacts were not regenerated or overwritten. Existing B1 refusal/deployment controls remain unchanged; M22 independent labels/metrics and AZU-0058 retain their previous pending/unresolved status.

## Offline execution and database freshness

Installed **Syft 1.50.0** and **Trivy 0.72.0** were available. Every actual scan ran under [an OS sandbox profile](../../../outputs/deployment/m23-b2d/scanner.sb) denying **all network operations, including Unix sockets**, blocking execution except installed scanners/launcher, denying credential/Docker socket paths and protecting prior files from writes. Explicit local OCI/directory/SBOM inputs were used. Clean child environments and explicit configuration disabled updates, telemetry, remote enrichment/lookups, VEX updates and implicit ignore files; no registry/daemon fallback was used. Profile initialization inside the outer sandbox was denied, so the same network-denying profile was launched outside that outer sandbox after the permission check. No network probe/request was used to test it.

The original local Trivy DB and a new scan copy remain byte-identical:

- Schema **2**, **1,764,941,824 bytes**; SHA-256 `024e3e42822e93b63a119eae8997d24425a8703b7bb463e5afc1bcec92da2e67`.
- Updated **2026-11-12 18:57:38 UTC**, downloaded **2026-11-12 19:19:23 UTC**; expected next update **2026-11-13 18:57:38 UTC**.
- About **23.38 hours old** at the freshness check: within B1's seven-day window. Online latest/freshness was not checked; **no DB/check/version update occurred**.
- **Admission blocker:** this actual DB exceeds B1's unchanged **1 GiB** database-evidence limit. It is usable by the installed scanner, but cannot honestly pass the existing B1 report contract. No cap was relaxed, database truncated, or small summary substituted for the DB.

## SBOM and scanner coverage

| Scope | Actual coverage | Limit |
| --- | --- | --- |
| Dependency wheels | Syft inventories all **39 exact pins**; Trivy's SBOM path scans all **39 Python targets**, reporting **zero matches** in this DB | Not proof of no vulnerabilities or runtime compatibility |
| Debian base | Syft and direct local-OCI Trivy agree on **105 Debian packages** | Applicability/reachability of source-package advisories requires review |
| Base Python/bootstrap | Syft records **CPython 3.12.16**, **pip 25.0.1** and six vendored launcher records; Trivy scans pip | Base CPython binary vulnerability coverage **NOT_TESTED** in these reports |
| Native files | Syft observes **seven ELF extensions**, hashes, dependencies and static security metadata | File evidence is not complete linked-library decomposition or runtime testing |
| Bundled/native declarations | Four wheel-embedded SBOMs declare **158 component occurrences**. Local deduplication yields **157 library entries** (156 Cargo, one generic OpenSSL), alongside seven observed file entries | Publisher declarations are not independent proof of compiled/runtime linkage; build-only scope is not fully separated |
| Cargo | Trivy scans **156 Cargo targets** from the labelled merged SBOM, reporting zero matches | Conditional on supplied component inventory and this offline DB |
| Bundled OpenSSL | `cryptography` declares **OpenSSL 4.0.3**; its native binary contains `OpenSSL 4.0.3 29 Sep 2026` | Generic PURL produces **zero Trivy targets**: CVE assessment **NOT_TESTED**, not PASS |
| Other C native dependencies | Wrapper files are observed | Complete bundled/dependency inventory for cffi/msgspec/PyYAML/regex remains unproven |

Syft emits genuine Syft JSON, SPDX **2.3** and default CycloneDX **1.7** reports. Trivy emits a diagnostic CycloneDX **1.7** base SBOM. These 1.7 files are retained as produced and are outside B1's 1.6 enum; **they were not relabelled**. B1-compatible SPDX 2.3 outputs exist. The explicit native evidence merge uses CycloneDX 1.6 and labels observed file facts versus publisher-declared library information; it does not claim a complete dependency graph or built image.

## Vulnerability findings

Primary evidence is the **direct exact local-OCI scan**, with no severity/status/ignore suppression. It reports **355 package/CVE occurrences across 158 distinct CVE IDs**:

| Severity | Package/CVE occurrences | Distinct CVE IDs at highest observed severity |
| --- | --- | --- |
| CRITICAL | 2 | 2 |
| HIGH | 96 | 29 |
| MEDIUM | 134 | 62 |
| LOW | 109 | 58 |
| UNKNOWN | 14 | 7 |

[Full findings, affected versions, status, fix availability and component rollups](../../../outputs/deployment/m23-b2d/vulnerability-assessment.json) retain every raw finding. Licence classifier severities are **not included** in these CVE counts.

Critical records requiring disposition:

| CVE | Component/version | Scanner status / fix field | Review requirement |
| --- | --- | --- | --- |
| CVE-2025-7458 | `libsqlite3-0` `3.40.1-2+deb12u2` | affected; no FixedVersion in this DB; NVD Critical | Determine affected feature/reachability and approved remediation; no exploit/runtime testing performed |
| CVE-2023-45853 | `zlib1g` `1:1.2.13.dfsg-1` | will_not_fix; no FixedVersion in this DB; NVD Critical | Title concerns minizip/zipOpenNewFileInZip functionality. Source-package association needs component-specific applicability review; **not automatically a proven exploitable path or a false positive** |

All **98 Critical/High occurrences** lack a FixedVersion field in the current DB. This means no fix is listed for these records in this snapshot, not that no fix exists anywhere. Many High records map multiple installed binary packages to a shared source package, including Kerberos/util-linux; counts do not represent 98 independently demonstrated exploit paths.

Only **six occurrences have listed fixes**, all in vulnerable base **pip 25.0.1**: five Medium and one Low. Listed fixed versions range from 25.3 through 26.2.0. A scanner status of `fixed` denotes upstream fix availability, **not that the frozen installed component is fixed**. No upgrade or remediation was performed. Other statuses are **279 affected / 53 fix_deferred / 17 will_not_fix**. No status is an authorised risk acceptance or suppression. Non-root/disabled hosting is not used to waive findings.

### Scan interoperability and honest NOT_TESTED results

- Initial Trivy filesystem scan recognised zero Python files; that output is **NOT_TESTED for Python coverage**, replaced by the actual 39-target SBOM scan.
- Initial OCI-tar input was unsupported by this Trivy path; the exact local OCI **directory** succeeded. No daemon/registry fallback occurred.
- Feeding Syft's base CycloneDX to Trivy reports only **40 occurrences** and omits **118 primary CVE IDs**. Comparison shows the SBOM import path substitutes Debian binary names for `SrcName` despite Syft's upstream qualifier; source-package mappings are lost. The lower count is **not accepted as the security result**.
- Trivy's own generated base SBOM roundtrip reproduces **all 355 primary occurrences**, with zero missing/extra finding tuples. Both producer paths and all failed/partial diagnostics remain preserved.
- Generic OpenSSL and base CPython CVE coverage remain **NOT_TESTED**; zero-target outputs are not labelled finding-free.

## Licence and provenance review

All 39 main wheel notice inventories remain available (**41 files**), and B2C located mapped copyright for all 105 installed Debian packages plus 14 common texts. Notice availability is not legal acceptance. Trivy classifies 35 wheel entries as `notice`, but leaves **MIT-0 (cffi), Apache-2.0 AND CNRI-Python (regex), and PSF-2.0 (typing-extensions)** unknown. Syft omits the agent-framework-core licence classification even though its retained notice explicitly begins `MIT License`; the file is present, not missing.

Base licence scanning produces **662 classification rows**, including 353 `restricted` and 174 `unknown`; these are repeated tool licence classifications, **not CVEs, legal violations or project-policy determinations**. Copyleft, exception and redistribution obligations need authorised review. Of the 157 merged library entries, **rpds-py root and OpenSSL** lack a declared licence in their supplied component records. This does not negate the rpds wheel's main notice or prove an absent notice. Per-component bundled/Cargo/OpenSSL notice mappings remain incomplete. The project wheel's distribution-licence/source-bound review remains separate and pending.

Independent local checks verify **all 39 wheel RECORD inventories/digests/sizes** and **all four uncompressed OCI layer diff IDs** against the original config. B2B's image/source/catalog/provenance hash links remain intact; OpenSSL's static string corroborates its declared version. These checks establish byte consistency, **not publisher/builder ownership, upstream signature validity or truthful full dependency provenance**. The existing DB cache was hashed and checked for freshness, but its upstream signature/origin was not independently authenticated offline. No offline trusted signer/key material or genuine independent reviewer approval was supplied. Those statuses remain NOT_VERIFIED/PENDING; no signature or reviewer was created.

## Decision, required corrective work and preservation

**NO-GO.** The frozen base has unresolved Critical/High findings; licence, native/CPython coverage and authenticated review remain incomplete, and the real DB cannot pass the current B1 evidence-size gate. Preserve this candidate and all failures as historical evidence. Separately authorise a revised candidate/remediation or supported component-level applicability dispositions, then rescan with full coverage. Do not silently upgrade packages, change the frozen inventory, ignore findings, waive `will_not_fix`, or relabel unsupported SBOM formats. Any bounded B1 database-contract correction requires separate review and tests.

Required reviewers must reconcile source-package applicability and reachability; approve licence/notice obligations and bundled components; verify provenance/trust; and sign actual source-bound evidence through independent enrolment. Genuine base-runtime observation and physical **BuildKit** isolation remain unexercised. The scanner sandbox is not proof of builder isolation. B1's unconditional refusal remains intact; no build, package/container execution or Azure operation is authorised.

All **1,140 prior files/evidence remain byte-identical** against the new preservation baseline. All 39 scanner analysis trees also match their original wheel RECORD/member inventories. No installation, dependency change, external request, Docker operation, Azure access, staging, commit or push was performed. Existing application/full-pytest results were not regenerated; the review ran only trusted installed scanners and data-validation tooling. No M24 work. Stop after B2D.
