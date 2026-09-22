# AI-OS v1.0.0 — Terminal 1 First Controlled Project Audit Report

**Auditor:** Terminal 1 (Independent QA)
**Date:** 2026-09-15
**Scope:** PRE-EXECUTION AUDIT ONLY — READ-ONLY. No files modified.

---

## A. Readiness Summary

**NOT READY.**

The AI-OS codebase has all infrastructure components in place (DashboardService,
ProjectService, DashboardHTTPServer, SecurityManager, ObsidianGit adapter,
Dashboard UI). However, a **critical gap** prevents the first controlled
project from executing through the Dashboard → Project Workspace path:

> **No SecurityManager allow-rules are registered for any dashboard action.**

The SecurityManager's `authorize()` method is fail-closed (CC-SEC-001):
`SecurityDecision.DENY` is returned unless an explicit allow-rule is
registered via `register_allow_rule()`. Searches across the entire `src/aios/`
tree confirm that `register_allow_rule` is **defined** but **never called**.
The `_allow_rules` set is initialized empty (line 1078) and never populated.

Consequently, every `POST /api/action` with `action: "project.create"`,
`"project.transition"`, `"project.publish_notion"`, `"project.clear_action"`,
or any other action — whether from the Dashboard UI or a manual curl
request — will receive `SecurityDecision.DENY` at Gate 1 in
`DashboardService.request_action()` (line 680-697), and the action will be
rejected before `_execute_bounded_action` is ever called.

The project creation path is **architecturally complete** but
**operationally blocked** by the fail-closed security gate having no allow
rules.

| Component | Status |
|---|---|
| ProjectState lifecycle graph | ✅ All 13 states + transition graph implemented in `project_service.py:64-90` |
| ProjectService lifecycle methods (`start`/`stop`) | ✅ Added in uncommitted diff (fixes `AttributeError` at kernel boot) |
| DashboardService → ProjectService wiring | ✅ `_init_project_service()` at `kernel.py:2864`, wired to DashboardService at line 2916 |
| DashboardHTTPServer routes | ✅ `GET /api/pages`, `POST /api/action` at `dashboard_server.py` |
| Dashboard UI | ✅ `dashboard.html` with project create, transition, Notion handoff buttons |
| SecurityManager fail-closed gate | ✅ `authorize()` at `security_manager.py:1341` |
| **Allow-rules registered for dashboard actions** | ❌ **NONE registered** — `register_allow_rule()` never called anywhere in codebase |
| Obsidian Git mock store | ✅ `_MockObsidianGitStore` in-memory, tamper-evident, no real credentials needed |
| Notion handoff (bounded, advisory) | ✅ `publish_final_plan_to_notion()` with mock adapter |
| Existing persisted data in `data/` | ⚠️ Contains prior checkpoints, evidence, state — but no projects created yet |

---

## B. Complete Project Creation Path

**Trace:** Dashboard UI → dashboard action → DashboardService → SecurityManager gate → ProjectService → persistence

### 1. Dashboard UI (`src/aios/ui/dashboard.html`)

The Project Workspace page (page 3) renders the UI at `renderProject()` (line 166).
In the index view (no project selected), a "Create project" form at line 204-207:

```html
<input id="proj-name" placeholder="Project name">
<button class="action" onclick="createProject()">Create project</button>
```

`createProject()` (line 212-215):
```javascript
function createProject() {
  const name = document.getElementById('proj-name').value || 'Untitled Project';
  act('project.create', {name});
}
```

`act()` (line 335-343) sends a POST to `/api/action`:
```javascript
async function act(action, params) {
  const res = await fetch(API_ACTION, {method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({action, params, principal:"dashboard_user"})
  });
  const out = await res.json();
  toast(`[${action}] ${out.status} — ${out.detail||''}`, out.authorized || out.status==='completed');
}
```

### 2. DashboardHTTPServer (`src/aios/services/dashboard_server.py`)

`do_POST` (line 154) receives the action:
- **Action:** `"project.create"`
- **Params:** `{"name": "<user-entered name>"}`
- **Principal:** `"dashboard_user"` (default, from line 172)

