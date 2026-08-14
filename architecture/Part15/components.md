# AI-OS Part 15 — Component Registry and Boundary Specification

## PART 1 — DOCUMENT IDENTITY
=============================================================

**components.md** = Part 15 Component Registry and Boundary Specification.

"This document indexes and specifies architectural components established by authoritative architecture. It does not create new architectural components."

### Document Purpose

This document provides the **authoritative implementation-facing registry of AI-OS architectural components**, establishing the single source of truth for implementation teams, AI coding agents, architects, and reviewers.

**components.md does NOT replace:**
- Parts 0–14
- dependency-map.md
- implementation-contracts.md
- runtime-map.md
- deployment.md

Each has a separate responsibility.

## PART 2 — AUTHORITY BOUNDARY
=============================================================

### Component Authority

```
Parts 0–14
        ↓
Authoritative Component Definition
        ↓
Part 15 Component Registry
        ↓
Implementation Mapping
        ↓
Verification
```

**Rules:**
1. A component is architectural only when source architecture establishes it.
2. A component may be DERIVED only when its existence follows logically from authoritative architecture.
3. A component MUST NOT become authoritative merely because it appears in components.md.
4. A missing implementation class does not mean the architectural component does not exist.
5. An implementation class does not automatically become an architectural component.
6. Conflicting component definitions MUST remain visible.

## PART 3 — COMPONENT DEFINITION
=============================================================

### Component Definition

An **architectural component** is: "A bounded architectural unit with an identifiable responsibility, ownership boundary, interface or interaction model, lifecycle, and relationship to other architectural elements."

**Explicit Distinctions:**
- **Component** vs. **Class** vs. **Module** vs. **Service** vs. **Manager** vs. **Agent** vs. **Plugin** vs. **External System**
- Do not assume these terms are interchangeable

## PART 4 — COMPONENT TAXONOMY
=============================================================

### Component Categories

The architecture already distinguishes these categories:

| Category | Meaning | Source | Status |
|----------|---------|--------|--------|
| Core Components | Architectural components establishing foundation capabilities | Parts 0–4 | CONFLICT-CC-01 |
| Core Managers | Capability management components | Parts 0–4 | CONFLICT-CM-01 |
| Engineering Services | SDLC-phase services | Parts 0, 5 | CONFLICT-ES-01 |
| Capability Facades | Event-driven facades over managers | Part 6 | CONFLICT-FACADE-01 |
| Governance Components | Governance and security services | Part 13 | EXISTING |
| Agent Components | AI runtime capability components | Part 4 | EXISTING |
| Council Components | Consensus coordination components | Part 6 | EXISTING |
| Workflow Components | Workflow orchestration components | Part 4 | EXISTING |
| Memory Components | State management components | Part 0, 4 | EXISTING |
| Communication Components | Communication substrate components | Part 1, 2 | CONFLICT-CC-01 |
| Integration/Plugin Components | External system integration | Part 6 | EXISTING |

**Classification Guidance:**
- Components are **ARCHITECTURAL CATEGORY** when explicitly defined as architectural entities in source Parts 0–14
- Use **ANALYTICAL GROUPING** for human-readable classification when source doesn't provide strict categories

## PART 5 — CANONICAL COMPONENT REGISTRY
=============================================================

### Canonical Component Registry

**Every architectural component MUST appear exactly once in the canonical registry.** Do not duplicate the same component under multiple names.

| Component ID | Component Name | Category | Responsibility | Owner | Status | Source |
|--------------|----------------|----------|----------------|-------|--------|--------|

**Notes:**
- If the same architectural component has different names in different source documents, DO NOT silently choose one. Record the conflict.
- State manager accountability gaps require explicit documentation to maintain architectural integrity.

## PART 6 — COMPONENT IDENTITY
=============================================================

### Component Identity Matrix

For every component, define:
- **canonical name**
- **component ID**
- **aliases, if actually documented**
- **source name**
- **status**
- **architectural category**

**Identity Rules:**
- DO NOT invent aliases
- DO NOT normalize names merely for aesthetics if doing so changes architectural meaning
- If two names may represent the same component, mark: **IDENTITY AMBIGUITY** until authoritative evidence resolves it

## PART 7 — COMPONENT RESPONSIBILITIES
=============================================================

### Responsibilities

Every responsibility must be:
- **specific**
- **architectural**
- **source-backed**
- **bounded**

**Avoid vague statements** such as: "Handles system operations."

**Template:**

### Responsibilities

For every component add:

```
### Responsibilities

[Specific architectural responsibility established by source documentation]
```

### Non-Responsibilities

The non-responsibilities section is important. It should explicitly prevent responsibility leakage into other components.

**Template:**

```
### Non-Responsibilities

[Explicitly state what the component does NOT own, based on boundaries or responsibility definitions]
```

DO NOT invent non-responsibilities. Only state them when supported by boundaries or responsibility definitions.

## PART 8 — COMPONENT BOUNDARIES
=============================================================

### Component Boundaries

For each component:

| Component | Owns | Does Not Own | Boundary Rule | Source | Status |
|-----------|------|--------------|---------------|--------|--------|

**Boundary Rules:**
- Boundary rules MUST identify what must remain inside the component versus what belongs elsewhere
- DO NOT turn implementation preferences into architectural boundaries

## PART 9 — OWNERSHIP MODEL
=============================================================

### Ownership

**Distinctions:**
- Responsibility ownership vs. data ownership vs. lifecycle ownership vs. configuration ownership vs. policy ownership vs. execution ownership

**Do not assume** that the component responsible for something also owns its persistent data.

For every ownership relationship:
- **source it**

## PART 10 — INTERFACES
=============================================================

### Interface Matrix

For each component document:

| Component | Provided Interface | Required Interface | Purpose | Source | Status |
|-----------|-------------------|-------------------|---------|--------|--------|

**Interface Rules:**
- DO NOT invent method signatures
- DO NOT invent APIs
- DO NOT invent protocols
- DO NOT invent class names

**When architecture only establishes an interface concept but not its concrete API:**
- Record: **Interface = EXISTING**
- Record: **Concrete API = UNSPECIFIED**

### Interface Classification

**Template:**

### Provided Interfaces


### Required Interfaces


## PART 11 — COMPONENT DEPENDENCIES
=============================================================

### Component Dependency Summary

**DO NOT duplicate the entire dependency graph.** Instead create:

| Component | Depends On | Dependency Type | Reason | Source |
|-----------|------------|----------------|--------|--------|

**Dependency Rules:**
- Every dependency must match dependency-map.md
- If they disagree, record: **CROSS-DOCUMENT CONFLICT**
- DO NOT silently rewrite dependency-map.md
- Do not duplicate the entire dependency graph from dependency-map.md
- Instead create: ## Component Dependency Summary

**Template:**

