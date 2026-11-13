# M22 Stage A candidate suite

**60 candidates; all PENDING_REVIEW. No scored evaluation or independent approval.**

Version `v1` is a native-text/control candidate set with cohort counts **15/10/10/10/10/5**. It is author-visible, not a sealed blind benchmark. See the [construction and review contract](../../../docs/quality/m22-stage-a-contracts-and-holdout.md) and [Stage A milestone](../../../docs/milestones/milestone-22.md).

The independently retained SHA-256 of `v1/candidate-manifest.json` is:

`42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b`

`inventory.json` contains exact per-file byte sizes and SHA-256 values. Inputs additionally contain per-asset UTF-8 content hashes; labels/reviews bind individual input/reference/gate hashes. The candidate manifest is externally pinned rather than included in its own inventory. Six authoring modules are bound by the manifest's authoring hash.

Prediction access is restricted by contract to `inputs/manifest.json` and `inputs/cases.json`; the caller supplies the independently pinned input-manifest hash from the trusted candidate record. Reference labels/guide and review templates are outside that view. The input loader does not provide OS isolation: public authoring code and labels remain readable to this checkout's owner. Genuine independent holdout review/exposure controls remain outstanding.

Candidate files are created exclusively and made read-only. Owner replacement of both artifacts and pins remains outside this trusted-host integrity guarantee. Changes require a new version; approval is a separate real review/release record, not an edit to pending v1 files. No reviewer, signature, claim decision or current application authority is invented or restored from these files.

For a fresh construction/reproducibility copy, use a **new directory**:

```sh
PYTHONPATH=src .venv/bin/python -B -m claims_ai.quality_ops.candidate \
  --repository-root . --output /tmp/new-m22-stage-a-copy
```

An existing destination fails. Historical `data` namespaces and `outputs` are refused. No predictor, evaluator, telemetry provider or installation is run by this command. Missing/altered files and incorrect independent pins reject verification; there is no automatic repair or overwrite.

All policy/rule/disposition labels are fictional author proposals. There are no scanned PDF/photo fixtures, OCR/model outputs, live identity or real insurance authority. M4/M8/M19 inputs and all historical outputs remain unchanged.
