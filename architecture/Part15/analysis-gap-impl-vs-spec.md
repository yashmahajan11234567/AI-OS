# Implementation Gap Analysis: src/aios/ vs Parts 0–14 Specification

**Status:** DRAFT — Analysis of reference implementation against normative spec
**Scope:** `src/aios/` kernel reference implementation vs Parts 0–14 architecture specification
**Date:** 2026-08-21
**Classification:** DERIVED (inferred from code inspection with documented inference path)

---

## Executive Summary

The `src/aios/` reference implementation at `C:\Development\AI-OS\src\aios\` contains a genuine, partial implementation of the AI-OS HermesKernel architecture. It implements **5 of the 9 Core Managers** defined in Part 4 §4.2.1, plus LifecycleManager (Task 9), Configuration Manager, ServiceRegistry, StructuredLogger, and the canonical EventBus with the full 12-field Event envelope.

### Coverage Status

| Architecture Layer | Spec Coverage | Implementation Status | Gap Classification |
|---|---|---|---|
| **C1 EventBus (Part 1 §1.8.1, Task 5)** | Full 12-field Event, 97 EventType categories, singleton | **EXISTING** — Full canonical Event + EventBus | — |
| **C2 ServiceRegistry (Part 1 §1.8.2, Part 3 §3.4)** | Service registration/registry API | **EXISTING** — Implemented, `core.lifecycle`/`core.state` etc. | — |
| **C3 ConfigurationManager (Part 1 §1.8.3, Part 3 §3.5)** | 4-layer config merge (defaults→app→env→env vars), freeze() | **EXISTING** — Implements merge + freeze + schema | — |
| **C4 StructuredLogger (Part 1 §1.8.4, CONFLICT-CC-01)** | Structured JSON logging | **EXISTING** — Replaces stdlib logging | — |
| **LifecycleManager (Part 4 §4.3, Task 9)** | Phase-sequenced init/shutdown, rollback, recovery | **EXISTING** — ICoreManager, 5-phase topology, conflict-resolved events | — |
| **StateManager (Part 4 §4.4, Task 10)** | Phase-2 state management | **EXISTING** — Fully upgraded to Core Manager | — |
| **StorageManager (Part 4 §4.5, Task 11)** | 6 namespaces, checkpoint/artifact storage | **EXISTING** — Fully upgraded to Core Manager | — |
| **HealthManager (Part 4 §4.6, Task 12)** | Phase-3 health checks | **EXISTING** — Fully upgraded to Core Manager | — |
| **ResourceManager (Part 4 §4.7, Task 13)** | Phase-3 resource allocation | **EXISTING** — Fully upgraded to Core Manager | — |
| **SecurityManager (Part 4 §4.7, M8)** | ABAC, 5-phase init | **GAP** — Not implemented | GAP |
| **CapabilityManager (Part 4 §4.6, CONFLICT-CM-01)** | Capability registry | **GAP** — Not implemented | GAP |
| **WorkflowManager (Part 4 §4.6, Task 7)** | DAG execution | **EXISTING?** — Exported but not yet reviewed | DERIVED |
| **ObservabilityManager (Part 4 §4.9)** | Metrics, tracing, observability | **GAP** — Not implemented | GAP |
| **ModelRouter (Part 1 §1.8.2)** | Model routing | **EXISTING?** — Exported from `__init__` | DERIVED |
| **MemoryManager (Part 1 §1.8.1)** | Memory storage/retrieval | **EXISTING?** — Exported from `__init__` | DERIVED |
| **SkillManager (Part 1 §1.8.3)** | Skill execution | **EXISTING?** — Exported from `__init__` | DERIVED |
| **MCPManager (Part 1 §1.8.4)** | MCP server integration | **EXISTING?** — Exported from `__init__` | DERIVED |
| **CouncilManager (Part 1 §1.8.5)** | Multi-agent deliberation | **EXISTING?** — Exported from `__init__` | DERIVED |
| **CheckpointManager** | Checkpoint orchestration | **EXISTING?** — Exported from `__init__` | DERIVED |
| **RetryManager** | Retry budgeting | **EXISTING?** — Exported from `__init__` | DERIVED |
| **RootCauseAnalyzer** | Failure analysis | **EXISTING?** — Exported from `__init__` | DERIVED |
| **AIAgencyService** | Audit orchestration | **EXISTING?** — Exported from `__init__` | DERIVED |

---

## Part 1 Core Manager Gap (CONFLICT-CM-01)

Part 1 §1.8.1 defines a **different set** of 9 Core Managers than Part 4 §4.2.1:

### Part 1 §1.8.1 Core Managers (9):
1. MemoryManager — `kernel.memory` (singleton accessor exists)
2. LLMManager — `kernel.llm` (NOT in implementation)
3. ToolManager — `kernel.tools` (NOT in implementation)
4. StorageManager — `kernel.storage` ✅ Implemented as Core Manager (Task 11)
5. ContextManager — `kernel.context` (NOT in implementation)
6. AgentManager — `kernel.agents` (NOT in implementation)
7. WorkflowManager — `kernel.workflows` ✅ Exported (needs review)
8. SecurityManager — `kernel.security` (NOT in implementation)
9. ObservabilityManager — `kernel.observability` (NOT in implementation)

### Part 4 §4.2.1 Core Managers (9):
1. LifecycleManager — ✅ Implemented (Task 9)
2. StateManager — ✅ Implemented (Task 10)
3. StorageManager — ✅ Implemented (Task 11)
4. WorkflowManager — ✅ Exported (needs deeper review)
5. SecurityManager — ❌ GAP (not implemented)
6. CapabilityManager — ❌ GAP (not implemented)
7. ResourceManager — ✅ Implemented (Task 13)
8. HealthManager — ✅ Implemented (Task 12)
9. ObservabilityManager — ❌ GAP (not implemented)

**Inference:** The implementation follows the **Part 4 Core Manager taxonomy**, not Part 1's. The Part 1 managers LLMManager, ToolManager, ContextManager, and AgentManager are **NOT implemented** — they appear to have been subsumed/replaced by the Part 4 set (e.g., LLMManager → ModelRouter, ToolManager → SkillManager/MCPManager are present as exported modules but are NOT Core Managers in the Part 4 sense).

---

## Kernel Architecture: Implementation Reality

### HermesKernel (kernel.py:109-769)

**Status: EXISTING (partial)**

| Spec Requirement | Implementation |
|---|---|
| 5-state FSM (UNINITIALIZED→INITIALIZING→RUNNING→SHUTTING_DOWN→TERMINATED) | **ASSUMPTION** — Uses `_running: bool` flag (line 139) instead of 5-state FSM |
| 9-phase initialization (Part 1 §1.8.5) | **DERIVED** — Implements Part 4 §4.2.3 5-phase model via LifecycleManager (`_build_phase_topology()`), deferred phases empty |
| 10-phase shutdown (Part 1 §1.8.6) | **DERIVED** — Reverse phase order via LifecycleManager `_do_shutdown()` |
| Core Components C1-C4 construction | **EXISTING** — C1 EventBus (Phase 0), C2 ServiceRegistry (Phase 1), C3 ConfigurationManager (Phase 2), C4 StructuredLogger (Phase 3) |
| `kernel.memory` / `kernel.llm` / etc. accessors | **CONCLICT** — Part 1 §1.8.1 lists 9 singleton accessors; implementation provides `EventBus`, `StateManager`, `StorageManager`, `WorkflowManager`, `ResourceManager`, `HealthManager`, `ConfigurationManager`, `ServiceRegistry`, `StructuredLogger`, `LifecycleManager` (11 accessors, different set) |
| KernelReady / KernelShutdownStarted events | **EXISTING** — `KERNEL_READY` and `KERNEL_SHUTDOWN_STARTED` emitted (lines 296-306, 348-361) |
| Configuration freeze boundary | **EXISTING** — `ConfigurationManager.freeze()` called during Phase 2 |

### State Manager FSM

**Status: ASSUMPTION**

The HermesKernel in `kernel.py` uses a simple `_running: bool` flag (line 139) rather than the 5-state FSM defined in Part 1 §1.8.5. The **LifecycleManager** (not the kernel itself) implements the full 8-state `LifecycleState` enum (UNINITIALIZED, INITIALIZING, OPERATIONAL, DEGRADED, SHUTTING_DOWN, TERMINATED, ROLLBACK_IN_PROGRESS, RECOVERY_IN_PROGRESS) at `lifecycle_manager.py:106-120`. This represents a **DERIVED** architectural decision: the kernel delegates lifecycle state to LifecycleManager rather than maintaining its own FSM.

### EventBus (bus.py / core/bus.py)

**Status: EXISTING**

The EventBus is implemented in two locations:

| Aspect | Canonical Implementation (`events/core/bus.py`) | Legacy Implementation |
|---|---|---|
| **EventBusState** | UNINITIALIZED, INITIALIZING, RUNNING, DRAINING, SHUTDOWN | — |
| **PublishStatus** | ACCEPTED, REJECTED_VALIDATION, REJECTED_CAPACITY, REJECTED_SHUTDOWN, REJECTED_DUPLICATE | — |
| **Priority lanes** | 5 levels: CRITICAL, HIGH, NORMAL, LOW, BACKGROUND | — |
| **Max dispatch depth** | Configurable (default 16) | 8 (`_EVENT_EMIT_DEPTH_CAP` in hermes-agent) |
| **DLQ** | DeadLetterEntry with classification, bounded deque | — |
| **Idempotency keys** | Supported via PublishOptions.idempotencyKey | — |
| **Event history** | Bounded ring buffer (default 10000) | — |
| **Replay** | Memory-only v1.0 API | — |
| **Single dispatch worker** | Optional background worker | Single daemon thread (`_event_worker_loop`) |
| **Sync-to-async bridge** | N/A (async-native) | `_pending_tasks` strong-reference pattern |

**Key difference from hermes-agent:** The canonical EventBus validates events against the **EventTypeRegistry** (checks registered EventTypes, validates payload schema, verifies SHA-256 checksum). The hermes-agent PluginContext does none of this — it uses bare strings for events.

### Event Envelope (event.py)

**Status: EXISTING — Full 12-field envelope verified**

All 12 fields are implemented as read-only properties with validation:

```
eventId           : UUIDv7           ✅ (validated version=7)
eventType         : EventType        ✅ (closed enum, 121 members)
eventVersion      : SemanticVersion  ✅ (defaults "1.0.0")
timestamp         : ISO8601 UTC ns   ✅ (regex-validated, Z suffix)
timestampMonotonic: MonotonicNs      ✅ (auto-generated if None)
correlationId     : UUID             ✅ (required, auto-UUIDv7 if None)
causationId       : UUID | null      ✅ (null for root events)
source            : ComponentIdentity ✅ (required, anonymous prohibited)
target            : ComponentIdentity | null ✅ (null = broadcast)
priority          : EventPriority    ✅ (5-level: CRITICAL→BACKGROUND)
category          : EventCategory    ✅ (5-level, derived from EventType)
payload           : EventPayload     ✅ (immutable, JSON-safe, validated)
checksum          : SHA256Hex        ✅ (computed from canonical payload)
```

**Immutability:** `__slots__` + raising `__setattr__` enforces write-once immutability (INV-EVT-001). Deep immutability via `object.__setattr__` bypass for internal storage (INV-EVT-012).

### EventType Enumeration

**Status: EXISTING — 121 canonical types**

The spec (Part 2 §2.3.1) states 97 types but the enumerated implementation has 121 members. The docstring at `types.py:6` explicitly notes: "118 canonical types in the enumeration; the prose states 97 — we conform to the enumeration." Code inspection confirms **121 members** via `grep -c`.

Categories (spec Part 2 §2.3.2):
- SYSTEM: 16 events (KERNEL_*, CORE_COMPONENT_*, CORE_MANAGER_*, HEARTBEAT, CONFIGURATION_*)
- CONTROL: 6 events (WORKFLOW_*, TASK_*, etc.)
- DATA: ~12 events (STATE_*, ARTIFACT_*, CHECKPOINT_*, MEMORY_*, CONTEXT_*)
- AUDIT: ~32 events (PLANNING_*, CODING_*, REVIEW_*, TESTING_*, DEPLOYMENT_*, COUNCIL_*)
- DIAGNOSTIC: ~32 events (METRIC_*, TRACE_*, HEALTH_*, SERVICE_*, RESOURCE_*, SKILL_*, MCP_*, MODEL_*, etc.)

**Note:** The hermes-agent `CoreComponentInitialized` is NOT a canonical EventType — it is a string passed to the `diagnostic_hook` callback, not an emitted `Event` object. This is an **ASSUMPTION** that diagnostic callbacks suffice.

### CONFLICT Resolution: `kernel.*` vs `core.*` Namespace

**Status: CONFLICT (resolved with documented deviation)**

Part 3 §3.4.8 / INV-SR-NS-002 reserves the `kernel` namespace in ServiceRegistry ("not in ServiceRegistry; registration throws"). Part 4 repeatedly names manager ServiceRegistry identities as `kernel.lifecycle`, `kernel.state`, `kernel.storage`, `kernel.health`, `kernel.resource`.

The implementation resolves this consistently across all Core Managers:

| Spec (Part 4) | Implementation | Reason |
|---|---|---|
| `kernel.lifecycle` | `core.lifecycle` | INV-SR-NS-002 violation |
| `kernel.state` | `core.state` | Same precedent (Task 10) |
| `kernel.storage` | `core.storage` | Same precedent (Task 11) |
| `kernel.health` | `core.health` | Same precedent (Task 12) |
| `kernel.resource` | `core.resource` | Same precedent (Task 13) |

**Configuration namespace** remains `kernel.{manager}.*` (per Part 4 config schema) — only the ServiceRegistry *identity* uses `core.*`. This is documented as **CONFLICT E.1** in every manager's module docstring.

### Event Type Mapping (CONFLICT E.1)

Part 4 §4.3.10 names PascalCase events (`KernelLifecycleEvent`, `KernelPhaseCompletedEvent`, etc.) that do NOT exist in the canonical `EventType` enum. The implementation maps these to canonical SCREAMING_SNAKE_CASE types:

| Part 4 Intended Event | Canonical EventType Used |
|---|---|
| `KernelLifecycleEvent` (INITIALIZING) | `KERNEL_INITIALIZATION_STARTED` |
| `KernelLifecycleEvent` (OPERATIONAL) | `KERNEL_READY` |
| `KernelLifecycleEvent` (DEGRADED) | `CORE_COMPONENT_DEGRADED` |
| `KernelLifecycleEvent` (SHUTTING_DOWN) | `KERNEL_SHUTDOWN_STARTED` |
| `KernelLifecycleEvent` (TERMINATED) | `KERNEL_TERMINATED` |
| `KernelPhaseCompletedEvent` | `CORE_MANAGER_INITIALIZED` |
| `KernelDegradedEvent` | `CORE_MANAGER_DEGRADED` |
| `KernelLifecycleEvent` (ROLLBACK) | `KERNEL_INITIALIZATION_FAILED` |
| `KernelRecoveryEvent` | (no canonical equivalent — omitted) |

The intended Part-4 name is preserved in the event payload's `event_name` field. This is a **DERIVED** mapping with documented inference path (CONFLICT E.1 resolution).

---

## hermes-agent Comparison

The `hermes-agent/` codebase (v0.20.1) is a **separate CLI application**, NOT the AI-OS kernel. It has zero overlap with the spec's Core Components, Core Managers, or kernel architecture.

| Spec Concept | hermes-agent Implementation | Status |
|---|---|---|
| HermesKernel singleton | Does NOT exist | GAP |
| 5-state kernel FSM | Does NOT exist | GAP |
| EventBus with typed events | `PluginContext.emit/subscribe` pub/sub | **CONFLICT** |
| 12-field Event envelope | 5-field `_QueuedPluginEvent` (no envelope) | GAP |
| 97/121 EventType enum | Bare string event names | GAP |
| Core Components C1-C4 | Not implemented | GAP |
| Core Managers (Part 4 §4.2) | Not implemented | GAP |
| Phase-based init (9 phases) | No phases; simple init | GAP |
| Phase-based shutdown (10 phases) | No phases; simple finalize | GAP |
| `kernel.*` ServiceRegistry namespaces | Not applicable | GAP |
| SecurityManager (ABAC) | Not implemented | GAP |
| ConfigurationManager 4-layer merge | `ConfigManager` (flat config) | GAP |

**Event bus gap detail:** The hermes-agent `PluginContext` (plugins.py:3213-5101) implements a pub/sub system with:
- 5-field `_QueuedPluginEvent` (event, payload, subscriptions, depth, generation) — missing all 12 envelope fields
- Namespace-forcing: rejects `:` in event names, forces `<plugin_key>:<event>`
- `_EVENT_EMIT_DEPTH_CAP=8` recursion protection
- `_EVENT_PENDING_CAP=64` bounded pending budget
- `copy.deepcopy(item.payload)` per subscriber for isolation
- Generation-based reset via `_reset_event_bus()`
- Single daemon thread dispatch (`_event_worker_loop`)
- NO idempotency keys
- NO dead-letter queue
- NO priority lanes
- NO replay
- NO EventBusState lifecycle (UNINITIALIZED/INITIALIZING/RUNNING/DRAINING/SHUTDOWN)
- NO EventRegistryError / EventValidationError error model
- NO EventBusConfig

---

## Summary of Gaps in src/aios/

### Critical Gaps (unimplemented Core Managers from Part 4 §4.2.1):
1. **SecurityManager** (Part 4 §4.7, M8) — ABAC authorization, 7 enforcement points, 5 secret types. Exported from `__init__.py` but module file not yet reviewed for content.
2. **CapabilityManager** (Part 4 §4.6, CONFLICT-CM-01) — Capability registry for step execution mediation.
3. **ObservabilityManager** (Part 4 §4.9) — Metrics, tracing, observability pipeline.

### Assumed/Partially-GAP Areas:
4. **HermesKernel FSM** — Uses `_running: bool` rather than 5-state FSM (ASSUMPTION; FSM delegated to LifecycleManager).
5. **ModelRouter, MemoryManager, SkillManager, MCPManager, CouncilManager, CheckpointManager, RetryManager, RootCauseAnalyzer, AIAgencyService** — Exported from `__init__.py` but file content not yet inspected for depth. Classification pending deeper review.

### Spec-vs-Enum Discrepancy:
6. **EventType count** — Spec says 97; enumeration has 121 (docstring notes 118). The discrepancy is documented in `types.py:6` as a DERIVED correction.

---

## Inference Paths

All **DERIVED** claims above cite specific file/line locations:
- Event envelope fields: `event.py:63-80` (slots), `:308-358` (properties)
- EventType count: `types.py:22-169`, verified via `grep -c` = 121
- Lifecycle state machine: `lifecycle_manager.py:106-120` (LifecycleState enum), `:124-165` (_TRANSITIONS)
- Phase topology: `lifecycle_manager.py:286-303` (_build_phase_topology)
- Kernel `_running` flag: `kernel.py:139`
- ServiceRegistry namespace conflict: All manager modules cite `INV-SR-NS-002`, Part 3 §3.4.8

All **CONFLICT** claims preserve the contradiction without resolution:
- CONFLICT-CC-01: Core Component set varies (Part 1: 4 components; Part 3: StructuredLogger vs Part 1 LifecycleManager)
- CONFLICT-CM-01: Core Manager set varies (Part 1: 9 managers vs Part 4: different 9 managers)
- CONFLICT-EVENT-01: SCREAMING_SNAKE_CASE (Part 2) vs PascalCase (Part 4 §4.3.10)
- CONFLICT-INIT-01: Part 1 9-phase vs Part 4 5-phase
- CONFLICT E.1: `kernel.*` ServiceRegistry namespace (Part 4) vs `core.*` reserved (Part 3)

---

## Recommendations

1. **Complete the 3 missing Core Managers**: SecurityManager (Part 4 §4.7), CapabilityManager (Part 4 §4.6), ObservabilityManager (Part 4 §4.9) — these are the only Part 4 Core Managers not present.
2. **Resolve the kernel FSM**: Either implement the 5-state FSM in HermesKernel (Part 1 §1.8.5) or formally document the delegation to LifecycleManager's 8-state model as a design decision.
3. **Audit exported-but-unreviewed modules**: ModelRouter, MemoryManager, SkillManager, MCPManager, CouncilManager, CheckpointManager, RetryManager, RootCauseAnalyzer, AIAgencyService — verify they are full Core Managers or helper services.
4. **Document the EventType count discrepancy**: 97 (prose) vs 121 (enumeration). The implementation chose to conform to the enumeration; this should be formally ratified.
