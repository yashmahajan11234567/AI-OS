# AI-OS Part 14 — Integration Context

**Document Status:** Architecture Context
**Purpose:** Establish the architectural context in which AI-OS integrations exist; do not redesign Parts 0–13.
**Last Updated:** 2026-08-11

---

## 0. Meta Rules

### 0.1 Status Classification Policy

Every normative statement in this document MUST carry exactly one of the following status labels. Labels are mutually exclusive:

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

### 0.2 Source-of-Truth Rules

1. **Part 00 foundational governance authority.** Part 00 is the supreme authority for terminology, principles, conformance model, and scope. Any statement in this document that contradicts Part 00 is invalid regardless of other source support.
2. **Domain-specific Part authority.** Each Part is authoritative for its defined domain. A later Part does not override an earlier Part unless the earlier Part explicitly permits extension or delegation. Example: Part 01 governs kernel composition; Part 13 governs governance architecture; neither overrides the other.
3. **Document identity matters within a domain.** Where the same concern is documented in multiple document types, the precedence is: frozen architecture spec > frozen context.md > dependency-map.md (DRAFT) > ADR > implementation.
4. **Accepted ADR authority.** An accepted ADR is authoritative for its explicit decision and expiry conditions, but only within the domain it addresses.
5. **Part 14 is derived integration documentation.** Part 14 defines integration composition only. It does not create new control-plane constructs unless a source Part explicitly delegates that responsibility.
6. **No redesign authority.** Part 14 MUST NOT redefine Core Component interfaces, Kernel boundaries, or principle semantics. Where Part 14 needs a behavior not specified in Parts 0–13, it MUST be labeled GAP/PROPOSED and resolved through the ADR process before implementation.

### 0.3 Provenance Requirement

Every section in this document MUST include:
- **Status label** (from 0.1)
- **Source citation** (Part, section or file, and anchor when possible)
- **Part 14 implication** (what integration components must do/avoid)

### 0.4 Document Status

This document is **DRAFT**. It reflects a first-pass inventory. Section 0.5 and Section 17 enumerate unresolved items that must be resolved before Part 14 chapters are treated as authoritative.

### 0.5 Assumptions Stance

Part 14 treats Parts 0–13 as the **existing architecture** and integrates against them. It does **not** assume those Parts are internally consistent, exhaustive, or free of contradictions. Part 14 records identified inconsistencies as CONFLICT and preserves both authoritative sources without silent resolution.

### 0.6 Part 14 Integrity Rules

These rules apply to this document and **all Part 14 chapter documents**. Any Part 14 document that violates these rules is non-conformant with this context.

**Integrity Rule 1 — Status discipline.**
Every normative claim MUST carry exactly one status label from Section 0.1. Mixed or missing status labels are prohibited.

**Integrity Rule 2 — Provenance discipline.**
Every major claim MUST cite its source Part, source document, and anchor. DERIVED claims MUST state their inference path. ASSUMPTION claims MUST be explicitly flagged for pre-implementation review.

**Integrity Rule 3 — Conflict preservation.**
When two authoritative sources disagree, Part 14 MUST classify the disagreement as CONFLICT, preserve both sources with their original positions, and escalate to ARB. Part 14 MUST NOT silently resolve, override, invent a compromise, or paper over source conflicts.

**Integrity Rule 4 — Anti-invention.**
Part 14 MUST NOT invent components, managers, APIs, events, schemas, protocols, infrastructure, or guarantees absent from Parts 0–13 or accepted ADRs. Where Parts 0–13 are silent, Part 14 MUST label the item UNSPECIFIED, GAP, or PROPOSED, and MUST NOT substitute an invented definition.

**Integrity Rule 5 — No redesign.**
Part 14 documents integration composition only. It MUST NOT redefine Core Component interfaces, Kernel boundaries, principle semantics, non-extension points, or any frozen contract from Parts 0–13.

**Integrity Rule 6 — Domain authority respect.**
Part 14 MUST NOT claim authority outside integration composition. Each Part remains authoritative for its own domain. Part 14 consumes, documents, and connects—it does not override.

**Integrity Rule 7 — Conformance.**
All Part 14 documents MUST conform to the status, provenance, authority, and conflict rules defined by this document. Chapter authors are responsible for verifying traceability before publication.

**Integrity Rule 8 — Derived claim transparency.**
DERIVED claims MUST include a visible inference chain: the EXISTING source(s), the logical step, and the resulting integration implication. Hidden or implicit derivation is prohibited.

---

## 1. Architectural Context

### 1.1 What "Integration" Means in AI-OS

**Status:** DERIVED

Integration in Part 14 refers to the mechanisms and boundaries through which external systems, tools, services, and domain applications attach to the AI-OS platform, authenticate, publish or consume events, access shared context, delegate tasks, and participate in observability and governance.

This scope is derived from:
- Part 14 README: "Integration patterns between Core Components … Communication contracts … Extension point mechanisms … Security boundaries … Observability integration"
- Part 00 §0.2.1: Extension points explicitly permit custom skills, custom MCP transports, custom model providers, custom resource types, custom memory backends, custom consensus algorithms, and custom AI Agency agents.
- Part 00 §0.2.2: v1.0 explicitly excludes distributed orchestration, authentication/authorization, network protocols, and UI concerns from the kernel scope.

**Assumptions stance:** Part 14 treats Parts 0–13 as the existing architecture. It does not assume they are complete, internally consistent, or free of contradictions. Where Parts 0–13 disagree, Part 14 records the disagreement as CONFLICT, preserves both sources, and escalates to ARB. Part 14 does not silently resolve source conflicts.

**Part 14 implication:** Part 14 documents how these extension and integration surfaces compose with the frozen Parts 0–13 architecture. It does not redefine extension semantics.

### 1.2 Integration Layer Position

**Status:** EXISTING

The Part 14 README defines Part 14 as the integration layer that documents how components from Parts 1–13 compose, without modifying them. Part 14 sits outside the Part 00 layer stack but consumes all layers below it.

**Part 14 implication:** Integration components are not Core Components, not Core Managers, and not Engineering Services. They are consumers of the EventBus and kernel services via documented extension points and accessors.

### 1.3 Non-Goals for Part 14

**Status:** EXISTING / DERIVED

