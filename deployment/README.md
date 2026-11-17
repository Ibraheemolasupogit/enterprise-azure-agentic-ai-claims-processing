# Offline deployment tooling — M23 Stage A

Current container deployment status: **DEFERRED — SECURITY GATE NO-GO**. See the [milestone record](../docs/milestones/milestone-23.md) for verified work, unresolved findings and mandatory reopening criteria. Historical acquisition permissions do not authorise new acquisitions, builds or runtime validation; each phase needs separate approval. B1's unconditional refusal remains in force.

Tooling is outside `src/claims_ai`, has no Azure client/credential chain and grants no application authority. It leaves all existing API/UI/MCP/identity/outcome implementations and their default loopback profiles unchanged.

```sh
.venv/bin/python -I -B deployment/foundation.py --root .
make deployment-foundation-check
```

`foundation.py` checks the versioned contract, the 39 unchanged runtime pins, disabled environment/resource gates, key data/network/registry invariants and workflow permissions. It also checks selected guards in locally compiled ARM JSON, without sending that template to ARM. These targeted checks are not a general Bicep evaluator or an independent security certification. Mutation tests exercise unsafe configurations and rejected approval/status claims.

`contract.json` distinguishes 14 mandatory approval gates, dev/test/prod boundaries, missing adapters and optional disabled AI services. Actual subscription/tenant/owner/budget/expiry/approval values are null. Unknown values cannot be interpreted as zero-cost or approved. `--check-deployment` always exits 78, even when an operator supplies claimed approval strings. No approval record is authenticated or executed by Stage A.

## Workflow definitions

Both `.github/workflows/m23-*.yml` files use JSON-compatible YAML so their security structure can be parsed with the Python standard library; the existing PyYAML parser also verifies compatibility in tests. Checkout is pinned to the actual public v7.0.1 commit recorded in `actions-pin.json`, with credential persistence disabled. Hosted runner/action execution itself is NOT_TESTED.

Validation is credential-free, contents-read-only, bounded to ten minutes and performs no installation, image push or cloud call. Deployment has only a manual dispatch trigger. Its preflight always refuses; the separate deployment job has literal `if: ${{ false }}` and an `exit 78` body, with **no login or deployment action**. The future job declares minimal OIDC permission only inside that never-running job and names the environment `m23-dev`, `m23-test` or `m23-prod`.

YAML cannot establish GitHub server-side protection. Actual environment reviewers, prevent-self-review policy, protected branches, fork restrictions, exact repository/environment federation subject, issuer/audience, scoped identities and audit retention are UNVERIFIED. No environment, federated credential, service principal, app registration or IAM grant has been created. These prerequisites require separately authorised administration before any future workflow activation.

## B1 locked supply-chain admission (no build execution)

[Stage B1 contract and acquisition/review procedure](../docs/deployment/m23/stage-b1-supply-chain.md) supersedes the original Stage A executor. `build_container.py --validate-only` now requires a complete source-bound v2 manifest, independently pinned manifest and reviewer trust store, current Ed25519 reviewer signature, verified local base manifest/config/layers/runtime report, all 39 compatible wheel/hash records and bound provenance/licence/SBOM/vulnerability evidence. Manylinux glibc floors, filename/metadata/Requires-Python, ELF AMD64 headers and project source bytes are checked. No dependency is added.

The original `containers/build-inputs.pending.json` is preserved and refused. [Nine new templates](containers/evidence-templates/) remain pending, with absent hashes/signatures and no enrolled keys. A review plan is not a verified physical builder or permission to execute. **All B1 build calls refuse before any subprocess/daemon/network access**, including otherwise valid signed input. There is no automatic download, image pull/build/run/push, signing, or deployment enablement. The future builder requires verified daemon/frontend/RUN isolation beyond `--pull=false`; B1 does not implement or claim that environment.

The existing Dockerfile, UID/GID 10001, allowlisted context helper and host ASGI smoke remain unchanged. Frozen M22 JSON/credentials/runtime databases stay outside the context; public authoring modules remain in the general wheel, so it is not a sealed predictor. Entry/health always exit 78. Input admission PASS is not image/runtime/SBOM reproducibility or Azure acceptance.

For host-only validation without an image:

```sh
PYTHONPATH=src .venv/bin/python -B deployment/containers/smoke.py --fixture-root data/rules/motor/v1
```

This is `IN_PROCESS_ASGI_NOT_TCP_NOT_AZURE`. It does not authorise container execution or live identity/model calls. Preserve all historical evidence; use new paths for any later authorised packet/reports. See [B1 evidence](../docs/milestones/milestone-23-stage-b1.md) for actual test results and unresolved prerequisites.
