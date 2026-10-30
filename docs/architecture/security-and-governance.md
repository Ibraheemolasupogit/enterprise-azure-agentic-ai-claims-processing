# Security and governance baseline

Status: **PLANNED requirements**, not implemented controls or certification. Only synthetic data is allowed. Follow the [architecture](target-architecture.md); prove controls with negative tests before claiming security.

## Trust boundaries and identity

| Boundary | Required control |
| --- | --- |
| User/browser to API and uploads | Entra ID sign-in; server-side token issuer/audience/expiry and role validation; case authorization on every request; short-lived, single-object upload grants; no anonymous evidence access |
| Untrusted file to processing | Quarantine, signature/type/size checks, malware scanning, bounded parsing and timeouts; reject unsafe/encrypted/unsupported files without sending them to AI |
| Worker/agent to model and tools | Separate managed identities and explicit tool grants; case-scoped, bounded arguments; validate all model/tool output; treat text, OCR, images and retrieved content as untrusted data |
| Service to data stores | Entra-based access where supported, narrow data-plane roles, encryption in transit/at rest and private endpoints/private DNS where supported by selected tiers |
| Pipeline to Azure control plane | GitHub Actions OIDC federation scoped to repository/ref/environment; narrowly scoped deployment identity and separately controlled role-assignment privileges |

No cloud identity or role assignments exist yet. Avoid shared API keys; any unavoidable service secret requires Key Vault, rotation and access logging. Do not grant an agent deployment, secret-management or role-assignment rights. API and worker identities are distinct; the policy publisher can activate approved versions, while runtime identities cannot alter them.

## Authorization and decision governance

- Roles: submitter can access assigned synthetic cases; reviewer can assess assigned cases; supervisor can handle escalations/overrides; policy administrator can publish approved fictional policies; operator manages service health without blanket evidence access. Deny by default and test cross-case access. Small-team role overlap must be declared.
- The API enforces ownership, role and case revision independently of UI state. Workers carry a trusted case scope; model-supplied IDs never enlarge it. Agent-created text cannot trigger state transitions or change authorization.
- APIM validates Entra tokens and applies operation allowlists, input limits, throttles and audit correlation. Backends also authorize the caller/case and restrict direct ingress. MCP discovery advertises only approved tools; no remote tool descriptions may change agent policy. [APIM MCP support](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview) must be verified for the selected tier.
- Every initial case outcome needs an authorized human; supervisor review is mandatory for ambiguous/high-risk/adverse recommendations. Corrections and overrides require reasons and preserve prior snapshots. A reviewer cannot approve a stale assessment.
- Policy/rule changes require owner approval, versioning, regression evaluation and an activation record. Store concise decision evidence and reviewer actions in an append-only application audit ledger; restricted audit export and tamper-evident/immutable retention are release requirements, not current guarantees.

## Responsible AI and privacy

Prompt injection may arrive in narratives, OCR, photographs, policy text or MCP output. Separate instructions from evidence; prohibit tool execution from document instructions; use scoped retrieval, output schemas, tool allowlists, egress restrictions and citation validation. Evaluate [Prompt Shields](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection) for document/user attacks where available. Detection is defense in depth, not a guarantee. Flagged or unverifiable content stops automated assessment and routes to a reviewer.

Do not infer protected characteristics, causation, intent, fraud or roadworthiness from images. Missing evidence must remain visible. Generated explanations must separate observed facts, rule conclusions and uncertainty. Reviewers can inspect source material and reject model suggestions. Synthetic robustness slices cover document quality, wording variation and vehicle appearance; no claim of demographic fairness or real-world validity follows from synthetic-only testing.

Use generated fictional people/vehicles/policies and non-identifying imagery with recorded provenance; no real faces, number plates, addresses or production claims. Mark fixtures as synthetic. Block accidental sensitive uploads and scan fixtures/logs before release. Treat accidental real data as an incident: isolate, stop processing and follow an approved deletion/incident procedure.

Provisional retention: evidence/case content 30 days in dev/test; minimized audit metadata 90 days; operational telemetry 30 days. Final periods, deletion across Blob/database/index/exports, backup expiry and legal-hold behavior require owner review before cloud use. Logs exclude raw documents, narratives, prompts, model responses, tokens/secrets and signed URLs; use opaque IDs and redacted errors. Evidence/audit storage remains separately access-controlled.

## Governance exit requirements

Before cloud release: approve a threat model, data-flow inventory, role matrix, data-residency decision, retention/deletion procedure, model/tool inventory and incident runbook. Exercise prompt injection, access bypass, stale approvals, malicious uploads and exfiltration attempts. Record dependency/model limitations and preview-feature exceptions; do not claim regulatory compliance or production readiness from this portfolio baseline.
