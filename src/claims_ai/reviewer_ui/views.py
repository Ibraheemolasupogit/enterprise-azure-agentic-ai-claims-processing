"""Escaped semantic HTML with no scripts, remote assets, Markdown or source-owned links."""

from base64 import b64encode
from hashlib import sha256
from html import escape

from claims_ai.api.contracts import ReviewQueueResponse
from claims_ai.human_review.contracts import OPEN_STATES, ReviewAction, ReviewEvent, ReviewState
from claims_ai.models import DocumentKind, ReviewerRole
from claims_ai.reviewer_ui.client import CaseView
from claims_ai.reviewer_ui.sessions import Session

CSS = """
:root{color-scheme:light;
font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
color:#172b40;
background:#f3f5f8;
font-size:16px}

*{box-sizing:border-box}
body{margin:0}
a{color:#164ca6;
text-underline-offset:3px}
a:hover{text-decoration-thickness:2px}

:focus-visible{outline:3px solid #a34c00;
outline-offset:4px}
header{background:#112b45;
color:white;
padding:22px 5%;
display:flex;
justify-content:space-between;
gap:24px;
align-items:center}

.brand{font-weight:750;
letter-spacing:.035em;
font-size:20px}
.brand small{display:block;
color:#cbd9e7;
font-weight:450;
font-size:13px;
letter-spacing:0;
margin-top:4px}

header a{color:white}
main{max-width:1220px;
margin:0 auto;
padding:30px 28px 60px}
.skip{position:absolute;
left:-10000px}
.skip:focus{position:fixed;
left:12px;
top:12px;
background:white;
padding:14px;
z-index:5}

.boundary{background:#fff4df;
border-left:4px solid #9a5b06;
padding:14px 18px;
margin-bottom:26px;
font-size:14px;
line-height:1.65}
.eyebrow{text-transform:uppercase;
font-size:12px;
font-weight:750;
letter-spacing:.12em;
color:#50657d}

h1{font-size:32px;
margin:8px 0 10px;
letter-spacing:-.035em}
h2{font-size:20px;
margin:0 0 18px}
h3{font-size:16px}
.muted{color:#50657d}
.intro{max-width:850px;
line-height:1.6;
margin-bottom:24px}

.toolbar{display:flex;
justify-content:space-between;
align-items:center;
gap:20px;
margin-bottom:24px}
.toolbar p{margin:0}
.metrics{display:grid;
grid-template-columns:repeat(3,1fr);
gap:18px;
margin-bottom:26px}

.metric,.card{background:white;
border:1px solid #d8e0ea;
border-radius:10px;
padding:24px}
.metric strong{display:block;
font-size:32px;
margin:8px 0}
.metric span{color:#50657d;
font-size:14px}
.card{margin-bottom:24px;
box-shadow:0 2px 5px #172b4005}

.table-wrap{overflow-x:auto}
table{width:100%;
border-collapse:collapse;
font-size:14px}
caption{text-align:left;
color:#50657d;
padding-bottom:16px}
th{text-align:left;
font-size:12px;
letter-spacing:.04em;
text-transform:uppercase;
color:#50657d;
background:#f7f9fc}
td,th{padding:14px 12px;
border-bottom:1px solid #e4e9f0;
vertical-align:top}
td{line-height:1.6}
tbody tr:last-child td{border-bottom:0}

.badge{display:inline-block;
background:#eaf1fc;
color:#204d88;
padding:4px 9px;
border-radius:5px;
font-size:12px;
font-weight:650}
.notice{padding:16px;
background:#edf3fc;
border-left:3px solid #225ab1;
margin:16px 0;
line-height:1.6}

.grid{display:grid;
grid-template-columns:1.4fr 1fr;
gap:24px}
.grid .card{align-self:start}
.error{background:#fff0ee;
border-color:#a83322}
.success{background:#edf7f1;
border-color:#28704c}
.mono,code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;
overflow-wrap:anywhere;
font-size:12px}

dl{display:grid;
grid-template-columns:minmax(120px,1fr) 2fr;
gap:12px;
margin:0}
dt{color:#50657d}
dd{margin:0;
overflow-wrap:anywhere}
p,li{line-height:1.65}
blockquote{margin:12px 0;
padding:8px 16px;
border-left:3px solid #ccd7e6;
background:#f7f9fc;
white-space:pre-wrap}

label{display:block;
font-size:14px;
font-weight:650;
margin:18px 0 8px}
input:not([type=checkbox]),textarea,select{font:inherit;
width:100%;
border:1px solid #8193a9;
border-radius:5px;
padding:11px;
background:white;
color:#172b40}
textarea{min-height:120px;
resize:vertical}
fieldset{border:1px solid #d8e0ea;
border-radius:5px;
padding:12px 16px;
margin-top:20px}
legend{font-weight:650;
font-size:14px}
.check{font-weight:450;
margin:10px 0;
overflow-wrap:anywhere}
.check input{margin-right:8px;
min-width:18px;
min-height:18px;
vertical-align:middle}

button,.button{font:inherit;
display:inline-block;
border:1px solid #1d53a0;
border-radius:5px;
background:#1d53a0;
color:white;
padding:11px 18px;
font-weight:650;
cursor:pointer;
text-decoration:none;
margin-top:18px}
button:hover,.button:hover{background:#153d77}
.secondary{background:white;
color:#164ca6}
.secondary:hover{color:white}
header button{background:transparent;
border-color:#a9bfd4;
margin:0;
font-size:13px;
padding:8px 12px}

details{margin:18px 0}
summary{cursor:pointer;
font-weight:650;
padding:8px 0}
.login{max-width:520px;
margin:36px auto}
.small{font-size:13px}
footer{color:#50657d;
font-size:12px;
border-top:1px solid #d8e0ea;
padding-top:20px;
margin-top:32px}
.break{overflow-wrap:anywhere}

@media(max-width:760px){header{align-items:start;
padding:20px}
.toolbar{align-items:start;
flex-direction:column}
main{padding:24px 16px}
.metrics{grid-template-columns:1fr;
gap:10px}
.metric{padding:16px}
.metric strong{font-size:26px}
.grid{grid-template-columns:1fr;
gap:0}
.card{padding:18px}
h1{font-size:27px}
dl{grid-template-columns:1fr;
gap:6px}
dd{margin-bottom:10px}
}

""".strip()
STYLE_HASH = b64encode(sha256(CSS.encode()).digest()).decode()


