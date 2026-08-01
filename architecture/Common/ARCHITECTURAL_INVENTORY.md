# AI-OS Hermes Kernel — Complete Architectural Inventory

**Generated:** 2026-07-28  
**Status:** Implementation exists; architecture being frozen for Specification v1.0  
**Test Status:** 12/21 integration tests passing (6 critical bugs identified — see ARCHITECTURE_REVIEW_REPORT.md)

---

## Executive Summary

The AI-OS Hermes Kernel implements a **pure event-driven architecture** where:
- **Hermes Kernel** = Orchestration only (owns 4 core components: EventBus, StateManager, WorkflowManager, ResourceManager)
- **All communication** = EventBus only (no direct service-to-service calls)
- **Global singletons** = `get_xxx()`/`set_xxx()` accessors for all managers (13 global accessors)
- **17 Services** = 8 Engineering Services + 4 Capability Services + 5 Kernel Managers exposed as services
- **90+ Event Types** spanning complete SDLC + operations + AI agency

---

## 1. Hermes Kernel (Core Orchestration)

| Field | Detail |
|-------|--------|
| **Component** | `HermesKernel` (`src/aios/core/kernel.py`) |
| **Purpose** | Owns & initializes exactly 4 core components; registers as global singletons; manages service lifecycle |
| **Status** | ✅ Implemented — kernel starts/stops, emits KernelStarted/KernelStopped events |
| **Files** | `kernel.py`, `kernel_management.py`, `constants.py`, `version.py` |
| **Dependencies** | EventBus, StateManager, WorkflowManager, ResourceManager, ServiceRegistry, Config |
| **Events Emitted** | `KernelStarted`, `KernelStopped` |
| **Events Consumed** | None (kernel is the orchestrator) |
| **Missing / Gap** | ❌ `datetime.utcnow()` deprecation (15+ files) · ❌ Global singletons create hidden coupling · ❌ No kw_only on Event base (breaks subclassing) |

### KernelConfig (`kernel.py:36-65`)
| Field | Type | Default |
|-------|------|---------|
| `name` | str | "Hermes" |
| `version` | str | "0.1.0" |
| `data_dir` | Path | "./data" |
| `event_bus_max_history` | int | 10000 |
| `auto_start_services` | bool | True |
| `log_level` | str | "INFO" |

### Kernel Lifecycle
```
__init__ → start() → _init_core_components() → _init_service_registry() → 
            _start_services() → emit KernelStarted → running
            ↓
       stop() → _stop_services() → emit KernelStopped → shutdown EventBus → stopped
```

---

## 2. Event System (The Backbone)

### 2.1 Event Base & Factory (`src/aios/events/base.py`)

| Field | Detail |
|-------|--------|
| **Component** | `Event` base class + `EventType` enum (90+ values) + `create_event()` factory |
| **Purpose** | Immutable event carrier with correlation/causation IDs, payload, tags, timestamp |
| **Status** | ❌ **CRITICAL BUG** — `@dataclass` missing `kw_only=True` → subclasses must pass `event_type` positionally; breaks test doubles & user-defined events |
| **Files** | `base.py` |
| **Dependencies** | `uuid`, `datetime`, `dataclasses`, `enum` |
| **Events Used** | N/A (base infrastructure) |
| **Architecture Match** | ✅ Matches spec "Event system with typed events & correlation IDs" |
| **Critical Fix Required** | Add `@dataclass(kw_only=True)` to `Event` class; update all 90+ concrete events in `types.py` to use `event_type: EventType = EventType.XXX` |

### 2.2 Event Bus (`src/aios/events/bus.py`)

| Field | Detail |
|-------|--------|
| **Component** | `EventBus` + `Subscription` dataclass + global `get_event_bus()/set_event_bus()` |
| **Purpose** | Central pub/sub with sync/async publish, filters, history (10k default), wildcards |
| **Status** | ✅ Implemented — sync `publish()`, async `publish_async()`, history queries, stats |
| **Files** | `bus.py` |
| **Dependencies** | `Event`, `EventType`, `EventHandler`, `AsyncEventHandler` |
| **Events Emitted** | None (infrastructure) |
| **Events Consumed** | None (infrastructure) |
| **Missing / Gap** | ❌ `datetime.utcnow()` in `Subscription.subscription_id` factory · ❌ No schema validation/versioning on publish |

