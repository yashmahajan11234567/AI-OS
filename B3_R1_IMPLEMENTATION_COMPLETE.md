# B3-R1 — COMPLETE EXECUTION APPROVAL BOUNDARY — Terminal 2 Report

**Date:** 2026-09-22  
**Status:** ✅ COMPLETE  
**Scope:** Terminal 2 — IMPLEMENTATION ONLY (no commit, no push)

---

## 1. Objective

Wire `validate_execution_approval()` into the actual production execution path and fix `approve_plan()`/`reject_plan()` to bind approval to the exact plan_id, establishing a complete human-approval boundary at the SelfLoop phase 7→9 gate.

## 2. Changes Made

### src/aios/services/project_service.py
- Added three fields to `Project` dataclass:
  - `approved_plan_id: Optional[str] = None`
  - `approval_timestamp: Optional[str] = None`
  - `plan_rejected: bool = False`
- Fixed `approve_plan()`: validates exact plan_id match, stores `approved_plan_id` + `approval_timestamp`, clears `plan_rejected`
- Fixed `reject_plan()`: validates exact plan_id match, clears `approved_plan_id`, sets `plan_rejected = True`
- Fixed `save_plan()`: invalidates prior approval by clearing `approved_plan_id`, `approval_timestamp`, and `plan_rejected` on plan regeneration (state NOT reverted — stale detection handled by kernel gate)

### src/aios/core/kernel.py
- Rewrote `validate_execution_approval()` with strict exact-plan-binding enforcement:
  1. ProjectService must be available
  2. Project must exist
  3. Project must be in `PLAN_APPROVED` state
  4. Plan must exist
  5. `current_plan.id == approved_plan_id` (stale/replaced detection)
  6. `requested_plan_id == approved_plan_id` (exact binding)
  7. Rejected plan with no new plan → deny

### src/aios/core/self_loop_engine.py
- `execute_cycle()`: After planning phases complete, attaches `cycle._project_id = project_id` before emitting pause events
- `resume()`: Added `validate_execution_approval()` call before allowing resume past approval boundary. If validation fails, emits `SELF_LOOP_EXECUTION_DENIED` and stays paused

### tests/unit/test_self_loop_engine.py
- Updated `test_mock_cycle_execution`: Asserts `PAUSED` state, 7 cognition phases completed, no `BOUNDED_EXECUTION`
- Renamed `test_self_prompt_generated_in_cycle` → `test_self_prompt_not_generated_without_approval`: Asserts `self_prompt is None`, state is `PAUSED`
- Added `test_execution_denied_without_approval`: Verifies pause without auto-approve
- Added `test_resume_requires_valid_approval`: With kernel mock denying approval, verifies resume stays paused

### tests/unit/test_b3_human_approval_gate.py
- Added `TestExactPlanBinding` class (6 tests):
  - `test_approve_plan_stores_plan_id`
  - `test_approve_wrong_plan_id_denied`
  - `test_reject_clears_approval`
  - `test_save_plan_invalidates_prior_approval`
  - `test_execute_with_wrong_project_denied`
  - `test_execute_with_replaced_plan_denied`
- Added `TestKernelExecutionGate` class (6 tests):
  - `test_kernel_has_validate_execution_approval`
  - `test_execution_denied_no_project_service`
  - `test_execution_denied_no_project`
  - `test_execution_denied_not_approved`
  - `test_execution_allowed_with_valid_approval`
  - `test_selfloop_resume_calls_validation`

## 3. Test Results

| Suite | Passed | Failed | Errors |
|-------|--------|--------|--------|
| test_b3_human_approval_gate.py | 12 | 0 | 0 |
| test_self_loop_engine.py | 22 | 0 | 0 |
| test_dashboard_service.py | 23 | 0 | 0 |
| test_event_type.py | 13 | 0 | 0 |
| test_state_manager.py (B2 regression) | 10 | 0 | 0 |
| **TOTAL** | **80** | **0** | **0** |

Full B2 regression (test_state_manager.py + test_model_router_dispatch.py): 41 passed, 1 pre-existing failure, 5 pre-existing errors — all unchanged from before B3-R1 changes.

## 4. Invariants Enforced

| Invariant | Status |
|-----------|--------|
| INV-B3-1: Planning does NOT auto-authorize | ✅ |
| INV-B3-2: Project enters PLAN_AWAITING_HUMAN_APPROVAL | ✅ |
| INV-B3-3: Explicit human approval required | ✅ |
| INV-B3-4: Approval passes through SecurityManager | ✅ |
| INV-B3-5: Valid approval transitions to PLAN_APPROVED | ✅ |
| INV-B3-6: Execution without approval denied | ✅ |
| INV-B3-7: Execution with valid approval succeeds | ✅ |
| INV-B3-8: Wrong project approval denied | ✅ |
| INV-B3-9: Wrong/stale plan approval denied | ✅ |
| INV-B3-10: Rejected plan cannot execute | ✅ |
| INV-B3-11: SelfLoop cannot auto-approve | ✅ |
| INV-B3-12: Dashboard merely forwards approval | ✅ |
| INV-B3-13: validate_execution_approval() is production gate | ✅ |
| Plan regeneration invalidates prior approval | ✅ |
| Project isolation enforced | ✅ |

## 5. Pre-existing Failures (Unchanged)

- `test_model_router_dispatch.py::test_disabled_provider_not_dispatched_via_registry` — 1 failed (pre-existing)
- `test_model_router_dispatch.py` — 5 errors (pre-existing, EventBus init issues)
- These are unrelated to B3-R1 changes

## 6. Constraints Verified

- ✅ Did NOT expand into B4
- ✅ Did NOT introduce new state machines
- ✅ Preserved all existing authority boundaries
- ✅ No commit made
- ✅ No push made

## 7. FINAL STATUS

**B3-R1 IMPLEMENTATION: COMPLETE**

All 80 B3-R1 + regression tests pass. Zero new failures introduced. All 14 invariants (INV-B3-1 through INV-B3-13 + plan regeneration invalidation) enforced and tested.