Part 14 MUST NOT:
- Redesign Core Components or Core Managers
- Introduce new kernel-level interfaces
- Override Part 00 principles
- Define new communication substrates outside EventBus
- Define implementation-level code structure

Source: Part 14 README "Explicitly excluded from scope"; Part 00 §0.5.2 "Non-Extension Points."

**Part 14 implication:** Part 14 chapters that appear to redefine kernel boundaries must be flagged as non-conformant and revised.

---

## 2. Layers and Boundaries

### 2.1 Source-of-Truth Layer Stack

**Status:** EXISTING (Part 00 §0.7; Part 00 §0.5.2; Part 01 §1.2)

| Layer | Owner | Part | Extension Posture |
|-------|-------|------|-------------------|
| Hermes Kernel | HermesKernel | Part 01 | NOT extendable in v1.0 |
| Core Managers (9) | Kernel | Part 01 / Part 04 | Capabilities extendable; manager ownership is fixed |
| Engineering Services (8) | Service layer | Part 05 / Part 06 | New services permitted |
| Capability Facade Services (4) | Service layer | Part 06 | Interfaces fixed; implementations bridge-only |
| Extensions / Plugins | Consumer side | Part 00 §0.5.2 | Explicit extension points only |

**Part 14 implication:** Integration components attach at the Extensions/Plugins layer. They MUST NOT treat Core Components as extension targets.

### 2.2 Integration Boundary

**Status:** EXISTING

The integration boundary is the architectural perimeter where external entities cross into the AI-OS platform. It consists of:
- **Extension points** (Part 00 §0.5.2)
- **Facade Service interfaces** (Part 00 §0.4 Principle 7; Part 06)
- **EventBus subscription/publication** (Part 00 §0.4 Principle 1; Part 02)
- **Global Singleton Accessors** (Part 00 §0.4 Principle 4; Part 01 §1.8)

**Part 14 implication:** Integration components cross this boundary. Every boundary crossing must be traceable to one of the four mechanisms above.

### 2.3 Internal / Boundary / External / Out-of-Scope Zones

**Status:** EXISTING / DERIVED

| Zone | Definition | Part 14 implication |
|------|-----------|---------------------|
| **Internal** | Core Components, Core Managers, Engineering Services, Facade Services as defined in Parts 0–13 | Part 14 documents their integration surfaces; it does not modify them. |
| **Integration Boundary** | Extension points, EventBus publish/subscribe, Facade Service events, Global Singleton Accessors, configuration layer | Part 14 MUST document every public interface at this boundary with version, schema, and access constraints. |
| **External** | Third-party tools, external systems, enterprise services, Part 15 domain applications | Interact only through the integration boundary. No direct access to Core Components or Core Managers. |
| **Out of Scope** | UI/UX, implementation code structure, persistence schema migration tooling, distributed EventBus, network transport bindings, specific LLM provider SDKs | Part 14 MUST NOT specify these. If an integration concern touches an out-of-scope item, label it UNSPECIFIED and defer. |

Source: Part 00 §0.2.2 "Explicitly Out of Scope"; Part 14 README "Explicitly excluded from scope."

---

## 3. Components and Composite Identity

### 3.1 Known Component Taxonomy

**Status:** EXISTING / CONFLICT (Part 00 §0.3.2; Part 00 §0.7; Part 01 §1.7, §1.8; Part 14 README)

The canonical AI-OS component taxonomy is:

- **Core Components (4):** `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager` (Part 01 §1.7.1)
- **Core Managers (9):** `MemoryManager`, `LLMManager`, `ToolManager`, `StorageManager`, `ContextManager`, `AgentManager`, `WorkflowManager`, `SecurityManager`, `ObservabilityManager` (Part 01 §1.8.1)
- **Engineering Services (8):** Planning, Coding, Review, Testing, Deployment, Operations, Learning, Memory (Part 00 §0.3.2)
- **Capability Facade Services (4):** `SkillService`, `CouncilService`, `MCPService`, `MemoryService` (Part 00 §0.3.2)
- **Governance Components (16):** G-00 through G-15 (Part 13 §13.2; Part 13 components.md)
- **Implementation-mapped managers:** `StateManager`, `CheckpointManager`, `RetryManager`, `RootCauseAnalyzer`, `ModelRouter`, `MCPManager`, `SkillManager`, `CouncilManager`, `ResourceManager` — these are implementation-layer names that map to canonical Core Manager capabilities (Part 14 dependency-map.md §1.2 note)
- **Integration components:** Defined in Part 14; not Core Components or Core Managers

**CONFLICT — Core Component Naming: Part 00 §0.3.2/§0.7 vs Part 01 §1.7.1:**
Part 00 §0.3.2 defines Core Components as `EventBus`, `StateManager`, `WorkflowManager`, `ResourceManager`. Part 00 §0.7 diagram shows the same four names. Part 01 §1.7.1 defines Core Components as `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager`. These sets are disjoint except for `EventBus`. **This is a CONFLICT** between Part 00 and Part 01. Part 14 MUST NOT silently resolve it.

**CONFLICT — StructuredLogger in Part 14 dependency-map.md:**
The Part 14 `dependency-map.md` references `StructuredLogger` as a Core Component in row CC-04 ("HermesKernel → StructuredLogger"). `StructuredLogger` does not appear in Part 00 §0.3.2, Part 00 §0.7, or Part 01 §1.7.1. Part 00 §0.4 Principle 12 names `StructuredLogger` as the single logging abstraction, but does not classify it as a Core Component. **This is a CONFLICT.** Part 14 MUST NOT treat `StructuredLogger` as a Core Component until resolved via ADR.

**Part 14 implication:** Until CONFLICTs are resolved by ARB:
- Part 14 chapter authors MUST use Part 01 §1.7.1 Core Component names for kernel composition: `EventBus`, `ServiceRegistry`, `ConfigurationManager`, `LifecycleManager`.
- Part 14 chapter authors MUST use Part 01 §1.8.1 Core Manager names: `MemoryManager`, `LLMManager`, `ToolManager`, `StorageManager`, `ContextManager`, `AgentManager`, `WorkflowManager`, `SecurityManager`, `ObservabilityManager`.
- References to `StateManager`, `CheckpointManager`, `RetryManager`, `RootCauseAnalyzer`, `ModelRouter`, `MCPManager`, `SkillManager`, `CouncilManager`, `ResourceManager` in the Part 14 `dependency-map.md` are **implementation-mapped manager names** and MUST be traced to their canonical Core Manager counterparts before use in integration specifications.
- `StructuredLogger` references in integration documentation MUST be labeled DERIVED from Part 00 §0.4 Principle 12 until its component classification is resolved.

