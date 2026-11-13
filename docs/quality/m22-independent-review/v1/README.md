# M22 independent golden-suite review packet — v1

**REVIEW PREPARATION ONLY. All 60 cases are PENDING_REVIEW. Every label is an author proposal; none is independently approved ground truth.** No review identity, decision, signature or approval is supplied. The benchmark is not released, independent-quality metrics remain NOT_TESTED, and no scored evaluation is performed.

## Submitted version and contents

Candidate: `data/evaluation/m22/v1`, native-text/control fixtures, not scanned PDFs, photographs or OCR/model results. Distribution: **15 ordinary damage / 10 exclusions and dates / 10 evidence problems / 10 policy boundaries / 10 security / 5 recovery**.

Trusted candidate-manifest SHA-256: `42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b`.

- [Case inventory](case-inventory.md): 60-row navigation and author hypothesis/route summary.
- [Case notes](case-notes.md): all five field proposals per case, exact source pointers/native lines, policy bindings, rule/route/financial/control proposals and case-specific questions.
- [Submission manifest](submission-manifest.json): all eight original artifact hashes/sizes, exact case/input/reference/review bindings and per-asset UTF-8 hashes. Per-case hashes use sorted, indented JSON with `ensure_ascii=True`, `allow_nan=False` and a final newline, matching the original review bindings. Whole-file hashes always use original bytes.
- [Checklist](checklist.md): correctness, provenance, ambiguity, applicability, independence, exposure and leakage checks.
- [Adjudication template](adjudication-template.json): 60 pre-bound cases, all pending with null reviewer/decision/approved-label fields.
- [Separate release-approval template](release-approval-template.json): adjudication authentication, exposure/scope decisions, service mapping and all 12 unchanged frozen metric proposals. No release authority is asserted.
- [Verification record](verification.json) and [packet hash inventory](hash-inventory.json): preparation/integrity evidence, not correctness approval. Obtain the packet inventory pin independently from the [M22 evidence addendum](../../../milestones/milestone-22-stage-b.md#independent-golden-suite-review-packet).

The packet and the eight original files listed by the submission manifest form the reviewer handoff; retain their repository-relative paths so source links work. Supply those exact existing bytes, not regenerated candidates. These documents do not copy or activate a prediction dataset. Earlier Stage B wheels/reports remain historical and have not been regenerated to include this later packet.

## Reviewer procedure

1. A real evaluation owner selects a reviewer independent of label authoring, prediction implementation and tuning. The reviewer records actual identity, role, conflicts, prior case/code/label exposure and any previous model/training use. No independence can be inferred from these blank templates. Hashes establish integrity, not identity or an attestation.
2. Verify the independent candidate pin, packet pin and all file/case/asset bindings before reviewing. Read the [original reference guide](../../../../data/evaluation/m22/v1/references/guide.md), [frozen gates](../../../../data/evaluation/m22/v1/gates.json) and [Stage A procedure](../../m22-stage-a-contracts-and-holdout.md). Historical Stage A statements predate Stage B; the preserved labels still have no operational adapter or independent scoring approval.
3. Inspect original native source text first, then compare each author's proposal. Complete a copy of the adjudication template in a new separately retained review record outside this packet and the frozen candidate directory. Apply the checklist to every case and supply source/line rationale, including null/conflict labels and capability gaps.
4. Choose **ACCEPT_PROPOSAL**, **REJECT** or **REQUEST_CORRECTIONS** for each case in that separate record. Acceptance means the actual reviewer agrees with the documented proposal for an explicit scope; it is not a runtime permission or release. For rejection/corrections identify the exact disputed field/clause/control, evidence, proposed correction and rationale. Do not silently drop difficult cases or change denominator rules. All 60 must be resolved, or a new reviewed version must define the revised roster/scope.
5. Any source, label, clause-relevance, gate or roster correction requires a new candidate version and a new hash/review cycle. Leave v1 and its pending templates unchanged. Preserve disagreements and append superseding records rather than rewriting prior decisions. Genuine accepted labels must be bound to a separately authenticated independent adjudication record; a copied proposal or an APPROVED string is insufficient.
6. A real evaluation/release owner separately completes a copy of the release template, authenticates the completed adjudication, resolves exposure/holdout eligibility, reviews every gate/denominator/applicable capability and approves exact source/service/policy/rule/index mapping plus predictor isolation/freeze. Record actual identity/time and attestation provenance only when supplied. Use authentic signatures only if actually provided and independently verifiable; hashes are not signatures.
7. **Stop at the review/release decision.** Neither template is consumed by runtime code. Stage B's independent-scoring guard remains unconfigured and rejects even a claimed approval. Actual scoring/release integration requires separately authorised work and capability evidence; this packet supplies no switch to enable it. Original cases remain PENDING_REVIEW in all circumstances under this task.

## Leakage and exposure boundaries

This is a **reviewer-only, label-bearing packet**. Never put it, reference proposals, review records, release templates or reference-authoring modules in a prediction workspace, model prompt, tool response, runtime telemetry or tuning set. Reference review is deliberately allowed for the human reviewer and trusted scoring coordinator; it is not prediction access.

The future predictor input view is exactly `inputs/manifest.json` and `inputs/cases.json`, with the independent input-manifest pin `05a8829d55e86bd8d6ee23aadbcb7a87b9a75e2473c5b3bc393ec99bc7791988`. The current input loader opens only those two files. This task changes neither bytes, schema nor loader/runtime paths. This contract does not provide an OS filesystem sandbox. Keep reviewer materials on a separately controlled filesystem/access boundary, freeze prediction code/configuration before future prediction access, and retain an actual access/exposure record.

The suite and authoring code have already been visible in this repository. Opaque IDs, separate files and an independent label review do **not** restore blindness or demonstrate absence of training contamination. Scenario names/fault hints, narratives and synthetic metadata can reveal intended controls. Review whether that exposure invalidates the intended holdout; if necessary obtain genuinely independent, unexposed cases in a new version. Do not tune against this packet, then claim held-out quality.

M22 fictional 2028/2029 policies and excess/cap illustrations are not the existing provisional M9 rules or approved insurer terms. Requested version, source date and policy bundle must bind exactly; no date-based version fallback is authorised. Missing source values must not be filled from intake metadata without an explicitly reviewed rule. Security/recovery narratives and fault strings are proposed scenarios, not supplied live grants, sessions, ledgers, indexes or process evidence. Stage B's 17 operational controls use separate synthetic fixtures and do not score these 60 cases. Missing adapters, live-model/OCR capability, approved workload and human studies remain NOT_TESTED.

## Read-only hash verification

Use Python 3.12 and replace the second argument with the independently retained packet inventory SHA-256 from the M22 addendum. This reads bytes only; it does not import application code, create artifacts, contact services, run a predictor or authenticate a review.

```sh
python3 -B - docs/quality/m22-independent-review/v1 'REPLACE_WITH_TRUSTED_PACKET_PIN' <<'PY'
import hashlib, json, pathlib, re, sys
packet = pathlib.Path(sys.argv[1]).resolve(strict=True)
pin = sys.argv[2]
assert re.fullmatch(r"[0-9a-f]{64}", pin), "supply independent packet pin"
raw = (packet / "hash-inventory.json").read_bytes()
assert hashlib.sha256(raw).hexdigest() == pin
inventory = json.loads(raw)
assert {p.name for p in packet.iterdir() if p.is_file()} == set(inventory["files"]) | {"hash-inventory.json"}
for name, binding in inventory["files"].items():
    path = packet / name
    assert path.resolve().is_relative_to(packet) and not path.is_symlink()
    data = path.read_bytes()
    assert len(data) == binding["bytes"]
    assert hashlib.sha256(data).hexdigest() == binding["sha256"]
submission = json.loads((packet / "submission-manifest.json").read_bytes())
repo = packet.parents[3]
for name, binding in submission["files"].items():
    path = repo / name
    assert path.resolve().is_relative_to(repo) and not path.is_symlink()
    data = path.read_bytes()
    assert len(data) == binding["bytes"]
    assert hashlib.sha256(data).hexdigest() == binding["sha256"]
assert submission["candidate_manifest_sha256"] == "42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b"
assert not submission["scored_evaluation_allowed"] and not submission["benchmark_released"]
print("Packet/source byte integrity verified; independent correctness/review not approved.")
PY
```

Record completed review results separately; never edit the published packet or original pending templates. Read-only files and hashes are trusted-host process safeguards, not WORM storage or protection from replacing both artifacts and external pins.