The server calls `self.dashboard_service.request_action(action, params, principal)`
(line 182) — **the server itself decides nothing**.

### 3. DashboardService.request_action (`src/aios/services/dashboard_service.py:639`)

Entry point (line 639):
```python
async def request_action(self, action, params=None, principal="dashboard_user")
```

**Gate 1 — SecurityManager authorization (fail-closed)** (line 680-697):
```python
decision = SecurityDecision.DENY
if self._security_manager is not None:
    decision = self._security_manager.authorize(
        principal=principal,
        action=action,
        resource=params.get("name") or action,
        context={"source": "dashboard", "params": params, ...},
    )
if decision != SecurityDecision.ALLOW:
    # Emit DASHBOARD_ACTION_REJECTED, return DashboardActionResult(status="rejected")
    return DashboardActionResult(authorized=False, status="rejected", ...)
```

**Critical finding:** `self._security_manager` is the real `SecurityManager`
passed at `kernel.py:2838`. Its `authorize()` returns `DENY` because no
allow-rule exists for `(principal="dashboard_user", action="project.create",
resource=<project_name>)`.

### 4. _execute_bounded_action (`dashboard_service.py:748`)

If authorized (which it never is for project actions without allow-rules),
dispatches to `_execute_project_action` (line 814) for:
- `"project.create"` → `project_service.create_project(name=...)` (line 827)
- `"project.transition"` → `project_service.validate_transition(...)` then
  `project_service.apply_transition(...)` (line 834-843)
- `"project.publish_notion"` → `project_service.publish_final_plan_to_notion(...)` (line 846-853)
- `"project.clear_action"` → transition to `READY_FOR_ACTION` (line 855-867)

### 5. ProjectService.create_project (`project_service.py:274`)

```python
def create_project(self, name, description="", owner="dashboard_user", project_id=None)
    -> Project:
    # No AI-OS authorization needed; project creation is a local workspace scaffold
    pid = project_id or _new_knowledge_id("proj")
    project = Project(project_id=pid, name=name, state=ProjectState.CREATED, ...)
    self._projects[pid] = project  # cache-only; not authoritative persistence
    return project
```

**Note:** `create_project` itself does NOT call `SecurityManager.authorize()` —
but it is only reachable **through** `DashboardService.request_action` which
does. So the gate is enforced at the DashboardService layer.

### 6. Persistence

After creation, messages/decisions/plans/tasks persist to the Obsidian Git
adapter's mock store via `create_knowledge()`:
- `chat/{project_id}/{msg_id}` — conversation
- `knowledge/{project_id}/{kid}` — knowledge entries
- `decisions/{project_id}/{dec_id}` — decisions
- `plans/{project_id}/{plan_id}` — plan variants
- `tasks/{project_id}/{task_id}` — task items

The adapter is resolved via `self._get_adapter("obsidian_git_adapter")` →
`kernel.obsidian_git_adapter` (line 234-236 in project_service.py).

### 7. Failure Behavior

- If SecurityManager denies (current state): `DashboardActionResult(status="rejected", authorized=False)`
- If SecurityManager is None or raises: fail-closed DENY (line 694-696)
- If transition is invalid (e.g., CREATED → EXECUTING): `ValueError` → `status="error"` (line 842)
- If ProjectService is unavailable: `RuntimeError` (line 809)

### 8. Success Behavior

When authorized and valid:
- `project.create` → returns `{"project_id": ..., "state": "CREATED"}`
- `project.transition` → returns `{"project_id": ..., "state": "<new_state>"}`
- `project.publish_notion` → returns `{"published": True, "notion_page_id": ..., "advisory": True}`

---

## C. Project State Machine

**Authoritative model:** `ProjectState` enum in `src/aios/services/project_service.py:44-59`

### All Project States (13)

| State | Description |
|---|---|
| `CREATED` | Initial state — project scaffold created |
| `DISCUSSION` | Planning chat / initial discussion |
| `RESEARCH` | Research phase |
| `PLANNING` | Plan drafting |
| `REVIEW` | Plan under review |
| `DECISION_PENDING` | Awaiting approval decision |
| `APPROVED` | Plan approved |
| `FINALIZED` | Plan finalized |
| `PUBLISHED_TO_NOTION` | Final plan handed off to Notion (advisory) |
| `READY_FOR_ACTION` | Cleared for execution |
| `EXECUTING` | Execution in progress |
| `COMPLETED` | Terminal — execution complete |
| `BLOCKED` | Error/recovery state — can exit to any non-terminal state |

