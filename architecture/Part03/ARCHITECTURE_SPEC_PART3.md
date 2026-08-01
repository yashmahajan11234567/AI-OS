# AI-OS Architecture Specification v1.0
## Part 3: Core Components Architecture

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

### 3.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART3 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 3 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (4–N) MUST conform to Part 3. Part 3 MUST NOT contradict Part 0, Part 1, or Part 2. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles), PART1 (kernel architecture), PART2 (event system), PART4 (service framework), PART5 (engineering services), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis) |

**Conformance Requirement:** Every subsequent Part (4–N) of this specification MUST explicitly reference Part 3 sections for Core Component terminology, interfaces, and conformance criteria. Any Part that contradicts Part 3 is non-conformant and MUST be revised.

---

### 3.1 Purpose

#### 3.1.1 Why Core Components Exist

The four Core Components exist to provide the **immutable infrastructure foundation** upon which all AI-OS capabilities are built. They are not services, not managers, and not application logic — they are the kernel primitives that enable the Event-First architecture (Part 0 Principle 1), Kernel-as-Pure-Orchestrator (Part 0 Principle 2), and all cross-cutting capabilities (Part 0 Principle 3).

Without Core Components:
- No communication substrate exists (EventBus)
- No service discovery or dependency topology exists (ServiceRegistry)
- No immutable configuration authority exists (ConfigurationManager)
- No structured, correlated observability substrate exists (StructuredLogger)

#### 3.1.2 Architectural Role

```
┌─────────────────────────────────────────────────────────────────┐
│                      Hermes Kernel                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   C1:       │  │   C2:       │  │   C3:                   │  │
│  │ EventBus    │  │ Service     │  │ ConfigurationManager    │  │
│  │             │  │ Registry    │  │                         │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                     │                │
│         └────────────────┼─────────────────────┘                │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │   C4: StructuredLogger                                  │   │
│  │   (Permeates all components via singleton accessor)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Core Managers (9) access Core Components via kernel            │
│  Services access Core Components via kernel accessors           │
└─────────────────────────────────────────────────────────────────┘
```

**Core Component Positioning:**
- **C1 EventBus** — Initializes Phase 0 (first). Foundation for all communication.
- **C2 ServiceRegistry** — Initializes Phase 1. Depends on EventBus.
- **C3 ConfigurationManager** — Initializes Phase 2. Depends on EventBus.
- **C4 StructuredLogger** — Initializes Phase 3 (last Core Component). Depends on EventBus, ServiceRegistry, ConfigurationManager.

#### 3.1.3 Design Principles

| Principle ID | Principle | Traceability |
|--------------|-----------|--------------|
| CC-DP-001 | **Exclusive Kernel Ownership** — Core Components are constructed, initialized, and destroyed ONLY by HermesKernel | Part 1 §1.6.1, INV-OWN-001 |
| CC-DP-002 | **Fixed Count** — Exactly four Core Components; no more, no less, without ARB approval | Part 1 §1.7, INV-STR-002 |
| CC-DP-003 | **Sequential Initialization** — Phases 0→1→2→3 strict order; each depends only on prior phases | Part 1 §1.7.3, INV-CC-001 |
| CC-DP-004 | **EventBus-First Communication** — Post-initialization, Core Components communicate ONLY via EventBus | Part 1 §1.7.4, CC-IR-001 |
| CC-DP-005 | **Immutable Interfaces** — Public responsibilities and contracts are architecture-defined; implementation may vary | Part 0 §0.2.1 |
| CC-DP-006 | **Conformance-Verifiable** — Every responsibility has a static or runtime conformance check | Part 0 §0.5.1 |

#### 3.1.4 Non-Goals

| Non-Goal | Rationale |
|----------|-----------|
| **Business Logic** | Core Components contain zero domain logic (planning, coding, review, etc.) |
| **Persistence** | State persistence is delegated to Core Managers (StorageManager, StateManager) |
| **Service Implementation** | Services are registered, not implemented, by Core Components |
| **Network I/O** | Transport bindings are adapter concerns, not Core Component responsibilities |

---

### 3.2 Core Component Overview

#### 3.2.1 The Four Core Components

| Symbol | Name | Kernel Accessor | Initialization Phase | Primary Responsibility |
|--------|------|-----------------|---------------------|------------------------|
| **C1** | **EventBus** | `kernel.eventBus` | Phase 0 | Sole communication substrate; event publication, subscription, routing, correlation, ordering |
| **C2** | **ServiceRegistry** | `kernel.serviceRegistry` | Phase 1 | Service registration, discovery, dependency topology, health tracking, lifecycle coordination |
| **C3** | **ConfigurationManager** | `kernel.configuration` | Phase 2 | Immutable configuration authority; four-layer merge, schema validation, freeze enforcement |
| **C4** | **StructuredLogger** | `kernel.logger` | Phase 3 | Structured logging substrate; correlation support, audit logging, sink management |

#### 3.2.2 Ownership

| Component | Owner | Construction | Initialization | Destruction | Access Control |
|-----------|-------|--------------|----------------|-------------|----------------|
| EventBus | HermesKernel (exclusive) | Kernel constructor | Phase 0 `initialize()` | Phase S0 `shutdown()` | Read-only accessor `kernel.eventBus` |
| ServiceRegistry | HermesKernel (exclusive) | Kernel constructor | Phase 1 `initialize()` | Phase S1 `shutdown()` | Read-only accessor `kernel.serviceRegistry` |
| ConfigurationManager | HermesKernel (exclusive) | Kernel constructor | Phase 2 `initialize()` | Phase S2 `shutdown()` | Read-only accessor `kernel.configuration` |
| StructuredLogger | HermesKernel (exclusive) | Kernel constructor | Phase 3 `initialize()` | Phase S3 `shutdown()` | Read-only accessor `kernel.logger` |

**Ownership Invariants:**
- **INV-CC-OWN-001** — No entity outside HermesKernel may instantiate a Core Component.
- **INV-CC-OWN-002** — Core Components MUST NOT hold references to each other post-initialization.
- **INV-CC-OWN-003** — Core Components MUST be destroyed during SHUTTING_DOWN phase in reverse initialization order.
- **INV-CC-OWN-004** — Core Component accessors MUST return the same instance for the kernel lifetime (singleton semantics).

#### 3.2.3 Responsibilities Summary

| Component | Public Responsibilities (Architecture-Defined) |
|-----------|------------------------------------------------|
| **EventBus** | Event publication, subscription management, dispatch, ordering, delivery guarantees, dead letter handling, replay, observability emission |
| **ServiceRegistry** | Service registration, discovery, dependency resolution, topological initialization/shutdown plans, health tracking, capability advertisement |
| **ConfigurationManager** | Configuration loading (4-layer merge), schema validation, freeze enforcement, runtime read-only access, environment/secret overlay |
| **StructuredLogger** | Structured log emission, correlation enrichment, level filtering, audit logging, sink routing, buffering, rotation |

#### 3.2.4 Interactions

| Interaction | Mechanism | Constraint |
|-------------|-----------|------------|
| **C1 ↔ C2** | EventBus publishes `ServiceRegistered`, `ServiceHealthChanged`; ServiceRegistry subscribes during init | Post-init: EventBus only |
| **C1 ↔ C3** | EventBus publishes `ConfigurationFrozen`, `ConfigurationChanged` (dev); ConfigurationManager subscribes | Post-init: EventBus only |
| **C1 ↔ C4** | EventBus uses StructuredLogger for internal diagnostics; StructuredLogger may emit logs as events | StructuredLogger is infrastructure; EventBus is substrate |
| **C2 ↔ C3** | ServiceRegistry reads configuration for service discovery paths; ConfigurationManager is frozen first | Unidirectional: C2 reads C3 |
| **C2 ↔ C4** | ServiceRegistry logs registration/health events via StructuredLogger | Unidirectional: C2 uses C4 |
| **C3 ↔ C4** | ConfigurationManager loads logging configuration; StructuredLogger applies it | Unidirectional: C4 reads C3 |

---

### 3.3 Component C1 — EventBus

**Reference:** Part 2 (Event System Architecture) is the authoritative specification for EventBus behavior, contracts, and conformance. This section specifies only ownership, lifecycle, dependencies, interaction contracts, public responsibilities, and conformance as they pertain to Core Component architecture.

#### 3.3.1 Ownership

- **Owner:** HermesKernel (exclusive, Part 1 §1.6.1)
- **Accessor:** `kernel.eventBus` (read-only, Part 1 §1.13.1)
- **Construction:** During `HermesKernel` instantiation, before `initialize()`
- **Destruction:** Phase S0 (last Core Component, Part 1 §1.11.2)

#### 3.3.2 Lifecycle

| State | Transition Trigger | Entry Action |
|-------|-------------------|--------------|
| UNINITIALIZED | Kernel construction | Component instantiated, no queues, no registry |
| INITIALIZING | `initialize(kernel)` called | Register core component subscriptions; prepare queues |
| RUNNING | Phase 0 complete, invariants verified | Accept publishes; dispatch loop active |
| DRAINING | `shutdown()` called | Reject new publishes (`REJECTED_SHUTDOWN`); process in-flight |
| SHUTDOWN | All queues empty, subscriptions cleared | Publish `CoreComponentShutdown{name:"EventBus"}` |

