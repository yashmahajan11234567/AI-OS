# AI-OS Architecture Specification v1.0
## Part 1: Hermes Kernel Architecture

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

### 1.1 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART1 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 1 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (2–N) MUST conform to Part 1. Part 1 MUST NOT contradict Part 0. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles, conformance), PART2 (Event System), PART3 (Core Managers), PART4 (Service Framework), PART5 (Engineering Services), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis), MIGRATION_PLAN.md (phasing), ARCHITECTURE_ANALYSIS.md (architectural decisions) |

**Conformance Requirement:** Every subsequent Part (2–N) of this specification MUST explicitly reference Part 1 sections for kernel terminology, interfaces, and conformance criteria. Any Part that contradicts Part 1 is non-conformant and MUST be revised.

---

### 1.2 Scope

This Part defines the authoritative architecture of the **Hermes Kernel** — the orchestration core of AI-OS. The Hermes Kernel owns exactly four (4) Core Components and nine (9) Core Managers, and serves as the central coordination substrate for all Services (Engineering Services and Application Services) via the Event System.

**In Scope:**
- HermesKernel class definition, responsibilities, and ownership boundaries
- The four (4) Core Components: EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager
- The nine (9) Core Managers and their global singleton accessors
- Kernel lifecycle: initialization sequence, state transitions, shutdown sequence
- Internal interactions between Core Components and Core Managers
- Public interfaces (kernel API surface)
- Extension constraints and conformance requirements
- Failure handling and recovery behavior
- Architectural invariants

**Out of Scope:**
- Event System detailed specification (covered in Part 2)
- Core Manager detailed specifications (covered in Part 3)
- Service Framework detailed specification (covered in Part 4)
- Engineering Services detailed specifications (covered in Part 5)
- Application Services (domain-specific, not architectural)

---

### 1.3 Terminology

| Term | Definition |
|------|------------|
| **HermesKernel** | The singleton orchestration core of AI-OS; owns Core Components and Core Managers |
| **Core Component** | One of four (4) kernel-owned infrastructure primitives: EventBus, ServiceRegistry, ConfigurationManager, LifecycleManager |
| **Core Manager** | One of nine (9) kernel-owned capability managers exposed via global singleton accessors |
| **Service** | A BaseService-derived entity registered in ServiceRegistry, managed by LifecycleManager |
| **Kernel State** | The finite state machine governing HermesKernel lifecycle: UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED |
| **Initialization Phase** | A numbered, ordered stage in kernel boot (Phase 0–N) with strict dependency ordering |
| **Shutdown Phase** | A numbered, ordered stage in kernel termination (Phase N–0) with strict reverse dependency ordering |
| **Singleton Accessor** | A property on `HermesKernel.instance` returning a Core Manager instance (e.g., `kernel.memory`, `kernel.llm`) |
| **Conformance** | Mandatory adherence to this specification; verified by automated tooling and ARB review |

---

### 1.4 Architectural Principles (from Part 0)

The following principles from Part 0 §0.3 govern this Part:

1. **Single Orchestration Core** — Exactly one HermesKernel instance exists per process. Multiple instances are a conformance violation.
2. **Four Core Components** — The kernel owns exactly four Core Components. No more, no less.
3. **Nine Core Managers** — The kernel exposes exactly nine Core Managers via singleton accessors. No more, no less.
4. **Event-First Communication** — All inter-component, inter-manager, and inter-service communication MUST flow through the EventBus. Direct method calls between managers are PROHIBITED except for initialization-time dependency injection.
5. **Explicit Lifecycle** — Every kernel-owned entity (Core Component, Core Manager, Service) MUST participate in the kernel's phased initialization and shutdown sequences.
6. **Immutable Configuration** — ConfigurationManager state MUST be frozen after INITIALIZING phase completes. Runtime mutation is PROHIBITED.
7. **Failure Isolation** — Failures in one Core Manager or Service MUST NOT cascade to others without explicit kernel mediation.
8. **Deterministic Ordering** — Initialization and shutdown sequences MUST be deterministic and reproducible given identical configuration.

---

### 1.5 HermesKernel — Purpose and Responsibilities

#### 1.5.1 Purpose

The HermesKernel is the **sole orchestration authority** in AI-OS. It provides:

- **Component Composition** — Instantiates, wires, and owns the four Core Components
- **Capability Provisioning** — Instantiates, configures, and exposes the nine Core Managers
- **Service Orchestration** — Hosts the ServiceRegistry and LifecycleManager for all Services
- **Lifecycle Governance** — Enforces phased initialization, runtime steady state, and ordered shutdown
- **Failure Containment** — Isolates, reports, and recovers from component/manager/service failures
- **Configuration Authority** — Owns the immutable configuration contract via ConfigurationManager

#### 1.5.2 Responsibilities