### 2.3 Event Types (`src/aios/events/types.py` — 1471 lines)

| Field | Detail |
|-------|--------|
| **Component** | 100+ concrete `@dataclass(kw_only=True)` event classes grouped by domain |
| **Purpose** | Typed event payloads for the entire SDLC + operations + AI agency |
| **Status** | ✅ Implemented — all concrete events have `kw_only=True` (correct!) |
| **Files** | `types.py` |
| **Dependencies** | `Event`, `EventType`, `create_event` |
| **Event Categories (90+ types)** | |
| Task Events (6) | `task.created`, `task.started`, `task.completed`, `task.failed`, `task.cancelled`, `task.retry_requested` |
| Workflow Events (9) | `workflow.created`, `workflow.started`, `workflow.step_started`, `workflow.step_completed`, `workflow.step_failed`, `workflow.completed`, `workflow.failed`, `workflow.paused`, `workflow.resumed` |
| Planning Events (5) | `planning.requested`, `planning.started`, `planning.completed`, `planning.failed`, `plan.approved`, `plan.rejected` |
| Coding Events (6) | `coding.started`, `coding.completed`, `coding.failed`, `code.generated`, `code_review.requested` |
| Review Events (8) | `review.started`, `review.completed`, `review.failed`, `review.approved`, `review.rejected`, `security.issue_found`, `performance.issue_found`, `architecture.issue_found` |
| Testing Events (6) | `testing.started`, `testing.completed`, `testing.failed`, `tests.passed`, `tests.failed`, `test.generated` |
| Deployment Events (5) | `deployment.requested`, `deployment.started`, `deployment.completed`, `deployment.failed`, `deployment.rolled_back` |
| Operations Events (5) | `production.incident`, `metrics.alert`, `log.anomaly_detected`, `user.feedback_received` |
| Memory Events (4) | `memory.stored`, `memory.retrieved`, `memory.updated`, `memory.consolidated` |
| Skill Events (4) | `skill.loaded`, `skill.unloaded`, `skill.executed`, `skill.failed` |
| MCP Events (4) | `mcp.server_connected`, `mcp.server_disconnected`, `mcp.tool_called`, `mcp.tool_result` |
| Council Events (5) | `council.convened`, `council.deliberated`, `council.decided`, `council.dissented` |
| AI Agency Events (18) | `security.audit_requested/completed`, `performance.audit_requested/completed`, `chaos.experiment_requested/completed`, `accessibility.audit_requested/completed`, `documentation.audit_requested/completed`, `concurrency.audit_requested/completed`, `bug_hunt.requested/completed`, `architecture.validation_requested/completed`, `final_judgment.requested/completed` |
| Checkpoint Events (3) | `checkpoint.created`, `checkpoint.restored`, `checkpoint.deleted` |
| Retry Events (3) | `retry.budget_exhausted`, `retry.scheduled`, `retry.executed` |
| Root Cause Events (3) | `root_cause.analyzed`, `root_cause.resolved`, `failure.classified` |
| Learning Events (3) | `learning.captured`, `pattern.extracted`, `knowledge.updated` |
| State Events (3) | `state.transitioned`, `state.checkpointed`, `state.restored` |
| System Events (8) | `service.started/stopped/healthy/unhealthy`, `kernel.started/stopped/error` |

### 2.4 Event Handlers (`src/aios/events/handlers.py`)

| Field | Detail |
|-------|--------|
| **Component** | `EventHandler` (sync), `AsyncEventHandler` (async) base classes + decorators `handler_for`, `async_handler_for` |
| **Purpose** | Declarative handler registration with metadata |
| **Status** | ✅ Implemented |
| **Files** | `handlers.py` |
| **Dependencies** | `Event` |

---

## 3. Core Managers (Kernel-Owned Capabilities)

### 3.1 State Manager (`src/aios/core/state.py`)

| Field | Detail |
|-------|--------|
| **Component** | `StateManager` + `StateScope` enum (WORKFLOW, SERVICE, GLOBAL, SESSION) + `StateSnapshot` |
| **Purpose** | Scoped state with history, snapshots, persistence to disk |
| **Status** | ✅ Implemented |
| **Files** | `state.py` |
| **Dependencies** | `EventBus` (via global), `json`, `pathlib` |
| **Global Accessor** | `get_state_manager()`, `set_state_manager()` |
| **Events Emitted** | None directly (used by WorkflowManager) |
| **Events Consumed** | None |
| **Missing / Gap** | ❌ `datetime.utcnow()` used · ❌ No event emission on state changes (per spec, StateManager emits `StateTransitioned`) |