### 3.2 Component Identity Model

**Status:** EXISTING

All components in AI-OS are identified through:
- Core Components and Core Managers: owned exclusively by HermesKernel, exposed via Global Singleton Accessors (Part 01 §1.8.4)
- Services: registered in ServiceRegistry (Part 01 §1.7.2; Part 01 §1.8.4)
- Custom extensions: registered via documented extension points (Part 00 §0.5.2)

**Part 14 implication:** Integration components that operate as Services must register via ServiceRegistry. Integration components that operate as extensions must register via the applicable extension point.

### 3.3 Composite Identity and Principal Representation

**Status:** EXISTING / DERIVED

Part 00 §0.3.2 defines `correlation_id` and `causation_id` as mandatory on every event. Part 00 Principle 8 requires immutability on every Event. Part 01 §1.15.2 runtime invariant INV-RT-002 requires all inter-component communication via EventBus post-initialization.

Integration components MUST carry identity through:
- `correlation_id` — trace a logical workflow across event boundaries
- `causation_id` — identify the direct cause event
- `actor_id` / `actor_kind` / `actor_role` in event envelopes where defined by consuming contracts
- EventBus subscription identity registered at ServiceRegistry or applicable extension point

**Part 14 implication:** Every integration event MUST carry correlation and causation IDs. Integration component identity MUST be established before EventBus publication.

---

## 4. Control Plane vs Data Plane

### 4.1 Control-Plane Responsibilities

**Status:** EXISTING / DERIVED

The control plane manages configuration, policy, lifecycle, and orchestration. Source:
- Part 01 §1.5.2: Kernel responsibilities include configuration authority, lifecycle orchestration, failure handling
- Part 00 §0.4 Principle 10: Configuration is declarative and layered; Part 07 owns the four-layer merge
- Part 00 §0.2.2: AuthN/AuthZ explicitly deferred in v1.0 — kernel assumes trusted single-tenant process

**CONFLICT — AuthN/AuthZ Boundary:**
Part 00 §0.2.2 states AuthN/AuthZ is deferred to v2.0 ("Kernel assumes trusted single-tenant process"). However, the current Part 14 context and Part 14 dependency-map.md reference `G-14`, `G-05`, `SecurityManager.authorize`, and `INT-SEC-AUTH-001` as if governance-level authN/authz exists within v1.0. This may reflect Part 13 governance architecture, which operates as a logical overlay rather than kernel-internal control plane. **This is a CONFLICT** between Part 00 v1.0 scope and Part 13 governance architecture.

**Part 14 implication:** Part 14 MUST clarify whether integration security requirements are satisfied by:
- (a) the kernel-level trusted-process model from Part 00 §0.2.2, or
- (b) the governance-layer security model from Part 13.

Until resolved, integration security references MUST be labeled PROPOSED for the governance overlay and EXISTING for the kernel assumption.

### 4.2 Data-Plane Responsibilities

**Status:** EXISTING

The data plane handles event flow, context data, and observability telemetry. Sources:
- Part 00 §0.4 Principle 1: EventBus is the sole communication substrate
- Part 00 §0.4 Principle 8: Events carry correlation/causation IDs; events are immutable
- Part 00 §0.4 Principle 12: Observability is built-in via StructuredLogger and events

**Part 14 implication:** Integration components processing events, reading/writing context, or publishing telemetry operate on the data plane. These interactions are asynchronous, event-mediated, and idempotent by design.

### 4.3 Integration Plane Classification

**Status:** DERIVED

| Integration Concern | Plane | Reasoning |
|---------------------|-------|-----------|
| Event publishing/subscribing | Data | EventBus-mediated, immutable events |
| Context read/write | Data | StateManager scoped access; event-sourced |
| Task delegation | Control | Orchestration decisions via EventBus events |
| Configuration read | Control | Four-layer merge; immutable after freeze |
| Observability telemetry | Data | StructuredLogger + ObservabilityManager events |
| Health/status reporting | Data | Lifecycle events via EventBus |

Source: Part 00 §0.4 Principles 1, 8, 10, 12; Part 01 §1.12; Part 14 README.

**Part 14 implication:** Integration components must respect EventBus-only communication and configuration immutability regardless of which plane their primary concern targets.

---

## 5. Interaction Patterns

### 5.1 Event-First Communication

**Status:** EXISTING

Source: Part 00 §0.4 Principle 1:

> All inter-component communication MUST occur via the EventBus. There are no direct service-to-service calls, no synchronous RPC, no shared mutable state outside StateManager.

Part 00 §0.4 Principle 5 reinforces:

> Every Service MUST extend BaseService, declare depends_on, subscribe in on_start(), emit typed Events, and MUST NOT call other services directly.

Part 00 §0.4 Principle 7:

> The four Capability Facade Services MUST translate incoming Events into Manager calls and emit result Events. They MUST NOT contain business logic.

**Part 14 implication:**
- Integration components MUST communicate with AI-OS only via EventBus.
- Integration components MUST NOT establish direct method calls to Core Components, Core Managers, or Engineering Services.
- Integration components MAY use Facade Services only through EventBus-mediated request/response events, not by direct invocation.

### 5.2 Task Delegation Integration Pattern

**Status:** DERIVED

Task delegation in AI-OS is event-mediated. The Part 14 dependency-map.md documents:
- WorkflowManager publishes workflow lifecycle events (CM-01)
- Services subscribe to and publish SDLC chain events (SC-18 through SC-23)
- Facade Services translate events to manager calls (SC-14 through SC-17)

Integration components participate in delegation by:
1. Subscribing to relevant event topics
2. Publishing result events with correlation/causation IDs
3. Registering capabilities via applicable extension points

**Part 14 implication:** Integration adapters that handle delegated tasks follow the same event pattern as Engineering Services. They are not a shortcut around the EventBus.

### 5.3 Shared Context Integration Pattern

**Status:** UNSPECIFIED / GAP

