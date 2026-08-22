# Task 13 Architecture Review — Terminal 2 Handoff

## Terminal 1 Handoff (Architecture / Implementation Planning)

**Assignment**: Terminal 1 — ARCHITECTURE/IMPLEMENTATION PLANNING ONLY.
**Task**: Upgrade `ResourceManager` to a Phase-3 (Governance) Core Manager.
**Spec Reference**: Part 4 §4.9 (ResourceManager), Part 4 §4.2.3 (Phase topology), Part 4 §4.2.5 (Dependency matrix)

---

## Section 1: Executive Summary

**Task**: Upgrade `ResourceManager` (`src/aios/core/resource_manager.py`) from a plain class to a Phase-3 (Governance) Core Manager implementing the `ICoreManager` Protocol, orchestrated by `LifecycleManager`.

**Scope**: ResourceManager is the 4th Core Manager in the deterministic implementation sequence (Tasks 9→12: LifecycleManager→StateManager→StorageManager→HealthManager). It is already declared in the Phase 3 topology but is NOT yet registered with LifecycleManager and does NOT implement `ICoreManager`.

**Verdict**: **READY FOR TERMINAL 2 IMPLEMENTATION** — with 1 conditional decision documented in §5.3.

**Readiness Score**: **92/100**

**Score Breakdown**:
- Architectural clarity: 10/10 — all conflicts pre-resolved using Task 9-12 precedent
- Specification fidelity: 9/10 — Part 4 §4.9 requirements fully mapped
- Implementation guidance: 9/10 — HealthManager (Task 12) provides exact template
- Risk mitigation: 9/10 — 5 conflicts identified and resolved; 1 conditional decision
- Test strategy: 8/10 — 30-35 test targets defined; exact count TBD by Terminal 2

**Deductions**: The EventType mapping decision (§5.3) requires a deliberate choice on whether to emit `QUOTA_EXCEEDED` for pressure signals or omit entirely. This does not block but affects final test count.

---

## Section 2: Task Scope Determination

Task 13 is not explicitly named in any task file or commit message. It is inferred from the Core Manager implementation sequence established by Tasks 9-12:

| Task | Manager | Part 4 § | Phase | Implementation Status |
|------|---------|----------|-------|----------------------|
| 9  | LifecycleManager  | §4.3  | 1 (Foundation) | ✓ Complete |
| 10 | StateManager      | §4.4  | 2 (State & Storage) | ✓ Complete |
| 11 | StorageManager    | §4.5  | 2 (State & Storage) | ✓ Complete |
| 12 | HealthManager     | §4.10 | 3 (Governance) | ✓ Complete |
| 13 | **ResourceManager** | **§4.9** | **3 (Governance)** | **Pending** |

**Key observation**: The LifecycleManager phase topology (`lifecycle_manager.py:286-303`) **already declares** ResourceManager in Phase 3:
```python
CoreManagerPhase(3, "Governance", ("SecurityManager", "ResourceManager", "HealthManager"), (1, 2)),
```
This means LifecycleManager is **already prepared** to orchestrate ResourceManager. The gap is purely in `resource_manager.py` (no `ICoreManager` surface) and `kernel.py` (not registered with LifecycleManager).

---

## Section 3: Current State — ResourceManager (Pre-Task-13)

### 3.1 Existing Implementation

**File**: `src/aios/core/resource_manager.py` (438 lines)

| Aspect | Current | Target |
|---|---|---|
| Class type | Plain class | Core Manager implementing `ICoreManager` |
| Constructor | `__init__(config: dict \| None)` | DI pattern: `service_registry`, `configuration_manager`, `logger` (keyword-only) |
| Phase | N/A | Phase 3 (Governance) |
| ServiceRegistry | Not registered | Register as `core.resource` |
| ConfigurationManager | Not integrated | Read `kernel.resource.*` from frozen C3 |
| StructuredLogger | Uses stdlib `logging` | Use injected C4 `StructuredLogger` |
| EventBus | Does not emit events | Emit `RESOURCE_ALLOCATED`, `RESOURCE_RELEASED`, `RESOURCE_EXHAUSTED`, `QUOTA_EXCEEDED` |
| Lifecycle | Engineering service via kernel `_start_services()` | Driven by LifecycleManager Phase 3 |
| Singleton | Module-level, lock-free `get_resource_manager()` | Lock-guarded singleton (Task 9-12 pattern) |
| `health_ready()` | Missing | Return `self._initialized and self._event_bus is not None` |

