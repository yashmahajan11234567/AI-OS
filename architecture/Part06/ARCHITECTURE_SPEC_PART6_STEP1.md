# AI-OS Architecture Specification v1.0
## Part 6: Capability Facade Services Architecture

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

### 6.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART6 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 6 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (7–N) MUST conform to Part 6. Part 6 MUST NOT contradict Part 0, Part 1, Part 2, Part 3, Part 4, or Part 5. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles, conformance), PART1 (kernel architecture), PART2 (event system), PART3 (core components), PART4 (core managers), PART5 (engineering services), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis), MIGRATION_PLAN.md (phasing) |

**Conformance Requirement:** Every subsequent Part (7–N) of this specification MUST explicitly reference Part 6 sections for Capability Facade Service terminology, interfaces, and conformance criteria. Any Part that contradicts Part 6 is non-conformant and MUST be revised.

**Scope:** This Part defines the authoritative architecture of the **Capability Facade Services** layer — the four (4) event-driven facade services that bridge the EventBus-based communication of Engineering Services (Part 5) with the singleton-accessor-based Capability Managers owned by the Hermes Kernel (Parts 1, 4). This Part specifies the architectural purpose, positioning, principles, and invariants governing this layer. Detailed specifications for each individual facade service appear in subsequent sections of Part 6.

**Out of Scope:**
- Detailed specification of individual Capability Facade Services (covered in Part 6, sections 6.2–6.5)
- Implementation code, APIs, or technology-specific details
- Core Manager internals (covered in Parts 1, 4)
- Engineering Service behavior (covered in Part 5)
- Event System contracts (covered in Part 2)

---

### 6.1 Purpose

#### 6.1.1 Why Capability Facade Services Exist

Capability Facade Services exist to resolve a fundamental architectural tension in AI-OS: **Core Managers are kernel-owned infrastructure exposed via Global Singleton Accessors (Part 0 Principle 3, Part 1 §1.8.4), while Engineering Services communicate exclusively via the EventBus (Part 0 Principle 1, Part 5 §5.1.2).** These two communication paradigms are architecturally incompatible without an intervening translation layer.

Without Capability Facade Services, the following violations would occur:

1. **Direct Manager Access by Services** — Engineering Services would need to call `kernel.memory.get()`, `kernel.skills.execute()`, or similar singleton accessor methods directly, violating Part 0 Principle 1 (Event-First Communication) and Part 1 CC-IR-001 (EventBus-only post-initialization communication).

2. **EventBus Dependency in Core Managers** — Capability Managers would need to subscribe to EventBus events and emit events directly, violating Part 0 Principle 3 (Capability Managers Are Kernel-Owned) and Part 4 §4.1.4 (Managers consume Core Components, not the reverse). Core Managers are infrastructure, not services; they are not registered in ServiceRegistry, do not extend BaseService, and do not participate in the event-driven lifecycle (Part 1 §1.8).

3. **Domain Logic Leakage into Managers** — Engineering Services would need to embed event-to-manager translation logic inline, violating Part 0 Principle 6 (Engineering Services Implement SDLC Phases) by coupling phase logic to manager access patterns.

4. **Lifecycle Coupling** — Core Managers initialize in Phases 4–8 (Part 1 §1.8.3), while Engineering Services initialize in Phase 9+ (Part 1 §1.10.2). Without a facade layer, Service initialization would need direct knowledge of Manager initialization state, violating Part 1 INV-CM-006 (Accessor access before RUNNING throws).

Capability Facade Services solve these problems by providing a **thin, event-driven translation layer** that:

- **Subscribes to events** on the EventBus (as a proper BaseService, Part 5 §5.2.5)
- **Translates event payloads** into Capability Manager method calls via kernel singleton accessors
- **Emits result events** back to the EventBus for consumption by Engineering Services
- **Contains zero business logic** — translation only, never domain decision-making (Part 0 Principle 7)

#### 6.1.2 Architectural Problem Statement

The architectural gap that Capability Facade Services fill can be stated precisely:

> AI-OS has two distinct architectural domains — **Event Space** (where all Engineering Services, Core Components, and governance entities communicate via typed, correlated, immutable Events on the EventBus) and **Manager Space** (where Capability Managers execute infrastructure logic accessed via typed method calls on Global Singleton Accessors). These domains MUST remain architecturally isolated: Services MUST NOT enter Manager Space, and Managers MUST NOT enter Event Space. Capability Facade Services are the **sole architectural bridge** between these domains.

The four Capability Facade Services correspond to the four Capability Manager domains that Engineering Services need to consume:

| Capability Domain | Core Manager (Manager Space) | Capability Facade Service (Event Space) |
|-------------------|------------------------------|----------------------------------------|
| **Skill Execution** | SkillManager | SkillService |
| **Council Governance** | CouncilManager | CouncilService |
| **MCP Tool Invocation** | MCPManager | MCPService |
| **Memory Operations** | MemoryManager | MemoryService |

**Invariant:** `INV-CFS-BRIDGE-001` — There MUST be exactly four Capability Facade Services, one per bridged Capability Manager domain. No additional facades MAY be added without ARB approval and specification revision.

**Invariant:** `INV-CFS-BRIDGE-002` — No Capability Facade Service MAY bridge more than one Capability Manager domain. One-to-one mapping is mandatory.

#### 6.1.3 Relationship to Hermes Kernel

Capability Facade Services SHALL be registered in the **ServiceRegistry** (Core Component C2, Part 3 §3.4) and initialized by the **LifecycleManager** (Core Manager, Part 4 §4.3) in Phase 9+ of the kernel initialization sequence (Part 1 §1.10.2). They SHALL follow the same topological initialization ordering as Engineering Services (Part 5 §5.2.5).

The Hermes Kernel SHALL:
- **Host** Capability Facade Services in the ServiceRegistry, alongside Engineering Services
- **Lifecycle-Manage** them via LifecycleManager, respecting declared `depends_on` dependencies
- **Provide** singleton accessor access to Capability Managers via `HermesKernel.instance` (Part 1 §1.13.1)
- **NOT** distinguish Capability Facade Services from Engineering Services in lifecycle coordination — they are identical from the kernel's perspective
- **Enforce** that Capability Facade Services do not bypass EventBus for inter-service communication

The Capability Facade Services SHALL:
- **Extend BaseService** (Part 5 Service Framework) and register in ServiceRegistry
- **Subscribe to event types** in `on_start()` per BaseService lifecycle contract
- **Access** Capability Managers exclusively via `HermesKernel.instance.<manager>` singleton accessors
- **Emit result events** in the `capability_facade` ComponentIdentity type (Part 2 §2.2.2)
- **Declare** `depends_on` dependencies on Zero Engineering Services — they depend only on Core Managers and Core Components

**Invariant:** `INV-CFS-KERNEL-001` — The Hermes Kernel MUST NOT apply special treatment to Capability Facade Services during lifecycle management. They are Services, indistinguishable from Engineering Services, with one exception: they MUST NOT declare dependencies on any Engineering Service.

**Invariant:** `INV-CFS-KERNEL-002` — Capability Facade Services MUST initialize AFTER the Capability Managers they bridge (Phase 4–8 managers must be RUNNING before Phase 9+ facade initialization).

#### 6.1.4 Relationship to Core Components

Capability Facade Services SHALL consume the four Core Components (Part 3) as all Services do — through kernel accessors and EventBus:

| Core Component | Usage by Capability Facade Services | Constraint |
|----------------|-------------------------------------|------------|
| **EventBus** (C1) | Subscribe to incoming events; publish result events | Part 2 — all events MUST carry `correlationId`, `causationId`, valid `ComponentIdentity` |
| **ServiceRegistry** (C2) | Register self with declared `depends_on`, `capabilities`, `critical` flag | Part 3 §3.4 — registration MUST complete before kernel RUNNING state |
| **ConfigurationManager** (C3) | Read facade-specific configuration (timeouts, retries, routing) | Part 3 §3.5 — configuration is FROZEN; read-only access only |
| **StructuredLogger** (C4) | Emit structured logs with correlation enrichment | Part 3 §3.6 — per Part 0 Principle 12 |

**Invariant:** `INV-CFS-CORE-001` — Capability Facade Services MUST NOT introduce new Core Component dependencies beyond the four defined in Part 3.