Part 00 §0.3.2 defines `State Scope` as `WORKFLOW`, `SERVICE`, `GLOBAL`, `SESSION` and mentions `StateManager` as a state-management concept. Part 00 §0.7 diagram shows `StateManager` as a Core Component; Part 01 §1.7.1 does not list `StateManager` in the Core Component registry (see CONFLICT-01 in Section 3.1). Part 01 §1.8.1 does not include `StateManager` among the nine Core Managers. The `StateManager` implementation-mapped name appears in the Part 14 `dependency-map.md` but its canonical Core Manager counterpart is not identified there.

However, the current inspected documents do not specify:
- The exact API for reading/writing state scopes from integration components
- Whether integration components can hold `SERVICE` or `SESSION` scoped state
- The event types emitted on state transitions
- The canonical Core Manager responsible for state management per Part 01 §1.8.1

This is a **GAP** — `StateManager` is referenced as a state-management concept in Parts 0–1, but its integration surface and canonical Core Manager mapping are not documented in the inspected Parts 0–1 or Part 14 README.

**PROPOSED:** Part 14 chapter 14.3 or equivalent MUST document the state-management integration surface, or explicitly defer to the relevant Core Manager specification once the CONFLICT-01 naming resolution identifies the canonical manager.

### 5.4 Facade Service Responsibilities — Do Not Expand

**Status:** EXISTING

Part 00 §0.4 Principle 7:

> The four Capability Facade Services MUST translate incoming Events into Manager calls and emit result Events. They MUST NOT contain business logic.

Part 14 MUST NOT expand Facade Service responsibilities to include business logic, orchestration decisions, or integration-specific routing. Integration components that need Facade Service functionality interact via EventBus events on the Facade Service's published topics.

**Part 14 implication:** Integration adapters are thin bridges. If an integration adapter contains domain logic, it must be moved to an Engineering Service or external system, not embedded in the facade.

---

## 6. Schema and Contract Ownership

### 6.1 Schema Registry and Versioning

**Status:** EXISTING

Source: Part 00 §0.4 Principle 11:

> Event schemas, configuration schemas, and APIs MUST carry version identifiers. Breaking changes require major version bump and migration path.

Part 00 §0.5.2 permits custom event types via the `EventType` enum extension point, subject to Part 2.1/2.2 registration requirements.

**Part 14 implication:**
- Integration event schemas MUST carry version identifiers.
- Breaking changes to integration event schemas require major version bumps and migration paths.
- Integration-specific event types MUST be registered in the EventType catalog.

### 6.2 Forward Contracts Consumed by Part 14

**Status:** EXISTING / DERIVED

Part 14 consumes the following forward contracts defined in Parts 0–13:

| Contract | Defined In | Part 14 Use |
|----------|-----------|-------------|
| EventBus publish/subscribe | Part 00 §0.4 Principle 1; Part 01 §1.7.2; Part 02 | All integration communication |
| BaseService lifecycle | Part 00 §0.4 Principle 5; Part 05/Part 06 | Service-type integration components |
| ServiceRegistration | Part 01 §1.7.2, §1.8.4 | Integration component registration |
| Global Singleton Accessors | Part 00 §0.4 Principle 4; Part 01 §1.8.4 | Kernel access for integration adapters |
| Configuration read | Part 00 §0.4 Principle 10; Part 01 §1.7.1 C3; Part 07 | Integration configuration |
| Extension points | Part 00 §0.5.2 | Custom skills, MCP transports, model providers, etc. |

**Part 14 implication:** Part 14 is a terminal consumer of these contracts. It does not modify them. Any Part 14 chapter that redefines a contract from Parts 0–13 is non-conformant.

---

## 7. Dependency Direction

### 7.1 Consumption Direction

**Status:** EXISTING / DERIVED

Source: Part 14 README: "Part 14 assumes the architecture defined in Parts 1-13 as immutable foundation. It does not modify, contradict, or extend the specifications in those parts."

Part 14's dependency direction is strictly consumption:
- Part 14 → Part 00 (principles, terminology, conformance model)
- Part 14 → Part 01 (Kernel, Core Components, Core Managers, lifecycle)
- Part 14 → Part 02 (EventBus, event types, schemas)
- Part 14 → Part 03/04 (Core Manager interfaces)
- Part 14 → Part 05/06 (Engineering Services, Facade Services)
- Part 14 → Part 07 (Configuration)
- Part 14 → Part 08 (CLI)
- Part 14 → Part 09 (Invariants)
- Part 14 → Part 10–13 (extensions, governance, collaboration, observability)

Part 14 does not produce interfaces consumed by Parts 0–13.

**Part 14 implication:** Part 14 MUST NOT introduce new control-plane dependencies that Parts 0–13 must satisfy. Observability events produced by Part 14 flow into the EventBus as data-plane events and do not create architectural back-pressure on Parts 0–13.

### 7.2 Initialization Order

**Status:** EXISTING

Source: Part 01 §1.10.2:

```
Phase 0: EventBus
Phase 1: ServiceRegistry
Phase 2: Configuration Freeze
Phase 3: LifecycleManager
Phase 4–8: Core Managers
Phase 9+: Services
```

**Part 14 implication:** Integration components MUST initialize after Phase 9+ (Service initialization), per the Part 14 README integration lifecycle. They MUST NOT initialize before the EventBus is operational (Phase 0) and before configuration is frozen.

### 7.3 Circular Dependency Avoidance

**Status:** DERIVED

Part 14 produces observability events that Part 14 itself consumes for self-monitoring. This is not a true circular dependency because:
- Observability production and consumption are separate components within Part 14
- Both communicate via EventBus (Part 00 Principle 1)
- EventBus is already initialized before Part 14 components start

Source: Part 00 §0.4 Principle 1; Part 01 §1.10.2 Phase 0.

**Part 14 implication:** Part 14 self-monitoring MUST use EventBus topics with the `observability.*` namespace (or equivalent). No direct component-to-component coupling within Part 14 is permitted for self-monitoring.

---

## 8. Runtime Boundaries

### 8.1 Integration Runtime Environment

**Status:** EXISTING / UNSPECIFIED

Source: Part 00 §0.5.2 defines extension point governance. Part 00 §0.2.2 states v1.0 is single-process, in-memory only. Part 00 §0.5.2 requires sandboxing for custom Skills.

Part 14 integration components execute within the same single-process boundary unless they are external-system bridges. The Part 14 dependency-map.md references external runtime connectors but the runtime isolation mechanism is not specified in inspected Parts 0–13.