**Lifecycle Invariants:**
- **INV-EB-LC-001** — EventBus MUST be the first Core Component to reach RUNNING.
- **INV-EB-LC-002** — EventBus MUST be the last Core Component to reach SHUTDOWN.
- **INV-EB-LC-003** — No other Core Component, Core Manager, or Service may publish or subscribe before EventBus enters RUNNING.

#### 3.3.3 Dependencies

| Dependency | Type | Phase | Purpose |
|------------|------|-------|---------|
| **None** | — | 0 | EventBus has no Core Component dependencies (foundation) |
| **StructuredLogger** | Initialization injection | 0 | Logger instance passed to `initialize()` for internal diagnostics |
| **ConfigurationManager** | Post-freeze read | 2+ | Queue capacities, timeouts, retry defaults (read-only after freeze) |

> **Note:** Per Part 1 §1.7.4 CC-IR-002, initialization-time dependency injection via `initialize(kernel)` parameters is PERMITTED. Post-initialization, EventBus communicates ONLY via EventBus (CC-IR-001).

#### 3.3.4 Interaction Contracts

| Contract | Counterparty | Mechanism | Description |
|----------|--------------|-----------|-------------|
| **CoreComponentInitialized** | All | EventBus publishes | Emitted when EventBus reaches RUNNING |
| **CoreComponentShutdown** | All | EventBus publishes | Emitted when EventBus enters SHUTDOWN |
| **ServiceRegistered** | ServiceRegistry | EventBus receives | Registry publishes; EventBus routes to subscribers |
| **ServiceHealthChanged** | ServiceRegistry | EventBus receives | Registry publishes; EventBus routes to subscribers |
| **ConfigurationFrozen** | ConfigurationManager | EventBus receives | Config publishes; EventBus routes to subscribers |
| **LogEvent** | StructuredLogger | EventBus may emit | Internal EventBus diagnostics as structured log events |

**Invariant:** **INV-EB-IC-001** — EventBus MUST NOT directly invoke methods on any Core Component, Core Manager, or Service post-initialization. All communication via EventBus.

#### 3.3.5 Public Responsibilities

The following responsibilities are architecture-mandated for EventBus as Core Component C1. Detailed behavior is specified in Part 2.

| Responsibility ID | Responsibility | Conformance Reference |
|-------------------|----------------|----------------------|
| EB-PR-001 | **Event Publication** — Accept, validate, enqueue events from any component | Part 2 §2.4.7, §2.8 |
| EB-PR-002 | **Subscription Management** — Register, deregister, filter, prioritize subscribers | Part 2 §2.5 |
| EB-PR-003 | **Dispatch & Ordering** — Route events to subscribers per priority, correlation, FIFO | Part 2 §2.4.6, §2.7 |
| EB-PR-004 | **Delivery Guarantees** — Implement at-most-once, at-least-once (default), exactly-once (opt-in) | Part 2 §2.8 |
| EB-PR-005 | **Failure Handling** — Retry, dead letter, recursive detection, loop detection | Part 2 §2.9 |
| EB-PR-006 | **Replay** — Historical event replay with determinism safeguards | Part 2 §2.11 |
| EB-PR-007 | **Observability** — Structured logging, tracing, metrics, audit events, diagnostics | Part 2 §2.12 |
| EB-PR-008 | **Resource Bounding** — Enforce queue capacities, subscription limits, history limits | Part 2 §2.4.4, §2.8.9 |

#### 3.3.6 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-EB-001 | Exactly one EventBus instance per process | Static: singleton enforcement; Runtime: accessor identity |
| CONF-EB-002 | Initializes in Phase 0, before all other Core Components | Static: phase metadata; Runtime: initialization sequence |
| CONF-EB-003 | Implements `ICoreComponent` interface (name, phase, dependencies, initialize, shutdown, healthCheck) | Static: interface verification |
| CONF-EB-004 | Publishes `CoreComponentInitialized` on RUNNING transition | Runtime: event emission test |
| CONF-EB-005 | Publishes `CoreComponentShutdown` on DRAINING transition | Runtime: event emission test |
| CONF-EB-006 | All Part 2 conformance requirements (L1–L4) satisfied | Part 2 §2.16 |

---

### 3.4 Component C2 — ServiceRegistry

#### 3.4.1 Purpose

The ServiceRegistry is the **authoritative directory** of all Services in the AI-OS process. It provides registration, discovery, dependency topology computation, health tracking, and lifecycle coordination for Services. It is the single source of truth for "what services exist" and "how they depend on each other."

#### 3.4.2 Responsibilities

| Responsibility ID | Responsibility | Description |
|-------------------|----------------|-------------|
| SR-R-001 | **Service Registration** — Accept `BaseService` registrations; validate uniqueness, dependencies, capabilities |
| SR-R-002 | **Service Discovery** — Provide lookup by service ID, type, capability, tag; support wildcard queries |
| SR-R-003 | **Dependency Topology** — Build and maintain DAG of service dependencies; detect cycles |
| SR-R-004 | **Initialization Planning** — Compute topological initialization batches (parallelizable groups) |
| SR-R-005 | **Shutdown Planning** — Compute reverse topological shutdown batches |
| SR-R-006 | **Health Tracking** — Poll `healthCheck()` on registered services; maintain health state |
| SR-R-007 | **Capability Advertisement** — Expose service-declared capabilities for cross-service discovery |
| SR-R-008 | **Lifecycle Event Emission** — Publish `ServiceRegistered`, `ServiceHealthChanged`, `ServiceInitialized`, `ServiceShutdown` events |

#### 3.4.3 Ownership

- **Owner:** HermesKernel (exclusive, Part 1 §1.6.1)
- **Accessor:** `kernel.serviceRegistry` (read-only, Part 1 §1.13.1)
- **Construction:** During `HermesKernel` instantiation
- **Initialization:** Phase 1 (depends on EventBus)
- **Destruction:** Phase S1 (second-to-last Core Component)

**Ownership Invariants:**
- **INV-SR-OWN-001** — Only HermesKernel constructs ServiceRegistry.
- **INV-SR-OWN-002** — Services register themselves via `kernel.serviceRegistry.register()`; they do not instantiate the registry.
- **INV-SR-OWN-003** — ServiceRegistry does not own Service lifecycles; it coordinates via LifecycleManager.

#### 3.4.4 Service Registration

**Registration Contract:**

```
ServiceRegistration {
  service: BaseService;              // The service instance
  serviceId: string;                 // Unique identifier (e.g., "PlanningService")
  serviceType: ServiceType;          // ENGINEERING | CAPABILITY_FACADE | APPLICATION
  dependsOn: string[];               // Service IDs this service depends on (must be acyclic)
  capabilities: Capability[];        // Declared capabilities for discovery
  critical: boolean;                 // If true, failure → kernel FATAL
  tags: string[];                    // Optional categorization tags
  metadata: Record<string, unknown>; // Extensible
}
```

**Registration Rules:**
| Rule ID | Rule |
|---------|------|
| SR-REG-001 | `serviceId` MUST be globally unique within the process. Duplicate registration throws. |
| SR-REG-002 | `dependsOn` MUST reference only registered or to-be-registered service IDs. |
| SR-REG-003 | `dependsOn` graph MUST be acyclic. Cycle detection throws at registration. |
| SR-REG-004 | `capabilities` MUST conform to declared capability schemas (Part 4). |
| SR-REG-005 | Registration MUST occur during Service construction or `on_register()`; not after kernel RUNNING. |
| SR-REG-006 | On successful registration, ServiceRegistry MUST publish `ServiceRegistered` event. |

#### 3.4.5 Discovery

**Discovery Operations:**

| Operation | Signature | Returns |
|-----------|-----------|---------|
| `getService(serviceId)` | Exact ID lookup | `BaseService` or `null` |
| `getServicesByType(type)` | Type filter | `BaseService[]` |
| `getServicesByCapability(capability)` | Capability filter | `BaseService[]` |
| `getServicesByTag(tag)` | Tag filter | `BaseService[]` |
| `getAllServices()` | No filter | `BaseService[]` |
| `query(criteria)` | Composite filter (type ∩ capability ∩ tag) | `BaseService[]` |

**Discovery Invariants:**
- **INV-SR-DISC-001** — Discovery MUST return only services in `REGISTERED` or `RUNNING` state.
- **INV-SR-DISC-002** — Discovery MUST be consistent with current registry state (no stale caches).
- **INV-SR-DISC-003** — Discovery MUST NOT expose services in `FAILED` or `SHUTDOWN` state.

#### 3.4.6 Lookup

**Lookup Contract:**
- **Service-to-Service Lookup** — PROHIBITED. Services MUST NOT look up other services directly. Communication is via EventBus only (Part 0 Principle 1).
- **Kernel/Manager Lookup** — PERMITTED. Core Managers and LifecycleManager use ServiceRegistry for topology computation.
- **External Lookup** — PROHIBITED. No external process may query ServiceRegistry directly.

#### 3.4.7 Capabilities

**Capability Model:**