**Invariant:** `INV-CFS-CORE-002` — Capability Facade Services MUST consume Core Components via kernel accessors (Part 1 §1.13.1), never by direct instantiation.

#### 6.1.5 Relationship to Core Managers

Capability Facade Services SHALL bridge Event Space to Manager Space by translating EventBus events into Capability Manager method calls. This relationship is governed by strict architectural constraints:

**Access Mechanism:**
- Capability Facade Services SHALL access Capability Managers exclusively via `HermesKernel.instance.<manager>` singleton accessors (Part 1 §1.8.4, Part 1 §1.13.1)
- Access SHALL occur ONLY during event handler execution (never during initialization or registration)
- Each Facade Service SHALL access exactly ONE Capability Manager (INV-CFS-BRIDGE-002)

**Translation Contract:**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TRANSLATION CONTRACT                                      │
│                                                                              │
│  EventBus Event                          Capability Manager Call             │
│  ┌───────────────────────┐              ┌─────────────────────────┐         │
│  │ EventType:             │    Facade   │                         │         │
│  │ SKILL_EXECUTE_REQUEST │───Service──▶│ skill_manager.execute() │         │
│  │ Payload: {skillId,    │   translates│                         │         │
│  │   input, context}     │             └──────────┬──────────────┘         │
│  └───────────────────────┘                        │                          │
│                                                    │                          │
│  ┌───────────────────────┐                        │                          │
│  │ EventType:             │◄────Facade────────────┘                          │
│  │ SKILL_EXECUTED        │   translates                                     │
│  │ Payload: {skillId,    │                                                   │
│  │   result, duration}   │                                                   │
│  └───────────────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Forbidden Patterns:**
- Capability Facade Services MUST NOT call methods on any Capability Manager other than their designated bridge target
- Capability Facade Services MUST NOT contain business logic that interprets, transforms, or enriches Manager return values beyond serialization
- Capability Facade Services MUST NOT cache or maintain state derived from Manager calls (all state belongs in StateManager, Part 4 §4.4)
- Capability Facade Services MUST NOT subscribe to events from other Capability Facade Services

**Invariant:** `INV-CFS-MGR-001` — Capability Facade Services SHALL call exactly one Capability Manager per event handler invocation. No multi-Manager orchestration within a single handler.

**Invariant:** `INV-CFS-MGR-002` — Capability Manager method signatures and behavior SHALL NOT change to accommodate Capability Facade Services. The facade adapts to the Manager, not the reverse.

**Invariant:** `INV-CFS-MGR-003` — Capability Facade Services MUST NOT access Capability Managers outside the context of event handler execution (no proactive polling, no scheduled Manager calls outside event-driven flow).

#### 6.1.6 Relationship to Engineering Services

Capability Facade Services and Engineering Services share the ServiceRegistry, the EventBus, and the BaseService contract (Part 5). Their relationship is defined by the following architectural rules:

**Consumer-Producer Model:**
- Engineering Services are **consumers** of Capability Facade Services' emitted events
- Capability Facade Services are **producers** of capability execution results consumed by Engineering Services
- All interactions flow through EventBus events — no direct service-to-service calls (Part 0 Principle 1)
- Engineering Services declare `depends_on` on the Capability Facade Services they consume (Part 5 §5.2.4)

**Dependency Direction:**
- Engineering Services DEPEND on Capability Facade Services (declare in `depends_on`)
- Capability Facade Services do NOT depend on any Engineering Service
- This ensures Capability Facade Services can initialize before Engineering Services in the topological order (Phase 9+)
- MemoryService is depended upon by ALL Engineering Services (Part 5 INV-ENG-DEP-004)

**Communication Pattern:**
```
Engineering Service                Capability Facade Service
┌──────────────────────┐          ┌────────────────────────┐
│ PlanningService      │          │ MemoryService          │
│  on_start():         │          │  on_start():           │
│    subscribe(        │          │    subscribe(          │
│      PLANNING_*      │          │      MEMORY_RETRIEVE,  │
│    )                 │          │      MEMORY_STORE      │
│                      │          │    )                   │
│  handle(event):      │          │                        │
│    → emit(           │          │  handle(event):        │
│      MEMORY_RETRIEVE,│──event──▶│    → kernel.memory     │
│      {query, scope}  │          │      .retrieve(payload)│
│    )                │          │    → emit(             │
│                      │          │      MEMORY_RETRIEVED, │
│                      │◄─event───│      {result}          │
│                      │          │    )                   │
└──────────────────────┘          └────────────────────────┘
```

