# Terminal 1 Audit Report — AI-OS Hermes Kernel

**Date:** 2026-08-22  
**Classification:** READ-ONLY ANALYSIS — Terminal 1 (no modifications made)  
**Scope:** Evidence-based complete repository audit of `src/aios/` against Parts 0–14 architecture specification  
**Authority Chain:** Parts 0–14 > Accepted ADRs > Part 15 > Implementation > Tests  
**Git HEAD:** `dc09784` — "Ignore external hermes-agent repository"  

---

## 1. Repository State Summary

### 1.1 Git State
| Field | Value |
|-------|-------|
| Branch | `main` |
| HEAD commit | `dc09784` "Ignore external hermes-agent repository" |
| Status | Clean working tree |
| Key commits (reverse chronological) | `759a990` Complete AI-OS Hermes Kernel release implementation; `20895b0` integrate Tasks 14-15 managers; `e529a3b` complete Tasks 14-15 core managers; `aee3fec` upgrade ResourceManager; `1a49277` implement HealthManager |

### 1.2 Untracked Files (Repository Hygiene)
| Path | Type | Notes |
|------|------|-------|
| `.pytest-cache/` | Temp artifact | Should be in `.gitignore` |
| `FINAL_ARCHITECTURE_REVIEW_REPORT.md` | Analysis artifact | Outdated snapshot — contains factual errors vs current code |
| `TASK_13_ARCHITECTURE_REVIEW.md` | Analysis artifact | Pre-implementation review |
| `TASK_13_IMPLEMENTATION_REPORT.md` | Analysis artifact | Post-implementation report |
| `architecture/Part15/MEMORY.md` | In-session context | Claude Code memory file |
| `architecture/Part15/analysis-gap-impl-vs-spec.md` | Gap analysis (DRAFT) | Stale — claims SecurityManager/CapabilityManager/ObservabilityManager are GAP |
| `architecture/Part15/TERMINAL_1_GAP_ANALYSIS.md` | Gap analysis (FINAL) | Current document — accurate |
| `hermes-agent/` | Separate application | v0.20.1, NOT part of `aios` package |

### 1.3 Test Suite Baseline
| Metric | Value |
|--------|-------|
| Tests collected | 767 |
| Tests passing | 697 (in `tests/unit/`) + integration + performance |
| Tests failing | 0 |
| Test errors | 3 — `TestCheckpointRecovery` in `test_storage_manager.py` (pre-seeded workflow state required) |
| Warnings | 177 — `datetime.utcnow()` deprecation warnings |
| Test collection errors | 225 — caused by pytest discovering `hermes-agent/tests/` which has missing dependencies |

---

## 2. Architecture Spec Status

### 2.1 Part Status
| Part | Status | Notes |
|------|--------|-------|
| Parts 1–13 | Completed | Per MASTER_ARCHITECTURE_ROADMAP.md |
| Part 14 | Planned | Documentation audit and corrections in progress — see Part 14 memory entries |
| Part 15 | NOT READY | 27 files total; all substantive (none empty — earlier "15 empty" claim was based on outdated snapshot) |

### 2.2 Part 15 File Inventory (27 files)
All 27 files have substantive content (minimum 68 bytes). Chapter files 15.1–15.13 are all populated. The README, review-checklist, and glossary are all complete. STATUS: NOT READY per README and review-checklist document control sections, but NOT due to missing files.

---

## 3. Current-State Matrix

### 3.1 Core Components (C1–C4)
| Component | Spec (Part 1 §1.8) | Implementation | Status | ICoreManager Compliant |
|-----------|--------------------|----------------|--------|----------------------|
| **C1 EventBus** | Canonical async-native bus | `events/core/bus.py` — full EventBus with DLQ, priority lanes, 5-state FSM | ✅ EXISTING | N/A (not a manager) |
| **C2 ServiceRegistry** | Service registration/registry | `core/service_registry.py` — full implementation | ✅ EXISTING | N/A |
| **C3 ConfigurationManager** | 4-layer merge, freeze() | `core/configuration_manager.py` — merge + freeze + schema | ✅ EXISTING | N/A |
| **C4 StructuredLogger** | Structured JSON logging | `core/structured_logger.py` — replaces stdlib logging | ✅ EXISTING | N/A |

