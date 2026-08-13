# Part 14 — Memory and Continuity Index

**Document Status:** ACTIVE — Continuity / Memory Index
**Version:** 1.0.0
**Date:** 2026-08-13
**Authority:** This document is a **memory and continuity artifact**. It is NOT an architectural source of truth.

---

## 1. Purpose of This Document

MEMORY.md is a **continuity and index document for Part 14 Integration Architecture**.

Its purpose is to help a future AI agent or human contributor understand:
- what Part 14 is
- what has already been established in Part 14
- what has been corrected
- what remains unresolved
- where authoritative information comes from
- what must NOT be inferred

### What MEMORY.md Is NOT

MEMORY.md is NOT:
- an architectural source of truth
- an implementation specification
- a replacement for Parts 0–13
- a replacement for ADRs
- a place to introduce new architecture

If a claim is not sourced to a Part 0–13 document or an accepted/active ADR, it does not belong in MEMORY.md as established fact.

---

## 2. What Part 14 Is

Part 14 is the **integration layer** of the AI-OS architecture specification.

Part 14:
- documents how components from Parts 0–13 compose for integration
- inventories integration-relevant events, interfaces, schemas, components, and ADRs
- records conflicts, gaps, and retractions discovered during traceability review
- provides traceability from integration concerns back to Parts 0–13
- classifies every claim with a status label (EXISTING, DERIVED, ASSUMPTION, UNSPECIFIED, GAP, PROPOSED, FUTURE, CONFLICT)

Part 14 is **derived integration documentation**. It does not redesign, extend, or redefine Parts 0–13.

### What Part 14 Is NOT

Part 14 is NOT:
- a new architectural layer
- an authority that overrides Parts 0–13
- a place to invent components, APIs, events, schemas, protocols, or security mechanisms
- a place to silently resolve conflicts between Parts 0–13

---

## 3. Part 14 Authority Model

### 3.1 Source Authority Hierarchy

1. **Part 00** is the supreme authority for foundational governance: terminology, principles, conformance model, extension-point governance, and scope. Any statement contradicting Part 00 is invalid regardless of other source support.

2. **Each Part (1–13)** is authoritative for its own defined domain. A later Part does not override an earlier Part unless the earlier Part explicitly permits extension or delegation. Part numbering does NOT automatically establish precedence.

3. **Document type precedence within a domain**: frozen architecture spec > frozen context.md > dependency-map.md (DRAFT) > ADR > implementation.

4. **Accepted/Active ADRs** are authoritative only within their explicit scope and stated expiry conditions.

5. **Draft ADRs** (notably all ten Part 13 ADRs: P13-ADR-001 through P13-ADR-010) represent proposals under Architecture Review Board (ARB) review. They MUST NOT be treated as mandatory constraints. They MAY inform design as PROPOSED considerations only.

6. **Part 14** defines integration composition only. It does not create new control-plane constructs unless a source Part explicitly delegates that responsibility.

7. **No redesign authority.** Part 14 MUST NOT redefine Core Component interfaces, Kernel boundaries, or principle semantics. Where Part 14 needs a behavior not specified in Parts 0–13, it MUST be labeled GAP/PROPOSED and resolved through the ADR process before implementation.

### 3.2 Part 14's Role

Part 14 is a **consumer** of Parts 0–13. It documents integration relationships derived from source architecture. It does not produce interfaces consumed by Parts 0–13.

### 3.3 ADR Authority Within Part 14

- **Core ADRs (ADR-001 through ADR-016)**: Active per `project-knowledge/ARCHITECTURE_DECISIONS.md` and Part 01 §1.7.1.
- **Part 12 ADRs (P12-ADR-001 through P12-ADR-010)**: Accepted per Part 12 `adrs.md`.
- **Part 13 ADRs (P13-ADR-001 through P13-ADR-010)**: Draft per Part 13 `adrs.md`. NOT binding.
- **Part 14 own ADRs (P14-ADR-001 through P14-ADR-005)**: Integration Impact Records — cross-references showing how Active/Accepted ADRs affect integration design. They do NOT introduce new architectural decisions.

**Governing Principle**: SOURCE ADRs DECIDE. PART 14 SUMMARIZES. PART 14 ANALYZES. PART 14 DOES NOT SILENTLY DECIDE.

---

## 4. Important Integration Principles Already Established

These principles are sourced from Parts 0–13 and recorded in Part 14. They are NOT new inventions.