```
Capability {
  name: string;                      // Unique capability identifier
  version: SemanticVersion;          // Capability contract version
  interface: CapabilityInterface;    // Structural description (methods, events)
  metadata: Record<string, unknown>;
}
```

**Capability Rules:**
| Rule ID | Rule |
|---------|------|
| SR-CAP-001 | Capabilities are declared at registration; immutable post-registration. |
| SR-CAP-002 | Capability names MUST be globally unique or versioned to avoid collision. |
| SR-CAP-003 | ServiceRegistry MUST expose capability index for discovery. |
| SR-CAP-004 | Core Managers declare capabilities; Services declare capabilities; Extensions declare capabilities. |

#### 3.4.8 Namespaces

**Namespace Model:**

| Namespace | Scope | Purpose |
|-----------|-------|---------|
| **kernel** | Core Components, Core Managers | Reserved; not in ServiceRegistry |
| **engineering** | 8 Engineering Services | Part 5 |
| **facade** | 4 Capability Facade Services | Part 6 |
| **application** | Domain-specific Application Services | Extensible |
| **extension** | Custom services, skills, agents | Part 0 §0.5.2 |

**Namespace Rules:**
- **INV-SR-NS-001** — Service IDs MUST be prefixed with namespace (e.g., `engineering.PlanningService`).
- **INV-SR-NS-002** — `kernel` namespace is reserved; registration throws.
- **INV-SR-NS-003** — Namespace determines initialization phase ordering and criticality defaults.

#### 3.4.9 Lifecycle

**Service Lifecycle States (tracked by ServiceRegistry):**

```
UNREGISTERED → REGISTERED → INITIALIZING → RUNNING → DEGRADED → FAILED
                                      ↘                         ↘
                                       → SHUTTING_DOWN → SHUTDOWN
```

**Lifecycle Coordination:**
| Phase | ServiceRegistry Action |
|-------|------------------------|
| Initialization | Compute topological plan → LifecycleManager executes batches |
| Running | Poll `healthCheck()` every 30s (configurable) → update state → emit `ServiceHealthChanged` |
| Failure | On health check failure → mark DEGRADED/FAILED → emit event → LifecycleManager handles recovery |
| Shutdown | Compute reverse topological plan → LifecycleManager executes batches |

#### 3.4.10 Initialization

**Initialization Sequence:**
1. ServiceRegistry `initialize(kernel)` called in Phase 1
2. Registers internal subscriptions: `ServiceRegistered`, `ServiceHealthChanged`, `ConfigurationFrozen`
3. Validates all pre-registered services (if any) for dependency acyclicity
4. Publishes `CoreComponentInitialized{name:"ServiceRegistry"}`
5. Waits for `ConfigurationFrozen` before accepting Application Service registrations (if configured)

**Initialization Invariants:**
- **INV-SR-INIT-001** — ServiceRegistry MUST be operational before any Service initializes.
- **INV-SR-INIT-002** — Dependency topology MUST be validated before Phase 9 (Service initialization) begins.

#### 3.4.11 Shutdown

**Shutdown Sequence:**
1. ServiceRegistry `shutdown()` called in Phase S1
2. Deregisters all subscriptions
3. Publishes `CoreComponentShutdown{name:"ServiceRegistry"}`
4. Registry enters `SHUTDOWN` state; all lookups return empty

**Shutdown Invariants:**
- **INV-SR-SD-001** — ServiceRegistry MUST shut down AFTER all Services (Phase S9+).
- **INV-SR-SD-002** — ServiceRegistry MUST shut down BEFORE ConfigurationManager (Phase S2).

#### 3.4.12 Failure Handling

| Failure Scenario | Classification | Response |
|------------------|----------------|----------|
| Service registration duplicate | PERMANENT | Reject registration; throw |
| Dependency cycle detected | PERMANENT | Reject registration; throw |
| Service health check fails (1st) | TRANSIENT | Mark DEGRADED; emit `ServiceHealthChanged`; schedule re-check |
| Service health check fails (3 consecutive) | CRITICAL | Mark FAILED; emit `ServiceFailed`; LifecycleManager initiates recovery |
| Critical service fails | FATAL | Kernel emergency shutdown (Part 1 §1.12) |
| ServiceRegistry internal error | FATAL | Kernel emergency shutdown (Core Component failure = FATAL per Part 1 INV-FH-001) |

#### 3.4.13 Recovery

| Recovery Trigger | Procedure |
|------------------|-----------|
| Service DEGRADED → HEALTHY | Automatic on health check pass; emit `ServiceHealthChanged` |
| Service FAILED → RESTART | LifecycleManager calls `service.initialize()` (max 2 attempts); if success → RUNNING |
| ServiceRegistry corruption | FATAL — no recovery; kernel shutdown |

**Recovery Invariants:**
- **INV-SR-REC-001** — Service recovery MUST respect dependency topology (dependencies must be RUNNING first).
- **INV-SR-REC-002** — Recovery attempts MUST be tracked; max 2 per service per kernel run.

#### 3.4.14 Visibility Rules

| Visibility Level | Entities | Access |
|------------------|----------|--------|
| **Public API** | `getService`, `getServicesBy*`, `query`, `register`, `unregister` | Kernel, Core Managers, LifecycleManager, test fixtures |
| **Internal Events** | `ServiceRegistered`, `ServiceHealthChanged`, `ServiceInitialized`, `ServiceShutdown` | All subscribers via EventBus |
| **Hidden** | Dependency graph internals, health check scheduler, topology cache | ServiceRegistry only |

#### 3.4.15 Extension Rules

| Extension Point | Mechanism | Governance |
|-----------------|-----------|------------|
| **Custom Service Types** | Implement `BaseService`; register via `register()` | ARB review for Engineering/Capability Facade; open for Application |
| **Custom Capabilities** | Declare in `capabilities` array at registration | MUST conform to capability contract (Part 4) |
| **Custom Health Checks** | Override `healthCheck()` in Service | Part 4 |
| **Custom Tags** | Add to `tags` array at registration | Open; conventions encouraged |

**Extension Prohibitions:**
- **INV-SR-EXT-001** — MUST NOT modify ServiceRegistry topology computation algorithm.
- **INV-SR-EXT-002** — MUST NOT bypass ServiceRegistry for service discovery.
- **INV-SR-EXT-003** — MUST NOT register services in `kernel` namespace.

#### 3.4.16 Architectural Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-SR-STR-001 | Exactly one ServiceRegistry instance per process. |
| INV-SR-STR-002 | Service registry state is the single source of truth for service existence and dependencies. |
| INV-SR-STR-003 | Dependency graph is acyclic at all times. |
| INV-SR-STR-004 | Topological initialization plan respects all declared dependencies. |
| INV-SR-STR-005 | Topological shutdown plan is exact reverse of initialization plan. |
| INV-SR-STR-006 | ServiceRegistry never directly invokes Service methods (except `healthCheck()`). |
| INV-SR-STR-007 | ServiceRegistry communicates state changes exclusively via EventBus events. |

#### 3.4.17 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-SR-001 | Implements `ICoreComponent` interface | Static: interface verification |
| CONF-SR-002 | Initializes in Phase 1, after EventBus | Static: phase metadata; Runtime: sequence |
| CONF-SR-003 | Publishes `CoreComponentInitialized` on RUNNING | Runtime: event emission test |
| CONF-SR-004 | Publishes `CoreComponentShutdown` on SHUTDOWN | Runtime: event emission test |
| CONF-SR-005 | Rejects duplicate service IDs | Unit test |
| CONF-SR-006 | Rejects cyclic dependencies | Unit test |
| CONF-SR-007 | Computes correct topological initialization order | Integration test (various DAGs) |
| CONF-SR-008 | Computes correct reverse topological shutdown order | Integration test |
| CONF-SR-009 | Health check polling respects interval config | Integration test |
| CONF-SR-010 | All events emitted with correlationId, causationId | Contract test |

---

### 3.5 Component C3 — ConfigurationManager

#### 3.5.1 Configuration Hierarchy

