"""Pure provisional findings with independently gated policy/evidence inputs; never outcomes."""

from hashlib import sha256

from claims_ai.benchmark.contracts import Provider
from claims_ai.evidence.contracts import Disposition, EvidenceRecord
from claims_ai.evidence.processing import process_extraction
from claims_ai.knowledge.ingestion import parse_policy, register_conflicts
from claims_ai.models import (
    CaseState,
    DocumentKind,
    PolicyArtifact,
    PolicyCitation,
    ReviewerRole,
    RiskFlag,
    ScanStatus,
)
from claims_ai.rules.contracts import (
    Calculation,
    EvaluationRequest,
    EvidenceProvenance,
    RuleEvaluation,
    RuleFinding,
    RuleId,
    RuleSpecification,
    Terms,
)
from claims_ai.rules.contracts import (
    FindingStatus as Status,
)
from claims_ai.rules.specification import clause_texts, digest, pence


def evaluate(request: EvaluationRequest, specification: RuleSpecification) -> RuleEvaluation:
    request = EvaluationRequest.model_validate(request)
    spec = RuleSpecification.model_validate(specification)
    case = request.case
    case_hash = digest(case.model_dump(mode="json"))
    spec_hash = digest(spec.model_dump(mode="json"))
    flags = set(request.risk_flags)
    if case.assessment is not None:
        flags.update(case.assessment.risk_flags)
    findings: list[RuleFinding] = []
    provenance: list[EvidenceProvenance] = []
    terms: Terms | None = None
    citations: dict[str, PolicyCitation] = {}

    def finding(
        rule: RuleId,
        status: Status,
        explanation: str,
        *,
        issues: tuple[str, ...] = (),
        records: tuple[EvidenceRecord, ...] = (),
        calculation: Calculation | None = None,
    ) -> None:
        definition = next(r for r in spec.rules if r.rule_id == rule)
        findings.append(
            RuleFinding(
                rule_id=rule,
                status=status,
                specification_sha256=spec_hash,
                specification_pointer=f"/rules/{list(spec.rules).index(definition)}",
                citations=tuple(citations[c] for c in definition.clauses if c in citations),
                evidence_ids=tuple(sorted({r.evidence.evidence_id for r in records})),
                fact_ids=tuple(sorted(f.fact_id for f in request.reviewed_facts)),
                issues=tuple(sorted(set(issues))),
                explanation=explanation,
                calculation=calculation,
            )
        )

    binding_issues = []
    binding_status = Status.INDETERMINATE
    try:
        if request.specification_sha256 != spec_hash:
            binding_issues.append("specification_mismatch")
        if case.state != CaseState.ASSESSING:
            binding_issues.append("case_not_assessing")
        if request.policy_id != case.claim.policy_id:
            binding_issues.append("policy_identity_mismatch")
            binding_status = Status.FAIL
        index = request.index
        if index is None:
            binding_issues.append("policy_index_missing")
        else:
            if index.claim_id != case.claim.claim_id or index.policy_id != case.claim.policy_id:
                binding_issues.append("index_scope_mismatch")
            if (
                index.index_sha256
                != digest(index.model_dump(mode="json", exclude={"index_sha256"}))
                or index.issues
            ):
                binding_issues.append("index_unverified")
            policies = tuple(e.policy for e in index.entries)
            if register_conflicts(policies):
                binding_issues.append("conflicting_policy_versions")
                flags.add(RiskFlag.CONFLICTING)
            for entry in index.entries:
                if parse_policy(case, entry.policy, entry.sources) != entry:
                    binding_issues.append("policy_source_mismatch")
                if any(s.document.scan_status != ScanStatus.ACCEPTED for s in entry.sources):
                    binding_issues.append("policy_document_quarantined")
            selected = [e for e in index.entries if e.policy.version == request.policy_version]
            matching = [t for t in spec.terms if t.policy_version == request.policy_version]
            if len(selected) != 1 or len(matching) != 1:
                binding_issues.append("exact_policy_version_missing")
            else:
                entry, terms = selected[0], matching[0]
                if case.policy is not None and case.policy != entry.policy:
                    binding_issues.append("case_policy_mismatch")
                if (entry.policy.effective_from, entry.policy.effective_to) != (
                    terms.effective_from,
                    terms.effective_to,
                ):
                    binding_issues.append("specification_interval_mismatch")
                if not terms.effective_from <= case.claim.loss_at.date() < terms.effective_to:
                    binding_issues.append("incident_outside_interval")
                    binding_status = Status.FAIL
                expected = clause_texts(terms)
                actual = {c.clause.citation.clause_id: c for c in entry.chunks}
                if any(
                    c not in actual or actual[c].clause.text != text for c, text in expected.items()
                ):
                    binding_issues.append("rule_clause_mismatch")
                if not binding_issues:
                    citations = {c: actual[c].clause.citation for c in expected}
    except ValueError:
        binding_issues.append("policy_source_unverified")
    if not binding_issues:
        binding_status = Status.PASS
    finding(
        RuleId.BINDING,
        binding_status,
        "Exact provisional policy, source, specification and incident-date binding required.",
        issues=tuple(binding_issues),
    )
    bound = binding_status == Status.PASS

    evidence_issues = []
    records: list[EvidenceRecord] = []
    seen_documents: set[str] = set()
    for bundle in request.evidence_inputs:
        original = bundle.request
        document_id = original.document_id
        if document_id in seen_documents:
            evidence_issues.append("duplicate_document_execution")
        seen_documents.add(document_id)
        if original.case.claim != case.claim or original.case.documents != case.documents:
            evidence_issues.append("stale_or_cross_case_evidence")
            continue
        result = process_extraction(original, bundle.response)
        if result.disposition != Disposition.ACCEPTED:
            evidence_issues.extend(i.code.value for i in result.issues if i.severity != "warning")
            continue
        if any(
            r.provider.provider != Provider.FIXTURE or r.provider.execution_mode != "SIMULATED"
            for r in result.candidates
        ):
            evidence_issues.append("unsupported_evidence_origin")
        if not request.allow_simulated_evidence:
            evidence_issues.append("simulation_not_authorized")
        records.extend(result.candidates)
        for record in result.candidates:
            provenance.append(
                EvidenceProvenance(
                    evidence_id=record.evidence.evidence_id,
                    record_sha256=record.record_sha256,
                    artifact=PolicyArtifact(
                        document_id=document_id, sha256=record.evidence.artifact_sha256
                    ),
                    page=record.evidence.page,
                    source_lines=tuple(
                        sorted({s.source_line for s in record.sources if s.source_line is not None})
                    ),
                    processing_key=result.operation_key,
                )
            )
    evidence_by_id = {r.evidence.evidence_id: r for r in records}
    if seen_documents != {d.document_id for d in case.documents}:
        evidence_issues.append("unprocessed_case_document")
    if any(d.scan_status != ScanStatus.ACCEPTED for d in case.documents):
        evidence_issues.append("case_document_not_accepted")
    if len(evidence_by_id) != len(records) or {e.evidence_id: e for e in case.evidence} != {
        r.evidence.evidence_id: r.evidence for r in records
    }:
        evidence_issues.append("case_evidence_not_exactly_verified")
    kinds = {d.document_id: d.kind for d in case.documents}
    verified_kinds = {kinds[r.evidence.document_id].value for r in records}
    if not set(spec.required_kinds) <= verified_kinds:
        evidence_issues.append("required_evidence_missing")
    field_values: dict[str, set[str]] = {}
    for record in records:
        if kinds[record.evidence.document_id] in {
            DocumentKind.CLAIM_FORM,
            DocumentKind.REPAIR_ESTIMATE,
        }:
            field_values.setdefault(record.evidence.field_name, set()).add(
                record.evidence.normalized_value or ""
            )
    if any(len(values) != 1 for values in field_values.values()):
        evidence_issues.append("contradictory_evidence")
    for field in ("claimed_amount", "estimate_amount"):
        if len(field_values.get(field, set())) != 1:
            evidence_issues.append("verified_money_missing")
    if not evidence_issues and field_values["claimed_amount"] != field_values["estimate_amount"]:
        evidence_issues.append("claim_estimate_amount_conflict")
    evidence_status = Status.PASS if bound and not evidence_issues else Status.INDETERMINATE
    finding(
        RuleId.EVIDENCE,
        evidence_status,
        "Source-replayed, case-admitted evidence and matching monetary observations required.",
        issues=tuple(evidence_issues) if bound else ("policy_binding_required", *evidence_issues),
        records=tuple(records),
    )
    trusted = bound and evidence_status == Status.PASS
    if evidence_issues:
        flags.add(RiskFlag.AMBIGUOUS)
        if any("conflict" in i for i in evidence_issues):
            flags.add(RiskFlag.CONFLICTING)

    fact_issues = []
    classifications = {(f.category, f.cause) for f in request.reviewed_facts}
    narrative_ids = {
        r.evidence.evidence_id for r in records if r.evidence.field_name == "narrative"
    }
    if not request.reviewed_facts:
        fact_issues.append("reviewed_facts_missing")
    if len({f.fact_id for f in request.reviewed_facts}) != len(request.reviewed_facts):
        fact_issues.append("duplicate_fact_id")
    for fact in request.reviewed_facts:
        if fact.case_sha256 != case_hash or not set(fact.evidence_ids) <= narrative_ids:
            fact_issues.append("fact_provenance_mismatch")
    if len(classifications) > 1:
        fact_issues.append("conflicting_reviewed_facts")
        flags.add(RiskFlag.CONFLICTING)
    category, cause = (
        next(iter(classifications)) if len(classifications) == 1 else ("unknown", "unknown")
    )
    category_status = Status.INDETERMINATE
    if trusted and not fact_issues:
        category_status = (
            Status.PASS
            if category == spec.supported_category
            else Status.FAIL
            if category == "other"
            else Status.INDETERMINATE
        )
    finding(
        RuleId.CATEGORY,
        category_status,
        "Category requires source-linked synthetic human assertions; no narrative interpretation.",
        issues=(*fact_issues, *(("category_unknown",) if category == "unknown" else ())),
        records=tuple(r for r in records if r.evidence.evidence_id in narrative_ids),
    )
    exclusion_status = Status.INDETERMINATE
    if trusted and not fact_issues:
        if category_status == Status.FAIL:
            exclusion_status = Status.NOT_APPLICABLE
        elif category_status == Status.PASS:
            exclusion_status = {
                "impact": Status.PASS,
                "gradual_wear_only": Status.FAIL,
                "unknown": Status.INDETERMINATE,
            }[cause]
    finding(
        RuleId.EXCLUSION,
        exclusion_status,
        "Only reviewed gradual_wear_only triggers this provisional exclusion finding.",
        issues=(
            *fact_issues,
            *(("cause_unknown",) if category_status == Status.PASS and cause == "unknown" else ()),
        ),
        records=tuple(r for r in records if r.evidence.evidence_id in narrative_ids),
    )

    calculation = None
    math_status = Status.INDETERMINATE
    unsafe_flags = flags & {
        RiskFlag.AMBIGUOUS,
        RiskFlag.CONFLICTING,
        RiskFlag.INJECTION_FLAGGED,
        RiskFlag.UNSUPPORTED,
    }
    if trusted and category_status == exclusion_status == Status.PASS and not unsafe_flags:
        assert terms is not None
        amount = pence(next(iter(field_values["estimate_amount"])))
        after_excess = max(amount - terms.excess_pence, 0)
        illustration = min(after_excess, terms.limit_pence)
        calculation = Calculation(
            estimate_pence=amount,
            excess_pence=terms.excess_pence,
            after_excess_pence=after_excess,
            limit_pence=terms.limit_pence,
            illustration_pence=illustration,
            limit_reduction_pence=after_excess - illustration,
        )
        math_status = Status.PASS
    elif trusted and (category_status == Status.FAIL or exclusion_status == Status.FAIL):
        math_status = Status.NOT_APPLICABLE
    finding(
        RuleId.ILLUSTRATION,
        math_status,
        "Pence illustration: subtract excess, floor at zero, cap net; no settlement authority.",
        records=tuple(
            r for r in records if r.evidence.field_name in {"claimed_amount", "estimate_amount"}
        ),
        calculation=calculation,
        issues=("prerequisites_or_risk_block",) if math_status == Status.INDETERMINATE else (),
    )
    if bound and terms is not None:
        try:
            if pence(format(case.claim.claimed_amount, "f")) >= terms.high_value_pence:
                flags.add(RiskFlag.HIGH_RISK)
        except ValueError:
            flags.add(RiskFlag.AMBIGUOUS)
    if any(f.status == Status.INDETERMINATE for f in findings):
        flags.add(RiskFlag.AMBIGUOUS)
    supervisor = bool(flags) or any(
        f.status in {Status.FAIL, Status.INDETERMINATE} for f in findings
    )
    finding(
        RuleId.REVIEW,
        Status.FAIL if supervisor else Status.PASS,
        "Human review always; adverse, ambiguous and high-risk findings require a supervisor.",
        issues=tuple(sorted(flag.value for flag in flags)),
        records=tuple(r for r in records if r.evidence.field_name == "claimed_amount"),
    )
    canonical = request.model_dump(mode="json", exclude={"evidence_inputs"})
    canonical["evidence_inputs"] = sorted(
        (
            {
                "request": b.request.model_dump(mode="json"),
                "response": b.response.model_dump(mode="json"),
                "content_sha256": sha256(b.request.content).hexdigest(),
            }
            for b in request.evidence_inputs
        ),
        key=lambda b: b["request"]["document_id"],
    )
    canonical["reviewed_facts"] = sorted(canonical["reviewed_facts"], key=lambda f: f["fact_id"])
    canonical["risk_flags"] = sorted(canonical["risk_flags"])
    input_hash = digest(canonical)
    return RuleEvaluation(
        claim_id=case.claim.claim_id,
        case_policy_id=case.claim.policy_id,
        requested_policy_id=request.policy_id,
        requested_policy_version=request.policy_version,
        execution_key=digest(
            {"engine": spec.engine_version, "input": input_hash, "specification": spec_hash}
        ),
        case_sha256=case_hash,
        specification_sha256=spec_hash,
        input_sha256=input_hash,
        findings=tuple(findings),
        evidence_provenance=tuple(sorted(provenance, key=lambda p: p.evidence_id)),
        risk_flags=tuple(sorted(flags)),
        required_reviewer=ReviewerRole.SUPERVISOR if supervisor else ReviewerRole.REVIEWER,
    )
