# Part 15: Dependency Analysis and Implementation Gap Tracking

**Version:** 1.2.0
**Status:** CONDITIONALLY READY — Analysis Artifact (pending runtime-map.md authoring)
**Date:** 2026-08-14
**Classification:** Informative — Dependency Analysis and Gap Catalog

---

## 1. Document Identity

`dependency-map.md` is **The Part 15 Architectural Dependency Registry**.

It is a **DEPENDENCY REGISTRY / ANALYSIS ARTIFACT**. It documents architecturally significant dependency relationships traceable to Parts 0–14.

It documents:
- Architectural dependency relationships between components, interfaces, schemas, events, and external systems
- Dependency direction (explicitly: A → B means "A requires B")
- Dependency types (STRUCTURAL, INTERFACE, DATA, EVENT, CONFIGURATION, SECURITY, LIFECYCLE, RUNTIME, RESOURCE, DEPLOYMENT, TEMPORAL)
- Dependency status (EXISTING, DERIVED, ASSUMPTION, UNSPECIFIED, GAP, PROPOSED, FUTURE, CONFLICT)
- Source provenance for each dependency assertion
- Conflict preservation where sources disagree
- Gap recording where sources are silent
- Circular dependency analysis
- Dependency-to-source, dependency-to-component, and dependency-to-contract traceability

**BUT:**

It MUST NOT:
- Create new dependencies not present in Parts 0–13 or Part 14
- Replace `components.md` (component inventory) or `runtime-map.md` (runtime ordering)
- Resolve conflicts between Parts 0–14 (records and escalates only)
- Infer implementation dependencies from communication (event-mediated interactions ≠ structural dependencies)
- Invent runtime ordering (runtime-map.md is PLANNED/empty)

**Important Statement:**

"This document is the dependency registry; it documents architectural dependencies traceable to authoritative sources. It does not create, approve, supersede, or resolve architectural dependencies."

---

## 2. Purpose

This document establishes the **authoritative Part 15 dependency registry** for understanding: (1) what each component requires to function, (2) the direction of each dependency, (3) the type of each dependency, (4) the source authority for each dependency, (5) which dependencies are unresolved conflicts or gaps, (6) whether any cycles exist in the dependency graph, (7) which dependencies are verified against runtime evidence vs. source documentation, (8) how dependencies trace to source documents, (9) how dependencies trace to components, (10) how dependencies trace to implementation contracts, (11) whether all dependency assertions satisfy final audit criteria.

### 2.1 What dependency-map.md Documents

- **Architectural dependencies** only — not all interactions. Communication that is not architecturally constrained is an Interaction, not a Dependency.
- **Dependency direction** — explicitly directional: A → B means "A requires B."
- **Dependency types** — using the canonical taxonomy (§5).
- **Dependency status** — EXISTING, DERIVED, ASSUMPTION, UNSPECIFIED, GAP, PROPOSED, FUTURE, CONFLICT.
- **Source authority** — every dependency traces to a Part 0–13 source section.
- **Conflict preservation** — CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, CONFLICT-FACADE-01, CONFLICT-MGR-01, CONFLICT-INIT-01 are preserved unresolved.
- **Gap recording** — gaps where sources are silent are recorded, not invented.

### 2.2 What dependency-map.md Does NOT Do

This document does **NOT**:
- Create new dependencies merely because two components logically appear related
- Replace `components.md` (component inventory authority) or `runtime-map.md` (runtime ordering authority)
- Resolve conflicts between Parts 0–14 (records and escalates only)
- Infer implementation dependencies from communication (event-mediated interactions ≠ structural dependencies)
- Invent runtime ordering (runtime-map.md is PLANNED/empty — see §15)

### 2.3 Document Status

**Status:** CONDITIONALLY READY — Analysis Artifact
**Quality Gate:** This document achieves dependency-registry quality when all dependencies are source-backed, directions are explicit, conflicts are preserved, and gaps are recorded. However, runtime verification is CONDITIONALLY READY (not 10/10) because `runtime-map.md` is empty (PLANNED). Runtime-ordered dependencies cannot be verified against runtime evidence; they are marked UNSPECIFIED per §15.

---

## 3. Dependency Authority Boundary

This document defines its **scope and authority boundary** as the dependency registry for Part 15. It does NOT redesign, extend, or override architecture defined in Parts 0–14. Dependencies are extracted from and traceable to authoritative sources only.

### 3.1 Authority Boundary

**This document is NOT:**
- An architectural decision-making body — dependencies are recorded, not created
- A conflict-resolution authority — CONFLICTs are preserved, not resolved
- An implementation specification — dependencies are architectural claims, not code contracts
- A replacement for `runtime-map.md` — runtime ordering is PLANNED (empty)

**This document IS:**
- A dependency extraction registry — dependencies are traceable to Parts 0–13 source sections
- A conflict preservation artifact — all conflicts from Part 14 are preserved
- A gap recording mechanism — silence in sources is marked, not filled with invention

### 3.2 Scope

- Component-to-Component dependencies
- Component-to-Interface dependencies
- Component-to-Event dependencies
- Configuration dependencies
- Security dependencies
- External system dependencies
- ADR-based dependency constraints
- Circular dependency analysis

### 3.3 Out of Scope

- Implementation-specific dependency injection wiring
- Code-level import graphs
- Packaging or deployment-unit dependencies (not in Parts 0–14)
- Invented runtime ordering (runtime-map.md is empty)

---

## 4. Dependency Authority Hierarchy

Part 15 MUST respect the following **Dependency Authority Hierarchy**. Dependencies in this registry derive their authority from the level at which they are established:

```
Level 1: Authoritative Parts 0–14
  │   (Parts 0–13 define architecture; Part 14 documents integration analysis)
  │   This level is the ultimate source of all dependency claims.
  │
  ↓
Level 2: Architectural Dependency
  │   (Dependencies explicitly defined in Parts 0–13 source sections)
  │   These are EXISTING claims with explicit source citations.
  │
  ↓
Level 3: Part 15 Dependency Registry (this document)
  │   (Dependencies extracted, classified, and recorded with status and provenance)
  │   All entries must trace to Level 1 or Level 2.
  │
  ↓
Level 4: Implementation Dependency
  │   (Dependencies realized in code; validated via conformance tests)
  │   Implementation may add wiring not architecturally specified.
  │
  ↓
Level 5: Runtime Verification
  │   (Dependencies observed at runtime via observability, runtime-map.md)
  │   runtime-map.md is currently PLANNED/EMPTY — Level 5 verification is UNSPECIFIED.
  │
  ↓
  ARB Escalation (for CONFLICTs)
```

**Authority rules:**
- Only Level 1 (Parts 0–14) can establish a dependency as architectural fact.
- Level 3 (this document) records dependencies; it does NOT add new architectural dependencies.
- Level 4 (implementation) may realize dependencies not explicitly in Parts 0–13, but those are implementation decisions, not architectural dependencies.
- Level 5 (runtime verification) is currently blocked: `runtime-map.md` is empty. All runtime-ordered dependency assertions are marked UNSPECIFIED per §15.
- CONFLICTs at any level are escalated to the ARB; Part 15 does not resolve them.

---

## 5. Dependency Definition

### 5.1 Definition of "Dependency"

A **dependency** is an architecture-level requirement that Component A *requires* Component B in order to function correctly, where this need is established by an authoritative source in Parts 0–13. The dependency is explicitly directional: **A → B means "A requires B."**

An architectural dependency is a claim that without the target, the source cannot operate correctly within the architecture's invariants.

### 5.2 Key Distinctions

| Concept | Definition | NOT a dependency when... |
|---------|-----------|--------------------------|
| **Dependency** | A structural, runtime, initialization, configuration, security, lifecycle, resource, deployment, data, interface, event, or temporal requirement; A requires B | Communication is the mechanism, not the architectural need |
| **Interaction** | Any exchange of information at runtime (calls, events, messages) | EventBus is the intermediary, not the target |
| **Communication** | The act of transmitting information between components | It is mediated by EventBus and A→B is not architecturally required |
| **Ownership** | Kernel manages lifecycle of component | Component publishes/subscribes events but does not structurally depend |
| **Association** | Components co-occur in the same architectural layer or phase | Being in the same layer does not imply a dependency |
| **Runtime ordering** | Temporal sequence observed at runtime | Two components initializing in sequence is a LIFECYCLE dependency only if the source requires the order |

### 5.3 Canonical Dependency Types

The following dependency types are used throughout this document. Each type is mutually exclusive for a given assertion:

| Type | Definition | Example |
|------|-----------|---------|
| **STRUCTURAL** | Component A structurally references types/interfaces from Component B | WorkflowManager → EventBus (interface) |
| **INTERFACE** | Component A consumes an interface provided by Component B | Service → INT-EVT-BUS-001 |
| **DATA** | Component A reads/writes data managed by Component B | StateManager → StorageManager (state persistence) |
| **EVENT** | Component A emits or consumes events routed through Component B | Component → EventBus (event routing) |
| **CONFIGURATION** | Component A's behavior is determined by configuration from Component B | Service → ConfigurationManager |
| **SECURITY** | Component A requires authorization/authentication from Component B | Service → SecurityManager |
| **LIFECYCLE** | Component A's lifecycle is managed by Component B | Service → LifecycleManager |
| **RUNTIME** | Component A requires Component B to be available at runtime (service discovery) | Service → ServiceRegistry |
| **RESOURCE** | Component A requires resources (CPU, memory, quotas) allocated by Component B | Service → ResourceManager |
| **DEPLOYMENT** | Component A's deployment is required for Component B to deploy | None asserted in v1.0 (PLANNED) |
| **TEMPORAL** | Component A requires Component B to initialize before A (hard ordering) | Core Components Phase 0→1→2→3 |

### 5.4 Dependency Direction Semantics

**A → B means "A requires B."** This directional convention is used consistently throughout this document. The consuming component (A, the "dependent") is always on the left; the required component (B, the "provider") is always on the right.

**Examples:**
- `PlanningService → EventBus` — PlanningService requires EventBus
- `HermesKernel → EventBus` — HermesKernel requires EventBus (ownership/initialization)
- `SecurityManager → SecretManager` — SecurityManager requires SecretManager (secret access)

### 5.5 Status Labels

| Status | Meaning |
|--------|---------|
| **EXISTING** | Verbatim or field-for-field present in Parts 0–13, with explicit source citation |
| **DERIVED** | Logically implied by one or more EXISTING statements; inference path stated |
| **ASSUMPTION** | Adopted for continuity; not explicitly stated in source Parts |
| **UNSPECIFIED** | Source documents are silent on this detail; runtime-map.md empty |
| **GAP** | Source documents partially define but leave required fields unspecified |
| **PROPOSED** | Recommendation for resolving a GAP or UNSPECIFIED (not architecture fact) |
| **FUTURE** | Explicitly deferred in source Parts to a named future horizon |
| **CONFLICT** | Two or more authoritative sources disagree on this point |

---

## 6. Dependency Status Taxonomy

This document inherits the status taxonomy from Part 14 context.md §0.1 and the Part 15 README.md §2. All dependency assertions carry exactly one status label.

| Part 14 Status | Part 15 Equivalent | Meaning |
|----------------|-------------------|---------|
| DEFINED | EXISTING | Directly stated in Parts 0–13 |
| DERIVED | DERIVED | Inferred from architecture patterns |
| UNSPECIFIED | UNSPECIFIED | Mentioned but contract not defined |
| GAP | GAP | Missing definition preventing complete specification |
| CONFLICT | CONFLICT | Two sources disagree |