### Valid Transitions (from `_ALLOWED_TRANSITIONS` at line 64)

```
CREATED → {DISCUSSION, BLOCKED}
DISCUSSION → {RESEARCH, DISCUSSION, BLOCKED}
RESEARCH → {PLANNING, RESEARCH, BLOCKED}
PLANNING → {REVIEW, PLANNING, BLOCKED}
REVIEW → {DECISION_PENDING, REVIEW, BLOCKED}
DECISION_PENDING → {APPROVED, DECISION_PENDING, BLOCKED}
APPROVED → {FINALIZED, APPROVED, BLOCKED}
FINALIZED → {PUBLISHED_TO_NOTION, FINALIZED, BLOCKED}
PUBLISHED_TO_NOTION → {READY_FOR_ACTION, BLOCKED}
READY_FOR_ACTION → {EXECUTING, BLOCKED}
EXECUTING → {COMPLETED, EXECUTING, BLOCKED}
COMPLETED → {COMPLETED, BLOCKED}
BLOCKED → {CREATED, DISCUSSION, RESEARCH, PLANNING, REVIEW, DECISION_PENDING,
           APPROVED, FINALIZED, PUBLISHED_TO_NOTION, READY_FOR_ACTION, EXECUTING}
```

**Self-loops** (same state) are always allowed (`can_transition` returns True
when `from_state == to_state`, line 88-89).

### Invalid Transitions

Examples of disallowed transitions (confirmed by `test_can_transition_spec_graph`
at line 110):
- `CREATED → EXECUTING` (skipping the entire lifecycle)
- `PLANNING → EXECUTING` (skipping REVIEW, DECISION_PENDING, APPROVAL)
- `DISCUSSION → PLANNING` (skipping RESEARCH)

### How Transitions Are Authorized

**Two-layer authorization:**

1. **SecurityManager gate** (DashboardService.request_action, line 680-697):
   The principal `"dashboard_user"` must have an allow-rule for
   `action="project.transition"` on `resource=<project_id>`. Currently no
   allow-rules are registered → always DENIED.

2. **Lifecycle graph validation** (ProjectService.validate_transition, line 307):
   Even if SecurityManager allows the action, `validate_transition` checks the
   transition against `_ALLOWED_TRANSITIONS`. If invalid, returns
   `(False, "transition X -> Y not permitted")`, which raises `ValueError` in
   `_execute_project_action` (line 842), resulting in `status="error"`.

### What Happens on Invalid Transition Request

From `dashboard_service.py:834-843`:
```python
if action == "project.transition":
    ok, reason = project_service.validate_transition(project_id, to_state)
    if not ok:
        raise ValueError(f"Lifecycle transition rejected by AI-OS: {reason}")
    project = project_service.apply_transition(project_id, to_state)
```

The `ValueError` is caught at line 738-745 and returned as:
```python
DashboardActionResult(authorized=True, status="error",
    detail=f"Bounded execution failed: {exc}")
```

The project state remains unchanged. This is **advisory validation only** —
the authoritative enforcement is the SecurityManager gate (which denies all
actions anyway due to missing allow-rules).

---

## D. Recommended First Controlled Project

**Recommendation: NONE — system not ready for first controlled project.**

The system cannot execute the first controlled project because the
SecurityManager fail-closed gate denies all dashboard actions. The project
service infrastructure is complete, but the authorization pathway is blocked.

**IF allow-rules were registered**, the recommended smallest project would be:

> **"Local Project Lifecycle End-to-End"** — Create a local project, add a
> discussion message, store a research finding, draft a plan, record a
> decision, transition through the full lifecycle (CREATED→DISCUSSION→RESEARCH→PLANNING→REVIEW→DECISION_PENDING→APPROVED→FINALIZED),
> publish the final plan to Notion (mock), clear for action, and mark complete.

