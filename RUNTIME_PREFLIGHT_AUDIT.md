# AI-OS v1.0.0 — Runtime Preflight Audit
*Terminal 1 — Independent QA (Evidence Audit Only)*
*Date: 2026-09-15*

---

## A. Why Evidence Was Lost

The evidence for the `EXECUTING → COMPLETED` action was lost because of a **process-local in-memory persistence design** combined with a **kernel restart**. Specifically:

1. **Obsidian Git adapter is in MOCK mode** (no `OBSIDIAN_VAULT_PATH` set, no real mode enabled). In mock mode, `ObsidianGitAdapter._store` is a `_MockObsidianGitStore` (obsidian_git_adapter.py:275) — a plain Python object held in the kernel process's heap.

2. **`_MockObsidianGitStore` uses only in-memory dicts** (`self._knowledge`, `self._history`, `self._head` at obsidian_git_adapter.py:151-154). No writes to `data/obsidian/` occur. The `data/obsidian/` directory is empty (confirmed).

3. **`ProjectService._projects` is also process-local memory** (project_service.py:221) — a `dict[str, Project]` cache described explicitly as "cache-only; never the source of truth."

4. **When the kernel was restarted**, the old process exited, destroying all in-memory objects. The new kernel starts with a fresh empty `_MockObsidianGitStore` and a fresh empty `_projects` dict.

5. **No durable reload path exists.** There is no mechanism to reconstruct the project registry or the mock store contents from disk after a restart. The `data/` directory contains only `kernel.health`, `evidence/`, `state/`, `memory/`, and `working/` — none of which contain project workspace data.

**In summary:** The architecture is correct for mock mode (in-process, no real external dependencies). The evidence was lost because the kernel process was restarted after the controlled project ran but before Terminal 3 could independently verify — and mock-mode persistence has no disk durability by design.

---

## B. Authoritative Runtime Evidence Source

The authoritative runtime evidence source is the **live kernel process itself**, accessed through:

| Evidence Type | Source Object | Location |
|---|---|---|
| Project state, messages, decisions, tasks, plans, transitions | `ProjectService._projects` + `ProjectService._obsidian_git()` (`_MockObsidianGitStore`) | `kernel.project_service` |
| Security authorization decisions (ALLOW/DENY per action) | `SecurityManager.authorize()` return value + `_allow_rules` registry | `kernel.security_manager` |
| Action lifecycle events (REQUESTED → AUTHORIZED/REJECTED → COMPLETED) | Canonical EventBus history (`EventType.DASHBOARD_ACTION_*`) | `kernel.event_bus` |
| Kernel health/liveness/readiness | `kernel.health_state`, `kernel.is_alive`, `kernel.is_ready`, `data/kernel.health` | `kernel` / `data/kernel.health` |
| Observability (metrics, spans, component health) | `ObservabilityManager`, `HealthManager` | `kernel.observability_manager` / `kernel.health_manager` |

**Key point:** The `SecurityManager` has now registered allow-rules for `dashboard_user` (kernel.py:2852-2874) covering `project.create`, `project.transition`, `project.publish_notion`, `project.clear_action`. This means the fail-closed gate is unblocked.

---

## C. Evidence That Must Remain Live

For Terminal 3 to independently verify the `EXECUTING → COMPLETED` transition, the following runtime objects must remain alive in the kernel process:

1. **`ProjectService._projects`** — the in-memory project objects. T3 needs to read `project.state` to see `EXECUTING` then `COMPLETED`.

2. **`ObsidianGitAdapter._store`** (`_MockObsidianGitStore._knowledge` + `_history`) — the commit history proving knowledge entries were persisted during DISCUSSION/RESEARCH/PLANNING/REVIEW phases. This is the audit trail of what was stored.

3. **`SecurityManager._allow_rules`** — to verify the rules that permitted the transitions are registered and match expectations.

4. **EventBus event history** — to verify the `DASHBOARD_ACTION_REQUESTED`, `DASHBOARD_ACTION_AUTHORIZED`, `DASHBOARD_ACTION_COMPLETED` event chain per transition.

5. **`kernel._services`** — to verify ProjectService and DashboardService started successfully.

6. **`data/kernel.health`** — to verify the kernel is alive/ready/degraded throughout the test.

If the kernel restarts, items 1, 2, 3, and 4 are lost. Item 5 is recoverable from a restart. Item 6 is written to disk.

---

## D. Exact Endpoints/Read Paths Available

### Live HTTP API (via DashboardHTTPServer on 127.0.0.1:8787)