| # | Responsibility | Description |
|---|----------------|-------------|
| R1 | **Singleton Enforcement** | Ensure exactly one HermesKernel instance per process; throw on second construction attempt |
| R2 | **Core Component Ownership** | Construct, initialize, and destroy exactly four Core Components in mandated order |
| R3 | **Core Manager Ownership** | Construct, initialize, and destroy exactly nine Core Managers in mandated order |
| R4 | **Lifecycle Orchestration** | Drive the kernel state machine through UNINITIALIZED → INITIALIZING → RUNNING → SHUTTING_DOWN → TERMINATED |
| R5 | **Phase Management** | Execute initialization phases (0–N) and shutdown phases (N–0) with dependency-ordered sequencing |
| R6 | **EventBus Integration** | Ensure all Core Components and Core Managers register event subscriptions during their initialization |
| R7 | **Service Registration** | Provide ServiceRegistry for Service registration, discovery, and dependency resolution |
| R8 | **Configuration Freeze** | Enforce ConfigurationManager immutability after INITIALIZING phase completion |
| R9 | **Failure Handling** | Catch, classify, and route failures per §1.12; initiate recovery or controlled shutdown |
| R10 | **Conformance Enforcement** | Validate architectural invariants at phase transitions; reject non-conformant state |

#### 1.5.3 Non-Responsibilities

The HermesKernel MUST NOT:
- Contain business logic for any SDLC phase (delegated to Engineering Services)
- Directly process user requests or LLM interactions (delegated to Core Managers and Services)
- Manage persistence schemas or migration logic (delegated to StorageManager)
- Implement event routing logic (delegated to EventBus)
- Provide HTTP/gRPC endpoints (delegated to Gateway Service, an Application Service)

---

### 1.6 Ownership Boundaries

#### 1.6.1 Kernel-Owned Entities

| Entity Category | Count | Ownership | Lifecycle Managed By |
|-----------------|-------|-----------|---------------------|
| Core Components | 4 | **Exclusive** — Kernel constructs, initializes, destroys | LifecycleManager (phases) |
| Core Managers | 9 | **Exclusive** — Kernel constructs, initializes, destroys | LifecycleManager (phases) |
| Services | N (dynamic) | **Registry** — Kernel hosts registry; Services self-register | LifecycleManager (phases) |

#### 1.6.2 Ownership Invariants

| Invariant ID | Statement |
|--------------|-----------|
| INV-OWN-001 | No entity outside HermesKernel may instantiate a Core Component or Core Manager |
| INV-OWN-002 | Core Components and Core Managers MUST NOT hold references to each other outside kernel-managed initialization injection |
| INV-OWN-003 | Services MUST NOT instantiate Core Components or Core Managers; access ONLY via `HermesKernel.instance.<manager>` |
| INV-OWN-004 | Kernel MUST NOT delegate construction of Core Components or Core Managers to any Service or external factory |
| INV-OWN-005 | All kernel-owned entities MUST be destroyed during SHUTTING_DOWN phase; no entity may outlive kernel termination |

---

### 1.7 Core Components

The HermesKernel owns exactly four (4) Core Components. This number is FIXED and MUST NOT change without ARB approval and specification revision.

#### 1.7.1 Core Component Registry

| # | Core Component | Symbol | Responsibility | Initialization Phase |
|---|----------------|--------|----------------|---------------------|
| C1 | **EventBus** | `kernel.eventBus` | Sole communication substrate; event publication, subscription, routing, correlation | Phase 0 (first) |
| C2 | **ServiceRegistry** | `kernel.serviceRegistry` | Service registration, discovery, dependency topology, health tracking | Phase 1 |
| C3 | **ConfigurationManager** | `kernel.configuration` | Immutable configuration authority; schema validation, environment overlay, freeze enforcement | Phase 2 |
| C4 | **LifecycleManager** | `kernel.lifecycle` | Phased initialization/shutdown orchestration; state machine; failure escalation | Phase 3 (last core) |

#### 1.7.2 Core Component Interface Contract

All Core Components MUST implement the `ICoreComponent` interface:

```typescript
interface ICoreComponent {
  readonly name: string;                    // Unique identifier (e.g., "EventBus")
  readonly initializationPhase: number;     // Mandated phase number (0–3)
  readonly dependencies: string[];          // Names of Core Components this depends on
  
  initialize(kernel: HermesKernel): Promise<void>;  // Called during INITIALIZING phase
  shutdown(): Promise<void>;                 // Called during SHUTTING_DOWN phase
  healthCheck(): Promise<HealthStatus>;      // Periodic health probe
}
```

#### 1.7.3 Core Component Initialization Order

The initialization order is **mandated and immutable**:

```
Phase 0: EventBus              (no dependencies)
Phase 1: ServiceRegistry       (depends: EventBus)
Phase 2: ConfigurationManager  (depends: EventBus)
Phase 3: LifecycleManager      (depends: EventBus, ServiceRegistry, ConfigurationManager)
```

**Invariant:** `INV-CC-001` — Core Components MUST initialize in Phase 0→1→2→3 order. Reverse order for shutdown.

