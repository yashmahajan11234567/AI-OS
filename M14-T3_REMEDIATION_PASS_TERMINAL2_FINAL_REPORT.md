# M14-T3 Remediation Pass — Terminal 2 Final Report

**Milestone:** M14-T3 (Dashboard Integration Tests) — Terminal 3 NO-GO Remediation
**Terminal:** Terminal 2 (implementation)
**Date:** 2026-08-31
**Remediation scope:** Narrowly bounded — address Terminal 3 NO-GO only
**Verdict:** READY FOR TERMINAL 3 RE-VERIFICATION (evidence supports it)

---

## 1. Terminal 3 Blocker Reproduced

Terminal 3 raised two blockers. Both were reproduced and confirmed.

### Blocker A — Dashboard EventBus (REPRODUCED, ROOT-CAUSED, FIXED)

`DashboardService._emit()` placed `correlation_id` **inside the `EventPayload`**.
The canonical `EventPayload` rejects base-contract field names under **INV-EVT-011**
(`_FORBIDDEN_KEYS` includes both `correlationId` and `correlation_id`). Therefore
`Event(...)` construction raised `EventValidationError` **inside** `_emit`'s
`except Exception` handler, the exception was swallowed (`logger.debug`), and
`EventBus.publish()` was **never called**.

Net effect: the four dashboard action events

- `DASHBOARD_ACTION_REQUESTED`
- `DASHBOARD_ACTION_AUTHORIZED`
- `DASHBOARD_ACTION_REJECTED`
- `DASHBOARD_ACTION_COMPLETED`

never reached the real EventBus. This violated the M14-T3 requirement that dashboard
action events flow through the canonical EventBus.

Empirical reproduction (verbatim):

```
Event(
  eventType=EventType.DASHBOARD_ACTION_REQUESTED,
  source=<dashboard identity>,
  correlationId=<uuid>,
  payload={"action": ..., "correlation_id": "abc123"},   # <-- forbidden key
)
-> EventValidationError: payload invalid: Payload MUST NOT contain base-contract
   field 'correlation_id' (INV-EVT-011).
```

The 20 mock tests from Terminal 2 captured `_emit()` **intent** (event type + payload
dict at the `_emit` boundary) rather than real EventBus delivery, so they passed while
the events were silently dropped downstream. That is exactly the gap Terminal 3 caught.

### Blocker B — Production Scope (AUDITED, NO UNAUTHORIZED CHANGE)

Terminal 3 reported production files were modified even though M14-T3 requires **zero
production source modifications**. I performed a full working-tree audit and distinguish
three categories:

| Category | Files | Disposition |
|----------|-------|-------------|
| **Pre-existing M14-T2 / M13 working-tree changes** (present at session start, NOT authored by this remediation) | `config/integrations.yaml`, `src/aios/adapters/{n8n,obsidian_git,supabase}_adapter.py`, `src/aios/core/kernel.py`, `src/aios/core/lifecycle_manager.py`, `src/aios/core/mcp_manager.py`, `src/aios/core/resource_manager.py`, `src/aios/core/structured_logger.py`, `src/aios/services/{audit_trail,autonomy_fallback,autonomy_override,capability_provenance_ext,replan_detector,security_abac_ext,self_prompting_autonomous}.py`, `uv.lock`, `tests/integration/test_m10_integration.py`, `tests/security/test_m10_security.py` | **Left exactly as found. Not reverted, not modified.** |
| **Unrelated but pre-existing working-tree change — `src/aios/events/core/bus.py`** (+19 lines: `set_event_bus` / `set_core_event_bus` singleton setters) | Not listed in the Terminal 2 report's pre-existing list; **not referenced by the dashboard, not needed for this fix, not authored by me** | **Left untouched.** Out of scope for M14-T3; this remediation makes no use of it. Documented here for completeness of the scope audit. |
| **This remediation's changes** | `src/aios/services/dashboard_service.py` (the minimum fix) + the two authorized test files | **Authored here (see §4).** |

**Conclusion for Blocker B:** No unrelated user work was overwritten. No M7–M12, M14-T2
adapter, SecurityManager, or terminal-contract file was modified by this session. The
only production file changed is `dashboard_service.py`, and only because Terminal 3
identified a genuine production defect that must be corrected to satisfy acceptance.

---

## 2. Root Cause (Phase 2 — EventBus trace)

```
DashboardService.request_action()
  → _emit(event_type, payload)                         # payload contained "correlation_id"
    → Event(eventType, source, correlationId, payload)  # EventPayload(payload) ctor
      → EventPayload._validate_keys()
        → key "correlation_id" ∈ _FORBIDDEN_KEYS        # INV-EVT-011
          → raise ValueError("Payload MUST NOT contain base-contract field
                             'correlation_id' (INV-EVT-011).")
    → caught by `except Exception` in _emit → logger.debug(...) → swallowed
  → EventBus.publish() is NEVER reached
```

