# V2 ARCHITECTURE DECISION RECORD (CONSOLIDATED FINAL BLUEPRINT)

**Terminal 1 — Architecture / Reconciliation / Planning Authority**
**Date:** 2026-08-23
**Status:** DEFINITIVE IMPLEMENTATION BLUEPRINT (READ-ONLY; no code, no installs). Supersedes the earlier "testing extension" version of this file and consolidates `TERMINAL_1_V2_FREEZE_RECONCILIATION_REPORT.md` + `TERMINAL_1_V2_IMPLEMENTATION_PLAN.md`.

**Evidence labels:** `[EXISTING]`=present/working in `src/` · `[PARTIAL]`=scaffolded but simulated/incomplete · `[PLANNED]`=build in M7 · `[REFERENCE]` · `[OPTIONAL]` · `[CONTRADICTION]`.

**Precedence rule (brief §30):** V1 source + latest explicitly approved decisions beat assumptions. Never claim an integration is implemented when only planned.

---

## 1. EXECUTIVE SUMMARY

Adopt **M4 → M5 → M6 → M7**. V2 = **intensify + realize + connect + verify + learn + simplify** the verified V1 scaffold — not a rebuild. One `HermesKernel` (sole authority); one `CouncilManager` substrate serving **two council *mechanisms*** (LLM synthesis + Contrarian/Outsider dissent) and **two council *domains*** (reasoning vs testing/verification); one verification authority; one reused M3 closed loop.

**New permanent components (each passed the §20/§31 necessity test — no existing component can do it):**
1. `TestingEvidence` schema (typed, provenanced) — replaces loose `dict` evidence.
2. `TestOrchestratorService` — **extends** `WorkflowManager` (no duplication).
3. `UserSimulationAgent` — the one genuinely missing testing perspective.
4. `CouncilManager.critique()` — new stage on existing `CouncilManager`.
5. `LLMCouncil` façade — Analyst/Contrarian/Outsider/Skeptic/Specialist/Simplifier roles over `CouncilManager`.
6. `SelfPromptingService` — bounded self-questioning.
7. `SimplificationGate` — pre-acceptance complexity control.

**Verdict: READY WITH CONDITIONS.** Conditions C1–C5 must close before M7 code starts (all are vocabulary/doc/edict actions — no production code).

---

## 2. PROBLEM STATEMENT

V1 testing is **SIMULATED, not real** (`SecurityAgency.review()` does `asyncio.sleep(0.5)` + string-matches `"sql"`/`"query"` — `ai_agency.py:167-213`). The 9 `AgencyType` roles, `CouncilManager`, `WorkflowManager`, `LearningService`, `ModelRouter`, `MCPManager` all exist but are stubbed/unwired. V2 must realize them and connect external execution behind boundaries — without Frankenstein duplication.

---

## 3. V1 BASELINE (authoritative, protected)

| Component | Evidence | State |
|---|---|---|
| `HermesKernel` (core authority) | `kernel.py:142`, `constants.py:9` | `[EXISTING]` |
| 9 Core Managers (State/Storage/Workflow/Resource/Health/Security/Capability/Observability/Lifecycle) | `kernel.py:473-583` | `[EXISTING]` |
| `CouncilManager` (convene/propose/vote/decide/dissent + **5** consensus algos; NO `critique()`) | `council_manager.py` | `[EXISTING]`+`[PLANNED stage]` |
| `AIAgencyService` + 9 `AgencyType` roles | `ai_agency.py:37-48,561-569` | `[PARTIAL]` simulated |
| `TestingService` scaffold | `services/` | `[PARTIAL]` |
| `LearningService` (RCA→capture wired) | `services/learning.py:33`, `root_cause.py:382-404` | `[PARTIAL]` logs only |
| `WorkflowManager` (register/execute handlers) | `workflow.py:224,477,711` | `[EXISTING]` |
| `ModelRouter` (provider registry + `route()`) | `model_router.py:89,207,236` | `[EXISTING]` |
| `SecurityManager`, `RCA` | core | `[EXISTING]` |
| `FinalJudgeAgency` | `ai_agency.py:507` | `[EXISTING]` |
| 121 `EventType`s, EventBus | `events/core/types.py` | `[EXISTING]` |
| 802/802 collected tests; **12/12 gates** | `pytest --collect-only`=802; `Part15/TERMINAL_3_FINAL_V1_RELEASE_QA.md:182` | `[EXISTING]` (collection-confirmed; execution run pre-M7 — R1) |
| `MCPManager` (generic, unfilled) | `core/mcp_manager.py`; only `config/mcp/test_mcp.json` | `[PARTIAL]` no servers wired |
| `hermes-agent` (EXT) external browser repo | `/hermes-agent/` on disk, **gitignored** (`dc09784`) | `[DISK]` untracked |
| **Notion** | zero refs in `src/`/`config/` | ⚠️ **ABSENT (C4)** |
| Obsidian / Graphify | memory-system labels only (`memory.py:40-41`) | `[PARTIAL]` no MCP wiring |