def text(value: object) -> str:
    return escape(str(value), quote=True)


def human(value: object) -> str:
    return text(str(value).replace("_", " ").capitalize())


def requirement(role: ReviewerRole, state: ReviewState) -> str:
    # Presentation of the API's current routing, never permission to submit an action.
    return "Supervisor" if state == ReviewState.SUPERVISOR else human(role)


def hidden(name: str, value: str) -> str:
    return f'<input type="hidden" name="{text(name)}" value="{text(value)}">'


def page(title: str, body: str, session: Session | None = None) -> str:
    identity = '<span class="small">Offline demonstration</span>'
    if session is not None and session.profile is not None:
        identity = (
            f'<div><p class="small">{text(session.profile.label)} · simulated identity</p>'
            '<form method="post" action="/logout">'
            + hidden("csrf", session.csrf)
            + '<button type="submit">End session</button></form></div>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{text(title)} · Northstar Claims Operations</title><style>{CSS}</style></head>"
        '<body><a class="skip" href="#main">Skip to main content</a><header>'
        '<div class="brand">NORTHSTAR<small>Claims reviewer operations</small></div>'
        + identity
        + (
            '</header><main id="main"><aside class="boundary" aria-label="Authority'
            ' boundary"><strong>Synthetic review environment.</strong> Evidence and'
            " model responses are simulated. Approving an advisory recommendation "
            "does not approve an insurance claim, deny coverage or authorize "
            "payment or settlement.</aside>"
        )
        + body
        + (
            "<footer>Offline · process-local storage · synthetic host capabilities,"
            " not Entra authentication. No live model calls or Azure operations. "
            "Session lifetime: 15 minutes. Audit timestamps use fixed synthetic scenario time."
            "</footer></main></body></html>"
        )
    )


