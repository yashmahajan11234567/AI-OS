# AI-OS Architecture Specification v1.0 — Recommended Table of Contents

**Status:** DRAFT — Based on complete implementation inventory (ARCHITECTURAL_INVENTORY.md)  
**Purpose:** Freeze the architecture before continuing development; document what EXISTS vs. what PLANNED  
**Source:** Full repository inspection — 15 core modules, 17 services, 90+ events, 21 integration tests (12 failing)

---

## Part 0: Front Matter

| Section | Description |
|---------|-------------|
| **0.1** | Document Control (version, authors, status, review history) |
| **0.2** | Scope & Non-Goals (what this spec covers; what is explicitly out of scope) |
| **0.3** | Terminology & Conventions (Event vs. Command vs. Query; Kernel vs. Service; Correlation vs. Causation) |
| **0.4** | Architectural Principles (Event-First, Kernel as Orchestrator, No Direct Calls, Singleton Accessors, Capability vs. Engineering Services) |

---

## Part 1: System Overview

| Section | Description |
|---------|-------------|
| **1.1** | High-Level Architecture Diagram (Kernel + EventBus + 17 Services + 13 Managers) |
| **1.2** | Component Taxonomy — **Kernel Components (4)**, **Kernel Capability Managers (9)**, **Engineering Services (8)**, **Capability Facade Services (4)** |
| **1.3** | Data Flow Overview — TaskCreated → Planning → Coding → Review → Testing → Deployment → Operations → Learning (all via events) |
| **1.4** | Deployment Topology (single-process, in-memory EventBus; future: distributed bus) |
| **1.5** | Version & Compatibility Matrix (Python 3.12+, Pydantic v2, Event Schema Versioning Strategy) |

---

## Part 2: Event System Specification

| Section | Description |
|---------|-------------|
| **2.1** | **Event Base Contract** — `Event` dataclass fields, `kw_only=True` requirement, immutability, serialization (`to_dict`/`from_dict`) |
| **2.2** | **EventType Enum** — Complete catalog of 90+ event types grouped by domain (table with event_type, payload schema, producer, consumers) |
| **2.3** | **Event Bus Contract** — `EventBus` interface: `subscribe`, `unsubscribe`, `publish` (sync), `publish_async`, `get_history`, `get_stats`, `shutdown` |
| **2.4** | **Subscription Model** — `Subscription` dataclass, filter functions, wildcard (`*`) matching, sync vs. async handlers, error handling policy |
| **2.5** | **Correlation & Causation** — `correlation_id` (workflow trace), `causation_id` (direct cause), propagation rules, debugging/tracing |
| **2.6** | **Event Versioning & Schema Registry** — **DECISION NEEDED**: How schema evolution works (Avro? JSON Schema? pydantic models as source of truth?) |
| **2.7** | **Handler Decorators** — `@handler_for(EventType)`, `@async_handler_for(EventType)` — metadata attachment, auto-registration |

---

## Part 3: Hermes Kernel Specification

| Section | Description |
|---------|-------------|
| **3.1** | **Kernel Responsibilities** — What the kernel owns (4 core components) vs. what it does NOT own (engineering logic) |
| **3.2** | **Kernel Configuration** — `KernelConfig` schema, defaults, environment overrides |
| **3.3** | **Kernel Lifecycle** — `start()` → init core → init registry → start services → emit `KernelStarted`; `stop()` → stop services → emit `KernelStopped` → shutdown bus |
| **3.4** | **Global Singleton Registry** — All 13 `get_xxx()`/`set_xxx()` accessors, initialization order, circular import prevention, testing strategy |
| **3.5** | **Service Registration** — `register_service()`, `get_service()`, integration with ServiceRegistry |
| **3.6** | **Kernel Statistics** — `get_stats()` output schema (kernel, event_bus, resource_manager, services) |
| **3.7** | **Kernel Management API** — `run_kernel()`, `stop_kernel()`, `get_kernel()`, `execute_with_kernel()` (async context manager) |

---

## Part 4: Core Managers (Kernel Capabilities)

*Each manager gets a subsection with: Purpose, Public API, State Model, Events Emitted/Consumed, Configuration, Persistence, Testing Notes*

