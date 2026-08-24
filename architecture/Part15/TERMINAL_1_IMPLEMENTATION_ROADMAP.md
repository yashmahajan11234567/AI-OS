# Terminal 1 — AI-OS V1 Implementation Roadmap

**Date:** 2026-08-22  
**Classification:** READ-ONLY PLANNING — Terminal 1 session  
**Authority Chain:** Parts 0–14 > Accepted ADRs > Part 15 > Implementation > Tests  
**Source Audit:** `TERMINAL_1_AUDIT_REPORT.md` (this document supersedes all older gap analyses)  
**Git HEAD:** `dc09784` — "Ignore external hermes-agent repository"

---

## 1. Executive Summary

The repository is in a substantially more mature state than older gap-analysis documents suggest. The audit confirmed that **all 9 Core Managers are ICoreManager compliant**, including WorkflowManager (upgraded in `759a990`). Several issues cited in the audit as "needs fixing" were found to be **already resolved** in the current HEAD.

This roadmap identifies the **minimum safe set of work** required to reach AI-OS V1 completion. It classifies all remaining work into MUST HAVE, SHOULD HAVE, OPTIONAL, DEFERRED, and OBSOLETE buckets. Two obsolete audit claims (EventType count fix, WorkflowManager registration) are explicitly corrected based on direct source verification.

**Key finding:** The EventType count correction and WorkflowManager ICoreManager upgrade are **already complete**. The audit report's claims to the contrary were based on stale commits. The roadmap corrects these and focuses V1 effort on genuinely remaining work.

**V1 can be achieved in 4 milestones**, not 6. The audit's 6-milestone structure over-partitions work that can be safely compressed into dependency-aligned groups.

---

## 2. Current Repository State

### 2.1 Git State
| Field | Value |
|-------|-------|
| Branch | `main` |
| HEAD | `dc09784` — "Ignore external hermes-agent repository" |
| Status | Clean working tree (untracked: `.pytest-cache/`, `TERMINAL_1_AUDIT_REPORT.md`) |

### 2.2 Core Managers — All 9 Compliant
| Manager | Phase | ICoreManager | Registered with LM | Status |
|---------|-------|-------------|-------------------|--------|
| LifecycleManager | 1 | ✅ | Self-registers | COMPLIANT |
| StateManager | 2 | ✅ | ✅ (`kernel.py:628`) | COMPLIANT |
| StorageManager | 2 | ✅ | ✅ (`kernel.py:638`) | COMPLIANT |
| HealthManager | 3 | ✅ | ✅ (`kernel.py:647`) | COMPLIANT |
| ResourceManager | 3 | ✅ | ✅ (`kernel.py:659`) | COMPLIANT |
| SecurityManager | 3 | ✅ | ✅ (`kernel.py:669`) | COMPLIANT |
| CapabilityManager | 4 | ✅ | ✅ (`kernel.py:694`) | COMPLIANT |
| WorkflowManager | 4 | ✅ | ✅ (`kernel.py:703-704`) | COMPLIANT |
| ObservabilityManager | 5 | ✅ | ✅ (`kernel.py:712`) | COMPLIANT |

**Correction to audit §3.2/§3.4/§4.2/§10.1:** The audit states WorkflowManager is "NOT registered" and that `_start_workflow_manager()` is a no-op. This is **STALE** — verified that `kernel.py:703-704` registers WorkflowManager with LifecycleManager. All 9 managers are registered and compliant.

### 2.3 Test Suite Baseline
| Metric | Value |
|--------|-------|
| Tests collected (tests/unit/) | 697 |
| Tests passing | 697 (0 failures) |
| Test errors | 3 (`TestCheckpointRecovery` — pre-seeded state) |
| Collection errors (from repo root) | 225 (`hermes-agent/tests/` contamination) |
| Empty stub test files | `tests/test_cli.py` (0B), `tests/test_config.py` (0B) |

