"""Explicit byte-bearing M12 recovery, with same-runtime compatibility only."""

import asyncio
from base64 import b64decode, b64encode

from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.validation import VerifiedAdvisory, verify_advisory
from claims_ai.models import Case, CaseState
from claims_ai.outcomes.contracts import ApprovedInput, OutcomeError, RecoveryBundle
from claims_ai.rules.specification import digest
from claims_ai.workflow.engine import code_fingerprint


def unpack(bundle: RecoveryBundle) -> VerifiedAdvisory:
    bundle = RecoveryBundle.model_validate(bundle)
    if bundle.runtime_sha256 != code_fingerprint():
        raise OutcomeError("incompatible_runtime")
    if len(json_bytes(bundle.model_dump(mode="json"))) > 12582912:
        raise OutcomeError("recovery_capacity")
    if len(bundle.contents) != len(bundle.request.evidence_inputs):
        raise OutcomeError("missing_recovery_bytes")
    inputs = []
    total = 0
    for original, encoded in zip(bundle.request.evidence_inputs, bundle.contents, strict=True):
        content = b64decode(encoded, validate=True)
        if b64encode(content).decode() != encoded:
            raise OutcomeError("noncanonical_recovery_bytes")
        total += len(content)
        if total > 8388608:
            raise OutcomeError("recovery_capacity")
        inputs.append(
            original.model_copy(
                update={"request": original.request.model_copy(update={"content": content})}
            )
        )
    request = bundle.request.model_copy(update={"evidence_inputs": tuple(inputs)})
    return asyncio.run(verify_advisory(request, bundle.grant, bundle.checkpoint, bundle.limits))


def verify_approval(approval: ApprovedInput) -> VerifiedAdvisory:
    approval = ApprovedInput.model_validate(approval)
    source = unpack(approval.bundle)
    snapshot = source.snapshot
    index = snapshot.index
    if index is None or snapshot.retrieval_response is None:
        raise OutcomeError("missing_policy")
    policy = next(
        e.policy for e in index.entries if e.policy.version == source.initial.binding.policy_version
    )
    revision = (
        snapshot.case.revision if approval.parent is None else approval.parent.case_revision + 3
    )
    expected = Case.model_validate(
        {**snapshot.case.model_dump(), "policy": policy, "revision": revision}
    )
    assessment = approval.assessment
    if (
        approval.case != expected
        or expected.state != CaseState.ASSESSING
        or assessment.claim_id != expected.claim.claim_id
        or assessment.case_revision != revision
        or assessment.policy != policy
        or assessment.input_sha256 != digest(expected.model_dump(mode="json"))
        or set(assessment.evidence_ids) != {e.evidence_id for e in expected.evidence}
        or not assessment.citations
        or not set(assessment.citations)
        <= {h.chunk.clause.citation for h in snapshot.retrieval_response.hits}
        or source.initial.required_reviewer == "supervisor"
        and not assessment.requires_supervisor
        or approval.approved_by in source.initial.producer_ids
    ):
        raise OutcomeError("unapproved_assessment_binding")
    return source
