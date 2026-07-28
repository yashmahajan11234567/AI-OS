# AI-OS Event-Driven Architecture Migration Plan

## Overview
Migrate AI-OS from a traditional pipeline architecture (Planning → Coding → Review → Testing → Deployment) to an Event-Driven Software Engineering Operating System with Hermes as the Kernel orchestrating Engineering Services through an Event Bus.

## Current State Analysis
**Phase 1 - Foundation (Current):**
- `src/aios/cli/` - Typer CLI with `version` and `doctor` commands
- `src/aios/config/` - Configuration loading, validation, models (Pydantic v2)
- `src/aios/core/` - Constants and version
- Empty directories: agents, deployment, integrations, mcp, memory, observers, planner, research, skills, testing, utils, workflow

**Package:** `ai-os` (src-layout, Python 3.12+, Typer, Rich, Pydantic, PyYAML)

---

## Target Architecture

### Core Components (Hermes Kernel)
```
Hermes Kernel
├── Event Bus                 - Pub/Sub for all inter-service communication
├── Workflow Manager          - Manages workflow state transitions
├── State Manager             - Manages application/workflow state
├── Root Cause Analyzer       - Analyzes failures, routes to responsible service
├── Model Router              - Routes LLM requests to appropriate models
├── Resource Manager          - Manages compute, memory, API quotas
├── Memory Manager            - Manages Working Memory, Claude Memory, Engineering Intelligence, Obsidian, Graphify
├── Skill Manager             - Loads, manages, executes skills
├── MCP Manager               - Manages MCP server connections
├── Council Manager           - Manages council deliberation
├── Logger                    - Centralized logging
├── Checkpoint Manager        - Workflow checkpoints for recovery
├── Retry Manager             - Retry budgets per service
└── Learning Manager          - Captures learnings to Engineering Intelligence
```

### Engineering Services (Event-Driven)
```
Services (never call each other directly - only via events):
├── Planning Service          - Task decomposition, scheduling, resource allocation
├── Coding Service            - Code generation, refactoring, implementation
├── Review Service            - Code review, security, performance, architecture
├── Testing Service           - Test generation, execution, coverage analysis
├── Deployment Service        - Container build, deploy, rollback
├── Operations Service        - Monitoring, logs, metrics, incidents, alerts
├── Learning Service          - Pattern extraction, prompt improvements, architecture decisions
├── Memory Service            - Working/Claude/Engineering/Obsidian/Graphify stores
├── Council Service           - Multi-agent deliberation, consensus
├── Skill Service             - Skill registry, loading, execution, marketplace
├── MCP Service               - MCP server/client management, tool orchestration
└── AI Agency Service         - Security, Performance, Chaos, Accessibility, Documentation, Concurrency, Bug Hunter, Architecture Validator, Final Judge
```

### Event System
```
Core Events:
├── TaskCreated / TaskCompleted / TaskFailed
├── PlanningRequested / PlanningCompleted / PlanningFailed
├── CodingStarted / CodingCompleted / CodingFailed
├── ReviewRequested / ReviewPassed / ReviewFailed / SecurityIssueFound
├── TestingStarted / TestingCompleted / TestingFailed
├── DeploymentStarted / DeploymentSucceeded / DeploymentFailed
├── ProductionIncident / MemoryUpdated / SkillLoaded / CheckpointCreated
├── RetryBudgetExceeded / RootCauseResolved / CheckpointResumed
└── LearningCaptured / PromptImproved / ArchitectureDecisionRecorded
```

### Key Architectural Changes
1. **Pipeline → Event-Driven**: Replace sequential phases with event-driven workflow
2. **Direct Calls → Event Bus**: Services communicate ONLY through events
3. **Fixed Phases → State Transitions**: Workflow manager manages state machine
4. **Infinite Retries → Retry Budgets**: Per-service retry budgets with Root Cause Analysis on exhaustion
5. **No Checkpoints → Checkpoint Manager**: Save state after each major service for recovery
6. **Single Memory → Multi-Memory**: Working, Claude, Engineering Intelligence, Obsidian, Graphify
7. **No AI Agency → AI Agency Service**: Security, Performance, Chaos, Accessibility, Documentation, Concurrency, Bug Hunter, Architecture Validator, Final Judge

---

## Migration Phases

