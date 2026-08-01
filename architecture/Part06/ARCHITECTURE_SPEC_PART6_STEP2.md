# AI-OS Architecture Specification v1.0
## Part 6: Capability Facade Services Architecture — Section 6.2

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-28  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  

---

# 6.2 Capability Architecture Overview

This section defines the canonical architecture that every Capability Facade Service MUST follow.

This section is NOT about any specific facade implementation.

Instead, it defines the common architectural model shared by:

- SkillService
- MCPService
- MemoryService
- CouncilService

---

## 6.2.1 Capability Abstraction Philosophy

### Why Capabilities Are Abstracted

Capabilities represent cross-cutting operational functions (skill execution, council governance, MCP tool invocation, memory operations) that multiple Engineering Services consume. Without abstraction, each Engineering Service would embed manager-specific access logic, creating:

- **Tight coupling** between SDLC phase logic and infrastructure access patterns
- **Duplication** of translation, error handling, and observability code across services
- **Inability** to replace or evolve Capability Managers without modifying all consumers
- **Violation** of Part 0 Principle 1 (Event-First Communication) — Services would call Managers directly

The Capability Facade Services layer exists to **abstract the Manager Space behind a stable, event-driven contract**. Consumers (Engineering Services) interact exclusively with event types; they never reference Manager interfaces, method signatures, or provider implementations.

### Separation Between Event Space and Manager Space

AI-OS enforces a strict architectural boundary between two communication domains:

| Domain | Communication Mechanism | Participants | Governance |
|--------|------------------------|--------------|------------|
| **Event Space** | EventBus (typed, correlated, immutable Events) | Engineering Services, Capability Facade Services, Core Components, Application Services | Part 2 (Event System), Part 5 (Service Framework) |
| **Manager Space** | Singleton Accessor method calls (`kernel.manager.method()`) | Capability Managers (9), Core Components (4), LifecycleManager | Part 1 (Kernel Architecture), Part 4 (Core Managers) |

**Invariant:** `INV-CFS-DOMAIN-001` — No entity in Event Space MAY directly invoke methods on any Capability Manager. All Manager Space access MUST be mediated by exactly one Capability Facade Service.

**Invariant:** `INV-CFS-DOMAIN-002` — No Capability Manager MAY subscribe to, publish, or otherwise interact with the EventBus. Manager Space is EventBus-free by design (Part 1 §1.7.4 CC-IR-001, Part 4 §4.1 Principle: Event-First).

The Capability Facade Services are the **sole architectural bridge** spanning this boundary. They:
- Reside in Event Space (extend `BaseService`, register in `ServiceRegistry`, subscribe/publish on EventBus)
- Access exactly one Capability Manager via kernel singleton accessor during event handler execution
- Translate event payloads ↔ Manager method calls with zero business logic

### Stable Abstraction Boundary

The abstraction boundary is defined by the **event contract** — the set of EventTypes a Capability Facade Service subscribes to and emits. This contract:

- **MUST** remain stable across Manager implementation changes
- **MUST** be versioned per Part 2 §2.10 (Event Schema Versioning)
- **MUST NOT** leak Manager-specific concepts (method names, internal types, provider details) into event payloads
- **MUST** be defined in Part 2 (Event System), not in facade implementation

**Invariant:** `INV-CFS-BOUNDARY-001` — Event payloads consumed and emitted by Capability Facade Services MUST contain only domain-level concepts (e.g., `skillId`, `input`, `result`), never Manager-internal concepts (e.g., `executionHandle`, `providerContext`, `retryToken`).

### Provider Independence

Capabilities MAY be backed by multiple interchangeable providers (e.g., multiple LLM providers for skill execution, multiple storage backends for memory). The abstraction layer:

- **Hides** provider identity, selection logic, and failover from consumers
- **Exposes** only the capability façade contract (event types + payload schemas)
- **Delegates** provider selection to CapabilityManager (Part 4 §4.8) at resolution time
- **Ensures** that swapping providers requires zero changes to Engineering Services

**Invariant:** `INV-CFS-PROVIDER-001` — No event payload emitted by a Capability Facade Service SHALL contain provider-specific fields, identifiers, or metadata. Provider selection is an implementation concern of CapabilityManager.

### Technology Independence

The abstraction layer MUST NOT couple event contracts to specific technologies, protocols, or runtimes:

- Event types MUST NOT encode transport details (HTTP, gRPC, WebSocket, IPC)
- Payload schemas MUST NOT reference technology-specific types (e.g., no `grpc.StatusCode`, no `http.Header`)
- Facade Services MUST be implementable on any EventBus-compatible substrate (Part 0 §0.2.2 — distributed EventBus is v2.0 scope)

**Invariant:** `INV-CFS-TECH-001` — Capability Facade Service event contracts MUST be expressible in pure JSON Schema with no technology-dependent extensions.

### Replaceability

A Capability Manager MAY be replaced with a fundamentally different implementation (different algorithm, data store, provider ecosystem) without affecting Engineering Services, provided:

1. The replacement Manager satisfies the same capability façade contract
2. The corresponding Capability Facade Service translation logic is updated to map events to the new Manager's interface
3. The event contract (EventTypes, payload schemas, correlation semantics) remains unchanged

**Invariant:** `INV-CFS-REPLACE-001` — Engineering Services MUST NOT require modification when a Capability Manager is replaced, provided the Capability Facade Service's emitted event contract is preserved.

### Extensibility

New capabilities MAY be added to AI-OS through the governed extension process (Part 0 §0.5.2):

| Extension Point | Governance |
|-----------------|------------|
| New Capability Manager + Facade pair | ARB approval required (Part 1 EXT-002, Part 6.1 INV-CFS-FUTURE-001) |
| New event types for existing facade | Part 2 §2.3 event catalog extension process |
| New payload fields (minor version) | Backward-compatible per Part 2 §2.10 |
| New provider for existing capability | CapabilityManager registration (Part 4 §4.8.3) |

**Invariant:** `INV-CFS-EXT-001` — Adding a new Capability Facade Service REQUIRES adding a corresponding new Capability Manager. Standalone facades are forbidden (Part 6.1 INV-CFS-BRIDGE-002).

---

## 6.2.2 Capability Taxonomy

### Capability Categories

Capabilities are classified into four categories based on their operational role in the SDLC pipeline (Part 5 §5.1):

| Category | Definition | Facade Service | Core Manager |
|----------|------------|-----------------|--------------|
| **Execution** | Invokes reusable, sandboxed logic units with defined inputs/outputs | SkillService | SkillManager |
| **Governance** | Coordinates multi-agent consensus, decision-making, escalation | CouncilService | CouncilManager |
| **Integration** | Invokes external tools, APIs, and protocols via standardized transport | MCPService | MCPManager |
| **State** | Manages persistent and ephemeral memory across workflow lifecycles | MemoryService | MemoryManager |

### Capability Domains

Each category maps to a distinct **Capability Domain** — a bounded context with its own data model, lifecycle, and invariants:

| Domain | Scope | Primary Artifacts | Invariants |
|--------|-------|-------------------|------------|
| **Skill Execution** | Stateless, deterministic, sandboxed computation units | Skill definitions, execution results, sandbox metrics | Idempotency (per skill contract), resource isolation, timeout enforcement |
| **Council Governance** | Multi-party consensus with audit trail and human escalation | Proposals, votes, decisions, dissent records, escalation artifacts | Quorum validity, decision finality, audit completeness |
| **MCP Integration** | External tool/protocol invocation with permission mediation | Tool calls, results, permission grants, transport metadata | Capability sandboxing, permission least-privilege, result serialization |
| **Memory Operations** | Multi-tier storage with retention, consolidation, and retrieval | Memory records, context assemblies, consolidation artifacts, indices | Retention compliance, referential integrity, retrieval consistency |

### Ownership

Each Capability Domain has a single owning Capability Manager (Part 4 §4.2.6 Ownership Boundaries) and a single owning Capability Facade Service (Part 6.1 §6.1.2):

| Domain | Manager Owner (Manager Space) | Facade Owner (Event Space) | Consumer Services (Engineering Services) |
|--------|-------------------------------|----------------------------|------------------------------------------|
| Skill Execution | SkillManager | SkillService | PlanningService, CodingService, ReviewService, TestingService |
| Council Governance | CouncilManager | CouncilService | All Engineering Services (via governance gates) |
| MCP Integration | MCPManager | MCPService | CodingService, TestingService, DeploymentService, OperationsService |
| Memory Operations | MemoryManager | MemoryService | ALL Engineering Services (universal dependency) |