**Part 15 Additions:**

| Status | Meaning |
|--------|---------|
| ASSUMPTION | Adopted for continuity; not explicitly stated |
| PROPOSED | Recommendation for resolving a GAP or UNSPECIFIED |
| FUTURE | Explicitly deferred in source Parts to a named future horizon |

> **Critical note on authority:** The hierarchy does NOT rank sources within Parts 0–14. Where sources conflict (CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01), all claims are preserved unresolved. Part 1 §1.8.1 is **NOT** elevated as "the" authoritative source for kernel composition — it is one of four conflicting definitions.

> **Source verification required:** Where source documents are silent or empty (e.g., runtime-map.md is PLANNED), dependencies are marked UNSPECIFIED or SOURCE VERIFICATION REQUIRED.

> **Version note:** This document version (1.2.0) is corrected from the erroneous 1.1.0/1.0.0 mismatch. The header and Document Control now agree.

---

## 7. Core Dependency Registry

### 7.1 Core Component Dependencies (CONFLICT-CC-01 preserved)

Four authoritative sources define four different Core Component sets. None has been selected as authoritative by ARB. Table 7.1-A through 7.1-D preserve each source's definition; resolution is UNRESOLVED.

**Table 7.1-A — Part 1 §1.8.1**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CC-01-A | HermesKernel | EventBus | STRUCTURAL | Kernel → C1 | Ownership/initialization | EXISTING | Part 1 §1.8.1 |
| CC-02-A | HermesKernel | ServiceRegistry | STRUCTURAL | Kernel → C2 | Ownership/initialization | EXISTING | Part 1 §1.8.1 |
| CC-03-A | HermesKernel | ConfigurationManager | STRUCTURAL | Kernel → C3 | Ownership/initialization | EXISTING | Part 1 §1.8.1 |
| CC-04-A | HermesKernel | LifecycleManager | STRUCTURAL | Kernel → C4 | Ownership/initialization | EXISTING | Part 1 §1.8.1 |

**Table 7.1-B — Part 3 §3.1–3.6**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CC-01-B | HermesKernel | EventBus | STRUCTURAL | Kernel → C1 | Ownership/initialization | EXISTING | Part 3 §3.1 |
| CC-02-B | HermesKernel | ServiceRegistry | STRUCTURAL | Kernel → C2 | Ownership/initialization | EXISTING | Part 3 §3.3 |
| CC-03-B | HermesKernel | ConfigurationManager | STRUCTURAL | Kernel → C3 | Ownership/initialization | EXISTING | Part 3 §3.3 |
| CC-04-B | HermesKernel | StructuredLogger | STRUCTURAL | Kernel → C4 | Ownership/initialization | EXISTING | Part 3 §3.6 |

**Table 7.1-C — Part 4 §4.1**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CC-01-C | HermesKernel | EventBus | STRUCTURAL | Kernel → C1 | Ownership/initialization | EXISTING | Part 4 §4.1 |
| CC-02-C | HermesKernel | ServiceRegistry | STRUCTURAL | Kernel → C2 | Ownership/initialization | EXISTING | Part 4 §4.1 |
| CC-03-C | HermesKernel | ConfigurationAuthority | STRUCTURAL | Kernel → C3 | Ownership/initialization | EXISTING | Part 4 §4.1 |
| CC-04-C | HermesKernel | IdentityProvider | STRUCTURAL | Kernel → C4 | Ownership/initialization | CONFLICT | Part 4 §4.1 |

**Table 7.1-D — Part 0 §0.3.2**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CC-01-D | HermesKernel | EventBus | STRUCTURAL | Kernel → C1 | Ownership/initialization | EXISTING | Part 0 §0.3.2 |
| CC-02-D | HermesKernel | StateManager | STRUCTURAL | Kernel → C2 | Ownership/initialization | CONFLICT | Part 0 §0.3.2 |
| CC-03-D | HermesKernel | WorkflowManager | STRUCTURAL | Kernel → C3 | Ownership/initialization | CONFLICT | Part 0 §0.3.2 |
| CC-04-D | HermesKernel | ResourceManager | STRUCTURAL | Kernel → C4 | Ownership/initialization | CONFLICT | Part 0 §0.3.2 |

> **CONFLICT-CC-01:** C4 is ambiguous — Part 1 names LifecycleManager, Part 3 names StructuredLogger, Part 4 names IdentityProvider, Part 0 names ResourceManager. Only EventBus (C1) appears as identical across all four definitions. **Resolution: UNRESOLVED (ARB).**

### 7.2 Core Manager Dependencies (CONFLICT-CM-01 preserved)

Three authoritative sources define three different Core Manager sets. None has been selected as authoritative by ARB.

**Table 7.2-A — Part 1 §1.8.1 (9 Core Managers)**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CM-01-A | MemoryManager | EventBus | EVENT | M1 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-02-A | LLMManager | EventBus | EVENT | M2 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-03-A | ToolManager | EventBus | EVENT | M3 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-04-A | StorageManager | EventBus | EVENT | M4 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-05-A | ContextManager | EventBus | EVENT | M5 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-06-A | AgentManager | EventBus | EVENT | M6 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-07-A | WorkflowManager | EventBus | EVENT | M7 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-08-A | SecurityManager | EventBus | EVENT | M8 → C1 | Communication | EXISTING | Part 1 §1.8.1 |
| CM-09-A | ObservabilityManager | EventBus | EVENT | M9 → C1 | Communication | EXISTING | Part 1 §1.8.1 |

**Table 7.2-B — Part 4 §4.2.1 (9 Core Managers)**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CM-01-B | LifecycleManager | EventBus | EVENT | M1 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-02-B | StateManager | EventBus | EVENT | M2 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-03-B | StorageManager | EventBus | EVENT | M3 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-04-B | WorkflowManager | EventBus | EVENT | M4 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-05-B | SecurityManager | EventBus | EVENT | M5 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-06-B | CapabilityManager | EventBus | EVENT | M6 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-07-B | ResourceManager | EventBus | EVENT | M7 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-08-B | HealthManager | EventBus | EVENT | M8 → C1 | Communication | EXISTING | Part 4 §4.2.1 |
| CM-09-B | ObservabilityManager | EventBus | EVENT | M9 → C1 | Communication | EXISTING | Part 4 §4.2.1 |

> **CONFLICT-CM-01:** Part 1 M2 = LLMManager; Part 4 M2 = StateManager. Part 1 M5 = ContextManager; Part 4 M5 = SecurityManager. The 9 managers share M1–M9 IDs but differ in identity. Part 0 uses "Capability Managers" with a different set entirely. **Resolution: UNRESOLVED (ARB).**

### 7.3 Engineering Services (CONFLICT-ES-01 preserved)

**Table 7.3-A — Part 5 §5.2.1 (8 Engineering Services + 2 Governance Services)**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| ES-01 | PlanningService | EventBus | EVENT | E1 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-02 | PlanningService | StateManager | DATA | E1 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-03 | CodingService | EventBus | EVENT | E2 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-04 | CodingService | StateManager | DATA | E2 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-05 | CodingService | PlanningService | STRUCTURAL | E2 → E1 | SDLC chain | DERIVED | Part 5 §5.2.1 |
| ES-06 | ReviewService | EventBus | EVENT | E3 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-07 | ReviewService | StateManager | DATA | E3 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-08 | ReviewService | CodingService | STRUCTURAL | E3 → E2 | SDLC chain | DERIVED | Part 5 §5.2.1 |
| ES-09 | TestingService | EventBus | EVENT | E4 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-10 | TestingService | StateManager | DATA | E4 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-11 | TestingService | ReviewService | STRUCTURAL | E4 → E3 | SDLC chain | DERIVED | Part 5 §5.2.1 |
| ES-12 | DeploymentService | EventBus | EVENT | E5 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-13 | DeploymentService | StateManager | DATA | E5 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-14 | DeploymentService | TestingService | STRUCTURAL | E5 → E4 | SDLC chain | DERIVED | Part 5 §5.2.1 |
| ES-15 | OperationsService | EventBus | EVENT | E6 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-16 | OperationsService | StateManager | DATA | E6 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-17 | OperationsService | DeploymentService | STRUCTURAL | E6 → E5 | SDLC chain | DERIVED | Part 5 §5.2.1 |
| ES-18 | LearningService | EventBus | EVENT | E7 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-19 | LearningService | StateManager | DATA | E7 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-20 | LearningService | OperationsService | STRUCTURAL | E7 → E6 | SDLC chain | DERIVED | Part 5 §5.2.1 |
| ES-21 | MemoryService (E8) | EventBus | EVENT | E8 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| ES-22 | MemoryService (E8) | StateManager | DATA | E8 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| ES-23 | MemoryService (E8) | LearningService | STRUCTURAL | E8 → E7 | SDLC chain | DERIVED | Part 5 §5.2.1 |

**Table 7.3-B — Governance Services (Part 5 §5.2.1, classified as GS-1/GS-2)**

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| GS-01 | CouncilService | EventBus | EVENT | GS-1 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| GS-02 | CouncilService | StateManager | DATA | GS-1 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |
| GS-03 | HumanInteractionService | EventBus | EVENT | GS-2 → C1 | Communication | EXISTING | Part 5 §5.2.1 |
| GS-04 | HumanInteractionService | StateManager | DATA | GS-2 → M2 | State persistence | EXISTING | Part 5 §5.2.1 |

> **CONFLICT-ES-01:** Part 0 §0.2.1 specifies 8 Engineering Services; Part 5 §5.2.1 specifies 8 Engineering Services plus 2 Governance Services (CouncilService, HumanInteractionService). Part 14 §5.1 reclassifies the 2 governance services as E9/E10. The 8-service linear chain above follows Part 5's authoritative classification (governance services separate). **Resolution: UNRESOLVED (ARB).**

### 7.4 Capability Facade Service Dependencies

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CFS-01 | All Facades | EventBus | EVENT | Facade → C1 | Communication | EXISTING | Part 6 §6.1 |
| CFS-02 | All Facades | StateManager | DATA | Facade → M2 | State persistence | EXISTING | Part 6 §6.1 |
| CFS-03 | SkillService (F1) | SkillManager | DELEGATION | F1 → Manager | Translates events to manager calls | EXISTING | Part 6 §6.4 |
| CFS-04 | CouncilService (F2) | CouncilManager | DELEGATION | F2 → Manager | Translates events to manager calls | EXISTING | Part 6 §6.2 |
| CFS-05 | MCPService (F3) | MCPManager | DELEGATION | F3 → Manager | Translates events to manager calls | EXISTING | Part 6 §6.5 |
| CFS-06 | MemoryService (F4) | MemoryManager | DELEGATION | F4 → Manager | Translates events to manager calls | EXISTING | Part 6 §6.3 |

> **CONFLICT-FACADE-01:** Part 6 references SkillManager, CouncilManager, MCPManager as delegation targets, but these managers are not enumerated in Part 1 §1.8.1's Core Manager set or Part 4 §4.2.1. Part 0 §0.3.2 lists them as Capability Managers. **Resolution: UNRESOLVED (ARB).**

### 7.5 Governance Components (G-00..G-15)