### Phase 1: Foundation (Core Infrastructure) ✅ COMPLETED
- [x] Basic package structure
- [x] CLI framework (Typer)
- [x] Configuration system (Pydantic + YAML)
- [x] Python packaging (pyproject.toml)

### Phase 2: Event Bus & Kernel Core (Week 1-2)
**New Files:**
- `src/aios/events/__init__.py` - Event definitions (dataclasses/enums)
- `src/aios/events/bus.py` - Event bus implementation (pub/sub)
- `src/aios/events/types.py` - Event type definitions
- `src/aios/core/kernel.py` - Hermes kernel core
- `src/aios/core/state.py` - State manager
- `src/aios/core/workflow.py` - Workflow manager
- `src/aios/core/checkpoint.py` - Checkpoint manager
- `src/aios/core/retry.py` - Retry manager with budgets
- `src/aios/core/root_cause.py` - Root cause analyzer
- `src/aios/core/logger.py` - Structured logger

**Modify Existing:**
- `src/aios/__init__.py` - Export new core modules
- `src/aios/config/models.py` - Add event bus, workflow config
- `config/app.yaml` - Add kernel, event bus, services config

### Phase 3: Service Framework (Week 2-3)
**New Files:**
- `src/aios/services/__init__.py` - Service base class and registry
- `src/aios/services/base.py` - BaseService with event subscription
- `src/aios/services/registry.py` - Service discovery and lifecycle

**Service Stubs (implement minimal interface):**
- `src/aios/services/planning/__init__.py`
- `src/aios/services/coding/__init__.py`
- `src/aios/services/review/__init__.py`
- `src/aios/services/testing/__init__.py`
- `src/aios/services/deployment/__init__.py`
- `src/aios/services/operations/__init__.py`
- `src/aios/services/learning/__init__.py`
- `src/aios/services/memory/__init__.py`
- `src/aios/services/council/__init__.py`
- `src/aios/services/skill/__init__.py`
- `src/aios/services/mcp/__init__.py`
- `src/aios/services/ai_agency/__init__.py`

### Phase 4: Memory System (Week 3)
**New Files:**
- `src/aios/memory/__init__.py` - Memory manager
- `src/aios/memory/working.py` - Working memory (short-term)
- `src/aios/memory/claude.py` - Claude memory (session persistence)
- `src/aios/memory/engineering.py` - Engineering Intelligence (long-term learnings)
- `src/aios/memory/obsidian.py` - Obsidian vault integration
- `src/aios/memory/graphify.py` - Graphify knowledge graph
- `src/aios/memory/base.py` - Base memory interface

**Config:**
- `config/memory.yaml` - Memory system configuration

### Phase 5: Skill & MCP Systems (Week 3-4)
**New Files:**
- `src/aios/skills/manager.py` - Skill manager
- `src/aios/skills/registry.py` - Skill registry
- `src/aios/skills/loader.py` - Skill loader (from .claude/skills, marketplace)
- `src/aios/skills/base.py` - Base skill class

- `src/aios/mcp/manager.py` - MCP manager
- `src/aios/mcp/client.py` - MCP client
- `src/aios/mcp/server.py` - MCP server
- `src/aios/mcp/registry.py` - MCP server registry

**Config:**
- `config/skills.yaml` - Skill configuration
- `config/mcps.yaml` - MCP server configuration

### Phase 6: Model Router & Resource Manager (Week 4)
**New Files:**
- `src/aios/core/model_router.py` - Multi-model routing (Claude, local, cloud)
- `src/aios/core/resource_manager.py` - Resource quotas, limits, scheduling

**Config:**
- `config/models.yaml` - Model configurations
- `config/resources.yaml` - Resource limits

### Phase 7: Council & AI Agency (Week 4-5)
**New Files:**
- `src/aios/council/manager.py` - Council manager
- `src/aios/council/deliberation.py` - Deliberation engine
- `src/aios/council/consensus.py` - Consensus algorithms

- `src/aios/ai_agency/security.py` - Security review agent
- `src/aios/ai_agency/performance.py` - Performance review agent
- `src/aios/ai_agency/chaos.py` - Chaos engineering agent
- `src/aios/ai_agency/accessibility.py` - Accessibility agent
- `src/aios/ai_agency/documentation.py` - Documentation agent
- `src/aios/ai_agency/concurrency.py` - Concurrency agent
- `src/aios/ai_agency/bug_hunter.py` - Bug hunter agent
- `src/aios/ai_agency/architecture.py` - Architecture validator agent
- `src/aios/ai_agency/final_judge.py` - Final judge agent