**Invariant:** `INV-CC-002` — EventBus MUST be fully operational before any other Core Component initializes.

**Invariant:** `INV-CC-003` — LifecycleManager MUST be the last Core Component to initialize and first to shut down.

#### 1.7.4 Core Component Interaction Rules

| Rule ID | Rule |
|---------|------|
| CC-IR-001 | Core Components communicate ONLY via EventBus after initialization completes |
| CC-IR-002 | During initialization, dependency injection via constructor/initialize() parameters is PERMITTED |
| CC-IR-003 | Core Components MUST NOT call methods on each other directly post-initialization |
| CC-IR-004 | Core Components MUST publish `CoreComponentInitialized` event upon successful initialization |
| CC-IR-005 | Core Components MUST publish `CoreComponentShutdown` event upon shutdown initiation |

---

### 1.8 Core Managers

The HermesKernel exposes exactly nine (9) Core Managers via singleton accessors on `HermesKernel.instance`. This number is FIXED and MUST NOT change without ARB approval.

#### 1.8.1 Core Manager Registry

| # | Core Manager | Accessor | Capability Domain | Initialization Phase |
|---|--------------|----------|-------------------|---------------------|
| M1 | **MemoryManager** | `kernel.memory` | Episodic, semantic, working memory; context assembly; retention policies | Phase 4 |
| M2 | **LLMManager** | `kernel.llm` | Model routing, prompt templating, token budgeting, provider abstraction | Phase 4 |
| M3 | **ToolManager** | `kernel.tools` | Tool registry, execution sandbox, permission mediation, result caching | Phase 5 |
| M4 | **StorageManager** | `kernel.storage` | Persistence abstraction; schemas, migrations, transactions, backups | Phase 5 |
| M5 | **ContextManager** | `kernel.context` | Conversation context, window management, compression, relevance scoring | Phase 6 |
| M6 | **AgentManager** | `kernel.agents` | Agent spawning, lifecycle, communication, resource quotas | Phase 6 |
| M7 | **WorkflowManager** | `kernel.workflows` | Workflow definition, execution, checkpointing, compensation | Phase 7 |
| M8 | **SecurityManager** | `kernel.security` | Authentication, authorization, audit, secrets, encryption | Phase 7 |
| M9 | **ObservabilityManager** | `kernel.observability` | Metrics, tracing, logging, alerting, profiling | Phase 8 (last) |

#### 1.8.2 Core Manager Interface Contract

All Core Managers MUST implement the `ICoreManager` interface:

```typescript
interface ICoreManager {
  readonly name: string;                    // Unique identifier (e.g., "MemoryManager")
  readonly initializationPhase: number;     // Mandated phase number (4–8)
  readonly dependencies: string[];          // Names of Core Components/Managers this depends on
  readonly capabilities: Capability[];      // Declared capabilities for discovery
  
  initialize(kernel: HermesKernel): Promise<void>;  // Called during INITIALIZING phase
  shutdown(): Promise<void>;                 // Called during SHUTTING_DOWN phase
  healthCheck(): Promise<HealthStatus>;      // Periodic health probe
  getMetrics(): ManagerMetrics;              // Observability data
}
```

#### 1.8.3 Core Manager Initialization Order

The initialization order is **mandated and immutable**:

```
Phase 4: MemoryManager, LLMManager           (depends: EventBus, ConfigurationManager)
Phase 5: ToolManager, StorageManager         (depends: EventBus, ConfigurationManager, MemoryManager, LLMManager)
Phase 6: ContextManager, AgentManager        (depends: Phase 4–5 managers)
Phase 7: WorkflowManager, SecurityManager    (depends: Phase 4–6 managers)
Phase 8: ObservabilityManager                (depends: all prior managers)
```

**Within-phase ordering** (for deterministic reproducibility):
- Phase 4: MemoryManager → LLMManager
- Phase 5: ToolManager → StorageManager
- Phase 6: ContextManager → AgentManager
- Phase 7: WorkflowManager → SecurityManager

**Invariant:** `INV-CM-001` — Core Managers MUST initialize in Phase 4→5→6→7→8 order with within-phase ordering as specified.

**Invariant:** `INV-CM-002` — No Core Manager may initialize before Phase 4 (after all Core Components).

**Invariant:** `INV-CM-003` — ObservabilityManager MUST be the last Core Manager to initialize and first to shut down.

#### 1.8.4 Core Manager Singleton Accessors

The HermesKernel class MUST expose exactly nine (9) read-only properties:

```typescript
class HermesKernel {
  // Core Components (also accessible)
  get eventBus(): EventBus;
  get serviceRegistry(): ServiceRegistry;
  get configuration(): ConfigurationManager;
  get lifecycle(): LifecycleManager;
  
  // Core Managers — EXACTLY THESE NINE
  get memory(): MemoryManager;
  get llm(): LLMManager;
  get tools(): ToolManager;
  get storage(): StorageManager;
  get context(): ContextManager;
  get agents(): AgentManager;
  get workflows(): WorkflowManager;
  get security(): SecurityManager;
  get observability(): ObservabilityManager;
}
```

