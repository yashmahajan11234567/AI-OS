# Architecture Specification Part 6 — Step 4: MCPService Architecture

## 6.4 MCPService: The MCP Execution Facade

### 6.4.1 Purpose

The **MCPService** exists to resolve the fundamental architectural tension between *capability definition* and *capability execution* for external capabilities within the AI-OS Capability Facade (Section 5.1).

The **MCPManager** (Section 6.2) owns the **Definition Plane** — the static topology of external capability providers and capabilities including registration, manifest validation, capability discovery, versioning, dependency resolution, and lifecycle governance. It operates on declarative artifacts: provider manifests, capability schemas, and registration graphs.

**Engineering Services** (Part 4) operate in the **Execution Plane** — they must *invoke* external capabilities at runtime, supplying arguments and receiving results. They require a stable, uniform invocation surface that is insulated from the volatility and complexity of provider registration mechanics, manifest validation logic, communication mechanism heterogeneity, protocol negotiation, and persistence concerns.

These two planes **MUST NOT** communicate directly. Direct coupling would violate the Capability Facade principle: Engineering Services would become dependent on MCPManager's internal representation of external providers and capabilities, creating transitive dependencies on concerns orthogonal to execution.

MCPService solves the **External Capability Execution Facade Problem**: how to present a stable, authoritative invocation surface to Engineering Services while maintaining strict separation from the Definition Plane and enforcing the external boundary against untrusted capability providers.

Without MCPService, the architecture faces three architecturally unacceptable alternatives:

1. **Engineering Services import MCPManager directly** — violating layer separation, leaking registration concerns into execution logic, and making external capability invocation inseparable from provider discovery.

2. **Engineering Services invoke external capabilities via raw Event Space messages** — requiring each service to implement protocol-level message construction, communication mechanism selection, protocol handshake, correlation tracking, timeout handling, and error normalization across heterogeneous mechanisms, duplicating infrastructure logic across every consumer.

3. **External providers self-register execution endpoints** — inverting control, scattering invocation logic across provider implementations, and preventing centralized observability, policy enforcement, communication security, and routing optimization.

MCPService eliminates these alternatives by providing a **single, mandatory execution facade** that all Engineering Services **SHALL** use for all external capability invocations. It is the **sole architectural boundary** between the trusted AI-OS Execution Plane and untrusted external capability providers.

### 6.4.2 Architectural Position

Within the AI-OS layered architecture (Part 1), MCPService occupies a mediating position between two architectural planes:

| Plane | Responsibility | Representative Component |
|-------|----------------|--------------------------|
| **Definition Plane** | External provider registration, manifest validation, capability discovery, versioning, lifecycle governance | MCPManager |
| **Execution Plane** | Capability invocation, external communication management, protocol translation, argument validation, result normalization, policy enforcement | MCPService |

MCPService is the **sole component** that bridges these planes. It consumes MCPManager's registration events to maintain an **execution index** — a read-optimized projection of the external provider and capability graph optimized for invocation-time decisions (routing, protocol translation, validation, policy lookup). It does not modify registration state; it only projects it.

This unidirectional dependency is an **architectural invariant**:

> **INV-6.4.1 (Unidirectional Dependency — Definition Plane)**: MCPManager **SHALL NOT** depend on MCPService. MCPService **SHALL** depend on MCPManager's published registration events only.

### 6.4.3 Role Within the Capability Facade

The Capability Facade (Section 5.1) presents two distinct interfaces to two distinct consumer classes:

| Facade Interface | Owner | Consumers | Plane |
|------------------|-------|-----------|-------|
| **Definition Contract** (register provider, discover capabilities, validate manifest, version, deprecate) | MCPManager | Platform operators, CI/CD pipelines, external capability provider authors | Definition Plane |
| **Execution Contract** (invoke, stream, cancel, health, metrics, external communication binding) | MCPService | Engineering Services, external integrations, AI agents | Execution Plane |