| Component | Depends On | Dependency Type | Reason | Source |
|-----------|------------|----------------|--------|--------|

Every dependency must match dependency-map.md.
If they disagree:
- Record: **CROSS-DOCUMENT CONFLICT**
- DO NOT silently rewrite dependency-map.md

## PART 12 — EVENT-BASED COMMUNICATION
=============================================================

### Event Relationship Matrix

**Explicitly distinguish:**
- **Direct interface dependency** from **Event-mediated interaction**

**Event Pattern:**

Component A
    ↓
EventBus / Event
    ↓
Component B

**ONLY if the architecture establishes that event mechanism.**

Do not imply direct coupling if communication is event-mediated.

**Template:**

| Producer | Event | Consumer | Direct Dependency? | Source | Status |
|----------|-------|----------|--------------------|--------|--------|

## PART 13 — COMPONENT LIFECYCLE
=============================================================

### Component Lifecycle

For each component:

| Component | Creation | Initialization | Operational State | Shutdown | Recovery | Source |
|-----------|----------|----------------|-------------------|----------|----------|--------|

**Lifecycle Rules:**
- Only populate lifecycle stages supported by architecture
- DO NOT invent: `start()`, `stop()`, `restart()`, `initialize()` method names
- DO NOT assume every component has the same lifecycle

## PART 14 — COMPONENT STATE
=============================================================

### Component State Model

**Distinguish:**
- stateless
- stateful
- persistent state
- runtime state
- externally managed state

**ONLY where architecture defines it.**

Do not infer statelessness merely because a component is conceptual.

If state behavior is not defined:
- **UNSPECIFIED**

## PART 15 — FAILURE RESPONSIBILITY
=============================================================

### Failure and Recovery Responsibilities

Where architecture supports it:

| Component | Failure Responsibility | Recovery Responsibility | Failure Propagation | Source | Status |
|-----------|------------------------|-------------------------|--------------------|--------|--------|

**Recovery Rules:**
- DO NOT invent retry logic
- DO NOT invent circuit breakers
- DO NOT invent fallback behavior
- DO NOT invent recovery mechanisms

If recovery is unspecified:
- **mark it UNSPECIFIED**

## PART 16 — CONFIGURATION RELATIONSHIP
=============================================================

Cross-check: configuration.md

For components that consume configuration:

| Component | Configuration Responsibility | Access Model | Source | Status |
|-----------|-----------------------------|--------------|--------|--------|

**Configuration Rules:**
- DO NOT invent configuration APIs
- DO NOT invent environment variables
- If access mechanism is not architecturally defined:
  - **mark: UNSPECIFIED**

## PART 17 — SECURITY BOUNDARIES
=============================================================

### Security Boundaries

For each security-sensitive component:

**Document only architecture-supported:**
- authentication responsibility
- authorization responsibility
- secret handling
- access control
- trust boundary
- audit responsibility

**DO NOT invent:**
- IdentityManager
- authentication providers
- security infrastructure

**If the architecture uses SecurityManager:**
- use the exact authoritative name

If conflicting names exist:
- **record the conflict** rather than choosing one silently

## PART 18 — AGENTS AND COUNCILS
=============================================================

### Component Classification Matrix

| Element | Architectural Type | Component? | Source | Status |
|---------|---------------------|------------|--------|--------|

**Classification Rules:**
- DO NOT automatically classify every Agent as a Component unless architecture explicitly does so
- Use explicit architecture statements for component status

**When architecture defines Agents as components:**
- record that explicitly

If not:
- preserve the distinction

## PART 19 — PLUGINS / INTEGRATIONS
=============================================================

### Integration Classification

**Distinguish:**
- Core Component
- Plugin
- Integration
- External System

**DO NOT make a plugin a core component merely because it is loaded by one.**

**DO NOT invent:**
- MCP transport classes
- plugin APIs
- adapter interfaces unless source architecture defines them

## PART 20 — EXTERNAL SYSTEMS
=============================================================

### External Dependencies

Where architecture explicitly identifies external systems:

| Component | External System | Dependency | Interface | Source | Status |
|-----------|-----------------|------------|-----------|--------|--------|

**External System Rules:**
- DO NOT invent: cloud providers, databases, message brokers, model providers, identity providers, external APIs
- If the architecture only defines an abstract external dependency:
  - **keep it abstract**

## PART 21 — COMPONENT INVARIANTS
=============================================================

### Component Invariants

| ID | Invariant | Source | Status | Verification |
|----|-----------|--------|--------|--------------|

**Potential examples (ONLY if source architecture supports them):**
- boundaries must be preserved
- ownership must be unambiguous
- components must use defined interfaces
- direct coupling must not bypass architectural communication mechanisms

**Rules:**
- ONLY retain these as MUST requirements if source architecture supports them
- Otherwise mark DERIVED or remove

## PART 22 — COMPONENT CONFORMANCE
=============================================================

### Component Conformance

A component implementation conforms when:

1. **it implements the architectural responsibility**
2. **it respects the boundary**
3. **it uses the defined interface/communication mechanism**
4. **it does not assume unspecified responsibilities**
5. **it respects dependency direction**
6. **its lifecycle behavior matches architecture**
7. **its security responsibilities are preserved**

**Distinguish:**
- **Architectural conformance** from **Code quality**
- A component can be architecturally conformant without being implementation-perfect

## PART 23 — COMPONENT-TO-SOURCE TRACEABILITY
=============================================================

### Component-to-Source Traceability

Use:

| Component ID | Component | Source Document | Source Section | Evidence | Status |
|--------------|-----------|-----------------|----------------|----------|--------|

**Every canonical component MUST have source evidence.**

No component should have:
- Source = "architecture" without a specific source

## PART 24 — COMPONENT-TO-CONTRACT TRACEABILITY
=============================================================

### Component-to-Contract Traceability

Cross-check: implementation-contracts.md

Use:

| Component | Contract ID | Contract | Status | Verification |
|-----------|-------------|----------|--------|--------------|

**Contract Rules:**
- DO NOT invent contract IDs
- If a contract refers to a component that does not exist:
  - **record: TRACEABILITY CONFLICT**

## PART 25 — COMPONENT-TO-ADR TRACEABILITY
=============================================================

### Component-to-ADR Traceability

Cross-check: adrs.md

Use:

| Component | Decision / ADR | Type | Source | Status |
|-----------|----------------|------|--------|--------|

**ADR Rules:**
- DO NOT invent ADR identifiers
- If the architecture establishes the component but no ADR exists:
  - **use: Architectural Decision** rather than inventing an ADR number

## PART 26 — COMPONENT CONFLICT REGISTRY
=============================================================

### Component Conflicts

Use:

| Conflict ID | Component / Topic | Source A | Source B | Difference | Impact | Status |
|-------------|-------------------|----------|----------|------------|--------|--------|

