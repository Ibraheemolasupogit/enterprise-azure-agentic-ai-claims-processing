# Milestone 19 — targeted F-001 / F-002 remediation

Status: **COMPLETE — F-001 and F-002 closed for the demonstrated offline paths**. Verification date: **2026-11-10**. This is the explicitly authorized narrow correction after the [original M19 acceptance record](milestone-19.md), which remains unchanged. No M20 work, cloud integration, new dependency, agent, policy-rule change or insurance outcome authority is included.

## Root causes and corrections

**F-001 / R-008, contextual Medium.** The consumer previously accepted two congruent representations of the same untrusted MCP result without independent source binding. `mcp_server.client.checked` now rejects a successful response unless the caller supplies the independently loaded host `AssessmentInput` and the actual requested tool. Existing M6/M7/M9 `prepare_packet` replay verifies source bytes/rendering and ownership, policy/version/date/index, evidence provenance, rule findings and retrieval. The consumer compares the returned tool, independently rebuilt packet fingerprint and **complete typed data**, including every policy clause, citation, source line and chunk, against that host snapshot. Response-provided hashes or a rehashed forgery cannot replace the comparison.

Native stdio, the sequential Agent Framework parser, HTTP roundtrips and the adversarial probe all supply that host context. Safe error envelopes remain decodable without it and cannot expose successful data. Missing or corrupted local context fails closed. The host input is not accepted from an MCP response or caller identity field. Existing manifest-pinned demo artifacts remain provisional synthetic authority; this does not create an approved insurance-policy register or authenticate a remote provider.

**F-002 / R-009, contextual Low.** The M9 CLI previously guessed a protected `data` tree from the process working directory. It now protects the explicit specification root and conventional `data` ancestors of both its lexical and canonical paths. Separate/nonstandard trees can be supplied through repeated absolute `--protected-data-root` arguments. Roots must exist and be directories. Output and root paths are resolved before overlap checks, covering traversal and symlink aliases; ancestor overlaps, existing files and symlink leaves also fail closed. Binding is checked before evaluation and again before writing; exclusive creation is retained. No historical dataset is modified.

The local operator must configure every separate trusted data root. This protects declared paths and static aliases under the existing trusted-host/filesystem assumption, not malicious concurrent directory replacement or a compromised OS. Default repository-root CLI use and valid new output destinations retain their intended behavior.

## Before and after evidence

| Boundary | Original evidence | Corrected runtime evidence |
| --- | --- | --- |
| F-001 / ADV-MCP-09 | FAIL: consistently changed policy text returned; source report SHA-256 `7e3faefd23333482f6fe5a7e318edf731188ab389471807ff8b85265a0354804` | PASS: actual MCP SDK response obtained, then manipulated; production consumer rejects it with the independent host snapshot. Matching legitimate responses from all three tools still pass |
| Coherent/partial forgery | Congruence alone was insufficient | Consistent and partial alterations, real other-case/version replies, a fully re-rendered/rehashed alternate policy source, copied expected packet hashes, absent context and corrupted local sources are rejected |
| F-002 | Separate ancillary FAIL: outside-directory M9 CLI created a new sibling-data report; original evidence hash `a3fd250f67bdc05fd9a9c306f1b601a783cace86a0fe5e0fb06ab109a2232bae` | Outside-checkout actual CLI probes reject sibling/specification output, traversal, directory/leaf aliases, symlinked input roots, explicit protected roots and existing evidence; legitimate external output still succeeds |
| Full unchanged catalog | **79 PASS / 1 FAIL / 8 NOT_TESTED**, 88 cases | **80 PASS / 0 FAIL / 8 NOT_TESTED**, same 88 attempts and criteria; F-002 remains separate from this catalog |

New reports use `outputs/adversarial/m19-remediation-*`; the original M19 JSON, ancillary finding and package/report artifacts are not overwritten. The unchanged catalog/manifest/guide retain their original authored source context; this addendum records current behavior. An old installed baseline run also reproduces the original report byte for byte, separately labeled `m19-remediation-baseline-installed.json`.

Current regression expectations change only after actual behavior changes. CLI success for the corrected catalog is exit **0**; a counterfactual authored criterion over a genuine identity verification still produces a complete FAIL report and exit **2**. All eight production cases remain NOT_TESTED, not blocked attacks.

## Validation