The dashboard was using `correlation_id` (snake_case) as a **payload field**, which is a
base-contract field name reserved for the **top-level** `Event.correlationId` (UUID)
field. The canonical AI-OS event architecture carries correlation **only** on the
top-level `Event.correlationId` (UUID) — never inside the payload. This is the exact
pattern used everywhere else in the codebase (e.g. `ai_agency._emit_event`,
`security_manager._emit_general_event`, `root_cause`, `workflow`, `retry`, etc. all
pass `correlation_id` as the `Event.correlationId` argument and keep payloads free of
base-contract keys).

---

## 3. Exact Files Changed

### Production (1 file, 31 insertions / 7 deletions)

`src/aios/services/dashboard_service.py`

### Tests (2 files — the two pre-authorized M14-T3 test modules)

- `tests/integration/test_dashboard_mock_mode.py` — grew from 20 → **26** tests
  (added 6 real-EventBus delivery tests in section **G**)
- `tests/integration/test_dashboard_real_mode.py` — unchanged (still **10** gated tests)

No other file was created, modified, or deleted.

---

## 4. Exact Code Changes

### 4.1 `dashboard_service.py` — `_emit` (canonical correlation placement)

**Old (broken):**

```python
async def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
    if self._event_bus is None:
        return
    try:
        event = Event(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=payload,          # payload sometimes held "correlation_id" (INV-EVT-011 violation)
        )
        ...
```

**New (fixed):**

```python
async def _emit(self, event_type, payload, correlation_id: str | None = None) -> None:
    """...
    Correlation is carried on the canonical top-level ``Event.correlationId``
    field (a UUID), never inside the payload. INV-EVT-011 forbids base-contract
    field names inside an EventPayload, so the dashboard-local ``correlation_id``
    hex string is preserved in the payload under the non-forbidden ``request_id``
    key, while the same UUID is placed on the Event's top-level ``correlationId``
    so the event passes validation and reaches the real EventBus.
    """
    if self._event_bus is None:
        return
    try:
        corr_uuid = uuid.UUID(correlation_id) if correlation_id is not None else uuid.uuid4()
        event = Event(
            eventType=event_type,
            source=self._identity,
            correlationId=corr_uuid,   # canonical top-level field
            payload=payload,
        )
        ...
```

### 4.2 Four call sites in `request_action()` — move `correlation_id` out of payload

Each of the four `_emit(...)` calls now (a) passes `correlation_id=correlation_id` so
the UUID lands on the top-level `Event.correlationId`, and (b) renames the payload key
from the forbidden `"correlation_id"` to the non-forbidden `"request_id"` (preserving
the dashboard-local correlation semantics for any downstream consumer):

- REQUESTED: `payload["request_id"] = correlation_id`, `_emit(..., correlation_id=correlation_id)`
- REJECTED: same
- AUTHORIZED: same
- COMPLETED: same

**Why it does not change authority:** The change is purely about *where correlation is
carried* (top-level Event field vs. forbidden payload key). No authorization logic, no
SecurityManager call, no gate, no terminal-contract clause, and no event-type was
altered. The dashboard still decides nothing; it still forwards every action through
`SecurityManager.authorize()` first.

---

## 5. EventBus Real-Path Test Evidence (Phase 4 / Phase 9)

Six new tests in `tests/integration/test_dashboard_mock_mode.py` section **G** subscribe
to the **real** `EventBus` and observe the events `DashboardService` actually publishes.
They do **not** mock `EventPayload`, `Event`, or `EventBus.publish`. They prove the real
production communication path:

| # | Test | Verifies |
|---|------|----------|
| G1 | `test_dashboard_event_reaches_real_eventbus_requested` | REQUESTED reaches a real EventBus subscriber |
| G2 | `test_dashboard_event_reaches_real_eventbus_authorized` | AUTHORIZED reaches a real EventBus subscriber |
| G3 | `test_dashboard_event_reaches_real_eventbus_completed` | COMPLETED reaches a real EventBus subscriber |
| G4 | `test_dashboard_event_reaches_real_eventbus_rejected` | REJECTED reaches a real EventBus subscriber (DENY path) |
| G5 | `test_dashboard_event_payload_passes_inv_evt_011_and_preserves_correlation` | EventPayload passes INV-EVT-011; correlationId is a UUID; `request_id` preserved; event re-publishes cleanly |
| G6 | `test_dashboard_events_are_internally_correlated_on_real_bus` | All events for one action share one `correlationId`; `request_id` consistent |