def login(session: Session) -> str:
    return page(
        "Synthetic session",
        '<section class="card login"><p class="eyebrow">Reviewer access</p>'
        "<h1>Start a synthetic session</h1><p>Use the one-time enrollment code delivered by "
        "the local host. Your identity and assigned cases are fixed by the host; this form "
        'cannot select a role or grant access.</p><form method="post" action="/login">'
        + hidden("csrf", session.csrf)
        + '<label for="code">One-time host code</label><input id="code" name="code" '
        'type="password" required maxlength="43" autocomplete="off" spellcheck="false">'
        '<p class="muted small">Codes expire after five minutes and can be used once.</p>'
        '<button type="submit">Open assigned queue</button></form></section>',
    )


def dashboard(queue: ReviewQueueResponse, session: Session, offset: int) -> str:
    pending = sum(item.state in OPEN_STATES for item in queue.items)
    supervisor = sum(
        item.required_reviewer == ReviewerRole.SUPERVISOR or item.state == ReviewState.SUPERVISOR
        for item in queue.items
    )
    rows = "".join(
        '<tr><td><a class="mono" href="/reviews/'
        + text(item.entry_id)
        + '">'
        + text(item.claim_id)
        + '</a></td><td><span class="badge">'
        + human(item.state)
        + "</span></td><td>"
        + requirement(item.required_reviewer, item.state)
        + "</td><td>"
        + (
            "Available · advisory only"
            if item.recommendation_available
            else "Missing · evidence triage"
        )
        + f"</td><td>{item.case_revision} / {item.review_revision}</td></tr>"
        for item in queue.items
    )
    if not rows:
        rows = '<tr><td colspan="5">No assigned reviews are available for this session.</td></tr>'
    pagination = '<nav aria-label="Queue pages">'
    if offset:
        previous = "/" if offset == 16 else f"/queue/{offset - 16}"
        pagination += f'<a class="button secondary" href="{previous}">Previous page</a> '
    if queue.next_offset is not None:
        pagination += f'<a class="button secondary" href="/queue/{queue.next_offset}">Next page</a>'
    pagination += "</nav>"
    return page(
        "Assigned review queue",
        '<p class="eyebrow">Operations workspace</p><div class="toolbar"><div>'
        '<h1>Assigned review queue</h1><p class="muted">Inspect sources. Resolve uncertainty. '
        "Record an explicit recommendation decision.</p></div>"
        '<a class="button secondary" href="/">Refresh queue</a></div>'
        '<div class="metrics" aria-label="Current page summary">'
        '<div class="metric"><span>Assigned on this page</span>'
        f"<strong>{len(queue.items)}</strong></div>"
        f'<div class="metric"><span>Pending human action</span><strong>{pending}</strong></div>'
        '<div class="metric"><span>Supervisor required</span>'
        f"<strong>{supervisor}</strong></div></div>"
        '<section class="card"><h2>Case worklist</h2><div class="table-wrap"><table>'
        "<caption>Case scope and permissions are enforced by the API on every request.</caption>"
        '<thead><tr><th scope="col">Case</th><th scope="col">Review status</th>'
        '<th scope="col">Required reviewer</th><th scope="col">Recommendation</th>'
        '<th scope="col">Case / review revision</th></tr></thead><tbody>'
        + rows
        + "</tbody></table></div>"
        + pagination
        + "</section>",
        session,
    )