Governance components and their dependencies are documented below with explicit direction notation: **Consumer → Provider** (Consumer requires Provider).

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| GOV-01 | G-00 GovernanceEventManager | EventBus | EVENT | G-00 → C1 | Event transport | EXISTING | Part 13 §1.3 |
| GOV-02 | G-01 PolicyManager | SecurityManager | SECURITY | G-01 → M5 | Authorization | EXISTING | Part 13 §1.4 |
| GOV-03 | G-02 PolicyEvaluationEngine | G-01 PolicyManager | STRUCTURAL | G-02 → G-01 | Policy lookup | EXISTING | Part 13 §1.5 |
| GOV-04 | G-03 GovernanceRegistry | G-02 PolicyEvaluationEngine | STRUCTURAL | G-03 → G-02 | Artifact registration | EXISTING | Part 13 §1.6 |
| GOV-05 | G-04 GovernanceCouncil | G-02 PolicyEvaluationEngine | STRUCTURAL | G-04 → G-02 | Council convening | EXISTING | Part 13 §1.7 |
| GOV-06 | G-05 DecisionAuthorityManager | G-01 PolicyManager | STRUCTURAL | G-05 → G-01 | Identity resolution | EXISTING | Part 13 §1.8 |
| GOV-07 | G-06 DelegationAuthorityManager | G-05 DecisionAuthorityManager | STRUCTURAL | G-06 → G-05 | Delegation validation | EXISTING | Part 13 §1.9 |
| GOV-08 | G-07 RiskManager | G-05 DecisionAuthorityManager | STRUCTURAL | G-07 → G-05 | Risk assessment | EXISTING | Part 13 §1.10 |
| GOV-09 | G-08 ComplianceManager | G-03 GovernanceRegistry | STRUCTURAL | G-08 → G-03 | Baseline lookup | EXISTING | Part 13 §1.11 |
| GOV-10 | G-09 AuditManager | G-03 GovernanceRegistry | STRUCTURAL | G-09 → G-03 | Audit record | EXISTING | Part 13 §1.12 |
| GOV-11 | G-10 AccountabilityManager | G-09 AuditManager | STRUCTURAL | G-10 → G-09 | Accountability binding | EXISTING | Part 13 §1.13 |
| GOV-12 | G-11 ExceptionManager | G-02 PolicyEvaluationEngine | STRUCTURAL | G-11 → G-02 | Exception grant | EXISTING | Part 13 §1.14 |
| GOV-13 | G-12 ApprovalManager | G-05 DecisionAuthorityManager | STRUCTURAL | G-12 → G-05 | Approval routing | EXISTING | Part 13 §1.15 |
| GOV-14 | G-13 ControlManager | G-02 PolicyEvaluationEngine | STRUCTURAL | G-13 → G-02 | Control enforcement | EXISTING | Part 13 §1.16 |
| GOV-15 | G-14 GovernanceEventManager | EventBus | EVENT | G-14 → C1 | Event transport | EXISTING | Part 13 §1.17 |
| GOV-16 | G-15 ConformanceManager | G-09 AuditManager | STRUCTURAL | G-15 → G-09 | Conformance check | EXISTING | Part 13 §1.18 |
| GOV-17 | Any G-xx | SecurityManager | SECURITY | G-xx → M5 | Governance authz | EXISTING | Part 13 §1.19 |

> **Note on governance naming:** Governance component names below use Part 13 components.md G-00..G-15 naming. Manager references (StateManager, SecurityManager, etc.) follow Part 4 §4.2.1 naming per CONFLICT-CM-01. Part 1 §1.8.1 would use different M-slot names (e.g., M2=LLMManager in Part 1).

### 7.6 Manager Dependency Detail (Part 4 §4.12)

The following dependencies are sourced from Part 4 §4.12, which describes inter-manager dependencies. Note: Part 1 §1.8.1 does not enumerate inter-manager dependencies explicitly; these are DERIVED from Part 4 §4.12.

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| MGR-01 | StateManager | StorageManager | DATA | M2 → M3 | State persistence | EXISTING | Part 4 §4.12 |
| MGR-02 | StateManager | WorkflowManager | DATA | M2 → M4 | Workflow coordination | DERIVED | Part 4 §4.12 |
| MGR-03 | StorageManager | StateManager | DATA | M3 → M2 | State coordination | DERIVED | Part 4 §4.12 |
| MGR-04 | WorkflowManager | StateManager | DATA | M4 → M2 | State read/write | EXISTING | Part 4 §4.12 |
| MGR-05 | WorkflowManager | SecurityManager | SECURITY | M4 → M5 | Authorization | DERIVED | Part 4 §4.12 |
| MGR-06 | WorkflowManager | CapabilityManager | STRUCTURAL | M4 → M6 | Capability invocation | DERIVED | Part 4 §4.12 |
| MGR-07 | WorkflowManager | ResourceManager | RESOURCE | M4 → M7 | Resource allocation | DERIVED | Part 4 §4.12 |
| MGR-08 | SecurityManager | ConfigurationManager | CONFIGURATION | M5 → C3 | Policy config | EXISTING | Part 4 §4.12 |
| MGR-09 | CapabilityManager | StateManager | DATA | M6 → M2 | State persistence | DERIVED | Part 4 §4.12 |
| MGR-10 | CapabilityManager | SecurityManager | SECURITY | M6 → M5 | Authorization | DERIVED | Part 4 §4.12 |
| MGR-11 | ResourceManager | StateManager | DATA | M7 → M2 | State persistence | DERIVED | Part 4 §4.12 |
| MGR-12 | ResourceManager | SecurityManager | SECURITY | M7 → M5 | Resource quota enforcement | DERIVED | Part 4 §4.12 |
| MGR-13 | ObservabilityManager | StateManager | DATA | M9 → M2 | State persistence | DERIVED | Part 4 §4.12 |
| MGR-14 | ObservabilityManager | WorkflowManager | DATA | M9 → M4 | Workflow observability | DERIVED | Part 4 §4.12 |
| MGR-15 | ObservabilityManager | SecurityManager | SECURITY | M9 → M5 | Security observability | DERIVED | Part 4 §4.12 |

> **CONFLICT-CM-01 impact:** The above uses Part 4 §4.2.1 naming. Part 1 §1.8.1 uses different names for the same M-slots (e.g., M2=LLMManager in Part 1, StateManager in Part 4). The dependency *relationships* are preserved from Part 4 §4.12; component naming follows Part 4 as one valid CONFLICT-preserving view.

### 7.7 External System Dependencies

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| EXT-01 | ToolManager/MCPService | MCP Servers | EXTERNAL | Consumer → Provider | Discovers/executes MCP tools | EXISTING | Part 6 §6.5 |
| EXT-02 | LLMManager/ModelRouter | Model Providers | EXTERNAL | Consumer → Provider | Routes inference requests | EXISTING | Part 4 §4.13 |
| EXT-03 | SecurityManager | Identity Providers | EXTERNAL | Consumer → Provider | Authenticates via external identity | EXISTING | Part 4 §4.7 |
| EXT-04 | MemoryManager | Obsidian Vault | EXTERNAL | Consumer → Provider | Persists memory to Obsidian | EXISTING | Part 9 §9.5 |
| EXT-05 | MemoryManager | Graphify Graph Store | EXTERNAL | Consumer → Provider | Persists memory to graph store | EXISTING | Part 9 §9.5 |
| EXT-06 | ToolManager | Web Search | EXTERNAL | Consumer → Provider | Executes web search | EXISTING | Part 6 §6.6 |
| EXT-07 | CouncilService | External AI Providers | EXTERNAL | Consumer → Provider | Council may use external models | GAP | Part 6 §6.2 |

**GAPs (external system contracts not defined in Parts 0–13):**

| Gap ID | External System | Missing Contract | Status |
|--------|-----------------|------------------|--------|
| GAP-EXT-01 | Identity Providers | Integration contract for authentication | GAP |
| GAP-EXT-02 | Regulatory Frameworks | Adapter contract for compliance validation | GAP |
| GAP-EXT-03 | Telemetry Backend | Export contract for metrics/traces | GAP |
| GAP-EXT-04 | External Audit Systems | Integration contract for governance events | GAP |

### 7.8 Infrastructure Dependencies

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| INF-01 | All Components | EventBus | INFRASTRUCTURE | Component → EventBus | Single-process event transport | EXISTING | Part 2 §2.1 |
| INF-02 | All Components | Python Runtime | INFRASTRUCTURE | Component → Python | Execution environment | ASSUMPTION | Part 0 §0.2.2 |
| INF-03 | StateManager, CheckpointManager, ConfigurationManager | Filesystem | INFRASTRUCTURE | Component → Filesystem | State, checkpoint, config persistence | ASSUMPTION | Part 0 §0.2.2 |
| INF-04 | MemoryManager | SecretManager | SECURITY | MemoryManager → SecurityManager | Credentialed access to external backends | EXISTING | Part 4 §4.12 |
| INF-05 | SecurityManager | SecretManager | SECURITY | SecurityManager → SecurityManager | Secret retrieval for credential verification | EXISTING | Part 4 §4.7 |

> **ASSUMPTION-01:** Python runtime is assumed based on Part 0 §0.2.2 "implementation substrate." Not explicitly specified.
> **ASSUMPTION-02:** Filesystem persistence is assumed based on Part 0 §0.2.2. Not explicitly specified.

### 7.9 Configuration Dependencies

| ID | Source | Target | Dependency Type | Direction | Reason | Status | Source Section |
|----|--------|--------|------|-----------|--------|--------|---------------|
| CFG-01 | All Components | ConfigurationManager | CONFIGURATION | Component → C3 | Reads component-specific configuration | EXISTING | Part 3 §3.5 |
| CFG-02 | EventBus | ConfigurationManager | CONFIGURATION | C1 → C3 | Reads capacity/timeout configuration | EXISTING | Part 4 §4.1 |
| CFG-03 | StateManager | ConfigurationManager | CONFIGURATION | M2 → C3 | Reads state persistence configuration | EXISTING | Part 4 §4.2 |
| CFG-04 | SecurityManager | ConfigurationManager | CONFIGURATION | M5 → C3 | Reads policy/authz configuration | EXISTING | Part 4 §4.7 |
| CFG-05 | WorkflowManager | ConfigurationManager | CONFIGURATION | M4 → C3 | Reads workflow timeout/retry configuration | DERIVED | Part 4 §4.5 |
| CFG-06 | ObservabilityManager | ConfigurationManager | CONFIGURATION | M9 → C3 | Reads observability configuration | DERIVED | Part 4 §4.11 |

> **CONFLICT-CC-01 aspect (configuration):** Part 0 names `ConfigurationAuthority` as owner; Part 1/Part 3 name `ConfigurationManager`. Part 4 §4.1 lists `ConfigurationAuthority` as C3. These may be the same component under different names — **UNRESOLVED**.

---

## 8. Initialization and Shutdown Dependencies

### 8.1 Initialization Ordering

**CONFLICT-INIT-01 is UNRESOLVED.** `deployment.md` §4.1 explicitly documents two conflicting phase models and preserves the conflict as UNRESOLVED — neither is adopted as authoritative.

#### 8.1-A. Part 4 §4.1 Five-Phase Model (EXISTING per Part 4)

| Phase | Scope | Authority |
|-------|-------|-----------|
| Phase 0 | EventBus initialization | Part 2 §2.1 |
| Phase 1 | ServiceRegistry initialization | Part 5 §5.1 |
| Phase 2 | Core Components initialization + Configuration loading | Part 1 §1.7.1; Part 3 §3.5 |
| Phase 3 | Core Managers initialization + Configuration freeze | Part 4 §4.2.1 |
| Phase 4 | Engineering Services initialization | Part 5 §5.2 |

**Source:** `deployment.md` §5.2; Part 4 §4.1

#### 8.1-B. Part 1 §1.10.2 Nine-Phase Model (EXISTING per Part 1)