### 3.2 Core Managers (9 per Part 4 §4.2.3) — ICoreManager Compliance Matrix
| Manager | Phase | ICoreManager Surface | Constructor DI | StructuredLogger | Registered with LM | Reset Singleton | Status |
|---------|-------|---------------------|----------------|-------------------|-------------------|-----------------|--------|
| **LifecycleManager** | 1 | ✅ Full | ✅ Self-registers | ✅ | ✅ Self | ✅ | COMPLIANT |
| **StateManager** | 2 | ✅ Full | ✅ DI (`event_bus`, `service_registry`, `configuration_manager`, `logger`) | ✅ | ✅ Registered (line 628) | ✅ | COMPLIANT |
| **StorageManager** | 2 | ✅ Full | ✅ DI same pattern | ✅ | ✅ Registered (line 638) | ✅ | COMPLIANT |
| **HealthManager** | 3 | ✅ Full | ✅ DI same pattern | ✅ | ✅ Registered (line 647) | ✅ | COMPLIANT |
| **ResourceManager** | 3 | ✅ Full | ✅ DI same pattern | ✅ | ✅ Registered (line 659) | ✅ | COMPLIANT |
| **SecurityManager** | 3 | ✅ Full | ✅ DI same pattern | ✅ | ✅ Registered (line 669) | ✅ | COMPLIANT |
| **CapabilityManager** | 4 | ✅ Full | ✅ DI same pattern | ✅ | ✅ Registered (line 678) | ✅ | COMPLIANT |
| **ObservabilityManager** | 5 | ✅ Full | ✅ DI same pattern | ✅ | ✅ Registered (line 687) | ✅ | COMPLIANT |
| **WorkflowManager** | 4 | ✅ Full (`_NAME`, `_PHASE=4`, `_MANAGER_ID`, `_MANAGER_DEPENDENCIES`, `name`, `phase`, `dependencies`, `health_ready()`, `initialize()`, `shutdown()`) | ✅ DI (`event_bus`, `service_registry`, `configuration_manager`, `logger`, `state_manager`) | ✅ | ✅ Registered (line 703-704) | ✅ (`reset_workflow_manager_singleton`) | **COMPLIANT** |

**Key correction:** The `TERMINAL_1_GAP_ANALYSIS.md` and `analysis-gap-impl-vs-spec.md` were written against commit `e529a3b` (HEAD at their creation). The current HEAD is `dc09784` (`759a990` "Complete AI-OS Hermes Kernel release implementation") which **already upgraded WorkflowManager to ICoreManager compliance**. All 9 Core Managers are now compliant.

### 3.3 Core Manager Standard Pattern (9/9 compliant managers)
All 9 Core Managers follow this exact pattern:
1. Module-level constants: `_NAME`, `_MANAGER_ID`, `_PHASE`, `_MANAGER_DEPENDENCIES`
2. ICoreManager Protocol surface: `name`, `phase`, `dependencies`, `health_ready()`, `initialize()`, `shutdown()`
3. Constructor receives dependencies via DI (C1 EventBus resolved from canonical singleton; C2/C3/C4 injected as optional keyword args with fallback to singletons)
4. `register_with_service_registry()` method registers as `core.{name}` with `kind: "core_manager"` metadata
5. Uses `StructuredLogger` (C4), NOT `logging.getLogger(__name__)`
6. Has `get_{name}_manager()` / `set_{name}_manager()` / `reset_{name}_manager_singleton()` trio
7. Registered with LifecycleManager in `kernel.py._init_lifecycle_manager()`

### 3.4 Engineering Services (8)
| Service | File | BaseService | Legacy Event? | Event-Driven Only? | Status |
|---------|------|-------------|---------------|-------------------|--------|
| PlanningService | `services/planning.py` | ✅ | ✅ `from aios.events.base import Event` | ✅ | EXISTS |
| CodingService | `services/coding.py` | ✅ | ✅ `from aios.events.base import Event` | ✅ | EXISTS |
| ReviewService | `services/review.py` | ✅ | ✅ | ✅ | EXISTS |
| TestingService | `services/testing.py` | ✅ | ✅ | ✅ | EXISTS |
| DeploymentService | `services/deployment.py` | ✅ | ✅ | ✅ | EXISTS |
| OperationsService | `services/operations.py` | ✅ | ✅ | ✅ | EXISTS |
| LearningService | `services/learning.py` | ✅ | ✅ | ✅ | EXISTS |
| MemoryService | `services/memory.py` | ✅ | ✅ | ✅ | EXISTS |