---

## 4. V1 → V2 GAP ANALYSIS

| Capability | V1 | V2 action |
|---|---|---|
| Agency execution | simulated | realize via adapters/MCP/ACP |
| `TestingEvidence` | loose `dict` | add typed schema |
| `TestOrchestratorService` | absent | extend `WorkflowManager` |
| `UserSimulationAgent` | absent | new perspective on `hermes-agent`(EXT) |
| `critique()` | absent | new `CouncilManager` stage |
| LLM Council + Contrarian/Outsider | absent | façade over `CouncilManager` |
| Self-Prompting | absent | bounded `SelfPromptingService` |
| Learning (lesson-extraction) | log capture | add extraction + feedback |
| Simplification Gate | absent | pre-acceptance control |
| Isolation/sandbox | none | per-test env separation |
| External MCP/ACP | none wired | integrate per boundary |
| Notion plane | absent | C4: adopt-or-drop |

---

## 5. FINAL ARCHITECTURE (three parts, per brief §2)

**PART 1 — PLANNING / ORGANIZATION** (NOT kernel): Notion (planning/tracking), Obsidian (PKM vault), Graphify (graph/context), GSD Core (methodology). Organizational only.

**PART 2 — EXECUTION / INTELLIGENCE / LEARNING:** AI Agency, `hermes-agent`(EXT) workers, agency-agents personas, FreeLLMAPI via `ModelRouter`, subagents, self-prompting, self-loop, learning, skills, MCP/ACP. AI-OS governs.

**PART 3 — REQUIREMENTS / GOVERNANCE / VERIFICATION / TESTING:** requirements, policy, security, verification, testing, councils, adjudication, independence, evidence, final decisions, deployment gates. AI-OS final authority.

---

## 6. COMPONENT LIST (permanent AI-OS)

Existing `[EXISTING]`: `HermesKernel`, 9 Core Managers, `CouncilManager`, `AIAgencyService` (9 roles), `WorkflowManager`, `ModelRouter`, `LearningService`(partial), `MCPManager`(partial), `SecurityManager`, `RCA`, `FinalJudgeAgency`, EventBus.

New `[PLANNED]`: `TestingEvidence`, `TestOrchestratorService`, `UserSimulationAgent`, `critique()`, `LLMCouncil`, `SelfPromptingService`, `SimplificationGate`.

**Not created (anti-Frankenstein):** second kernel, second `CouncilManager`, second verification, second loop, native AI-OS browser, in-house browser farm, vendored KKC/EVC code.

---

## 7. COUNCIL TAXONOMY — TWO MECHANISMS × TWO DOMAINS (resolves C5)

Brief-3 refines the earlier "LLM Council vs Testing Council" wording. Correct model:

- **Mechanism A — LLM Council (synthesis):** independent opinions, cross-review, disagreement detection, synthesis. KKC techniques adopted (anonymized cross-ranking, chairman) — NOT imported.
- **Mechanism B — Contrarian/Outsider (dissent):** actively challenges assumptions ("What if majority is wrong?", "What would an outsider notice?", "Are we overengineering?"). Adopts evisoft techniques (worldview diversity, relabel-then-review, dissenter-override) as TECHNIQUES.

- **Domain 1 — Reasoning Council:** uses A+B for architecture/planning/design/self-criticism. → `LLMCouncil` façade.
- **Domain 2 — Testing Council:** consumes `TestingEvidence`; verification-domain session on the *same* `CouncilManager`. → Testing Council = a `convene` topic + membership (builder excluded), not a new hierarchy.

All four are served by the **single `CouncilManager`** via `convene/propose/vote/decide/dissent/critique`. **No second council framework.** `[CONTRADICTION→RESOLVED as C5]`: earlier plan's "Testing Council as a separate façade" is demoted to a domain/session; `LLMCouncil` remains the only reasoning façade.

---

## 8. LLM COUNCIL ROLES (Mechanism A + B over `CouncilManager`)

| Role | Mandate |
|---|---|
| Analyst / Primary | strongest conventional solution |
| Contrarian | why might this be wrong |
| Outsider | what would someone without our assumptions see |
| Skeptic / Critic | which claims lack evidence |
| Specialist | what does the domain imply |
| Simplifier | same outcome with less complexity |

Flow: `convene` → independent `propose` (blind) → `critique()` (anonymized cross-ranking + relabel-then-review) → `dissent()` preserved → `decide()` → synthesis. Feeds planning/self-prompting. **Does NOT replace verification or Testing Council.**

---

## 9. TESTING SYSTEM (9 + 1 perspectives)

`AIAgencyService` roles remain canonical testers; realize via adapters/MCP/ACP. **No new permanent agencies beyond `UserSimulationAgent`.**

| # | Perspective | Owner `[EXISTING]` | Realization `[PLANNED]` |
|---|---|---|---|
| 1 | Security | `SecurityAgency` | `hermes-agent`(EXT)+SkillSpecTor gate+agency-agents pentester |
| 2 | Performance | `PerformanceAgency` | benchmark worker/local harness |
| 3 | Chaos/Reliability | `ChaosAgency` | root_cause/retry + fault injection |
| 4 | Accessibility | `AccessibilityAgency` | `hermes-agent`(EXT) browser + axe |
| 5 | Documentation | `DocumentationAgency` | static + LLM review |
| 6 | Concurrency | `ConcurrencyAgency` | static + dynamic analysis |
| 7 | BugHunter | `BugHunterAgency` | fuzz generation |
| 8 | Architecture | `ArchitectureAgency` | Graphify evidence + review |
| 9 | FinalJudge | `FinalJudgeAgency` | deterministic verdict → verification |
| 10 | User Simulation | **`UserSimulationAgent`** `[PLANNED]` | `hermes-agent`(EXT) ACP browser |

---

## 10. USER SIMULATION AGENT

First-class perspective; **NOT** BugHunter/a11y/dev.
- **Receives:** app purpose + user goal + user-level context. **NOT** source code as primary basis.
- **Behavior:** discovery-first; expected/confused/incorrect actions; back/forward; refresh; empty/invalid; boundary; interrupted; recovery.
- **Evaluates:** goal_completion_pct, workflow_success, usability_blockers, confusing_states, navigation_failures, missing_feedback, invalid_input_results, recovery_behavior, expected_vs_observed.
- **Executes on:** `hermes-agent`(EXT) isolated ACP browser. **Hermes executes; AI-OS decides** (C1 vocabulary: `hermes-agent`(EXT) ≠ `HermesKernel`).

**Evidence `UserSimulationCompleted` extends `TestingEvidence`:** `{user_goal, exploration_strategy, goal_completion_pct, workflow_success, actions[], observations[], unexpected_errors[], usability_blockers[], navigation_failures[], confusing_states[], missing_feedback[], invalid_input_results[], recovery_behavior, expected_vs_observed, proof[](screenshots/DOM/traces/session_id), provenance, hermes_session_id}`.

