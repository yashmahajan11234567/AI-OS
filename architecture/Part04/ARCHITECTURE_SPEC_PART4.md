# AI-OS Architecture Specification v1.0
## Part 4: Core Managers Architecture

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

### 4.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART4 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 4 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (5–N) MUST conform to Part 4. Part 4 MUST NOT contradict Part 0, Part 1, Part 2, or Part 3. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles), PART1 (kernel architecture), PART2 (event system), PART3 (core components), PART5 (engineering services), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis) |

**Conformance Requirement:** Every subsequent Part (5–N) of this specification MUST explicitly reference Part 4 sections for Core Manager terminology, interfaces, and conformance criteria. Any Part that contradicts Part 4 is non-conformant and MUST be revised.

---

### 4.1 Purpose

#### 4.1.1 Why Core Managers Exist

The nine Core Managers exist to provide the **operational governance layer** of the Hermes Kernel. They are not application services, not business logic, and not infrastructure primitives — they are the kernel's executive functions that translate architectural intent into runtime behavior.

Without Core Managers:
- No authoritative lifecycle control exists (LifecycleManager)
- No kernel state authority exists (StateManager)
- No persistent storage governance exists (StorageManager)
- No workflow execution governance exists (WorkflowManager)
- No security policy enforcement exists (SecurityManager)
- No capability discovery and routing exists (CapabilityManager)
- No resource accounting and quotas exist (ResourceManager)
- No health authority exists (HealthManager)
- No observability governance exists (ObservabilityManager)

#### 4.1.2 Architectural Role

Core Managers SHALL serve as the **exclusive operational authority** for their respective domains within the Hermes Kernel. They SHALL:

1. **Own** their domain state and decision logic
2. **Enforce** domain invariants without delegation
3. **Coordinate** with other managers only through defined contracts
4. **Expose** capabilities exclusively through the EventBus (Part 2) and ServiceRegistry (Part 3)
5. **Remain** stateless with respect to application logic — they manage kernel concerns only

#### 4.1.3 Relationship to Hermes Kernel

Per Part 1 (Kernel-as-Pure-Orchestrator), the Hermes Kernel SHALL compose Core Managers as its internal executive components. The Kernel SHALL:
- **Instantiate** all nine Core Managers during kernel initialization
- **Sequence** their initialization and shutdown per the dependency graph (Section 4.12)
- **Route** all inter-manager communication through the EventBus (Part 2)
- **Never** expose Core Manager internals to services or applications
- **Enforce** that Core Managers have no direct references to each other

#### 4.1.4 Relationship to Core Components

Per Part 3 (Core Components Architecture), Core Managers SHALL consume the four Core Components as infrastructure:

| Core Component | Consumers |
|----------------|-----------|
| **EventBus** | All nine Core Managers (mandatory) |
| **ServiceRegistry** | All nine Core Managers (registration, discovery) |
| **ConfigurationAuthority** | All nine Core Managers (configuration) |
| **IdentityProvider** | SecurityManager, CapabilityManager, ObservabilityManager (mandatory); others (as needed) |

Core Managers SHALL NOT bypass Core Components for communication, configuration, or identity.

#### 4.1.5 Design Principles

Core Managers SHALL adhere to the following principles derived from Part 0:

| Principle | Requirement |
|-----------|-------------|
| **Event-First** (Part 0 §1) | All manager-to-manager and manager-to-service communication SHALL occur via EventBus. Direct method calls between managers are FORBIDDEN. |
| **Kernel-as-Pure-Orchestrator** (Part 0 §2) | Managers SHALL contain no business logic. They SHALL orchestrate, validate, account, and enforce. |
| **Cross-Cutting Capabilities** (Part 0 §3) | Security, Observability, Health, Resources SHALL be enforced by dedicated managers, not embedded in others. |
| **Single Ownership** | Each kernel concern SHALL have exactly one owning manager. Shared ownership is FORBIDDEN. |
| **Explicit Contracts** | Every manager interaction SHALL be defined by an event contract or interface contract. Implicit coupling is FORBIDDEN. |
| **Failure Isolation** | A failure in one manager SHALL NOT cascade to others without explicit propagation through EventBus. |
| **Deterministic Lifecycle** | Initialization and shutdown order SHALL be fully determined by the dependency graph. |

#### 4.1.6 Non-Goals

Core Managers SHALL NOT:
- Implement application-level business logic
- Provide user-facing APIs directly
- Manage service-internal state
- Replace the EventBus, ServiceRegistry, ConfigurationAuthority, or IdentityProvider
- Couple to specific storage technologies, messaging systems, or cloud providers
- Perform work that belongs to Engineering Services (Part 5)

---

### 4.2 Core Manager Overview

#### 4.2.1 The Nine Core Managers

| Manager | Domain | Primary Responsibility |
|---------|--------|------------------------|
| **LifecycleManager** | Kernel lifecycle | Authoritative control over kernel initialization, phase execution, shutdown, rollback, and recovery coordination |
| **StateManager** | Kernel state | Authoritative control over kernel state transitions, snapshots, checkpoints, consistency, and recovery |
| **StorageManager** | Persistent storage | Governance of persistent storage, checkpoint storage, artifact storage, retention, compaction, integrity, and encryption coordination |
| **WorkflowManager** | Workflow execution | Governance of workflow lifecycle, scheduling, cancellation, timeouts, retry, nested workflows, and coordination |
| **SecurityManager** | Security policy | Authentication, authorization, policy enforcement, secret handling, audit coordination, identity, and trust boundaries |
| **CapabilityManager** | Capability registry | Capability registration, discovery, resolution, routing, version compatibility, facade interaction, provider selection, conflict resolution |
| **ResourceManager** | Resource accounting | CPU, memory, disk, network, GPU, LLM quota accounting, reservations, limits, backpressure |
| **HealthManager** | Health authority | Health monitoring, readiness, liveness, heartbeat, diagnostics, recovery recommendations, health aggregation |
| **ObservabilityManager** | Observability governance | Metrics, tracing, monitoring, dashboards, alerting, telemetry, diagnostics, audit integration |

#### 4.2.2 Manager Properties

Each Core Manager SHALL have the following defined properties:

| Property | Description |
|----------|-------------|
| **Ownership** | Exclusive domain of responsibility; no other manager may own this concern |
| **Initialization Phase** | Kernel initialization phase in which this manager becomes operational (Phase 1–5) |
| **Shutdown Phase** | Kernel shutdown phase in which this manager ceases operations (Phase 1–5, reverse order) |
| **Dependencies** | Other Core Managers whose operational state this manager requires |
| **Primary Responsibility** | Single-sentence statement of the manager's exclusive authority |

#### 4.2.3 Initialization Phases

The Hermes Kernel SHALL initialize Core Managers in five sequential phases:

| Phase | Name | Managers Initialized |
|-------|------|---------------------|
| **Phase 1** | Foundation | ConfigurationAuthority, IdentityProvider (Core Components), LifecycleManager |
| **Phase 2** | State & Storage | StateManager, StorageManager |
| **Phase 3** | Governance | SecurityManager, ResourceManager, HealthManager |
| **Phase 4** | Execution | CapabilityManager, WorkflowManager |
| **Phase 5** | Observability | ObservabilityManager |

**Rationale:** Foundation managers must exist before state/storage; governance managers need state/storage; execution managers need governance; observability observes all prior phases.

#### 4.2.4 Shutdown Phases

Shutdown SHALL proceed in strict reverse order of initialization:

| Phase | Name | Managers Shutdown |
|-------|------|-------------------|
| **Phase 1** | Observability | ObservabilityManager |
| **Phase 2** | Execution | WorkflowManager, CapabilityManager |
| **Phase 3** | Governance | HealthManager, ResourceManager, SecurityManager |
| **Phase 4** | State & Storage | StorageManager, StateManager |
| **Phase 5** | Foundation | LifecycleManager, IdentityProvider, ConfigurationAuthority |

#### 4.2.5 Dependency Matrix

The following matrix defines the **direct operational dependencies** between Core Managers. A dependency exists if Manager A requires Manager B to be operational before A can fulfill its responsibilities.

| Manager → | Lifecycle | State | Storage | Workflow | Security | Capability | Resource | Health | Observability |
|-----------|-----------|-------|---------|----------|----------|------------|----------|--------|---------------|
| **LifecycleManager** | — | — | — | — | — | — | — | — | — |
| **StateManager** | ✓ | — | ✓ | — | — | — | — | — | — |
| **StorageManager** | ✓ | ✓ | — | — | — | — | — | — | — |
| **WorkflowManager** | ✓ | ✓ | ✓ | — | ✓ | ✓ | ✓ | — | — |
| **SecurityManager** | ✓ | — | — | — | — | — | — | — | — |
| **CapabilityManager** | ✓ | ✓ | — | — | ✓ | — | — | — | — |
| **ResourceManager** | ✓ | ✓ | — | — | ✓ | — | — | — | — |
| **HealthManager** | ✓ | ✓ | — | — | — | — | ✓ | — | — |
| **ObservabilityManager** | ✓ | — | — | ✓ | ✓ | — | ✓ | ✓ | — |

**Legend:** ✓ = direct operational dependency; — = no direct dependency.

**Notes:**
- LifecycleManager has no Core Manager dependencies (depends only on Core Components)
- ObservabilityManager depends on WorkflowManager for workflow tracing correlation
- WorkflowManager has the most dependencies (reflects its coordination role)
- SecurityManager is a dependency for WorkflowManager, CapabilityManager, ResourceManager

#### 4.2.6 Ownership Boundaries

Each manager SHALL own exactly one primary domain. Ownership SHALL NOT be shared.

| Domain | Owner | Forbidden to Others |
|--------|-------|---------------------|
| Kernel lifecycle phases | LifecycleManager | All others |
| Kernel state machine | StateManager | All others |
| Persistent storage governance | StorageManager | All others |
| Workflow execution governance | WorkflowManager | All others |
| Security policy enforcement | SecurityManager | All others |
| Capability registry & routing | CapabilityManager | All others |
| Resource accounting & quotas | ResourceManager | All others |
| Health authority | HealthManager | All others |
| Observability governance | ObservabilityManager | All others |

---

### 4.3 LifecycleManager

#### 4.3.1 Purpose

LifecycleManager SHALL serve as the **sole authoritative controller** of the Hermes Kernel's operational lifecycle. It SHALL own the kernel lifecycle state machine, phase execution sequencing, initialization ordering, shutdown ordering, rollback coordination, and recovery coordination.

#### 4.3.2 Responsibilities

LifecycleManager SHALL be responsible for:

1. **Kernel Lifecycle Authority** — Exclusive ownership of the kernel lifecycle state machine (states: UNINITIALIZED, INITIALIZING, OPERATIONAL, DEGRADED, SHUTTING_DOWN, TERMINATED, ROLLBACK_IN_PROGRESS, RECOVERY_IN_PROGRESS)
2. **Phase Execution** — Execution of the five initialization phases and five shutdown phases in strict sequence
3. **Initialization Sequencing** — Determination and enforcement of manager initialization order per the dependency graph (Section 4.12)
4. **Shutdown Sequencing** — Determination and enforcement of manager shutdown order (strict reverse of initialization)
5. **Rollback** — Coordination of rollback to a prior consistent state upon initialization failure
6. **Recovery Coordination** — Coordination of kernel recovery from DEGRADED or failed states
7. **Dependency Validation** — Verification that all declared dependencies are satisfied before advancing phases
8. **Health Gate Enforcement** — Requirement that HealthManager reports READY before transitioning to OPERATIONAL
9. **Event Emission** — Emission of KernelLifecycleEvent for every state transition (Part 2 event contracts)

#### 4.3.3 Kernel Lifecycle Authority

LifecycleManager SHALL maintain the **single source of truth** for kernel lifecycle state. No other component SHALL maintain or mutate kernel lifecycle state.

The kernel lifecycle state machine SHALL define the following states:

| State | Description | Valid Transitions |
|-------|-------------|-------------------|
| **UNINITIALIZED** | Kernel process started, no managers instantiated | → INITIALIZING |
| **INITIALIZING** | Phase 1–5 execution in progress | → OPERATIONAL, → ROLLBACK_IN_PROGRESS, → TERMINATED |
| **OPERATIONAL** | All managers healthy, kernel serving requests | → DEGRADED, → SHUTTING_DOWN |
| **DEGRADED** | One or more managers unhealthy, reduced functionality | → OPERATIONAL, → RECOVERY_IN_PROGRESS, → SHUTTING_DOWN |
| **SHUTTING_DOWN** | Phase 1–5 shutdown in progress | → TERMINATED |
| **TERMINATED** | Kernel stopped, all managers shut down | (terminal) |
| **ROLLBACK_IN_PROGRESS** | Rolling back to prior checkpoint | → UNINITIALIZED, → TERMINATED |
| **RECOVERY_IN_PROGRESS** | Attempting recovery from DEGRADED | → OPERATIONAL, → DEGRADED, → SHUTTING_DOWN |

**Invariant:** State transitions SHALL be atomic and SHALL emit KernelLifecycleEvent before and after transition.

#### 4.3.4 Phase Execution

LifecycleManager SHALL execute each phase as follows:

1. **Pre-phase validation** — Verify all dependencies for managers in this phase are satisfied
2. **Manager instantiation** — Instantiate each manager in the phase (order within phase: alphabetical by manager name)
3. **Manager initialization** — Invoke each manager's `initialize()` contract
4. **Post-phase validation** — Verify all managers in phase report READY via HealthManager
5. **Phase completion event** — Emit KernelPhaseCompletedEvent

**Failure during phase execution** SHALL trigger immediate rollback coordination (Section 4.3.6).

#### 4.3.5 Initialization Sequencing

Initialization sequence SHALL be deterministic and derived solely from the dependency graph (Section 4.2.5). LifecycleManager SHALL:

1. Compute topological sort of the dependency graph
2. Assign phases per Section 4.2.3
3. Execute phases sequentially
4. Never skip, reorder, or parallelize phases

**Invariant:** The initialization sequence SHALL be identical across all kernel starts given the same manager set.

#### 4.3.6 Shutdown Sequencing

Shutdown sequence SHALL be the strict reverse of initialization. LifecycleManager SHALL:

1. Transition kernel state to SHUTTING_DOWN
2. Execute shutdown phases per Section 4.2.4
3. For each manager in phase: invoke `shutdown()`, await completion, verify termination
4. Emit KernelPhaseCompletedEvent for each phase
5. Transition to TERMINATED only after all managers confirm shutdown

**Invariant:** No manager SHALL be shut down before all managers that depend on it have been shut down.

#### 4.3.7 Rollback

Upon initialization failure (any manager fails to initialize or reports NOT_READY), LifecycleManager SHALL:

1. Transition kernel state to ROLLBACK_IN_PROGRESS
2. Invoke `shutdown()` on all managers initialized in the current phase (reverse order)
3. Invoke `shutdown()` on all managers from prior phases (reverse phase order, reverse order within phase)
4. Invoke StorageManager `rollback()` to prior consistent checkpoint
5. Invoke StateManager `restore()` to prior consistent state
6. Transition to UNINITIALIZED or TERMINATED based on configuration

**Rollback SHALL be idempotent** — repeating rollback SHALL produce the same end state.

#### 4.3.8 Recovery Coordination

When HealthManager reports a manager as UNHEALTHY, LifecycleManager SHALL:

1. Transition kernel state to DEGRADED (if not already)
2. Emit KernelDegradedEvent with affected manager list
3. Coordinate with HealthManager on recovery strategy
4. If recovery initiated: transition to RECOVERY_IN_PROGRESS
5. Upon recovery completion: transition to OPERATIONAL or remain DEGRADED

Recovery strategies SHALL be defined per-manager in HealthManager (Section 4.10).

#### 4.3.9 Dependency Validation

LifecycleManager SHALL validate dependencies at two points:

1. **Static validation** (pre-initialization): Verify dependency graph is acyclic and all declared dependencies exist
2. **Runtime validation** (per phase): Verify each dependency manager reports READY via HealthManager before initializing dependents

**Failure** of runtime validation SHALL trigger rollback.

#### 4.3.10 Interaction Contracts

LifecycleManager SHALL interact with other components exclusively through:

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: KernelLifecycleEvent, KernelPhaseCompletedEvent, KernelDegradedEvent, KernelRecoveryEvent. Consumes: ManagerInitializedEvent, ManagerShutdownEvent, ManagerHealthChangedEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.lifecycle` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.lifecycle.*` configuration |
| **HealthManager** | Inbound | Queries manager readiness via `health.readiness(manager)` |
| **StateManager** | Outbound | Invokes `state.transition(targetState)` |
| **StorageManager** | Outbound | Invokes `storage.rollback(checkpointId)` |

**Forbidden:** Direct method calls to other Core Managers. All coordination SHALL occur via EventBus.

#### 4.3.11 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Manager initialization timeout | Rollback |
| Manager health check failure during init | Rollback |
| Dependency validation failure | Rollback |
| StateManager transition failure | Rollback |
| StorageManager rollback failure | Terminate kernel (unrecoverable) |
| HealthManager unavailable | Remain in INITIALIZING, retry with backoff |
| EventBus unavailable | Terminate kernel (unrecoverable) |

**Invariant:** LifecycleManager SHALL never leave the kernel in an undefined state. Every failure path leads to a defined lifecycle state.

#### 4.3.12 Extension Rules

**Extension Points** (MAY be extended):
- Custom phase definitions via configuration (Phase 1.5, 2.5, etc.)
- Custom recovery strategies per manager type
- Custom health gate predicates

**Extension Constraints** (MUST be preserved):
- Phase ordering SHALL remain topologically sorted
- Kernel lifecycle state machine SHALL NOT be modified
- Rollback idempotency SHALL be preserved
- EventBus as sole communication mechanism SHALL be preserved

**Forbidden Extensions:**
- Direct manager-to-manager calls during lifecycle operations
- Bypassing HealthManager readiness checks
- Modifying another manager's lifecycle state

#### 4.3.13 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single lifecycle authority** | No other component emits KernelLifecycleEvent |
| **Deterministic phase order** | Given same manager set, initialization sequence is identical across runs |
| **Rollback idempotency** | Repeated rollback from same failure point produces identical end state |
| **No cyclic dependencies** | Dependency graph validation passes statically |
| **Health gate enforcement** | Kernel never reaches OPERATIONAL without HealthManager READY for all managers |
| **EventBus exclusivity** | No direct inter-manager calls observed in lifecycle operations |

#### 4.3.14 Conformance

A LifecycleManager implementation SHALL be conformant IFF:

1. **Static:** Passes dependency graph validation, lifecycle state machine validation, event contract validation
2. **Runtime:** Completes initialization to OPERATIONAL within configured timeout; rollback completes within configured timeout; all state transitions emit events
3. **Architectural:** No direct references to other Core Managers; all communication via EventBus; ownership boundaries respected

---

### 4.4 StateManager

#### 4.4.1 Purpose

StateManager SHALL serve as the **sole authoritative controller** of the Hermes Kernel's runtime state. It SHALL own the kernel state machine, state transitions, snapshots, checkpoint integration, consistency guarantees, and state recovery.

#### 4.4.2 Responsibilities

StateManager SHALL be responsible for:

1. **Kernel State Authority** — Exclusive ownership of the kernel state machine (distinct from lifecycle state; includes: runtime configuration, active workflows, resource allocations, capability bindings, security contexts)
2. **State Transitions** — Validation, authorization, and execution of all kernel state mutations
3. **Snapshots** — Creation, validation, and management of point-in-time kernel state snapshots
4. **Checkpoint Integration** — Coordination with StorageManager for durable checkpoint persistence
5. **Consistency Guarantees** — Enforcement of state consistency invariants (serializability, isolation, durability)
6. **Recovery** — Restoration of kernel state from checkpoints/snapshots

#### 4.4.3 Kernel State Authority

StateManager SHALL maintain the **single source of truth** for kernel runtime state. Kernel runtime state SHALL include:

| State Category | Examples |
|----------------|----------|
| **Runtime Configuration** | Effective configuration after merges, overrides, feature flags |
| **Active Workflows** | Workflow instances, execution state, correlations |
| **Resource Allocations** | Current reservations, limits, usage attribution |
| **Capability Bindings** | Active provider-facade bindings, routing rules |
| **Security Contexts** | Active principals, sessions, policy decisions |
| **Health State** | Aggregated health, per-manager status |

**Invariant:** No other manager or service SHALL maintain authoritative kernel runtime state. All state mutations SHALL go through StateManager.

#### 4.4.4 State Transitions

StateManager SHALL govern state transitions through a **transition protocol**:

1. **Request** — Caller (manager or service via EventBus) emits StateTransitionRequestEvent with: target state, preconditions, expected postconditions
2. **Validation** — StateManager validates preconditions, authorization (via SecurityManager), resource availability (via ResourceManager), consistency constraints
3. **Authorization** — SecurityManager evaluates policy; denial emits StateTransitionDeniedEvent
4. **Execution** — StateManager applies transition atomically (or marks PENDING for async)
5. **Verification** — StateManager verifies postconditions
6. **Commit** — StateManager emits StateTransitionCommittedEvent with new state hash
7. **Persistence** — StateManager requests StorageManager checkpoint (async)

**Invariant:** All state transitions SHALL be serialized. Concurrent transitions SHALL be queued and executed in request order.

#### 4.4.5 Snapshots

StateManager SHALL support snapshot operations:

| Operation | Description |
|-----------|-------------|
| **Create Snapshot** | Capture complete kernel state at a point in time; assign unique snapshot ID; compute integrity hash |
| **Validate Snapshot** | Verify snapshot integrity, completeness, consistency |
| **List Snapshots** | Enumerate available snapshots with metadata (timestamp, state hash, size, tags) |
| **Delete Snapshot** | Remove snapshot (subject to retention policy) |
| **Diff Snapshots** | Compute semantic diff between two snapshots |

**Snapshot Triggers:**
- Manual (admin request)
- Scheduled (configured interval)
- Pre-transition (before risky operations)
- Post-recovery (after successful recovery)
- Checkpoint coordination (StorageManager request)

#### 4.4.6 Checkpoint Integration

StateManager SHALL coordinate with StorageManager for durable checkpoints:

1. StateManager determines checkpoint necessity (configuration, snapshot trigger, recovery prep)
2. StateManager serializes kernel state to canonical format
3. StateManager invokes StorageManager `checkpoint.write(stateBlob, metadata)`
4. StorageManager persists and returns checkpoint reference
5. StateManager records checkpoint reference in state metadata

**Invariant:** Checkpoint write SHALL be acknowledged before StateTransitionCommittedEvent for transitions requiring durability.

#### 4.4.7 Consistency Guarantees

StateManager SHALL enforce the following consistency model:

| Guarantee | Scope | Enforcement |
|-----------|-------|-------------|
| **Serializability** | All state transitions | Single-threaded transition execution; queue with FIFO ordering |
| **Isolation** | Concurrent readers | Readers see committed state only; snapshot isolation for long reads |
| **Durability** | Committed transitions | Checkpoint acknowledgment before commit event (configurable per transition class) |
| **Atomicity** | Multi-part transitions | All-or-nothing; compensation on partial failure |
| **Linearizability** | State reads | Reads reflect latest committed transition |

**Consistency Classes** (configurable per state category):
- **STRONG** — Full ACID; checkpoint before commit; linearizable reads
- **EVENTUAL** — Async checkpoint; snapshot isolation reads; higher throughput
- **EPHEMERAL** — No checkpoint; in-memory only; lost on restart

#### 4.4.8 Recovery

StateManager SHALL support recovery modes:

| Mode | Trigger | Procedure |
|------|---------|-----------|
| **Full Restore** | Kernel restart, rollback | Load latest valid checkpoint from StorageManager; validate integrity; replay transitions since checkpoint (if event log available); verify end state |
| **Point-in-Time** | Admin request, corruption | Load specified snapshot; validate; transition kernel to restored state |
| **Partial Restore** | Single category corruption | Restore only affected state category; validate cross-category consistency |
| **Forward Recovery** | Checkpoint gap | Replay EventBus event log from last checkpoint to current |

**Recovery Validation:** After any recovery, StateManager SHALL:
1. Validate all state invariants
2. Verify cross-manager consistency via HealthManager
3. Emit StateRecoveryCompletedEvent or StateRecoveryFailedEvent