| Section | Manager | Key Spec Items |
|---------|---------|----------------|
| **4.1** | **StateManager** | `StateScope` enum (4), `get_state`/`set_state`/`snapshot`/`restore`, persistence format, history retention |
| **4.2** | **WorkflowManager** | `WorkflowDefinition`/`WorkflowStep` schema, DAG validation, parallel execution semantics, step handler registration, checkpoint integration, RCA routing |
| **4.3** | **CheckpointManager** | `Checkpoint` schema, disk format (JSON), retention/pruning policy, restore semantics, **BUG FIX: allow first checkpoint without pre-state** |
| **4.4** | **RetryManager** | `RetryPolicy`/`RetryStrategy` (4), `RetryBudget` semantics (**FIX: max_retries = retry count, not total calls**), budget exhaustion → `RetryBudgetExhausted` event |
| **4.5** | **RootCauseAnalyzer** | `FailureCategory` (8), `FailureSeverity` (4), `RecoveryAction` (7), keyword classification rules (with "timeout" fix), service responsibility mapping |
| **4.6** | **MemoryManager** | `MemoryType` (5), `MemoryBackend` ABC, `InMemoryBackend`/`FileMemoryBackend`, consolidation pipeline, TTL, query API |
| **4.7** | **SkillManager** | `Skill` schema, discovery protocol, built-in skills (4), marketplace extension point, execution sandboxing |
| **4.8** | **MCPManager** | `MCPTransport` (4), server config schema, connection lifecycle, tool registry, call timeout/retries |
| **4.9** | **CouncilManager** | `CouncilRole` (5), `ConsensusAlgorithm` (5), session/proposal/vote/decision lifecycle, dissent handling |
| **4.10** | **AIAgencyService** | 9 Agent specifications (Security, Performance, Chaos, Accessibility, Documentation, Concurrency, BugHunter, Architecture, FinalJudge), audit event pairs, orchestration |
| **4.11** | **ModelRouter** | Capability-based routing, cost optimization, fallback chains, model registry schema |
| **4.12** | **ResourceManager** | `ResourceType` (7), allocation/quota/wait-queue/TTL, cleanup task, stats |

---

## Part 5: Service Framework Specification

| Section | Description |
|---------|-------------|
| **5.1** | **BaseService Contract** — Abstract methods: `on_start()`, `on_stop()`, `on_health_check()`; `subscribe()`/`emit()` helpers; `depends_on` declaration; status lifecycle (`CREATED→STARTING→RUNNING/STOPPED/FAILED/DEGRADED`) |
| **5.2** | **ServiceRegistry** — Topological sort by `depends_on`, parallel start where independent, health check aggregation, `ServiceStarted`/`ServiceStopped` events |
| **5.3** | **Service Metadata** — `name`, `version`, `description`, `depends_on` — single source of truth (remove `ServiceInfo` duplication) |
| **5.4** | **Testing Contract** — Test double requirements (must match `BaseService.__init__` signature), fixture patterns |

---

## Part 6: Engineering Services Specification (8)

*Each service: Purpose, Consumed Events (with payload), Emitted Events (with payload), API Methods, Dependencies, State, Configuration, Error Handling, Testing Scenarios*

| Section | Service | Key Events |
|---------|---------|------------|
| **6.1** | **PlanningService** | Consumes: `PlanningRequested`, `PlanRejected` → Emits: `PlanningCompleted`, `PlanningFailed`, `TaskCreated` |
| **6.2** | **CodingService** | Consumes: `CodingStarted`, `ReviewApproved` → Emits: `CodeGenerated`, `CodingCompleted`, `CodingFailed`, `CodeReviewRequested` |
| **6.3** | **ReviewService** | Consumes: `CodeReviewRequested` → Emits: `ReviewStarted`, `ReviewApproved`, `ReviewRejected`, `ReviewFailed`, `SecurityIssueFound`, `PerformanceIssueFound` |
| **6.4** | **TestingService** | Consumes: `ReviewApproved`, `TestingStarted` → Emits: `TestGenerated`, `TestsPassed`, `TestsFailed`, `TestingCompleted`, `TestingFailed` |
| **6.5** | **DeploymentService** | Consumes: `DeploymentRequested` → Emits: `DeploymentStarted`, `DeploymentCompleted`, `DeploymentFailed`, `DeploymentRolledBack` |
| **6.6** | **OperationsService** | Consumes: `DeploymentCompleted`, `ProductionIncident`, `MetricsAlert`, `LogAnomalyDetected`, `UserFeedbackReceived` → Emits: `TaskCreated` (follow-ups) |
| **6.7** | **LearningService** | Consumes: `RootCauseResolved`, `WorkflowCompleted`, `TestingCompleted`, `DeploymentCompleted` → Emits: `LearningCaptured` |
| **6.8** | **MemoryService** (facade) | Consumes: `LearningCaptured`, `CheckpointCreated` → Emits: `MemoryStored`, `MemoryRetrieved`, `MemoryUpdated`, `MemoryConsolidated` |

---

## Part 7: Capability Facade Services (4)

| Section | Service | Wraps Manager |
|---------|---------|---------------|
| **7.1** | **SkillService** | `SkillManager` |
| **7.2** | **CouncilService** | `CouncilManager` |
| **7.3** | **MCPService** | `MCPManager` |
| **7.4** | **MemoryService** | `MemoryManager` |

