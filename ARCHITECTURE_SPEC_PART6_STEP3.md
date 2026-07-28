# Architecture Specification Part 6 — Step 3: SkillService Execution Architecture

## 6.3 SkillService: The Execution Facade

### 6.3.1 Purpose

The **SkillService** exists to resolve the fundamental architectural tension between *capability definition* and *capability execution* within the AI-OS Capability Facade (Section 5.1).

The **SkillManager** (Section 6.2) owns the **Definition Plane** — the static topology of capabilities including registration, validation, versioning, dependency resolution, and lifecycle governance. It operates on declarative artifacts: manifests, schemas, and capability graphs.

**Engineering Services** (Part 4) operate in the **Execution Plane** — they must *invoke* capabilities at runtime, supplying arguments and receiving results. They require a stable, uniform invocation surface that is insulated from the volatility and complexity of registration mechanics, validation logic, and persistence concerns.

These two planes **MUST NOT** communicate directly. Direct coupling would violate the Capability Facade principle: Engineering Services would become dependent on SkillManager's internal representation of capabilities, creating transitive dependencies on concerns orthogonal to execution.

SkillService solves the **Execution Facade Problem**: how to present a stable, authoritative invocation surface to Engineering Services while maintaining strict separation from the Definition Plane.

Without SkillService, the architecture faces three architecturally unacceptable alternatives:

1. **Engineering Services import SkillManager directly** — violating layer separation, leaking registration concerns into execution logic, and making capability invocation inseparable from capability discovery.

2. **Engineering Services invoke capabilities via raw Event Space messages** — requiring each service to implement protocol-level message construction, correlation tracking, timeout handling, and error normalization, duplicating infrastructure logic across every consumer.

3. **Capabilities self-register execution endpoints** — inverting control, scattering invocation logic across capability implementations, and preventing centralized observability, policy enforcement, and routing optimization.

SkillService eliminates these alternatives by providing a **single, mandatory execution facade** that all Engineering Services **SHALL** use for all capability invocations.

### 6.3.2 Architectural Position

Within the AI-OS layered architecture (Part 1), SkillService occupies a mediating position between two architectural planes:

| Plane | Responsibility | Representative Component |
|-------|----------------|--------------------------|
| **Definition Plane** | Capability registration, validation, versioning, lifecycle governance | SkillManager |
| **Execution Plane** | Capability invocation, argument validation, result normalization, policy enforcement | SkillService |

SkillService is the **sole component** that bridges these planes. It consumes SkillManager's registration events to maintain an **execution index** — a read-optimized projection of the capability graph optimized for invocation-time decisions (routing, validation, policy lookup). It does not modify registration state; it only projects it.

This unidirectional dependency is an **architectural invariant**:

> **INV-6.3.1 (Unidirectional Dependency)**: SkillManager **SHALL NOT** depend on SkillService. SkillService **SHALL** depend on SkillManager's published registration events only.

### 6.3.3 Role Within the Capability Facade

The Capability Facade (Section 5.1) presents two distinct interfaces to two distinct consumer classes:

| Facade Interface | Owner | Consumers | Plane |
|------------------|-------|-----------|-------|
| **Definition Contract** (register, validate, list, deprecate, version) | SkillManager | Platform operators, CI/CD pipelines, capability authors | Definition Plane |
| **Execution Contract** (invoke, stream, cancel, health, metrics) | SkillService | Engineering Services, external integrations, AI agents | Execution Plane |

SkillService **owns the Execution Contract entirely**. It defines the invocation contract, error taxonomy, timeout semantics, streaming protocol, cancellation model, and correlation identity model for distributed tracing. These are *execution concerns* — they do not exist in the Definition Plane.

### 6.3.4 Relationship to SkillManager

The SkillManager–SkillService relationship is **publisher/subscriber**, not client/server:

- **SkillManager** publishes capability registration, update, and deprecation events to the Event Space (Part 4).
- **SkillService** subscribes to these events to maintain its execution index.
- **SkillService** **SHALL NOT** invoke SkillManager APIs, query SkillManager directly, or import SkillManager types. It operates exclusively on the *eventually consistent* projection built from the event stream.

This design ensures:
- **Temporal decoupling**: SkillService remains operational during SkillManager maintenance windows.
- **Failure isolation**: SkillManager failures do not cascade into execution failures (provided the execution index is current).
- **Scalability independence**: SkillService can scale horizontally for invocation throughput without affecting registration throughput.

