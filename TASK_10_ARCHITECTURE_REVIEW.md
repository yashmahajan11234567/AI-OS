# TASK 10 ARCHITECTURE REVIEW — StateManager Core Manager Upgrade

**Status:** DRAFT → READY FOR GIT CHECKPOINT  
**Task:** 10 (immediately follows Task 9 — LifecycleManager)  
**Date:** 2026-08-20  
**Terminal:** Terminal 1 (Architecture / Implementation Planning)  
**Scope:** Determine exact scope of Task 10. Does NOT implement anything. Does NOT modify any files. Does NOT write code.  

---

## 1. Task 10 Identity

| Field | Value |
|-------|-------|
| **Task** | 10 |
| **Core Manager** | StateManager |
| **Part 4 Section** | §4.4 (StateManager) |
| **Initialization Phase** | Phase 2 — "State & Storage" |
| **Shutdown Phase** | Phase 4 — "State & Storage" (reverse order) |
| **Dependencies** | LifecycleManager (Phase 1), StorageManager (Phase 2, same phase — alphabetical: StateManager before StorageManager) |
| **ServiceRegistry ID** | `kernel.state` (per §4.4.9) |
| **Configuration Namespace** | `kernel.state.*` (per §4.4.9) |
| **Preceded by** | Task 9 — LifecycleManager (Phase 1, COMPLETE) |
| **Followed by** | Task 11 — StorageManager (Phase 2) |

**Confirmation:** Task 10 = **StateManager Core Manager upgrade**. The StateManager must be transformed from a standalone module with global singleton accessors into a fully-registered Core Manager that participates in the LifecycleManager 5-phase topology, implements the `ICoreManager` Protocol, registers with ServiceRegistry as `kernel.state`, reads `kernel.state.*` configuration, and uses StructuredLogger for diagnostics.

---

## 2. Existing State (Current Code Snapshot)

### 2.1 What EXISTS today in `src/aios/core/state.py`

- **Class:** `StateManager` (line 50) — has business logic for state management
- **Singletons:** `get_state_manager()`, `set_state_manager()` (lines 431–450)
- **EventBus integration:** Uses `get_core_event_bus()` from C1, emits `STATE_CHANGED`, `STATE_SNAPSHOT_CREATED`, `STATE_RESTORED` — all canonical EventTypes (Part 2 §2.3.1)
- **ComponentIdentity:** Already constructed with `ComponentType.CORE_MANAGER` (line 84–88)
- **Persistence:** File-based snapshot persistence to `self._persistence_path`

### 2.2 What is MISSING from `state.py` (the Task 10 gap)

The existing `StateManager` class does **NOT** implement the `ICoreManager` Protocol. Specifically:

| ICoreManager member | Status in current code | Required for Task 10 |
|---------------------|------------------------|----------------------|
| `name: str` | ❌ Not a property; implicit via class | ✅ Must return `"StateManager"` |
| `phase: int` | ❌ Missing | ✅ Must return `2` |
| `dependencies: list[str]` | ❌ Missing | ✅ Must return `["LifecycleManager", "StorageManager"]` |
| `async initialize()` | ❌ Not async; not a lifecycle method | ✅ Must exist |
| `async shutdown()` | ❌ Missing entirely | ✅ Must exist |
| `def health_ready() -> bool` | ❌ Missing | ✅ Must exist |
| ServiceRegistry registration | ❌ Not done by StateManager itself | ✅ Must register as `kernel.state` |
| ConfigurationManager consumption | ❌ Not wired | ✅ Must read `kernel.state.*` config |
| StructuredLogger diagnostics | ❌ Uses `logging.getLogger(__name__)` (stdlib) | ✅ Must use C4 StructuredLogger |
| LifecycleManager registration | ❌ Not done | ✅ Kernel must call `lifecycle.register_manager(state_mgr)` |

### 2.3 Kernel integration gap (`kernel.py`)

In `kernel.py:_init_core_components()` (line 377–380):
```python
self._state_manager = StateManager(
    persistence_path=self._config.data_dir / "state"
)
set_state_manager(self._state_manager)
```

The kernel constructs StateManager directly but:
- ❌ Does NOT call `lifecycle.register_manager(...)` for StateManager
- ❌ Does NOT call `state_mgr.initialize()` via LifecycleManager phases
- ❌ Does NOT register with ServiceRegistry as `kernel.state`
- The `_start_state_manager()` method (line 591) only calls `load_persisted_snapshots()` — no `initialize()`, no readiness

### 2.4 Phase topology (from `lifecycle_manager.py:286–303`)

```python
CoreManagerPhase(1, "Foundation", ("LifecycleManager",), ())
CoreManagerPhase(2, "State & Storage", ("StateManager", "StorageManager"), (1,))
CoreManagerPhase(3, "Governance", ("SecurityManager", "ResourceManager", "HealthManager"), (1, 2))
CoreManagerPhase(4, "Execution", ("CapabilityManager", "WorkflowManager"), (1, 2, 3))
CoreManagerPhase(5, "Observability", ("ObservabilityManager",), (1, 2, 3, 4))
```

