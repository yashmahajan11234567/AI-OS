# Architecture Specification Part 6 — Step 7: Cross-Capability Coordination

## 6.7 Cross-Capability Coordination

### 6.7.1 Purpose

The **Cross-Capability Coordination** architecture exists to resolve the fundamental architectural tension between *capability autonomy* and *coordinated operation* within the AI-OS Capability Facade (Section 5.1) and Council Facade (Section 5.3).

Each execution facade — **SkillService** (Section 6.3), **MCPService** (Section 6.4), **MemoryService** (Section 6.5), and **CouncilService** (Section 6.6) — operates as an independently owned, independently versioned architectural subsystem. Each owns its Execution Contract, its execution index, its policy enforcement boundary, its failure containment domain, and its lifecycle. This autonomy is an architectural invariant established in Sections 6.3–6.6.

However, Engineering Services (Part 4) and AI Agents (Part 3) require the ability to compose capabilities across these facades within a single logical operation: invoking a skill that reads from memory, calling an external capability that writes to memory, executing a council whose participants access memory and invoke skills, and so on. These compositions **MUST** not violate the autonomy of the individual execution facades.

Cross-Capability Coordination defines the architectural principles, rules, and conceptual model that enable multi-facade compositions while preserving:

- **Capability autonomy** — no facade depends on another facade's internal implementation
- **Definition Plane purity** — coordination does not leak Definition Plane concerns into the Execution Plane
- **Event Space as the sole coordination substrate** — asynchronous interaction occurs exclusively through the Event Space (Part 4)
- **Failure isolation** — a failure in one facade's domain does not cascade into another
- **Policy coherence** — cross-cutting policies apply uniformly without duplication or omission

Without Cross-Capability Coordination, the architecture faces three architecturally unacceptable alternatives:

1. **Facades import each other directly** — creating cyclic dependencies, coupling execution indices, leaking policy enforcement boundaries, and making independent versioning impossible.

2. **Consumers orchestrate across facades via raw Event Space messages** — requiring each Engineering Service and AI Agent to implement correlation tracking, saga coordination, compensation logic, and cross-facade error normalization, duplicating infrastructure logic across every consumer.

3. **A central orchestrator coordinates facades** — inverting control, creating a single point of failure, centralizing policy logic that belongs at facade boundaries, and preventing horizontal scaling of individual facades.

Cross-Capability Coordination eliminates these alternatives by establishing architectural rules that govern *how* facades may interact without introducing direct coupling, and by designating the Event Space as the authoritative coordination mechanism.

### 6.7.2 Architectural Role

Cross-Capability Coordination is **not a component**. It is an architectural regime — a set of principles, constraints, and interaction rules that govern the relationships between the four execution facades.

Within the AI-OS layered architecture (Part 1), Cross-Capability Coordination occupies a mediating role in the **Capability Space** (the collection of all execution facades):

| Facade | Execution Domain | Coordination Surface |
|--------|------------------|----------------------|
| **SkillService** | Capability invocation | Event Space events, correlation identity |
| **MCPService** | External capability invocation | Event Space events, correlation identity |
| **MemoryService** | Memory access | Event Space events, correlation identity |
| **CouncilService** | Council execution | Event Space events, correlation identity |

The coordination regime establishes:

- **What** may coordinate: any combination of facades, initiated by any consumer in the Execution Plane
- **Why** coordination exists: to enable multi-facade compositions required by Engineering Services and AI Agents
- **Where** architectural boundaries exist: between facades, between Capability Space and Event Space, between Definition Plane and Execution Plane
- **What invariants** preserve architectural integrity: autonomy, unidirectional Definition Plane dependency, Event Space mediation, failure isolation, policy completeness

Cross-Capability Coordination does **not** define a coordinator component, a workflow engine, a saga manager, or an orchestration layer. Such constructs would violate the autonomy invariants of Sections 6.3–6.6. Instead, it defines the architectural contract that makes coordination *possible* without coordination *logic* being centralized.

### 6.7.3 Coordination Principles

The following principles are **architectural law** for all cross-capability interactions. They derive from the autonomy invariants of Sections 6.3–6.6 and the Event Space architecture of Part 4.

> **PRINCIPLE-6.7.1 (Facade Autonomy)**: Each execution facade **SHALL** remain independently deployable, independently versioned, independently scalable, and independently operable. No facade **SHALL** depend on the internal implementation, internal data structures, internal APIs, or internal lifecycle of another facade.

> **PRINCIPLE-6.7.2 (Event Space Mediation)**: All asynchronous cross-facade interaction **SHALL** occur exclusively through the Event Space (Part 4). No facade **SHALL** invoke another facade's APIs directly. No facade **SHALL** share memory, databases, or internal queues with another facade. The Event Space is the **sole** coordination substrate.

> **PRINCIPLE-6.7.3 (Definition Plane Exclusion)**: Cross-capability coordination **SHALL NOT** involve Definition Plane components (SkillManager, MCPManager, MemoryManager, CouncilManager). Coordination operates exclusively in the Execution Plane among execution facades. Definition Plane components publish events; they do not participate in execution-time coordination.

> **PRINCIPLE-6.7.4 (Correlation Identity as Coordination Key)**: A **correlation identity** generated at the consumer ingress point **SHALL** be the sole mechanism for associating related operations across facades. Each facade **SHALL** propagate the correlation identity in all Event Space events it produces. No other implicit association mechanism (timing, payload similarity, caller identity) **SHALL** be used for coordination.

> **PRINCIPLE-6.7.5 (Policy Coherence Without Centralization)**: Cross-cutting execution policies (authorization, rate limiting, quotas, audit) **SHALL** be evaluated at each facade boundary independently, using policy definitions consumed from the Policy Manager via the Event Space. No facade **SHALL** delegate policy evaluation to another facade. No central policy orchestration layer **SHALL** exist. Policy coherence emerges from shared policy definitions, not shared policy enforcement.

> **PRINCIPLE-6.7.6 (Failure Isolation Across Facades)**: A failure in one facade's execution domain (index corruption, dependency unavailability, resource exhaustion, participant failure) **SHALL NOT** cause failure in another facade's execution domain. Each facade's failure containment boundary (established in Sections 6.3.16, 6.4.16, 6.5.16, 6.6.16) **SHALL** extend to cross-facade compositions. A facade **SHALL** degrade gracefully (per its own Degraded mode) without propagating its degraded state as a failure to other facades.

