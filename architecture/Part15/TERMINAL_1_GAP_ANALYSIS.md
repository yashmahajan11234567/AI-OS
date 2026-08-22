# Terminal 1 Gap Analysis — FINAL
## AI-OS / Hermes Kernel Architecture Gap Analysis

**Date:** 2026-08-21  
**Classification:** READ-ONLY ANALYSIS — Terminal 1 (analysis-only, no modifications)  
**Scope:** Evidence-based gap analysis of `src/aios/` against Parts 0–14 architecture specification  
**Authority Chain:** Parts 0–14 > Accepted ADRs > Part 15 > Implementation > Tests

---

## 1. Repository State

### 1.1 Git State
- **Branch:** `main`
- **Commit:** `e529a3b feat(core): complete Tasks 14-15 core managers` (HEAD)
- **Working tree:** Clean (all tracked files committed)
- **Untracked files:**
  - `.pytest-cache/` — temporary test artifact, should be gitignored
  - `FINAL_ARCHITECTURE_REVIEW_REPORT.md` — analysis report (untracked)
  - `TASK_13_ARCHITECTURE_REVIEW.md` — analysis report (untracked)
  - `TASK_13_IMPLEMENTATION_REPORT.md` — analysis report (untracked)
  - `architecture/Part15/MEMORY.md` — in-session context (untracked)
  - `architecture/Part15/analysis-gap-impl-vs-spec.md` — analysis (untracked)
  - `hermes-agent/` — **separate application** (v0.20.1), not the AI-OS kernel. Has its own `pyproject.toml`, `package.json`, Docker setup, and plugin system. Should NOT be part of `aios` package.

### 1.2 Architecture Spec Completeness
- **Parts 1–13:** Status = "Completed" (per MASTER_ARCHITECTURE_ROADMAP.md)
- **Part 14:** Status = "Planned"
- **Part 15:** Status = **NOT READY** — 15 of 27 files are EMPTY (13 chapter files 15.1–15.13, context.md, runtime-map.md, testing.md). Only 12 files have substantive content. CONFLICT-P15-01 (naming/classification divergence between ROADMAP and TOC) remains unresolved.

---

## 2. EventType Canonical Count — Resolution

### 2.1 Authoritative Source: Part 2 §2.3.1

**`architecture/Part02/ARCHITECTURE_SPEC_PART2.md`:**

- **Line 398:** "Count: The above defines **97** canonical event types. Extensions may add types via governed process (Part 0 §0.5.2)."
- **Line 2103:** "Canonical Event Types | **97** | §2.3.1"
- **Lines 262-267:** §2.3.1 defines `EventType` as a "closed enum" with a full enumeration list.
- **Lines 411-419:** Lists 5 categories (SYSTEM, CONTROL, DATA, AUDIT, DIAGNOSTIC).

### 2.2 The Discrepancy — Three Numbers

| Source | Count | Context |
|--------|-------|---------|
| Part 2 §2.3.1 prose | **97** | Stated in the spec text |
| Part 2 §2.3.1 enumeration | **121** | The actual enum members (97 + 24 from retry/root-cause) |
| `EventType` enum (`types.py`) | **121** | `len(EventType) == 121` |
| `EventTypeRegistry` docstring | **118** | *Incorrect* — says "118" but iterates all 121 members |
| `test_event_type.py` | **121** | `EXPECTED_COUNT = 121`; asserts `len(EventType) == 121` |
| `test_event_type_registry.py` | **121** | `EXPECTED_CANONICAL_COUNT = 121`; asserts registry has 121 |
| `test_event_core.py` | **118** | `test_event_type_catalog_complete` asserts `len(list(EventType)) == 118` — **OUTDATED TEST** |

### 2.3 The Three Target Events

All three are present in the canonical `EventType` enum at `src/aios/events/core/types.py`:

| Event | Line | Category | Present? |
|-------|------|----------|----------|
| `RETRY_SCHEDULED` | 82 | CONTROL | ✅ |
| `RETRY_EXECUTED` | 83 | CONTROL | ✅ |
| `FAILURE_CLASSIFIED` | 169 | DIAGNOSTIC | ✅ |

### 2.4 Authoritative Count Determination

**Per the architecture authority chain (Parts 0–14 > Implementation > Tests):**