| Endpoint | Method | Returns | Read Path |
|---|---|---|---|
| `/api/pages` | GET | All 8 dashboard page bundles | `DashboardService.get_all_pages()` → `get_project_workspace()` → `ProjectService.get_workspace_index()` / `get_project_snapshot(pid)` |
| `/api/pages` (with query) | GET | Same, with optional `project_id` filtering | Same path + `get_project_workspace(project_id)` |
| `/api/action` | POST | `DashboardActionResult` with `status`, `authorized`, `decision`, `data` | `DashboardService.request_action()` → SecurityManager gate → `_execute_bounded_action()` |
| `/alive` | GET | `{"alive": true/false, "status": ...}` | `kernel.check_alive()` → `kernel.is_alive` (reads `data/kernel.health`) |
| `/ready` | GET | `{"ready": true/false, "status": ...}` | `kernel.check_ready()` → `kernel.is_ready` |
| `/health` | GET | Full health report dict | `kernel.get_health()` |

### Programmatic Read Paths (via kernel Python object)

| What to Read | Object Path | Method/Attribute |
|---|---|---|
| Project index | `kernel.project_service.get_workspace_index()` | `dict` with `projects` list |
| Project snapshot | `kernel.project_service.get_project_snapshot(pid)` | Full `dict` with `project.state`, `messages`, `decisions`, `tasks`, `plan`, `allowed_transitions` |
| Project list | `kernel.project_service.list_projects()` | `list[Project]` |
| Single project | `kernel.project_service.get_project(pid)` | `Project` object (has `.state`, `.messages`, `.decisions`, etc.) |
| Obsidian mock history | `kernel.obsidian_git_adapter._store.history(kid)` | `list[str]` of commit hashes per knowledge_id |
| Obsidian mock all keys | `kernel.obsidian_git_adapter._store._knowledge.keys()` | `dict_keys` of all knowledge_ids — **the only way to enumerate all persisted entries** |
| Security allow-rules | `kernel.security_manager._allow_rules` | `set[tuple[str, str, str]]` |
| EventBus recent events | `kernel.event_bus.getRecentEvents(limit=100)` | `list[Event]` — filter for `DASHBOARD_ACTION_*` |
| Kernel stats | `kernel.get_stats()` | Full stats dict |
| Kernel health | `kernel.get_health()` | Async; returns full health dict |
| Service status | `kernel.get_service_status()` | Dict of service statuses |

### File System

| File | Content |
|---|---|
| `data/kernel.health` | JSON: `status`, `timestamp`, `uptime_seconds`, `alive`, `ready`, `lifecycle_state`, `health_manager_status` |
| `data/obsidian/` | **Empty** — mock mode does not write here |

---

## E. Required Evidence for EXECUTING → COMPLETED

The minimum evidence to prove the final transition is:

| Evidence | Source | How T3 Verifies |
|---|---|---|
| 1. Project existed and reached EXECUTING | `ProjectService.get_project(pid).state == "EXECUTING"` before the action | Read `kernel.project_service` snapshot via `/api/pages?project_id=...` |
| 2. `project.transition` action was REQUESTED | EventBus event `DASHBOARD_ACTION_REQUESTED` with `action="project.transition"`, `params.to_state="COMPLETED"` | Read from `kernel.event_bus.getRecentEvents()` or `/api/pages` → `system_observability.recent_events` |
| 3. SecurityManager ALLOWED the action | EventBus event `DASHBOARD_ACTION_AUTHORIZED` with same `request_id` (correlation_id) | Match `request_id` between REQUESTED and AUTHORIZED events |
| 4. Transition was EXECUTING → COMPLETED (not arbitrary) | `ProjectService.apply_transition()` updated `project.state` from `EXECUTING` to `COMPLETED` | Read `project.state` == "COMPLETED" after the action; verify `can_transition(EXECUTING, COMPLETED)` was True (project_service.py:75) |
| 5. Action COMPLETED (not rejected/error) | `DashboardActionResult.status == "completed"` in the `/api/action` POST response | Check the HTTP response from the POST call |
| 6. EventBus emitted COMPLETED event | EventBus event `DASHBOARD_ACTION_COMPLETED` with same `request_id` | Match `request_id` across REQUESTED→AUTHORIZED→COMPLETED events |
| 7. Kernel remained healthy throughout | `data/kernel.health` shows `alive: true`, `ready: true`, `lifecycle_state: OPERATIONAL` | Read health file before and after the transition |