**Invariant:** `INV-CFS-OWN-001` — Each Capability Domain SHALL have exactly one Capability Manager and exactly one Capability Facade Service. No shared ownership.

### Scope

The scope of each Capability Facade Service is strictly bounded:

| Facade Service | In Scope | Out of Scope |
|----------------|----------|--------------|
| **SkillService** | Translate `SKILL_EXECUTE_REQUEST` → `SkillManager.execute()`; emit `SKILL_EXECUTED` / `SKILL_FAILED` | Skill definition, sandbox policy, provider selection, retry logic |
| **CouncilService** | Translate council events ↔ `CouncilManager` methods; emit audit events | Consensus algorithm implementation, quorum calculation, escalation policy |
| **MCPService** | Translate `MCP_TOOL_CALL` ↔ `MCPManager.invoke()`; emit `MCP_TOOL_SUCCEEDED` / `MCP_TOOL_FAILED` | Transport implementation, permission evaluation, result caching |
| **MemoryService** | Translate memory events ↔ `MemoryManager` methods; emit memory result events | Storage backend, consolidation algorithm, retention policy, index management |

**Invariant:** `INV-CFS-SCOPE-001` — Capability Facade Services SHALL NOT implement, configure, or influence the out-of-scope concerns listed above. Those belong exclusively to the Capability Manager.

### Taxonomy Summary Table

| Capability Category | Domain | Manager (Space) | Facade (Space) | Event Types Produced | Event Types Consumed | Universal Dependency |
|---------------------|--------|-----------------|----------------|---------------------|----------------------|---------------------|
| **Execution** | Skill Execution | SkillManager (Manager) | SkillService (Event) | `SKILL_EXECUTED`, `SKILL_FAILED` | `SKILL_EXECUTE_REQUEST` | No |
| **Governance** | Council Governance | CouncilManager (Manager) | CouncilService (Event) | `COUNCIL_CONVENED`, `COUNCIL_PROPOSAL_SUBMITTED`, `COUNCIL_VOTE_CAST`, `COUNCIL_CONSENSUS_REACHED`, `COUNCIL_DISSENT_REGISTERED`, `COUNCIL_DECISION_FINALIZED`, `COUNCIL_ESCALATED` | `COUNCIL_CONVENE`, `COUNCIL_SUBMIT_PROPOSAL`, `COUNCIL_CAST_VOTE`, `COUNCIL_ESCALATE` | No (gated) |
| **Integration** | MCP Integration | MCPManager (Manager) | MCPService (Event) | `MCP_TOOL_CALLED`, `MCP_TOOL_SUCCEEDED`, `MCP_TOOL_FAILED` | `MCP_TOOL_CALL` | No |
| **State** | Memory Operations | MemoryManager (Manager) | MemoryService (Event) | `MEMORY_STORED`, `MEMORY_RETRIEVED`, `MEMORY_UPDATED`, `MEMORY_CONSOLIDATED`, `MEMORY_PRUNED` | `MEMORY_STORE`, `MEMORY_RETRIEVE`, `MEMORY_UPDATE`, `MEMORY_CONSOLIDATE`, `MEMORY_PRUNE` | **Yes** (Part 5 INV-ENG-DEP-004) |

---

## 6.2.3 Capability Registration Model

### Registration Lifecycle

Every capability provider (the Capability Manager implementation behind a facade) MUST be registered with the CapabilityManager (Part 4 §4.8) before it can be invoked. The registration lifecycle follows a strict state machine:

```
┌─────────────┐
│ REGISTERING │  (provider submits CapabilityRegisterEvent)
└──────┬──────┘
       │ validation passes
       ▼
┌─────────────┐
│    ACTIVE   │  (available for resolution and invocation)
└──────┬──────┘
       │ deprecation announced
       ▼
┌─────────────┐
│  DEPRECATED │  (excluded from default resolution; grace period active)
└──────┬──────┘
       │ grace period expires OR explicit removal
       ▼
┌─────────────┐
│   DRAINING  │  (no new invocations; completing in-flight)
└──────┬──────┘
       │ in-flight complete OR force timeout
       ▼
┌─────────────┐
│   REMOVED   │  (registry entry archived; no further operations)
└─────────────┘
```

**Invariant:** `INV-CFS-REG-001` — A capability provider SHALL NOT receive invocations while in REGISTERING, DEPRECATED (unless caller opts in), DRAINING, or REMOVED state.

**Invariant:** `INV-CFS-REG-002` — Transition from ACTIVE to DEPRECATED SHALL require a configured grace period (configured by the Configuration Specification) during which both old and new versions MAY coexist.

**Invariant:** `INV-CFS-REG-003` — The CapabilityManager SHALL emit `CapabilityRegisteredEvent`, `CapabilityDeprecatedEvent`, `CapabilityRemovedEvent` at each lifecycle transition (Part 4 §4.8.11).

### Registration Metadata

Each registration MUST include the following metadata fields:

| Field | Type | Requirement | Description |
|-------|------|-------------|-------------|
| `capabilityId` | String | Mandatory | Globally unique identifier (format: `<domain>.<facade>.<name>.v<major>`) |
| `facadeId` | String | Mandatory | Facade contract identifier (e.g., `ai-os.skill.execution.v1`) |
| `providerId` | String | Mandatory | Unique provider instance identifier |
| `version` | SemVer | Mandatory | Provider implementation version |
| `contract` | SchemaRef | Mandatory | Reference to input/output event schemas (Part 2 §2.3) |
| `lifecycleState` | Enum | Mandatory | Current state: `REGISTERING` \| `ACTIVE` \| `DEPRECATED` \| `DRAINING` \| `REMOVED` |
| `resourceProfile` | Object | Mandatory | CPU, memory, GPU, network, LLM quota requirements (Part 4 §4.9) |
| `securityContext` | Object | Mandatory | Required trust level, authentication, authorization policy (Part 4 §4.7) |
| `healthEndpoint` | URI | Optional | Provider health check endpoint (if distinct from manager) |
| `tags` | Map<String,String> | Optional | Discovery tags for selection policies |
| `registeredAt` | ISO8601 | Mandatory | Registration timestamp |
| `deprecatedAt` | ISO8601 | Conditional | Deprecation announcement timestamp (required if DEPRECATED) |
| `owner` | String | Mandatory | Owning team/component identifier |

**Invariant:** `INV-CFS-REG-004` — The `capabilityId` MUST follow the format `<domain>.<facade>.<name>.v<major>` where domain ∈ {`skill`, `council`, `mcp`, `memory`}, facade ∈ {`execution`, `governance`, `integration`, `operations`}.

**Invariant:** `INV-CFS-REG-005` — The `contract` field MUST reference schemas registered in the Event System schema registry (Part 2 §2.3). Unregistered schemas are a registration validation failure.

### Identity

A capability's identity is a composite key:

```
CapabilityIdentity = (capabilityId, providerId)
```

- `capabilityId` identifies the **capability contract** (what the capability does)
- `providerId` identifies the **specific implementation instance** (who provides it)

Multiple providers MAY register for the same `capabilityId` (different `providerId`), enabling load balancing, canary deployments, and failover (Part 4 §4.8.9).

**Invariant:** `INV-CFS-ID-001` — No two registrations SHALL share the same `(capabilityId, providerId)` pair. Duplicate providerId for a given capabilityId is a `CapabilityConflictEvent` (Part 4 §4.8.10).

**Invariant:** `INV-CFS-ID-002` — The `providerId` MUST be unique within the kernel instance. Recommended format: `<manager>.<instance>.<random-suffix>`.

### Versioning

Capability versioning follows **semantic versioning (SemVer 2.0.0)** applied to the provider implementation:

| Version Component | Meaning | Compatibility |
|-------------------|---------|---------------|
| **MAJOR** | Breaking change to provider interface or behavior | INCOMPATIBLE — requires new `capabilityId` |
| **MINOR** | Backward-compatible feature addition | COMPATIBLE — same `capabilityId`, new version |
| **PATCH** | Backward-compatible bug fix | COMPATIBLE — same `capabilityId`, new version |

The `facadeId` encodes the **facade contract version** (always MAJOR only, e.g., `v1`, `v2`). Facade contracts evolve only through governed extension process (Part 0 §0.5.2).