### 3.2 How ResourceManager Is Currently Wired (kernel.py)

```python
# kernel.py:438 — construction (plain, no DI)
self._resource_manager = ResourceManager()
set_resource_manager(self._resource_manager)

# kernel.py:563 — engineering service startup (WRONG — bypasses LifecycleManager)
services = [
    ("workflow_manager", self._start_workflow_manager),
    ("resource_manager", self._start_resource_manager),  # <-- REMOVE
]

# kernel.py:695-699 — start/stop methods (will be orphaned)
async def _start_resource_manager(self):
    self._resource_manager.start_cleanup_task()
async def _stop_resource_manager(self):
    self._resource_manager.stop_cleanup_task()
```

**Not registered**: No `lm.register_manager(self._resource_manager)` call exists in `_init_lifecycle_manager()`.

---

## Section 4: Part 4 §4.9 Specification — Requirements Mapping

### 4.1 Identity and Phase
| Spec (§4.9) | Implementation |
|---|---|
| ServiceRegistry identity: `kernel.resource` | **CONFLICT E.1** → `core.resource` |
| Phase 3 (Governance) | `_PHASE = 3` |
| Dependencies: LifecycleManager ✓, SecurityManager ✓ (§4.2.5) | `("LifecycleManager",)` only — same-phase siblings NOT formal deps (Phase Dependency Rule) |
| `kernel.resource.*` config namespace | Read from frozen C3 via `configuration_manager.get()` |

### 4.2 Responsibilities Coverage (§4.9.2)

| # | Responsibility | Current Coverage | Action Needed |
|---|---|---|---|
| 1 | Resource Accounting | ✓ `_allocations` dict tracks allocations | Add EventBus events |
| 2-7 | CPU/Memory/Disk/Network/GPU/LLM accounting | ⚠ Partial (no GPU, no network as separate types; LLM quota not separate) | Preserve existing types; config-driven |
| 8 | Reservations | ⚠ `allocate()` is not called "reserve()" | Keep `allocate()` signature; document as reservation |
| 9 | Limits | ✓ `set_limit()`, `ResourceLimit` | Add config-driven limits |
| 10 | Backpressure | ⚠ Threshold checks exist but no EventBus signals | Add `QUOTA_EXCEEDED` emission |

### 4.3 Interaction Contracts (§4.9.8)

| Contract Partner | Direction | Current | Required |
|---|---|---|---|
| EventBus | Bidirectional | ❌ None | Emit `RESOURCE_ALLOCATED`/`RESOURCE_RELEASED`/`RESOURCE_EXHAUSTED`; consume requests |
| ServiceRegistry (C2) | Outbound | ❌ Not registered | Register as `core.resource` |
| ConfigurationManager (C3) | Inbound | ❌ Hardcoded defaults | Read `kernel.resource.*` |
| WorkflowManager | Inbound | ❌ N/A | `resource.reserve()`, `resource.release()` (existing API preserved) |
| CapabilityManager | Inbound | ❌ N/A | `resource.checkAvailability(profile)` (future — Phase 4) |
| SecurityManager | Outbound | ❌ N/A | `security.authorize(principal, resource.reserve)` (future — Phase 3) |
| HealthManager | Outbound | ❌ N/A | Report resource health (future — Phase 3) |
| ObservabilityManager | Outbound | ❌ N/A | Emit resource metrics (future — Phase 5) |

### 4.4 Invariants (§4.9.11)

| Invariant | Testable Criterion | Implementation |
|---|---|---|
| No over-allocation | Sum of reservations ≤ global capacity | Existing `_can_allocate()` check — **preserve** |
| Attribution completeness | Every allocated unit has a principal | `ResourceAllocation.requestor` field — **preserve** |
| Atomic reservations | Zero partial reservations under concurrent load | `self._lock` (asyncio.Lock) — **preserve** |
| Limit enforcement | No reservation exceeds declared limit | Existing `_can_allocate()` — **preserve** |
| Backpressure signaling | ResourcePressureEvent within 100ms | **NEW** — emit `QUOTA_EXCEEDED` on threshold crossing |

---

## Section 5: Architectural Conflicts and Resolutions

### 5.1 CONFLICT E.1 — ServiceRegistry Namespace