**Invariant:** `INV-CM-004` — No additional accessors may be added. No accessor may be removed. Renaming requires ARB approval.

**Invariant:** `INV-CM-005` — Accessors MUST return the same instance for the lifetime of the kernel (singleton semantics).

**Invariant:** `INV-CM-006` — Accessing an accessor before kernel reaches RUNNING state MUST throw `KernelNotReadyError`.

---

### 1.9 Kernel Lifecycle

#### 1.9.1 Kernel State Machine

The HermesKernel operates as a deterministic finite state machine:

```
┌──────────────┐
│ UNINITIALIZED│  (initial state, before .initialize() called)
└──────┬───────┘
       │ initialize()
       ▼
┌──────────────┐
│ INITIALIZING │  (phased initialization: Core Components → Core Managers → Services)
└──────┬───────┘
       │ all phases complete successfully
       ▼
┌──────────────┐
│ RUNNING      │  (steady state; kernel accepts requests, processes events)
└──────┬───────┘
       │ shutdown() called OR fatal error
       ▼
┌──────────────┐
│ SHUTTING_DOWN│  (phased shutdown: Services → Core Managers → Core Components)
└──────┬───────┘
       │ all phases complete (success or forced)
       ▼
┌──────────────┐
│ TERMINATED   │  (final state; no further operations permitted)
└──────────────┘
```

**Invariant:** `INV-LC-001` — Kernel state transitions MUST follow the exact sequence above. Skipping states is PROHIBITED.

**Invariant:** `INV-LC-002` — Kernel MUST NOT transition from RUNNING directly to TERMINATED; SHUTTING_DOWN is mandatory.

**Invariant:** `INV-LC-003` — Once TERMINATED, the kernel instance MUST be discarded; re-initialization is PROHIBITED.

#### 1.9.2 State Transition Events

The kernel MUST publish the following events on `EventBus` at each transition:

| Transition | Event Type | Payload |
|------------|------------|---------|
| UNINITIALIZED → INITIALIZING | `KernelInitializationStarted` | `{ timestamp, configHash }` |
| INITIALIZING → RUNNING | `KernelReady` | `{ timestamp, initializationDurationMs, componentCount, managerCount, serviceCount }` |
| RUNNING → SHUTTING_DOWN | `KernelShutdownStarted` | `{ timestamp, reason: 'graceful' | 'error' | 'forced', error? }` |
| SHUTTING_DOWN → TERMINATED | `KernelTerminated` | `{ timestamp, shutdownDurationMs, errors: Error[] }` |

---

### 1.10 Initialization Sequence

#### 1.10.1 Initialization Entry Point

```typescript
async function initialize(config: KernelConfig): Promise<void>
```

**Preconditions:**
- Kernel state = UNINITIALIZED
- `config` passes ConfigurationManager schema validation
- No other HermesKernel instance exists in process

**Postconditions:**
- Kernel state = RUNNING
- All Core Components initialized (Phases 0–3)
- All Core Managers initialized (Phases 4–8)
- All registered Services initialized (Service phases)
- `KernelReady` event published

#### 1.10.2 Phase Definitions

| Phase | Name | Entities | Parallelism | Timeout |
|-------|------|----------|-------------|---------|
| 0 | **EventBus Bootstrap** | EventBus | Sequential (single) | 5s |
| 1 | **Registry Bootstrap** | ServiceRegistry | Sequential | 5s |
| 2 | **Configuration Freeze** | ConfigurationManager | Sequential | 10s |
| 3 | **Lifecycle Bootstrap** | LifecycleManager | Sequential | 5s |
| 4 | **Memory & LLM** | MemoryManager, LLMManager | **Parallel** (within phase) | 30s |
| 5 | **Tools & Storage** | ToolManager, StorageManager | **Parallel** (within phase) | 30s |
| 6 | **Context & Agents** | ContextManager, AgentManager | **Parallel** (within phase) | 30s |
| 7 | **Workflows & Security** | WorkflowManager, SecurityManager | **Parallel** (within phase) | 30s |
| 8 | **Observability** | ObservabilityManager | Sequential | 10s |
| 9+ | **Service Initialization** | All registered Services | Per Service dependency topology | Per Service |

#### 1.10.3 Phase Execution Algorithm

