# AI-OS V2 — FINAL ARCHITECTURE RECONCILIATION & IMPLEMENTATION PLAN

**Terminal 1 — Architecture / Planning / Reconciliation (READ-ONLY)**
**Date:** 2026-08-23
**Mode:** Planning only. No production code modified. No repositories installed. No implementation performed.
**Precedent:** Builds on `TERMINAL_1_V2_FREEZE_RECONCILIATION_REPORT.md` (same date). That report's conditions C1–C4 are carried forward and resolved here.

**Evidence labels (per §30):**
`[EXISTING]` = present & working in `src/` · `[PARTIAL]` = scaffolded but simulated/incomplete · `[PLANNED]` = to be built in M7 · `[OPTIONAL]` · `[REFERENCE]` · `[CONTRADICTION]`.

---

# 1. EXECUTIVE DECISION

**Adopt M4 → M5 → M6 → M7.** V2 is an **intensification + realization + connection** of the verified V1 scaffold — *not* a rebuild. The architecture is **frozen** with the single AI-OS `HermesKernel` as sole authority, a single `CouncilManager` substrate serving **two distinct councils** (LLM Council for reasoning, Testing Council for verification), and a bounded self-loop reusing the M3 RCA→Learning→Replan→Re-execute→Retest loop.

**New permanent components (justified per §31 — no existing component can do them):**
1. `TestingEvidence` schema (typed, provenanced) — replaces loose `dict` evidence.
2. `TestOrchestratorService` — **extends** `WorkflowManager`, does not duplicate it.
3. `UserSimulationAgent` — the one genuinely missing testing perspective.
4. `CouncilManager.critique()` — new stage on existing `CouncilManager`.
5. `LLMCouncil` façade — roles (Analyst/Contrarian/Outsider/Skeptic/Specialist/Simplifier) over existing `CouncilManager`.
6. `SelfPromptingService` — bounded self-questioning over existing council infra.
7. `SimplificationGate` — pre-acceptance complexity control.

**Verdict: READY WITH CONDITIONS (carried from freeze report).** Conditions C1–C4 below are **blocking for M7 start**; none require code change to resolve — only vocabulary edicts + doc patches.

---

# 2. V1 BASELINE (authoritative, must remain)

| Component | Evidence | State |
|---|---|---|
| `HermesKernel` (core authority) | `kernel.py:142`, `constants.py:9` | `[EXISTING]` |
| 9 Core Managers (State/Storage/Workflow/Resource/Health/Security/Capability/Observability/Lifecycle) | `kernel.py:473-583` | `[EXISTING]` |
| `CouncilManager` (convene/propose/vote/decide/dissent + 5 algos) | `council_manager.py` | `[EXISTING]` |
| `AIAgencyService` + 9 `AgencyType` roles | `ai_agency.py:37-48, 561-569` | `[PARTIAL]` — simulated |
| `TestingService` scaffold | `services/` | `[PARTIAL]` |
| `LearningService` (RCA→capture wired) | `services/learning.py:33`, `root_cause.py:370-404` | `[PARTIAL]` — log capture, not yet lesson-extraction |
| `WorkflowManager` (register/execute handlers) | `workflow.py:224,477,711` | `[EXISTING]` |
| `ModelRouter` (provider registry + route) | `model_router.py:89,207,236` | `[EXISTING]` |
| `SecurityManager`, `RCA` (`root_cause.py`) | core | `[EXISTING]` |
| 121 `EventType`s, EventBus | `events/core/types.py` | `[EXISTING]` |
| 802/802 collected tests; **12/12 gates** | `pytest --collect-only`=802; `Part15/TERMINAL_3_FINAL_V1_RELEASE_QA.md:182` | `[EXISTING]` (collection-confirmed; execution run recommended pre-M7) |
| `MCPManager` (generic, unfilled) | `core/mcp_manager.py` | `[PARTIAL]` — manager present, no servers wired |

---

# 3. V2 DELTA (exactly what changes)