> **PRINCIPLE-6.7.7 (Consumer-Driven Coordination)**: Cross-facade coordination **SHALL** be consumer-driven by default. Consumers (Engineering Services, AI Agents) operating in the Execution Plane **SHALL** initiate and drive multi-facade compositions. Facades **SHALL NOT** initiate invocations on other facades on behalf of consumers unless such behavior is explicitly defined as part of that facade's approved architecture (e.g., CouncilService coordinating council participants per Section 6.6). This exception does not create general facade-to-facade coupling.

> **PRINCIPLE-6.7.8 (No Distributed Transaction Semantics)**: The architecture **SHALL NOT** provide atomic commit, distributed transaction, or saga orchestration across facades. Each facade operation is independently committed or failed at its own boundary. Consumers **SHALL** implement their own compensation logic if multi-facade atomicity is required. The architecture provides correlation identity and observability events to enable compensation; it does **not** provide coordination logic.

### 6.7.4 Coordination Model

The Cross-Capability Coordination model defines the conceptual structure of how facades relate during multi-facade compositions. It is a **model**, not a mechanism — it describes the architectural relationships that emerge when Principles 6.7.1–6.7.8 are satisfied.

#### 6.7.4.1 Coordination Topology

The coordination topology is **star-shaped with the consumer at the center**:

```
         ┌─────────────────┐
         │  Engineering    │
         │  Service /      │
         │  AI Agent       │
         │  (Consumer)     │
         └────────┬────────┘
                  │
       ┌──────────┼──────────┬──────────────┬──────────────┐
       ▼          ▼          ▼              ▼              ▼
┌────────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐
│ Skill      │ │ MCP      │ │ Memory   │ │ Council    │ │ Event      │
│ Service    │ │ Service  │ │ Service  │ │ Service    │ │ Space      │
└────────────┘ └──────────┘ └──────────┘ └────────────┘ └────────────┘
       │          │          │              │              │
       └──────────┴──────────┴──────────────┴──────────────┘
                          │
                    Correlation Identity
                    (propagated by all)
```

The consumer **owns the composition**. Each facade operates independently, receiving invocation requests from the consumer and emitting events to the Event Space. The Event Space provides the event fabric that makes the composition observable, auditable, and debuggable — but it does **not** orchestrate.

#### 6.7.4.2 Correlation Identity Model

The **correlation identity** is the architectural primitive that enables coordination without coupling.