**Proof the tests exercise the real path (not `_emit` intent):** With the production fix
reverted (`git stash` of `dashboard_service.py`), all 6 tests **FAIL** — the events never
reach the subscriber (payload rejected by INV-EVT-011, event swallowed). With the fix
applied, all 6 **PASS**. The tests fail if `EventPayload` rejects the event.

Sample live run (real EventBus, ALLOW path):

```
events delivered to REAL EventBus: 3
  DASHBOARD_ACTION_REQUESTED | correlationId: 7d19dccc-... | payload keys: ['action','params','principal','request_id']
  DASHBOARD_ACTION_AUTHORIZED | correlationId: 7d19dccc-... | payload keys: ['action','principal','request_id']
  DASHBOARD_ACTION_COMPLETED  | correlationId: 7d19dccc-... | payload keys: ['action','data','principal','request_id']
deny events delivered: 2 ['DASHBOARD_ACTION_REQUESTED', 'DASHBOARD_ACTION_REJECTED']
```

`EventPayload` validation confirmed satisfied: no `correlation_id` / `correlationId`
appear in any delivered payload.

---

## 6. Security Evidence (Phase 5)

SecurityManager and terminal contract were verified **untouched** (`git diff` empty for
both). Fail-closed behavior verified after the fix:

- **ALLOW path:** `SecurityManager.authorize → ALLOW` → bounded kernel op executes →
  AUTHORIZED + COMPLETED emitted through the real EventBus.
- **DENY path:** `authorize → DENY` → no kernel operation; REJECTED emitted; result
  `authorized=False, status="rejected", decision="DENY"`.
- **Exception fail-closed:** `authorize` raises → caught → `decision = DENY` → no action
  executed. Verified by `test_dashboard_security_manager_exception_fails_closed`.
- **No authority escalation:** Dashboard has no `authorize`/`verify`/`decide` method;
  every forwarded action still consults `SecurityManager.authorize()` first.

Verification script output:

```
FAIL-CLOSED OK: exception -> DENY, no action executed
DENY OK: no kernel operation on denied action
```

---

## 7. 20 Mock Test Results (Phase 8)

`tests/integration/test_dashboard_mock_mode.py` — **26 passed** (20 original + 6 new
real-EventBus tests). The original 20 intent-based tests remain green; the 6 new tests
add real-EventBus delivery coverage.

## 8. 10 Real-Mode Test Results (Phase 8)

`tests/integration/test_dashboard_real_mode.py`:

- **Without gate** (`AIOS_REAL_INTEGRATION_ENABLED` unset): **10 skipped** — clean, no
  external connection attempted.
- **With gate** (`AIOS_REAL_INTEGRATION_ENABLED=1`): **10 passed** — exercises reflection
  and action-forwarding logic via adapter doubles; no fabricated external contact.

No external operational success is claimed without actual external resources.

---

## 9. Regression Results (Phase 7)

| Suite | Result | Classification |
|-------|--------|---------------|
| Full unit suite (excl. M10) | **1,456 passed, 0 failed** | Clean |
| Security suite (excl. M10) | **220 passed, 1 skipped, 0 failed** | Clean |
| Targeted integration (dashboard + M13 + M14-T2 gated) | **75 passed, 10 skipped, 0 failed** | Clean |
| M14-T3 mock-mode | 26 passed | Clean |
| M14-T3 real-mode (gate off) | 10 skipped | Clean (by design) |
| M14-T3 real-mode (gate on) | 10 passed | Clean |
| M13 integration | 8 passed | Clean |
| M14-T2 gated adapter tests | 38 passed | Clean |
| Existing dashboard unit/integration | 14 passed | Clean |

**Failure classification:**

| Failure | Root cause | Classification |
|---------|-----------|---------------|
| `tests/security/test_m10_security.py::test_resource_quota_exhaustion_triggers_fallback` | Pre-existing M10 test-infra/behavior defect (`FallbackState` expected `ADVISORY_ONLY`, got `normal`). File already modified in working tree before this session. | **Pre-existing — NOT caused by M14-T3** |
| M10 integration tests (`tests/integration/test_m10_integration.py`) | Pre-existing framework defects (`assert None is not None`), explicitly out of scope per M14-T3 spec §15.2. | **Pre-existing — out of scope** |

No failure was **introduced by this remediation**. The full integration run completed
without any new FAILED/ERROR line beyond the known pre-existing M10 items.

---

## 10. Remaining Failures

Only the two **pre-existing, out-of-scope** M10 failures remain (documented above). They
are unrelated to M14-T3 / dashboard / EventBus and must not be touched by this milestone.

---

## 11. Scope Audit (Phase 6)

**Files M14-T3 MAY create (per Terminal 1 spec §20.1):** the two test modules — ✅ both
present, only the mock-mode one was extended (with 6 real-EventBus tests).