### 3.5 Capability Facade Services (4)
| Service | File | Wraps Kernel Manager | Status |
|---------|------|---------------------|--------|
| SkillService | `services/skill.py` | `core.skill_manager` | EXISTS |
| CouncilService | `services/council.py` | `core.council_manager` | EXISTS |
| MCPService | `services/mcp.py` | `core.mcp_manager` | EXISTS |
| MemoryService | `services/memory.py` | `core.memory` | EXISTS |

### 3.6 CLI Command Groups
| Command Group | Spec (Part 9) | Implemented? | File |
|--------------|---------------|--------------|------|
| `aios version` | 9.1 | ✅ | `cli/main.py:33` |
| `aios kernel` | 9.2 | ✅ (start/stop/status) | `cli/commands/kernel/__init__.py` |
| `aios doctor` | 9.3 | ✅ (config validation only) | `cli/commands/doctor/__init__.py` |
| `aios plan` | 9.4 | ❌ | — |
| `aios code` | 9.5 | ❌ | — |
| `aios review` | 9.6 | ❌ | — |
| `aios test` | 9.7 | ❌ | — |
| `aios deploy` | 9.8 | ❌ | — |
| `aios operate` | 9.9 | ❌ | — |
| `aios learn` | 9.10 | ❌ | — |
| `aios memory` | 9.11 | ❌ | — |
| `aios interact` | 9.12 | ❌ | — |

### 3.7 Event System Architecture
| Aspect | Legacy (`aios.events`) | Canonical (`aios.events.core`) | Bridge Layer |
|--------|----------------------|-------------------------------|--------------|
| `EventType` | `events/base.py` — string constants | `events/core/types.py` — 121-member closed enum | ✅ `bus.py` compatibility layer delegates to canonical |
| `EventBus` | `events/bus.py` — thread-based wrapper | `events/core/bus.py` — async-native | ✅ Legacy `EventBus` class delegates to canonical singleton |
| `Event` | `events/base.py` — 6-field dataclass, no `kw_only=True` | `events/core/event.py` — 12-field frozen dataclass | ✅ `_convert_to_core_event()` (raises if not CoreEvent) |
| `ServiceRegistry` | `services/registry.py` — legacy wrapper | `core/service_registry.py` — canonical | ✅ Delegates to canonical singleton |

**Critical insight:** `BaseService` (services/base.py:78-103) accepts and uses the **canonical** `CoreEventBus` as its `event_bus` property. Services' `subscribe()` uses canonical `SubscribeOptions` + `EventType`. Services' `emit()` publishes to the canonical bus. But service files import `from aios.events.base import Event` — the compatibility layer's `_convert_to_core_event()` converts legacy events to CoreEvent. This is the **bridge pattern** keeping the system functional.

### 3.8 Kernel Lifecycle
| Component | Phase | Status | Notes |
|-----------|-------|--------|-------|
| C1 EventBus | Phase 0 | ✅ | Initialized in `_init_event_bus()` |
| C2 ServiceRegistry | Phase 1 | ✅ | Initialized in `_init_service_registry()` |
| C3 ConfigurationManager | Phase 2 | ✅ | Initialized in `_init_configuration_manager()`, `freeze()` at Phase 2→3 boundary |
| C4 StructuredLogger | Phase 3 | ✅ | Initialized in `_init_structured_logger()` |
| LifecycleManager | Phase 1 | ✅ | Self-registers, drives 5-phase Core Manager topology |
| 8 Phase 2-5 Managers | Phases 2-5 | ✅ | All constructed + registered with LM |
| WorkflowManager | Phase 4 | ⚠️ | Constructed but NOT registered; `_start_workflow_manager()` is no-op |
| Engineering Services | Post-kernel | ✅ | Started via `_start_services()` |
| FSM | Kernel | ❌ | Uses `_running: bool` flag, NOT 5-state FSM. FSM is in LifecycleManager (8-state) |