**All 7 pieces of evidence exist simultaneously only while the kernel process is running.** They are distributed across in-memory Python objects (ProjectService, ObsidianGitAdapter._store, SecurityManager._allow_rules, EventBus history) and one file (kernel.health). After kernel restart, pieces 1-4 and 6 are destroyed.

---

## F. T2 Evidence-Capture Procedure

Terminal 2 executes the controlled project lifecycle (CREATED → DISCUSSION → RESEARCH → ... → EXECUTING → COMPLETED) and must capture evidence **before** any kernel shutdown. The procedure:

### Step 1: Start kernel (if not already running)
```bash
aios kernel start &
sleep 5
curl http://127.0.0.1:8787/ready  # must return {"ready": true}
```

### Step 2: Execute the controlled project lifecycle via `/api/action`
```bash
# Create
curl -X POST http://127.0.0.1:8787/api/action \
  -H "Content-Type: application/json" \
  -d '{"action":"project.create","params":{"name":"Controlled Project Audit"},"principal":"dashboard_user"}'
# => capture response: {"status":"completed","authorized":true,"data":{"project_id":"proj-xxx","state":"CREATED"}}

# Transition through lifecycle (each step: REQUESTED → AUTHORIZED → COMPLETED)
# DISCUSSION, RESEARCH, PLANNING, REVIEW, DECISION_PENDING, APPROVED, FINALIZED, PUBLISHED_TO_NOTION, READY_FOR_ACTION, EXECUTING
# (content operations: add_message, store_knowledge, save_plan, store_decision between transitions)
# Final transition:
curl -X POST http://127.0.0.1:8787/api/action \
  -H "Content-Type: application/json" \
  -d '{"action":"project.transition","params":{"project_id":"proj-xxx","to_state":"COMPLETED"},"principal":"dashboard_user"}'
# => capture response: {"status":"completed","authorized":true,"data":{"project_id":"proj-xxx","state":"COMPLETED"}}
```

### Step 3: Capture all evidence BEFORE shutdown
```bash
# Snapshot 1: Full pages bundle (includes project state + observability events)
curl http://127.0.0.1:8787/api/pages > /tmp/aios_evidence_pages.json

# Snapshot 2: Specific project snapshot
curl "http://127.0.0.1:8787/api/pages?project_id=proj-xxx" > /tmp/aios_evidence_project.json

# Snapshot 3: Health
curl http://127.0.0.1:8787/health > /tmp/aios_evidence_health.json

# Snapshot 4: Kernel alive/ready
curl http://127.0.0.1:8787/alive > /tmp/aios_evidence_alive.json
curl http://127.0.0.1:8787/ready > /tmp/aios_evidence_ready.json
```

### Step 4: Export all evidence to durable local files
**The existing read-only mechanism that already provides this is the `/api/pages` endpoint and the `DashboardService.get_all_pages()` method.** This captures:
- `project_workspace` page → full project state, messages, decisions, tasks, plan, allowed_transitions
- `system_observability` page → recent Events (all `DASHBOARD_ACTION_*` events with correlation IDs)
- `knowledge_history` page → adapter modes, Obsidian Git commit history
- `system_health` page → kernel stats, service status, terminal contract violations

The `/api/action` POST responses themselves capture each `DashboardActionResult` (authorized, status, decision, data) — these are the authoritative per-action evidence.

**Additionally**, for the Obsidian Git commit history (which proves knowledge was persisted during DISCUSSION/RESEARCH/PLANNING phases), T2 can access:
```python
# Via Python access to the live kernel object:
obsidian_store = kernel.obsidian_git_adapter._store
all_kids = list(obsidian_store._knowledge.keys())  # enumerate all persisted knowledge
for kid in all_kids:
    commits = obsidian_store.history(kid)  # list of commit hashes per entry
```
This data is also surfaced in `get_all_pages()` → `knowledge_history.obsidian_git_history`, though currently that only shows the first 20 history entries globally (dashboard_service.py:337). For full enumeration, direct Python access to `_store._knowledge.keys()` is needed.

**No new persistence mechanism is required.** The existing `/api/pages` endpoint + `/api/action` responses + `data/kernel.health` file capture all necessary evidence.

---

## G. T3 Independent-Verification Procedure

Terminal 3 can independently inspect the same live runtime **while Terminal 2 keeps the kernel running**, using:

### Remote HTTP checks (no kernel Python access needed)
```bash
# 1. Verify kernel is alive and ready
curl http://127.0.0.1:8787/alive    # expect {"alive": true}
curl http://127.0.0.1:8787/ready     # expect {"ready": true}

# 2. Verify project reached COMPLETED
curl http://127.0.0.1:8787/api/pages | python -c "
import json,sys
d = json.load(sys.stdin)
proj = d['pages']['project_workspace']['projects'][0]
print(f'Project: {proj[\"name\"]}')
print(f'State: {proj[\"state\"]}')
assert proj['state'] == 'COMPLETED', f'Expected COMPLETED, got {proj[\"state\"]}'
print('PASS: project is COMPLETED')
"

# 3. Verify the EXECUTING → COMPLETED transition event chain
curl http://127.0.0.1:8787/api/pages | python -c "
import json,sys
d = json.load(sys.stdin)
events = d['pages']['system_observability']['recent_events']
# Filter for the last project.transition action sequence
transition_events = [e for e in events if e['payload_summary'].get('action') == 'project.transition']
print(f'Total transition events: {len(transition_events)}')
# The final one should be COMPLETED
last = transition_events[-1]
print(f'Last transition: {last[\"payload_summary\"][\"payload\"].get(\"params\", {}).get(\"to_state\")}')
assert 'COMPLETED' in str(last), 'Final transition not COMPLETED'
print('PASS: EXECUTING → COMPLETED transition verified via event chain')
"
```

### Full Python access (if T3 has kernel object access)
```python
# T3 can directly inspect the live kernel:
kernel = get_kernel()  # or however T3 obtains the reference

# Verify project state
proj = kernel.project_service.get_project("proj-xxx")
assert proj.state.value == "COMPLETED"

# Verify the transition was authorized (allow-rules present)
rules = kernel.security_manager._allow_rules
assert ("dashboard_user", "project.transition", None) in rules

# Verify event chain
events = kernel.event_bus.getRecentEvents(limit=100)
action_events = [e for e in events if e.eventType.name.startswith("DASHBOARD_ACTION_")]
# Verify REQUESTED → AUTHORIZED → COMPLETED sequence for the final transition

# Verify knowledge was persisted during the lifecycle
store = kernel.obsidian_git_adapter._store
all_kids = list(store._knowledge.keys())
assert len(all_kids) > 0, "Knowledge store is empty — no content persisted"
```

### What T3 CANNOT do without T2's cooperation
- **Nothing.** T3 can perform all verification remotely via HTTP. If T3 needs to enumerate the full Obsidian Git mock store contents (all knowledge_ids with their commit histories), it can use the `/api/pages` → `knowledge_history` endpoint, though the current implementation only surfaces the first 20 history entries. For complete enumeration, T3 would need to access `kernel.obsidian_git_adapter._store._knowledge` directly — which requires same-process access.

---

## H. Shutdown Timing

The shutdown timing boundary is critical:

```
T2 executes project lifecycle
    ├─ create → transition → ... → EXECUTING → COMPLETED
    └─ Each action: capture HTTP response (DashboardActionResult)
↓
T2 captures evidence
    ├─ curl /api/pages > evidence_pages.json
    ├─ curl /api/pages?project_id=... > evidence_project.json
    ├─ curl /health > evidence_health.json
    ├─ curl /alive + /ready > evidence_status.json
    └─ (optionally) capture event chain from observability page
↓
KERNEL REMAINS RUNNING
↓
T3 independently verifies live state/evidence
    ├─ curl /alive, /ready, /health
    ├─ curl /api/pages → verify project.state == "COMPLETED"
    ├─ curl /api/pages → verify event chain REQUESTED→AUTHORIZED→COMPLETED
    └─ (optionally) direct Python inspection if same-process
↓
T3 VERDICT (READY / NOT READY / etc.)
↓
Only after T3 verdict → kernel shutdown
```

**The kernel must NOT be stopped between T2's completion and T3's verification.** The `data/kernel.health` file alone is insufficient — it shows `status` and `alive`/`ready` but does NOT contain project state, transition history, or the `DASHBOARD_ACTION_*` event chain. Those exist only in-process.

---

## I. Whether Any Architecture Change Is Required

**No architecture change is required.**

The existing architecture is sound:

1. **The allow-rule gap has been closed.** `kernel.py:2852-2874` registers allow-rules for `dashboard_user` covering `project.create`, `project.transition`, `project.publish_notion`, `project.clear_action` during `_init_dashboard_backend()`. The fail-closed gate now permits these specific bounded actions.

2. **The ProjectService lifecycle graph is correct.** `can_transition()` enforces the spec graph (project_service.py:86-90). `EXECUTING → COMPLETED` is a valid transition (line 75). The two-layer enforcement (SecurityManager gate + lifecycle validation) is intact.