The ConfigurationManager implements a **four-layer configuration merge** with strict precedence ordering. This hierarchy is MANDATORY and IMMUTABLE.

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION LAYERS                         │
│  (Highest precedence at top — wins on conflict)                 │
├─────────────────────────────────────────────────────────────────┤
│  Layer 4: Environment Variables (AIOS_*)                        │
│    └─ Highest precedence; runtime overrides; secrets injection  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 3: Environment-Specific File (env.yaml)                  │
│    └─ Per-deployment overrides (staging.yaml, production.yaml)  │
├─────────────────────────────────────────────────────────────────┤
│  Layer 2: Application Configuration (app.yaml)                  │
│    └─ Committed configuration; version-controlled               │
├─────────────────────────────────────────────────────────────────┤
│  Layer 1: Built-in Defaults (KernelConfigDefaults)              │
│    └─ Hardcoded fallback defaults; lowest precedence            │
└─────────────────────────────────────────────────────────────────┘
```

**Precedence Rule:** For any configuration key, the value from the highest-numbered layer that defines it is used. Layers are merged deeply (recursive object merge), not replaced.

#### 3.5.2 Configuration Sources

| Layer | Source | Format | Loading | Mutability |
|-------|--------|--------|---------|------------|
| **1: Defaults** | `KernelConfigDefaults` (embedded) | Structured object | Compile-time | Immutable |
| **2: App Config** | `config/app.yaml` (configurable path) | YAML | Phase 2 init | Immutable post-freeze |
| **3: Env Config** | `config/env/{environment}.yaml` | YAML | Phase 2 init | Immutable post-freeze |
| **4: Env Vars** | `AIOS_<SECTION>_<KEY>` | String (parsed) | Phase 2 init | Immutable post-freeze |

**Source Invariants:**
- **INV-CM-SRC-001** — All four layers MUST be loaded during Phase 2 initialization.
- **INV-CM-SRC-002** — Missing Layer 2 or 3 files are non-fatal (treated as empty); missing Layer 1 is fatal.
- **INV-CM-SRC-003** — Environment variable parsing MUST follow `AIOS_<SECTION>_<KEY>` convention (Part 0 §0.3.3).
- **INV-CM-SRC-004** — ConfigurationManager MUST NOT read from any source not listed above.

#### 3.5.3 Layer Precedence

**Merge Algorithm:**
1. Start with Layer 1 (Defaults) as base
2. Deep-merge Layer 2 (App Config) — Layer 2 values override Layer 1
3. Deep-merge Layer 3 (Env Config) — Layer 3 values override Layer 1+2
4. Deep-merge Layer 4 (Env Vars) — Layer 4 values override Layer 1+2+3

**Deep Merge Semantics:**
- Objects: Recursive merge; keys present in both → higher layer wins
- Arrays: **Replace** (not merge) — higher layer array completely replaces lower layer array
- Primitives: Higher layer value replaces lower layer value
- `null` in higher layer: Removes key (allows "unset" from env vars)

**Precedence Invariants:**
- **INV-CM-PREC-001** — Layer 4 (Env Vars) ALWAYS wins over Layers 1–3.
- **INV-CM-PREC-002** — Array replacement semantics are mandatory; no array concatenation.
- **INV-CM-PREC-003** — Merge MUST be deterministic: same inputs → same output.

#### 3.5.4 Validation

**Validation Stages:**

| Stage | Timing | Scope | Failure Behavior |
|-------|--------|-------|------------------|
| **Schema Validation** | Phase 2 (init) | Full merged config vs. `KernelConfigSchema` | Abort initialization; kernel startup fails |
| **Cross-Reference Validation** | Phase 2 (init) | Paths exist, ports available, refs resolvable | Abort initialization |
| **Semantic Validation** | Phase 2 (init) | Values in valid ranges, enums valid, dependencies consistent | Abort initialization |
| **Runtime Validation** | On access (dev mode) | Accessed config subset | Log warning; return value |

**Schema Contract:**
- `KernelConfigSchema` is a **canonical schema** (JSON Schema Draft 2020-12 or equivalent)
- Schema defines: required fields, types, enums, ranges, formats, cross-field constraints
- Schema is versioned; `KernelConfigSchemaVersion` in metadata

**Validation Invariants:**
- **INV-CM-VAL-001** — ConfigurationManager MUST validate against schema before freeze.
- **INV-CM-VAL-002** — Validation errors MUST include full path to failing key and constraint violated.
- **INV-CM-VAL-003** — Invalid configuration MUST prevent kernel from reaching RUNNING state.

#### 3.5.5 Schema

**Schema Architecture:**

```
KernelConfigSchema {
  version: SemanticVersion;
  required: string[];                    // Required top-level keys
  properties: Record<string, PropertySchema>;
  dependencies: Record<string, string[]>; // Cross-field dependencies
  additionalProperties: boolean;         // false (strict)
}