### 6.3.5 Engineering Service Communication Constraint

The prohibition on direct Engineering Service–SkillManager communication is absolute:

> **REQ-6.3.1 (Execution Monopoly)**: Engineering Services **SHALL NOT** import, reference, or communicate with SkillManager under any circumstances. All capability invocations **SHALL** transit SkillService.

Rationale:
- **Interface Segregation**: Engineering Services require execution semantics (invoke, stream, cancel, timeout). SkillManager exposes registration semantics (register, validate, deprecate, query). These are disjoint concerns.
- **Stability**: SkillManager's APIs evolve with the registration model. SkillService's execution API is stable — it changes only when the *invocation contract* changes.
- **Policy Centralization**: Cross-cutting execution policies (authentication, rate limiting, circuit breaking, observability, audit logging) **MUST** be enforced at a single choke point. SkillService is that choke point.
- **Substitutability**: SkillService can be stubbed, mocked, or replaced (e.g., with a local executor for development) without touching SkillManager.

### 6.3.6 Architectural Responsibilities

SkillService bears the following **architectural responsibilities** (concerns, not implementations):

| Responsibility | Description |
|----------------|-------------|
| **Invocation Routing** | Resolving a capability identifier to its execution endpoint using the execution index. |
| **Contract Enforcement** | Validating that invocation arguments conform to the capability's declared input schema before dispatch. |
| **Policy Application** | Applying cross-cutting execution policies (authorization, rate limits, timeouts, retries, circuit breaking) uniformly. |
| **Result Normalization** | Transforming raw capability responses into the **canonical execution result contract** (success, error, streaming). |
| **Correlation Tracking** | Maintaining end-to-end invocation identity across asynchronous boundaries for observability and debugging. |
| **Lifecycle Isolation** | Ensuring capability execution failures cannot corrupt the execution index or affect other invocations. |
| **Index Freshness** | Guaranteeing the execution index reflects registration state within a bounded staleness window. |

### 6.3.7 Architectural Invariants

The following invariants define SkillService's architectural contract. They are **necessary conditions** for the Capability Facade architecture to hold:

> **INV-6.3.1 (Unidirectional Dependency)**: SkillService depends on SkillManager's events; SkillManager has zero dependency on SkillService.

> **INV-6.3.2 (Execution Monopoly)**: All capability invocations from Engineering Services transit SkillService. No alternative execution path exists.

> **INV-6.3.3 (Index Read-Only)**: SkillService's execution index is derived exclusively from SkillManager's published events. SkillService never writes registration state.

> **INV-6.3.4 (Policy Completeness)**: Every execution policy applicable to capability invocation is enforced at SkillService. No policy enforcement is delegated to callers or capabilities.

> **INV-6.3.5 (Failure Containment)**: A capability's execution failure (crash, timeout, logic error) cannot cause SkillService to lose its execution index, drop unrelated invocations, or publish spurious registration events.

> **INV-6.3.6 (Staleness Bound)**: The execution index reflects SkillManager's registration state with a maximum staleness of **T_index_max**. Engineering Services observe at-most **T_index_max** delay for new capabilities to become invocable.

> **INV-6.3.7 (Schema Fidelity)**: SkillService validates invocation arguments against the *exact* input schema declared in the capability's registered manifest. No schema transformation, relaxation, coercion, or inference occurs at the facade.

> **INV-6.3.8 (Result Canonicality)**: All invocations return the **canonical execution result contract**. No capability-specific response formats escape SkillService.

> **INV-6.3.9 (Correlation Completeness)**: Every invocation carries a correlation identity that is propagated to the capability, emitted in all observability signals, and returned to the caller.

These invariants are **architectural law**. Implementation decisions that violate them constitute architectural defects, regardless of functional correctness.

### 6.3.8 Event Space Interactions

SkillService participates in the Event Space (Part 4) as both consumer and producer:

#### Consumed Events (from SkillManager)

| Event | Purpose |
|-------|---------|
| `CapabilityRegistered` | New capability version available for execution |
| `CapabilityUpdated` | Capability metadata, schema, or endpoint changed |
| `CapabilityDeprecated` | Capability version entering deprecation grace period |
| `CapabilityRemoved` | Capability version removed after grace period expiry |