### 3.2 Workflow Manager (`src/aios/core/workflow.py`)

| Field | Detail |
|-------|--------|
| **Component** | `WorkflowManager` + `WorkflowDefinition` + `WorkflowStep` + `WorkflowStatus` enum |
| **Purpose** | DAG-based workflow execution with parallel steps, checkpoint integration, RCA recovery routing |
| **Status** | ✅ Core implemented; ⚠️ **Design Gap** — duplicates retry logic instead of delegating to RetryManager; does not emit checkpoints after each step; RCA integration incomplete |
| **Files** | `workflow.py` |
| **Dependencies** | `StateManager`, `EventBus` (global), `RetryManager` (global), `RootCauseAnalyzer` (global), `CheckpointManager` (global) |
| **Global Accessor** | `get_workflow_manager()`, `set_workflow_manager()` |
| **Events Emitted** | `WorkflowStarted`, `WorkflowStepStarted`, `WorkflowStepCompleted`, `WorkflowStepFailed`, `WorkflowCompleted`, `WorkflowFailed` |
| **Events Consumed** | `TaskCreated`, `RetryBudgetExhausted`, `CheckpointRestored` |
| **Key Methods** | `register_workflow()`, `register_step_handler()`, `start_workflow()`, `get_workflow_status()`, `pause_workflow()`, `resume_workflow()` |
| **Architecture Gap (per ARCHITECTURE_ANALYSIS.md)** | Should delegate retries to RetryManager; emit `CheckpointCreated` after each step; on failure, emit to RootCauseAnalyzer and route `RecoveryAction` back to responsible service |

### 3.3 Checkpoint Manager (`src/aios/core/checkpoint.py`)

| Field | Detail |
|-------|--------|
| **Component** | `CheckpointManager` + `Checkpoint` dataclass |
| **Purpose** | Disk-persisted workflow checkpoints with pruning, retention, restore |
| **Status** | ⚠️ **CRITICAL BUG** — `create_checkpoint()` calls `get_state(execution_id, "workflow")` which returns `{}` for unknown IDs → raises `ValueError("No workflow state found")` — cannot create first checkpoint for new execution |
| **Files** | `checkpoint.py` |
| **Dependencies** | `StateManager` (global), `EventBus` (global), `json`, `pathlib` |
| **Global Accessor** | `get_checkpoint_manager()`, `set_checkpoint_manager()` |
| **Events Emitted** | `CheckpointCreated`, `CheckpointRestored`, `CheckpointDeleted` |
| **Events Consumed** | None |
| **Critical Fix** | Allow checkpoint creation without pre-existing workflow state or auto-create minimal state |

### 3.4 Retry Manager (`src/aios/core/retry.py`)

| Field | Detail |
|-------|--------|
| **Component** | `RetryManager` + `RetryPolicy` + `RetryStrategy` enum (FIXED, EXPONENTIAL, LINEAR, FIBONACCI) + `RetryBudget` + `RetryAttempt` |
| **Purpose** | Per-task retry budgets, backoff strategies, budget exhaustion → event emission |
| **Status** | ⚠️ **CRITICAL BUG** — Semantics wrong: `max_retries=3` allows 3 TOTAL calls (1 initial + 2 retries), not 4 (1 + 3 retries). Test expects 4 calls. |
| **Files** | `retry.py` |
| **Dependencies** | `EventBus` (global), `RetryPolicy`, `RetryStrategy` |
| **Global Accessor** | `get_retry_manager()`, `set_retry_manager()` |
| **Events Emitted** | `RetryScheduled`, `RetryExecuted`, `RetryBudgetExhausted`, `TaskFailed` |
| **Events Consumed** | None |
| **Critical Fix** | Change `RetryBudget.remaining` to track `total_attempts = len(attempts) + 1`; exhaust when `total_attempts > max_retries + 1` |

### 3.5 Root Cause Analyzer (`src/aios/core/root_cause.py`)