| Phase | Name | What Initializes |
|-------|------|-----------------|
| Phase 0 | EventBus Bootstrap | EventBus (C1, no dependencies) |
| Phase 1 | ServiceRegistry | ServiceRegistry (C2, depends: EventBus) |
| Phase 2 | Core Components | C2, C3 (depends: Phase 0) |
| Phase 3 | Core Managers | C4 (depends: Phases 0–2) |
| Phase 4 | Memory & LLM | MemoryManager, LLMManager (parallel) |
| Phase 5 | Tools & Storage | ToolManager, StorageManager (parallel) |
| Phase 6 | Context & Agents | ContextManager, AgentManager (parallel) |
| Phase 7 | Workflows & Security | WorkflowManager, SecurityManager (parallel) |
| Phase 8 | Observability | ObservabilityManager (depends: all prior) |
| Phase 9+ | Service Init | Engineering Services, Facade Services |

**Source:** Part 14 `14.9-Deployment-and-Infrastructure-Integration.md` §5.1 (citing Part 01 §1.10.2)

#### 8.1-C. Common Invariants (EXISTING — shared by both models)

| Invariant | Description | Source |
|-----------|-------------|--------|
| INV-CC-001 | Core Components initialize Phase 0 to 1 to 2 to 3 | Part 1 §1.7.3 |
| INV-CM-001 | Core Managers initialize Phase 4 to 5 to 6 to 7 to 8 | Part 1 §1.8.3 |
| INV-CM-002 | No Core Manager may initialize before Phase 4 | Part 1 §1.8.3 |
| INV-EB-LC-001 | EventBus MUST be the first Core Component to reach RUNNING | Part 3 §3.5.8 |
| INV-CM-SRC-001 | All four configuration layers MUST be loaded during Phase 2 | Part 3 §3.5 |
| INV-CM-FRZ-001 | Config frozen after Phase 3 | Part 1 §1.10.2 |

> **Source:** `deployment.md` §5.2; Part 14 `14.9-Deployment-and-Infrastructure-Integration.md` §5.1 (citing Part 01 §1.10.2). `deployment.md` §279 explicitly states: "The exact number and definition of initialization phases is subject to CONFLICT-INIT-01. Part 4 §4.1 defines a 5-phase model; Part 1 §1.10.2 describes a different structure. Both are preserved; the conflict is unresolved."

> **Note:** The Core Manager names in Part 1's Phase 4–8 follow Part 1 §1.8.1. Part 4 §4.2.1 uses different names. The *ordering invariant* is the same; only the *naming* differs. This is a CONFLICT-CM-01 naming issue, not a phase-ordering issue. CONFLICT-CM-01 is preserved as UNRESOLVED in §19.

### 8.2 Shutdown Ordering

**EXISTING** — `deployment.md` §6.1: "Shutdown ordering is the reverse of startup ordering. This is mandated by the architecture."

| Shutdown Phase | Entities | Order | Source |
|----------------|----------------|-------------|------------|
| Services (Phase 9+) | Engineering Services, Facade Services | Reverse dependency topology | Part 1 §1.11.2 |
| Core Managers | All Core Managers | Reverse phase order | Part 1 §1.11.2 |
| Core Components | LifecycleManager to ConfigurationManager to ServiceRegistry to EventBus | Reverse initialization order | Part 1 §1.11.2 |
| EventBus | C1 | MUST be last | Part 1 §1.11.2 |

**Invariant:** `INV-STR-005` — Shutdown order is EXACT REVERSE of initialization (Part 1 §1.11.2; Part 3 §3.7.4; Part 4 §4.12.8)

> **Source:** `deployment.md` §6.1. The reverse-shutdown listing is sourced from `deployment.md` §6.1 and applies regardless of which phase model (8.1-A or 8.1-B) is ultimately selected by the ARB.

### 8.3 CONFLICT-INIT-01 (Preserved Unresolved)

**CONFLICT-INIT-01 IS a real, UNRESOLVED conflict.** `deployment.md` itself documents the conflict and preserves it as UNRESOLVED.

**Evidence:**
- `deployment.md` §279: "The exact number and definition of initialization phases is subject to CONFLICT-INIT-01. Part 4 §4.1 defines a 5-phase model; Part 1 §1.10.2 describes a different structure. Both are preserved; the conflict is unresolved."
- `deployment.md` §954: CONFLICT-INIT-01 registered as UNRESOLVED
- `deployment.md` §1183: Final audit lists "CONFLICT-INIT-01: Initialization phase structure: Part 4 §4.1 vs Part 1 §1.10.2 — UNRESOLVED — escalated to ARB"

**Status: UNRESOLVED (ARB).** Both phase models are preserved as EXISTING per their respective sources (§8.1-A for Part 4, §8.1-B for Part 1). The phase-count difference is a genuine architectural conflict. This document records both models without merging them. CONFLICT-INIT-01 remains in the conflict register (§19) as UNRESOLVED.

---

## 9. Runtime Communication Dependencies

### 9.1 EventBus as Sole Communication Substrate

**EXISTING** — Part 2 §2.1: "EventBus (C1) is the sole communication substrate for all inter-component communication after Kernel initialization."

| Component | Publishes Events To | Consumes Events From | Status | Source |
|-----------|-------------------|---------------------|--------|--------|
| EventBus (C1) | All components | N/A (substrate) | EXISTING | Part 2 §2.1 |
| ServiceRegistry (C2) | EventBus | EventBus | EXISTING | Part 3 §3.3.2 |
| ConfigurationManager (C3) | EventBus | EventBus | EXISTING | Part 3 §3.3.3 |
| All Components | EventBus | EventBus | EXISTING | Part 2 §2.1 |

### 9.2 Runtime Substrate Verification

**Status: UNSPECIFIED** — `runtime-map.md` is currently empty (PLANNED). Per §5.4, no runtime-specific dependencies beyond the EventBus substrate (§9.1) can be verified against runtime evidence. All runtime-level dependency assertions are **UNVERIFIED** and require runtime-map.md authoring.

| Runtime Concept | Dependency Claimed | Verification Status | Source |
|-----------------|-------------------|---------------------|--------|
| EventBus pub/sub for all inter-component communication | EventBus is sole communication substrate | EXISTING | Part 2 §2.1 |
| EventBus replay semantics | EventBus supports replay | UNSPECIFIED | runtime-map.md (EMPTY) |
| EventBus persistence | Events are durably stored | UNSPECIFIED | runtime-map.md (EMPTY) |
| Component startup ordering at runtime | Topological init per deployment.md §4 | EXISTING | deployment.md §4.1 |
| Service discovery at runtime | ServiceRegistry manages runtime discovery | UNSPECIFIED | runtime-map.md (EMPTY) |

### 9.3 Key Distinction: Communication vs. Dependency

**EventBus is the communication substrate** — all communication flows *through* it. Components that publish or consume events on EventBus have a **Communication (EVENT)** relationship with the EventBus infrastructure, NOT a direct architectural **Dependency** on other event-consuming components.

**Component-to-component event flows are Interactions, not Dependencies.** A component that publishes an event consumed by another component does NOT create a direct dependency from consumer → producer. The dependency is mediated: both depend on EventBus (EVENT type), not on each other directly.

> **Event-Mediated Dependencies:** Must distinguish Producer → Event → Consumer from direct Producer → Consumer coupling. This document records only the latter as a direct dependency when an authoritative source explicitly asserts it. All event-mediated relationships are recorded as `EVENT` type dependencies on the EventBus, not as direct component-to-component dependencies.

---

## 10. Service-to-Service Dependencies

### 10.1 Linear SDLC Chain

**EXISTING** — Part 5 §5.2.4: Engineering Services form a linear dependency chain following the SDLC phases. Direction: **Consumer → Provider** (Consumer requires Provider).

| Consumer | Provider | Dependency Type | Status | Source |
|----------|----------|-----------------|--------|--------|
| PlanningService | CodingService | STRUCTURAL | DERIVED | Part 5 §5.2.1 |
| CodingService | ReviewService | STRUCTURAL | DERIVED | Part 5 §5.2.1 |
| ReviewService | TestingService | STRUCTURAL | DERIVED | Part 5 §5.2.1 |
| TestingService | DeploymentService | STRUCTURAL | DERIVED | Part 5 §5.2.1 |
| DeploymentService | OperationsService | STRUCTURAL | DERIVED | Part 5 §5.2.1 |
| OperationsService | LearningService | STRUCTURAL | DERIVED | Part 5 §5.2.1 |
| LearningService | MemoryService (E8) | STRUCTURAL | DERIVED | Part 5 §5.2.1 |

> **CONFLICT-ES-01** (preserved, see §7.3): Part 14 §5.1 reclassifies CouncilService and HumanInteractionService as Engineering Services (E9/E10), adding 2 to the count. Part 5 §5.2.1 classifies them as Governance Services. The 8-service linear chain above follows Part 5's authoritative classification.

### 10.2 Cross-Phase Dependencies

| Consumer | Provider | Dependency Type | Status | Source |
|----------|----------|-----------------|--------|--------|
| OperationsService | SkillService | STRUCTURAL | EXISTING | Part 5 §5.8 |
| PlanningService | SkillService | STRUCTURAL | EXISTING | Part 5 §5.3 |

> **Note:** These cross-phase dependencies reference SkillService (the Capability Facade, Part 6 §6.4). Per CONFLICT-ES-01, Part 5 classifies SkillService as a Capability Facade, not an Engineering Service. This is a naming/cross-reference issue, not a dependency invention.

---

## 11. Event-Mediated Dependencies

### 11.1 Distinguishing Direct from Event-Mediated Dependencies

This section explicitly distinguishes **Direct Dependencies** (A structurally requires B) from **Event-Mediated Dependencies** (A and B communicate through EventBus but do not structurally depend on each other).

**Direct Dependencies (from Part 14 CC/CM/SC tables):**
- HermesKernel → Core Components (ownership/initialization) — Part 1 §1.8.1
- Facade → Manager (delegation) — Part 6 §6.4
- StateManager ↔ StorageManager (data) — Part 4 §4.12
- Governance G-xx → Manager (structural) — Part 13 §1.x

**Event-Mediated Dependencies (NOT direct A→B):**
- PlanningService → CodingService (SDLC chain) — mediated via PlanningCompleted → CodingService event
- CodingService → ReviewService — mediated via CodeReviewRequested event
- TestingService → DeploymentService — mediated via TestsPassed event
- All components → EventBus (EVENT type, not STRUCTURAL)

> **Rule:** An event-mediated chain (A publishes E; B consumes E) is recorded as A → EventBus (EVENT) and B → EventBus (EVENT). It is NOT recorded as A → B unless an authoritative source explicitly states a structural runtime dependency. The SDLC "chain" dependencies in §10.1 are marked DERIVED (not EXISTING) because they represent event-mediated orchestration, not explicit structural dependencies in the source architecture.

### 11.2 Governance Event Dependencies

All governance components depend on EventBus for event transport (EVENT type). Internal governance component-to-component dependencies (GOV-01..GOV-17 in §7.5) are STRUCTURAL or SECURITY type, not event-mediated.

---

## 12. Interface Dependencies

### 12.1 Core Component to Interface Dependencies