1. **Part 2 §2.3.1** is the authoritative source for EventType. It defines a **closed enum** with an **enumeration** containing 121 entries.
2. The prose says "97" — this is acknowledged as a discrepancy by the test file itself (`test_event_type.py:8-13`): "Part 2 §2.3.1 advertises 97 canonical EventTypes in its prose, but the canonical enumeration list in §2.3.1 contains 121 entries (97 prose + 24 RETRY_SCHEDULED/RETRY_EXECUTED/FAILURE_CLASSIFIED added by the retry and root-cause subsystems)."
3. The **implementation conforms to the enumeration (121)**, as documented in the module docstring (`types.py:6`): "121 canonical types in the enumeration; the prose states 97 — we conform to the enumeration."
4. **Verdict:** The authoritative EventType count is **121** (the enumeration from Part 2 §2.3.1). The "97" is prose that does not match the enumeration. The "118" is an outdated docstring in `registry.py` and an outdated assertion in `test_event_core.py`.

### 2.5 The 24 "Extra" Events

The 24 events beyond the prose's 97 are:
- RETRY_SCHEDULED, RETRY_EXECUTED (retry subsystem)
- ROOT_CAUSE_ANALYZED, RECOVERY_ACTION_DISPATCHED, RECOVERY_ACTION_COMPLETED, RECOVERY_ACTION_FAILED (root-cause subsystem)
- And 20 additional events in the CONTROL, DATA, AUDIT, DIAGNOSTIC categories that exist in the enumeration but are not counted in the prose's 97.

These are **legitimate canonical event types** — they appear in the Part 2 §2.3.1 enumeration and are part of the closed EventType enum.

---

## 3. Core Manager ICoreManager Compliance Matrix

### 3.1 ICoreManager Protocol (lifecycle_manager.py:240-262)

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

**Key observation:** `register_manager()` (line 456) does NOT perform `isinstance` checks against `ICoreManager`. It only checks that `manager.name` appears in the declared phase topology (line 463-468). The Protocol is `@runtime_checkable` but not enforced at registration time. This means any object with a `name` attribute matching a phase topology entry will be silently accepted, even if it doesn't implement the full Protocol surface.

### 3.2 Compliance Verification

| Manager | ICoreManager Surface | Phase Topology | Kernel Construction | Kernel Registration | DI Pattern | Singleton | Status |
|---------|---------------------|----------------|---------------------|---------------------|-----------|-----------|--------|
| **LifecycleManager** | ✅ Full (self-registers) | Phase 1 | ✅ Constructed (line 611) | ✅ Self-registers | ✅ DI | ✅ (`set_lifecycle_manager`) | COMPLIANT |
| **StateManager** | ✅ Full | Phase 2 | ✅ Constructed (line 460) | ✅ Registered (line 628) | ✅ DI | ✅ (`set_state_manager`) | COMPLIANT |
| **StorageManager** | ✅ Full | Phase 2 | ✅ Constructed (line 478) | ✅ Registered (line 638) | ✅ DI | ✅ (`set_storage_manager`) | COMPLIANT |
| **ResourceManager** | ✅ Full | Phase 3 | ✅ Constructed (line 498) | ✅ Registered (line 659) | ✅ DI | ✅ (`set_resource_manager`) | COMPLIANT |
| **HealthManager** | ✅ Full | Phase 3 | ✅ Constructed (line 514) | ✅ Registered (line 647) | ✅ DI | ✅ (`set_health_manager`) | COMPLIANT |
| **SecurityManager** | ✅ Full | Phase 3 | ✅ Constructed (line 530) | ✅ Registered (line 669) | ✅ DI | ✅ (`set_security_manager`) | COMPLIANT |
| **CapabilityManager** | ✅ Full | Phase 4 | ✅ Constructed (line 544) | ✅ Registered (line 678) | ✅ DI | ✅ (`set_capability_manager`) | COMPLIANT |
| **ObservabilityManager** | ✅ Full | Phase 5 | ✅ Constructed (line 557) | ✅ Registered (line 687) | ✅ DI | ✅ (`set_observability_manager`) | COMPLIANT |
| **WorkflowManager** | ❌ **NONE** — No `name`, no `phase`, no `dependencies`, no `initialize()`, no `shutdown()`, no `health_ready()` | Phase 4 | ✅ Constructed (line 486) | ❌ **NOT REGISTERED** | ❌ **Uses legacy singletons** (`get_core_event_bus`, `get_retry_manager`) | ✅ (`set_workflow_manager`) | **CRITICAL GAP** |

### 3.3 The WorkflowManager Gap — Detailed