**Invariant:** `INV-CFS-VER-001` — CapabilityManager resolution (Part 4 §4.8.5) MUST enforce SemVer compatibility: a facade requesting `^1.2.3` resolves to providers `1.2.x` only, never `2.x.x`.

**Invariant:** `INV-CFS-VER-002` — A MAJOR version change in a provider REQUIRES a new `capabilityId` with incremented major (e.g., `skill.execution.llm.v1` → `skill.execution.llm.v2`). In-place major version updates are forbidden.

### Capability Descriptors

Each capability registration produces a **Capability Descriptor** — the immutable runtime representation used for discovery and resolution:

| Descriptor Field | Source | Mutability |
|------------------|--------|------------|
| `capabilityId` | Registration | Immutable |
| `facadeId` | Registration | Immutable |
| `providerId` | Registration | Immutable |
| `version` | Registration | Immutable |
| `contract` | Registration | Immutable |
| `lifecycleState` | Lifecycle | Mutable (state machine) |
| `resourceProfile` | Registration | Mutable (configurable) |
| `securityContext` | Registration | Immutable |
| `healthStatus` | HealthManager | Mutable (derived) |
| `selectionWeight` | CapabilityManager policy | Mutable (configurable) |
| `registeredAt` | Registration | Immutable |
| `lastInvokedAt` | Runtime | Mutable (derived) |
| `invocationCount` | Runtime | Mutable (derived) |
| `errorRate` | Runtime | Mutable (derived) |

**Invariant:** `INV-CFS-DESC-001` — Capability Descriptors SHALL be constructed by CapabilityManager at registration and updated only via defined lifecycle transitions and runtime telemetry. No external component SHALL mutate descriptors directly.

### Discovery Metadata

For discovery queries (Part 4 §4.8.4), the CapabilityManager indexes descriptors by:

| Index | Key | Query Support |
|-------|-----|---------------|
| **By Facade** | `facadeId` + version range | Exact, prefix, range |
| **By Tag** | `tags` key-value pairs | Equality, presence, expression |
| **By Resource** | `resourceProfile` dimensions | Range (≥, ≤), exact |
| **By Health** | `healthStatus` | Minimum threshold |
| **By Security** | `securityContext.trustLevel` | Minimum trust level |

**Invariant:** `INV-CFS-DISC-001` — Discovery indexes SHALL be updated synchronously with descriptor lifecycle changes. Stale discovery results are a conformance violation.

### Registration Table

| Phase | Actor | Action | Event Emitted | Validation |
|-------|-------|--------|---------------|------------|
| 1 | Provider (Manager) | Emit `CapabilityRegisterEvent` with metadata | — | Schema validation, conflict check, resource profile validation, security context validation |
| 2 | CapabilityManager | Validate, assign `providerId`, set `REGISTERING` | `CapabilityRegisterEvent` (echo) | — |
| 3 | CapabilityManager | Transition to `ACTIVE`, update indexes | `CapabilityRegisteredEvent` | HealthManager readiness confirmed |
| 4 | Provider / CapabilityManager | Deprecation trigger (config, schedule, manual) | `CapabilityDeprecatedEvent` | Grace period configured |
| 5 | CapabilityManager | After grace period, transition to `DRAINING` | — | In-flight invocation tracking |
| 6 | CapabilityManager | After drain timeout, transition to `REMOVED`, archive | `CapabilityRemovedEvent` | — |

**Invariant:** `INV-CFS-REG-006` — Registration validation MUST reject any provider whose `contract` schemas are not registered in the Event System schema registry (Part 2).

**Invariant:** `INV-CFS-REG-007` — Registration validation MUST reject any provider whose `resourceProfile` exceeds global capacity limits (Part 4 §4.9).

**Invariant:** `INV-CFS-REG-008` — Registration validation MUST reject any provider whose `securityContext` requires a trust level higher than the facade declares (Part 4 §4.8.10 Conflict Resolution).

---

## 6.2.4 Capability Discovery Model

### Discovery Process

Discovery is the process by which a Capability Facade Service (or any Event Space consumer) locates and binds to a capable provider at invocation time. The process operates exclusively through the CapabilityManager (Manager Space) and is exposed to Event Space via the facade's event contract.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DISCOVERY PROCESS                                     │
│                                                                              │
│  Event Space                    Manager Space                               │
│  ┌──────────────────┐           ┌────────────────────────────┐             │
│  │ Capability       │           │ CapabilityManager          │             │
│  │ Facade Service   │           │                            │             │
│  │                  │           │  1. receive DiscoveryQuery │             │
│  │  1. emit         │──────────▶│  2. filter by facadeId,    │             │
│  │  DiscoveryQuery  │  Event    │     versionRange, tags     │             │
│  │                  │           │  3. filter by health ≥     │             │
│  │                  │           │     HEALTHY                │             │
│  │                  │           │  4. filter by security     │             │
│  │                  │           │     (caller trust level)   │             │
│  │                  │           │  5. filter by resources    │             │
│  │                  │           │     (caller quota)         │             │
│  │                  │           │  6. apply selection policy │             │
│  │                  │           │  7. return providerRefs    │             │
│  │  8. receive      │◀──────────│                            │             │
│  │  DiscoveryResult │  Event    │                            │             │
│  └──────────────────┘           └────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Invariant:** `INV-CFS-DISC-001` — Discovery MUST be mediated by CapabilityManager. No Event Space entity MAY maintain a local provider cache or bypass the discovery protocol.

**Invariant:** `INV-CFS-DISC-002` — Discovery queries MUST carry the caller's `correlationId`, `principalId`, and `trustLevel` for security and resource filtering.

### Lookup Rules

| Rule ID | Rule | Enforcement |
|---------|------|-------------|
| **LR-001** | Query MUST specify `facadeId` and `versionRange` (SemVer range syntax) | CapabilityManager validates on receipt |
| **LR-002** | Query MAY specify `tagSelector` (key=value, expressions) | CapabilityManager matches against provider `tags` |
| **LR-003** | Query MAY specify `minHealthLevel` (default: HEALTHY) | HealthManager provides current status |
| **LR-004** | Query MAY specify `resourceRequirements` | ResourceManager validates against caller quota |
| **LR-005** | Caller trust level is derived from authentication context | SecurityManager provides at query time |

**Invariant:** `INV-CFS-LOOKUP-001` — A discovery query with no matching ACTIVE providers MUST return empty result (not an error). The facade translates empty results to a capability unavailable event.

### Resolution Rules

Once discovery yields candidate providers, CapabilityManager applies resolution to select a single provider for the invocation:

| Rule ID | Rule | Priority |
|---------|------|----------|
| **RR-001** | Exclude DEPRECATED providers unless `includeDeprecated=true` in query | 1 (highest) |
| **RR-002** | Exclude providers failing health threshold | 2 |
| **RR-003** | Exclude providers exceeding caller's resource quota | 3 |
| **RR-004** | Exclude providers requiring trust level > caller's trust level | 4 |
| **RR-005** | Apply configured selection policy (round-robin, least-loaded, priority, affinity) | 5 |
| **RR-006** | If multiple equally-ranked, deterministic tie-break by `providerId` | 6 (lowest) |

**Invariant:** `INV-CFS-RESOLVE-001` — Resolution MUST be deterministic given identical registry state and query parameters.

**Invariant:** `INV-CFS-RESOLVE-002` — Resolution MUST NOT consider provider-internal state (queue depth, circuit breaker) — only registry metadata and HealthManager-published health.

### Visibility

Visibility governs which capabilities are discoverable by which callers:

| Visibility Level | Scope | Access Control |
|------------------|-------|----------------|
| **PUBLIC** | All authenticated principals | No additional authorization |
| **TENANT** | Principals within same tenant | SecurityManager validates tenant membership |
| **PRIVATE** | Specific principal or role list | SecurityManager evaluates explicit grants |
| **SYSTEM** | Kernel-owned managers only | Implicit (kernel trust level) |

**Invariant:** `INV-CFS-VIS-001` — CapabilityManager MUST enforce visibility at discovery time. Invisible capabilities MUST NOT appear in discovery results.

### Namespaces

Capabilities are organized into namespaces to prevent naming collisions and enable hierarchical governance:

```
ai-os.<domain>.<facade>.<name>.v<major>
```

Examples:
- `ai-os.skill.execution.llm-code.v1`
- `ai-os.memory.operations.working.v1`
- `ai-os.council.governance.consensus.v1`
- `ai-os.mcp.integration.filesystem.v1`