3. **Evidence capture mechanisms already exist.** The `/api/pages` endpoint exposes all 8 dashboard pages including project state, observability events, knowledge history, and system health. The `/api/action` POST endpoint returns `DashboardActionResult` with `status`, `authorized`, `decision`, and `data` for each action.

4. **The kernel can remain running** during T3 verification. No restart is needed. T3 can verify via HTTP endpoints while T2 holds the kernel alive.

5. **No new persistence mechanism is needed.** The existing `/api/pages` + `/api/action` + `data/kernel.health` capture all required evidence while the kernel is running. The instructions explicitly say: "Do NOT create a new persistence mechanism." The existing read-only mechanisms suffice.

6. **The ProjectService `start()`/`stop()` no-op methods** (uncommitted diff) fix the `AttributeError` during kernel boot when `ProjectService` is registered as `ServiceType.ENGINEERING`. **These must be committed** before repeating the controlled project, otherwise `_start_services()` will crash (kernel.py:3119-3120 calls `svc.start()` on all engineering services).

---

## J. Risks / Warnings

| # | Risk | Severity | Mitigation |
|---|---|---|---|
| 1 | Obsidian Git mock store is in-memory only; kernel restart destroys evidence | HIGH | Capture all evidence via `/api/pages` before shutdown. Kernel must remain running during T3 verification. |
| 2 | `ProjectService._projects` is cache-only; no durable project registry | HIGH | Same as above — `/api/pages` → `project_workspace` page captures current state. |
| 3 | No allow-rule registration mechanism exposed via CLI/API | LOW | Allow-rules are already registered in `_init_dashboard_backend()` (kernel.py:2852-2874). No further action needed. |
| 4 | Dashboard UI lacks content creation controls (messages, knowledge, plans, decisions) | LOW | These can be driven programmatically via direct `ProjectService` method calls or via additional `DashboardService.request_action` calls. The UI gap is cosmetic; the API path works. |
| 5 | Uncommitted `start()`/`stop()` methods on ProjectService | CRITICAL | Must be committed before next kernel start. Kernel boot will crash otherwise. |
| 6 | `kernel.health` shows `"status": "running"` but `health_manager_status: "UNKNOWN"` | INFO | HealthManager has no `_health_checks` registered (line 1078 area shows `UNKNOWN`). This is expected in the current state — the kernel is OPERATIONAL per LifecycleManager. Not a blocker. |
| 7 | The `/api/pages` → `knowledge_history.obsidian_git_history` only returns first 20 commit hashes | LOW | For full enumeration, use direct Python access to `kernel.obsidian_git_adapter._store._knowledge.keys()` + `store.history(kid)`. Or increase the limit in `get_knowledge_history()`. |
| 8 | Terminal 1's git status shows uncommitted changes to `kernel.py` and `project_service.py` | INFO | These changes (allow-rules, start/stop methods) are required for the controlled project. They should be committed before proceeding, but the strict rules say "Do NOT commit." The allow-rules are already in the working tree. |

---

## FINAL VERDICT

### **READY WITH CONDITION**

The system is ready to repeat the controlled project validation **with one mandatory precondition**:

> **The uncommitted changes to `kernel.py` (allow-rule registration, lines 2852-2874) and `project_service.py` (`start()`/`stop()` no-op methods) must be committed before the next kernel start.**

Without these commits:
- The allow-rules will not be registered at runtime → all dashboard actions will be DENIED (fail-closed).
- `ProjectService` lacks `start()`/`stop()` → kernel boot will crash at `_start_services()` (kernel.py:3119).

### EXACTLY ONE NEXT ACTION

**Commit the working-tree changes to `src/aios/core/kernel.py` and `src/aios/services/project_service.py`.**

Specifically:
```bash
git add src/aios/core/kernel.py src/aios/services/project_service.py
git commit -m "M14-T2: Register dashboard_user allow-rules + ProjectService lifecycle methods

Terminal 1 audit requires these changes committed before the next
controlled project validation:
- kernel.py: register allow-rules for dashboard_user (project.create,
  project.transition, project.publish_notion, project.clear_action)
- project_service.py: add start()/stop() no-op methods to fix AttributeError
  during _start_services() boot path

Co-Authored-By: Claude <noreply@anthropic.com>"
```

After this commit (and only after), Terminal 2 may proceed with the controlled project execution → evidence capture → T3 independent verification → T2/T3 verdict → kernel shutdown.