| Principle | Status | Primary Source |
|-----------|--------|----------------|
| Event-First Communication | EXISTING | Part 00 §0.4 Principle 1; ADR-001 (Active) |
| Kernel Purity / Orchestration Boundaries | EXISTING | Part 00 §0.4 Principle 2; ADR-002 (Active) |
| Capability Managers Are Kernel-Owned | EXISTING | Part 00 §0.4 Principle 3; ADR-003 (Active) |
| Global Singleton Accessors Are Explicit Architecture | EXISTING | Part 00 §0.4 Principle 4 |
| Services Are Event-Driven Actors | EXISTING | Part 00 §0.4 Principle 5; ADR-005 (Active) |
| Engineering Services Implement SDLC Phases | EXISTING | Part 00 §0.4 Principle 6; Part 01 §1.4 |
| Capability Facade Services Bridge Events to Managers | EXISTING | Part 00 §0.4 Principle 7; ADR-007 (Active) |
| Immutable Events with Correlation & Causation | EXISTING | Part 00 §0.4 Principle 8; ADR-008 (Active) |
| Explicit Failure Handling via Events | EXISTING | Part 00 §0.4 Principle 9; ADR-009 (Active) |
| Configuration Is Declarative & Layered | EXISTING | Part 00 §0.4 Principle 10; ADR-010 (Active) |
| Version & Compatibility Are First-Class | EXISTING | Part 00 §0.4 Principle 11; ADR-011 (Active) |
| Observability Is Built-In | EXISTING | Part 00 §0.4 Principle 12; ADR-012 (Active) |

These principles are the foundation of Part 14 integration documentation. All Part 14 integration claims must be consistent with them.

---

## 5. Important Source Conflicts Preserved

Part 14 preserves these conflicts. It does NOT silently resolve them. They must be escalated to ARB.

### CONFLICT-01: Core Component Naming

**Parties**: Part 00 §0.3.1 (Core Definitions table) vs Part 01 §1.7.1

Part 00 §0.3.1 Core Definitions table defines Core Components as `EventBus`, `StateManager`, `WorkflowManager`, `ResourceManager`. Part 00 §0.7 layer overview diagram reinforces the same four names. Part 01 §1.7.1 defines Core Components as `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager`. These sets are disjoint except for `EventBus`.

**Part 14 position**: Part 01 §1.7.1 is the frozen architecture spec for kernel composition. Part 14 MUST use Part 01 §1.7.1 names: `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager`.

**Status**: UNRESOLVED — requires ARB decision on the internal conflict in source documents.

### CONFLICT-02: StructuredLogger Component Classification

**Parties**: Part 01 §1.7.1 (C4 = LifecycleManager) vs Part 3 §3.6 (StructuredLogger = C4) / interfaces.md §2.1

Part 01 §1.7.1 defines the 4th Core Component as `LifecycleManager`. Part 3 §3.6 calls `StructuredLogger` "the last Core Component" (C4). `interfaces.md` §2.1 lists `StructuredLogger` as a Core Component. Part 00 §0.4 Principle 12 names `StructuredLogger` as the single logging abstraction but does NOT classify it as a Core Component.

**Part 14 position**: `StructuredLogger` MUST NOT be classified as a Core Component until resolved via ADR.

**Status**: UNRESOLVED — requires ARB decision.

### CONFLICT-03: AuthN/AuthZ Scope for v1.0

**Parties**: Part 00 §0.2.2 vs Part 4 §4.1.4/§4.7 (SecurityManager) vs Part 13 governance architecture

Part 00 §0.2.2 states AuthN/AuthZ is deferred to v2.0 ("Kernel assumes trusted single-tenant process"). Part 4 §4.1.4 lists `IdentityProvider` and `ConfigurationAuthority` as Core Component consumers, and Part 4 §4.7 describes `SecurityManager` with detailed authorization semantics (`authorize(principal, action, resource)`). Part 13 governance architecture references `SecurityManager`, `G-14`, `G-05`, and `INT-SEC-AUTH-001` as if governance-level AuthN/AuthZ exists within v1.0.

**Part 14 position**: This may be resolvable if Part 13 security operates as an optional overlay rather than kernel-mandated infrastructure. Part 14 MUST document both paths (with and without governance overlay) until resolved.

**Status**: UNRESOLVED — requires ARB clarification.

### CONFLICT-04: Event Naming / Envelope Differences (Part 2 vs Part 12)

**Parties**: Part 2 §2.2.1 vs Part 12 §4 / Part 14 schemas.md §1.1

- **Field names**: `eventId` / `eventType` / `correlationId` (Part 2, PascalCase) vs `event_id` / `event_type` / `correlation_id` (Part 12, snake_case)
- **ID format**: `eventId` = UUIDv7 (Part 2) vs `event_id` = ULID (Part 12)
- **Priority encoding**: 5-level (CRITICAL/HIGH/NORMAL/LOW/BACKGROUND) in Part 2 vs 4-level (P0/P1/P2/P3) in Part 12
- **Envelope fields**: Part 2 has `target`, `checksum`, `category`; Part 12 has `partition_key`, `schema_ref`, `tenant_id`, `security`, `trace`
- **Event type registry**: Part 2 uses SCREAMING_SNAKE_CASE closed enum (118 types); Part 12 uses lowercase-dotted (104 types); Part 13 uses `governance.*` dotted (51 types)

**Part 14 position**: Each source remains authoritative within its domain. Part 14 does NOT select one as a universal replacement. The three registries (Part 2: 118, Part 12: 104, Part 13: 51) are NOT a single set described three ways — they are partially overlapping and partially disjoint. GAP-UNIVERSE.

**Status**: UNRESOLVED — requires ADR-level reconciliation.

### CONFLICT-05: Part 13 "Context Envelope" vs Part 14 Proposed Cross-Boundary Context Envelope