#### 4.4.9 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: StateTransitionRequestedEvent, StateTransitionCommittedEvent, StateTransitionDeniedEvent, StateSnapshotCreatedEvent, StateRecoveryCompletedEvent. Consumes: StateTransitionRequestEvent, ManagerInitializedEvent, ManagerHealthChangedEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.state` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.state.*` configuration |
| **StorageManager** | Outbound | Invokes `checkpoint.write()`, `checkpoint.read()`, `checkpoint.list()` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, action, resource)` |
| **ResourceManager** | Outbound | Invokes `resources.checkAvailability(resources)` |
| **HealthManager** | Outbound | Invokes `health.readiness(manager)` |

**Forbidden:** Direct state mutations by other managers. All state changes SHALL go through StateTransitionRequestEvent.

#### 4.4.10 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Transition validation failure | Emit StateTransitionDeniedEvent; state unchanged |
| Authorization failure | Emit StateTransitionDeniedEvent; state unchanged |
| Resource unavailable | Queue transition; emit StateTransitionQueuedEvent; retry on resource release |
| Checkpoint write failure | If STRONG: deny transition; if EVENTUAL: emit StateCheckpointDeferredEvent; retry async |
| Checkpoint read failure (recovery) | Try next older checkpoint; if none: emit StateRecoveryFailedEvent |
| State corruption detected | Emit StateCorruptionDetectedEvent; transition kernel to DEGRADED; initiate recovery |
| Concurrent transition conflict | Queue later transition; first wins |

**Invariant:** StateManager SHALL never silently drop a transition request. Every request receives a definitive response event.

#### 4.4.11 Extension Rules

**Extension Points** (MAY be extended):
- Custom state categories with dedicated consistency classes
- Custom transition validators (plugged via configuration)
- Custom snapshot serialization formats
- Custom recovery replay strategies

**Extension Constraints** (MUST be preserved):
- Single state authority SHALL be preserved
- Transition serialization SHALL be preserved
- Consistency guarantees SHALL not be weakened
- EventBus as sole mutation interface SHALL be preserved

**Forbidden Extensions:**
- Direct state access by other managers
- Bypassing transition protocol
- Weakening durability for STRONG consistency class
- Adding state categories without consistency class assignment

#### 4.4.12 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single state authority** | No other component emits StateTransitionCommittedEvent |
| **Transition serialization** | Under concurrent load, transitions execute in request order (verified by sequence numbers) |
| **Snapshot integrity** | Every snapshot validates its own integrity hash on read |
| **Checkpoint durability** | STRONG transitions have checkpoint reference in commit event |
| **Recovery completeness** | After recovery, all state invariants pass validation |
| **No silent drops** | Every StateTransitionRequestEvent produces exactly one response event |

#### 4.4.13 Conformance

A StateManager implementation SHALL be conformant IFF:

1. **Static:** Passes state machine validation, consistency class validation, event contract validation
2. **Runtime:** All transitions serialize; snapshots validate; checkpoints acknowledge per consistency class; recovery restores valid state
3. **Architectural:** No direct state mutations by others; all mutations via EventBus; ownership boundaries respected

---

### 4.5 StorageManager

#### 4.5.1 Purpose

StorageManager SHALL serve as the **sole governance authority** for all persistent storage within the Hermes Kernel. It SHALL own persistent storage provisioning, checkpoint storage, artifact storage, retention policies, compaction, integrity verification, encryption coordination, and storage recovery.

#### 4.5.2 Responsibilities

StorageManager SHALL be responsible for:

1. **Persistent Storage Governance** — Provisioning, configuration, and lifecycle of all persistent storage volumes
2. **Checkpoint Storage** — Durable storage of StateManager checkpoints with integrity and ordering guarantees
3. **Artifact Storage** — Storage of workflow artifacts, logs, traces, and diagnostic bundles
4. **Retention Policies** — Enforcement of TTL, count, and size-based retention for all stored data
5. **Compaction** — Reclamation of space from deleted/expired data; deduplication
6. **Integrity Verification** — Continuous and on-demand verification of data integrity
7. **Encryption Coordination** — Coordination with SecurityManager for encryption-at-rest keys and policies
8. **Storage Recovery** — Reconstruction of storage state after failure or corruption

#### 4.5.3 Persistent Storage

StorageManager SHALL manage storage **namespaces** (logical partitions):

| Namespace | Purpose | Retention | Encryption |
|-----------|---------|-----------|------------|
| **checkpoints** | StateManager checkpoints | Configurable (default: 30 days or N generations) | Mandatory |
| **artifacts** | Workflow outputs, logs, traces | Per-workflow TTL (default: 90 days) | Optional (per workflow) |
| **diagnostics** | Health dumps, core dumps, profiles | Short TTL (default: 7 days) | Optional |
| **audit** | Security audit logs | Long TTL (default: 7 years) | Mandatory |
| **configuration** | ConfigurationAuthority backups | Versioned (keep all) | Mandatory |
| **identity** | IdentityProvider key material | Indefinite | Mandatory (HSM-backed) |

**Invariant:** Each namespace SHALL have explicitly configured retention, encryption, and access policy. No namespace SHALL use defaults implicitly.

#### 4.5.4 Checkpoint Storage

StorageManager SHALL provide checkpoint storage with:

| Property | Guarantee |
|----------|-----------|
| **Ordering** | Checkpoints written in sequence order; readers see monotonic sequence |
| **Atomicity** | Checkpoint write is all-or-nothing; partial writes are rolled back |
| **Integrity** | Each checkpoint has cryptographic hash verified on read |
| **Isolation** | Checkpoint reads do not block writes; snapshot isolation |
| **Pruning** | Automatic pruning per retention policy; never prune latest N (configurable) |

**Checkpoint Write Protocol:**
1. StateManager invokes `checkpoint.write(blob, metadata)`
2. StorageManager validates metadata, assigns sequence number
3. StorageManager writes to temporary location, computes hash
4. StorageManager atomically moves to final location (or equivalent atomic operation)
5. StorageManager updates checkpoint index
6. StorageManager returns checkpoint reference (sequence, hash, location)

#### 4.5.5 Artifact Storage

StorageManager SHALL store workflow artifacts with:

| Property | Guarantee |
|----------|-----------|
| **Addressability** | Artifacts referenced by (workflowId, stepId, artifactName, version) |
| **Streaming** | Support for streaming write/read of large artifacts |
| **Metadata** | Content-type, size, hash, creator, timestamps, tags |
| **Lifecycle** | Auto-expire per workflow retention policy; manual pin to prevent expiry |
| **Lineage** | Track artifact derivation (input artifacts → transformation → output artifacts) |

#### 4.5.6 Retention

StorageManager SHALL enforce retention policies per namespace:

| Policy Type | Enforcement |
|-------------|-------------|
| **TTL** | Delete objects older than configured duration |
| **Generation Count** | Keep latest N checkpoints/snapshots |
| **Size Quota** | Enforce per-namespace size limit; evict oldest (LRU) when exceeded |
| **Legal Hold** | Override retention for flagged objects (audit, investigation) |

**Retention Execution:** Background compaction job SHALL evaluate and enforce policies. Deletion SHALL be logged to audit namespace.

#### 4.5.7 Compaction

StorageManager SHALL perform compaction to reclaim space:

| Compaction Type | Trigger | Scope |
|-----------------|---------|-------|
| **Garbage Collection** | Scheduled, size threshold | Reclaim space from deleted/expired objects |
| **Deduplication** | Scheduled, write-time | Identify and deduplicate identical content (content-addressed) |
| **Index Rebuild** | Corruption detection, schema change | Rebuild checkpoint/artifact indexes |
| **Tier Migration** | Age threshold, access pattern | Move cold data to cheaper tier (if multi-tier configured) |

**Invariant:** Compaction SHALL NOT block reads or writes. Compaction SHALL be interruptible and resumable.

#### 4.5.8 Integrity

StorageManager SHALL verify integrity at multiple levels:

| Level | When | Method |
|-------|------|--------|
| **Write-time** | Every write | Compute and store cryptographic hash (SHA-256 minimum) |
| **Read-time** | Every read (configurable) | Verify hash matches stored value |
| **Background** | Scheduled (default: daily) | Scan all objects; verify hashes; report corruption |
| **Checkpoint** | Every checkpoint write | Full verification of checkpoint chain integrity |
| **Recovery** | Every recovery | Validate entire namespace before restore |

**Corruption Response:** On corruption detection, StorageManager SHALL:
1. Quarantine affected object(s)
2. Emit StorageCorruptionDetectedEvent
3. Attempt repair from replica (if replicated)
4. If unrecoverable: notify StateManager for checkpoint fallback

#### 4.5.9 Encryption Interaction

StorageManager SHALL coordinate with SecurityManager for encryption:

| Aspect | Responsibility |
|--------|----------------|
| **Key Management** | SecurityManager generates, rotates, revokes keys |
| **Key Access** | StorageManager requests decryption key per namespace per session |
| **Key Rotation** | SecurityManager initiates; StorageManager rewrites affected objects (async) |
| **HSM Integration** | SecurityManager mediates HSM operations; StorageManager never accesses HSM directly |
| **Algorithm** | SecurityManager dictates; StorageManager implements |

**Invariant:** StorageManager SHALL never persist plaintext keys. All encryption operations SHALL use SecurityManager-provided key handles.

#### 4.5.10 Recovery

StorageManager SHALL support storage recovery modes:

| Mode | Trigger | Procedure |
|------|---------|-----------|
| **Namespace Rebuild** | Index corruption | Re-scan namespace; rebuild index from object metadata |
| **Checkpoint Chain Repair** | Missing checkpoint | Verify adjacent checkpoints; reconstruct gap from event log if possible |
| **Tier Restoration** | Tier failure | Restore from backup tier; validate integrity |
| **Full Disaster Recovery** | Catastrophic loss | Restore from offsite backup; validate all namespaces |

#### 4.5.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: StorageCheckpointWrittenEvent, StorageArtifactStoredEvent, StorageRetentionAppliedEvent, StorageCorruptionDetectedEvent, StorageCompactionCompletedEvent. Consumes: StorageCheckpointRequestEvent, StorageArtifactRequestEvent, ManagerHealthChangedEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.storage` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.storage.*` configuration |
| **StateManager** | Inbound | Receives `checkpoint.write()`, `checkpoint.read()`, `checkpoint.list()` |
| **WorkflowManager** | Inbound | Receives `artifact.store()`, `artifact.retrieve()` |
| **SecurityManager** | Outbound | Invokes `security.getKeyHandle(namespace)`, `security.rotateKey(namespace)` |
| **HealthManager** | Outbound | Invokes `health.readiness(storage)`; reports storage health |
| **ObservabilityManager** | Outbound | Emits storage metrics (capacity, usage, latency, errors) |

**Forbidden:** Direct storage access by other managers. All storage operations SHALL go through StorageManager.

#### 4.5.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Write failure (disk full) | Emit StorageWriteFailedEvent; retry with backoff; trigger compaction |
| Write failure (hardware error) | Quarantine volume; failover to replica; emit StorageVolumeFailedEvent |
| Read failure (corruption) | Attempt repair from replica; if fails: emit StorageReadFailedEvent |
| Retention policy violation | Emits StorageRetentionViolationEvent; emergency compaction |
| Encryption key unavailable | Queue operation; emit StorageKeyUnavailableEvent; retry |
| Background compaction failure | Retry; if persistent: emit StorageCompactionFailedEvent; alert |

**Invariant:** StorageManager SHALL never silently lose acknowledged writes. Every acknowledged write SHALL be durable per namespace policy.

#### 4.5.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom storage backends (S3, GCS, Azure Blob, local, distributed)
- Custom retention policy evaluators
- Custom compaction algorithms
- Custom integrity verification methods
- Custom tiering policies

**Extension Constraints** (MUST be preserved):
- Namespace isolation SHALL be preserved
- Checkpoint ordering and atomicity SHALL be preserved
- Integrity verification SHALL not be disabled
- Encryption coordination with SecurityManager SHALL be preserved
- EventBus as sole interface SHALL be preserved

**Forbidden Extensions:**
- Direct backend access by other managers
- Bypassing retention policies
- Storing plaintext in encrypted namespaces
- Modifying checkpoint sequence order

#### 4.5.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Namespace isolation** | No cross-namespace object access without explicit policy |
| **Checkpoint atomicity** | No partial checkpoints visible to readers |
| **Integrity verification** | 100% of objects have verified hash on background scan |
| **Retention compliance** | No object exceeds its retention policy (except legal hold) |
| **Encryption compliance** | All encrypted-namespace objects encrypted at rest |
| **No silent data loss** | Every acknowledged write recoverable after single-node failure |

#### 4.5.15 Conformance

A StorageManager implementation SHALL be conformant IFF:

1. **Static:** Passes namespace configuration validation, retention policy validation, encryption policy validation
2. **Runtime:** Checkpoints write atomically; artifacts store/retrieve correctly; retention enforced; integrity verified; encryption coordinated
3. **Architectural:** No direct storage access by others; all operations via EventBus; ownership boundaries respected

---

**End of Part 4 (Sections 4.1–4.5)**
### 4.6 WorkflowManager

#### 4.6.1 Purpose

WorkflowManager SHALL serve as the **sole governance authority** for workflow execution within the Hermes Kernel. It SHALL own workflow lifecycle, scheduling, cancellation, timeouts, retry, nested workflows, and coordination.

#### 4.6.2 Responsibilities

WorkflowManager SHALL be responsible for:

1. **Workflow Execution Governance** — Authoritative control over workflow instance lifecycle from submission to completion
2. **Workflow Lifecycle** — State machine for workflow instances (PENDING, SCHEDULED, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED, COMPENSATING)
3. **Scheduling** — Placement of workflow steps on available capacity; coordination with ResourceManager
4. **Cancellation** — Cooperative and forced cancellation of running workflows
5. **Timeouts** — Enforcement of step-level and workflow-level timeouts
6. **Retry** — Configurable retry policies with backoff, jitter, and circuit breaking
7. **Nested Workflows** — Management of parent-child workflow relationships, isolation, and propagation
8. **Coordination** — Synchronization, branching, joining, and event-driven continuation

#### 4.6.3 Workflow Execution

WorkflowManager SHALL execute workflows as **directed acyclic graphs (DAGs)** of steps.

**Workflow Definition:**
- Steps with explicit dependencies (edges)
- Each step: capability invocation, inline logic, or sub-workflow
- Resource requirements per step (CPU, memory, GPU, LLM quota)
- Timeout per step and workflow-level
- Retry policy per step
- Compensation (saga) actions for rollback

**Execution Model:**
1. Workflow submitted via EventBus (WorkflowSubmitEvent)
2. WorkflowManager validates definition, resolves capabilities (CapabilityManager), checks resources (ResourceManager), authorizes (SecurityManager)
3. WorkflowManager creates workflow instance, assigns ID, emits WorkflowCreatedEvent
4. Scheduler places ready steps (dependencies met) on execution queue
5. Step execution: invoke capability via CapabilityManager; capture result/artifact
6. On step completion: evaluate downstream readiness; schedule next steps
7. On workflow completion: emit WorkflowCompletedEvent; store artifacts via StorageManager
8. On failure: execute compensation; emit WorkflowFailedEvent

**Invariant:** WorkflowManager SHALL NOT execute step logic directly. All step execution SHALL be via CapabilityManager resolution.

#### 4.6.4 Workflow Lifecycle

Workflow instance state machine:

| State | Description | Valid Transitions |
|-------|-------------|-------------------|
| **PENDING** | Submitted, awaiting validation | → SCHEDULED, → CANCELLED |
| **SCHEDULED** | Validated, awaiting resources | → RUNNING, → CANCELLED |
| **RUNNING** | At least one step executing | → PAUSED, → COMPLETED, → FAILED, → CANCELLED |
| **PAUSED** | Suspended (admin, resource pressure) | → RUNNING, → CANCELLED |
| **COMPLETED** | All steps succeeded | (terminal) |
| **FAILED** | Step failed, compensation done | → CANCELLED (terminal) |
| **CANCELLED** | Terminated before completion | (terminal) |
| **COMPENSATING** | Executing saga compensation | → FAILED, → CANCELLED |

**Invariant:** Every state transition SHALL emit WorkflowStateChangedEvent with timestamp, previous state, new state, and reason.

#### 4.6.5 Scheduling

WorkflowManager SHALL schedule steps based on:

1. **Readiness** — All upstream dependencies completed successfully
2. **Resources** — ResourceManager confirms availability for step requirements
3. **Priority** — Workflow priority (configurable per submission)
4. **Fairness** — Prevent starvation (weighted fair queuing across tenants/workflows)
5. **Affinity** — Placement preferences (GPU, zone, data locality)

**Scheduling Decisions** SHALL be logged for observability.

#### 4.6.6 Cancellation

WorkflowManager SHALL support two cancellation modes:

| Mode | Behavior |
|------|----------|
| **Cooperative** | Emit CancellationRequestedEvent to running steps; steps check cancellation token; graceful shutdown; execute compensation |
| **Forced** | After grace period (configurable): terminate step execution; force resource release; execute compensation |

**Invariant:** Cancellation SHALL always execute compensation actions for completed steps (saga pattern).

#### 4.6.7 Timeouts

WorkflowManager SHALL enforce timeouts at two levels:

| Level | Scope | Enforcement |
|-------|-------|-------------|
| **Step Timeout** | Individual step execution | Hard limit; on expiry: mark step failed; trigger retry or compensation |
| **Workflow Timeout** | Entire workflow wall-clock | Hard limit; on expiry: initiate cancellation (cooperative then forced) |

**Timeout Configuration:** Per-step and per-workflow; inheritable from workflow template; overrideable at submission.

#### 4.6.8 Retry

WorkflowManager SHALL support configurable retry policies:

| Policy Parameter | Description |
|------------------|-------------|
| **Max Attempts** | Maximum retry count (default: 3) |
| **Backoff Strategy** | Exponential, linear, fixed (default: exponential) |
| **Base Delay** | Initial delay (default: 1s) |
| **Max Delay** | Cap on delay (default: 60s) |
| **Jitter** | Randomization factor (default: 0.1) |
| **Retryable Errors** | Error classification for retry (default: transient only) |
| **Circuit Breaker** | Open after N failures; half-open probe; close on success |

**Retry Execution:** Retries SHALL be scheduled as new step attempts; original attempt marked RETRYING.

#### 4.6.9 Nested Workflows

WorkflowManager SHALL support parent-child workflow relationships:

| Aspect | Behavior |
|--------|----------|
| **Invocation** | Parent step invokes sub-workflow via CapabilityManager (capability type: workflow) |
| **Isolation** | Child has own state machine, resources, timeout; failure does not auto-fail parent |
| **Propagation** | Parent may configure: wait for child, fire-and-forget, rollback on child failure |
| **Context** | Child inherits parent's security context (subject to policy); own resource allocation |
| **Observability** | Correlation ID links parent and child traces |

**Invariant:** Nested workflow depth SHALL be bounded (configurable max, default: 10).

#### 4.6.10 Coordination

WorkflowManager SHALL provide coordination primitives:

| Primitive | Description |
|-----------|-------------|
| **Join** | Wait for multiple parallel branches to complete |
| **Branch** | Split into parallel execution paths |
| **Signal** | Event-driven continuation (wait for external event) |
| **Barrier** | Synchronize multiple workflow instances |
| **Aggregate** | Collect results from dynamic fan-out |

**Event-Driven Continuation:** Steps may emit WaitForEventEvent; WorkflowManager suspends workflow until matching EventBus event arrives.

#### 4.6.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: WorkflowCreatedEvent, WorkflowStateChangedEvent, WorkflowStepStartedEvent, WorkflowStepCompletedEvent, WorkflowCompletedEvent, WorkflowFailedEvent, WorkflowCancelledEvent. Consumes: WorkflowSubmitEvent, WorkflowCancelEvent, WorkflowPauseEvent, WorkflowResumeEvent, CapabilityInvocationResultEvent, ResourceReleasedEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.workflow` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.workflow.*` configuration |
| **CapabilityManager** | Outbound | Invokes `capability.invoke(capabilityId, input)`; receives async result |
| **ResourceManager** | Outbound | Invokes `resources.reserve(requirements)`, `resources.release(reservationId)` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, workflowAction, workflowId)` |
| **StorageManager** | Outbound | Invokes `artifact.store()`, `artifact.retrieve()` |
| **HealthManager** | Outbound | Reports workflow health; invokes `health.readiness(capability)` |
| **ObservabilityManager** | Outbound | Emits workflow metrics, traces |

