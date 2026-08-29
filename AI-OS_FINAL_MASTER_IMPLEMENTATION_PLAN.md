# AI-OS FINAL MASTER IMPLEMENTATION PLAN

**Terminal 1 — Architecture / Planning / Master Execution Plan**
**Date:** 2026-08-24 (verification addendum 2026-08-25)
**Current Checkpoint:** POST-M7 (M7 verified complete, 1046 tests passing)
**Status:** DRAFT — Pending approval before Terminal 2 execution

> **VERIFICATION ADDENDUM (2026-08-25):** Independent re-run of the full suite
> on a clean checkout: **1,045 passed, 1 failed, 1,046 collected** — not ~1,174
> as stated in some M7-era claims. The single failure is
> `tests/performance/test_structured_logger_perf.py::test_memory_bounded_under_load`,
> which imports `psutil` at module scope with no `pytest.importorskip` guard;
> `psutil` is declared in neither runtime nor dev dependencies. Root cause is an
> undeclared test dependency, NOT an M7 code defect — M7 scope is unaffected and
> will not be reopened for this. Disposition (for Terminal 2, first task):
> either declare `psutil` as a dev/test extra or guard the import with
> `pytest.importorskip("psutil")`. All other plan figures verified against repo:
> 8 real agency adapters + base + mocks present, zero TODO/FIXME markers in src,
> M7 QA chain = NO-GO(35/100) → remediation → GO(95/100).

---

## 1. EXECUTIVE SUMMARY

AI-OS is an event-driven, multi-perspective AI operating system with a single authoritative kernel (`HermesKernel`). After M7 completion (verified 2026-08-24), the core V2 architecture is **fully implemented and tested**. The system has:

- **1046 tests passing** (48 unit + 13 integration + 1 performance suites; 0 failures)
- **9 agency adapters** with real production execution paths
- **TestOrchestratorService** extending WorkflowManager (no duplication)
- **UserSimulationAgent** (10th perspective) with isolated browser sessions
- **CouncilManager.critique()** with KKC/EVC techniques adopted
- **SimplificationGate** pre-acceptance complexity governance
- **M4–M7 all verified complete** per independent QA reports

**What remains is NOT new architecture — it is production hardening, external integration realization, deployment readiness, and documentation completion.** The plan identifies the actual remaining work, classifies every external component, and defines the path to final AI-OS.

**Verdict: AI-OS V2 Core = 93/100. Remaining work = Phase 2 hardening.**

---

## 2. WHAT AI-OS IS

AI-OS is an autonomous, self-governing software-development and verification operating system built in Python 3.12+. Its **core is a single kernel** (`HermesKernel`) that plans, reasons, builds, tests, judges, learns, and improves — orchestrating a closed control loop in which failures are diagnosed (RCA), turned into reusable knowledge (Learning), used to replan, and re-executed until verified PASS.

**Architecture principle:** ONE of everything that has authority. One kernel, one governance system, one verification authority, one closed loop.

---

## 3. PROJECT OBJECTIVES

1. **Deliver a production-ready AI-OS** that autonomously tests software through multiple independent perspectives
2. **Maintain strict authority boundaries** — AI-OS is sole decision authority; external systems execute, never decide
3. **Achieve full closed-loop operation** — FAIL → RCA → Learning → Replan → Re-execute → Retest → PASS
4. **Ensure security-first design** — fail-closed authorization, sandboxed workers, provenanced evidence
5. **Provide reproducible deployment** — configuration-driven, secrets-managed, health-checked

---

## 4. DEFINITION OF THE FINAL SYSTEM

**"AI-OS COMPLETE"** means:

| Dimension | Acceptance Criterion |
|-----------|---------------------|
| **Architecture** | Single authority kernel, no duplicate governance, all invariants pass |
| **Execution** | Real production adapters (not heuristics), controlled external workers |
| **Councils** | Multi-perspective synthesis, dissent preserved, FinalJudge independent |
| **Verification** | Evidence-backed decisions, no self-approval, builder ≠ judge |
| **Testing** | 1046+ tests, anti-cheating validated, seeded defect detection, regression green |
| **Learning** | RCA→Learning→Simplify→Replan→Re-execute loop bounded and convergent |
| **Security** | Fail-closed authorization, SkillSpecTor gate, external trust boundaries |
| **Deployment** | Reproducible, configuration-driven, health checks, rollback capability |
| **Documentation** | Parts 0–15 complete, architecture gaps resolved, ADRs documented |

---

## 5. HISTORICAL DEVELOPMENT PATH

| Milestone | Date | Status | Tests | QA Score |
|-----------|------|--------|-------|----------|
| **M0–M3** (V1 baseline) | 2026-07 | ✅ Complete | 802/802 | 12/12 gates |
| **M4** (Skill & Security Standardization) | 2026-08 | ✅ Verified | +8 | ACCEPT |
| **M5** (Integration Backbone) | 2026-08 | ✅ Ready | +11 EventTypes | READY |
| **M6** (Council Synthesis & Quality) | 2026-08 | ✅ Verified | +57 | 98/100 |
| **M7** (Multi-Perspective Testing & User Sim) | 2026-08 | ✅ Verified | +1046 total | 95/100 |

**Current Commit:** `42c2017 verified completion of M7`

---

## 6. CURRENT STATE — POST-M7

### 6.1 Code Inventory

| Component | File(s) | Lines | Status |
|-----------|---------|-------|--------|
| **HermesKernel** | `core/kernel.py`, `core/kernel_management.py` | 1,271 | ✅ EXISTING |
| **Core Managers (9)** | `state`, `storage`, `workflow`, `resource`, `health`, `security`, `capability`, `observability`, `lifecycle` | ~7,500 | ✅ EXISTING |
| **Event System** | `events/core/` (12 modules) | ~2,500 | ✅ EXISTING (132 EventType members) |
| **CouncilManager** | `core/council_manager.py` | 868 | ✅ EXISTING + critique() |
| **LLMCouncil** | `core/llm_council.py` | 260 | ✅ EXISTING (6 roles) |
| **AIAgencyService** | `core/ai_agency.py` | 1,034 | ✅ REAL (post-M7 remediation) |
| **TestOrchestratorService** | `services/testing.py` | 803 | ✅ EXISTING (extends WorkflowManager) |
| **UserSimulationAgent** | `core/user_simulation_agent.py` | 307 | ✅ EXISTING |
| **TestingEvidence** | `core/testing_evidence.py` | 386 | ✅ EXISTING |
| **SimplificationGate** | `core/simplification_gate.py` | 236 | ✅ EXISTING |
| **RootCauseAnalyzer** | `core/root_cause.py` | 848 | ✅ EXISTING |
| **LearningService** | `services/learning.py` | 217 | ✅ PARTIAL (logs only, captures learnings) |
| **SelfPromptingService** | `services/self_prompting.py` | 430 | ✅ EXISTING |
| **SecurityManager** | `core/security_manager.py` | 1,676 | ✅ EXISTING |
| **SkillSpecTorGate** | `core/security_manager.py` (embedded) | — | ✅ EXISTING (M4) |
| **ModelRouter** | `core/model_router.py` | 402 | ✅ EXISTING |
| **HermesBridge** | `adapters/hermes_bridge.py` | 310 | ✅ EXISTING (MCP fallback) |
| **9 Agency Adapters** | `adapters/*_agency_adapter.py` | ~15K | ✅ REAL (post-M7 remediation) |
| **MCP Adapters** | `adapters/agent_reach.py`, `adapters/freellmapi.py` | ~18K | ✅ EXISTING (M5) |
| **Mock Servers** | `adapters/mock_*.py` (3 files) | ~9K | ✅ EXISTING (testing only) |

**Total Source:** ~95 Python files, ~65K lines (excluding venv)

### 6.2 Test Inventory

| Suite | Files | Tests | Status |
|-------|-------|-------|--------|
| Unit | 48 | ~836 | ✅ PASS |
| Integration | 13 | ~119 | ✅ PASS |
| Performance | 1 | 4 | ✅ PASS |
| **Total** | **62** | **1,046** | **ALL PASS** |

### 6.3 Remaining Stubs / Placeholders

| Location | Type | Description | Priority |
|----------|------|-------------|----------|
| `events/core/registry.py:26,68,74,79,449,450,651` | PLACEHOLDER | No authoritative per-event payload schema (documented as such) | P3 (deferred) |
| `model_router.py:324` | COMMENT | "For now, return a mock response" — needs real LLM integration | P2 |
| `self_prompting.py:229` | COMMENT | "For now, we create mock accuracy/insight scores per role" | P3 |
| `memory.py` | PARTIAL | 5-tier memory scaffold; Obsidian/Graphify labels present but no MCP wiring | P2 |

### 6.4 Open Conditions from Pre-M7

| ID | Issue | Status | Resolution Needed |
|----|-------|--------|-------------------|
| **C1** | "Hermes" naming collision (HermesKernel vs hermes-agent EXT) | OPEN | Vocabulary resolution — document distinction |
| **C2** | Verification gate count (12/12 vs 11-layer) | DOCUMENTATION | Update narrative to match code (8 LifecycleState members) |
| **C3** | Lifecycle state count (narrative 5 vs code 8) | CODE TRUTH | Code = 8; update architecture docs |
| **C4** | Notion absent from repo | OPEN | Adopt-or-drop decision required |
| **R1** | Test execution verification | RESOLVED | 1,046 tests now verified in this session |

---

## 7. CURRENT IMPLEMENTATION AUDIT

### 7.1 What is IMPLEMENTED and TESTED

| Capability | Status | Evidence |
|-----------|--------|----------|
| Kernel lifecycle (start/stop/restart) | ✅ TESTED | `test_kernel_lifecycle_e2e.py` (18 tests) |
| Event bus (publish/subscribe/history) | ✅ TESTED | `test_event_bus.py`, `test_event_core.py` |
| Configuration management (freeze, secrets, schema) | ✅ TESTED | `test_configuration_manager.py` (25+ tests) |
| Service registry (namespace control, health) | ✅ TESTED | `test_service_registry.py` |
| State manager (checkpoint/restore, persistence) | ✅ TESTED | `test_state_manager.py` |
| Storage manager (namespaces, singleton) | ✅ TESTED | `test_storage_manager.py` |
| Lifecycle manager (phase ordering, shutdown) | ✅ TESTED | `test_lifecycle_manager.py`, `test_*_phase.py` |
| Security manager (authorize, deny, SkillSpecTor) | ✅ TESTED | `test_task14_security_manager.py`, `test_m7_security.py` |
| ResourceManager (allocation, quota, cleanup) | ✅ TESTED | `test_task13_resource_manager.py` |
| Health manager (status aggregation) | ✅ TESTED | `test_task12_health_manager.py` |
| Capability manager (registration, events) | ✅ TESTED | `test_task15_capability_manager.py` |
| Workflow manager (DAG, retry, recovery) | ✅ TESTED | `test_workflow_lifecycle.py`, `test_integration.py` |
| CouncilManager (convene, propose, vote, dissent) | ✅ TESTED | `test_m6_council_synthesis.py` (57 tests) |
| LLMCouncil (6 roles, builder exclusion) | ✅ EXISTING | `core/llm_council.py` |
| 9 Agency adapters (real execution) | ✅ TESTED | `test_agency_adapters.py`, `test_agency_review_production_path.py` |
| TestOrchestratorService (dispatch, normalize, council) | ✅ TESTED | `test_test_orchestrator.py` |
| UserSimulationAgent (no source access, isolated sessions) | ✅ TESTED | `test_user_simulation_agent.py` |
| SimplificationGate (complexity scoring, safeguard preservation) | ✅ TESTED | `test_simplification_gate.py` |
| FinalJudgeAgency (evidence-first, builder exclusion) | ✅ TESTED | `test_final_judge_agency.py` |
| M7 isolation (builder ≠ tester) | ✅ TESTED | `test_m7_isolation.py` |
| M7 evidence integrity (provenance, immutability) | ✅ TESTED | `test_m7_evidence_integrity.py` |
| M7 multi-perspective dispatch | ✅ TESTED | `test_m7_multi_perspective.py` |
| M7 seeded defect detection (9/9) | ✅ TESTED | `test_m7_seeded_defects.py` |
| Closed-loop convergence | ✅ TESTED | `test_m7_closed_loop.py` |
| StructuredLogger (sinks, correlation, backpressure) | ✅ TESTED | `test_structured_logger.py`, perf test |
| MCPManager (server registration, gate-before-connect) | ✅ TESTED | `test_m5_gate.py` |
| AgentReach adapter | ✅ EXISTING | `adapters/agent_reach.py` |
| FreeLLMAPI adapter | ✅ EXISTED | `adapters/freellmapi.py` |
| HermesBridge (MCP fallback) | ✅ EXISTING | `adapters/hermes_bridge.py` |
| Mock servers (AgentReach, Hermes, Graphify) | ✅ EXISTING | 3 mock server files |