Phase 2 is currently **deferred** because no Phase-2 manager is registered with LifecycleManager. Once StateManager is registered, Phase 2 will execute:
1. `StateManager.initialize()` (alphabetical: "StateManager" < "StorageManager")
2. If StorageManager is registered, `StorageManager.initialize()`
3. `_validate_phase_readiness()` — all present managers must pass `health_ready()`
4. Emit `CORE_MANAGER_INITIALIZED` with `{"phase": 2, "managers": ["StateManager"], ...}`

### 2.5 Shutdown topology (from `lifecycle_manager.py:614`)

Shutdown reverses phase order: Phase 5 → Phase 4 → Phase 3 → Phase 2 → Phase 1. Within Phase 2, alphabetical reverse means `StorageManager` shuts down before `StateManager` (if both present).

### 2.6 Other managers in Phase 2 with `get_*`/`set_*` accessors

- `CheckpointManager` (`checkpoint.py`) — Phase 2 Recovery manager, has `get_checkpoint_manager()`/`set_checkpoint_manager()`
- `RetryManager` (`retry.py`) — Phase 2 Recovery manager, has `get_retry_manager()`/`set_retry_manager()`
- `RootCauseAnalyzer` (`root_cause.py`) — Phase 2 Recovery manager, has `get_root_cause_analyzer()`/`set_root_cause_analyzer()`

These are NOT declared in the phase topology and are NOT Core Managers — they are **Recovery managers** (referenced in Part 4 §4.4.8 Recovery and §4.3.7 rollback). Task 10 does NOT touch them. They remain outside the `ICoreManager` orchestration surface.

---

## 3. Required Files — Create / Modify / Forbid

### 3.1 Files to MODIFY

| # | File | Change |
|---|------|--------|
| 1 | `src/aios/core/state.py` | Add `ICoreManager` interface (name, phase, dependencies, initialize, shutdown, health_ready); add `register_with_service_registry()`; wire StructuredLogger; consume `kernel.state.*` config; keep existing business logic API intact (backward compatible) |
| 2 | `src/aios/core/kernel.py` | After constructing StateManager, register it with LifecycleManager via `lifecycle.register_manager(state_mgr)`; remove/defer `_start_state_manager()` from `_start_services()` (lifecycle now owns it) |
| 3 | `src/aios/core/kernel.py` (imports) | No new imports needed; `StateManager` already imported. May need to pass C2/C3/C4 refs to StateManager constructor |

### 3.2 Files to CREATE