---

## 11. TEST ORCHESTRATION — `TestOrchestratorService` EXTENDS `WorkflowManager`

Source inspection (`workflow.py:224,477,711` — `register_workflow`/`register_step_handler`/`execute_handler`) confirms `WorkflowManager` can absorb plan→dispatch→execute→collect→normalize. **Decision: EXTEND, do NOT duplicate.** `TestOrchestratorService` registers a test-run workflow + step handlers per perspective; adds normalize→submit-to-council. No second orchestrator.

---

## 12. STRUCTURED TESTING EVIDENCE

`TestingEvidence` `[PLANNED]` (replaces loose `dict`):
`{evidence_id, perspective, target, test_id, action[], observation[], severity, confidence, result, proof[](screenshot/DOM/log/trace/output/session_id), provenance(source/worker/session/ts/env), environment, timestamp, reproducibility}`.
User-sim extension: §10 fields. Machine-checkable. `provenance` mandatory (INV-007).

---

## 13. LEARNING LAYER

`LearningService` `[PARTIAL]` already captures from RCA (`root_cause.py:382-404`). **V2 adds:** lesson extraction (failure→fix categorization), validation, knowledge update, feedback into planning/self-prompting. Inputs: failures, RCA, successful/unsuccessful fixes, test evidence, council disagreements, traces, simplification decisions, user-sim findings. Progressive mistake-avoidance.

---

## 14. SELF-PROMPTING

`SelfPromptingService` `[PLANNED]` — bounded, traceable, objective-linked.
Seeds: "What assumption am I making?" / "What could fail?" / "What evidence would prove this?" / "What would the Contrarian argue?" / "Can this be simplified?" / "What requirement have we not tested?"
**Bounds:** max-depth, token budget, must cite objective, no open recursion. Routes into `LLMCouncil`. Reuses `CouncilManager`.

## 15. SELF-LOOPING

Reuses **M3 closed loop** `[EXISTING]` (no competing loop). `FAIL→RCA→Learning→Replan→Self-Prompt→Re-execute→Retest`. Bounded by iteration limit, budget, convergence, no-improvement detection, regression protection, human escalation.

---

## 16. SIMPLIFICATION LAYER

`SimplificationGate` `[PLANNED]` — mandatory, **before** final verification; its changes are **retested**. Simplifier detects: unnecessary abstraction, duplicated services/state/agents, redundant deps, complex control flow, premature optimization, excessive config, competing orchestrators/councils, unnecessary repos/MCP/layers. Distinguishes necessary vs accidental complexity; never removes necessary safeguards. Integrates with Contrarian/Outsider council + code review + learning.

---

## 17. EXTERNAL REPOSITORY CLASSIFICATION (authoritative matrix)