| Field | Detail |
|-------|--------|
| **Component** | `RootCauseAnalyzer` + `FailureContext` + `RootCauseAnalysis` + `FailureCategory` enum (8) + `FailureSeverity` enum (4) + `RecoveryAction` enum (7) |
| **Purpose** | Keyword-based failure classification → responsible service + recovery action |
| **Status** | ⚠️ **2 CRITICAL BUGS** |
| **Files** | `root_cause.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_root_cause_analyzer()`, `set_root_cause_analyzer()` |
| **Events Emitted** | `RootCauseAnalyzed`, `RootCauseResolved`, `FailureClassified` |
| **Events Consumed** | `TaskFailed`, `RetryBudgetExhausted` |
| **Failure Categories (8)** | TRANSIENT, RESOURCE, CONFIGURATION, CODE_DEFECT, DEPENDENCY, INFRASTRUCTURE, SECURITY, UNKNOWN |
| **Recovery Actions (7)** | RETRY_WITH_BACKOFF, RETURN_TO_PLANNING, RETURN_TO_CODING, RETURN_TO_REVIEW, RETURN_TO_TESTING, ROLLBACK, ESCALATE_TO_HUMAN |
| **Bug 1** | `transient_keywords` missing "timeout" → "Connection timeout" classified as RESOURCE (matches "timeout" in resource_keywords) |
| **Bug 2** | Code defect logic requires `"test" in error_lower` → "SyntaxError: invalid syntax" falls to UNKNOWN |

### 3.6 Memory Manager (`src/aios/core/memory.py`)

| Field | Detail |
|-------|--------|
| **Component** | `MemoryManager` + `MemoryType` enum (5) + `MemoryEntry` + `MemoryBackend` ABC + `InMemoryBackend` + `FileMemoryBackend` |
| **Purpose** | 5 memory systems: WORKING (short-term), CLAUDE (session), ENGINEERING (long-term learnings), OBSIDIAN (vault), GRAPHIFY (graph) |
| **Status** | ✅ Implemented with pluggable backends, consolidation pipeline, TTL, stats |
| **Files** | `memory.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_memory_manager()`, `set_memory_manager()` |
| **Events Emitted** | `MemoryStored`, `MemoryRetrieved`, `MemoryUpdated`, `MemoryConsolidated` |
| **Events Consumed** | None (facade service consumes events) |
| **Memory Types** | 5 distinct stores with different purposes/backends |

### 3.7 Skill Manager (`src/aios/core/skill_manager.py`)

| Field | Detail |
|-------|--------|
| **Component** | `SkillManager` + `Skill` + `SkillExecution` + 4 built-in skills (shell, file_ops, web_search, code_analysis) |
| **Purpose** | Skill registry, discovery, loading, execution, marketplace-ready |
| **Status** | ✅ Implemented |
| **Files** | `skill_manager.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_skill_manager()`, `set_skill_manager()` |
| **Events Emitted** | `SkillLoaded`, `SkillUnloaded`, `SkillExecuted`, `SkillFailed` |
| **Built-in Skills** | `shell`, `file_operations`, `web_search`, `code_analysis` |

### 3.8 MCP Manager (`src/aios/core/mcp_manager.py`)

| Field | Detail |
|-------|--------|
| **Component** | `MCPManager` + `MCPServerConfig` + `MCPTool` + `MCPServerStatus` enum + `MCPTransport` enum (4) |
| **Purpose** | MCP server/client management, tool orchestration, 4 transports (STDIO, HTTP, SSE, WEBSOCKET) |
| **Status** | ✅ Implemented |
| **Files** | `mcp_manager.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_mcp_manager()`, `set_mcp_manager()` |
| **Events Emitted** | `MCPServerConnected`, `MCPServerDisconnected`, `MCPToolCalled`, `MCPToolResult` |

### 3.9 Council Manager (`src/aios/core/council_manager.py`)

| Field | Detail |
|-------|--------|
| **Component** | `CouncilManager` + `CouncilMember` + `CouncilProposal` + `CouncilVote` + `CouncilDecision` + `CouncilSession` + `CouncilRole` enum (5) + `ConsensusAlgorithm` enum (5) |
| **Purpose** | Multi-agent deliberation, consensus protocols (majority, unanimous, weighted, ranked, consent) |
| **Status** | ✅ Implemented |
| **Files** | `council_manager.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_council_manager()`, `set_council_manager()` |
| **Events Emitted** | `CouncilConvened`, `CouncilDeliberated`, `CouncilDecided`, `CouncilDissented` |
| **Council Roles (5)** | CHAIR, MEMBER, OBSERVER, ADVISOR, CRITIC |
| **Consensus Algorithms (5)** | MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT |

### 3.10 AI Agency Service (`src/aios/core/ai_agency.py`)

| Field | Detail |
|-------|--------|
| **Component** | `AIAgencyService` + 9 specialized agents |
| **Purpose** | Autonomous AI review agents for security, performance, chaos, accessibility, documentation, concurrency, bug hunting, architecture, final judgment |
| **Status** | ✅ Implemented |
| **Files** | `ai_agency.py` |
| **Dependencies** | `EventBus` (global), `ModelRouter` (global) |
| **Global Accessor** | `get_ai_agency_service()`, `set_ai_agency_service()` |
| **Events Emitted** | All 18 audit event pairs (requested/completed) |
| **Agents (9)** | SecurityAuditor, PerformanceAuditor, ChaosEngineer, AccessibilityAuditor, DocumentationAuditor, ConcurrencyAuditor, BugHunter, ArchitectureValidator, FinalJudge |

### 3.11 Model Router (`src/aios/core/model_router.py`)

| Field | Detail |
|-------|--------|
| **Component** | `ModelRouter` + capability-based routing, cost optimization, fallback chains |
| **Purpose** | Route LLM requests to appropriate models (Claude, local, cloud) |
| **Status** | ✅ Implemented |
| **Files** | `model_router.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_model_router()`, `set_model_router()` |
| **Events Emitted** | None currently |

### 3.12 Resource Manager (`src/aios/core/resource_manager.py`)

| Field | Detail |
|-------|--------|
| **Component** | `ResourceManager` + `ResourceType` enum (7) + allocation tracking, wait queues, TTL cleanup |
| **Purpose** | Manage compute, memory, API quotas, tokens, storage, network, GPU |
| **Status** | ✅ Implemented |
| **Files** | `resource_manager.py` |
| **Dependencies** | `EventBus` (global) |
| **Global Accessor** | `get_resource_manager()`, `set_resource_manager()` |
| **Resource Types (7)** | COMPUTE, MEMORY, API_QUOTA, TOKENS, STORAGE, NETWORK, GPU |

### 3.13 Structured Logger (`src/aios/core/logger.py`)

| Field | Detail |
|-------|--------|
| **Component** | `StructuredLogger` + JSON formatting, correlation IDs, BoundLogger, EventBus integration |
| **Purpose** | Centralized structured logging with event emission |
| **Status** | ✅ Implemented |
| **Files** | `logger.py` |
| **Dependencies** | `EventBus` (global) |
| **Missing / Gap** | ❌ Uses stdlib `logging` not `structlog` (per review, should use structlog) · ❌ `datetime.utcnow()` |

---

## 4. Service Framework

### 4.1 Base Service (`src/aios/services/base.py`)

| Field | Detail |
|-------|--------|
| **Component** | `BaseService` abstract class + `ServiceStatus` enum (CREATED, STARTING, RUNNING, STOPPED, FAILED, DEGRADED) |
| **Purpose** | Event-driven service base with lifecycle, event subscription helpers, stats |
| **Status** | ✅ Implemented |
| **Files** | `base.py` |
| **Dependencies** | `EventBus` (global), `Event`, `EventType` |
| **Key Methods** | `on_start()`, `on_stop()`, `on_health_check()`, `subscribe()`, `emit()`, `get_stats()` |
| **Critical Bug (Test Double)** | `BaseService.__init__(event_bus=None, info=None)` but `TestService.__init__(name)` calls `super().__init__(name, "1.0.0")` → `name` becomes `event_bus`, `"1.0.0"` becomes `info` |

### 4.2 Service Registry (`src/aios/services/registry.py`)

| Field | Detail |
|-------|--------|
| **Component** | `ServiceRegistry` + `ServiceInfo` dataclass |
| **Purpose** | Topological start/stop via `depends_on`, health checks, lifecycle events |
| **Status** | ✅ Implemented |
| **Files** | `registry.py` |
| **Dependencies** | `EventBus`, `BaseService` |
| **Global Accessor** | `get_service_registry()`, `set_service_registry()` |
| **Events Emitted** | `ServiceStarted`, `ServiceStopped` (via registry) |
| **Events Consumed** | None |

