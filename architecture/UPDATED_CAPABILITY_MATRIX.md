# UPDATED AI-OS CAPABILITY MATRIX — WITH TESTING / QA LAYER

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Adds the multi-perspective testing + adversarial QA + User Simulation requirement (PART 9/12/13/14) to the existing `FULL_AI_OS_CAPABILITY_MATRIX.md`.

> Evidence rule: `IMPLEMENTED` = AI-OS V1 provides it; `PROVIDED (ext)` = external repo provides it; `DUPLICATED` = AI-OS AND external; `PARTIAL` = AI-OS partially implements; `MISSING` = absent in AI-OS, available externally; `UNCLEAR` = insufficient evidence; `N/A` = not applicable.
>
> All AI-OS determinations verified against `src/aios/` (`core/ai_agency.py`, `services/testing.py`, `core/council_manager.py`, `core/workflow.py`) and the local Hermes repo. References to "simulated" mean the V1 class exists but currently uses heuristic placeholders, not real execution. `[AI-OS SOURCE]` `[LOCAL REPOSITORY]`

---

## 1. CRITICAL FINDING — THE TESTING SCAFFOLD ALREADY EXISTS IN V1

Before adding new capabilities, the reconciliation found that **AI-OS V1 already contains the skeleton of the entire multi-perspective testing system**. It is currently *simulated* (string-heuristic placeholders), but the architecture, event types, and agent roles are present:

- `core/ai_agency.py` → `AIAgencyService` with **9 agencies**, each emitting `findings[]` + `verdict` + `confidence`:
  `SECURITY`, `PERFORMANCE`, `CHAOS` (failure/recovery), `ACCESSIBILITY`, `DOCUMENTATION`, `CONCURRENCY`, `BUG_HUNTER` (fuzz/edge), `ARCHITECTURE`, `FINAL_JUDGE` (aggregates findings → APPROVE/REJECT/CONDITIONAL).
- `services/testing.py` → `TestingService` (deterministic smoke-test runner; emits `TestGenerated`/`TestsPassed`/`TestsFailed`/`TestingCompleted`/`TestingFailed`).
- Events already defined: `TESTING_COMPLETED`, `TESTS_PASSED`, `TESTS_FAILED`, `TESTING_STARTED`, `TEST_GENERATED`, `REVIEW_APPROVED`, `FINAL_JUDGE_DECISION` (`events/types.py`).
- `core/council_manager.py` → `CouncilManager` with 5 consensus algorithms (`UNANIMOUS`, `MAJORITY`, `SUPERMAJORITY`, `WEIGHTED`, `RANKED_CHOICE`) + `CouncilMember.expertise`, `CouncilProposal`, `CouncilVote`, `CouncilDecision`, `dissent()`.
- `core/workflow.py` → full closed loop with `_on_root_cause_analyzed`, `_route_to_planning`, `_route_to_review`, `_route_to_coding`, failure recovery.

**Implication:** The V2 testing requirement is primarily a *realization/intensification* of an existing scaffold (replace simulated heuristics with real execution via subagents/Hermes/MCP), **not greenfield**. Frankenstein risk is LOW because the seams already exist.

---

## 2. CAPABILITY × SOURCE MATRIX (TESTING-EXTENDED)

Legend (new columns vs base matrix):
`AIOS` = AI-OS V1 · `SIM` = AI-OS present-but-simulated (scaffold) · `HER` = Hermes (local) · `AGA` = agency-agents personas · `KKC` = Karpathy LLM Council · `EVC` = evisoft Council · `RUF` = Ruflo · `ARE` = Agent-Reach · `SKS` = SkillSpecTor · `ECC` = Everything Claude Code · `GRF` = Graphify · `LOE` = Loop Engineering

