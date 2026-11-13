# Offline deployment tooling — M23 Stage A

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

## Locked local Linux build contract

`containers/build-inputs.pending.json` records the exact existing 39 runtime versions and leaves Linux base/wheel hashes and review evidence absent. It is deliberately **not buildable**. Do not replace absent hashes with invented digests or reuse macOS native wheels as Linux evidence.

A future separately retained, genuinely reviewed input manifest must contain:

- `status=REVIEWED_LOCAL_BUILD_INPUTS`, `platform=linux/amd64`, Python minor 3.12 and a positive source-date epoch.
- An independently retained manifest SHA-256 and a cached official Python base referenced as `docker.io/library/python@sha256:…`, with actual digest/provenance review.
- Exactly one Linux/Python-compatible wheel for each of the 39 pinned distributions, plus a byte-matching project wheel. Every basename and SHA-256 is bound; native macOS/other-architecture wheels, unsafe ZIP paths, `.pth` injection and mismatched metadata are rejected.
- Actual base/licence/vulnerability review evidence and the current application-source fingerprint. These records are artifact review inputs, not an authenticated human-identity or cloud-approval mechanism. The trusted operator must obtain the input pin independently.

Only after those inputs exist, the local-only command is:

```sh
.venv/bin/python -B -m deployment.build_container --root . \
  --manifest /absolute/path/to/reviewed-linux-inputs.json \
  --artifacts /absolute/path/to/reviewed-wheels \
  --trusted-manifest-sha256 ACTUAL_INDEPENDENT_MANIFEST_SHA256
```

The command validates inputs **before invoking Docker**, requires a local Unix-socket daemon and an already cached base, and never downloads/pushes anything. Build steps use no network, no index, no dependency resolution and hash-required wheels. An isolated allowlisted context contains only the Dockerfile/scripts, wheels and the three original provisional M9 fixture files needed for smoke tests. It contains no frozen M22 candidate/reviewer JSON files, `.git`, `.env`, credentials, SQLite state, historical outputs or unrelated data. The general application wheel still includes public reference-authoring modules; it is not a sealed or approved held-out prediction environment. Future predictor isolation must exclude that authoring access separately.

The multi-stage image runs as UID/GID 10001, with no apt/curl installation. The local smoke contract uses the resulting image ID rather than a mutable tag, `--pull=never`, no network, read-only root, bounded tmpfs/CPU/memory/PIDs, dropped capabilities and no-new-privileges. It exercises actual local API/UI ASGI and three governed MCP SDK reads, then checks that default cloud startup still exits 78. No socket hosting, cloud health, live Entra, real model or independent quality is claimed. Repeat builds must compare application/dependency inventories and image digests; byte-identical OCI output is not claimed without an exercised deterministic builder/base/toolchain record.

`containers/entrypoint.py` never starts a demo server, listens publicly or reads credentials. Even an enabling environment variable cannot bypass the refusal. Its Docker health check is intentionally unsuccessful. A cloud-ready entrypoint remains a required future implementation; Stage A must not disguise missing adapters behind healthy probes.

For host-only validation of the same ASGI contract, without building an image:

```sh
PYTHONPATH=src .venv/bin/python -B deployment/containers/smoke.py --fixture-root data/rules/motor/v1
```

This is explicitly `IN_PROCESS_ASGI_NOT_TCP_NOT_AZURE`; it is not container execution. Under this Stage A run Docker is available but no Python base is cached and no reviewed Linux wheel inventory exists. No image was pulled or built. See [milestone evidence](../docs/milestones/milestone-23-stage-a.md) for actual checks and remaining limits.