MCPService **owns the Execution Contract entirely**. It defines the invocation contract, error taxonomy, timeout semantics, streaming protocol, cancellation model, correlation identity model for distributed tracing, and external communication binding abstraction. These are *execution concerns* — they do not exist in the Definition Plane.

### 6.4.4 Relationship to MCPManager

The MCPManager–MCPService relationship is **publisher/subscriber**, not client/server:

- **MCPManager** publishes provider registration, capability discovery, manifest update, and provider deprecation/removal events to the Event Space (Part 4).
- **MCPService** subscribes to these events to maintain its execution index.
- **MCPService** **SHALL NOT** invoke MCPManager APIs, query MCPManager directly, or import MCPManager types. It operates exclusively on the *eventually consistent* projection built from the event stream.

This design ensures:
- **Temporal decoupling**: MCPService remains operational during MCPManager maintenance windows.
- **Failure isolation**: MCPManager failures do not cascade into execution failures (provided the execution index is current).
- **Scalability independence**: MCPService can scale horizontally for invocation throughput without affecting registration throughput.
- **Protocol insulation**: Changes to external capability protocol versions or communication mechanisms are absorbed at the MCPService boundary without affecting MCPManager.

### 6.4.5 External Tool Integration Constraint

The prohibition on direct Engineering Service–MCPManager communication is absolute, extended with the external boundary constraint:

> **REQ-6.4.1 (Execution Monopoly — External Capabilities)**: Engineering Services **SHALL NOT** import, reference, or communicate with MCPManager under any circumstances. All external capability invocations **SHALL** transit MCPService.

> **REQ-6.4.2 (External Boundary Enforcement)**: Engineering Services **SHALL NOT** communicate directly with external capability providers via external capability protocol, raw communication mechanisms, or any other mechanism. All external capability interactions **SHALL** transit MCPService.

Rationale:
- **Interface Segregation**: Engineering Services require execution semantics (invoke, stream, cancel, timeout). MCPManager exposes registration semantics (register provider, discover capabilities, validate manifest, query). These are disjoint concerns.
- **Stability**: MCPManager's APIs evolve with the registration model. MCPService's execution API is stable — it changes only when the *invocation contract* changes.
- **Policy Centralization**: Cross-cutting execution policies (authentication, rate limiting, circuit breaking, observability, audit logging, communication security, payload size limits) **MUST** be enforced at a single choke point. MCPService is that choke point.
- **Substitutability**: MCPService can be stubbed, mocked, or replaced (e.g., with a local executor for development) without touching MCPManager.
- **Security Isolation**: External capability providers are untrusted. MCPService is the **sole trust boundary** — it validates all inbound responses, enforces schema conformance, applies size limits, and sanitizes errors before they enter the AI-OS trust domain.

### 6.4.6 Architectural Responsibilities

MCPService bears the following **architectural responsibilities** (concerns, not implementations):

| Responsibility | Description |
|----------------|-------------|
| **Invocation Routing** | Resolving a capability identifier to its external provider, communication mechanism binding, and authentication context using the execution index. |
| **External Communication Management** | Negotiating and managing the communication mechanism to the target external provider; abstracting communication heterogeneity from callers. |
| **External Protocol Translation** | Translating the canonical AI-OS invocation contract into the external capability protocol and translating external responses/errors into the canonical execution result contract. |
| **Contract Enforcement** | Validating that invocation arguments conform to the capability's declared input schema before dispatch; validating responses against the declared output schema. |
| **Policy Application** | Applying cross-cutting execution policies (authorization, rate limits, timeouts, retries, circuit breaking, payload size limits) uniformly. |
| **Result Normalization** | Transforming raw external responses into the **canonical execution result contract** (success, error, streaming). |
| **Correlation Tracking** | Maintaining end-to-end invocation identity across asynchronous communication boundaries for observability and debugging. |
| **Provider Lifecycle Isolation** | Ensuring external provider failures (crash, timeout, protocol error) cannot corrupt the execution index or affect other invocations. |
| **Index Freshness** | Guaranteeing the execution index reflects registration state within a bounded staleness window. |
| **External Credential Management** | Managing authentication credentials for external providers; injecting credentials into communication mechanisms without exposing them to callers. |

