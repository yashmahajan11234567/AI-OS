# Part 13: Logical Governance Component Specification

> **Scope:** Logical architecture only. This document defines *what* governance components exist, *why* they exist, and *how* they relate. Physical deployment is out of scope.
>
> **Style:** Architecture 3 contract — section-anchored, traceable, diagram-first.

## 1. Component Index

| # | Component | Tier | Primary Domain |
|---|-----------|------|-----------------|
| G-00 | Governance Manager | Tier 0: Foundation | Orchestration, lifecycle, dispatches |
| G-01 | Policy Manager | Tier 0: Foundation | Policy CRUD, lifecycle, distribution |
| G-02 | Policy Evaluation Engine | Tier 1: Execution | Runtime policy evaluation, decision records |
| G-03 | Governance Registry | Tier 0: Foundation | Canonical state of all governance artifacts |
| G-04 | Governance Council | Tier 1: Execution | Governance body interface, charter, committees |
| G-05 | Decision Authority Manager | Tier 1: Execution | Authority grants, thresholds, constraints |
| G-06 | Delegation Authority Manager | Tier 1: Execution | Delegation chains, revocation, audit trail |
| G-07 | Risk Manager | Tier 1: Execution | Risk life cycle, tolerance, treatment |
| G-08 | Compliance Manager | Tier 1: Execution | Obligation registration, baseline, reporting |
| G-09 | Audit Manager | Tier 1: Execution | Audit records, evidence, findings |
| G-10 | Accountability Manager | Tier 1: Execution | Principal, actor, subject, log linking |
| G-11 | Exception Manager | Tier 1: Execution | Exception cases, expiry, escalation |
| G-12 | Approval Manager | Tier 1: Execution | Request, review, decision, routing |
| G-13 | Control Manager | Tier 2: Oversight | Control design, testing, effectiveness |
| G-14 | Governance Event Manager | Tier 1: Execution | Event schema, ingestion, classification |
| G-15 | Conformance Manager | Tier 2: Oversight | Snapshot evaluation, pass/fail, continuous conformance |

---

## 2. Component Relationship Diagram

```text
                    ┌────────────────────────────────────────────────────────┐
                    │                  GOVERNANCE MANAGER (G-00)              │
                    │            orchestrates, dispatches, coordinates        │
                    └────────────┬───────────────┬─────────────┬────────────┘
                                 │               │             │
          ┌──────────────────────┘               │             └───────────────────┐
          │                                      │                                │
┌─────────────────────────────┐  ┌─────────────────────────────┐  ┌──────────────────────┐
│    Policy Manager (G-01)    │  │   Governance Registry (G-03) │  │ Governance Council   │
│  CRUD, lifecycle, version   │  │ Canonical state, query,      │  │     (G-04)           │
│  policy source of record    │  │ lookup, snapshot             │  │ Charter, committees, │
└──────────────┬──────────────┘  └──────────────┬──────────────┘  │ audits/view          │
               │                               │                └──────────┬─────────┘
               │     ┌─────────────────────────┘                                │
               ▼     ▼                                                           │
┌─────────────────────────────────────────┐    ┌─────────────────────────────────┐
│         Decision Authority Manager (G-05) ◄──│         Authority Layer          │
│     Authority grants, thresholds        │    │   (G-05 ↔ G-06 ↔ G-14)         │
└──────────────────────┬──────────────────┘    └─────────────────────────────────┘
                       │
         ┌─────────────┼──────────────┐
         ▼             ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐
│  Policy       │ │  Delegation  │ │  Risk Manager (G-07) │
│  Eval Engine  │ │  Authority   │ │  Risk register,      │
│  (G-02)       │ │  Manager      │ │  treatment, tolerance│
│               │ │  (G-06)      │ └──────────┬───────────┘
└──────────────┘ └──────────────┘            │
                                               ▼
                              ┌───────────────────────────┐
                              │    Control Manager (G-13)  │
                              │   Control set, testing,    │
                              │   effectiveness evidence   │
                              └──────────────┬────────────┘
                                             │
          ┌──────────────────────────────────┼──────────────────────────────────┐
          ▼                                  ▼                                  ▼
┌──────────────────┐             ┌──────────────────┐            ┌──────────────────┐
│  Approval Manager│             │   Exception      │            │  Compliance      │
│  (G-12)          │             │   Manager (G-11) │            │  Manager (G-08)  │
│  Review, record   │             │  Exception cases,│            │  Obligations,    │
│  routing          │             │  override logic  │            │  baseline, regs  │
└────────┬─────────┘             └──────────────────┘            └────────┬─────────┘
         │                                                                │
         └────────────────────────┬───────────────────────────────────────┘
                                  ▼
                     ┌─────────────────────────┐
                     │    Accountability       │
                     │    Manager (G-10)        │
                     │  Principal-actor-subject │
                     │  link, causal chain     │
                     └────────────┬────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         ▼                        ▼                        ▼
┌──────────────┐        ┌──────────────┐        ┌──────────────┐
│  Audit Mgr   │        │  Conformance │        │ Governance   │
│  (G-09)      │        │  Manager     │        │ Event Manager│
│  Evidence,   │        │  (G-15)      │        │  (G-14)      │
│  findings    │        │  Snapshot,    │        │  Events,      │
│              │        │  pass/fail    │        │  classification│
└──────────────┘        └──────────────┘        └──────────────┘
```

### 2.1 What the Diagram Means

- The **left-to-right spine** runs Policy → Evaluation → Authority → Risk/Control → Exception/Approval.
- **Governance Manager (G-00)** dispatches work and owns orchestration; it is not a gateway in this diagram.
- **Governance Council (G-04)** feeds decision criteria into authority grants and views audit output for oversight.
- **Accountability Manager (G-10)** is the convergence point for audit/conformance/event data — every governance action must have an accountable principal at creation time.

---

## 3. Governance Component Hierarchy

```text
Tier 0 — Foundation (no governance substrate dependency)
├── G-00  Governance Manager
├── G-01  Policy Manager
└── G-03  Governance Registry

Tier 1 — Execution (depends on Tier 0)
├── G-02  Policy Evaluation Engine
├── G-04  Governance Council
├── G-05  Decision Authority Manager
├── G-06  Delegation Authority Manager
├── G-07  Risk Manager
├── G-08  Compliance Manager
├── G-09  Audit Manager
├── G-10  Accountability Manager
├── G-11  Exception Manager
├── G-12  Approval Manager
├── G-14  Governance Event Manager

Tier 2 — Oversight (depends on Tier 1)
├── G-13  Control Manager
└── G-15  Conformance Manager

Tier 3 — Outcomes (cross-cutting)
└── (Outcomes layer — governance results reported to operating context)
```

### 3.1 Tier Rationale

| Tier | Rationale |
|------|-----------|
| Tier 0 | Self-sufficient: must start before any other governance flow. Cannot be self-governed in bootstrap. |
| Tier 1 | Operates on substrate provided by Tier 0. Must reference policy (G-01) and state (G-03). |
| Tier 2 | Evaluates Tier 1 outputs. Requires stable execution evidence before assessing control effectiveness or conformance. |
| Tier 3 | Results — conformance scorecards, audit packages, compliance reports. |

---

## 4. Component Lifecycle Diagram

```text
┌─────────────────────────────────────  lifecycle  ─────────────────────────────────────┐
│                                                                                         │
│   DEFINE    ─►  INSTANTIATE    ─►  CONFIGURE    ─►  ACTIVATE    ─►  VALIDATE         │
│   (contract)                 (instance)              (policy, ACLs)  (invariants)     │
│                                                                                         │
│   ◄─────────────────────────────────────────────────────────────────────────────────── │
│                                                                                         │
│   RUNNING state:                                                                        │
│   accept (Inputs) → transition on (Events) → emit (Outputs)                            │
│   on failure → FAIL-STOP → notify recovery boundary                                    │
│                                                                                         │
│   TERMINATE:                                                                           │
│   drain, finalize, close contract                                                      │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

States per component instance:
  UNSET → CONFIGURED → ACTIVE → DRAINING → CLOSED
                 ↘       ↗
                    FAILED (terminal, requires recovery)
```

---

## 5. Component Specifications

### 5.1 G-00 — Governance Manager

#### Purpose
Central orchestrator for all governance flows. Receives triggers from operating context, coordinates cross-component calls, maintains control loop, and dispatches governance sessions.

#### Responsibilities
- Accept governance triggers from any operating context layer (workflow, data, resource, agent, security).
- Determine which governance flows apply based on context tag and policy.
- Coordinate sequential and parallel governance stage execution.
- Maintain session-level governance context (correlation IDs, principal chain, decision trail).
- Handle governance session lifecycle: open → execute → close → audit.
- Enforce governance invariants: every governance action must originate from a traceable trigger.
- Aggregate governance outcomes into a single governance report for the parent context.

#### Non-Responsibilities
- Does not evaluate policy conditions itself — delegates to G-02.
- Does not store policy or governance state — delegates to G-01, G-03.
- Does not make authority decisions — delegates to G-05.
- Does not generate or own policy language or artifacts.

#### Inputs
- Governance trigger event (from operating context)
- Correlation context (request, session, flow)
- Active policy snapshot reference (from G-03)
- Principal identity context (from G-10)

#### Outputs
- Governance decision record (composite)
- Governance stage transition events (to G-14)
- Error / escalated event (when governance flow fails)
- Governance outcome package (to caller)

#### Interfaces
- **Inbound:** `GovernanceTrigger` event from any operating layer
- **Outbound:** `requestEvaluation(policySet, context) → G-02`; `resolveAuthority(req) → G-05`; `emit(event) → G-14` (events routed to G-09 for audit persistence via G-14)
- **Query:** `queryGovernanceState(sessionId) → decision record`

