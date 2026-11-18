# M23 R7 — Agent Framework licence evidence reconciliation

**PENDING_REVIEW. Proposed SPDX expression: `MIT`. Licence conclusion: `NOASSERTION`.** Static integrity/traceability reconciliation completed on 2026-11-18 at HEAD `ec39d8d5f28dbe5e854ce9cba39ae14c40b37e36`. This is not licence approval, a regenerated SBOM or security acceptance. [Machine evidence and verification](r7-agent-framework-licence-reconciliation.json) retains complete source hashes and review fields; reviewer identity, approval and signature remain null.

## Verified wheel-to-notice chain

| Evidence | Verified value |
| --- | --- |
| Distribution/version | `agent-framework-core==1.23.0` |
| Exact wheel | `agent_framework_core-1.23.0-py3-none-any.whl`; **829,938 bytes**; tag `py3-none-any` |
| Actual wheel SHA-256 | `b16e8b44c0033e28d339d03d3b6367f0bec2dd8da9d533b8ba6c278d6a72bd01` |
| Notice member | `agent_framework_core-1.23.0.dist-info/licenses/LICENSE`; **1,141 bytes** |
| Actual notice SHA-256 | `c2cfccb812fe482101a8f04597dfc5a9991a6b2748266c47ac91b6a5aae15383` |
| Syft package | `pkg:pypi/agent-framework-core@1.23.0`, artifact `ff2e9cf45308a174`, Syft **1.50.0**, `python-installed-package-cataloger` |
| Original Syft classification | `licenses: []`; unchanged |

The actual local wheel matches the retained hash-pinned **[B2B inventory](b2b-acquisition-inventory.json)** and **[B2C inventory](b2c-artifact-inventory.json)** records and the retained acquisition receipt, by exact filename, size and SHA-256. These pins establish consistency with retained evidence, not independent publisher authentication.

Non-executing ZIP inspection confirms METADATA name/version, WHEEL tag and the exact notice member. The member bytes match the [retained B2C notice](../../../outputs/deployment/m23-b2c/notices/wheels/agent-framework-core/agent_framework_core-1.23.0.dist-info/licenses/LICENSE), its recorded hash/size and the B2D analysis-tree copy. The wheel's RECORD entry records the same digest/size within that hash-bound archive. Syft's own package file inventory also carries that member's matching digest/size. The original [Syft JSON](../../../outputs/deployment/m23-b2d/wheels.syft.json) matches its recorded [SBOM-manifest](b2d-sbom-manifest.json) hash. No wheel was installed, imported or extracted into a new runtime tree.

## Omission cause: UNKNOWN

The retained notice begins `MIT License`, names Microsoft Corporation and includes permission, notice-retention and warranty/disclaimer terms supporting the **proposed** MIT mapping. Wheel METADATA contains `Classifier: License :: OSI Approved :: MIT License` and `License-File: LICENSE`; `License` and `License-Expression` fields are absent.

Despite the notice being present in its analysis tree and file inventory, Syft emitted an empty package licence list. Retained configuration has `license.content=all` and Python remote licence lookup disabled, as required for the offline scan. The retained wheel-scan log contains only a directory-source naming warning, without a package-specific explanation. These observations do **not** establish which parser, matching rule or catalogue behaviour caused the omission. Missing explicit metadata fields and disabled remote lookup are not proven causes, and no Syft implementation defect is asserted. No diagnostic rerun or source-code experiment was performed. **Root cause remains UNKNOWN.**

## Proposed mapping and verification result

The separate R7 annotation proposes `MIT` for this exact wheel/PURL and notice hash. It does not replace the original empty Syft classification, change publisher metadata, conclude a licence for dependencies/bundled components, or satisfy B1's complete licence/admission report requirements.

**Verification result: wheel identity, recorded/actual hashes, notice bytes, RECORD linkage and Syft file-inventory linkage MATCH. Review status: PENDING_REVIEW.** The JSON records the metadata/member hashes, immutable input references, performed checks and unchanged-file verification. B2B/B2C inventory pins, acquisition-receipt pin and Syft report pin were rechecked; no scanner or runtime result was regenerated.

An independent reviewer must inspect the exact notice and scope, confirm or reject the proposed SPDX expression and applicable notice/redistribution obligations, and provide a genuine source-bound review through the established approval process. No reviewer identity, approval, time or signature is supplied by R7. Retained local wheel, notice and raw scanner outputs remain ignored/local-only; only this documentation/annotation is new.

All historical evidence and application/dependency/security-gate files are preserved. No downloads, builds, Docker, acquired-code/application/scanner execution, cloud access, vulnerability remediation, staging, commits or pushes occurred. **M23 remains DEFERRED — SECURITY GATE NO-GO; B1 build refusal is unchanged.**