**Parties**: Part 13 §13.2 vs Part 14 proposed cross-boundary Context Envelope

Part 13 §13.2 "context envelope" refers to a governance operating context for governance components (G-00..G-15). The Part 14 proposed Context Envelope is a structured wrapper carrying tenant identity, authentication principal, correlation/causation IDs, feature flags, locale, trace flags, and deadlines across integration boundaries. These are materially different concepts with the same name.

**Part 14 position**: Do NOT merge them. They are distinct concepts. The cross-boundary Context Envelope remains PROPOSED (not established in Parts 1–13).

**Status**: UNRESOLVED — naming collision, not a single concept.

### CONFLICT-06: Part 12 Internal Event Naming Contradiction

**Parties**: Part 12 §22 (canonical dotted catalog) vs Part 12 own component docs/prose

Part 12 §22 defines events in lowercase-dotted format (`workflow.step.completed`, `delegation.task.dispatched`). Part 12's own component docs, prose, and `components.md` use verb-object PascalCase (`TaskDelegated`, `SessionRequested`, `WorkflowStarted`). The §22 catalog is canonical; the PascalCase forms are CONFLICT.

**Status**: UNRESOLVED — internal contradiction within Part 12.

### CONFLICT-07: Part 3 FROZEN PascalCase Lifecycle vs Part 2 SCREAMING_SNAKE_CASE

**Parties**: Part 3 §3.4 (FROZEN) vs Part 2 §2.3.1

Part 3 (FROZEN, authoritative SoT) uses PascalCase lifecycle names (`CoreComponentInitialized`, `ServiceHealthChanged`, `ServiceFailed`). Part 2 uses SCREAMING_SNAKE_CASE (`CORE_COMPONENT_INITIALIZED`, `SERVICE_DEGRADED`, `SERVICE_FAILED`). These represent the same concepts with different identifiers. Part 3 is explicitly "MUST NOT contradict Part 2" yet uses a different naming scheme.

**Status**: UNRESOLVED — FROZEN document contradicts Part 2.

---

## 6. Important Retractions and Corrections

These retractions safeguard continuity. Future agents MUST treat them as historical corrections, NOT as current architecture.

### Retraction Group A: RPC Architecture

- **AI-OS does not establish an RPC substrate.** Parts 1–13 establish EventBus as the sole communication substrate (Part 00 §0.4 Principle 1; Part 01 §1.7.4 CC-IR-001).
- **Interfaces do not establish RPC operations.** AI-OS has no RPC mechanism.
- **RPC is not an AI-OS communication mechanism.** Previous references to "RPC substrate", "RPC layer for sync operations", and "service providers exposing RPC operations" are RETRACTED.
- **Correlation IDs do NOT propagate through RPC calls.** Propagation is via EventBus only.
- **Synchronous integration is NOT "opt-in and requires explicit justification in ADRs."** Parts 1–13 do not specifically mandate this.

### Retraction Group B: Universal Plugin Registry

- **Universal Plugin Registry is NOT established.** Parts 1–13 establish per-domain registries (SkillRegistry, MemoryBackendRegistry, MCPTransportRegistry, etc.) and extension points. A standalone universal "plugin registry" is NOT established.

### Retraction Group C: Topology Manager

- **Topology Manager is NOT established.** Parts 1–13 use ServiceRegistry for provider registration. References to "topology manager" for provider registration are RETRACTED.

### Retraction Group D: Exactly-Once Transport Delivery

- **Exactly-once transport delivery is NOT established.** Exactly-once is NOT a transport-layer guarantee in Parts 0–13. It requires idempotent producer AND consumer (application-layer semantics). No event in Parts 0–13 is labeled "exactly-once delivery."

### Retraction Group E: Zero-Trust mTLS

- **mTLS must not automatically be described as zero-trust.** Parts 1–13 establish mTLS per Part 12.12 CM-015 but do NOT characterize it as zero-trust.

### Retraction Group F: Conformance → Circuit Breaker / Rollback

- **Conformance violations do NOT automatically imply circuit breaker activation.** Circuit breakers are triggered by operational failures (RI-028), not by conformance checks.
- **Conformance violations do NOT automatically imply rollback.** Rollback (WI-011) is an operational recovery mechanism, not an automated conformance response.

### Retraction Group G: Four Compatibility Modes

- **Four compatibility modes (Structural, Behavioral, Temporal, Semantic) are NOT source-established.** Parts 1–13 use conformance levels and backward/forward schema compatibility, not "modes."

### Retraction Group H: Three Versioning Axes

- **Three versioning axes are a Part 14 derivation, not a source-defined universal platform model.** The axes are derived from combining Parts 0, 2, and 12. They are PROPOSED as an integration analysis tool, not source-established architecture.

### Retraction Group I: Context Envelope Scope

- **Context Envelope is NOT an established universal cross-boundary envelope.** The structured Context Envelope (as a single envelope object wrapping every cross-boundary call) is PROPOSED, not established in Parts 1–13. Part 13 §13.2 "context envelope" refers to governance context — a different concept.

### Retraction Group J: ServiceRegistration Fields