---

## 5. Engineering Services (8) — Event-Driven SDLC Phases

All services extend `BaseService`, declare `depends_on`, subscribe in `on_start()`, emit typed events, **never call each other directly**.

| # | Service | File | Consumes | Emits | Depends On |
|---|---------|------|----------|-------|------------|
| 1 | **PlanningService** | `planning.py` | `PlanningRequested`, `PlanRejected` | `PlanningCompleted`, `PlanningFailed`, `TaskCreated` | `memory` |
| 2 | **CodingService** | `coding.py` | `CodingStarted`, `ReviewApproved` | `CodeGenerated`, `CodingCompleted`, `CodingFailed`, `CodeReviewRequested` | `planning`, `memory` |
| 3 | **ReviewService** | `review.py` | `CodeReviewRequested` | `ReviewStarted`, `ReviewApproved`, `ReviewRejected`, `ReviewFailed`, `SecurityIssueFound`, `PerformanceIssueFound` | `coding`, `ai_agency` |
| 4 | **TestingService** | `testing.py` | `ReviewApproved`, `TestingStarted` | `TestGenerated`, `TestsPassed`, `TestsFailed`, `TestingCompleted`, `TestingFailed` | `review` |
| 5 | **DeploymentService** | `deployment.py` | `DeploymentRequested` | `DeploymentStarted`, `DeploymentCompleted`, `DeploymentFailed`, `DeploymentRolledBack` | `testing`, `review` |
| 6 | **OperationsService** | `operations.py` | `DeploymentCompleted`, `ProductionIncident`, `MetricsAlert`, `LogAnomalyDetected`, `UserFeedbackReceived` | `TaskCreated` (follow-up engineering tasks) | `deployment` |
| 7 | **LearningService** | `learning.py` | `RootCauseResolved` (also `WorkflowCompleted`, etc.) | `LearningCaptured` | `memory` |
| 8 | **MemoryService** (facade) | `memory.py` | `LearningCaptured`, `CheckpointCreated` | `MemoryStored`, `MemoryRetrieved`, `MemoryUpdated`, `MemoryConsolidated` | (none) |

### Service Dependency Graph (Topological Order)
```
memory (leaf)
  ↑
planning
  ↑
coding → ai_agency (capability)
  ↑
review
  ↑
testing
  ↑
deployment
  ↑
operations
  ↑
learning → memory
```

---

## 6. Capability Services (4) — Facades over Kernel Managers

| # | Service | File | Wraps Manager | Purpose |
|---|---------|------|---------------|---------|
| 1 | **SkillService** | `skill.py` | `SkillManager` | Skill registry, load/unload/execute, auto-discover on KernelStarted |
| 2 | **CouncilService** | `council.py` | `CouncilManager` | Multi-agent deliberation, consensus protocols |
| 3 | **MCPService** | `mcp.py` | `MCPManager` | MCP server connections, tool orchestration |
| 4 | **MemoryService** | `memory.py` | `MemoryManager` | Event-driven facade over 5 memory systems |

---

## 7. Configuration System (`src/aios/config/`)

| File | Purpose |
|------|---------|
| `models.py` | Pydantic v2: `AppConfig`, `WorkspaceConfig`, `LogsConfig`, `Environment` enum |
| `defaults.py` | Default values (name, version, paths) |
| `validator.py` | Path validation, cross-field consistency, semver check |
| `loader.py` | 4-layer merge: defaults → app.yaml → env.yaml → env vars (dotted paths) |
| `__init__.py` | Exports `load_config`, `AppConfig`, `Environment` |

**Config File:** `config/app.yaml`
```yaml
name: AI-OS
version: "0.2.0"
environment: development
workspace: ../workspace
logs: ../logs
config: .
```

---

## 8. CLI (`src/aios/cli/`)

| Command | File | Status |
|---------|------|--------|
| `aios version` | `main.py` | ✅ |
| `aios doctor` | `commands/doctor/__init__.py` | ✅ Validates config |
| `aios kernel start/stop/status` | `commands/kernel/__init__.py` | ✅ Basic impl |
| **Spec Target** (Phase 8) | Workflow, Service, Event, Checkpoint, Memory, Skill, MCP, Council, Learning commands | ❌ Not implemented |