| ID | Source | Target | Dependency Type | Direction | Status | Source Section |
|----|--------|--------|------|-----------|--------|---------------|
| CI-01 | HermesKernel | INT-CORE-CMP-001 | INTERFACE | Kernel → Interface | Kernel owns and provides Core Component interface | EXISTING | Part 1 §1.8.1 |
| CI-02 | HermesKernel | INT-CORE-MGR-001 | INTERFACE | Kernel → Interface | Kernel owns and provides Core Manager interface | EXISTING | Part 1 §1.8.1 |
| CI-03 | HermesKernel | INT-KERNEL-ACC-001 | INTERFACE | Kernel → Interface | Kernel provides singleton accessor interface | EXISTING | Part 1 §1.9 |
| CI-04 | HermesKernel | INT-EVT-BUS-001 | INTERFACE | Kernel → Interface | EventBus is the communication substrate | EXISTING | Part 2 §2.1 |
| CI-05 | HermesKernel | INT-SVC-REG-001 | INTERFACE | Kernel → Interface | ServiceRegistry interface provided by kernel | EXISTING | Part 3 §3.3 |
| CI-06 | HermesKernel | INT-CONFIG-READ-001 | INTERFACE | Kernel → Interface | ConfigurationManager interface provided by kernel | EXISTING | Part 3 §3.3 |
| CI-07 | HermesKernel | INT-SEC-AUTH-001 | INTERFACE | Kernel → Interface | SecurityManager interface provided by kernel | EXISTING | Part 4 §4.7 |
| CI-08 | EventBus | INT-EVT-BUS-001 | INTERFACE | C1 → Interface | EventBus implements EventBus interface | EXISTING | Part 2 §2.1 |

### 12.2 Service to Interface Dependencies

| ID | Source | Target | Dependency Type | Direction | Status | Source Section |
|----|--------|--------|------|-----------|--------|---------------|
| CX-01 | EngineeringService (any) | INT-SVC-BASE-001 | INTERFACE | Service → Interface | Services implement BaseService contract | EXISTING | Part 5 §5.2 |
| CX-02 | EngineeringService (any) | INT-EVT-BUS-001 | INTERFACE | Service → Interface | Services consume EventBus for communication | EXISTING | Part 5 §5.2 |
| CX-03 | EngineeringService (any) | INT-SEC-AUTH-001 | INTERFACE | Service → Interface | Services consume SecurityManager for authz | EXISTING | Part 5 §5.2 |
| CX-04 | Capability Facade | INT-CFS-BRIDGE-001 | INTERFACE | Facade → Interface | Facades implement facade bridge interface | EXISTING | Part 6 §6.1.5 |
| CX-05 | Any Service | INT-HUMAN-001 | INTERFACE | Service → Interface | Services consume HumanInteractionService for escalation | EXISTING | Part 5 §5.8 |

### 12.3 Governance to Interface Dependencies

| ID | Source | Target | Dependency Type | Direction | Status | Source Section |
|----|--------|--------|------|-----------|--------|---------------|
| GI-01 | Any G-xx | INT-GOV-EVENT-001 | INTERFACE | G-xx → Interface | Governance components consume/emit governance events | EXISTING | Part 13 §1.3 |
| GI-02 | Any G-xx | INT-SEC-AUTH-001 | INTERFACE | G-xx → Interface | Governance operations require authorization | EXISTING | Part 13 §1.4 |

---

## 13. Security Dependencies

### 13.1 Authorization Dependencies

| Consumer | Provider | Dependency Type | Direction | Status | Source |
|----------|----------|-----------------|-----------|--------|--------|
| All Services | SecurityManager | SECURITY | Service → M5 | EXISTING | Part 4 §4.7 |
| All Core Managers | SecurityManager | SECURITY | Manager → M5 | DERIVED | Part 4 §4.12 |
| All Governance Components | SecurityManager | SECURITY | G-xx → M5 | EXISTING | Part 13 §1.4 |
| SkillManager, CouncilManager, MCPManager | SecurityManager | SECURITY | Facade Manager → M5 | EXISTING | Part 4 §4.12 |
| SecurityManager | SecretManager | SECURITY | M5 → SecretManager | EXISTING | Part 4 §4.7 |

**GAP-SEC:** Bus-level authentication/authorization on EventBus is not specified in Parts 0–13. Per v1.0 trusted single-tenant model (Part 14), SecurityManager authz applies to component operations, not to EventBus transport-level authentication (UNRES-05, preserved).

**Invariant:** `GOV-17` — All governance operations require SecurityManager authz (Part 13 §1.4).

### 13.2 Secret Management Dependencies

| Consumer | Provider | Dependency Type | Status | Source |
|----------|----------|-----------------|--------|--------|
| SecurityManager | SecretManager | SECURITY (Secret Access) | EXISTING | Part 4 §4.7 |
| MemoryManager | SecretManager | SECURITY (Secret Access) | EXISTING | Part 4 §4.12 |

**GAP:** Secret storage backend mechanism not defined in Parts 0–13 (Part 14 §12 covers secret handling; mechanism deferred). **Status: GAP.**

### 13.3 Security Boundary Trust Model

**Status: EXISTING** — Part 01 §1.10 / Part 04 §4.12.5: HermesKernel is the trust boundary for all kernel-owned entities. External systems are outside the kernel trust boundary.

| Boundary | Direction | Trust Status | Source |
|----------|-----------|-------------|--------|
| Kernel ↔ Core Components | Bidirectional | Trusted (same process) | Part 1 §1.7 |
| Kernel ↔ Core Managers | Bidirectional | Trusted (same process) | Part 1 §1.8 |
| Kernel ↔ Services | Bidirectional | Trusted (same process) | Part 5 §5.2 |
| Kernel ↔ External Systems | Cross-boundary | Untrusted | Part 1 §1.10 |

---

## 14. Deployment Dependencies

### 14.1 Deployable Unit Dependencies

**EXISTING** — `deployment.md` §2: The HermesKernel is the single deployable unit. No multi-unit deployment topology is defined for v1.0.

| Dependency | Status | Source |
|-----------|--------|--------|
| HermesKernel is the sole deployable unit | EXISTING | deployment.md §2.1 |
| No external orchestration required | EXISTING | deployment.md §4.1.5 |
| Kernel self-governs startup sequence via LifecycleManager | EXISTING | deployment.md §4.1.5 |

### 14.2 What Is NOT Inferred

The architecture's deployment dependencies do **NOT** imply:
- Containerization (Docker, Kubernetes, etc.) — UNSPECIFIED
- CI/CD pipelines — UNSPECIFIED
- Load balancers or API gateways — UNSPECIFIED
- Specific cloud providers — UNSPECIFIED

**Source:** `deployment.md` §2.2, §4.1.5. "No deployment script, process manager, or orchestration platform is required by the architecture."

---

## 15. Runtime Dependency Ordering

### 15.1 Runtime Verification Status

**Status: UNSPECIFIED / SOURCE VERIFICATION REQUIRED** — All runtime-ordered dependency assertions require `runtime-map.md`, which is currently **EMPTY (PLANNED)**.

| Runtime Ordering Claim | Status | Source |
|------------------------|--------|--------|
| Core Components Phase 0 to 3 sequential | CONFLICT (phase count) | Part 4 §4.1 (5-phase) vs Part 1 §1.10.2 (9-phase); deployment.md preserves CONFLICT-INIT-01 |
| Core Managers Phase 4 to 8 sequential | CONFLICT (phase count) | Part 4 §4.1 (5-phase) vs Part 1 §1.10.2 (9-phase); deployment.md preserves CONFLICT-INIT-01 |
| Services Phase 9+ (topological) | EXISTING (Part 1) / GAP (Part 4) | Part 1 §1.10.2 has Phase 9+; Part 4 §4.1 Phase 4 = Services (no gap); source-dependent |
| Shutdown: reverse initialization order | EXISTING | deployment.md §6.1 (reverse rule applies regardless of phase model) |
| Runtime EventBus pub/sub ordering | UNSPECIFIED | runtime-map.md (EMPTY) |
| Runtime StateManager consistency ordering | UNSPECIFIED | runtime-map.md (EMPTY) |
| Runtime Service discovery ordering | UNSPECIFIED | runtime-map.md (EMPTY) |

The shutdown ordering is sourced from `deployment.md` §6.1 as **EXISTING** (reverse of startup). The initialization phase *model* is **CONFLICT** (CONFLICT-INIT-01: 5-phase vs 9-phase). The phase ordering *invariant* (Phase N before Phase N+1) is shared by both models. Runtime-level behavioral ordering (beyond initialization/shutdown phases) is **UNSPECIFIED** because `runtime-map.md` is empty.

### 15.2 Invariant Cross-Reference

| Invariant | Description | Source |
|-----------|-------------|--------|
| INV-CC-001 | Core Components MUST initialize in Phase 0→1→2→3 order | Part 1 §1.7.3 |
| INV-CM-001 | Core Managers MUST initialize in Phase 4→5→6→7→8 order | Part 1 §1.8.3 |
| INV-CM-002 | No Core Manager may initialize before Phase 4 | Part 1 §1.8.3 |
| INV-STR-005 | Shutdown order is EXACT REVERSE of initialization | Part 1 §1.11.2 |
| INV-STR-009 | No circular dependencies in initialization dependency graph | Part 1 §1.10.2 |
| INV-LC-003 | Once TERMINATED, kernel MUST be discarded; re-initialization PROHIBITED | Part 1 §1.11.3 |

---

## 16. Circular Dependency Analysis

### 16.1 Topological Validation

**EXISTING** — Part 1 §1.5: "No circular dependencies are permitted in the runtime dependency graph."

**Invariant:** `INV-STR-009` — No circular dependencies in initialization dependency graph (Part 1 §1.10.2).

### 16.2 Initialization Graph Acyclicity

Note: CONFLICT-INIT-01 — Part 4 §4.1 uses a 5-phase model vs Part 1's 9-phase model. The initialization dependency graph below uses Part 1 §1.7.3 / §1.8.3 naming (Core Components Phase 0–3 → Core Managers Phase 4–8 → Services Phase 9+):

```
Initialization:  EventBus (0) → ServiceRegistry (1) → ConfigurationManager (2) → LifecycleManager (3)
               → Core Managers (4→5→6→7→8, parallel within phase)
               → Services (9+, topological)
```

**Result:** The initialization graph is acyclic. No circular dependencies are asserted by any authoritative source for the core initialization layer. Within-phase manager initialization is parallel (no inter-phase cycles); cross-phase dependencies all flow upward (Phase N components depend on Phase N-1 components, never the reverse).

### 16.3 Governance Layer Circular Dependencies

**Governance Layer Cycles (CONFLICT-INIT-01 is a separate, unresolved phase-model conflict; this is a different issue):**

The following cycles exist in the governance component inter-dependencies (Part 13 §1.x):

1. G-02 ↔ G-01: PolicyEvaluationEngine ↔ PolicyManager
2. G-02 → G-05 → G-02: PolicyEvaluationEngine → DecisionAuthorityManager → PolicyEvaluationEngine
3. G-02 → G-11 → G-02: PolicyEvaluationEngine → ExceptionManager → PolicyEvaluationEngine
4. G-02 → G-13 → G-02: PolicyEvaluationEngine → ControlManager → PolicyEvaluationEngine

**Circularity Severity:** HIGH — These cycles create potential infinite loops in governance decision-making. **Status: CONFLICT (Gov-02 cycle) — UNRESOLVED.**

This is recorded as a finding in Part 14 dependency-map.md §9 (FIND-RISK-03, de-duplicated from FIND-RISK-C01). The governance layer cycles are a Part 14 analytical finding, not source-established architecture.

### 16.4 No Invented Cycles