| Resource | Class | In-repo | AI-OS role | Authority |
|---|---|---|---|---|
| `HermesKernel` | CORE | `[EXISTING]` | sole authority | AI-OS |
| `hermes-agent`(EXT) | INTEGRATION | `[DISK]` gitignored | browser/workers/ACP exec | AI-OS decides |
| agency-agents | SKILL/PERSONA | `[REFERENCE]` | curated personas (~8-10) | AI-OS |
| SkillSpecTor | INTEGRATION (gate) | `[REFERENCE]` | security/adversarial gate | AI-OS |
| Agent-Reach | INTEGRATION | `[REFERENCE]` | web/social ingest | AI-OS |
| Vercel Skills | INTEGRATION (spec) | `[REFERENCE]` | SKILL.md packaging | AI-OS |
| FreeLLMAPI | INTEGRATION | `[REFERENCE]` | model/provider abstraction via `ModelRouter` | AI-OS |
| Playwright MCP | INTEGRATION | `[REFERENCE]` | deterministic browser test | AI-OS |
| Trail of Bits Skills | INTEGRATION/SEC | `[REFERENCE]` | security skills | AI-OS |
| Codebase Memory MCP | INTEGRATION CANDIDATE | `[REFERENCE]` | large-repo context (investigate) | AI-OS |
| Notion MCP | PLANNING | **ABSENT (C4)** | planning/tracking | AI-OS |
| Obsidian MCP | KNOWLEDGE | `[PARTIAL]` label | PKM vault | AI-OS |
| Graphify | KNOWLEDGE | `[PARTIAL]` label | graph/context | AI-OS |
| GSD Core | METHODOLOGY | `[REFERENCE]` | planning/execution method | AI-OS |
| Free Claude Code | OPTIONAL/ENV | `[REFERENCE]` | dev tooling | AI-OS |
| Ruflo | REFERENCE | `[REFERENCE]` | do NOT replace kernel | — |
| Loop Eng / Prompt Hub / Book-to-Skill / Superpowers / ECC | REFERENCE | — | technique only | — |
| Caveman | OPTIONAL | — | compression if required | — |
| KKC / evisoft | TECHNIQUE ONLY | — | critique techniques, not subsystems | — |
| ego-lite | REFERENCE/OPT | — | not core without evidence | — |

---

## 18. MCP / ACP BOUNDARY

`MCPManager` `[PARTIAL]` present, no servers wired. **V2 wires:** `hermes-agent`(EXT) (ACP preferred for worker sessions + provenance; MCP fallback), Playwright MCP, SkillSpecTor MCP, Graphify MCP, Notion MCP (if adopted), FreeLLMAPI MCP, agency-agents/Vercel via SKILL adapter. All external outputs = external observations until normalized+verified by AI-OS. Adapters only; no kernel change.

---

## 19. INDEPENDENCE / TRUST MODEL

Builder ≠ Test Generator ≠ Test Executor ≠ User Simulator ≠ Council Reviewer ≠ Final Judge.
- Builder artifact = input-only to testers.
- `hermes-agent`(EXT) returns observations, **no verdicts**; ACP session isolated + provenanced.
- Perspective↔perspective: anonymous during critique; one vote each.
- Testing Council membership **excludes builder**; `FinalJudgeAgency` independent of builder.
- AI-OS Verification = final control authority.

---

## 20. VERIFICATION & FAILURE ROUTING

All major outputs → **AI-OS Verification** `[EXISTING, 12 gates]`. Testing provides evidence; councils synthesize; `FinalJudgeAgency` gives final testing verdict; Verification = system-level gate. FAIL → Council → FinalJudge → Verification FAIL → RCA → Learning → Replan → Re-execute → Retest. **No parallel recovery loop.**

---

## 21. SANDBOXING / ISOLATION

Min: builder env ≠ testing env. Browser: isolated `hermes-agent`(EXT) ACP session. Consider git worktree / container / isolated process / test DB / disposable fixtures (M7-E). No cross-contamination.

## 22. ADVERSARIAL TESTING

Real execution via SkillSpecTor gate + Trail of Bits + agency-agents pentester + `SecurityManager`. SkillSpecTor = security gate; external tooling ≠ final authority.

## 23. PERF/ACCESS/INTEGRATION (P2)

Realize after P1 stable: performance/load, accessibility, integration probes, data correctness, AI-generated regression, reproducibility. Do not overbuild pre-P1.

---

## 24. MILESTONE PLAN (verified; do not invent)

| Milestone | Scope | State |
|---|---|---|
| **M4** | SKILL.md adapter + SkillSpecTor security gate | `[PLANNED]` |
| **M5** | MCP/ACP bridge (`hermes-agent`(EXT), Playwright, Graphify, FreeLLMAPI via `ModelRouter`) + AI-OS-side ACP adapter | `[PLANNED]` |
| **M6** | `critique()` + `LLMCouncil` façade + `SelfPromptingService` | `[PLANNED]` |
| **M7** | Testing intensification: real 9-agency, `TestOrchestratorService`(extend WF), `TestingEvidence`, `UserSimulationAgent`+`hermes-agent`(EXT) browser, isolation, Testing Council `critique()`, independent judge, adversarial, `SimplificationGate`, learning integration, closed-loop retest, seeded-defect acceptance | `[PLANNED]` |

