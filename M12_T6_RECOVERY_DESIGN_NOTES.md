# M12-T6 #53 — Recovery Integration Design Notes (Terminal 2)

## Existing architecture (verified)

1. **`HealthManager` EXISTS** (`src/aios/core/health_manager.py`, Task 12, Phase-3 Governance Core Manager).
   It already: registers checks, `record_health()` updates per-check status +
   `_recompute_overall()` (worst-wins: UNHEALTHY > DEGRADED > HEALTHY > UNKNOWN),
   emits canonical events. It has NO recovery logic and NO LifecycleManager
   reference. Kernel constructs it in `_init_core_components()` and registers it
   with LifecycleManager in `_init_lifecycle_manager()`.

2. **`LifecycleManager`** is the sole lifecycle authority. `begin_recovery()`
   (DEGRADED → RECOVERY_IN_PROGRESS) and `complete_recovery()` (RECOVERY_IN_PROGRESS →
   OPERATIONAL/DEGRADED) are state-transition helpers only, invoked only from
   `tests/unit/test_lifecycle_manager.py`. `mark_degraded()` (OPERATIONAL|RECOVERY_IN_PROGRESS → DEGRADED) is likewise production-uninvoked.

3. **`HermesKernel`** (`src/aios/core/kernel.py`):
   - `health_state` / `_compute_canonical_health_state()` READ health + lifecycle, but
     never drive recovery. `RECOVERY_IN_PROGRESS` maps to canonical DEGRADED (read-only).
   - `_heartbeat_loop()` calls `_update_health_state()` every 30s — a real production
     periodic execution path.
   - `_start_services()` starts engineering services from the canonical registry
     (`engineering.<name>` id convention). Failures recorded, skipped.

4. **Existing recovery scopes to PRESERVE (do not merge):**
   - `M10RecoveryManager` — M10 autonomy-service (N1–N12) recovery; circuit breaker.
   - `FailureRecoveryManager` — bounded external-resource recovery (M13).
   - Kernel lifecycle recovery (#53) = LifecycleManager state machine driven by
     HealthManager — this task.

## Existing primitives to reuse (no invention)

- `HealthManager.record_health()` + `HealthStatus.DEGRADED` — health detection.
- `HealthManager._recompute_overall()` — aggregate worst-wins.
- `LifecycleManager.mark_degraded()`, `begin_recovery()`, `complete_recovery()`.
- ServiceRegistry `update_health()` + `get_registration()` (engineering services).
- BaseService `start()/stop()/on_health_check()` — restart mechanism.
- Canonical EventBus events (HEALTH_CHECK_PASSED/FAILED, CORE_MANAGER_DEGRADED,
  KERNEL_READY) — CONFLICT E.1: no invented EventTypes.

## Design (smallest architecture-consistent mechanism)

### HealthManager gains a `lifecycle_manager` optional dependency (DI, kernel-wired)

- `set_lifecycle_manager_ref(lm)` — set by kernel in `_init_lifecycle_manager()`
  (after both exist). HealthManager does NOT import LifecycleManager globally
  (no circular import; constructor contract unchanged).
- `HealthManager.record_health()` extended: when the recorded status is DEGRADED
  (worst-wins aggregate becomes DEGRADED while lifecycle is OPERATIONAL), it calls
  `lm.mark_degraded(affected=[...])` — production degraded trigger.
- Repeated DEGRADED records while lifecycle already DEGRADED: no re-trigger
  (mark_degraded from DEGRADED is invalid — lifecycle invariant preserved; guard
  on current state).

### HealthManager-driven recovery coordinator: `trigger_recovery()`

Async production entry point on HealthManager (M12-T6 #53):

```
trigger_recovery(affected) ->
  1. requires initialized HealthManager + lifecycle ref (else HealthManagerError — never silently swallow)
  2. requires lifecycle state == DEGRADED (else no-op with log — LM-REC-001 stays authoritative in LifecycleManager)
  3. await lm.begin_recovery(affected)          # RECOVERY_IN_PROGRESS
  4. attempt recovery action via existing AI-OS mechanisms:
     for each affected engineering service in canonical ServiceRegistry:
       - svc.on_health_check() probe; if unhealthy: svc.stop(); svc.start() (existing BaseService restart)
  5. verify: re-probe all affected services on_health_check()
  6. await lm.complete_recovery(success=verified)  # OPERATIONAL | DEGRADED
```

- Recursion guard: if lifecycle is already RECOVERY_IN_PROGRESS when
  `trigger_recovery` is called → no-op (no recursive loops).
- Failure stays explicit: `complete_recovery(success=False)` → DEGRADED; kernel
  canonical health remains DEGRADED (never falsely OPERATIONAL).
- SecurityManager untouched; no capability/authz paths touched (restart of own
  engineering services is kernel-internal authority, same as `_start_services`).

### Kernel production wiring

- `HermesKernel._init_lifecycle_manager()`: after registering HealthManager with
  LifecycleManager, call `hm.set_lifecycle_manager_ref(lm)` — production wiring.
- `HermesKernel.trigger_recovery(affected)` public async API on the kernel
  (runtime authority entry point) that delegates to the HealthManager
  coordinator — so production kernel execution reaches begin/complete_recovery.
  (Runtime authority stays in the kernel; recovery strategy coordination in
  HealthManager; lifecycle transitions in LifecycleManager — 3-authority split
  per Part 4.)

### What we will NOT do

- No new HealthManager, no new lifecycle manager, no second health subsystem.
- No event replay/checkpoints (M10 scope), no external-resource recovery (M13 scope).
- No new EventTypes (CONFLICT E.1); lifecycle emits its canonical mapped events.
- No change to #53 status in the master plan (Terminal 3 decides).
- No modification of ACP/Notion/M8-T1 files; no commit/push.

## Tests (new file `tests/integration/test_m12_t6_recovery_integration.py`)

- Test A: real kernel boot (run_kernel) → record_health(DEGRADED) through the
  production HealthManager singleton → lifecycle becomes DEGRADED via
  mark_degraded (production) → kernel.trigger_recovery() → lifecycle
  RECOVERY_IN_PROGRESS via production path. Assert begin reached through
  production code (state transitions + not calling lm.begin_recovery directly).
- Test B: recovery action (service restart) succeeds → verified →
  complete_recovery(success=True) → OPERATIONAL; canonical health RUNNING path.
- Test C: recovery action fails (unhealthy service that stays unhealthy) →
  complete_recovery(success=False) → DEGRADED; NOT OPERATIONAL; canonical health
  not falsely healthy.
- Test D: no regression — normal boot/shutdown lifecycle still works (existing
  E2E) + healthy record after recovery restores RUNNING canonical state.