---

## 9. Tests (`tests/integration/test_integration.py`)

| Test Class | Tests | Status |
|------------|-------|--------|
| `TestEventBus` | `test_publish_subscribe`, `test_multiple_subscribers`, `test_event_history` | ❌ Fail (Event kw_only bug) |
| `TestRetryManager` | `test_successful_execution`, `test_retry_on_failure`, `test_exhausted_retries`, `test_non_retryable_exception` | ❌ `test_exhausted_retries` fail (semantic bug) |
| `TestWorkflowExecution` | `test_simple_workflow`, `test_parallel_workflow`, `test_workflow_failure` | ✅ Pass |
| `TestCheckpointRecovery` | `test_create_and_restore_checkpoint`, `test_list_checkpoints`, `test_checkpoint_persistence` | ❌ Fail (pre-seeded state bug) |
| `TestRootCauseAnalysis` | `test_classify_transient_failure`, `test_classify_config_failure`, `test_classify_code_defect`, `test_retry_budget_exhausted_routes_to_service` | ❌ 2 fail (classification bugs) |
| `TestServiceRegistry` | `test_register_and_start_service`, `test_stop_service`, `test_dependency_order`, `test_health_check` | ❌ Fail (BaseService init bug in test doubles) |

**Total:** 9 passed, 12 failed (all failures = production code bugs, not test bugs)

---

## 10. Architecture Gaps: Spec vs. Implementation

| Spec Item (MIGRATION_PLAN.md / ARCHITECTURE_ANALYSIS.md) | Implementation Status |
|--------------------------------------------------------|----------------------|
| Phase 1: Foundation (CLI, Config, Packaging) | ✅ Complete |
| Phase 2: Event Bus & Kernel Core | ✅ Core exists; ❌ Event base bug; ❌ datetime.utcnow() deprecation |
| Phase 3: Service Framework + 12 Service Stubs | ✅ Framework + 12 services implemented (not stubs) |
| Phase 4: Memory System (5 types) | ✅ Implemented in core + MemoryService facade |
| Phase 5: Skill & MCP Systems | ✅ Implemented in core + facades |
| Phase 6: Model Router & Resource Manager | ✅ Implemented in core |
| Phase 7: Council & AI Agency (9 agents) | ✅ Implemented in core + facades |
| Phase 8: CLI Integration (14 command groups) | ⚠️ Only kernel + doctor implemented |
| Phase 9: Config & Documentation | ⚠️ Config done; ❌ Architecture docs incomplete |
| Phase 10: Testing & Verification | ⚠️ 12/21 tests failing (6 production bugs) |

**Major Architectural Decision Not Yet Implemented:**
- MIGRATION_PLAN.md mentions `LearningManager` in kernel core (line 35) — **not implemented**; Learning is a Service, not a Kernel Manager
- ARCHITECTURE_ANALYSIS.md says "WorkflowManager duplicates retry logic instead of delegating to RetryManager" — **still true**
- ARCHITECTURE_ANALYSIS.md says "does not feed failures into RootCauseAnalyzer or create checkpoints" — **still true**

---

## 11. Critical Bugs Summary (Must Fix Before Spec Freeze)

| # | Component | Bug | Test Impact | Fix |
|---|-----------|-----|-------------|-----|
| 1 | `events/base.py:164` | `Event` dataclass missing `kw_only=True` | 3 EventBus tests | Add `@dataclass(kw_only=True)`; update all 90+ events in `types.py` |
| 2 | `core/retry.py:73-79` | `max_retries=3` = 3 total calls, not 4 | `test_exhausted_retries` | Track `total_attempts = len(attempts) + 1` |
| 3 | `core/root_cause.py:323` | "timeout" missing from transient_keywords | `test_classify_transient_failure` | Add "timeout" to transient_keywords; check transient before resource |
| 4 | `core/root_cause.py:313-320` | Code defect requires "test" in error | `test_classify_code_defect` | Remove "test" requirement |
| 5 | `core/checkpoint.py:94-98` | `create_checkpoint` requires pre-existing workflow state | 3 Checkpoint tests | Allow empty state or auto-create minimal state |
| 6 | `tests/integration/test_integration.py:396-414` | Test double `super().__init__` signature mismatch | 4 ServiceRegistry tests | Fix test double OR fix BaseService `__init__` signature |