| Field | Value |
|---|---|
| **Source** | Part 4 §4.9.8: names SR identity as `kernel.resource` |
| **Constraint** | Part 3 §3.4.8 / INV-SR-NS-002: `kernel.*` namespace reserved; `_validate_namespace()` (service_registry.py:899-916) blanket-rejects |
| **Resolution** | Register as `core.resource` with metadata `{"kind": "core_manager", "manager": "ResourceManager", "phase": 3}` |
| **Precedent** | Task 9: `core.lifecycle`; Task 10: `core.state`; Task 11: `core.storage`; Task 12: `core.health` |
| **Verification** | `service_registry.py` is **FORBIDDEN** — `core.*` requires NO carve-out; no validator exception needed |

### 5.2 CONFLICT E.2 — Phase Ordering vs. Spec Section

| Field | Value |
|---|---|
| **Source** | Part 4 §4.2.3 lists Phase 3 as SecurityManager, ResourceManager, HealthManager; §4.2.4 shutdown is reverse |
| **Constraint** | Same-phase siblings cannot be formal dependencies |
| **Resolution** | HealthManager docstring already states ordering is alphabetical: HealthManager, ResourceManager, SecurityManager. Verified: `lifecycle_manager.py:862-865` (`_resolve_phase_managers`) **sorts alphabetically by name at runtime**, so tuple declaration order is irrelevant. No change needed to topology or dependencies. |
| **Precedent** | Task 12 HealthManager: `dependencies = ["LifecycleManager"]`, same-phase siblings are event-driven |

### 5.3 CONFLICT E.3 — EventType Invention (⚠️ CONDITIONAL DECISION)

| Field | Value |
|---|---|
| **Source** | Part 4 §4.9.8 names 10 event types: `ResourceReservedEvent`, `ResourceReleasedEvent`, `ResourcePressureEvent`, `ResourceExhaustedEvent`, `ResourceCriticalEvent`, `ResourceOOMIminentEvent`, `ResourceUsageReportEvent`, `ResourceReserveRequestEvent`, `ResourceReleaseRequestEvent`, `ResourceLimitChangeEvent` |
| **Constraint** | `EventType` enum is **closed** (Part 2 §2.3.1, Task 2); `service_registry.py` and `types.py` are immutable |
| **Available canonical EventTypes**: | `RESOURCE_ALLOCATED`, `RESOURCE_RELEASED`, `RESOURCE_EXHAUSTED`, `QUOTA_EXCEEDED`, `SERVICE_DEGRADED` |
| **Resolution A (recommended)**: | Map: `ResourceReservedEvent`→`RESOURCE_ALLOCATED`, `ResourceReleasedEvent`→`RESOURCE_RELEASED`, `ResourceExhaustedEvent`→`RESOURCE_EXHAUSTED`, `ResourcePressureEvent`→`QUOTA_EXCEEDED`. Omit all others (ResourceCriticalEvent, ResourceOOMIminentEvent, ResourceUsageReportEvent, etc.) — they have no canonical equivalent. |
| **Resolution B (conservative)**: | Only emit `RESOURCE_ALLOCATED` and `RESOURCE_RELEASED`. Omit `RESOURCE_EXHAUSTED` and `QUOTA_EXCEEDED` as well, since Part 4 uses different semantics. |
| **Decision**: | **Resolution A** — emit all 4 mapped canonical events. The event names are semantically equivalent (allocation/release/exhaustion/pressure). Omission of unmapped events follows the exact Task 12 HealthManager precedent (§4.6.10 has ~13 named events; only 3 canonical equivalents emitted; rest omitted). |

### 5.4 CONFLICT E.4 — Constructor Signature

| Field | Value |
|---|---|
| **Source** | Existing `ResourceManager.__init__(self, config: dict \| None = None)` vs. DI pattern `__init__(self, *, service_registry, configuration_manager, logger)` |
| **Constraint** | Kernel constructs as `ResourceManager()` (no DI args); `__init__.py` exports `get_resource_manager(config)` |
| **Resolution** | Accept `config=None` as optional backward-compat param with deprecation warning. New C2/C3/C4 params keyword-only, defaulting to None. If `config` is passed, log deprecation and use it to populate defaults (same path as `_init_default_limits`). |
| **Precedent** | HealthManager accepts all DI params as keyword-only; no backward-compat `config` param needed (was new code). ResourceManager needs the compat shim. |

### 5.5 CONFLICT E.5 — Singleton Pattern