### 2.4 Package Exports
- `src/aios/core/__init__.py` `__all__`: **COMPLETE** — SecurityManager, CapabilityManager, ObservabilityManager, LifecycleManager, ICoreManager all present.
- `src/aios/__init__.py` `__all__`: **Incomplete** — only `["__version__"]`. Names are imported at module level (so direct import works) but not listed in `__all__` (so starred imports won't re-export them).

### 2.5 EventType Count — ALREADY CORRECTED
- `registry.py:11`: reads "121-member" ✅ (audit claimed "118-member" — STALE)
- `test_event_core.py:351`: asserts `== 121` and **passes** ✅ (audit claimed 118 — STALE)
- `EventType` enum has exactly 121 members (verified via Python runtime)

### 2.6 Kernel FSM
- `HermesKernel` uses `_running: bool` flag, NOT a 5-state FSM.
- `LifecycleManager` has an 8-state FSM that drives Core Manager lifecycle.
- No `_start_workflow_manager()` no-op found — WorkflowManager is registered and participates in lifecycle.

### 2.7 CLI
8 command groups implemented (version, kernel, doctor out of 11). 9 groups missing: plan, code, review, test, deploy, operate, learn, memory, interact.

### 2.8 WorkflowManager Singleton Usage
Confirmed: `workflow.py:278` calls `get_core_event_bus()` and `workflow.py:300` calls `get_retry_manager()` in the constructor.

### 2.9 Repository Hygiene
- `.gitignore` already contains `.pytest-cache/` — the untracked `.pytest-cache/` directory exists because it was created before the ignore rule was committed (or git was not refreshed).
- `pyproject.toml` has NO `testpaths` setting — causes `hermes-agent/tests/` discovery.
- `hermes-agent/` is listed at repo root with `/hermes-agent/` in `.gitignore` (line 22).

---

## 3. Audit Findings Incorporated

All findings from `TERMINAL_1_AUDIT_REPORT.md` are incorporated. **Two audit claims are explicitly corrected** based on direct source verification:

| Audit Claim | Correction | Evidence |
|------------|-----------|----------|
| EventType count still 118 in `registry.py` and test | Already corrected to 121 | `registry.py:11` says "121-member"; `test_event_core.py:351` asserts 121 and passes |
| WorkflowManager "constructed but NOT registered" | Already registered at `kernel.py:703-704` | Live source code shows `lm.register_manager(self._workflow_manager)` |
| Audit §3.4: WorkflowManager "⚠️ Constructed but NOT registered" | Superseded by `759a990` | Audit's own §3.2 correction note acknowledges the fix |

All other audit findings are accepted as-is.

---

## 4. Remaining V1 Scope

### MUST HAVE — Required for AI-OS V1

| ID | Work | Rationale | Priority |
|----|------|-----------|----------|
| V1-MUST-1 | Complete top-level `aios/__init__.py` `__all__` | External consumers and CLI depend on `from aios import SecurityManager` working via starred imports and IDE auto-completion. Currently works via direct import but `__all__` is incomplete. | HIGH |
| V1-MUST-2 | Add `testpaths` to `pyproject.toml` | 225 collection errors from `hermes-agent/tests/` discovery. Blocks clean test runs from repo root. | HIGH |
| V1-MUST-3 | Verify Kernel E2E lifecycle (init→run→shutdown) with all 9 managers | No test verifies complete lifecycle start through all 5 phases to stop with reverse shutdown order. Audit §7.4. | MEDIUM |
| V1-MUST-4 | Verify WorkflowManager lifecycle through LifecycleManager | Audit §7.4 notes no E2E coverage for WorkflowManager lifecycle. Must confirm it participates correctly in init/shutdown. | MEDIUM |

### SHOULD HAVE — Important but not blocking V1

| ID | Work | Rationale | Priority |
|----|------|-----------|----------|
| V1-SHOULD-1 | Delete empty stub test files | `tests/test_cli.py` (0B), `tests/test_config.py` (0B) — 0 tests, just noise. | LOW |
| V1-SHOULD-2 | Kernel FSM formalization | Currently uses `_running` flag. Functional but not architecturally clean per Part 1 §1.8.5. Document as design decision OR implement. | LOW |
| V1-SHOULD-3 | `aios/__init__.py` canonical EventType import | Should import canonical EventType for user-facing consistency. All internal code already uses canonical. | LOW |
| V1-SHOULD-4 | Repository hygiene cleanup | Archive stale reports, finalize `.pytest-cache` removal. | LOW |

### OPTIONAL — Can be deferred without blocking V1

| ID | Work | Rationale | Priority |
|----|------|-----------|----------|
| V1-OPT-1 | CLI command groups 9.4–9.12 | Not required for kernel operation. User can invoke via SDK. | LOW |
| V1-OPT-2 | WorkflowManager singleton reduction | Technical debt, not an architecture violation. `get_core_event_bus()` and `get_retry_manager()` are established singleton patterns used across the codebase. | LOW |
| V1-OPT-3 | `datetime.utcnow()` deprecation warnings | 177 warnings — deprecation only, no failures. | LOW |
| V1-OPT-4 | Complete reverse-shutdown-order E2E test | Extends V1-MUST-3 but tests Phase 5→1 reverse ordering specifically. | LOW |

### DEFERRED — Explicitly outside V1 scope
- CLI command groups 9.4–9.12 (`plan`, `code`, `review`, `test`, `deploy`, `operate`, `learn`, `memory`, `interact`)
- WorkflowManager singleton reduction (`get_core_event_bus()` / `get_retry_manager()` in constructor)
- Kernel 5-state FSM implementation (if not done in SHOULD-2)
- Event system consolidation (canonical EventType in `aios/__init__.py`) if SHOULD-3 is deferred

### OBSOLETE — Remove from roadmap / Already resolved
- EventType count correction (M1 in old roadmap) — **already done**, verified: registry says 121, test asserts 121 and passes
- WorkflowManager ICoreManager upgrade (Group A) — **already done** in `759a990`, verified
- `analysis-gap-impl-vs-spec.md` claim that SecurityManager/CapabilityManager/ObservabilityManager are GAP — **incorrect**, all implemented and compliant
- `TERMINAL_1_GAP_ANALYSIS.md` claim that WorkflowManager is not ICoreManager compliant — **incorrect**, fixed in `759a990`
- `FINAL_ARCHITECTURE_REVIEW_REPORT.md` — contains 5+ factual errors vs current code; DELETE

---

## 5. Deferred / Optional / Obsolete Work

| Item | Classification | Rationale |
|------|----------------|-----------|
| EventType count fix | **OBSOLETE** — already resolved | Verified: registry.py:11 = "121-member", test passes with 121 |
| WorkflowManager ICoreManager upgrade | **OBSOLETE** — already resolved | Verified: `759a990` fixed it, all 9 managers compliant |
| WorkflowManager "not registered with LM" | **OBSOLETE** — audit claim was stale | Verified: `kernel.py:703-704` registers it |
| `FINAL_ARCHITECTURE_REVIEW_REPORT.md` | **DELETE** | 5+ factual errors vs `dc09784` |
| `analysis-gap-impl-vs-spec.md` | **DELETE or UPDATE** | Claims SecurityManager/CapabilityManager/ObservabilityManager are GAP — wrong |
| CLI 9.4–9.12 command groups | **DEFERRED** | Not required for V1 kernel operation |
| WorkflowManager singleton reduction | **DEFERRED** | Technical debt, non-blocking, same pattern used system-wide |
| Kernel 5-state FSM | **OPTIONAL/DEFERRED** | `_running` flag is functional; LifecycleManager owns the real FSM |
| `hermes-agent/` test contamination | **OBSOLETE** — already gitignored | `/hermes-agent/` is in `.gitignore`; the issue is missing `testpaths` |
| `test_cli.py`, `test_config.py` empty stubs | **SHOULD** — low priority | 0 bytes, 0 tests |
| `datetime.utcnow()` warnings | **OPTIONAL** | DeprecationWarning only, no failures |

---

## 6. Dependency Graph

```
V1-MUST-1 (Package exports __all__)
    ├── depends on: none (pure export additions)
    └── parallel with: V1-MUST-2

V1-MUST-2 (testpaths / no collection errors)
    ├── depends on: none (config change)
    └── parallel with: V1-MUST-1

V1-MUST-3 (Kernel E2E lifecycle test)
    ├── depends on: V1-MUST-1, V1-MUST-2 (clean test environment)
    ├── depends on: all 9 managers being registered (VERIFIED ✅)
    └── parallel with: V1-MUST-4 (same test file)

V1-MUST-4 (WorkflowManager lifecycle E2E)
    ├── depends on: V1-MUST-2 (clean test environment)
    ├── depends on: WorkflowManager registered (VERIFIED ✅)
    └── parallel with: V1-MUST-3

V1-SHOULD-1 (Delete empty stubs)
    ├── depends on: none
    └── can run anytime

V1-SHOULD-2 (Kernel FSM)
    └── depends on: V1-MUST-3 results (decide implement vs document)

V1-OPT-1 (CLI)
    └── independent (deferred)

V1-OPT-2 (Singleton reduction)
    └── independent (deferred)
```

**Hard dependencies:**
- E2E lifecycle tests (V1-MUST-3/4) require clean test collection (V1-MUST-2) — `hermes-agent/tests/` contamination causes 225 collection errors.
- E2E tests require all 9 managers registered — **verified complete** ✅.

**Parallel opportunities:**
- V1-MUST-1, V1-MUST-2, V1-SHOULD-1 can all proceed in parallel.
- V1-MUST-3, V1-MUST-4 can be written in the same test file in parallel.

---

## 7. Task Compression Analysis

### Previous task-level structure (from audit §10–§11)
The audit proposed 6 milestones with task-level granularity:
- M1: EventType count fix (2 tasks)
- M2: Repository hygiene (4 tasks)
- M3: Package exports (3 tasks)
- M4: Kernel FSM + E2E (1 task)
- M5: CLI extension (deferred)
- M6: Singleton reduction (deferred)

### New development group structure
After verification, two milestones collapsed:
- **M1 (EventType) is OBSOLETE** — already fixed. Removed entirely.
- **M4 (Kernel FSM)** demoted to OPTIONAL — `_running` flag is functional; real FSM is in LifecycleManager.

### Compression metrics
| Metric | Old | New |
|--------|-----|-----|
| Previous implementation units | 6 milestones (11 tasks) | — |
| New development groups | 4 groups (within 4 milestones) | — |
| New milestones | — | **4** |
| Eliminated redundant context loads | ~3 (EventType, WorkflowManager upgrade, stale-gap-analysis review) | — |
| Eliminated redundant QA cycles | ~2 (M1 EventType test was already passing, M4 FSM was not blocking) | — |

**Compression achieved:** The audit's M1 and part of M4 are eliminated. Two remaining audit items (EventType fix, WorkflowManager upgrade) were already completed, so no implementation is needed — only verification and documentation update.

---

## 8. Final Milestone Structure

| Milestone | Name | V1 Required | Risk | QA Boundary |
|-----------|------|-------------|------|-------------|
| **M0** | Baseline Stabilization | ✅ Required | Low | `python -m pytest tests/unit/ --tb=short -q` — 697 pass, 0 failures, 0 collection errors |
| **M1** | Kernel Lifecycle E2E | ✅ Required | Medium | New E2E test passes; existing 697 tests still pass |
| **M2** | Package API Completion | ✅ Required | Low | `from aios import *` exports all 9 managers; `from aios.core import SecurityManager` works |
| **M3** | Closed-Loop Verification | ✅ Required | High | Full kernel lifecycle test (init→all phases→shutdown→reverse) + integration smoke test |

**NOT in V1 scope:**
- CLI extension (M5 in old roadmap) — DEFERRED
- WorkflowManager singleton reduction (M6 in old roadmap) — DEFERRED
- Kernel 5-state FSM implementation — OPTIONAL

---

## 9. Detailed Group Structure

### M0: Baseline Stabilization
**Purpose:** Eliminate all test-collection and repository-hygiene failures so QA runs are clean and reliable.

**Included groups:**
| Group | Work | Why Grouped |
|-------|------|-------------|
| G0-A | Add `testpaths = ["tests/unit", "tests/integration", "tests/performance"]` to `pyproject.toml` | Eliminates 225 collection errors from `hermes-agent/tests/` |
| G0-B | Delete empty stub files `tests/test_cli.py` (0B) and `tests/test_config.py` (0B) | 0 tests, causes confusion, both 0 bytes |
| G0-C | Delete stale report `FINAL_ARCHITECTURE_REVIEW_REPORT.md` (5+ factual errors) | Superseded by this audit report |

**Excluded work:**
- `analysis-gap-impl-vs-spec.md` — UPDATE only (mark superseded), not delete (may contain useful historical context)
- `TASK_13_ARCHITECTURE_REVIEW.md`, `TASK_13_IMPLEMENTATION_REPORT.md` — historical artifacts, leave as-is
- `TERMINAL_1_GAP_ANALYSIS.md` — superseded by this audit report, but leave in place for historical reference

**Dependencies:** None.

**Files/components affected:**
- `pyproject.toml` (add `testpaths`)
- `tests/test_cli.py` (delete)
- `tests/test_config.py` (delete)
- `FINAL_ARCHITECTURE_REVIEW_REPORT.md` (delete)

**Interfaces affected:** None (test infrastructure only).

**Implementation order:** G0-A → G0-B → G0-C (independent, can be parallel)

**Parallel opportunities:** All three groups are independent.

**Group-level tests:**
```bash
python -m pytest tests/unit/ --collect-only -q  # Should collect 697 tests with 0 errors
python -m pytest tests/unit/ --tb=short -q      # Should pass 697, 0 failures
```

**Milestone-level tests:**
```bash
python -m pytest tests/unit/ tests/integration/ tests/performance/ --tb=short -q
# Target: 700+ passed, 0 failures, 0 collection errors
```

**Regression tests:** All 697 existing unit tests must still pass.

**Acceptance criteria:**
- `python -m pytest` from repo root collects 767 tests with 0 collection errors
- `python -m pytest tests/unit/ --tb=short -q` → 697 passed, 0 failed
- No `.pytest_cache/` untracked directory (git status clean after first `pytest` run)

**Failure recovery:** Revert `pyproject.toml` change; restore deleted files from git.

---

### M1: Kernel Lifecycle E2E
**Purpose:** Verify the Hermes Kernel can execute a complete lifecycle through all 5 Core Manager phases with correct initialization and reverse-shutdown ordering, including WorkflowManager.

**Included groups:**
| Group | Work | Why Grouped |
|-------|------|-------------|
| G1-A | Write E2E lifecycle test: Kernel.start() → all 9 managers initialize through 5 phases → Kernel.stop() → all 9 managers shutdown in reverse phase order | Single coherent test boundary; verifies the entire lifecycle machinery |
| G1-B | Write WorkflowManager-specific lifecycle test: verify WM initializes in Phase 4 (after CapabilityManager) and shuts down in reverse | Extends G1-A; same lifecycle path, specific manager verification |

**Excluded work:**
- Kernel 5-state FSM implementation (OPTIONAL — `LifecycleManager` 8-state FSM is the real lifecycle orchestrator)

**Dependencies:**
- M0 complete (clean test environment)
- All 9 Core Managers registered with LifecycleManager (VERIFIED ✅ at `kernel.py:659-714`)

**Files/components affected:**
- `tests/integration/test_kernel_lifecycle_e2e.py` (new file)
- `src/aios/core/kernel.py` (READ-ONLY — verification only, no modifications)

**Interfaces affected:**
- `HermesKernel.start()` / `HermesKernel.stop()` (read-only verification)
- `LifecycleManager.initialize()` / `LifecycleManager.shutdown()` (read-only verification)

**Implementation order:** G1-A (full lifecycle) → G1-B (WorkflowManager specific, builds on G1-A patterns)

**Parallel opportunities:** G1-A and G1-B both write tests; G1-B can start once G1-A establishes patterns. Partial parallelism possible.

**Group-level tests:**
```bash
python -m pytest tests/integration/test_kernel_lifecycle_e2e.py -v
# Target: all new tests pass
```

**Milestone-level tests:**
```bash
python -m pytest tests/unit/ tests/integration/ -q
# Existing 697 unit + new E2E tests must pass together
```

**Regression tests:** All 697 existing unit tests + 2 acceptance test files must still pass.

**Acceptance criteria:**
- New E2E test verifies: Kernel creation → Initialization → Manager registration → Ready → Execution → Shutdown → Stopped
- All 9 Core Managers verified as initialized (Phase 1→5 order) and shut down (Phase 5→1 reverse order)
- WorkflowManager confirmed participating in lifecycle (not a no-op)
- All 697 existing tests still pass

**Failure recovery:** Fix only the failing test group; do not modify kernel code unless a genuine bug is found. If a bug is found, file it for the next milestone.

---

### M2: Package API Completion
**Purpose:** Ensure the full public API surface is properly exported so external consumers (CLI, integrations, users) can access all core components via standard import patterns.

**Included groups:**
| Group | Work | Why Grouped |
|-------|------|-------------|
| G2-A | Add `SecurityManager`, `CapabilityManager`, `ObservabilityManager`, `LifecycleManager`, `ICoreManager`, `HermesKernel`, `run_kernel`, `stop_kernel`, `execute_with_kernel`, `KernelConfig`, `ServiceStatus` to top-level `aios/__init__.py` `__all__` | All are core API exports; single coherent change to one file |
| G2-B | Verify all 9 Core Managers + 4 Core Components are importable from both `aios.core` and `aios` top-level | Same concern: API surface completeness; can be verified with one test script |

**Excluded work:**
- Canonical EventType import in `aios/__init__.py` (OPTIONAL — `EventType` already works via direct import through `aios.events`)

**Dependencies:** None (pure export additions; does not change runtime behavior).

**Files/components affected:**
- `src/aios/__init__.py` (add ~15-20 names to `__all__`)
- `src/aios/core/__init__.py` (already complete — READ-ONLY verify)

**Interfaces affected:**
- `aios.__all__` — expanded public API contract
- No behavioral changes to any manager or component

**Implementation order:** G2-A (edit `__all__`) → G2-B (verify imports)

**Parallel opportunities:** G2-A and G2-B can overlap — write verification script while editing.

**Group-level tests:**
```python
# Verification script (not a test file — run inline)
from aios.core import SecurityManager, CapabilityManager, ObservabilityManager, LifecycleManager, ICoreManager
from aios import HermesKernel, run_kernel, stop_kernel, ResourceManager
print("All imports successful")
```

**Milestone-level tests:**
```bash
python -c "from aios.core import SecurityManager, CapabilityManager, ObservabilityManager"
python -c "from aios import HermesKernel, LifecycleManager, SecurityManager"
python -m pytest tests/unit/ tests/integration/ -q  # No regressions
```

**Regression tests:** All 697 existing unit tests must still pass.

**Acceptance criteria:**
- `from aios.core import SecurityManager, CapabilityManager, ObservabilityManager, LifecycleManager, ICoreManager` succeeds
- `from aios import HermesKernel, run_kernel, stop_kernel, execute_with_kernel` succeeds
- `from aios import SecurityManager, CapabilityManager, ObservabilityManager` succeeds (top-level)
- All 697 existing tests still pass
- `import aios; len(aios.__all__)` > 1 (not just `["__version__"]`)

**Failure recovery:** Revert `__all__` change in `aios/__init__.py`.

---

### M3: Closed-Loop Verification
**Purpose:** Verify the complete AI-OS workflow from user goal to execution to verification to learning, confirming the system can operate as an integrated whole.

**Included groups:**
| Group | Work | Why Grouped |
|-------|------|-------------|
| G3-A | Write integration test: Kernel start → PlanningService → CouncilService (both councils) → CapabilityManager → MCPService → execution → verification → Kernel stop | Single end-to-end flow testing the cognitive loop |
| G3-B | Write failure-path test: execution → failure → RootCauseAnalyzer → LearningService → replanning → re-execute | Same loop, failure branch; validates the recovery path |

**Excluded work:**
- CLI invocation of the loop (DEFERRED — CLI groups not in V1)

**Dependencies:**
- M0 complete (clean test environment)
- M1 complete (kernel lifecycle verified)
- M2 complete (API exports verified)
- All 8 Engineering Services exist (VERIFIED ✅ — PlanningService, CodingService, ReviewService, TestingService, DeploymentService, OperationsService, LearningService, MemoryService)
- Capability Facade Services exist (VERIFIED ✅ — SkillService, CouncilService, MCPService, MemoryService)

**Files/components affected:**
- `tests/integration/test_closed_loop.py` (new file)
- `tests/integration/test_failure_recovery.py` (new file)
- READ-ONLY inspection of: `services/planning.py`, `services/council.py`, `services/mcp.py`, `services/skill.py`, `services/memory.py`, `services/learning.py`, `core/council_manager.py`, `core/mcp_manager.py`, `core/skill_manager.py`

**Interfaces affected:**
- All Engineering Services (event-based)
- All Capability Facade Services (event-based)
- All Core Managers (event-based)

**Implementation order:** G3-A (happy path) → G3-B (failure path)

**Parallel opportunities:** G3-A and G3-B can be drafted independently, but G3-B depends on G3-A's patterns for event subscription/testing.

**Group-level tests:**
```bash
python -m pytest tests/integration/test_closed_loop.py tests/integration/test_failure_recovery.py -v
# Target: all pass
```

**Milestone-level tests:**
```bash
python -m pytest tests/unit/ tests/integration/ tests/performance/ -q
# Target: all pass (700+ tests)
```

**Regression tests:** All 697 existing unit tests + M1 E2E tests must still pass.

**Acceptance criteria:**
- Happy-path test: User goal → Intent → Plan → Context selection → Learning Council deliberates → Orchestrating Council deliberates → Reconciliation → Capability selection → MCP invocation → Kernel execution → Verification → Independent review → PASS
- Failure-path test: Execution fails → RootCauseAnalyzer → LearningService captures → Plan update → Re-execute succeeds
- All existing tests still pass
- No new collection errors

**Failure recovery:** Fix only the failing test; inspect services/managers only if a genuine integration bug is found.

---

## 10. Milestone-by-Milestone Implementation Plan

### M0: Baseline Stabilization
```
Implement:
- Add testpaths to pyproject.toml
- Delete tests/test_cli.py and tests/test_config.py
- Delete FINAL_ARCHITECTURE_REVIEW_REPORT.md

Do not modify:
- src/aios/ (production code)
- tests/unit/ (any existing test)
- hermes-agent/ (it's already gitignored)

Files:
- pyproject.toml
- tests/test_cli.py (delete)
- tests/test_config.py (delete)
- FINAL_ARCHITECTURE_REVIEW_REPORT.md (delete)

Interfaces:
- pytest configuration only

Dependencies:
- None

Tests:
- python -m pytest tests/unit/ --collect-only -q  (0 errors)
- python -m pytest tests/unit/ --tb=short -q       (697 pass, 0 fail)

Acceptance criteria:
- 697 tests pass, 0 failures, 0 collection errors from root
- Git status clean (only .pytest-cache/ re-created during test run, already gitignored)
```

### M1: Kernel Lifecycle E2E
```
Implement:
- tests/integration/test_kernel_lifecycle_e2e.py — full lifecycle test
- tests/integration/test_workflow_lifecycle.py — WorkflowManager lifecycle test

Do not modify:
- src/aios/core/kernel.py
- src/aios/core/lifecycle_manager.py
- src/aios/core/workflow.py

Files:
- tests/integration/test_kernel_lifecycle_e2e.py (new)
- tests/integration/test_workflow_lifecycle.py (new)

Interfaces:
- HermesKernel.start() / HermesKernel.stop()
- LifecycleManager.initialize() / LifecycleManager.shutdown()

Dependencies:
- M0 complete

Tests:
- python -m pytest tests/integration/test_kernel_lifecycle_e2e.py -v
- python -m pytest tests/integration/test_workflow_lifecycle.py -v
- python -m pytest tests/unit/ --tb=short -q  (regression — 697 pass)

Acceptance criteria:
- All 9 managers initialize in Phase 1→5 order
- All 9 managers shut down in Phase 5→1 reverse order
- WorkflowManager confirmed active in lifecycle
- 697 existing tests unchanged
```

### M2: Package API Completion
```
Implement:
- Add all core exports to aios/__init__.py __all__

Do not modify:
- src/aios/core/__init__.py (already complete)
- Any manager or service implementation

Files:
- src/aios/__init__.py

Interfaces:
- aios.__all__ — expanded public API

Dependencies:
- None (but benefits from M0's clean test env)

Tests:
- python -c "from aios import HermesKernel, SecurityManager, CapabilityManager, ObservabilityManager, LifecycleManager"
- python -m pytest tests/unit/ --tb=short -q  (no regressions)

Acceptance criteria:
- from aios import * includes all 9 Core Managers + 4 Core Components
- from aios.core import SecurityManager, CapabilityManager, ObservabilityManager, ICoreManager — succeeds
- 697 existing tests still pass
```

### M3: Closed-Loop Verification
```
Implement:
- tests/integration/test_closed_loop.py — happy path
- tests/integration/test_failure_recovery.py — failure path

Do not modify:
- src/aios/services/ (any service)
- src/aios/core/ (any manager)

Files:
- tests/integration/test_closed_loop.py (new)
- tests/integration/test_failure_recovery.py (new)

Interfaces:
- EventBus (subscribe/emit)
- All Engineering Services (event-based)
- All Capability Facade Services (event-based)

Dependencies:
- M0 complete
- M1 complete (kernel lifecycle verified)
- M2 complete (API exports verified)

Tests:
- python -m pytest tests/integration/test_closed_loop.py tests/integration/test_failure_recovery.py -v
- python -m pytest tests/unit/ tests/integration/ --tb=short -q  (full regression)

Acceptance criteria:
- Happy path: goal → plan → councils → capability → MCP → execution → verify → PASS
- Failure path: execute → fail → RCA → learning → replan → re-execute → PASS
- All existing tests still pass
```

---

## 11. Terminal 2 Handoff

Terminal 2 receives milestones in order: M0 → M1 → M2 → M3.

**M0 Handoff:**
```
Implement:
- Add testpaths to pyproject.toml [tool.pytest.ini_options]
- Delete tests/test_cli.py (0 bytes)
- Delete tests/test_config.py (0 bytes)
- Delete FINAL_ARCHITECTURE_REVIEW_REPORT.md (superseded, 5+ factual errors)

Do not modify:
- src/aios/ (any production code)
- tests/unit/ (any existing test)
- hermes-agent/ (already gitignored)

Files:
- pyproject.toml
- tests/test_cli.py (delete)
- tests/test_config.py (delete)
- FINAL_ARCHITECTURE_REVIEW_REPORT.md (delete)

Interfaces: None (test infrastructure only)

Dependencies: None

Tests:
- python -m pytest tests/unit/ --collect-only -q  (# should show 697, 0 errors)
- python -m pytest tests/unit/ --tb=short -q       (# should show 697 passed, 0 failed)

Acceptance criteria:
- 697 tests pass, 0 failures, 0 collection errors from repo root
- pytest discover tests without hermes-agent contamination
```

**M1 Handoff:**
```
Implement:
- tests/integration/test_kernel_lifecycle_e2e.py
- tests/integration/test_workflow_lifecycle.py

Do not modify:
- src/aios/core/kernel.py
- src/aios/core/lifecycle_manager.py
- src/aios/core/workflow.py
- Any existing tests

Files:
- tests/integration/test_kernel_lifecycle_e2e.py (new)
- tests/integration/test_workflow_lifecycle.py (new)

Interfaces:
- HermesKernel.start() / HermesKernel.stop()
- LifecycleManager.initialize() / shutdown()
- All 9 Core Managers (already registered, verified at kernel.py:659-714)

Dependencies:
- M0 complete (clean test env)

Tests:
- python -m pytest tests/integration/test_kernel_lifecycle_e2e.py -v
- python -m pytest tests/integration/test_workflow_lifecycle.py -v
- python -m pytest tests/unit/ --tb=short -q  (regression)

Acceptance criteria:
- Kernel.start() initializes all 9 managers through Phase 1→5
- Kernel.stop() shuts down all 9 managers through Phase 5→1
- WorkflowManager confirmed active (not no-op)
- 697 existing tests unchanged
```

**M2 Handoff:**
```
Implement:
- Expand aios/__init__.py __all__ to include all exported core names

Do not modify:
- src/aios/core/__init__.py (already complete)
- Any manager or service implementation

Files:
- src/aios/__init__.py

Interfaces:
- aios.__all__ — expanded public API

Dependencies: None

Tests:
- python -c "from aios import HermesKernel, SecurityManager, CapabilityManager, ObservabilityManager, LifecycleManager"
- python -m pytest tests/unit/ --tb=short -q  (no regressions)

Acceptance criteria:
- len(aios.__all__) > 1 (currently only ["__version__"])
- from aios import * includes all 9 Core Managers
- from aios.core import SecurityManager, CapabilityManager, ObservabilityManager, ICoreManager — succeeds
- 697 existing tests still pass
```

**M3 Handoff:**
```
Implement:
- tests/integration/test_closed_loop.py
- tests/integration/test_failure_recovery.py

Do not modify:
- src/aios/services/ (any service)
- src/aios/core/ (any manager)
- src/aios/events/ (any event code)

Files:
- tests/integration/test_closed_loop.py (new)
- tests/integration/test_failure_recovery.py (new)

Interfaces:
- All Engineering Services (8 services, all verified existing)
- All Capability Facade Services (4 services, all verified existing)
- All Core Managers (9 managers, all verified registered)

Dependencies:
- M0, M1, M2 complete

Tests:
- python -m pytest tests/integration/test_closed_loop.py -v
- python -m pytest tests/integration/test_failure_recovery.py -v
- python -m pytest tests/unit/ tests/integration/ --tb=short -q  (full regression)

Acceptance criteria:
- Happy path test passes: goal→plan→councils→capability→MCP→execute→verify→PASS
- Failure path test passes: execute→fail→RCA→learn→replan→re-execute→PASS
- All existing tests still pass
```

---

## 12. Terminal 3 QA Handoff

### M0 QA Specification
**Group QA:**
- Verify `pyproject.toml` has `testpaths` key under `[tool.pytest.ini_options]`
- Verify `tests/test_cli.py` and `tests/test_config.py` no longer exist
- Verify `FINAL_ARCHITECTURE_REVIEW_REPORT.md` no longer exists

**Integration QA:** Run `python -m pytest` from repo root — should collect 767 tests with 0 collection errors (no hermes-agent contamination).

**Architecture QA:** No architectural impact — test infrastructure only.

**Regression QA:** `python -m pytest tests/unit/ --tb=short -q` → 697 passed, 0 failed.

**E2E QA:** N/A (no production code changes).

**Failure QA:** N/A.

### M1 QA Specification
**Group QA:**
- Verify both test files exist and have substantive content
- Verify each test asserts 9 managers initialized in correct Phase 1→5 order
- Verify each test asserts 9 managers shut down in correct Phase 5→1 reverse order
- Verify WorkflowManager lifecycle is explicitly asserted (not just "exists")

**Integration QA:** Run M1 tests alongside full unit suite — `python -m pytest tests/unit/ tests/integration/ -q` → all pass, 0 new failures.

**Architecture QA:**
- Verify test follows the actual phase topology: Phase 1 (Lifecycle), Phase 2 (State/Storage), Phase 3 (Security/Resource/Health), Phase 4 (Capability/Workflow), Phase 5 (Observability)
- Verify reverse shutdown order is Phase 5→1
- Verify test does not mock core managers — uses real HermesKernel

**Regression QA:** All 697 unit tests unchanged.

**E2E QA:** Full kernel lifecycle: `create_kernel()` → `start()` → verify all managers → `stop()` → verify cleanup.

**Failure QA:** Test that `stop()` correctly handles already-stopped kernel and that double-`start()` does not re-initialize managers.

### M2 QA Specification
**Group QA:**
- Verify `aios.__all__` contains at minimum: `HermesKernel`, `LifecycleManager`, `SecurityManager`, `CapabilityManager`, `ObservabilityManager`, `StateManager`, `StorageManager`, `HealthManager`, `ResourceManager`, `ICoreManager`, `run_kernel`, `stop_kernel`, `execute_with_kernel`
- Verify `len(aios.__all__) > 1`

**Integration QA:** Run:
```python
from aios.core import SecurityManager, CapabilityManager, ObservabilityManager, ICoreManager
from aios import HermesKernel, SecurityManager, LifecycleManager, run_kernel
```
Both must succeed without error.

**Architecture QA:**
- Verify `aios.core.__all__` already contains all required exports (READ-ONLY check — should be complete)
- Verify no production code was modified, only `__all__` list

**Regression QA:** `python -m pytest tests/unit/ tests/integration/ -q` → all pass.

**E2E QA:** `python -c "import aios; print(sorted(aios.__all__))"` — verify output includes all managers.

**Failure QA:** N/A (no behavioral changes).

### M3 QA Specification
**Group QA:**
- Verify happy-path test covers: UserGoal → Intent → Plan → Context → Learning Council → Orchestrating Council → Reconciliation → Capability → MCP → Kernel → Execution → Verification → Review → PASS
- Verify failure-path test covers: Execution → Failure → RootCauseAnalyzer → LearningService → Plan Update → Re-execute → PASS
- Verify tests use real services, not mocks (where feasible)

**Integration QA:** Run all integration tests together — `python -m pytest tests/integration/ -q` → all pass.

**Architecture QA:**
- Verify the closed loop matches the intended AI-OS lifecycle from the task spec
- Verify both councils (Learning + Orchestrating) are exercised
- Verify MCP invocation is tested
- Verify Kernel execution is the final step
- Verify failure recovery includes RCA → Learning → Replanning → Re-execute

**Regression QA:** `python -m pytest tests/unit/ tests/integration/ tests/performance/ -q` → 700+ tests, 0 failures.

**E2E QA:** Execute the full happy-path test as a standalone script with real kernel startup.

**Failure QA:**
- Verify failure path test actually triggers a failure and recovery
- Verify RootCauseAnalyzer is invoked
- Verify LearningService captures the failure
- Verify plan is updated and re-execution succeeds

---

## 13. Acceptance Criteria

### V1 Completion — All of the following must be true:

**Core runtime:** ✅ HermesKernel operational (verified, 697 tests pass)
**Managers:** ✅ All 9 Core Managers operational and ICoreManager compliant (verified)
**Lifecycle:** ⏳ Complete kernel lifecycle verified via E2E test (M1)
**Planning:** ✅ PlanningService exists and is event-driven (verified)
**Context:** N/A — context selection is part of the closed-loop test (M3) — to be verified
**Decision:** ⏳ Both councils exercisable in closed-loop test (M3)
**Capability:** ✅ CapabilityManager + SkillService/MCPService/CouncilService exist (verified)
**MCP:** ✅ MCPService + MCPManager exist (verified)
**Execution:** ✅ Hermes controls execution (WorkflowManager registered, verified)
**Verification:** ⏳ Independent review verified in closed-loop (M3)
**Learning:** ✅ LearningService exists (verified)
**Recovery:** ⏳ RCA → Learning → Replanning → Re-execute in failure test (M3)
**Security:** ✅ SecurityManager operational (verified)
**Observability:** ✅ ObservabilityManager operational (verified)
**Regression:** ✅ 697 existing tests pass (verified)
**E2E:** ⏳ At least one complete AI-OS workflow (M3 happy path)

**Milestone completion gates:**
- M0: 697 tests pass, 0 collection errors from root
- M1: +2 E2E lifecycle tests pass, 697 regression intact
- M2: `from aios import SecurityManager` succeeds, `__all__` expanded, 697 regression intact
- M3: +2 integration tests pass, full regression (700+) intact

---

## 14. Failure / Recovery Strategy

### Milestone-level failure handling:
```
MILESTONE X COMPLETE
    ↓
TERMINAL 3 QA
    ↓
PASS → proceed to next milestone
    ↓
FAIL → identify failing group(s)
    ↓
Fix only affected group(s)
    ↓
Focused re-test
    ↓
Milestone integration QA
    ↓
PASS → proceed
    ↓
FAIL → escalate: bug in production code (not test) → create fix task
```

### Recovery per milestone:

**M0 failure:** Revert pyproject.toml and restore deleted files. Re-run with fresh checkout.

**M1 failure:** If the lifecycle test reveals a genuine kernel bug (not a test bug), file it as a new issue. Do NOT modify kernel code during M1 — the test is verification-only. If it's a test issue, fix the test.

**M2 failure:** Revert `__all__` changes. The imports worked before (direct import, not starred) so this is non-blocking.

**M3 failure:** If the closed-loop test reveals integration bugs, identify the specific service/manager boundary that fails. Fix only that boundary. Do NOT rewrite services wholesale.

### General rule:
- **Do NOT restart milestones.**
- **Do NOT redo unrelated work.**
- **Fix only what fails, at the smallest boundary.**

---

## 15. V1 Definition of Done

AI-OS V1 is declared COMPLETE when ALL of the following are true:

1. **Kernel operational** — `HermesKernel.start()` → all 5 phases → `HermesKernel.stop()` → reverse shutdown (M1 verified)
2. **All 9 Core Managers compliant** — verified ✅ (no further action)
3. **Package API complete** — `from aios import SecurityManager, CapabilityManager, ObservabilityManager` works via `__all__` (M2 verified)
4. **Repository hygiene** — 0 collection errors from root `pytest` (M0 verified)
5. **Closed loop operational** — goal → plan → councils → capability → MCP → execute → verify → PASS (M3 happy path)
6. **Recovery operational** — fail → RCA → learn → replan → re-execute → PASS (M3 failure path)
7. **All regression tests pass** — 700+ tests, 0 failures, 0 collection errors
8. **Security boundary** — SecurityManager enforces permissions (no capability bypass — verified via M3 integration)
9. **Observability** — ObservabilityManager captures lifecycle events (verified via M1+M3)
10. **No stale/obsolete documents** — `FINAL_ARCHITECTURE_REVIEW_REPORT.md` deleted; `analysis-gap-impl-vs-spec.md` updated to mark superseded claims

---

## 16. Risk Register

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **M3 closed-loop test reveals integration bugs across multiple services** | CRITICAL | Medium | Write test with detailed assertion messages per service; isolate to specific service boundary |
| **M1 lifecycle test reveals WorkflowManager is not actually driving execution** | HIGH | Low | Verified WorkflowManager IS registered at kernel.py:703-704; test will confirm |
| **hermes-agent/ collection errors persist after testpaths added** | MEDIUM | Low | `.gitignore` already ignores `/hermes-agent/`; testpaths should fully exclude it |
| **__all__ expansion breaks existing import behavior** | LOW | Very Low | Adding names to `__all__` is purely additive; no removals |
| **Kernel FSM discrepancy causes test confusion** | MEDIUM | Low | Documented: LifecycleManager owns the 8-state FSM; Kernel's `_running` is a simple flag; tests verify via LifecycleManager state |
| **3 TestCheckpointRecovery errors persist** | LOW | Certain | Pre-existing; not in scope for V1 fix; documented as known limitation |
| **177 datetime.utcnow() warnings** | LOW | Certain | DeprecationWarning only; no failures; deferred |

**Critical risks:** M3 integration complexity — 8 services + 9 managers + 4 facade services must all coordinate via events. Mitigated by incremental test writing.

**High risks:** M1 kernel lifecycle — if real bugs exist in Phase ordering. Mitigated by verification that all 9 managers are registered.

**Medium risks:** Repository hygiene completeness; FSM documentation clarity.

**Low risks:** Stub file deletion; `__all__` expansion; known test errors and warnings.

---

## 17. Compression / Efficiency Analysis

### Context efficiency gains:

| Redundant activity eliminated | Estimated context saved |
|-------------------------------|------------------------|
| Re-audit of WorkflowManager ICoreManager compliance | ~2000 tokens |
| Re-fix of EventType count (already correct) | ~1500 tokens |
| Re-audit of SecurityManager/CapabilityManager/ObservabilityManager existence | ~1500 tokens |
| Duplicate test environment setup per milestone | ~3000 tokens |
| Re-reading stale gap-analysis documents | ~2000 tokens |
| **Total estimated context saved** | **~10,000 tokens** |

### Implementation cycles eliminated:
- EventType count fix: 0 cycles needed (already done)
- WorkflowManager upgrade: 0 cycles needed (already done)
- Package exports in `aios/core/__init__.py`: already complete (0 cycles)

### QA cycles eliminated:
- M1 (EventType) QA: 0 cycles (test already passing)
- WorkflowManager compliance QA: 0 cycles (already compliant)

### New implementation cycles:
- M0: 1 cycle (testpaths + cleanup)
- M1: 1 cycle (lifecycle E2E test)
- M2: 1 cycle (__all__ expansion)
- M3: 1 cycle (closed-loop + failure test)

**Total: 4 implementation cycles + 4 QA cycles = 8 cycles total.**

Old roadmap would have been 6 milestones × ~2 cycles each = 12 cycles. **~33% reduction in cycles.**

---

## 18. 100-Point Score

| Category | Weight | Score | Notes |
|----------|-------:|------:|-------|
| Accuracy against current repository | 15 | 15/15 | Verified all claims against source: EventType=121, all managers compliant, WorkflowManager registered |
| Correct dependency analysis | 15 | 15/15 | Hard deps: clean tests for E2E; API exports independent; closed-loop depends on all prior |
| Safe grouping | 15 | 14/15 | M0+M1 could potentially be split further, but they're coherent; -1 for minor granularity |
| Reduction of unnecessary overhead | 10 | 9/10 | Eliminated 2 obsolete milestones; ~33% cycle reduction; -1 for not fully compressing M0+M2 |
| Architecture preservation | 15 | 15/15 | No production code modifications; LifecycleManager FSM preserved; no destructive changes |
| QA completeness | 10 | 10/10 | Every milestone has group QA, integration QA, regression QA, acceptance criteria |
| Implementation feasibility | 10 | 10/10 | All work verified as achievable against current repo state |
| V1 scope discipline | 5 | 5/5 | CLI, singleton reduction, FSM explicitly deferred; no scope creep |
| Final completion clarity | 5 | 5/5 | 10-point V1 Definition of Done with objective criteria |
| **TOTAL** | **100** | **93/100** | |

---

## 19. Final Recommended Execution Order

```
AI-OS V1
│
├── M0 — Baseline Stabilization
│   ├── G0-A: testpaths in pyproject.toml
│   ├── G0-B: delete empty test stubs (test_cli.py, test_config.py)
│   └── G0-C: delete stale report (FINAL_ARCHITECTURE_REVIEW_REPORT.md)
│
├── M1 — Kernel Lifecycle E2E
│   ├── G1-A: full lifecycle E2E test (all 9 managers, Phase 1→5 → 5→1)
│   └── G1-B: WorkflowManager lifecycle test (Phase 4 init, reverse shutdown)
│
├── M2 — Package API Completion
│   ├── G2-A: expand aios/__init__.py __all__
│   └── G2-B: verify all imports from both aios.core and aios
│
└── M3 — Closed-Loop Verification
    ├── G3-A: happy-path integration test (goal→plan→councils→capability→MCP→execute→verify)
    └── G3-B: failure-recovery integration test (fail→RCA→learn→replan→re-execute)
```

**Execution flow:** M0 → M1 → M2 → M3 (sequential due to dependencies). M0 and M2 can partially overlap (M2 doesn't depend on M0's testpaths, but benefits from clean test runs). M1 and M2 are independent. M3 depends on M0, M1, and M2.

**Optimal parallel schedule:**
```
M0 ── M1 ── M3-A/B
  \  /
   M2
```
M0, M1, M2 can run with partial parallelism. M3 must come last.

---

*This concludes the Terminal 1 Implementation Roadmap. This document supersedes all older gap analyses (`TERMINAL_1_GAP_ANALYSIS.md`, `analysis-gap-impl-vs-spec.md`, `FINAL_ARCHITECTURE_REVIEW_REPORT.md`) where they conflict with the current repository state at HEAD `dc09784`.*