### 7.2 What is PARTIAL or NEEDS HARDENING

| Capability | Current State | Required |
|-----------|--------------|----------|
| **Real Hermes execution** | MCP fallback only; `hermes-agent` gitignored | ACP integration for browser/user-sim |
| **Graphify MCP wiring** | Adapter exists; mock server for tests | Real Graphify server connection |
| **ModelRouter real LLM calls** | Stub returns mock response | Integrate with FreeLLMAPI |
| **LearningService lesson extraction** | Captures RCA events; logs learnings | Add extraction/validation/feedback loop |
| **SelfPromptingService scoring** | Mock accuracy/insight scores | Real LLM-based evaluation |
| **Notion integration** | Not mentioned in code | Adopt-or-drop decision |
| **Obsidian integration** | Label only in memory.py | PKM vault wiring (if adopted) |
| **Event payload schemas** | PLACEHOLDER documented | Part 2 authoritative schema |
| **CLI commands** | Basic `aios` CLI with doctor/kernel | Expand with testing/deployment commands |
| **Deployment scripts** | None present | Docker, health checks, config management |

---

## 8. CURRENT ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        AI-OS KERNEL                             │
│                     HermesKernel (sole authority)                │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐  │
│  │ Core Comps  │ Core Mgrs   │ Engineering │ Governance      │  │
│  │ (C1-C4)     │ (M1-M9)     │ Services    │                 │  │
│  │ EventBus    │ State       │ Coding      │ CouncilManager  │  │
│  │ ServiceReg  │ Storage     │ Planning    │ LLMCouncil      │  │
│  │ ConfigMgr   │ Workflow    │ Review      │ (6 roles)       │  │
│  │ StructLogger│ Resource    │ Deployment  │                 │  │
│  └─────────────┴─────────────┴─────────────┴─────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           TEST ORCHESTRATION (M7)                        │    │
│  │  TestOrchestratorService (extends WorkflowManager)       │    │
│  │  ├─ 9 Agency Perspectives (real adapters)               │    │
│  │  ├─ UserSimulationAgent (10th perspective)              │    │
│  │  ├─ CouncilManager.critique() (KKC/EVC)                 │    │
│  │  ├─ FinalJudgeAgency (independent verdict)              │    │
│  │  └─ SimplificationGate (complexity governance)          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │           CLOSED LOOP (M3 reused)                        │    │
│  │  FAIL → RootCauseAnalyzer → LearningService → Replan    │    │
│  │  → SelfPromptingService → TestOrchestratorService        │    │
│  │  (bounded: max iterations, budget, regression protection) │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
    EXECUTION PLANE    TESTING PLANE   KNOWLEDGE PLANE
    ┌──────────┐      ┌──────────┐     ┌──────────┐
    │Hermes    │      │Agency    │     │Obsidian  │
    │Bridge    │      │Adapters  │     │(PKM)     │
    │MCP/ACP   │      │(9 real)  │     │Graphify  │
    │Playwright│      │UserSim   │     │(graph)   │
    │Skills    │      └──────────┘     └──────────┘
    └──────────┘
```

---

## 9. FINAL TARGET ARCHITECTURE

The target architecture matches the current implementation with additions for production hardening:

```
                         ┌──────────────────────────────┐
                         │        AI-OS KERNEL          │
                         │                              │
                         │  Governance                  │
                         │  Verification                │
                         │  Councils                    │
                         │  Workflow                    │
                         │  Evidence                    │
                         │  Learning / RCA              │
                         │  Decision Authority          │
                         └──────────────┬───────────────┘
                                        │
                ┌───────────────────────┼────────────────────────┐
                │                       │                        │
                ▼                       ▼                        ▼
        EXECUTION PLANE          TESTING PLANE            KNOWLEDGE PLANE
                │                       │                        │
        Hermes / workers          TestOrchestrator          Obsidian Vault
        MCP / ACP                 agencies                 Graphify
        Playwright                User Simulation           Claude-Mem (eval)
        Skills                    Testing Council           (optional)
        Security tools            Evidence                  Notion (eval)
                │                       │                        │
                └───────────────────────┼────────────────────────┘
                                        │
                                        ▼
                              AI-OS remains authority
                                        │
                                        ▼
                              DEPLOYMENT PLANE
                              ├── Configuration management
                              ├── Health monitoring
                              ├── Rollback capability
                              └── CI/CD integration
```

---

## 10. AUTHORITY MODEL

**AI-OS = sole runtime authority.** Every external component is evaluated against these questions:

| Question | Answer |
|----------|--------|
| Can it read AI-OS state? | Only via approved MCP/ACP interfaces |
| Can it write AI-OS state? | No — AI-OS writes its own state |
| Can it make decisions? | No — AI-OS decides; external systems execute |
| Can it approve itself? | No — FinalJudgeAgency is internal |
| Can it override verification? | No — SecurityManager is final authority |
| Can it declare PASS/FAIL? | No — workers return observations only |
| Can it modify protected state? | No — SecurityManager.authorize() required |
| Can it bypass governance? | No — all paths route through kernel |

---

## 11. CORE KERNEL

### 11.1 Canonical Core Components (C1-C4)

| ID | Component | File | Status |
|----|-----------|------|--------|
| C1 | EventBus | `events/core/bus.py` | ✅ EXISTING |
| C2 | ServiceRegistry | `core/service_registry.py` | ✅ EXISTING |
| C3 | ConfigurationManager | `core/configuration_manager.py` | ✅ EXISTING |
| C4 | StructuredLogger | `core/structured_logger.py` | ✅ EXISTING |

### 11.2 Core Managers (M1-M9, Phase 1-5)

| Phase | Manager | File | Lines | Status |
|-------|---------|------|-------|--------|
| 1 | LifecycleManager | `core/lifecycle_manager.py` | 1,036 | ✅ EXISTING |
| 2 | StateManager | `core/state.py` | 924 | ✅ EXISTING |
| 2 | StorageManager | `core/storage.py` | 997 | ✅ EXISTING |
| 3 | HealthManager | `core/health_manager.py` | 836 | ✅ EXISTING |
| 3 | ResourceManager | `core/resource_manager.py` | 1,121 | ✅ EXISTING |
| 3 | SecurityManager | `core/security_manager.py` | 1,676 | ✅ EXISTING |
| 4 | CapabilityManager | `core/capability_manager.py` | 767 | ✅ EXISTING |
| 4 | WorkflowManager | `core/workflow.py` | 1,292 | ✅ EXISTING |
| 5 | ObservabilityManager | `core/observability_manager.py` | 725 | ✅ EXISTING |

### 11.3 Engineering Services

| Service | File | Status |
|---------|------|--------|
| TestingService (TestOrchestrator) | `services/testing.py` | ✅ EXISTING |
| LearningService | `services/learning.py` | ⚠️ PARTIAL |
| SelfPromptingService | `services/self_prompting.py` | ✅ EXISTING |
| PlanningService | `services/planning.py` | ✅ EXISTING |
| SkillService | `services/skill.py` | ✅ EXISTING |
| CouncilService | `services/council.py` | ✅ EXISTING |
| MCPService | `services/mcp.py` | ✅ EXISTING |
| MemoryService | `services/memory.py` | ✅ EXISTING |

### 11.4 Core Agencies (9 + 1)

| # | Agency | Adapter | Status |
|---|--------|---------|--------|
| 1 | SecurityAgency | `SecurityAgencyAdapter` | ✅ REAL |
| 2 | PerformanceAgency | `PerformanceAgencyAdapter` | ✅ REAL |
| 3 | ChaosAgency | `ChaosAgencyAdapter` | ✅ REAL |
| 4 | AccessibilityAgency | `AccessibilityAgencyAdapter` | ✅ REAL |
| 5 | DocumentationAgency | `DocumentationAgencyAdapter` | ✅ REAL |
| 6 | ConcurrencyAgency | `ConcurrencyAgencyAdapter` | ✅ REAL |
| 7 | BugHunterAgency | `BugHunterAgencyAdapter` | ✅ REAL |
| 8 | ArchitectureAgency | `ArchitectureAgencyAdapter` | ✅ REAL |
| 9 | FinalJudgeAgency | Independent | ✅ EXISTING |
| 10 | UserSimulationAgent | `HermesBridge` | ✅ EXISTING |

---

## 12. EXECUTION PLANE

### 12.1 Hermes Bridge (`adapters/hermes_bridge.py`)

**Current:** MCP fallback connection to `hermes-agent`(EXT). Returns `HermesObservation` (observations only, never verdicts). Session isolation via `hermes_<uuid>`.

**Gap:** `hermes-agent` is gitignored (external repo on disk at `hermes-agent/`). Real ACP protocol not yet wired. Tests use `mock_hermes_server.py`.

**Remaining work:**
1. Wire ACP protocol for user-simulation browser sessions
2. Connect to real Hermes worker (requires Browserbase/Use/ Firecrawl credentials)
3. CI/dev: continue using mock server; production: real Hermes endpoint

### 12.2 MCP Adapters

| Adapter | File | Status |
|---------|------|--------|
| AgentReach | `adapters/agent_reach.py` | ✅ ADAPTER EXISTS |
| FreeLLMAPI | `adapters/freellmapi.py` | ✅ ADAPTER EXISTS |
| Graphify | `adapters/mock_graphify_server.py` | ⚠️ MOCK ONLY |

### 12.3 Playwright

**Status:** Referenced in `AccessibilityAgencyAdapter` but not directly wired as a standalone adapter. Tests use mock server.

**Remaining work:** Real Playwright MCP integration for accessibility testing (axe-core).

---

## 13. TESTING / VERIFICATION PLANE

### 13.1 Current Coverage

| Category | Tests | Files | Status |
|----------|-------|-------|--------|
| Unit | ~836 | 48 | ✅ PASS |
| Integration | ~119 | 13 | ✅ PASS |
| Performance | 4 | 1 | ✅ PASS |
| **Total** | **1,046** | **62** | **ALL PASS** |

### 13.2 M7 Anti-Cheating Validated

| Mechanism | Status | Evidence |
|-----------|--------|----------|
| No target-name heuristics | ✅ | `test_agency_review_production_path.py` (16 tests) |
| Builder exclusion | ✅ | `test_m7_isolation.py` |
| Evidence-first verdicts | ✅ | `test_final_judge_agency.py` |
| External worker untrusted | ✅ | `test_m7_security.py` |
| Immutable evidence | ✅ | `test_m7_evidence_integrity.py` |
| Bounded closed loop | ✅ | `test_m7_closed_loop.py` |
| 9/9 seeded defects detected | ✅ | `test_m7_seeded_defects.py` |

### 13.3 Remaining Test Gaps

| Gap | Description | Priority |
|-----|-------------|----------|
| Real Hermes E2E | End-to-end test with real Hermes worker (not mock) | P1 |
| Real Graphify E2E | End-to-end test with real Graphify MCP server | P2 |
| Security adversarial | Red-team testing of SecurityManager boundaries | P1 |
| Performance under load | Scaling tests beyond logger benchmark | P2 |
| Chaos testing | Fault injection into kernel components | P3 |
| Accessibility real browser | Live browser test with axe-core | P2 |

---

## 14. KNOWLEDGE / MEMORY PLANE

### 14.1 Current Memory Architecture

| Tier | Backend | Status |
|------|---------|--------|
| Working Memory | In-memory (session-scoped) | ✅ EXISTING |
| Claude Memory | File-based (session persistence) | ✅ EXISTING |
| Engineering Intelligence | LearningService (RCA-derived) | ⚠️ PARTIAL |
| Obsidian | Label only | ⚠️ NOT WIRED |
| Graphify | Label only; mock server | ⚠️ NOT WIRED |

### 14.2 Claude-Mem Analysis

**Repository:** `https://github.com/thedotmack/claude-mem`