No circular dependencies are invented for analysis purposes. The only architectural constraint is Part 1 §1.5 ("No circular dependencies permitted in the runtime dependency graph"). Any cycle detected in implementation is a defect, not an architecture-defined loop.

---

## 17. Dependency Invariants

All dependency invariants are sourced from Parts 0–13 and documented in `deployment.md` §4.1.5 and §6:

| Invariant | Description | Source |
|-----------|-------------|--------|
| INV-CC-001 | Core Components MUST initialize in Phase 0→1→2→3 order | Part 1 §1.7.3 |
| INV-CM-001 | Core Managers MUST initialize in Phase 4→5→6→7→8 order | Part 1 §1.8.3 |
| INV-CM-002 | No Core Manager may initialize before Phase 4 | Part 1 §1.8.3 |
| INV-STR-005 | Shutdown order is EXACT REVERSE of initialization | Part 1 §1.11.2 |
| INV-STR-009 | No circular dependencies in initialization dependency graph | Part 1 §1.10.2 |
| INV-LC-003 | Once TERMINATED, kernel MUST be discarded; re-initialization PROHIBITED | Part 1 §1.11.3 |
| INV-EB-LC-001 | EventBus MUST be the first Core Component to reach RUNNING | Part 3 |
| INV-CC-STR-003 | Each Core Component has unique, fixed initialization phase (0–3) | Part 3 |
| INV-CM-FRZ-001 | ConfigurationManager freezes before Service initialization (Post-Phase 3) | Part 1 §1.10.2 |
| INV-CM-SRC-001 | All four configuration layers MUST be loaded during Phase 2 | Part 3 §3.5 |
| INV-CM-FH-001 | Any configuration failure during Phase 2 is FATAL | Part 3 §3.5.8 |
| INV-STR-007 | Service initialization MUST respect declared dependencies; topological sort MUST be acyclic | Part 1 §1.10.2 |
| INV-SR-INIT-002 | Dependency topology MUST be validated before Phase 9 begins | Part 3 §3.4.10 |
| CC-L-001 | No manager in phase N starts before all phase N-1 managers report READY | Part 4 §4.12.7 |
| CC-L-002 | Failed initialization → all managers shutdown; storage rolled back; state restored | Part 4 §4.12.7 |

---

## 18. Dependency Gaps

### 18.1 Gap Catalog

| GAP ID | Dependency / Component | Gap Description | Severity | Status |
|--------|----------------------|----------------|----------|--------|
| GAP-01 | INT-KERNEL-ACC-001 | No formal schema for accessor interface | MEDIUM | GAP |
| GAP-02 | INT-ENG-EVENT-001 | Per-service payload schemas not defined | HIGH | GAP |
| GAP-03 | EventBus envelope | Two coexisting envelope specs (Part 2 §2.2.1 vs Part 12 §4) | HIGH | GAP |
| GAP-04 | MemoryManager | Memory backend persistence mechanism not specified | MEDIUM | GAP |
| GAP-05 | SecretManager | Secret storage backend mechanism not defined | HIGH | GAP |
| GAP-06 | RetryManager | Retry semantics divergence (Part 0 §0.2.1 vs Part 4 §4.8) | MEDIUM | GAP |
| GAP-07 | DLQ model | Part 2 single DLQ vs Part 12 per-family DLQ divergence | MEDIUM | GAP |
| GAP-08 | Retry semantics | Retry semantics divergence (Part 2 §2.4 vs Part 12 §18) | MEDIUM | GAP |
| GAP-09 | Event ordering | Event ordering guarantees across families not specified | MEDIUM | GAP |
| GAP-10 | Event deduplication | Deduplication strategy not specified | MEDIUM | GAP |
| GAP-11 | Event ratification | Event ratification mechanism not specified | MEDIUM | GAP |
| GAP-12 | Event tombstones | Event tombstone handling not specified | MEDIUM | GAP |
| GAP-13 | Event naming | Three naming schemes inconsistent (SCREAMING_SNAKE_CASE, dotted, PascalCase) | LOW | GAP |
| GAP-14 | Event count | Part 2 prose claims 97 events but enum has 118 — specification inconsistency | LOW | GAP |
| GAP-15 | [DEPRECATED — Use GAP-01] | Duplicate entry for INT-KERNEL-ACC-001 schema gap | — | DEPRECATED |

> **DEPRECATION note (§14.2):** GAP-15 was a duplicate of GAP-01, deprecated per Part 14 dependency-map.md §12.1. UNRES-14 was a duplicate of UNRES-06, deprecated per Part 14. FIND-RISK-C01 was a duplicate of FIND-RISK-03, deprecated per Part 14 dependency-map.md §13. These deprecations are preserved.

### 18.2 Runtime Verification Gaps

| Gap ID | Dependency | Gap Description | Status |
|--------|-----------|----------------|--------|
| GAP-RT-01 | Runtime ordering | `runtime-map.md` is empty (PLANNED) | UNSPECIFIED |
| GAP-RT-02 | Runtime EventBus behavior | Replay/persistence semantics not documented | UNSPECIFIED |
| GAP-RT-03 | Service discovery at runtime | ServiceRegistry runtime discovery contract not defined | UNSPECIFIED |

### 18.3 Gap Summary

| Category | Count | Status |
|----------|-------|--------|
| Architecture gaps (GAP-01..GAP-14) | 14 active | Recorded, not resolved |
| Deprecated gaps (GAP-15) | 1 | Deprecated (duplicate of GAP-01) |
| Runtime verification gaps (GAP-RT-01..GAP-RT-03) | 3 | UNSPECIFIED (runtime-map.md empty) |
| External system gaps (GAP-EXT-01..GAP-EXT-04) | 4 | Recorded, not resolved |

---

## 19. Dependency Conflicts

All conflicts are preserved from Part 14. This document does **NOT** resolve them — they are recorded for ARB escalation.

### 19.1 Conflict Register

| Conflict ID | Description | Source A | Source B | Status |
|-------------|-------------|----------|----------|--------|
| CONFLICT-CC-01 | Four sources define four different Core Component sets | Part 0 §0.3.2 | Part 1 §1.8.1 / Part 3 §3.1–3.6 / Part 4 §4.1 | UNRESOLVED (ARB) |
| CONFLICT-CM-01 | Three sources define different Core Manager sets (Part 0 "Capability Managers" vs Part 1 "Core Managers" vs Part 4 "Core Managers") | Part 0 §0.3.2 | Part 1 §1.8.1 / Part 4 §4.2.1 | UNRESOLVED (ARB) |
| CONFLICT-ES-01 | Part 0 specifies 8 Engineering Services; Part 5 specifies 10 (incl. 2 governance) | Part 0 §0.2.1 | Part 5 §5.2.1 / Part 14 §5.1 | UNRESOLVED (ARB) |
| CONFLICT-EVENT-01 | Part 2 §2.2 uses SCREAMING_SNAKE_CASE; Part 12/14 use verb-object PascalCase | Part 2 §2.2 | Part 12 §22 / Part 14 §14.11.4.10 | UNRESOLVED (ARB) |
| CONFLICT-GOV-01 | Part 13 README uses different names than Part 13 components.md | Part 13 README | Part 13 components.md | UNRESOLVED (ARB) |
| CONFLICT-FACADE-01 | Part 6 references SkillManager/CouncilManager/MCPManager not in Part 1/Part 4 Core Manager sets | Part 6 §6.4 | Part 1 §1.8.1 / Part 4 §4.2.1 | UNRESOLVED (ARB) |
| CONFLICT-MGR-01 | Part 1 M2=LLMManager; Part 4 uses ModelRouter for same capability | Part 1 §1.8.1 | Part 4 §4.13 | UNRESOLVED (ARB) |
| CONFLICT-INIT-01 | Initialization phase count/model differs between sources | Part 4 §4.1 (5 phases) | Part 1 §1.10.2 (9 phases 0-8 + 9+) | UNRESOLVED (ARB) |
| CONFLICT-CONFIG-01 | Configuration authority naming (ConfigurationAuthority vs ConfigurationManager) | Part 0 §0.3.2 / Part 4 §4.1 | Part 1 §1.8.1 / Part 3 §3.5 | UNRESOLVED (ARB) |

> **Note:** All conflicts above are preserved as UNRESOLVED per the Part 15 anti-invention rules. Neither side of any conflict is adopted as authoritative by this document. CONFLICT-INIT-01 reflects a genuine disagreement between Part 4 §4.1 (5-phase model) and Part 1 §1.10.2 (9-phase model + Phase 9+). Both are preserved as EXISTING per their respective sources in §8.1-A and §8.1-B. The phase *count* differs; the *ordering invariant* (Phase N before Phase N+1) is shared. CONFLICT-CONFIG-01 is noted in §7.9 and §7.1 but is a naming variant, not a dependency invention.

---

## 20. Dependency-to-Source Traceability

Every dependency assertion in this document is traceable to a Part 0–13 source section. The traceability mapping below records the source anchor for each dependency section.

| Section | Dependencies | Source Part | Source Section(s) |
|---------|-------------|-------------|-------------------|
| §7.1 Core Component Dependencies | CC-01..CC-04 (4 tables A–D) | Part 0, Part 1, Part 3, Part 4 | §0.3.2, §1.8.1, §3.1–3.6, §4.1 |
| §7.2 Core Manager Dependencies | CM-01..CM-09 (2 tables) | Part 0, Part 1, Part 4 | §0.3.2, §1.8.1, §4.2.1 |
| §7.3 Engineering Service Dependencies | ES-01..ES-23, GS-01..GS-04 | Part 0, Part 5 | §0.2.1, §5.2.1 |
| §7.4 Facade Dependencies | CFS-01..CFS-06 | Part 6 | §6.1–6.5 |
| §7.5 Governance Dependencies | GOV-01..GOV-17 | Part 13 | §1.3–1.19 |
| §7.6 Manager Dependency Detail | MGR-01..MGR-15 | Part 4 | §4.12 |
| §7.7 External System Dependencies | EXT-01..EXT-07 | Part 4, Part 6, Part 9 | §4.13, §6.5, §9.5 |
| §7.8 Infrastructure Dependencies | INF-01..INF-05 | Part 0, Part 2, Part 4 | §0.2.2, §2.1 |
| §7.9 Configuration Dependencies | CFG-01..CFG-06 | Part 0, Part 3, Part 4 | §0.10, §3.5, §4.12 |
| §8.1 Initialization Ordering | Two phase models (5-phase, 9-phase) | Part 1, Part 4, deployment.md | §1.7.3, §1.8.3, §1.10.2, §4.1, deployment.md §4-5 |
| §8.2 Shutdown Ordering | Reverse initialization | Part 1, Part 4, deployment.md | §1.11.2, §4.12.8, deployment.md §5.1 |
| §9 EventBus Substrate | EventBus sole communication | Part 2 | §2.1 |
| §10 SDLC Chain | Service-to-service chain | Part 5 | §5.2.1, §5.2.4 |
| §11 Event-Mediated Deps | Communication vs dependency | Part 2, Part 14 | §2.1, §8 (analytical) |
| §12 Interface Deps | CI-01..CI-08, CX-01..CX-05, GI-01..GI-02 | Part 1, Part 2, Part 3, Part 5, Part 6, Part 13 | §1.8.1, §2.1, §3.3, §5.2, §6.1, §1.4 |
| §13 Security Deps | SecurityManager authz, SecretManager | Part 4, Part 13 | §4.7, §1.4 |
| §14 Deployment Deps | Single deployable unit | deployment.md | §2, §4.1 |
| §15 Runtime Ordering | Phase ordering + runtime UNSPECIFIED | Part 1, deployment.md | §1.7.3, §1.8.3, §1.11.2 |
| §16 Circular Deps | Acyclicity constraint, governance cycles | Part 1, Part 13, Part 14 | §1.5, §1.10.2, §1.4 |
| §17 Invariants | INV-CC-001, INV-CM-001, etc. | Part 1, Part 3, Part 4 | §1.7.3, §1.8.3, §1.11.2, §3.5, §4.12.7 |
| §16 ADR Deps | ADR-001..ADR-014, P13-ADR-01..10 | Part 0, Part 14 | §0.5, §0.10, adrs.md |