| Capability | AIOS | SIM (scaffold) | HER | AGA | KKC | EVC | RUF | ARE | SKS | ECC | GRF | LOE | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| MULTI-PERSPECTIVE TESTING | ✅ | ✅(AIAgency) | ✅(workers) | ✅(personas) | | | ◐ | | | ✅ | | ◐ | IMPLEMENTED (scaffold) + INTEGRATION |
| TEST ORCHESTRATION | | ✅(workflow) | ✅(orchestrator) | ✅(orchestrator) | | | ✅ | | | ✅ | | ✅ | PARTIAL (workflow exists; no test-orchestrator service) |
| TEST PLANNING | ✅(planning) | | | ◐ | | | | | | | | | IMPLEMENTED + REFERENCE |
| FUNCTIONAL TESTING | | ✅(AIAgency stub) | ✅ | ✅(evidence-collector) | | | | | | ✅ | | | PARTIAL → INTENSIFY |
| API TESTING | | ✅(agency) | ✅ | ✅(api-tester) | | | | | | | | | PARTIAL → INTENSIFY |
| INTEGRATION TESTING | ✅(integration tests pass) | ✅(agency) | ✅ | ✅(api-tester) | | | | ✅ | | ✅ | | | IMPLEMENTED + PARTIAL |
| SECURITY TESTING | | ✅(SecurityAgency) | ✅(estop) | ✅(pentester) | | | | | ✅ | ✅(AgentShield) | | | PARTIAL + INTEGRATION |
| PERFORMANCE TESTING | | ✅(PerformanceAgency) | ✅ | ✅(benchmarker) | | | | | | | | | PARTIAL → INTENSIFY |
| RELIABILITY TESTING | | ✅(ChaosAgency) | | ✅(sre) | | | | | | | | ✅(sandbox) | PARTIAL → INTENSIFY |
| UX / UI TESTING | | ✅(AccessibilityAgency) | ✅(browser) | ✅(ux/access) | | | | | | | | | PARTIAL + INTEGRATION (browser) |
| ACCESSIBILITY TESTING | | ✅(AccessibilityAgency) | ✅(axe) | ✅(access-auditor) | | | | | | | | | PARTIAL → INTENSIFY |
| ADVERSARIAL TESTING | | ✅(BugHunter/Chaos) | ✅(red-team tools) | ✅(pentester/reality-chk) | | | | | ✅ | ✅ | | | PARTIAL + INTEGRATION |
| REGRESSION TESTING | ✅(802/802 suite) | ✅(agency) | ✅ | ✅(automation-eng) | | | | | | ✅ | | | IMPLEMENTED + PARTIAL |
| ARCHITECTURE REVIEW | | ✅(ArchitectureAgency) | ✅ | ✅(architect/reviewer) | | | ✅ | | | ✅ | ✅ | | PARTIAL + REFERENCE |
| CODE QUALITY TESTING | | ✅(DocAgency) | ✅ | ✅(code-reviewer) | | | ✅ | | | ✅ | | | PARTIAL + REFERENCE |
| USER SIMULATION | ❌ | | ✅(cloud browser) | ◐(ux-researcher) | | | | | | ✅ | | | MISSING → INTEGRATION (Hermes browser) |
| BROWSER TESTING | ❌ | | ✅(Browserbase/Use/Firecrawl CDP) | | | | | | | ✅ | | | MISSING → INTEGRATION (Hermes) |
| FAILURE/RECOVERY TESTING | ✅(root_cause/retry) | ✅(ChaosAgency) | ◐ | | | | | | | | | ✅ | IMPLEMENTED + PARTIAL |
| CONFIG/DEPLOY TESTING | ✅(deployment svc) | | | | | | | | | | | | IMPLEMENTED + REFERENCE |
| DATA CORRECTNESS TESTING | ❌ | | ✅(code exec) | ◐ | | | | | | | | | MISSING → INTENSIFY (new agency) |
| TEST GENERATION | | ✅(TestingService stub) | ✅ | ✅ | | | | | | ✅ | | | PARTIAL → INTENSIFY |
| TEST EXECUTION | | ✅(TestingService) | ✅(workers) | | | | ✅ | | | ✅ | | ✅ | PARTIAL → INTENSIFY |
| TEST EVIDENCE COLLECTION | | ✅(findings[]) | ✅(screenshots) | ✅(evidence-collector) | | | | | | | | | PARTIAL → INTENSIFY |
| TEST RESULT SYNTHESIS | ✅(FinalJudgeAgency) | | ✅(MOA) | | ✅ | ✅ | ✅ | | | ✅ | | | IMPLEMENTED (scaffold) + TECHNIQUE |
| INDEPENDENT JUDGE / ADJUDICATOR | ✅(FinalJudge/Council) | | ✅(MOA chair) | | ✅(chairman) | ✅(chairman) | ✅ | | | ✅ | | | IMPLEMENTED + TECHNIQUE |
| CROSS-AGENT CRITIQUE | ❌ | | ✅(MOA) | | ✅(cross-rank) | ✅(relabel-review) | | | | | | | MISSING → TECHNIQUE (KKC/EVC) |
| DISAGREEMENT DETECTION | ✅(CouncilVote/dissent) | | | | ◐ | ✅(dissenter) | | | | | | | IMPLEMENTED (partial) + TECHNIQUE |
| PERSPECTIVE ISOLATION | ✅(AgencyType enum) | | ✅(delegation) | ✅(personas) | ✅(tabs) | ✅(advisors) | | | | | | | IMPLEMENTED (scaffold) + TECHNIQUE |
| DEBATE / STAGED CRITIQUE | ❌ | | | | | ✅(staged flow) | | | | | | | MISSING → TECHNIQUE (EVC) |
| SANDBOXING (test env isolation) | ◐(agent quotas) | | ◐(worktree) | | | | ✅(WASM) | | | | | ✅(worktree) | PARTIAL + REFERENCE |
| TEST REPRODUCIBILITY | ❌(no fixture model) | | ◐ | | | | | | | | | | MISSING → BUILD (gap) |

✅ = provides · ◐ = partial/related · ❌ = absent · blank = not offered