*Each: API surface, event emission mapping, auto-discovery behavior (e.g., SkillService on `KernelStarted`)*

---

## Part 8: Configuration System Specification

| Section | Description |
|---------|-------------|
| **8.1** | **Configuration Model** — `AppConfig`, `WorkspaceConfig`, `LogsConfig`, `Environment` enum |
| **8.2** | **Layered Loading** — 4-layer merge: Defaults → `config/app.yaml` → `config/{env}.yaml` → Environment Variables (dotted paths) |
| **8.3** | **Validation Rules** — Path existence/permissions, cross-field consistency, semver pattern, environment-specific requirements |
| **8.4** | **Configuration Files** — `config/app.yaml` schema, `config/global.yaml` (planned), `config/logging.yaml` (planned) |
| **8.5** | **CLI Validation** — `aios doctor` behavior, output format, exit codes |

---

## Part 9: CLI Command Specification

| Section | Command Group | Status |
|---------|---------------|--------|
| **9.1** | `aios version` | ✅ Implemented |
| **9.2** | `aios doctor` | ✅ Implemented |
| **9.3** | `aios kernel start/stop/status/stats` | ✅ Basic impl |
| **9.4** | `aios workflow create/run/status/recover/list` | ❌ Spec only |
| **9.5** | `aios service list/start/stop/logs/health` | ❌ Spec only |
| **9.6** | `aios event publish/subscribe/history/stats` | ❌ Spec only |
| **9.7** | `aios checkpoint create/list/restore/delete` | ❌ Spec only |
| **9.8** | `aios memory query/store/list/consolidate` | ❌ Spec only |
| **9.9** | `aios skill install/list/run/discover` | ❌ Spec only |
| **9.10** | `aios mcp connect/list/tools/call` | ❌ Spec only |
| **9.11** | `aios council convene/propose/vote/decide/dissent/list` | ❌ Spec only |
| **9.12** | `aios learning capture/query/stats` | ❌ Spec only |

---

## Part 10: Observability & Logging Specification

| Section | Description |
|---------|-------------|
| **10.1** | **Structured Logging** — Migration from stdlib `logging` to `structlog` (decision recorded), JSON output, correlation ID propagation |
| **10.2** | **Log Levels & Formats** — Per-service config, production vs development |
| **10.3** | **Metrics** — Prometheus exposition format, key metrics per component (events published/consumed, latency, error rates) |
| **10.4** | **Tracing** — Correlation ID flow, OpenTelemetry integration (planned) |
| **10.5** | **Health Checks** — `/health` endpoint spec, liveness vs readiness, dependencies |

---

## Part 11: Testing Strategy & Contracts

| Section | Description |
|---------|-------------|
| **11.1** | **Test Pyramid** — Unit (per module), Integration (EventBus, Workflow, Retry, Checkpoint, RCA, Registry), E2E (CLI + kernel + workflow) |
| **11.2** | **Test Fixtures** — `event_bus`, `kernel`, `workflow_manager`, `retry_manager`, `checkpoint_manager`, `root_cause_analyzer`, `service_registry` |
| **11.3** | **Contract Tests** — Event schema validation, Service lifecycle contract, Kernel start/stop contract |
| **11.4** | **Known Test Failures & Fixes** — Document the 6 critical bugs and their test expectations |
| **11.5** | **Property-Based Testing** — Event bus ordering, retry budget invariants, checkpoint persistence |

---

## Part 12: Security & Safety

| Section | Description |
|---------|-------------|
| **12.1** | **Skill Execution Sandbox** — Isolation model for shell/file/web skills |
| **12.2** | **MCP Server Trust** — Connection verification, tool allow-lists |
| **12.3** | **Event Bus Authorization** — Service identity, event signing (future) |
| **12.4** | **Secret Management** — Config loading, environment variable handling, no secrets in events |
| **12.5** | **AI Agency Safety** — FinalJudge as gate, dissent escalation, human-in-the-loop triggers |

---

## Part 13: Operational Procedures

| Section | Description |
|---------|-------------|
| **13.1** | **Kernel Startup/Shutdown** — Order, timeouts, graceful degradation |
| **13.2** | **Checkpoint/Recovery** — When checkpoints created, how to restore, RPO/RTO targets |
| **13.3** | **Failure Routing** — RCA → RecoveryAction → responsible service, escalation paths |
| **13.4** | **Capacity Planning** — ResourceManager quotas, EventBus history sizing, Memory backend scaling |
| **13.5** | **Upgrade/Migration** — Event schema versioning, config migration, state migration |

---

## Part 14: Extension Points & Plugin Architecture