### Phase 8: CLI Integration & Commands (Week 5)
**Modify Existing:**
- `src/aios/cli/main.py` - Add kernel commands
- `src/aios/cli/commands/` - New commands for:
  - `aios kernel start/stop/status`
  - `aios workflow create/run/status/recover`
  - `aios service list/start/stop/logs`
  - `aios event publish/subscribe/history`
  - `aios checkpoint create/list/restore`
  - `aios memory query/store/list`
  - `aios skill install/list/run`
  - `aios mcp connect/list/tools`
  - `aios council convene/propose/vote`
  - `aios learning capture/query`

### Phase 9: Configuration & Documentation (Week 5-6)
**Update Config Files:**
- `config/app.yaml` - Main app config with all services
- `config/global.yaml` - Global settings
- `config/logging.yaml` - Logging configuration
- `config/defaults.yaml` - Default values

**Documentation:**
- `docs/Architecture/event-driven-overview.md`
- `docs/Architecture/event-bus.md`
- `docs/Architecture/workflow-manager.md`
- `docs/Architecture/root-cause-analyzer.md`
- `docs/Architecture/memory-system.md`
- `docs/Guides/migration-guide.md`

### Phase 10: Testing & Verification (Week 6)
**Tests:**
- `tests/test_event_bus.py`
- `tests/test_workflow_manager.py`
- `tests/test_checkpoint_manager.py`
- `tests/test_retry_manager.py`
- `tests/test_root_cause_analyzer.py`
- `tests/test_state_manager.py`
- `tests/test_memory_system.py`
- `tests/test_skill_manager.py`
- `tests/test_mcp_manager.py`
- `tests/integration/test_kernel_workflow.py`

**Verify:**
- `aios version` works
- `aios doctor` validates full config
- `aios kernel start` starts Hermes kernel
- Events flow correctly between services
- Checkpoints save/restore state
- Retry budgets enforced
- Root cause analysis routes failures correctly

---

## File Mapping: Old → New

| Current Path | New Path | Action |
|-------------|----------|--------|
| `src/aios/cli/main.py` | `src/aios/cli/main.py` | Extend with kernel commands |
| `src/aios/cli/commands/doctor/` | `src/aios/cli/commands/doctor/` | Keep, enhance validation |
| `src/aios/config/` | `src/aios/config/` | Extend with service configs |
| `src/aios/core/constants.py` | `src/aios/core/constants.py` | Extend with kernel constants |
| `src/aios/core/version.py` | `src/aios/core/version.py` | Keep |
| `src/aios/core/__init__.py` | `src/aios/core/__init__.py` | Export new core modules |
| `src/aios/__init__.py` | `src/aios/__init__.py` | Export all public APIs |

**New Directories to Create:**
```
src/aios/events/
src/aios/core/ (new modules)
src/aios/services/
src/aios/memory/
src/aios/skills/
src/aios/mcp/
src/aios/council/
src/aios/ai_agency/
src/aios/cli/commands/kernel/
src/aios/cli/commands/workflow/
src/aios/cli/commands/service/
src/aios/cli/commands/event/
src/aios/cli/commands/checkpoint/
src/aios/cli/commands/memory/
src/aios/cli/commands/skill/
src/aios/cli/commands/mcp/
src/aios/cli/commands/council/
src/aios/cli/commands/learning/
```

---

## Risk Mitigation

1. **Don't Break Existing CLI**: Keep `aios version` and `aios doctor` working throughout
2. **Incremental Migration**: Add new modules alongside old ones, switch imports gradually
3. **Config Backwards Compatibility**: Support both old and new config formats during transition
4. **Test Each Phase**: Add tests for each new component before integrating
5. **Preserve Package Structure**: Keep src-layout, don't change import paths for existing code

---

## Success Criteria

- [ ] `aios version` works
- [ ] `aios doctor` validates all config
- [ ] `aios kernel start` starts Hermes kernel with event bus
- [ ] Services register and receive events
- [ ] Workflow executes via state transitions
- [ ] Checkpoint save/restore works
- [ ] Retry budgets enforced, root cause analysis triggers
- [ ] Memory systems operational
- [ ] Skills load and execute
- [ ] MCP connections managed
- [ ] All tests pass
- [ ] Documentation complete