```pseudocode
function executeInitialization(config):
    state ← INITIALIZING
    publish KernelInitializationStarted
    
    // Phase 0–3: Core Components (strict sequential)
    for phase in 0..3:
        component ← getCoreComponentForPhase(phase)
        await withTimeout(component.initialize(this), phaseTimeout[phase])
        verifyInvariant(component)
        publish CoreComponentInitialized(component.name)
    
    // Phase 4–8: Core Managers (parallel within phase, sequential across phases)
    for phase in 4..8:
        managers ← getCoreManagersForPhase(phase)
        await parallelWithTimeout(
            managers.map(m → m.initialize(this)),
            phaseTimeout[phase]
        )
        for m in managers:
            verifyInvariant(m)
            publish CoreManagerInitialized(m.name)
    
    // Configuration freeze enforcement
    configuration.freeze()
    publish ConfigurationFrozen
    
    // Phase 9+: Services (topological order per ServiceRegistry)
    servicePlan ← serviceRegistry.computeInitializationPlan()
    for batch in servicePlan.batches:
        await parallelWithTimeout(
            batch.map(s → s.initialize()),
            serviceTimeout
        )
    
    state ← RUNNING
    publish KernelReady
```

#### 1.10.4 Initialization Failure Handling

| Failure Point | Behavior |
|---------------|----------|
| Core Component initialization fails | Abort initialization; initiate SHUTTING_DOWN for already-initialized components in reverse order; publish `KernelInitializationFailed`; throw |
| Core Manager initialization fails | Abort phase; shut down managers initialized in current and prior phases in reverse order; shut down Core Components in reverse order; publish `KernelInitializationFailed`; throw |
| Service initialization fails | Mark Service as FAILED; continue initializing other Services per dependency topology; if critical Service fails, escalate per Service criticality flag |
| Phase timeout | Treat as initialization failure; initiate rollback |

**Invariant:** `INV-INIT-001` — Partial initialization MUST be fully rolled back; no kernel-owned entity may remain in initialized state after initialization failure.

**Invariant:** `INV-INIT-002` — ConfigurationManager MUST be frozen before any Service initializes.

---

### 1.11 Shutdown Sequence

#### 1.11.1 Shutdown Entry Point

```typescript
async function shutdown(reason: ShutdownReason = 'graceful', error?: Error): Promise<void>
```

**Preconditions:**
- Kernel state = RUNNING or INITIALIZING (emergency shutdown)

**Postconditions:**
- Kernel state = TERMINATED
- All Services shut down
- All Core Managers shut down
- All Core Components shut down
- `KernelTerminated` event published

#### 1.11.2 Shutdown Phase Definitions

| Phase | Name | Entities | Order | Timeout |
|-------|------|----------|-------|---------|
| S9+ | **Service Shutdown** | All Services | Reverse dependency topology | Per Service |
| S8 | **Observability Flush** | ObservabilityManager | Sequential | 10s |
| S7 | **Workflows & Security** | WorkflowManager, SecurityManager | **Parallel** | 30s |
| S6 | **Context & Agents** | ContextManager, AgentManager | **Parallel** | 30s |
| S5 | **Tools & Storage** | ToolManager, StorageManager | **Parallel** | 30s |
| S4 | **Memory & LLM** | MemoryManager, LLMManager | **Parallel** | 30s |
| S3 | **Lifecycle Teardown** | LifecycleManager | Sequential | 5s |
| S2 | **Configuration Archive** | ConfigurationManager | Sequential | 5s |
| S1 | **Registry Teardown** | ServiceRegistry | Sequential | 5s |
| S0 | **EventBus Drain** | EventBus | Sequential | 10s |

#### 1.11.3 Shutdown Execution Algorithm

```pseudocode
function executeShutdown(reason, error?):
    state ← SHUTTING_DOWN
    publish KernelShutdownStarted({ reason, error })
    
    // Services first (reverse dependency order)
    servicePlan ← serviceRegistry.computeShutdownPlan()
    for batch in servicePlan.batches:
        await parallelWithTimeout(
            batch.map(s → s.shutdown()),
            serviceTimeout
        )
        await drainEventsForBatch(batch)
    
    // Core Managers (reverse initialization order)
    for phase in 8 down to 4:
        managers ← getCoreManagersForPhase(phase)
        await parallelWithTimeout(
            managers.map(m → m.shutdown()),
            phaseTimeout[phase]
        )
    
    // Core Components (reverse initialization order)
    for phase in 3 down to 0:
        component ← getCoreComponentForPhase(phase)
        await withTimeout(component.shutdown(), phaseTimeout[phase])
    
    state ← TERMINATED
    publish KernelTerminated({ errors: collectedErrors })
```

#### 1.11.4 Shutdown Failure Handling

| Failure Point | Behavior |
|---------------|----------|
| Service shutdown fails | Log error; continue shutting down other Services; collect errors for `KernelTerminated` payload |
| Core Manager shutdown fails | Log error; continue shutting down remaining managers; collect errors |
| Core Component shutdown fails | Log error; continue; collect errors (EventBus shutdown failure is critical) |
| Phase timeout | Force-terminate remaining entities in phase; collect timeout errors; proceed |

**Invariant:** `INV-SD-001` — Shutdown MUST proceed to completion regardless of individual entity failures (best-effort).