SkillService **SHALL** process these events in order, maintaining the execution index as a faithful projection.

#### Produced Events (to Event Space)

| Event | Purpose |
|-------|---------|
| `InvocationStarted` | Invocation admitted to execution pipeline |
| `InvocationCompleted` | Invocation terminated (success, error, or cancellation) |
| `PolicyViolation` | Policy enforcement denied an invocation |
| `SchemaValidationFailed` | Request or response failed schema validation |
| `ExecutionIndexStalenessExceeded` | Index freshness SLO breach detected |

These events enable platform observability, audit, and automated remediation without coupling consumers to SkillService internals.

### 6.3.9 Manager Space Interactions

SkillService **SHALL NOT** directly invoke Manager Space components (Part 2). Its only Manager Space interaction is indirect, via the Event Space:

- It consumes SkillManager's registration events.
- It produces execution observability events consumed by platform managers (e.g., MonitoringManager, AuditManager).

This preserves the Manager Space / Event Space separation defined in Part 2.

### 6.3.10 Lifecycle

SkillService lifecycle is defined by three states:

| State | Entry Condition | Exit Condition |
|-------|-----------------|----------------|
| **Bootstrapping** | Process start | Execution index built from event log and published |
| **Serving** | Index published, health checks passing | Shutdown signal or index corruption detected |
| **Degraded** | Dependency unavailable (event stream, policy service) | Dependency restored or graceful shutdown |

**Bootstrapping**: On startup, SkillService **SHALL** reconstruct its execution index by consuming the registration event stream from the last known consistent position. It **SHALL NOT** enter Serving state until the index reflects all events up to the stream head.

**Serving**: SkillService accepts invocations, maintains index currency via event consumption, and emits observability events.

**Degraded**: If the event stream becomes unavailable, SkillService **SHALL** continue serving from its last consistent index while emitting `ExecutionIndexStalenessExceeded` events. If staleness exceeds a configured threshold, it **SHALL** transition to a safe mode (rejecting invocations for capabilities not in index, or failing open/closed per policy domain configuration).

**Shutdown**: On termination signal, SkillService **SHALL** drain in-flight invocations (up to a configured grace period), flush pending observability events, and persist its index position for fast restart.

### 6.3.11 Ownership Boundaries

| Concern | Owner | SkillService Role |
|---------|-------|-------------------|
| Capability manifest | SkillManager | Consumer (read-only projection) |
| Capability schema | SkillManager | Consumer (exact enforcement) |
| Capability endpoint | SkillManager | Consumer (routing target) |
| Execution policy | Policy Manager (Part 2) | Consumer (enforcement point) |
| Invocation execution | Capability process | Orchestrator (dispatch, timeout, retry) |
| Invocation result | Capability process | Transformer (normalization, validation) |
| Observability emission | SkillService | Producer (canonical events) |
| Correlation identity | SkillService | Generator / propagator |

SkillService **owns** the Execution Contract, the canonical execution result contract, the ErrorCode taxonomy, the correlation identity model, and the execution index data structure. It **does not own** capability definitions, schemas, endpoints, or policy definitions — it consumes and enforces them.

### 6.3.12 Dependency Rules

| Dependency | Direction | Type | Rationale |
|------------|-----------|------|-----------|
| SkillManager → SkillService | **Forbidden** | — | Preserves Definition Plane purity |
| SkillService → SkillManager (events) | **Required** | Event subscription | Index currency |
| SkillService → Policy Manager | **Required** | Policy consumption | Policy enforcement |
| SkillService → Event Space | **Required** | Infrastructure | Event consumption/production |
| Engineering Service → SkillService | **Required** | API invocation | Execution monopoly |
| Engineering Service → SkillManager | **Forbidden** | — | Facade integrity |
| Capability → SkillService | **None** | — | Capabilities are opaque executables |

### 6.3.13 Communication Model

SkillService communication follows the **Request–Response** and **Request–Stream** patterns over the **Event Space communication model** (Part 4). The Execution Contract is **transport-agnostic** — it defines the logical interaction, not the wire protocol.

#### Invocation Model

