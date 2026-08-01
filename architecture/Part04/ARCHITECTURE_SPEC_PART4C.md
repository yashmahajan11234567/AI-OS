# AI-OS Architecture Specification v1.0
## Part 4: Core Managers Architecture (Continued)

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-28)

---

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