M7 internal: A evidence → B orchestrator → C 9-agency → D UserSim+hermes → E isolation → F critique → G judge → H adversarial → I loop → J seeded acceptance.

## 25. DEPENDENCY GRAPH

```
M4 ─┐
    ├─► M5 ─┐
M6a critique() ─┘        ├─► M7
M6b LLMCouncil ───────────┤
M6c SelfPrompting ────────┤
existing WorkflowManager/ModelRouter/LearningService ──┘
```

---

## 26. RESPONSIBILITY / TRUST / INDEPENDENCE MATRICES (condensed)

**Responsibility (OWNER/EXECUTOR/SOURCE/REFERENCE):**
- Decisions/Verification/Council/RCA/Learning/Replan → **AI-OS OWNER**.
- Browser/worker execution → `hermes-agent`(EXT) **EXECUTOR**.
- agency-agents personas → **SOURCE**.
- Obsidian/Graphify/Notion → **SOURCE/ORG**.
- GSD → **REFERENCE (method)**.
- FreeLLMAPI → **INFRA (model access)**.

**Trust:** all external outputs = untrusted observations until AI-OS-normalized.

**Independence (≠):** Builder / TestGen / TestExec / UserSim / CouncilReviewer / FinalJudge all distinct (§19).

## 27. STATE OWNERSHIP

AI-OS runtime state (`StateManager`/`StorageManager`) = authoritative. Notion/Obsidian/Graphify = organizational mirrors only; **not** sources of truth (per C4 and §2). No dual source-of-truth.

## 28. DECISION AUTHORITY

Final PASS/FAIL/decision = `HermesKernel` + Verification + `FinalJudgeAgency`. External = none.

## 29. FAILURE HANDLING

External worker fails → AI-OS records evidence gap, retries per `retry.py`, escalates to RCA. No external self-approval.

## 30. SIMPLIFICATION / COMPLEXITY-CONTROL MATRIX

Triggers (§16) → `SimplificationGate` → if unnecessary complexity found → refactor proposal → retest. Necessary complexity preserved.

---

## 31. ACCEPTANCE CRITERIA (brief §29 — all 24)

1. AI-OS governs. 2. One `CouncilManager`. 3. LLM Council techniques integrated (not imported). 4. Contrarian/Outsider integrated w/o duplicate governance. 5. `hermes-agent`(EXT) = exec substrate. 6. FreeLLMAPI = model infra. 7. Notion = planning. 8. Obsidian = PKM. 9. Graphify = graph/org. 10. GSD = method. 11. `UserSimulationAgent` first-class. 12. Real browser execution behind boundary. 13. Structured machine-checkable evidence. 14. Builder≠tester. 15. Builder≠judge. 16. External no final authority. 17. Failures via RCA→Learning→Replan→Re-execute. 18. Self-prompting bounded. 19. Self-looping bounded. 20. Simplification in architecture. 21. No blind imports. 22. No duplicate kernel/orchestrator/council/memory. 23. Every new component justified. 24. Simpler than sum of repos.

## 32. REJECTION DECISIONS

Rejected as core/permanent: Ruflo kernel, KKC/evisoft subsystems (techniques only), second `CouncilManager`, native AI-OS browser, in-house browser farm, vendored persona repos, parallel failure loop, Notion-as-state (C4).

## 33. MUST / MUST-NOT

**MUST:** TestingEvidence; TestOrchestratorService(extend WF); UserSimulationAgent; critique(); LLMCouncil façade; SelfPromptingService(bounded); SimplificationGate; real 9-agency; isolation; Testing≠LLM council; independence; learning extraction; closed-loop retest; 12/12 gates; seeded-defect acceptance.
**MUST NOT:** second kernel/council/verification/loop; import Ruflo/KKC/evisoft; native browser; let `hermes-agent`(EXT) decide; Notion/Obsidian/Graphify/GSD/FreeLLMAPI governance; builder self-judge; duplicate WorkflowManager/verification; blindly install 230+ personas; V1 core change during reconciliation.