---

## 3. CAPABILITY DETERMINATION (per testing category)

| Capability | Determined as | Evidence |
|---|---|---|
| MULTI-PERSPECTIVE TESTING | Implemented (9-agency scaffold) + Integration (Hermes workers, agency-agents personas) | `core/ai_agency.py:548` `AIAgencyService` `[AI-OS SOURCE]` |
| TEST ORCHESTRATION | Partial — `WorkflowManager` exists; no dedicated Test Orchestrator service | `core/workflow.py:224` `[AI-OS SOURCE]` |
| FUNCTIONAL/API/PERF/ACCESS/ARCH/CHAOS | Partial (agency stubs simulated) → INTENSIFY real execution | `core/ai_agency.py:161-545` `[AI-OS SOURCE]` |
| USER SIMULATION | Missing → Integration (Hermes cloud-browser) | `hermes-agent/agent/browser_provider.py` `[LOCAL REPOSITORY]` |
| BROWSER TESTING | Missing → Integration (Hermes Browserbase/Browser-Use/Firecrawl via CDP) | `hermes-agent/agent/browser_provider.py:50` `[LOCAL REPOSITORY]` |
| TEST SYNTHESIS / JUDGE | Implemented (FinalJudgeAgency + CouncilManager) + Technique (Hermes MOA, KKC chairman, EVC dissenter) | `core/ai_agency.py:507` `core/council_manager.py:115` `[AI-OS SOURCE]` |
| CROSS-AGENT CRITIQUE / DISAGREEMENT | Technique only (KKC anonymized cross-ranking; EVC relabel-then-review + side-with-dissenter) | WebFetch Karpathy/evisoft `[EXTERNAL REPOSITORY]` |
| REGRESSION / INTEGRATION | Implemented (802/802 suite) + Partial (agency) | `[AI-OS SOURCE]` |
| DATA CORRECTNESS / REPRODUCIBILITY | Missing → BUILD (new gap) | No evidence in V1 `[INFERENCE]` |
| SANDBOXING | Partial (agent quotas) + Reference (Loop Eng worktree, Ruflo WASM, Hermes worktree) | `[AI-OS SOURCE]` `[EXTERNAL]` |

---

## 4. CAPABILITY CLUSTERS → AI-OS LAYER (TESTING)

| Cluster | AI-OS Layer (exists) | External provider (status) | Action |
|---|---|---|---|
| Multi-perspective testers | `AIAgencyService` (9 agencies, simulated) | agency-agents personas (INTEGRATION), Hermes workers (INTEGRATION) | INTENSIFY — replace stubs with real execution |
| User Simulation / Browser | (none) | Hermes cloud-browser via MCP/ACP (INTEGRATION) | ADD — new agent, Hermes-backed |
| Test Orchestration | `WorkflowManager` (closed loop) | Hermes orchestrator, agency-agents orchestrator (REFERENCE) | EXTEND — add test-orchestration workflow |
| Synthesis / Judge | `FinalJudgeAgency` + `CouncilManager` | Hermes MOA (TECHNIQUE), KKC chairman (TECHNIQUE), EVC dissenter (TECHNIQUE) | ADOPT techniques, keep AI-OS authority |
| Evidence Collection | `AgencyResponse.findings[]` | Hermes screenshots, agency-agents evidence-collector (INTEGRATION/REFERENCE) | INTENSIFY — structure evidence schema |
| Security/Adversarial testing | `SecurityAgency` (stub) | SkillSpecTor (INTEGRATION gate), agency-agents pentester (INTEGRATION), ECC AgentShield (REFERENCE) | INTENSIFY + gate |
| Sandboxing | agent quotas | Loop Eng worktree (REFERENCE), Hermes worktree (REFERENCE) | BUILD/POLISH isolation |

---

## 5. CONSOLIDATION RULES (carried forward + testing-specific)

1. **One kernel** — AI-OS. Ruflo/LLM-Council/evisoft-Council are NOT kernels.
2. **One council layer** — `CouncilManager`. KKC/EVC are *synthesis techniques*, not a second council.
3. **One skill format** — open `SKILL.md`.
4. **One model-routing path** — behind `mcp_manager`/AI Runtime.
5. **One memory core** — AI-OS 5-tier.
6. **MCP is the only integration boundary** — Hermes testing workers enter via MCP/ACP.
7. **Testing testers GENERATE evidence; AI-OS evaluation/verification EVALUATES; CouncilManager SYNTHESIZES; AI-OS kernel DECIDES.** No parallel decision loop.
8. **Independence model** — the implementation builder MUST NOT be the test generator, executor, user-simulator, or judge (see `V2_ARCHITECTURE_DECISION_RECORD.md`).

---

*End of updated capability matrix. Every claim tagged to `[AI-OS SOURCE]` / `[LOCAL REPOSITORY]` / `[EXTERNAL REPOSITORY]` / `[INFERENCE]`.*