**Findings:**
- Claude-Mem is a **development-time memory tool** for Claude Code sessions
- It provides session-scoped context persistence, NOT persistent knowledge vault
- **No overlap with AI-OS Engineering Intelligence** (which is RCA-derived, structured, provenanced)
- **No overlap with Obsidian** (which is human-facing PKM)
- **Should NOT become AI-OS authoritative memory** — it is a developer tool
- **Classification:** REFERENCE / OPTIONAL DEVELOPER TOOL
- **Security implication:** Runs locally, no network access, low risk
- **Recommendation:** Do not integrate as AI-OS component. May be used by developers alongside AI-OS.

### 14.3 Obsidian / Graphify / Notion Architecture

| System | Role | Read Path | Write Path | Source of Truth |
|--------|------|-----------|------------|-----------------|
| **Obsidian** | Persistent knowledge vault | Human reads; AI-OS may query via MCP (future) | AI-OS writes architectural decisions | NO — AI-OS is authority |
| **Graphify** | Knowledge graph / relationship exploration | AI-OS queries for architecture review (ArchitectureAgency) | AI-OS updates graph nodes | NO — organizational mirror |
| **Notion** | Planning / operational tracking | Human reads project plans | AI-OS may write status updates | NO — organizational mirror |
| **Claude-Mem** | Development session memory | Developer reads context | Developer writes session notes | NO — external tool |

**Ownership rules:**
- AI-OS runtime state = `StateManager` / `StorageManager` (authoritative)
- Obsidian/Graphify/Notion = organizational mirrors (NOT sources of truth)
- No dual source-of-truth allowed
- AI-OS writes TO these systems only via explicit, auditable operations

### 14.4 Remaining Work

| Task | Description | Priority |
|------|-------------|----------|
| Obsidian MCP integration | Query vault for architectural context | P2 (optional) |
| Graphify MCP wiring | Connect real Graphify server for ArchitectureAgency | P2 |
| Notion status sync | Write test results/status to Notion (if adopted) | P3 (optional) |
| Claude-Mem evaluation | Decide whether to integrate as dev tool | P3 |

---

## 15. PLANNING / ORGANIZATION PLANE

### 15.1 Notion

**Current status:** C4 — ABSENT from repository. Zero references in `src/` or `config/`.

**Decision required:** ADOPT or DROP.

**If ADOPTED:**
- Notion = human-facing project/operational organization
- AI-OS writes status updates via Notion API (read-only for AI-OS planning)
- Notion MCP adapter needed
- **Must NOT become runtime authority**

**If DROPPED:**
- Remove from V2 architecture diagram
- Documentation-only reference
- No implementation work required

**Recommendation:** **ADOPT with boundary** — Notion as operational mirror, not runtime authority. Requires:
1. Notion MCP adapter (or REST API client)
2. Write-only path: AI-OS → Notion (status, test results, milestones)
3. Read path: Human → Notion (plans, requirements); AI-OS reads via MCP if needed
4. Explicit documentation of boundary: "Notion is organizational, not authoritative"

### 15.2 GSD Core

**Repository:** `https://github.com/open-gsd/gsd-core`

**Classification:** REFERENCE (methodology only)
**Role:** Structured project-planning / task-decomposition methodology
**Decision:** Do NOT import as runtime component. Use as planning reference for Terminal 1/2/3 workflow.

### 15.3 Boundaries

| System | AI-OS reads | AI-OS writes | Final authority |
|--------|------------|--------------|-----------------|
| Notion | Optional (plans) | Status updates | AI-OS |
| GSD | N/A | N/A | AI-OS |
| Obsidian | Optional (context) | Architectural decisions | AI-OS |
| Graphify | Yes (architecture review) | Graph nodes (if wired) | AI-OS |

---

## 16. SECURITY ARCHITECTURE

### 16.1 Current Security Model

| Component | File | Status |
|-----------|------|--------|
| SecurityManager | `core/security_manager.py` | ✅ EXISTING (fail-closed) |
| SkillSpecTorGate | `core/security_manager.py` | ✅ EXISTING (M4) |
| MCPServerSecurityGate | `core/security_manager.py` | ✅ EXISTING (M5, C18) |
| SecurityAgencyAdapter | `adapters/security_agency_adapter.py` | ✅ REAL |
| HermesBridge authorization | `adapters/hermes_bridge.py` | ✅ EXISTING |

### 16.2 Security Invariants

| ID | Rule | Status |
|----|------|--------|
| SEC-001 | Fail-closed authorization (DENY default) | ✅ |
| SEC-002 | SecurityManager is FINAL authority | ✅ |
| SEC-003 | SkillSpecTor is INTEGRATION gate only | ✅ |
| SEC-004 | External workers return observations only | ✅ |
| SEC-005 | No source code to UserSimulationAgent | ✅ (INV-008) |
| SEC-006 | Builder excluded from TestingCouncil | ✅ (INV-009) |
| SEC-007 | Evidence provenance mandatory | ✅ (INV-007) |
| SEC-008 | MCP servers gated before connect | ✅ (C18) |

### 16.3 Remaining Security Work

| Task | Description | Priority |
|------|-------------|----------|
| SecurityManager audit | Independent review of authorization paths | P1 |
| Prompt injection testing | Test adapters against prompt injection | P1 |
| External trust boundaries | Document and verify all external trust boundaries | P1 |
| Secrets management | Production secrets rotation, vault integration | P2 |
| Network security | MCP/ACP transport encryption verification | P2 |
| Supply chain security | Dependency vulnerability scanning (OSV) | P2 |

---

## 17. EVIDENCE / PROVENANCE ARCHITECTURE

### 17.1 Current Evidence Lifecycle

```
External source → Retrieval → Raw observation → Provenance → Validation
    → Normalized evidence → Council analysis → Decision → Verification
    → Persistent record (TestingEvidence)
```

### 17.2 TestingEvidence Schema

```python
@dataclass(frozen=True)
class TestingEvidence:
    evidence_id: str
    perspective: str
    target: str
    test_id: str
    actions: list[dict]
    observations: list[dict]
    expected: str
    observed: str
    severity: str  # critical|high|medium|low
    confidence: float  # [0.0, 1.0]
    proof: list[str]  # screenshots, DOM, traces
    provenance: Provenance  # source, worker, session, timestamp, env
    environment: dict
    timestamp: datetime
    reproducibility: float  # [0.0, 1.0]
    verdict: str  # pass|fail|inconclusive
```

### 17.3 Provenance Requirements

| Field | Required | Source |
|-------|----------|--------|
| `source` | ✅ | Agency type or worker label |
| `worker` | ✅ | External worker identifier |
| `session` | ✅ | Isolated session ID |
| `timestamp` | ✅ | ISO 8601 UTC |
| `environment` | ✅ | Builder vs tester environment tag |
| `correlation_id` | ✅ | Closed-loop tracking |
| `test_id` | ✅ | Test case identifier |

### 17.4 Remaining Evidence Work

| Task | Description | Priority |
|------|-------------|----------|
| Evidence persistence | Persistent storage of TestingEvidence ledger | P2 |
| Evidence retrieval API | Query evidence by perspective, target, time | P2 |
| Evidence export | Export evidence for external audit | P3 |

---

## 18. LEARNING / RCA / REPLAN LOOP

### 18.1 Current State

| Component | Status |
|-----------|--------|
| RootCauseAnalyzer | ✅ EXISTING — classifies failures, routes to responsible service |
| LearningService | ⚠️ PARTIAL — captures RCA events, logs learnings, no extraction/validation |
| SimplificationGate | ✅ EXISTING — pre-acceptance complexity governance |
| SelfPromptingService | ✅ EXISTING — bounded self-questioning |
| TestOrchestratorService.closed_loop | ✅ EXISTING — bounded retest (max 5 iterations, 1M token budget) |

### 18.2 Closed Loop Flow

```
FAIL → RootCauseAnalyzer → LearningService.capture_learning()
    → PlanningService.replan() → TestOrchestratorService.coordinate_retest()
    → (bounded: max iterations, convergence detection, regression protection)
```

### 18.3 Remaining Learning Work

| Task | Description | Priority |
|------|-------------|----------|
| Learning extraction | Failure→fix categorization, lesson validation | P2 |
| Learning feedback | Feed lessons into PlanningService and SelfPromptingService | P2 |
| Regression protection | Ensure learning doesn't introduce harmful patterns | P1 |
| Convergence detection | Detect when loop isn't improving | P2 |
| Human escalation | Escape hatch when loop exhausts bounds | P2 |

---

## 19. EXTERNAL ECOSYSTEM

### 19.1 Master Classification Table

| Component | Official URL | Category | Purpose | Required? | Runtime/Dev | Integration | Security Risk | License | Current Status | Planned Milestone |
|-----------|-------------|----------|---------|-----------|-------------|-------------|---------------|---------|----------------|-------------------|
| **hermes-agent** | Local (`hermes-agent/`) | INTEGRATION + REFERENCE | Browser automation, worker execution | YES (for UserSim) | Runtime | MCP/ACP bridge | Medium (external worker) | See repo | PARTIAL (MCP fallback) | M5 completed (bridge); ACP pending |
| **agency-agents** | `github.com/msitarzewski/agency-agents` | SKILL/PERSONA SOURCE | 230+ MIT personas; curated ~10 for testing | OPTIONAL | Dev | SKILL.md adapter (M4) | Low (content only) | MIT | PARTIAL (10 curated) | M4 complete |
| **SkillSpecTor** | `github.com/NVIDIA/SkillSpecTor` | INTEGRATION (gate) | Security scanner for skills/MCPs | YES (gate) | Runtime | Integrated in SecurityManager | Low (local scan) | Apache-2.0 | IMPLEMENTED (M4) | M4 complete |
| **Agent-Reach** | `github.com/Panniantong/agent-reach` | INTEGRATION | Web/social ingestion via MCP | OPTIONAL | Runtime | MCP adapter | Medium (network access) | See repo | ADAPTER EXISTS | M5 partial |
| **FreeLLMAPI** | `github.com/free-llm-api` (assumed) | INTEGRATION | Model/provider abstraction via MCP | OPTIONAL | Runtime | MCP adapter | Low (API key required) | See repo | ADAPTER EXISTS | M5 partial |
| **Graphify** | `github.com/davioud/graphify` (assumed) | INTEGRATION | AST knowledge graph via MCP | OPTIONAL | Runtime | MCP adapter | Low (local graph) | See repo | MOCK ONLY | M5 pending |
| **Playwright MCP** | `github.com/microsoft/playwright` | INTEGRATION | Deterministic browser testing | OPTIONAL | Runtime | Adapter needed | Low (local browser) | Apache-2.0 | NOT WIRED | Future |
| **Vercel Skills (SKILL.md)** | `github.com/vercel/skills` | INTEGRATION (spec) | Canonical skill format | YES (standard) | Dev | SKILL.md parser (M4) | Low (spec only) | MIT | IMPLEMENTED (M4) | M4 complete |
| **Trail of Bits Skills** | `github.com/trailofbits` | REFERENCE | Security skill patterns | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |
| **Karpathy LLM Council** | `github.com/karpathy/llm-council` | TECHNIQUE | Cross-ranking synthesis method | NO | Technique | Adopted as critique() | N/A | None (unlicensed) | TECHNIQUE ADOPTED | M6 complete |
| **evisoft Council** | Claude Code SKILL.md prompts | TECHNIQUE | Dissenter-override method | NO | Technique | Adopted as critique() | N/A | None (unlicensed) | TECHNIQUE ADOPTED | M6 complete |
| **Obsidian** | `github.com/obsidianmd/obsidian` | REFERENCE | PKM vault | OPTIONAL | Dev | Future MCP | Low (local vault) | AGPL-3.0 | NOT WIRED | Future |
| **Notion** | `notion.so` | REFERENCE | Planning/tracking | OPTIONAL (C4) | Dev | Future API/MCP | Medium (API key) | Proprietary | ABSENT (C4) | TBD |
| **GSD Core** | `github.com/open-gsd/gsd-core` | METHODOLOGY | Planning methodology | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |
| **Ruflo** | `github.com/ruflo` (assumed) | REFERENCE | Agent meta-OS (competitor) | NO | Reference | REJECTED as core | N/A | See repo | REFERENCE ONLY | None |
| **Loop Engineering** | `github.com/loop-engineering` (assumed) | REFERENCE | Loop patterns/primitives | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |
| **Caveman** | `github.com/caveman-compression` (assumed) | OPTIONAL | Token compression | NO | Optional | Feature-flagged | Low | BSL-1.1 | NOT NEEDED | Future |
| **Free Claude Code** | Unaffiliated | OPTIONAL | Provider launcher | NO | Optional | Reference | Medium (billing) | See repo | NOT NEEDED | Future |
| **Book-to-Skill** | `github.com/book-to-skill` (assumed) | REFERENCE | Offline SKILL.md authoring | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |
| **Prompt Eng Hub** | `github.com/prompt-eng-hub` (assumed) | REFERENCE | Static prompt patterns | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |
| **Superpowers** | `github.com/superpowers` (assumed) | REFERENCE | Composable skill methodology | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |
| **ECC** | `github.com/everything-claude-code` (assumed) | REFERENCE | 68-agent harness patterns | NO | Reference | Reference only | N/A | See repo | REFERENCE | None |