```
Engineering Service → SkillService → Capability Process
        │                  │                │
        │   1. Route       │                │
        │   2. Authorize   │                │
        │   3. Validate    │                │
        │   4. Dispatch ───▶                │
        │                  │  5. Execute    │
        │                  ◀─── 6. Respond  │
        │   7. Normalize   │                │
        │   8. Validate    │                │
        │   9. Respond ────▶                │
        │                  │                │
```

All invocations traverse a fixed **pipeline** of stages. Each stage either passes (enriching context) or fails (returning a typed error, aborting the pipeline). The pipeline is an architectural construct — its stages are responsibilities, not implementation modules.

#### Pipeline Stages (Architectural)

1. **Route** — Resolve capability identifier to execution entry; verify deprecation status.
2. **Authorize** — Verify caller identity, evaluate policy binding, check quotas.
3. **Validate Request** — Validate arguments against declared input schema.
4. **Execute** — Dispatch to capability endpoint; apply timeout, retry, circuit breaker.
5. **Validate Response** — Validate capability output against declared output schema.
6. **Normalize** — Transform to canonical Result Envelope.
7. **Emit Observability** — Emit completion event, record metrics.

For streaming capabilities, stages 4–6 operate incrementally per chunk, with a final completion chunk.

#### Cancellation Model

Callers **MAY** cancel in-flight invocations. SkillService **SHALL** propagate cancellation to the capability process and **SHALL** emit an `InvocationCancelled` observability event. Cancellation **SHALL NOT** corrupt the execution index or affect other invocations.

### 6.3.14 Security Responsibilities

SkillService enforces security at the **execution boundary**:

| Security Concern | SkillService Responsibility |
|------------------|----------------------------|
| Caller authentication | Verified at ingress (gateway); re-verified at SkillService entry |
| Caller authorization | Policy evaluation against capability's policy binding |
| Capability isolation | Capabilities execute in untrusted processes; responses treated as untrusted input |
| Data protection | Request/response payloads validated against schemas; size limits enforced |
| Audit integrity | All invocations emit immutable audit events with correlation identity |
| Transport security | Capability endpoints invoked over mutually authenticated channels |

SkillService **SHALL NOT** delegate any of these responsibilities to callers or capabilities.

### 6.3.15 Resource Responsibilities

| Resource | Responsibility |
|----------|----------------|
| Execution index memory | SkillService owns lifecycle; bounded by capability count and schema size |
| Event stream consumer position | SkillService manages position tracking; consistent projection semantics |
| In-flight invocation state | SkillService tracks fortimeout, cancellation, observability; bounded by concurrency limits |
| Policy evaluation cache | SkillService manages; invalidated on policy update events |
| Schema validator cache | SkillService manages; keyed by schema identifier; invalidated on capability update |

Resource exhaustion **SHALL** trigger graceful degradation per Section 6.3.10, not catastrophic failure.

### 6.3.16 Failure Containment

Failure domains are strictly isolated by architectural boundary:

| Failure Domain | Containment Boundary |
|----------------|---------------------|
| Capability process crash | Affects only that invocation; index unchanged; other invocations proceed |
| Capability timeout | Affects only that invocation; circuit breaker state updated |
| Capability schema violation | Affects only that invocation; validation error returned |
| Policy service unavailable | Degraded mode per policy domain (fail-open or fail-closed); index unaffected |
| Event stream unavailable | Index serves stale data; staleness events emitted; no index corruption |
| SkillService process crash | Index rebuilt from event log on restart; no capability state lost |

The execution index is **immutable per projection cycle** — it is reconstructed atomically from the event log and updated atomically. No capability execution can corrupt it.

### 6.3.17 Architecture Decision Records

#### ADR-6.3.1: Unidirectional SkillManager → SkillService Dependency

**Status**: Accepted

**Context**: The Capability Facade has two planes (Definition, Execution). The dependency direction between their owning components must be decided.

**Decision**: SkillManager publishes events; SkillService consumes. Zero reverse dependency.

**Consequences**:
- Definition Plane remains pure — no execution concerns leak into SkillManager.
- SkillService can be independently versioned and substituted.
- SkillService operates with bounded staleness (T_index_max).
- SkillManager cannot query execution health directly (by design).

#### ADR-6.3.2: Exact Schema Validation at Facade

**Status**: Accepted

**Context**: Whether SkillService should coerce, transform, or relax request payloads to match capability schemas.

**Decision**: Validation is exact — the schema declared at registration is the schema enforced at invocation. No coercion, transformation, default injection, or inference.