def case_detail(view: CaseView, session: Session, ticket: str) -> str:
    detail, advisory = view.detail, view.advisory
    entry, case, snapshot = detail.entry, detail.current_case, detail.advisory_snapshot
    evidence = (
        "".join(
            "<tr><td><strong>"
            + human(e.field_name)
            + '</strong><br><span class="mono">'
            + text(e.evidence_id)
            + "</span></td><td>"
            + text(e.observed_value)
            + '</td><td><span class="mono">'
            + text(e.document_id)
            + "</span><br>Page "
            + str(e.page)
            + '<br><span class="mono">'
            + text(e.artifact_sha256)
            + "</span></td><td>"
            + text(e.extraction_method)
            + " / "
            + text(e.extraction_version)
            + "<br>"
            + (
                "Confidence unavailable"
                if e.confidence is None
                else text(e.confidence) + " · uncalibrated"
            )
            + "</td></tr>"
            for e in case.evidence
        )
        or '<tr><td colspan="4">No admitted evidence is available.</td></tr>'
    )
    provenance = ""
    if snapshot.history is not None:
        for record in snapshot.history.records:
            provenance += '<li><span class="mono">' + text(record.evidence.evidence_id)
            provenance += "</span> · " + human(record.quality.source_verification)
            provenance += " · " + human(record.quality.confidence_status)
            for source in record.sources:
                provenance += "<p>Source: " + text(source.document_id) + " · page "
                provenance += text(source.page) + " · line " + text(source.source_line) + "</p>"
            provenance += '<span class="mono">Record ' + text(record.record_sha256) + "</span></li>"
    clauses = ""
    if snapshot.retrieval_response is not None:
        for hit in snapshot.retrieval_response.hits:
            citation = hit.chunk.clause.citation
            clauses += "<article><h3>" + text(citation.clause_id) + " · policy "
            clauses += text(citation.policy_version) + " · page " + str(citation.page) + "</h3>"
            clauses += "<blockquote>" + text(hit.chunk.clause.text) + "</blockquote>"
            clauses += '<p class="mono">' + text(citation.document_id) + " · "
            clauses += text(citation.artifact_sha256) + "</p></article>"
    rules = ""
    if advisory.rules is not None:
        for finding in advisory.rules.findings:
            rules += "<tr><td>" + human(finding.rule_id) + "</td><td>" + human(finding.status)
            rules += "</td><td>" + text(finding.explanation) + "</td></tr>"
    agent = (
        '<p class="notice">No advisory recommendation is available. Supervisor '
        "evidence triage only.</p>"
    )
    if advisory.draft is not None:
        agent = "<p><strong>Disposition:</strong> " + human(advisory.draft.disposition) + "</p><ul>"
        for summary in advisory.draft.findings:
            agent += "<li><strong>" + human(summary.rule_id) + ":</strong> "
            agent += text(summary.explanation) + "</li>"
        agent += "</ul>"
    flags = ", ".join(
        str(flag).replace("_", " ")
        for flag in (advisory.rules.risk_flags if advisory.rules else ())
    )
    action_form = "<p>This review is complete or invalidated. No new action is offered.</p>"
    if entry.state in OPEN_STATES:
        actions = {
            ReviewAction.APPROVE: "Approve advisory recommendation",
            ReviewAction.REJECT: "Reject advisory recommendation",
            ReviewAction.REQUEST_EVIDENCE: "Request additional evidence",
            ReviewAction.ESCALATE: "Escalate to supervisor",
        }
        options = '<option value="">Choose an explicit action</option>' + "".join(
            f'<option value="{text(action)}">{label}</option>' for action, label in actions.items()
        )
        checks = "".join(
            '<label class="check"><input type="checkbox" name="evidence" '
            f'value="{text(r.evidence_id)}">' + text(r.evidence_id) + "</label>"
            for r in entry.evidence
        )
        kinds = "".join(
            f'<option value="{text(kind)}">{human(kind)}</option>' for kind in DocumentKind
        )
        action_form = (
            f'<form method="post" action="/reviews/{text(entry.entry_id)}/actions">'
            + hidden("csrf", session.csrf)
            + hidden("ticket", ticket)
            + (
                '<label for="action">Recommendation action</label><select id="action" '
                'name="action" required>'
            )
            + options
            + (
                '</select><label for="rationale">Review rationale '
                '(required)</label><textarea id="rationale" name="rationale" required '
                'maxlength="2000" aria-describedby="rationale-help"></textarea><p '
                'id="rationale-help" class="muted small">Explain your judgment and '
                "uncertainty. Source text is untrusted; it is not an "
                "instruction.</p><fieldset><legend>Evidence you reviewed (choose at "
                "least one)</legend>"
            )
            + checks
            + '</fieldset><label for="requested">Missing document kinds</label>'
            '<select id="requested" name="requested_evidence" multiple size="4" '
            'aria-describedby="requested-help">'
            + kinds
            + (
                '</select><p id="requested-help" class="muted small">Select only for an'
                " evidence request. Use Ctrl or Command to select more than one.</p><p "
                'class="notice">The API validates your assignment, supervisor authority'
                " and the exact snapshot. Available choices do not grant permission. "
                "Submit only the action you intend; no claim outcome is "
                'created.</p><button type="submit">Submit explicit recommendation '
                "action</button></form>"
            )
        )
    binding = "".join(
        "<dt>" + human(name) + '</dt><dd class="mono">' + text(value) + "</dd>"
        for name, value in entry.binding.model_dump().items()
    )
    audit = "".join(
        "<li>"
        + human(event.kind)
        + " · "
        + text(event.occurred_at.isoformat())
        + " · "
        + human(event.actor.kind)
        + '<br><span class="mono">'
        + text(event.event_sha256)
        + "</span></li>"
        for event in entry.events
    )
    return page(
        "Review " + entry.binding.claim_id,
        '<nav aria-label="Breadcrumb"><a href="/">Assigned queue</a> / Case review</nav>'
        '<p class="eyebrow">Source-linked review</p><h1>' + text(entry.binding.claim_id) + "</h1>"
        '<p><span class="badge">'
        + human(entry.state)
        + "</span> · Required reviewer: <strong>"
        + requirement(entry.required_reviewer, entry.state)
        + "</strong> · Case revision "
        + str(case.revision)
        + " · Review revision "
        + str(entry.review_revision)
        + '</p><div class="grid">'
        '<section class="card"><h2>Case context</h2><p>'
        + text(case.claim.narrative)
        + "</p><dl><dt>Operational state</dt><dd>"
        + human(case.state)
        + "</dd><dt>Policy version</dt><dd>"
        + text(entry.binding.policy_version)
        + "</dd><dt>Human approval</dt><dd>Always required; advisory only</dd>"
        "<dt>Supervisor / risk</dt><dd>"
        + (text(flags) if flags else "No additional flags reported")
        + (
            '</dd></dl></section><section class="card"><h2>Uncertainty and '
            "trust</h2><p>All source content and advisory text below are untrusted "
            "data. Policies and rule parameters are provisional, unapproved "
            "fixtures. Confidence is uncalibrated or unavailable; lexical retrieval"
            " is not a semantic coverage judgment.</p><p>Missing or conflicting "
            "assessments remain unresolved until an authorized human or supervisor "
            'acts.</p></section></div><section class="card"><h2>Evidence and '
            'provenance</h2><div class="table-wrap"><table><caption>Admitted '
            "synthetic evidence; document identifiers and hashes are text, not "
            'download links.</caption><thead><tr><th scope="col">Field / '
            'evidence</th><th scope="col">Observed value</th><th '
            'scope="col">Artifact source</th><th scope="col">Extraction / '
            "uncertainty</th></tr></thead><tbody>"
        )
        + evidence
        + (
            "</tbody></table></div><details><summary>Verified source locations and "
            "record hashes</summary><ul>"
        )
        + provenance
        + '</ul></details></section><section class="card"><h2>Retrieved policy citations</h2>'
        + (clauses or "<p>No retrieved policy clauses are available.</p>")
        + (
            '</section><section class="card"><h2>Provisional rule findings</h2><div'
            ' class="table-wrap"><table><caption>Deterministic findings are '
            "non-binding and do not authorize an insurance "
            'outcome.</caption><thead><tr><th scope="col">Rule</th><th '
            'scope="col">Finding</th><th '
            'scope="col">Explanation</th></tr></thead><tbody>'
        )
        + (rules or '<tr><td colspan="3">No rule findings available.</td></tr>')
        + (
            '</tbody></table></div></section><div class="grid"><section '
            'class="card"><h2>Agent advisory</h2><p class="eyebrow">Simulated '
            "existing M12 model · not a decision</p>"
        )
        + agent
        + '</section><section class="card"><h2>Record your review</h2>'
        + action_form
        + '</section></div><section class="card"><h2>Snapshot and audit trace</h2><details>'
        "<summary>Exact server-held binding</summary><dl>" + binding + "</dl></details><details>"
        "<summary>Append-only review events</summary><ol>" + audit + "</ol></details></section>",
        session,
    )