PropertySchema {
  type: string | string[];               // string, number, boolean, object, array
  enum?: unknown[];                      // Allowed values
  minimum?: number;                      // Numeric bounds
  maximum?: number;
  pattern?: string;                      // Regex for strings
  format?: string;                       // Format hint (uri, email, uuid, etc.)
  default?: unknown;                     // Default value (for documentation)
  deprecated?: boolean;                  // Field deprecated
  description?: string;                  // Human-readable
  // Nested for objects
  properties?: Record<string, PropertySchema>;
  required?: string[];
  additionalProperties?: boolean | PropertySchema;
  // Array items
  items?: PropertySchema;
}
```

**Schema Invariants:**
- **INV-CM-SCH-001** — Schema MUST be loaded/embedded before Phase 2 begins.
- **INV-CM-SCH-002** — Schema version MUST be recorded in merged configuration metadata.
- **INV-CM-SCH-003** — Schema evolution follows Part 2 §2.10 rules (MAJOR/MINOR/PATCH).

#### 3.5.6 Freeze Behavior

**Freeze Contract:**
- **Trigger:** After Phase 3 (LifecycleManager initialization) completes, before Phase 4 (Core Managers)
- **Action:** `ConfigurationManager.freeze()` called by LifecycleManager
- **Effect:** Configuration becomes **immutable**; all write operations throw `ConfigurationFrozenError`
- **Event:** `ConfigurationFrozen` published on EventBus

**Freeze Invariants:**
- **INV-CM-FRZ-001** — ConfigurationManager MUST be frozen BEFORE any Core Manager initializes (Phase 4+).
- **INV-CM-FRZ-002** — ConfigurationManager MUST be frozen BEFORE any Service initializes (Phase 9+).
- **INV-CM-FRZ-003** — Post-freeze, any mutation attempt (set, merge, delete) MUST throw.
- **INV-CM-FRZ-004** — Freeze is irreversible for the kernel lifetime; no unfreeze operation exists.
- **INV-CM-FRZ-005** — `ConfigurationFrozen` event MUST carry configuration hash for audit.

#### 3.5.7 Runtime Access

**Access Contract:**
- **Read-Only:** All accessors return deep-frozen (or effectively immutable) configuration views
- **Typed Access:** `get<T>(path: string): T` with schema-aware type inference
- **Section Access:** `getSection(section: string): ConfigSection`
- **Full Access:** `getAll(): Readonly<KernelConfig>`

**Access Invariants:**
- **INV-CM-ACC-001** — All access methods MUST return immutable views (defensive copy or frozen object).
- **INV-CM-ACC-002** — Access before freeze (dev/hot-reload) MAY return mutable view; post-freeze MUST NOT.
- **INV-CM-ACC-003** — Configuration must be accessible via `kernel.configuration` accessor in RUNNING state.

#### 3.5.8 Environment Variables

**Mapping Rules:**
| Env Var Pattern | Config Path | Parsing |
|-----------------|-------------|---------|
| `AIOS_KERNEL_LOG_LEVEL` | `kernel.logLevel` | String enum |
| `AIOS_KERNEL_HEALTH_CHECK_INTERVAL_MS` | `kernel.healthCheckIntervalMs` | Integer |
| `AIOS_SECURITY_JWT_SECRET` | `security.jwtSecret` | String (secret) |
| `AIOS_LLM_PROVIDER_OPENAI_API_KEY` | `llm.providers.openai.apiKey` | String (secret) |

**Parsing Rules:**
- Prefix `AIOS_` stripped
- Double underscore `__` → nested object delimiter
- Single underscore `_` → preserved in key name
- Values parsed as: boolean (`true`/`false`), number (numeric), null (`null`), string (default)
- **Secrets** are NOT logged; masked in diagnostics (`***`)

**Env Var Invariants:**
- **INV-CM-ENV-001** — All environment variables with `AIOS_` prefix MUST be processed.
- **INV-CM-ENV-002** — Unknown `AIOS_` variables (not in schema) are logged as warnings; not errors.
- **INV-CM-ENV-003** — Environment variables MUST override all file-based layers.

#### 3.5.9 Secrets

**Secret Handling:**
- **Detection:** Keys matching patterns: `*_SECRET`, `*_KEY`, `*_TOKEN`, `*_PASSWORD`, `*_CREDENTIAL`
- **Storage:** Secrets are stored in-memory only; never written to disk by ConfigurationManager
- **Access:** `getSecret(path)` returns value; `get(path)` returns `***` for secret keys
- **Audit:** Secret access logged at AUDIT level with key path (not value)
- **Environment:** Secrets MUST come from Layer 4 (env vars) in production; Layer 2/3 for dev only

**Secret Invariants:**
- **INV-CM-SEC-001** — Secrets MUST NOT appear in `getAll()`, diagnostics, or logs.
- **INV-CM-SEC-002** — Secrets MUST NOT be persisted by ConfigurationManager.
- **INV-CM-SEC-003** — Secret values MUST be masked in all structured log output.

#### 3.5.10 Overrides

**Override Mechanism:**
- **Dev/Hot-Reload:** `ConfigurationManager.applyOverride(overrides)` — ONLY available before freeze
- **Test Override:** `ConfigurationManager.setTestOverride(path, value)` — Test-only API
- **Production:** Overrides PROHIBITED; use env vars (Layer 4) or config files (Layer 2/3)

**Override Invariants:**
- **INV-CM-OVR-001** — Overrides MUST NOT be permitted after `ConfigurationFrozen`.
- **INV-CM-OVR-002** — Test overrides MUST be guarded by `NODE_ENV === 'test'`.
- **INV-CM-OVR-003** — Overrides follow same merge precedence as Layer 4 (highest).

#### 3.5.11 Lifecycle

| Phase | State | Action |
|-------|-------|--------|
| **0–1** | UNINITIALIZED | Component constructed; no config loaded |
| **2** | INITIALIZING | Load all 4 layers → merge → validate → prepare for freeze |
| **2→3** | FREEZING | `freeze()` called → deep-freeze config → publish `ConfigurationFrozen` |
| **3–8** | FROZEN | Read-only access; all mutations throw |
| **S2** | SHUTTING_DOWN | Archive config hash; publish `CoreComponentShutdown` |

**Lifecycle Invariants:**
- **INV-CM-LC-001** — ConfigurationManager MUST reach FROZEN state before Phase 4 begins.
- **INV-CM-LC-002** — ConfigurationManager MUST remain FROZEN throughout RUNNING and SHUTTING_DOWN.
- **INV-CM-LC-003** — Configuration hash MUST be included in `KernelReady` and `KernelTerminated` events.

#### 3.5.12 Failure Handling

| Failure Point | Classification | Response |
|---------------|----------------|----------|
| Layer 1 (defaults) missing | FATAL | Abort initialization; kernel cannot start |
| Schema validation fails | FATAL | Abort initialization; emit `KernelInitializationFailed` |
| Cross-reference validation fails | FATAL | Abort initialization; emit `KernelInitializationFailed` |
| Layer 2/3 file parse error | FATAL | Abort initialization; emit `KernelInitializationFailed` |
| Env var parsing error | FATAL | Abort initialization; emit `KernelInitializationFailed` |
| Freeze called twice | CRITICAL | Second call throws `ConfigurationFrozenError` |
| Mutation after freeze | PERMANENT | Throw `ConfigurationFrozenError` |

**Failure Invariants:**
- **INV-CM-FH-001** — Any configuration failure during Phase 2 is FATAL (kernel cannot start).
- **INV-CM-FH-002** — Post-freeze mutation attempts are programming errors; throw immediately.

#### 3.5.13 Recovery

| Scenario | Recovery |
|----------|----------|
| Configuration error at startup | Fix config file/env var; restart kernel (no in-process recovery) |
| Hot-reload (dev only) | `ConfigurationManager.reload()` before freeze; re-merge, re-validate |
| Schema migration | New schema version; migrate config files; restart kernel |

**Recovery Invariants:**
- **INV-CM-REC-001** — No in-process recovery from configuration errors in production (frozen = immutable).
- **INV-CM-REC-002** — Dev-mode reload MUST re-validate and re-freeze atomically.

#### 3.5.14 Extension Rules

| Extension Point | Mechanism | Governance |
|-----------------|-----------|------------|
| **Custom Config Sections** | Extend `KernelConfigSchema` via schema composition | ARB review; MUST NOT conflict with kernel sections |
| **Custom Config Sources** | Implement `ConfigSource` interface; register in KernelConfig | Part 0 §0.5.2; MUST follow layer precedence |
| **Custom Validators** | Register validation functions for custom sections | ARB review; MUST be pure and fast |

**Extension Prohibitions:**
- **INV-CM-EXT-001** — MUST NOT modify the four-layer merge algorithm.
- **INV-CM-EXT-002** — MUST NOT add layers beyond the four defined.
- **INV-CM-EXT-003** — MUST NOT change layer precedence order.
- **INV-CM-EXT-004** — MUST NOT make configuration mutable post-freeze.

#### 3.5.15 Architectural Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-CM-STR-001 | Exactly one ConfigurationManager instance per process. |
| INV-CM-STR-002 | Configuration is immutable after freeze. |
| INV-CM-STR-003 | Four-layer merge precedence is fixed and non-negotiable. |
| INV-CM-STR-004 | Schema validation is mandatory before freeze. |
| INV-CM-STR-005 | Secrets are never logged, persisted, or exposed via non-secret accessors. |
| INV-CM-STR-006 | Configuration hash is deterministic for identical inputs. |
| INV-CM-STR-007 | All configuration access in RUNNING state goes through ConfigurationManager. |

#### 3.5.16 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-CM-001 | Implements `ICoreComponent` interface | Static: interface verification |
| CONF-CM-002 | Initializes in Phase 2, after EventBus | Static: phase metadata; Runtime: sequence |
| CONF-CM-003 | Publishes `CoreComponentInitialized` on RUNNING | Runtime: event emission test |
| CONF-CM-004 | Publishes `CoreComponentShutdown` on SHUTDOWN | Runtime: event emission test |
| CONF-CM-005 | Loads and merges all four layers correctly | Unit test (various layer combinations) |
| CONF-CM-006 | Validates against schema before freeze | Unit test (valid/invalid configs) |
| CONF-CM-007 | Freezes before Phase 4 (Core Managers) | Integration test: phase ordering |
| CONF-CM-008 | Freezes before Phase 9 (Services) | Integration test: phase ordering |
| CONF-CM-009 | Post-freeze mutations throw | Unit test |
| CONF-CM-010 | Secrets masked in logs/diagnostics | Contract test |
| CONF-CM-011 | Env vars override file layers | Unit test |
| CONF-CM-012 | Deterministic merge output | Property test |

---

### 3.6 Component C4 — StructuredLogger

#### 3.6.1 Purpose

The StructuredLogger is the **single logging abstraction** for all AI-OS components. It provides structured (JSON) log emission with mandatory correlation enrichment, level filtering, audit logging, performance-optimized buffering, configurable sinks, and rotation. It is the observability substrate required by Part 0 Principle 12.

#### 3.6.2 Logging Architecture

**Architecture Model:**

```
┌─────────────────────────────────────────────────────────────────┐
│                      StructuredLogger                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Frontend   │  │  Pipeline   │  │  Sinks (pluggable)      │  │
│  │  (log,      │→ │  (enrich,   │→ │  • ConsoleSink          │  │
│  │   audit,    │  │   filter,   │  │  • FileSink             │  │
│  │   levels)   │  │   buffer,   │  │  • EventBusSink         │  │
│  └─────────────┘  │   rotate)   │  │  • CustomSink           │  │
│                   └─────────────┘  └─────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Correlation Context (correlationId, causationId,       │   │
│  │  componentIdentity, spanContext) — Thread/Task Local    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

**Key Properties:**
- **Single Instance:** One `StructuredLogger` per process (Core Component C4)
- **Global Accessor:** `kernel.logger` (read-only)
- **Thread/Task Safe:** Concurrent logging from any context
- **Context-Aware:** Automatic correlation enrichment from execution context

#### 3.6.3 Structured Log Format

**Canonical Log Entry:**

```
LogEntry {
  // Identity
  timestamp: ISO8601Instant           // UTC, nanosecond precision
  timestampMonotonic: MonotonicNs     // Process-local ordering
  logId: UUID                         // UUIDv7 (unique per entry)

  // Level & Category
  level: LogLevel                     // TRACE, DEBUG, INFO, WARN, ERROR, CRITICAL, AUDIT
  category: LogCategory               // SYSTEM, CONTROL, DATA, AUDIT, DIAGNOSTIC, SECURITY

  // Correlation (MANDATORY)
  correlationId: UUID | null          // From context; null if no active correlation
  causationId: UUID | null            // From context; null if no active causation

  // Source
  source: ComponentIdentity           // Emitting component (kernel, manager, service, extension)
  loggerName: string                  // Logical logger name (e.g., "aios.kernel.eventbus")

  // Message
  message: string                     // Human-readable message
  messageTemplate: string | null      // Template if structured (e.g., "Task {taskId} started")

  // Structured Fields
  fields: Record<string, unknown>     // Key-value pairs (JSON-serializable)
  error: SerializedError | null       // If logging an error/exception

  // Integrity
  checksum: SHA256Hex                 // Hash of canonical JSON for tamper detection
}
```

**Format Invariants:**
- **INV-SL-FMT-001** — Every log entry MUST contain `correlationId` and `causationId` (may be null).
- **INV-SL-FMT-002** — Every log entry MUST contain `source` identifying the emitting component.
- **INV-SL-FMT-003** — Log entries MUST be JSON-serializable; circular references prohibited.
- **INV-SL-FMT-004** — `checksum` MUST be SHA-256 of canonical JSON (RFC 8785).

#### 3.6.4 Correlation Support

**Correlation Context:**
- Maintained in **thread/task-local storage** (or async context equivalent)
- Set by: EventBus dispatch (on event handler entry), WorkflowManager (on step entry), Service initialization
- Propagated automatically to all log calls within the same execution context

**Correlation Operations:**
| Operation | Purpose |
|-----------|---------|
| `withCorrelation(correlationId, causationId, fn)` | Execute `fn` with correlation context |
| `getCorrelationContext()` | Read current context (for manual enrichment) |
| `clearCorrelation()` | Clear context (cleanup) |

**Correlation Invariants:**
- **INV-SL-CORR-001** — All log entries emitted during event handler execution MUST carry that event's `correlationId` and `causationId`.
- **INV-SL-CORR-002** — Correlation context MUST be cleared on handler exit (success or failure).
- **INV-SL-CORR-003** — StructuredLogger MUST NOT require manual correlationId passing on every log call.

#### 3.6.5 Log Levels