---

## 12. Code Smells / Technical Debt (Architecture Spec Should Document)

| Category | Count | Examples |
|----------|-------|----------|
| `datetime.utcnow()` deprecation | 15+ files | `kernel.py:193, 203, 296, 303, 306, 316, 337, 343, 385, 400`, `bus.py:32`, `retry.py:60`, `checkpoint.py:52`, `workflow.py:180`, `root_cause.py:37`, `state.py:57`, `state.py:80`, `logger.py:42`, etc. |
| Global singleton anti-pattern | 13 accessors | `get_event_bus`, `get_state_manager`, `get_workflow_manager`, `get_retry_manager`, `get_root_cause_analyzer`, `get_checkpoint_manager`, `get_memory_manager`, `get_skill_manager`, `get_mcp_manager`, `get_council_manager`, `get_model_router`, `get_resource_manager`, `get_ai_agency_service` |
| Circular import risk | High | Global accessors imported across core modules |
| No event schema registry/versioning | 1 gap | Events serialized as dicts; no evolution strategy |
| `RetryPolicy.retryable_exceptions = (Exception,)` | 1 | Catches programming errors (AssertionError, etc.) |
| No structured logging (structlog) | 1 gap | Plain logging with inconsistent formats |
| `ServiceInfo` duplicates `BaseService` attrs | 1 | Both have name, version, description, depends_on |
| Magic strings in subscriptions | Multiple | `"root_cause.analyzed"` vs `EventType.ROOT_CAUSE_ANALYZED` |

---

## 13. Directory Structure (Current)

```
AI-OS/
├── ARCHITECTURE_REVIEW_REPORT.md
├── ARCHITECTURE_ANALYSIS.md
├── MIGRATION_PLAN.md
├── CONFIG_SYSTEM_DESIGN.md
├── ARCHITECTURAL_INVENTORY.md (this file)
├── config/
│   └── app.yaml
├── pyproject.toml
├── src/
│   └── aios/
│       ├── __init__.py
│       ├── __version__.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── main.py
│       │   └── commands/
│       │       ├── doctor/__init__.py
│       │       └── kernel/__init__.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── defaults.py
│       │   ├── loader.py
│       │   ├── models.py
│       │   └── validator.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── constants.py
│       │   ├── version.py
│       │   ├── kernel.py
│       │   ├── kernel_management.py
│       │   ├── state.py
│       │   ├── workflow.py
│       │   ├── checkpoint.py
│       │   ├── retry.py
│       │   ├── root_cause.py
│       │   ├── memory.py
│       │   ├── skill_manager.py
│       │   ├── mcp_manager.py
│       │   ├── council_manager.py
│       │   ├── ai_agency.py
│       │   ├── model_router.py
│       │   ├── resource_manager.py
│       │   └── logger.py
│       ├── events/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── bus.py
│       │   ├── types.py
│       │   └── handlers.py
│       └── services/
│           ├── __init__.py
│           ├── base.py
│           ├── registry.py
│           ├── planning.py
│           ├── coding.py
│           ├── review.py
│           ├── testing.py
│           ├── deployment.py
│           ├── operations.py
│           ├── learning.py
│           ├── memory.py
│           ├── skill.py
│           ├── council.py
│           └── mcp.py
└── tests/
    └── integration/
        └── test_integration.py
```

---

## 14. Dependencies (from pyproject.toml)

**Core:** Python 3.12+, pydantic>=2.0, pyyaml, typer, rich
**Testing:** pytest, pytest-asyncio
**Missing per Spec:** structlog (for structured logging), possibly tenacity (retry), networkx (DAG)

---

## 15. Recommended Next Steps (Per Spec Freeze)

1. **Fix 6 Critical Bugs** — Enables 12/21 tests to pass; makes architecture testable
2. **Apply `kw_only=True` to `Event`** — Unblocks event extensibility
3. **Replace `datetime.utcnow()`** — Python 3.12+ compliance
4. **Decide: Global Singletons vs. DI** — Document decision in spec
5. **Add Event Schema Registry** — Required for production event evolution
6. **Write Architecture Specification v1.0** — Using the TOC below