---

## 4. Dependency Graph

### 4.1 Core Manager Phase Topology (from `lifecycle_manager.py:286-303`)
```
Phase 1 (Foundation):
    LifecycleManager
        │
Phase 2 (State & Storage):
    StateManager        depends on: (1)
    StorageManager      depends on: (1)
        │
Phase 3 (Governance):
    SecurityManager     depends on: (1)
    ResourceManager     depends on: (1, 2)
    HealthManager       depends on: (1, 2)
        │
Phase 4 (Execution):
    CapabilityManager   depends on: (1, 2, 3)
    WorkflowManager     depends on: (1, 2, 3) — registered with LM at kernel.py:703-704
        │
Phase 5 (Observability):
    ObservabilityManager   depends on: (1, 2, 3, 4)
```

### 4.2 Kernel Construction Dependencies (from `kernel.py._init_core_components()`)
```
Kernel.__init__()
    ├── _init_event_bus()         → C1 EventBus (singleton)
    ├── _init_service_registry()   → C2 ServiceRegistry (singleton)
    ├── _init_configuration_manager()  → C3 ConfigurationManager (singleton)
    │   └── _init_structured_logger()   → C4 StructuredLogger (singleton)
    ├── _init_lifecycle_manager()
    │   ├── new LifecycleManager()      → Phase 1 (self-registers)
    │   ├── _init_core_managers()       → Constructs StateManager, StorageManager, ...
    │   │   ├── ResourceManager(state_manager) → Phase 3
    │   │   ├── SecurityManager(...)       → Phase 3
    │   │   ├── HealthManager(...)         → Phase 3
    │   │   ├── CapabilityManager(...)     → Phase 4
    │   │   ├── ObservabilityManager(...)  → Phase 5
    │   │   └── WorkflowManager(state_manager)  → Phase 4 (NOT registered)
    │   └── _init_lifecycle_manager() registers all 9 managers including WorkflowManager (line 703-704)
    └── _start_services()
        └── ("resource_manager", cleanup)
```

### 4.3 Engineering Service Dependencies
All Engineering Services → EventBus (publish/subscribe only). No direct service-to-service dependencies. `PlanningService.depends_on = ["memory"]` is declarative only.

### 4.4 Capability Facade Service Dependencies
| Facade | Wraps | Access Pattern |
|--------|-------|----------------|
| SkillService | `core.skill_manager` | `get_skill_manager()` singleton |
| CouncilService | `core.council_manager` | `get_council_manager()` singleton |
| MCPService | `core.mcp_manager` | `get_mcp_manager()` singleton |
| MemoryService | `core.memory` | `get_memory_manager()` singleton |

---

## 5. Task Groupings (Strict Grouping Rules Applied)

Per the workflow spec's strict grouping rules: *Group tasks by dependency boundary; tasks in the same group can be verified together.*

### Group A: WorkflowManager Upgrade (P1 — COMPLETED in `759a990`)
**Status:** ✅ COMPLETED — WorkflowManager is fully ICoreManager compliant. No remaining work needed.

### Group B: Package Export Fixes (P2 — MEDIUM)
**Tasks:**
- B1: Add `SecurityManager`, `CapabilityManager`, `ObservabilityManager` to `aios/core/__init__.py` `__all__`
- B2: Add `LifecycleManager`, `ICoreManager` to `aios/core/__init__.py` `__all__`
- B3: Add all Core Managers to `aios/__init__.py` `__all__`

**Can be verified together** — all are import/export consistency fixes.

### Group C: EventType Count Documentation Fixes (P2 — MEDIUM)
**Tasks:**
- C1: Fix `registry.py:11` docstring from "118-member" to "121-member"
- C2: Fix `test_event_core.py:351` assertion from 118 to 121

**Can be verified together** — both are test/doc alignment fixes on the same count value.