- **"Capacity" and "health endpoint" are NOT ServiceRegistration fields.** ServiceRegistration includes `capabilities`, `critical`, `dependsOn`, `tags`, `metadata` but does NOT explicitly list capacity or health endpoint fields.

### Retraction Group K: Interface Negotiation

- **Interfaces are NOT "negotiable at connection time."** Part 12 §12.3 negotiation is agent-level, not connection-time interface negotiation.

---

## 7. Status Taxonomy

Part 14 uses the following status vocabulary. Do NOT create a new status vocabulary unless an existing Part 14 document already establishes it.

| Status | Meaning |
|--------|---------|
| **EXISTING** | Verbatim or field-for-field present in a source Part 0–13 document or accepted ADR, with explicit source citation. |
| **DERIVED** | Logically implied by one or more EXISTING statements. The inference path and source anchors MUST be stated. |
| **ASSUMPTION** | Adopted for continuity or scoping clarity. Not explicitly stated in source Parts. MUST be flagged, reviewed before implementation, and resolved to EXISTING, DERIVED, or GAP. |
| **UNSPECIFIED** | Source Parts and accepted ADRs are silent on this detail. Part 14 MUST NOT invent a value, schema, or rule to fill the silence. |
| **GAP** | Source Parts partially define a concern but leave required fields, interfaces, or behavior unspecified for integration use. Requires a PROPOSED resolution or explicit deferral. |
| **PROPOSED** | A recommendation for Part 14 chapter authors to resolve a GAP or UNSPECIFIED item. MUST NOT be stated as architecture fact or binding requirement. |
| **FUTURE** | Explicitly deferred in source Parts to a named future horizon (e.g., v2.0). MUST NOT be introduced as v1.0 behavior. |
| **CONFLICT** | Two or more authoritative sources disagree on this point. Both sources MUST be preserved. Part 14 MUST NOT silently resolve, override, or paper over the disagreement. Escalate to ARB. |

**RETRACTED / CORRECTED** is used only for historical documentation of corrections (see Section 6). It is NOT a current architectural status.

---

## 8. Part 14 Document Map

The following documents exist in Part 14. Their purpose, authority level, and content status are recorded here.

### 8.1 Foundational / Context Documents

| Document | Purpose | Authority Level | Source-Derived | Analytical | Contracts/Events/ADRs |
|----------|---------|-----------------|----------------|------------|----------------------|
| **context.md** (~827 lines) | Integration context, status classification policy, source-of-truth rules, layers/boundaries, component taxonomy, control/data plane, interaction patterns, schema ownership, dependency direction, runtime boundaries, configuration propagation, failure boundaries, versioning, security, observability, inherited constraints, forward contracts, gaps | Reference — defines Part 14's own authority model and status taxonomy | No — it IS the Part 14 authority model document | Partial — identifies gaps and conflicts | Events, components, ADRs, contracts |
| **glossary.md** (~925 lines) | Term definitions for Part 14 integration documentation; conflict log; retraction log; cross-reference index | Reference — terminology only | No — defines Part 14's terminology usage | Partial | Terms, conflicts, retractions |
| **README.md** (~331 lines) | Part 14 purpose, scope, status taxonomy, principles, document map, source-of-truth rules, lifecycle, AI agent guidance | Reference — Part 14 scope and principles | Derived from Part 00 and Parts 1–13 | No | Scope, principles |

### 8.2 Inventory / Analysis Documents

| Document | Purpose | Authority Level | Source-Derived | Analytical | Contracts/Events/ADRs |
|----------|---------|-----------------|----------------|------------|----------------------|
| **adrs.md** (~1104 lines) | ADR index and integration impact classification for all 41 ADRs (16 Core Active + 10 Part 12 Accepted + 10 Part 13 Draft + 5 Part 14 Integration Impact Records); conflict register; gap register; traceability matrix; overlap analysis; normative language index | Integration index — authoritative for Part 14 integration impact; source ADRs are authoritative for their own decisions | Yes | Yes — conflict register, gap register, overlap analysis | ADRs, conflicts, gaps, normative statements |
| **events.md** (~612 lines) | Event catalog: 273 EXISTING event types across 3 authoritative registries (Part 2: 118, Part 12: 104, Part 13: 51); envelope specifications; delivery semantics; ordering; idempotency; retry; failure handling; GAPs; CONFLICTs | Catalog — inventories source events; does not invent | Yes | Yes — GAPs, CONFLICTs, reconciliation map | Events (273 EXISTING), GAPs, CONFLICTs |
| **interfaces.md** (~substantial) | Integration interface inventory: INT-CORE-CMP-001, INT-SVC-REG-001, INT-EVT-BUS-001, INT-CFS-BRIDGE-001, INT-CONFIG-READ-001, INT-KERNEL-ACC-001, INT-GOV-EVENT-001, INT-SEC-AUTH-001, INT-WF-CTRL-001, etc. | Inventory — catalogs source interfaces; many fields marked NOT YET DEFINED | Yes | Yes — identifies UNSPECIFIED fields | Interfaces, schemas, events |
| **schemas.md** (~substantial) | Integration schema catalog: EVENT-ENVELOPE-v1, domain schemas, configuration schemas, metadata/context schemas | Integration reference — derived from Parts 0–13 | Yes | Yes — GAPs, CONFLICTs | Schemas, GAPs, CONFLICTs |
| **components.md** (~substantial) | Integration-oriented component inventory: Core Components, Core Managers, Services, Facade Services, Governance components, External systems, Infrastructure dependencies | Inventory — catalogs source components; does not create | Yes | Yes — identifies CONFLICTs | Components, interfaces, events, ADRs |
| **integrations.md** (~substantial) | Integration catalog: 18 attributes per integration, classification categories, integration principles, gap analysis | Integration reference — derived from Parts 1–13 | Yes | Yes — gap analysis, classification | Integrations (INT-NNN), principles |
| **dependency-map.md** (~substantial) | Dependency analysis: component-to-component, component-to-interface, interface-to-schema, component-to-event, external-system, infrastructure, configuration, ADR dependencies; architectural risk analysis with findings; ASCII dependency diagram | Analysis artifact — inventories source dependencies; identifies risks | Yes | Yes — risk findings, gap analysis | Dependencies, findings, risks, ADRs |