#### Dependencies
- G-01, G-02, G-03, G-05, G-09, G-10, G-14 (logical)
- Must bootstrap after Tier 0 components are active

#### Authority
- Owns governance session lifecycle.
- Cannot bypass evaluation results — all positive/negative decisions flow through G-02.
- Cannot override Delegation Authority grant — that ownership belongs to G-06.
- Does not hold policy editing authority.

#### Ownership
- Governance Operations owner (operational).
- Product owner for governance flow UX/API surface.
- Design authority for session protocol and correlation model.

#### Lifecycle
Starts after G-01, G-03 are available. Destroys on platform shutdown. Stateless across sessions; state held in governance context envelope.

#### State Model
```
PRISTINE → CONFIGURE → ACTIVE → EXECUTING → CLOSING → CLOSED
                        ↘ TIER_FAILURE → RECOVERING ↙
```

#### Security Boundary
Governance Manager does **not** read the contents of operating context payloads beyond the correlation envelope and principal chain. Payloads are opaque. Trust boundary: every orchestrator input must be attributable.

#### Failure Boundary
Any single-stage failure aborts the current governance session. Policy decisions made before the failure remain valid. No partial governance outcomes are issued to the caller — result is either complete-go or escalation.

#### Events
- `SessionOpened`, `StageTransitioned`, `SessionCompleted`, `SessionFailed`, `SessionEscalated`, `PolicyEvaluated`, `AuthorityResolved`

#### Observability
Duration per governance stage. Evaluation latency hot-path. Authority resolution count. Failure breakdown by stage.

#### Performance Considerations
Gate: longest eval stage dominates session latency. Strategy: pipeline independent stages where order permits. Cache policy snapshot references during session.

#### Scalability
Session parallelism bounded by operating context load. Governance sessions are immutable once closed; results can be cached in G-03 for read-only replay.

#### Recovery
Governance sessions are replay-capable from recorded events. Replay regenerates the decision record identical to the original (deterministic given identical inputs).

#### Governance Constraints
Every governance session MUST have a trigger principal. Every session MUST close (either Completed, Failed, or Escalated). No silent governance — sessions without outcomes are prohibited.

#### Cross-Part Dependencies
- Part 1: identity model for principal chain (G-10)
- Part 4-8: operating context trigger sources (workflow, data, resource, agent, security)
- Part 12: audit model alignment

---

### 5.2 G-01 — Policy Manager

#### Purpose
Executive authority for policy artifacts: create, version, approve, publish, deprecate, and retire all written-down governance policies, standards, procedures, controls, and definitions.

#### Responsibilities
- Policy text CRUD with approval workflow integration.
- Policy lifecycle: Draft → Review → Approved → Published → Deprecated → Retired.
- Version management: immutable versions; comparison; rollback approval.
- Policy taxonomy management (categories, domains, scopes).
- Policy packaging: bundle policies into named packages for distribution to G-02 and G-08.
- Immutability of published versions — Editing a published version requires FORK, not mutation.
- Policy chain of custody — trace every policy to author, reviewer, approver (via G-10).