**Invariant:** `INV-CFS-ENG-001` — The `depends_on` graph from Engineering Services to Capability Facade Services MUST be acyclic and statically verifiable.

**Invariant:** `INV-CFS-ENG-002` — Capability Facade Services MUST NOT import, reference, or communicate with any Engineering Service module. All interaction is exclusively through EventBus events.

**Invariant:** `INV-CFS-ENG-003` — Engineering Services MUST NOT access Capability Manager singleton accessors directly. All capability consumption MUST go through the corresponding Capability Facade Service.

#### 6.1.7 Relationship to the Event System

Capability Facade Services are **first-class participants** in the Event System (Part 2). Their architectural relationship to EventBus is defined by the following contracts:

**Event Type Ownership:**
Capability Facade Services are the **canonical producers** for specific DIAGNOSTIC-category events (Part 2 §2.3.1):

| Capability Facade Service | Produced Event Types | Category |
|---------------------------|---------------------|----------|
| **SkillService** | `SKILL_EXECUTED`, `SKILL_FAILED` | DIAGNOSTIC |
| **CouncilService** | `COUNCIL_CONVENED`, `COUNCIL_PROPOSAL_SUBMITTED`, `COUNCIL_VOTE_CAST`, `COUNCIL_CONSENSUS_REACHED`, `COUNCIL_DISSENT_REGISTERED`, `COUNCIL_DECISION_FINALIZED`, `COUNCIL_ESCALATED` | AUDIT |
| **MCPService** | `MCP_TOOL_CALLED`, `MCP_TOOL_SUCCEEDED`, `MCP_TOOL_FAILED` | DIAGNOSTIC |
| **MemoryService** | `MEMORY_STORED`, `MEMORY_RETRIEVED`, `MEMORY_UPDATED`, `MEMORY_CONSOLIDATED`, `MEMORY_PRUNED` | DATA |

**Subscription Rules:**
- Each Capability Facade Service SHALL subscribe to exactly the event types that trigger its bridge target Manager operations
- Wildcard subscriptions (`*`) are PROHIBITED for Capability Facade Services (must subscribe to specific EventType values)
- Subscription filters MAY be used for field-level routing (e.g., MemoryService filtering by `memory_type`)
- HandlerPriority SHALL be NORMAL (500) per Part 2 §2.5.4

**Correlation and Causation:**
- Capability Facade Services MUST propagate `correlationId` from incoming events to Manager calls
- Capability Facade Services MUST set `causationId` to the `eventId` of the triggering event on all emitted events
- Capability Facade Services MUST include the Manager execution result as payload (not as separate correlation context)

**Event Schema Responsibility:**
- Capability Facade Services MUST validate incoming event payloads against registered schemas before Manager invocation
- Capability Facade Services MUST construct outgoing event payloads conforming to registered EventType schemas (Part 2 §2.3)
- Event schema versioning follows Part 2 §2.10 (MAJOR/MINOR/PATCH)

**Invariant:** `INV-CFS-EVT-001` — Every event emitted by a Capability Facade Service MUST carry `source.componentType: 'capability_facade'` and `source.componentName` matching the registered Service ID.

**Invariant:** `INV-CFS-EVT-002` — Capability Facade Services MUST NOT emit events outside their declared EventType catalog. Emitting an unregistered EventType is a conformance violation.

**Invariant:** `INV-CFS-EVT-003` — Capability Facade Services MUST handle event processing errors by emitting a failure-type event (e.g., `SKILL_FAILED`), NOT by throwing exceptions. Per Part 0 Principle 9, failures are data, not control flow.

#### 6.1.8 Relationship to Future Implementations

The Capability Facade Services architecture is designed to accommodate the following future evolutions without requiring architectural changes to this layer:

**Capability Manager Replacement:**
A Capability Manager (e.g., MemoryManager) MAY be replaced with a fundamentally different implementation without affecting consumers, because:
- Consumers (Engineering Services) communicate only via EventBus events, not Manager method signatures
- The Capability Facade Service translates events to Manager calls — if the event contract remains stable, consumers are unaffected
- A new Manager implementation requires only an update to the facade's translation logic, not changes to Engineering Services

**Distributed EventBus (v2.0):**
When the EventBus becomes distributed (Part 0 §0.2.2 — explicitly deferred to v2.0), Capability Facade Services:
- Require zero architectural changes — they already communicate exclusively via EventBus
- MAY require configuration changes (timeouts, retries for network latency)
- Continue to serve as the sole bridge between Event Space and Manager Space

**Additional Capability Managers:**
If new Capability Managers are added in a future specification revision (requiring ARB approval per Part 1 EXT-001), a corresponding Capability Facade Service MUST be created following the architectural patterns established in this Part. The four existing facades serve as the architectural template.

**Capability Manager Internal Evolution:**
Capability Managers MAY evolve their internal implementation, data stores, algorithms, or provider backends without affecting the facade layer, provided that:
- The Manager's public method signatures remain stable (or the facade is updated in lockstep)
- The Manager's behavioral contract (what it does, not how) remains stable
- The Manager continues to be accessible via the established singleton accessor

**Invariant:** `INV-CFS-FUTURE-001` — Future Capability Facade Services MUST conform to all architectural invariants, principles, and conformance requirements established in this Part. No new facade MAY be added without a corresponding new Capability Manager.

**Invariant:** `INV-CFS-FUTURE-002` — The four existing Capability Facade Services (SkillService, CouncilService, MCPService, MemoryService) SHALL NOT be removed, merged, or split without ARB approval and a major specification revision.

#### 6.1.9 Architectural Principles

The following principles govern the Capability Facade Services layer, derived from Part 0 §0.4 and elaborated for this architectural context:

| Principle ID | Principle | Rationale | Traceability |
|--------------|-----------|-----------|--------------|
| **CFS-P-001** | **Event-Bound Communication** — Capability Facade Services communicate exclusively via EventBus events. No direct Manager access from Services. No direct Service access to Managers. | Preserves Part 0 Principle 1 (Event-First Communication) across the Event Space ↔ Manager Space boundary. | Part 0 §0.4 Principle 1, Part 1 CC-IR-001 |
| **CFS-P-002** | **Thin Translation Only** — Capability Facade Services contain zero business logic, zero domain decision-making, and zero state. They translate events to Manager calls and back. | Business logic belongs in Engineering Services (Part 5). Infrastructure logic belongs in Capability Managers (Part 4). Facades are pure plumbing. | Part 0 §0.4 Principle 7 |
| **CFS-P-003** | **One Manager Per Facade** — Each Capability Facade Service bridges exactly one Capability Manager domain. No facade orchestrates multiple Managers. | Single responsibility ensures replaceability, testability, and clear dependency topology. | Derived from Part 0 §0.4 Principle 3 |
| **CFS-P-004** | **Manager Independence** — Capability Managers are unaware of Capability Facade Services. The facade adapts to the Manager, not the reverse. | Preserves Part 0 Principle 3 (Capability Managers Are Kernel-Owned). Managers are infrastructure; facades are services. | Part 0 §0.4 Principle 3, Part 4 §4.1.4 |
| **CFS-P-005** | **Consumer Agnosticism** — Capability Facade Services emit events without knowledge of which Services consume them. No producer-consumer coupling. | Decouples capability provision from capability consumption. Enables future consumers without facade changes. | Part 0 §0.4 Principle 1 (EventBus decoupling) |
| **CFS-P-006** | **Deterministic Translation** — Given identical incoming event payload and identical Manager response, a Capability Facade Service MUST produce identical outgoing event payload. | Enables deterministic replay (Part 2 §2.11.3) and testability of the translation layer. | Part 0 §0.4 Principle 6 |
| **CFS-P-007** | **Fail as Events** — All Capability Facade Service failures are communicated as typed failure events. No exceptions cross the facade boundary. | Consistent with Part 0 Principle 9 (Explicit Failure Handling via Events). Failures must be observable, routable, and recoverable. | Part 0 §0.4 Principle 9 |
| **CFS-P-008** | **Observable Translation** — Every event-to-Manager-call translation is observable via structured logs, metrics, and diagnostic events. | Enables debugging, performance analysis, and audit of the bridge layer. | Part 0 §0.4 Principle 12 |