### 8.3 Empty / Incomplete Part 14 Chapter Files

The following Part 14 chapter files exist but are currently **EMPTY or INCOMPLETE**. Do NOT pretend they contain architecture.

| File | Status | Notes |
|------|--------|-------|
| **14.1-Architecture-Overview.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.2-Platform-Integration-Architecture.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.3-API-and-Interface-Architecture.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.4-Plugin-and-Extension-Architecture.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.5-External-System-Integration.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.6-Model-and-Provider-Integration.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.7-Storage-and-Data-Integration.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.8-Observability-and-Operations-Integration.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.9-Deployment-and-Infrastructure-Integration.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.10-Integration-Security.md** | POPULATED | Security integration chapter documenting SecurityManager (M8), INT-SEC-AUTH-001, event/governance/external-system security, trust boundaries, extension security, CONFLICT-03, GAP-SEC, UNRES-05/UNRES-08, GOV-17; includes Final Security Audit checklist |
| **14.11-Integration-Schemas-and-Contracts.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.12-Integration-Invariants-and-Conformance.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |
| **14.13-Cross-References-and-ADR-Summary.md** | EMPTY/INCOMPLETE | Listed in README document map; no verified content |

**Note**: README.md, context.md, glossary.md, adrs.md, events.md, interfaces.md, schemas.md, components.md, integrations.md, dependency-map.md, and review-checklist.md are the **actual populated Part 14 documents**. The 14.x chapter files are placeholders, **with the exception of 14.10-Integration-Security.md** which is now populated (see §8.3).

---

## 9. Key Gaps Requiring Future Attention

These are the most important gaps identified across Part 14 documents. They MUST be addressed before Part 14 chapters are treated as authoritative.

| Gap ID | Description | Source Silence | Required Action |
|--------|-------------|----------------|----------------|
| **GAP-UNIVERSE** | Three partially-disjoint event registries (Part 2: 118, Part 12: 104, Part 13: 51) are NOT a single reconciled set | No unified event registry in Parts 0–13 | ADR-level reconciliation decision |
| **GAP-ENV** | Two incompatible envelope specifications: Part 2 §2.2.1 (PascalCase, UUIDv7, 5-level priority) vs Part 12 §4 (snake_case, ULID, 4-level priority, `partition_key`/`tenant_id`/`security`) | No unified envelope definition | ADR-level reconciliation or explicit dual-envelope policy |
| **GAP-01** | StateManager integration API for external readers/writers | Part 00 §0.3.1 names StateManager; no public integration interface in inspected Parts 0–1; canonical Core Manager identity obscured by CONFLICT-01 | Document in Part 14 after CONFLICT-01 resolution; or defer to relevant Core Manager specification |
| **GAP-02** | Configuration schema for integration components | Part 00 §0.4 Principle 10 specifies four-layer merge; no integration-specific schema documented | Part 14 MUST define or explicitly defer |
| **GAP-03** | Retry policy semantics for integration adapters | Part 01 §1.12.1 specifies kernel-internal retry; integration adapter retry not addressed | Part 14 MUST specify or reference kernel retry |
| **GAP-04** | Integration failure event taxonomy | Kernel defines ComponentDegraded/ComponentFailed/CoreManagerFailed/KernelFatalError; integration-specific failure events not defined | Part 14 MUST define via EventType extension |
| **GAP-05** | Observability metric names/dimensions for integration components | Part 00 §0.4 Principle 12 requires observability; specific integration metric names not defined in inspected Parts 0–1 | Part 14 MUST define or reference Part 02/Part 09 |
| **GAP-06** | AuthN/AuthZ model for v1.0 integrations | Part 00 §0.2.2 defers to v2.0; Part 13 governance may provide overlay; relationship not clarified | ARB decision required |
| **GAP-07** | Distributed tracing fields on events | `trace_id`/`span_id`/`parent_span_id` referenced in current context but not confirmed in inspected Parts 0–1 | Verify in Part 02; Part 14 MUST NOT introduce without source |
| **GAP-08** | External runtime isolation mechanism | Part 00 §0.2.2 states single-process v1.0; external adapter runtime not specified | Part 14 MUST define or label FUTURE |
| **GAP-DLQ** | Single DLQ vs per-family DLQ topics | Part 2 models one DLQ; Part 12 §19 names 8 per-family DLQ topics; Part 13 adds `governance.dlq` | Reconcile single-vs-many model |
| **GAP-RETRY** | Two retry models | Part 12 §18 (5/10 attempts, 200ms→64s) vs Part 2 §2.4 (queue-based, per-subscription retryPolicy, no fixed attempt count) | Reconcile |
| **GAP-DEDUP** | Dedup window source conflict | Part 12 §30 (24h `event_id` dedup window) vs Part 2 §2.4.7 (`eventId`/`idempotencyKey` dedup, no stated TTL) | Reconcile |
| **GAP-SEC** | Signing/ACL absent from Part 2 base contract | Part 2 `Event` has no `security.*` block; signing exists only in Part 12 envelope | Define Part 2 security posture or accept as Part 12-only |
| **GAP-EXT** | Closed enum vs "custom events" extension point | Part 2 INV-ET-003 prohibits late EventType registration; ADR-013 lists "custom events" as permitted extension point | Reconcile via ADR |
| **GAP-RATIFICATION** | `governance.*` ESC ratification pending | Part 13 §5 registers `governance` as 12th namespace "subject to ESC ratification per Part 12 §24/§25" | Wait for ratification; treat 51 types as ratified-candidate |
| **GAP-XREF** | `schemas.md` "Related Events" reference non-canonical dotted names | 18 dotted event names referenced in Part 14 schemas.md do not appear in Part 12 §22 catalog | Either ratify into Part 12 §22 or correct schemas.md references |
| **GAP-P14-ENV** | Part 14 `schemas.md` §11 envelope errors | schemas.md §11 incorrectly claims Part 12 §4 envelope "does not include `tenant_id`" and understates Part 12 event count as "64+" (actual: 104) | Correct schemas.md §11; do not propagate errors |
| **GAP-14-INTEGRATION-ANALYSIS** | Original per-component integration analysis lost | Original Part 14 adrs.md v1.0 contained per-component mapping (ADR × integration impact by component); lost during truncation | Reconstruct or explicitly defer |
| **GAP-ADRDATES** | Core ADR dates unspecified | ADR-001 through ADR-016 have no explicit dates in source documents | Supply dates via ARB or ADR authors |