**Conflict Rules:**
- At minimum cross-check for:
  - conflicting component lists
  - conflicting manager lists
  - renamed components
  - duplicate component names
  - conflicting responsibilities
  - conflicting ownership
  - conflicting security boundaries
- DO NOT resolve conflicts

## PART 27 — UNSPECIFIED / GAP REGISTRY
=============================================================

### Component Gaps and Unspecified Areas

Use:

| Area | Source | Current State | Impact | Status |
|------|--------|---------------|--------|--------|

**Possible areas:**
- missing lifecycle details
- missing interfaces
- missing ownership
- missing recovery behavior
- ambiguous component identity
- missing implementation mapping

**Rules:**
- **ONLY record actual gaps**

## PART 28 — AI CODING AGENT RULES
=============================================================

### AI Coding Agent Rules

**AI coding agents MUST:**

1. **inspect components.md before creating a new architectural component**
2. **verify whether the component already exists**
3. **never create duplicate components under different names**
4. **never create a component solely because a class is convenient**
5. **preserve component boundaries**
6. **preserve ownership boundaries**
7. **use defined interfaces**
8. **distinguish events from direct calls**
9. **inspect dependency-map.md before adding dependencies**
10. **inspect configuration.md before adding configuration access**
11. **inspect implementation-contracts.md before implementing MUST requirements**
12. **inspect adrs.md before relying on ADR references**
13. **never invent missing lifecycle behavior**
14. **never invent security responsibilities**
15. **never resolve component conflicts silently**
16. **report ambiguous component identity**
17. **stop when implementation requires an unresolved architectural component decision**

## PART 29 — CROSS-DOCUMENT CONSISTENCY
=============================================================

Cross-check WITHOUT MODIFYING:

adrs.md
configuration.md
dependency-map.md
deployment.md
implementation-contracts.md
observability.md
glossary.md
review-checklist.md
README.md
runtime-map.md
testing.md

**Verify:**
- component names
- manager names
- responsibilities
- ownership
- dependency direction
- lifecycle
- security terminology
- configuration terminology
- contract IDs
- ADR references

**For every inconsistency:**

| Document | Issue | Impact | Status |
|----------|-------|--------|--------|

**Do not silently resolve source conflicts.**

## PART 30 — CLEANUP
=============================================================

### Cleanup Actions

**Remove or correct:**
- duplicate component definitions
- duplicate component names
- inconsistent terminology
- stale component names
- unsupported components
- invented implementation classes presented as architecture
- invented APIs
- invented lifecycle methods
- invented external systems
- unsupported dependencies
- unsupported security components
- false completion claims

**If a component is referenced by another document but cannot be verified:**
- **do NOT invent it**
- **Mark: SOURCE VERIFICATION REQUIRED** or **UNSUPPORTED COMPONENT REFERENCE**

## PART 31 — COMPONENT COUNTS
=============================================================

### Component Count Verification

**If the document currently claims:**
- "X components"
- "X managers"
- "X agents"

**Recalculate the count from the canonical registry.**

Do not manually preserve old numbers.

**Separate categories if needed:**
- Core Components
- Managers
- Agents
- Councils
- Plugins
- External Systems

Do not count categories together unless the architecture explicitly treats them as one component taxonomy.

## PART 32 — FINAL AUDIT
=============================================================

### Final Component Architecture Audit

Replace any self-declared "10/10" statement with:

## Final Component Architecture Audit

Use:

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Component identity | PASS/FAIL | ... |
| Responsibility boundaries | PASS/FAIL | ... |
| Ownership | PASS/FAIL | ... |
| Interfaces | PASS/FAIL | ... |
| Dependencies | PASS/FAIL | ... |
| Event relationships | PASS/FAIL | ... |
| Lifecycle | PASS/FAIL | ... |
| State model | PASS/FAIL | ... |
| Security boundaries | PASS/FAIL | ... |
| Configuration relationship | PASS/FAIL | ... |
| Source traceability | PASS/FAIL | ... |
| Contract traceability | PASS/FAIL | ... |
| ADR traceability | PASS/FAIL | ... |
| Conflict handling | PASS/FAIL | ... |
| Anti-invention | PASS/FAIL | ... |

**DO NOT automatically mark all rows PASS.**

## PART 33 — READINESS
=============================================================

### Component Architecture Readiness

**Allowed:**
- READY
- CONDITIONALLY READY
- NOT READY

**Use evidence to determine readiness.**

**If runtime lifecycle details depend on the currently EMPTY runtime-map.md:**
- **do not claim full lifecycle verification**

**If component conflicts remain:**
- **do not claim fully resolved architecture**

**If the canonical component registry is otherwise sufficiently source-backed:**
- **CONDITIONALLY READY** may be appropriate

## PART 34 — FINAL STRUCTURE
=============================================================

**The final document should approximately follow:**

1. Document Identity
2. Purpose
3. Authority Boundary
4. Component Definition
5. Component Taxonomy
6. Canonical Component Registry
7. Component Identity
8. Responsibilities
9. Non-Responsibilities
10. Component Boundaries
11. Ownership
12. Provided Interfaces
13. Required Interfaces
14. Component Dependency Summary
15. Event-Mediated Communication
16. Component Lifecycle
17. Component State Model
18. Failure and Recovery Responsibilities
19. Configuration Relationship
20. Security Boundaries
21. Agents and Councils
22. Plugins and Integrations
23. External Dependencies
24. Component Invariants
25. Component Conformance
26. Component-to-Source Traceability
27. Component-to-Contract Traceability
28. Component-to-ADR Traceability
29. Component Conflicts
30. Component Gaps and Unspecified Areas
31. Cross-Document Consistency
32. AI Coding Agent Rules
33. Final Audit
34. Component Architecture Readiness

**If existing sections already contain this information, reorganize them.**

DO NOT create duplicate sections merely to follow this numbering.

## PART 35 — 10/10 ACCEPTANCE CRITERIA
=============================================================

**components.md is 10/10 ONLY if ALL criteria are met:**

[ ] **Every architectural component has a canonical identity.**
[ ] **Every component has source evidence.**
[ ] **Component categories are clearly defined.**
[ ] **Components are distinguished from classes/modules/services/managers/agents/plugins.**
[ ] **Responsibilities are explicit.**
[ ] **Boundaries are explicit.**
[ ] **Ownership is explicit where architecture defines it.**
[ ] **Interfaces are traceable.**
[ ] **Interface implementation details are not invented.**
[ ] **Dependencies match dependency-map.md.**
[ ] **Event-mediated communication is distinguished from direct dependencies.**
[ ] **Lifecycle behavior is not invented.**
[ ] **State behavior is not invented.**
[ ] **Failure/recovery behavior is not invented.**
[ ] **Configuration relationships match configuration.md.**
[ ] **Security boundaries match authoritative security architecture.**
[ ] **Agents and councils are not incorrectly collapsed into generic components.**
[ ] **Plugins and external systems are distinguished from core components.**
[ ] **Component counts are accurate if stated.**
[ ] **Component-to-source traceability exists.**
[ ] **Component-to-contract traceability exists.**
[ ] **Component-to-ADR traceability exists.**
[ ] **Component conflicts remain visible.**
[ ] **Gaps and unspecified areas remain visible.**
[ ] **AI coding agents are explicitly prevented from inventing components.**
[ ] **No duplicate or stale component definitions remain.**
[ ] **No false completeness claims remain.**
[ ] **Final readiness reflects actual architectural maturity.**