**Forbidden:** Direct step execution. All capability invocations SHALL go through CapabilityManager.

#### 4.6.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Step capability unavailable | Retry per policy; if exhausted: mark step failed; trigger compensation |
| Step timeout | Mark step failed; trigger retry or compensation |
| Resource exhaustion mid-workflow | Pause workflow; emit WorkflowPausedEvent; resume when resources available |
| CapabilityManager failure | Pause affected workflows; emit WorkflowManagerDegradedEvent |
| StorageManager failure (artifacts) | Queue artifact writes; retry; if persistent: mark workflow degraded |
| SecurityManager denial | Mark workflow failed; emit WorkflowAuthorizationFailedEvent |
| Nested workflow failure | Per parent propagation config: fail, compensate, or continue |

**Invariant:** WorkflowManager SHALL never leave a workflow in an undefined state. Every failure path leads to a defined terminal state (COMPLETED, FAILED, CANCELLED) with compensation executed.

#### 4.6.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom scheduling algorithms (pluggable)
- Custom coordination primitives
- Custom retry policies (per workflow template)
- Custom compensation action types
- Custom timeout enforcement (e.g., CPU-time vs wall-clock)

**Extension Constraints** (MUST be preserved):
- DAG execution model SHALL be preserved
- Saga compensation SHALL be mandatory for stateful steps
- EventBus as sole coordination mechanism SHALL be preserved
- CapabilityManager for all step execution SHALL be preserved
- Nested workflow depth bound SHALL be enforced

**Forbidden Extensions:**
- Direct capability invocation bypassing CapabilityManager
- Shared state between sibling workflows (except via artifacts)
- Unbounded recursion in nested workflows
- Skipping compensation for completed steps

#### 4.6.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **DAG execution** | No cycles in executed step graph; topological order preserved |
| **Saga compensation** | Every completed step in failed workflow has compensation executed |
| **Resource accounting** | Every step execution has ResourceManager reservation |
| **Capability mediation** | Zero direct capability invocations observed |
| **State machine completeness** | Every workflow instance reaches terminal state |
| **Correlation integrity** | All nested workflow events carry parent correlation ID |

#### 4.6.15 Conformance

A WorkflowManager implementation SHALL be conformant IFF:

1. **Static:** Passes workflow schema validation, DAG validation, compensation completeness validation
2. **Runtime:** Workflows execute per DAG; compensation executes on failure; timeouts enforced; retries per policy; nested workflows isolated
3. **Architectural:** No direct step execution; all capabilities via CapabilityManager; all resources via ResourceManager; all coordination via EventBus

---

### 4.7 SecurityManager

#### 4.7.1 Purpose

SecurityManager SHALL serve as the **sole enforcement authority** for all security policies within the Hermes Kernel. It SHALL own authentication, authorization, policy enforcement, secret handling, audit coordination, identity management, and trust boundaries.

#### 4.7.2 Responsibilities

SecurityManager SHALL be responsible for:

1. **Authentication** — Verification of principal identity for all kernel interactions
2. **Authorization** — Evaluation of access control decisions for all protected operations
3. **Policy Enforcement** — Centralized policy decision and enforcement point (PDP/PEP)
4. **Secret Handling** — Secure storage, rotation, injection, and access control for secrets
5. **Audit Coordination** — Emission of security audit events for all security-relevant actions
6. **Identity Management** — Principal lifecycle, authentication methods, credential management
7. **Trust Boundaries** — Definition and enforcement of trust zones, network policies, capability boundaries

#### 4.7.3 Authentication

SecurityManager SHALL authenticate all principals before authorization:

| Principal Type | Authentication Method |
|----------------|----------------------|
| **Human Operators** | OIDC/OAuth2, mTLS, SSH certificates, WebAuthn |
| **Services** | mTLS, SPIFFE/SPIRE, JWT (short-lived), API keys (deprecated) |
| **Workflows** | Short-lived workload identity (SPIFFE), capability tokens |
| **Core Managers** | Kernel-internal identity (bootstrapped at init) |
| **External Systems** | Mutual TLS, signed requests, pre-shared keys (rotated) |

**Authentication Flow:**
1. Principal presents credentials to SecurityManager (via EventBus or direct for kernel-internal)
2. SecurityManager validates credentials against IdentityProvider (Core Component, Part 3)
3. On success: SecurityManager issues authenticated context (principal ID, claims, expiry, trust level)
4. On failure: SecurityManager emits AuthenticationFailedEvent; denies request

**Invariant:** No authorization decision SHALL be made without successful authentication.

#### 4.7.4 Authorization

SecurityManager SHALL authorize all protected operations using **Attribute-Based Access Control (ABAC)**:

| Decision Input | Source |
|----------------|--------|
| **Principal** | Authenticated context (ID, roles, attributes, trust level) |
| **Action** | Operation being attempted (capability invocation, state transition, storage access, etc.) |
| **Resource** | Target resource (namespace, workflow, capability, secret, etc.) |
| **Context** | Request metadata (time, network zone, certification level, etc.) |

**Policy Language:** Declarative, versioned, stored in ConfigurationAuthority. Policies SHALL support:
- Allow/deny with obligations
- Condition evaluation (CEL or equivalent)
- Data-dependent decisions (resource attributes)
- Delegation and impersonation constraints

**Authorization Flow:**
1. Caller (manager or service) invokes `security.authorize(principal, action, resource, context)`
2. SecurityManager evaluates applicable policies in priority order
3. SecurityManager returns Decision: ALLOW, DENY, or CHALLENGE (step-up auth)
4. SecurityManager emits AuthorizationDecisionEvent (audit)

**Invariant:** Authorization SHALL be the single enforcement point. No manager SHALL implement custom authorization logic.

#### 4.7.5 Policy Enforcement

SecurityManager SHALL enforce policies at **enforcement points**:

| Enforcement Point | Protected Operations |
|-------------------|---------------------|
| **Capability Invocation** | `capability.invoke()` — principal must have `capability.invoke` on target |
| **State Transition** | `state.transition()` — principal must have `state.transition` on target category |
| **Storage Access** | `storage.read/write/delete` — principal must have `storage.*` on namespace |
| **Workflow Control** | `workflow.submit/cancel/pause` — principal must have `workflow.*` on workflow |
| **Secret Access** | `secret.get/set/rotate` — principal must have `secret.*` on secret path |
| **Configuration** | `config.read/write` — principal must have `config.*` on key path |
| **Manager Admin** | `manager.restart/configure` — principal must have `kernel.admin` |

**Enforcement Modes:**
- **Blocking** (default): Request waits for decision
- **Non-blocking**: Decision cached; async re-evaluation on policy change
- **Audit-only**: Log decision but allow (for policy testing)

#### 4.7.6 Secret Handling

SecurityManager SHALL govern all secrets:

| Secret Type | Examples | Handling |
|-------------|----------|----------|
| **Static Secrets** | API keys, database passwords | Encrypted at rest; injected via environment/files at runtime; never logged |
| **Dynamic Secrets** | Database credentials, cloud tokens | Generated on-demand; short TTL; auto-rotated |
| **Certificates** | mTLS certs, signing keys | Managed via PKI; auto-renewed before expiry |
| **Encryption Keys** | Data encryption keys, KEK | HSM-backed; never exported; key handles only |
| **Workflow Secrets** | Per-workflow credentials | Scoped to workflow; auto-revoked on completion |

**Secret Operations:**
- `secret.create(path, type, policy)` — Create secret with policy
- `secret.get(handle)` — Retrieve secret value (audited)
- `secret.rotate(path)` — Rotate secret per policy
- `secret.revoke(path)` — Immediately revoke

**Invariant:** SecurityManager SHALL never log secret values. All secret access SHALL be audited.

#### 4.7.7 Audit Coordination

SecurityManager SHALL emit **SecurityAuditEvent** for all security-relevant actions:

| Event Category | Examples |
|----------------|----------|
| **Authentication** | Login success/failure, MFA challenge, token issuance/refresh/revocation |
| **Authorization** | Allow/deny/challenge decisions with full context |
| **Secret Access** | Create, read, rotate, revoke, injection |
| **Policy Changes** | Policy create/update/delete, version activation |
| **Identity Changes** | Principal create/update/delete, role assignment, credential rotation |
| **Trust Boundary** | Zone changes, network policy updates, certificate validation |

**Audit Event Structure:** Timestamp, principal, action, resource, decision, policy version, correlation ID, request context.

**Invariant:** SecurityAuditEvent SHALL be emitted to EventBus with `audit` namespace. ObservabilityManager SHALL ensure durable delivery to audit store (Part 4 §4.11).

#### 4.7.8 Identity

SecurityManager SHALL manage principal identity lifecycle:

| Operation | Description |
|-----------|-------------|
| **Provision** | Create principal identity (human, service, workflow) |
| **Authenticate** | Bind credentials to principal |
| **Attribute** | Assign/modify attributes (roles, groups, trust level) |
| **Delegate** | Create delegation token with constrained scope |
| **Revoke** | Invalidate all credentials and tokens for principal |
| **Archive** | Soft-delete; retain for audit; prevent reuse |

**Identity Source of Truth:** IdentityProvider (Core Component, Part 3) for authentication; SecurityManager for authorization attributes.

#### 4.7.9 Trust Boundaries

SecurityManager SHALL define and enforce trust boundaries:

| Boundary Type | Enforcement |
|---------------|-------------|
| **Network Zones** | Ingress/egress policies per zone; mTLS required cross-zone |
| **Capability Boundaries** | Capability invocation restricted by trust level |
| **Data Classification** | Storage namespace access by data classification |
| **Workflow Isolation** | Workflow tenants isolated unless explicit sharing |
| **Manager Boundaries** | Core Managers operate at highest trust; services at lower |

**Trust Levels:** SYSTEM (kernel managers), PRIVILEGED (platform services), STANDARD (user services), UNTRUSTED (external).

#### 4.7.10 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: SecurityAuditEvent, AuthenticationFailedEvent, AuthorizationDecisionEvent, SecretRotatedEvent, PolicyUpdatedEvent, TrustBoundaryViolationEvent. Consumes: AuthenticateRequestEvent, AuthorizeRequestEvent, SecretRequestEvent, PolicyChangeEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.security` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.security.*` configuration; policy definitions |
| **IdentityProvider** | Outbound | Invokes `identity.validate(credentials)`, `identity.getPrincipal(id)` |
| **CapabilityManager** | Inbound | Receives `capability.invoke` authorization requests |
| **StateManager** | Inbound | Receives `state.transition` authorization requests |
| **StorageManager** | Inbound | Receives `storage.*` authorization requests; provides key handles |
| **WorkflowManager** | Inbound | Receives `workflow.*` authorization requests |
| **ResourceManager** | Inbound | Receives `resources.reserve` authorization requests |
| **ObservabilityManager** | Outbound | Emits security metrics (auth latency, authz decisions, violations) |

**Forbidden:** Any manager or service performing authentication or authorization independently. All security decisions SHALL go through SecurityManager.

#### 4.7.11 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| IdentityProvider unavailable | Cache recent authentications (short TTL); deny new; emit SecurityDegradedEvent |
| Policy evaluation error | Default deny; emit SecurityPolicyErrorEvent; alert |
| Secret rotation failure | Retry; alert; do not revoke old until new confirmed |
| HSM unavailable | Queue key operations; emit SecurityHSMUnavailableEvent |
| Audit event loss | Buffer locally; retry with backoff; emit SecurityAuditBufferFullEvent if persistent |
| Policy conflict (allow+deny) | Default deny; emit SecurityPolicyConflictEvent |

**Invariant:** SecurityManager SHALL fail closed (deny) on any internal failure. Availability degradation SHALL NOT weaken enforcement.

#### 4.7.12 Extension Rules

**Extension Points** (MAY be extended):
- Custom authentication methods (pluggable validators)
- Custom policy language (if CEL-compatible)
- Custom obligation handlers (post-authorization actions)
- Custom trust boundary types
- Custom secret types with custom rotation logic

**Extension Constraints** (MUST be preserved):
- ABAC model SHALL be preserved
- Single enforcement point SHALL be preserved
- Fail-closed behavior SHALL be preserved
- Audit completeness SHALL be preserved
- IdentityProvider as authn source SHALL be preserved

**Forbidden Extensions:**
- Bypassing authorization for "internal" calls
- Caching allow decisions beyond TTL
- Logging secret values in any form
- Custom encryption without SecurityManager coordination

#### 4.7.13 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single enforcement point** | Zero authorization decisions outside SecurityManager |
| **Fail-closed** | All induced failures result in deny decisions |
| **Audit completeness** | Every protected operation has SecurityAuditEvent |
| **Secret non-logging** | Zero secret values in any log/observability output |
| **Policy versioning** | Every decision references policy version |
| **Trust boundary enforcement** | No cross-boundary access without explicit policy |

#### 4.7.14 Conformance

A SecurityManager implementation SHALL be conformant IFF:

1. **Static:** Passes policy language validation, trust boundary configuration validation, secret policy validation
2. **Runtime:** All authn/authz decisions correct per policy; secrets managed per policy; audit events complete; fail-closed under failure
3. **Architectural:** No independent authn/authz; all via SecurityManager; EventBus for audit; IdentityProvider for authn source

---

### 4.8 CapabilityManager

#### 4.8.1 Purpose

CapabilityManager SHALL serve as the **sole registry and routing authority** for all capabilities within the Hermes Kernel. It SHALL own capability registration, discovery, resolution, routing, version compatibility, facade interaction, provider selection, and conflict resolution.

#### 4.8.2 Responsibilities

CapabilityManager SHALL be responsible for:

1. **Capability Registration** — Registration of capability providers with metadata, contracts, and health
2. **Discovery** — Query and enumeration of available capabilities by type, interface, tags
3. **Resolution** — Binding of capability requests to specific provider instances
4. **Routing** — Direction of invocation requests to selected providers
5. **Version Compatibility** — Enforcement of semantic version compatibility between facades and providers
6. **Facade Interaction** — Management of capability facades (stable interfaces) and provider implementations
7. **Provider Selection** — Load balancing, affinity, priority, and policy-based selection
8. **Conflict Resolution** — Handling of duplicate registrations, version conflicts, capability overlaps

#### 4.8.3 Capability Registration

CapabilityManager SHALL maintain a **Capability Registry** with entries:

| Field | Description |
|-------|-------------|
| **Capability ID** | Globally unique identifier (e.g., `ai-os.llm.inference.v1`) |
| **Facade** | Interface definition (schema, version, stability) |
| **Provider ID** | Unique provider instance identifier |
| **Provider Metadata** | Version, capabilities, resource profile, health endpoint, tags |
| **Contract** | Input/output schemas, SLOs, error definitions, deprecation policy |
| **Lifecycle State** | REGISTERING, ACTIVE, DEPRECATED, DRAINING, REMOVED |
| **Security Context** | Required trust level, authentication, authorization policy |
| **Resource Profile** | CPU, memory, GPU, network, LLM quota requirements |

**Registration Flow:**
1. Provider (service or manager) emits CapabilityRegisterEvent
2. CapabilityManager validates facade contract, version, metadata
3. CapabilityManager checks for conflicts (Section 4.8.10)
4. CapabilityManager registers provider; emits CapabilityRegisteredEvent
5. Provider begins health reporting via HealthManager

**Invariant:** No capability SHALL be invocable before CapabilityRegisteredEvent is emitted.

#### 4.8.4 Discovery

CapabilityManager SHALL support discovery queries:

| Query Type | Parameters | Returns |
|------------|------------|---------|
| **By Facade** | Facade ID, version range | All compatible providers |
| **By Tag** | Tag selector (key=value, expressions) | Matching providers |
| **By Resource** | Resource requirements (GPU, memory) | Providers meeting requirements |
| **By Health** | Minimum health level | Healthy providers only |
| **By Security** | Required trust level | Providers meeting trust level |

**Discovery Result:** List of provider summaries (ID, version, health, location, resource profile).

**Invariant:** Discovery SHALL only return ACTIVE providers. DEPRECATED providers SHALL be excluded unless explicitly requested.

#### 4.8.5 Resolution

CapabilityManager SHALL resolve invocation requests to providers:

**Resolution Input:** Capability ID (or facade + version), input payload, caller context (principal, workflow, priority), routing hints.

**Resolution Algorithm:**
1. Filter providers by facade compatibility (semver)
2. Filter by caller authorization (SecurityManager)
3. Filter by resource availability (ResourceManager)
4. Filter by health (HealthManager)
5. Apply selection policy (Section 4.8.7)
6. Return selected provider ID + routing information

**Resolution Result:** Provider endpoint, capability version, correlation ID, timeout, retry policy.

**Invariant:** Resolution SHALL be deterministic given same inputs and registry state.

#### 4.8.6 Routing

CapabilityManager SHALL route invocations:

| Routing Mode | Description |
|--------------|-------------|
| **Direct** | Caller invokes provider directly using returned endpoint |
| **Proxied** | CapabilityManager proxies request (for authz, observability, transformation) |
| **Async** | Request queued; result via EventBus (for long-running) |
| **Streaming** | Bidirectional streaming for streaming capabilities |

**Routing Responsibilities:**
- Inject correlation IDs
- Enforce timeouts
- Apply retry policy (from facade contract)
- Emit CapabilityInvocationEvent (observability)
- Handle provider failures (circuit breaker, failover)

#### 4.8.7 Version Compatibility

CapabilityManager SHALL enforce **semantic versioning (SemVer)** compatibility:

| Compatibility Rule | Facade → Provider |
|--------------------|-------------------|
| **Exact Match** | Facade `1.2.3` → Provider `1.2.3` |
| **Compatible** | Facade `^1.2.3` → Provider `1.2.x` (patch) |
| **Minor Compatible** | Facade `~1.2.3` → Provider `1.x.x` (minor+patch) |
| **Major Incompatible** | Facade `1.x.x` ↛ Provider `2.x.x` (blocked) |

**Deprecation Handling:**
- DEPRECATED providers: excluded from resolution unless caller opts in
- Deprecation timeline: announced → grace period (configurable) → removal
- Migration: CapabilityManager SHALL emit CapabilityDeprecatedEvent with migration guidance

#### 4.8.8 Facade Interaction

CapabilityManager SHALL manage **facades** (stable interfaces):

| Facet | Responsibility |
|-------|----------------|
| **Facade Definition** | Schema (input/output), version, stability (EXPERIMENTAL, STABLE, DEPRECATED), owner |
| **Facade Registry** | Global registry of facades; version history; deprecation schedule |
| **Contract Validation** | Provider registration validates against facade schema |
| **Compatibility Matrix** | Published matrix of facade versions ↔ provider versions |
| **Mock/Stub Support** | Test facades for development (never in OPERATIONAL) |

**Invariant:** Facades SHALL be owned by a single team. Facade evolution SHALL follow SemVer.

#### 4.8.9 Provider Selection

CapabilityManager SHALL select providers using configurable policies:

| Policy | Description |
|--------|-------------|
| **Round Robin** | Distribute evenly across healthy providers |
| **Least Loaded** | Select provider with lowest current utilization |
| **Priority** | Providers with priority weight; higher weight preferred |
| **Affinity** | Prefer provider in same zone, with cached data, same GPU type |
| **Cost-Aware** | Prefer lower-cost providers (spot, reserved) when SLO permits |
| **Canary** | Route small percentage to new version |

**Policy Composition:** Policies SHALL compose (e.g., priority → least loaded → affinity). ConfigurationAuthority defines policy per capability or globally.

#### 4.8.10 Conflict Resolution

CapabilityManager SHALL resolve conflicts:

| Conflict Type | Resolution |
|---------------|------------|
| **Duplicate Provider ID** | Reject registration; emit CapabilityConflictEvent |
| **Same Facade, Same Version** | Allow multiple (load balanced); require distinct provider IDs |
| **Same Facade, Overlapping Versions** | Allow; resolution picks highest compatible |
| **Contract Mismatch** | Reject registration; provider must match facade schema |
| **Resource Profile Mismatch** | Warn; allow but resolution filters by actual resources |
| **Security Context Mismatch** | Reject if provider requires higher trust than facade declares |

**Invariant:** Conflicts SHALL be detected at registration time. No runtime surprises.

#### 4.8.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: CapabilityRegisteredEvent, CapabilityDeprecatedEvent, CapabilityRemovedEvent, CapabilityInvocationEvent, CapabilityConflictEvent. Consumes: CapabilityRegisterEvent, CapabilityDeregisterEvent, CapabilityInvokeEvent, CapabilityDiscoverEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.capability` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.capability.*` configuration; selection policies |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, capability.invoke, capabilityId)` |
| **ResourceManager** | Outbound | Invokes `resources.checkAvailability(profile)` |
| **HealthManager** | Outbound | Invokes `health.readiness(providerId)`; subscribes to health changes |
| **WorkflowManager** | Inbound | Receives `capability.invoke()` for workflow steps |
| **ObservabilityManager** | Outbound | Emits capability metrics (latency, errors, throughput, selection) |

**Forbidden:** Direct provider invocation bypassing CapabilityManager resolution. All capability calls SHALL go through CapabilityManager.

#### 4.8.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| No compatible provider | Emit CapabilityUnavailableEvent; fail invocation |
| Provider health check failure | Mark provider UNHEALTHY; exclude from resolution; emit CapabilityProviderUnhealthyEvent |
| Provider invocation timeout | Retry per facade retry policy; circuit breaker on repeated failure |
| Provider returns error | Classify error (retryable/non-retryable); retry or fail per policy |
| Registry corruption | Rebuild from ServiceRegistry; emit CapabilityRegistryRecoveredEvent |
| Version incompatibility | Emit CapabilityVersionConflictEvent; fail resolution |

**Invariant:** CapabilityManager SHALL never route to an UNHEALTHY provider. Circuit breaker SHALL open after configurable failure threshold.

#### 4.8.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom selection policies (pluggable)
- Custom routing modes (e.g., gRPC, HTTP, message queue)
- Custom contract validation (beyond schema)
- Custom conflict resolution rules
- Custom facade stability levels

**Extension Constraints** (MUST be preserved):
- Single registry authority SHALL be preserved
- SemVer compatibility SHALL be preserved
- Facade ownership SHALL be preserved
- SecurityManager authorization SHALL be mandatory
- HealthManager health checks SHALL be mandatory

**Forbidden Extensions:**
- Provider self-registration without validation
- Bypassing version compatibility
- Direct provider references in callers
- Unregistered capability invocation

#### 4.8.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single registry** | All capability registrations visible in CapabilityManager registry |
| **SemVer enforcement** | No resolution of incompatible major versions |
| **Authorization gate** | Zero invocations without SecurityManager allow |
| **Health gating** | Zero routes to UNHEALTHY providers |
| **Facade ownership** | Each facade has exactly one owning team |
| **No direct invocation** | Zero capability invocations bypassing CapabilityManager |

#### 4.8.15 Conformance

A CapabilityManager implementation SHALL be conformant IFF:

1. **Static:** Passes facade schema validation, SemVer compatibility matrix validation, policy configuration validation
2. **Runtime:** Registrations validated; discovery accurate; resolution deterministic; routing observes policies; conflicts detected
3. **Architectural:** Single registry; all invocations mediated; EventBus for events; SecurityManager for authz; HealthManager for health

---

### 4.9 ResourceManager

#### 4.9.1 Purpose

ResourceManager SHALL serve as the **sole accounting and enforcement authority** for all computational resources within the Hermes Kernel. It SHALL own resource accounting (CPU, memory, disk, network, GPU, LLM quotas), reservations, limits, and backpressure.

#### 4.9.2 Responsibilities

ResourceManager SHALL be responsible for:

1. **Resource Accounting** — Real-time tracking of resource allocation, usage, and availability across all resource types
2. **CPU Accounting** — Core allocation, usage tracking, throttling
3. **Memory Accounting** — Allocation tracking, OOM prevention, swap management
4. **Disk Accounting** — Volume allocation, usage, IOPS, throughput
5. **Network Accounting** — Bandwidth allocation, connection tracking, egress/ingress quotas
6. **GPU Accounting** — Device allocation, memory, compute units, MIG slices
7. **LLM Quota Accounting** — Token budgets, request rates, model-specific quotas
8. **Reservations** — Advance reservation of resources for workflows/capabilities
9. **Limits** — Hard and soft limits per principal, workflow, capability, namespace
10. **Backpressure** — Signaling and enforcement when resources exhausted

#### 4.9.3 Resource Accounting

ResourceManager SHALL maintain a **Resource Ledger** for each resource type:

| Resource Type | Unit | Accounting Granularity |
|---------------|------|------------------------|
| **CPU** | Millicores (mCPU) | Per reservation |
| **Memory** | Bytes | Per reservation |
| **Disk** | Bytes, IOPS, throughput (MB/s) | Per volume |
| **Network** | Mbps, connections | Per interface/zone |
| **GPU** | Device, memory (bytes), compute % | Per device/slice |
| **LLM Quota** | Tokens (input+output), requests | Per model, per principal |

**Accounting Principles:**
- **Attribution** — Every allocation attributed to a principal (workflow, capability, service, manager)
- **Hierarchy** — Nested allocations (workflow → step → capability) roll up to parent
- **Real-time** — Ledger reflects current state within 100ms
- **Auditable** — All allocation/release events emitted to EventBus

#### 4.9.4 Reservations

ResourceManager SHALL support **advance reservations**:

| Reservation Type | Use Case | Lifetime |
|------------------|----------|----------|
| **Workflow Reservation** | Full workflow resource needs | Workflow duration |
| **Step Reservation** | Single capability invocation | Step duration |
| **Capability Reservation** | Provider capacity guarantee | Configurable TTL |
| **Maintenance Reservation** | Kernel operations (compaction, backup) | Operation duration |

**Reservation Protocol:**
1. Caller invokes `resources.reserve(requirements, holder, ttl)`
2. ResourceManager checks availability against limits and current usage
3. If available: atomically deduct from available; emit ResourceReservedEvent; return reservation ID
4. If unavailable: queue request (if waitable) or reject with ResourceUnavailableEvent
5. On completion: caller invokes `resources.release(reservationId)`; ResourceManager returns to available

**Invariant:** Reservations SHALL be atomic. Partial reservations SHALL NOT occur.

#### 4.9.5 Limits

ResourceManager SHALL enforce limits at multiple scopes:

| Scope | Limit Types | Enforcement |
|-------|-------------|-------------|
| **Global** | Total cluster capacity | Hard; never exceeded |
| **Namespace** | Per Kubernetes namespace equivalent | Hard; quota enforcement |
| **Principal** | Per user, service, workflow | Hard + soft (warning) |
| **Capability** | Per capability type | Soft; backpressure |
| **Workflow** | Per workflow template | Hard; defined at submit |

**Limit Configuration:** Via ConfigurationAuthority; versioned; changes take effect on next reservation.

#### 4.9.6 Backpressure

ResourceManager SHALL signal and enforce backpressure:

| Signal | Trigger | Action |
|--------|---------|--------|
| **Soft Limit Warning** | Usage > 80% of limit | Emit ResourcePressureEvent; callers may throttle |
| **Hard Limit Reached** | Usage = limit | Reject new reservations; emit ResourceExhaustedEvent |
| **Critical Pressure** | Usage > 95% + queue depth > threshold | Emit ResourceCriticalEvent; LifecycleManager may degrade kernel |
| **OOM Imminent** | Memory available < reserve | Trigger emergency eviction; emit ResourceOOMImminentEvent |

**Backpressure Enforcement:**
- WorkflowManager pauses scheduling on ResourcePressureEvent
- CapabilityManager rejects invocations on ResourceExhaustedEvent
- LifecycleManager transitions to DEGRADED on ResourceCriticalEvent

#### 4.9.7 LLM Quota Accounting

ResourceManager SHALL provide specialized accounting for LLM resources:

| Quota Dimension | Description |
|-----------------|-------------|
| **Token Budget** | Total tokens (input+output) per period (day, month) |
| **Request Rate** | Requests per minute/hour |
| **Model-Specific** | Separate budgets per model (e.g., `opus`, `sonnet`, `haiku`) |
| **Priority Classes** | Guaranteed, best-effort, batch |
| **Carryover** | Unused budget rollover (configurable) |