---

## 10. Machine-Agent Safety Rules

Future AI agents working with Part 14 MUST follow these rules:

1. **Never treat MEMORY.md as higher authority than source Parts.** Source Parts remain authoritative for their own domains.

2. **Never treat a DERIVED claim as EXISTING.** DERIVED claims require an inference path. If the inference path is not documented, the claim is not valid.

3. **Never treat PROPOSED as implemented.** PROPOSED items are recommendations for Part 14 chapter authors. They are NOT current architecture.

4. **Never treat UNSPECIFIED as supported.** If a source Part is silent on a detail, Part 14 MUST NOT invent a value.

5. **Never silently resolve CONFLICT.** When authoritative sources disagree, record the CONFLICT, preserve both sources with their original positions, and escalate to ARB.

6. **Never infer implementation from terminology alone.** The existence of a term in documentation does not prove the corresponding mechanism exists in the implemented architecture.

7. **Always follow source authority references.** Every significant claim must cite its source Part, source document, and (where known) section.

8. **Treat RETRACTED claims as historical corrections only.** RETRACTED claims document what was previously stated incorrectly. They MUST NOT be interpreted as current architecture.

9. **Never invent architecture.** This includes: no new components, no new APIs, no new events, no new schemas, no new protocols, no new security mechanisms, no new guarantees, no new interfaces.

10. **Respect Part 14's derived nature.** Part 14 is integration documentation. It does not redesign, extend, or redefine Parts 0–13.

---

## 11. Important Event Facts

### 11.1 Event Registries

Parts 0–13 contain **three distinct, authoritative event registries** that are NOT a single set described three ways:

| Registry | Authority | Count | Naming Convention |
|----------|-----------|-------|-------------------|
| **Part 2 EventType enum** | Part 2 §2.3.1 | 118 types (spec prose incorrectly says 97 — GAP-SPEC-COUNT) | SCREAMING_SNAKE_CASE |
| **Part 12 dotted events** | Part 12 `events.md` §22 | 104 types | lowercase-dotted |
| **Part 13 governance events** | Part 13 `governance-events.md` §15 | 51 types (ratified-candidate, pending ESC ratification) | `governance.*` dotted |

**Total distinct event types across registries: ~273** (with conceptual overlaps between registries).

### 11.2 Envelope Specifications

There are **two coexisting envelope specifications** (GAP-ENV):

- **Part 2 §2.2.1**: `eventId` (UUIDv7), `eventType`, `eventVersion` (SemVer), `timestamp`, `timestampMonotonic`, `correlationId`, `causationId`, `source`, `target`, `priority` (5-level), `category`, `payload`, `checksum`
- **Part 12 §4 / Part 14 schemas.md §1.1**: `event_id` (ULID), `event_type`, `event_version` (integer), `produced_at`, `produced_by`, `partition_key`, `correlation_id`, `causation_id`, `tenant_id`, `priority` (P0–P3), `trace`, `schema_ref`, `payload`, `metadata`, `security`