#### Non-Responsibilities
- Does not evaluate policy conditions at runtime — that is G-02.
- Does not hold governance execution state.
- Does not govern what content appears in policy text (that is the council's role via G-04).
- Does not distribute policies — only prepares packages; G-03 holds canonical copies.

#### Inputs
- Policy creation/edit request (with draft content, author principal)
- Approval decision (from G-12)
- Deprecation or retirement intent
- Search/query requests

#### Outputs
- Approved policy package (immutable artifact)
- Policy snapshot (reference for G-03)
- Approval request (to G-12)
- Policy events (to G-14)

#### Interfaces
- **Inbound:** Policy lifecycle commands
- **Outbound:** `publishPackage(version, scope, content) → G-03`; `queueApproval(policyId, diff) → G-12`; `emit(event) → G-14`
- **Query:** `resolvePolicy(policyId, version) → package`; `listPolicies(scope) → []`

#### Dependencies
- G-03 (publish output)
- G-04 (charter-level policy decisions)
- G-10 (principal chain for traceability)
- G-12 (approval flow)

#### Authority
- Owns policy text and policy package. Edits only via versioned fork.
- Cannot approve its own packages — authority to approve belongs to G-12.

#### Ownership
- Governance Product team (product-owned content).
- Council / Committee (charter ownership).
- Architect (taxonomy and coupling constraints).

#### Lifecycle
Always active. Cannot be deactivated while governance is operational. Bootstrap: initial policy package loaded on G-03 init.

#### State Model
```
Policy state machine:
DRAFT → PENDING_APPROVAL → APPROVED → PUBLISHED → DEPRECATED → RETIRED
              ↘ REJECTED (back to DRAFT)
```

#### Security Boundary
Policy content is world-readable within operating trust domain once published. Drafts are author-readable + approval-role-readable only. No external egress without explicit export approval.

#### Failure Boundary
Loss of draft content is recoverable from audit records in G-09. Loss of published policy is a governance halt condition — escalate to G-12 immediately. Recovery must replay from the latest approved snapshot.

#### Events
`PolicyCreated`, `PolicyUpdated`, `PolicySubmitted`, `PolicyApproved`, `PolicyRejected`, `PolicyPublished`, `PolicyDeprecated`, `PolicyRetired`, `PackagePublished`

#### Observability
Policy count by state. Approval latency. Forks per policy. Publish frequency by domain.

#### Performance Considerations
Policy read is hot path for G-02. Cache policy snapshot by version in-memory during evaluation sessions.

#### Scalability
Policy set size is bounded (governance document corpus is orders of magnitude smaller than operational data). Horizontal read scaling via G-03.

#### Recovery
Published policies recovered from G-03 snapshot. Drafts recovered via G-09 replay.

#### Governance Constraints
No published policy may be edited in place — mutation requires version bump. All policy changes require audited approval. Policy changes to Tier 1/2 components require staged rollout.

#### Cross-Part Dependencies
- Part 1: principal identity (author, reviewer, approver roles)
- Part 12: audit record linkage

---

### 5.3 G-02 — Policy Evaluation Engine

#### Purpose
Evaluate policy conditions at runtime, produce policy decisions, and record every evaluation as a retrievable event with the exact policy snapshot used.

#### Responsibilities
- Receive policy evaluation requests from G-00.
- Resolve the correct policy package and applicable conditions via G-03.
- Evaluate all applicable conditions: permit/deny/pending/override.
- Produce an evaluationDecision object that includes:
    - Outcome (permit | deny | pending | override)
    - Applied policy IDs, rule IDs, snapshot reference
    - Applied facts (derived from context, immutable)
    - Exception reference (when applicable, from G-11)
    - Decision timestamp and correlation ID
- Emit evaluation events to G-14.
- Support staged evaluation: early-stop on deny, collect-tier on permit.

#### Non-Responsibilities
- Does not create or modify policy — only evaluates approved published policy from G-03.
- Does not execute enforcement actions — only produces a decision; enforcement is caller's responsibility.
- Does not manage delegation — reads authority but does not grant.
- Does not track operational state outside evaluation scope.

#### Inputs
- Evaluation request: `{sessionId, context, policyScope}` from G-00
- Policy snapshot reference (via G-03 lookup)
- Delegation authority state (read-only from G-06)
- Exception state (read-only from G-11)
- Principal chain (via G-10)

#### Outputs
- `evaluationDecision` object
- Evaluation event (to G-14)
- Evaluation fact record (for accountability)

#### Interfaces
- **Inbound:** `evaluate(request) → decision` (from G-00)
- **Query:** `replayEvaluation(evaluationId) → decision + applied facts`
- **Outbound:** `getArtifact(id, version) → G-03`; `isExceptionActive(exceptionId) → G-11`; `getActiveChainForActor(actorId) → G-06`; `emit(event) → G-14`

#### Dependencies
- G-00 (caller)
- G-03 (policy state)
- G-06 (authority citations)
- G-10 (principal binding)
- G-11 (exception state)

#### Authority
- Evaluates but does not decide — decision authority belongs to policy author + approver via G-12.
- Cannot override Deny without an authority-granted exception from G-05.
- Cannot bypass accountability: every evaluation must bind an actor principal.

#### Ownership
- Platform Engineering (engine correctness, testability, determinism).
- Governance Product (evaluation semantics — what "permit" means).

#### Lifecycle
Starts after G-01 and G-03 are active. Evaluator instances are stateless with respect to policy — reloaded on package updates.

#### State Model
```
IDLE → LOADING_SNAPSHOT → EVALUATING → EMITTING_DECISION → COMPLETE
                                             ↘ FAILED → RETRYING ↙
```

#### Security Boundary
Evaluator processes only governed inputs from G-00. No direct network egress. Evaluation context is ephemeral — never persisted inside G-02 boundary.

#### Failure Boundary
Evaluation failure aborts the governance session (notified to G-00). Evaluation failure does NOT produce a Permit — the safety default is Deny-Unknown treated as Deny for enforcement callers.

#### Events (Component-Internal)
`EvaluationStarted`, `EvaluationCompleted`, `EvaluationDenied`, `EvaluationPermitted`, `EvaluationExceptionApplied`, `EvaluationFailed` — these events are internal to G-02 and are not part of the canonical governance event catalog (governance-events.md).

#### Observability
Evaluation count by policy scope. Evaluation latency p50/p99. Deny rate. Exception invocation rate. Snapshot age.

#### Performance Considerations
Policy evaluation is the hot path for governance. Favor in-memory compiled conditions. Avoid per-request API calls to G-03 — pre-load snapshot per session. Cache permissions aggressively for read-heavy workloads.

#### Scalability
Stateless instances; scale horizontally. Snapshot files loaded once per instance restart; evaluate without repeated G-03 calls.

#### Recovery
Stateless — no internal state to recover. Recovery = reload snapshot from G-03 and retry evaluation.

#### Governance Constraints
Every evaluation must be auditable. Evaluations against deprecated policy are prohibited — enforce snapshot freshness check. All override decisions require exception reference from G-11 and authority citation from G-05.

#### Cross-Part Dependencies
- Part 3: data model for evaluation context shaping
- Part 7: execution context for enforcement integration
- Part 10: accountability and identity linkage (G-10)

---

### 5.4 G-03 — Governance Registry

#### Purpose
Single source of truth for all governance artifacts: policy packages, snapshots, contracts, governance entity registrations, conformance baselines, control definitions, and authoritative status records.

#### Responsibilities
- Store immutable governance artifacts with structured metadata.
- Provide lookup by ID, version, scope, status, effective date.
- Maintain consistency: only one "current" snapshot per policy.
- Support snapshot compilation for G-02 consumption.
- Reject mutations to published artifacts (read-only after publish).
- Interface with conformance baselines (G-15 requires baseline access).

#### Non-Responsibilities
- Does not create or evaluate policy.
- Does not govern what goes into the registry.
- Does not run workflows — serves read/write API only.

#### Inputs
- Policy packages (from G-01)
- Governance entity definitions (from G-04, G-05, G-06, G-13)
- Control definitions and test results (from G-13)
- Conformance baseline records (from G-15)
- Query requests (any consumer)

#### Outputs
- Artifact retrieval by ID/version/scope
- Snapshot compilation for evaluator consumption
- Status-consistent view of all artifacts

#### Interfaces
- **Inbound:** `registerArtifact(artifact, metadata)`; `updateStatus(id, newStatus)`
- **Outbound:** `getArtifact(id, version)`; `getSnapshot(scope, effectiveAsOf)`; `listArtifacts(query)`
- **Query:** `resolvePackage(policyId) → compiled snapshot`

#### Dependencies
- All Tier 0 and Tier 1 components write to G-03.
- Must be available before G-02 initializes.

#### Authority
- Authority over artifact validity — only G-03 decides if an artifact is "current."
- Cannot unilaterally retire an artifact — retirement intent must come from owning component (G-01 for policy, G-04 for council charter).

#### Ownership
- Platform Engineering (infrastructure layer).
- Governance Operations (business rules for status transitions).

#### Lifecycle
Always active. Must not be single-point-of-failure for read operations — read replicas acceptable. Write intensity is low (policy publish cadence is weeks/months).

#### State Model
```
ARTIFACT states:
DRAFT → REGISTERED → PUBLISHED → DEPRECATED → RETIRED
```

#### Security Boundary
Published artifacts are generally readable. Draft artifacts are restricted by creator role. Registry itself is not a policy enforcement point — enforcement is at G-02 evaluation time.

#### Failure Boundary
Read failure = governance halt. Registry write failure = governance session queued. Must distinguish read availability from write availability.

#### Events
`ArtifactRegistered`, `ArtifactStatusChanged`, `ArtifactDeprecated`, `SnapshotCompiled`, `QuotaThreshold`, `ReadAvailabilityChanged`

#### Observability
Registry size by artifact type. Read/write latency. Cache hit rate. Snapshot build duration.

#### Performance Considerations
Read-heavy, write-light. Cache aggressively. Pre-compile evaluator snapshots on package publish to avoid G-02 cold start.

#### Scalability
Sublinear growth (policy artifact volume). Split by scope domain if needed.

#### Recovery
Artifact rebuild from owner-component audit records (G-09). Draft recovery from G-09 replay. Publish recovery via G-01 re-submit flow.

#### Governance Constraints
Registry is terminal for artifact truth. No shadow registries — all legitimate artifacts must flow through G-03.

#### Cross-Part Dependencies
- Part 1: identity metadata on artifacts (author, approver)
- Part 12: registry state backed by audit trail

---

### 5.5 G-04 — Governance Council

#### Purpose
Formal interface to the governance body — define charter, register committees, appoint members, define scope and authority, and publish governance outcomes from council proceedings.

#### Responsibilities
- Maintain governance body charter (in G-03 as artifact).
- Register standing committees and ad-hoc committees with scope and authority limits.
- Record appointment and revocation of council and committee members.
- Publish council decisions as policy proposals (routed to G-01) or as direct approvals (routed to G-12).
- Maintain quorum and voting rules per committee.
- Produce governance minutes and decision records (to G-09).

#### Non-Responsibilities
- Does not execute policy evaluation — delegates to G-02.
- Does not approve day-to-day operational exceptions — delegates to G-11 and appropriate committee.
- Does not enforce decisions — produces decisions; enforcement is caller responsibility.

#### Inputs
- Council decision (policies, exceptions, charters)
- Committee formation / dissolution requests
- Appointment revocation requests
- Voting outcome

#### Outputs
- Approved/Rejected decision records
- Policy proposals (to G-01)
- Direct approvals (to G-12)
- Charter changes (as artifact to G-03)
- Governance minutes (to G-09)

#### Interfaces
- **Inbound:** Council decision events; committee lifecycle events.
- **Outbound:** `registerCharter(charter) → G-03`; `proposePolicy(proposal) → G-01`; `approveDecision(decision) → G-12`; `emit(event) → G-14`; `recordMinutes(minutes) → G-09`
- **Query:** `getCharter(version)`; `getCommittee(name)`; `listMembers(committee)`

#### Dependencies
- G-01, G-03, G-09, G-10, G-12, G-14

#### Authority
- Owns charter and committee definitions.
- Owns appointment/removal of council members (subject to allocation — see Part 5).
- Cannot unilaterally override published policy — amendment requires publication flow via G-01.

#### Ownership
- Legal/Compliance function (charter authority).
- Governance Product (committee definitions).
- Chairperson / Secretary (meeting outcome authority).

#### Lifecycle
Active whenever governance is operational. Committees may be dissolved; council persists. Council cannot be dissolved during active exception windows without replacement body authority.

#### State Model
```
Council:
ACTIVE → SUSPENDED (requires replacement authority) → REACTIVATED

Committee:
PROPOSED → APPROVED → ACTIVE → SUSPENDED → DISSOLVED
```

#### Security Boundary
Council minutes and internal deliberations are restricted to members and designated observers. Published outcomes are world-readable. Appointment records sensitive (PII-like for council members).

#### Failure Boundary
Council dissolution without succession = governance halt. Cannot enter suspended state without replacement authority registered in G-03. Failure to produce minutes is a compliance violation (G-08) and audit finding (G-09).

#### Events
`CouncilSitting`, `DecisionPublished`, `CommitteeFormed`, `CommitteeDissolved`, `MemberAppointed`, `MemberRevoked`, `QuorumNotMet`

#### Observability
Meeting frequency by committee. Decision latency (proposal → approval). Amendment rate. Committee proliferation count.

#### Performance Considerations
Governance cadence is weekly/monthly/quarterly, not sub-second. Low throughput, high importance. Prioritize audit correctness over speed.

#### Scalability
Number of committees bounded by human governance capacity. No horizontal scaling concern.

#### Recovery
Council decisions are recorded in G-09 and G-03. Recovery = re-issue decisions from minutes. Must explicitly mark re-issued decisions as "re-issued" with original decision reference.

#### Governance Constraints
Quorum rules are enforced by import — not self-declared. Charter changes require the same approval tier as the charter type itself (quorum + approval role).

#### Cross-Part Dependencies
- Part 5: principal allocation model for member appointment
- Part 6: committee scope definition
- Part 12: minutes as audit artifacts

---

### 5.6 G-05 — Decision Authority Manager

#### Purpose
Define, maintain, and resolve decision authority grants: who can approve what, under what conditions, within which scope, with which constraints, and up to what threshold.

#### Responsibilities
- Maintain decision authority space: actors (principals), scope, authority type, threshold, constraint set.
- Resolve authority requests from G-00 against current grants.
- Emit authority resolution event (parsed into **EvaluationSubject** by caller).
- Track threshold utilization (how much of an authority grant has been consumed).
- Enforce expiration/revocation of authority grants.
- Produce authority resolution audit record (routed to G-09 via caller).

#### Non-Responsibilities
- Does not delegate authority — delegates via G-06.
- Does not grant authority to council members — that is done via G-04 charter or appointments recorded in G-05.
- Does not override delegation chains — reads G-06 for chain validation.
- Does not make policy decisions — produces authority resolution only.

#### Inputs
- Authority resolution request: `actorId, action, target, context`
- Delegation chain validation request (from G-06, read-only).
- Threshold consumption events.

#### Outputs
- `authorityDecision`: GRANTED | DENIED | BOUNDARY | UNAVAILABLE
- Resolution fact set: applied grant ID, threshold state, effective period.
- Authority events (to G-14).

#### Interfaces
- **Inbound:** `resolveAuthority(request) → decision` (from G-00)
- **Outbound:** `checkDelegationChain(delegationId) → validation` (to G-06, read); `emit(event) → G-14`
- **Query:** `getAuthorityForActor(actorId) → grants`

#### Dependencies
- G-00 (caller)
- G-03 (authority artifact storage)
- G-06 (delegation chains — read-only)
- G-10 (principal identity)
- G-14 (events)

#### Authority
Does not grant authority — records authority grants (grants come from G-04 appointments and self-declared roles defined in G-05 with G-03 artifact).
Self-grants are prohibited. All grants require a governance artifact backing them.

#### Ownership
- Governance Product (authority model definition).
- Council / Legal (senior authority grants).
- Platform (implementation of resolution algorithm).

#### Lifecycle
Active after policy baseline is established. Pre-bootstrap: G-05 must have a minimum viable authority set to govern bootstrap governance actions.

#### State Model
```
GRANT: PENDING_APPROVAL → ACTIVE → SUSPENDED → REVOKED → ARCHIVED
                   ↘ REJECTED (terminal)
```

#### Security Boundary
Authority resolution is sensitive — reveals organizational decision structure. Resolution results are scoped to the requesting session only. No broad enumeration of grants to unauthorized actors.

#### Failure Boundary
Authority resolution failure → governance session escalates via G-00. Default deny on inability to resolve (failure-transparent: operator gets escalation, not silent deny).

#### Events
`AuthorityGranted`, `AuthorityResolved`, `AuthorityDenied`, `AuthorityBoundaryHit`, `GrantSuspended`, `GrantRevoked`, `ThresholdConsumed`

#### Observability
Authority resolution latency. Grant count by actor. Authority denial reason breakdown. Threshold consumption rate by grant type.

#### Performance Considerations
Authority resolution is on the hot path for every governance-but-not-required and approval flow. Cache resolution by actor-scope-action tuple. Invalidate cache on grant lifecycle change.

#### Scalability
Scales with principal count. Principal set is organizational — typically low thousands. Linear scaling appropriate.

#### Recovery
Authority state recovered from G-03 (artifacts) and G-09 (audit trail). Active sessions must re-resolve authority on recovery.

#### Governance Constraints
Self-authority grant is a prohibited pattern. Every active grant must trace to a governance artifact in G-03. Grants have maximum lifetime — perpetual grants require explicit renewal.

#### Cross-Part Dependencies
- Part 1: principal identity model
- Part 5: principal allocation model for appointment records
- Part 12: grant audit trail

---

### 5.7 G-06 — Delegation Authority Manager

#### Purpose
Represent, maintain, validate, and revoke delegation chains — sequences of authority grants that allow an actor to act on behalf of a principal at a defined scope and level with documented constraints.

#### Responsibilities
- Record delegation grants: `delegator → delegatee, scope, level, period, constraints`.
- Maintain revocation chain — revoke one, revoke all downstream.
- Validate complete delegation chain on each resolution request.
- Emit delegation validation confirmation or failure.
- Provide delegation chain enumeration for auditing (G-09) and accountability (G-10).
- Enforce that every delegation grant is backed by a governance artifact (from G-03).

#### Non-Responsibilities
- Does not grant initial authority — G-05 owns grants.
- Does not evaluate whether a delegation is "wise" or "policy-compliant" at grant time — that is enforcement by G-12 or G-13 post-facto.
- Does not manage the council's appointment of delegation authority — that is G-04 charter resolution.
- Does not execute governance flows.

#### Inputs
- Delegation grant request (grantor, grantee, scope, level, constraints).
- Delegation revocation (by grantor or authority).
- Delegation validation request (from G-05, read-only).

#### Outputs
- `DelegationChain: {valid: bool, grant: Grant, previous: Grant | null, constraintsApplied: []}`
- Revocation events (to G-14).
- Delegation events.

#### Interfaces
- **Inbound:** `createDelegation(request) → grant`; `revokeDelegation(delegationId, reason)`
- **Outbound:** `validateChain(actorId, action, target) → ChainValidation` (to G-05, read); `emit(event) → G-14`
- **Query:** `getActiveChainForActor(actorId) → chain; `getGrant(delegationId) → grant`

#### Dependencies
- G-03 (artifact backing for delegation grants)
- G-04 (scope definitions that limit what can be delegated)
- G-05 (authority linkage — downstream)
- G-09 (audit trail for revocation)
- G-10 (principal binding)
- G-14 (events)

#### Authority
Delegation manager is a record-keeper, not an authority-granter. Grants originate from principals who hold corresponding authority in G-05. Cannot create delegation for a principal who has no G-05 grant.

#### Ownership
- Governance Product (delegation model, chain rules).
- Council (scope and level constraints).
- Platform (implementation and storage).

#### Lifecycle
Active after G-05 has baseline grants. Pre-bootstrap: bootstrap grants are direct G-05 grants, not delegated.

#### State Model
```
Grant: PENDING → ACTIVE → SUSPENDED → REVOKED → ARCHIVED

Delegation chain is ACTIVE only if all grants in chain are ACTIVE.
```

#### Security Boundary
Delegation chains reveal organizational trust structure. Chain enumeration requires audit authority (typically auditor or governance operator role). Validation result is returned to requesting session only.

#### Failure Boundary
Chain validation failure → G-05 returns DENIED. This is a governable outcome, not an error. Chain resolution failure (system error, not validation failure) → escalate to G-00.

#### Events (Component-Internal with Canonical Mapping)
`DelegationGranted`, `DelegationValidated`, `DelegationRevoked`, `ChainInvalidated`, `ChainCascadedRevocation` — these are G-06 internal event names that map to canonical events in governance-events.md §3.3: `governance.authority.delegated`, `governance.authority.revoked`, etc.

#### Observability
Delegation depth distribution. Chain failure rate. Average chain length. Revocation frequency.

#### Performance Considerations
Chain validation is on hot path for authority resolution. Cache by actor-action-target. Invalidate on any revocation in relevant chain.

#### Scalability
Scales linearly with principal count. Consider pruning historical delegations from active set (archive to G-09).

#### Recovery
Recovery from G-03 (grant artifacts) and G-09 (revocation events). Chain rebuild from artifact + event replay.

#### Governance Constraints
No orphan delegations (delegation must trace to active delegation grant and upstream active grant). No circular delegations (enforced on grant creation). Maximum chain depth is configurable in charter (default: 4).

#### Cross-Part Dependencies
- Part 1: principal binding (delegator, delegatee)
- Part 5: allocation of delegation authority within principal bounds
- Part 12: revocation and chain history as audit artifacts

---

### 5.8 G-07 — Risk Manager

#### Purpose
Govern the process of identifying, assessing, treating, monitoring, and reporting risk exposure across governance scopes.

#### Responsibilities
- Maintain risk register: risk ID, description, scope, category, probability, impact, treatment, residual risk, review period.
- Produce risk assessment record: risk score, trend, treatment gap, owner.
- Produce risk treatment plan updates (routed to approval via G-12).
- Report risk posture to G-15 for conformance gap analysis.
- Trigger risk review reminders when review period expires.

#### Non-Responsibilities
- Does not make treatment decisions — proposes, routes for approval via G-12.
- Does not set risk appetite — risk appetite comes from policy and council (G-04).
- Does not own compliance obligations — that is G-08's domain.

#### Inputs
- Risk identification events (from any operating layer, via G-14).
- Risk treatment proposal (from risk owner).
- Risk appetite parameters (from G-03 policy snapshot).
- Risk review triggers (scheduled or event-driven).

#### Outputs
- Risk register entry (stored, returned on query).
- Risk assessment report.
- Risk treatment proposal (routed to G-12).
- Risk posture aggregation (to G-08, G-15).

#### Interfaces
- **Inbound:** `submitRisk(risk)`; `submitTreatment(treatment)`; `reportRiskContext(context)`
- **Outbound:** `queryAppetite(scope) → G-03`; `routeForApproval(proposal) → G-12`; `emit(event) → G-14`; `shareRiskPosture() → G-08, G-15`
- **Query:** `getRisk(riskId)`; `getRiskRegister(scope)`; `getRiskPosture(scope)`

#### Dependencies
- G-03 (risk policy artifacts, risk appetite parameters)
- G-08 (compliance linkage)
- G-09 (audit of risk assessments)
- G-10 (risk owner identity)
- G-12 (treatment approval flow)
- G-14 (risk identification events)

#### Authority
Does not set risk appetite or treatment — records risk, proposes treatment, enforces review cycle.

#### Ownership
- Risk Management function (risk register ownership).
- Governance Product (risk taxonomy).
- Council (risk appetite charter).

#### Lifecycle
Active after G-03 has risk policy loaded. Risk register initialized at governance boot.

#### State Model
```
Risk item states:
IDENTIFIED → ASSESSED → TREATMENT_PLANNED → TREATMENT_IN_PROGRESS
         → MONITORING → CLOSED
                                           ↘ REOPENED (new trigger event)
```

#### Security Boundary
Risk register is structured for governance reporting — access controlled by scope. Treatment plans may contain sensitive operational information. Restrict to risk owner and governance operator roles.

#### Failure Boundary
Failure to record a risk identification event = risk data loss. Must not drop risk events. Event queue in G-14 absorbs failures; G-07 must validate queue state at startup.

#### Events
`RiskIdentified`, `RiskAssessed`, `TreatmentProposed`, `TreatmentApproved`, `TreatmentRejected`, `TreatmentApplied`, `RiskClosed`, `RiskReopened`, `RiskPostureProduced`

#### Observability
Risk item count by state and scope. Treatment approval latency. Open risk age distribution. Risk posture trend by scope.

#### Performance Considerations
Risk register grows with operational scope. Bounded and bounded-growth; not unbounded.

#### Scalability
Per-scope partitioning. Read-heavy for posture queries; write-light for new items.

#### Recovery
Risk register recovered from G-03. Risk assessment history from G-09 audit trail. Open treatment plans in CLOSING state require atomic recovery — mark held by G-12 until committed.

#### Governance Constraints
Every treatment proposal must route through G-12 before execution. Risk owner must be a named principal in G-10. Risk posture must be published to G-15 at specified intervals.

#### Cross-Part Dependencies
- Part 1: risk owner and risk committee member identity (G-10)
- Part 3: data context for risk identification (cross-domain)
- Part 12: risk assessment audit records (G-09)

---

### 5.9 G-08 — Compliance Manager

#### Purpose
Track, report, and evidence all applicable governance obligations — regulatory, contractual, policy, and standards-derived — and verify evidence currency against compliance baselines.

#### Responsibilities
- Maintain obligation register: obligation ID, source, scope, control mapping, evidence requirements, review period, owner.
- Produce compliance baseline for G-15 comparison.
- Track evidence currency: when evidence becomes stale, trigger refresh request.
- Produce compliance reports for internal and external use.
- Flag control gaps (identified by G-13) as compliance findings.
- Interface with external compliance authority (if applicable).
- Report to G-15 when baseline is updated.

#### Non-Responsibilities
- Does not create obligations — obligations are derived from policy, regulation, and contract.
- Does not set control design — proposes controls from obligation requirements; G-13 designs and tests them.
- Does not manage enforcement — reports findings, acts on direction.

#### Inputs
- Obligation imports (from G-03 policy package).
- Evidence updates (from control testing — G-13).
- Compliance authority notifications (external).
- Renewal requests (from obligation owners).

#### Outputs
- Compliance baseline record (to G-03, G-15).
- Compliance report.
- Compliance finding (to G-13, G-09).
- Obligation state record.

#### Interfaces
- **Inbound:** `importObligations(source, scope)`; `updateEvidence(obligationId, evidence)`; `submitFinding(finding)`
- **Outbound:** `publishBaseline(baseline) → G-03`; `notifyConformanceEngine(baseline) → G-15`; `emit(event) → G-14`
- **Query:** `getObligation(id)`; `getComplianceReport(scope)`; `getBaseline(scope)`

#### Dependencies
- G-03 (obligation identifiers, control baselines)
- G-13 (control evidence)
- G-14 (events for notification)
- G-15 (conformance baseline interface)
- G-09 (compliance audit records)

#### Authority
Compliance manager imports obligations from authoritative sources. Cannot modify an obligation — any change requires re-import from source. Cannot override the compliance baseline — baseline changes require explicit governance action.

#### Ownership
- Legal / Compliance function (obligation register).
- Governance Product (obligation lifecycle).
- Council (compliance scope definitions).

#### Lifecycle
Active after G-03 has initial obligation package. Continuous operation — compliance reporting cadence is calendar-driven.

#### State Model
```
Obligation states:
IDENTIFIED → IMPORTED → VALIDATED → ACTIVE → MONITORING → EVIDENT → REVIEW_DUE
                                               → EVIDENCE_STALE → RENEWAL_REQUIRED
                          ↘ SUPERSEDED (from re-import)
```

#### Security Boundary
Compliance reports are often external-facing. Evidence within report must be verified for access appropriateness — some evidence items are sensitive. Obligation register import actions controlled by source authority.

#### Failure Boundary
Compliance failure (obligation gap) does not halt governance — it is reported as conformance finding. Registry update failure during re-import = stale baseline — escalate via G-00 and notify compliance authority.

#### Events
`ObligationIdentified`, `ObligationImported`, `EvidenceStale`, `BaselinePublished`, `FindingIssued`, `ComplianceGapDetected`, `ObligationReviewDue`

#### Observability
Obligation count by state. Evidence staleness ratio. Gap count by scope. Compliance score trend. Review completion rate.

#### Performance Considerations
Obligation register is large but bounded by regulatory universe (typically low-hundreds to low-thousands). Read-heavy, write-light.

#### Scalability
Per-jurisdiction partitioning for multinational operations. Read replicas for report generation.

#### Recovery
Registry rebuilt from G-03 artifacts. Evidence history from G-09. Active obligation review deadlines from schedule — reschedule on recovery.

#### Governance Constraints
Evidence authenticity is a hard constraint — evidence links must be verifiable hash-chained. Compliance report generation requires completeness confirmation — no reports on partial data.

#### Cross-Part Dependencies
- Part 3: obligation scope anchored to data context
- Part 6: obligation source derived from standards and contracts
- Part 12: compliance evidence audit trail (G-09)

---

### 5.10 G-09 — Audit Manager

#### Purpose
Produce, maintain, and provide access to complete, immutable, verifiable audit records for every governance action, decision, and state change.

#### Responsibilities
- Record all governance events as immutable audit entries with:
    - Principal chain (from G-10)
    - Full context state at time of event
    - Reference to causal event (for decision trails)
    - Compliance hash for integrity verification
- Provide audit manifests: sealed bundles of audit records for a period, scope, or session.
- Support audit queries by scope, principal, time range, event type.
- Preserve immutability: once recorded, audit entries cannot be edited or deleted.
- Support evidence extraction and packaging for external compliance use.
- Coordinate with G-15 for conformance audit trail.

#### Non-Responsibilities
- Does not create audit data — receives events from G-14, records them.
- Does not interpret audit findings — reports to auditors or compliance function.
- Does not approve audit scope — that is an approval flow via G-12.

#### Inputs
- Governance events (from G-14).
- Audit request (scope, time range, requester principal).
- Evidence packaging request.

#### Outputs
- Immutable audit record (sealed entry).
- Audit manifest (aggregated entries).
- Audit report (formatted, scoped).
- Integrity verification result.

#### Interfaces
- **Inbound:** `acceptEvent(event)`; `requestAuditManifest(scope, range)`; `packageEvidence(scope, range)`
- **Outbound:** `notifyIntegrityBreach(auditId)` (alert to G-00)
- **Query:** `queryAudit(scope, range, filters) → entries` (with access control); `verifyIntegrity(auditId)` → pass/fail.

#### Dependencies
- G-00, G-01, G-04, G-05, G-06, G-07, G-08, G-09 (all components emit events)
- G-10 (principal chain component of audit record)
- G-12 (approval record linkage)
- G-14 (event source)
- G-15 (conformance audit trail exchange)
- Read access to G-03 for policy/artifact references at event time.

#### Authority
Audit manager is technically immutable once recorded. Cannot delete or edit entries. Cannot withhold recorded entries from authorized auditors. Cannot originate events (events originate at source via G-14).

#### Ownership
- Internal Audit function (audit scope, frequency, access policy).
- Governance Product (audit schema, event taxonomy).
- Platform (storage, integrity, retention).

#### Lifecycle
Active from governance boot. Cannot be turned off during active governance. Archive mode — read-only, no new records accepted only after formal governance dissolution.

#### State Model
```
Record: RECEIVED → RECORDED (immutable, cannot transition)

Audit session: OPEN → RECORDING → MANIFEST_READY → ARCHIVED
```

#### Security Boundary
Most sensitive governance component. Integrity is governance constraint. Access to audit entries is role-gated: reader role must be registered in G-05 (decision authority) or granted via exception via G-11. No public access to audit entries.

#### Failure Boundary
Concurrent write failure → events buffered in G-14 queue. Storage exhaustion → emergency escalation to G-00, governance halt declared. Loss of completed audit manifest is governance halt — manifest must be re-sealed from event replay.

#### Events
`AuditEventRecorded`, `IntegrityVerified`, `IntegrityBreachDetected`, `ManifestSealed`, `ManifestArchived`, `AccessDenied`, `AccessGranted`, `RetentionExpired`

#### Observability
Event ingestion rate by type. Storage growth rate. Manifest generation time. Integrity verification pass rate. Query latency.

#### Performance Considerations
Write path must be append-only and fast. Consider write-ahead log + async materialization for heavy query patterns. Integrity hash must be computed on every record — optimize hash computation.

#### Scalability
Event volume governance events are low compared to operational data. Scale for high-regulation environments with partitioned scope.

#### Recovery
Recover from G-14 event queue for recent events. Rebuild from G-09 manifest archive for historical events. Integrity verification on every load.

#### Governance Constraints
Tamper-evident is a hard constraint. Hash-chained entries. Any integrity breach = mandatory escalation. Audit retention period is compliance-mandated — G-09 cannot age-out records during active retention.

#### Cross-Part Dependencies
- Part 1: principal identity for audit trail binding (G-10)
- Part 5: audit reader role allocation
- All governance components emit to G-09

---

### 5.11 G-10 — Accountability Manager

#### Purpose
Bind every governance action to its accountable principals — the actor who performed the action and the principal(s) the actor represents — and support causal chain reconstruction.

#### Responsibilities
- Maintain actor-to-principal mapping with proof (delegation chain, appointment record).
- Record every governance action with its principal bindings.
- Support trace queries: given an outcome, what principals were bound?
- Produce accountability manifest: who is accountable for this governance decision.
- Flag principal state changes (crash, suspension) that affect ongoing governance accountability.

#### Non-Responsibilities
- Does not verify that the actor actually performed the action — it records intended bindings.
- Does not make authorization decisions — delegates to G-05.
- Does not prevent principal spoofing — input authenticity is operating layer's responsibility.
- Does not manage principal lifecycle — that is Part 1.

#### Inputs
- Principal binding request: actor identifier + principal identifier + evidence reference.
- Governance action completion (from all governance components).
- Principal state changes.

#### Outputs
- Principal binding record: `{actor, principal, evidence, boundAt, validUntil}`
- Accountability manifest for governance decision.
- Principal state change warning.

#### Interfaces
- **Inbound:** `bindActor(actor, principal, evidence)`; `recordAction(action, principalBindings)`
- **Query:** `resolvePrincipalChain(actorId)`; `getAccountabilityFor(decisionId)`
- **Outbound:** `emit(event) → G-14`; `readSnapshot(entityRef) → G-03` (delegation record reference).

#### Dependencies
- G-01 (policy for accountability model definition)
- G-03 (delegation and appointment artifacts)
- G-06 (delegation chain reference)
- G-14 (accountability events)

#### Authority
Does not author principal relationships, only records them. Record is valid only if evidence is backed by an artifact in G-03.

#### Ownership
- Governance Product (accountability model definition).
- Legal (accountability legal definition).
- Platform (implementation).

#### Lifecycle
Active with governance. Pre-bootstrap: bootstrap governance uses a declared root principal (platform authority) with artifact backing in G-03.

#### State Model
```
Binding: ACTIVE → SUSPENDED → REVOKED (cascading from upstream)

Principal state (observed, not managed):
ACTIVE → SUSPENDED → REVOKED (Part 1 owned)
```

#### Security Boundary
Accountability records are sensitive. They map actor identity to principal. Treat as PII. Access restricted to governance operators and authorized auditors.

#### Failure Boundary
Binding failure does not block governance action — action is recorded with best available binding. Binding gap is flagged as accountability gap in audit (G-09). Governance action proceeds; accountability gap is governed as finding, not failure.

#### Events
`PrincipalBound`, `BindingVerified`, `PrincipalSuspended`, `BindingRevoked`, `AccountabilityGap`, `AccountabilityRestored`

#### Observability
Binding rate. Gap rate. Principal suspension frequency. Cross-component accountability coverage.

#### Performance Considerations
Principal binding is on hot path for every governance action. Cache by actorId. Invalidate on principal state change or revocation.

#### Scalability
Organization-scale — principal count in low thousands. Index on actorId for fast lookup.

#### Recovery
Rebuild from G-09 audit events. Append-only log ensures no loss. Gap events flag partial binding recovery.

#### Governance Constraints
Every governance action must have at least one bound principal at the time of action. Actions bound to suspended principals are flagged. Bindings are immutable after record.

#### Cross-Part Dependencies
- Part 1: core principal model (identity, state, relationships)
- Part 12: accountability events as audit records

---

### 5.12 G-11 — Exception Manager

#### Purpose
Govern the lifecycle of exceptions to published policy and control baselines — document, constrain, expire, and audit every exception.

#### Responsibilities
- Receive exception requests with scope, rationale, evidence, and period.
- Evaluate exception request against available authority (via G-05) and permissibility (from exception policy in G-03).
- Issue exception grant: exception ID, scope, conditions, start/end, monitoring requirements.
- Monitor exception expiry and trigger renewal or expiration.
- Produce exception audit record and notify G-09 and G-14.
- Produce exception compliance report for G-15 and G-08.

#### Non-Responsibilities
- Does not authorize exceptions — issuance is based on authority from G-05.
- Does not determine that an operating event qualifies for an exception path — that is G-02's evaluation to identify Deny+Exception path.
- Does not enforce during exception — produces the exception scope; enforcement is at G-02 evaluation.

#### Inputs
- Exception request: scope, rationale, evidence, period.
- Authority resolution result (from G-05 — is the requester authorized to request this exception?).
- Exception policy (from G-03).

#### Outputs
- Exception grant (if authorized): `exceptionId, scope, conditions, validPeriod, monitoringRequirements`.
- Exception expiry warning.
- Exception compliance report.
- Exception event.

#### Interfaces
- **Inbound:** `requestException(request)`; `renewException(exceptionId)`; `closeException(exceptionId)`
- **Outbound:** `notifyEvaluator(exceptionId) → G-02` (exception scope inserted into evaluation); `emit(event) → G-14`; `reportCompliance() → G-08, G-15`
- **Query:** `getException(exceptionId)`; `listActiveExceptions(scope)`; `getComplianceReport()`

#### Dependencies
- G-03 (exception policy, instance policy for scope definition)
- G-05 (authority grant for requester)
- G-02 (exception injected into evaluation context)
- G-08, G-15 (exception compliance surface)
- G-09 (exception audit record linkage)
- G-14 (event dissemination)

#### Authority
Exception issuance requires positive authority resolution in G-05 for the exception scope. Cannot issue an exception without the requesting principal holding appropriate authority grant. Exception issuance without matching authorization in G-05 is invalid.

#### Ownership
- Council and relevant committee (exception approval for their scope).
- Governance Product (exception model, conditions, period constraints).
- Compliance (exception compliance reporting).

#### Lifecycle
Active after G-05 and G-02 are operational. Pre-bootstrap: no exceptions issued; bootstrap constraints are absolute.

#### State Model
```
Exception: REQUESTED → PENDING_REVIEW → ACTIVE → EXPIRING → EXPIRED / RENEWED
                                         → CLOSED_EARLY
```

#### Security Boundary
Exception scope is governance-critical information. Exception grants treated like control bypass authorizations. Access: requester + approver + governance operator + auditor.

#### Failure Boundary
Exception expiry without renewal = policy returns to strict evaluation. This is a governable outcome, not a failure. Exception service failure = active exceptions are not renewed — explicit degradation to strict mode on expiry.

#### Events
`ExceptionRequested`, `ExceptionGranted`, `ExceptionDenied`, `ExceptionExpiring`, `ExceptionExpired`, `ExceptionRenewed`, `ExceptionClosed`

#### Observability
Exception count by scope and type. Exception age distribution. Exception approval rate. Pending review count.

#### Performance Considerations
Exception set is bounded by human governance capacity — typically low numbers. Read-heavy: G-02 checks exception state during every evaluation.

#### Scalability
Linear with operational scope. Per-scope partitioning if needed.

#### Recovery
Rebuild current exception state from G-03 snapshot + G-09 events for recent expiries/renewals. Active exceptions rehydrated on G-02 restart.

#### Governance Constraints
Every exception must have rationale and evidence. Exceptions have maximum lifespan — perpetual exceptions require explicit renewal at council level. Exception violations (operation outside exception scope) are compliance findings (G-08, G-09).

#### Cross-Part Dependencies
- Part 1: requester and approver identity (G-10)
- Part 5: exception authority source (G-05)
- Part 6: exception definitions within committee scope
- Part 9: exception may affect data access boundaries
- Part 12: exception audit trail

---

### 5.13 G-12 — Approval Manager

#### Purpose
Route, track, and record approval decisions for all governance artifacts and actions that require explicit approval.

#### Responsibilities
- Receive and route approval requests from source components (G-01, G-04, G-13, G-08).
- Identify approval role from G-05 for the request type and scope.
- Present request to approver with context, rationale, evidence.
- Record approval decision: approved / rejected / returned with conditions.
- Record approval chain (sequential or parallel).
- Publish approval decision — route outcomes to appropriate components.
- Maintain approval history and tie to governing artifact in G-03.

#### Non-Responsibilities
- Does not determine approval policy — policy comes from G-03 artifact.
- Does not set approval roles — role assignment is G-05.
- Does not make policy content decisions — that is council's responsibility (G-04).
- Does not execute the approved action.

#### Inputs
- Approval request: artifact reference, request type, rationale, evidence, requester identity.
- Approval decision: approve / reject / conditions.
- Approval policy (from G-03).

#### Outputs
- Approval decision record.
- Routing instruction for approved artifact/action.
- Approval events.
- Approval rejection rationale (to requester and G-14).

#### Interfaces
- **Inbound:** `submitForApproval(request)`; `recordDecision(requestId, decision)`
- **Outbound:** `notifyApproved(requestId, action) → appropriate component`; `notifyRejected(requestId, rationale)`; `emit(event) → G-14`; `recordMinutes(notes) → G-09`
- **Query:** `getApprovalStatus(requestId)`; `listPendingApprovals(approverId)`

#### Dependencies
- All components that require approval submit via G-12.
- G-03 (approval policy artifacts, quorum rules).
- G-04 (committee-level approval definitions).
- G-05 (approval roles and authority).
- G-09 (approval decision audit records).
- G-14 (approval events).

#### Authority
Routing and recording authority. Cannot override an authority's decision. Cannot approve a request on behalf of an approver without explicit delegation via G-06.

#### Ownership
- Governance Product (approval workflow and UX).
- Council and relevant committee (approval policy).
- Platform (implementation).

#### Lifecycle
Active after G-03 approval policy loaded. Handles all approval flow for governance lifecycle.

#### State Model
```
Request: SUBMITTED → ROUTED → IN_REVIEW → DECIDED (APPROVED | REJECTED | RETURNED)
                              → ESCALATED (approver cannot act)
                              → EXPIRED (approval window elapsed)
```

#### Security Boundary
Approval requests contain rationale and evidence that may be sensitive. Access: requester, designated approver, governance operator, auditor. Routing rule inference is sensitive — accessing routing rules implies organizational structure knowledge.

#### Failure Boundary
Routing failure = escalation via G-00. Approval timeout = governance decision block — operating context blocked unless agreed-upon override protocol invoked (via G-11). Approval service outage = governance halt declared.

#### Events
`ApprovalRequested`, `ApprovalRouted`, `InReview`, `ApprovalDecided`, `ApprovalRejected`, `ApprovalEscalated`, `ApprovalExpired`, `ApprovalWithdrawn`

#### Observability
Approval request count by type. Approval latency (request → decision). Rejection rate. Approval role utilization.

#### Performance Considerations
Approval is not on hot path of execution — it is on governance governance lifecycle path. Latency acceptable in minutes to hours. SLA driven by charter, not technical performance.

#### Scalability
Approval count bounded by organizational governance capacity. Not a horizontal scalability concern.

#### Recovery
Pending approvals recorded in G-03. Recover and re-present on recovery. Completed approvals in G-09 audit trail.

#### Governance Constraints
Approval decisions must reference governing authority (charter, policy). No approval without valid principal binding. Approval records immutable after recording. Re-approval on recovery of service outage required (policy-dependent).

#### Cross-Part Dependencies
- Part 1: principal identity for requester and approver
- Part 4-9: operating context requests requiring approval
- Part 12: approval decision audit trail (G-09)

---

### 5.14 G-13 — Control Manager

#### Purpose
Design, implement, test, and evidence governance controls — linking each control to its governing obligation, policy, and governance evidence.

#### Responsibilities
- Maintain control register: control ID, description, type, scope, governing obligations, control objective.
- Produce control design description and implementation records.
- Test control effectiveness: test procedure, evidence, result, date, next review.
- Produce evidence for audit and compliance (to G-09, G-08, G-15).
- Track control lifecycle: design → implement → test → operate → degrade → remediate.
- Produce control effectiveness report.

#### Non-Responsibilities
- Does not evaluate policy — delegates to G-02.
- Does not set obligations — delegates to G-08.
- Does not enforce controls at runtime — controls runtime effect happens at evaluation and operating context.
- Does not make risk treatments — delegates to G-07 for treatment proposal, G-12 for approval.

#### Inputs
- Control design (from control owner, approved via G-12).
- Test results and evidence (from testing function).
- Obligation mapping (from G-08 obligation register).
- Policy coverage gaps (from G-15 conformance analysis).
- Remediation plan.

#### Outputs
- Control record (stored in G-03).
- Test result and evidence record.
- Control effectiveness report (for G-09, G-08, G-15).
- Control gap finding (when conformance shows gap).

#### Interfaces
- **Inbound:** `registerControl(control)`; `submitTestResult(controlId, test)`; `submitRemediation(remediation)`
- **Outbound:** `queryControl(testId)` → root; `emit(event) → G-14`; `shareEvidence() → G-09, G-08, G-15`
- **Query:** `getControlsForObligation(obligationId)`; `getControlEffectiveness(scope)`; `listControlGaps()`

#### Dependencies
- G-03 (control records, obligation references)
- G-08 (obligation linkage)
- G-09 (evidence storage link)
- G-14 (control events)
- G-15 (conformance gap input)

#### Authority
Does not create obligations. Control design is subject to approval via G-12. Control test results are self-attested by testing function — independent verification is G-09 or council audit.

#### Ownership
- Internal Audit / Risk function (control design and ownership).
- Governance Product (control model, evidence schema).
- Testing function (execution and attestation).

#### Lifecycle
Active after G-03 has baseline control set. Controls have their own lifecycle independent of platform lifecycle.

#### State Model
```
Control lifecycle:
DESIGNED → APPROVED → IMPLEMENTED → TESTED → OPERATING
                                                  → DEGRADED → REMEDIATION_IN_PROGRESS
                                                  → EFFECTIVE
                          ↘ FAILED → REMEDIATION_PLANNED → REMEDIATION_IN_PROGRESS ↙
```

#### Security Boundary
Control evidence contains operational details that may be sensitive. Testing methodology considered proprietary. Control gap findings distributable only to authorized roles.

#### Failure Boundary
Control registration failure = obligation gap risk. G-08 must surface gap as compliance finding. Control effectiveness cannot be "unknown" for too long — maximum assessment period is charter-defined.

#### Events
`ControlRegistered`, `ControlTested`, `TestPassed`, `TestFailed`, `ControlDegraded`, `RemediationPlanned`, `RemediationApplied`, `EffectivenessReported`

#### Observability
Control count by state. Test pass rate. Control age distribution. Gap count by scope.

#### Performance Considerations
Controls are fewer than policies (tens to hundreds). Read-heavy for reporting. Test scheduling is calendar-driven.

#### Scalability
Organizational scale. Not a horizontal scalability concern. High-SLA on evidence retrieval for audit.

#### Recovery
Recover control records from G-03. Test evidence from G-09. Active remediation plans recorded in G-03.

#### Governance Constraints
Every control must trace to at least one obligation in G-08. No control without planned test cadence. Test results must include evidence with integrity hash. Control gap is a compliance finding (G-08) and conformance finding (G-15).

#### Cross-Part Dependencies
- Part 3: data control linkages
- Part 6: control scope definition
- Part 9: data-related controls
- Part 12: control evidence audit trail (G-09)

---

### 5.15 G-14 — Governance Event Manager

#### Purpose
Define governance event schema, ingest events from all components, classify, route, and make governance events available for all governance flows.

#### Responsibilities
- Maintain governance event schema (standardized event shape and taxonomy).
- Receive events from all governance components.
- Classify events by type, source component, scope, and severity.
- Route events to consumers (G-09 for persistence, G-00 for correlation, G-07/G-08 for root-cause, etc.).
- Maintain event correlation context for governance session tracing.
- Retain events for governance session window and for audit retention.
- Emit event publication notifications to subscribed components.

#### Non-Responsibilities
- Does not originate events — sources originate.
- Does not evaluate events — routing only.
- Does not execute governance actions.
- Does not retain operator/system events — only governance-domain events.

#### Inputs
- Governance events from all G-00–G-13 components.
- Event subscription requests.
- Event schema updates (from governance Product).

#### Outputs
- Routed governance events (to subscribing components).
- Event manifest per governance session.
- Classification metadata.
- Event publication notifications.

#### Interfaces
- **Inbound:** `emit(event)` from all governance components.
- **Query:** `getEventsForSession(sessionId)`; `getEventsByType(type, range)`; `getEventStream(filter)` (read-only subscribers)
- **Outbound:** `routeEvent(event, target)`; `notifySubscribers(event)`

#### Dependencies
- All governance components (G-00 through G-13) — every component is an emitter.
- G-03 (event schema artifact).
- G-09 (event persistence — write-through on acceptance).
- G-15 (conformance event stream).

#### Authority
Event routing is Technical. Cannot suppress events. Routing rules are defined by schema; cannot be modified by components.

#### Ownership
- Governance Product (event taxonomy, schema).
- Platform (infrastructure, routing, retention).
- Internal Audit (schema change approval).

#### Lifecycle
Active at governance boot. Pre-bootstrap events are not accepted — bootstrap events are recorded retroactively once G-03 is initialized.

#### State Model
```
Event: EMITTED → ROUTED → PERSISTED → RETAINED
                    ↘ DROPPED (rare, schema rejection, notifies source)
```

#### Security Boundary
Governance events may contain sensitive context. Event routing is scoped: components receive only events matching their subscription. Audit subscription is broad; requires audit role in G-05.

#### Failure Boundary
Event loss = governance decision gap. Event persistence failure → emergency escalation to G-00. Governance session cannot close until all emitted events are confirmed persisted. Queue-based buffering for partial failures.

#### Events
`EventRouted`, `EventPersisted`, `EventSubscribed`, `SubscriptionChanged`, `SchemaUpdated`, `EventQuotaThreshold`

#### Observability
Event ingestion rate by component and type. Routing latency. Persistence backlog. Schema change frequency. Subscription count.

#### Performance Considerations
Event throughput is governance-scaled (not comparable to operational event volume). Prioritize consistency over throughput. Write path must be synchronous for audit-critical events.

#### Scalability
Scalable by scope partitioning in multi-domain deployments. Event retention is bounded by charter-defined retention period — bounded-growth.

#### Recovery
Event replay from G-09 audit manifest. Recovery from G-14 buffered queue. Schema version reconciliation required if schema changes occurred during outage.

#### Governance Constraints
Every governance action MUST emit at least one event before completing. Event suppression is prohibited. Schema changes require audit Product approval and charter compliance verification.

#### Cross-Part Dependencies
- All governance components emit to G-14.
- Part 12: G-09 persistence layer.
- Part 10: principal binding for event source identification.

---

### 5.16 G-15 — Conformance Manager

#### Purpose
Evaluate governance conformance against policy baselines, control sets, compliance obligations, and council-defined governance standards — produce continuous conformance posture.

#### Responsibilities
- Receive baseline snapshot from G-08 (compliance), G-03 (policy snapshot), G-13 (control set).
- Evaluate conformance at specified cadence (continuous or scheduled).
- Evaluate three conformance domains:
    1. **Policy conformance**: does current behavior match the published policy envelope?
    2. **Control conformance**: are controls designed and operating effectively against obligation baselines?
    3. **Governance conformance**: are governance processes (approval, exception, review cycle) followed?
- Produce conformance finding: compliant / non-compliant / partial / unknown.
- Produce conformance score by domain and scope.
- Produce conformance gap list with treatment proposal routed to G-12.
- Produce conformance report for council and audit distribution.
- Alert G-00 on conformance breach.

#### Conformance Domains
G-15 evaluates three conformance domains. These domains are an assessment overlay on top of the existing governance architecture, not a separate governance layer:
- **Policy conformance**: does current behavior match the published policy envelope? Assesses G-01/G-02/G-03 outputs.
- **Control conformance**: are controls designed and operating effectively against obligation baselines? Assesses G-13 outputs.
- **Governance conformance**: are governance processes (approval, exception, review cycle) followed? Assesses G-11, G-12, G-04 process adherence.
G-15 does not create or modify any governance artifact — it evaluates existing artifacts and produces conformance findings.

#### Non-Responsibilities
- Does not set policy baselines — receives from G-08/G-03.
- Does not design controls — delegates to G-13.
- Does not make treatment decisions — routes gap treatment to G-12.
- Does not manage conformance breach outcome — notifies stakeholders, does not unilaterally enforce halts.

#### Inputs
- Policy snapshot (from G-03).
- Compliance baseline (from G-08).
- Control set and test results (from G-13).
- Council-defined governance standards (from G-03).
- Governance exception set (from G-11).
- Scheduled or event-triggered conformance evaluation request.

#### Outputs
- Conformance finding (per domain, per scope).
- Conformance score.
- Conformance gap list (routed to G-12 for treatment).
- Conformance report (to council, G-09).
- Conformance breach notification (to G-00).

#### Interfaces
- **Inbound:** `requestConformanceEvaluation()`; `registerBaseline(baseline, source)`
- **Outbound:** `emit(event) → G-14`; `notifyGap(gap) → G-12`; `publishReport(report) → G-04 (council), G-09 (audit)`; `alertConformanceBreach(breach) → G-00`
- **Query:** `getConformanceScore(scope)`; `getGaps(scope)`; `getReport(scope, period)`

#### Dependencies
- G-03 (policy baselines, charter)
- G-04 (relevant council decision on conformance tolerance)
- G-08 (compliance baseline)
- G-11 (exceptions that modify compliance scope)
- G-13 (control evidence and findings)
- G-00 (conformance breach escalation)
- G-09 (conformance report record)
- G-14 (conformance events)

#### Authority
Conformance evaluation is a governance function. Evaluation methodology determined by council and compliance function. Cannot alter baselines — those are authoritative from G-03/G-08.

#### Ownership
- Internal Audit (conformance assessment methodology).
- Governance Product (score model and thresholds).
- Council (conformance tolerance definition).

#### Lifecycle
Active after G-08 and G-13 have baseline artifacts. Conformance evaluation runs on schedule — not real-time.

#### State Model
```
Evaluation: REQUESTED → RUNNING → COMPLETED → Published
                                    ↘ BREACH_DETECTED → ESCALATED

Scope conformance state:
COMPLIANT | PARTIALLY_COMPLIANT | NON_COMPLIANT | NOT_ASSESSED
```

#### Security Boundary
Conformance scores are governance board-level insight — not distributed broadly. Gap reports may contain findings about operating context; access control required. Conformance breach alerting: breach notification to G-00 is mandatory and cannot be suppressed.

#### Failure Boundary
Conformance evaluation failure = conformance remains at previous state. G-08 and G-13 receive "not assessed" flag. No silent gap recovery. Conformance breach detection must fire even when evaluation cadence is missed.

#### Events
`EvaluationStarted`, `EvaluationCompleted`, `ConformanceScoreUpdated`, `GapIdentified`, `GapTreatmentProposed`, `GapTreated`, `ConformanceBreach`, `ReportPublished`, `BaselineUpdated`, `BaselineExpired`

#### Observability
Conformance score by domain. Gap count and aging. Evaluation on-schedule rate. Breach count and time-to-treatment.

#### Performance Considerations
Conformance evaluation is batch operation bound. Not on hot path. Insert lazily between active governance cycles. Evaluation duration acceptable at minutes to hours (based on scope complexity).

#### Scalability
Conformance scope typically organization-level. Per-domain partitioning. Cache baseline references to avoid repeated G-03/G-08 lookups.

#### Recovery
Rebuild from G-03 snapshot + G-08 baseline + G-13 control state. Governance session events (G-09) reconcile evaluation boundaries.

#### Governance Constraints
Every scope must be assessed at charter-defined cadence — missed assessments are non-compliant. Conformance breach escalation to G-00 cannot be suppressed by any component. Baseline versions must be cited in findings — no gap report without baseline reference.

#### Cross-Part Dependencies
- All operating parts (conformance is cross-part aggregate)
- Part 12: conformance assessment audit trail (G-09)

---

## 6. Component Interaction Sequence

### 6.1 Authoritative Flow: Policy Change → Evaluation Update

```text
Actor: Policy Author
Trigger: New policy proposed for publish

┌──────┐    propose     ┌───────────┐    submit    ┌──────────┐
│ G-01 │──────────────▶│  G-12    │────────────▶│   G-04   │  (Council approval)
│Policy │               │Approval Mgr│            │Council   │
└──────┘                └───────────┘             └────┬─────┘
      ▲                                                │ approve
      │ publishDecision                                │
┌──────┘                                    ┌───────────┘
│                                           │
│  registerChange       publishPackage      │
│                          │                │
│                          ▼                ▼
│                    ┌───────────────┐   updateCharter
│                    │   G-03       │─────────────────────┐
│                    │ Governance  │                        │
│                    │   Registry   │◄─────────────────────┘
│                    └──────┬──────┘
│                           │ snapshotReleased
│                           ▼
│   snapshotAvailable event                            ┌──────────────┐
│                    ┌──────────────┐     reload        │    G-02      │
│                    │   G-00       │──────────────────▶│ Policy Eval  │
│                    │Governance Mgr│                   │  Engine      │
│                    └──────┬───────┘                   └──────┬───────┘
│                           │                                 │
│  nextEvaluation          │                                 │ applySnapshot
│       │                  │                                 │
│       ▼                  ▼                                 ▼
│  ┌──────────┐    requestEval    ┌──────────────┐  evaluate  ┌────────┐
│  │Context   │──────────────────▶│     G-02     │──────────▶│ G-03   │
│  │ Trigger  │                    │ Policy Eval  │◄──────────│  G-03   │
│  └──────────┘                    └──────┬───────┘            └────────┘
│                                        │
│                               emit(evaluationDecision)
│                                        │
│                     ┌──────────────────┘
│                     ▼
│  ┌─────────────┐                         ┌──────────────┐
│  │  G-00       │────────────────────────▶│   G-09       │
│  │Governance   │   auditRecord           │   Audit Mgr   │
│  │   Mgr       │                         └──────────────┘
│  └─────────────┘
│
└──────────────────────────────────────────────────────────────────────
```

### 6.2 Sequence: Exception Request and Application

```text
Trigger: Evaluator encounters Deny with active exception candidate

┌──────────┐                    ┌──────────────┐
│ G-01     │                    │    G-03      │
│Policy Mgr│                    │Governance Reg│
└────┬─────┘                    └──────┬───────┘
     │ container scope                  │ publishSnapshot
     │                                  │
     ▼                                  ▼
┌──────────┐                    ┌──────────────┐
│ G-00     │                    │    G-02      │
│Governance│                    │ Policy Eval  │
│   Mgr    │────────────────────│   Engine     │─ Deny exception path
└────┬─────┘ evaluateRequest   └──────┬───────┘
     │                                │ lookupException
     ▼                                ▼
┌──────────┐                    ┌──────────────┐
│ G-02     │                   │ G-03         │
│Policy Eval│◄─────────────────│ Governance   │
│  Engine  │ exceptionSnapshot  │   Registry   │
└────┬─────┘                   └──────┬───────┘
     │                                │
     │ emit(evaluationDecision)       │
     ▼                                ▼
┌──────────┐                    ┌──────────────┐
│ G-00     │                    │      G-11    │
│Governance│                    │  Exception   │
│   Mgr    │── applyException ──▶│   Manager    │ activate on policy path
└────┬─────┘                    └──────┬───────┘
     │                                │
     │  applyDecision                  │ issueActive
     ▼                                ▼
┌──────────┐                    ┌──────────────┐
│ Decision │                    │      G-09    │
│  Record  │───────────────────▶│   Audit Mgr  │ record decision
└──────────┘                    └──────────────┘
```

### 6.3 Sequence: Approval Lifecycle

```text
Trigger: Policy draft submitted for approval

┌───────┐
│ submit│
│draft  │
└───┬───┘
    │
    ▼
┌───────────┐
│  G-12     │  Approval Manager
│submit─────│─▶ routeToApprover (lookup approval role from G-05)
└─────┬─────┘
      │                                ┌──────────┐
      │ notifyApprover                 │  G-04    │ Council Function
      ▼                                │Council   │─ approve/reject
┌─────────────┐                        └──────────┘
│  Approver   │─ decision                          │
│   Role      │                                    │
└──────┬──────┘                                    │
       │                                           │
       │ decisionRecord                            │
       │                                           │
       ├─────────────────────▶ G-09  ◄─────────────┘
       │                         Audit Mgr
       │
       ├── if approved ▶ G-01  publish approved policy
       │
       └── if rejected ▶ G-01  back to draft
```

---

## 7. Specification Notes

### 7.1 Relation to "Parts" in the AI-OS Specification

Part 13 (Governance Architecture) defines governance components. The components above operate across Parts 1–12 (permissions, execution, data, agents, security, audit).

- **Part 5 (Principal Allocation)** defines the hierarchy of principals and groups. G-05 (Decision Authority Manager) is the runtime expression of those allocations — it does not create them, it enforces them.
- **Part 6 (Governance & Admin Committees)** defines the charter and scope of governance bodies. G-04 (Governance Council) is the component realizing those bodies.
- **Part 12 (Auditability)** governs audit model and records. G-09 (Audit Manager) implements Part 12's audit contract.

Components in Part 13 do **not** replace or re-specify Part 5, 6, or 12. They operate within the authority model defined by those parts.

### 7.2 Logical vs Physical

This document is entirely logical. Physical decomposition (service boundaries, deployment models, technology choices) should be derived per operating environment and is deliberately out of scope.

- "Tier" labels reflect logical dependency, not deployment topology.
- Component state models describe logical states, not process states.
- Event schemas define logical contracts, not wire formats.

### 7.3 Future Extension Points

New components may be added if a new governance capability cannot be expressed through existing components. Any new component must:
- Map to at least one Policy or Obligation (from G-01, G-08).
- Emit events to G-14.
- Store artifacts and snapshots in G-03.
- Bind all actions to Principals via G-10.
- Record audit trails via G-09.
- Route approval through G-12 if it modifies governed state.
- Support conformance evaluation via G-15.

This constraint ensures the logical architecture remains coherent as it grows.