| Check | Result |
| --- | --- |
| Focused MCP/HTTP/rules/adversarial/remediation regression | **306 passed in 56.76 seconds** |
| Final focused adversarial/remediation regression | **153 passed in 27.42 seconds**, including 38 new remediation tests and retained failing-criterion CLI behavior |
| Full source | **1,128 passed in 321.61 seconds**: previous 1,090 plus 38 new remediation cases |
| Independent installed-wheel | **1,128 passed in 323.65 seconds**, no warnings; isolated Python, separate wheel target, pytest source path replaced and all loaded application origins checked |
| Ruff / strict mypy | Pass, including **130** source/test Python files |
| Dependency / packaging | `pip check` and all **37** existing nested pins pass; zero new dependencies. Offline wheel/source archive; all **106** runtime files match source/wheel/tested target, and all **363** nonignored repository files match the source archive |
| Preservation | All **137** pre-existing output artifacts, all **164** reference-data files (including unchanged M19 catalog/manifest/guide), and all original milestone records remain byte-identical; only the live roadmap changes among prior milestone-directory files |
| Other contracts | Historical M16 OpenAPI remains byte-identical; APIM templates and existing source outside the five authorized runtime files are unchanged |

Two source reports and one independent installed-wheel report are byte-identical: `outputs/adversarial/m19-remediation-source-verified-a.json`, `m19-remediation-source-verified-b.json` and `m19-remediation-wheel-verified.json`. Common SHA-256: **`08bd7136c68eda874e618a99328283d08ed2976381258872ff019861ce849821`**. Runtime fingerprint: **`b627b3e63ba684c7786de12c540f098a30efce2e353b408973be7248890b62bb`**. All record zero socket attempts, Azure operations, live model calls and observed operational outcomes, with a complete harness.

F-002's nine additional runtime checks produce byte-identical source/wheel reports at `outputs/adversarial/m19-remediation-paths-source.json` and `m19-remediation-paths-wheel.json`, SHA-256 **`a82025c792092867bf7ae06774682c0430f146e08d322aa90e2f25952c90e425`**. These checks are separate from the unchanged 88-case catalog. `outputs/adversarial/m19-remediation-summary.json` binds before/after observations, the unchanged attempts/criteria and eight NOT_TESTED identities, code/report hashes and preservation results. Package artifacts, independent pytest log and byte/hash verification are under `outputs/packages/m19-remediation/`.

The independent installation shares pinned dependencies. Older CLI tests retain intentional source-launch paths; the corrected adversarial CLI and M9 path probes are additionally launched outside the checkout against the independent installation. Normal isolated installed imports succeed without `PYTHONPATH`; no editable installation is relied on.

## Files changed

Five existing runtime files: `mcp_server/client.py`, `mcp_server/__main__.py`, `mcp_http/transport.py`, `rules/__main__.py` and `adversarial/runtime.py`. Existing `test_mcp_server.py` supplies expected host context for successful reads; `test_adversarial.py` verifies corrected observations and retains real failed-criterion exit behavior. New `tests/test_m19_remediation.py` adds the 38 focused cases. README, threat/security/target architecture, risk register, traceability and roadmap are updated, with this new addendum. Exact paths and artifact hashes are recorded in `outputs/packages/m19-remediation/package-verification.json`. No dependency, dataset, original milestone record or original report is rewritten.

Reproduction uses the existing extras/constraints. Run `PYTHONPATH=src .venv/bin/python -m pytest tests/test_m19_remediation.py tests/test_adversarial.py` and `PYTHONPATH=src .venv/bin/python -m claims_ai.adversarial --output outputs/adversarial/new-remediation-report.json`. For an outside-directory rules launch, pass an absolute `--spec-root`; add absolute `--protected-data-root` arguments for any independent data trees. Regression tests use temporary copied specifications, not writes into historical data.

## Remaining scope and acceptance

**Recommendation: close F-001 and F-002 within their demonstrated offline scope.** Source, independent installed-wheel and packaging evidence support both corrections. This does not close broader M3 production risks. Live-model semantics, real Entra/JWKS/APIM/TLS/private ingress, distributed DoS/cost controls, hard CPU isolation, browser/session delivery/accessibility, durable audit/shared concurrency, hostile native parsers and vector poisoning remain NOT_TESTED. M8's Q-007/Q-012/Q-015/Q-029 failures, M12 timing-dependent retry/reproducibility and M15/M17/M18 limitations are preserved.

No Azure operations or spending, autonomous outcomes, Git staging/commits/pushes or M20 implementation. Stop after this remediation.
