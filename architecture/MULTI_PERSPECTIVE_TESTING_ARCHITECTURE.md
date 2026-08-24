# MULTI-PERSPECTIVE TESTING ARCHITECTURE

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Conceptual architecture of the multi-perspective testing system (PART 12). Designs which components are needed and which can be personas/skills/subagents/council-roles/services/external-workers — minimizing unnecessary agents.

> Built on the verified V1 scaffold: `AIAgencyService` (9 agencies), `TestingService`, `CouncilManager`, `WorkflowManager` closed loop. `[AI-OS SOURCE]`
> No code changed.

---

## 1. PRINCIPLE: INTENSIFY, DON'T PROLIFERATE

The task lists 16 candidate testing components (Test Orchestrator, Test Planner, Functional/Security/Performance/API/Integration/Reliability/UX/Architecture/Adversarial/Regression Testers, User Simulation Agent, Evidence Collector, Independent Judge, Council Synthesizer). **Most already exist as AI-OS agencies or map to council/mcp constructs.** We must NOT spawn 16 permanent agents.

Mapping to existing AI-OS constructs:

| Task's candidate | AI-OS existing construct | Action |
|---|---|---|
| Test Orchestrator | `WorkflowManager` + new thin `TestOrchestratorService` | EXTEND (1 new service) |
| Test Planner | `planning` service (Part 10) | REUSE |
| Functional Tester | `BugHunterAgency` + `SecurityAgency`(partial) | INTENSIFY |
| Security Tester | `SecurityAgency` | INTENSIFY (+ SkillSpecTor gate) |
| Performance Tester | `PerformanceAgency` | INTENSIFY |
| API Tester | `ArchitectureAgency`(API) + agency-agents api-tester persona | INTENSIFY + persona |
| Integration Tester | `AIAgencyService` + Hermes worker + Agent-Reach | INTENSIFY |
| Reliability Tester | `ChaosAgency` | INTENSIFY |
| UX Tester | `AccessibilityAgency` + agency-agents ux-researcher | INTENSIFY + persona |
| Architecture Reviewer | `ArchitectureAgency` | INTENSIFY |
| Adversarial Tester | `BugHunterAgency` + `ChaosAgency` + agency-agents pentester | INTENSIFY + persona |
| Regression Tester | 802/802 suite + agency-agents automation-eng | INTENSIFY (AI-generated) |
| User Simulation Agent | **NEW** `UserSimulationAgent` (Hermes browser) | ADD (1 new agent) |
| Evidence Collector | `AgencyResponse.findings[]` → typed `TestingEvidence` | INTENSIFY (schema) |
| Independent Judge | `FinalJudgeAgency` + `CouncilManager` | INTENSIFY |
| Council Synthesizer | `CouncilManager.synthesize()` + MOA technique | EXTEND (critique stage) |

**Net new permanent components: 2** — `TestOrchestratorService` and `UserSimulationAgent`. Everything else is intensification of the existing 9-agency scaffold or adoption of a technique. The 9 agencies ARE the "testers"; they are council *members*, not separate subsystems.

---

## 2. CONCEPTUAL ARCHITECTURE

```
                          AI-OS GOAL / TARGET UNDER TEST
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │   TestOrchestratorService    │   (NEW, thin)
                       │  (plans perspectives,         │
                       │   dispatches, collects,       │
                       │   normalizes evidence)        │
                       └──────────────┬───────────────┘
                                      │  parallel dispatch
        ┌──────────────┬──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼              ▼
  SECURITY        PERFORMANCE     CHAOS          ACCESSIBILITY  DOCUMENTATION
  Agency          Agency          Agency         Agency         Agency
  (intensified)  (intensified)   (intensified)  (intensified)  (intensified)
        │              │              │              │              │
  ┌─────┴──────┬───────┴──────┬──────┴──────┬──────┴──────┬──────┴──────┐
  ▼            ▼              ▼              ▼              ▼            ▼
 CONCURRENCY BUG_HUNTER  ARCHITECTURE   REGRESSION      USER SIM      (external)
 Agency      Agency      Agency         (suite+AI)     AGENT         workers
 (intensified)(intensified)(intensified) (intensified)  (NEW, Hermes
  │            │            │              │            browser)
  └────────────┴────────────┴──────────────┴──────────────┘
                                      │  structured evidence (TestingEvidence)
                                      ▼
                       ┌──────────────────────────────┐
                       │  Evidence Normalization        │
                       │  (typed schema, severity,      │
                       │   proof, provenance)           │
                       └──────────────┬───────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │   CouncilManager              │
                       │   TestingCouncil:              │
                       │   1. convene(perspectives)     │
                       │   2. critique()  [NEW stage]   │
                       │      - anonymized cross-rank   │
                       │      - dissenter-override       │
                       │   3. synthesize()/decide()      │
                       │   4. FinalJudge → verdict       │
                       └──────────────┬───────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │   AI-OS Verification           │
                       │   (11-layer validation)        │
                       └──────────────┬───────────────┘
                                      │
                          ┌───────────┴───────────┐
                        PASS                     FAIL
                          │                        │
                       COMPLETE              RCA → Learning
                                                 → Replan → Re-execute
                                                 → Retest (loop)
```