**Invariant:** `INV-SD-002` — EventBus MUST be the last Core Component to shut down (drains in-flight events).

**Invariant:** `INV-SD-003` — All collected errors MUST be included in `KernelTerminated` event payload.

---

### 1.12 Failure Handling and Recovery

#### 1.12.1 Failure Classification

| Class | Description | Kernel Response |
|-------|-------------|-----------------|
| **TRANSIENT** | Temporary condition (network blip, temporary resource exhaustion) | Retry with exponential backoff (max 3); if persistent → DEGRADED |
| **DEGRADED** | Component functional but impaired (reduced capacity, fallback mode) | Publish `ComponentDegraded`; continue RUNNING; alert via ObservabilityManager |
| **CRITICAL** | Component non-functional but kernel can continue (e.g., non-critical Service failure) | Publish `ComponentFailed`; isolate; attempt restart (max 2); if persistent → mark FAILED |
| **FATAL** | Kernel-integrity threatening (Core Component/Manager failure, invariant violation) | Initiate emergency SHUTTING_DOWN; publish `KernelFatalError`; terminate |

#### 1.12.2 Failure Detection

- **Health Checks** — LifecycleManager polls `healthCheck()` on all kernel-owned entities every 30s (configurable)
- **Event Heartbeats** — Core Components/Managers MUST publish `Heartbeat` event every 10s; missed 3 → DEGRADED
- **Exception Handling** — Uncaught exceptions in event handlers → TRANSIENT classification; rethrow → CRITICAL/FATAL per context

#### 1.12.3 Recovery Procedures

| Failure Class | Recovery Procedure |
|---------------|-------------------|
| TRANSIENT | Automatic retry via LifecycleManager; no Service disruption |
| DEGRADED | `ComponentDegraded` event → ObservabilityManager alert → Manual or automated remediation |
| CRITICAL (Service) | `ComponentFailed` event → ServiceRegistry marks FAILED → dependent Services notified → attempt Service restart |
| CRITICAL (Core Manager) | `CoreManagerFailed` event → LifecycleManager attempts re-initialization (max 2) → if fails → FATAL |
| FATAL | Emergency shutdown sequence (abbreviated: Services → Managers → Components); no re-initialization |

**Invariant:** `INV-FH-001` — Core Component failure is ALWAYS FATAL.

**Invariant:** `INV-FH-002` — Core Manager failure escalates to FATAL if re-initialization (max 2 attempts) fails.

**Invariant:** `INV-FH-003` — Service failure is CRITICAL unless marked `critical: true` in registration, then FATAL.

**Invariant:** `INV-FH-004` — Recovery MUST NOT violate initialization phase ordering or dependency constraints.

#### 1.12.4 Failure Event Contract

```typescript
interface KernelFailureEvent {
  type: 'ComponentDegraded' | 'ComponentFailed' | 'CoreManagerFailed' | 'KernelFatalError';
  timestamp: ISO8601;
  component: string;           // Name of affected component/manager/service
  classification: 'TRANSIENT' | 'DEGRADED' | 'CRITICAL' | 'FATAL';
  error: SerializedError;      // Error details
  recoveryAction: 'retry' | 'restart' | 'isolate' | 'shutdown';
  attemptNumber: number;       // For retry/restart tracking
}
```

---

### 1.13 Public Interfaces

#### 1.13.1 HermesKernel Class API

```typescript
class HermesKernel {
  // Singleton access
  static instance: HermesKernel | null;
  static getInstance(): HermesKernel;
  static create(config: KernelConfig): Promise<HermesKernel>;
  static reset(): void;  // ONLY for testing; PROHIBITED in production
  
  // State
  readonly state: KernelState;
  readonly config: Readonly<KernelConfig>;
  readonly startTime: Date | null;
  readonly readyTime: Date | null;
  
  // Core Component Accessors (read-only)
  readonly eventBus: EventBus;
  readonly serviceRegistry: ServiceRegistry;
  readonly configuration: ConfigurationManager;
  readonly lifecycle: LifecycleManager;
  
  // Core Manager Accessors (read-only) — EXACTLY NINE
  readonly memory: MemoryManager;
  readonly llm: LLMManager;
  readonly tools: ToolManager;
  readonly storage: StorageManager;
  readonly context: ContextManager;
  readonly agents: AgentManager;
  readonly workflows: WorkflowManager;
  readonly security: SecurityManager;
  readonly observability: ObservabilityManager;
  
  // Lifecycle
  initialize(config: KernelConfig): Promise<void>;
  shutdown(reason?: ShutdownReason, error?: Error): Promise<void>;
  
  // Health & Diagnostics
  healthCheck(): Promise<KernelHealthReport>;
  getMetrics(): KernelMetrics;
  getDiagnostics(): KernelDiagnostics;
  
  // Extension Points (controlled)
  registerService(service: BaseService): Promise<void>;
  unregisterService(serviceId: string): Promise<void>;
}
```