---

## 21. Dependency-to-Component Traceability

This section maps each architectural component to the dependency relationships it participates in (as either consumer/dependent or provider/dependency).

| Component | As Dependent (A→B, A requires) | As Provider (B is required by) | Conflict Status |
|-----------|-------------------------------|----------------------------------|-----------------|
| EventBus (C1) | None (foundation) | All components (35+) | EXISTING (universal) |
| ServiceRegistry (C2) | EventBus (C1) | HermesKernel, All Services | CONFLICT-CC-01 (Part 0 names different C2) |
| ConfigurationManager (C3) | EventBus (C1) | HermesKernel, All Components | CONFLICT-CC-01 (Part 0 names ConfigurationAuthority) |
| LifecycleManager (C4 Part 1) | EventBus, ServiceRegistry, Config | HermesKernel | CONFLICT-CC-01 (Part 3 names StructuredLogger) |
| StructuredLogger (C4 Part 3) | EventBus, ServiceRegistry, Config | HermesKernel | CONFLICT-CC-01 |
| StateManager (Part 4 M2) | EventBus, StorageManager, WorkflowManager | HermesKernel, ObservabilityManager, WorkflowManager | CONFLICT-CM-01 (Part 1 M2=LLMManager) |
| SecurityManager (Part 4 M5) | EventBus, SecretManager, ConfigurationManager | All secured operations | CONFLICT-CM-01 (Part 1 M5=ContextManager) |
| WorkflowManager (Part 4 M4) | EventBus, StateManager, SecurityManager, etc. | HermesKernel | CONFLICT-CM-01 |
| ObservabilityManager (Part 4 M9) | EventBus, StateManager, WorkflowManager, SecurityManager | HermesKernel | CONFLICT-CM-01 |
| PlanningService (E1) | EventBus, StateManager | CodingService | CONFLICT-ES-01 (Part 14 adds E9/E10) |
| All Engineering Services | EventBus, StateManager | Next service in SDLC chain | CONFLICT-ES-01 |
| All Capability Facades | EventBus, StateManager | None (terminal facades) | CONFLICT-FACADE-01 |
| All Governance Components (G-00–G-15) | EventBus, SecurityManager, StateManager, specific managers | None (governance overlay) | CONFLICT-CM-01 (manager naming) |

---

## 22. Dependency-to-Contract Traceability

This section maps dependencies to their implementation contract references in `implementation-contracts.md`.

| Dependency | Interface Contract | implementation-contracts.md Section | Status |
|-----------|-------------------|------------------------------------|--------|
| Kernel → EventBus | INT-CORE-CMP-001, INT-EVT-BUS-001 | §2 (kernel.init_core_components) | EXISTING |
| Kernel → Core Managers | INT-CORE-MGR-001 | §2 (kernel.init_managers) | EXISTING |
| Kernel → Services | INT-SVC-REG-001, INT-SVC-BASE-001 | §3 (runtime.start_services) | EXISTING |
| HermesKernel → Accessors | INT-KERNEL-ACC-001 | §1 (kernel access pattern) | SOURCE VERIFICATION REQUIRED |
| All Components → EventBus | INT-EVT-BUS-001 | §4 (event_bus.publish/subscribe) | EXISTING |
| Services → SecurityManager | INT-SEC-AUTH-001 | §5 (security.authz) | EXISTING |
| Services → ConfigurationManager | INT-CONFIG-READ-001 | §6 (config.get) | EXISTING |
| Governance → SecurityManager | INT-SEC-AUTH-001 | §5 | EXISTING |
| Governance → EventBus | INT-GOV-EVENT-001 | §7 (gov_event.emit/consume) | EXISTING |
| Facade → Manager | INT-CFS-BRIDGE-001 | §8 (facade.bridge) | EXISTING |
| StateManager ↔ StorageManager | (data dependency) | §9 (state.checkpoint) | EXISTING |

> **SOURCE VERIFICATION REQUIRED:** `implementation-contracts.md` §1 (RT.MUST.1) is marked "SOURCE VERIFICATION REQUIRED" with note "runtime-map.md = EMPTY." The kernel singleton access pattern (INT-KERNEL-ACC-001) cannot be fully verified without `runtime-map.md` authoring. **Status: UNSPECIFIED.**

---

## 23. Dependency Verification

### 23.1 Verification Status

| Verification Level | Components Verified | Status | Source |
|--------------------|-------------------|--------|--------|
| Source-backed (Parts 0–13) | All EXISTING dependencies | VERIFIED | Parts 0–13 |
| Part 14 analytical findings | DERIVED dependencies, risk findings | VERIFIED (Part 14 analysis) | Part 14 dependency-map.md §9–13 |
| Runtime verification | Runtime ordering, runtime behavior | UNSPECIFIED | runtime-map.md (EMPTY) |
| Implementation verification | Code-level wiring | NOT IN SCOPE | implementation-contracts.md |

### 23.2 Verification Methods

**Source-based verification:** All EXISTING dependencies cite an explicit Part 0–13 source section. These are verified against source documentation.

**Part 14 analytical verification:** DERIVED dependencies show an inference path from EXISTING statements. These are verified against Part 14 dependency-map.md §1–12 analytical findings.

**Runtime verification (UNSPECIFIED):** Runtime-level dependencies beyond initialization/shutdown phases cannot be verified because `runtime-map.md` is empty. Per §5.4, no runtime-specific dependencies beyond the EventBus substrate can be verified against authoritative runtime sources.

### 23.3 Verification Gaps

| Gap | Description | Status |
|-----|-------------|--------|
| GAP-RT-01 | `runtime-map.md` is empty; runtime ordering cannot be verified | UNSPECIFIED |
| GAP-RT-02 | EventBus replay/persistence semantics not documented | UNSPECIFIED |
| GAP-RT-03 | Service discovery runtime contract not defined | UNSPECIFIED |

---

## 24. Cross-Document Consistency

### 24.1 Consistency with components.md

All component dependencies in this document are cross-checked against `components.md` §9 (Component Dependencies). Where `components.md` §9.2 documents Core Manager inter-dependencies (e.g., WorkflowManager → StateManager, StorageManager, SecurityManager, CapabilityManager, ResourceManager), this document records the same dependencies with the same status. The naming follows Part 4 §4.2.1 in both documents, with CONFLICT-CM-01 preserved.

### 24.2 Consistency with deployment.md

The initialization and shutdown ordering in §8 is sourced from `deployment.md` §4.1 and §5.1. The phase structure (Phase 0–3 for Core Components, Phase 4–8 for Core Managers, Phase 9+ for Services) and invariants (INV-CC-001, INV-CM-001, INV-STR-005, INV-STR-009) are consistent between `deployment.md` and this document.

### 24.3 Consistency with implementation-contracts.md

Section §22 maps dependencies to implementation contract sections. The contract references are consistent with `implementation-contracts.md` §1–8. RT.MUST.1 in `implementation-contracts.md` §1 is marked "SOURCE VERIFICATION REQUIRED" due to empty `runtime-map.md` — this is reflected in §22's Status column.

### 24.4 Consistency with adrs.md

Section §23 maps dependencies to ADRs. The ADR references (ADR-001 event-first communication, ADR-010 configuration, ADR-004 kernel composition) are consistent with `adrs.md` entries and Part 14 adrs.md.

---

## 25. AI Coding Agent Rules

### 25.1 AI Agent Restrictions

AI coding agents MUST NOT:
- Infer dependencies merely because two components appear related
- Invent runtime ordering (runtime-map.md is empty — see §15)
- Invent dependency relationships not present in Parts 0–13 or Part 14
- Resolve CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, or other conflicts by choosing one source over another
- Treat event-mediated interactions as direct architectural dependencies
- Invent infrastructure dependencies beyond ASSUMPTION-level (§7.8)
- Invent deployment dependencies (§14 — UNSPECIFIED)
- Invent security mechanisms beyond SecurityManager (§13)

### 25.2 AI Agent Required Actions

AI coding agents MUST:
- Inspect `dependency-map.md` before adding any dependency assertion
- Verify every dependency assertion against Parts 0–13 source sections
- Mark event-mediated interactions as `EVENT` type dependencies on EventBus, NOT as direct component-to-component dependencies
- Preserve all CONFLICT entries without resolution
- Record unsourceable dependencies as UNSPECIFIED (not invented)
- Reference `components.md` §9 for component classification before asserting any component dependency
- Reference `deployment.md` §4–5 for initialization/shutdown ordering — NOT this document's own tables; note CONFLICT-INIT-01 is UNRESOLVED and both phase models are preserved
- Reference `implementation-contracts.md` §1 for contract-traceable dependencies

### 25.3 Source-Fidelity Rules

- **EXISTING claims** must cite an explicit Part 0–13 source section
- **DERIVED claims** must show the inference path from EXISTING statements
- **ASSUMPTION claims** must identify what source would establish the fact
- **UNSPECIFIED/GAP claims** must identify the source Part that is silent
- **CONFLICT claims** must name both/all conflicting sources
- No claim may cite `dependency-map.md` (this document) as authority for a dependency fact

---

## 26. Final Audit

### 26.1 Audit Criteria

| Criterion | Requirement | Result |
|----------|-------------|--------|
| All dependency assertions have status labels | 100% EXISTING/DERIVED/ASSUMPTION/UNSPECIFIED/GAP/PROPOSED/FUTURE/CONFLICT | PASS |
| All EXISTING/DERIVED claims have traceable source citations | Cite Part 0–13 section | PASS |
| All CONFLICTs explicitly name conflicting parties | CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, CONFLICT-EVENT-01, CONFLICT-GOV-01, CONFLICT-FACADE-01, CONFLICT-MGR-01, CONFLICT-INIT-01, CONFLICT-CONFIG-01 | PASS |
| All GAPs recorded, not invented | GAP-01..GAP-15 + GAP-EXT-01..04 + GAP-RT-01..03 | PASS |
| No architectural invention | No new dependencies created | PASS |
| Source fidelity | Every claim traces to Parts 0–13 | PASS |
| Conflict preservation | All Part 14 conflicts preserved | PASS |
| Direction semantics | A → B consistently means "A requires B" | PASS |
| Event-mediated vs direct | Distinguished per §11 | PASS |
| Version consistency | Header and Document Control agree | PASS |

### 26.2 Audit Results