| # | File | Purpose |
|---|------|---------|
| 1 | `tests/unit/test_state_manager.py` | Unit tests for StateManager Core Manager (ICoreManager contract, lifecycle, registration, config, logging) |
| 2 | `tests/integration/test_state_manager_phase.py` | Integration tests for StateManager participating in Phase 2 lifecycle |
| 3 | `tests/unit/test_task10_critical_acceptance.py` | Critical acceptance tests for Task 10 (mirrors Task 9's `test_task9_critical_acceptance.py` pattern) |

### 3.3 Files to FORBID (must NOT be touched)

| # | File | Reason |
|---|------|--------|
| 1 | `src/aios/core/lifecycle_manager.py` | Already Task 9 QA-approved; Task 10 integrates INTO it, not modify it |
| 2 | `src/aios/events/core/types.py` | Closed EventType enum (Part 2 §2.3.1); no new EventTypes to invent |
| 3 | `src/aios/core/configuration_manager.py` | Already Task 7 certified |
| 4 | `src/aios/core/service_registry.py` | Already Task 6 certified |
| 5 | `src/aios/core/structured_logger.py` | Already Task 8 certified |
| 6 | `src/aios/core/workflow.py` | Phase 4 — not in scope for Task 10 |
| 7 | `src/aios/core/resource_manager.py` | Phase 3 — not in scope |
| 8 | `src/aios/core/checkpoint.py`, `retry.py`, `root_cause.py` | Recovery managers — not Core Managers, not in phase topology |
| 9 | `src/aios/core/memory.py`, `mcp_manager.py`, `council_manager.py`, `skill_manager.py`, `ai_agency.py`, `model_router.py` | Engineering services / out-of-scope managers |

---

## 4. ICoreManager Protocol Surface (Target Interface)

From `lifecycle_manager.py:240–262`:

```python
@runtime_checkable
class ICoreManager(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def phase(self) -> int: ...
    @property
    def dependencies(self) -> list[str]: ...
    async def initialize(self) -> Any: ...
    async def shutdown(self) -> Any: ...
    def health_ready(self) -> bool: ...
```

### 4.1 StateManager ICoreManager implementation target

```python
class StateManager:
    # ICoreManager surface
    @property
    def name(self) -> str:
        return _NAME  # "StateManager"

    @property
    def phase(self) -> int:
        return 2  # Phase 2 — State & Storage

    @property
    def dependencies(self) -> list[str]:
        return ["LifecycleManager", "StorageManager"]  # Phase 1 dependency + same-phase sibling

    @property
    def manager_id(self) -> str:
        return _MANAGER_ID  # "kernel.state"

    async def initialize(self) -> KernelState:
        """Phase 2 initialization: load persisted snapshots, register with C2, emit init event."""

    async def shutdown(self) -> KernelState:
        """Phase 4 shutdown: checkpoint, persist, deregister."""

    def health_ready(self) -> bool:
        """Readiness probe: True if event_bus and config are wired."""

    async def register_with_service_registry(self) -> None:
        """Register self as 'kernel.state' in canonical C2."""
```

### 4.2 Constants to define (mirroring LifecycleManager's pattern)

```python
_NAME = "StateManager"
_MANAGER_ID = "kernel.state"  # Part 4 §4.4.9 — ServiceRegistry identity
_PHASE = 2  # Phase 2 — State & Storage
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = ("EventBus", "ServiceRegistry", "ConfigurationManager", "StructuredLogger")
```

> **CONFLICT-E.1 note:** Part 4 §4.4.10 names events like `StateTransitionRequestEvent`, `StateTransitionCommittedEvent`, `StateTransitionDeniedEvent`, `StateSnapshotCreatedEvent`, `StateRecoveryCompletedEvent`. These do NOT exist in the canonical `EventType` enum. Per the CONFLICT E.1 resolution pattern established by Task 9, StateManager must NOT invent new EventTypes. Instead, it uses the existing canonical types:
> - `STATE_CHANGED` (already emits) — maps to `StateTransitionCommittedEvent`
> - `STATE_SNAPSHOT_CREATED` (already emits) — maps to `StateSnapshotCreatedEvent`
> - `STATE_RESTORED` (already emits) — maps to `StateRecoveryCompletedEvent`
> - For `StateTransitionRequestEvent` / `StateTransitionDeniedEvent` — these map to consumption patterns; since SecurityManager (Phase 3) is not yet implemented, the authorization path is deferred (logged as a known gap, same as Task 9's rollback path deferral)

---

## 5. Lifecycle Integration

### 5.1 Initialization Sequence (Phase 2, alphabetical order)

When `LifecycleManager._do_initialize()` reaches Phase 2:

1. **StateManager.initialize()** is called (alphabetically first in Phase 2)
2. (StorageManager.initialize() deferred until Task 11 — phase is deferred if no StorageManager present)
3. `_validate_phase_readiness()` — calls `StateManager.health_ready()`
4. `_emit_phase_completed(Phase 2, [StateManager])` — emits `CORE_MANAGER_INITIALIZED` with `{"phase": 2, "managers": ["StateManager"], ...}`

### 5.2 StateManager.initialize() responsibilities (Task 10 scope)

| Step | Action | Dependency |
|------|--------|------------|
| 1 | Read `kernel.state.*` config from frozen ConfigurationManager | C3 |
| 2 | Initialize StructuredLogger with `manager="StateManager"` | C4 |
| 3 | Load persisted snapshots from disk | Self |
| 4 | Register self with ServiceRegistry as `kernel.state` | C2 |
| 5 | Emit `CORE_MANAGER_INITIALIZED` (via LifecycleManager phase event) | C1 |
| 6 | Set `_initialized = True`, transition to ready state | Self |

### 5.3 StateManager.shutdown() responsibilities (Task 10 scope)

Called during reverse-order Phase 4 shutdown:

| Step | Action | Notes |
|------|--------|-------|
| 1 | Create final state snapshot | Persistence before shutdown |
| 2 | Deregister from ServiceRegistry | C2 cleanup |
| 3 | Flush any pending events | C1 drain |
| 4 | Set `_initialized = False` | Readiness gate |
| 5 | Emit `CORE_MANAGER_SHUTDOWN` | C1 via EventBus |

### 5.4 Dependency validation (LifecycleManager:822–830)

```python
satisfied: set[str] = set(_COMPONENT_DEPENDENCIES)  # C1–C4 always satisfied
for earlier in self._initialized_order:               # phases already done
    satisfied.update(earlier)
for mgr in present:
    for dep in mgr.dependencies:
        if dep not in satisfied:
            raise LifecycleManagerError(...)  # LM-DEP-003
```

StateManager's `dependencies` MUST include:
- `"LifecycleManager"` (Phase 1 — already initialized) ✅
- `"StorageManager"` (same Phase 2 — NOT yet implemented; LifecycleManager resolves alphabetical order: StateManager before StorageManager, so StorageManager will NOT be in `satisfied` at StateManager's init time)

**Resolution:** If StateManager lists `"StorageManager"` as a dependency, `_validate_phase_dependencies` will reject it because StorageManager is in the same phase (Phase 2) and won't be in the `satisfied` set yet. **Solution:** StateManager should list ONLY Phase 1 dependencies: `["LifecycleManager"]`. The StorageManager relationship is a *same-phase sibling* relationship, not a *predecessor* dependency. This matches the dependency matrix in §4.2.5 where StateManager depends on Lifecycle (✓) and Storage (✓) — but the Phase 2 ordering is alphabetical (StateManager before StorageManager), so StateManager initializes first. The StorageManager dependency is handled by deferring checkpoint integration until StorageManager exists (same pattern as Task 9 deferring HealthManager gate).

**Final `dependencies`:** `["LifecycleManager"]`

---

## 6. EventBus Integration

### 6.1 Events CURRENTLY emitted by StateManager (existing code)

| EventType | §4.4.10 Mapping | Status |
|-----------|-----------------|--------|
| `STATE_CHANGED` | → `StateTransitionCommittedEvent` | ✅ Already emitted, canonical |
| `STATE_SNAPSHOT_CREATED` | → `StateSnapshotCreatedEvent` | ✅ Already emitted, canonical |
| `STATE_RESTORED` | → `StateRecoveryCompletedEvent` | ✅ Already emitted, canonical |

### 6.2 Events CURRENTLY consumed by StateManager

None — StateManager does not currently subscribe to any events.

### 6.3 Events StateManager SHOULD consume (per §4.4.9)

| EventType | Purpose | Implementation status |
|-----------|---------|----------------------|
| `CORE_COMPONENT_INITIALIZED` | Know when C1–C4 are ready (for dependency awareness) | Phase boundary; handled by kernel |
| `CORE_MANAGER_INITIALIZED` | Know when Phase 1 (LifecycleManager) is complete | ✅ Available |
| `CORE_MANAGER_DEGRADED` | Know when another manager is degraded | Available for future |
| `CONFIGURATION_FROZEN` | Know when C3 config is frozen (ready to read `kernel.state.*`) | Available |

### 6.4 Events StateManager SHOULD NOT emit (CONFLICT E.1 mapping)

StateManager must NOT invent `StateTransitionRequestEvent`, `StateTransitionDeniedEvent`, `StateCorruptionDetectedEvent`, `StateCheckpointDeferredEvent`, `StateRecoveryFailedEvent`. These map to:
- `STATE_CHANGED` (commit → use existing)
- `CORE_MANAGER_FAILED` (denial/failure → use existing)
- `CORE_COMPONENT_DEGRADED` (deferred → use existing)

---

## 7. ServiceRegistry Integration

### 7.1 Registration pattern (mirror LifecycleManager §4.3.10)

StateManager must register itself with the canonical ServiceRegistry (C2) during `initialize()`:

```python
await self._service_registry.register(
    self,
    service_id="kernel.state",  # _MANAGER_ID
    service_type=ServiceType.ENGINEERING,
    metadata={
        "kind": "core_manager",
        "manager": "StateManager",
        "phase": 2,
        "lifecycle_state": self._state.value,
    },
)
```

### 7.2 Namespace rules (INV-SR-NS-002)

- `kernel` namespace is reserved by ServiceRegistry
- `kernel.state` is permitted (mirrors `core.lifecycle` pattern used by LifecycleManager, but Part 4 §4.4.9 explicitly says `kernel.state`)
- Must NOT use `core.state` — Part 4 §4.4.9 says `kernel.state` specifically

### 7.3 Deregistration on shutdown

StateManager must call `self._service_registry.mark_service_shutdown("kernel.state")` during `shutdown()`.

---

## 8. Configuration Integration

### 8.1 Configuration namespace (§4.4.9)

| Config Path | Type | Default | Description |
|-------------|------|---------|-------------|
| `kernel.state.persistencePath` | str | `./data/state` | Where snapshots are persisted |
| `kernel.state.snapshotIntervalSeconds` | int | 300 | Scheduled snapshot interval |
| `kernel.state.retentionPolicy.maxSnapshots` | int | 10 | Max snapshots per identifier |
| `kernel.state.consistencyClass` | str | `EVENTUAL` | STRONG / EVENTUAL / EPHEMERAL |
| `kernel.state.checkpointOnTransition` | bool | true | Whether to checkpoint before commit |
| `kernel.state.shutdownTimeoutMs` | int | 5000 | Max time for shutdown checkpoint |

### 8.2 Configuration read pattern (mirror LifecycleManager)

StateManager reads from the **frozen** ConfigurationManager (frozen at `Phase 2 → 3` boundary per kernel.py:367):

```python
def _read_config_str(self, path: str, default: str) -> str:
    if self._configuration is None:
        return default
    val = self._configuration.get(path, default=default)
    return str(val) if val is not None else default

def _read_config_int(self, path: str, default: int) -> int:
    if self._configuration is None:
        return default
    val = self._configuration.get(path, default=default)
    return int(val) if isinstance(val, (int, float)) else default
```

---

## 9. StructuredLogger Integration

### 9.1 Current logging (state.py)

Uses `logging.getLogger(__name__)` — stdlib logger, NOT C4 StructuredLogger.

### 9.2 Target logging pattern (mirror LifecycleManager §3.6.4/§3.6.6)

```python
def _log_info(self, message: str, **fields: Any) -> None:
    if self._logger is not None:
        self._logger.info(message, manager="StateManager", **fields)
```

### 9.3 Log levels to use

| Event | LogLevel |
|-------|----------|
| initialize() start/complete | INFO |
| shutdown() start/complete | INFO |
| State transition | DEBUG |
| State transition denied | WARNING |
| Checkpoint write/read failure | ERROR |
| State corruption detected | CRITICAL (AUDIT) |
| Snapshot restoration | INFO |

---

## 10. Singleton Rules

### 10.1 Invariant compliance

| Invariant | Current state |
|-----------|---------------|
| INV-EB-001: Exactly one EventBus per process | ✅ Already uses `get_core_event_bus()` |
| INV-SR-STR-001: Exactly one ServiceRegistry per process | ✅ Must register with the canonical singleton |
| Singleton pattern for StateManager | ✅ Must maintain `get_state_manager()` / `set_state_manager()` / `reset_state_manager()` for backward compatibility |

### 10.2 Singleton accessor pattern (mirror LifecycleManager)

StateManager must provide:
- `get_state_manager(...)` — returns the singleton (for backward compat with kernel.py:54, workflow.py, etc.)
- `set_state_manager(manager)` — sets the singleton (for kernel wiring)
- `reset_state_manager_singleton()` — NEW, for test isolation (mirrors `reset_lifecycle_manager_singleton`)

### 10.3 Kernel wiring changes

In `_init_core_components()`, the kernel currently does:
```python
self._state_manager = StateManager(persistence_path=...)
set_state_manager(self._state_manager)
```

After Task 10, it must additionally:
```python
# After LifecycleManager is initialized (Phase 1 complete):
lm = get_lifecycle_manager(...)
lm.register_manager(self._state_manager)  # Register for Phase 2 orchestration
```

The kernel must NOT call `state_manager.initialize()` directly — LifecycleManager's phase topology handles that.

---

## 11. Implementation Sequence (Recommended Order)

> **NOTE:** This is analysis only. Terminal 2 will receive this review and implement.

| Step | File | Action | Key methods/constants |
|------|------|--------|----------------------|
| 1 | `state.py` | Add module constants | `_NAME`, `_MANAGER_ID`, `_PHASE`, `_VERSION`, `_COMPONENT_DEPENDENCIES` |
| 2 | `state.py` | Add `register_with_service_registry` method | Mirror `LifecycleManager.register_with_service_registry` |
| 3 | `state.py` | Add `initialize()` method | Read config, setup logger, load snapshots, register with C2 |
| 4 | `state.py` | Add `shutdown()` method | Final snapshot, deregister, emit shutdown event |
| 5 | `state.py` | Add `health_ready()` method | Return True if initialized + event_bus wired |
| 6 | `state.py` | Add ICoreManager properties | `name`, `phase`, `dependencies`, `manager_id` |
| 7 | `state.py` | Wire StructuredLogger | Replace stdlib logger with C4; add `_log_*` helpers |
| 8 | `state.py` | Add `reset_state_manager_singleton()` | Mirror lifecycle_manager pattern |
| 9 | `kernel.py` | Register StateManager with LifecycleManager | Call `lm.register_manager(...)` after Phase 1 |
| 10 | `kernel.py` | Remove StateManager from `_start_services` | Let LifecycleManager handle Phase 2 init |
| 11 | `kernel.py` | Remove `_start_state_manager` | No longer needed (lifecycle handles it) |
| 12 | Tests | Create `test_state_manager.py` | Unit tests for ICoreManager surface |
| 13 | Tests | Create `test_state_manager_phase.py` | Integration: Phase 2 lifecycle |
| 14 | Tests | Create `test_task10_critical_acceptance.py` | Acceptance gate |

---

## 12. Testing Plan

### 12.1 Unit Tests (`tests/unit/test_state_manager.py`)

| Test Category | Test Description | Assertion |
|---------------|-----------------|-----------|
| ICoreManager Protocol | StateManager is structurally compatible with ICoreManager | `isinstance(sm, ICoreManager)` |
| Metadata | name, phase, dependencies, manager_id | `sm.name == "StateManager"`, `sm.phase == 2`, etc. |
| initialize() | Reads config, sets up logger, registers with SR | `sm._initialized == True`, SR has `kernel.state` |
| initialize() idempotency | Calling twice is safe | No exceptions, no double-registration |
| shutdown() | Creates final snapshot, deregisters | `sm._initialized == False`, SR marks shutdown |
| shutdown() idempotency | Calling twice is safe | No exceptions |
| health_ready() | Returns True when wired | `sm.health_ready() == True` |
| Singleton accessors | get/set/reset work correctly | Singleton round-trip |
| Config consumption | Reads `kernel.state.*` correctly | Config values applied |
| StructuredLogger integration | Uses C4 logger, not stdlib | `_logger` is StructuredLogger |

### 12.2 Integration Tests (`tests/integration/test_state_manager_phase.py`)

| Test Category | Test Description |
|---------------|-----------------|
| Phase 2 integration | StateManager completes Phase 2 initialization via LifecycleManager |
| Phase completeness | `CORE_MANAGER_INITIALIZED` emitted with phase=2, managers=["StateManager"] |
| ServiceRegistry registration | `kernel.state` appears in SR after Phase 2 |
| Reverse shutdown | StateManager shuts down in Phase 4 reverse order |
| Dependency satisfaction | LifecycleManager does NOT reject StateManager deps |
| Kernel integration | `run_kernel()` → Phase 2 executes → `kernel.state_manager` accessible |
| Idempotency | Re-initialize after shutdown fails gracefully |

### 12.3 Critical Acceptance (`tests/unit/test_task10_critical_acceptance.py`)

Mirrors Task 9's `test_task9_critical_acceptance.py` pattern:

| Test | Assertion |
|------|-----------|
| ACCEPT-01: ICoreManager compliance | `StateManager` satisfies `ICoreManager` Protocol |
| ACCEPT-02: Phase topology | StateManager appears in Phase 2 of `phase_plan` |
| ACCEPT-03: ServiceRegistry registration | After kernel start, `kernel.state` is registered in C2 |
| ACCEPT-04: EventBus usage | StateManager publishes only canonical EventTypes |
| ACCEPT-05: Shutdown path | `kernel.stop()` cleanly shuts down StateManager in Phase 4 |

---

## 13. Regression Requirements

### 13.1 Must NOT break (existing working code)

| Component | Must still work | Risk area |
|-----------|----------------|-----------|
| `test_integration.py` | `test_simple_workflow`, `test_parallel_workflow` use `StateManager` via `get_state_manager()` | API compatibility of existing methods |
| `test_integration.py` | `TestCheckpointRecovery` uses `CheckpointManager` | CheckpointManager is separate — no risk |
| `test_integration.py` | `kernel` fixture starts/stops kernel | Kernel lifecycle must still work |
| `state.py` existing API | `set_state()`, `get_state()`, `update_state()`, `delete_state()`, `checkpoint()`, `restore()`, `get_history()`, `list_identifiers()`, `clear_scope()`, `load_persisted_snapshots()` | All must remain backward-compatible |

### 13.2 Backward compatibility constraints

- `get_state_manager()` signature: must still accept `persistence_path` kwarg
- `StateManager.__init__` signature: must still accept `persistence_path` kwarg (kernel.py:377 passes it)
- All existing public methods on StateManager: must preserve signatures and behavior
- The ICoreManager methods (`initialize`, `shutdown`, `health_ready`) are NEW additions — must not change existing call patterns

### 13.3 Kernel.py changes that must be backward-compatible

- `_start_services()` currently calls `_start_state_manager()` which calls `load_persisted_snapshots()`
- After Task 10: Phase 2 LifecycleManager initialization calls `StateManager.initialize()` which should do `load_persisted_snapshots()` internally
- The kernel's `_start_services()` should NOT call StateManager start methods directly — they're handled by LifecycleManager phases
- But if LifecycleManager is not initialized (edge case / test without kernel), `get_state_manager()` must still work standalone

---

## 14. Error Handling Strategy

### 14.1 Exception types

StateManager should define (mirroring LifecycleManager's `LifecycleManagerError`):

```python
class StateManagerError(Exception):
    """StateManager-specific error with rule_id and original_error."""
    def __init__(self, message: str, *, rule_id: str | None = None, original_error: BaseException | None = None):
        super().__init__(message)
        self.rule_id = rule_id
        self.original_error = original_error
```

### 14.2 Error scenarios and responses

| Scenario | Response | Rule ID |
|----------|----------|---------|
| EventBus not available at construction | Raise RuntimeError (matches existing pattern) | SM-INIT-001 |
| ServiceRegistry registration fails | Log warning, continue (non-fatal, like LifecycleManager) | SM-REG-001 |
| Snapshot load fails during initialize | Log error, continue with empty state (recovery path in Phase 3+) | SM-SNAP-001 |
| Checkpoint persistence fails | Log error (non-fatal for EVENTUAL consistency) | SM-CP-001 |
| Shutdown timeout | Log warning, proceed to deregister | SM-SHUT-001 |
| Configuration read fails | Use defaults | SM-CFG-001 |

### 14.3 Idempotency

- `initialize()`: If already initialized, return current state (no-op)
- `shutdown()`: If already shut down, return current state (no-op)
- `health_ready()`: Returns True only after successful `initialize()` and before `shutdown()`

---

## 15. Forbidden Changes

### 15.1 Architecture violations (MUST NOT)

| Forbidden action | Architecture rule |
|------------------|-------------------|
| Invent new EventType members | Closed enum (Part 2 §2.3.1); CONFLICT E.1 mapping rule |
| Direct state mutations bypassing StateManager | §4.4.11 Extension Constraints |
| Bypass EventBus for inter-manager communication | Part 4 §4.12.3 — event-first architecture |
| Implement StorageManager in this task | Phase 2, alphabetical order: StateManager first; StorageManager is Task 11 |
| Implement SecurityManager/ResourceManager/HealthManager | Phase 3 — separate tasks |
| Modify LifecycleManager's phase topology | Task 9 is QA-approved; Task 10 integrates into it |
| Bypass LifecycleManager for StateManager init/shutdown | Violates Phase 1–5 orchestration model |

### 15.2 Code-level prohibitions

| Prohibited pattern | Explanation |
|--------------------|-------------|
| `def initialize(self)` (non-async) | ICoreManager Protocol requires `async def initialize()` |
| `import logging` + stdlib logger | Must use C4 StructuredLogger with `manager="StateManager"` field |
| Direct `self._event_bus = EventBus()` construction | Must use `get_core_event_bus()` singleton (INV-EB-001) |
| `self._service_registry = ServiceRegistry()` construction | Must receive C2 via DI from kernel |
| `self._config = ConfigurationManager()` construction | Must receive C3 via DI from kernel |
| Hardcoded config values | Must read from `kernel.state.*` namespace |
| Synchronous I/O in initialize/shutdown | Must be async; use asyncio for file I/O |
| `time.sleep()` in async context | Use `asyncio.sleep()` |

---

## 16. Architecture Risks

| Risk ID | Risk | Severity | Mitigation |
|---------|------|----------|------------|
| RISK-16-1 | StorageManager dependency listed in `dependencies` causes LifecycleManager dep validation failure (same-phase sibling) | HIGH | Only list `["LifecycleManager"]` as dependency; defer StorageManager integration |
| RISK-16-2 | Existing `StateManager.__init__` takes `persistence_path` but ICoreManager pattern in LifecycleManager takes no args → constructor signature conflict | HIGH | Kernel constructs StateManager with params; then calls `register_manager()`. `initialize()` takes no args. |
| RISK-16-3 | Removing StateManager from `_start_services()` breaks test_integration.py kernel fixture | MEDIUM | Keep `load_persisted_snapshots()` inside `initialize()` so Phase 2 covers it |
| RISK-16-4 | WorkflowManager (Phase 4) and ResourceManager (Phase 3) depend on StateManager → timing of registration matters | MEDIUM | Phase 2 < Phase 3 < Phase 4, so StateManager initializes first — correct ordering |
| RISK-16-5 | StructuredLogger may not be available when StateManager.initialize() runs (C4 is Phase 3 in §3.7.3 but kernel init is different) | LOW | Kernel initializes C4 before LifecycleManager; pass as DI param |
| RISK-16-6 | `reset_state_manager_singleton()` needed for test isolation but doesn't exist yet | LOW | Add it; mirror `reset_lifecycle_manager_singleton()` pattern |
| RISK-16-7 | `kernel.state` namespace conflicts with existing ServiceRegistry entries | LOW | Check §4.4.9 — this is the canonical ID; no conflict in current code |
| RISK-16-8 | `test_integration.py` imports `StateManager` from `aios.core.state` — path must not change | LOW | Do NOT move the file; modify in place |

---

## 17. Acceptance Criteria

### 17.1 Functional

| # | Criterion | Test |
|---|-----------|------|
| AC-1 | StateManager satisfies `ICoreManager` Protocol | `isinstance(sm, ICoreManager)` |
| AC-2 | StateManager is registered with LifecycleManager | `lm._managers["StateManager"] == sm` |
| AC-3 | StateManager Phase 2 initializes via LifecycleManager.initialize() | `KERNEL_READY` event after Phase 2 complete |
| AC-4 | StateManager registers as `kernel.state` in ServiceRegistry | `sr.get_registration("kernel.state")` succeeds |
| AC-5 | StateManager reads `kernel.state.*` configuration | Config values are applied (snapshot interval, etc.) |
| AC-6 | StateManager uses StructuredLogger for diagnostics | `_logger` is `StructuredLogger` instance |
| AC-7 | StateManager emits only canonical EventTypes | Grep: no new EventType members added |
| AC-8 | Phase 4 shutdown calls StateManager.shutdown() | `CORE_MANAGER_SHUTDOWN` emitted during kernel.stop() |
| AC-9 | Existing StateManager API backward-compatible | All `test_integration.py` tests pass |
| AC-10 | `kernel.state_manager` accessible after init | `kernel.state_manager is not None` |

### 17.2 Quality gates

| Gate | Requirement |
|------|-------------|
| QG-1 | All new unit tests pass (`pytest tests/unit/test_state_manager.py`) |
| QG-2 | All new integration tests pass (`pytest tests/integration/test_state_manager_phase.py`) |
| QG-3 | All critical acceptance tests pass (`pytest tests/unit/test_task10_critical_acceptance.py`) |
| QG-4 | No regressions: `pytest tests/integration/test_integration.py` passes |
| QG-5 | No regressions: `pytest tests/unit/test_lifecycle_manager.py` passes |
| QG-6 | No new EventType members added (grep `types.py`) |
| QG-7 | No modifications to `lifecycle_manager.py` |
| QG-8 | ICoreManager Protocol unchanged |

---

## 18. Key Code References

| Artifact | Location | Lines |
|----------|----------|-------|
| ICoreManager Protocol | `lifecycle_manager.py` | 240–262 |
| Phase topology | `lifecycle_manager.py` | 286–303 |
| `register_manager()` | `lifecycle_manager.py` | 456–470 |
| `_validate_phase_dependencies()` | `lifecycle_manager.py` | 822–830 |
| `_resolve_phase_managers()` | `lifecycle_manager.py` | 862–865 |
| LifecycleManager as ICoreManager | `lifecycle_manager.py` | 372–401 |
| StateManager (current) | `state.py` | 50–451 |
| StateManager singletons | `state.py` | 427–450 |
| StateManager ComponentIdentity | `state.py` | 84–88 |
| StateManager `_emit_event` | `state.py` | 391–424 |
| Kernel init StateManager | `kernel.py` | 377–380 |
| Kernel `_start_state_manager` | `kernel.py` | 591–592 |
| Kernel `_init_lifecycle_manager` | `kernel.py` | 420–451 |
| LifecycleManager `register_with_service_registry` | `lifecycle_manager.py` | 943–968 |
| LifecycleManager `_log_*` helpers | `lifecycle_manager.py` | 972–986 |
| LifecycleManager singleton accessors | `lifecycle_manager.py` | 993–1036 |
| LifecycleManager constants | `lifecycle_manager.py` | 84–95 |
| EventType STATE_* members | `types.py` | 90–92 |
| EventType CORE_MANAGER_* members | `types.py` | 51–54 |
| Shutdown reverse-order loop | `lifecycle_manager.py` | 612–632 |

---

## 19. Readiness Score

| Dimension | Weight | Score | Notes |
|-----------|--------|-------|-------|
| Requirements clarity | 15% | 5/5 | §4.4.1–§4.4.13 is detailed; clear interaction contracts |
| Existing code coverage | 15% | 4/5 | StateManager exists with business logic; missing ICoreManager surface |
| Dependency availability | 15% | 5/5 | C1–C4 all complete (Tasks 5–8); LifecycleManager complete (Task 9) |
| Architecture risk | 15% | 4/5 | Main risk: same-phase dependency validation (RISK-16-1); manageable |
| Implementation clarity | 15% | 5/5 | Clear pattern from LifecycleManager to mirror |
| Test coverage plan | 10% | 4/5 | Clear test categories; critical acceptance pattern from Task 9 |
| Regression safety | 10% | 4/5 | Existing API must be preserved; kernel.py changes are localized |
| Forbidden invention risk | 10% | 5/5 | CONFLICT E.1 mapping is established; no new EventTypes |

**Overall Score: 91/100 — READY FOR IMPLEMENTATION**

> **Note on score:** Slightly lower than Task 9's 94/100 due to the same-phase dependency validation subtlety (RISK-16-1) and the need to carefully preserve backward compatibility with existing `StateManager.__init__` signature while conforming to the ICoreManager `initialize()` pattern. These are manageable but require careful attention.

---

## 20. Deliverable to Terminal 2

Terminal 2 should receive this document and implement:

1. **StateManager ICoreManager upgrade** in `src/aios/core/state.py`:
   - Add module constants (`_NAME`, `_MANAGER_ID`, `_PHASE`, `_VERSION`, `_COMPONENT_DEPENDENCIES`)
   - Add `ICoreManager` surface: `name`, `phase`, `dependencies`, `manager_id`, `initialize()`, `shutdown()`, `health_ready()`, `register_with_service_registry()`
   - Add `reset_state_manager_singleton()` for test isolation
   - Wire StructuredLogger (replace stdlib logger)
   - Move `load_persisted_snapshots()` into `initialize()`
   - Add `StateManagerError` exception class with `rule_id` / `original_error`
   - Preserve ALL existing public API (backward compatible)

2. **Kernel integration** in `src/aios/core/kernel.py`:
   - After `_init_lifecycle_manager()`, call `lm.register_manager(self._state_manager)`
   - Remove StateManager from `_start_services()` (lifecycle now handles Phase 2)
   - Remove/defer `_start_state_manager()` method

3. **Tests:**
   - `tests/unit/test_state_manager.py` — unit tests for ICoreManager surface
   - `tests/integration/test_state_manager_phase.py` — Phase 2 lifecycle integration
   - `tests/unit/test_task10_critical_acceptance.py` — acceptance gate

4. **Quality gates:**
   - All 3 new test files pass
   - `pytest tests/integration/test_integration.py` — no regressions
   - `pytest tests/unit/test_lifecycle_manager.py` — no regressions
   - No new EventType members in `types.py`
   - `lifecycle_manager.py` unmodified