### 6.4.7 Architectural Invariants

The following invariants define MCPService's architectural contract. They are **necessary conditions** for the Capability Facade architecture to hold:

> **INV-6.4.1 (Unidirectional Dependency — Definition Plane)**: MCPService depends on MCPManager's events; MCPManager has zero dependency on MCPService.

> **INV-6.4.2 (Unidirectional Dependency — External Boundary)**: External capability providers have zero dependency on MCPService internals. MCPService treats all external providers as untrusted.

> **INV-6.4.3 (Execution Monopoly)**: All external capability invocations from Engineering Services transit MCPService. No alternative execution path exists.

> **INV-6.4.4 (Index Read-Only)**: MCPService's execution index is derived exclusively from MCPManager's published events. MCPService never writes registration state.

> **INV-6.4.5 (Policy Completeness)**: Every execution policy applicable to external capability invocation is enforced at MCPService. No policy enforcement is delegated to callers or external providers.

> **INV-6.4.6 (Failure Containment)**: An external provider's execution failure (crash, timeout, protocol error, communication failure) cannot cause MCPService to lose its execution index, drop unrelated invocations, or publish spurious registration events.

> **INV-6.4.7 (Staleness Bound)**: The execution index reflects MCPManager's registration state with a maximum staleness of **T_index_max**. Engineering Services observe at-most **T_index_max** delay for new external capabilities to become invocable.

> **INV-6.4.8 (Schema Fidelity)**: MCPService validates invocation arguments against the *exact* input schema declared in the capability's registered manifest. No schema transformation, relaxation, coercion, or inference occurs at the facade.

> **INV-6.4.9 (Result Canonicality)**: All invocations return the **canonical execution result contract**. No external-protocol-specific response formats escape MCPService.

> **INV-6.4.10 (Correlation Completeness)**: Every invocation carries a correlation identity that is propagated to the external provider (via protocol metadata), emitted in all observability signals, and returned to the caller.

> **INV-6.4.11 (Communication Mechanism Transparency)**: Engineering Services invoke capabilities through a communication-agnostic contract. MCPService absorbs all communication mechanism heterogeneity. No mechanism-specific concerns leak to callers.

> **INV-6.4.12 (Untrusted Response)**: Every response from an external capability provider is treated as untrusted input. MCPService **SHALL** validate against the declared output schema, enforce size limits, and sanitize error payloads before returning to the caller.

These invariants are **architectural law**. Implementation decisions that violate them constitute architectural defects, regardless of functional correctness.

### 6.4.8 Event Space Interactions

MCPService participates in the Event Space (Part 4) as both consumer and producer:

#### Consumed Events (from MCPManager)

| Event | Purpose |
|-------|---------|
| `ExternalProviderRegistered` | New external capability provider available for capability execution |
| `ExternalProviderUpdated` | Provider metadata, capabilities, or communication binding changed |
| `ExternalProviderDeprecated` | Provider entering deprecation grace period |
| `ExternalProviderRemoved` | Provider removed after grace period expiry |
| `ExternalCapabilityDiscovered` | New capability version available on registered provider |
| `ExternalCapabilityUpdated` | Capability schema, metadata, or version changed |
| `ExternalCapabilityDeprecated` | Capability version entering deprecation grace period |
| `ExternalCapabilityRemoved` | Capability version removed after grace period expiry |

MCPService **SHALL** process these events in order, maintaining the execution index as a faithful projection.

#### Produced Events (to Event Space)