**Consequences**:
- Capability authors have certainty: what they declare is what they receive.
- No hidden transformation logic to debug or version.
- Schema evolution requires explicit capability version bump.
- Callers must conform exactly to declared schemas.

#### ADR-6.3.3: Canonical Execution Result Contract

**Status**: Accepted

**Context**: How to unify heterogeneous capability response formats (unary, streaming, error, partial) for Engineering Service consumers.

**Decision**: All invocations return a **canonical execution result contract** with three variants: Success, Error, Streaming. The contract carries metadata (correlation ID, execution time, attempt count, policy decisions, cache status).

**Consequences**:
- Engineering Services handle one response model regardless of capability implementation.
- Observability, retry logic, and error handling are uniform.
- Capability authors cannot leak implementation-specific response formats.

#### ADR-6.3.4: Streaming as First-Class Invocation Mode

**Status**: Accepted

**Context**: Whether streaming capabilities are a separate API or a variant of the invocation pipeline.

**Decision**: Streaming is a first-class invocation mode within the same pipeline. The pipeline operates incrementally for streaming capabilities (per-chunk validation, per-chunk timeout, completion chunk). The Execution Contract exposes both unary and streaming entry points.

**Consequences**:
- Single policy enforcement point for both modes.
- Unified correlation tracking and observability.
- Capability authors declare streaming in manifest; SkillService handles streaming interaction mechanics.

### 6.3.18 Conformance Requirements

A SkillService implementation conforms to this specification **iff** all of the following hold:

#### Invariant Conformance
- [ ] **INV-6.3.1**: Zero dependency on SkillManager APIs; consumes only registration event stream.
- [ ] **INV-6.3.2**: All Engineering Service invocations route through SkillService; no bypass path exists.
- [ ] **INV-6.3.3**: Execution index is read-only projection; no registration writes performed.
- [ ] **INV-6.3.4**: All execution policies enforced at SkillService; none delegated to callers or capabilities.
- [ ] **INV-6.3.5**: Capability failures cannot corrupt index or affect unrelated invocations.
- [ ] **INV-6.3.6**: Index staleness ≤ T_index_max (measurable, configurable, alerted).
- [ ] **INV-6.3.7**: Input validation uses exact registered schema; no coercion or transformation.
- [ ] **INV-6.3.8**: All invocations return canonical execution result contract.
- [ ] **INV-6.3.9**: Correlation identity generated/propagated end-to-end; emitted in all observability.

#### Event Space Conformance
- [ ] Consumes all four SkillManager registration event types in order.
- [ ] Produces all five execution observability event types.
- [ ] Event processing is idempotent and maintains consistent projection state.

#### Pipeline Conformance
- [ ] Pipeline stages execute in defined order with fail-fast semantics.
- [ ] Request validation occurs before dispatch; response validation occurs after receipt.
- [ ] Timeout, retry, and circuit breaker policies applied per capability policy binding.
- [ ] Cancellation propagated to capability; index unaffected.

#### Lifecycle Conformance
- [ ] Bootstraps index from event log before entering Serving state.
- [ ] Enters Degraded mode on dependency loss; emits staleness events.
- [ ] Drains in-flight invocations on shutdown within grace period.
- [ ] Preserves index state for fast restart.

#### Security Conformance
- [ ] Verifies caller authentication at entry.
- [ ] Evaluates authorization policy per capability binding.
- [ ] Treats capability responses as untrusted; validates against output schema.
- [ ] Enforces request/response size limits.
- [ ] Invokes capabilities over mutually authenticated channels.

#### Observability Conformance
- [ ] Emits `InvocationStarted` and `InvocationCompleted`/`InvocationFailed` for every invocation.
- [ ] Emits `PolicyViolation` for every policy denial.
- [ ] Emits `SchemaValidationFailed` for every validation failure.
- [ ] Emits metrics for invocation count, duration, in-flight, error rates, staleness, policy latency, validation latency, circuit breaker state.

#### Runtime Conformance
- [ ] Horizontally scalable without session affinity (execution index is read-only projection).
- [ ] Supports concurrent instantiation without coordination (parallel bootstrap capability).
- [ ] Health assessment distinguishes liveness, readiness, and index currency.

---

*End of Architecture Specification Part 6 — Step 3*