Requirements:
- Local only (mock Obsidian Git adapter, in-memory)
- No real credentials or external API
- No destructive operations
- Deterministic and inspectable via `/api/pages` and dashboard UI
- Exercises: create, message, knowledge, plan, decision, transition, Notion
  handoff, clear_action, complete

---

## E. Exact Project Operations to Execute

*(These are the operations that WOULD be executed once the security gate is
unblocked.)*

1. **Start the kernel:** `aios kernel start`
2. **Verify dashboard:** `curl http://127.0.0.1:8787/api/pages` → check
   `project_workspace.available == true`
3. **Create project:** `POST /api/action` with
   `{"action": "project.create", "params": {"name": "Lifecycle Test"}, "principal": "dashboard_user"}`
4. **Add discussion message:** Through DashboardService, the message is stored
   in the ProjectService cache + persisted to Obsidian vault `/chat/{project_id}/`
5. **Store knowledge:** `project_service.store_knowledge(project_id, "research_finding", "content")`
6. **Save plan:** `project_service.save_plan(project_id, {"content": "plan body", "variant": "v1"})`
7. **Record decision:** `project_service.store_decision(project_id, "Use X", "Because Y")`
8. **Transition through lifecycle:** Sequential `POST /api/action` calls for
   `project.transition` with `to_state` values: DISCUSSION, RESEARCH, PLANNING,
   REVIEW, DECISION_PENDING, APPROVED, FINALIZED
9. **Publish to Notion (mock):** `POST /api/action` with
   `project.publish_notion` — advisory handoff, no state change
10. **Clear for action:** `POST /api/action` with `project.clear_action`
    → transitions to READY_FOR_ACTION
11. **Start execution:** `POST /api/action` with `project.transition`,
    `to_state: "EXECUTING"`
12. **Complete:** `POST /api/action` with `project.transition`,
    `to_state: "COMPLETED"`
13. **Verify:** `GET /api/pages` → check project state and message/task counts

---

## F. Dashboard-Supported vs Service-Level Operations

| Operation | Dashboard-supported? | Mechanism |
|---|---|---|
| **Create project** | ✅ (via `POST /api/action`, action `project.create`) | `createProject()` button in `dashboard.html` |
| **Read project snapshot** | ✅ (`GET /api/pages`) | `DashboardService.get_project_workspace(project_id)` |
| **List all projects** | ✅ (`GET /api/pages`) | `DashboardService.get_project_workspace()` (index) |
| **Add message / discussion** | ❌ Not exposed via UI | No button in `dashboard.html`; requires direct service call to `ProjectService.add_message()` |
| **Store knowledge** | ❌ Not exposed via UI | No UI button; requires `ProjectService.store_knowledge()` |
| **Draft plan** | ❌ Not exposed via UI | No UI button; requires `ProjectService.save_plan()` |
| **Add task** | ❌ Not exposed via UI | No UI button; requires `ProjectService.add_task()` |
| **Record decision** | ❌ Not exposed via UI | No UI button; requires `ProjectService.store_decision()` |
| **Transition state** | ✅ (via UI buttons) | Buttons for DISCUSSION, RESEARCH, PLANNING; `project.transition` action |
| **Publish to Notion** | ✅ (via `project.publish_notion`) | Button in `dashboard.html` (project view) |
| **Clear for action** | ✅ (via `project.clear_action`) | Button in `dashboard.html` |
| **Execute** | ❌ Not exposed (design constraint) | Discussion never becomes execution; no auto-execution path |

**Key gap:** The dashboard UI exposes project *creation*, *state transition*,
*Notion handoff*, and *clear for action* buttons. But it does **not** expose
the project workspace content operations (discussion, knowledge, plan, tasks,
decisions) through the UI. These require direct service-level calls. The
Project Workspace page shows these once they exist, but provides no UI controls
to create them.

---

## G. Security / Authority Boundaries

### What the Dashboard CANNOT Do (verified)

1. **Authorize operations** — `DashboardService` has no `authorize` method
   (verified by `test_dashboard_cannot_authorize_or_decide` at line 335):
   ```python
   def test_dashboard_cannot_authorize_or_decide():
       svc = _make_dashboard(_FakeKernel(), None, None)
       assert not hasattr(svc, "authorize")
       assert not hasattr(svc, "verify")
       assert not hasattr(svc, "decide")
   ```