| Event | Purpose |
|-------|---------|
| `ExternalInvocationStarted` | Invocation admitted to execution pipeline |
| `ExternalInvocationCompleted` | Invocation terminated (success, error, or cancellation) |
| `ExternalInvocationStreamChunk` | Streaming chunk emitted for streaming capabilities |
| `ExternalPolicyViolation` | Policy enforcement denied an invocation |
| `ExternalSchemaValidationFailed` | Request or response failed schema validation |
| `ExternalCommunicationError` | Communication-level failure (connection refused, protocol error, timeout) |
| `ExternalProviderUnhealthy` | Provider health check failed; circuit breaker state change |
| `ExecutionIndexStalenessExceeded` | Index freshness SLO breach detected |

These events enable platform observability, audit, and automated remediation without coupling consumers to MCPService internals.

### 6.4.9 Manager Space Interactions

MCPService **SHALL NOT** directly invoke Manager Space components (Part 2). Its only Manager Space interaction is indirect, via the Event Space:

- It consumes MCPManager's registration events.
- It produces execution observability events consumed by platform managers (e.g., MonitoringManager, AuditManager, SecurityManager).

This preserves the Manager Space / Event Space separation defined in Part 2.

### 6.4.10 Lifecycle

MCPService lifecycle is defined by three states:

| State | Entry Condition | Exit Condition |
|-------|-----------------|----------------|
| **Bootstrapping** | Process start | Execution index built from event log and published |
| **Serving** | Index published, health checks passing | Shutdown signal or index corruption detected |
| **Degraded** | Dependency unavailable (event stream, policy service, auth service) | Dependency restored or graceful shutdown |

**Bootstrapping**: On startup, MCPService **SHALL** reconstruct its execution index by consuming the registration event stream from the last known consistent position. It **SHALL NOT** enter Serving state until the index reflects all events up to the stream head.

**Serving**: MCPService accepts invocations, maintains index currency via event consumption, and emits observability events.

**Degraded**: If the event stream becomes unavailable, MCPService **SHALL** continue serving from its last consistent index while emitting `ExecutionIndexStalenessExceeded` events. If staleness exceeds a configured threshold, it **SHALL** transition to a safe mode (rejecting invocations for capabilities not in index, or failing open/closed per policy domain configuration).

**Shutdown**: On termination signal, MCPService **SHALL** drain in-flight invocations (up to a configured grace period), flush pending observability events, and persist its index position for fast restart.

### 6.4.11 Ownership Boundaries

| Concern | Owner | MCPService Role |
|---------|-------|-----------------|
| External provider manifest | MCPManager | Consumer (read-only projection) |
| External capability schema | MCPManager | Consumer (exact enforcement) |
| External provider communication binding | MCPManager | Consumer (routing target) |
| Execution policy | Policy Manager (Part 2) | Consumer (enforcement point) |
| Invocation execution | External provider process | Orchestrator (dispatch, timeout, retry, circuit break) |
| Invocation result | External provider process | Transformer (normalization, validation) |
| Authentication credentials | Secret Manager (Part 2) | Consumer (injection at communication binding) |
| Observability emission | MCPService | Producer (canonical events) |
| Correlation identity | MCPService | Generator / propagator |
| Communication mechanism lifecycle | MCPService | Owner (per provider pool) |

MCPService **owns** the Execution Contract, the canonical execution result contract, the External ErrorCode taxonomy, the correlation identity model, the execution index data structure, and the communication mechanism pools. It **does not own** external provider definitions, capability schemas, communication configurations, policy definitions, or authentication secrets — it consumes and enforces them.

### 6.4.12 Dependency Rules

| Dependency | Direction | Type | Rationale |
|------------|-----------|------|-----------|
| MCPManager → MCPService | **Forbidden** | — | Preserves Definition Plane purity |
| MCPService → MCPManager (events) | **Required** | Event subscription | Index currency |
| MCPService → Policy Manager | **Required** | Policy consumption | Policy enforcement |
| MCPService → Secret Manager | **Required** | Credential consumption | External credential management |
| MCPService → Event Space | **Required** | Infrastructure | Event consumption/production |
| Engineering Service → MCPService | **Required** | API invocation | Execution monopoly |
| Engineering Service → MCPManager | **Forbidden** | — | Facade integrity |
| Engineering Service → External Capability Provider | **Forbidden** | — | External boundary enforcement |
| External Capability Provider → MCPService | **None** | — | External providers are opaque executables |