---

## 3. COMPONENT RESPONSIBILITIES

### TestOrchestratorService (NEW, thin)
- Translates a target + intent into a **test plan**: which perspectives apply (not all 9 for every target).
- Dispatches agencies **in parallel** (asyncio.gather, as `AIAgencyService.run_full_review` already does).
- Collects `TestingEvidence` from each, normalizes to a common schema.
- Convenes the `TestingCouncil` in `CouncilManager`.
- Emits `TestingCompleted`/`TestingFailed` (existing events) → feeds verification + closed loop.
- **Does NOT decide.** It orchestrates; `CouncilManager` + verification decide.

### The 9 Agencies as Perspectives (INTENSIFY)
Each `BaseAgency.review()` is upgraded from heuristic string-match to real execution:
- **SecurityAgency** → invokes SkillSpecTor gate + agency-agents pentester persona (Hermes worker) for active checks.
- **PerformanceAgency** → runs load/benchmark via Hermes worker or local harness; collects metrics.
- **ChaosAgency** → failure-injection experiments (extends existing root_cause/retry surface).
- **AccessibilityAgency** → WCAG/axe execution (Hermes browser + agency-agents access-auditor).
- **DocumentationAgency** → doc/usability review.
- **ConcurrencyAgency** → race/deadlock analysis.
- **BugHunterAgency** → fuzz/edge-case generation.
- **ArchitectureAgency** → boundary/dependency/contract checks (+ Graphify evidence).
- **FinalJudgeAgency** → aggregates normalized evidence → APPROVE/REJECT/CONDITIONAL.

### UserSimulationAgent (NEW)
- A distinct AI Agency persona (NOT a developer persona) that drives the target app as a *user* via **Hermes cloud-browser (ACP session)**.
- Executes realistic workflows, confused/incorrect inputs, edge-case paths; observes errors, navigation failures, missing feedback.
- Emits `UserSimulationCompleted` with structured UX evidence (task completion %, blockers, confusing states).
- See `USER_SIMULATION_AGENT_SPEC.md` for full spec.

### Evidence Collector (INTENSIFY — schema, not a separate agent)
- Replaces loose `findings[]` dicts with a typed `TestingEvidence` dataclass:
  `{ perspective, target, actions: [], observations: [], severity, proof: [screenshot/dom/trace], confidence, provenance }`.
- Each agency populates it; `TestOrchestratorService` normalizes.

### Independent Judge / Council Synthesizer (INTENSIFY + EXTEND)
- `CouncilManager` gains a `critique()` stage adopting KKC (anonymized two-axis ranking) + EVC (relabel-then-review, dissenter-override).
- `FinalJudgeAgency` remains the authority that converts synthesized perspectives into a verdict.
- See `COUNCIL_SYNTHESIS_ARCHITECTURE.md`.

---

## 4. WHICH CAN BE PERSONAS / SKILLS / SUBSERCIENTS / EXTERNAL WORKERS

| Construct | Form | Why |
|---|---|---|
| 9 agencies | **AI-OS council members** (intensified) | Already exist; avoid new agents |
| Tester sub-behaviors | **SKILL.md personas** (agency-agents, curated) | Content feed via M4 adapter |
| Per-perspective execution | **Hermes workers (ACP)** or local subagents | Isolation + real execution |
| Browser/UX/user-sim | **Hermes cloud-browser (ACP)** | Only real browser substrate |
| Synthesis technique | **CouncilManager.critique()** (KKC/EVC technique) | No second council |
| Security gate | **SkillSpecTor (MCP)** | Integration, not new code |
| Evidence graph | **Graphify (MCP)** | Integration |

**Minimization result:** Only **2 new permanent components** (`TestOrchestratorService`, `UserSimulationAgent`); the rest is intensification + technique adoption. No 16-agent sprawl.

---

## 5. INDEPENDENCE BOUNDARY (preview — full in ADR)

The orchestrator dispatches; agencies execute; User Simulation simulates; `CouncilManager` synthesizes; verification decides. **None of these may be the implementation builder.** The builder's artifacts are the *target under test*, never a voter in their own test council.

---

*End of multi-perspective testing architecture. Conceptual only; intensifies verified V1 scaffold.*