2. **Make decisions** — All decision logic is delegated to ProjectService's
   `validate_transition()` (lifecycle graph) and SecurityManager's
   `authorize()` (access control).

3. **Directly access external integrations** — All external calls go through
   the kernel's bounded adapters. The `act()` function in `dashboard.html`
   only calls `/api/action`, which forwards to `DashboardService.request_action`,
   which re-runs the SecurityManager gate.

4. **Bypass SecurityManager** — `request_action` (line 680-697) makes
   `SecurityDecision.DENY` the default. If `self._security_manager` is None,
   `decision` remains `SecurityDecision.DENY`. If `authorize()` raises, the
   `except` clause sets `decision = SecurityDecision.DENY` (line 696).

### What SecurityManager Enforces

- **Fail-closed (CC-SEC-001):** `authorize()` returns `DENY` unless an explicit
  allow-rule matches (line 1341-1397).
- **Unknown principal:** If `principal` is None or "" and
  `_deny_unknown_principal=True`, returns `DENY` and records a violation
  (line 1362-1381).
- **Audit trail:** Every DENY is recorded as a `SECURITY_ISSUE_FOUND` event via
  `record_violation()` (line 1399-1431).

### Critical Gap: No Allow-Rules Registered

The `SecurityManager.register_allow_rule()` method (line 1289) is the **only**
way to make `authorize()` return `ALLOW`. It is defined but **never called**
anywhere in the codebase:

```
src/aios/core/security_manager.py:1289:    def register_allow_rule(  ← only definition
```

A recursive grep across all of `src/aios/` for `register_allow_rule` returned
**only this definition** — no calls. The `_allow_rules` set is initialized
empty at line 1078 and never populated.

**Consequence:** `authorize(principal="dashboard_user", action="project.create", ...)`
will always return `SecurityDecision.DENY` because no matching rule exists.
Every dashboard action — including project creation, state transitions, Notion
handoff, service control — is structurally blocked.

### SecurityABACExtension Note

The `SecurityAbacExtensionService` (`src/aios/services/security_abac_ext.py`)
is a separate service that wraps `authorize()` for autonomous operations
(roles like `autonomous_objective_generator`, `autonomous_judge`, etc.). It
also calls `self._security_manager.authorize()` at line 366 for autonomous
actions — which would also be DENIED since no allow-rules exist. This extension
is for the self-loop engine, not the dashboard.

### Dashboard Observational Status

The dashboard is correctly read-only and non-authoritative for **reads**:
- All page getters return `"read_only": True` and `"authority": "aios_sole"`
- The header badge in `dashboard.html` line 43: `"READ-ONLY · NON-AUTHORITATIVE"`

For **writes** (actions): the fail-closed gate ensures that even if
allow-rules were registered incorrectly, the dashboard could not escalate
beyond what the kernel's security policy permits. The current problem is the
opposite — no allow-rules at all means no writes can happen.

---

## H. Persistence / Evidence

### Where Projects Persist

**Project data** is NOT persisted to disk in an authoritative way. The
`ProjectService` uses an **in-memory cache** (`self._projects: dict[str, Project]`,
line 221) as its working set. The docstring at line 219-220 is explicit:

> "Cache-only project registry. Authoritative persistence lives in the
> Obsidian vault; this dict is a working set, never the source of truth."

However, persistence to the Obsidian vault is **delegated to the Obsidian Git
adapter**, which in mock mode uses an in-memory store (`_MockObsidianGitStore`
at `obsidian_git_adapter.py:143`). When the adapter is `None` (as in test
fixtures), persistence is silently skipped (graceful degradation).

### Knowledge/Message Persistence

- Chat messages → `chat/{project_id}/{msg_id}` in the Obsidian vault
- Knowledge entries → `knowledge/{project_id}/{kid}`
- Decisions → `decisions/{project_id}/{dec_id}`
- Plans → `plans/{project_id}/{plan_id}`
- Tasks → `tasks/{project_id}/{task_id}`
- Notion page IDs → stored in `Project.notion_page_id` (cache-only; advisory)