**Invariant:** `INV-CFS-NS-001` — All `capabilityId` values MUST conform to the namespace format. CapabilityManager rejects non-conforming registrations.

**Invariant:** `INV-CFS-NS-002` — Namespace ownership is assigned to a single team. Cross-team capability registration requires ARB approval.

### Version Compatibility

Compatibility between facade contract version and provider implementation version follows SemVer:

| Facade Requests | Provider Version | Compatible? |
|-----------------|------------------|-------------|
| `^1.2.3` (caret) | `1.2.x` (any patch) | ✓ |
| `~1.2.3` (tilde) | `1.x.x` (any minor/patch) | ✓ |
| `1.2.3` (exact) | `1.2.3` only | ✓ |
| `^1.2.3` | `2.0.0` | ✗ |
| `>=1.0.0 <2.0.0` | `1.5.0` | ✓ |

**Invariant:** `INV-CFS-VCOMP-001` — CapabilityManager MUST reject resolution where provider MAJOR version falls outside facade's declared compatible range.

### Selection Rules

Selection policy is configured per-facade in ConfigurationManager and applied by CapabilityManager:

| Policy | Behavior | Use Case |
|--------|----------|----------|
| **ROUND_ROBIN** | Cycle through eligible providers | Stateless, uniform load |
| **LEAST_LOADED** | Select provider with lowest current utilization | Latency-sensitive |
| **PRIORITY** | Select highest-priority healthy provider | Primary/standby |
| **AFFINITY** | Prefer provider in same zone, with cached data | Data locality |
| **COST_AWARE** | Prefer lower-cost provider within SLO | Batch/non-critical |
| **CANARY** | Route small % to new version | Progressive rollout |

**Invariant:** `INV-CFS-SEL-001` — Selection policy MUST be declared in facade configuration (not hardcoded). Policy changes take effect without facade restart.

---

## 6.2.5 Capability Metadata Model

Every capability registration in the CapabilityManager registry carries a canonical metadata record. This model defines the complete set of fields, their types, constraints, and semantics.

### Canonical Metadata Schema

| Field | Type | Cardinality | Mutability | Description |
|-------|------|-------------|------------|-------------|
| **identity** | | | | |
| `capabilityId` | String | 1 | Immutable | Globally unique capability identifier (namespace format) |
| `providerId` | String | 1 | Immutable | Unique provider instance identifier |
| `facadeId` | String | 1 | Immutable | Facade contract identifier and major version |
| **versioning** | | | | |
| `providerVersion` | SemVer | 1 | Immutable | Provider implementation version |
| `facadeVersion` | MajorVer | 1 | Immutable | Facade contract major version (e.g., `v1`) |
| `compatRange` | SemVerRange | 1 | Immutable | Declared compatible facade version range |
| **contract** | | | | |
| `inputSchemaRef` | SchemaRef | 1 | Immutable | Event System schema registry reference for input |
| `outputSchemaRef` | SchemaRef | 1 | Immutable | Event System schema registry reference for output |
| `errorSchemaRef` | SchemaRef | 1 | Immutable | Event System schema registry reference for errors |
| **lifecycle** | | | | |
| `lifecycleState` | Enum | 1 | State Machine | `REGISTERING` \| `ACTIVE` \| `DEPRECATED` \| `DRAINING` \| `REMOVED` |
| `registeredAt` | ISO8601 | 1 | Immutable | Registration timestamp |
| `activatedAt` | ISO8601 | 0..1 | Once | Transition to ACTIVE timestamp |
| `deprecatedAt` | ISO8601 | 0..1 | Once | Deprecation announcement timestamp |
| `removedAt` | ISO8601 | 0..1 | Once | Removal timestamp |
| **resources** | | | | |
| `resourceProfile` | ResourceProfile | 1 | Configurable | CPU, memory, GPU, network, LLM quota requirements |
| `maxConcurrency` | Integer | 1 | Configurable | Maximum concurrent invocations |
| `timeoutProfile` | TimeoutProfile | 1 | Configurable | Default, max, and per-operation timeouts |
| **security** | | | | |
| `requiredTrustLevel` | TrustLevel | 1 | Immutable | Minimum caller trust level (SYSTEM\|PRIVILEGED\|STANDARD\|UNTRUSTED) |
| `requiredPermissions` | Permission[] | 0..N | Immutable | Fine-grained permissions required for invocation |
| `dataClassification` | Classification | 1 | Immutable | Data sensitivity level handled by capability |
| **health** | | | | |
| `healthEndpoint` | URI | 0..1 | Configurable | Provider-specific health check endpoint |
| `healthStatus` | HealthStatus | 1 | Derived | Current health (HEALTHY\|DEGRADED\|UNHEALTHY\|UNKNOWN) |
| `lastHealthCheck` | ISO8601 | 1 | Derived | Timestamp of last health evaluation |
| **discovery** | | | | |
| `tags` | Map<String,String> | 0..N | Configurable | Arbitrary key-value tags for discovery filtering |
| `selectionWeight` | Float | 1 | Configurable | Weight for weighted selection policies |
| `priority` | Integer | 1 | Configurable | Priority for priority-based selection |
| **ownership** | | | | |
| `ownerTeam` | String | 1 | Immutable | Owning team identifier |
| `ownerContact` | String | 1 | Configurable | On-call contact or escalation path |
| **observability** | | | | |
| `instrumentationLevel` | Enum | 1 | Configurable | `NONE` \| `BASIC` \| `DETAILED` \| `DEBUG` |
| `sampleRate` | Float | 1 | Configurable | Trace sampling rate (0.0–1.0) |

### Nested Type Definitions

**ResourceProfile:**
```json
{
  "cpuMilliCores": 100,
  "memoryBytes": 256000000,
  "gpuCount": 0,
  "gpuMemoryBytes": 0,
  "networkMbps": 100,
  "llmQuotaTokens": 10000,
  "storageBytes": 1000000
}
```

**TimeoutProfile:**
```json
{
  "defaultMs": 30000,
  "maxMs": 120000,
  "perOperation": {
    "initialize": 5000,
    "execute": 30000,
    "cleanup": 5000
  }
}
```

**TrustLevel Enum:** `SYSTEM` > `PRIVILEGED` > `STANDARD` > `UNTRUSTED`

**HealthStatus Enum:** `HEALTHY` > `DEGRADED` > `UNHEALTHY` > `UNKNOWN`

**DataClassification Enum:** `PUBLIC` < `INTERNAL` < `CONFIDENTIAL` < `RESTRICTED`

### Metadata Invariants

| Invariant | Statement |
|-----------|-----------|
| `INV-CFS-META-001` | All immutable fields MUST be set at registration and NEVER modified. Violation = registry corruption. |
| `INV-CFS-META-002` | `inputSchemaRef`, `outputSchemaRef`, `errorSchemaRef` MUST resolve to valid schemas in Event System registry at registration time. |
| `INV-CFS-META-003` | `resourceProfile` MUST NOT exceed global capacity limits (ResourceManager validation at registration). |
| `INV-CFS-META-004` | `requiredTrustLevel` MUST be ≤ facade's declared maximum trust level (facade configuration). |
| `INV-CFS-META-005` | `lifecycleState` transitions MUST follow the state machine defined in §6.2.3. Illegal transitions are rejected. |
| `INV-CFS-META-006` | `healthStatus` is DERIVED exclusively from HealthManager. No component may write it directly. |
| `INV-CFS-META-007` | `tags` keys MUST be prefixed with team identifier (e.g., `team-a.cost-center`, `team-b.region`). |

---

## 6.2.6 Dependency Model

### Dependency Direction

Dependencies flow **unidirectionally** from Capability Facade Services to Capability Managers, mediated by CapabilityManager:

```
Engineering Service (Event Space)
       │ depends_on
       ▼
Capability Facade Service (Event Space)
       │ translates to Manager call
       ▼
CapabilityManager (Manager Space) ──resolves──▶ Capability Provider (Manager Space)
```

**Invariant:** `INV-CFS-DEP-001` — Capability Facade Services declare `depends_on` ONLY on Core Components and Core Managers (via kernel accessors). They MUST NOT depend on other Capability Facade Services or Engineering Services.

**Invariant:** `INV-CFS-DEP-002` — Capability Managers declare NO dependencies on Capability Facade Services. Manager Space is facade-agnostic.