### Group D: Kernel FSM (P3 — LOW)
**Task:** Implement 5-state FSM in `HermesKernel` (UNINITIALIZED→INITIALIZING→RUNNING→SHUTTING_DOWN→TERMINATED) per Part 1 §1.8.5, or formally document the delegation to LifecycleManager's 8-state model as a design decision (CONFLICT).

Can be done independently.

### Group E: CLI Extension (P3 — LOW)
**Task:** Implement CLI command groups 9.4–9.12 (`plan`, `code`, `review`, `test`, `deploy`, `operate`, `learn`, `memory`, `interact`). All depend on services being operational; can be implemented incrementally.

### Group F: Event System Consolidation (P3 — LOW)
**Task:** Migrate `aios/__init__.py` to import canonical `EventType` instead of legacy. All Core Managers already use canonical EventType; this is a user-facing API cleanup.

---

## 6. Deletable / Deferrable Work

| Item | Recommendation | Rationale |
|------|----------------|-----------|
| `FINAL_ARCHITECTURE_REVIEW_REPORT.md` | DELETE | Contains 5+ factual errors vs current `dc09784` code |
| `analysis-gap-impl-vs-spec.md` | DELETE or UPDATE | Stale — claims Tasks 14-15 managers are GAP; written against pre-`e529a3b` snapshot |
| `TERMINAL_1_GAP_ANALYSIS.md` | UPDATE or supersede | Claims WorkflowManager is not ICoreManager compliant — WRONG, fixed in `759a990` `dc09784`
| `TASK_13_ARCHITECTURE_REVIEW.md` | DEFER | Pre-implementation review, historical only |
| `TASK_13_IMPLEMENTATION_REPORT.md` | DEFER | Historical artifact |
| `hermes-agent/tests/` | EXCLUDE from test runs | Separate application; causes 225 collection errors when pytest discovers it; should add `testpaths` or `conftest.py` exclusion |
| `test_cli.py`, `test_config.py` | DELETE (empty stubs) | Both are 0-byte files; no tests to collect |
| CLI command groups 9.4–9.12 | DEFER | Not blocking kernel operation |
| Kernel 5-state FSM | DEFER | Currently functional with `_running` flag; LifecycleManager has the full FSM |

---

## 7. Test Coverage Analysis

### 7.1 Test Inventory (767 tests)
| Directory | Tests |
|-----------|-------|
| `tests/unit/` | 697 |
| `tests/integration/` | ~60 |
| `tests/performance/` | 2 |
| `tests/test_cli.py` | 0 (empty file) |
| `tests/test_config.py` | 0 (empty file) |

### 7.2 Acceptance Test Matrix
| Test File | Core Manager | Tests | Status |
|-----------|-------------|-------|--------|
| `test_task9_critical_acceptance.py` | LifecycleManager | — | ✅ PASS |
| `test_task10_critical_acceptance.py` | StateManager | — | ✅ PASS |
| `test_task11_critical_acceptance.py` | StorageManager | — | ✅ PASS |
| `test_task12_critical_acceptance.py` | HealthManager | — | ✅ PASS |
| `test_task12_health_manager.py` | HealthManager | — | ✅ PASS |
| `test_task13_critical_acceptance.py` | ResourceManager | — | ✅ PASS |
| `test_task13_resource_manager.py` | ResourceManager | — | ✅ PASS |
| `test_task14_critical_acceptance.py` | SecurityManager | — | ✅ PASS |
| `test_task14_security_manager.py` | SecurityManager | — | ✅ PASS |
| `test_task15_critical_acceptance.py` | CapabilityManager | — | ✅ PASS |
| `test_task15_capability_manager.py` | CapabilityManager | — | ✅ PASS |
| `test_task15_observability_manager.py` | ObservabilityManager | — | ✅ PASS |
| `test_task15_workflow_manager.py` | WorkflowManager | — | ✅ PASS (tests ICoreManager surface + business API + canonical events) |

### 7.3 Known Test Issues
| Issue | File | Lines | Classification |
|-------|------|-------|----------------|
| 3 test errors in TestCheckpointRecovery | `test_storage_manager.py` | — | Pre-seeded workflow state required |
| `test_event_core.py:351` asserts 118 | `test_event_core.py` | 349-351 | OUTDATED — enum has 121 |
| `registry.py:11` says "118" | `events/core/registry.py` | 11 | STALE DOCSTRING |
| 177 `datetime.utcnow()` deprecation warnings | Multiple files | — | DeprecationWarning, not failures |