**UNSPECIFIED:** Process isolation, network boundaries, and sandboxing mechanism for external integration adapters.

**PROPOSED:** Part 14 MUST define runtime environments for each integration adapter class:
- In-process extension (same trust domain as kernel)
- Sandboxed extension (restricted capabilities, Part 00 §0.5.2 sandboxing requirement)
- External bridge (out-of-process, communicates via EventBus or adapter protocol)

### 8.2 Lifecycle Management

**Status:** EXISTING / DERIVED

Source: Part 01 §1.9.1 kernel state machine; Part 00 §0.4 Principle 5 (Service lifecycle).

Integration components follow the same lifecycle model:
1. Registered (ServiceRegistry or extension point)
2. Configured (ConfigurationManager, frozen after Phase 2/3)
3. Authorized (kernel trusted-process assumption per Part 00 §0.2.2; or governance layer per Part 13)
4. Started (subscribe to EventBus in `on_start()`)
5. Healthy (heartbeat and healthCheck())
6. Stopped (unsubscribe, release resources)
7. Deregistered

**Part 14 implication:** Integration component lifecycle MUST be managed by LifecycleManager (or equivalent), not self-managed. Lifecycle events MUST be published to EventBus.

### 8.3 Event Processing Constraints

**Status:** EXISTING

Source: Part 00 §0.4 Principle 8; Part 01 §1.15.2 INV-RT-002; Part 01 §1.12.

Integration components MUST:
- Publish immutable events with correlation_id and causation_id
- Handle TRANSIENT failures via retry; DEGRADED via alert; CRITICAL via isolation; FATAL via shutdown
- Respond to healthCheck() within configured intervals
- Emit Heartbeat events where required by the component contract

**Part 14 implication:** Integration event handlers MUST be idempotent. Integration components MUST NOT mutate events after emission.

---

## 9. Configuration Propagation

### 9.1 Configuration Model

**Status:** EXISTING

Source: Part 00 §0.4 Principle 10:

> Configuration MUST use the four-layer merge (defaults → app.yaml → env.yaml → env vars). No hardcoded defaults in Kernel or Manager code.

Part 01 §1.7.1 C3 names the `ConfigurationManager` Core Component; Part 01 §1.10.2 Phase 2 is "Configuration Freeze." The core Component naming conflict between Part 00 §0.3.2/§0.7 and Part 01 §1.7.1 is documented in Section 3.1.

**Part 14 implication:** Integration components MUST obtain configuration through the kernel's configuration authority. Configuration MUST NOT be read from environment variables or local files directly by integration components.

### 9.2 Integration Configuration Requirements

**Status:** GAP

The inspected source Parts do not specify the configuration schema for integration components: parameter names, nested structure, default values, or reload semantics.

**PROPOSED:** Part 14 MUST define an integration configuration schema that specifies at minimum:
- Connection parameters for external systems
- Event topic subscriptions and publishers
- Trust level / capability set
- Observability settings

All values MUST flow through the kernel's configuration authority. Configuration is immutable after freeze; reload requires lifecycle restart.

### 9.3 Secrets Management

**Status:** EXISTING / UNSPECIFIED

Source: Part 00 §0.2.2 states secrets via env vars are in scope for the four-layer configuration model. Part 00 §0.5.2 requires custom Skills to be sandboxed. Part 13 governance architecture references G-14 and G-05 for identity and authority.

**UNSPECIFIED:** The exact secrets management API for integration components is not defined in inspected Parts 0–1. Part 13 may define this; Part 14 MUST reference Part 13's secrets management contract rather than inventing one.

**Part 14 implication:** Integration components MUST NOT store secrets in event payloads or configuration. Secrets MUST be retrieved at runtime through the designated secrets mechanism.

---

## 10. Failure Boundaries

### 10.1 Failure Isolation Model

**Status:** EXISTING

Source: Part 00 §0.4 Principle 9; Part 01 §1.12.

Failure classification:
- TRANSIENT → retry with exponential backoff (max 3)
- DEGRADED → ComponentDegraded event; continue
- CRITICAL → ComponentFailed event; isolate; restart (max 2)
- FATAL → emergency shutdown

**Part 14 implication:** Integration components MUST emit failure events via EventBus. Integration failures MUST NOT propagate as exceptions across architectural boundaries. Integration failures MUST be classified and handled per the kernel failure model.

### 10.2 Retry and Backoff Policies

**Status:** EXISTING / UNSPECIFIED

Source: Part 01 §1.12.1: TRANSIENT retry max 3 with exponential backoff; CRITICAL max 2 restarts.

**UNSPECIFIED:** The exact retry budget for integration components and whether they participate in the kernel's RetryBudget or have their own retry policy is not defined in inspected Parts 0–13.

**PROPOSED:** Part 14 MUST specify retry policy for integration adapters, including:
- Whether integration adapters share the kernel's RetryManager
- Dead-letter queue behavior for integration events
- Reconciliation job triggers for persistent integration failures

### 10.3 Integration Failure Events

**Status:** GAP

The kernel defines `ComponentDegraded`, `ComponentFailed`, `CoreManagerFailed`, `KernelFatalError` events (Part 01 §1.12.4). Integration-specific failure events are not defined in inspected source Parts.

**PROPOSED:** Part 14 MUST define integration failure event types using the Part 00 event-type extension point. These events MUST include:
- Error code and message
- Integration component identifier
- Correlation ID for tracing
- Failure classification per Part 01 §1.12.1

---

## 11. Versioning

### 11.1 Semantic Versioning

**Status:** EXISTING

Source: Part 00 §0.4 Principle 11:

> Event schemas, configuration schemas, and APIs MUST carry version identifiers. Breaking changes require major version bump and migration path.

Part 14 README references schema versioning strategies from Part 2.6.

**Part 14 implication:** All integration event schemas, API contracts, and configuration schemas MUST carry versions. Breaking changes require new major versions with documented migration paths.

### 11.2 Component Versioning

**Status:** EXISTING / DERIVED

Source: Part 14 `dependency-map.md` shows `agent.lifecycle.registered` events carrying a `version` field. Part 01 §1.8.1 Core Managers have initialization phases and capability declarations.

**Part 14 implication:** Integration components MUST register with version identifiers. Version bumps follow semantic versioning. New versions are registered separately; existing registrations are not modified in place.