| Field | Value |
|---|---|
| **Source** | Existing `get_resource_manager()` is lock-free module-level singleton |
| **Constraint** | Task 9-12 pattern uses `threading.Lock` guard; `__init__.py` has `reset_*_singleton` for tests |
| **Resolution** | Replace with lock-guarded singleton matching HealthManager pattern. Add `reset_resource_manager_singleton()` to `__all__`. |

---

## Section 6: Implementation Plan — File-by-File

### 6.1 `src/aios/core/resource_manager.py` (Primary Rewrite)

**Add to module header (after line 5, matching health_manager.py docstring pattern)**:
```python
"""
ResourceManager — the Phase-3 (Governance) Core Manager for AI-OS Hermes Kernel.

ResourceManager is the sole accounting and enforcement authority for all
computational resources... [mirror health_manager.py docstring structure]

CONFLICT E.1: Part 4 §4.9.8 names ServiceRegistry identity as `kernel.resource`,
but Part 3 §3.4.8 / INV-SR-NS-002 reserve `kernel.*`. Resolution: register as
`core.resource` (same precedent as core.lifecycle/core.state/core.storage/core.health).

CONFLICT E.3: Part 4 §4.9.8 names 10 event types not in closed EventType enum.
Canonical mappings: RESOURCE_ALLOCATED, RESOURCE_RELEASED, RESOURCE_EXHAUSTED,
QUOTA_EXCEEDED. All others omitted.
"""
```