- **Generation**: The consumer (or the ingress gateway on the consumer's behalf) generates a globally unique correlation identity at the start of a logical operation that may span multiple facades.
- **Propagation**: The consumer **SHALL** pass the correlation identity to every facade invocation. Each facade **SHALL** propagate the correlation identity to all Event Space events it produces (started, completed, failed, policy violation, schema validation failed, staleness, etc.) and to all participant/external provider interactions it mediates.
- **Consumption**: Platform managers (MonitoringManager, AuditManager, SecurityManager, QuotaManager) and consumers **MAY** use the correlation identity to reconstruct the end-to-end operation trace across facades.
- **Scope**: A correlation identity **SHALL** span a single consumer-initiated logical operation. It **SHALL NOT** be reused across unrelated operations. It **SHALL NOT** be generated by facades.

#### 6.7.4.3 Event Space as Coordination Fabric

The Event Space (Part 4) provides the **coordination fabric** — the infrastructure that makes cross-facade composition observable and governable without centralized control.

Each facade produces a canonical set of execution observability events (defined in Sections 6.3.8, 6.4.8, 6.5.8, 6.6.8). When a consumer composes facades, the Event Space contains an interleaved, correlation-ordered stream of events from all participating facades. This stream is the **single source of truth** for:

- **Observability**: Platform managers reconstruct execution timelines, latency distributions, error rates, and dependency graphs.
- **Audit**: AuditManager verifies policy compliance, data access patterns, and authorization chains across facades.
- **Debugging**: Consumers and operators trace failures across facade boundaries using correlation identity.
- **Automated Remediation**: Platform managers detect cross-facade anomaly patterns (cascading timeouts, correlated quota exhaustion, correlated schema violations) and trigger remediation.

The Event Space does **not** provide:
- Ordering guarantees across events from different facades (events are ordered per-facade; cross-facade ordering is by correlation identity at consumption time).
- Delivery guarantees to specific consumers (Event Space is a publish-subscribe fabric; consumers subscribe to event types).
- Transaction boundaries (each facade event represents an independent facade operation).

#### 6.7.4.4 Composition Strategy

The architecture **does not prescribe** execution or composition patterns. Consumers and approved capability architectures determine composition strategy. Regardless of composition style, all cross-capability interactions **SHALL** preserve:

- Capability autonomy
- Execution boundary integrity
- Event Space coordination
- Policy enforcement
- Failure isolation
- Correlation identity propagation

A capability **MAY** coordinate interactions with other capabilities only when such behavior is explicitly defined as part of that capability's approved architecture (e.g., CouncilService dispatching to council participants per Section 6.6). This exception does not create general facade-to-facade coupling.

#### 6.7.4.5 Staleness Independence

Each facade maintains its own execution/access index with its own staleness bound **T_index_max** (Sections 6.3.7, 6.4.7, 6.5.7, 6.6.7). Cross-facade composition **SHALL NOT** introduce a unified staleness bound. A consumer observing a composition **MAY** encounter different staleness windows per facade. The architecture **SHALL NOT** provide a "consistent snapshot" of all facades' indices simultaneously. Consumers **SHALL** tolerate per-facade staleness as an inherent property of the event-driven projection model.

#### 6.7.4.6 Degraded Mode Composition

When one facade enters **Degraded** mode (Sections 6.3.10, 6.4.10, 6.5.10, 6.6.10), it continues serving from its last consistent index while emitting staleness events. Other facades remain in **Serving** mode. A consumer composing across them experiences:

- Successful invocations on Serving-mode facades.
- Rejected or degraded invocations on the Degraded-mode facade (per that facade's safe-mode semantics: fail-open or fail-closed per policy domain).

The Degraded-mode facade's staleness events are visible in the Event Space. Other facades **SHALL NOT** alter their behavior based on another facade's Degraded state. There is **no** cross-facade health propagation.

---

### 6.7.5 Cross-Capability Interaction Rules

The following rules govern all interactions between execution facades. They are **architectural laws** — violations constitute architectural defects regardless of functional correctness.

#### 6.7.5.1 Permitted Interactions

| Interaction | Description |
|-------------|-------------|
| Consumer → Facade | Consumers (Engineering Services, AI Agents) **SHALL** invoke facades through their Execution Contracts. This is the primary and intended interaction path. |
| Facade → Event Space (produce) | Each facade **SHALL** publish execution observability events to the Event Space per its event contract (Sections 6.3.8, 6.4.8, 6.5.8, 6.6.8). |
| Facade → Event Space (consume) | Each facade **SHALL** consume registration and policy events from the Event Space to maintain index currency. |
| Facade → Participant/Provider | A facade **MAY** invoke its own participants/external providers as defined in its architecture (SkillService → capabilities, MCPService → external providers, MemoryService → memory providers, CouncilService → council members). |
| CouncilService → Facade (mediated) | CouncilService **MAY** dispatch to other facades when executing a council whose participants are served by those facades, per Section 6.6. This is the **sole** facade-to-facade invocation path. |

#### 6.7.5.2 Prohibited Interactions

| Interaction | Rationale |
|-------------|-----------|
| Facade → Facade (direct) | No facade **SHALL** invoke another facade's Execution Contract directly. This includes synchronous API calls, internal method invocations, and shared library calls that cross facade boundaries. |
| Facade → Facade (shared state) | No facade **SHALL** share memory, databases, caches, queues, or any mutable state with another facade. |
| Facade → Manager (direct) | No Execution Plane facade **SHALL** invoke Definition Plane Managers (SkillManager, MCPManager, MemoryManager, CouncilManager) or Manager Space components directly. All Manager interactions are via Event Space events. |
| Facade → Consumer (callback) | No facade **SHALL** invoke callbacks, webhooks, or push notifications to consumers outside the Execution Contract's defined response model (Request–Response, Request–Stream). |
| Consumer → Manager (direct) | Consumers **SHALL NOT** invoke Definition Plane Managers. All consumer interactions with capabilities transit the Execution Contracts. |
| Consumer → Participant/Provider (direct) | Consumers **SHALL NOT** communicate directly with capability processes, external providers, memory providers, or council members. All interactions transit the respective facade. |
| Definition Plane → Execution Plane (direct) | Definition Plane components **SHALL NOT** invoke Execution Plane facades. The dependency direction is strictly Definition Plane → Event Space → Execution Plane. |

#### 6.7.5.3 Execution Boundary Preservation

> **RULE-6.7.1 (Execution Boundary Integrity)**: Each facade's execution boundary **SHALL** be preserved in all cross-capability compositions. The facade **SHALL** validate all inputs against its declared schema, enforce all policies applicable to its domain, normalize all outputs to its canonical result contract, and emit its observability events. No composition **SHALL** bypass, weaken, or delegate any of these responsibilities.

> **RULE-6.7.2 (No Boundary Leakage)**: Internal facade concerns (execution index structure, pipeline stage details, participant pool management, transport connection state, consistency domain coordination) **SHALL NOT** leak across facade boundaries. Consumers and other facades interact exclusively through the Execution Contract and Event Space events.

#### 6.7.5.4 Ownership Preservation

> **RULE-6.7.3 (Ownership Invariance)**: Cross-capability composition **SHALL NOT** transfer ownership of any architectural concern. Each facade retains exclusive ownership of its Execution Contract, execution index, policy enforcement boundary, failure containment domain, correlation identity propagation for its domain, and resource lifecycle. A facade **SHALL NOT** assume responsibility for another facade's concerns, nor **SHALL** it relinquish its own.

#### 6.7.5.5 Contract-Based Interaction

> **RULE-6.7.4 (Contract Conformance)**: All interactions between consumers and facades **SHALL** conform strictly to the facade's Execution Contract. The Execution Contract defines: valid operations, argument schemas, result schemas, error taxonomy, timeout semantics, cancellation model, streaming protocol (where applicable), and correlation identity handling. No interaction **SHALL** rely on implementation-specific behaviors, undocumented extensions, or version-specific quirks.

> **RULE-6.7.5 (Contract Stability)**: Execution Contracts **SHALL** be stable across facade versions. Breaking changes to an Execution Contract require a new facade version. Consumers **SHALL NOT** depend on behaviors outside the declared contract.

#### 6.7.5.6 Policy Boundary Preservation

> **RULE-6.7.6 (Policy Enforcement Locality)**: Policy evaluation **SHALL** occur at each facade boundary independently. A facade **SHALL** evaluate authorization, quota, rate limiting, and other execution policies using its own policy evaluation logic against policy definitions consumed from the Policy Manager via the Event Space. No facade **SHALL** trust another facade's policy decision. No facade **SHALL** skip policy evaluation because a prior facade evaluated policy.

> **RULE-6.7.7 (Policy Definition Sharing)**: Policy definitions are shared via the Event Space. All facades consume the same policy events from the Policy Manager. Policy coherence is achieved through shared definitions, not shared enforcement.

#### 6.7.5.7 Capability Autonomy Preservation

> **RULE-6.7.8 (Autonomy Preservation in Composition)**: When a consumer composes multiple facades, each facade **SHALL** operate as if it were the sole facade invoked. No facade **SHALL** alter its behavior based on the presence, absence, or behavior of other facades in the composition. Specifically: no facade **SHALL** optimize for another facade, coordinate with another facade, wait for another facade, or propagate its internal state to another facade.

#### 6.7.5.8 Correlation Identity Continuity

> **RULE-6.7.9 (Correlation Identity Propagation)**: A correlation identity provided by the consumer **SHALL** be propagated by every facade in the composition. Each facade **SHALL** include the correlation identity in: all Event Space events it produces for that operation, all participant/provider invocations it mediates, all observability signals, and the Execution Result returned to the consumer. A facade **SHALL NOT** generate a new correlation identity for a consumer-initiated operation. A facade **SHALL NOT** strip or modify the correlation identity.

### 6.7.6 Event Space Coordination

The Event Space (Part 4) serves as the **sole architectural coordination substrate** for cross-capability composition. This section describes its role in coordination; it does not redefine the Event Space architecture.

#### 6.7.6.1 Event Publication

Each facade **SHALL** publish execution observability events to the Event Space as defined in its architecture:

- **SkillService**: `InvocationStarted`, `InvocationCompleted`, `InvocationFailed`, `InvocationCancelled`, `PolicyViolation`, `SchemaValidationFailed`, `ExecutionIndexStalenessExceeded` (Section 6.3.8).
- **MCPService**: `MCPInvocationStarted`, `MCPInvocationCompleted`, `MCPInvocationFailed`, `MCPInvocationCancelled`, `MCPInvocationStreamChunk`, `MCPPolicyViolation`, `MCPSchemaValidationFailed`, `MCPTransportError`, `MCPServerUnhealthy`, `MCPExecutionIndexStalenessExceeded` (Section 6.4.8).
- **MemoryService**: `MemoryAccessStarted`, `MemoryAccessCompleted`, `MemoryAccessFailed`, `MemoryAccessCancelled`, `MemoryAccessStreamChunk`, `MemoryPolicyViolation`, `MemorySchemaValidationFailed`, `MemoryConsistencyViolation`, `MemoryProviderError`, `AccessIndexStalenessExceeded` (Section 6.5.8).
- **CouncilService**: `CouncilExecutionStarted`, `CouncilExecutionCompleted`, `CouncilExecutionFailed`, `CouncilExecutionCancelled`, `CouncilPolicyViolation`, `CouncilSchemaValidationFailed`, `CouncilMemberUnhealthy`, `CouncilExecutionIndexStalenessExceeded` (Section 6.6.8).

All events **SHALL** carry the correlation identity. Event schemas are defined by each facade and are part of its Execution Contract.

#### 6.7.6.2 Event Consumption

Each facade **SHALL** consume the following event streams from the Event Space:

- **Registration events** from its Definition Plane Manager (SkillManager, MCPManager, MemoryManager, CouncilManager) to maintain execution/access index currency.
- **Policy events** from the Policy Manager (Part 2) to maintain policy evaluation currency.
- **Credential events** from the Secret Manager (Part 2) where applicable (MCPService, MemoryService, CouncilService).

Event consumption **SHALL** be ordered, idempotent, and maintain consistent projection semantics. Facades **SHALL NOT** consume execution observability events from other facades for coordination purposes.

#### 6.7.6.3 Observability Coordination

The Event Space provides the **unified observability fabric** for cross-capability compositions:

- Consumers and platform managers **MAY** subscribe to execution observability events from all facades.
- By filtering on correlation identity, observers reconstruct the end-to-end operation trace across facades.
- No facade **SHALL** aggregate or forward observability events from other facades. Each facade publishes its own events; the Event Space provides the union.

#### 6.7.6.4 Policy Event Propagation

Policy Manager events published to the Event Space are consumed independently by each facade. This ensures:

- All facades operate on the same policy definitions (eventual consistency bounded by Event Space delivery).
- Policy changes propagate to all facades without direct coupling to Policy Manager.
- No facade acts as a policy proxy for another facade.

#### 6.7.6.5 Correlation Propagation

The correlation identity is the **coordination key** in the Event Space:

- Every facade event related to a consumer operation **SHALL** include the correlation identity.
- Cross-facade correlation is achieved at consumption time by grouping events by correlation identity.
- The Event Space does not enforce, validate, or route by correlation identity — it is a payload field.

#### 6.7.6.6 Decoupling Guarantees

The Event Space provides the following architectural decoupling guarantees for cross-capability coordination:

- **Temporal decoupling**: Facades operate on eventually consistent projections. A facade's index may be stale relative to another facade's index; this is normal and bounded by **T_index_max**.
- **Failure decoupling**: Event Space unavailability in one facade's consumption path does not affect other facades' Event Space interactions.
- **Scaling decoupling**: Facades scale event consumption independently. High event throughput in one facade does not backpressure another.
- **Evolution decoupling**: Facade event schemas evolve independently. The Event Space carries versioned events; consumers handle versioning.

### 6.7.7 Dependency Constraints

The following matrix defines the architectural dependency constraints between all components in the Capability Space and adjacent spaces. These are **structural constraints** — they define what dependencies are permitted, required, or forbidden by the architecture.

| From | To | Dependency | Type | Rationale |
|------|-----|------------|------|-----------|
| **SkillService** | Event Space | **Required** | Infrastructure | Event consumption/production |
| **SkillService** | SkillManager (events) | **Required** | Event subscription | Index currency |
| **SkillService** | Policy Manager (events) | **Required** | Event subscription | Policy currency |
| **SkillService** | Policy Manager | **Required** | Policy consumption | Policy enforcement |
| **SkillService** | SkillManager (API) | **Forbidden** | — | Definition Plane purity |
| **SkillService** | MCPService | **Forbidden** | — | Facade autonomy |
| **SkillService** | MemoryService | **Forbidden** | — | Facade autonomy |
| **SkillService** | CouncilService | **Forbidden** | — | Facade autonomy |
| **SkillService** | MCPManager | **Forbidden** | — | Definition Plane purity |
| **SkillService** | MemoryManager | **Forbidden** | — | Definition Plane purity |
| **SkillService** | CouncilManager | **Forbidden** | — | Definition Plane purity |
| **SkillService** | Secret Manager | **Forbidden** | — | No external credentials |
| **SkillService** | Capability Process | **Required** | Execution | Capability invocation |
| **MCPService** | Event Space | **Required** | Infrastructure | Event consumption/production |
| **MCPService** | MCPManager (events) | **Required** | Event subscription | Index currency |
| **MCPService** | Policy Manager (events) | **Required** | Event subscription | Policy currency |
| **MCPService** | Policy Manager | **Required** | Policy consumption | Policy enforcement |
| **MCPService** | Secret Manager | **Required** | Credential consumption | External auth mediation |
| **MCPService** | MCPManager (API) | **Forbidden** | — | Definition Plane purity |
| **MCPService** | SkillService | **Forbidden** | — | Facade autonomy |
| **MCPService** | MemoryService | **Forbidden** | — | Facade autonomy |
| **MCPService** | CouncilService | **Forbidden** | — | Facade autonomy |
| **MCPService** | SkillManager | **Forbidden** | — | Definition Plane purity |
| **MCPService** | MemoryManager | **Forbidden** | — | Definition Plane purity |
| **MCPService** | CouncilManager | **Forbidden** | — | Definition Plane purity |
| **MCPService** | External Provider | **Required** | Execution | External capability invocation |
| **MemoryService** | Event Space | **Required** | Infrastructure | Event consumption/production |
| **MemoryService** | MemoryManager (events) | **Required** | Event subscription | Index currency |
| **MemoryService** | Policy Manager (events) | **Required** | Event subscription | Policy currency |
| **MemoryService** | Policy Manager | **Required** | Policy consumption | Access policy enforcement |
| **MemoryService** | Secret Manager | **Required** | Credential consumption | Provider auth mediation |
| **MemoryService** | MemoryManager (API) | **Forbidden** | — | Definition Plane purity |
| **MemoryService** | SkillService | **Forbidden** | — | Facade autonomy |
| **MemoryService** | MCPService | **Forbidden** | — | Facade autonomy |
| **MemoryService** | CouncilService | **Forbidden** | — | Facade autonomy |
| **MemoryService** | SkillManager | **Forbidden** | — | Definition Plane purity |
| **MemoryService** | MCPManager | **Forbidden** | — | Definition Plane purity |
| **MemoryService** | CouncilManager | **Forbidden** | — | Definition Plane purity |
| **MemoryService** | Memory Provider | **Required** | Execution | Memory access |
| **CouncilService** | Event Space | **Required** | Infrastructure | Event consumption/production |
| **CouncilService** | CouncilManager (events) | **Required** | Event subscription | Index currency |
| **CouncilService** | Policy Manager (events) | **Required** | Event subscription | Policy currency |
| **CouncilService** | Policy Manager | **Required** | Policy consumption | Execution policy enforcement |
| **CouncilService** | Secret Manager | **Required** | Credential consumption | Member auth mediation |
| **CouncilService** | CouncilManager (API) | **Forbidden** | — | Definition Plane purity |
| **CouncilService** | SkillService | **Forbidden*** | — | Facade autonomy |
| **CouncilService** | MCPService | **Forbidden*** | — | Facade autonomy |
| **CouncilService** | MemoryService | **Forbidden*** | — | Facade autonomy |
| **CouncilService** | SkillManager | **Forbidden** | — | Definition Plane purity |
| **CouncilService** | MCPManager | **Forbidden** | — | Definition Plane purity |
| **CouncilService** | MemoryManager | **Forbidden** | — | Definition Plane purity |
| **CouncilService** | Council Member (facade) | **Required*** | Execution | Council participant dispatch |
| **Engineering Service** | SkillService | **Required** | API invocation | Capability execution |
| **Engineering Service** | MCPService | **Required** | API invocation | External capability execution |
| **Engineering Service** | MemoryService | **Required** | API invocation | Memory access |
| **Engineering Service** | CouncilService | **Required** | API invocation | Council execution |
| **Engineering Service** | SkillManager | **Forbidden** | — | Facade integrity |
| **Engineering Service** | MCPManager | **Forbidden** | — | Facade integrity |
| **Engineering Service** | MemoryManager | **Forbidden** | — | Facade integrity |
| **Engineering Service** | CouncilManager | **Forbidden** | — | Facade integrity |
| **Engineering Service** | Capability Process | **Forbidden** | — | Capability boundary |
| **Engineering Service** | External Provider | **Forbidden** | — | External boundary |
| **Engineering Service** | Memory Provider | **Forbidden** | — | Memory boundary |
| **Engineering Service** | Council Member | **Forbidden** | — | Council boundary |
| **AI Agent** | SkillService | **Required** | API invocation | Capability execution |
| **AI Agent** | MCPService | **Required** | API invocation | External capability execution |
| **AI Agent** | MemoryService | **Required** | API invocation | Memory access |
| **AI Agent** | CouncilService | **Required** | API invocation | Council execution |
| **AI Agent** | All Managers | **Forbidden** | — | Facade integrity |
| **AI Agent** | All Providers/Members | **Forbidden** | — | Boundary enforcement |
| **Definition Plane Managers** | Execution Facades | **Forbidden** | — | Unidirectional dependency |
| **Definition Plane Managers** | Event Space | **Required** | Infrastructure | Event publication |
| **Manager Space** | Execution Facades | **Forbidden** | — | Manager/Event Space separation |
| **Manager Space** | Event Space | **Required** | Infrastructure | Event consumption |

\* **CouncilService exception**: CouncilService **MAY** dispatch to other facades' Execution Contracts when executing a council whose participants are served by those facades (Section 6.6). This is an architectural exception explicitly defined in CouncilService's approved architecture. It does not create a general dependency — the dependency is on the Execution Contract interface, not the facade implementation.

### 6.7.8 Architectural Invariants

The following invariants are the **architectural laws** of Cross-Capability Coordination. They are necessary conditions for the Capability Space architecture to hold. Implementation decisions that violate them constitute architectural defects, regardless of functional correctness.

> **INV-6.7.1 (Facade Autonomy — Cross-Capability)**: No execution facade depends on another facade's internal implementation, internal data structures, internal APIs, or internal lifecycle. Each facade is independently deployable, versioned, scalable, and operable.

> **INV-6.7.2 (Event Space Mediation — Cross-Capability)**: All asynchronous cross-facade interaction occurs exclusively through the Event Space. No facade invokes another facade's APIs directly. No facade shares memory, databases, or internal queues with another facade.

> **INV-6.7.3 (Definition Plane Exclusion — Cross-Capability)**: Cross-capability coordination does not involve Definition Plane components (SkillManager, MCPManager, MemoryManager, CouncilManager). Coordination operates exclusively in the Execution Plane. Definition Plane components publish events; they do not participate in execution-time coordination.

> **INV-6.7.4 (Consumer-Driven Coordination)**: Cross-facade coordination is consumer-driven by default. Facades do not initiate invocations on other facades on behalf of consumers unless explicitly defined in that facade's approved architecture (e.g., CouncilService per Section 6.6). This exception does not create general facade-to-facade coupling.

> **INV-6.7.5 (Execution Boundary Integrity — Cross-Capability)**: Each facade's execution boundary is preserved in all cross-capability compositions. The facade validates inputs against its declared schema, enforces all applicable policies, normalizes outputs to its canonical result contract, and emits its observability events. No composition bypasses, weakens, or delegates these responsibilities.

> **INV-6.7.6 (Ownership Invariance — Cross-Capability)**: Cross-capability composition does not transfer ownership of any architectural concern. Each facade retains exclusive ownership of its Execution Contract, execution index, policy enforcement boundary, failure containment domain, correlation identity propagation for its domain, and resource lifecycle.

> **INV-6.7.7 (Policy Coherence Without Centralization)**: Cross-cutting execution policies are evaluated at each facade boundary independently, using policy definitions consumed from the Policy Manager via the Event Space. No facade delegates policy evaluation to another facade. No central policy orchestration layer exists. Policy coherence emerges from shared policy definitions, not shared policy enforcement.

> **INV-6.7.8 (Failure Isolation — Cross-Capability)**: A failure in one facade's execution domain (index corruption, dependency unavailability, resource exhaustion, participant/provider failure) does not cause failure in another facade's execution domain. Each facade's failure containment boundary extends to cross-facade compositions. A facade degrades gracefully per its own Degraded mode without propagating degraded state as failure to other facades.

> **INV-6.7.9 (Contract Conformance — Cross-Capability)**: All interactions between consumers and facades conform strictly to the facade's Execution Contract. No interaction relies on implementation-specific behaviors, undocumented extensions, or version-specific quirks.

> **INV-6.7.10 (Correlation Identity Continuity — Cross-Capability)**: A correlation identity provided by the consumer is propagated by every facade in the composition. Each facade includes the correlation identity in all Event Space events it produces for that operation, all participant/provider invocations it mediates, all observability signals, and the Execution Result returned to the consumer. No facade generates a new correlation identity for a consumer-initiated operation. No facade strips or modifies the correlation identity.

> **INV-6.7.11 (Staleness Independence — Cross-Capability)**: Each facade maintains its own execution/access index with its own staleness bound **T_index_max**. Cross-facade composition does not introduce a unified staleness bound. The architecture does not provide a "consistent snapshot" of all facades' indices simultaneously.

> **INV-6.7.12 (No Distributed Transaction Semantics — Cross-Capability)**: The architecture does not provide atomic commit, distributed transaction, or saga orchestration across facades. Each facade operation is independently committed or failed at its own boundary. Consumers implement their own compensation logic if multi-facade atomicity is required.

> **INV-6.7.13 (Capability Substitutability — Cross-Capability)**: Each facade can be stubbed, mocked, or replaced (e.g., with a local executor for development) without affecting other facades, without touching Definition Plane Managers, and without requiring changes to consumers (provided the Execution Contract is implemented).

> **INV-6.7.14 (Unidirectional Definition Plane Dependency — Cross-Capability)**: All Execution Plane facades depend on their respective Definition Plane Manager's published events. No Definition Plane Manager depends on any Execution Plane facade. No Definition Plane Manager invokes any Execution Plane facade.

> **INV-6.7.15 (Manager Space Separation — Cross-Capability)**: Execution facades do not directly invoke Manager Space components (Part 2). All Manager Space interactions are indirect via the Event Space (consuming registration events, policy events, credential events; producing observability events consumed by platform managers).

---

### 6.7.9 Failure Isolation

The Cross-Capability Coordination architecture extends the failure containment boundaries of each facade (Sections 6.3.16, 6.4.16, 6.5.16, 6.6.16) to cross-facade compositions. This section defines the architectural isolation guarantees; it does not describe recovery procedures, health checks, or operational remediation.

#### 6.7.9.1 Independent Failure Domains

Each execution facade constitutes an **independent failure domain**. The failure domains are:

| Failure Domain | Scope | Containment Boundary |
|----------------|-------|---------------------|
| **SkillService** | Capability invocation pipeline, execution index, policy evaluation cache, schema validator cache, in-flight invocation state | Capability process crashes, timeouts, schema violations, policy service unavailability, event stream unavailability |
| **MCPService** | External capability invocation pipeline, execution index, transport connection pools, protocol session state, policy evaluation cache | External provider process crashes, transport failures, protocol violations, authentication failures, policy service unavailability, event stream unavailability |
| **MemoryService** | Memory access pipeline, access index, memory abstraction bindings, consistency domain state, quota tracking state | Memory provider crashes, timeouts, protocol violations, corruption detection, consistency violations, policy service unavailability, event stream unavailability |
| **CouncilService** | Council execution pipeline, execution index, member binding pools, protocol session state, policy evaluation cache | Council member crashes, timeouts, protocol violations, schema violations, policy service unavailability, event stream unavailability |

A failure within one domain **SHALL NOT** compromise the integrity, availability, or correctness of any other domain.

#### 6.7.9.2 Containment Boundaries

The following architectural boundaries enforce failure isolation across facades:

> **BOUNDARY-6.7.1 (Execution Index Isolation)**: Each facade's execution/access index is a read-only projection reconstructed from its Definition Plane Manager's event stream. An index corruption in one facade (e.g., SkillService) cannot affect another facade's index (e.g., MemoryService). Indices are physically and logically separate.

> **BOUNDARY-6.7.2 (Event Space Consumption Isolation)**: Each facade consumes the Event Space independently. Event stream unavailability, backpressure, or consumer lag in one facade's consumption path does not affect other facades' Event Space interactions. The Event Space infrastructure itself is shared, but consumption is per-facade.

> **BOUNDARY-6.7.3 (Policy Evaluation Isolation)**: Each facade evaluates policy independently using its own policy evaluation logic against cached policy definitions. Policy service unavailability causes each facade to enter its own Degraded mode (fail-open or fail-closed per its policy domain configuration) independently. One facade's policy degradation does not trigger another's.

> **BOUNDARY-6.7.4 (Resource Exhaustion Isolation)**: Resource limits (memory, file descriptors, connection pools, in-flight operation tracking) are enforced per facade. Exhaustion in one facade (e.g., MCPService transport pool exhaustion) does not consume resources of another facade (e.g., MemoryService abstraction bindings).

> **BOUNDARY-6.7.5 (Participant/Provider Isolation)**: A failure in a capability process, external provider, memory provider, or council member affects only the facade that mediates that participant. Other facades' participants/providers remain unaffected. CouncilService's mediated dispatch to other facades (Section 6.6) respects this boundary — a participant failure in SkillService does not propagate as a facade failure to CouncilService; it is handled per the council protocol.

#### 6.7.9.3 Coordination Resilience

Cross-facade compositions are resilient to partial facade failures by architectural design:

- **Consumer-driven composition**: The consumer initiates each facade invocation independently. A failure in Facade A does not block the consumer from invoking Facade B.
- **Independent error semantics**: Each facade returns its own canonical error contract. Errors do not cascade across facades.
- **No distributed transactions**: Per INV-6.7.12, there is no atomic commit across facades. A failure in one facade's operation does not trigger rollback in another facade's completed operation.
- **Correlation persistence**: Per INV-6.7.10, correlation identity continues to propagate through successful facade invocations even when other facades in the composition fail. The Event Space retains the full event trace for observability and compensation.

#### 6.7.9.4 Event Space Independence

The Event Space provides coordination fabric independence:

- **Production independence**: A facade's ability to publish events is independent of other facades' publishing. One facade's event publication backpressure does not block another's.
- **Consumption independence**: A facade's event consumption lag or failure does not affect other facades' consumption.
- **Schema independence**: Facade event schemas evolve independently. A schema change in CouncilService events does not affect SkillService event consumers.
- **Delivery independence**: Event Space delivery guarantees (at-least-once, ordering per partition) apply per event stream. Cross-facade ordering is not guaranteed and not required.

#### 6.7.9.5 Degraded-Mode Independence

When a facade enters **Degraded** mode (per its lifecycle, Sections 6.3.10, 6.4.10, 6.5.10, 6.6.10):

- The degraded facade continues serving from its last consistent index.
- Other facades remain in **Serving** mode unaffected.
- The degraded facade emits staleness events to the Event Space.
- Other facades **SHALL NOT** alter their behavior based on another facade's Degraded state.
- There is **no** cross-facade health propagation, no circuit breaker chaining, no coordinated failover.

A composition spanning a Serving-mode facade and a Degraded-mode facade yields: successful results from the Serving-mode facade, and degraded/rejected results from the Degraded-mode facade. The composition continues at the consumer level; the architecture does not halt the composition.

#### 6.7.9.6 Correlation Continuity During Failures

Correlation identity propagation is **failure-transparent**:

- A correlation identity generated by the consumer persists across all facade invocations in the composition.
- If Facade A fails, the correlation identity is included in Facade A's failure event.
- The consumer continues invoking Facade B, C, etc. with the same correlation identity.
- Facade B, C, etc. propagate the correlation identity in their events and results.
- The Event Space contains a complete, correlation-grouped trace of the composition including successes and failures.
- No facade **SHALL** generate a new correlation identity due to another facade's failure.

#### 6.7.9.7 Execution Boundary Preservation During Failures

Even during cross-facade failures, each facade's execution boundary remains intact:

- A failing facade **SHALL** still validate inputs against its schema (if the request was received).
- A failing facade **SHALL** still enforce policies (if policy evaluation is available).
- A failing facade **SHALL** still emit observability events for the failure.
- A failing facade **SHALL** still return its canonical error contract to the consumer.
- No facade **SHALL** bypass its boundary responsibilities due to another facade's failure.

---

### 6.7.10 Architecture Decision Records

#### ADR-6.7.1: Coordination by Architectural Rules, Not Central Component

**Decision**: Cross-capability coordination is governed by architectural principles, interaction rules, and invariants rather than a central coordination component (workflow engine, saga orchestrator, or coordination service).

**Rationale**: A central coordinator would create a single point of failure, a scaling bottleneck, a coupling nexus, and a violation of facade autonomy (INV-6.7.1). It would require facades to expose internal coordination interfaces, leak execution boundary details, and surrender ownership of their execution lifecycle. The approved architecture (Sections 6.3–6.6) establishes each facade as an independently operable subsystem with its own execution index, policy boundary, and failure domain. A coordinator would invert this ownership.

**Consequences**:
- Consumers drive composition logic (consumer-driven coordination, INV-6.7.4).
- No facade-to-facade invocation chain exists by default (PRINCIPLE-6.7.7).
- CouncilService's mediated dispatch to other facades is an explicit, architecture-approved exception (Section 6.6), not a general pattern.
- Observability and audit rely on Event Space correlation, not coordinator state.
- Compensation logic is consumer responsibility (INV-6.7.12).

#### ADR-6.7.2: Event Space as Exclusive Coordination Substrate

**Decision**: All asynchronous cross-facade interaction occurs exclusively through the Event Space (Part 4). No direct facade-to-facade communication, shared state, or synchronous API calls are permitted.

**Rationale**: Direct facade-to-facade communication would create cyclic dependencies, temporal coupling (facades must be simultaneously available), implementation coupling (facades must agree on internal interfaces), and failure coupling (one facade's failure cascades to callers). The Event Space provides temporal decoupling (eventually consistent projections), failure decoupling (independent consumption), scaling decoupling (independent consumer scaling), and evolution decoupling (independent event schema evolution) — all required by the autonomy invariants of Sections 6.3–6.6.

**Consequences**:
- Facades consume registration and policy events independently.
- Facades publish observability events independently.
- Correlation identity is the sole cross-facade association mechanism (PRINCIPLE-6.7.4).
- Cross-facade ordering is not guaranteed; consumers correlate at consumption time.
- No facade acts as an Event Space proxy for another facade.

#### ADR-6.7.3: Execution Facades Remain Autonomous Despite Coordinated Composition

**Decision**: Facade autonomy (INV-6.7.1) is preserved in all cross-capability compositions. Each facade operates as if it were the sole facade invoked, with no awareness of other facades in the composition.

**Rationale**: If facades adapted behavior based on other facades' presence (e.g., optimizing for a known composition, skipping policy because another facade validated, sharing caches), autonomy would be violated. Independent deployability, versioning, scaling, and operability would be compromised. The architecture must support arbitrary composition by consumers without facade coordination logic.

**Consequences**:
- No facade optimizes for another facade (RULE-6.7.8).
- No facade coordinates with another facade.
- No facade waits for another facade.
- Policy evaluation occurs at every facade boundary independently (RULE-6.7.6).
- Execution boundaries are preserved in all compositions (INV-6.7.5).
- Ownership of architectural concerns is invariant (INV-6.7.6).

#### ADR-6.7.4: No Distributed Transaction Semantics Across Facades

**Decision**: The architecture does not provide atomic commit, distributed transactions, or saga orchestration across facades. Each facade operation is independently committed or failed at its own boundary.

**Rationale**: Distributed transactions require a coordinator, locks/leases across participants, compensation logic embedded in the infrastructure, and strong consistency guarantees — all of which violate facade autonomy, Event Space mediation, and failure isolation. The Capability Space is designed for independent, eventually consistent execution. Consumers (Engineering Services, AI Agents) operate at a higher semantic layer and are best positioned to implement domain-specific compensation (retry, reversal, notification, idempotency).

**Consequences**:
- Consumers implement their own compensation logic (INV-6.7.12).
- The architecture provides correlation identity and observability events to enable compensation.
- No facade participates in another facade's commit/rollback.
- A failure in one facade does not trigger rollback in another facade's completed operation.
- Eventual consistency is the architectural model; strong consistency is not available across facades.

---

### 6.7.11 Conformance Requirements

A conforming Cross-Capability Coordination architecture **SHALL** satisfy all of the following architectural requirements. These are structural and behavioral constraints, not implementation checklists.

#### 6.7.11.1 Capability Autonomy Conformance

- [ ] **AR-6.7.1**: No execution facade depends on another facade's internal implementation, internal data structures, internal APIs, or internal lifecycle.
- [ ] **AR-6.7.2**: Each facade is independently deployable, independently versioned, independently scalable, and independently operable.
- [ ] **AR-6.7.3**: No facade alters its behavior based on the presence, absence, or behavior of other facades in a composition.

#### 6.7.11.2 Dependency Constraint Conformance

- [ ] **AR-6.7.4**: No forbidden dependencies exist per the Dependency Constraints matrix (Section 6.7.7).
- [ ] **AR-6.7.5**: All required dependencies (Event Space, Definition Plane Manager events, Policy Manager, Secret Manager where applicable, participant/provider execution) are satisfied.
- [ ] **AR-6.7.6**: CouncilService's mediated dispatch to other facades occurs only when executing a council whose participants are served by those facades, per Section 6.6.
- [ ] **AR-6.7.7**: No Definition Plane Manager invokes any Execution Plane facade.
- [ ] **AR-6.7.8**: No Execution Plane facade directly invokes any Manager Space component.

#### 6.7.11.3 Event Space Mediation Conformance

- [ ] **AR-6.7.9**: All asynchronous cross-facade interaction occurs exclusively through the Event Space.
- [ ] **AR-6.7.10**: No facade invokes another facade's Execution Contract directly.
- [ ] **AR-6.7.11**: No facade shares memory, databases, caches, queues, or mutable state with another facade.
- [ ] **AR-6.7.12**: Facades consume registration and policy events independently; consumption is ordered, idempotent, and maintains consistent projection semantics.
- [ ] **AR-6.7.13**: Facades publish observability events independently; no facade aggregates or forwards another facade's events.
- [ ] **AR-6.7.14**: Correlation identity is included in all facade events and propagated to all participant/provider invocations.

#### 6.7.11.4 Execution Boundary Conformance

- [ ] **AR-6.7.15**: Each facade validates all inputs against its declared schema in every invocation.
- [ ] **AR-6.7.16**: Each facade enforces all applicable execution policies (authorization, quota, rate limiting) at its boundary in every invocation.
- [ ] **AR-6.7.17**: Each facade normalizes all outputs to its canonical result contract (success, error, streaming).
- [ ] **AR-6.7.18**: Each facade emits its canonical observability events for every invocation.
- [ ] **AR-6.7.19**: No composition bypasses, weakens, or delegates any facade's boundary responsibilities.

#### 6.7.11.5 Policy Enforcement Conformance

- [ ] **AR-6.7.20**: Policy evaluation occurs at each facade boundary independently.
- [ ] **AR-6.7.21**: No facade trusts another facade's policy decision.
- [ ] **AR-6.7.22**: No facade skips policy evaluation because a prior facade evaluated policy.
- [ ] **AR-6.7.23**: All facades consume policy definitions from the Policy Manager via the Event Space.
- [ ] **AR-6.7.24**: Policy coherence is achieved through shared definitions, not shared enforcement.

#### 6.7.11.6 Correlation Identity Conformance

- [ ] **AR-6.7.25**: A correlation identity provided by the consumer is propagated by every facade in the composition.
- [ ] **AR-6.7.26**: Each facade includes the correlation identity in all Event Space events it produces for that operation.
- [ ] **AR-6.7.27**: Each facade includes the correlation identity in all participant/provider invocations it mediates.
- [ ] **AR-6.7.28**: Each facade includes the correlation identity in all observability signals.
- [ ] **AR-6.7.29**: Each facade includes the correlation identity in the Execution Result returned to the consumer.
- [ ] **AR-6.7.30**: No facade generates a new correlation identity for a consumer-initiated operation.
- [ ] **AR-6.7.31**: No facade strips or modifies the correlation identity.

#### 6.7.11.7 Architectural Invariant Conformance

- [ ] **AR-6.7.32**: INV-6.7.1 through INV-6.7.15 hold under all execution conditions (Section 6.7.8).
- [ ] **AR-6.7.33**: RULE-6.7.1 through RULE-6.7.9 are enforced in all cross-capability interactions (Section 6.7.5).
- [ ] **AR-6.7.34**: PRINCIPLE-6.7.1 through PRINCIPLE-6.7.8 govern all cross-capability coordination (Section 6.7.3).
- [ ] **AR-6.7.35**: BOUNDARY-6.7.1 through BOUNDARY-6.7.5 are maintained during all failures (Section 6.7.9).

#### 6.7.11.8 Failure Isolation Conformance

- [ ] **AR-6.7.36**: A failure in one facade's execution domain does not cause failure in another facade's execution domain.
- [ ] **AR-6.7.37**: Each facade's failure containment boundary extends to cross-facade compositions.
- [ ] **AR-6.7.38**: A facade degrades gracefully per its own Degraded mode without propagating degraded state as failure to other facades.
- [ ] **AR-6.7.39**: No cross-facade health propagation, circuit breaker chaining, or coordinated failover exists.
- [ ] **AR-6.7.40**: Correlation identity continuity is maintained during partial composition failures.
- [ ] **AR-6.7.41**: Execution boundaries remain intact during cross-facade failures.

#### 6.7.11.9 Composition Conformance

- [ ] **AR-6.7.42**: Cross-facade coordination is consumer-driven by default (INV-6.7.4).
- [ ] **AR-6.7.43**: The architecture does not prescribe execution or composition patterns (Section 6.7.4.4).
- [ ] **AR-6.7.44**: Consumers and approved capability architectures determine composition strategy.
- [ ] **AR-6.7.45**: All cross-capability interactions preserve capability autonomy, execution boundary integrity, Event Space coordination, policy enforcement, failure isolation, and correlation identity propagation regardless of composition style.

---

*End of Architecture Specification Part 6 — Step 7*