### Allowed Dependencies

| From (Consumer) | To (Provider) | Mechanism | Justification |
|-----------------|---------------|-----------|---------------|
| SkillService | SkillManager | the designated SkillManager operation | Facade→Manager bridge (mandatory) |
| CouncilService | CouncilManager | the designated CouncilManager operations | Facade→Manager bridge (mandatory) |
| MCPService | MCPManager | the designated MCPManager operation | Facade→Manager bridge (mandatory) |
| MemoryService | MemoryManager | the designated MemoryManager operations | Facade→Manager bridge (mandatory) |
| All Facades | EventBus (C1) | EventBus subscribe/emit | Event Space communication |
| All Facades | ServiceRegistry (C2) | Registration, discovery | Service Framework |
| All Facades | ConfigurationManager (C3) | Read-only config access | Configuration |
| All Facades | StructuredLogger (C4) | Structured logging | Observability |
| All Facades | Capability Managers | Discovery, resolution | Capability routing |
| All Facades | SecurityManager | Authorization checks | Security |
| All Facades | ResourceManager | Quota validation | Resource governance |
| All Facades | HealthManager | Readiness checks | Health gating |

### Forbidden Dependencies

| Forbidden Pattern | Reason | Invariant |
|-------------------|--------|-----------|
| Facade → Facade direct call | Violates Event-First; creates coupling | `INV-CFS-DEP-003` |
| Facade → Engineering Service | Violates dependency direction; cycle risk | `INV-CFS-DEP-004` |
| Manager → Facade | Manager Space MUST NOT know Event Space | `INV-CFS-DEP-005` (Part 4) |
| Facade → Manager (non-designated) | One-to-one bridge rule | `INV-CFS-BRIDGE-002` (Part 6.1) |
| Facade → StorageManager direct | Storage is Manager Space; use MemoryService | `INV-CFS-DEP-006` |
| Facade → WorkflowManager direct | Workflow is Manager Space; use event contract | `INV-CFS-DEP-007` |

### Dependency Graph Rules

1. **Acyclic** — The `depends_on` graph across all Services (Engineering + Facade) MUST be a DAG. Verified at ServiceRegistry registration.
2. **Topological Initialization** — LifecycleManager initializes Services in topological order. Facades (no Engineering Service deps) initialize before Engineering Services.
3. **No Cross-Facade Dependencies** — Facades are siblings; no inter-facade communication.
4. **Kernel Accessor Only** — Facades access Managers ONLY via the kernel singleton accessor for their designated Capability Manager. No direct Manager references.

### Initialization Ordering

| Phase | Entities | Dependency Basis |
|-------|----------|------------------|
| 0–3 | Core Components | Part 1 §1.10.2 |
| 4–8 | Core Managers | Part 1 §1.10.2, Part 4 §4.2.3 |
| 9+ | Capability Facade Services | Depends on: EventBus, ServiceRegistry, ConfigManager, LifecycleManager, **target Capability Manager** |
| 9+ | Engineering Services | Depends on: Facade Services (declared in `depends_on`), Core Components |

**Invariant:** `INV-CFS-INIT-001` — A Capability Facade Service MUST NOT complete initialization until its target Capability Manager reports READY via HealthManager.

**Invariant:** `INV-CFS-INIT-002` — CapabilityManager MUST be initialized before any Capability Facade Service (Manager Phase 4–8 vs Service Phase 9+).

### Shutdown Ordering

Strict reverse of initialization:

| Phase | Entities | Order |
|-------|----------|-------|
| S9+ | Engineering Services | Reverse topological |
| S9+ | Capability Facade Services | Parallel (no inter-deps) |
| S8–S4 | Core Managers | Reverse Part 1 §1.10.2 |
| S3–S0 | Core Components | Reverse Part 1 §1.10.2 |

**Invariant:** `INV-CFS-SD-001` — A Capability Facade Service MUST complete shutdown (drain in-flight, cancel subscriptions) before its target Capability Manager begins shutdown.

---

## 6.2.7 Capability Lifecycle

The capability lifecycle governs the end-to-end states a capability provider traverses from registration to removal. This lifecycle is distinct from the Capability Facade Service lifecycle (which follows BaseService) and the kernel lifecycle (Part 1 §1.9).

### Lifecycle State Machine

```
┌──────────────┐
│  REGISTERING │  ← CapabilityRegisterEvent received
└──────┬───────┘
       │ validation OK + HealthManager READY
       ▼
┌──────────────┐
│    ACTIVE    │  ← Normal operation: discoverable, invocable
└──────┬───────┘
       │ deprecation triggered (config, schedule, manual)
       ▼
┌──────────────┐
│  DEPRECATED  │  ← Grace period: excluded from default discovery
└──────┬───────┘
       │ grace period expires OR explicit removal
       ▼
┌──────────────┐
│   DRAINING   │  ← No new invocations; completing in-flight
└──────┬───────┘
       │ in-flight complete OR forceTimeout expires
       ▼
┌──────────────┐
│   REMOVED    │  ← Archived; no further operations
└──────────────┘
```

### State Definitions and Transitions

| State | Description | Entry Condition | Exit Condition | Allowed Operations |
|-------|-------------|-----------------|----------------|-------------------|
| **REGISTERING** | Provider submitted, validation in progress | `CapabilityRegisterEvent` received | Validation passes + health READY | None (not discoverable) |
| **ACTIVE** | Fully operational, accepting invocations | Validation complete | Deprecation trigger | Discovery, Resolution, Invocation |
| **DEPRECATED** | Announced end-of-life, grace period active | Deprecation announced | Grace period end / manual remove | Discovery (opt-in only), Invocation (existing clients) |
| **DRAINING** | Grace period ended, finishing in-flight | Grace period expired | In-flight = 0 OR forceTimeout | Invocation completion only |
| **REMOVED** | Permanently removed, archived | Draining complete | (terminal) | None |

### Lifecycle Events

The CapabilityManager emits the following events at each transition (Part 4 §4.8.11):

| Transition | Event | Payload |
|------------|-------|---------|
| → REGISTERING | `CapabilityRegisterEvent` (echo) | `capabilityId`, `providerId`, `validationStatus` |
| REGISTERING → ACTIVE | `CapabilityRegisteredEvent` | `capabilityId`, `providerId`, `version`, `activatedAt` |
| ACTIVE → DEPRECATED | `CapabilityDeprecatedEvent` | `capabilityId`, `providerId`, `deprecatedAt`, `gracePeriodEnd`, `migrationGuidance` |
| DEPRECATED → DRAINING | `CapabilityDrainingEvent` | `capabilityId`, `providerId`, `drainingAt`, `inFlightCount` |
| DRAINING → REMOVED | `CapabilityRemovedEvent` | `capabilityId`, `providerId`, `removedAt`, `finalStats` |

**Invariant:** `INV-CFS-LC-001` — Every state transition MUST emit the corresponding event. Missing events = conformance failure.

**Invariant:** `INV-CFS-LC-002` — `CapabilityDeprecatedEvent` MUST include `migrationGuidance` (replacement capabilityId, breaking changes, migration steps).

### Operational Rules Per State

| Rule | REGISTERING | ACTIVE | DEPRECATED | DRAINING | REMOVED |
|------|-------------|--------|------------|----------|---------|
| Discoverable (default query) | ✗ | ✓ | ✗ | ✗ | ✗ |
| Discoverable (opt-in deprecated) | ✗ | ✓ | ✓ | ✗ | ✗ |
| Resolvable for new invocations | ✗ | ✓ | ✗ | ✗ | ✗ |
| Accepts new invocations | ✗ | ✓ | ✗ | ✗ | ✗ |
| Completes in-flight invocations | N/A | ✓ | ✓ | ✓ | N/A |
| Health checks required | ✓ | ✓ | ✓ | ✓ | ✗ |
| Resource reservation held | ✗ | ✓ | ✓ | ✓ (draining) | ✗ |
| Metrics emitted | ✗ | ✓ | ✓ | ✓ | ✗ |

### Grace Period

The DEPRECATED state includes a configurable grace period:

| Property | Configuration |
|----------|---------------|
| `gracePeriodDays` | Configured by the Configuration Specification |
| `forceDrainTimeoutHours` | Configured by the Configuration Specification |
| `notifyBeforeDays` | Configured by the Configuration Specification |