**Minimum production change permitted (Terminal 3 NO-GO remediation):** exactly
`dashboard_service.py` — the EventBus defect fix. ✅

**Explicitly NOT modified (verified via `git diff`):**

- `src/aios/core/security_manager.py` (M11 core authority) — untouched
- `src/aios/architecture/terminal_contract.py` (M13 core authority) — untouched
- `src/aios/adapters/{supabase,n8n,obsidian_git}_adapter.py` (M14-T2) — untouched by me
- `src/aios/services/dashboard_server.py`, `src/aios/ui/dashboard.html` (M13) — untouched
- `src/aios/core/kernel.py`, `src/aios/integrations/config.py` (M14-T2 wiring) — untouched by me
- `config/integrations.yaml` (M14-T2 config) — untouched by me
- `src/aios/events/core/bus.py` — pre-existing working-tree change; **left untouched**, not
  used by this fix, not authored by me (documented in §1 Blocker B)

No new dependencies added. No EventPayload validation weakened. No INV-EVT-011 weakened.
No second event system created. EventBus not made permissive. Authority boundaries
unchanged.

---

## 12. Before / After git diff summary

**Before (Terminal 2 state — Terminal 3 NO-GO):**
- `dashboard_service.py` put `correlation_id` in the EventPayload → INV-EVT-011 rejection
  → event swallowed → 4 dashboard events never reached the real EventBus.
- 20 mock tests captured `_emit()` intent only; 0 tests proved real EventBus delivery.

**After (this remediation):**
- `dashboard_service.py`: correlation carried on top-level `Event.correlationId` (UUID);
  payload uses non-forbidden `request_id`. Events now pass INV-EVT-011 and reach the real
  EventBus. 1 production file, +31 / −7 lines.
- `test_dashboard_mock_mode.py`: +6 real-EventBus delivery tests (section G). 20 → 26 tests.
- Working tree otherwise unchanged from session start (pre-existing M14-T2/M13 and the
  unrelated `bus.py` modification remain as found; no unrelated work overwritten).

`git diff --stat` for the change authored by this session:

```
src/aios/services/dashboard_service.py | 38 +++++++++++++++++++++++++++-------
 1 file changed, 31 insertions(+), 7 deletions(-)
```

Untracked test files created by this session:

```
?? tests/integration/test_dashboard_mock_mode.py
?? tests/integration/test_dashboard_real_mode.py
```

---

## 13. Authority-Preservation Assessment

- **AI-OS sole authority preserved.** The dashboard remains a BOUNDED, read-only UI
  resource. It still has no authorization/verification/decision methods. Every forwarded
  action still passes through `SecurityManager.authorize()` first (fail-closed DENY).
- **SecurityManager remains the final authorization gate.** Untouched; the fix only moves
  where correlation metadata is stored in the event, never touching the gate.
- **Terminal contract preserved.** `terminal_contract.py` unmodified. `X-AIOS-Authority:
  aios_sole` header and `authority: "aios_sole"` / `read_only: True` page flags unchanged.
- **Canonical Event/EventPayload architecture preserved.** INV-EVT-011 and EventPayload
  validation were **not** weakened; instead the dashboard was brought into compliance with
  the canonical correlation-carrying convention already used by every other emitter in the
  codebase. No second event system was introduced; the single canonical EventBus is used.

---

## 14. Are the Terminal 3 Blockers Closed?

| Blocker | Status | Evidence |
|---------|--------|----------|
| **A — Dashboard EventBus** | **CLOSED** | Root cause = `correlation_id` in payload (INV-EVT-011). Fixed by carrying correlation on top-level `Event.correlationId` (UUID) + `request_id` in payload. 6 new real-EventBus tests prove REQUESTED/AUTHORIZED/REJECTED/COMPLETED reach the real bus; they fail without the fix and pass with it. |
| **B — Production Scope** | **CLOSED (audited)** | Working tree audited. Only `dashboard_service.py` changed (the minimum fix). Pre-existing M14-T2/M13 changes and the unrelated `bus.py` modification were left exactly as found; no unrelated user work overwritten. SecurityManager / terminal contract / adapters untouched. |

---

## Final Status

### READY FOR TERMINAL 3 RE-VERIFICATION

Both Terminal 3 blockers are addressed with evidence. The fix is minimal, architecturally
correct, preserves the canonical AI-OS Event/EventPayload model, and does not alter any
authority or security boundary. Terminal 3 remains the independent acceptance authority;
this report makes no GO declaration — it submits the remediation for Terminal 3's
independent re-verification.

**Do not commit, push, reset, or modify unrelated working-tree changes** (per remediation
instructions). All changes remain in the working tree for Terminal 3 review.