#### 1.13.2 Static Factory Method

```typescript
static async create(config: KernelConfig): Promise<HermesKernel> {
  if (HermesKernel.instance !== null) {
    throw new KernelAlreadyInitializedError();
  }
  const kernel = new HermesKernel(config);
  await kernel.initialize(config);
  HermesKernel.instance = kernel;
  return kernel;
}
```

**Invariant:** `INV-API-001` — `HermesKernel.instance` MUST be null until `create()` completes successfully.

**Invariant:** `INV-API-002` — `reset()` MUST ONLY be available in test environments (guarded by `NODE_ENV === 'test'`).

**Invariant:** `INV-API-003` — Direct constructor `new HermesKernel()` MUST be private; only `create()` permitted.

#### 1.13.3 KernelConfig Schema

```typescript
interface KernelConfig {
  // Required
  environment: 'development' | 'staging' | 'production';
  serviceDiscoveryPaths: string[];  // Paths to scan for Service registration
  
  // Optional (with defaults)
  initializationTimeouts?: Partial<PhaseTimeouts>;
  shutdownTimeouts?: Partial<PhaseTimeouts>;
  healthCheckIntervalMs?: number;   // Default: 30000
  heartbeatIntervalMs?: number;     // Default: 10000
  maxRecoveryAttempts?: number;     // Default: 2
  
  // Feature flags
  features?: {
    enableHotReload?: boolean;      // Default: false (dev only)
    enableProfiling?: boolean;      // Default: false
    strictConformance?: boolean;    // Default: true
  };
}
```

---

### 1.14 Extension Constraints

#### 1.14.1 Kernel Extension Prohibitions

| Constraint ID | Prohibition |
|---------------|-------------|
| EXT-001 | Adding, removing, or renaming Core Components (fixed at 4) |
| EXT-002 | Adding, removing, or renaming Core Managers (fixed at 9) |
| EXT-003 | Adding, removing, or renaming singleton accessors on HermesKernel |
| EXT-004 | Modifying initialization phase assignments for Core Components or Core Managers |
| EXT-005 | Modifying shutdown phase assignments for Core Components or Core Managers |
| EXT-006 | Bypassing EventBus for inter-component/manager communication |
| EXT-007 | Direct instantiation of Core Components or Core Managers outside kernel |
| EXT-008 | Modifying KernelState machine transitions |
| EXT-009 | Accessing Core Manager accessors before RUNNING state |
| EXT-010 | Mutating ConfigurationManager after freeze |

#### 1.14.2 Permitted Extension Points

| Extension Point | Mechanism | Governance |
|-----------------|-----------|------------|
| **Services** | Implement `BaseService`; register via `ServiceRegistry` | Open (Application Services); ARB review (Engineering Services) |
| **Core Manager Capabilities** | Declare in `capabilities` array; discovered via `ServiceRegistry` | Part 3 specification |
| **Event Types** | Define new event types; publish/subscribe via EventBus | Part 2 specification; schema registry |
| **Configuration Schema** | Extend via ConfigurationManager schema composition | Part 3 (ConfigurationManager) |
| **Health Check Extensions** | Override `healthCheck()` in Service/Core Manager | Part 3/Part 4 |
| **Observability Custom Metrics** | `observability.recordMetric()` | Part 3 (ObservabilityManager) |

---

### 1.15 Architectural Invariants

The following invariants are **mandatory** and verified by automated conformance tooling at phase transitions and periodically during RUNNING state.

#### 1.15.1 Structural Invariants

| Invariant | Description | Verification Point |
|-----------|-------------|-------------------|
| INV-STR-001 | Exactly one HermesKernel instance per process | `create()`, `reset()` |
| INV-STR-002 | Exactly 4 Core Components, exactly 9 Core Managers | Initialization, shutdown |
| INV-STR-003 | Core Component initialization phases 0–3, sequential | Phase execution |
| INV-STR-004 | Core Manager initialization phases 4–8, parallel within phase | Phase execution |
| INV-STR-005 | Shutdown order strictly reverse of initialization | Shutdown execution |
| INV-STR-006 | EventBus initializes first, shuts down last | Phase 0 / Phase S0 |
| INV-STR-007 | ConfigurationManager freezes before Service initialization | Post-Phase 3 |
| INV-STR-008 | All Core Components/Managers implement required interfaces | Construction |
| INV-STR-009 | No circular dependencies in initialization dependency graph | Spec validation |

#### 1.15.2 Runtime Invariants

| Invariant | Description | Verification Point |
|-----------|-------------|-------------------|
| INV-RT-001 | Kernel state machine follows prescribed transitions | Every state change |
| INV-RT-002 | All inter-component communication via EventBus (post-init) | EventBus instrumentation |
| INV-RT-003 | No direct references between Core Managers post-init | Heap analysis (periodic) |
| INV-RT-004 | ConfigurationManager remains frozen in RUNNING state | Write attempts throw |
| INV-RT-005 | All kernel-owned entities respond to healthCheck() | Periodic (30s default) |
| INV-RT-006 | Heartbeat events published by all Core Components/Managers | EventBus monitoring |
| INV-RT-007 | Service dependency topology acyclic | Registration, initialization |
| INV-RT-008 | ObservabilityManager receives metrics from all managers | Metric collection verification |