During grace period:
- CapabilityManager emits `CapabilityDeprecationWarningEvent` at each `notifyBeforeDays` milestone
- Existing consumers continue to resolve deprecated provider (backward compatibility)
- New consumers DEFAULT to non-deprecated providers unless `includeDeprecated=true`

**Invariant:** `INV-CFS-GRACE-001` — Grace period MUST be ≥ 1 day. Zero or negative grace period is a configuration error.

**Invariant:** `INV-CFS-GRACE-002` — At grace period end, CapabilityManager MUST transition to DRAINING automatically. No manual intervention required.

### Forced Removal

If a provider in DRAINING state exceeds `forceDrainTimeoutHours` with in-flight invocations remaining:

1. CapabilityManager emits `CapabilityForceDrainEvent` with remaining invocation list
2. In-flight invocations receive `CAPABILITY_FORCE_DRAINED` error event
3. Provider transitions to REMOVED

**Invariant:** `INV-CFS-FORCE-001` — Force drain MUST emit error events to all affected callers with `correlationId` for traceability.

### Capability Facade Service Lifecycle Alignment

Each Capability Facade Service (BaseService lifecycle) aligns with capability registry state:

| Facade Service State | Capability Registry State | Behavior |
|----------------------|---------------------------|----------|
| `INITIALIZING` | N/A | Subscribes to event types; queries CapabilityManager for ACTIVE providers |
| `RUNNING` | ACTIVE providers exist | Normal event handling; translates requests to Manager calls |
| `RUNNING` | No ACTIVE providers for facade | Emits `CAPABILITY_UNAVAILABLE` for incoming requests; logs warning |
| `RUNNING` | Provider DEPRECATED | Continues routing to deprecated if `includeDeprecated`; logs deprecation warnings |
| `SHUTTING_DOWN` | Any | Drains in-flight event handlers; unsubscribes; emits shutdown event |
| `TERMINATED` | Any | No further operations |

**Invariant:** `INV-CFS-FACADE-LC-001` — A Capability Facade Service in RUNNING state with zero ACTIVE providers for its domain MUST emit `CAPABILITY_UNAVAILABLE` (not fail silently) for all incoming requests.

**Invariant:** `INV-CFS-FACADE-LC-002` — Facade Service shutdown MUST wait for in-flight Manager calls to complete or timeout (configured `shutdownDrainTimeoutMs`, configurable by the Configuration Specification).

---

## 6.2.8 Capability Ownership

### Ownership Boundaries

Each Capability Domain has a single, unambiguous owner for every artifact, state, and event within that domain. Ownership is not shared.

| Domain | Manager Owner (Manager Space) | Facade Owner (Event Space) | State Owner | Event Owner |
|--------|-------------------------------|----------------------------|-------------|-------------|
| Skill Execution | SkillManager | SkillService | SkillManager (execution state, sandbox) | SkillService (SKILL_EXECUTED, SKILL_FAILED) |
| Council Governance | CouncilManager | CouncilService | CouncilManager (proposals, votes, decisions) | CouncilService (7 audit events) |
| MCP Integration | MCPManager | MCPService | MCPManager (transport state, permissions) | MCPService (MCP_TOOL_SUCCEEDED, MCP_TOOL_FAILED) |
| Memory Operations | MemoryManager | MemoryService | MemoryManager (records, indices, consolidation) | MemoryService (5 DATA events) |

**Invariant:** `INV-CFS-OWN-002` — No artifact, state object, or event type SHALL have multiple owners. Ownership is exclusive and non-transferable without ARB approval.

**Invariant:** `INV-CFS-OWN-003` — The Capability Manager owns all Manager Space state. The Capability Facade Service owns all Event Space events for its domain. Neither owns the other's artifacts.

### Responsibility Matrix

| Responsibility | Skill | Council | MCP | Memory |
|----------------|-------|---------|-----|--------|
| **Capability Definition** | SkillManager | CouncilManager | MCPManager | MemoryManager |
| **Provider Implementation** | SkillManager | CouncilManager | MCPManager | MemoryManager |
| **Event Contract Definition** | (Part 2) | (Part 2) | (Part 2) | (Part 2) |
| **Event Emission (results)** | SkillService | CouncilService | MCPService | MemoryService |
| **Event Subscription (triggers)** | SkillService | CouncilService | MCPService | MemoryService |
| **Schema Registration** | Part 2 process | Part 2 process | Part 2 process | Part 2 process |
| **Configuration** | ConfigurationManager | ConfigurationManager | ConfigurationManager | ConfigurationManager |
| **Health Reporting** | HealthManager | HealthManager | HealthManager | HealthManager |
| **Resource Accounting** | ResourceManager | ResourceManager | ResourceManager | ResourceManager |
| **Authorization** | SecurityManager | SecurityManager | SecurityManager | SecurityManager |

**Invariant:** `INV-CFS-RESP-001` — Every operational responsibility in the matrix above SHALL have exactly one owner. Ambiguous or shared responsibility is a conformance violation.

### Mutation Rules

| Artifact | Mutable By | Mutation Mechanism | Immutable Fields |
|----------|------------|-------------------|------------------|
| Capability Descriptor (Manager Space) | CapabilityManager | Lifecycle transitions, health updates, config changes | identity, versioning, contract, security, ownership |
| Event Payload (Event Space) | Facade Service (emission only) | Event emission | correlationId, causationId, source, timestamp, schema version |
| Manager Internal State | Respective Manager | Manager-internal logic | All fields not explicitly exposed via capability contract |
| Facade Configuration | ConfigurationManager | Config layer merge (Part 7) | None (fully mutable via config layers) |

**Invariant:** `INV-CFS-MUTATE-001` — Capability Facade Services MUST NOT mutate Manager Space state directly. All mutations go through Manager method calls.

**Invariant:** `INV-CFS-MUTATE-002` — Capability Managers MUST NOT emit Event Space events. All Event Space events originate from Facade Services.

**Invariant:** `INV-CFS-MUTATE-003` — Event payloads are immutable after emission. No component modifies an event in transit.

### State Ownership

| State Category | Owner | Access by Others |
|----------------|-------|-------------------|
| Execution sandbox state | SkillManager | Read-only via SkillService (translated to events) |
| Council proposals/votes/decisions | CouncilManager | Read-only via CouncilService (translated to events) |
| MCP transport sessions | MCPManager | Read-only via MCPService (translated to events) |
| Memory records/indices | MemoryManager | Read-only via MemoryService (translated to events) |
| Capability registry | CapabilityManager | Read-only via discovery queries |
| Facade subscription state | Facade Service | Private to facade |
| Correlation/causation chains | EventBus | Immutable, queryable via observability |

**Invariant:** `INV-CFS-STATE-001` — Manager Space state is NEVER directly exposed to Event Space. All access is mediated by Facade Service translation.

### Artifact Ownership

| Artifact Type | Owner | Lifecycle |
|---------------|-------|-----------|
| Skill definitions | SkillManager | Create/update/delete via SkillManager API |
| Council proposals | CouncilManager | Create via CouncilService event; lifecycle managed by CouncilManager |
| MCP tool definitions | MCPManager | Register via MCPManager; invoked via MCPService |
| Memory records | MemoryManager | CRUD via MemoryService events; consolidation/deletion by MemoryManager |
| Checkpoints (workflow) | WorkflowManager | Part 4 §4.6; not capability-owned |
| Audit logs | ObservabilityManager + SecurityManager | Immutable append-only; Part 4 §4.7, §4.11 |

**Invariant:** `INV-CFS-ARTIFACT-001` — Artifacts created by Manager Space operations are owned by the Manager. Facade Services may translate them into events but do not own the source artifact.

### Event Ownership