**LLM Quota Enforcement:**
- CapabilityManager checks quota before routing LLM invocations
- Streaming token counting (estimate → actual on completion)
- Quota exhaustion triggers ResourceExhaustedEvent for LLM capability

#### 4.9.8 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: ResourceReservedEvent, ResourceReleasedEvent, ResourcePressureEvent, ResourceExhaustedEvent, ResourceCriticalEvent, ResourceOOMImminentEvent, ResourceUsageReportEvent. Consumes: ResourceReserveRequestEvent, ResourceReleaseRequestEvent, ResourceLimitChangeEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.resource` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.resource.*` configuration; limits, quotas |
| **WorkflowManager** | Inbound | Receives `resources.reserve()`, `resources.release()` |
| **CapabilityManager** | Inbound | Receives `resources.checkAvailability(profile)` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, resources.reserve, resourceType)` |
| **HealthManager** | Outbound | Reports resource health (capacity, pressure, saturation) |
| **ObservabilityManager** | Outbound | Emits resource metrics (usage, saturation, latency, quotas) |

**Forbidden:** Direct resource allocation by other managers. All allocation SHALL go through ResourceManager.

#### 4.9.9 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Reservation conflict (race) | Retry with backoff; deterministic ordering via reservation ID |
| Limit configuration error | Reject change; emit ResourceConfigErrorEvent; retain previous limits |
| Accounting drift detected | Reconcile from source of truth (cgroups, device plugins); emit ResourceDriftCorrectedEvent |
| GPU device loss | Release all reservations on device; emit ResourceDeviceLostEvent; notify affected holders |
| LLM quota service unavailable | Cache last known quota; allow with warning; emit ResourceQuotaUnavailableEvent |
| Backpressure signal loss | Default to conservative (assume pressure); emit ResourceSignalLostEvent |

**Invariant:** ResourceManager SHALL never over-allocate beyond global capacity. Accounting drift SHALL be detected and corrected within 30 seconds.

#### 4.9.10 Extension Rules

**Extension Points** (MAY be extended):
- Custom resource types (e.g., TPU, FPGA, custom accelerators)
- Custom limit scopes (e.g., team, project, folder)
- Custom backpressure algorithms
- Custom quota models (e.g., cost-based, carbon-aware)
- Custom reservation priority schemes

**Extension Constraints** (MUST be preserved):
- Single accounting authority SHALL be preserved
- Atomic reservations SHALL be preserved
- Global capacity hard limit SHALL be preserved
- Attribution to principal SHALL be preserved
- EventBus for all allocation events SHALL be preserved

**Forbidden Extensions:**
- Untracked resource usage
- Bypassing limits for "system" workloads
- Shared reservations without attribution
- Negative resource accounting

#### 4.9.11 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **No over-allocation** | Sum of reservations ≤ global capacity for all resource types |
| **Attribution completeness** | Every allocated unit has a principal |
| **Atomic reservation** | Zero partial reservations under concurrent load |
| **Limit enforcement** | No reservation exceeds declared limit |
| **Backpressure signaling** | ResourcePressureEvent emitted within 100ms of threshold crossing |
| **Accounting accuracy** | Ledger matches actual usage within 5% (measured via cgroups/device plugins) |

#### 4.9.12 Conformance

A ResourceManager implementation SHALL be conformant IFF:

1. **Static:** Passes resource type registration, limit configuration validation, quota model validation
2. **Runtime:** Reservations atomic; limits enforced; backpressure signaled; accounting accurate; drift corrected
3. **Architectural:** Single accounting authority; all allocation via ResourceManager; EventBus for events; SecurityManager for authz

---

### 4.10 HealthManager

#### 4.10.1 Purpose

HealthManager SHALL serve as the **sole health authority** within the Hermes Kernel. It SHALL own health monitoring, readiness, liveness, heartbeat, diagnostics, recovery recommendations, and health aggregation.

#### 4.10.2 Responsibilities

HealthManager SHALL be responsible for:

1. **Health Monitoring** — Continuous assessment of all kernel components (managers, services, capabilities, infrastructure)
2. **Readiness** — Determination of whether a component can serve traffic / perform its function
3. **Liveness** — Determination of whether a component is alive (not deadlocked, not crashed)
4. **Heartbeat** — Collection and aggregation of heartbeat signals
5. **Diagnostics** — On-demand and automated diagnostic data collection
6. **Recovery Recommendations** — Emission of actionable recovery steps for unhealthy components
7. **Health Aggregation** — Composite health views (kernel, subsystem, tenant, workflow)

#### 4.10.3 Health Monitoring

HealthManager SHALL monitor health at multiple levels:

| Level | Subjects | Frequency | Method |
|-------|----------|-----------|--------|
| **Kernel** | All Core Managers | Continuous (event-driven) | State machine + dependency graph |
| **Manager** | Each Core Manager | 10s interval | HTTP/health endpoint + self-report |
| **Service** | Registered services | 30s interval | HTTP/health endpoint |
| **Capability** | Capability providers | 30s interval | CapabilityManager health proxy |
| **Infrastructure** | Nodes, disks, network, GPUs | 60s interval | Node agent + device plugins |
| **Workflow** | Active workflows | Event-driven | WorkflowManager state events |

**Health State Values:** HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN, DRAINING

#### 4.10.4 Readiness

Readiness SHALL indicate **ability to serve current function**:

| Component | Ready Criteria |
|-----------|----------------|
| **LifecycleManager** | All phases complete; kernel OPERATIONAL |
| **StateManager** | Accepting transitions; checkpoint current |
| **StorageManager** | All namespaces accessible; no corruption |
| **WorkflowManager** | Scheduler running; no backlog > threshold |
| **SecurityManager** | Policy engine responsive; IdentityProvider reachable |
| **CapabilityManager** | Registry consistent; >0 healthy providers per facade |
| **ResourceManager** | Accounting current; no critical pressure |
| **HealthManager** | Self-healthy; monitoring active |
| **ObservabilityManager** | Collectors running; no buffer overflow |
| **Service** | HTTP 200 on /ready; dependencies ready |
| **Capability Provider** | HTTP 200 on /ready; resources available |

**Invariant:** HealthManager SHALL be the single source of readiness truth. LifecycleManager SHALL gate OPERATIONAL on all managers READY.

#### 4.10.5 Liveness

Liveness SHALL indicate **process viability**:

| Component | Live Criteria |
|-----------|---------------|
| **All Managers** | Process responds; no deadlock detected; heartbeat within 3× interval |
| **Services** | Process responds; HTTP 200 on /live |
| **Infrastructure** | Node agent heartbeat; kernel responsive |

**Invariant:** Liveness failure SHALL trigger immediate recovery action (restart, failover). Readiness failure SHALL trigger traffic draining.

#### 4.10.6 Heartbeat

HealthManager SHALL manage heartbeat protocol:

| Aspect | Specification |
|--------|---------------|
| **Interval** | 10s (managers), 30s (services), 60s (infrastructure) |
| **Missed Threshold** | 3× interval = UNHEALTHY |
| **Payload** | Component ID, state, metrics snapshot, dependency health |
| **Aggregation** | HealthManager maintains heartbeat timeline per component |
| **Failure Detection** | Missing heartbeat → DEGRADED → UNHEALTHY (configurable) |

#### 4.10.7 Diagnostics

HealthManager SHALL collect diagnostics:

| Trigger | Collection | Output |
|---------|------------|--------|
| **On-Demand** | Admin request | Diagnostic bundle (logs, metrics, traces, config, state) |
| **State Change** | HEALTHY → DEGRADED/UNHEALTHY | Automated mini-bundle (last 5min logs, current metrics, stack traces) |
| **Periodic** | Daily | Full diagnostic snapshot (archived) |
| **Pre-Recovery** | Before recovery action | Pre-recovery baseline |

**Diagnostic Bundle:** Stored in StorageManager (diagnostics namespace); correlated via EventBus.

#### 4.10.8 Recovery Recommendations

HealthManager SHALL emit **HealthRecoveryRecommendationEvent** for UNHEALTHY components:

| Component | Recommendation Types |
|-----------|---------------------|
| **Manager** | Restart manager; rollback to checkpoint; failover to standby |
| **Service** | Restart pod; drain + reschedule; circuit breaker reset |
| **Capability Provider** | Drain connections; restart; failover to alternate provider |
| **Infrastructure** | Node cordon+drain; disk replacement; network reset |
| **Workflow** | Retry failed step; compensate; cancel |

**Recommendation Properties:** Priority, estimated duration, risk level, prerequisites, automation eligibility.

#### 4.10.9 Health Aggregation

HealthManager SHALL compute aggregate health:

| Aggregate | Composition | Semantics |
|-----------|-------------|-----------|
| **Kernel Health** | All Core Managers | HEALTHY iff all managers HEALTHY |
| **Subsystem Health** | Related managers (e.g., execution: workflow+capability+resource) | Worst-of |
| **Tenant Health** | Tenant's workflows, capabilities, services | Weighted by criticality |
| **Workflow Health** | Workflow steps, dependencies | HEALTHY iff all steps HEALTHY |
| **Capability Health** | All providers for a facade | HEALTHY iff ≥1 provider HEALTHY per required version |

**Aggregation Rules:** Configurable per aggregate; default: worst-of.

#### 4.10.10 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: HealthChangedEvent, ReadinessChangedEvent, LivenessLostEvent, HealthRecoveryRecommendationEvent, HealthAggregatedEvent, DiagnosticBundleReadyEvent. Consumes: ComponentHeartbeatEvent, ComponentStateEvent, ManagerInitializedEvent, WorkflowStateChangedEvent, CapabilityProviderHealthEvent |
| **ServiceRegistry** | Outbound | Registers self as `kernel.health` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.health.*` configuration; thresholds, intervals |
| **LifecycleManager** | Outbound | Invokes `lifecycle.getKernelState()`, `lifecycle.requestRecovery(manager)` |
| **StateManager** | Outbound | Invokes `state.getSnapshot()` for diagnostics |
| **StorageManager** | Outbound | Invokes `storage.diagnosticBundle()` |
| **ResourceManager** | Outbound | Invokes `resources.getUsage()` for pressure detection |
| **CapabilityManager** | Outbound | Invokes `capability.getProviderHealth()` |
| **WorkflowManager** | Outbound | Invokes `workflow.getHealth()` |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, health.diagnostic, component)` |
| **ObservabilityManager** | Outbound | Emits health metrics; receives observability alerts |

**Forbidden:** Other managers making independent health determinations for gating. All readiness/liveness SHALL come from HealthManager.

#### 4.10.11 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| HealthManager self-failure | LifecycleManager detects via missing heartbeat; initiates HealthManager restart |
| Heartbeat storm (too frequent) | Throttle; emit HealthHeartbeatStormEvent |
| Diagnostic collection failure | Retry; partial bundle; emit HealthDiagnosticPartialEvent |
| Recovery recommendation ignored | Escalate; emit HealthRecoveryIgnoredEvent after timeout |
| Aggregation inconsistency | Recompute; emit HealthAggregationCorrectedEvent |

**Invariant:** HealthManager SHALL monitor itself. Self-health SHALL be reported via dedicated heartbeat.

#### 4.10.12 Extension Rules

**Extension Points** (MAY be extended):
- Custom health check types (pluggable)
- Custom aggregation functions
- Custom diagnostic collectors
- Custom recovery recommendation engines
- Custom health state values (beyond standard 5)

**Extension Constraints** (MUST be preserved):
- Single health authority SHALL be preserved
- Readiness/liveness separation SHALL be preserved
- Heartbeat protocol SHALL be preserved
- LifecycleManager gating on readiness SHALL be preserved
- EventBus for all health events SHALL be preserved

**Forbidden Extensions:**
- Services self-declaring ready without HealthManager
- Managers bypassing HealthManager for peer health
- Health state modification without HealthManager
- Diagnostic bundles without StorageManager

#### 4.10.13 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single health authority** | Zero readiness/liveness decisions outside HealthManager |
| **Readiness gating** | Kernel never OPERATIONAL with any manager NOT_READY |
| **Heartbeat timeliness** | UNHEALTHY declared within 3× interval of missed heartbeat |
| **Diagnostic completeness** | Every state change to UNHEALTHY produces diagnostic bundle |
| **Aggregation consistency** | Aggregate health = f(component health) per configured function |
| **Self-monitoring** | HealthManager reports own health via heartbeat |

#### 4.10.14 Conformance

A HealthManager implementation SHALL be conformant IFF:

1. **Static:** Passes health check configuration validation, aggregation rule validation, threshold validation
2. **Runtime:** Readiness/liveness accurate; heartbeats processed; diagnostics collected; recommendations emitted; aggregation correct
3. **Architectural:** Single authority; all gating via HealthManager; EventBus for events; StorageManager for diagnostics

---

### 4.11 ObservabilityManager

#### 4.11.1 Purpose

ObservabilityManager SHALL serve as the **sole governance authority** for all observability within the Hermes Kernel. It SHALL own metrics, tracing, monitoring, dashboards, alerting, telemetry, diagnostics, and audit integration.

#### 4.11.2 Responsibilities

ObservabilityManager SHALL be responsible for:

1. **Metrics Governance** — Collection, aggregation, storage, and query of all kernel and service metrics
2. **Tracing Governance** — Distributed trace collection, correlation, sampling, and storage
3. **Monitoring** — Real-time observation of system state via metrics and traces
4. **Dashboards** — Governance of dashboard definitions, versioning, and access
5. **Alerting** — Rule evaluation, notification routing, deduplication, escalation
6. **Telemetry** — OpenTelemetry-compatible collection pipeline management
7. **Diagnostics** — On-demand high-cardinality data collection
8. **Audit Integration** — Secure, tamper-evident delivery of SecurityAuditEvent to audit store

#### 4.11.3 Metrics

ObservabilityManager SHALL govern metrics per **OpenTelemetry Metric Data Model**:

| Metric Type | Kernel Sources | Cardinality Control |
|-------------|----------------|---------------------|
| **Counter** | Request counts, error counts, event counts | Low (labels: component, operation, status) |
| **Gauge** | Current usage, queue depth, health status | Low (labels: component, resource) |
| **Histogram** | Latency, duration, size | Medium (labels: component, operation, quantile) |
| **Summary** | Quantile latencies (client-side) | Low |

**Metric Standards:**
- **Naming:** `ai_os_<subsystem>_<metric>` (snake_case)
- **Labels:** Standardized (component, instance, version, zone, tenant)
- **Units:** Base units (seconds, bytes, count) with SI prefixes
- **Collection Interval:** 10s (managers), 30s (services), configurable
- **Retention:** Hot (24h, 10s resolution), Warm (30d, 1m), Cold (1y, 1h)

**Cardinality Enforcement:** ObservabilityManager SHALL reject metric registration exceeding cardinality budget (default: 10k series/metric).

#### 4.11.4 Tracing

ObservabilityManager SHALL govern distributed tracing per **W3C TraceContext**:

| Aspect | Specification |
|--------|---------------|
| **Trace Propagation** | `traceparent`, `tracestate` headers on all RPC/EventBus |
| **Sampling** | Head-based (probabilistic), tail-based (error/latency), parent-based |
| **Sampling Rate** | Default 1% (configurable per component, operation) |
| **Span Attributes** | Standard (service.name, span.kind, http.*, db.*, messaging.*) + kernel custom |
| **Context Propagation** | Automatic via EventBus correlation IDs; manual for external calls |
| **Retention** | Hot (24h, all), Warm (7d, sampled), Cold (30d, errors only) |

**Kernel Trace Spans:** Every manager operation SHALL produce spans:
- LifecycleManager: phase transitions, rollback, recovery
- StateManager: transitions, snapshots, recovery
- StorageManager: checkpoint/artifact operations
- WorkflowManager: workflow/step execution, scheduling
- SecurityManager: authn, authz, secret operations
- CapabilityManager: registration, resolution, invocation
- ResourceManager: reservations, pressure, limits
- HealthManager: checks, diagnostics, recommendations

#### 4.11.5 Monitoring

ObservabilityManager SHALL provide **real-time monitoring** capabilities:

| Capability | Description |
|------------|-------------|
| **Live Query** | Ad-hoc metric/trace queries (PromQL/OTel compatible) |
| **Streaming** | WebSocket/SSE for real-time metric updates |
| **Topology** | Service/manager dependency graph from traces |
| **SLO Tracking** | SLI/SLO definition, burn rate alerting |

#### 4.11.6 Dashboards

ObservabilityManager SHALL govern dashboards as **code**:

| Property | Requirement |
|----------|-------------|
| **Definition** | JSON/YAML (Grafana-compatible or native) |
| **Versioning** | Stored in ConfigurationAuthority; git-tracked |
| **Templating** | Variables for tenant, component, time range |
| **Access Control** | SecurityManager authorization (read/write) |
| **Validation** | Schema validation on register; reference validation (metrics exist) |

#### 4.11.7 Alerting

ObservabilityManager SHALL govern alerting:

| Aspect | Specification |
|--------|---------------|
| **Rule Definition** | PromQL/OTel query + condition + duration + labels |
| **Evaluation Interval** | 30s (configurable per rule) |
| **States** | FIRING, PENDING, RESOLVED |
| **Deduplication** | Group by labels; suppress during maintenance windows |
| **Notification** | Webhook, PagerDuty, Slack, email (pluggable) |
| **Escalation** | Time-based; auto-escalate if unacknowledged |
| **Silencing** | Label-based; scheduled; manual |

**Alert Categories:** Infrastructure, Kernel, Service, Security, Business.

#### 4.11.8 Telemetry

ObservabilityManager SHALL manage the **telemetry pipeline**:

| Pipeline Stage | Responsibility |
|----------------|----------------|
| **Collection** | OTel receivers (OTLP, Prometheus, statsd, custom) |
| **Processing** | Transformation, filtering, enrichment, batching |
| **Export** | OTel exporters (OTLP, Prometheus, CloudWatch, custom) |
| **Buffering** | In-memory + disk spillover; backpressure to senders |

**Pipeline Guarantees:**
- At-least-once delivery (configurable)
- Ordering per trace
- Resource attribution preserved
- PII redaction (configurable)

#### 4.11.9 Diagnostics

ObservabilityManager SHALL support **high-cardinality diagnostics**:

| Trigger | Data | Retention |
|---------|------|-----------|
| **On-Demand** | Profiler traces, heap dumps, custom queries | 7 days |
| **Alert Firing** | Context snapshot (metrics, traces, logs) | 30 days |
| **Error Spike** | Exemplar traces for erroring requests | 14 days |
| **Performance Regression** | Comparative profiles | 30 days |

**Diagnostic Isolation:** Diagnostics SHALL NOT impact production pipeline (separate buffer, lower priority).

#### 4.11.10 Audit Integration

ObservabilityManager SHALL ensure **audit event delivery**:

| Requirement | Implementation |
|-------------|----------------|
| **Tamper Evidence** | Cryptographic chaining (hash chain) or Merkle tree |
| **Immutability** | Write-once storage (WORM) or append-only log |
| **Completeness** | Gap detection via sequence numbers |
| **Delivery** | Direct to audit namespace (StorageManager) + SIEM export |
| **Latency** | <5s from SecurityAuditEvent emission to durable storage |
| **Verification** | Periodic audit log integrity verification |

**Invariant:** SecurityAuditEvent SHALL never be dropped. Buffer overflow SHALL block SecurityManager (backpressure).

#### 4.11.11 Interaction Contracts

| Contract | Direction | Events/Methods |
|----------|-----------|----------------|
| **EventBus** | Bidirectional | Emits: MetricRegisteredEvent, AlertFiringEvent, AlertResolvedEvent, DashboardRegisteredEvent, TraceSampledEvent. Consumes: All kernel events (for metrics/traces), SecurityAuditEvent (for audit pipeline), HealthChangedEvent (for SLO) |
| **ServiceRegistry** | Outbound | Registers self as `kernel.observability` |
| **ConfigurationAuthority** | Inbound | Reads `kernel.observability.*` configuration; pipelines, rules, dashboards |
| **StorageManager** | Outbound | Invokes `storage.auditWrite()` for audit events; `artifact.store()` for diagnostic bundles |
| **SecurityManager** | Outbound | Invokes `security.authorize(principal, observability.*, resource)` |
| **ResourceManager** | Outbound | Invokes `resources.reserve()` for telemetry pipeline resources |
| **HealthManager** | Inbound | Receives health metrics; emits SLO burn alerts |
| **All Managers** | Inbound | Receive metrics, spans, logs via OTel SDK (configured by ObservabilityManager) |

**Forbidden:** Direct metric/trace emission to backends bypassing ObservabilityManager pipeline. All telemetry SHALL flow through ObservabilityManager.

#### 4.11.12 Failure Handling

| Failure Mode | Response |
|--------------|----------|
| Metric backend unavailable | Buffer locally (disk spillover); emit ObservabilityBackendUnavailableEvent |
| Trace sampling misconfiguration | Default to parent-based; emit ObservabilitySamplingWarnEvent |
| Alert evaluation failure | Skip cycle; emit ObservabilityAlertEvalFailedEvent; alert on repeated failure |
| Audit pipeline backpressure | Block SecurityManager; emit ObservabilityAuditBackpressureEvent |
| Cardinality explosion | Auto-throttle high-cardinality metrics; emit ObservabilityCardinalityThrottleEvent |
| Diagnostic collection failure | Retry; partial; emit ObservabilityDiagnosticPartialEvent |

**Invariant:** ObservabilityManager failure SHALL NOT cause kernel degradation. Telemetry is best-effort; audit is mandatory.

#### 4.11.13 Extension Rules

**Extension Points** (MAY be extended):
- Custom metric types (beyond OTel)
- Custom trace exporters
- Custom alert notification channels
- Custom dashboard formats
- Custom diagnostic collectors
- Custom PII redaction rules

**Extension Constraints** (MUST be preserved):
- OTel compatibility SHALL be preserved
- Audit pipeline priority SHALL be preserved
- Cardinality budgets SHALL be enforced
- SecurityManager authorization SHALL be mandatory
- EventBus as event source SHALL be preserved

**Forbidden Extensions:**
- Dropping audit events
- Bypassing pipeline for "internal" metrics
- Unbounded cardinality
- Plaintext audit storage

#### 4.11.14 Architectural Invariants

| Invariant | Testable Criterion |
|-----------|-------------------|
| **Single telemetry pipeline** | Zero direct backend writes by managers/services |
| **Audit completeness** | Zero SecurityAuditEvent gaps (sequence continuity) |
| **Audit latency** | 99th percentile <5s emission to durable storage |
| **Cardinality compliance** | No metric exceeds registered cardinality budget |
| **Trace correlation** | 100% of kernel operations have trace span |
| **Pipeline isolation** | Diagnostic collection never blocks primary pipeline |

#### 4.11.15 Conformance

An ObservabilityManager implementation SHALL be conformant IFF:

1. **Static:** Passes pipeline configuration validation, alert rule validation, dashboard schema validation, cardinality budget validation
2. **Runtime:** Metrics collected per interval; traces sampled per policy; alerts evaluated; audit events delivered; cardinality enforced
3. **Architectural:** Single pipeline; all telemetry mediated; audit priority; EventBus as source; SecurityManager for authz

---

**End of Part 4 (Sections 4.6–4.11)**
### 4.12 Manager Interaction

#### 4.12.1 Dependency Graph

The Core Manager dependency graph (from Section 4.2.5) defines all **allowed direct operational dependencies**. This graph SHALL be the single source of truth for initialization order, shutdown order, and failure propagation.

**Graph Properties:**
- **Acyclic** — Verified statically at kernel start
- **Complete** — All operational dependencies declared
- **Minimal** — No transitive dependencies declared as direct
- **Versioned** — Graph version locked per kernel release

```text
LifecycleManager (Phase 1)
    ↓