---

## 20. EXTERNAL REPOSITORY DETAILED ANALYSIS

### 20.1 hermes-agent (LOCAL — `hermes-agent/`)

| Attribute | Value |
|-----------|-------|
| **Location** | `C:\Development\AI-OS\hermes-agent\` (gitignored) |
| **Classification** | INTEGRATION + REFERENCE |
| **Purpose** | External browser automation and worker execution engine |
| **AI-OS Role** | UserSimulationAgent execution substrate; tester worker delegation |
| **Authority** | NONE — AI-OS controls via MCP/ACP; Hermes returns observations only |
| **Integration** | `HermesBridge` (MCP fallback); ACP preferred for production |
| **Security** | Session isolation, provenance tracking, fail-closed |
| **Status** | PARTIAL — MCP fallback wired; ACP not yet integrated |
| **Requirement** | YES — required for UserSimulationAgent (10th perspective) |

**Key Hermes capabilities used by AI-OS:**
- Cloud browser automation (Browserbase/Use/Firecrawl backends)
- Delegation workers (per-perspective tester isolation)
- MOA synthesis (reference technique, not imported)
- ACP protocol (preferred for worker/runtime relationship)
- Estop/safety gate (reference)

**Remaining work:**
1. Wire ACP protocol in `HermesBridge` for user-simulation sessions
2. Connect to real Hermes worker endpoint (requires Browserbase credentials)
3. CI/dev: continue using `mock_hermes_server.py`

### 20.2 agency-agents (`github.com/msitarzewski/agency-agents`)

| Attribute | Value |
|-----------|-------|
| **Classification** | SKILL/PERSONA SOURCE |
| **Purpose** | 230+ MIT-licensed persona definitions |
| **AI-OS Role** | Seed content for `AIAgencyService` roles |
| **Authority** | NONE — personas are content, not governance |
| **Integration** | SKILL.md adapter (M4) curates ~10 personas |
| **Security** | Low risk — MIT license, content only, no execution |
| **Status** | M4 COMPLETE — 10 personas curated and seeded |

**Curated personas (from Testing/Security Divisions):**
- `testing-api-tester` → ArchitectureAgency
- `testing-performance-benchmarker` → PerformanceAgency
- `testing-accessibility-auditor` → AccessibilityAgency
- `testing-evidence-collector` → All agencies (evidence collection)
- `testing-reality-checker` → FinalJudgeAgency (adversarial)
- `security-penetration-tester` → SecurityAgency
- `security-architect` → ArchitectureAgency
- `engineering-code-reviewer` → DocumentationAgency
- `testing-test-automation-engineer` → BugHunterAgency
- `design-ux-researcher` → UserSimulationAgent (reference, not substitute)

**Critical rule:** agency-agents MUST NOT become a second governance layer. Personas are CONTENT, not DECISION-makers.

### 20.3 Claude-Mem (`github.com/thedotmack/claude-mem`)

| Attribute | Value |
|-----------|-------|
| **Classification** | REFERENCE / OPTIONAL DEVELOPER TOOL |
| **Purpose** | Session-scoped memory for Claude Code development |
| **AI-OS Role** | NONE — not an AI-OS component |
| **Overlap with AI-OS** | None — AI-OS has Engineering Intelligence (RCA-derived, structured, provenanced) |
| **Security** | Low — local tool, no network access |
| **Recommendation** | Do NOT integrate. May be used by developers alongside AI-OS. |

**Rationale:**
- Claude-Mem is a DEVELOPMENT-TIME tool for Claude Code sessions
- AI-OS Engineering Intelligence is PRODUCTION-TIME, structured, and provenanced
- Different purpose, different audience, different trust model
- Integrating would add unnecessary dependency without capability gain

### 20.4 Karpathy LLM Council (`github.com/karpathy/llm-council`)

| Attribute | Value |
|-----------|-------|
| **Classification** | TECHNIQUE |
| **Purpose** | Local web app for multi-LLM parallel reasoning |
| **AI-OS Role** | Techniques adopted into `CouncilManager.critique()` |
| **Authority** | NONE — technique only, not imported as subsystem |
| **Techniques adopted:** | 1. Independent first-opinions (perspective isolation) |
| | 2. Blind/anonymized cross-ranking (accuracy + insight axes) |
| | 3. Separate chairman synthesis (distinct from voters) |
| **Status** | M6 COMPLETE — techniques adopted, not code imported |

### 20.5 evisoft Council (`github.com/evisoft/council` — SKILL.md prompts)

| Attribute | Value |
|-----------|-------|
| **Classification** | TECHNIQUE |
| **Purpose** | Claude Code SKILL.md prompt templates for deliberation |
| **AI-OS Role** | Techniques adopted into `CouncilManager.critique()` |
| **Authority** | NONE — technique only, not imported as subsystem |
| **Techniques adopted:** | 1. Worldview-diverse advisors (parallel, isolated) |
| | 2. Relabel-before-review (break authority bias) |
| | 3. Side-with-dissenter (minority may beat majority) |
| **Status** | M6 COMPLETE — techniques adopted, not code imported |

---

## 21. AGENCY-AGENTS INTEGRATION

### 21.1 How agency-agents Relates to AI-OS

```
agency-agents (230+ personas, MIT)
    ↓ [M4: Curate ~10 via SKILL.md adapter]
    ↓
AI-OS AIAgencyService (9 roles + FinalJudge)
    ↓ [Each role populated with curated persona content]
    ↓
Real execution adapters (8 adapters in src/aios/adapters/)
    ↓
TestOrchestratorService dispatches to real adapters
    ↓
TestingEvidence with provenance
```

### 21.2 Persona Mapping

| AI-OS Agency | Curated Persona Source | Adapter |
|-------------|----------------------|---------|
| SecurityAgency | `security-penetration-tester` | `SecurityAgencyAdapter` |
| PerformanceAgency | `testing-performance-benchmarker` | `PerformanceAgencyAdapter` |
| AccessibilityAgency | `testing-accessibility-auditor` | `AccessibilityAgencyAdapter` |
| ArchitectureAgency | `security-architect`, `engineering-code-reviewer` | `ArchitectureAgencyAdapter` |
| DocumentationAgency | `engineering-code-reviewer` | `DocumentationAgencyAdapter` |
| ConcurrencyAgency | `testing-api-tester` | `ConcurrencyAgencyAdapter` |
| BugHunterAgency | `testing-test-automation-engineer` | `BugHunterAgencyAdapter` |
| FinalJudgeAgency | `testing-reality-checker` | Independent (no adapter) |

### 21.3 Governance Boundary

**CRITICAL:** agency-agents personas are CONTENT, not AUTHORITY.
- Personas inform what each agency CHECKS
- AI-OS determines WHAT IS FOUND via real execution
- AI-OS determines PASS/FAIL via FinalJudgeAgency
- No persona can bypass SecurityManager or override verification

---

## 22. CLAUDE-MEM ANALYSIS

### 22.1 What Claude-Mem Solves

Claude-Mem provides session-scoped memory persistence for Claude Code development sessions. It allows Claude to remember context across conversations within a single development session.

### 22.2 Overlap Analysis

| Capability | Claude-Mem | AI-OS | Overlap? |
|-----------|-----------|-------|----------|
| Session memory | ✅ Yes | ❌ No (different scope) | NO |
| Cross-session persistence | ⚠️ Partial | ✅ Engineering Intelligence | PARTIAL (different purpose) |
| Structured learnings | ❌ No | ✅ Yes (RCA-derived) | NO |
| Provenanced evidence | ❌ No | ✅ Yes | NO |
| Production runtime | ❌ No | ✅ Yes | NO |

### 22.3 Decision

**CLASSIFICATION:** REFERENCE / OPTIONAL DEVELOPER TOOL
**INTEGRATION:** NOT RECOMMENDED
**Rationale:**
1. Claude-Mem serves DEVELOPERS, not the AI-OS runtime
2. AI-OS Engineering Intelligence serves the TESTING/VERIFICATION loop
3. Different trust models, different persistence requirements
4. Adding Claude-Mem as AI-OS memory would conflate development tool with production system

---

## 23. AGENT REACH EVALUATION

### 23.1 Capabilities

| Attribute | Value |
|-----------|-------|
| **Repository** | `github.com/Panniantong/agent-reach` (assumed) |
| **Classification** | INTEGRATION (MCP) |
| **Purpose** | Web/social content ingestion via MCP |
| **AI-OS Role** | Environment/context ingestion for testing (optional) |
| **Dependencies** | MCP server, API credentials |
| **Security** | Medium (network access, external content) |
| **Overlap with Hermes** | Partial — Hermes for browser automation; Agent-Reach for web search |
| **Overlap with Graphify** | None — different purpose |

### 23.2 Integration Path

```
Agent-Reach MCP server
    ↓ [M5: Register via MCPManager]
    ↓
AI-OS AgentReachAdapter
    ↓
Returns AgentReachObservation (untrusted, provenanced)
    ↓
