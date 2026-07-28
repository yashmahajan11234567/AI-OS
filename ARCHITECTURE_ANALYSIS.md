# AI-OS Architecture Analysis & Event-Driven Refactor

> Status as of this refactor: **baseline repaired** — `aios version`, `aios doctor`, and an in-process Hermes Kernel smoke test all pass. The disconnected event-bus bug is fixed.

## 1. What already exists (preserve)

The Phase-2/3 foundation was already substantially built in `src/aios/`:

### Hermes Kernel (`core/`) — coordination + managers
- `core/kernel.py` — `HermesKernel`, `KernelConfig`, `ServiceStatus`, lifecycle.
- `core/kernel_management.py` — `run_kernel`, `stop_kernel`, `get_kernel`, `is_running`, `execute_with_kernel`.
- `events/` — `Event`, `EventType` (90+ events), `EventBus` (sync+async pub/sub, history, filters), `EventHandler`/`AsyncEventHandler`, `handler_for`/`async_handler_for` decorators.
- `core/state.py` — `StateManager`, `StateScope`, `StateSnapshot` (scoped state + history + persistence).
- `core/workflow.py` — `WorkflowManager`, `WorkflowDefinition`, `WorkflowStep`, `WorkflowStatus` (DAG steps, parallel execution).
- `core/checkpoint.py` — `CheckpointManager`, `Checkpoint` (disk-persisted, restore, prune, retention).
- `core/retry.py` — `RetryManager`, `RetryPolicy`, `RetryStrategy`, `RetryBudget`, `RetryAttempt` (budgets, backoff strategies, `RetryBudgetExhausted` event).
- `core/root_cause.py` — `RootCauseAnalyzer`, `FailureContext`, `RootCauseAnalysis`, `FailureCategory`, `FailureSeverity`, `RecoveryAction` (failure classification + responsible-service routing).
- `core/model_router.py`, `core/resource_manager.py`, `core/logger.py`.
- Kernel capability managers (storage/registry/locking logic — NOT engineering-phase orchestration):
  - `core/memory.py` — `MemoryManager`, `MemoryType`, `MemoryEntry`, `FileMemoryBackend`, `InMemoryBackend`.
  - `core/skill_manager.py` — `SkillManager`, `Skill`, `SkillExecution`.
  - `core/mcp_manager.py` — `MCPManager`, `MCPServerConfig`, `MCPTool`, `MCPServerStatus`, `MCPTransport`.
  - `core/council_manager.py` — `CouncilManager`, `CouncilMember`, `CouncilProposal`, `CouncilVote`, `CouncilDecision`, `CouncilSession`.
  - `core/ai_agency.py` — `AIAgencyService` + 9 agents (Security, Performance, Chaos, Accessibility, Documentation, Concurrency, BugHunter, Architecture, FinalJudge).

### Config + CLI
- `config/` — Pydantic v2 models, YAML loader/validator, defaults.
- `cli/` — Typer `app`; `version`, `doctor`, `kernel start/stop/status/stats` commands.

### What is **missing** (this refactor builds it)
- **All Engineering Service directories are empty** (`agents/`, `ai_agency/`, `council/`, `deployment/`, `integrations/`, `mcp/`, `memory/`, `observers/`, `planner/`, `research/`, `services/`, `skills/`, `testing/`, `utils/`, `workflow/`).
- **No `BaseService` / service registry** — nothing standardises "a service subscribes to events and exposes an API."
- **WorkflowManager duplicates retry logic** instead of delegating to `RetryManager`, and **does not feed failures into `RootCauseAnalyzer`** or create checkpoints.
- **The kernel's event bus was disconnected** from the managers (see fix S3).

## 2. Target architecture (per spec)

Hermes = **Kernel** (coordinator only). Everything else = **Engineering Services**.
Services **never call each other directly** — they communicate **only via events** on the single `EventBus`.

```
                 +--------------- Hermes Kernel ---------------+
                 | EventBus WorkflowMgr StateMgr CheckpointMgr |
                 | RetryMgr RootCauseAnalyzer ModelRouter       |
                 | ResourceManager Logger                       |
                 | MemoryManager SkillManager MCPManager        |
                 | CouncilManager                               |
                 +--^--------------------------------------^----+
                    |                                      |
          (events only - no direct service<->service calls)
                    |                                      |
   Planning   Coding   Review   Testing   Deployment   Operations   ...
   Service    Service  Service  Service   Service      Service
   (use Memory/Skill/MCP/Council/AI-Agency services + kernel managers)
```

### Kernel vs Service responsibilities
- **Kernel managers** stay in `core/` as the *capabilities/coordination layer* the spec explicitly names (Memory/Skill/MCP/Council Manager ...). They expose low-level APIs and hold state, but contain **no engineering-phase logic**.
- **Engineering Services** live in `services/`. Each:
  1. extends `BaseService`
  2. declares `name`, `version`, an API (`async` methods exposed via events)
  3. subscribes to events in `on_start()`
  4. emits completion/failure events
  5. never imports or calls another service directly

## 3. Bugs found & fixed (baseline repair)

| # | Bug | Fix |
|---|-----|-----|
| 1 | `aios doctor` raised `WorkspaceConfig() argument after ** must be a mapping, not str` because `app.yaml` stored `workspace`/`logs` as bare strings. | `config/loader.py::_dict_to_app_config` now coerces bare strings -> `{"path": str}`. |
| 2 | `config/app.yaml` resolved `config: ./config` to a non-existent `config/config` (validator resolves relative to the file's own dir). | Set `config: .`, `workspace: ../workspace`, `logs: ../logs` so paths land at the project root. |
| 3 | **Disconnected event bus** — `kernel._init_core_components` created a local `EventBus` but never registered it as the global singleton. Every manager called `get_event_bus()` (a *different* global) so events never crossed. | Kernel now calls `set_event_bus(...)` and `set_*_manager(...)` for every manager it owns, so all components share one bus. |

**Smoke test (now passing):** `HermesKernel.start()` -> kernel bus `is` global bus; subscribing to `task.created` and publishing it reaches the handler; `get_stats()['kernel']['healthy_services']` == 13.

## 4. Refactor approach (non-breaking, incremental)

1. **Build the Service Framework** (`services/base.py`, `services/registry.py`).
2. **Author Engineering Services** that wrap existing kernel managers via events (Planning, Coding, Review, Testing, Deployment, Operations, Learning) plus capability services (Memory, Skill, MCP, Council, AI Agency) that own the *event-handling* surface while delegating storage/state to the existing `core/*_manager.py` (preserved, not rewritten).
3. **Refactor `WorkflowManager`**: replace its inline retry loop with `RetryManager` execution; on budget exhaustion emit the failure to `RootCauseAnalyzer`; create a `Checkpoint` after each major service completes; route `RecoveryAction` back to the earliest responsible service.
4. **Define the canonical SDLC workflow** (Planning -> Coding -> Review -> Testing -> Deployment -> Operations+) with checkpoints after each service.
5. **Add tests** for event bus, workflow+retry+rca, checkpoint, root cause, and services.
6. **Verify** CLI + workflow demo green end-to-end.

The pre-existing `aios` public API in `aios/__init__.py` and `core/__init__.py` is preserved; new services are additive re-exports only.