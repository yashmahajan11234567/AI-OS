# AI-OS Part 13 — Governance Event Architecture

**Document Status:** Architecture Specification (v1.0)
**Layer:** Governance event taxonomy (consumes and extends the Part 12 event backbone)
**Sister Documents:** Part 12 (Event Architecture), Part 13.2 (Governance Architecture), Part 13.3 (Policy Architecture), Part 13.4 (Decision Authority and Delegation), Part 13.5 (Councils and Committees), Part 13.6 (Risk and Compliance Governance), Part 13.11 (Auditability and Accountability), Part 13.12 (Governance Invariants and Conformance)
**Distribution:** Governance services, policy gates, councils, audit service, security domain, observability
**Source of Truth:** This file is authoritative for the governance event taxonomy; for the canonical envelope, delivery guarantees, idempotency, versioning, retention, and conformance rules it defers to Part 12 `events.md`.

---

## Table of Contents

1. [Relationship to Part 12 (Integration, Not Duplication)](#1-relationship-to-part-12-integration-not-duplication)
2. [Canonical Governance Event Taxonomy](#2-canonical-governance-event-taxonomy)
3. [Event Definitions](#3-event-definitions)
   - 3.1 [Policy Aggregate](#31-policy-aggregate)
   - 3.2 [Decision Aggregate](#32-decision-aggregate)
   - 3.3 [Authority Aggregate](#33-authority-aggregate)
   - 3.4 [Approval Aggregate](#34-approval-aggregate)
   - 3.5 [Risk Aggregate](#35-risk-aggregate)
   - 3.6 [Compliance Aggregate](#36-compliance-aggregate)
   - 3.7 [Audit Aggregate](#37-audit-aggregate)
   - 3.8 [Control & Conformance Aggregate](#38-control--conformance-aggregate)
   - 3.9 [Agent Aggregate](#39-agent-aggregate)
   - 3.10 [Capability Aggregate](#310-capability-aggregate)
4. [Event Naming Convention](#4-event-naming-convention)
   - 4.1 [Rule: No Competing Canonical Names](#rule-no-competing-canonical-names)
   - 4.2 [Legacy and Alias Handling](#legacy-and-alias-handling)
5. [Event Namespace](#5-event-namespace)
6. [Event Ownership](#6-event-ownership)
7. [Event Versioning](#7-event-versioning)
8. [Event Compatibility](#8-event-compatibility)
9. [Event Governance](#9-event-governance)
10. [Event Security](#10-event-security)
11. [Event Replay](#11-event-replay)
12. [Event Auditability](#12-event-auditability)
13. [Event Retention](#13-event-retention)
14. [Event Conformance](#14-event-conformance)
15. [Complete Event Catalog](#15-complete-event-catalog)
16. [Cross-References](#16-cross-references)

---

## 1. Relationship to Part 12 (Integration, Not Duplication)

Part 12 `events.md` is the **authoritative event architecture** for all of AI-OS: it defines the canonical envelope (§4), the eventing principles (§2), delivery guarantees and ordering (§18, §29), idempotency/correlation/causation standards (§30), the event lifecycle model (§26), versioning strategy (§27), governance model (§24), security and replay protection (§20), retention tiers (§33), and conformance requirements (§36).

**This document does not re-define any Part 12 construct.** It defines only the *governance-specific* event taxonomy — the set of `governance.*` event types — and specifies how those types **conform to and extend** Part 12. Where a governance rule is identical to a Part 12 rule, this document references the Part 12 section rather than restating it.

### Integration contract

| Part 12 construct | Role in governance events |
|---|---|
| Canonical envelope (§4) | Every `governance.*` event uses the exact Part 12 envelope. `event_type` is the short form (`governance.policy.created`); the FQN `ai-os.event.governance.policy.created@v1` is the registry identity. |
| `security.policy.violated` (§13.1) | The runtime enforcement signal emitted by a policy gate. `governance.policy.violation.detected` is **causation-linked** to it (`causation_id` → the `security.policy.violated` event) and carries the same `policy_id`. The security event is the raw enforcement fact; the governance event is the recorded governance artifact + triage state. |
| `council.decision.published` (§7.7) | A council decision is the *mechanism* by which many governance decisions are reached. `governance.decision.*` records the governance artifact so produced. Where a governance decision originates from a council, `governance.decision.created` cites the `council_session_id` and the `council.decision.published` event as causation. |
| `security.audit.record` (§13.8) | Chain-anchors all governance events into the tamper-evident audit Merkle chain (see §12). |
| `monitoring.alert.raised` (§14.4) | Governance services subscribe to governance events to drive alerts (e.g., `governance.risk.escalated` → `monitoring.alert.raised` sev1). |
| `knowledge.memory.deleted` / `system.event.tombstoned` (§33) | RTBF and tombstone deletion of governance artifacts flow through these Part 12 mechanisms, not bespoke ones. |
| Event Registry (§28) | The `governance` namespace and all `governance.*` types are registered here under ownership by the Governance domain (Part 13), per the ESC process (§24). |

### New namespace registration

Part 12 §25 lists eleven reserved namespaces and does **not** include `governance`. This document registers `governance` as a twelfth namespace owned by the Part 13 Governance domain. Registration requires ESC ratification per Part 12 §24/§25. See [§5 Event Namespace](#5-event-namespace).

---

## 2. Canonical Governance Event Taxonomy

The governance taxonomy is organized into **ten aggregates** under the `governance` namespace. Each event is a *fact* (per Part 12 §2, principle 1), describing a state transition of a governance artifact — never a command.

| Aggregate | Event Types | Partition Key |
|---|---|---|
| `policy` | `policy.created`, `policy.updated`, `policy.approved`, `policy.activated`, `policy.suspended`, `policy.deprecated`, `policy.retired`, `policy.violation.detected`, `policy.exception.requested`, `policy.exception.approved`, `policy.exception.rejected`, **`policy.submitted`, `policy.override.granted`, `policy.exception.expiring`, `policy.conflict.detected`, `policy.validation.failed`** | `policy_id` |
| `decision` | `decision.created`, `decision.approved`, `decision.rejected` | `decision_id` |
| `authority` | `authority.delegated`, `authority.revoked` | `authority_id` |
| `approval` | `approval.requested`, `approval.granted`, `approval.rejected` | `approval_id` |
| `risk` | `risk.identified`, `risk.escalated`, `risk.accepted` | `risk_id` |
| `compliance` | `compliance.violation.detected` | `scope_id` (typically `tenant_id` or `control_id`) |
| `audit` | `audit.started`, `audit.completed` | `audit_id` |
| `control` | `control.evaluated`, `conformance.verified`, `conformance.failed` | `control_id` |
| `agent` | `agent.created`, `agent.provisioned`, `agent.activated`, `agent.suspended`, `agent.revoked`, `agent.action`, `agent.action.denied`, `agent.behavior.anomaly`, `agent.accountability.gap` | `agent_id` |
| `capability` | `capability.created`, `capability.issued`, `capability.revoked`, `capability.expired`, `capability.suspended`, `capability.modified`, `capability.used`, `capability.usage.violation`, `capability.usage.anomaly` | `capability_id` |

> **Naming note (canonical authority).** The conceptual PascalCase names in the request (e.g., `PolicyCreated`) and Part-13-internal short names (e.g., `policy.drafted`, `policy.modified`) map 1:1 to the canonical lowercase `event_type` shown above. **The `governance.<aggregate>.<action>[.<qualifier>]` form shown in this taxonomy is the sole canonical wire identity; PascalCase and Part-13-internal shorthand forms are non-canonical — used only in prose and mapping tables labeled "non-canonical."** On the wire every event uses the Part 12 envelope `event_type` lowercase dotted form. No competing canonical names are permitted (Part 12 §25; see §4 for the full rule).

> **Canonical name alignment with Part 13 `policies.md` §"Policy Events".** That section defines *policy-domain reference names* in short form (`policy.drafted`, `policy.submitted`, `policy.approved`, `policy.activated`, `policy.modified`, `policy.suspended`, `policy.deprecated`, `policy.retired`, `policy.override`, `policy.exception.granted`, `policy.exception.expiring`, `policy.conflict.detected`, `policy.validation.failed`, `policy.distributed`, `policy.violation`, `policy.decision`) and identifies them as "first-class governance events (see governance-events.md)". Per §4, these short names are **non-canonical, within-document labels**; they are NOT competing canonical event names. The FQN `governance.policy.*` forms below are the Part 12 Registry identities. They denote the **same events**, mapped here:
>
> | `policies.md` reference (non-canonical shorthand) | `governance.*` FQN (canonical registry identity) | Note |
> |---|---|---|
> | `policy.drafted` | `governance.policy.created` | draft registered (DRAFT state) |
> | `policy.modified` | `governance.policy.updated` | revision committed |
> | `policy.submitted` | `governance.policy.submitted` | entered Review/Pending-Approval; emits `approval.requested` |
> | `policy.approved` | `governance.policy.approved` | authorized approval |
> | `policy.activated` | `governance.policy.activated` | enforceable + distributed (policies.md `policy.distributed` is the distribution consequence of activation) |
> | `policy.suspended` | `governance.policy.suspended` | temporary disable |
> | `policy.deprecated` | `governance.policy.deprecated` | marked obsolete |
> | `policy.retired` | `governance.policy.retired` | withdrawn |
> | `policy.violation` | `governance.policy.violation.detected` | causation-linked to `security.policy.violated` (Part 12 §13.1) |
> | `policy.exception.granted` | `governance.policy.exception.approved` | |
> | `policy.exception.expiring` | `governance.policy.exception.expiring` | |
> | `policy.override` | `governance.policy.override.granted` | overrides take precedence over exceptions (Part 13 `schemas.md` `PolicyOverride`) |
> | `policy.conflict.detected` | `governance.policy.conflict.detected` | |
> | `policy.validation.failed` | `governance.policy.validation.failed` | structural validation at draft/submit time |
> | `policy.decision` | subsumed by `governance.decision.*` + the specific policy events above | a policy-level governance decision is recorded by `decision.*` and the applicable policy event; no separate duplicate event is emitted |
>
> The five **bold** `policy` events in the table above are added here so this taxonomy is complete against `policies.md` and `schemas.md`; the other events in the table are unchanged from the original 28.

---

## 3. Event Definitions

Each event below declares the fifteen required attributes. Fields that are uniform across governance events are given once and referenced:

- **Envelope:** Part 12 §4. Every event carries `event_id` (ULID), `event_version`, `correlation_id`, `causation_id` (where applicable), `partition_key` (per aggregate table above), `produced_by.actor_kind ∈ {governance, council, security, agent, system}`, `priority`, `trace`, `metadata.classification`, `security.signature`.
- **Idempotency:** Part 12 §30 — `event_id` dedup window (default 24h) + `correlation_id` grouping + version-stamped projections.
- **Delivery expectations:** At-least-once, ordered per `partition_key`, priority-laned (Part 12 §18/§29).
- **Audit requirements:** Every governance event is audit-grade — signed (Part 12 §20), chain-anchored via `security.audit.record` (Part 12 §13.8), immutable in the WORM log (Part 12 §29), non-repudiable. Never silently deleted (Part 12 §33).
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr (see §13).
- **Versioning:** Part 12 §27 semantic `<major>.<minor>`; governance-specific constraints in §7.
- **Security:** Part 12 §20/§36 — signed, classified `confidential` minimum, ACL-gated subscription; sealed `governance.dlq` (see §10).
- **Lifecycle:** Event-*type* lifecycle follows Part 12 §26 (proposed→ratified→active→deprecated→retired). The per-instance *record* lifecycle is stated per event.

### 3.1 Policy Aggregate

#### `governance.policy.created`
- **Purpose:** A new policy artifact has been drafted and registered in the policy store.
- **Producer:** Policy Service (Part 13.3).
- **Consumers:** Policy distribution engine, Audit Service, Observability, Council (for review if policy is council-ratified).
- **Trigger:** Policy author submits a draft that passes structural validation; the policy enters the *draft* state.
- **Payload concept:** `{ "policy_id", "name", "version", "domain", "owner", "classification", "draft_by", "created_at" }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** Root event for the policy instance (no `causation_id`); may be preceded by a `governance.approval.granted` if authoring required prior approval.
- **Ordering:** First event of any `policy_id`; strictly precedes all other `governance.policy.*` events for that policy.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P2.
- **Idempotency:** `event_id` dedup; projection writers reject a second `created` for an existing `policy_id`.
- **Security:** Signed; `confidential` (policy text may encode sensitive internal rules).
- **Audit requirements:** Signed + chain-anchored; establishes the immutable origin record of the policy.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Policy *content* is versioned independently of event schema; event `event_version` follows Part 12 §27.
- **Lifecycle:** Type lifecycle per Part 12 §26. Record lifecycle: `draft → approved → activated → suspended|deprecated → retired`.

#### `governance.policy.updated`
- **Purpose:** A policy artifact was revised (text, parameters, scope, or metadata changed).
- **Producer:** Policy Service.
- **Consumers:** Policy distribution engine, Audit Service, Observability, subscribers that cache policy state.
- **Trigger:** An approved edit to an existing policy is committed to the policy store.
- **Payload concept:** `{ "policy_id", "from_version", "to_version", "changed_fields", "rationale", "updated_by", "updated_at" }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → the prior `governance.policy.created` or `governance.policy.updated` for the same policy.
- **Ordering:** Per `policy_id`; linear causal chain, monotonic version.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P2.
- **Idempotency:** `event_id` dedup; version-stamped projection prevents out-of-order overwrite.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored; diff retained for reconstruction.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Bumps policy content version; event schema per Part 12 §27. A `major` policy content change does not require an event `major` bump.
- **Lifecycle:** Record lifecycle: `draft|approved|activated → updated → approved|activated`.

#### `governance.policy.approved`
- **Purpose:** A policy (or policy revision) was formally approved by the authorized governance body.
- **Producer:** Policy Service (recording the approval) or Council Orchestrator when approval is council-issued.
- **Consumers:** Policy distribution engine (gates activation), Audit Service, Observability, Authority Service (may depend on policy state).
- **Trigger:** Required approvers grant approval per the policy's approval routing (Part 13.3).
- **Payload concept:** `{ "policy_id", "policy_version", "approver", "approver_role", "approval_ref", "council_session_id?": null, "approved_at" }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → `governance.policy.created`/`updated`, or → `council.decision.published` if council-ratified (Part 12 §7.7).
- **Ordering:** Per `policy_id`; precedes `governance.policy.activated`.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P1.
- **Idempotency:** `event_id` dedup; a policy version is approved at most once (duplicate approvals ignored via projection).
- **Security:** Signed; `confidential`; approval identity is non-repudiable.
- **Audit requirements:** Signed + chain-anchored; approval is a compliance-critical record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27; no event version bump on repeated approvals of different policy versions.
- **Lifecycle:** Record lifecycle: `draft → approved`.

#### `governance.policy.activated`
- **Purpose:** An approved policy has become enforceable across the system.
- **Producer:** Policy Service.
- **Consumers:** Policy gate / enforcement points (Part 13 enforcement model), Audit Service, Observability, agents requiring policy accessibility (Part 13 invariant 6).
- **Trigger:** An approved policy is promoted to `active` and distributed to enforcement points.
- **Payload concept:** `{ "policy_id", "policy_version", "effective_at", "scope", "enforcement_points", "activated_by" }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → `governance.policy.approved`.
- **Ordering:** Per `policy_id`; strictly follows approval; cannot pre-empt a suspension of an earlier version.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P1 (activation changes enforcement, so propagation is critical).
- **Idempotency:** `event_id` dedup; idempotent activation (re-activation is a no-op if already active at version).
- **Security:** Signed; `confidential`; propagation is gated so only authorized enforcement points receive it.
- **Audit requirements:** Signed + chain-anchored; marks the moment a rule became binding.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `approved → activated`.

#### `governance.policy.suspended`
- **Purpose:** An active policy was temporarily disabled without retirement (e.g., emergency halt, pending investigation).
- **Producer:** Policy Service, Authority Service, or Security (emergency authority, Part 13 context).
- **Consumers:** Policy gate (stops enforcement), Audit Service, Observability, affected agents.
- **Trigger:** An authorized suspendor invokes suspension (time-bounded or indefinite) with rationale.
- **Payload concept:** `{ "policy_id", "policy_version", "reason", "suspended_by", "suspended_at", "resume_at?": null, "emergency": bool }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → `governance.policy.activated` (or → `security.policy.violated` if suspended due to a defect uncovered by a violation).
- **Ordering:** Per `policy_id`; supersedes `activated` for the active enforcement state.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P0 if `emergency` else P1.
- **Idempotency:** `event_id` dedup; multiple suspends are idempotent (state already suspended).
- **Security:** Signed; `confidential`; emergency suspensions are flagged and may trigger `monitoring.alert.raised` (Part 12 §14.4).
- **Audit requirements:** Signed + chain-anchored; suspension is a reversible but audited override.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `activated → suspended → activated|deprecated`.

#### `governance.policy.deprecated`
- **Purpose:** A policy (or version) is marked obsolete; no longer recommended, pending retirement.
- **Producer:** Policy Service.
- **Consumers:** Policy distribution engine (stops new enforcement), Audit Service, Observability, replacement-policy pointer consumers.
- **Trigger:** Policy owner marks the policy deprecated (replaced by a newer policy or no longer needed).
- **Payload concept:** `{ "policy_id", "policy_version", "replaced_by?": null, "deprecated_by", "deprecated_at", "removal_at?": null }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → `governance.policy.updated`/`suspended` as appropriate.
- **Ordering:** Per `policy_id`; follows activation/suspension; precedes `retired`.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `activated|suspended → deprecated → retired`.

#### `governance.policy.retired`
- **Purpose:** A policy is fully withdrawn from the system; no longer referenced by new code or enforcement.
- **Producer:** Policy Service.
- **Consumers:** Policy store (purge active references), Audit Service, Observability.
- **Trigger:** Deprecation window elapsed and migration complete; owner retires the policy (Part 13 policy lifecycle "Withdrawal").
- **Payload concept:** `{ "policy_id", "policy_version", "retired_by", "retired_at", "final_audit_ref" }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → `governance.policy.deprecated`.
- **Ordering:** Per `policy_id`; terminal event for that policy instance.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P1.
- **Idempotency:** `event_id` dedup; retirement is terminal/idempotent.
- **Security:** Signed; `confidential`; historical `policy_id` remains resolvable for audit.
- **Audit requirements:** Signed + chain-anchored; retirement is recorded but historical events remain in WORM log.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr (the retired *event* persists; the live policy reference is gone).
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `deprecated → retired`.

#### `governance.policy.violation.detected`
- **Purpose:** A governance policy was violated (or an attempted violation was pre-empted), recorded as a governance artifact for triage.
- **Producer:** Governance monitoring service (subscribes to `security.policy.violated`, Part 12 §13.1) or a governance enforcement point.
- **Consumers:** Exception handling (Part 13 exception lifecycle), Risk Service (may raise a risk), Compliance Service, Audit Service, Observability, Council (for review if severe).
- **Trigger:** A `security.policy.violated` event is observed, or governance monitoring independently detects a violation.
- **Payload concept:** `{ "policy_id", "violation_id", "actor", "subject_ref", "severity", "action_taken", "source_event_id": "<security.policy.violated event_id>", "detected_at" }`.
- **Correlation:** `correlation_id = policy_id` (or the violating workflow/correlation).
- **Causation:** `causation_id` → the originating `security.policy.violated` event (Part 12 §13.1) or the runtime action that violated the policy.
- **Ordering:** Per `policy_id`; multiple violations of the same policy are strictly ordered by detection time.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P0 for `critical`/`high` severity, P1 otherwise.
- **Idempotency:** `event_id` dedup; the same underlying `security.policy.violated` must not spawn duplicate governance records (dedup on `source_event_id`).
- **Security:** Signed; `confidential` minimum, `secret` if the violation touches credentials/keys; flagged and may page oncall (Part 12 §20).
- **Audit requirements:** Signed + chain-anchored; this is a primary compliance record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `open → triaged → exception.requested|resolved|escalated → closed`.

#### `governance.policy.exception.requested`
- **Purpose:** A party requests an exception (waiver/deviation) to a policy for a bounded scope and duration.
- **Producer:** Exception requester service (on behalf of an agent, workflow, or human).
- **Consumers:** Approval Service, Audit Service, Observability, the policy owner.
- **Trigger:** A detected or anticipated violation leads to a formal exception request (Part 13 exception lifecycle "Detection/Notification").
- **Payload concept:** `{ "exception_id", "policy_id", "requested_by", "scope", "justification", "requested_duration", "linked_violation_id?": null, "requested_at" }`.
- **Correlation:** `correlation_id = exception_id`.
- **Causation:** `causation_id` → `governance.policy.violation.detected` (if exception follows a violation) or → the action requiring deviation.
- **Ordering:** Per `policy_id`; exception requests for the same policy are ordered by request time.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one exception request yields one approval workflow.
- **Security:** Signed; `confidential`; requester identity non-repudiable.
- **Audit requirements:** Signed + chain-anchored; exceptions are high-scrutiny compliance records.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `requested → approved|rejected`.

#### `governance.policy.exception.approved`
- **Purpose:** An exception request was granted; the policy is relaxed for the approved scope/duration.
- **Producer:** Approval Service (or Authority Service acting under delegated authority).
- **Consumers:** Policy gate (applies the waiver), Audit Service, Observability, the requester.
- **Trigger:** Required approver(s) grant the exception per routing rules (Part 13.4).
- **Payload concept:** `{ "exception_id", "policy_id", "approver", "scope", "effective_from", "effective_to", "conditions", "approval_ref" }`.
- **Correlation:** `correlation_id = exception_id`.
- **Causation:** `causation_id` → `governance.policy.exception.requested`, and transitively → the linked violation.
- **Ordering:** Per `policy_id`; follows the matching `requested` event.
- **Delivery expectations:** At-least-once, P1 (enforcement must learn the waiver).
- **Idempotency:** `event_id` dedup; one approval per exception id.
- **Security:** Signed; `confidential`; approval is non-repudiable and alertable if scope is broad.
- **Audit requirements:** Signed + chain-anchored; approval of a deviation is a compliance-critical record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `requested → approved` (then active until `effective_to`).

#### `governance.policy.exception.rejected`
- **Purpose:** An exception request was denied.
- **Producer:** Approval Service (or Authority Service).
- **Consumers:** Audit Service, Observability, the requester, Risk Service (may record residual risk).
- **Trigger:** Required approver(s) deny the exception.
- **Payload concept:** `{ "exception_id", "policy_id", "rejector", "reason", "rejected_at", "appeal_ref?": null }`.
- **Correlation:** `correlation_id = exception_id`.
- **Causation:** `causation_id` → `governance.policy.exception.requested`.
- **Ordering:** Per `policy_id`; follows the matching `requested` event.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `requested → rejected`.

#### `governance.policy.submitted`
- **Purpose:** A draft policy was submitted into the review/approval pipeline (entered Review / Pending-Approval state).
- **Producer:** Policy Service.
- **Consumers:** Approval Service (opens the approval workflow), Audit Service, Observability, Council (if council-ratified).
- **Trigger:** The author submits a structurally valid draft for review; this causes an `approval.requested` of `requestType: policy_approval` to be opened (Part 13.3).
- **Payload concept:** `{ "policy_id", "policy_version", "submitted_by", "submitted_at", "approval_ref", "council_session_id?": null }`.
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** `causation_id` → `governance.policy.created`/`updated` (the draft being submitted). It is the proximate cause of the resulting `governance.approval.requested`.
- **Ordering:** Per `policy_id`; follows `created`/`updated`; strictly precedes `approved`.
- **Delivery expectations:** At-least-once, ordered per `policy_id`, P1.
- **Idempotency:** `event_id` dedup; a version is submitted once (resubmission after rejection re-opens as a new approval, not a duplicate).
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored; records entry into the governed approval path.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `draft → submitted → approved|rejected`.

#### `governance.policy.override.granted`
- **Purpose:** A policy/rule override was granted (distinct from an exception: overrides take precedence over exceptions, Part 13 `schemas.md` `PolicyOverride`).
- **Producer:** Override-authorizing service (authority holder with `override_authorization` delegation, or council per the `GovernanceDecision.decisionType = override_authorization`).
- **Consumers:** Policy gate (applies the override above any exception), Audit Service, Observability, the requester, Risk Service (residual risk of the override).
- **Trigger:** An authorized principal grants an override for emergency maintenance, emergency response, or other authorized deviation (Part 13.3 "Policy Overrides", distinct from "Policy Exceptions").
- **Payload concept:** `{ "override_id", "override_type", "target_id", "target_rule_id?": null, "overridden_action", "granted_by", "granted_at", "effective_from", "effective_until?": null, "justification", "decision_ref?": null }`.
- **Correlation:** `correlation_id = policy_id` (the overridden policy; `override_id` is the artifact id).
- **Causation:** `causation_id` → the governing `governance.decision.approved` (when override-authorization is council-issued) or → the `governance.approval.granted` that permitted it.
- **Ordering:** Per `policy_id`; an override supersedes any active exception for the same target while `effective`.
- **Delivery expectations:** At-least-once, P0 (overrides change enforcement immediately and are alertable).
- **Idempotency:** `event_id` dedup; one grant per `override_id`.
- **Security:** Signed; `confidential`; overrides are high-scrutiny and flagged for monitoring/alert.
- **Audit requirements:** Signed + chain-anchored; an override is a compliance-critical record (an authorization to deviate from policy).
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `granted → effective → expired|revoked`.

#### `governance.policy.exception.expiring`
- **Purpose:** An approved exception is approaching its expiry window and will soon revert to strict policy enforcement.
- **Producer:** Exception Service (time-driven sweep) or the scheduler.
- **Consumers:** Exception Service (manages renewal/expiration), Policy gate, Audit Service, Observability, the requester/approver.
- **Trigger:** The exception's `effective_to` enters the configured pre-expiry warning window; distinct from terminal `ExceptionExpired` in components.md G-11.
- **Payload concept:** `{ "exception_id", "policy_id", "expires_at", "warning_window", "renewal_ref?": null, "emitted_at" }`.
- **Correlation:** `correlation_id = exception_id`.
- **Causation:** `causation_id` → the matching `governance.policy.exception.approved`; proximate cause of a later `governance.approval.requested` if renewed.
- **Ordering:** Per `policy_id`; follows `exception.approved`; precedes the terminal expiry (no separate `expired` event is defined here — expiry is handled by components.md G-11; see §16).
- **Delivery expectations:** At-least-once, P2 (warning, not enforcement-critical), P1 if auto-renewal is blocked.
- **Idempotency:** `event_id` dedup; one warning per window (re-emitted only on re-notification).
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored; recorded for exception lifecycle completeness.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `approved → expiring → expired|renewed`.

#### `governance.policy.conflict.detected`
- **Purpose:** Two or more policies (or rules within scope) were found to conflict, creating ambiguous or contradictory obligations.
- **Producer:** Policy analysis service (static analysis at authoring/activation, or at evaluation time).
- **Consumers:** Policy Service (resolution), Audit Service, Observability, Council (if severe), the policy owners.
- **Trigger:** A conflict check surfaces overlapping/contrary rules for the same target/condition (Part 13.3 "policy conflict").
- **Payload concept:** `{ "conflict_id", "policy_ids", "rule_ids", "scope", "conflict_kind", "detected_by", "detected_at", "severity" }`.
- **Correlation:** `correlation_id = policy_id` (primary conflicting policy; may span multiple).
- **Causation:** Root for the conflict instance; may cite the `governance.policy.updated`/`activated` that introduced the overlap.
- **Ordering:** Per `policy_id`; multiple conflicts for the same policy are ordered by detection time.
- **Delivery expectations:** At-least-once, P1 (conflicts threaten correct enforcement).
- **Idempotency:** `event_id` dedup; dedup on `(policy_ids, rule_ids, scope)` within a resolution window.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored; conflict detection is part of the assurance trail.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `open → triaged → resolved|escalated`.

#### `governance.policy.validation.failed`
- **Purpose:** A policy (or policy revision) failed structural/semantic validation and was not accepted into the governed lifecycle.
- **Producer:** Policy Service (validation gate).
- **Consumers:** Policy Service (author correction), Audit Service, Observability, the author.
- **Trigger:** A draft/submit fails schema, rule, or governance validation (Part 13.3 validation step that guards `policy.created`/`submitted`).
- **Payload concept:** `{ "policy_id", "policy_version?": null, "validation_errors", "failed_at", "failed_by", "stage" }` (stage ∈ {draft, submit}).
- **Correlation:** `correlation_id = policy_id`.
- **Causation:** Root for the rejected attempt; if the policy later passes, `governance.policy.created`/`submitted` is the succeeding event, correlated by `policy_id`.
- **Ordering:** Per `policy_id`; precedes any successful `created`/`submitted` for that attempt.
- **Delivery expectations:** At-least-once, P2 (authoring feedback); P1 if failure blocks a required activation.
- **Idempotency:** `event_id` dedup; one failure record per validation pass.
- **Security:** Signed; `confidential` (may echo redacted rule fragments).
- **Audit requirements:** Signed + chain-anchored; records that an invalid policy was rejected at the gate.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `attempted → failed → (corrected → created|submitted)`.

### 3.2 Decision Aggregate

#### `governance.decision.created`
- **Purpose:** A governance decision record was opened (a significant decision requiring governance trail).
- **Producer:** Decision Service (Part 13.4) or Council Orchestrator (recording from `council.decision.published`, Part 12 §7.7).
- **Consumers:** Approval Service (if approval required), Audit Service, Observability, accountable owners.
- **Trigger:** A decision trigger occurs (Part 13 decision lifecycle "Initiation") — event, request, or scheduled process.
- **Payload concept:** `{ "decision_id", "kind", "context_ref", "initiated_by", "council_session_id?": null, "requires_approval": bool, "created_at" }`.
- **Correlation:** `correlation_id = decision_id`.
- **Causation:** Root for the decision instance; if council-derived, `causation_id` → `council.decision.published` (Part 12 §7.7).
- **Ordering:** First event of any `decision_id`; strictly precedes `approved`/`rejected`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one create per decision id.
- **Security:** Signed; `confidential` (decisions may encode sensitive rationale).
- **Audit requirements:** Signed + chain-anchored; the origin of the decision trail.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `created → approved|rejected`.

#### `governance.decision.approved`
- **Purpose:** A governance decision was authorized by the required decision rights holder(s).
- **Producer:** Decision Service / Authority Service, or Council Orchestrator (from `council.decision.published`).
- **Consumers:** Enforcement/implementation consumers, Audit Service, Observability, accountable owners.
- **Trigger:** Required approvers grant the decision per decision rights (Part 13 "Decision Rights").
- **Payload concept:** `{ "decision_id", "approver", "approver_role", "decision_ref", "council_session_id?": null, "approved_at", "implementation_ref?": null }`.
- **Correlation:** `correlation_id = decision_id`.
- **Causation:** `causation_id` → `governance.decision.created` (or → `council.decision.published`).
- **Ordering:** Per `decision_id`; follows `created`; precedes implementation actions.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; a decision is approved once; duplicates ignored.
- **Security:** Signed; `confidential`; approver identity non-repudiable.
- **Audit requirements:** Signed + chain-anchored; compliance-critical.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `created → approved`.

#### `governance.decision.rejected`
- **Purpose:** A governance decision was denied by the required decision rights holder(s).
- **Producer:** Decision Service / Authority Service, or Council Orchestrator.
- **Consumers:** Audit Service, Observability, initiator, Risk Service (residual risk).
- **Trigger:** Required approvers deny the decision.
- **Payload concept:** `{ "decision_id", "rejector", "reason", "rejected_at", "appeal_ref?": null }`.
- **Correlation:** `correlation_id = decision_id`.
- **Causation:** `causation_id` → `governance.decision.created`.
- **Ordering:** Per `decision_id`; follows `created`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `created → rejected`.

### 3.3 Authority Aggregate

#### `governance.authority.delegated`
- **Purpose:** A grant of governance authority was delegated from one entity to another (Part 13 "Delegated Authority").
- **Producer:** Authority Service (Part 13.4).
- **Consumers:** Enforcement points, Audit Service, Observability, the delegate, the delegator (accountability retained).
- **Trigger:** A delegator with sufficient authority issues a delegation under explicit, documented conditions.
- **Payload concept:** `{ "authority_id", "delegator", "delegate", "scope", "decision_rights", "granted_at", "expires_at?": null, "subdelegable": bool, "approved_by?": null }`.
- **Correlation:** `correlation_id = authority_id`.
- **Causation:** `causation_id` → `governance.approval.granted` if the delegation required prior approval; otherwise a root for the authority instance.
- **Ordering:** Per `authority_id`; a delegation and its later revocation are strictly ordered.
- **Delivery expectations:** At-least-once, P1 (authority changes must propagate before dependent actions).
- **Idempotency:** `event_id` dedup; duplicate delegation of the same `authority_id` is a no-op.
- **Security:** Signed; `confidential`; delegation is a high-sensitivity governance action.
- **Audit requirements:** Signed + chain-anchored; authority grants are primary accountability records (Part 13 "No Action Without Authority" invariant).
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `delegated → active → revoked|expired`.

#### `governance.authority.revoked`
- **Purpose:** A previously delegated authority was withdrawn.
- **Producer:** Authority Service (delegator or a higher authority).
- **Consumers:** Enforcement points (stop honoring the authority), Audit Service, Observability, the former delegate.
- **Trigger:** Misuse, condition change, expiry, or higher-authority override.
- **Payload concept:** `{ "authority_id", "revoked_by", "reason", "revoked_at", "cascade": bool }`.
- **Correlation:** `correlation_id = authority_id`.
- **Causation:** `causation_id` → the matching `governance.authority.delegated`.
- **Ordering:** Per `authority_id`; terminal event for that authority instance; must follow any actions taken under the authority.
- **Delivery expectations:** At-least-once, P1 (must propagate before the delegate acts again).
- **Idempotency:** `event_id` dedup; revocation is terminal/idempotent.
- **Security:** Signed; `confidential`; revocation of security-relevant authority is flagged.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `active → revoked`.

### 3.4 Approval Aggregate

#### `governance.approval.requested`
- **Purpose:** A formal request for approval was submitted (policy, decision, action, or authority).
- **Producer:** The requesting service (Policy, Decision, Authority, or an operational workflow seeking governance sign-off).
- **Consumers:** Approval Service, Audit Service, Observability, the targeted approver(s).
- **Trigger:** A governance-controlled action requires approval (Part 13 approval lifecycle "Request Submission").
- **Payload concept:** `{ "approval_id", "target_kind", "target_ref", "requested_by", "routing", "justification", "requested_at" }`.
- **Correlation:** `correlation_id = approval_id`.
- **Causation:** Root for the approval instance; may cite the action awaiting approval.
- **Ordering:** First event of any `approval_id`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one request yields one approval workflow.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `requested → granted|rejected`.

#### `governance.approval.granted`
- **Purpose:** An approval request was granted; the target action may proceed.
- **Producer:** Approval Service.
- **Consumers:** The requesting service (proceeds), Audit Service, Observability, dependent governance events (e.g., `authority.delegated`).
- **Trigger:** Approver evaluates and grants per routing (Part 13 approval lifecycle "Decision").
- **Payload concept:** `{ "approval_id", "target_kind", "target_ref", "approver", "approval_ref", "granted_at", "conditions?": null }`.
- **Correlation:** `correlation_id = approval_id`.
- **Causation:** `causation_id` → `governance.approval.requested`.
- **Ordering:** Per `approval_id`; follows `requested`.
- **Delivery expectations:** At-least-once, P1 (downstream action depends on it).
- **Idempotency:** `event_id` dedup; one grant per approval id.
- **Security:** Signed; `confidential`; approver non-repudiable.
- **Audit requirements:** Signed + chain-anchored; approvals are compliance-critical.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `requested → granted`.

#### `governance.approval.rejected`
- **Purpose:** An approval request was denied; the target action may not proceed.
- **Producer:** Approval Service.
- **Consumers:** The requesting service (halts), Audit Service, Observability, Risk Service.
- **Trigger:** Approver denies the request.
- **Payload concept:** `{ "approval_id", "target_kind", "target_ref", "rejector", "reason", "rejected_at", "appeal_ref?": null }`.
- **Correlation:** `correlation_id = approval_id`.
- **Causation:** `causation_id` → `governance.approval.requested`.
- **Ordering:** Per `approval_id`; follows `requested`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `requested → rejected`.

### 3.5 Risk Aggregate

#### `governance.risk.identified`
- **Purpose:** A risk was identified and registered in the risk register (Part 13.6).
- **Producer:** Risk Service.
- **Consumers:** Risk Service (tracking), Audit Service, Observability, Compliance Service, Council (if high).
- **Trigger:** Analysis, monitoring, or reporting surfaces a potential risk (Part 13 risk lifecycle "Identification").
- **Payload concept:** `{ "risk_id", "title", "category", "likelihood", "impact", "identified_by", "identified_at", "owner?": null }`.
- **Correlation:** `correlation_id = risk_id`.
- **Causation:** Root for the risk instance; may cite a `governance.policy.violation.detected` or `compliance.violation.detected` that surfaced it.
- **Ordering:** First event of any `risk_id`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one identify per risk id.
- **Security:** Signed; `confidential` (risk content may be sensitive).
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `identified → analyzed → prioritized → mitigated|escalated|accepted`.

#### `governance.risk.escalated`
- **Purpose:** A risk exceeded tolerance and was escalated to a higher governance level.
- **Producer:** Risk Service (or monitor triggering auto-escalation).
- **Consumers:** Higher authority / Council, Audit Service, Observability, oncall.
- **Trigger:** Risk severity crosses a tolerance threshold (Part 13 risk lifecycle "Escalation").
- **Payload concept:** `{ "risk_id", "from_level", "to_level", "reason", "escalated_by", "escalated_at", "target_authority" }`.
- **Correlation:** `correlation_id = risk_id`.
- **Causation:** `causation_id` → `governance.risk.identified` (or the prior `risk.escalated`).
- **Ordering:** Per `risk_id`; escalation chain is strictly ordered.
- **Delivery expectations:** At-least-once, P0 (escalation demands prompt attention).
- **Idempotency:** `event_id` dedup; multiple escalations of the same risk form a chain, not duplicates.
- **Security:** Signed; `confidential`; escalation may page oncall (Part 12 §14.4).
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `identified → escalated → accepted|mitigated`.

#### `governance.risk.accepted`
- **Purpose:** Residual risk was formally accepted (post-mitigation) by the accountable authority.
- **Producer:** Risk Service (recording acceptance by the risk owner/authority).
- **Consumers:** Audit Service, Observability, Compliance Service, Council.
- **Trigger:** Risk owner acknowledges residual risk within tolerance (Part 13 risk lifecycle "Acceptance").
- **Payload concept:** `{ "risk_id", "acceptor", "acceptor_role", "residual_likelihood", "residual_impact", "accepted_at", "review_by?": null }`.
- **Correlation:** `correlation_id = risk_id`.
- **Causation:** `causation_id` → `governance.risk.identified`/`risk.escalated`.
- **Ordering:** Per `risk_id`; follows identification/escalation.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; acceptance is recorded once per acceptance decision.
- **Security:** Signed; `confidential`; acceptance is a non-repudiable accountability act.
- **Audit requirements:** Signed + chain-anchored; formal risk acceptance is a compliance record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `identified|escalated → accepted`.

### 3.6 Compliance Aggregate

#### `governance.compliance.violation.detected`
- **Purpose:** A violation of an external regulation or internal compliance standard was detected.
- **Producer:** Compliance Service (or a control/conformance evaluation that surfaced the violation).
- **Consumers:** Audit Service, Risk Service (may raise a risk), Observability, Council, regulators-facing reporting.
- **Trigger:** A control evaluation, conformance check, or external signal indicates non-compliance.
- **Payload concept:** `{ "violation_id", "framework", "requirement_ref", "scope_id", "severity", "detected_by", "detected_at", "source_event_id?": null }`.
- **Correlation:** `correlation_id = scope_id` (e.g., `tenant_id`).
- **Causation:** `causation_id` → the `governance.control.evaluated`/`conformance.failed` that surfaced it, or an external report.
- **Ordering:** Per `scope_id`; multiple violations within a scope are ordered by detection time.
- **Delivery expectations:** At-least-once, P0 for `critical`/`high`, P1 otherwise.
- **Idempotency:** `event_id` dedup; dedup on `source_event_id` to avoid duplicate compliance records.
- **Security:** Signed; `confidential`; compliance violations are regulated records, access-restricted.
- **Audit requirements:** Signed + chain-anchored; this is a primary regulatory compliance record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr (regulatory retention may extend cold per framework).
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `open → triaged → remediated → closed`.

### 3.7 Audit Aggregate

#### `governance.audit.started`
- **Purpose:** A governance audit commenced (Part 13.11, Part 13 audit lifecycle "Planning/Notification").
- **Producer:** Audit Service.
- **Consumers:** Audit Service (fieldwork), Audit Service consumers, Observability.
- **Trigger:** Scheduled or triggered audit reaches its start condition.
- **Payload concept:** `{ "audit_id", "scope", "objective", "methodology", "auditor", "started_at", "planned_end?": null }`.
- **Correlation:** `correlation_id = audit_id`.
- **Causation:** Root for the audit instance.
- **Ordering:** First event of any `audit_id`; strictly precedes `audit.completed`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one start per audit id.
- **Security:** Signed; `confidential` (audit scope may be sensitive).
- **Audit requirements:** Signed + chain-anchored; marks audit commencement.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `planned → started → fieldwork → reported → closed → archived`.

#### `governance.audit.completed`
- **Purpose:** A governance audit concluded and its report was issued.
- **Producer:** Audit Service.
- **Consumers:** Audit Service (follow-up), Compliance Service, Observability, Council, accountable owners.
- **Trigger:** Fieldwork and reporting complete; closure report issued (Part 13 audit lifecycle "Reporting/Archival").
- **Payload concept:** `{ "audit_id", "report_ref", "findings_count", "outcome", "completed_at", "follow_up_refs?": null }`.
- **Correlation:** `correlation_id = audit_id`.
- **Causation:** `causation_id` → `governance.audit.started`.
- **Ordering:** Per `audit_id`; terminal for the active audit; follows all fieldwork.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; completion recorded once.
- **Security:** Signed; `confidential`; audit reports are restricted.
- **Audit requirements:** Signed + chain-anchored; the audit closure is a key assurance record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr (audit records often retained at the cold tier for the full regulatory period).
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `started → completed`.

### 3.8 Control & Conformance Aggregate

#### `governance.control.evaluated`
- **Purpose:** A governance control was evaluated and produced a result (effectiveness/status).
- **Producer:** Control Service / conformance engine.
- **Consumers:** Compliance Service, Risk Service, Audit Service, Observability, Conformance Service.
- **Trigger:** A scheduled or event-driven control evaluation ran.
- **Payload concept:** `{ "control_id", "evaluation_id", "status", "result", "evidence_ref", "evaluated_by", "evaluated_at" }`.
- **Correlation:** `correlation_id = control_id`.
- **Causation:** Root for the evaluation instance; may cite an `audit.started` or a monitoring signal.
- **Ordering:** Per `control_id`; evaluations are ordered by time.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one evaluation record per `evaluation_id`.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored; control evidence feeds compliance assurance.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `scheduled → evaluated → passed|failed`.

#### `governance.conformance.verified`
- **Purpose:** A system artifact/behavior was verified as conformant with a governance requirement.
- **Producer:** Conformance Service (or a control evaluation that concluded conformant).
- **Consumers:** Compliance Service, Audit Service, Observability, the verified artifact's owner.
- **Trigger:** Conformance check passed against the required standard/policy.
- **Payload concept:** `{ "control_id", "target_ref", "requirement_ref", "verified_at", "verifier", "evidence_ref" }`.
- **Correlation:** `correlation_id = control_id`.
- **Causation:** `causation_id` → `governance.control.evaluated` (the evaluation that established conformance).
- **Ordering:** Per `control_id`; paired with the matching `control.evaluated`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; a verification is recorded once per check.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored; positive conformance is part of the assurance trail.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `checked → verified`.

#### `governance.conformance.failed`
- **Purpose:** A system artifact/behavior failed a conformance check against a governance requirement.
- **Producer:** Conformance Service (or a control evaluation that concluded non-conformant).
- **Consumers:** Compliance Service (→ `compliance.violation.detected`), Risk Service, Audit Service, Observability, Council, the owner.
- **Trigger:** Conformance check failed against the required standard/policy.
- **Payload concept:** `{ "control_id", "target_ref", "requirement_ref", "failed_at", "verifier", "gap", "severity", "evidence_ref" }`.
- **Correlation:** `correlation_id = control_id`.
- **Causation:** `causation_id` → `governance.control.evaluated`.
- **Ordering:** Per `control_id`; paired with the matching `control.evaluated`; precedes any resulting `compliance.violation.detected`.
- **Delivery expectations:** At-least-once, P1 (often P0 for `critical` gaps).
- **Idempotency:** `event_id` dedup; dedup on `(control_id, target_ref, evaluation_id)` to avoid duplicate failure records.
- **Security:** Signed; `confidential`; failures are sensitive and may alert (Part 12 §14.4).
- **Audit requirements:** Signed + chain-anchored; a primary non-conformance record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `checked → failed → remediated → re-verified`.

### 3.9 Agent Aggregate

#### `governance.agent.created`
- **Purpose:** An agent identity was registered in the agent store.
- **Producer:** Agent Provisioning Service (Part 13.7).
- **Consumers:** Policy Evaluation Engine (for policy applicability), Audit Service, Observability, Agent Runtime.
- **Trigger:** Agent identity creation request validated and registered.
- **Payload concept:** `{ "agent_id", "name", "version", "created_by", "created_at", "initial_authorities", "initial_capabilities" }`.
- **Correlation:** `correlation_id = agent_id`.
- **Causation:** Root event for the agent instance.
- **Ordering:** First event of any `agent_id`; strictly precedes all other `governance.agent.*` events for that agent.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; projection writers reject a second `created` for an existing `agent_id`.
- **Security:** Signed; `confidential`; agent identity is sensitive.
- **Audit requirements:** Signed + chain-anchored; establishes the immutable origin record of the agent.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.
- **Lifecycle:** Record lifecycle: `registered → provisioned → activated → suspended|revoked → archived`.

#### `governance.agent.provisioned`
- **Purpose:** Capabilities and authority were assigned to an agent.
- **Producer:** Agent Provisioning Service.
- **Consumers:** Policy Evaluation Engine, Audit Service, Observability, Agent Runtime.
- **Trigger:** Agent identity registered; initial capabilities and authorities granted.
- **Payload concept:** `{ "agent_id", "capability_ids", "authority_ids", "provisioned_by", "provisioned_at" }`.
- **Correlation:** `correlation_id = agent_id`.
- **Causation:** `causation_id` → `governance.agent.created`.
- **Ordering:** Per `agent_id`; precedes `activated`.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; provisioning record created once.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.activated`
- **Purpose:** An agent became operational.
- **Producer:** Agent Management Service.
- **Consumers:** Agent Runtime (can now operate), Policy Evaluation Engine, Risk Service, Audit Service, Observability.
- **Trigger:** Agent passes activation checks and becomes operational.
- **Payload concept:** `{ "agent_id", "activated_by", "activated_at", "activation_context" }`.
- **Correlation:** `correlation_id = agent_id`.
- **Causation:** `causation_id` → `governance.agent.provisioned`.
- **Ordering:** Per `agent_id`; follows provisioning.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; activation record created once.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.suspended`
- **Purpose:** An agent was temporarily suspended.
- **Producer:** Agent Management Service or Security Service.
- **Consumers:** Agent Runtime (suspends operations), Policy Evaluation Engine, Audit Service, Observability.
- **Trigger:** Suspension action invoked by authorized authority.
- **Payload concept:** `{ "agent_id", "suspended_by", "reason", "suspended_at", "resume_at?": null, "emergency": bool }`.
- **Correlation:** `correlation_id = agent_id`.
- **Causation:** `causation_id` → `governance.agent.activated`.
- **Ordering:** Per `agent_id`; supersedes `activated` for active status.
- **Delivery expectations:** At-least-once, P0 if `emergency` else P1.
- **Idempotency:** `event_id` dedup; multiple suspends are idempotent.
- **Security:** Signed; `confidential`; emergency suspensions are flagged.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.revoked`
- **Purpose:** An agent identity was permanently revoked.
- **Producer:** Agent Management Service.
- **Consumers:** Agent Runtime (terminates), Policy Evaluation Engine, Risk Service, Audit Service, Observability.
- **Trigger:** Revocation action invoked by authorized authority.
- **Payload concept:** `{ "agent_id", "revoked_by", "reason", "revoked_at", "cascade_result" }`.
- **Correlation:** `correlation_id = agent_id`.
- **Causation:** `causation_id` → `governance.agent.suspended` or `governance.agent.activated`.
- **Ordering:** Per `agent_id`; terminal event for the agent.
- **Delivery expectations:** At-least-once, P0.
- **Idempotency:** `event_id` dedup; revocation is terminal/idempotent.
- **Security:** Signed; `confidential` (credential compromise, etc.).
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.action`
- **Purpose:** An agent performed an action.
- **Producer:** Agent Runtime.
- **Consumers:** Policy Evaluation Engine, Audit Service, Observability, Accountability Manager.
- **Trigger:** Agent operation executed.
- **Payload concept:** `{ "agent_id", "action_id", "action_type", "target_ref", "parameters", "performed_at" }`.
- **Correlation:** `correlation_id = action_id` (or `agent_id` for agent-scoped actions).
- **Causation:** Root for the action; may cite `governance.agent.activated`.
- **Ordering:** Per `action_id`; ordered by execution time.
- **Delivery expectations:** At-least-once, P2.
- **Idempotency:** `event_id` dedup; action recorded once.
- **Security:** Signed; `internal` classification (agent self-reporting).
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 1yr / Cold 5yr (operational action records).
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.action.denied`
- **Purpose:** An agent action was denied by policy.
- **Producer:** Policy Evaluation Engine.
- **Consumers:** Agent Runtime (receives denial), Audit Service, Observability, Owner.
- **Trigger:** Policy gate rejects an agent action.
- **Payload concept:** `{ "agent_id", "action_id", "policy_id", "reason", "denied_at" }`.
- **Correlation:** `correlation_id = action_id` or `agent_id`.
- **Causation:** `causation_id` → `governance.agent.action` (or the triggering request).
- **Ordering:** Per `action_id`; follows the original action attempt.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; one denial per action.
- **Security:** Signed; `confidential`; security-relevant denial may be flagged.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.behavior.anomaly`
- **Purpose:** Anomaly detected in agent behavior.
- **Producer:** Behavior Monitoring Service.
- **Consumers:** Risk Service (may escalate), Audit Service, Observability, Security Council.
- **Trigger:** Pattern matching or statistical analysis detects anomalous behavior.
- **Payload concept:** `{ "agent_id", "anomaly_id", "pattern", "confidence", "detected_at", "evidence_refs" }`.
- **Correlation:** `correlation_id = agent_id`.
- **Causation:** Root for the anomaly detection; may cite `governance.agent.action` sequences.
- **Ordering:** Per `agent_id`; anomalies are ordered by detection time.
- **Delivery expectations:** At-least-once, P1 (anomalies may be security-relevant).
- **Idempotency:** `event_id` dedup; one anomaly record per detection.
- **Security:** Signed; `confidential`; anomalies may involve sensitive behavioral data.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.agent.accountability.gap`
- **Purpose:** An agent action could not be bound to a principal.
- **Producer:** Accountability Manager.
- **Consumers:** Audit Service, Observability, Security Council.
- **Trigger:** Accountability binding fails or evidence is missing.
- **Payload concept:** `{ "agent_id", "action_id", "gap_type", "detected_at", "investigation_ref" }`.
- **Correlation:** `correlation_id = agent_id` or `action_id`.
- **Causation:** `causation_id` → `governance.agent.action` or `governance.agent.behavior.anomaly`.
- **Ordering:** Per `agent_id`; processed in detection order.
- **Delivery expectations:** At-least-once, P0 (accountability gaps are critical).
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`; accountability failures are highly sensitive.
- **Audit requirements:** Signed + chain-anchored; critical compliance record.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

### 3.10 Capability Aggregate

#### `governance.capability.created`
- **Purpose:** A new capability was defined.
- **Producer:** Capability Management Service (Part 13.7).
- **Consumers:** Audit Service, Observability, Policy Evaluation Engine, Authority Service.
- **Trigger:** Capability definition submitted and validated.
- **Payload concept:** `{ "capability_id", "name", "category", "risk_level", "scope", "created_by", "created_at" }`.
- **Correlation:** `correlation_id = capability_id`.
- **Causation:** Root event for the capability instance.
- **Ordering:** First event of any `capability_id`; precedes `issued`.
- **Delivery expectations:** At-least-once, P2.
- **Idempotency:** `event_id` dedup; one create per capability.
- **Security:** Signed; `internal` (capability definitions are governance metadata).
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.issued`
- **Purpose:** A capability was granted to an agent.
- **Producer:** Capability Management Service or Authority Service.
- **Consumers:** Agent Runtime (can use), Policy Evaluation Engine, Risk Service, Audit Service, Observability.
- **Trigger:** Capability grant approved and recorded.
- **Payload concept:** `{ "capability_id", "agent_id", "issued_by", "effective_from", "effective_until?": null, "constraints", "issued_at" }`.
- **Correlation:** `correlation_id = capability_id` (or `agent_id`).
- **Causation:** `causation_id` → `governance.capability.created` or `governance.approval.granted`.
- **Ordering:** Per `capability_id`; follows `created`.
- **Delivery expectations:** At-least-once, P1 (critical for agent operation).
- **Idempotency:** `event_id` dedup; one issue record per grant.
- **Security:** Signed; `confidential`; capability grants are highly sensitive.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.revoked`
- **Purpose:** A capability was revoked from an agent.
- **Producer:** Capability Management Service or Authority Service.
- **Consumers:** Agent Runtime (can no longer use), Audit Service, Observability, Risk Service.
- **Trigger:** Revocation action invoked.
- **Payload concept:** `{ "capability_id", "agent_id", "revoked_by", "reason", "revoked_at", "cascade": bool }`.
- **Correlation:** `correlation_id = capability_id` (or `agent_id`).
- **Causation:** `causation_id` → `governance.capability.issued` or `governance.agent.revoked`.
- **Ordering:** Per `capability_id`; terminal event for that grant.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup; revocation is terminal/idempotent.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.expired`
- **Purpose:** A capability expired by temporal bound.
- **Producer:** Capability Management Service.
- **Consumers:** Agent Runtime (can no longer use), Audit Service, Observability.
- **Trigger:** `effectiveUntil` timestamp reached.
- **Payload concept:** `{ "capability_id", "agent_id", "expired_at" }`.
- **Correlation:** `correlation_id = capability_id` (or `agent_id`).
- **Causation:** `causation_id` → `governance.capability.issued`.
- **Ordering:** Per `capability_id`; terminal event for that grant.
- **Delivery expectations:** At-least-once, P2 (scheduled).
- **Idempotency:** `event_id` dedup; expiration is terminal/idempotent.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.suspended`
- **Purpose:** A capability was temporarily suspended.
- **Producer:** Capability Management Service or Security Service.
- **Consumers:** Agent Runtime (can no longer use), Audit Service, Observability.
- **Trigger:** Suspension action invoked by authorized authority.
- **Payload concept:** `{ "capability_id", "agent_id", "suspended_by", "reason", "suspended_at", "resume_at?": null, "emergency": bool }`.
- **Correlation:** `correlation_id = capability_id` (or `agent_id`).
- **Causation:** `causation_id` → `governance.capability.issued`.
- **Ordering:** Per `capability_id`; supersedes `issued` for active status.
- **Delivery expectations:** At-least-once, P0 if `emergency` else P1.
- **Idempotency:** `event_id` dedup; multiple suspends are idempotent.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.modified`
- **Purpose:** A capability definition or scope was modified.
- **Producer:** Capability Management Service.
- **Consumers:** Audit Service, Observability, owners, affected agents.
- **Trigger:** Modification approved and applied.
- **Payload concept:** `{ "capability_id", "from_version", "to_version", "modified_fields", "modified_by", "modified_at" }`.
- **Correlation:** `correlation_id = capability_id`.
- **Causation:** `causation_id` → `governance.capability.created` or `governance.capability.issued`.
- **Ordering:** Per `capability_id`; follows the prior event.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.used`
- **Purpose:** A capability was exercised by an agent.
- **Producer:** Agent Runtime.
- **Consumers:** Behavior Monitoring Service, Audit Service, Observability, Risk Service.
- **Trigger:** Agent operation using a capability executes.
- **Payload concept:** `{ "capability_id", "agent_id", "action_id", "used_at" }`.
- **Correlation:** `correlation_id = capability_id` (or `action_id`).
- **Causation:** Root for the usage; may cite `governance.agent.action`.
- **Ordering:** Per `capability_id`; ordered by usage time.
- **Delivery expectations:** At-least-once, P2.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `internal` classification (runtime self-reporting).
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 1yr / Cold 5yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.usage.violation`
- **Purpose:** Capability was used outside its constraints.
- **Producer:** Behavior Monitoring Service.
- **Consumers:** Audit Service, Observability, Risk Service, Security.
- **Trigger:** Usage violates defined constraints (scope, temporal, parameter limits).
- **Payload concept:** `{ "capability_id", "agent_id", "violation_id", "constraint_breached", "actual_value", "expected_limit", "detected_at" }`.
- **Correlation:** `correlation_id = capability_id` or `agent_id`.
- **Causation:** `causation_id` → `governance.capability.used`.
- **Ordering:** Per `capability_id`; follows the usage that violated.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`; constraint violations may be security-relevant.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

#### `governance.capability.usage.anomaly`
- **Purpose:** Unusual capability usage pattern detected.
- **Producer:** Behavior Monitoring Service.
- **Consumers:** Risk Service, Audit Service, Observability, Security Council.
- **Trigger:** Statistical analysis detects anomalous usage.
- **Payload concept:** `{ "capability_id", "agent_id", "anomaly_id", "pattern", "confidence", "detected_at", "evidence_refs" }`.
- **Correlation:** `correlation_id = capability_id`.
- **Causation:** Root for the anomaly detection.
- **Ordering:** Per `capability_id`; ordered by detection time.
- **Delivery expectations:** At-least-once, P1.
- **Idempotency:** `event_id` dedup.
- **Security:** Signed; `confidential`.
- **Audit requirements:** Signed + chain-anchored.
- **Retention:** Hot 30d / Warm 3yr / Cold 7yr.
- **Versioning:** Event schema per Part 12 §27.

---

## 4. Event Naming Convention

Governance events obey the Part 12 naming RFC (§25) **without exception**:

```
ai-os.event.governance.<aggregate>.<action>[.<qualifier>]@<major>.<minor>
```

- **Canonical identity is sole and exclusive.** The canonical wire-level `event_type` for every governance event is **`governance.<aggregate>.<action>[.<qualifier>]`** in lowercase dotted form. There is exactly one canonical name per event type. No other form (PascalCase, shorthands such as `policy.drafted`, or ad-hoc aliases) is ever canonical and they MUST NOT appear as competing canonical event names in any definition, catalog entry, schema, or consumer subscription.
- The wire-level `event_type` drops the `ai-os.event.` prefix and uses the short form, e.g. `governance.policy.activated`.
- Components are lowercase, alphanumeric, dot-separated. No underscores/hyphens/camelCase in the FQN.
- `qualifier` (e.g., `violation`, `exception`) yields a **distinct event type** with its own schema, version, and lifecycle (Part 12 §25).
- Names are immutable once registered; aliases are forbidden (Part 12 §25). Consumers subscribe to the canonical FQN.
- Conceptual PascalCase labels in governance prose (e.g., `PolicyActivated`) and Part-13-internal short names (e.g., `policy.drafted`) map 1:1 to the canonical lowercase `event_type`; they are **non-canonical, for readability only**, and are NEVER emitted on the wire.

### Rule: No Competing Canonical Names

Older shorthand names, PascalCase conceptual labels, and legacy references (e.g., `PolicyCreated`, `policy.drafted`, `policy.modified`, `policy.override`, `policy.violation`) MAY appear in:

1. **Prose** — when describing events conceptually or mapping to Part 13 domain documents.
2. **Cross-reference tables** — when mapping `policies.md` short names to the canonical FQN (see §2).
3. **Glossaries** — when defined as non-canonical terminology.

They MUST NOT appear as:
- A canonical `event_type` value in any event definition or catalog entry.
- A registry entry or schema name in the Event Registry (Part 12 §28).
- A consumer subscription topic.
- A competing identity for the same event.

Where a shorthand name exists, it is recorded in the §2 mapping table as **non-canonical** and points unambiguously to the single canonical FQN. If a shorthand name cannot be mapped to a canonical FQN, it is legacy terminology and MUST NOT be used as an event identity anywhere.

### Legacy and Alias Handling

This document is the single authoritative taxonomy for `governance.*` events (see §1). Any shorthand name or PascalCase label appearing in Part 13 documents (e.g., `policies.md` §"Policy Events", `glossary.md`) that refers to a governance event is an **alias** or **conceptual shorthand** for the canonical FQN registered here.

- **Aliases are non-normative.** They are useful for human communication and cross-document mapping, but they carry no weight in routing, schema resolution, or consumer logic.
- **No new aliases may be registered** as canonical event identifiers (Part 12 §25 naming constraints).
- All event definitions in §3, the catalog in §15, and any schema references use the canonical `governance.<aggregate>.<action>[.<qualifier>]` form exclusively.
- When this document references a Part 13 shorthand name (e.g., in the §2 mapping table), it explicitly labels the column as "non-canonical" to make the distinction unambiguous.

---

## 5. Event Namespace

This document **registers the `governance` namespace** as a new entry in the Part 12 §25 registry of reserved namespaces, owned by the Part 13 Governance domain, subject to ESC ratification (Part 12 §24).

| Namespace | Owning Domain | Description |
|---|---|---|
| `governance` | Governance (Part 13) | Policy, decision, authority, approval, risk, compliance, audit, control, conformance, agent, and capability lifecycle events. |

Aggregates within `governance` (each a level-2 FQN segment):

| Aggregate | Governs |
|---|---|
| `policy` | Policy artifact lifecycle (created/submitted/approved/activated/suspended/deprecated/retired), policy-level exceptions/violations, overrides, conflict detection, and validation. |
| `decision` | Governance decision records and their approval/rejection. |
| `authority` | Delegation and revocation of governance authority. |
| `approval` | Generic approval workflows spanning policy/decision/authority/action. |
| `risk` | Risk register lifecycle (identify/escalate/accept). |
| `compliance` | External/internal compliance violation detection. |
| `audit` | Audit execution lifecycle. |
| `control` | Control evaluation and conformance verification/failure. |
| `conformance` | Conformance verification and failure events. |
| `agent` | Agent identity lifecycle (created/provisioned/activated/suspended/reactivated/revoked/decommissioned/archived) and agent behavior events (action, action denied, behavior anomaly, accountability gap). |
| `capability` | Capability lifecycle (created/issued/revoked/expired/suspended/modified) and capability usage events (used/usage violation/usage anomaly). |

A namespace may not be retired while any `governance.*` type is active; deprecation follows the Part 12 §25 minimum 6-month timeline.

---

## 6. Event Ownership

Per Part 12 §24, each event type has a **single owning domain**. For governance events the owning domain is **Governance (Part 13)**, with sub-ownership by the service that produces each aggregate:

| Aggregate | Producing/Owning Service | Accountable For |
|---|---|---|
| `policy.*` | Policy Service (Part 13.3) | Schema, policy lifecycle events, consumer docs. |
| `decision.*` | Decision Service (Part 13.4) | Decision artifact events. |
| `authority.*` | Authority Service (Part 13.4) | Delegation/revocation events. |
| `approval.*` | Approval Service (Part 13.4) | Approval workflow events. |
| `risk.*` | Risk Service (Part 13.6) | Risk lifecycle events. |
| `compliance.*` | Compliance Service (Part 13.6) | Compliance violation events. |
| `audit.*` | Audit Service (Part 13.11) | Audit lifecycle events. |
| `control.*`, `conformance.*` | Control/Conformance Service (Part 13.12) | Control & conformance events. |
| `agent.*` | Agent Governance Service (Part 13.7) | Agent lifecycle and behavior events. |
| `capability.*` | Capability Management Service (Part 13.7) | Capability lifecycle and usage events. |

Owning services are accountable for: schema validity at publish (Part 12 §28), notifying consumers of breaking changes, maintaining migration guides, and honoring deprecation timelines (≥3 months for breaking changes, Part 12 §24/§27). Emergency governance event types (e.g., a new critical violation class) may be introduced by the Security domain with post-hoc ESC ratification within 72 hours, per Part 12 §24.

---

## 7. Event Versioning

Governance events use the Part 12 §27 semantic `<major>.<minor>` strategy exactly:

- **Minor** — additive optional fields, new enum values. No ESC approval; owning service notifies consumers; consumers ignore unknown fields.
- **Major** — removed/renamed/retyped fields or changed semantics. Requires ESC approval + ≥3-month deprecation window for the prior major (Part 12 §27).

**Governance-specific constraint:** because governance events feed SOC 2 / ISO 27001 / regulatory assurance (Part 12 §36), a **major** version bump of any `governance.*` type additionally requires co-signature by the Security domain, and the schema Registry entry must reference the compliance frameworks affected. Producers MUST remain forward-compatible (never remove fields, never change field types, never change enum semantics without deprecation) per Part 12 §27.

`policy_id` / `decision_id` / etc. content versions are independent of event `event_version`; a policy content major change does **not** imply an event schema major bump.

---

## 8. Event Compatibility

Governance events conform to the Part 12 §27 backward- and forward-compatibility rules:

- **Backward compatible (minor):** new optional fields defaulted; new enum values tolerated or fail-closed with warning; field order irrelevant; access by name.
- **Forward compatible:** producers never remove/retype/reshape semantics without a major bump + deprecation; complex extensions use `metadata.extensions` keyed by version (Part 12 §27).

**Governance-specific strictness:** governance events sit in the compliance-critical path, so the bar is higher than the Part 12 baseline:
- No field may be removed from an `active` schema without a full major-bump deprecation cycle.
- `correlation_id` / `causation_id` / `partition_key` semantics are frozen at ratification and may not change within a major version.
- Consumers pin the major version they were built against (Part 12 §27); during a major transition both majors are active and the broker routes by `event_version`.

---

## 9. Event Governance

Governance of the `governance.*` taxonomy follows the Part 12 §24 Event Stewardship Council (ESC) model, with the Governance domain (Part 13) as a voting ESC member and owner of the `governance` namespace.

- **Addition:** owning Governance service proposes a type (FQN, initial version, payload schema, producer/consumer lists, priority, retention class, security class) → ESC review → ratification → activation.
- **Evolution:** per §7/§8; major bumps need ESC + Security co-signature.
- **Retirement:** `deprecated` (≥3 months, no new producers) → `tombstoned` (consumers migrated) → `retired` (removed from registry; historical events remain in WORM log). Part 12 §26.
- **Quarterly ESC audit:** orphaned/unused types, schema drift, consumer-index staleness (Part 12 §28).
- **Emergency:** Security domain may introduce a critical governance event type with post-hoc ratification within 72h (Part 12 §24).

The Event Registry (Part 12 §28) is the single source of truth; schemas are immutable once published; no producer/consumer keeps a private copy.

---

## 10. Event Security

Governance events are **security-sensitive by default** and adopt the Part 12 §20/§36 controls plus governance-specific tightening:

- **Signing:** every `governance.*` event is signed (Ed25519 over canonical envelope, signature excluded). This is **not** a deviation from Part 12 — Part 12 §20 mandates that *every* event is signed by its producer at emit time, so signing is universal, not baseline-plus. Governance events are always treated as *signed domains* at the broker admission gate, where unsigned or tampered events are rejected per Part 12 §26. The governance-specific point is that `governance.*` producers MUST be keyed and MUST never emit unsigned, since the audit trail (§12) depends on verifiable producer binding.
- **Classification:** `metadata.classification` ∈ {`internal`, `confidential`, `secret`}. Most governance events are `confidential`; events touching credentials/keys or sealed authority are `secret`. `secret`-tier events are not broadcast to unauthorized subscribers (Part 12 §20).
- **PII/secrets:** redacted in payload, echoed as pointers (`mem_…`) or hashes; never inline plaintext (Part 12 §2 principle 9).
- **Access control:** subscription to `governance.*` is ACL-gated; subscribing requires ESC/Governance authorization + mTLS to the governance/security domain (Part 12 §20).
- **Dead-letter:** as part of the `governance` namespace registration, a dedicated **`governance.dlq`** topic is registered alongside the existing Part 12 §19 DLQ set (which includes `security.dlq` as encrypted/read-restricted). `governance.dlq` follows the same encrypted, read-restricted treatment as `security.dlq`. Overflow escalates to `system.dlq.entry` (Part 12 §19).
- **Tamper detection:** chain-anchored via `security.audit.record` (Part 12 §13.8); any mismatch surfaces as `security.policy.violated` class `tamper_detected` (Part 12 §20).
- **Rate limiting:** per-producer token bucket; P0 governance events reserve capacity (Part 12 §20).

---

## 11. Event Replay

Governance events are replayable under the Part 12 replay primitives (§18, §19, §34) — replay is a first-class primitive, not an afterthought (Part 12 §2 principle 6).

- **Replay tagging:** replayed governance events carry `metadata.replay = { from_offset, replay_id }`; replays are explicit operations, never silent (Part 12 §20).
- **Causation preserved:** the `causation_id` DAG is retained across replays (Part 12 §20).
- **ACLs apply:** replay of `governance.*` (especially `secret`-classified authority/approval events) is governed by the same subscription ACLs as live consumption; replay from `governance.dlq` requires council/Governance approval, mirroring the Part 12 §19 rule that security/identity DLQ replays require council approval.
- **Cross-region:** governance replays respect the Part 12 §34 cross-region ordering/isolation guarantees.
- **Use cases:** reconstruct a policy's full lifecycle for an audit (pair `audit.started`/`audit.completed`), re-run conformance analysis, or rebuild a governance projection after a consumer migration.

---

## 12. Event Auditability

All `governance.*` events are **audit-grade by construction**, satisfying Part 13 "Immutable Audit Trail" and the Part 12 §36 compliance frameworks:

- **Immutable:** once published, a governance event cannot be modified or deleted during the retention window; corrections are new events with `causation_id` → original and a `correction_of` payload field (Part 12 §29).
- **Chain-anchored:** every N events the broker emits `security.audit.record` (Part 12 §13.8) with a Merkle root; governance events are included in the anchor chain, providing tamper-evident assurance.
- **Non-repudiable:** signed by the producing Governance service; `produced_by.actor_kind` + signature bind the action to an identity (Part 13 accountability model).
- **Reconstructable:** the full causal/audit history of any governance artifact is recoverable from the WORM log alone via `correlation_id` (artifact id) and `causation_id` chains (Part 12 §29/§30).
- **RTBF:** deletion of personal data in governance artifacts flows through `knowledge.memory.deleted` (RTBF tombstone) and `system.event.tombstoned`/`deleted` (Part 12 §33) — the audit trail that a deletion occurred is preserved.

---

## 13. Event Retention

Governance events adopt the Part 12 §33 three-tier model (Hot 30d / Warm 1yr / Cold 7yr baseline) with a **governance-specific extension** to the Part 12 §33 family table:

| Event Family | Hot | Warm | Cold | Rationale |
|---|---|---|---|---|
| `governance.*` | 30 days | **3 years** | **7 years** | Governance decisions, authority grants, approvals, and audits carry extended regulatory/assurance retention (consistent with `council.*` and `security.*` in Part 12 §33). |

- **Archival:** automatic and event-driven; compressed and copied tier-to-tier; content-addressable by SHA-256 (Part 12 §33).
- **Cold deletion:** never automatic; requires retention-policy exception (legal-hold release / RTBF) + ESC approval + a verifiable `system.event.deleted` record (Part 12 §33).
- **RTBF:** `knowledge.memory.deleted` with `reason: rtbf` shreds hot data and tombstones warm/cold indexes; the tombstone is never deleted (Part 12 §33).
- **Override:** a specific framework (e.g., PCI DSS, HIPAA) may require longer cold retention for a given `governance.*` subset; such overrides are recorded in the Event Registry entry's retention class.

---

## 14. Event Conformance

`governance.*` producers, consumers, and broker paths MUST conform to Part 12 §36, with governance additions:

**Part 12 baseline (all apply):**
1. Canonical envelope compliance — all mandatory fields present (§4).
2. Schema compliance — validates against the registered schema at the broker boundary.
3. Signature compliance — governance events are signed per the universal Part 12 §20 rule and are always treated as signed domains at the admission gate (see §10).
4. Classification compliance — every event declares `metadata.classification`.
5. Priority compliance — declares a `priority`; defaults to P2 if absent.
6. Partition-key compliance — declares a `partition_key` per the §2 aggregate table; synthetic `system` key if absent.
7. Correlation/causation compliance — every non-root event declares `causation_id`; every event declares `correlation_id`.

**Governance additions:**
8. **Artifact identity:** every governance event carries its artifact id (`policy_id`, `decision_id`, `authority_id`, `approval_id`, `risk_id`, `audit_id`, `control_id`, or `scope_id`) in the payload and uses it as `partition_key`.
9. **Sealed DLQ:** governance consumer failures route to `governance.dlq` (encrypted, read-restricted); overflow → `system.dlq.entry`.
10. **ACL enforcement:** subscription to any `governance.*` topic requires Governance/ESC authorization + mTLS.
11. **Compliance classification:** `secret`-classified governance events are never broadcast to unauthorized subscribers.

**Conformance testing (extends Part 12 §36):**
- Schema conformance — every `governance.*` schema parses and yields valid example events.
- Envelope conformance — all produced governance events include mandatory fields + artifact id.
- Producer conformance — each owning Governance service emits valid events through its normal lifecycle.
- Consumer conformance — governance consumers handle duplicates, schema-version transitions, and DLQ replay correctly.
- **Governance audit conformance** — quarterly ESC audit verifies orphaned types, schema drift, consumer-index staleness, and that all `governance.*` events are chain-anchored (§12). Annual certification validates WORM integrity, anchor verification, access control, retention, and RTBF (Part 12 §36).

---

## 15. Complete Event Catalog

Each `event_type` value below is the **canonical wire-level identifier** registered in the Part 12 §28 Event Registry under the `governance` namespace. These are the sole canonical names; no aliases or shorthand forms are used as event identities (see §4 for naming authority).

| # | `event_type` (canonical wire form) | Aggregate | Priority | Partition Key | Persistence | Schema |
|---|---|---|---|---|---|---|
| 1 | `governance.policy.created` | policy | P2 | policy_id | Yes (sealed) | v1 |
| 2 | `governance.policy.updated` | policy | P2 | policy_id | Yes (sealed) | v1 |
| 3 | `governance.policy.submitted` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 4 | `governance.policy.approved` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 5 | `governance.policy.activated` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 6 | `governance.policy.suspended` | policy | P0/P1 | policy_id | Yes (sealed) | v1 |
| 7 | `governance.policy.deprecated` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 8 | `governance.policy.retired` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 9 | `governance.policy.violation.detected` | policy | P0/P1 | policy_id | Yes (sealed) | v1 |
| 10 | `governance.policy.exception.requested` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 11 | `governance.policy.exception.approved` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 12 | `governance.policy.exception.rejected` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 13 | `governance.policy.exception.expiring` | policy | P1/P2 | policy_id | Yes (sealed) | v1 |
| 14 | `governance.policy.override.granted` | policy | P0 | policy_id | Yes (sealed) | v1 |
| 15 | `governance.policy.conflict.detected` | policy | P1 | policy_id | Yes (sealed) | v1 |
| 16 | `governance.policy.validation.failed` | policy | P1/P2 | policy_id | Yes (sealed) | v1 |
| 17 | `governance.decision.created` | decision | P1 | decision_id | Yes (sealed) | v1 |
| 18 | `governance.decision.approved` | decision | P1 | decision_id | Yes (sealed) | v1 |
| 19 | `governance.decision.rejected` | decision | P1 | decision_id | Yes (sealed) | v1 |
| 20 | `governance.authority.delegated` | authority | P1 | authority_id | Yes (sealed) | v1 |
| 21 | `governance.authority.revoked` | authority | P1 | authority_id | Yes (sealed) | v1 |
| 22 | `governance.approval.requested` | approval | P1 | approval_id | Yes (sealed) | v1 |
| 23 | `governance.approval.granted` | approval | P1 | approval_id | Yes (sealed) | v1 |
| 24 | `governance.approval.rejected` | approval | P1 | approval_id | Yes (sealed) | v1 |
| 25 | `governance.risk.identified` | risk | P1 | risk_id | Yes (sealed) | v1 |
| 26 | `governance.risk.escalated` | risk | P0 | risk_id | Yes (sealed) | v1 |
| 27 | `governance.risk.accepted` | risk | P1 | risk_id | Yes (sealed) | v1 |
| 28 | `governance.compliance.violation.detected` | compliance | P0/P1 | scope_id | Yes (sealed) | v1 |
| 29 | `governance.audit.started` | audit | P1 | audit_id | Yes (sealed) | v1 |
| 30 | `governance.audit.completed` | audit | P1 | audit_id | Yes (sealed) | v1 |
| 31 | `governance.control.evaluated` | control | P1 | control_id | Yes (sealed) | v1 |
| 32 | `governance.conformance.verified` | control | P1 | control_id | Yes (sealed) | v1 |
| 33 | `governance.conformance.failed` | control | P0/P1 | control_id | Yes (sealed) | v1 |
| 34 | `governance.agent.created` | agent | P1 | agent_id | Yes (sealed) | v1 |
| 35 | `governance.agent.provisioned` | agent | P1 | agent_id | Yes (sealed) | v1 |
| 36 | `governance.agent.activated` | agent | P1 | agent_id | Yes (sealed) | v1 |
| 37 | `governance.agent.suspended` | agent | P0/P1 | agent_id | Yes (sealed) | v1 |
| 38 | `governance.agent.revoked` | agent | P0 | agent_id | Yes (sealed) | v1 |
| 39 | `governance.agent.action` | agent | P2 | agent_id | Yes (sealed) | v1 |
| 40 | `governance.agent.action.denied` | agent | P1 | agent_id | Yes (sealed) | v1 |
| 41 | `governance.agent.behavior.anomaly` | agent | P1 | agent_id | Yes (sealed) | v1 |
| 42 | `governance.agent.accountability.gap` | agent | P0 | agent_id | Yes (sealed) | v1 |
| 43 | `governance.capability.created` | capability | P2 | capability_id | Yes (sealed) | v1 |
| 44 | `governance.capability.issued` | capability | P1 | capability_id | Yes (sealed) | v1 |
| 45 | `governance.capability.revoked` | capability | P1 | capability_id | Yes (sealed) | v1 |
| 46 | `governance.capability.expired` | capability | P2 | capability_id | Yes (sealed) | v1 |
| 47 | `governance.capability.suspended` | capability | P0/P1 | capability_id | Yes (sealed) | v1 |
| 48 | `governance.capability.modified` | capability | P1 | capability_id | Yes (sealed) | v1 |
| 49 | `governance.capability.used` | capability | P2 | capability_id | Yes (sealed) | v1 |
| 50 | `governance.capability.usage.violation` | capability | P1 | capability_id | Yes (sealed) | v1 |
| 51 | `governance.capability.usage.anomaly` | capability | P1 | capability_id | Yes (sealed) | v1 |

**Total governance events:** 51 across 10 aggregates under the `governance` namespace (the original 28 plus 5 policy events, 9 agent events, and 9 capability events added to align with Part 13.7 and `schemas.md`).

---

## 16. Cross-References

- **Part 12 `events.md`** — authoritative envelope (§4), principles (§2), delivery/ordering (§18, §29), idempotency/correlation/causation (§30), lifecycle (§26), versioning (§27), governance model (§24), naming/namespace (§25), registry (§28), security/replay (§20), retention (§33), conformance (§36), CloudEvents (§32), tracing (§31), DLQ (§19). This document defers all those constructs to Part 12 and adds only the `governance.*` taxonomy + governance-specific tightening.
- **Part 12 §13.1 `security.policy.violated`** — the runtime enforcement fact that `governance.policy.violation.detected` is causation-linked to.
- **Part 12 §7.7 `council.decision.published`** — the council mechanism cited by `governance.decision.*` when a decision is council-issued.
- **Part 12 §13.8 `security.audit.record`** — chain-anchor including all governance events (§12).
- **Part 12 §14.4 `monitoring.alert.raised`** — driven by governance events (e.g., `risk.escalated`, `policy.suspended` emergency, `conformance.failed` critical).
- **Part 12 §19/§33 `system.dlq.entry`, `knowledge.memory.deleted`, `system.event.deleted`** — deletion/RTBF/tombstone paths used by governance artifacts. The `governance.dlq` topic is registered as part of the `governance` namespace (§10); it mirrors `security.dlq` and is not a pre-existing Part 12 §19 topic.
- **Part 13.2 Governance Architecture** — governance principles, authority/responsibility/accountability models.
- **Part 13.3 Policy Architecture** — policy lifecycle (Draft→…→Retired) mirrored by `policy.*` events; `policies.md` §"Policy Events" canonical short names mapped to the `governance.policy.*` FQNs in §2. Override vs exception distinction (`schemas.md` `PolicyOverride` vs `PolicyException`) realized by `governance.policy.override.granted` (overrides take precedence) vs `governance.policy.exception.*`. Policy conflict and validation failures covered by `governance.policy.conflict.detected` / `governance.policy.validation.failed`. Exception *terminal* expiry/renewal (`ExceptionExpired`/`ExceptionRenewed` in components.md G-11) is a component-internal lifecycle event; this taxonomy records the governable `governance.policy.exception.expiring` warning and the approval/renewal that follows, and does not duplicate the component's internal terminal transitions.
- **Part 13.4 Decision Authority and Delegation** — decision rights and delegated authority mirrored by `decision.*` / `authority.*` / `approval.*` events.
- **Part 13.5 Councils and Committees** — councils as a producer path for `decision.*` and `policy.approved`.
- **Part 13.6 Risk and Compliance Governance** — risk and compliance lifecycles mirrored by `risk.*` / `compliance.*` events.
- **Part 13.7 Agent and Capability Governance** — agent identity lifecycle and capability governance mirrored by `agent.*` and `capability.*` events; `agent.*` events cover registration through archival and behavior monitoring; `capability.*` events cover definition through revocation and usage tracking.
- **Part 13.11 Auditability and Accountability** — audit lifecycle and immutable trail realized by `audit.*` events and the §12 auditability model.
- **Part 13.12 Governance Invariants and Conformance** — control/conformance evaluation realized by `control.*` / `conformance.*` events; invariants enforced via the §14 conformance rules.

---

*Document complete. 51 governance events across 10 aggregates under the `governance` namespace, fully conformant to and extending Part 12 `events.md` without duplicating its event architecture. Ready for ESC ratification of the `governance` namespace and Event Registry pinning.*