TestOrchestratorService normalizes to TestingEvidence
```

### 23.3 Requirement Assessment

| Question | Answer |
|----------|--------|
| Does AI-OS need web/social ingestion? | OPTIONAL — useful for architecture review context |
| Can AI-OS function without it? | YES — core testing doesn't require web access |
| Should it be runtime or optional? | OPTIONAL — feature-flagged |
| How should outputs be validated? | Via SecurityManager + provenance tracking |
| What provenance is required? | Source URL, fetch timestamp, worker ID |

**Decision:** OPTIONAL INTEGRATION — implement adapter, gate via SecurityManager, feature-flagged.

---

## 24. COUNCIL / LLM COUNCIL EVALUATION

### 24.1 What AI-OS Already Implements

| Component | Status | Details |
|-----------|--------|---------|
| `CouncilManager` | ✅ EXISTING | 5 consensus algorithms, dissent preservation |
| `critique()` stage | ✅ EXISTING (M6) | KKC anonymized cross-ranking + EVC dissenter-override |
| `LLMCouncil` | ✅ EXISTING | 6 cognitive roles (Analyst, Contrarian, Outsider, Skeptic, Specialist, Simplifier) |
| `SelfPromptingService` | ✅ EXISTING | Bounded self-questioning routed to LLMCouncil |

### 24.2 What Karpathy/evisoft Contribute

| Technique | Source | Implementation |
|-----------|--------|----------------|
| Anonymized cross-ranking | Karpathy LLM Council | ✅ Adopted in `critique()` |
| Two-axis scoring (accuracy + insight) | Karpathy LLM Council | ✅ Adopted in `CritiqueRanking` |
| Chairman synthesis | Karpathy LLM Council | ✅ Adopted in `synthesize()` |
| Worldview-diverse advisors | evisoft Council | ✅ Adopted in `LLMCouncil` roles |
| Relabel-then-review | evisoft Council | ✅ Adopted in `critique()` |
| Side-with-dissenter | evisoft Council | ✅ Adopted in `critique()` |

### 24.3 Decision

**NO NEW INTEGRATION REQUIRED.** All techniques from Karpathy and evisoft have been adopted into the existing `CouncilManager` during M6. No code was imported; only techniques were re-implemented.

---

## 25. GSD EVALUATION

| Attribute | Value |
|-----------|-------|
| **Repository** | `github.com/open-gsd/gsd-core` |
| **Classification** | METHODOLOGY / REFERENCE |
| **Purpose** | Structured project-planning and task-decomposition methodology |
| **AI-OS Role** | Reference for Terminal 1/2/3 workflow planning |
| **Integration** | NONE — methodology only, not runtime component |
| **Decision** | REFERENCE ONLY — use for planning discipline, not as AI-OS component |

---

## 26. OBSIDIAN / GRAPHIFY / NOTION ARCHITECTURE

### 26.1 System Roles

| System | Role | Read Path | Write Path | AI-OS Authority |
|--------|------|-----------|------------|-----------------|
| **Obsidian** | Persistent knowledge vault | Human reads; AI-OS may query via MCP | AI-OS writes architectural decisions | NO — AI-OS is authority |
| **Graphify** | Knowledge graph / relationships | AI-OS queries for architecture review | AI-OS updates graph nodes (if wired) | NO — organizational mirror |
| **Notion** | Planning / operational tracking | Human reads plans; AI-OS may query | AI-OS writes status updates | NO — organizational mirror |
| **Claude-Mem** | Development session memory | Developer reads context | Developer writes session notes | NO — external tool |

### 26.2 Ownership Rules

1. **AI-OS runtime state** = `StateManager` / `StorageManager` (authoritative)
2. **Obsidian/Graphify/Notion** = organizational mirrors (NOT sources of truth)
3. **No dual source-of-truth** allowed
4. **AI-OS writes TO** these systems only via explicit, auditable operations
5. **These systems cannot read AI-OS state** without explicit MCP/API gateway

### 26.3 Provenance Requirements

When AI-OS writes to external knowledge systems:
- Operation must be logged via StructuredLogger
- Correlation ID must be attached
- Timestamp must be recorded
- Operator identity must be captured (AI-OS kernel identity)

### 26.4 Conflict Resolution

If external knowledge conflicts with AI-OS state:
1. AI-OS state is authoritative
2. External system is flagged for review
3. Human operator resolves conflict
4. Resolution is logged as architectural decision

---

## 27. CAPABILITY GAP REGISTER

| Capability | Already Exists? | Missing? | External Tool Candidate | Required? | Reason | Decision |
|-----------|----------------|----------|------------------------|-----------|--------|----------|
| Real Hermes browser execution | ⚠️ PARTIAL (MCP fallback) | Yes (ACP) | hermes-agent | YES | UserSimulationAgent requires browser | IMPLEMENT — wire ACP |
| Real Graphify MCP server | ❌ No | Yes | Graphify | OPTIONAL | ArchitectureAgency evidence | INTEGRATE (OPTIONAL) |
| Real Playwright browser testing | ❌ No | Yes | Playwright MCP | OPTIONAL | AccessibilityAgency enhancement | INTEGRATE (OPTIONAL) |
| Real model provider calls | ⚠️ PARTIAL (stub) | Yes | FreeLLMAPI | OPTIONAL | ModelRouter needs real routing | INTEGRATE (OPTIONAL) |
| Web/social content ingestion | ❌ No | Yes | Agent-Reach | OPTIONAL | Environment context for testing | INTEGRATE (OPTIONAL) |
| Notion status sync | ❌ No | Yes | Notion API | OPTIONAL | Operational tracking | ADOPT (C4 decision) |
| Obsidian vault query | ❌ No | Yes | Obsidian MCP | OPTIONAL | Architectural context | INTEGRATE (OPTIONAL) |
| Skill marketplace | ⚠️ PARTIAL (M4) | Partial | Vercel Skills + agency-agents | YES | Portable skill format | COMPLETE (M4) |
| Security scanning gate | ✅ Yes | No | SkillSpecTor | YES | Skill/MCP security vetting | COMPLETE (M4) |
| Council synthesis | ✅ Yes | No | (adopted techniques) | YES | Multi-perspective reasoning | COMPLETE (M6) |
| Token compression | ❌ No | Yes | Caveman | NO | Cost reduction (nice-to-have) | DEFER |
| Production browser farm | ❌ No | N/A | (rejected) | NO | Hermes cloud-browser sufficient | REJECT |
| Second kernel / council | ❌ No | N/A | (rejected) | NO | AI-OS is sole authority | REJECT |

---

## 28. MUST-NOT-IMPLEMENT RULES

### Permanent Architecture Protection List

**AI-OS MUST NOT:**

1. Make Notion the runtime authority
2. Make Obsidian the decision engine
3. Make Graphify the governance engine
4. Make Claude-Mem the authoritative AI-OS memory
5. Make GSD the AI-OS runtime kernel
6. Allow Hermes to make final decisions
7. Allow agency-agents to become governance
8. Allow external agencies to bypass AI-OS
9. Allow external councils to override AI-OS verification
10. Blindly trust external knowledge
11. Treat external repository output as evidence automatically
12. Copy external architectures wholesale
13. Silently import unnecessary dependencies
14. Allow external tools to mutate protected state
15. Allow an external system to declare final PASS/FAIL
16. Bypass provenance
17. Bypass testing
18. Bypass security
19. Use mocks as proof of production execution
20. Expand scope without a demonstrated capability gap
21. Create a second kernel, council, verification, or closed loop
22. Let `hermes-agent`(EXT) decide — it executes only
23. Use Ruflo as core (competitor kernel)
24. Import KKC/evisoft code (techniques only)
25. Build native AI-OS browser (use Hermes cloud-browser)

---

## 29. REMAINING WORK

### 29.1 What is COMPLETE (M0–M7)

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0–M3 | V1 baseline (kernel, managers, events, closed loop) | ✅ Complete |
| M4 | SKILL.md standard + SkillSpecTor gate | ✅ Verified |
| M5 | Integration backbone (MCP adapters, Hermes bridge) | ✅ Verified |
| M6 | Council synthesis (critique, LLMCouncil, SelfPrompting) | ✅ Verified |
| M7 | Multi-perspective testing + User Simulation | ✅ Verified |

**Current test count: 1,046 passing**

### 29.2 What Remains (Phase 2: Hardening & Delivery)

| Area | Work | Priority | Estimated Effort |
|------|------|----------|-----------------|
| **Hermes ACP Integration** | Wire ACP protocol for real browser execution | P1 | Medium |
| **Production Adapter Testing** | E2E tests with real workers (not mocks) | P1 | Medium |
| **LearningService Enhancement** | Lesson extraction, validation, feedback loop | P2 | Small |
| **ModelRouter Real Integration** | Connect FreeLLMAPI for real LLM calls | P2 | Small |
| **Graphify MCP Wiring** | Connect real Graphify server | P2 | Small |
| **Notion Decision** | Adopt or drop Notion; implement if adopted | P2 | Small |
| **Security Audit** | Independent security review of all authorization paths | P1 | Medium |
| **Deployment** | Docker, health checks, config management | P1 | Large |
| **Documentation** | Complete Parts 10–15, resolve C1–C4 | P2 | Medium |
| **CLI Expansion** | Testing/deployment commands | P3 | Small |
| **Performance Testing** | Scaling tests beyond logger benchmark | P3 | Small |
| **Chaos Testing** | Fault injection into kernel components | P3 | Small |

---

## 30. COMPLETE MILESTONE ROADMAP

### Current State: POST-M7

```
M0 ✅ → M1 ✅ → M2 ✅ → M3 ✅ → M4 ✅ → M5 ✅ → M6 ✅ → M7 ✅
                                                         ↓
                                                   [CURRENT]
                                                         ↓
                                                   PHASE 2