| Event Type | Producer (Owner) | Consumers | Category (Part 2) |
|------------|------------------|-----------|-------------------|
| SKILL_EXECUTE_REQUEST | Engineering Services | SkillService | COMMAND |
| SKILL_EXECUTED | SkillService | Engineering Services | DIAGNOSTIC |
| SKILL_FAILED | SkillService | Engineering Services | DIAGNOSTIC |
| COUNCIL_CONVENE | Engineering Services | CouncilService | COMMAND |
| COUNCIL_CONVENED | CouncilService | All (audit) | AUDIT |
| COUNCIL_PROPOSAL_SUBMITTED | CouncilService | All (audit) | AUDIT |
| COUNCIL_VOTE_CAST | CouncilService | All (audit) | AUDIT |
| COUNCIL_CONSENSUS_REACHED | CouncilService | All (audit) | AUDIT |
| COUNCIL_DISSENT_REGISTERED | CouncilService | All (audit) | AUDIT |
| COUNCIL_DECISION_FINALIZED | CouncilService | All (audit) | AUDIT |
| COUNCIL_ESCALATED | CouncilService | Human operators | AUDIT |
| MCP_TOOL_CALL | Engineering Services | MCPService | COMMAND |
| MCP_TOOL_CALLED | MCPService | All (observability) | DIAGNOSTIC |
| MCP_TOOL_SUCCEEDED | MCPService | Engineering Services | DIAGNOSTIC |
| MCP_TOOL_FAILED | MCPService | Engineering Services | DIAGNOSTIC |
| MEMORY_STORE | Engineering Services | MemoryService | COMMAND |
| MEMORY_STORED | MemoryService | Engineering Services | DATA |
| MEMORY_RETRIEVE | Engineering Services | MemoryService | QUERY |
| MEMORY_RETRIEVED | MemoryService | Engineering Services | DATA |
| MEMORY_UPDATE | Engineering Services | MemoryService | COMMAND |
| MEMORY_UPDATED | MemoryService | Engineering Services | DATA |
| MEMORY_CONSOLIDATE | Engineering Services | MemoryService | COMMAND |
| MEMORY_CONSOLIDATED | MemoryService | All (observability) | DATA |
| MEMORY_PRUNE | Engineering Services | MemoryService | COMMAND |
| MEMORY_PRUNED | MemoryService | All (observability) | DATA |

**Invariant:** `INV-CFS-EVT-OWN-001` — Every event type in the above table has exactly one producer (the listed Facade Service or Engineering Services). No other component emits these event types.

---

## 6.2.9 Cross-Capability Communication

### Communication Philosophy

Capability domains are **independent bounded contexts**. They communicate exclusively through the EventBus — never through direct Manager-to-Manager calls, shared state, or Facade-to-Facade calls.

```
Engineering Service A          Engineering Service B
       │                              │
       ▼                              ▼
Capability Facade X           Capability Facade Y
       │                              │
       ▼                              ▼
   EventBus ────── Correlation/Causation ──────▶ EventBus
       │                              │
       ▼                              ▼
  Capability Manager X          Capability Manager Y
```

**Invariant:** `INV-CFS-XCOMM-001` — Capability Facade Services MUST NOT subscribe to events emitted by other Capability Facade Services. All cross-domain coordination is the responsibility of Engineering Services (consumers).

**Invariant:** `INV-CFS-XCOMM-002` — Capability Managers MUST NOT communicate with each other directly. All inter-manager coordination goes through WorkflowManager (Part 4 §4.6) or CapabilityManager (Part 4 §4.8).

### Event Usage

Events are the **sole communication mechanism** between capabilities and their consumers:

| Pattern | Description | Example |
|---------|-------------|---------|
| **Request-Reply** | Consumer emits request event → Facade translates → Manager executes → Facade emits result event | `MEMORY_STORE` → `MEMORY_STORED` |
| **Fire-and-Forget** | Consumer emits command event → Facade translates → Manager executes → No result expected | `MEMORY_PRUNE` (optional `MEMORY_PRUNED`) |
| **Long-Running with Progress** | Request → Immediate acknowledgement → Progress events → Final result | `COUNCIL_CONVENE` → `COUNCIL_CONVENED` → `COUNCIL_PROPOSAL_SUBMITTED`... |
| **Broadcast Notification** | Facade emits event → Multiple consumers receive | `COUNCIL_DECISION_FINALIZED` → all interested services |

**Invariant:** `INV-CFS-EVT-USAGE-001` — Every capability operation MUST follow the request-reply pattern (explicit result event) unless explicitly documented as fire-and-forget in Part 2.

**Invariant:** `INV-CFS-EVT-USAGE-002` — Facade Services MUST propagate `correlationId` from request to result. `causationId` MUST be set to the request's `eventId`.

### Manager Invocation

Facade Services invoke their designated Manager via the kernel singleton accessor during event handler execution:

| Facade | Manager Accessor | Invocation Pattern |
|--------|------------------|-------------------|
| SkillService | kernel accessor | the designated Capability Manager operation |
| CouncilService | kernel accessor | the designated Capability Manager operations |
| MCPService | kernel accessor | the designated Capability Manager operation |
| MemoryService | kernel accessor | the designated Capability Manager operations |

**Invariant:** `INV-CFS-MGR-INVOKE-001` — Manager invocation occurs ONLY within an event handler. No proactive polling, scheduling, or background Manager calls.

**Invariant:** `INV-CFS-MGR-INVOKE-002` — Each event handler invocation results in AT MOST one Manager method call (Part 6.1 INV-CFS-MGR-001).

### Translation Rules

Facade Services translate between Event Space and Manager Space:

| Direction | Rule |
|-----------|------|
| Event → Manager | Map event payload fields to Manager method parameters 1:1. No transformation, enrichment, or business logic. |
| Manager → Event | Map Manager return value/error to result event payload 1:1. No interpretation, filtering, or aggregation. |
| Errors | Manager exceptions → typed failure event (e.g., `SKILL_FAILED`). Exception details serialized per error schema. |
| Correlation | `correlationId` passes through unchanged. `causationId` = incoming `eventId`. |

**Invariant:** `INV-CFS-TRANS-001` — Translation logic MUST be pure functions of (event payload, Manager response). No external state, no randomness, no time-dependent behavior.

**Invariant:** `INV-CFS-TRANS-002` — Given identical event payload and identical Manager response, the emitted result event payload MUST be bitwise identical (deterministic translation).

### Allowed Communication

| From | To | Mechanism | Condition |
|------|-----|-----------|-----------|
| Engineering Service | Capability Facade Service | EventBus (request events) | Always |
| Capability Facade Service | Capability Manager | Singleton accessor (method call) | Only during event handler |
| Capability Facade Service | CapabilityManager (registry) | CapabilityManager discovery/resolution APIs | During event handler for provider selection |
| Capability Facade Service | SecurityManager | `security.authorize()` | Before Manager invocation |
| Capability Facade Service | ResourceManager | `resources.reserve()` | Before Manager invocation |
| Capability Facade Service | EventBus | `emit(resultEvent)` | After Manager response |
| Engineering Service | Engineering Service | EventBus (via workflow/phase events) | Part 5 SDLC pipeline |

### Forbidden Communication

| Forbidden Pattern | Reason | Invariant |
|-------------------|--------|-----------|
| Facade → Facade direct call | Violates Event-First; creates coupling | `INV-CFS-XCOMM-003` |
| Facade → Facade event subscription | Violates consumer-agnosticism; creates hidden dependency | `INV-CFS-XCOMM-004` |
| Manager → Manager direct call | Violates Manager Space isolation; EventBus-only post-init | `INV-CFS-XCOMM-005` (Part 1 CC-IR-001) |
| Manager → EventBus publish/subscribe | Managers are EventBus-free by design | `INV-CFS-XCOMM-006` (Part 4 §4.1) |
| Facade → Engineering Service direct call | Violates dependency direction; creates cycles | `INV-CFS-XCOMM-007` (Part 6.1 INV-CFS-ENG-002) |
| Engineering Service → Manager singleton | Violates bridge architecture; bypasses facade | `INV-CFS-XCOMM-008` (Part 6.1 INV-CFS-ENG-003) |
| Facade ↔ Shared mutable state | All state in StateManager; facades are stateless | `INV-CFS-XCOMM-009` |

---

## 6.2.10 Architectural Invariants

The following invariants are **objectively testable** and govern all Capability Facade Services. They use RFC2119 terminology (MUST, MUST NOT, SHALL, SHALL NOT).

### Structural Invariants

| ID | Invariant | Test Criterion |
|----|-----------|----------------|
| `INV-CFS-STRUCT-001` | AI-OS v1.0 defines four Capability Facade Services: SkillService, CouncilService, MCPService, MemoryService. | Static verification: count of `BaseService` subtypes annotated `@CapabilityFacade` equals 4. |
| `INV-CFS-STRUCT-002` | Each Facade Service bridges exactly one Capability Manager domain. | Static verification: each facade references exactly one Capability Manager accessor. |
| `INV-CFS-STRUCT-003` | No Facade Service imports or references any Engineering Service module. | Import graph verification: zero edges from facade packages to engineering service packages. |
| `INV-CFS-STRUCT-004` | No Facade Service imports or references another Facade Service. | Import graph verification: zero edges between facade packages. |
| `INV-CFS-STRUCT-005` | Each Facade Service declares `depends_on` only on Core Components (C1–C4) and CapabilityManager. | ServiceRegistry registration validation. |
| `INV-CFS-STRUCT-006` | No Facade Service declares `depends_on` any Engineering Service. | ServiceRegistry registration validation. |