| Level | Value | Purpose | Default Sink Routing |
|-------|-------|---------|---------------------|
| **TRACE** | 0 | Verbose diagnostic detail | Buffered; file only |
| **DEBUG** | 1 | Debugging information | Buffered; file + console (dev) |
| **INFO** | 2 | General operational information | Console + file |
| **WARN** | 3 | Warning conditions (recoverable) | Console + file + EventBusSink |
| **ERROR** | 4 | Error conditions (non-fatal) | Console + file + EventBusSink |
| **CRITICAL** | 5 | Critical conditions (immediate action) | All sinks; synchronous flush |
| **AUDIT** | 6 | Audit/governance events (tamper-evident) | Audit sink (append-only) + EventBusSink |

**Level Invariants:**
- **INV-SL-LVL-001** — Log level filtering MUST be applied at the Frontend (before pipeline).
- **INV-SL-LVL-002** — AUDIT level is **distinct** from CRITICAL; audit events are never dropped.
- **INV-SL-LVL-003** — Default minimum level: INFO (production), DEBUG (development).

#### 3.6.6 Audit Logging

**Audit Log Contract:**
- **Separate Stream:** Audit logs go to dedicated `AuditSink` (append-only, tamper-evident)
- **Mandatory Events:** All AUDIT-category events from Part 2 §2.12.6 MUST be logged via `logger.audit()`
- **Immutability:** Audit log entries are never rotated, compressed, or deleted by StructuredLogger
- **Integrity:** Each audit entry includes `checksum` and links to previous entry (hash chain)

**Audit Invariants:**
- **INV-SL-AUD-001** — Audit logging MUST NOT be disabled or filtered by log level.
- **INV-SL-AUD-002** — Audit sink MUST be separate from operational log sinks.
- **INV-SL-AUD-003** — Audit entries MUST include `correlationId`, `causationId`, `source`, and `checksum`.

#### 3.6.7 Performance

**Performance Requirements:**
| Metric | Target | Enforcement |
|--------|--------|-------------|
| **Log Call Latency (no I/O)** | < 10µs (typical) | Benchmark test |
| **Log Call Latency (buffered)** | < 50µs (p99) | Benchmark test |
| **Memory Overhead (idle)** | < 10MB | Profile test |
| **Throughput** | > 100,000 entries/sec | Load test |

**Optimization Mechanisms:**
- **Lazy Evaluation:** Message templates and field serialization deferred until sink write
- **Object Reuse:** LogEntry objects pooled; fields map reused
- **Async Pipeline:** Frontend enqueues to buffer; background worker drains to sinks
- **Batching:** Sinks receive batches (configurable size, flush interval)

**Performance Invariants:**
- **INV-SL-PERF-001** — Logging MUST NOT block the calling thread for > 1ms under normal load.
- **INV-SL-PERF-002** — Backpressure handling: buffer full → drop lowest-level entries (TRACE/DEBUG first) with metric.
- **INV-SL-PERF-003** — CRITICAL and AUDIT entries MUST never be dropped due to backpressure.

#### 3.6.8 Buffering

**Buffer Architecture:**
- **Ring Buffer:** Fixed-capacity ring buffer per sink (configurable, default: 10,000 entries)
- **Flush Triggers:** Buffer full, flush interval (default: 100ms), explicit `flush()`, CRITICAL/AUDIT entry
- **Worker:** Single background worker per sink (or shared worker with sink affinity)

**Buffer Invariants:**
- **INV-SL-BUF-001** — Buffer capacity MUST be configurable via `kernel.configuration`.
- **INV-SL-BUF-002** — Buffer overflow MUST emit `LogBufferOverflow` metric and drop per priority policy.
- **INV-SL-BUF-003** — Flush on kernel shutdown MUST drain all buffers (Part 1 §1.11).

#### 3.6.9 Rotation

**Rotation Policy (FileSink):**
| Parameter | Default | Description |
|-----------|---------|-------------|
| `maxFileSize` | 100 MB | Rotate when file exceeds size |
| `maxFiles` | 10 | Keep N rotated files; delete oldest |
| `compress` | true | Compress rotated files (gzip) |
| `rotationInterval` | 24h | Time-based rotation (optional) |

**Rotation Invariants:**
- **INV-SL-ROT-001** — Rotation MUST NOT lose log entries (atomic rename + create new).
- **INV-SL-ROT-002** — Audit sink MUST NOT rotate (append-only for retention policy).
- **INV-SL-ROT-003** — Rotation MUST be coordinated across sinks if shared file system.

#### 3.6.10 Sinks

**Sink Interface:**

```
Sink {
  name: string;
  write(batch: LogEntry[]): Promise<void>;
  flush(): Promise<void>;
  close(): Promise<void>;
  handleError(error: Error): void;
}
```

**Built-In Sinks:**

| Sink | Purpose | Configuration |
|------|---------|---------------|
| **ConsoleSink** | Human-readable output (dev/ops) | `color`, `format` (json|pretty), `level` |
| **FileSink** | Persistent operational logs | `path`, `rotation`, `level` |
| **EventBusSink** | Bridge logs to EventBus as `LogEvent` | `level`, `includeFields` |
| **AuditSink** | Tamper-evident audit trail | `path`, `hashChain`, `retention` |
| **NullSink** | Discard (testing/benchmarking) | — |

**Sink Invariants:**
- **INV-SL-SNK-001** — At least one sink MUST be configured for operational logs.
- **INV-SL-SNK-002** — AuditSink MUST be configured and distinct from operational sinks.
- **INV-SL-SNK-003** — Sink failures MUST NOT crash StructuredLogger; errors logged internally.
- **INV-SL-SNK-004** — Custom sinks MUST implement `Sink` interface and register via extension point.

#### 3.6.11 Failure Handling

| Failure Scenario | Classification | Response |
|------------------|----------------|----------|
| Sink write fails (transient) | TRANSIENT | Retry with backoff (max 3); queue in buffer |
| Sink write fails (persistent) | DEGRADED | Mark sink DEGRADED; continue other sinks; alert via ObservabilityManager |
| Buffer overflow | DEGRADED | Drop per priority policy; emit `LogBufferOverflow` |
| Correlation context corrupt | CRITICAL | Log with null correlation; continue |
| StructuredLogger internal error | FATAL | Kernel emergency shutdown (Core Component failure = FATAL) |

**Failure Invariants:**
- **INV-SL-FH-001** — StructuredLogger failure is FATAL (Core Component invariant).
- **INV-SL-FH-002** — Sink failures are isolated; one sink failure does not affect others.
- **INV-SL-FH-003** — CRITICAL and AUDIT entries are never dropped due to sink failure.

#### 3.6.12 Recovery

| Scenario | Recovery |
|----------|----------|
| Sink DEGRADED → HEALTHY | Automatic on successful write; emit `SinkRecovered` |
| Buffer drained after overflow | Automatic; resume normal operation |
| Correlation context leak | Automatic clear on handler exit (Part 3.6.4) |

**Recovery Invariants:**
- **INV-SL-REC-001** — Sink recovery is automatic; no manual intervention required.
- **INV-SL-REC-002** — StructuredLogger itself has no recovery procedure (FATAL = kernel shutdown).

#### 3.6.13 Extension Rules

| Extension Point | Mechanism | Governance |
|-----------------|-----------|------------|
| **Custom Sinks** | Implement `Sink` interface; register in logging config | ARB review for production sinks |
| **Custom Fields Enrichment** | Register `LogEnricher` functions | Open; MUST be pure and fast |
| **Custom Serialization** | Override `LogEntry.toJson()` | Rare; MUST produce canonical JSON |

**Extension Prohibitions:**
- **INV-SL-EXT-001** — MUST NOT bypass StructuredLogger for operational logging.
- **INV-SL-EXT-002** — MUST NOT modify log entry format (canonical format is architecture-defined).
- **INV-SL-EXT-003** — MUST NOT disable audit logging.

#### 3.6.14 Architectural Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-SL-STR-001 | Exactly one StructuredLogger instance per process. |
| INV-SL-STR-002 | All structured logging goes through StructuredLogger (no direct sink writes). |
| INV-SL-STR-003 | Log entries are immutable after creation. |
| INV-SL-STR-004 | Correlation enrichment is automatic for event handler contexts. |
| INV-SL-STR-005 | Audit log is append-only, tamper-evident, and separate from operational logs. |
| INV-SL-STR-006 | CRITICAL and AUDIT entries are never dropped. |
| INV-SL-STR-007 | StructuredLogger is initialized in Phase 3 (last Core Component). |

#### 3.6.15 Conformance

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-SL-001 | Implements `ICoreComponent` interface | Static: interface verification |
| CONF-SL-002 | Initializes in Phase 3, after EventBus, ServiceRegistry, ConfigurationManager | Static: phase metadata; Runtime: sequence |
| CONF-SL-003 | Publishes `CoreComponentInitialized` on RUNNING | Runtime: event emission test |
| CONF-SL-004 | Publishes `CoreComponentShutdown` on SHUTDOWN | Runtime: event emission test |
| CONF-SL-005 | All log entries contain correlationId, causationId, source | Contract test (all log calls) |
| CONF-SL-006 | Audit entries go to AuditSink only | Integration test |
| CONF-SL-007 | CRITICAL/AUDIT never dropped under backpressure | Load test |
| CONF-SL-008 | Log entry format matches canonical schema | Schema validation test |
| CONF-SL-009 | Sink failures isolated | Fault injection test |
| CONF-SL-010 | Performance targets met | Benchmark test |