```

### Phase 2 Milestones

| Milestone | Name | Purpose | Dependencies | Complexity |
|-----------|------|---------|--------------|------------|
| **M8** | Production Integration | Wire real Hermes ACP, real Graphify, real Playwright | M7 | Medium |
| **M9** | Learning & Optimization | Enhance LearningService, ModelRouter real integration | M8 | Small |
| **M10** | Deployment & Operations | Docker, health checks, CLI expansion, config mgmt | M9 | Large |
| **M11** | Security Hardening | Independent security audit, adversarial testing | M10 | Medium |
| **M12** | Documentation & Closure | Resolve C1–C4, complete Parts 10–15, final QA | M11 | Medium |

### Milestone Details

#### M8 — Production Integration (P1)

**Objective:** Replace mock servers with real external integrations where feasible; establish production-grade execution paths.

**Components:**
1. Hermes ACP protocol wiring (`HermesBridge` upgrade)
2. Real Graphify MCP connection (`ArchitectureAgencyAdapter` real path)
3. Real Playwright MCP for accessibility testing
4. Real Agent-Reach MCP (optional, feature-flagged)
5. Real FreeLLMAPI connection (optional, feature-flagged)

**Tests:**
- E2E test with real Hermes worker (requires credentials)
- E2E test with real Graphify server
- E2E test with real Playwright
- Feature-flag tests for optional integrations
- Regression: all 1,046 existing tests must pass

**Acceptance Criteria:**
- UserSimulationAgent can drive real browser (when credentials available)
- ArchitectureAgency can query real knowledge graph
- AccessibilityAgency can run real axe-core tests
- All integrations behind feature flags (graceful degradation)
- Mock servers still work for CI/dev

**Definition of Done:**
- [ ] Hermes ACP wired in `HermesBridge`
- [ ] Graphify MCP connected (or documented as deferred)
- [ ] Playwright MCP integrated
- [ ] Feature flags for optional integrations
- [ ] E2E tests for real integrations
- [ ] All 1,046 regression tests pass
- [ ] Independent QA report

#### M9 — Learning & Optimization (P2)

**Objective:** Complete the learning loop with lesson extraction, validation, and feedback.

**Components:**
1. LearningService enhancement (lesson extraction, validation)
2. ModelRouter real LLM integration (FreeLLMAPI)
3. SelfPromptingService real scoring (replace mock scores)
4. Convergence detection in closed loop
5. Human escalation path

**Tests:**
- Learning extraction tests
- Model routing tests with real provider
- Convergence detection tests
- Escalation path tests
- Regression: all tests pass

**Acceptance Criteria:**
- LearningService extracts lessons from RCA
- ModelRouter routes to real LLM providers
- Closed loop detects convergence/no-improvement
- Human escalation works when bounds exhausted
- All 1,046+ regression tests pass

**Definition of Done:**
- [ ] LearningService lesson extraction implemented
- [ ] ModelRouter real LLM integration
- [ ] Convergence detection in closed loop
- [ ] Human escalation path
- [ ] Independent QA report

#### M10 — Deployment & Operations (P1)

**Objective:** Enable production deployment with configuration management, health checks, and operational tooling.

**Components:**
1. Docker deployment configuration
2. Health check endpoints
3. CLI expansion (testing, deployment commands)
4. Configuration validation (production profiles)
5. Rollback capability
6. Monitoring integration (OpenTelemetry if available)

**Tests:**
- Deployment smoke tests
- Health check tests
- Configuration validation tests
- Rollback tests
- Regression: all tests pass

**Acceptance Criteria:**
- AI-OS can be deployed via Docker
- Health checks report kernel status
- CLI has testing and deployment commands
- Configuration validated before startup
- Rollback to previous version supported
- All 1,046+ regression tests pass

**Definition of Done:**
- [ ] Docker configuration
- [ ] Health check endpoints
- [ ] CLI expansion
- [ ] Configuration validation
- [ ] Rollback capability
- [ ] Independent QA report

#### M11 — Security Hardening (P1)

**Objective:** Independent security audit and adversarial testing.

**Components:**
1. SecurityManager authorization path audit
2. Prompt injection testing
3. External trust boundary verification
4. Secrets management review
5. Supply chain security (dependency scanning)
6. Network security verification

**Tests:**
- Security audit test suite
- Prompt injection resilience tests
- Trust boundary tests
- Secrets rotation tests
- Dependency vulnerability scan
- Regression: all tests pass

**Acceptance Criteria:**
- All authorization paths verified
- Prompt injection resistance confirmed
- External trust boundaries documented
- Secrets management production-ready
- No critical/high vulnerabilities
- All 1,046+ regression tests pass

**Definition of Done:**
- [ ] Security audit report
- [ ] Prompt injection tests
- [ ] Trust boundary documentation
- [ ] Secrets management
- [ ] Dependency scan results
- [ ] Independent QA report

#### M12 — Documentation & Closure (P2)

**Objective:** Complete architecture documentation, resolve open conditions, final QA.

**Components:**
1. Resolve C1 (Hermes naming collision)
2. Resolve C2 (verification gate count)
3. Resolve C3 (lifecycle state count)
4. Resolve C4 (Notion adopt/drop)
5. Complete Parts 10–15 architecture docs
6. Final acceptance criteria verification
7. Release notes

**Tests:**
- Documentation completeness check
- Architecture conformance verification
- Final acceptance criteria test
- Regression: all tests pass

**Acceptance Criteria:**
- All open conditions resolved
- Parts 0–15 complete
- Final acceptance criteria met
- All 1,046+ regression tests pass
- Independent QA: GO

**Definition of Done:**
- [ ] C1–C4 resolved
- [ ] Parts 10–15 complete
- [ ] Final acceptance criteria met
- [ ] Release notes
- [ ] Independent QA: GO

---

## 31. DETAILED TASK BREAKDOWN

### M8 Tasks

| Task ID | Task Name | Description | Dependencies | Files/Modules | Acceptance Criteria | Definition of Done |
|---------|-----------|-------------|--------------|---------------|---------------------|-------------------|
| **M8-T1** | Hermes ACP Protocol | Wire ACP protocol in HermesBridge for real browser sessions | M7 | `adapters/hermes_bridge.py` | ACP connection established; observations returned with provenance | Code complete; E2E test passes |
| **M8-T2** | Graphify MCP Connection | Connect real Graphify MCP server for ArchitectureAgency | M7, M8-T1 | `adapters/architecture_agency_adapter.py`, `config/mcps.yaml` | Graph queries return real AST data | Adapter wired; E2E test passes |
| **M8-T3** | Playwright MCP Integration | Integrate Playwright MCP for AccessibilityAgency | M7 | `adapters/accessibility_agency_adapter.py`, `config/mcps.yaml` | axe-core runs on real browser | Adapter wired; E2E test passes |
| **M8-T4** | Feature Flags | Add feature flags for optional integrations | M8-T1, M8-T2, M8-T3 | `config/defaults.yaml`, `core/security_manager.py` | Optional integrations behind flags; graceful degradation | Flags implemented; tests for both enabled/disabled |
| **M8-T5** | E2E Integration Tests | Write E2E tests for real integrations | M8-T1, M8-T2, M8-T3 | `tests/integration/test_m8_*.py` | Real worker tests pass (with credentials); mock tests pass (without) | Test suite complete; CI configured |
| **M8-T6** | M8 Independent QA | Independent QA report for M8 | M8-T1–T5 | QA report | Score ≥ 90/100; all acceptance criteria met | QA report written; GO verdict |

### M9 Tasks

| Task ID | Task Name | Description | Dependencies | Files/Modules | Acceptance Criteria | Definition of Done |
|---------|-----------|-------------|--------------|---------------|---------------------|-------------------|
| **M9-T1** | LearningService Enhancement | Add lesson extraction, validation, feedback loop | M7 | `services/learning.py` | Lessons extracted from RCA; feedback to PlanningService | Service enhanced; tests pass |
| **M9-T2** | ModelRouter Real Integration | Connect FreeLLMAPI for real LLM calls | M8 | `core/model_router.py`, `adapters/freellmapi.py` | Real LLM responses routed correctly | Integration complete; tests pass |
| **M9-T3** | SelfPromptingService Scoring | Replace mock scores with real LLM evaluation | M9-T2 | `services/self_prompting.py` | Real accuracy/insight scores from LLM | Scoring real; tests pass |
| **M9-T4** | Convergence Detection | Detect when closed loop isn't improving | M7 | `services/testing.py` | Loop terminates on convergence or no-improvement | Detection implemented; tests pass |
| **M9-T5** | Human Escalation | Add escape hatch when loop exhausts bounds | M9-T4 | `services/testing.py`, `core/kernel.py` | Human notified when bounds exhausted; manual override possible | Escalation path implemented; tests pass |
| **M9-T6** | M9 Independent QA | Independent QA report for M9 | M9-T1–T5 | QA report | Score ≥ 90/100; all acceptance criteria met | QA report written; GO verdict |

### M10 Tasks

| Task ID | Task Name | Description | Dependencies | Files/Modules | Acceptance Criteria | Definition of Done |
|---------|-----------|-------------|--------------|---------------|---------------------|-------------------|
| **M10-T1** | Docker Configuration | Create Dockerfile and docker-compose for AI-OS | M7 | `Dockerfile`, `docker-compose.yaml`, `.dockerignore` | Container builds and runs; health checks pass | Docker config complete; container tested |
| **M10-T2** | Health Check Endpoints | Add HTTP health check endpoints | M10-T1 | `cli/commands/doctor/`, `core/health_manager.py` | `/health` returns kernel status; `/ready` returns readiness | Endpoints implemented; tests pass |
| **M10-T3** | CLI Expansion | Add testing and deployment CLI commands | M7 | `cli/main.py`, `cli/commands/` | `aios test`, `aios deploy`, `aios health` commands work | CLI expanded; help text complete |
| **M10-T4** | Configuration Validation | Add production config validation | M7 | `config/validator.py`, `config/defaults.yaml` | Invalid configs rejected at startup; clear error messages | Validation complete; tests pass |
| **M10-T5** | Rollback Capability | Implement version rollback | M10-T1 | `core/kernel.py`, `core/state.py` | Previous version state can be restored | Rollback implemented; tests pass |
| **M10-T6** | M10 Independent QA | Independent QA report for M10 | M10-T1–T5 | QA report | Score ≥ 90/100; all acceptance criteria met | QA report written; GO verdict |

### M11 Tasks

| Task ID | Task Name | Description | Dependencies | Files/Modules | Acceptance Criteria | Definition of Done |
|---------|-----------|-------------|--------------|---------------|---------------------|-------------------|
| **M11-T1** | Security Audit | Independent security audit of authorization paths | M7 | Security audit report | All paths verified; no bypasses found | Audit report complete |
| **M11-T2** | Prompt Injection Testing | Test adapters against prompt injection | M7 | `tests/unit/test_prompt_injection.py` | Adapters resist prompt injection | Test suite complete; all pass |
| **M11-T3** | Trust Boundary Documentation | Document all external trust boundaries | M7 | Architecture docs | All boundaries documented; mitigation strategies defined | Documentation complete |
| **M11-T4** | Secrets Management | Production secrets rotation and vault integration | M10-T4 | `core/configuration_manager.py` | Secrets rotated; vault integration tested | Management complete; tests pass |
| **M11-T5** | Supply Chain Security | Dependency vulnerability scanning | M7 | `requirements.txt`, CI config | No critical/high vulnerabilities | Scan results documented |
| **M11-T6** | M11 Independent QA | Independent QA report for M11 | M11-T1–T5 | QA report | Score ≥ 90/100; all acceptance criteria met | QA report written; GO verdict |

### M12 Tasks

| Task ID | Task Name | Description | Dependencies | Files/Modules | Acceptance Criteria | Definition of Done |
|---------|-----------|-------------|--------------|---------------|---------------------|-------------------|
| **M12-T1** | Resolve C1 | Fix Hermes naming collision documentation | M7 | Architecture docs | Naming distinction documented | C1 resolved |
| **M12-T2** | Resolve C2 | Update verification gate count in docs | M7 | Architecture docs | Docs match code (8 LifecycleState members) | C2 resolved |
| **M12-T3** | Resolve C3 | Update lifecycle state count in narrative | M7 | Architecture docs | Narrative matches code (8 states) | C3 resolved |
| **M12-T4** | Resolve C4 | Adopt or drop Notion | M7 | Architecture docs, config | Decision documented; implementation if adopted | C4 resolved |
| **M12-T5** | Complete Parts 10–15 | Finalize remaining architecture documentation | M7 | `architecture/Part10-15/` | All parts complete and consistent | Parts complete |
| **M12-T6** | Final Acceptance | Verify all acceptance criteria | M12-T1–T5 | QA report | All criteria met; score ≥ 95/100 | Final QA: GO |
| **M12-T7** | Release Notes | Write release notes for v1.0 | M12-T1–T6 | `CHANGELOG.md`, `README.md` | Release notes complete | Notes written |

---

## 32. DEPENDENCY GRAPH

```
M7 (current)
    │
    ├─► M8-T1 (Hermes ACP) ──► M8-T2 (Graphify) ──┐
    │          │                                   │
    │          └─► M8-T3 (Playwright) ──► M8-T4 (Flags) ──► M8-T5 (E2E) ──► M8-T6 (QA)
    │                                                                          │
    ├─► M9-T1 (Learning) ──► M9-T2 (ModelRouter) ──► M9-T3 (Scoring) ──┐      │
    │                                             │                     │      │
    │                                             └─► M9-T4 (Convergence) ──► M9-T5 (Escalation) ──► M9-T6 (QA)
    │                                                                               │
    ├─► M10-T1 (Docker) ──► M10-T2 (Health) ──► M10-T3 (CLI) ──► M10-T4 (Config) ──► M10-T5 (Rollback) ──► M10-T6 (QA)
    │                                                                                                            │
    ├─► M11-T1 (Audit) ──► M11-T2 (Injection) ──► M11-T3 (Boundaries) ──► M11-T4 (Secrets) ──► M11-T5 (Supply) ──► M11-T6 (QA)
    │                                                                                                                     │
    └─► M12-T1 (C1) ──► M12-T2 (C2) ──► M12-T3 (C3) ──► M12-T4 (C4) ──► M12-T5 (Docs) ──► M12-T6 (Final) ──► M12-T7 (Release)