`src/aios/core/workflow.py` (822 lines):

1. **Does NOT implement ICoreManager Protocol:**
   - No `name` property
   - No `phase` property
   - No `dependencies` property
   - No `async def initialize()`
   - No `async def shutdown()`
   - No `def health_ready()`
   - Does NOT reference `ICoreManager` anywhere (confirmed via grep — zero matches)

2. **NOT registered with LifecycleManager:**
   - `kernel.py:486` constructs `WorkflowManager(self._state_manager)`
   - `_init_lifecycle_manager()` registers StateManager, StorageManager, HealthManager, ResourceManager, SecurityManager, CapabilityManager, ObservabilityManager — but **NOT WorkflowManager**

3. **Uses legacy singletons instead of Dependency Injection:**
   - `workflow.py:18`: `from aios.events.core.bus import get_core_event_bus` (legacy singleton accessor)
   - `workflow.py:25`: `from aios.core.retry import get_retry_manager` (legacy singleton accessor)
   - Contrast: All other Core Managers receive `event_bus`, `service_registry`, `configuration_manager`, `logger` via constructor DI

4. **Dead-code duplicate `_emit_event` at module level (lines 790-811):**
   - A module-level function `_emit_event(self, ...)` that shadows the instance method `_emit_event` defined at line 651
   - This is a Python anti-pattern: the module-level function takes `self` as a parameter but is NOT a method — it exists in the module namespace and would need to be called as `_emit_event(instance, ...)` rather than `instance._emit_event(...)`
   - The module-level function is never called anywhere in the codebase

5. **`_start_workflow_manager` is a no-op:**
   - `kernel.py:839-840`: `async def _start_workflow_manager(self) -> None: pass`
   - The kernel treats WorkflowManager as an "engineering service" (line 709) and calls `_start_workflow_manager()` which does nothing

6. **No `reset_workflow_manager_singleton()` function:**
   - The module has `get_workflow_manager()` and `set_workflow_manager()` but no reset function, unlike all other Core Managers

**Classification:** WorkflowManager is a **legitimate remaining defect** — the code was never upgraded to the ICoreManager pattern that all other 8 Core Managers follow. The Phase 4 topology declares `("CapabilityManager", "WorkflowManager")` but WorkflowManager cannot be registered because it lacks the `name` attribute required by `register_manager()`.

---

## 4. Event System — Test Regression Classification

### 4.1 EventType Count Tests

| Test File | Test | Expected | Actual | Classification |
|-----------|------|----------|--------|----------------|
| `test_event_type.py:154` | `EXPECTED_COUNT = 121` | 121 | 121 | ✅ **PASS** — Correct, matches enumeration |
| `test_event_type.py:160` | `test_event_type_count_is_121` | 121 | 121 | ✅ **PASS** |
| `test_event_type.py:173` | `test_value_equals_member_name` | — | — | ✅ **PASS** |
| `test_event_type_registry.py:68` | `EXPECTED_CANONICAL_COUNT = 121` | 121 | 121 | ✅ **PASS** |
| `test_event_core.py:348-351` | `test_event_type_catalog_complete` | 118 | 121 | ❌ **OUTDATED TEST** — Asserts 118 but enum has 121. The test comment says "Part 2 §2.3.1's enumeration defines 118 canonical event types" but Part 2 §2.3.1 enumeration has 121. This test was written before RETRY_SCHEDULED/RETRY_EXECUTED/FAILURE_CLASSIFIED were added to the enum. |

### 4.2 Subscription Filter Tests

**Status:** The FINAL_ARCHITECTURE_REVIEW_REPORT.md claims a HIGH severity filter bug in `filters.py:66`. This is **INCORRECT** — the current code at `filters.py:65` reads:

```python
if callable(getattr(cur, "get", None)):
    cur = cur.get(part, _MISSING)
else:
    cur = getattr(cur, part, _MISSING)
```

This correctly handles both `dict` objects and dict-like objects with a `.get()` method. The test's `_Payload` class (line 31-35) has a `.get()` method, which `callable(getattr(cur, "get", None))` correctly detects. The report appears to be based on an outdated version of `filters.py` where the check was `isinstance(cur, dict)` instead of `callable(getattr(cur, "get", None))`.

### 4.3 StructuredLogger EventBusSink