These are **NOT merged**. Each is authoritative within its domain. The remaining disagreement is an unresolved GAP.

### 11.3 Delivery Semantics

- **At-least-once is the default** for all three registries.
- **Exactly-once is NOT a transport-layer guarantee** anywhere in Parts 0–13. It is achieved only at the application layer via idempotent handlers.
- **No event in Parts 0–13 is described as "exactly-once delivery."**

### 11.4 Naming Conflicts

Five event naming schemes exist across authoritative sources (CONFLICT, not normalized):

| Scheme | Example | Source |
|--------|---------|--------|
| A. SCREAMING_SNAKE_CASE | `MEMORY_STORED`, `WORKFLOW_STARTED` | Part 2 §2.3.1 |
| B. lowercase-dotted | `workflow.step.completed` | Part 12 §22, Part 13 §15 |
| C. PascalCase + Event suffix | `KernelLifecycleEvent`, `StateTransitionCommittedEvent` | Part 4 §4.3.10/§4.4.9 |
| D. verb-object PascalCase (no suffix) | `TaskDelegated`, `WorkflowStarted` | Part 12 component docs (contradicts Part 12 §22) |
| E. PascalCase no-suffix lifecycle (FROZEN) | `CoreComponentInitialized`, `ServiceHealthChanged` | Part 3 §3.4 (FROZEN — contradicts Part 2) |

---

## 12. Traceability Rules

### 12.1 Source Citation Requirement

Every important claim in Part 14 MUST preserve traceability:

- **Source Part**: Which Part the claim originates from
- **Source document/section**: Where known (do NOT fabricate exact line numbers or section numbers)
- **Status**: EXISTING, DERIVED, UNSPECIFIED, GAP, PROPOSED, CONFLICT, or FUTURE

### 12.2 DERIVED Claim Requirement

Every DERIVED claim MUST include:
- The EXISTING source(s)
- The logical inference step
- The resulting integration implication

Hidden or implicit derivation is prohibited.

### 12.3 CONFLICT Requirement

Every CONFLICT entry MUST name:
- The conflicting parties (specific Parts/sections)
- The specific point of disagreement
- Part 14's interim position (if any)
- The required ARB action

---

## 13. Quick-Reference: What Must NOT Be Inferred

The following are common inferences that MUST NOT be made by future agents:

| Do NOT Infer | Why |
|-------------|-----|
| That AI-OS uses RPC | No RPC mechanism exists in Parts 0–13 |
| That a Universal Plugin Registry exists | Per-domain registries exist; no universal registry is established |
| That Topology Manager exists | ServiceRegistry is used; no Topology Manager is established |
| That exactly-once transport delivery exists | Exactly-once is application-layer only |
| That mTLS implies zero-trust | mTLS is established but NOT characterized as zero-trust |
| That conformance violations trigger circuit breakers | Circuit breakers respond to operational failures, not conformance checks |
| That conformance violations trigger rollback | Rollback is operational, not automated conformance response |
| That four compatibility modes exist | Parts 0–13 use conformance levels and backward/forward compatibility |
| That three versioning axes are source-established | They are a Part 14 derivation, not a source-defined universal model |
| That a universal Context Envelope exists | The structured Context Envelope is PROPOSED, not established |
| That "97 canonical EventTypes" is correct | Part 2 §2.3.1 enumerates 118 types; "97" is a spec error |
| That Part 14 chapter files contain architecture | 14.1 through 14.13 are EMPTY/INCOMPLETE |
| That Draft ADRs are binding | P13-ADR-001 through P13-ADR-010 are Draft only |
| That Part 14 schemas.md §11 is correct | It contains two errors (tenant_id claim and event count); use authoritative Part 12 §4 instead |

---

## 14. Important Part 14 Corrections Already Applied

These corrections were made during Part 14's production-quality passes. Future agents must not re-introduce the errors.

| What Was Wrong | Correction Applied | Where |
|---------------|-------------------|-------|
| Core ADR status labeled "Accepted" | Corrected to "Active" per source documents | adrs.md §1.1 |
| Part 14 own ADRs labeled "Accepted" | Corrected to "Integration Impact Record" | adrs.md §1.4 |
| P14-ADR-003 linked to Schema Registry | Removed — ADR-013 (Extension Points) does not involve Schema Registry | adrs.md §2.4 |
| "seccomp-bpf" stated as architecture | Corrected to "Part 14 interpretation only; ADR-013 specifies sandboxing without naming mechanism" | adrs.md, glossary.md |
| Event count stated as "97" | Corrected to 118 per Part 2 §2.3.1 enumeration | events.md, interfaces.md |
| Part 12 event count stated as "64+" | Corrected to 104 per Part 12 §22 | events.md, schemas.md |
| schemas.md §11 claimed Part 12 envelope lacks `tenant_id` | Corrected — `tenant_id` IS present in Part 12 §4 | events.md §3.1, schemas.md |
| schemas.md §11 claimed `actor_kind` lacks `governance` | Corrected — `actor_kind` enumerates `agent\|council\|workflow\|runtime\|scheduler\|tool\|system` (no governance, which is correct) | events.md §3.1 |
| Core Component C4 named inconsistently | Part 14 uses Part 01 §1.7.1: `LifecycleManager` | context.md, components.md, interfaces.md, dependency-map.md |
| `StructuredLogger` listed as Core Component C4 | Flagged as CONFLICT; Part 14 MUST NOT classify as Core Component until resolved | context.md §3.1, interfaces.md §2.1, dependency-map.md CC-04 |