def receipt(event: ReviewEvent, session: Session) -> str:
    return page(
        "Recommendation action recorded",
        '<section class="card success"><p class="eyebrow">Review receipt</p>'
        '<h1>Recommendation action recorded</h1><p role="status">The API accepted your explicit '
        "synthetic human action.</p><dl><dt>Review state</dt><dd>"
        + human(event.after)
        + "</dd><dt>Case</dt><dd>"
        + text(event.claim_id)
        + "</dd><dt>Event hash</dt>"
        '<dd class="mono">' + text(event.event_sha256) + "</dd></dl><p>No insurance claim has "
        'been approved, denied, paid or settled.</p><a class="button" href="/reviews/'
        + text(event.entry_id)
        + '">Reload case detail</a> <a class="button secondary" href="/">'
        "Return to queue</a></section>",
        session,
    )


def error(status: int) -> str:
    messages = {
        400: ("Request unavailable", "Use the links and forms supplied by this application."),
        401: (
            "Synthetic session unavailable",
            (
                "Your session or API capability has expired or was revoked. Ask the "
                "local host for a new code."
            ),
        ),
        403: (
            "Action not authorized",
            (
                "The API requires the assigned human or supervisor. A visible control "
                "never grants permission."
            ),
        ),
        404: ("Case unavailable", "The case does not exist or is not assigned to this session."),
        409: (
            "Action conflicts with current review",
            (
                "The action was changed on replay or the review has already moved on. "
                "Reload and inspect the case."
            ),
        ),
        412: (
            "Review snapshot changed",
            (
                "Reload case detail and inspect the current evidence, task and "
                "revisions before making a new decision."
            ),
        ),
        413: ("Request too large", "Use a bounded rationale and the supplied form controls."),
        415: ("Form content unavailable", "Submit the application form without attachments."),
        422: (
            "Review input incomplete",
            (
                "Provide a nonblank rationale and known evidence references. Evidence "
                "requests require a missing document kind."
            ),
        ),
        429: (
            "Local capacity reached",
            "Wait for sessions to expire or ask the host to restart the bounded demonstration.",
        ),
        503: (
            "Review service unavailable",
            (
                "No successful action is confirmed. Reload when the service is "
                "available; an exact retry retains its original operation identity."
            ),
        ),
    }
    title, message = messages.get(status, messages[503])
    return page(
        title,
        '<section class="card error" role="alert"><h1>'
        + title
        + "</h1><p>"
        + message
        + '</p><a class="button secondary" href="/">Return to queue</a> '
        '<a class="button secondary" href="/login">Start a new session</a></section>',
    )