StateManager ←→ StorageManager (Phase 2)
    ↓              ↓
SecurityManager  ResourceManager  HealthManager (Phase 3)
    ↓              ↓                ↓
CapabilityManager ← WorkflowManager (Phase 4)
    ↓              ↓                ↓
         ObservabilityManager (Phase 5)
```

#### 4.12.2 Allowed Communication

Core Managers SHALL communicate **exclusively** through:

| Mechanism | Use Case |
|-----------|----------|
| **EventBus** (Part 2) | All asynchronous, event-driven communication; state changes, requests, responses, notifications |
| **Interface Contracts** (synchronous) | Rare; only for: SecurityManager authorization checks, ResourceManager availability checks, HealthManager readiness queries, CapabilityManager resolution |
| **ConfigurationAuthority** (Part 3) | Reading configuration; never writing |
| **ServiceRegistry** (Part 3) | Discovery of manager endpoints; registration |

**Interface Contract Constraints:**
- SHALL be defined in this specification (Sections 4.3–4.11)
- SHALL be invoked via capability-style interface (not direct object reference)
- SHALL have timeout and retry semantics
- SHALL emit events for audit/observability

#### 4.12.3 Forbidden Communication

The following communication patterns SHALL NEVER occur between Core Managers:

| Forbidden Pattern | Reason |
|-------------------|--------|
| **Direct method calls** | Violates Event-First; couples lifecycles; prevents substitution |
| **Shared memory/state** | Violates single ownership; causes consistency hazards |
| **RPC without EventBus** | Bypasses observability, audit, authorization |
| **Callback registration** | Creates hidden dependencies; complicates lifecycle |
| **Polling other managers** | Inefficient; EventBus provides push notification |
| **Configuration writes** | ConfigurationAuthority is single writer |

#### 4.12.4 Ownership Boundaries

Ownership boundaries (Section 4.2.6) SHALL be enforced by:

1. **Static Analysis** — Build-time verification that no manager imports another's internal types
2. **Runtime Guards** — Interface contracts validate caller authorization
3. **Event Contracts** — Event schemas define producer ownership
4. **Observability** — Cross-boundary calls detected via trace analysis

**Boundary Violation Response:** Any detected violation SHALL emit ManagerBoundaryViolationEvent (SecurityManager) and transition kernel to DEGRADED.

#### 4.12.5 Coordination Rules

Coordination between managers SHALL follow these rules:

| Rule | Specification |
|------|---------------|
| **Single Coordinator** | For any multi-manager operation, exactly one manager is designated coordinator (defined per operation) |
| **Event-Driven** | Coordination via EventBus events; no distributed locking |
| **Idempotency** | All coordination events idempotent; safe to retry |
| **Timeouts** | All coordination has explicit timeout; compensation on expiry |
| **Saga Pattern** | Multi-step coordination uses saga (compensation per step) |

**Example — Workflow Execution Coordination:**
- Coordinator: WorkflowManager
- Steps: Reserve resources (ResourceManager) → Resolve capability (CapabilityManager) → Authorize (SecurityManager) → Invoke (CapabilityManager) → Store artifact (StorageManager) → Release resources (ResourceManager)
- Each step: EventBus request/response; compensation on failure

**Example — Kernel Recovery Coordination:**
- Coordinator: LifecycleManager
- Steps: HealthManager recommends recovery → LifecycleManager requests StateManager restore → StorageManager provides checkpoint → StateManager restores → LifecycleManager re-initializes affected managers
- Each step: EventBus request/response; rollback on failure

#### 4.12.6 Failure Propagation

Failure propagation SHALL be **explicit and bounded**:

| Propagation Type | Mechanism | Scope |
|------------------|-----------|-------|
| **Dependency Failure** | Dependent manager detects via HealthManager; emits DegradedEvent | Direct dependents only |
| **Cascading Degradation** | LifecycleManager aggregates; may transition kernel to DEGRADED | Kernel-wide |
| **Isolation** | Unrelated managers continue operating | No propagation |
| **Recovery** | HealthManager recommends; LifecycleManager coordinates | Affected subtree |

**Prohibited:** Implicit failure propagation (e.g., manager crashes because dependency unavailable). All managers SHALL handle dependency unavailability gracefully (queue, degrade, fail fast with event).

#### 4.12.7 Initialization Order

Initialization order SHALL be **strictly derived** from the dependency graph (Section 4.2.5) via topological sort, grouped into phases (Section 4.2.3). Within a phase, order SHALL be alphabetical by manager name for determinism.

**Initialization Sequence:**
```
Phase 1: LifecycleManager
Phase 2: StateManager, StorageManager
Phase 3: HealthManager, ResourceManager, SecurityManager
Phase 4: CapabilityManager, WorkflowManager
Phase 5: ObservabilityManager
```

#### 4.12.8 Shutdown Order

Shutdown order SHALL be **strict reverse** of initialization:

```
Phase 1: ObservabilityManager
Phase 2: WorkflowManager, CapabilityManager
Phase 3: SecurityManager, ResourceManager, HealthManager
Phase 4: StorageManager, StateManager
Phase 5: LifecycleManager
```

**Shutdown Protocol per Manager:**
1. Stop accepting new work (drain)
2. Complete in-progress work (with timeout)
3. Release all resources (ResourceManager)
4. Deregister capabilities (CapabilityManager)
5. Emit ManagerShutdownEvent
6. Await LifecycleManager acknowledgment

---

### 4.13 Cross-Cutting Invariants

The following invariants apply to **ALL** Core Managers. Every invariant SHALL be **objectively testable** via automated conformance verification.

#### 4.13.1 Structural Invariants

| Invariant ID | Invariant | Test Criterion |
|--------------|-----------|----------------|
| **CC-S-001** | Single ownership per domain | Static analysis: exactly one manager declares each domain in ownership table |
| **CC-S-002** | No cyclic dependencies | Graph algorithm: dependency graph is DAG |
| **CC-S-003** | EventBus as sole async communication | Code scan: zero direct manager-to-manager async calls; all via EventBus client |
| **CC-S-004** | Interface contracts for sync calls | Code scan: all sync calls match declared contracts in Sections 4.3–4.11 |
| **CC-S-005** | ConfigurationAuthority for all config | Code scan: zero direct config file/env reads; all via ConfigurationAuthority client |
| **CC-S-006** | ServiceRegistry for discovery | Code scan: zero hardcoded endpoints; all via ServiceRegistry client |

#### 4.13.2 Runtime Invariants

| Invariant ID | Invariant | Test Criterion |
|--------------|-----------|----------------|
| **CC-R-001** | Deterministic initialization order | Multiple kernel starts produce identical manager start sequence |
| **CC-R-002** | Deterministic shutdown order | Multiple kernel stops produce identical manager stop sequence |
| **CC-R-003** | Health gate enforcement | Kernel never reaches OPERATIONAL with any manager NOT_READY |
| **CC-R-004** | No silent event drops | EventBus delivery guarantee: every published event delivered to all subscribers |
| **CC-R-005** | Bounded resource usage | Each manager's resource usage ≤ declared limits (ResourceManager accounting) |
| **CC-R-006** | Bounded event processing latency | P99 event processing < 100ms for all managers |
| **CC-R-007** | Graceful degradation | Single manager failure → kernel DEGRADED, not TERMINATED (unless foundation) |

#### 4.13.3 Lifecycle Invariants

| Invariant ID | Invariant | Test Criterion |
|--------------|-----------|----------------|
| **CC-L-001** | Phase ordering respected | No manager in phase N starts before all phase N-1 managers report READY |
| **CC-L-002** | Rollback completeness | Failed initialization → all managers shutdown; storage rolled back; state restored |
| **CC-L-003** | Shutdown completeness | All managers emit ManagerShutdownEvent before kernel TERMINATED |
| **CC-L-004** | No orphan resources | Post-shutdown: ResourceManager reports zero allocations |
| **CC-L-005** | Checkpoint consistency | Every OPERATIONAL → SHUTTING_DOWN transition has valid checkpoint |

#### 4.13.4 Security Invariants

| Invariant ID | Invariant | Test Criterion |
|--------------|-----------|----------------|
| **CC-SEC-001** | Fail-closed authorization | Induced SecurityManager failure → all authz decisions DENY |
| **CC-SEC-002** | No secret leakage | Log scan: zero secret values in any output (entropy-based detection) |
| **CC-SEC-003** | Audit completeness | Sequence gap check: zero missing SecurityAuditEvent sequence numbers |
| **CC-SEC-004** | Trust boundary enforcement | Network policy verification: no cross-zone traffic without policy |
| **CC-SEC-005** | Principal attribution | Every operation has authenticated principal in audit trail |

#### 4.13.5 Consistency Invariants

| Invariant ID | Invariant | Test Criterion |
|--------------|-----------|----------------|
| **CC-C-001** | State transition serialization | Concurrent transitions execute in request order (sequence numbers) |
| **CC-C-002** | Checkpoint durability | STRONG transitions: checkpoint ack before commit event |
| **CC-C-003** | Resource accounting accuracy | Ledger vs actual usage drift < 5% |
| **CC-C-004** | Capability registry consistency | Registry state = sum of registration events (event sourcing verification) |
| **CC-C-005** | Health aggregation correctness | Aggregate health = configured function of component healths |

#### 4.13.6 Recovery Invariants

| Invariant ID | Invariant | Test Criterion |
|--------------|-----------|----------------|
| **CC-REC-001** | Recovery validation | Post-recovery: all structural invariants (CC-S-*) pass |
| **CC-REC-002** | Recovery idempotency | Repeated recovery from same state produces identical end state |
| **CC-REC-003** | Recovery bounded time | Recovery completes within configured timeout (default: 300s) |
| **CC-REC-004** | No data loss on recovery | Acknowledged writes (storage, state) present post-recovery |
| **CC-REC-005** | Degraded recovery path | DEGRADED → OPERATIONAL possible without full restart |

---

### 4.14 Conformance Requirements

#### 4.14.1 Static Verification

Static verification SHALL be performed at **build time** and **deployment time**:

| Check | Tool | Failure Action |
|-------|------|----------------|
| Dependency graph acyclicity | Graph validator | Build fail |
| Ownership table completeness | Ownership checker | Build fail |
| Event contract conformance | Schema validator | Build fail |
| Interface contract conformance | Interface checker | Build fail |
| Configuration schema validation | Config validator | Build fail |
| Cardinality budget validation | Cardinality analyzer | Build fail |
| Secret handling scan | Secret scanner | Build fail |
| Forbidden pattern scan | Architecture linter | Build fail |

**Static Conformance:** A Core Manager build SHALL pass all static checks to be deployable.

#### 4.14.2 Runtime Verification

Runtime verification SHALL be performed **continuously** in OPERATIONAL state:

| Check | Frequency | Failure Action |
|-------|-----------|----------------|
| Health gate (all managers READY) | Continuous | Kernel → DEGRADED |
| Resource limit compliance | 10s | Backpressure + alert |
| Audit sequence continuity | Per event | Alert + investigation |
| Cardinality compliance | 60s | Throttle + alert |
| Accounting drift detection | 30s | Reconcile + alert |
| EventBus delivery latency | Per event | Alert if P99 > 100ms |
| Checkpoint durability | Per checkpoint | Alert if unacknowledged > 5s |

**Runtime Conformance:** Kernel SHALL maintain OPERATIONAL only while all runtime checks pass.

#### 4.14.3 Architectural Verification

Architectural verification SHALL be performed **periodically** (default: daily) and **on-demand**:

| Check | Method | Failure Action |
|-------|--------|----------------|
| Cross-cutting invariants (Section 4.13) | Automated test suite | Architecture Review Board notification |
| Failure injection resilience | Chaos testing (planned) | Remediation plan required |
| Upgrade/downgrade compatibility | Canary deployment | Rollback if verification fails |
| Disaster recovery drill | Quarterly exercise | Gap remediation required |
| Performance baseline comparison | Continuous profiling | Regression investigation |

**Architectural Conformance:** System SHALL pass architectural verification to remain in OPERATIONAL without restrictions.

#### 4.14.4 Violation Handling

| Violation Severity | Response |
|--------------------|----------|
| **Critical** (kernel integrity) | Immediate kernel → DEGRADED; ARB notification; root cause analysis required |
| **High** (security, data loss risk) | Alert + automatic mitigation (quarantine, throttle); 1h SLA for fix |
| **Medium** (performance, observability) | Alert; 24h SLA for fix |
| **Low** (cosmetic, non-functional) | Log; next release fix |

**Violation Classification:** Defined per invariant in Section 4.13.

#### 4.14.5 Audit Requirements

All conformance verification activities SHALL be audited:

| Activity | Audit Record |
|----------|--------------|
| Static verification run | Timestamp, commit, results, artifacts |
| Runtime check evaluation | Continuous (via SecurityAuditEvent for violations) |
| Architectural verification run | Timestamp, scope, results, evidence |
| Violation response | Timestamp, severity, action, resolution |
| Exception/waiver | ARB approval, justification, expiry, compensating controls |

**Audit Retention:** Per StorageManager audit namespace policy (default: 7 years).

---

### 4.15 Implementation vs Architecture Target

This section compares the **current implementation (v0.1.x)** with the **architecture target (v1.0)** defined in this specification.

#### 4.15.1 Implementation (v0.1.x) — Known Gaps

| Area | Implementation Status | Gap to Target |
|------|----------------------|---------------|
| **LifecycleManager** | Partial; hardcoded phases; no rollback | Missing: dependency graph, rollback coordination, health gating, recovery coordination |
| **StateManager** | Basic in-memory state; no snapshots/checkpoints | Missing: state machine, snapshots, checkpoint integration, consistency classes, recovery |
| **StorageManager** | Local filesystem only; no namespaces | Missing: namespace governance, checkpoint storage, artifact storage, retention, compaction, integrity, encryption coordination |
| **WorkflowManager** | Simple linear execution; no DAG | Missing: DAG execution, scheduling, cancellation, timeouts, retry, nested workflows, coordination primitives |
| **SecurityManager** | Basic authz; no authn integration | Missing: ABAC, secret handling, audit coordination, trust boundaries, IdentityProvider integration |
| **CapabilityManager** | Service registry only; no resolution | Missing: facade registry, version compatibility, provider selection, routing, conflict resolution |
| **ResourceManager** | Basic CPU/memory; no quotas | Missing: disk, network, GPU, LLM quotas, reservations, limits, backpressure |
| **HealthManager** | Basic liveness; no readiness | Missing: readiness, heartbeat, diagnostics, recovery recommendations, aggregation |
| **ObservabilityManager** | Logging only | Missing: metrics, tracing, dashboards, alerting, telemetry pipeline, audit integration |
| **Manager Interaction** | Direct calls common | Missing: EventBus exclusivity, forbidden patterns, coordination rules, explicit failure propagation |
| **Cross-Cutting Invariants** | Not enforced | Missing: all 25+ invariants with test criteria |
| **Conformance** | Ad-hoc testing | Missing: static/runtime/architectural verification, violation handling, audit requirements |

#### 4.15.2 Architecture Target (v1.0) — Mandatory Capabilities

| Capability | Target Specification | Verification |
|------------|---------------------|--------------|
| **Lifecycle Authority** | Full 8-state machine, 5-phase init/shutdown, rollback, recovery | Static + Runtime |
| **State Authority** | Serialized transitions, snapshots, checkpoints, 3 consistency classes, 4 recovery modes | Static + Runtime |
| **Storage Governance** | 6 namespaces, checkpoint atomicity, artifact lineage, retention, compaction, integrity, encryption | Static + Runtime |
| **Workflow Governance** | DAG execution, 8-state lifecycle, scheduling, 2 cancellation modes, timeouts, retry, nested (depth 10), coordination | Static + Runtime |
| **Security Enforcement** | ABAC, 7 authn methods, secret lifecycle, audit, trust boundaries, identity lifecycle | Static + Runtime |
| **Capability Registry** | Facade registry, SemVer, 6 selection policies, conflict resolution, 4 routing modes | Static + Runtime |
| **Resource Accounting** | 7 resource types, reservations, 5 limit scopes, 4 backpressure signals, LLM quotas | Static + Runtime |
| **Health Authority** | 6 monitoring levels, readiness/liveness, heartbeat, 4 diagnostic triggers, recovery recommendations, 5 aggregates | Static + Runtime |
| **Observability Governance** | OTel metrics/traces, dashboards-as-code, alerting, telemetry pipeline, audit integration | Static + Runtime |
| **Manager Interaction** | EventBus exclusivity, 4 allowed mechanisms, 6 forbidden patterns, ownership boundaries, coordination rules | Static + Architectural |
| **Cross-Cutting Invariants** | 25 invariants across 6 categories, all objectively testable | Static + Runtime + Architectural |
| **Conformance Framework** | 3 verification layers, violation handling, audit requirements | Architectural |

#### 4.15.3 Migration Path

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| **Phase 1** (v0.2) | Foundation | EventBus exclusivity, LifecycleManager phases, HealthManager readiness, SecurityManager authz |
| **Phase 2** (v0.3) | State & Storage | StateManager transitions, StorageManager namespaces, checkpoint integration |
| **Phase 3** (v0.4) | Execution | WorkflowManager DAG, CapabilityManager registry, ResourceManager accounting |
| **Phase 4** (v0.5) | Governance | SecurityManager ABAC/secrets, HealthManager diagnostics, ObservabilityManager pipeline |
| **Phase 5** (v1.0) | Conformance | All invariants testable, verification automated, architectural verification passing |

Each phase SHALL maintain backward compatibility for deployed services. Breaking changes SHALL follow deprecation policy (2 releases minimum).

---

### 4.16 Summary

#### 4.16.1 All Nine Core Managers

| Manager | Primary Responsibility | Initialization Phase | Shutdown Phase |
|---------|------------------------|---------------------|----------------|
| **LifecycleManager** | Kernel lifecycle authority, phase execution, rollback, recovery coordination | 1 | 5 |
| **StateManager** | Kernel state authority, transitions, snapshots, checkpoints, consistency, recovery | 2 | 4 |
| **StorageManager** | Persistent storage governance, checkpoints, artifacts, retention, compaction, integrity, encryption | 2 | 4 |
| **WorkflowManager** | Workflow execution governance, DAG lifecycle, scheduling, cancellation, timeouts, retry, nesting | 4 | 2 |
| **SecurityManager** | Security policy enforcement, authn, authz, secrets, audit, identity, trust boundaries | 3 | 3 |
| **CapabilityManager** | Capability registry, discovery, resolution, routing, versioning, facades, provider selection | 4 | 2 |
| **ResourceManager** | Resource accounting (CPU, memory, disk, network, GPU, LLM), reservations, limits, backpressure | 3 | 3 |
| **HealthManager** | Health authority, monitoring, readiness, liveness, heartbeat, diagnostics, recovery, aggregation | 3 | 3 |
| **ObservabilityManager** | Observability governance, metrics, tracing, dashboards, alerting, telemetry, audit integration | 5 | 1 |

#### 4.16.2 Ownership

Each manager owns exactly one domain. Ownership is exclusive and non-transferable. Boundaries are enforced by static analysis, runtime guards, and event contracts.

#### 4.16.3 Dependencies

The dependency graph (Section 4.2.5) is acyclic, complete, and minimal. It determines initialization order (5 phases), shutdown order (reverse), and failure propagation scope.

#### 4.16.4 Lifecycle

All managers follow the kernel lifecycle (UNINITIALIZED → INITIALIZING → OPERATIONAL → DEGRADED/SHUTTING_DOWN → TERMINATED) with health-gated transitions. Rollback and recovery are coordinated by LifecycleManager with HealthManager recommendations.

#### 4.16.5 Responsibilities

Each manager's responsibilities are defined in Sections 4.3–4.11 with detailed subsections for Purpose, Responsibilities, core domain operations, Interaction Contracts, Failure Handling, Extension Rules, Architectural Invariants, and Conformance.

#### 4.16.6 Mandatory Invariants

25 cross-cutting invariants across 6 categories (Structural, Runtime, Lifecycle, Security, Consistency, Recovery) — all objectively testable via automated verification.

#### 4.16.7 Conformance

Three-layer verification: Static (build-time), Runtime (continuous), Architectural (periodic). Violation handling by severity. Full audit trail required.

---

**End of Part 4**