| Capability | V1 state | V2 action |
|---|---|---|
| Agency execution | simulated heuristics | realize via adapters/MCP/ACP workers |
| `TestingEvidence` | loose `dict` | add typed schema (`#11`, `#20`) |
| `TestOrchestratorService` | absent | **extend** `WorkflowManager` (`#12`) |
| `UserSimulationAgent` | absent | new perspective on `hermes-agent`(EXT) browser |
| `CouncilManager.critique()` | absent | new stage (`#10`) |
| LLM Council | absent | façade over `CouncilManager` (`#7`) |
| Testing Council | implicit | explicit over `CouncilManager` (`#10`) |
| Self-Prompting | absent | bounded service (`#11`) |
| Learning Layer | log capture | add lesson-extraction + feedback (`#13`) |
| Simplification Gate | absent | pre-acceptance control (`#14`) |
| Isolation/sandbox | none | per-test env separation (`#18`) |
| External MCP/ACP | none wired | integrate per boundary (`#16`,`#18`) |
| Knowledge plane (Notion) | **absent** | C4: decide adopt-or-drop |

**Components deliberately NOT added:** second kernel, second council framework, second verification authority, second loop, native AI-OS browser, in-house browser farm, vendor KKC/EVC code.

---

# 4. FINAL ARCHITECTURE

One `HermesKernel` (CORE) owns governance, councils, verification, workflow, learning, RCA, replanning, final decisions. Around it:

- **Reasoning plane:** `LLMCouncil` (diverse cognitive roles) → feeds planning/self-prompting/design.
- **Execution plane:** Builder (implements target) → produces artifact/app = TARGET UNDER TEST.
- **Testing plane:** `TestOrchestratorService` (extends `WorkflowManager`) plans & dispatches 9 agencies + `UserSimulationAgent` → `hermes-agent`(EXT)/Playwright/MCP workers execute → `TestingEvidence`.
- **Synthesis plane:** Testing Council (`CouncilManager.critique()`) → `FinalJudgeAgency` → AI-OS Verification.
- **Control plane:** PASS→COMPLETE; FAIL→RCA→Learning→Replan→Re-execute→Retest (bounded).
- **Knowledge plane:** Obsidian (durable PKM) / Graphify (graph context) / Notion (planning) / GSD (methodology) — organizational only, never governance.
- **Infra plane:** FreeLLMAPI via `ModelRouter`; MCP/ACP servers; `hermes-agent`(EXT) workers.

---

# 5. FINAL ARCHITECTURE DIAGRAM (canonical end-to-end)

```
╔════════════════════════════════════════════════════════════════════════════╗
║                  AI-OS HermesKernel  [CORE — SOLE AUTHORITY]                ║
║  EventBus · 9 Core Managers · SecurityManager · WorkflowManager ·          ║
║  CouncilManager(conv/propose/vote/decide/dissent/critique) · Verification  ║
╠════════════════════════════════════════════════════════════════════════════╣
║  LLM COUNCIL (façade)          │   TESTING COUNCIL (façade)                ║
║   Analyst/Contrarian/          │   9 Agencies + UserSimulationAgent        ║
║   Outsider/Skeptic/            │   → critique() → synthesize →             ║
║   Specialist/Simplifier        │   FinalJudgeAgency → Verification         ║
║   (reasoning/design)           │   (verification)                          ║
╠════════════════════════════════════════════════════════════════════════════╣
║  SelfPromptingService → LLMCouncil (bounded, traceable)                    ║
║  LearningService ← RCA (experience→evidence→lesson→knowledge)              ║
║  SimplificationGate → pre-acceptance complexity control → retest           ║
╠════════════════════════════════════════════════════════════════════════════╣
║  TestOrchestratorService (EXTENDS WorkflowManager)                         ║
║    plan → dispatch(parallel) → collect → normalize → submit                ║
║        ├─ 9 Agencies → adapters/MCP/ACP → TestingEvidence                  ║
║        └─ UserSimulationAgent → hermes-agent(EXT) browser (ACP)            ║
╠════════════════════════════════════════════════════════════════════════════╣
║  MCP/ACP BOUNDARY → hermes-agent(EXT) · Playwright · SkillSpecTor ·        ║
║   Graphify · FreeLLMAPI · agency-agents · Vercel Skills · Agent-Reach     ║
╠════════════════════════════════════════════════════════════════════════════╣
║  KNOWLEDGE: Obsidian(PKM) · Graphify(graph) · Notion(planning) · GSD(method)║
╚════════════════════════════════════════════════════════════════════════════╝
        FAIL ↘ RCA → Learning → Replan → Re-execute → Retest (bounded loop)
```