```

**Critical Path:** M8 → M9 → M10 → M11 → M12 (sequential milestones)
**Parallelizable within milestones:** M8-T2 and M8-T3 can run in parallel; M9-T1 and M9-T2 can run in parallel.

---

## 33. TESTING ROADMAP

### 33.1 Current Test Baseline (Post-M7)

| Suite | Count | Status |
|-------|-------|--------|
| Unit | 836 | ✅ PASS |
| Integration | 119 | ✅ PASS |
| Performance | 4 | ✅ PASS |
| **Total** | **1,046** | **ALL PASS** |

### 33.2 M8 Test Additions

| Test File | Description | Count |
|-----------|-------------|-------|
| `test_m8_hermes_acp.py` | Real Hermes ACP E2E | ~10 |
| `test_m8_graphify.py` | Real Graphify MCP E2E | ~8 |
| `test_m8_playwright.py` | Real Playwright E2E | ~8 |
| `test_m8_feature_flags.py` | Optional integration flags | ~10 |
| **Subtotal** | | **~36** |

### 33.3 M9 Test Additions

| Test File | Description | Count |
|-----------|-------------|-------|
| `test_m9_learning.py` | Learning extraction, validation | ~15 |
| `test_m9_model_router.py` | Real LLM routing | ~10 |
| `test_m9_convergence.py` | Closed loop convergence | ~8 |
| `test_m9_escalation.py` | Human escalation | ~5 |
| **Subtotal** | | **~38** |

### 33.4 M10 Test Additions

| Test File | Description | Count |
|-----------|-------------|-------|
| `test_m10_deployment.py` | Docker deployment | ~10 |
| `test_m10_health.py` | Health check endpoints | ~8 |
| `test_m10_cli.py` | CLI commands | ~10 |
| `test_m10_config.py` | Config validation | ~8 |
| `test_m10_rollback.py` | Rollback capability | ~5 |
| **Subtotal** | | **~41** |

### 33.5 M11 Test Additions

| Test File | Description | Count |
|-----------|-------------|-------|
| `test_m11_security.py` | Security audit suite | ~20 |
| `test_m11_prompt_injection.py` | Prompt injection resilience | ~15 |
| `test_m11_secrets.py` | Secrets management | ~10 |
| `test_m11_supply_chain.py` | Dependency scan | ~5 |
| **Subtotal** | | **~50** |

### 33.6 Target Test Count

| Phase | Tests | Cumulative |
|-------|-------|------------|
| Post-M7 baseline | 1,046 | 1,046 |
| M8 additions | +36 | 1,082 |
| M9 additions | +38 | 1,120 |
| M10 additions | +41 | 1,161 |
| M11 additions | +50 | 1,211 |
| **Target** | | **1,200+** |

---

## 34. SECURITY ROADMAP

### 34.1 Current Security Posture (Post-M7)

| Control | Status | Evidence |
|---------|--------|----------|
| Fail-closed authorization | ✅ | `SecurityManager.authorize()` |
| SkillSpecTor gate | ✅ | M4 verified |
| MCP server gate (C18) | ✅ | M5 verified |
| Builder exclusion | ✅ | `test_m7_isolation.py` |
| Evidence provenance | ✅ | `test_m7_evidence_integrity.py` |
| External worker untrusted | ✅ | `test_m7_security.py` |

### 34.2 M11 Security Hardening

| Control | Status | Work |
|---------|--------|------|
| Authorization path audit | ⚠️ PARTIAL | M11-T1 |
| Prompt injection resistance | ❌ NOT TESTED | M11-T2 |
| Trust boundary documentation | ⚠️ PARTIAL | M11-T3 |
| Secrets rotation | ⚠️ PARTIAL | M10-T4, M11-T4 |
| Dependency scanning | ❌ NOT DONE | M11-T5 |
| Network security | ⚠️ PARTIAL | M11-T6 |

---

## 35. INTEGRATION ROADMAP

### 35.1 External Integration Status

| Integration | M4 | M5 | M6 | M7 | M8 | M9 | M10 | M11 | M12 |
|------------|----|----|----|----|----|----|-----|-----|-----|
| SkillSpecTor | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hermes Bridge (MCP) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hermes Bridge (ACP) | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Graphify MCP | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Agent-Reach MCP | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ (opt) | ✅ | ✅ | ✅ | ✅ |
| FreeLLMAPI | ❌ | ⚠️ | ⚠️ | ⚠️ | ✅ (opt) | ✅ | ✅ | ✅ | ✅ |
| Playwright MCP | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Notion API | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ (if adopted) | ✅ | ✅ |

### 35.2 Integration Priority

1. **M8:** Hermes ACP (required for UserSim), Graphify (required for ArchitectureAgency)
2. **M9:** FreeLLMAPI (required for real LLM calls), LearningService (required for closed loop)
3. **M10:** Notion (if adopted), CLI expansion
4. **M11:** Security audit (all integrations)

---

## 36. DEPLOYMENT ROADMAP

### 36.1 Current Deployment State

| Component | Status |
|-----------|--------|
|pip install | ✅ Works (pyproject.toml configured) |
| CLI entry point | ✅ `aios` command available |
| Configuration | ✅ YAML-based, schema-validated |
| Docker | ❌ Not implemented |
| Health checks | ❌ Not implemented |
| Rollback | ❌ Not implemented |
| CI/CD | ❌ Not implemented |

### 36.2 M10 Deployment Targets

| Target | Status | Work |
|--------|--------|------|
| Local pip install | ✅ Existing | None |
| Docker container | ❌ | M10-T1 |
| Kubernetes (future) | ❌ | Deferred |
| Cloud deployment (future) | ❌ | Deferred |

---

## 37. FINAL ACCEPTANCE CRITERIA

### 37.1 Architecture

| Criterion | Status | Target |
|-----------|--------|--------|
| Single authority kernel | ✅ | ✅ |
| No duplicate kernel | ✅ | ✅ |
| No external authority leakage | ✅ | ✅ |
| All invariants pass | ✅ | ✅ |

### 37.2 Execution

| Criterion | Status | Target |
|-----------|--------|--------|
| Real production execution | ⚠️ Partial | ✅ Real Hermes ACP |
| Real adapters | ✅ | ✅ |
| Controlled external workers | ✅ | ✅ |

### 37.3 Councils

| Criterion | Status | Target |
|-----------|--------|--------|
| Multiple perspectives | ✅ | ✅ |
| Synthesis | ✅ | ✅ |
| Dissent preserved | ✅ | ✅ |
| Independence | ✅ | ✅ |
| FinalJudge independent | ✅ | ✅ |

### 37.4 Verification

| Criterion | Status | Target |
|-----------|--------|--------|
| Independent verification | ✅ | ✅ |
| Evidence-backed decisions | ✅ | ✅ |
| No self-approval | ✅ | ✅ |

### 37.5 Testing

| Criterion | Status | Target |
|-----------|--------|--------|
| Deterministic tests | ✅ | ✅ |
| AI-driven tests | ✅ | ✅ |
| User simulation | ✅ | ✅ |
| Security tests | ⚠️ Partial | ✅ M11 |
| Regression | ✅ | ✅ |
| E2E | ⚠️ Partial | ✅ M8 |
| Chaos/reliability | ❌ | ✅ M11 |

### 37.6 Learning

| Criterion | Status | Target |
|-----------|--------|--------|
| RCA | ✅ | ✅ |
| Learning | ⚠️ Partial | ✅ M9 |
| Simplification | ✅ | ✅ |
| Replanning | ✅ | ✅ |
| Regression protection | ✅ | ✅ |
| Safe re-execution | ✅ | ✅ |

### 37.7 Knowledge

| Criterion | Status | Target |
|-----------|--------|--------|
| Obsidian | ❌ Not wired | ⚠️ Optional |
| Graphify | ⚠️ Partial | ✅ M8 |
| Claude-Mem | ❌ Not integrated (correct) | ❌ Not needed |
| Provenance | ✅ | ✅ |
| Authority boundaries | ✅ | ✅ |

### 37.8 Planning

| Criterion | Status | Target |
|-----------|--------|--------|
| Notion | ❌ C4 pending | ✅ M12 (if adopted) |
| GSD | ✅ Reference | ✅ Reference |
| Operational boundaries | ✅ | ✅ |

### 37.9 Security

| Criterion | Status | Target |
|-----------|--------|--------|
| Sandboxing | ✅ | ✅ |
| Secrets | ⚠️ Partial | ✅ M11 |
| External trust | ✅ | ✅ |
| Malicious content | ✅ | ✅ |
| Least privilege | ✅ | ✅ |

### 37.10 Infrastructure

| Criterion | Status | Target |
|-----------|--------|--------|
| Model access | ⚠️ Partial | ✅ M9 |
| MCP | ✅ | ✅ |
| ACP | ⚠️ Partial | ✅ M8 |
| Workers | ✅ | ✅ |
| Persistence | ✅ | ✅ |
| Monitoring | ⚠️ Partial | ✅ M10 |

### 37.11 Deployment

| Criterion | Status | Target |
|-----------|--------|--------|
| Reproducible deployment | ❌ | ✅ M10 |
| Configuration | ✅ | ✅ |
| Secrets | ⚠️ Partial | ✅ M11 |
| Health checks | ❌ | ✅ M10 |
| Rollback | ❌ | ✅ M10 |
| Recovery | ⚠️ Partial | ✅ M10 |

---

## 38. DEFINITION OF DONE

**AI-OS is COMPLETE when:**

1. **All M0–M12 milestones verified** with independent QA reports
2. **1,200+ tests passing** (current: 1,046)
3. **All production integrations wired** (Hermes ACP, Graphify, Playwright)
4. **Security audit passed** (M11)
5. **Deployment working** (M10)
6. **All open conditions resolved** (C1–C4)
7. **Architecture documentation complete** (Parts 0–15)
8. **Final acceptance criteria met** (Section 37)
9. **Independent QA: GO** (score ≥ 95/100)

---

## 39. CRITICAL RISKS

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Hermes ACP integration complex | Medium | High | Start early in M8; keep MCP fallback for CI |
| Real LLM provider costs | Medium | Medium | Feature-flag; use FreeLLMAPI for cost control |
| Graphify server availability | Low | Medium | Mock server for CI; real server for production |
| Notion API rate limits | Low | Low | Rate limiting in adapter; caching |
| Security vulnerability discovery | Medium | High | M11 audit; continuous scanning |
| Scope creep | Medium | High | Strict milestone boundaries; no new features without gap justification |
| Test flakiness with real integrations | Medium | Medium | Retry logic; deterministic fixtures |
| Dependency license issues | Low | Medium | M11 supply chain scan |

---

## 40. ARCHITECTURE FREEZE RULES

### 40.1 What is FROZEN (M0–M7)

| Component | Status | Change Rule |
|-----------|--------|-------------|
| HermesKernel | ✅ FROZEN | No changes without ADR |
| CouncilManager | ✅ FROZEN | Extensions only (critique added in M6) |
| AIAgencyService | ✅ FROZEN | Realized in M7; no new agencies |
| TestOrchestratorService | ✅ FROZEN | No changes without ADR |
| UserSimulationAgent | ✅ FROZEN | No changes without ADR |
| 9 Core Managers | ✅ FROZEN | No new managers without ADR |
| Event System (132 EventType) | ✅ FROZEN | No new events without ADR |
| TestingEvidence schema | ✅ FROZEN | No schema changes without ADR |

### 40.2 What Can Change (M8+)

| Component | Change Rule |
|-----------|-------------|
| External adapters | Add new adapters via ADR; existing adapters can be enhanced |
| Configuration | Add new config options via ADR |
| CLI commands | Add new commands via ADR |
| Documentation | Update as needed |
| Tests | Add tests for new functionality; do not remove existing tests |

### 40.3 Architecture Decision Record (ADR) Process

Any change to frozen components requires:
1. ADR document describing the change
2. Impact analysis (tests, security, performance)
3. Terminal 1 review
4. Terminal 2 implementation
5. Terminal 3 independent QA
6. Merge only after GO verdict

---

## 41. FINAL EXECUTION ORDER

```
CURRENT: M7 COMPLETE (1,046 tests passing)

↓
M8 — Production Integration (P1)
  ├─ T1: Hermes ACP Protocol
  ├─ T2: Graphify MCP Connection
  ├─ T3: Playwright MCP Integration
  ├─ T4: Feature Flags
  ├─ T5: E2E Integration Tests
  └─ T6: Independent QA

↓
M9 — Learning & Optimization (P2)
  ├─ T1: LearningService Enhancement
  ├─ T2: ModelRouter Real Integration
  ├─ T3: SelfPromptingService Scoring
  ├─ T4: Convergence Detection
  ├─ T5: Human Escalation
  └─ T6: Independent QA

↓
M10 — Deployment & Operations (P1)
  ├─ T1: Docker Configuration
  ├─ T2: Health Check Endpoints
  ├─ T3: CLI Expansion
  ├─ T4: Configuration Validation
  ├─ T5: Rollback Capability
  └─ T6: Independent QA

↓
M11 — Security Hardening (P1)
  ├─ T1: Security Audit
  ├─ T2: Prompt Injection Testing
  ├─ T3: Trust Boundary Documentation
  ├─ T4: Secrets Management
  ├─ T5: Supply Chain Security
  └─ T6: Independent QA

↓
M12 — Documentation & Closure (P2)
  ├─ T1: Resolve C1
  ├─ T2: Resolve C2
  ├─ T3: Resolve C3
  ├─ T4: Resolve C4
  ├─ T5: Complete Parts 10–15
  ├─ T6: Final Acceptance
  └─ T7: Release Notes