In mock mode, the `_MockObsidianGitStore` uses an in-memory dict with
SHA-1 commit hashes — **no filesystem writes**. No existing persisted data
would interfere because the store is fresh in each kernel start.

### Existing Persisted Data

The `data/` directory contains:
- `data/evidence/` — Evidence engine JSON outputs (from prior test runs)
- `data/state/` — State manager checkpoints, workflow state
- `data/memory/` — Memory manager persistence
- `data/working/` — Working directory artifacts
- `data/kernel.health` — Runtime health status file (created at kernel start)

**Assessment:** None of these contain project workspace data. The obsidian
vault directory (`data/obsidian/`) is **empty**. Existing evidence/state files
are from prior engineering service runs, not projects. They would not interfere
with a new project workspace test.

However, the obsidian vault being empty means the mock store is what would be
used. Since the mock store is in-memory and per-kernel-start, there is no
cross-contamination risk.

### Evidence After a Run

After a controlled project, evidence would be available from:
1. **ProjectService cache** — `/api/pages` → `project_workspace.project` shows
   state, message_count, decision_count, task_count, plan presence
2. **Obsidian Git mock store** — `DashboardService.get_knowledge_history()` exposes
   `obsidian_git_history` (commit hashes); the `_MockObsidianGitStore.history()`
   method returns version history
3. **Kernel health** — `data/kernel.health` reflects overall kernel status
4. **EventBus** — `DASHBOARD_ACTION_REQUESTED`, `_REJECTED`, `_AUTHORIZED`,
   `_COMPLETED` events (visible in `/api/pages` → `system_observability.recent_events`)
5. **SecurityManager violations** — If actions are denied,
   `SECURITY_ISSUE_FOUND` events are recorded (visible in observability page)
6. **StructuredLogger** — Debug log entries for all project operations

---

## I. External Integration Requirements

### Required for First Controlled Project (after allow-rules are registered)

| Integration | Requirement | Current State in Mock |
|---|---|---|
| **Obsidian Git adapter** (persistence) | Vault path (mock-safe) | ✅ Mock in-memory store; no real path needed |
| **Notion adapter** (advisory handoff) | Notion API token (mock-safe) | ✅ Mock adapter; no real token needed |
| **SecurityManager** | Fail-closed gate | ✅ Built-in; requires allow-rules (MISSING) |
| **EventBus** | Canonical event emission | ✅ Built-in; `DASHBOARD_ACTION_*` events |

### Integrations That Must Remain Disabled

- **Supabase** — Not needed for local project test; remains in mock mode
- **n8n** — Bounded automation; not needed for local test
- **Anthropic/OpenAI** — Not needed; project workflow is deterministic
- **MCP-based integrations** (Graphify, Playwright, Claude-Mem) — Not needed
- **All external integrations remain in mock mode by default** — confirmed
  by `config/integrations.yaml` and the `_init_*_adapter()` methods

### The Only Missing Piece

**No external integration is the blocker.** The project workspace uses the
Obsidian Git mock store (in-memory, no credentials) and the Notion mock adapter
(no API token needed in mock mode). The sole blocker is the **absence of
SecurityManager allow-rules** for dashboard actions.

---

## J. Failure / Recovery Expectations

### If a Controlled-Project Operation Fails

The existing failure/recovery behavior is:

1. **Security denial (current state):**
   - `DashboardService.request_action()` returns `DashboardActionResult(status="rejected")`
   - `DASHBOARD_ACTION_REJECTED` event emitted on EventBus
   - `SECURITY_ISSUE_FOUND` event emitted by SecurityManager (audit trail)
   - Project state unchanged (action never executed)
   - Dashboard UI shows toast: `[project.create] rejected — ...`

2. **Invalid lifecycle transition:**
   - `_execute_project_action` raises `ValueError`
   - Caught at `dashboard_service.py:738`, returns `status="error"`
   - `DASHBOARD_ACTION_COMPLETED` event NOT emitted (rejected before execution)
   - Project state unchanged
   - Dashboard UI shows toast: `[project.transition] error — Lifecycle transition rejected`