---

# 6. LAYER MODEL

| Layer | Responsibility | Owner |
|---|---|---|
| Core/Governance | kernel, security, config, lifecycle | `HermesKernel` `[EXISTING]` |
| Council Substrate | convene/propose/vote/decide/dissent/critique | `CouncilManager` `[EXISTING]`+`[PLANNED]` |
| Reasoning | LLM Council roles, self-prompting | `LLMCouncil`/`SelfPromptingService` `[PLANNED]` |
| Execution | builder, workflow, capability, model routing | `WorkflowManager`/`ModelRouter` `[EXISTING]` |
| Testing | orchestration, 9 agencies, user sim | `TestOrchestratorService`/`AIAgencyService`/`UserSimulationAgent` |
| Verification | 12-gate authority, final PASS/FAIL | AI-OS Verification `[EXISTING assert]` |
| Learning | lesson extraction, feedback | `LearningService` `[PARTIAL]` |
| Knowledge | Obsidian/Graphify/Notion/GSD | external `[PARTIAL]` |
| Infra | model access, MCP/ACP, workers | `ModelRouter`/`MCPManager`/`hermes-agent`(EXT) |

---

# 7. LLM COUNCIL

**Distinct from Testing Council (brief §3, acceptance #3).** Façade over `CouncilManager` (no second framework). Members are `CouncilMember` with `expertise` tags:

| Role | Prompt mandate |
|---|---|
| Analyst / Primary | "Strongest conventional solution?" |
| Contrarian | "Why might this be wrong?" |
| Outsider | "What would someone without our assumptions see?" |
| Skeptic / Critic | "Which claims lack evidence?" |
| Specialist | "What does the technical domain imply?" |
| Simplifier | "Same outcome with less complexity?" |

**Flow:** `convene` → independent `propose` (each role, blind) → `critique()` (anonymized cross-ranking + relabel-then-review, techniques from KKC/EVC) → `dissent()` preserved → `decide()` → synthesis. Output feeds planning/self-prompting. **Does NOT replace verification or Testing Council.** `[PLANNED]`

---

# 8. TESTING SYSTEM (9 + 1 perspectives)

| # | Perspective | Owner `[EXISTING]` | Realization `[PLANNED]` |
|---|---|---|---|
| 1 | Security | `SecurityAgency` | `hermes-agent`(EXT) + SkillSpecTor gate + agency-agents pentester |
| 2 | Performance | `PerformanceAgency` | benchmark worker / local harness |
| 3 | Chaos/Reliability | `ChaosAgency` | root_cause/retry surface + fault injection |
| 4 | Accessibility | `AccessibilityAgency` | `hermes-agent`(EXT) browser + axe |
| 5 | Documentation | `DocumentationAgency` | static + LLM review |
| 6 | Concurrency | `ConcurrencyAgency` | static + dynamic analysis |
| 7 | BugHunter | `BugHunterAgency` | fuzz generation |
| 8 | Architecture | `ArchitectureAgency` | Graphify evidence + review |
| 9 | FinalJudge | `FinalJudgeAgency` | deterministic verdict into verification |
| 10 | User Simulation | **`UserSimulationAgent`** `[PLANNED]` | `hermes-agent`(EXT) cloud browser (ACP) |

Agencies remain canonical tester roles; do **not** add permanent agencies beyond UserSimulationAgent (acceptance #24).

---

# 9. USER SIMULATION

`UserSimulationAgent` `[PLANNED]` — first-class perspective, **not** BugHunter/a11y/dev.
- **Receives:** app purpose, user goal, user-level context. **NOT** source code as primary basis.
- **Behavior:** discovery-first; expected/confused/incorrect actions; back/forward; refresh; empty/invalid submission; boundary; interrupted; recovery.
- **Evaluates:** goal_completion_pct, workflow_success, usability_blockers, confusing_states, navigation_failures, missing_feedback, invalid_input_results, recovery_behavior, expected_vs_observed.
- **Executes on:** `hermes-agent`(EXT) isolated ACP browser session. **Hermes executes; AI-OS decides.** (C1 vocabulary: `hermes-agent`(EXT) ≠ `HermesKernel`.)

**Evidence model** (`UserSimulationCompleted` extends `TestingEvidence`):
`{user_goal, exploration_strategy, goal_completion_pct, workflow_success, actions[], observations[], unexpected_errors[], usability_blockers[], navigation_failures[], confusing_states[], missing_feedback[], invalid_input_results[], recovery_behavior, expected_vs_observed, proof[](screenshots/DOM/traces/session_id), provenance, hermes_session_id}`

---

# 10. TESTING COUNCIL

**Differs from LLM Council:** consumes structured `TestingEvidence` from test perspectives; produces a *verification decision*, not a reasoning synthesis. Same `CouncilManager` substrate, separate `convene` topic + membership (builder excluded).
**Flow:** independent proposals → `critique()` → blind cross-ranking → disagreement capture → synthesis → final testing decision → `FinalJudgeAgency` → AI-OS Verification. `[PLANNED]` (infra `[EXISTING]`).

---

# 11. SELF-PROMPTING

`SelfPromptingService` `[PLANNED]` — bounded, traceable, objective-linked.
- Seed questions: "What assumption am I making?" / "What could fail?" / "What evidence would prove this?" / "What would the Contrarian argue?" / "Can this be simplified?" / "What requirement have we not tested?"
- **Bounds:** max-depth, token budget, must cite objective, no open recursion. Routes into `LLMCouncil`.
- Reuses `CouncilManager`; no new council.

---

# 12. SELF-LOOP (continuous improvement)

Reuses **M3 closed loop** `[EXISTING]` — do NOT create a competing loop (acceptance #26, anti-Frankenstein §23).
`FAIL → RCA(root_cause.py) → Learning(learning.py) → Replan(planning) → Self-Prompt → Re-execute(WorkflowManager) → Retest`.
**Bounded:** iteration limit, budget, convergence criterion, no-improvement detection, regression protection, human escalation. Never loops forever.

---

# 13. LEARNING LAYER

`LearningService` `[PARTIAL]` — already captures from RCA (`root_cause.py:382-404`). **V2 adds:** lesson extraction (categorize failure→fix), validation, knowledge update, feedback into future planning/self-prompting. Progressive mistake-avoidance.
Inputs: failures, RCA, successful/unsuccessful fixes, test evidence, council disagreements, decisions, traces, simplification decisions, user-sim findings.

---

# 14. SIMPLIFICATION LAYER

`SimplificationGate` `[PLANNED]` — pre-acceptance, **before** final verification; changes it introduces are **retested** (acceptance #19,#20).
Simplifier asks: reuse? duplicate service? justified abstraction? unnecessary dependency? consolidatable? excessive config? needless control flow? hypothetical future-proofing? existing-infra path? future-dev understandability? maintenance burden?
**Valid only if it preserves** correctness, security, isolation, testability, performance, explicit requirements, maintainability. SIMPLE ≠ fewer lines.

---

# 15. PLANNING / KNOWLEDGE

- **Notion** `[PARTIAL→C4]`: planning/tracking/status. **Currently ABSENT in repo** — C4: adopt-and-integrate or formally drop from V2 plane. Not decision authority.
- **Obsidian** `[PARTIAL]`: durable PKM; label only in `memory.py:40`. Not kernel.
- **Graphify** `[PARTIAL]`: graph/context; label only in `memory.py:41`. Integration layer, not authority.
- **GSD Core** `[REFERENCE]`: methodology; never kernel/runtime.

All four are organizational; do not collapse; none govern.

---

# 16. EXTERNAL INTEGRATIONS

| Resource | Class | In-repo | Role |
|---|---|---|---|
| `hermes-agent`(EXT) | INTEGRATION | `[DISK]`, gitignored `dc09784` | browser/workers/ACP exec substrate |
| agency-agents | SKILL/PERSONA | `[REFERENCE]` | curated tester personas (~8-10) |
| SkillSpecTor | INTEGRATION (gate) | `[REFERENCE]` | security/adversarial gate |
| Agent-Reach | INTEGRATION | `[REFERENCE]` | web/social ingest |
| Vercel Skills | INTEGRATION (spec) | `[REFERENCE]` | SKILL.md packaging |
| Playwright MCP | INTEGRATION | `[REFERENCE]` | deterministic browser test |
| Trail of Bits Skills | INTEGRATION/SEC | `[REFERENCE]` | security skills |
| Codebase Memory MCP | INTEGRATION CANDIDATE | `[REFERENCE]` | investigate before adopt |
| FreeLLMAPI | INTEGRATION | `[REFERENCE]` | model/provider abstraction via `ModelRouter` `[EXISTING]` |
| Ruflo / Loop Eng / Prompt Hub / Book-to-Skill / Superpowers / ECC | REFERENCE | — | technique only |
| Caveman | OPTIONAL | — | compression if required |
| KKC / evisoft | TECHNIQUE ONLY | — | critique techniques, not subsystems |
| ego-lite | REFERENCE/OPT | — | not core without evidence |
| Free Claude Code | OPTIONAL | — | dev tooling |

---

# 17. REPOSITORY CLASSIFICATION

(See §16 + §21 of freeze report's merged table — authoritative. Net: 1 CORE (AI-OS), ~9 INTEGRATION, 4 KNOWLEDGE/PLAN, 1 METHODOLOGY, several REFERENCE/OPTIONAL/TECHNIQUE.)

---

# 18. MCP / ACP BOUNDARY

`MCPManager` `[PARTIAL]` present but no servers wired (`config/mcp/test_mcp.json` only). **V2 wires:** `hermes-agent`(EXT) (ACP preferred for worker sessions + provenance; MCP fallback), Playwright MCP, SkillSpecTor MCP, Graphify MCP, FreeLLMAPI MCP, agency-agents/Vercel via SKILL adapter. All external outputs treated as **external observations** until normalized+verified by AI-OS. No kernel change; adapters only.

---

# 19. INDEPENDENCE / TRUST MODEL

Builder ≠ Test Generator ≠ Test Executor ≠ User Simulator ≠ Judge.
- Builder artifact = input-only to testers.
- `hermes-agent`(EXT) returns observations, **no verdicts**; ACP session isolated + provenanced.
- Perspective↔perspective: anonymous during critique; one vote each.
- Testing Council membership **excludes builder**; `FinalJudgeAgency` independent of builder.
- AI-OS Verification = final control authority. (acceptance #18)

---

# 20. EVIDENCE ARCHITECTURE

`TestingEvidence` `[PLANNED]` (typed, replace loose `dict`):
`{evidence_id, test_run_id, perspective, target, action[], observation[], severity, confidence, proof[](screenshot/DOM/log/trace/output/session_id), provenance(source/worker/session/ts/env), expected, observed, verdict_contribution}`.
User-sim extension adds §9 fields. Machine-checkable where possible. `provenance` mandatory (INV-007).

---

# 21. CLOSED LOOP

`FAIL → RCA(root_cause.py) → Learning(learning.py) → Replan → Self-Prompt → Re-execute(WorkflowManager) → Retest → (PASS→COMPLETE | FAIL→loop, bounded)`.

---

# 22. MILESTONE PLAN (verified against existing docs)

| Milestone | Scope | State |
|---|---|---|
| **M4** | Skill standard + security gate (SKILL.md adapter, SkillSpecTor gate) | `[PLANNED]` (prereq) |
| **M5** | Integration backbone (MCP/ACP bridge to `hermes-agent`(EXT), FreeLLMAPI via `ModelRouter`) | `[PLANNED]` |
| **M6** | Council synthesis technique (`critique()` + LLM Council façade + self-prompting) | `[PLANNED]` |
| **M7** | **Testing intensification:** real 9-agency execution, `TestOrchestratorService`(extend `WorkflowManager`), `TestingEvidence`, `UserSimulationAgent`+`hermes-agent`(EXT) browser, isolation, Testing Council critique, independent judge, adversarial, simplification gate, learning integration, closed-loop retest, seeded-defect acceptance | `[PLANNED]` |

M4→M5→M6 are prerequisites for M7's integration; do not duplicate M7 work into them.

---

# 23. DEPENDENCY GRAPH

```
M4 (skill/gate) ─┐
                 ├─► M5 (MCP/ACP bridge, FreeLLMAPI) ─┐
M6a critique() ──┘                                    ├─► M7
M6b LLMCouncil ───────────────────────────────────────┤
M6c SelfPrompting ────────────────────────────────────┤
existing WorkflowManager/ModelRouter/LearningService ──┘
```
M7 internal order: M7-A evidence → M7-B orchestrator(extend WF) → M7-C 9-agency → M7-D UserSim+hermes → M7-E isolation → M7-F critique → M7-G judge → M7-H adversarial → M7-I loop → M7-J seeded acceptance.

---

# 24. FILES / COMPONENTS TO CREATE `[PLANNED]`

- `src/aios/core/testing_evidence.py` — `TestingEvidence` + `UserSimulationCompleted` dataclasses.
- `src/aios/services/test_orchestrator.py` — `TestOrchestratorService` (extends `WorkflowManager`).
- `src/aios/core/user_simulation.py` — `UserSimulationAgent`.
- `src/aios/core/llm_council.py` — `LLMCouncil` façade over `CouncilManager`.
- `src/aios/services/self_prompting.py` — `SelfPromptingService`.
- `src/aios/core/simplification.py` — `SimplificationGate`.
- `src/aios/core/council_manager.py` — **add** `critique()` stage (modify existing).
- `config/mcp/*.json` — server configs (hermes/playwright/skillspec/graphify/freellmapi).
- Tests: `tests/integration/test_closed_loop.py` (exists), `tests/integration/test_kernel_lifecycle_e2e.py` (exists), new `tests/integration/test_user_simulation.py`, `test_testing_council.py`, `test_self_prompting.py`, `test_simplification.py`.

---

# 25. FILES / COMPONENTS TO MODIFY

- `council_manager.py` — add `critique()`.
- `ai_agency.py` — replace simulated `review()` bodies with adapter/MCP dispatch (keep class structure).
- `services/learning.py` — add lesson-extraction + feedback.
- `core/mcp_manager.py` — load real server configs.
- `memory.py` / `services/memory.py` — wire Obsidian/Graphify MCP (optional).
- Docs: `V2_ARCHITECTURE_DECISION_RECORD.md` (INV-009 rewrite, C1), `UPDATED_CAPABILITY_MATRIX.md`, `UPDATED_V2_MILESTONES.md`, `COUNCIL_SYNTHESIS_ARCHITECTURE.md`, `MULTI_PERSPECTIVE_TESTING_ARCHITECTURE.md` (resolve C2/C3/C4).

---

# 26. FILES NOT TO MODIFY (protect V1)

`kernel.py` (core authority), `lifecycle_manager.py` (8-state FSM), `security_manager.py`, `state.py`, `storage.py`, `resource_manager.py`, `health_manager.py`, `observability_manager.py`, `capability_manager.py`, `configuration_manager.py`, `events/*` (121 types), `root_cause.py` (loop logic), `workflow.py` (extend, don't rewrite), `model_router.py` (extend for FreeLLMAPI). **No second kernel/council/verification/loop anywhere.**

---

# 27. MUST IMPLEMENT

TestingEvidence; TestOrchestratorService(extend WF); UserSimulationAgent; critique(); LLMCouncil façade; SelfPromptingService(bounded); SimplificationGate; real 9-agency execution; isolation; Testing Council≠LLM Council; independence enforcement; learning lesson-extraction; closed-loop retest; 12/12 gates preserved; seeded-defect acceptance (9 defects).

# 28. SHOULD IMPLEMENT

FreeLLMAPI via ModelRouter; Graphify/Obsidian MCP wiring; SkillSpecTor gate; Playwright MCP; agency-agents curated personas; GSD methodology hook.

# 29. OPTIONAL

Caveman compression; Codebase Memory MCP; Free Claude Code launcher; ego-lite; Agent-Reach; MOA synthesis (hermes-agent technique).

# 30. REFERENCE ONLY

Ruflo; Loop Engineering; Prompt Hub; Book-to-Skill; Superpowers; ECC; KKC/evisoft (techniques only); Agentic R&D; Code Virtuoso; Instagram ref.

# 31. MUST NOT IMPLEMENT

Second kernel; second CouncilManager; import Ruflo/KKC/evisoft subsystems; native AI-OS browser; in-house browser farm; vendor unlicensed persona repos; let `hermes-agent`(EXT) decide; make Notion/Obsidian/Graphify/GSD/FreeLLMAPI governance; builder judges own work; duplicate WorkflowManager/verification; parallel failure loop; blindly install all 230+ personas; any V1 core change during reconciliation.

---

# 32. ACCEPTANCE TESTS (prove each V2 capability)

1. ≥9 independent perspectives run vs target (builder excluded).
2. UserSimulation completes known workflow in browser + reports structured UX evidence incl. 1 seeded defect.
3. Perspectives emit typed `TestingEvidence` (severity/proof/provenance/confidence).
4. `critique()` applies anonymized cross-ranking + dissenter-override.
5. `FinalJudgeAgency` emits deterministic verdict → verification.
6. FAIL routes into existing RCA→Learning→Replan→Re-execute→Retest (no parallel loop).
7. **All 12 V1 gates remain green; 802 tests pass** (fresh `pytest` run required — see R1).
8. No second kernel/council/verification.
9. LLM Council + Testing Council provably distinct (separate topics/membership).
10. Contrarian/Outsider/Simplifier roles explicitly present & preserved in dissent.
11. Self-Prompting bounded (depth/budget enforced, traceable).
12. Simplification gate runs pre-acceptance; its changes retested.
13. Seeded-defect loop: detect→evidence→council→judge→fail→RCA→learn→replan→re-execute→retest→pass only after real fix.
14. LearningService converts a failure into a reusable lesson (regression test).

---

# 33. RISK REGISTER

| ID | Risk | Sev | Mitigation |
|---|---|---|---|
| R1 | "802 passing" = collection-confirmed, not execution-verified | High | Fresh `pytest` run before M7 sign-off |
| R2 | **C1 Hermes naming collision** (kernel vs external) | High/BLOCK | Vocabulary edict + INV-009 rewrite (Condition 1) |
| R3 | No isolation infra (BUILDER≠TESTER env) | Med | Add per-test worktree/container in M7-E |
| R4 | C4 Notion absent | Med | Decide adopt-or-drop before M7 |
| R5 | ACP only in external `hermes-agent`; AI-OS side needs adapter | Med | M5 builds MCP/ACP bridge |
| R6 | `hermes-agent`(EXT) gitignored/untracked | Med | Pin to a vendored/referenced version; provenance |
| R7 | LearningService only logs, no lesson-extraction yet | Low | M7 learning integration |
| C2 | Gate count 11 vs 12 inconsistency | Low | Align docs to 12/12 (Condition 2) |
| C3 | Lifecycle 5-state vs 8-state narrative | Low | State 8-state canonical (Condition 3) |

---

# 34. ROLLBACK STRATEGY

Each M7 increment is independently revertible:
- New modules (`testing_evidence.py`, `test_orchestrator.py`, `user_simulation.py`, `llm_council.py`, `self_prompting.py`, `simplification.py`) are additive → `git revert` per file.
- `critique()` added to `council_manager.py` behind a flag; disabled → falls back to `decide()`.
- Agency `review()` realization wrapped so a failing adapter reverts to simulated stub (feature-flag).
- External MCP/ACP configs are additive JSON; removing a server = remove config, no core change.
- Closed loop untouched (M3) → no behavioral regression to V1.
- `hermes-agent`(EXT) is external/untracked → removing integration does not affect `HermesKernel`.

---

# 35. FINAL COMPLEXITY AUDIT (per §31 — necessity proof)

| Proposed component | Existing can do it? | Integration can? | Adapter can? | Required? | Justified? |
|---|---|---|---|---|---|
| TestingEvidence | no (loose dict) | no | no | YES | replaces ambiguity |
| TestOrchestratorService | WorkflowManager partial | no | no | YES (extend WF) | avoids dup |
| UserSimulationAgent | no (no UX perspective) | no | no | YES | missing perspective |
| critique() | no stage exists | no | no | YES | synthesis need |
| LLMCouncil | CouncilManager partial | no | no | YES (façade) | distinct council |
| SelfPromptingService | no | no | no | YES (bounded) | required mechanism |
| SimplificationGate | no | no | no | YES | acceptance #19 |
| Second kernel/council | — | — | — | NO | anti-Frankenstein |

**Conclusion:** every new permanent component passed the §31 5-test; no unnecessary component proposed.

---

# 36. FINAL IMPLEMENTATION ORDER (handoff to Terminal 2)

**Pre-M7 (conditions — Terminal 1 closes, no code):**
1. Resolve C1: rename external → `hermes-agent`(EXT); rewrite INV-009; doc patch.
2. Resolve C2: align gate count to 12/12 across docs.
3. Resolve C3: state 8-state `LifecycleState` canonical.
4. Resolve C4: adopt-or-drop Notion.
5. Fresh `pytest` run → confirm 802/802 green (closes R1).

**M4:** SKILL.md adapter + SkillSpecTor security gate.
**M5:** MCP/ACP bridge (`hermes-agent`(EXT), Playwright, Graphify, FreeLLMAPI via `ModelRouter`); AI-OS-side ACP adapter.
**M6:** `critique()` on `CouncilManager`; `LLMCouncil` façade; `SelfPromptingService`.
**M7 (internal order):**
- M7-A: `TestingEvidence` + `UserSimulationCompleted` schema.
- M7-B: `TestOrchestratorService` extending `WorkflowManager`.
- M7-C: realize 9 agencies via adapters/MCP/ACP (simulated→real).
- M7-D: `UserSimulationAgent` + `hermes-agent`(EXT) ACP browser.
- M7-E: isolation/sandbox (per-test env, builder≠tester).
- M7-F: Testing Council `critique()` synthesis.
- M7-G: independent `FinalJudgeAgency` verdict.
- M7-H: adversarial/security realization (SkillSpecTor gate).
- M7-I: closed-loop integration (RCA→Learning→Replan→Re-execute→Retest).
- M7-J: `SimplificationGate` pre-acceptance + seeded-defect acceptance (9 defects), full retest, 12/12 gates.

**FINAL VERDICT: READY WITH CONDITIONS** — M7 implementation MUST NOT begin until Conditions 1–4 (C1–C4) are closed and the fresh `pytest` run confirms green. None require production-code change to decide; they are vocabulary/doc/edict actions owned by Terminal 1.

---

*End of Terminal 1 V2 Implementation Plan. Read-only; no production code modified; no repositories installed.*