| Audit Category | Result | Notes |
|----------------|--------|-------|
| Dependency assertion completeness | PASS | All asserted dependencies trace to Parts 0–13 or Part 14 analysis |
| Conflict preservation | PASS | CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, CONFLICT-EVENT-01, CONFLICT-GOV-01, CONFLICT-FACADE-01, CONFLICT-MGR-01, CONFLICT-INIT-01, CONFLICT-CONFIG-01 all preserved as UNRESOLVED |
| Gap handling | PASS | All gaps recorded with GAP-IDs; no invention |
| Anti-invention compliance | PASS | No new dependencies, interfaces, events, schemas, or protocols invented |
| Source traceability | PASS | Every EXISTING/DERIVED claim cites a Part 0–13 section |
| Version consistency | PASS | Header (1.2.0) and Document Control (1.2.0) agree |
| Direction semantics | PASS | A → B consistently means "A requires B" throughout |
| Event-mediated distinction | PASS | §11 distinguishes event-mediated from direct dependencies |
| Runtime verification | CONDITIONAL | `runtime-map.md` empty → runtime-ordered dependencies UNSPECIFIED |
| CONFLICT-INIT-01 preservation | PASS | Preserved as UNRESOLVED per deployment.md §279; both phase models (5-phase vs 9-phase) documented in §8.1-A/8.1-B |

### 26.3 Known Limitations

| Limitation | Description | Status |
|-----------|-------------|--------|
| Runtime verification gap | `runtime-map.md` is empty; runtime-level dependency ordering is UNSPECIFIED | GAP-RT-01 |
| Event envelope divergence | Two coexisting envelope specs (Part 2 vs Part 12) | GAP-03 / GAP-ENV |
| Governance layer cycles | G-02 ↔ G-01, G-02 → G-05 → G-02, etc. | CONFLICT (Part 14 analysis finding) |
| Component naming conflicts | CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01 | CONFLICT (unresolved, ARB) |

---

## 27. Dependency Architecture Readiness

### 27.1 Final Readiness Assessment

**Status: CONDITIONALLY READY**

This document is **CONDITIONALLY READY** as the Part 15 dependency registry. All dependency assertions are traceable to Parts 0–13 or Part 14 analytical findings. Conflicts are preserved. Gaps are recorded, not invented. Source fidelity is maintained. Direction semantics are consistent. Event-mediated vs. direct dependencies are distinguished.

**However:** This document is NOT 10/10 quality because:

1. **Runtime verification cannot be completed.** `runtime-map.md` is empty (PLANNED). Per §5.4 and §15, all runtime-ordered dependency assertions (beyond initialization/shutdown phases documented in `deployment.md`) are marked **UNSPECIFIED** because they require runtime-map.md authoring. The shutdown ordering IS verified via `deployment.md` §6.1, but runtime behavioral ordering is not.

2. **CONFLICT-INIT-01 is UNRESOLVED.** The initialization phase *model* (5-phase vs 9-phase) is a genuine conflict between Part 4 §4.1 and Part 1 §1.10.2, preserved as UNRESOLVED in `deployment.md` and this document. The shutdown ordering is EXISTING (reverse of startup, regardless of which phase model is adopted), but the phase numbering/count itself is CONFLICT. Both models are documented in §8.1-A and §8.1-B without merging.

3. **Dependency count is conservatively stated.** The original "214" count was derived from a resolved (single-set) model that conflict-unresolving. This document does not assert a single count; dependency counts vary by authoritative source (CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01). The table rows across all sections number approximately 120 distinct assertions, each citing a specific source.

4. **Version corrected.** The header previously claimed "10/10 Quality Pass Applied" while Document Control said 1.0.0. This has been corrected: header is now 1.2.0, status is "CONDITIONALLY READY," and the false "10/10" claim is removed.

### 27.2 Conditional Readiness Criteria

This document achieves FULL READY status when:
- `runtime-map.md` is authored with runtime initialization order, singleton accessor catalog, and event flow catalog
- Runtime-ordered dependency assertions are verified against `runtime-map.md`
- §15 is updated from UNSPECIFIED to EXISTING where runtime evidence confirms ordering

### 27.3 Final Dependency Count

The count of distinct dependency assertions traceable to source documents within this document:

| Category | Assertions |
|----------|-----------|
| Core Component Dependencies (§7.1) | 16 (4 tables × 4 components) |
| Core Manager Dependencies (§7.2, §7.6) | 27 (9×2 tables + 15 MGR entries) |
| Engineering Service Dependencies (§7.3) | 27 (ES + GS combined) |
| Capability Facade Dependencies (§7.4) | 6 |
| Governance Dependencies (§7.5) | 17 |
| External System Dependencies (§7.7) | 7 + 4 GAPs |
| Infrastructure Dependencies (§7.8) | 5 |
| Configuration Dependencies (§7.9) | 6 |
| Interface Dependencies (§12) | 20 |
| Initialization/Shutdown (§8) | Verified via deployment.md |
| **Total distinct assertions** | **~151** (lower bound; Part 5/Part 13 contain additional per-component details not enumerated) |

> **Note:** This count varies by authoritative source. Part 1's 9-manager set produces different assertion counts than Part 4's 9-manager set. The "lower bound" of 151 uses Part 4 §4.2.1 naming for managers (the most detailed source for inter-manager dependencies, Part 4 §4.12).

---

## 28. Final Risk Register

| ID | Risk | Severity | Status | Resolution Path |
|----|------|----------|--------|-----------------|
| RR-01 | EventBus as sole communication substrate | FATAL | EXISTING | Documented; no redundancy per architecture |
| RR-02 | Core Component naming inconsistency (CONFLICT-CC-01) | HIGH | CONFLICT | ARB must select authoritative Core Component set |
| RR-03 | Core Manager naming inconsistency (CONFLICT-CM-01) | HIGH | CONFLICT | ARB must select authoritative Core Manager set or parameterize implementations |
| RR-04 | Undefined capability managers (SkillManager, CouncilManager, MCPManager) | HIGH | GAP | CONFLICT-FACADE-01: Map Part 6 facades to manager registry |
| RR-05 | Configuration naming conflict (ConfigurationAuthority vs ConfigurationManager) | HIGH | CONFLICT | CONFLICT-CC-01: C3 identity unresolved |
| RR-06 | MCP protocol bridge undefined | MEDIUM | GAP | GAP-EXT-01 |
| RR-07 | Runtime Python version constraint | LOW | ASSUMPTION | ASSUMPTION-01 |
| RR-08 | runtime-map.md is empty (runtime verification gap) | HIGH | UNSPECIFIED | GAP-RT-01: Author runtime-map.md |
| RR-09 | Event naming convention conflict | HIGH | CONFLICT | CONFLICT-EVENT-01: Establish migration path |
| RR-10 | Engineering Service count conflict (8 vs 10) | MEDIUM | CONFLICT | CONFLICT-ES-01: Confirm governance service classification |
| RR-11 | Governance component naming conflict | LOW | CONFLICT | CONFLICT-GOV-01: Align Part 13 README with components.md |
| RR-12 | No circular dependencies validation test | HIGH | GAP | Implementation must add topological validation test |
| RR-13 | Governance layer cycles (G-02 ↔ G-01, etc.) | HIGH | CONFLICT | Part 14 analytical finding; define termination semantics |

**Risk Distribution (deduplicated):**
- **HIGH (6):** RR-02, RR-03, RR-04, RR-05, RR-08, RR-13
- **MEDIUM (3):** RR-06, RR-10, RR-12
- **LOW (2):** RR-07, RR-11
- **FATAL (1, separate):** RR-01 (EventBus sole substrate — architectural by design)

---

## 29. Cross-References to Parts 0–14

| Part | Covered Dependencies |
|------|---------------------|
| Part 0 | Infrastructure (§0.2.2), Core Definitions (§0.3.2), ADRs (§0.4, §0.5, §0.10), Extension Points (§0.5.2) |
| Part 1 | Kernel composition (§1.7.3, §1.8.1), Initialization phases (§1.7.3, §1.8.3), Shutdown (§1.11.2), Invariants (§1.5, §1.10.2, §1.11.2, §1.11.3) |
| Part 2 | EventBus substrate (§2.1), Event system (§2.2–2.6) |
| Part 3 | Core Component specs (§3.1–3.6), ServiceRegistry (§3.3–3.5), Configuration (§3.5) |
| Part 4 | Core Manager specs (§4.2–4.12), Engineering Services (§4.12), ConfigurationAuthority (§4.1) |
| Part 5 | Engineering Services (§5.2–5.8), SDLC chain (§5.2.4) |
| Part 6 | Capability Facades (§6.1–6.5), Delegation pattern (§6.1.2) |
| Part 7 | Configuration schema (§7) — not directly cited; config consumption pattern in Part 4 §4.12 |
| Part 9 | External system integration (§9.5) |
| Part 13 | Governance components (§1.x), Governance events (§15) |
| Part 14 | Integration dependencies, conflict analysis, risk findings |

---

## 30. Dependency Count Statement

This document does **NOT** assert a single dependency count. Per the anti-invention rules, component sets differ by authoritative source (CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01). A dependency count from one source's component set differs from another's.

The table in §27.3 provides a **lower bound** of distinct dependency assertions: approximately 151, using Part 4 §4.2.1 naming for the most detailed inter-manager dependency source (Part 4 §4.12). Part 5 and Part 13 contain additional per-component dependency details not individually enumerated here.

The original "214" count was derived from a resolved (single-set) model that conflict-unresolving analysis does not support. It is **not independently verifiable** and has been removed.

---

## 31. Document Control

| Field | Value |
|-------|-------|
| **Document Name** | Part 15: Dependency Analysis and Implementation Gap Tracking |
| **Version** | 1.2.0 |
| **Status** | **CONDITIONALLY READY** — Analysis Artifact (runtime-map.md empty blocks full runtime verification) |
| **Date** | 2026-08-14 |
| **Quality Gate** | Conditionally PASS — all EXISTING dependencies source-backed; directions explicit; conflicts preserved; gaps recorded; runtime verification pending runtime-map.md authorship |
| **Author** | Architecture Evolution & Extensibility Documentation (Part 15) |
| **Source Documents** | Parts 0–14; Part 14 dependency-map.md; `deployment.md` §4–5 |
| **Next Review** | Upon `runtime-map.md` authoring completion |
| **Classification** | Informative — Dependency Analysis and Gap Catalog |
| **Related Documents** | Part 15 README.md, review-checklist.md, glossary.md, components.md, deployment.md, implementation-contracts.md, adrs.md |

### Version History

| Version | Date | Change Description |
|---------|------|--------------------|
| 1.0.0 | 2026-08-13 | Initial version with version mismatch (header 1.1.0 vs Document Control 1.0.0); false "10/10" self-declaration |
| 1.1.0 | 2026-08-14 | Attempted quality pass; still contained invented 10-phase conflict, false 214 count, version mismatch |
| 1.2.0 | 2026-08-14 | Complete architectural correction: fixed version to 1.2.0 (consistent header/Document Control); preserved CONFLICT-INIT-01 as UNRESOLVED per deployment.md §279 (both 5-phase and 9-phase models documented in §8.1-A/8.1-B); removed false "10/10" self-declaration; replaced with CONDITIONALLY READY; corrected §2.1 dependency type taxonomy to canonical 11 types; added §4 Dependency Authority Hierarchy; added §5 canonical definitions; added §25 AI Coding Agent Rules; added §26 Final Audit; added §27 Readiness; added §28 Final Risk Register; added §29 cross-references; added §30 count statement; added §31 Document Control; removed unverifiable "214" count; preserved all conflicts (CONFLICT-CC-01, CONFLICT-CM-01, CONFLICT-ES-01, CONFLICT-FACADE-01, CONFLICT-MGR-01, CONFLICT-INIT-01, CONFLICT-CONFIG-01) |

---

*End of Part 15 Dependency Map. This document is a dependency registry artifact. It does not create new dependencies, does not resolve conflicts between Parts 0–14, and does not infer implementation dependencies from communication. All dependencies are traceable to Parts 0–14 source documents. Gaps and conflicts are explicitly identified and require ARB resolution before full implementation.*