---

## 12. Security and Trust Boundaries

### 12.1 Zero-Trust Model

**Status:** EXISTING / CONFLICT

**CONFLICT — AuthN/AuthZ Scope:**
- Part 00 §0.2.2 explicitly states: "Authentication / Authorization (AuthN/AuthZ): Kernel assumes trusted single-tenant process; multi-tenant auth is v2.0."
- Part 14 current context and Part 13 governance architecture reference G-14, G-05, and governance-level authority resolution as if they are active in v1.0.
- Part 14 `dependency-map.md` references `INT-SEC-AUTH-001` and SecurityManager authorization checks (CM-06, SC-25).

These two positions are contradictory. Part 00 says no AuthN/AuthZ in v1.0; Part 13 and the Part 14 dependency map assume governance-layer security exists in v1.0. **This is a CONFLICT.** It may be resolvable if Part 13's security operates as an optional overlay rather than kernel-mandated infrastructure, but this distinction is not made explicit in inspected documents.

**Part 14 implication:** Part 14 MUST NOT state that integration security is mandatory in v1.0 until this conflict is resolved. If Part 13 security is optional, Part 14 MUST document both paths: with and without the governance overlay.

### 12.2 Integration Authorization

**Status:** UNSPECIFIED / PROPOSED

Given the conflict above, the authorization model for integration components is UNSPECIFIED in v1.0 per Part 00 §0.2.2.

**PROPOSED:** If Part 13 governance overlay is adopted for integration security:
- Integration components operate at Domain Authority level (Part 13 §13.4)
- Every integration action requiring authorization resolves authority via G-05 before proceeding
- Every delegation chain is validated via G-06

If Part 13 governance overlay is NOT adopted:
- Integration components operate in the kernel's trusted-process model
- Security is enforced at the process boundary, not per-component

### 12.3 Event Signing and Integrity

**Status:** EXISTING / UNSPECIFIED

Source: Part 00 §0.4 Principle 8 requires immutable events with correlation/causation IDs. Part 00 §0.4 Principle 9 requires failure communication via events. Cryptographic signing of events is not explicitly mandated in inspected Parts 0–1.

**UNSPECIFIED:** Whether events require cryptographic signatures in v1.0, and what signing infrastructure is available, is not stated in inspected Parts 0–1. Part 13 may define this.

**Part 14 implication:** Part 14 MUST NOT require event signing unless the requirement is sourced from Part 13 or explicitly adopted via ADR. If event signing is required, Part 14 MUST document the signing key issuance and rotation mechanism.

---

## 13. Observability

### 13.1 Observability as Built-In

**Status:** EXISTING

Source: Part 00 §0.4 Principle 12:

> Every component MUST emit structured logs (JSON, correlation IDs) and Events for state transitions. StructuredLogger is the single logging abstraction.

Part 01 §1.8.1 M9: ObservabilityManager is the last Core Manager to initialize (Phase 8). Part 01 §1.15.2 INV-RT-008: ObservabilityManager MUST receive metrics from all managers.

**Part 14 implication:** Integration components MUST emit structured logs and state-transition events. Integration components MUST participate in health checks. Integration observability data flows through the same ObservabilityManager as all other components.

### 13.2 Tracing Integration

**Status:** EXISTING / UNSPECIFIED

Source: Part 00 §0.4 Principle 8 requires correlation_id and causation_id on every event. Part 00 §0.4 Principle 12 requires observability built-in. Part 12.7 confirms W3C-style `trace_id`, `span_id`, and `parent_span_id` on the message envelope.

**Part 14 implication:** If Part 02 confirms these tracing fields as canonical, integration components MUST propagate trace context across event boundaries. If Part 02 does not confirm them, Part 14 MUST NOT introduce new tracing fields.

### 13.3 Observability Forward Contract

**Status:** DERIVED

Part 14 is the observability layer's primary consumer, not producer. Observability data is produced by:
- Core Components and Core Managers via event emission (Part 01 §1.7.4, §1.8.3)
- Engineering Services via lifecycle events (Part 05/Part 06)
- Governance components via governance events (Part 13)

Part 14 consumes these events to produce aggregate observability artifacts.

**Part 14 implication:** Part 14 does not define new observability interfaces for Parts 0–13 to consume. It instruments existing event flows.

---

## 14. Inherited Constraints from Parts 0–13

### 14.1 Kernel Constraints

| Constraint | Source | Part 14 Implication |
|------------|--------|---------------------|
| Exactly 4 Core Components; exactly 9 Core Managers | Part 01 §1.7.1, §1.8.1; Part 00 §0.4 Principles 2, 3 | Part 14 MUST NOT introduce new Core Components or Core Managers. |
| Core Components initialize Phases 0–3 sequentially; Core Managers Phases 4–8 | Part 01 §1.10.2 | Integration components initialize after Phase 9+. |
| EventBus is first to initialize and last to shut down | Part 01 §1.10.2, §1.11.2 | Integration components MUST NOT publish events before Phase 0 completes. |
| Configuration frozen before Service initialization | Part 01 §1.10.2 Phase 2/3; INV-INIT-002 | Integration components read configuration after freeze; no runtime reload. |
| Kernel state machine: UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED | Part 01 §1.9.1 | Integration components MUST handle kernel state transitions gracefully. |
| No direct service-to-service calls | Part 00 §0.4 Principle 1; Part 01 §1.15.2 INV-RT-002 | Integration components MUST communicate only via EventBus. |
| Services MUST extend BaseService and emit typed Events | Part 00 §0.4 Principle 5 | Service-type integration components MUST follow BaseService contract. |
| Facade Services translate Events to Manager calls; no business logic | Part 00 §0.4 Principle 7 | Integration MUST NOT add business logic to Facade Services. |
| Global Singleton Accessors are fixed set | Part 01 §1.8.4; INV-CM-004 | Integration components access kernel via existing accessors only. |
| Configuration uses four-layer merge; no hardcoded defaults | Part 00 §0.4 Principle 10 | Integration components MUST NOT bypass ConfigurationManager. |
| Event schemas, APIs, config schemas MUST carry version identifiers | Part 00 §0.4 Principle 11 | All integration schemas MUST be versioned. |
| Structured logs with correlation IDs on every event | Part 00 §0.4 Principle 12 | Integration components MUST emit structured, correlatable logs. |