---

## 34. CONTRADICTIONS / OPEN ISSUES (carried + resolved)

- **C1 (BLOCKING):** "Hermes" = AI-OS kernel name (`HermesKernel`) AND external browser repo. INV-009 self-contradictory. **Fix:** external = `hermes-agent`(EXT); core = `HermesKernel`/AI-OS Kernel; rewrite INV-009. Vocabulary/doc only.
- **C2:** gate count 11-layer vs 12-gate. **Resolved:** 12/12 (this brief §1). Align decision-record §2 wording.
- **C3:** brief implies 5-state lifecycle; actual `LifecycleState` = **8** members (`lifecycle_manager.py:106-118`). **Fix:** state 8-state canonical.
- **C4:** **Notion ABSENT** in repo; brief makes it permanent plane. **Fix:** adopt-and-integrate (add Notion MCP) OR formally drop from V2 plane.
- **C5 (resolved this brief):** Council taxonomy clarified — two *mechanisms* (LLM synthesis + Contrarian/Outsider dissent) over one `CouncilManager`, two *domains* (reasoning vs testing). Earlier "Testing Council façade" downgraded to a domain/session.

## 35. RISKS

| ID | Risk | Sev | Mitigation |
|---|---|---|---|
| R1 | "802 passing" = collection, not execution-verified | High | Fresh `pytest` run pre-M7 |
| R2=C1 | Hermes naming collision | High/BLOCK | Vocabulary edict + INV-009 |
| R3 | No isolation infra | Med | M7-E worktree/container |
| R4=C4 | Notion absent | Med | Adopt-or-drop |
| R5 | ACP only in external `hermes-agent`; AI-OS needs adapter | Med | M5 bridge |
| R6 | `hermes-agent`(EXT) gitignored/untracked | Med | Pin version; provenance |
| R7 | LearningService logs only | Low | M7 learning integration |

## 36. MIGRATION / ROLLBACK STRATEGY

Each M7 increment revertible: new modules additive (`git revert` per file); `critique()` behind flag → falls back to `decide()`; agency realization feature-flagged → reverts to simulated stub; MCP/ACP configs additive JSON; closed loop (M3) untouched; `hermes-agent`(EXT) external/untracked → removal doesn't affect `HermesKernel`.

## 37. SIMPLICITY AUDIT (per §20/§31)

Every new component passed: no existing component/integration/adapter can do it; capability required; complexity justified. No unnecessary component proposed. Architecture simpler than sum of considered repos (acceptance #24).

---

## 38. FINAL RECOMMENDATION

**Adopt M4→M5→M6→M7.** Intensify the verified scaffold; adopt (not import) council techniques; integrate `hermes-agent`(EXT)/Playwright/SkillSpecTor/FreeLLMAPI behind MCP/ACP; add only the 7 justified permanent components; enforce independence; run the reused M3 loop bounded. **Verdict: READY WITH CONDITIONS.**

**Conditions (close before M7 code — vocabulary/doc/edict, no production code):**
1. **C1 (BLOCKING):** rename external → `hermes-agent`(EXT); rewrite INV-009.
2. **C2:** align gate wording to 12/12.
3. **C3:** state 8-state `LifecycleState` canonical.
4. **C4:** adopt-or-drop Notion.
5. (C5 already resolved in this record.)
6. **R1:** fresh `pytest` run → confirm 802/802 green.

**Implementation order for Terminal 2:**
Pre-M7 conditions (Terminal 1 closes) → M4 → M5 → M6 → M7 (A→J). See §24/§25.

*End of V2 Architecture Decision Record. READ-ONLY; no production code modified; no repositories installed.*