### 6.4.13 Communication Model

MCPService communication follows the **Request–Response** and **Request–Stream** patterns over the **Event Space communication model** (Part 4). The Execution Contract is **communication-agnostic** — it defines the logical interaction, not the wire protocol. The external capability protocol is an implementation detail internal to MCPService.

#### Invocation Model

```
Engineering Service → MCPService → External Provider
        │                  │              │
        │   1. Route       │              │
        │   2. Authorize   │              │
        │   3. Validate    │              │
        │   4. Dispatch    ──────▶        │
        │                  │  5. Execute  │
        │                  ◀──── 6. Respond │
        │   7. Validate Response          │
        │   8. Normalize                   │
        │   9. Respond ──────▶             │
        │                  │              │
```

All invocations traverse a fixed **pipeline** of stages. Each stage either passes (enriching context) or fails (returning a typed error, aborting the pipeline). The pipeline is an architectural construct — its stages are responsibilities, not implementation modules.

#### Pipeline Stages (Architectural)

1. **Route** — Resolve capability identifier to external provider, communication binding, and authentication context; verify deprecation status.
2. **Authorize** — Verify caller identity, evaluate policy binding, check quotas.
3. **Validate Request** — Validate arguments against declared input schema.
4. **Dispatch** — Dispatch request via external capability protocol; apply timeout, retry, circuit breaker.
5. **Validate Response** — Validate response against declared output schema; enforce size limits.
6. **Normalize** — Transform to canonical Result Envelope.
7. **Emit Observability** — Emit completion event, record metrics.

For streaming capabilities, stages 4–6 operate incrementally per chunk, with a final completion chunk.

#### Cancellation Model

Callers **MAY** cancel in-flight invocations. MCPService **SHALL** propagate cancellation to the external provider (via protocol cancellation or communication termination) and **SHALL** emit an `ExternalInvocationCancelled` observability event. Cancellation **SHALL NOT** corrupt the execution index or affect other invocations.

### 6.4.14 Security Responsibilities

MCPService enforces security at the **execution boundary** and **external boundary**:

| Security Concern | MCPService Responsibility |
|------------------|---------------------------|
| Caller authentication | Verified at ingress (gateway); re-verified at MCPService entry |
| Caller authorization | Policy evaluation against capability's policy binding |
| External provider authentication | Credential injection at communication binding; mutual authentication where configured |
| Provider identity verification | Identity validation per communication mechanism |
| Capability isolation | External providers execute in untrusted processes; responses treated as untrusted input |
| Data protection | Request/response payloads validated against schemas; size limits enforced |
| Audit integrity | All invocations emit immutable audit events with correlation identity |
| Communication security | External provider endpoints invoked over mutually authenticated channels |
| Credential isolation | Callers never receive external provider credentials; injected only at communication layer |
| Protocol validation | Strict external capability protocol compliance; malformed responses rejected |

MCPService **SHALL NOT** delegate any of these responsibilities to callers or external providers.

### 6.4.15 Resource Responsibilities

| Resource | Responsibility |
|----------|----------------|
| Execution index memory | MCPService owns lifecycle; bounded by provider count, capability count, schema size |
| Event stream consumer position | MCPService manages position tracking; consistent projection semantics |
| In-flight invocation state | MCPService tracks for timeout, cancellation, observability; bounded by concurrency limits |
| Communication mechanism pools | MCPService manages per-provider pools; lifecycle tied to provider registration state |
| Policy evaluation cache | MCPService manages; invalidated on policy update events |
| Schema validator cache | MCPService manages; keyed by schema identifier; invalidated on capability update |
| External protocol session state | MCPService manages per-connection; includes initialization state, negotiated version |