| Section | Description |
|---------|-------------|
| **14.1** | **Custom Events** — How to define new `EventType`, register handlers, schema registration |
| **14.2** | **Custom Services** — Implementing `BaseService`, registering with kernel, dependency declaration |
| **14.3** | **Custom Skills** — Skill manifest, discovery, loading, execution interface |
| **14.4** | **Custom Memory Backends** — Implementing `MemoryBackend` ABC, registration |
| **14.5** | **Custom MCP Transports** — Transport interface, registration |
| **14.6** | **Custom AI Agency Agents** — Agent interface, registration, audit event conventions |

---

## Part 15: Appendices

| Appendix | Description |
|----------|-------------|
| **A** | **Complete Event Catalog** — All 90+ event types with payload JSON Schema |
| **B** | **Component Dependency Graph** — Visual (Mermaid) + adjacency matrix |
| **C** | **Configuration Reference** — All YAML keys with types, defaults, env var mapping |
| **D** | **API Reference** — Public Python API (`aios.*` exports) |
| **E** | **Glossary** — Kernel, Service, Event, Correlation ID, Causation ID, Checkpoint, Retry Budget, RCA, etc. |
| **F** | **Migration History** — Phase 1-10 summary, decisions, deprecated patterns |
| **G** | **Open Decisions** — Items requiring architectural decision before implementation continues |

---

## Part 16: Open Architectural Decisions (Must Resolve Before v1.0 Freeze)

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **Global Singletons vs. Dependency Injection** | Keep `get_xxx()` globals / Migrate to DI container / Hybrid (globals for kernel, DI for services) | Document current pattern; plan DI migration in v1.1 |
| 2 | **Event Schema Registry** | Pydantic models as source of truth / JSON Schema files / Avro / Protobuf | Use Pydantic models + export JSON Schema for external consumers |
| 3 | **`datetime.utcnow()` Replacement** | `datetime.now(timezone.utc)` / `datetime.utcnow()` with warning suppression / pendulum | `datetime.now(timezone.utc)` everywhere |
| 4 | **Retry Semantics** | `max_retries` = retry COUNT (current impl) / `max_retries` = TOTAL attempts - 1 | Align with industry standard: `max_retries` = retry count (1 initial + N retries = N+1 total) |
| 5 | **Structured Logging Library** | `structlog` / stdlib `logging` with JSON formatter / `loguru` | `structlog` (industry standard for structured logging) |
| 6 | **Checkpoint Initial State** | Require pre-seeded state / Auto-create minimal / Error with clear message | Auto-create minimal workflow state on first checkpoint |
| 7 | **Service Info Duplication** | Keep `ServiceInfo` / Remove, use `BaseService` class attrs | Remove `ServiceInfo`; single source of truth |
| 8 | **Magic Strings in Subscriptions** | Keep strings / Use `EventType` enum everywhere | Migrate all to `EventType` enum for type safety |

---

## Cross-Reference: Spec Sections → Implementation Files

| Spec Part | Primary Implementation Files |
|-----------|------------------------------|
| Part 2 (Events) | `src/aios/events/base.py`, `bus.py`, `types.py`, `handlers.py` |
| Part 3 (Kernel) | `src/aios/core/kernel.py`, `kernel_management.py` |
| Part 4 (Managers) | `src/aios/core/state.py`, `workflow.py`, `checkpoint.py`, `retry.py`, `root_cause.py`, `memory.py`, `skill_manager.py`, `mcp_manager.py`, `council_manager.py`, `ai_agency.py`, `model_router.py`, `resource_manager.py`, `logger.py` |
| Part 5 (Service Framework) | `src/aios/services/base.py`, `registry.py` |
| Part 6 (Engineering Services) | `src/aios/services/planning.py`, `coding.py`, `review.py`, `testing.py`, `deployment.py`, `operations.py`, `learning.py`, `memory.py` |
| Part 7 (Capability Services) | `src/aios/services/skill.py`, `council.py`, `mcp.py` |
| Part 8 (Config) | `src/aios/config/models.py`, `loader.py`, `validator.py`, `defaults.py` |
| Part 9 (CLI) | `src/aios/cli/main.py`, `commands/kernel/__init__.py`, `commands/doctor/__init__.py` |
| Part 11 (Tests) | `tests/integration/test_integration.py` |

---

## Document Control

| Field | Value |
|-------|-------|
| **Document** | AI-OS Architecture Specification v1.0 — Table of Contents |
| **Date** | 2026-07-28 |
| **Status** | DRAFT — Awaiting review & approval before full spec writing |
| **Prerequisite** | Fix 6 critical bugs (ARCHITECTURAL_INVENTORY.md §11) |
| **Next Step** | Stakeholder review of TOC → Write Part 0-2 (Event System) first |