### 7.4 Missing E2E Coverage
- No test verifies the **complete** kernel lifecycle from `start()` through all 5 phases to `stop()` with all 9 managers
- No test verifies reverse shutdown order (Phase 5 → Phase 1)
- No test verifies WorkflowManager lifecycle through LifecycleManager (it's not registered)
- `test_integration.py` uses `run_kernel()` but does NOT verify individual manager lifecycle states post-shutdown

---

## 8. Documentation Audit

### 8.1 Architecture Documents (Parts 1–13)
| Part | Status | Location |
|------|--------|----------|
| Part 1 | Complete | `architecture/Part01/` |
| Parts 2–13 | Complete | `architecture/Part02/` through `architecture/Part13/` |

### 8.2 Part 14
Per memory entries: De-duplication work complete, security chapter created, anti-invention corrections applied.

### 8.3 Part 15 (27 files)
All files have substantive content. Status per README.md and review-checklist.md: **NOT READY** (authoring of all 13 chapter files needed — they now exist but need integration review).

### 8.4 Stale Documents Requiring Update
| Document | Issue | Recommendation |
|----------|-------|----------------|
| `ARCHITECTURAL_INVENTORY.md` (July 28) | Claims "6 critical bugs", "12/21 tests failing", SecurityManager/CapabilityManager/ObservabilityManager as GAP | DELETE or mark superseded by TERMINAL_1_GAP_ANALYSIS.md |
| `analysis-gap-impl-vs-spec.md` | Claims SecurityManager/CapabilityManager/ObservabilityManager are "GAP — Not implemented" — WRONG, all implemented in `e529a3b`+`759a990` | Update or mark superseded |
| `TERMINAL_1_GAP_ANALYSIS.md` | Claims WorkflowManager is not ICoreManager compliant — WRONG, fixed in `759a990` | Update or supersede with current report |
| `FINAL_ARCHITECTURE_REVIEW_REPORT.md` | 5+ factual errors vs current code | DELETE |

---

## 9. Packaging & Installability

| Aspect | Status | Notes |
|--------|--------|-------|
| `pyproject.toml` | ✅ | Package: `ai-os` v0.2.0, Python >=3.12 |
| Entry point | ✅ | `aios = "aios.cli.main:app"` |
| Source layout | ✅ | `src/` layout |
| Dependencies | ✅ | typer, rich, pydantic, python-dotenv, PyYAML, aiohttp, websockets |
| Dev dependencies | ✅ | pytest, pytest-asyncio, ruff, mypy, black |
| `.gitignore` | ❌ | `.pytest-cache/` not ignored |
| `requirements.txt` | ❌ | No root-level requirements files |
| hermes-agent isolation | ⚠️ | Separate `pyproject.toml` at repo root; should be in `.gitignore` or subdirectory; causes pytest collection errors |

---

## 10. Terminal 2 Handoff Specification

### 10.1 Critical Priority Items (Must be addressed first)

**P1-RESOLVED (was critical, now fixed): WorkflowManager ICoreManager Upgrade**
Commit `759a990` ("Complete AI-OS Hermes Kernel release implementation") already completed this. WorkflowManager at `src/aios/core/workflow.py` now has: `_NAME`, `_PHASE=4`, `_MANAGER_ID="core.workflow"`, `_MANAGER_DEPENDENCIES`, full ICoreManager surface (`name`, `phase`, `dependencies`, `health_ready()`, `initialize()`, `shutdown()`), DI constructor, `register_with_service_registry()`, StructuredLogger (C4). Registered with LifecycleManager at `kernel.py:703-704`. The stale `TERMINAL_1_GAP_ANALYSIS.md` and `analysis-gap-impl-vs-spec.md` should be updated or superseded.

**P1-CRITICAL: EventType Count Fix (Group C)**
- `src/aios/events/core/registry.py:11`: "118-member" → "121-member"
- `tests/unit/test_event_core.py:349-351`: Assert 118 → Assert 121

### 10.2 Medium Priority Items

**P2-MEDIUM: Package Exports (Group B)**
- Add SecurityManager, CapabilityManager, ObservabilityManager to `aios/core/__init__.py` `__all__`
- Add all Core Managers to `aios/__init__.py` `__all__`

**P2-MEDIUM: Repository Hygiene**
- Add `.pytest-cache/` to `.gitignore`
- Add pytest `testpaths = ["tests/unit", "tests/integration", "tests/performance"]` to prevent hermes-agent discovery
- Delete empty `tests/test_cli.py` and `tests/test_config.py`
- Delete or archive stale `FINAL_ARCHITECTURE_REVIEW_REPORT.md` (5+ factual errors)
- Update or archive stale `analysis-gap-impl-vs-spec.md`

### 10.3 Low Priority / Deferrable

- Kernel 5-state FSM implementation (or formal documentation as design decision)
- CLI command groups 9.4–9.12 (`plan`, `code`, `review`, `test`, `deploy`, `operate`, `learn`, `memory`, `interact`)
- Event system consolidation: `aios/__init__.py` should import canonical EventType
- Complete E2E test coverage: full kernel lifecycle start→all 5 phases→stop with reverse shutdown verification

### 10.4 Test Verification Commands
```bash
# Core acceptance tests (all 6 pass)
python -m pytest tests/unit/test_task14_15_critical_acceptance.py -v

# Full unit test suite (697 pass, 177 warnings)
python -m pytest tests/unit/ --tb=short -q

# Post-Terminal-2 verification
python -m pytest tests/unit/ tests/integration/ tests/performance/ --tb=short -q
```

---

## 11. 100-Point Scored Roadmap

| Milestone | Scope | Points | QA Boundary |
|-----------|-------|--------|-------------|
| **M1: EventType Count & Documentation Alignment** | Groups C1-C2 + registry.py docstring | 15 | `test_event_core.py` asserts 121 + `test_event_type.py` asserts 121 + `test_event_type_registry.py` asserts 121 + `registry.py:11` says "121-member" |
| **M2: Repository Hygiene** | .gitignore + pytest testpaths + delete empty/stale files | 10 | `python -m pytest` from repo root collects ~767 tests with 0 collection errors |
| **M3: Package Export Completeness** | Groups B1-B3: all Core Managers in `__all__` | 15 | `from aios.core import SecurityManager, CapabilityManager, ObservabilityManager` succeeds; `from aios import HermesKernel, LifecycleManager, SecurityManager, CapabilityManager, ObservabilityManager` succeeds |
| **M4: Kernel FSM + E2E Coverage** | Implement 5-state FSM or document delegation + add full lifecycle E2E test | 20 | New test verifies 5-phase init + reverse-phase shutdown of all 9 managers; FSM state transitions asserted |
| **M5: CLI Extension (Optional/Deferred)** | Implement command groups 9.4–9.12 | 10 | `aios plan --help`, `aios code --help`, etc. all return help text |
| **M6: WorkflowManager Singleton Reduction (Optional/Deferred)** | Replace `get_core_event_bus()` / `get_retry_manager()` singleton calls in workflow.py with DI | 10 | WorkflowManager constructor accepts `event_bus` parameter directly; no `get_*()` singleton calls in constructor |
| **Total** | | **100** | |

### Milestone Dependency Chain
```
M1 (EventType fix) → M3 (Exports) → M4 (E2E test)
     ↘              ↗
M2 (Hygiene) ──────┘
M5 (CLI) —— independent (deferred)
M6 (Singleton reduction) —— independent (deferred)
```

### Terminal 2 Entry Criteria
- All 9 Core Managers are ICoreManager compliant (including WorkflowManager — already done in `759a990`)
- All existing tests must continue to pass (697 in unit tests)
- 0 collection errors from `python -m pytest tests/unit/`

### Terminal 2 Exit Criteria
- Score: 100/100
- All 6 milestones complete
- All 767 tests pass (0 errors, 0 failures)
- EventType count uniformly 121 across code, tests, and documentation
- All Core Managers exported from package `__all__`
- Repository hygiene enforced (no collection errors from root pytest run)

---

*End of Terminal 1 Audit Report*