3. **Adapter failure (network down, etc.):**
   - `ProjectService.add_message()` catches adapter exceptions at line 386:
     `logger.debug("Chat message persistence skipped: %s", exc)`
   - Message still lives in cache-only working set; degrades gracefully
   - No crash, no authority invention

4. **Kernel crash during project operation:**
   - `HermesKernel.trigger_recovery()` (line 638) delegates to HealthManager
   - HealthManager-driven recovery coordination is wired (`set_lifecycle_manager_ref`)
   - `record_health → mark_degraded` flow available for state recovery

**Do NOT fix anything.** The recovery paths exist and are testable — they
simply never activate when the first failure is the SecurityManager deny.

---

## K. Test Boundary

### What This FIRST CONTROLLED PROJECT IS Intended to Prove

1. **SecurityManager allow-rules function correctly** — Dashboard actions
   (`project.create`, `project.transition`, `project.publish_notion`,
   `project.clear_action`) succeed when allow-rules are present and fail when
   absent (fail-closed).
2. **Dashboard → ProjectService integration works end-to-end** — The full
   pipeline from UI button → HTTP POST → DashboardService → ProjectService
   → Obsidian Git mock store works for a complete lifecycle.
3. **Project lifecycle graph is enforced** — Transitions follow the spec
   graph; illegal transitions are rejected even when SecurityManager allows.
4. **Persistence works in mock mode** — Messages, decisions, plans, tasks
   reach the Obsidian Git mock store with correct paths and provenance.
5. **Authority boundaries hold** — Dashboard cannot bypass SecurityManager;
   ProjectService has no `authorize`/`verify`/`decide`; Notion is advisory.
6. **Observability is complete** — Events, violations, and project state are
   visible through `/api/pages` and log output.

### What This FIRST CONTROLLED PROJECT is NOT Intended to Prove

1. **NOT a full integration test** — Does not exercise real external
   integrations (Supabase, Notion API, n8n), real model providers, or
   cross-integration E2E workflows.
2. **NOT an autonomous execution test** — The project workflow is manually
   driven (UI button clicks or API calls). The self-loop engine and autonomous
   decision-making are out of scope.
3. **NOT a performance test** — Does not validate throughput, latency, or
   scalability under load.
4. **NOT a security penetration test** — Does not test for bypass attempts,
   credential leakage, or adversarial inputs (beyond the fail-closed gate).
5. **NOT a production readiness test** — Does not validate real-mode gating,
   credential configuration, network resilience, or deployment scenarios.
6. **NOT a UI/UX test** — The dashboard HTML is a minimal read-only view;
   visual polish and interaction design are out of scope.

---

## L. Risks / Blockers / Warnings

### BLOCKER: No SecurityManager Allow-Rules Registered (HIGH)

`register_allow_rule()` is defined in `SecurityManager` but **never called**
anywhere in the codebase. The `_allow_rules` set is empty at all times. Every
call to `authorize()` returns `SecurityDecision.DENY` (fail-closed,
CC-SEC-001). This means:

- `project.create` → DENIED
- `project.transition` → DENIED
- `project.publish_notion` → DENIED
- `project.clear_action` → DENIED
- `integration.validate` → DENIED
- `integration.connect` → DENIED
- `self_loop.control` → DENIED
- `self_loop.start_cycle` → DENIED
- `failure_recovery.trigger` → DENIED

**The dashboard is functionally a read-only observability panel. No user
action can be authorized.**

### Risk: SecurityABACExtensionService Does Not Help

The `SecurityAbacExtensionService` (`security_abac_ext.py`) is for autonomous
operations (self-loop engine roles). It **also** calls `SecurityManager.authorize()`
internally (line 366), so it would also be DENIED for any autonomous action
without allow-rules. This affects the self-loop engine, not just the dashboard.

### Risk: The Uncommitted `start()`/`stop()` Methods

The git diff shows uncommitted changes adding `start()` and `stop()` no-op
methods to `ProjectService`. These fix an `AttributeError` during kernel
boot when `ProjectService` is registered as `ServiceType.ENGINEERING` but
lacks lifecycle methods. **These changes must be committed before the
controlled project can proceed** — otherwise the kernel will crash during
`_start_services()` when it tries to call `project_service.start()`.