### Behavioral Invariants

| ID | Invariant | Test Criterion |
|----|-----------|----------------|
| `INV-CFS-BEHAV-001` | Every event handler completes in ≤ configured timeout. | Runtime: handler execution time metric. |
| `INV-CFS-BEHAV-002` | Every incoming request event produces exactly one result event (success or failure). | Event correlation: 1:1 request:result correlationId pairing. |
| `INV-CFS-BEHAV-003` | Facade Service emits zero events outside its declared EventType catalog. | Event schema registry: all emitted events validate against declared types. |
| `INV-CFS-BEHAV-004` | All emitted events carry `source.componentType = 'capability_facade'` and `source.componentName = <serviceId>`. | Event schema validation on emit. |
| `INV-CFS-BEHAV-005` | All emitted events propagate `correlationId` from request; `causationId` = request `eventId`. | Event payload inspection. |
| `INV-CFS-BEHAV-006` | Manager invocation occurs only within event handler scope. | Call stack verification: accessor calls only in handler call chain. |
| `INV-CFS-BEHAV-007` | Facade Service maintains zero mutable state across event handlers. | State verification: no instance fields modified after `on_start()`. |
| `INV-CFS-BEHAV-008` | Translation logic is deterministic: same input + same Manager response = same output. | Determinism verification: repeated identical inputs produce identical outputs. |

### Event Contract Invariants

| ID | Invariant | Test Criterion |
|----|-----------|----------------|
| `INV-CFS-EVT-001` | Request events validate against registered schema before Manager invocation. | Schema validation verification. |
| `INV-CFS-EVT-002` | Result events validate against registered schema before emission. | Schema validation verification. |
| `INV-CFS-EVT-003` | Failure events (SKILL_FAILED, MCP_TOOL_FAILED, etc.) are emitted for ALL error paths. | Fault injection verification: every exception path produces typed failure event. |
| `INV-CFS-EVT-004` | No raw exceptions cross the Facade boundary. All errors are events. | Exception verification: zero uncaught exceptions from facade handlers. |

### Lifecycle Invariants

| ID | Invariant | Test Criterion |
|----|-----------|----------------|
| `INV-CFS-LC-001` | Facade Service initializes AFTER its Capability Manager (Phase 9+ vs Phase 4–8). | Initialization phase ordering verification. |
| `INV-CFS-LC-002` | Facade Service subscribes to event types in `on_start()` only. | Lifecycle hook inspection. |
| `INV-CFS-LC-003` | Facade Service unsubscribes from all event types in `on_stop()`. | Lifecycle hook inspection. |
| `INV-CFS-LC-004` | Facade Service drains in-flight handlers on shutdown (≤ configured timeout). | Shutdown integration test with in-flight load. |

### Security Invariants

| ID | Invariant | Test Criterion |
|----|-----------|----------------|
| `INV-CFS-SEC-001` | Facade Service calls `security.authorize()` before Manager invocation. | Call chain verification: authorize() precedes every Manager call. |
| `INV-CFS-SEC-002` | Facade Service respects authorization DENY by emitting failure event. | AuthZ test: denied request → failure event, no Manager call. |
| `INV-CFS-SEC-003` | Facade Service never logs or emits sensitive data (secrets, tokens, PII). | Log verification: secret detection patterns. |

---

## 6.2.11 Conformance Requirements

### Static Verification (Build-Time)

| Requirement ID | Check | Tooling | Failure = |
|----------------|-------|---------|-----------|
| `CONF-ST-001` | AI-OS v1.0 defines four CapabilityFacade-annotated services | Static verification | Build FAIL |
| `CONF-ST-002` | Each facade references exactly 1 Capability Manager accessor | Static verification | Build FAIL |
| `CONF-ST-003` | Zero imports from engineering service packages | Import graph verification | Build FAIL |
| `CONF-ST-004` | Zero imports between facade packages | Import graph verification | Build FAIL |
| `CONF-ST-005` | `depends_on` contains only Core Components + CapabilityManager | ServiceRegistry schema validation | Build FAIL |
| `CONF-ST-006` | All event types declared in Part 2 schema registry | Schema registry validation | Build FAIL |
| `CONF-ST-007` | All event payloads have registered JSON schemas | Schema registry validation | Build FAIL |
| `CONF-ST-008` | Handler methods are pure (no side effects beyond Manager call + emit) | Effect system / manual review | Lint WARN |
| `CONF-ST-009` | Configuration keys follow `kernel.capability.<facade>.*` namespace | Config schema validation | Build FAIL |

### Runtime Verification (Integration Test)

| Requirement ID | Check | Scenario | Pass Criterion |
|----------------|-------|----------|----------------|
| `CONF-DY-001` | Request→result event pairing (1:1) | Concurrent requests per facade | 100% correlationId matched |
| `CONF-DY-002` | Deterministic translation | Repeated identical inputs, same Manager stub | Output identity across repeated executions |
| `CONF-DY-003` | Failure events on all error paths | Manager throws, timeouts, unavailable | Typed failure event emitted |
| `CONF-DY-004` | No direct Manager access outside handler | Attempt accessor invocation in `on_start`, background task | Access blocked or kernel not ready |
| `CONF-DY-005` | Authorization gate enforced | Request with insufficient trust level | DENY → failure event, no Manager call |
| `CONF-DY-006` | Resource reservation before invocation | Request exceeding quota | Resource exhausted event, no Manager call |
| `CONF-DY-007` | Graceful shutdown drains in-flight | Shutdown signal with in-flight requests | All complete or timeout, then shutdown |
| `CONF-DY-008` | Zero facade-to-facade event subscription | Subscription audit | Zero cross-facade subscriptions |
| `CONF-DY-009` | Health status reflects Manager readiness | Manager unhealthy → facade reports DEGRADED | Health status accuracy |

### Architectural Verification (Periodic Audit)

| Requirement ID | Check | Frequency | Auditor |
|----------------|-------|-----------|---------|
| `CONF-ARCH-001` | Ownership boundaries respected (no shared state mutation) | Quarterly | ARB |
| `CONF-ARCH-002` | Event contracts stable (no breaking changes without major version) | Per release | ARB |
| `CONF-ARCH-003` | Facade logic remains translation-only (no business logic creep) | Quarterly | ARB |
| `CONF-ARCH-004` | Dependency graph remains acyclic (Engineering → Facade → Manager) | Per release | ARB |
| `CONF-ARCH-005` | All four domains have active providers in ACTIVE state | Continuous | HealthManager |
| `CONF-ARCH-006` | Deprecation grace periods observed (no forced removal < 1 day) | Continuous | CapabilityManager |

### Audit Requirements

| Audit Type | Scope | Evidence Required |
|------------|-------|-------------------|
| **Conformance Review** | All invariants in §6.2.10 | Test reports, static analysis logs, architecture decision records |
| **Event Contract Audit** | Schema registry alignment, versioning compliance | Schema diff reports, migration plans for breaking changes |
| **Dependency Audit** | Import graphs, `depends_on` declarations, runtime call traces | Automated dependency report + manual review |
| **Security Audit** | Authorization gates, secret handling, audit event completeness | Penetration test report, secret scan, audit log sampling |
| **Performance Audit** | Translation latency, Manager call overhead, event throughput | Benchmark results vs. SLAs (Part 13) |

**Invariant:** `INV-CFS-CONF-001` — A Capability Facade Service implementation SHALL NOT be deployed to production unless all `CONF-ST-*` and `CONF-DY-*` checks pass.

**Invariant:** `INV-CFS-CONF-002` — Architectural audit (`CONF-ARCH-*`) SHALL be completed before any major version release of the Capability Facade Services layer.

---

**END OF SECTION 6.2.11**

**END OF PART 6, SECTION 6.2 — CAPABILITY ARCHITECTURE OVERVIEW**

*This document is FROZEN. Any modification requires Architecture Review Board approval. Sections 6.3–6.5 (individual facade specifications) SHALL follow in subsequent artifacts and MUST conform to the architectural principles and invariants established herein.*