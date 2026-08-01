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