Resource exhaustion **SHALL** trigger graceful degradation per Section 6.4.10, not catastrophic failure.

### 6.4.16 Failure Containment

Failure domains are strictly isolated by architectural boundary:

| Failure Domain | Containment Boundary |
|----------------|---------------------|
| External provider process crash | Affects only in-flight invocations to that provider; index unchanged; other providers proceed |
| External provider timeout | Affects only that invocation; circuit breaker state updated per provider |
| External provider protocol violation | Affects only that invocation; validation error returned; provider marked unhealthy |
| Communication mechanism failure | Affects only invocations using that mechanism; pool replenished; circuit breaker updated |
| External provider authentication failure | Affects only that provider's invocations; auth failure event emitted; no credential leakage |
| Schema validation failure (request) | Affects only that invocation; validation error returned to caller |
| Schema validation failure (response) | Affects only that invocation; validation error returned; provider marked unhealthy |
| Event stream unavailability | Degraded mode: serve from last consistent index; emit staleness events |
| Policy service unavailability | Degraded mode: fail closed (deny) or fail open per policy domain configuration |

### 6.4.17 Architecture Decision Records

| ADR | Title | Decision |
|-----|-------|----------|
| ADR-6.4.1 | MCPService as Execution Facade | MCPService is the sole execution facade for external capabilities; separates Definition Plane from Execution Plane. |
| ADR-6.4.2 | Publisher/Subscriber with MCPManager | MCPManager publishes events; MCPService subscribes. No direct API calls. |
| ADR-6.4.3 | External Providers as Untrusted | All external capability providers are untrusted; responses validated, size-limited, sanitized. |
| ADR-6.4.4 | Communication Abstraction | MCPService abstracts communication mechanisms behind a uniform execution contract. |
| ADR-6.4.5 | Canonical Result Contract | All external responses normalized to canonical Result Envelope; no protocol-specific formats escape. |
| ADR-6.4.6 | Correlation Identity Propagation | Correlation ID generated at ingress; propagated to external provider via protocol metadata; emitted in all events. |
| ADR-6.4.7 | Index Staleness SLO | Maximum index staleness T_index_max is an architectural SLO; breach triggers Degraded mode. |
| ADR-6.4.8 | Circuit Breaking per Provider | Circuit breaker state maintained per external provider; isolates cascading failures. |
| ADR-6.4.9 | Credential Injection at Communication Layer | External provider credentials injected at communication binding; never visible to callers or capability logic. |
| ADR-6.4.10 | Streaming as First-Class Contract | Streaming capabilities use incremental pipeline stages with chunk-level validation and normalization. |

### 6.4.18 Conformance Requirements

A conforming MCPService implementation **SHALL** satisfy all of the following:

1. **Invariant Compliance** — All invariants in Section 6.4.7 hold under all execution conditions.
2. **Interface Compliance** — The Execution Contract defined by MCPService is the *only* invocation path for Engineering Services.
3. **Event Compliance** — All consumed events are processed in order; all produced events are emitted with canonical schema.
4. **Pipeline Compliance** — Every invocation traverses all pipeline stages in order; no stage is bypassed.
5. **Staleness Compliance** — Index staleness never exceeds T_index_max without transitioning to Degraded state.
6. **Schema Compliance** — Request and response validation uses exact declared schemas; no coercion or relaxation.
7. **Communication Compliance** — Callers cannot detect or depend on the underlying external communication mechanism.
8. **Security Compliance** — All security responsibilities in Section 6.4.14 are enforced at MCPService; none delegated.
9. **Failure Compliance** — Failure domains in Section 6.4.16 are isolated; no single provider failure affects unrelated invocations.
10. **Lifecycle Compliance** — State transitions follow Section 6.4.10; Bootstrapping completes before Serving; Shutdown drains gracefully.