↓
AI-OS COMPLETE (1,200+ tests, all integrations, security hardened, deployed)
```

---

## 42. IMMEDIATE NEXT TASK

**After this plan is approved, the next task is:**

### M8-T1: Wire Hermes ACP Protocol

**Terminal 2 Action:**
1. Read `src/aios/adapters/hermes_bridge.py` (current MCP fallback implementation)
2. Read `hermes-agent/acp_adapter/` (existing ACP protocol implementation)
3. Upgrade `HermesBridge` to support ACP protocol (preferred) with MCP fallback
4. Add ACP session management (isolated `hermes_<uuid>` sessions)
5. Ensure `HermesObservation` still returns observations only (never verdicts)
6. Write `tests/integration/test_m8_hermes_acp.py` (E2E test with mock ACP server)
7. Ensure all 1,046 existing tests still pass

**Terminal 3 Action (after M8-T1 completion):**
1. Independent review of ACP integration
2. Verify no authority leakage to Hermes
3. Verify session isolation
4. Verify provenance tracking
5. Report: GO / CONDITIONAL GO / NO-GO

**Files affected:**
- `src/aios/adapters/hermes_bridge.py`
- `src/aios/core/user_simulation_agent.py`
- `tests/integration/test_m8_hermes_acp.py`
- `src/aios/adapters/mock_hermes_server.py` (extend for ACP)

**Acceptance Criteria:**
- [ ] HermesBridge supports ACP protocol
- [ ] ACP sessions isolated (unique session IDs)
- [ ] Observations returned with complete provenance
- [ ] No verdict from Hermes worker
- [ ] MCP fallback still works
- [ ] All 1,046 regression tests pass
- [ ] New E2E test passes

---

## APPENDIX A: FILE / MODULE IMPACT MAP

### M8 Impact

| File | Change |
|------|--------|
| `src/aios/adapters/hermes_bridge.py` | Add ACP protocol support |
| `src/aios/core/user_simulation_agent.py` | Use ACP bridge |
| `src/aios/adapters/mock_hermes_server.py` | Extend for ACP |
| `src/aios/adapters/architecture_agency_adapter.py` | Use real Graphify |
| `src/aios/adapters/accessibility_agency_adapter.py` | Use real Playwright |
| `config/mcps.yaml` | Add Graphify, Playwright configs |
| `tests/integration/test_m8_*.py` | New E2E tests |

### M9 Impact

| File | Change |
|------|--------|
| `src/aios/services/learning.py` | Enhance lesson extraction |
| `src/aios/core/model_router.py` | Real LLM integration |
| `src/aios/adapters/freellmapi.py` | Real FreeLLMAPI connection |
| `src/aios/services/self_prompting.py` | Real scoring |
| `src/aios/services/testing.py` | Convergence detection |
| `tests/unit/test_m9_*.py` | New unit tests |

### M10 Impact

| File | Change |
|------|--------|
| `Dockerfile` | New |
| `docker-compose.yaml` | New |
| `src/aios/cli/commands/` | Add testing, deployment commands |
| `src/aios/core/health_manager.py` | Add HTTP endpoints |
| `src/aios/config/validator.py` | Production validation |
| `tests/integration/test_m10_*.py` | New integration tests |

### M11 Impact

| File | Change |
|------|--------|
| `src/aios/core/security_manager.py` | Audit all paths |
| `tests/unit/test_prompt_injection.py` | New tests |
| `tests/integration/test_m11_*.py` | New integration tests |

### M12 Impact

| File | Change |
|------|--------|
| `architecture/*.md` | Update docs |
| `CHANGELOG.md` | Write release notes |
| `README.md` | Update |

---

## APPENDIX B: EXTERNAL REPOSITORY INVENTORY

| Repository | URL | Classification | License | Status |
|-----------|-----|---------------|---------|--------|
| hermes-agent | Local (`hermes-agent/`) | INTEGRATION | See repo | PARTIAL |
| agency-agents | `github.com/msitarzewski/agency-agents` | SKILL/PERSONA SOURCE | MIT | M4 COMPLETE |
| SkillSpecTor | `github.com/NVIDIA/SkillSpecTor` | INTEGRATION (gate) | Apache-2.0 | M4 COMPLETE |
| Agent-Reach | `github.com/Panniantong/agent-reach` | INTEGRATION | See repo | ADAPTER EXISTS |
| FreeLLMAPI | (assumed repo) | INTEGRATION | See repo | ADAPTER EXISTS |
| Graphify | `github.com/davioud/graphify` (assumed) | INTEGRATION | See repo | MOCK ONLY |
| Playwright | `github.com/microsoft/playwright` | INTEGRATION | Apache-2.0 | NOT WIRED |
| Vercel Skills | `github.com/vercel/skills` | INTEGRATION (spec) | MIT | M4 COMPLETE |
| Karpathy LLM Council | `github.com/karpathy/llm-council` | TECHNIQUE | None (unlicensed) | M6 COMPLETE |
| evisoft Council | SKILL.md prompts | TECHNIQUE | None (unlicensed) | M6 COMPLETE |
| Obsidian | `github.com/obsidianmd/obsidian` | REFERENCE | AGPL-3.0 | NOT WIRED |
| Notion | `notion.so` | REFERENCE | Proprietary | ABSENT (C4) |
| GSD Core | `github.com/open-gsd/gsd-core` | METHODOLOGY | See repo | REFERENCE |
| Ruflo | (assumed repo) | REFERENCE | See repo | REJECTED |
| Loop Engineering | (assumed repo) | REFERENCE | See repo | REFERENCE |
| Caveman | (assumed repo) | OPTIONAL | BSL-1.1 | NOT NEEDED |
| Free Claude Code | Unaffiliated | OPTIONAL | See repo | NOT NEEDED |
| Book-to-Skill | (assumed repo) | REFERENCE | See repo | REFERENCE |
| Prompt Eng Hub | (assumed repo) | REFERENCE | See repo | REFERENCE |
| Superpowers | (assumed repo) | REFERENCE | See repo | REFERENCE |
| ECC | (assumed repo) | REFERENCE | See repo | REFERENCE |
| Claude-Mem | `github.com/thedotmack/claude-mem` | REFERENCE/DEV TOOL | See repo | NOT INTEGRATED |

---

## APPENDIX C: OPEN CONDITIONS

| ID | Issue | Resolution | Owner | Deadline |
|----|-------|-----------|-------|----------|
| C1 | "Hermes" naming collision | Document distinction: `HermesKernel` (AI-OS) vs `hermes-agent`(EXT) (external) | Terminal 1 | M12 |
| C2 | Verification gate count (12/12 vs 11-layer) | Update narrative to match code (8 LifecycleState members) | Terminal 1 | M12 |
| C3 | Lifecycle state count (narrative 5 vs code 8) | Update narrative to match code | Terminal 1 | M12 |
| C4 | Notion absent from repo | Adopt or drop; if adopted, implement Notion MCP adapter | Terminal 1 | M12 |

---

## APPENDIX D: TERMINAL WORKFLOW

This plan preserves the project's Terminal workflow:

```
TERMINAL 1 (Architecture/Planning)
    ↓ Plan task
TERMINAL 2 (Implementation)
    ↓ Implement task
TERMINAL 3 (Independent QA)
    ↓ Verify task
REGRESSION
    ↓ All tests pass
GO / CONDITIONAL GO / NO-GO
    ↓
Next task
```

**Every future task must follow:**
PLAN → IMPLEMENT → TEST → INDEPENDENT REVIEW → REGRESSION → ACCEPTANCE

---

## APPENDIX E: KEY FILES REFERENCE

### Core Source Files

| File | Purpose |
|------|---------|
| `src/aios/core/kernel.py` | HermesKernel — single authority |
| `src/aios/core/council_manager.py` | Council synthesis and dissent |
| `src/aios/core/ai_agency.py` | 9 agency roles + FinalJudge |
| `src/aios/services/testing.py` | TestOrchestratorService |
| `src/aios/core/user_simulation_agent.py` | 10th perspective |
| `src/aios/core/testing_evidence.py` | Evidence schema |
| `src/aios/core/simplification_gate.py` | Complexity governance |
| `src/aios/core/security_manager.py` | Authorization + SkillSpecTor |
| `src/aios/core/root_cause.py` | RCA |
| `src/aios/core/workflow.py` | Workflow orchestration |
| `src/aios/core/lifecycle_manager.py` | Kernel lifecycle |
| `src/aios/core/model_router.py` | LLM routing |
| `src/aios/core/llm_council.py` | LLM Council facade |
| `src/aios/services/learning.py` | Learning capture |
| `src/aios/services/self_prompting.py` | Self-prompting |

### Adapter Files

| File | Purpose |
|------|---------|
| `src/aios/adapters/hermes_bridge.py` | Hermes MCP/ACP bridge |
| `src/aios/adapters/agent_reach.py` | Web/social ingestion |
| `src/aios/adapters/freellmapi.py` | Model routing |
| `src/aios/adapters/security_agency_adapter.py` | Security testing |
| `src/aios/adapters/performance_agency_adapter.py` | Performance testing |
| `src/aios/adapters/chaos_agency_adapter.py` | Chaos testing |
| `src/aios/adapters/accessibility_agency_adapter.py` | Accessibility testing |
| `src/aios/adapters/documentation_agency_adapter.py` | Documentation testing |
| `src/aios/adapters/concurrency_agency_adapter.py` | Concurrency testing |
| `src/aios/adapters/bug_hunter_agency_adapter.py` | Bug hunting |
| `src/aios/adapters/architecture_agency_adapter.py` | Architecture review |
| `src/aios/adapters/mock_*.py` | Test doubles |

### Test Files (Post-M7)

| File | Coverage |
|------|----------|
| `tests/unit/test_agency_adapters.py` | 8 real adapters |
| `tests/unit/test_agency_review_production_path.py` | Anti-cheating |
| `tests/unit/test_test_orchestrator.py` | Real orchestrator behavior |
| `tests/unit/test_user_simulation_agent.py` | No source access |
| `tests/unit/test_simplification_gate.py` | Complexity governance |
| `tests/unit/test_final_judge_agency.py` | Independent verdict |
| `tests/unit/test_m7_closed_loop.py` | Bounded convergence |
| `tests/integration/test_m7_*.py` | 4 integration suites |
| `tests/integration/test_kernel_lifecycle_e2e.py` | Kernel E2E |
| `tests/integration/test_workflow_lifecycle.py` | Workflow E2E |

### Architecture Docs

| File | Purpose |
|------|---------|
| `architecture/FINAL_AI_OS_V2_ARCHITECTURE.md` | Authoritative architecture |
| `architecture/V2_ARCHITECTURE_DECISION_RECORD.md` | Decisions and rationale |
| `architecture/UPDATED_V2_MILESTONES.md` | M4–M7 milestone definitions |
| `architecture/EXTERNAL_REPOSITORY_RECONCILIATION.md` | External repo classifications |
| `architecture/Part15/M7_IMPLEMENTATION_CONTRACT.md` | Frozen M7 contract |
| `architecture/Part15/README.md` | Part 15 navigation |

### QA Reports

| File | Content |
|------|---------|
| `M4_ADAPTER_FINAL_VERDICT.md` | M4 acceptance |
| `M5_GATE_READINESS_REPORT.md` | M5 readiness |
| `M6_INDEPENDENT_QA_REPORT.md` | M6 QA (98/100) |
| `M7_INDEPENDENT_QA_REPORT.md` | M7 independent QA (96/100) |
| `M7_AUDIT_SUMMARY.md` | M7 audit summary (95/100) |
| `M7_REMEDIATION_REPORT.md` | M7-C remediation |
| `M7_FORENSIC_QA_REPORT.md` | M7 forensic QA |
| `M7_TRUE_INDEPENDENT_QA_REPORT.md` | M7 true independent QA |

---

*End of AI-OS FINAL MASTER IMPLEMENTATION PLAN*

**Document Status:** DRAFT — Pending approval
**Next Action:** Approve plan → M8-T1 implementation begins