---

## 15. Unresolved Issues Requiring ARB Attention

The following items require Architecture Review Board (ARB) resolution before Part 14 can be considered authoritative:

| Issue | Type | ARB Action Required |
|-------|------|---------------------|
| Core Component naming (Part 00 vs Part 01) | CONFLICT-01 | Resolve which source is authoritative for Core Component enumeration |
| StructuredLogger classification | CONFLICT-02 | Determine whether StructuredLogger is a Core Component, a logging substrate, or something else |
| AuthN/AuthZ scope for v1.0 | CONFLICT-03 | Clarify whether Part 13 governance security is optional overlay or mandatory v1.0 requirement |
| Event envelope unification | GAP-UNIVERSE / GAP-ENV | Decide whether to unify or maintain dual envelopes |
| Event registry unification | GAP-UNIVERSE | Decide whether to create a unified registry or maintain three distinct registries |
| Part 3 FROZEN vs Part 2 naming | CONFLICT-07 | Resolve PascalCase vs SCREAMING_SNAKE_CASE for lifecycle events |
| Part 12 internal naming contradiction | CONFLICT-06 | Resolve dotted §22 vs PascalCase component docs |
| Closed enum vs custom events extension | GAP-EXT | Reconcile Part 2 INV-ET-003 with ADR-013 |
| Retry model reconciliation | GAP-RETRY | Choose between Part 2 and Part 12 retry models or define both |
| DLQ model reconciliation | GAP-DLQ | Choose between single DLQ and per-family DLQ topics |
| Dedup window reconciliation | GAP-DEDUP | Reconcile 24h window (Part 12) vs no-TTL (Part 2) |
| `governance.*` ESC ratification | GAP-RATIFICATION | Complete ESC ratification process for governance namespace |
| schemas.md §11 errors | GAP-P14-ENV | Correct `tenant_id` claim and event count |
| schemas.md "Related Events" dangling references | GAP-XREF | Either ratify 18 missing event types into Part 12 §22 or correct schemas.md |

---

## 16. Maintenance Rules

MEMORY.md MUST be updated when:

1. Any Part 14 chapter (14.1–14.13) resolves a GAP or CONFLICT
2. Any source Part 0–13 issues an update affecting Part 14
3. An ADR modifies an integration-relevant decision
4. ARB resolves a CONFLICT listed in this document
5. A new Part 14 document is created or an existing one is populated
6. A retraction or correction is identified

All updates MUST preserve:
- Status classification labels
- Provenance citations
- Conflict preservation rules
- Authority hierarchy rules

---

## 17. Final Consistency Check

Before considering this document complete:

- [x] MEMORY.md does not invent architecture.
- [x] Authority hierarchy is explicit (Section 3).
- [x] Source Parts remain authoritative.
- [x] Part 14 remains derived.
- [x] Conflicts are preserved (Section 5).
- [x] Important retractions are preserved (Section 6).
- [x] Status terminology matches Part 14 (Section 7).
- [x] No nonexistent files are referenced (Section 8).
- [x] No unsupported source claims are added.
- [x] No obsolete RPC architecture remains (Section 6, Group A).
- [x] No universal Context Envelope is implied (Section 6, Group I).
- [x] No universal Plugin Registry is implied (Section 6, Group B).
- [x] No exactly-once transport guarantee is implied (Section 6, Group D).
- [x] No automatic conformance→rollback/circuit-breaker behavior is implied (Section 6, Group F).
- [x] Document remains concise enough to function as memory.

---

## 18. Document Metadata

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-MEMORY-PART14-v1.0.0 |
| **Classification** | Continuity / Memory Index |
| **Status** | ACTIVE |
| **Version** | 1.0.0 |
| **Date** | 2026-08-13 |
| **Distribution** | All AI-OS engineers, architects, reviewers, integration teams, Parts 14–15 implementers, future AI agents |
| **Maintained By** | Architecture Review Board (ARB) |
| **Supersedes** | None (initial version) |
| **Governing Principle** | SOURCE PARTS → AUTHORITATIVE ARCHITECTURE. PART 14 → DERIVED INTEGRATION DOCUMENTATION. ADR → AUTHORITATIVE ONLY WITHIN ITS EXPLICIT SCOPE. |

---

*This document is a continuity and memory artifact. It does not create new architectural requirements. It preserves the distinction between source-established architecture and Part 14-derived integration documentation. Where Parts 0–13 are silent, this document records the silence. Where Parts 0–13 conflict, this document records the conflict for the ARB without silently resolving it.*

*No new architectural authority or implementation behavior was invented in this document.*