### 14.2 Extension Constraints

| Constraint | Source | Part 14 Implication |
|------------|--------|---------------------|
| Core Component interfaces are non-extension points | Part 00 §0.5.2 | Part 14 MUST NOT extend Core Component interfaces. |
| Core Manager interfaces are non-extension points | Part 00 §0.5.2 | Part 14 MUST NOT extend Core Manager interfaces. |
| Global accessor signatures cannot be altered | Part 00 §0.5.2 | Part 14 MUST NOT add, remove, or rename accessors. |
| EventBus interface is a non-extension point | Part 00 §0.5.2 | Part 14 MUST NOT modify EventBus contract. |
| BaseService contract is a non-extension point | Part 00 §0.5.2 | Integration Service components MUST implement BaseService correctly. |
| Custom events MUST register in EventType catalog | Part 00 §0.5.2 | Integration event types MUST be registered. |
| Custom Skills MUST be sandboxed and emit SkillExecuted/SkillFailed | Part 00 §0.5.2 | Integration adapters wrapping external tools MUST follow same sandboxing and event-emission rules. |
| Custom MCP Transports MUST satisfy MCPManager contract | Part 00 §0.5.2 | MCP integration adapters MUST satisfy the manager contract, not redefine it. |
| Custom Model Providers MUST register in ModelRouter | Part 00 §0.5.2 | Model integration MUST use ModelRouter capability registry. |
| Custom Resource Types MUST implement allocation/wait-queue/TTL semantics | Part 00 §0.5.2 | Resource integration MUST satisfy ResourceManager contract. |
| Custom Consensus Algorithms MUST satisfy liveness/safety properties | Part 00 §0.5.2 | Council integration MUST satisfy CouncilManager contract. |
| Custom AI Agency Agents MUST emit audit *Requested/*Completed event pairs | Part 00 §0.5.2 | Agent integration MUST emit paired audit events. |

### 14.3 Conformance Model

**Status:** EXISTING

Source: Part 00 §0.5.1:

| Level | Focus | Part 14 Implication |
|-------|-------|---------------------|
| L1: Structural | Compiles, imports resolve, base classes implemented | Part 14 integration components MUST pass structural conformance. |
| L2: Contract | Event schemas match spec; interfaces honor signatures | Integration event schemas MUST match registry. |
| L3: Behavioral | Runtime invariants hold | Integration handlers MUST be idempotent; ordering MUST be preserved. |
| L4: Architectural | No principle violations | Part 14 MUST NOT introduce direct service-to-service calls or kernel domain logic. |

**Part 14 implication:** Integration components must pass all four conformance levels. Part 14 chapters must specify the conformance tests for each integration surface.

---

## 15. Forward Contracts and Gaps

### 15.1 Confirmed Forward Contracts

**Status:** EXISTING

| Contract | Source | Part 14 Use |
|----------|--------|-------------|
| EventBus publish/subscribe | Part 00 §0.4 Principle 1; Part 01 §1.7.2 INT-EVT-BUS-001 | All integration communication |
| ServiceRegistration | Part 01 §1.7.2 INT-SVC-REG-001 | Integration component registration |
| Configuration read | Part 01 §1.7.1, §1.10.2 INT-CONFIG-READ-001 | Integration configuration |
| Singleton accessor interface | Part 01 §1.8.4 INT-KERNEL-ACC-001 | Kernel access for integration adapters |
| ICoreComponent initialization | Part 01 §1.7.2 INT-CORE-CMP-001 | For Service-type integration components |
| BaseService lifecycle | Part 00 §0.4 Principle 5; Part 05/Part 06 | Service-type integration lifecycle |
| Extension point contracts | Part 00 §0.5.2 | Skills, MCP transports, model providers, etc. |

### 15.2 Identified Gaps

**Status:** GAP

The following integration surfaces are not fully specified in inspected Parts 0–13:

| Gap ID | Description | Source Silence | Recommended Resolution |
|--------|-------------|----------------|------------------------|
| **GAP-01** | State management integration API for external readers/writers | Part 00 §0.3.2 names StateManager as a state-management concept; no public integration interface documented in inspected Parts 0–1; canonical Core Manager identity obscured by CONFLICT-01 | Document in Part 14 after CONFLICT-01 resolution identifies the canonical Core Manager, or defer to that manager's Part 03/Part 04 specification |
| **GAP-02** | Configuration schema for integration components | Part 00 §0.4 Principle 10 specifies four-layer merge; no integration-specific schema documented | Part 14 MUST define or explicitly defer |
| **GAP-03** | Retry policy semantics for integration adapters | Part 01 §1.12.1 specifies kernel-internal retry; integration adapter retry not addressed | Part 14 MUST specify |
| **GAP-04** | Integration failure event taxonomy | Kernel defines ComponentDegraded/ComponentFailed/CoreManagerFailed/KernelFatalError; integration-specific events not defined | Part 14 MUST define via EventType extension |
| **GAP-05** | Observability data model for integration metrics | Part 00 §0.4 Principle 12 requires observability; specific metric names/dimensions for integrations not defined | Part 14 MUST define or reference Part 02/Part 09 |
| **GAP-06** | AuthN/AuthZ model for v1.0 integrations | Part 00 §0.2.2 defers to v2.0; Part 13 governance may provide overlay; relationship not clarified | ARB decision required |
| **GAP-07** | Distributed tracing fields on events | trace_id/span_id/parent_span_id referenced in current context but not confirmed in inspected Parts 0–1 | Verify in Part 02; Part 14 MUST NOT introduce without source |
| **GAP-08** | External runtime isolation mechanism | Part 00 §0.2.2 states single-process v1.0; external adapter runtime not specified | Part 14 MUST define or label FUTURE |

### 15.3 CONFLICT Summary

**Status:** CONFLICT

| Conflict ID | Parties | Description | Required Action |
|-------------|---------|-------------|----------------|
| **CONFLICT-01** | Part 00 §0.3.2/§0.7 vs Part 01 §1.7.1 | Core Component naming: Part 00 lists EventBus, StateManager, WorkflowManager, ResourceManager; Part 01 lists EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager. Sets are disjoint except for EventBus. | ARB decision; Part 14 MUST use Part 01 §1.7.1 names for kernel composition until resolved |
| **CONFLICT-02** | Part 14 dependency-map.md vs Part 00 §0.4 Principle 12 / Part 01 §1.7.1 | StructuredLogger is referenced as a Core Component (CC-04) in dependency-map.md but is not listed in Part 00 §0.3.2 Core Component definition, Part 00 §0.7 diagram, or Part 01 §1.7.1 registry. Part 00 §0.4 Principle 12 names StructuredLogger as the logging abstraction but does not classify it as a Core Component. | ARB decision; Part 14 MUST NOT classify StructuredLogger as a Core Component until resolved |
| **CONFLICT-03** | Part 00 §0.2.2 vs Part 13 / Part 14 dependency-map.md | AuthN/AuthZ scope: Part 00 defers to v2.0; Part 13 and dependency-map.md reference governance security as active v1.0 | Clarify whether Part 13 governance security is optional overlay or mandatory v1.0 requirement |

---

## 16. Provenance Index

| Statement Cluster | Status | Primary Source |
|-------------------|--------|----------------|
| EventBus is sole communication substrate | EXISTING | Part 00 §0.4 Principle 1 |
| Exactly 4 Core Components: EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager (Part 01 §1.7.1) | EXISTING | Part 01 §1.7.1 |
| Core Component naming conflict: Part 00 §0.3.2/§0.7 lists EventBus, StateManager, WorkflowManager, ResourceManager | CONFLICT | Part 00 §0.3.2/§0.7 vs Part 01 §1.7.1 |
| Exactly 9 Core Managers | EXISTING | Part 01 §1.8.1 |
| 13 Global Singleton Accessors | EXISTING | Part 01 §1.8.4 |
| Kernel initialization phases 0–3, 4–8, 9+ | EXISTING | Part 01 §1.10.2 |
| Kernel shutdown phases S0–S9+ reverse order | EXISTING | Part 01 §1.11.2 |
| Failure classification TRANSIENT/DEGRADED/CRITICAL/FATAL | EXISTING | Part 01 §1.12.1 |
| Configuration four-layer merge; immutable after freeze | EXISTING | Part 00 §0.4 Principle 10 |
| Services extend BaseService; emit typed Events | EXISTING | Part 00 §0.4 Principle 5 |
| Facade Services bridge Events to Managers; no business logic | EXISTING | Part 00 §0.4 Principle 7 |
| Immutable events with correlation/causation IDs | EXISTING | Part 00 §0.4 Principle 8 |
| Failure via events, not exceptions | EXISTING | Part 00 §0.4 Principle 9 |
| Event schemas carry version identifiers | EXISTING | Part 00 §0.4 Principle 11 |
| Observability built-in via structured logs and events | EXISTING | Part 00 §0.4 Principle 12 |
| Custom event types via EventType enum extension | EXISTING | Part 00 §0.5.2 |
| AuthN/AuthZ deferred to v2.0 (kernel trusted single-tenant) | EXISTING | Part 00 §0.2.2 |
| v1.0 is single-process, in-memory only | EXISTING | Part 00 §0.2.2 |
| Extension points: Skills, MCP transports, Model providers, Resource types, Consensus algorithms, AI Agency agents | EXISTING | Part 00 §0.5.2 |
| Non-extension points: Core Component interfaces, Kernel lifecycle, BaseService, StateManager scopes, Checkpoint format, RetryBudget semantics, global accessor signatures | EXISTING | Part 00 §0.5.2 |
| Core Component naming: Part 00 §0.3.2/§0.7 vs Part 01 §1.7.1 | CONFLICT | Part 00 §0.3.2/§0.7 vs Part 01 §1.7.1 |
| StructuredLogger classified as Core Component in dependency-map.md CC-04 | CONFLICT | Part 14 dependency-map.md vs Part 00 §0.3.2/§0.7/§0.7/Part 01 §1.7.1 |
| AuthN/AuthZ conflict between Part 00 and Part 13/Part 14 | CONFLICT | Part 00 §0.2.2 vs Part 13/Part14/dependency-map.md |
| StateManager integration API for external consumers | GAP | Not specified in inspected Parts 0–1 |
| Integration configuration schema | GAP | Not specified in inspected Parts 0–1 |
| Integration retry policy semantics | GAP | Not specified in inspected Parts 0–1 |
| Integration failure event taxonomy | GAP | Not specified in inspected Parts 0–1 |
| Integration observability metric names/dimensions | GAP | Not specified in inspected Parts 0–1 |
| Distributed tracing event fields (trace_id/span_id/parent_span_id) | EXISTING | Part 12.7 confirms W3C-style fields on message envelope |
| External adapter runtime isolation mechanism | UNSPECIFIED | Part 00 §0.2.2 limits v1.0 to single-process |

---

## 17. Document Status and Next Steps

### 17.1 Immediate Blockers Before Part 14 Chapters Are Authoritative

1. **CONFLICT-01:** Resolve Core Component naming between Part 00 §0.3.2/§0.7 and Part 01 §1.7.1. Until resolved, Part 14 MUST use Part 01 §1.7.1 names for kernel composition.
2. **CONFLICT-02:** Resolve StructuredLogger component classification in Part 14 dependency-map.md. Part 14 MUST NOT classify StructuredLogger as a Core Component until resolved.
3. **CONFLICT-03:** Clarify AuthN/AuthZ scope. Part 14 MUST document both paths (trusted-process vs governance overlay) until resolved.
4. **CONFLICT-04 (future):** Any Part 14 chapter source-numbering references MUST use verified Part numbering: Part 00, Part 01, Part 02, etc.

### 17.2 Gaps Requiring Part 14 Resolution Before Implementation

- GAP-01 through GAP-08 (Section 15.2) MUST be addressed in the relevant Part 14 chapter documents.
- Each GAP MUST be resolved as either: (a) documented in Part 14 with source citation, (b) explicitly deferred with rationale, or (c) escalated to ARB as requiring source Part modification.

### 17.3 Maintenance Rule

This document MUST be updated when:
- Any Part 14 chapter resolves a GAP or CONFLICT
- Any source Part 0–13 issues an update affecting Part 14
- An ADR modifies an integration-relevant decision

All updates MUST preserve the status-classification labels and provenance citations.

---

*This document is a composition and inventory artifact. It does not create new architectural requirements. Where Parts 0–13 are silent, this document records the silence. Where Parts 0–13 conflict, this document records the conflict.*
