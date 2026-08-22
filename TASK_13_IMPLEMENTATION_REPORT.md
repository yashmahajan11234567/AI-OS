# Task 13 Implementation Report — Terminal 1 Planning Output

**Status**: PLANNING COMPLETE — READY FOR TERMINAL 2

**Task**: Upgrade ResourceManager to Phase-3 (Governance) Core Manager (Part 4 §4.9)

**Verdict**: **READY FOR TERMINAL 2 IMPLEMENTATION** — score 92/100

---

## What Was Done (Terminal 1 Scope)

This is an architecture/implementation planning task. No code was written, no files modified, no commits made. The full analysis is captured in `TASK_13_ARCHITECTURE_REVIEW.md`.

### Repository Inspection Summary

| Area Inspected | Finding |
|---|---|
| `resource_manager.py` | Plain class; no ICoreManager; uses stdlib logging; no EventBus/Registry/CConfig integration |
| `kernel.py` lines 438, 563, 695-699 | Constructs `ResourceManager()` plain (no DI); started via `_start_services()` engineering loop (WRONG); not registered with LifecycleManager |
| `lifecycle_manager.py` lines 286-303 | Phase 3 topology already declares `("SecurityManager", "ResourceManager", "HealthManager")` — no change needed |
| `lifecycle_manager.py` lines 862-865 | `_resolve_phase_managers()` sorts alphabetically at runtime — ordering guaranteed |
| `lifecycle_manager.py` lines 818-832 | LM-DEP-003: `dependencies` must be satisfied; ResourceManger needs only `["LifecycleManager"]` |
| `__init__.py` | Exports ResourceManager but not `reset_resource_manager_singleton` — needs addition |
| `health_manager.py` (Task 12) | GOLDEN TEMPLATE — all patterns to mirror |
| Part 4 §4.9 | 12 sections of ResourceManager spec fully mapped |
| EventType enum | Closed; 5 resource-relevant canonical types available: RESOURCE_ALLOCATED, RESOURCE_RELEASED, RESOURCE_EXHAUSTED, QUOTA_EXCEEDED |
| service_registry.py lines 899-916 | `_validate_namespace()` rejects `kernel.*` — CONFLICT E.1 resolved as `core.resource` |

### Architectural Conflicts Resolved

| Conflict | Resolution |
|---|---|
| E.1: SR id `kernel.resource` vs `kernel.*` reserved | Use `core.resource` (Task 9-12 precedent) |
| E.2: Phase ordering vs spec section | Alphabetical runtime sort in `_resolve_phase_managers()` — no change needed |
| E.3: 10 Part 4 event types vs closed enum | Map 4 to canonical; omit 6 (Resolution A — recommended) |
| E.4: Constructor signature change | Accept `config=None` backward-compat with deprecation warning |
| E.5: Singleton pattern upgrade | Lock-guarded pattern + `reset_resource_manager_singleton()` |

### Files Requiring Changes (Terminal 2)

1. `src/aios/core/resource_manager.py` — primary rewrite (class body, ICoreManager surface, DI, events, singleton)
2. `src/aios/core/__init__.py` — add `reset_resource_manager_singleton` export
3. `src/aios/core/kernel.py` — 4 edits (construction, registration, remove from services, get_stats)

### FORBIDDEN Files (must NOT be modified)

- `src/aios/core/service_registry.py`
- `src/aios/events/core/types.py`
- `src/aios/core/lifecycle_manager.py`

### Test Plan

30-35 tests targeting: ICoreManager protocol (6), init/shutdown (5), singleton (3), SR registration (2), event emission (4), config (3), business methods preserved (10-12), error handling (2-3).

### Reference

`src/aios/core/health_manager.py` (Task 12) is the exact template to follow — every pattern mirrors.

---

## Readiness

**✅ READY FOR TERMINAL 2 IMPLEMENTATION**

The architecture is fully specified. All conflicts are resolved with established precedent. The implementation path is a direct application of the Task 12 HealthManager template with ResourceManager domain semantics. No unknowns remain.

**Handoff document**: `TASK_13_ARCHITECTURE_REVIEW.md` (24 sections, full implementation plan, acceptance criteria, test strategy, risk assessment)