#### 1.15.3 Failure Invariants

| Invariant | Description | Verification Point |
|-----------|-------------|-------------------|
| INV-FL-001 | Partial initialization always rolled back | Initialization failure |
| INV-FL-002 | Shutdown proceeds to TERMINATED regardless of errors | Shutdown execution |
| INV-FL-003 | Core Component failure → FATAL → shutdown | Failure classification |
| INV-FL-004 | Core Manager failure → max 2 re-initialization → FATAL | Failure handling |
| INV-FL-005 | All failure events published to EventBus | Failure detection |

---

### 1.16 Conformance Requirements

#### 1.16.1 Static Conformance (Build-Time)

| Requirement ID | Check | Tooling |
|----------------|-------|---------|
| CONF-ST-001 | HermesKernel class has exactly 13 accessor properties (4 Core Components + 9 Core Managers) | TypeScript AST analysis |
| CONF-ST-002 | Core Component classes implement `ICoreComponent` | Interface verification |
| CONF-ST-003 | Core Manager classes implement `ICoreManager` | Interface verification |
| CONF-ST-004 | Initialization phase numbers match specification (0–3, 4–8) | Metadata validation |
| CONF-ST-005 | No public constructor on HermesKernel | Visibility analysis |
| CONF-ST-006 | `reset()` guarded by test environment check | AST pattern match |
| CONF-ST-007 | KernelConfig schema matches specification | JSON Schema validation |

#### 1.16.2 Dynamic Conformance (Runtime)

| Requirement ID | Check | Verification |
|----------------|-------|--------------|
| CONF-DY-001 | Kernel initializes through all phases in order | Integration test |
| CONF-DY-002 | Kernel shuts down through all phases in reverse order | Integration test |
| CONF-DY-003 | EventBus operational before any other component initializes | Phase 0 assertion |
| CONF-DY-004 | ConfigurationManager frozen before Service initialization | Post-Phase 3 assertion |
| CONF-DY-005 | All Core Managers accessible via singleton accessors in RUNNING state | Accessor test |
| CONF-DY-006 | Accessor access before RUNNING throws `KernelNotReadyError` | Error test |
| CONF-DY-007 | Failure injection triggers correct classification and recovery | Chaos test |
| CONF-DY-008 | All architectural invariants hold during RUNNING state | Periodic audit |

#### 1.16.3 Conformance Violation Handling

| Severity | Response |
|----------|----------|
| **Build-Time FAIL** | CI pipeline blocks; merge prohibited |
| **Runtime CRITICAL** | Kernel transitions to FATAL; emergency shutdown |
| **Runtime DEGRADED** | Alert via ObservabilityManager; remediation required within SLA |
| **Audit Finding** | ARB review; remediation plan within 5 business days |

---

### 1.17 Implementation vs. Architecture

| Aspect | Implementation (v0.1.x) | Architecture Target (v1.0) |
|--------|------------------------|---------------------------|
| Kernel Instance | Multiple instances possible | **Singleton enforced; second `create()` throws** |
| Core Components | 3–5 components, varying | **Exactly 4, fixed phases** |
| Core Managers | 6–11 managers, ad-hoc | **Exactly 9, fixed phases, fixed accessors** |
| Initialization | Ad-hoc, some parallel | **Phased: 0–3 sequential, 4–8 parallel-within-phase** |
| Shutdown | Best-effort, no order | **Strict reverse phase order with timeouts** |
| Configuration | Mutable at runtime | **Frozen after Phase 3; writes throw** |
| Failure Handling | Try-catch, inconsistent | **Classified: TRANSIENT/DEGRADED/CRITICAL/FATAL** |
| Recovery | Manual restart | **Automated retry (max 2); escalation defined** |
| State Machine | Implicit, 3 states | **Explicit 5-state FSM with events** |
| Conformance | None | **Static + Dynamic verification mandatory** |

---

### 1.18 Summary of Mandated Counts

| Category | Count | Reference |
|----------|-------|-----------|
| Core Components | **4** | §1.7.1 |
| Core Managers | **9** | §1.8.1 |
| Kernel State Machine States | **5** | §1.9.1 |
| Initialization Phases (Core) | **9** (0–8) | §1.10.2 |
| Shutdown Phases (Core) | **10** (S0–S9) | §1.11.2 |
| Singleton Accessors | **13** (4 CC + 9 CM) | §1.13.1 |
| Failure Classes | **4** | §1.12.1 |

---

**End of Part 1**

*This document is FROZEN. Any modification requires Architecture Review Board approval. All subsequent Parts MUST conform to this specification.*