**Replace class body with**:
1. Module-level constants (`_NAME`, `_MANAGER_ID = "core.resource"`, `_PHASE = 3`, `_COMPONENT_DEPENDENCIES`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`)
2. Canonical event type references (`_RESOURCE_ALLOCATED = EventType.RESOURCE_ALLOCATED`, etc.)
3. `__init__(self, *, service_registry=None, configuration_manager=None, logger=None, config=None)` — DI + backward-compat config param
4. ICoreManager properties: `name`, `phase`, `dependencies`, `manager_id`, `is_initialized`, `health_ready()`
5. `async initialize()` — read `kernel.resource.*` config, ensure cleanup task started, register with SR, mark initialized
6. `async shutdown()` — stop cleanup task, deregister from SR, mark uninitialized
7. `async register_with_service_registry()` / `async _deregister_from_service_registry()` — mirror HealthManager pattern
8. `_log_debug()` / `_log_info()` / `_log_warning()` / `_log_error()` — StructuredLogger bridge (null-safe)
9. `_emit_resource_event(event_type, allocation)` — sync-to-async bridge (mirror `_emit_health_event`)
10. Preserve all existing business methods: `set_limit`, `get_limit`, `allocate`, `release`, `get_usage`, `release_all_for_requestor`, `get_stats`, `add_allocation`, `start_cleanup_task`, `stop_cleanup_task`, `_cleanup_expired`
11. Replace singleton pattern with lock-guarded version; add `reset_resource_manager_singleton()`

### 6.2 `src/aios/core/kernel.py` (3 edits)

**Edit A** — `_init_core_components()` (line 438):
```python
# BEFORE:
self._resource_manager = ResourceManager()
set_resource_manager(self._resource_manager)

# AFTER:
self._resource_manager = ResourceManager(
    service_registry=self._service_registry,
    configuration_manager=self._configuration,
    logger=self._structured_logger,
)
set_resource_manager(self._resource_manager)
```

**Edit B** — `_init_lifecycle_manager()` (after HealthManager registration block, ~line 542):
```python
if self._resource_manager is not None:
    lm.register_manager(self._resource_manager)
    logger.debug("Registered ResourceManager with LifecycleManager (Phase 3).")
```

**Edit C** — `_start_services()` (line 561-564):
```python
# REMOVE resource_manager from services list:
services = [
    ("workflow_manager", self._start_workflow_manager),
    # ("resource_manager", self._start_resource_manager),  # <-- REMOVED
]
```
Also remove `_start_resource_manager()` / `_stop_resource_manager()` methods (or keep `_stop_resource_manager` as no-op if `get_stats()` still references it).

**Edit D** — `get_stats()` (line 741): Remove or update resource_manager service status reference.

### 6.3 `src/aios/core/__init__.py` (1 edit)

Add `reset_resource_manager_singleton` to imports and `__all__` list (after HealthManager block, line 337).

---

## Section 7: Forbidden Files

| File | Reason |
|---|---|
| `src/aios/core/service_registry.py` | Namespace validation must not change; `core.resource` requires no carve-out |
| `src/aios/events/core/types.py` | Closed EventType enum; no new members (CONFLICT E.3) |
| `src/aios/core/lifecycle_manager.py` | Phase topology and dependency validation must not change; ResourceManager already declared in Phase 3 tuple |

---

## Section 8: Acceptance Criteria

| # | Criterion | Test Evidence |
|---|---|---|
| AC-1 | ResourceManager implements all ICoreManager properties (name="ResourceManager", phase=3, dependencies=["LifecycleManager"], manager_id="core.resource") | Unit test: property assertions |
| AC-2 | `initialize()` reads `kernel.resource.*` config from frozen C3 and registers with SR as `core.resource` with `kind: core_manager` metadata | Unit test: config reading + SR registration mock |
| AC-3 | `shutdown()` is idempotent, stops cleanup task, deregisters from SR, sets `_initialized = False` | Unit test: double-shutdown no-op |
| AC-4 | `health_ready()` returns False before `initialize()`, True after, False after `shutdown()` | Unit test: state transitions |
| AC-5 | ResourceManager is registered with LifecycleManager in kernel.py `_init_lifecycle_manager()` | Integration test: `lm.register_manager` called |
| AC-6 | ResourceManager is NOT in kernel.py `_start_services()` engineering-services list | Code review: absent from list |
| AC-7 | `get_resource_manager()` uses lock-guarded singleton with `reset_resource_manager_singleton()` | Unit test: concurrent access + reset |
| AC-8 | `RESOURCE_ALLOCATED` event emitted on successful `allocate()` | Unit test: event payload |
| AC-9 | `RESOURCE_RELEASED` event emitted on successful `release()` | Unit test: event payload |
| AC-10 | `RESOURCE_EXHAUSTED` event emitted on allocation failure (timeout) | Unit test: event on ResourceExhausted |
| AC-11 | `QUOTA_EXCEEDED` event emitted on threshold crossing (80% warning) | Unit test: event on threshold |
| AC-12 | No new EventType members invented | Code review: grep EventType enum unchanged |
| AC-13 | No modifications to service_registry.py namespace validation | Git diff: file untouched |
| AC-14 | Backward-compatible `allocate()` / `release()` / `get_usage()` / `get_stats()` API preserved | Unit test: existing functionality |
| AC-15 | `kernel.resource.*` config values drive `ResourceLimit` defaults (replacing hardcoded) | Unit test: config override |

---

## Section 9: Test Strategy

**Target**: 30-35 tests (matching Task 12 HealthManager scope)

| Category | Test Count | Strategy | Reference File |
|---|---|---|---|
| ICoreManager Protocol | 6 | Assert all 6 Protocol members | Task 9/12 tests |
| initialize() / shutdown() | 5 | Idempotence, config, SR reg, cleanup task | health_manager tests |
| Singleton pattern | 3 | Concurrent access, get/set/reset | Task 10/11 tests |
| ServiceRegistry | 2 | `core.resource` id, `core_manager` metadata | Task 10/11 tests |
| Event emission | 4 | 4 canonical events via sync-to-async bridge | Task 12 tests |
| Configuration | 3 | `kernel.resource.*` reading, default fallback | Task 12 tests |
| Business methods (preserved) | 10-12 | allocate/release/get_usage/get_stats/set_limit | Existing tests if present |
| Error handling | 2-3 | ResourceExhausted, no-bus scenario | Task 12 pattern |

**Test file location**: `tests/core/test_resource_manager.py` (if exists, extend; else create following Task 12's `test_health_manager.py` structure).

**Pattern reference**: `src/aios/core/health_manager.py` is the **golden template** — Mirror its:
- Module docstring structure (with CONFLICT E.1/E.3 notes)
- Constants section (`_NAME`, `_MANAGER_ID`, `_PHASE`, `_VERSION`)
- DI constructor with C1 eager resolution + RuntimeError guard
- `_read_config_int` / `_read_config_str` / `_read_config_bool` helpers
- `_log_debug` / `_log_info` / `_log_warning` / `_log_error` bridge methods
- Sync-to-async event emission (`_emit_*_event` with `asyncio.ensure_future` + `_pending_tasks`)
- Lock-guarded singleton (`_global_*`, `_*_singleton_lock`, `reset_*` function)

---

## Section 10: Implementation Order (Terminal 2)

1. **Rewrite `resource_manager.py`** — Full class rewrite following §6.1. This is the largest change.
2. **Edit `__init__.py`** — Add `reset_resource_manager_singleton` export.
3. **Edit `kernel.py`** — 4 edits (construction, registration, remove from services, get_stats).
4. **Run tests** — `pytest tests/core/test_resource_manager.py` — expect 30-35 passing.
5. **Run full suite** — `pytest tests/` — ensure zero regressions in kernel/lifecycle tests.
6. **Verify FORBIDDEN files untouched** — `git diff --name-only` must exclude service_registry.py, types.py, lifecycle_manager.py.

**Critical sequencing**: Steps 1-3 must complete together — ResourceManager cannot be registered with LifecycleManager until it implements `ICoreManager` (AC-1), and kernel.py changes are meaningless without the class rewrite.

---

## Section 11: Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| `allocate()` is async but `release()` is sync — sync-to-async bridge for events | Medium | Use exact HealthManager `_emit_*_event` bridge pattern; never hand un-awaited coroutine to GC (FIX-FIND-01) |
| Backward compat: existing `ResourceManager(config={...})` callers | Low | `config` param accepted with deprecation warning; defaults preserved |
| Phase 3 ordering: SecurityManager not yet implemented (Task 13 only does ResourceManager) | Low | LifecycleManager only orchestrates **registered** managers; unregistered ones are skipped (`_resolve_phase_managers` filters `self._managers`) |
| Existing tests for ResourceManager may break on constructor change | Medium | Run full test suite; update tests to use new DI signature |
| `get_stats()` in kernel.py references resource_manager in service status | Low | Remove or update the reference in Edit D |

**No HIGH severity risks** — all patterns are established by Tasks 9-12; ResourceManager is a straightforward application of the same template.

---

## Section 12: Readiness Determination

**✅ READY FOR TERMINAL 2 IMPLEMENTATION**

All architectural conflicts are pre-resolved using established precedent. The HealthManager (Task 12) implementation serves as a complete reference template. The LifecycleManager phase topology already declares ResourceManager in Phase 3. The `ICoreManager` Protocol is stable and minimal (Task 9). No new EventTypes need invention. No forbidden file modifications are required.

**Score**: 92/100

**Conditions**: Terminal 2 must make the CONFLICT E.3 decision documented in §5.3 (use Resolution A: emit 4 canonical events, omit unmapped). This is a recommendation, not a blocker.

---

## Section 13: Appendix — Reference: HealthManager Implementation (Task 12 Template)

The following patterns from `src/aios/core/health_manager.py` MUST be mirrored in ResourceManager:

**Module docstring** (lines 1-68): Full CONFLICT E.1/E.3 documentation, Phase Dependency Rule note, component identity explanation.

**Constants block** (lines 109-142):
```python
_NAME = "HealthManager"  # → "ResourceManager"
_MANAGER_ID = "core.health"  # → "core.resource"
_PHASE = 3  # → same
_COMPONENT_DEPENDENCIES = ("EventBus", "ServiceRegistry", "ConfigurationManager", "StructuredLogger")
_MANAGER_DEPENDENCIES = ("LifecycleManager",)
```

**Constructor** (lines 253-312): DI for C2/C3/C4, eager C1 resolution with RuntimeError guard, `_pending_tasks` set, ComponentIdentity, lifecycle state flags.

**ICoreManager surface** (lines 318-358): `name`, `phase`, `dependencies`, `manager_id`, `is_initialized`, `overall_status`, `health_ready()`.

**Config helpers** (lines 364-397): `_read_config_str`, `_read_config_int`, `_read_config_bool` — all null-safe.

**initialize()** (lines 399-440): Read config, register with SR, mark initialized. Idempotent.

**shutdown()** (lines 442-463): Clear state, deregister from SR, mark uninitialized. Idempotent.

**SR integration** (lines 469-511): `register_with_service_registry()` with `core_manager` metadata envelope; `_deregister_from_service_registry()` via `mark_service_shutdown`.

**Logger bridge** (lines 780-794): `_log_debug`/`_log_info`/`_log_warning`/`_log_error` — all null-safe (check `self._logger is not None`).

**Event emission** (lines 708-774): `_emit_*_event` with `get_running_loop()` guard, `asyncio.ensure_future` on running loop, strong reference in `_pending_tasks`, `add_done_callback` discard.

**Singleton** (lines 801-835): Lock-guarded `_global_*_manager`, `_*_singleton_lock`, `get_*`/`set_*`/`reset_*_singleton`.