### Risk: Dashboard UI Lacks Content Creation Controls

The Dashboard HTML (`dashboard.html`) provides UI buttons for project creation,
state transitions, Notion handoff, and clear-for-action. But it provides
**no UI controls** for adding messages, storing knowledge, drafting plans,
adding tasks, or recording decisions. These operations require direct service-
level calls to `ProjectService`. This is not a blocker but means the
"discussion" and "knowledge storage" aspects of the first controlled project
must be driven programmatically, not through the UI.

### Risk: Obsidian Vault Is Empty in Mock Mode

The `_MockObsidianGitStore` is in-memory per kernel start. This means:
- **No cross-run persistence** — data is lost when the kernel restarts
- **No filesystem isolation issue** — existing `data/` contents won't interfere
- But also: **evidence must be captured during the live run** (before kernel
  stop), not inspected from disk afterward

### Risk: No Allow-Rule Registration Mechanism Exposed

There is no CLI command, API endpoint, or config file option to register
allow-rules for the `dashboard_user` principal. The `register_allow_rule()`
method is internal to `SecurityManager` and must be called programmatically.
This means fixing the blocker requires code changes to the kernel's
initialization path (e.g., in `_init_dashboard_backend()` in `kernel.py`).

### Warnings

- The `data/kernel.health` file exists (untracked) and shows `"status": "starting"`
  — the kernel was started at some point but not running now.
- The RUNTIME_PREFLIGHT_AUDIT.md in the repo root claims "READY WITH
  CONFIGURATION" but does NOT identify the allow-rule gap. This audit report
  supersedes that assessment.
- The `tests/integration/test_project_workspace_dashboard.py` tests pass because
  they use **mocked** SecurityManager fixtures (`security_allow`, `security_deny`)
  that bypass the real fail-closed logic. The tests verify the lifecycle logic
  and the dashboard's forwarding behavior, but do NOT test with a real
  SecurityManager that has no allow-rules.

---

## FINAL VERDICT

**NOT READY.**

The first controlled project cannot proceed. The SecurityManager's fail-closed
authorization gate (CC-SEC-001) has **no allow-rules registered** for any
dashboard action, causing every `POST /api/action` request to be rejected
with `SecurityDecision.DENY`. The `register_allow_rule()` method exists but
is never called anywhere in the codebase.

---

## EXACTLY ONE NEXT ACTION

**Register allow-rules for dashboard project actions in the kernel's
SecurityManager during `_init_dashboard_backend()`.**

Specifically, in `src/aios/core/kernel.py`, within or immediately after
`_init_dashboard_backend()` (currently at line 2813), add:

```python
# M14-T2 — register allow-rules for the non-authoritative dashboard User.
# The dashboard forwards user-initiated project lifecycle actions through the
# fail-closed SecurityManager gate; these rules make the dashboard_user
# principal eligible for project lifecycle actions. Authorization is still
# enforced: SecurityManager can revoke at any time, and ProjectService's
# validate_transition() still enforces the lifecycle graph.
if self._security_manager is not None:
    sm = self._security_manager
    for action in (
        "project.create",
        "project.transition",
        "project.publish_notion",
        "project.clear_action",
    ):
        sm.register_allow_rule(
            principal="dashboard_user",
            action=action,
            resource=None,  # wildcard resource — per-project checks in ProjectService
        )
```

This is the **smallest concrete action** that unblocks the first controlled
project. It:
- Does NOT modify SecurityManager's fail-closed logic
- Does NOT modify DashboardService or ProjectService business logic
- Does NOT modify the terminal contract or M7–M14 verified behavior
- Allows the dashboard to forward project actions through the existing gate
- Preserves the ability to revoke at any time via `revoke_allow_rule()`
- Leaves the lifecycle graph validation (ProjectService.validate_transition)
  as the second-layer enforcement

After this single change, the existing tests in
`test_project_workspace_dashboard.py` that use the `security_allow` mock
fixture already verify the end-to-end behavior works correctly when
SecurityManager permits the action.