**Invariant:** `INV-CFS-PRINCIPLE-001` — Every architectural decision in subsequent sections of Part 6 (6.2–6.5) MUST be traceable to one or more of the above principles. A design that violates a principle is non-conformant.

#### 6.1.10 Non-Goals

The following are explicitly NOT goals of the Capability Facade Services layer:

| Non-Goal | Rationale | Ownership |
|----------|-----------|-----------|
| **Implementing Business Logic** | Domain decision-making (planning, coding, review, testing, deployment) belongs in Engineering Services (Part 5). | Engineering Services |
| **Implementing Manager Infrastructure** | Retry policies, checkpointing, RCA, model routing, resource accounting belong in Core Managers (Part 4). | Core Managers |
| **Replacing EventBus Communication** | Capability Facade Services are EventBus participants, not replacements. They do not introduce alternative communication paths. | EventBus (C1) |
| **Caching or State Management** | All persistent state belongs in StateManager or StorageManager. Facades are stateless translators. | StateManager, StorageManager (Part 4) |
| **Service-to-Service Coordination** | Orchestration of multiple services is the responsibility of WorkflowManager (Part 4 §4.6). | WorkflowManager |
| **Providing External APIs** | HTTP/gRPC/WebSocket bindings are adapter concerns, not Capability Facade Service responsibilities. | Future Gateway Service |
| **Implementing Security Policy** | Authorization and policy enforcement belong in SecurityManager (Part 4 §4.7). | SecurityManager |
| **Defining Event Schemas** | Event types and payload schemas are defined in Part 2 (Event System) and extended via governed process (Part 0 §0.5.2). | Event System (Part 2) |

#### 6.1.11 Summary of Architectural Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-CFS-BRIDGE-001 | Exactly four Capability Facade Services, one per bridged Capability Manager domain. |
| INV-CFS-BRIDGE-002 | No Capability Facade Service bridges more than one Capability Manager domain. |
| INV-CFS-KERNEL-001 | Kernel applies no special treatment to Capability Facade Services during lifecycle management. |
| INV-CFS-KERNEL-002 | Capability Facade Services initialize AFTER the Capability Managers they bridge. |
| INV-CFS-CORE-001 | Capability Facade Services use exactly the four defined Core Components — no more. |
| INV-CFS-CORE-002 | Capability Facade Services consume Core Components via kernel accessors, not direct instantiation. |
| INV-CFS-MGR-001 | Exactly one Capability Manager per event handler invocation. |
| INV-CFS-MGR-002 | Capability Manager interfaces are not modified to accommodate facades. |
| INV-CFS-MGR-003 | Capability Managers are accessed only within event handler context. |
| INV-CFS-ENG-001 | Engineering Service → Capability Facade Service dependency graph is acyclic. |
| INV-CFS-ENG-002 | Capability Facade Services do not import or reference Engineering Service modules. |
| INV-CFS-ENG-003 | Engineering Services access capabilities only through Capability Facade Services. |
| INV-CFS-EVT-001 | Emitted events carry `source.componentType: 'capability_facade'`. |
| INV-CFS-EVT-002 | Only registered EventTypes are emitted by Capability Facade Services. |
| INV-CFS-EVT-003 | Failures are communicated as typed events, not exceptions. |
| INV-CFS-FUTURE-001 | Future facades conform to all invariants established in this Part. |
| INV-CFS-FUTURE-002 | The four existing facades are immutable in count and identity. |
| INV-CFS-PRINCIPLE-001 | All design decisions in subsequent Part 6 sections are traceable to CFS-P-001 through CFS-P-008. |

---

**END OF PART 6, SECTION 6.1 — CAPABILITY FACADE SERVICES ARCHITECTURE (PURPOSE)**

*This document is FROZEN. Any modification requires Architecture Review Board approval. Subsequent sections of Part 6 (6.2–6.5) SHALL specify individual Capability Facade Services and MUST conform to the architectural principles and invariants established herein.*