---

### 3.7 Component Interaction

#### 3.7.1 Interaction Rules

| Rule ID | Rule | Scope |
|---------|------|-------|
| CC-IR-001 | **EventBus-First:** All post-initialization communication between Core Components MUST occur via EventBus. | Mandatory |
| CC-IR-002 | **Initialization Injection:** During `initialize(kernel)`, Core Components MAY receive references to already-initialized dependencies via kernel accessors. | Permitted (Phase 0–3 only) |
| CC-IR-003 | **No Direct Calls:** Core Components MUST NOT invoke methods on each other directly after initialization completes. | Mandatory |
| CC-IR-004 | **Event Contracts:** All inter-component events MUST use defined EventTypes (Part 2). | Mandatory |
| CC-IR-005 | **Logger Ubiquity:** All Core Components, Core Managers, and Services MUST use `kernel.logger` for structured logging. | Mandatory |

#### 3.7.2 Dependency Graph

```
Initialization Dependencies (Directed Acyclic Graph):

    ┌─────────────┐
    │  EventBus   │  (C1) — Phase 0 — No dependencies
    └──────┬──────┘
           │
           ▼
    ┌─────────────┐     ┌──────────────────┐
    │ ServiceReg. │     │ ConfigManager    │  (C2, C3) — Phase 1, 2 — Depend on EventBus
    │   (C2)      │     │    (C3)          │
    └──────┬──────┘     └────────┬─────────┘
           │                     │
           └──────────┬──────────┘
                      ▼
         ┌─────────────────────┐
         │ StructuredLogger    │  (C4) — Phase 3 — Depends on C1, C2, C3
         │      (C4)           │
         └─────────────────────┘
```

**Dependency Invariants:**
- **INV-CC-DEP-001** — EventBus has ZERO Core Component dependencies.
- **INV-CC-DEP-002** — ServiceRegistry depends ONLY on EventBus.
- **INV-CC-DEP-003** — ConfigurationManager depends ONLY on EventBus.
- **INV-CC-DEP-004** — StructuredLogger depends on EventBus, ServiceRegistry, ConfigurationManager.
- **INV-CC-DEP-005** — No cycles in Core Component dependency graph.

#### 3.7.3 Initialization Order

| Phase | Component | Depends On | Parallelism |
|-------|-----------|------------|-------------|
| 0 | EventBus (C1) | — | Sequential |
| 1 | ServiceRegistry (C2) | EventBus | Sequential |
| 2 | ConfigurationManager (C3) | EventBus | Sequential |
| 3 | StructuredLogger (C4) | EventBus, ServiceRegistry, ConfigurationManager | Sequential |

**Order Invariants:**
- **INV-CC-INIT-001** — Phases 0→1→2→3 are strictly sequential.
- **INV-CC-INIT-002** — EventBus MUST be RUNNING before Phase 1 begins.
- **INV-CC-INIT-003** — ConfigurationManager MUST be FROZEN before Phase 3 completes.
- **INV-CC-INIT-004** — StructuredLogger MUST be the last Core Component to initialize.

#### 3.7.4 Shutdown Order

| Phase | Component | Order |
|-------|-----------|-------|
| S3 | StructuredLogger (C4) | First Core Component |
| S2 | ConfigurationManager (C3) | Second |
| S1 | ServiceRegistry (C2) | Third |
| S0 | EventBus (C1) | Last Core Component |

**Order Invariants:**
- **INV-CC-SD-001** — Shutdown order is EXACT REVERSE of initialization order.
- **INV-CC-SD-002** — EventBus MUST be the last Core Component to shut down (drains in-flight events).
- **INV-CC-SD-003** — StructuredLogger MUST shut down first (flushes logs from other components).

#### 3.7.5 Failure Propagation

| Failure Origin | Propagation | Kernel Response |
|----------------|-------------|-----------------|
| **EventBus (C1)** | All components lose communication | FATAL → Emergency shutdown |
| **ServiceRegistry (C2)** | Service discovery fails; LifecycleManager cannot coordinate | FATAL → Emergency shutdown |
| **ConfigurationManager (C3)** | Config reads fail; managers/services cannot configure | FATAL → Emergency shutdown |
| **StructuredLogger (C4)** | Observability lost; audit trail broken | FATAL → Emergency shutdown |

**Propagation Invariants:**
- **INV-CC-FP-001** — Core Component failure is ALWAYS FATAL (Part 1 INV-FH-001).
- **INV-CC-FP-002** — No graceful degradation for Core Component failures.
- **INV-CC-FP-003** — Failure events (`CoreComponentFailed`) MUST be published before shutdown if EventBus operational.

#### 3.7.6 Ownership Boundaries

| Boundary | Rule |
|----------|------|
| **Kernel ↔ Core Components** | Kernel exclusively owns lifecycle; Components are internal |
| **Core Components ↔ Core Managers** | Managers access Components via kernel accessors; no reverse dependency |
| **Core Components ↔ Services** | Services access Components via kernel accessors; Components know nothing of Services |
| **Core Component ↔ Core Component** | Post-init: EventBus only; no direct references |

**Boundary Invariants:**
- **INV-CC-OB-001** — Core Components do not import Service modules.
- **INV-CC-OB-002** — Core Components do not import Core Manager modules.
- **INV-CC-OB-003** — Core Component methods are never called directly by Services or Managers (except via kernel accessors for read-only state).

#### 3.7.7 Allowed Communication Paths

| From | To | Mechanism | Purpose |
|------|----|-----------|---------|
| Any Component | EventBus | `publish()` | Emit events |
| Any Component | EventBus | `subscribe()` | Receive events |
| ServiceRegistry | EventBus | `publish(ServiceRegistered)` | Notify registrations |
| ConfigurationManager | EventBus | `publish(ConfigurationFrozen)` | Notify freeze |
| StructuredLogger | EventBus | `publish(LogEvent)` | Optional: bridge logs to event stream |
| EventBus | Any Component | `dispatch()` | Deliver events |

#### 3.7.8 Forbidden Communication Paths

| From | To | Mechanism | Reason |
|------|----|-----------|--------|
| ServiceRegistry | EventBus | Direct method call | Violates EventBus-First |
| ConfigurationManager | ServiceRegistry | Direct method call | Violates EventBus-First |
| StructuredLogger | ConfigurationManager | Direct method call (post-init) | Violates EventBus-First |
| EventBus | ServiceRegistry | Direct method call | Violates EventBus-First |
| Any Component | Any Component | Shared mutable state | Part 0 Principle 1 |
| Service | Core Component | Direct method call | Must use kernel accessor + EventBus |

---

### 3.8 Cross-Cutting Invariants

The following invariants apply to **all four Core Components** and are verified at multiple points in the kernel lifecycle.

#### 3.8.1 Structural Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| INV-CC-STR-001 | Exactly four Core Components exist: EventBus, ServiceRegistry, ConfigurationManager, StructuredLogger. | Static: count verification |
| INV-CC-STR-002 | Each Core Component implements `ICoreComponent` interface. | Static: interface check |
| INV-CC-STR-003 | Each Core Component has unique, fixed initialization phase (0–3). | Static: metadata check |
| INV-CC-STR-004 | Each Core Component has unique, fixed shutdown phase (S0–S3). | Static: metadata check |
| INV-CC-STR-005 | Core Component accessors on `HermesKernel` are read-only and return singletons. | Static: API surface check |
| INV-CC-STR-006 | No Core Component is instantiated outside `HermesKernel` constructor. | Static: construction analysis |

#### 3.8.2 Runtime Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| INV-CC-RT-001 | All Core Components reach RUNNING state before Phase 4 (Core Managers) begins. | Runtime: phase transition |
| INV-CC-RT-002 | All Core Components remain RUNNING throughout kernel RUNNING state. | Periodic: health check |
| INV-CC-RT-003 | All inter-Core-Component communication post-init occurs via EventBus. | Runtime: EventBus instrumentation |
| INV-CC-RT-004 | No Core Component holds direct references to other Core Components post-init. | Periodic: heap analysis |
| INV-CC-RT-005 | All Core Components publish `Heartbeat` events every 10s (configurable). | Runtime: EventBus monitoring |
| INV-CC-RT-006 | All Core Components respond to `healthCheck()` within 5s. | Periodic: LifecycleManager poll |
| INV-CC-RT-007 | All Core Component events carry `correlationId` and `causationId`. | Contract: event validation |
| INV-CC-RT-008 | StructuredLogger is used by all Core Components for logging. | Static: import analysis; Runtime: log correlation |

