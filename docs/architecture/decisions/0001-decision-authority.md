# ADR-0001 — Deterministic authority and accountable human outcomes

Status: **Accepted baseline, recorded in Milestone 3**. Formalizes the approved Milestone 1 design and Milestone 2 guard behavior; no architecture or contract change. Runtime agents, identity and persistence remain planned.

Context: synthetic motor evidence and policy text need semantic comparison/explanation, while policy applicability, calculations and outcome authority must remain reproducible and reviewable. Giving a model final decision or rule-writing rights would undermine those requirements.

Decision: retain exactly the two bounded agents justified in the [architecture responsibility table](../target-architecture.md#agent-versus-code-boundaries). Code owns approved policy resolution/rules, scope/authorization, validation and transitions. Humans approve every initial outcome; supervisors handle the [FR-011 decision table](../../business/requirements.md#fr-011-supervisor-escalation). Decline an autonomous coverage/supervisor agent. Reconsider either proposed agent only on comparative evaluation evidence.

Consequences: model outputs are advisory candidates; no prompt, retrieved clause or typed protocol grants authority. Current local guards accept trusted role assertions and return in-memory records; future authentication/assignment and atomic audit persistence must enforce the same boundaries. Human review adds effort and single-maintainer role overlap limits independent assurance; neither is hidden behind an automation claim.

Trace: BR-002/BR-003/BR-004; FR-006 through FR-013, FR-015; NFR-002/NFR-003. [Traceability](../../business/traceability-matrix.md) links the enforcing foundation symbols and planned verification. Detailed components, service choices and security requirements remain in their existing documents; no duplicate ADR is needed for each service name.