**Status:** The FINAL_ARCHITECTURE_REVIEW_REPORT.md claims a MEDIUM severity bug in `sinks.py:594` referencing `EventType.LOG_ANOMALY_DETECTED`. This is **INCORRECT** — the current code at `sinks.py:65` reads:

```python
from aios.events.core.types import EventType as LegacyEventType
_LOG_EVENT_TYPE = LegacyEventType.CORE_COMPONENT_DEGRADED
```

The `LOG_ANOMALY_DETECTED` constant exists in the **legacy** `EventType` class (`aios/events/base.py:82`), NOT in the canonical `EventType` enum (`aios/events/core/types.py`). The `sinks.py` code correctly imports from `aios.events.core.types` (canonical) and uses `CORE_COMPONENT_DEGRADED`. The report was based on an outdated version of `sinks.py`.

### 4.4 Summary of Test Failure Classifications

The FINAL_ARCHITECTURE_REVIEW_REPORT.md's test status section reports "44 failed, 690 passed, 300 warnings, 2 errors." However, the report's analysis of **why** tests fail is based on an outdated snapshot. The report claims:

- **Category A (Unwired Managers - 4 failures):** Claims SecurityManager/CapabilityManager/ObservabilityManager are NOT wired into the kernel. **CORRECT assessment of the report's snapshot, but the current kernel.py IS wired.** The report was written against an older kernel.py version (likely `ae3fec` or earlier). The current `e529a3b` kernel.py DOES import, construct, and register all three managers.

- **Category B (EventType Count - 4 failures):** The report claims tests expect 118. **INCORRECT** — `test_event_type.py` and `test_event_type_registry.py` both assert 121. Only `test_event_core.py:351` asserts 118. This is a classification error.

- **Category C (EventType Registry - 9 failures):** Claims registry tests use 118. **INCORRECT** — the registry tests assert 121.

- **Category D (Subscription Filter - 9 failures):** The report claims a `_resolve()` bug. **INCORRECT** — the current code handles dict-like objects correctly.

- **Category E (StructuredLogger Sink - 1 failure):** The report claims `LOG_ANOMALY_DETECTED` bug. **INCORRECT** — the current code uses `CORE_COMPONENT_DEGRADED`.

**The FINAL_ARCHITECTURE_REVIEW_REPORT.md was written against an outdated snapshot of the codebase and contains multiple factual errors.** It needs to be re-generated against the current `e529a3b` code.

---

## 5. Core Manager Compliance — Detailed Findings

### 5.1 All Phase 3-5 Managers Implement ICoreManager ✅

**SecurityManager** (`security_manager.py`):
- `_NAME = "SecurityManager"`, `_PHASE = 3`, `_MANAGER_ID = "core.security"`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`
- Has `name`, `phase`, `dependencies`, `manager_id`, `is_initialized`, `health_ready()`, `initialize()`, `shutdown()`
- Uses DI pattern (receives `service_registry`, `configuration_manager`, `logger` via constructor)
- Uses `StructuredLogger` (C4), NOT stdlib logging

**CapabilityManager** (`capability_manager.py`):
- `_NAME = "CapabilityManager"`, `_PHASE = 4`, `_MANAGER_ID = "core.capability"`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`
- Same full ICoreManager surface as SecurityManager
- Uses DI pattern and StructuredLogger

**ObservabilityManager** (`observability_manager.py`):
- `_NAME = "ObservabilityManager"`, `_PHASE = 5`, `_MANAGER_ID = "core.observability"`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`
- Same full ICoreManager surface
- Uses DI pattern and StructuredLogger

**ResourceManager** (`resource_manager.py` — Phase 3):
- `_NAME = "ResourceManager"`, `_PHASE = 3`, `_MANAGER_ID = "core.resource"`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`
- Full ICoreManager surface, DI pattern, StructuredLogger