#### 3.8.3 Lifecycle Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| INV-CC-LC-001 | Initialization order: 0→1→2→3 strictly sequential. | Runtime: phase execution |
| INV-CC-LC-002 | Shutdown order: S3→S2→S1→S0 strictly sequential (reverse). | Runtime: phase execution |
| INV-CC-LC-003 | EventBus initializes first, shuts down last. | Runtime: phase execution |
| INV-CC-LC-004 | ConfigurationManager freezes before any Core Manager or Service initializes. | Runtime: phase transition |
| INV-CC-LC-005 | StructuredLogger initializes after ConfigurationManager freeze. | Runtime: phase execution |
| INV-CC-LC-006 | Partial initialization failure triggers full rollback. | Runtime: failure injection |

#### 3.8.4 Failure Invariants

| Invariant ID | Statement | Verification |
|--------------|-----------|--------------|
| INV-CC-FL-001 | Any Core Component failure → Kernel FATAL classification. | Runtime: failure handling |
| INV-CC-FL-002 | Core Component failure events published before shutdown (if EventBus alive). | Runtime: failure injection |
| INV-CC-FL-003 | No Core Component has automated recovery (unlike Core Managers). | Architecture: by definition |
| INV-CC-FL-004 | Kernel shutdown proceeds to TERMINATED regardless of Core Component shutdown errors. | Runtime: shutdown execution |

---

### 3.9 Conformance Requirements

#### 3.9.1 Static Conformance (Build-Time)

| Requirement ID | Check | Tooling |
|----------------|-------|---------|
| CONF-CC-ST-001 | Exactly 4 Core Component classes exist | AST analysis |
| CONF-CC-ST-002 | Each implements `ICoreComponent` | Interface verification |
| CONF-CC-ST-003 | Phase numbers match specification (0–3) | Metadata validation |
| CONF-CC-ST-004 | Shutdown phase numbers match specification (S0–S3) | Metadata validation |
| CONF-CC-ST-005 | `HermesKernel` has exactly 4 Core Component accessors | TypeScript AST analysis |
| CONF-CC-ST-006 | Core Component constructors are not public | Visibility analysis |
| CONF-CC-ST-007 | No Core Component imports Service or Core Manager modules | Import graph analysis |
| CONF-CC-ST-008 | All public methods have architectural contract documentation | Documentation lint |

#### 3.9.2 Dynamic Conformance (Runtime)

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-CC-DY-001 | Kernel initializes Core Components in Phase 0→1→2→3 order | Integration test |
| CONF-CC-DY-002 | Kernel shuts down Core Components in Phase S3→S2→S1→S0 order | Integration test |
| CONF-CC-DY-003 | EventBus operational before Phase 1 begins | Phase 0 assertion |
| CONF-CC-DY-004 | ConfigurationManager frozen before Phase 4 begins | Phase transition assertion |
| CONF-CC-DY-005 | All Core Components accessible via kernel accessors in RUNNING state | Accessor test |
| CONF-CC-DY-006 | Accessor access before RUNNING throws `KernelNotReadyError` | Error test |
| CONF-CC-DY-007 | Core Component health checks pass periodically | Periodic audit test |
| CONF-CC-DY-008 | All Core Component events have correlationId, causationId | Event schema validation |
| CONF-CC-DY-009 | No direct inter-Component method calls detected post-init | Runtime instrumentation |
| CONF-CC-DY-010 | Failure injection triggers FATAL for any Core Component | Chaos test |

#### 3.9.3 Verification

**Verification Layers:**

| Layer | Scope | Frequency | Tooling |
|-------|-------|-----------|---------|
| **L1: Structural** | Code compiles, interfaces satisfied | Every build | `mypy --strict`, TypeScript compiler |
| **L2: Contract** | Event schemas, method signatures | Every build | Schema validation, interface tests |
| **L3: Behavioral** | Runtime invariants, phase ordering, failure handling | Every CI run | Integration tests (21 scenarios) |
| **L4: Architectural** | No principle violations (Part 0 §0.4) | Every CI run + ARB audit | Static analysis rules, architecture tests |

**Verification Artifacts Required:**
- Phase transition logs with timestamps
- EventBus trace showing all Core Component initialization events
- Health check results for all Core Components at 30s intervals
- Configuration hash at freeze and termination
- Structured log sample with correlation IDs

#### 3.9.4 Violation Handling

| Severity | Detection | Response |
|----------|-----------|----------|
| **Build-Time FAIL** | Static analysis, type check, schema validation | CI pipeline blocks; merge prohibited |
| **Runtime CRITICAL** | Health check failure, invariant violation | Kernel transitions to FATAL; emergency shutdown |
| **Runtime DEGRADED** | Missed heartbeat, slow health check | Alert via ObservabilityManager; remediation within SLA |
| **Audit Finding** | L4 architectural review finds violation | ARB review; remediation plan within 5 business days |

---

### 3.10 Implementation vs Architecture Target

| Aspect | Implementation (v0.1.x) | Architecture Target (v1.0) |
|--------|------------------------|---------------------------|
| **Core Component Count** | 3–5 components, varying names | **Exactly 4: EventBus, ServiceRegistry, ConfigurationManager, StructuredLogger** |
| **Initialization Phases** | Ad-hoc, some parallel | **Phases 0–3 strictly sequential** |
| **Shutdown Phases** | Best-effort, no defined order | **Phases S3–S0 strictly reverse order** |
| **EventBus** | Basic pub/sub, no priority, no DLQ | **Full Part 2 spec: priority lanes, DLQ, replay, exactly-once opt-in** |
| **ServiceRegistry** | Simple dict, no topology | **DAG topology, health tracking, capability index, namespaces** |
| **ConfigurationManager** | Mutable, single file, no schema | **4-layer merge, schema validation, immutable freeze, secret handling** |
| **StructuredLogger** | Standard library logging | **Structured JSON, correlation enrichment, audit sink, buffering, rotation, sinks** |
| **Inter-Component Comm** | Mixed direct calls + events | **EventBus-only post-init (CC-IR-001)** |
| **Conformance** | None | **Static (L1/L2) + Dynamic (L3/L4) mandatory** |
| **Failure Handling** | Try-catch, inconsistent | **FATAL for any Core Component failure; classified for others** |

---

### 3.11 Summary

#### Core Components

| Symbol | Name | Phase | Accessor | Primary Contract |
|--------|------|-------|----------|------------------|
| **C1** | EventBus | 0 / S0 | `kernel.eventBus` | Part 2 (Event System) |
| **C2** | ServiceRegistry | 1 / S1 | `kernel.serviceRegistry` | This Part §3.4 |
| **C3** | ConfigurationManager | 2 / S2 | `kernel.configuration` | This Part §3.5 |
| **C4** | StructuredLogger | 3 / S3 | `kernel.logger` | This Part §3.6 |

#### Responsibilities

- **EventBus:** Sole communication substrate; publication, subscription, dispatch, ordering, delivery guarantees, failure handling, replay, observability.
- **ServiceRegistry:** Service registration, discovery, dependency topology, initialization/shutdown planning, health tracking, capability advertisement.
- **ConfigurationManager:** Four-layer configuration merge, schema validation, immutable freeze enforcement, runtime read-only access, environment/secret handling.
- **StructuredLogger:** Structured JSON logging, correlation enrichment, log levels, audit logging, buffering, rotation, pluggable sinks.

#### Ownership

- **Exclusive Owner:** HermesKernel for all four Core Components.
- **Construction:** Kernel constructor.
- **Initialization:** Phased (0→3) via `ICoreComponent.initialize()`.
- **Destruction:** Phased reverse (S3→S0) via `ICoreComponent.shutdown()`.
- **Access:** Read-only singleton accessors on `HermesKernel.instance`.

#### Initialization

- **Order:** EventBus (0) → ServiceRegistry (1) → ConfigurationManager (2) → StructuredLogger (3)
- **Dependencies:** Strict DAG; EventBus has none; logger depends on all three.
- **Freeze:** ConfigurationManager freezes at end of Phase 3, before Core Managers (Phase 4).
- **Verification:** All invariants checked at phase transitions.

#### Dependencies

- **EventBus:** None (foundation).
- **ServiceRegistry:** EventBus only.
- **ConfigurationManager:** EventBus only.
- **StructuredLogger:** EventBus, ServiceRegistry, ConfigurationManager.
- **Post-Init Communication:** EventBus only (CC-IR-001).

#### Mandatory Invariants

| Category | Count | Examples |
|----------|-------|----------|
| Structural | 6 | Fixed count, fixed phases, singleton accessors, no external construction |
| Runtime | 8 | Phase ordering, EventBus-only comms, health checks, heartbeats, correlation IDs |
| Lifecycle | 6 | Init order, shutdown order, freeze timing, rollback on failure |
| Failure | 4 | Core Component failure = FATAL, no auto-recovery, event publication, best-effort shutdown |

#### Conformance

- **Static (L1/L2):** Interface compliance, phase metadata, accessor count, import restrictions — verified every build.
- **Dynamic (L3/L4):** Phase ordering, freeze timing, health checks, event contracts, architectural principles — verified every CI run and ARB audit.
- **Violation:** Build-time = merge block; Runtime CRITICAL = emergency shutdown; Runtime DEGRADED = alert + SLA; Audit = ARB review + 5-day remediation.

---

**END OF PART 3 — CORE COMPONENTS ARCHITECTURE**

*This document is FROZEN. Any modification requires Architecture Review Board approval. All subsequent Parts (4–N) MUST conform to this specification.*