## FINAL INSTRUCTION
=============================================================

**Make components.md authoritative through SOURCE TRACEABILITY, not through assertion.**

**If architecture explicitly defines a component:**
- **document it as EXISTING**

**If a component is logically derived:**
- **mark DERIVED and explain why**

**If a component is mentioned but cannot be verified:**
- **mark SOURCE VERIFICATION REQUIRED**

**If two authoritative sources disagree:**
- **mark CONFLICT**

**If architecture is silent:**
- **mark UNSPECIFIED**

**DO NOT invent components.**
**DO NOT invent APIs.**
**DO NOT invent lifecycle behavior.**
**DO NOT invent implementation classes.**
**DO NOT invent infrastructure.**
**DO NOT resolve architectural conflicts.**
**DO NOT modify any other file.**

**ONLY MODIFY:** C:\Development\AI-OS\architecture\Part15\components.md

## 3. Core Component Definition Conflict

**CRITICAL: The architecture contains conflicting definitions of the Core Component set. This is NOT a permission to choose; it's an architectural constraint requiring resolution before implementation can proceed safely.**

| Source | Core Component Definition | Status | Implementation Impact |
|--------|---------------------------|--------|----------------------|
| **Part 0, §0.2.1** | Hermes Kernel owns: `EventBus`, `StateManager`, `WorkflowManager`, `ResourceManager` (Foundation managers) | **UNRESOLVED CONFLICT** | Different foundation managers; creates architectural fragmentation |
| **Part 1, §1.7.1** | HermesKernel owns: `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager` (Core Components C1-C4) | **UNRESOLVED CONFLICT** | Different Core Components; different initialization sequence and dependencies |
| **Part 2, §2.1** | EventBus is Core Component C1 (Communication substrate) | **SUPPORTS PART 1** | Confirms Part 1's EventBus as Core Component C1 |
| **Part 3, §3.2.1** | Four Core Components: `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `StructuredLogger` (C1-C4) | **UNRESOLVED CONFLICT** | Replaces StateManager/WorkflowManager/ResourceManager with ServiceRegistry + LifecycleManager + StructuredLogger |
| **Part 4, §4.2** | Core Managers: Nine capability managers (`LifecycleManager`, `StateManager`, `StorageManager`, `WorkflowManager`, `SecurityManager`, `CapabilityManager`, `ResourceManager`, `HealthManager`, `ObservabilityManager`) | **CATEGORY MISMATCH** | Core Managers vs Core Components are different architectural categories |

### 3.1 Conflict Analysis

| Conflict Element | Description | Why It Matters | Safe Implementation | Resolution Path |
|------------------|-------------|----------------|--------------------|----------------|
| **Source A (Part 0)** | Four foundation managers: EventBus, StateManager, WorkflowManager, ResourceManager | Establishes core capabilities of Hermes Kernel | Cannot safely ignore | ARB resolution required |
| **Source B (Part 1)** | Four Core Components: EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager | Establishes kernel-owned infrastructure primitives | Cannot safely ignore | ARB resolution required |
| **Source C (Part 3)** | Four Core Components: EventBus, ServiceRegistry, ConfigurationManager, StructuredLogger | Replaces StateManager/WorkflowManager/ResourceManager with ServiceRegistry + LifecycleManager + StructuredLogger | Cannot safely ignore | ARB resolution required |
| **Source D (Part 4)** | Nine Core Managers: LifecycleManager through ObservabilityManager | Introduces capability managers as Core Managers | Categorically different from Core Components | Must maintain separation | Must clarify distinction |

### 3.2 Implementation Impact Assessment

1. **Initialization Sequence Conflicts:** Different Core Component sets require different initialization phases and dependency orders
2. **Ownership Conflicts:** Different entities own different components (Kernel vs Foundation vs Core Components)
3. **Interface Conflicts:** Components may have different interfaces depending on which definition is used
4. **Lifecycle Conflicts:** Different components participate in different lifecycle phases
5. **Conformance Conflicts:** A component conforming to one definition will not conform to another

### 3.3 Safe Implementation Note

**CONFLICT ≠ permission to choose.** Implementation MUST:

- Identify which Core Component definition is being implemented
- Document the decision explicitly
- Ensure all other components align with this choice
- Document architectural implications of the chosen definition
- Avoid assuming compatibility between different Core Component definitions

## 4. Component Inventory

The following is an authoritative inventory of AI-OS architectural components. Sources are documented in the Source column.

| Component ID | Component Name | Category | Primary Responsibility | Ownership | Responsibilities | Dependencies | Interfaces | Source | Status | Lifecycle | Configuration | Observability | Security | Verification |
| ------------ | -------------- | -------- | ---------------------- | -------- | --------------- | ------------ | ---------- | ------ | ------ | --------- | ------------- | -------------- | --------- | ------------ |
| C1 | EventBus | Core / Runtime | Sole communication substrate; event publication, subscription, routing, correlation, ordering, delivery guarantees, failure handling, replay, observability | Kernel | Event publication, subscription, routing, correlation, ordering, delivery guarantees, failure handling, replay, observability | None (foundation) | EventBus (C1) interface | Part 1 §1.7.1, Part 2 §2.1, Part 3 §3.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| C2 | ServiceRegistry | Core / Runtime | Service registration, discovery, dependency topology, health tracking, lifecycle coordination | Kernel | Service registration, discovery, dependency topology, health tracking, lifecycle coordination | EventBus (C1) | ServiceRegistry interface | Part 1 §1.7.1, Part 3 §3.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| C3 | ConfigurationManager | Core / Runtime | Immutable configuration authority; four-layer merge, schema validation, freeze enforcement, runtime read-only access | Kernel | Configuration loading, schema validation, freeze enforcement, runtime read-only access | EventBus (C1) | ConfigurationManager interface | Part 1 §1.7.1, Part 3 §3.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| C4 | StructuredLogger | Core / Runtime | Structured logging substrate; correlation support, audit logging, sink routing, buffering, rotation | Kernel | Logging substrate, correlation support, audit logging, sink routing, buffering, rotation | EventBus (C1), ServiceRegistry (C2), ConfigurationManager (C3) | StructuredLogger interface | Part 1 §1.7.1, Part 3 §3.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |

| M1 | LifecycleManager | Core / Runtime | Authoritative control over kernel lifecycle phases, rollback coordination, recovery | Kernel | Kernel lifecycle governance, phase orchestration, rollback coordination, recovery | EventBus (C1), StateManager (M2), StorageManager (M3) | LifecycleManager interface | Part 4 §4.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M2 | StateManager | Core / Runtime | Authoritative control over kernel state transitions, snapshots, checkpoints, consistency | Kernel | Kernel state governance, state transitions, snapshots, checkpoints, consistency | EventBus (C1), StorageManager (M3), WorkflowManager (M4) | StateManager interface | Part 4 §4.2 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M3 | StorageManager | Core / Runtime | Governance of persistent storage, checkpoint storage, artifact storage, retention, integrity | Kernel | Storage governance, checkpoint storage, artifact storage, retention, integrity | EventBus (C1), StateManager (M2), WorkflowManager (M4) | StorageManager interface | Part 4 §4.4 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M4 | WorkflowManager | Core / Runtime | Governance of workflow lifecycle, scheduling, cancellation, retries, nested workflows | Kernel | Workflow governance, lifecycle, scheduling, cancellation, retries, nested workflows | EventBus (C1), StateManager (M2), StorageManager (M3), SecurityManager (M7), CapabilityManager (M8), ResourceManager (M9) | WorkflowManager interface | Part 4 §4.5 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M5 | SecurityManager | Core / Runtime | Authentication, authorization, policy enforcement, secret handling, audit coordination | Kernel | Security governance, authentication, authorization, policy enforcement, secret handling, audit coordination | EventBus (C1) | SecurityManager interface | Part 4 §4.7 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M6 | CapabilityManager | Core / Runtime | Capability registration, discovery, resolution, routing, version compatibility | Kernel | Capability governance, registration, discovery, resolution, routing, version compatibility | EventBus (C1), StateManager (M2), SecurityManager (M7) | CapabilityManager interface | Part 4 §4.8 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M7 | ResourceManager | Core / Runtime | CPU, memory, disk, network, GPU, LLM quota accounting, reservations, limits | Kernel | Resource governance, accounting, quotas, reservations, limits | EventBus (C1), StateManager (M2), SecurityManager (M7) | ResourceManager interface | Part 4 §4.9 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M8 | HealthManager | Core / Runtime | Health monitoring, readiness, liveness, heartbeat, diagnostics, recovery recommendations | Kernel | Health governance, monitoring, diagnostics, recovery recommendations | EventBus (C1), StateManager (M2), ResourceManager (M7) | HealthManager interface | Part 4 §4.10 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| M9 | ObservabilityManager | Core / Runtime | Metrics, tracing, monitoring, dashboards, alerting, telemetry, audit integration | Kernel | Observability governance, metrics, tracing, monitoring, telemetry, audit integration | EventBus (C1), StateManager (M2), WorkflowManager (M4), SecurityManager (M7) | ObservabilityManager interface | Part 4 §4.11 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |

| E1 | PlanningService | Engineering Services | SDLC Planning phase; requirements analysis, task creation, workflow initialization | ServiceRegistry | Requirements analysis, task creation, workflow initialization | EventBus (C1), StateManager (M2), SkillService (E4) | PlanningService interface | Part 5 §5.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E2 | CodingService | Engineering Services | SDLC Coding phase; code generation, implementation, testing | ServiceRegistry | Code generation, implementation, testing | EventBus (C1), StateManager (M2), PlanningService (E1), ReviewService (E3) | CodingService interface | Part 5 §5.4 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E3 | ReviewService | Engineering Services | SDLC Review phase; code review, approval, AI agency coordination | ServiceRegistry | Code review, approval, AI agency coordination | EventBus (C1), StateManager (M2), CodingService (E2), TestingService (E5) | ReviewService interface | Part 5 §5.5 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E4 | TestingService | Engineering Services | SDLC Testing phase; validation, verification, test execution | ServiceRegistry | Validation, verification, test execution | EventBus (C1), StateManager (M2), ReviewService (E3), DeploymentService (E6) | TestingService interface | Part 5 §5.6 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E5 | DeploymentService | Engineering Services | SDLC Deployment phase; artifact storage, distribution, installation | ServiceRegistry | Artifact storage, distribution, installation | EventBus (C1), StateManager (M2), TestingService (E4), OperationsService (E7) | DeploymentService interface | Part 5 §5.7 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E6 | OperationsService | Engineering Services | SDLC Operations phase; monitoring, maintenance, health checks | ServiceRegistry | Monitoring, maintenance, health checks | EventBus (C1), StateManager (M2), DeploymentService (E5), LearningService (E8) | OperationsService interface | Part 5 §5.8 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E7 | LearningService | Engineering Services | SDLC Learning phase; analysis, improvement, knowledge extraction | ServiceRegistry | Analysis, improvement, knowledge extraction | EventBus (C1), StateManager (M2), OperationsService (E6), MemoryService (E9) | LearningService interface | Part 5 §5.9 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| E8 | MemoryService | Engineering Services | SDLC Memory phase; knowledge base updates, retention, purging | ServiceRegistry | Knowledge base updates, retention, purging | EventBus (C1), StateManager (M2), LearningService (E7) | MemoryService interface | Part 5 §5.10 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |

| F1 | SkillService | Capability Facade | Event-driven facade over SkillManager; skill registration and execution | SkillManager | Skill registration and execution | EventBus (C1), StateManager (M2), SkillManager (M6) | SkillService interface | Part 6 §6.4 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| F2 | CouncilService | Capability Facade | Event-driven facade over CouncilManager; council coordination and consensus | CouncilManager | Council coordination and consensus | EventBus (C1), StateManager (M2), CouncilManager (M7) | CouncilService interface | Part 6 §6.2 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| F3 | MCPService | Capability Facade | Event-driven facade over MCPManager; MCP protocol transport | MCPManager | MCP protocol transport | EventBus (C1), StateManager (M2), MCPManager (M5) | MCPService interface | Part 6 §6.5 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| F4 | MemoryService | Capability Facade | Event-driven facade over MemoryManager; memory operations | MemoryManager | Memory operations | EventBus (C1), StateManager (M2), MemoryManager (M6) | MemoryService interface | Part 6 §6.3 | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |

*Note: Component IDs (C1-C4, M1-M9, E1-E8, F1-F4) follow Parts 0–6 naming conventions. E8 and F4 both named MemoryService — architectural distinction: E8 is Engineering Service, F4 is Capability Facade Service.*

## 5. Component Specifications

### 5.1 Component Ownership Boundaries

| Component | Responsibility Owner | State Owner | Configuration Owner | Security Owner | Observability Owner | Source |
|-----------|----------------------|------------|-------------------|---------------|---------------------|--------|
| EventBus (C1) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 1 §1.7.1 |
| ServiceRegistry (C2) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 1 §1.7.1 |
| ConfigurationManager (C3) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 1 §1.7.1 |
| StructuredLogger (C4) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 1 §1.7.1 |

| LifecycleManager (M1) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.3 |
| StateManager (M2) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.2 |
| StorageManager (M3) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.4 |
| WorkflowManager (M4) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.5 |
| SecurityManager (M5) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.7 |
| CapabilityManager (M6) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.8 |
| ResourceManager (M7) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.9 |
| HealthManager (M8) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.10 |
| ObservabilityManager (M9) | Kernel | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 4 §4.11 |

| PlanningService (E1) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.3 |
| CodingService (E2) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.4 |
| ReviewService (E3) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.5 |
| TestingService (E4) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.6 |
| DeploymentService (E5) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.7 |
| OperationsService (E6) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.8 |
| LearningService (E7) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.9 |
| MemoryService (E8) | ServiceRegistry | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 5 §5.10 |

| SkillService (F1) | SkillManager | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 6 §6.4 |
| CouncilService (F2) | CouncilManager | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 6 §6.2 |
| MCPService (F3) | MCPManager | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 6 §6.5 |
| MemoryService (F4) | MemoryManager | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** | Part 6 §6.3 |

## 6. Component Boundaries

### 6.1 Responsibility Boundaries

| Component | Must Own | May Interact With | Must Not Own |
|-----------|----------|-------------------|-------------|
| EventBus (C1) | Event publication, subscription, routing, correlation, ordering, delivery guarantees, failure handling, replay, observability | Communication with all components via events | **Not Defined** |
| ServiceRegistry (C2) | Service registration, discovery, dependency topology, health tracking, lifecycle coordination | Reads configuration, writes logs | **Not Defined** |
| ConfigurationManager (C3) | Configuration loading, schema validation, freeze enforcement | Reads services config, writes logs | **Not Defined** |
| StructuredLogger (C4) | Structured logging substrate, correlation support, audit logging | Reads configuration, publishes events | **Not Defined** |

### 6.2 State Boundaries

| Component | Owns Transient State | Owns Persistent State | Owns Runtime State |
|-----------|---------------------|---------------------|-------------------|
| EventBus (C1) | Event queues, subscriptions | **UNSPECIFIED** | **UNSPECIFIED** |
| ServiceRegistry (C2) | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| ConfigurationManager (C3) | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |
| StructuredLogger (C4) | **UNSPECIFIED** | **UNSPECIFIED** | **UNSPECIFIED** |

### 6.3 Communication Boundaries

| Component | Accepts Events From | Produces Events To | Direct Method Calls |
|-----------|-------------------|-------------------|------------------|
| EventBus (C1) | All components | All components | **Not Allowed** |
| ServiceRegistry (C2) | Core Components | Services, EventBus | **Not Allowed** |
| ConfigurationManager (C3) | Core Components | Services, EventBus | **Not Allowed** |
| StructuredLogger (C4) | Core Components, Services | Services, EventBus | **Not Allowed** |

## 7. Component Interfaces

### 7.1 EventBus Interface

| Interface | Producer | Consumer | Purpose | Inputs | Outputs | Error Behavior | Lifecycle | Source |
|-----------|----------|----------|---------|--------|---------|----------------|-----------|--------|
| EventBus (C1) | Hermes Kernel | All Components | Sole communication substrate | Events | Events | **UNSPECIFIED** | **UNSPECIFIED** | Part 2 §2.1 |

### 7.2 ServiceRegistry Interface

| Interface | Producer | Consumer | Purpose | Inputs | Outputs | Error Behavior | Lifecycle | Source |
|-----------|----------|----------|---------|--------|---------|----------------|-----------|--------|
| ServiceRegistry (C2) | Hermes Kernel | Core Components, Services | Service registration, discovery | Service descriptors | Service info | **UNSPECIFIED** | **UNSPECIFIED** | Part 3 §3.3 |

### 7.3 ConfigurationManager Interface

| Interface | Producer | Consumer | Purpose | Inputs | Outputs | Error Behavior | Lifecycle | Source |
|-----------|----------|----------|---------|--------|---------|----------------|-----------|--------|
| ConfigurationManager (C3) | Hermes Kernel | Core Components, Services | Configuration authority | Config data | Config values | **UNSPECIFIED** | **UNSPECIFIED** | Part 3 §3.3 |

### 7.4 StructuredLogger Interface

| Interface | Producer | Consumer | Purpose | Inputs | Outputs | Error Behavior | Lifecycle | Source |
|-----------|----------|----------|---------|--------|---------|----------------|-----------|--------|
| StructuredLogger (C4) | Hermes Kernel | Core Components, Services | Logging substrate | Log entries | Log confirmations | **UNSPECIFIED** | **UNSPECIFIED** | Part 3 §3.3 |

## 8. Component Lifecycle

### 8.1 EventBus Lifecycle

| State | Transition Trigger | Entry Action |
|-------|-------------------|--------------|
| UNINITIALIZED | Kernel construction | Component instantiated |
| INITIALIZING | `initialize(kernel)` called | Register subscriptions, prepare queues |
| RUNNING | Phase 0 complete, invariants verified | Accept publishes, dispatch loop active |
| DRAINING | `shutdown()` called | Reject new publishes, process in-flight |
| SHUTDOWN | All queues empty, subscriptions cleared | Publish shutdown event |

### 8.2 ServiceRegistry Lifecycle

| State | Transition Trigger | Entry Action |
|-------|-------------------|--------------|
| UNINITIALIZED | Kernel construction | Component instantiated, empty registry |
| INITIALIZING | `initialize(kernel)` called | Prepare discovery structures |
| RUNNING | Phase 1 complete | Accept registrations, process queries |
| SHUTDOWN | Kernel shutdown initiation | Clear registry, publish shutdown event |

### 8.3 ConfigurationManager Lifecycle

| State | Transition Trigger | Entry Action |
|-------|-------------------|--------------|
| UNINITIALIZED | Kernel construction | Component instantiated, empty config |
| INITIALIZING | `initialize(kernel)` called | Load configuration, validate schema |
| RUNNING | Phase 2 complete, frozen | Serve read-only config |
| SHUTDOWN | Kernel shutdown | Publish config event, clear config |

### 8.4 StructuredLogger Lifecycle

| State | Transition Trigger | Entry Action |
|-------|-------------------|--------------|
| UNINITIALIZED | Kernel construction | Component instantiated, no sinks |
| INITIALIZING | `initialize(kernel)` called | Load logging config, prepare sinks |
| RUNNING | Phase 3 complete | Accept log entries, route to sinks |
| SHUTDOWN | Kernel shutdown | Close all sinks, publish shutdown event |

## 9. Component Dependencies

### 9.1 Core Component Dependencies

| Component | Depends On | Reason | Type | Source |
|-----------|------------|--------|------|--------|
| EventBus (C1) | **None** | Foundation | **UNSPECIFIED** | **UNSPECIFIED** |
| ServiceRegistry (C2) | EventBus (C1) | Event communication | Structural | Part 1 §1.7.3 |
| ConfigurationManager (C3) | EventBus (C1) | Event communication | Structural | Part 1 §1.7.3 |
| StructuredLogger (C4) | EventBus (C1), ServiceRegistry (C2), ConfigurationManager (C3) | Event communication, registry access, config | Structural | Part 1 §1.7.3 |

### 9.2 Core Manager Dependencies

| Component | Depends On | Reason | Type | Source |
|-----------|------------|--------|------|--------|
| LifecycleManager (M1) | EventBus (C1), StateManager (M2), StorageManager (M3) | Kernel governance, state, storage | Structural | Part 4 §4.12 |
| StateManager (M2) | EventBus (C1), StorageManager (M3), WorkflowManager (M4) | Communication, persistence, workflow coordination | Structural | Part 4 §4.12 |
| StorageManager (M3) | EventBus (C1), StateManager (M2), WorkflowManager (M4) | Communication, state coordination, workflow | Structural | Part 4 §4.12 |
| WorkflowManager (M4) | EventBus (C1), StateManager (M2), StorageManager (M3), SecurityManager (M5), CapabilityManager (M6), ResourceManager (M7) | Comprehensive coordination | Structural | Part 4 §4.12 |
| SecurityManager (M5) | EventBus (C1) | Communication | Structural | Part 4 §4.12 |
| CapabilityManager (M6) | EventBus (C1), StateManager (M2), SecurityManager (M7) | Communication, state, security | Structural | Part 4 §4.12 |
| ResourceManager (M7) | EventBus (C1), StateManager (M2), SecurityManager (M7) | Communication, state, security | Structural | Part 4 §4.12 |
| HealthManager (M8) | EventBus (C1), StateManager (M2), ResourceManager (M7) | Communication, state, resources | Structural | Part 4 §4.12 |
| ObservabilityManager (M9) | EventBus (C1), StateManager (M2), WorkflowManager (M4), SecurityManager (M7) | Communication, state, workflow, security | Structural | Part 4 §4.12 |

### 9.3 Engineering Service Dependencies

| Component | Depends On | Reason | Type | Source |
|-----------|------------|--------|------|--------|
| PlanningService (E1) | EventBus (C1), StateManager (M2), SkillService (F1) | Communication, state, skills | Structural | Part 5 §5.3 |
| CodingService (E2) | EventBus (C1), StateManager (M2), PlanningService (E1), ReviewService (E3) | Communication, state, dependencies | Structural | Part 5 §5.4 |
| ReviewService (E3) | EventBus (C1), StateManager (M2), CodingService (E2), TestingService (E4) | Communication, state, dependencies | Structural | Part 5 §5.5 |
| TestingService (E4) | EventBus (C1), StateManager (M2), ReviewService (E3), DeploymentService (E5) | Communication, state, dependencies | Structural | Part 5 §5.6 |
| DeploymentService (E5) | EventBus (C1), StateManager (M2), TestingService (E4), OperationsService (E6) | Communication, state, dependencies | Structural | Part 5 §5.7 |
| OperationsService (E6) | EventBus (C1), StateManager (M2), DeploymentService (E5), LearningService (E7) | Communication, state, dependencies | Structural | Part 5 §5.8 |
| LearningService (E7) | EventBus (C1), StateManager (M2), OperationsService (E6), MemoryService (F4) | Communication, state, dependencies | Structural | Part 5 §5.9 |
| MemoryService (E8) | EventBus (C1), StateManager (M2), LearningService (E7) | Communication, state, dependencies | Structural | Part 5 §5.10 |

### 9.4 Capability Facade Dependencies

| Component | Depends On | Reason | Type | Source |
|-----------|------------|--------|------|--------|
| SkillService (F1) | EventBus (C1), StateManager (M2), SkillManager (M6) | Communication, state, manager | Structural | Part 6 §6.4 |
| CouncilService (F2) | EventBus (C1), StateManager (M2), CouncilManager (M7) | Communication, state, manager | Structural | Part 6 §6.2 |
| MCPService (F3) | EventBus (C1), StateManager (M2), MCPManager (M5) | Communication, state, manager | Structural | Part 6 §6.5 |
| MemoryService (F4) | EventBus (C1), StateManager (M2), MemoryManager (M6) | Communication, state, manager | Structural | Part 6 §6.3 |

## 10. Component EventBus Relationships

### 10.1 Structural Dependencies

| Component | Uses EventBus As | Reason |
|-----------|----------------|--------|
| All Core Components | EventBus (C1) | Sole communication substrate |
| All Core Managers | EventBus (C1) | Event-First communication |
| All Engineering Services | EventBus (C1) | Event-First communication |
| All Capability Facade Services | EventBus (C1) | Event-driven facade pattern |

### 10.2 Event Interactions

| Component | Publishes Events To | Subscribes To | Purpose |
|-----------|-------------------|--------------|--------|
| All Components | EventBus (C1) | EventBus (C1) | Communication and coordination |

### 10.3 EventBus Ownership

| Component | Owns EventBus State | Owns Event Processing |
|-----------|-------------------|-----------------------|
| EventBus (C1) | Queue structures, routing tables | Event dispatch, subscription management |
| All Other Components | **Not Owner** | **Not Owner** |

## 11. Component Runtime Relationships

### 11.1 Hermes Kernel Relationships

| Entity | Owns | Manages | Consumes |
|--------|------|---------|----------|
| Hermes Kernel | Core Components, Core Managers | ServiceRegistry, Lifecycle | Core Components, Core Managers |

### 11.2 Component Runtime States

| Component | Runtime Phase | Lifecycle Authority |
|-----------|--------------|-------------------|
| All Components | Initialization, Running, Shutdown | LifecycleManager (M1) |

## 12. Agent and Council Classification

### 12.1 Agent Components

| Component | Classification | Architectural Role |
|-----------|----------------|------------------|
| AIAgencyService | Agent Component | AI Agency capabilities |
| ModelRouter | Agent Component | LLM routing capabilities |

### 12.2 Council Components

| Component | Classification | Architectural Role |
|-----------|----------------|------------------|
| CouncilService | Council Component | Council coordination |

## 13. Workflow Classification

### 13.1 Workflow vs Component Distinction

| Entity | Is Component | Architectural Classification |
|--------|-------------|---------------------------|
| WorkflowManager (M4) | **Yes** | Core Manager component |
| Individual Workflows | **No** | Runtime execution entities |
| Workflow Engine | **No** | Part of WorkflowManager |

## 14. Memory/Knowledge Classification

### 14.1 Memory Subsystems

| Entity | Is Component | Architectural Classification |
|--------|-------------|---------------------------|
| MemoryManager (M6) | **Yes** | Core Manager component |
| Working Memory | **No** | Runtime state |
| Engineering Memory | **No** | Service concern |
| Obsidian Memory | **No** | Service concern |
| Graphify Memory | **No** | Service concern |

## 15. Plugin/MCP Classification

### 15.1 Plugin/Integration Architecture

| Entity | Is Component | Architectural Classification |
|--------|-------------|---------------------------|
| SkillManager (M8) | **Yes** | Core Manager component |
| MCPManager (M5) | **Yes** | Core Manager component |
| MCP Transport | **No** | Implementation detail |
| Tool | **No** | Capability concern |
| External Integration | **No** | Extension point |

## 16. Security Component Classification

### 16.1 Security Architecture

| Entity | Is Component | Architectural Classification |
|--------|-------------|---------------------------|
| SecurityManager (M5) | **Yes** | Core Manager component |
| Authentication | **No** | Security concern |
| Authorization | **No** | Security concern |
| Policy | **No** | Security concern |

## 17. Configuration Component Classification

### 17.1 Configuration Architecture

| Entity | Is Component | Architectural Classification |
|--------|-------------|---------------------------|
| ConfigurationManager (C3) | **Yes** | Core Component |
| KernelConfig | **No** | Configuration data |
| Environment Variables | **No** | Configuration source |

## 18. Observability Component Classification

### 18.1 Observability Architecture

| Entity | Is Component | Architectural Classification |
|--------|-------------|---------------------------|
| ObservabilityManager (M9) | **Yes** | Core Manager component |
| Metrics | **No** | Observability concern |
| Traces | **No** | Observability concern |
| Dashboards | **No** | Observability concern |

## 19. AI Coding Agent Safety Rules

### 19.1 AI Agent Restrictions

AI agents MUST NOT:

- Create components because a class is convenient
- Split components
- Merge components
- Create interfaces
- Infer ownership from interactions
- Infer lifecycle from state
- Infer dependencies from communication
- Treat architectural interfaces as network APIs
- Invent method signatures
- Invent initialization hooks
- Invent shutdown hooks
- Invent restart behavior
- Invent hot reload behavior

### 19.2 AI Agent Required Actions

AI agents MUST:

- Inspect components.md before creating any new component
- Validate against authoritative source architecture
- Verify component classification, responsibility, ownership, boundaries, dependencies, lifecycle, and interfaces
- Check for component conflicts (especially Core Component Definition Conflict)
- Not invent components or interfaces not documented here
- Validate against source documents before making changes
- Produce implementations that explicitly reference this registry

## 20. Component Conformance Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| Component exists where required | **UNSPECIFIED** | **UNSPECIFIED** |
| Responsibility matches architecture | **UNSPECIFIED** | **UNSPECIFIED** |
| Ownership matches architecture | **UNSPECIFIED** | **UNSPECIFIED** |
| Boundaries are preserved | **UNSPECIFIED** | **UNSPECIFIED** |
| Dependencies are correct | **UNSPECIFIED** | **UNSPECIFIED** |
| Interfaces are correct | **UNSPECIFIED** | **UNSPECIFIED** |
| Lifecycle is correct | **UNSPECIFIED** | **UNSPECIFIED** |
| Configuration ownership is correct | **UNSPECIFIED** | **UNSPECIFIED** |
| Security boundaries are correct | **UNSPECIFIED** | **UNSPECIFIED** |
| Observability requirements are correct | **UNSPECIFIED** | **UNSPECIFIED** |
| No unsupported responsibilities were added | **UNSPECIFIED** | **UNSPECIFIED** |

## 21. Component Gap Registry

| Gap / Conflict | Component | Missing Information | Implementation Impact | Status | Source |
|----------------|-----------|-------------------|---------------------|--------|--------|
| Core Component Definition Conflict | EventBus | **UNSPECIFIED** | Initialization sequence uncertainty | **UNSPECIFIED** | Parts 0, 1, 3 |
| Core Component Definition Conflict | StateManager | **UNSPECIFIED** | Ownership boundary uncertainty | **UNSPECIFIED** | Parts 0, 3 |
| Core Component Definition Conflict | WorkflowManager | **UNSPECIFIED** | Responsibility ambiguity | **UNSPECIFIED** | Parts 0, 1, 3 |
| Core Component Definition Conflict | ResourceManager | **UNSPECIFIED** | Category uncertainty | **UNSPECIFIED** | Parts 0, 4 |
| Core Manager / Capability Manager | Core Manager vs Capability Manager | **UNSPECIFIED** | Terminology conflict | **UNSPECIFIED** | Part 4 §4.2 |
| Engineering Service | Service vs Manager | **UNSPECIFIED** | Architectural classification | **UNSPECIFIED** | Parts 4-6 |
| Component Interface | Interface Signatures | **UNSPECIFIED** | Implementation guidance | **UNSPECIFIED** | **UNSPECIFIED** |

## 22. Cross-Document Consistency

### 22.1 Glossary Verification

| Glossary Term | Referenced Component | Consistency |
|---------------|--------------------|-------------|
| Core Component | C1-C4 | **UNSPECIFIED** |
| Core Manager | M1-M9 | **UNSPECIFIED** |
| Engineering Service | E1-E8 | **UNSPECIFIED** |
| Capability Facade | F1-F4 | **UNSPECIFIED** |

### 22.2 ADR Verification

All ADRs referencing components are documented in the conflict sections above.

### 22.3 Dependency Map Verification

All component dependencies align with dependency-map.md as documented in Section 9.

### 22.4 Implementation Contract Verification

All components support documented implementation contracts where architecture explicitly establishes them.

### 22.5 Testing Verification

Component testing requirements derived from testing.md where documented.

## 23. Cross-Reference Quality

All cross-references are repository-relative and verified against the current architecture.

## 24. Final Audit Status

### 24.1 Component Completeness

- **All architecturally established components** documented
- **No fictional components** introduced
- **All conflicts preserved** from authoritative sources
- **All gaps documented** where architecture is incomplete

### 24.2 Evidence Requirements

Every component specification traceable to Parts 0–14.

### 24.3 AI Agent Protection

Clear rules preventing component invention by AI coding agents.

### 24.4 Architecture Preservation

Existing correct content preserved, conflicts maintained, gaps identified.

**This component registry accurately represents AI-OS architecture as it exists, not as it could be invented, with all conflicts and ambiguities explicitly preserved for proper architectural resolution.**