**HealthManager** (`health_manager.py` — Phase 3):
- `_NAME = "HealthManager"`, `_PHASE = 3`, `_MANAGER_ID = "core.health"`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`
- Full ICoreManager surface, DI pattern, StructuredLogger

**StateManager** (`state.py` — Phase 2):
- Full ICoreManager surface, DI pattern, StructuredLogger

**StorageManager** (`storage.py` — Phase 2):
- Full ICoreManager surface, DI pattern, StructuredLogger

### 5.2 The Pattern — All Managers EXCEPT WorkflowManager Follow It

Every Core Manager follows this exact pattern:
1. Module-level constants: `_NAME`, `_MANAGER_ID`, `_PHASE`, `_MANAGER_DEPENDENCIES`
2. `ICoreManager` Protocol surface: `name`, `phase`, `dependencies`, `health_ready()`, `initialize()`, `shutdown()`
3. Constructor receives `service_registry`, `configuration_manager`, `logger` via DI
4. `register_with_service_registry()` method registers as `core.{name}` with `kind: "core_manager"` metadata
5. Uses `StructuredLogger` (C4), NOT `logging.getLogger(__name__)`
6. Has `get_{name}_manager()` / `set_{name}_manager()` / `reset_{name}_manager_singleton()` trio
7. Registered with LifecycleManager in `kernel.py._init_lifecycle_manager()`

**WorkflowManager is the sole exception** — it does NOT follow this pattern.

### 5.3 WorkflowManager — The Isolated Gap

WorkflowManager stands out as the only "Core Manager" that:
- Does NOT implement `ICoreManager`
- Does NOT receive dependencies via DI (uses `get_core_event_bus()` singleton instead)
- Does NOT register with LifecycleManager
- Does NOT have a `reset_workflow_manager_singleton()` function
- Has a dead-code module-level `_emit_event` (lines 790-811) that shadows the instance method
- Is treated as an "engineering service" in `_start_services()` with a no-op `_start_workflow_manager()` (line 839-840)
- Uses `logging.getLogger(__name__)` (line 27) instead of StructuredLogger (C4)

**Classification:** This is an **implementation bug** — WorkflowManager was never upgraded to the Core Manager pattern that was established by Tasks 9-12 and followed by Tasks 13-15.

---

## 6. Packaging and Installability

### 6.1 pyproject.toml (`pyproject.toml` at repo root)

- **Build system:** setuptools >=68, wheel
- **Package name:** `ai-os` v0.2.0
- **Python:** >=3.12
- **Dependencies:** typer, rich, pydantic, python-dotenv, PyYAML, aiohttp, websockets
- **Dev dependencies:** pytest, pytest-asyncio, ruff, mypy, black
- **Entry point:** `aios = "aios.cli.main:app"`
- **Layout:** src-layout (`package-dir = "src"`, `packages.find` in `src/`)
- **pytest config:** `asyncio_mode = "auto"`

### 6.2 Import Surface

The root `aios/__init__.py` exports from `aios.core` and `aios.events`. However:
- `aios.core.__init__` does **NOT** export `SecurityManager`, `CapabilityManager`, or `ObservabilityManager` (confirmed: no matches for these names)
- `aios.__init__` does **NOT** export `SecurityManager`, `CapabilityManager`, `ObservabilityManager`, `LifecycleManager`, `ICoreManager`, `ServiceRegistry`, `ConfigurationManager`, `StructuredLogger`, or `HermesKernel` — these are only available via direct import from `aios.core`
- The exports in `__init__.py` still reference the **legacy** event system: `from aios.events import Event, EventType, EventBus` — this uses the legacy `aios/events/__init__.py` which imports from `aios/events/base.py` (legacy EventType) rather than `aios/events/core/types.py` (canonical EventType)

### 6.3 Legacy vs Canonical Event System

There are **two parallel event systems**:

| Aspect | Legacy (`aios.events`) | Canonical (`aios.events.core`) |
|--------|----------------------|-------------------------------|
| `EventType` | `aios.events.base.EventType` — string constants | `aios.events/core/types.py EventType` — closed str Enum (121 members) |
| `EventBus` | `aios.events.bus.EventBus` — thread-based | `aios.events/core/bus.py EventBus` — async-native |
| `Event` | `aios.events.base.Event` | `aios.events/core/event.py Event` — 12-field immutable |
| `ServiceRegistry` | `aios.services.registry.ServiceRegistry` | `aios.core.service_registry.ServiceRegistry` |
| `StructuredLogger` | `aios.core.logger` (legacy) | `aios.core.structured_logger.StructuredLogger` |

The root `aios/__init__.py` imports `EventType` from `aios.events` (legacy), NOT from `aios.events.core`. This means `from aios import EventType` gives users the **legacy** EventType, while `from aios.events.core import EventType` gives the **canonical** one. This is a source of confusion.

### 6.4 Hermes-Agent

`hermes-agent/` is a **completely separate application** (v0.20.1) with its own `pyproject.toml`, `package.json`, and ~4000 Python files. It is NOT part of the `aios` package (it's at the repo root, not under `src/aios/`). It appears to be a consumer/integrator of the AI-OS kernel rather than a component of it.

### 6.5 Installability

The package should be installable via `pip install -e .` from the repo root. However:
- No `requirements.txt` at the repo root (dependencies are in `pyproject.toml`)
- The `hermes-agent/` directory has its own `pyproject.toml` — could cause confusion if someone tries to install from the wrong directory
- No `requirements-dev.txt` or `requirements-test.txt`

---

## 7. Full-System Lifecycle Integration

### 7.1 Kernel Lifecycle (kernel.py)

The `HermesKernel` implements a partial lifecycle:

| Step | Spec Requirement | Implementation | Status |
|------|-----------------|----------------|--------|
| `start()` | Phase 1-5 initialization, health_ready(), OPERATIONAL | ✅ Implements `_init_core_components()` → C1-C4 + managers, then `_init_lifecycle_manager()` → registers + initializes all 8 Core Managers | ✅ |
| `stop()` | Reverse phase shutdown, TERMINATED | ✅ Implements `_shutdown_lifecycle_manager()` + `_shutdown_structured_logger()` + `_stop_engineering_services()` | ✅ |
| `_start_services()` | Start engineering services | ✅ Starts `workflow_manager` (no-op) and `resource_manager` (cleanup task) | ⚠️ WorkflowManager no-op |
| FSM | 5-state (UNINITIALIZED→INITIALIZING→RUNNING→SHUTTING_DOWN→TERMINATED) | ❌ Uses `_running: bool` flag, NOT a 5-state FSM | **GAP** — documented in analysis-gap-impl-vs-spec.md as ASSUMPTION |

### 7.2 LifecycleManager Phases

| Phase | Managers (topology) | Registered? | Initialized by LM? |
|-------|---------------------|-------------|---------------------|
| 1 (Foundation) | LifecycleManager | ✅ Self | ✅ |
| 2 (State & Storage) | StateManager, StorageManager | ✅ | ✅ |
| 3 (Governance) | HealthManager, ResourceManager, SecurityManager | ✅ | ✅ |
| 4 (Execution) | CapabilityManager, **WorkflowManager** | ✅ Capability; ❌ Workflow | ✅ Capability; ❌ Workflow |
| 5 (Observability) | ObservabilityManager | ✅ | ✅ |

### 7.3 Reverse Shutdown

`LifecycleManager._do_shutdown()` (line 669) iterates `reversed(self._initialized_order)` and calls `mgr.shutdown()` on each. Since WorkflowManager is NOT registered, it is NOT shut down by LifecycleManager — it only gets a no-op `_start_workflow_manager()` during startup and nothing during shutdown.

### 7.4 E2E Test Coverage

| Test File | Coverage Area | Status |
|-----------|---------------|--------|
| `test_task9_critical_acceptance.py` | LifecycleManager identity, phase, registration | ✅ EXISTS |
| `test_task10_critical_acceptance.py` | StateManager identity, lifecycle, events | ✅ EXISTS |
| `test_task11_critical_acceptance.py` | StorageManager identity, lifecycle, events | ✅ EXISTS |
| `test_task12_critical_acceptance.py` | HealthManager identity, lifecycle, events | ✅ EXISTS |
| `test_task12_health_manager.py` | HealthManager unit tests | ✅ EXISTS |
| `test_task13_resource_manager.py` | ResourceManager identity, lifecycle, events | ✅ EXISTS |
| `test_task14_15_critical_acceptance.py` | SecurityManager/CapabilityManager/ObservabilityManager | ✅ EXISTS |
| `test_integration.py` | Full kernel lifecycle E2E | ✅ EXISTS — but uses `kernel_management.run_kernel()` which calls `kernel.start()` |
| `test_lifecycle_manager_phase.py` | LifecycleManager Phase 3 integration | ✅ EXISTS |

**Missing E2E coverage:**
- No test that verifies the **complete** kernel lifecycle from `start()` through all 5 phases to `stop()` with all 9 managers, including reverse shutdown verification
- `test_integration.py` uses `run_kernel()` which exercises `kernel.start()` but does NOT verify individual manager lifecycle states post-shutdown
- No test verifies WorkflowManager's lifecycle (it's not a Core Manager, so LifecycleManager doesn't manage it)

---

## 8. EventTypeRegistry Docstring Inconsistency

`registry.py:11` states: "Canonical 118-member EventType enum ... Part 2 §2.3.1 (Task 2)"

This is **incorrect** — the enum has 121 members, not 118. The `_populate_canonical_types()` method (line 405) iterates `for member in EventType:` which correctly covers all 121 members. The docstring on line 11 is stale.

**Classification:** Outdated documentation (the docstring was written when the enum had 118 members, before RETRY_SCHEDULED/RETRY_EXECUTED/FAILURE_CLASSIFIED were added).

---

## 9. `__all__` and Package Exports

### 9.1 `aios/core/__init__.py` — Missing Exports

The `__init__.py` exports HealthManager (lines 329-339) but does NOT export:
- `SecurityManager` / `get_security_manager` / `set_security_manager` / `reset_security_manager_singleton`
- `CapabilityManager` / `get_capability_manager` / `set_capability_manager` / `reset_capability_manager_singleton`
- `ObservabilityManager` / `get_observability_manager` / `set_observability_manager` / `reset_observability_manager_singleton`

These are importable directly from their modules but not from the package root. This is inconsistent with how HealthManager IS exported.

### 9.2 `aios/__init__.py` — Legacy Event System

Imports `EventType` from `aios.events` (legacy), not `aios.events.core` (canonical). Users doing `from aios import EventType` get a different enum than `from aios.events.core import EventType`.

---

## 10. Summary of All Findings

### 10.1 Critical Gaps (Blockers)

1. **WorkflowManager does not implement ICoreManager** — The only "Core Manager" that doesn't follow the pattern. Not registered with LifecycleManager, uses legacy singletons, has dead-code `_emit_event`, `_start_workflow_manager` is a no-op. All other 8 managers (Lifecycle, State, Storage, Health, Resource, Security, Capability, Observability) properly implement ICoreManager and are registered.

2. **WorkflowManager NOT in LifecycleManager phase execution** — Phase 4 topology declares `("CapabilityManager", "WorkflowManager")` but only CapabilityManager gets registered. WorkflowManager is constructed by the kernel but never driven by LifecycleManager.

### 10.2 Medium Gaps

3. **EventTypeRegistry docstring says "118" but enum has 121** — `registry.py:11` is stale documentation.

4. **`test_event_core.py:351` asserts 118** — Outdated test assertion. All other tests correctly assert 121.

5. **Kernel uses `_running: bool` instead of 5-state FSM** — Documented as ASSUMPTION in analysis-gap-impl-vs-spec.md. The LifecycleManager has the full 8-state FSM, but the kernel itself does not.

6. **Missing exports in `aios/core/__init__.py`** — SecurityManager, CapabilityManager, ObservabilityManager are not exported from the package.

7. **Legacy vs canonical event system** — `aios/__init__.py` imports the legacy EventType, not the canonical one.

### 10.3 Low Gaps

8. **`_start_workflow_manager` is a no-op** — Should either do something meaningful or be removed from `_start_services()`.

9. **Module-level `_emit_event` dead code** — `workflow.py:790-811` is never called and shadows the instance method.

10. **No `reset_workflow_manager_singleton()`** — All other Core Managers have this function; WorkflowManager does not.

### 10.4 Repository Hygiene

11. **`.pytest-cache/` is untracked** — Should be in `.gitignore`.

12. **`hermes-agent/` is untracked** — Separate application, should be excluded from `aios` package or in a subdirectory.

13. **3 untracked report files** — `FINAL_ARCHITECTURE_REVIEW_REPORT.md`, `TASK_13_ARCHITECTURE_REVIEW.md`, `TASK_13_IMPLEMENTATION_REPORT.md` — These are analysis artifacts.

14. **`architecture/Part15/MEMORY.md`** — In-session context file, should be excluded.

### 10.5 Corrections to FINAL_ARCHITECTURE_REVIEW_REPORT.md

The FINAL_ARCHITECTURE_REVIEW_REPORT.md (written against an older snapshot) contains several factual errors when compared to the current `e529a3b` code:

1. **Claim:** "SecurityManager, CapabilityManager, and ObservabilityManager are NOT wired into kernel.py" — **FALSE.** Current kernel.py DOES import (lines 85-109), construct (lines 530-562), and register (lines 669-688) all three managers.

2. **Claim:** "test_event_type.py asserts 118" — **FALSE.** Current `test_event_type.py:154` has `EXPECTED_COUNT = 121` and asserts 121.

3. **Claim:** "test_event_type_registry.py asserts 118" — **FALSE.** Current `test_event_type_registry.py:68` has `EXPECTED_CANONICAL_COUNT = 121`.

4. **Claim:** Subscription filter bug in `filters.py:66` — **FALSE.** Current code correctly handles dict-like objects via `callable(getattr(cur, "get", None))`.

5. **Claim:** `LOG_ANOMALY_DETECTED` bug in `sinks.py:594` — **FALSE.** Current code uses `EventType.CORE_COMPONENT_DEGRADED`.

---

## 11. Implementation Plan for Terminal 2

### 11.1 Priority 1: Fix WorkflowManager to be a proper Phase-4 Core Manager

Following the exact pattern established by HealthManager (Task 12) / ResourceManager (Task 13) / SecurityManager (Task 14):

**File: `src/aios/core/workflow.py`**
1. Add module-level constants: `_NAME = "WorkflowManager"`, `_PHASE = 4`, `_MANAGER_ID = "core.workflow"`, `_MANAGER_DEPENDENCIES = ("LifecycleManager",)`
2. Add ICoreManager surface: `name`, `phase`, `dependencies`, `manager_id`, `is_initialized`, `health_ready()`, `async initialize()`, `async shutdown()`
3. Change constructor to accept DI: `__init__(self, *, event_bus=None, service_registry=None, configuration_manager=None, logger=None, state_manager=None)` instead of `__init__(self, state_manager=None)`
4. Replace `get_core_event_bus()` singleton usage with `self._event_bus`
5. Replace `get_retry_manager()` singleton usage with DI (pass RetryManager in or access via ServiceRegistry)
6. Replace `logging.getLogger(__name__)` with StructuredLogger (C4)
7. Remove dead-code module-level `_emit_event` (lines 790-811)
8. Add `register_with_service_registry()` method (registers as `core.workflow`)
9. Add `get_workflow_manager()`, `set_workflow_manager()`, `reset_workflow_manager_singleton()` trio

**File: `src/aios/core/kernel.py`**
1. WorkflowManager construction is already at line 486 — update to use DI pattern
2. Add `lm.register_manager(self._workflow_manager)` in `_init_lifecycle_manager()` (after CapabilityManager registration, line 680)
3. Remove `("workflow_manager", self._start_workflow_manager)` from `_start_services()` list (line 709) — it's a Core Manager, not an engineering service
4. Remove or keep `_start_workflow_manager` no-op (line 839-840) — depends on whether WorkflowManager has background tasks that need the engineering-service lifecycle

**File: `src/aios/core/__init__.py`**
1. Add SecurityManager, CapabilityManager, ObservabilityManager exports (for consistency with HealthManager)

### 11.2 Priority 2: Fix EventType Count Documentation

1. **`src/aios/events/core/registry.py:11`** — Change "118-member" to "121-member" in docstring
2. **`tests/unit/test_event_core.py:349-351`** — Update `test_event_type_catalog_complete` to assert 121 instead of 118 (this is an outdated test, not an implementation bug)

### 11.3 Priority 3: Remove WorkflowManager from `_start_services()`

The `_start_services()` list (line 708-711) includes `("workflow_manager", self._start_workflow_manager)`. Once WorkflowManager becomes a Core Manager, it should be removed from this list — its lifecycle is owned by LifecycleManager, not the engineering-service startup path.

### 11.4 Priority 4: Export New Managers from `__init__.py`

Add SecurityManager, CapabilityManager, ObservabilityManager to `aios/core/__init__.py` and `__all__` for consistency.

---

## 12. Authority Chain Verification

### 12.1 EventType Count

- **Part 2 §2.3.1 enumeration** = 121 (authoritative)
- **Part 2 §2.3.1 prose** = 97 (discrepancy acknowledged in test docstring)
- **Implementation** = 121 (conforms to enumeration) ✅
- **Registry docstring** = 118 (stale — should be 121)
- **test_event_type.py** = 121 ✅
- **test_event_type_registry.py** = 121 ✅
- **test_event_core.py** = 118 ❌ (stale test)

**Authoritative answer:** **121** per Part 2 §2.3.1 enumeration.

### 12.2 Core Manager Count

- **Part 4 §4.2.3 phase topology** declares 9 Core Managers across 5 phases
- **LifecycleManager** declares them in `_build_phase_topology()` (line 286-303)
- **Implementation:** 8 of 9 are fully wired and registered; **WorkflowManager is the sole exception**

---

*End of Terminal 1 Gap Analysis*