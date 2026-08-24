# UPDATED AI-OS V1 → V2 GAP ANALYSIS (TESTING EXTENSION)

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Adds the multi-perspective testing + adversarial QA + User Simulation + Council-synthesis gap to `FULL_AI_OS_V1_V2_GAP_ANALYSIS.md`.

> V1 baseline treated as AUTHORITATIVE (M0–M3 ✅, 802/802 tests, 12/12 gates). `[AI-OS SOURCE]`
> Priority: **P0** blocker · **P1** high · **P2** medium · **P3** low · **Future** defer.

---

## 1. HEADLINE: THE BIGGEST GAP IS "SIMULATED, NOT REAL"

The single most important V1→V2 gap for testing is **not missing architecture — it is missing execution**. AI-OS V1 *has* the 9-agency `AIAgencyService`, `TestingService`, `CouncilManager`, and the closed loop, but every agency currently runs **heuristic string-matching placeholders** (`if "sql" in target: finding=sql_injection_risk`). The `TestingService` is a deterministic smoke-test stub.

So the V2 testing work is dominated by **intensification of an existing scaffold**, not greenfield construction. This drastically lowers risk and Frankenstein exposure.

---

## 2. NEW GAP TABLE (TESTING)

| Capability | V1 State | V2 Requires | External Available | Gap | Priority | Evidence |
|---|---|---|---|---|---|---|
| Real multi-perspective testers | 9 agencies **simulated** (string heuristics) | Real execution per perspective | agency-agents personas (INTEGRATION), Hermes workers (INTEGRATION) | Stubs → real | **P1** | `core/ai_agency.py:161-545` `[AI-OS SOURCE]` |
| User Simulation Agent | Absent (no user-role agent) | Independent user-behavior simulation | Hermes cloud-browser (INTEGRATION) | Missing runtime | **P1** | `hermes-agent/agent/browser_provider.py` `[LOCAL]` |
| Browser testing | Absent | UI navigation/observation | Hermes Browserbase/Use/Firecrawl CDP (INTEGRATION) | Missing runtime | **P1** | `[LOCAL]` |
| Test Orchestration service | `WorkflowManager` exists; no test-orchestrator | Plan→dispatch→collect→synthesize | Hermes/agency-agents orchestrators (REF) | No dedicated orchestrator | **P1** | `core/workflow.py:224` `[AI-OS SOURCE]` |
| Evidence schema (structured) | `AgencyResponse.findings[]` loose dicts | Typed evidence (action/observation/severity/proof) | agency-agents evidence-collector (REF) | Unstructured | **P1** | `core/ai_agency.py:74` `[AI-OS SOURCE]` |
| Council cross-review / disagreement | CouncilVote/dissent exist; no critique stage | Staged blind cross-review + dissenter rule | KKC cross-ranking, EVC relabel-review (TECHNIQUE) | Technique gap | **P1** | WebFetch `[EXTERNAL]` |
| Test environment isolation / sandboxing | Agent quotas only | Per-test isolated env (worktree/container) | Loop Eng worktree (REF), Hermes worktree (REF) | Partial isolation | **P1** | `[AI-OS SOURCE]` `[EXTERNAL]` |
| Independent judge/adjudication | FinalJudgeAgency exists (simulated) | Real judge, isolated from builder | Hermes MOA chair (TECH), KKC chairman (TECH) | Simulated | **P1** | `core/ai_agency.py:507` `[AI-OS SOURCE]` |
| Security/Adversarial testing (real) | SecurityAgency stub | Active pentest + poisoning scan | SkillSpecTor (INTEGRATION), agency-agents pentester (INTEGRATION) | Stub | **P2** | `[EXTERNAL]` |
| Performance testing (real) | PerformanceAgency stub | Load/benchmark execution | agency-agents benchmarker (INTEGRATION) | Stub | **P2** | `[EXTERNAL]` |
| Regression testing automation | 802/802 suite passes; no AI-generated regression | AI-generated regression from changes | agency-agents automation-eng (INTEGRATION) | Manual only | **P2** | `[AI-OS SOURCE]` |
| Data-correctness testing | Absent | Validate outputs/data integrity | (none direct) | Missing | **P2** | `[INFERENCE]` |
| Test reproducibility | No fixture/seed model | Deterministic, replayable tests | (none) | Missing | **P2** | `[INFERENCE]` |
| Accessibility testing (real) | AccessibilityAgency stub | WCAG/axe execution | agency-agents access-auditor (INTEGRATION), Hermes axe | Stub | **P2** | `[EXTERNAL]` |
| Integration testing (AI-driven) | 101 integration tests pass | AI-driven integration probes | Agent-Reach (INTEGRATION) | Manual | **P2** | `[EXTERNAL]` |
| Council synthesis technique (MOA) | CouncilManager 5 algos; no MOA | Multi-model synthesis option | Hermes MOA (TECHNIQUE) | Technique | **P3** | `[LOCAL]` `[AI-OS SOURCE]` |
| Token compression for test payloads | Absent | Compress large evidence payloads | Caveman (OPTIONAL) | Missing | **P3** | `[EXTERNAL]` |

---

## 3. PRIORITY RATIONALE (TESTING)

### P0 — Blockers (none architectural; one governance)
- **No P0 architecture blocker.** The verified V1 kernel, councils, verification, and closed loop are sufficient to host the testing layer. The only true "blocker" is governance: **the independence rule (PART 13) must be designed before any tester is built**, else AI-OS will test its own implementations (self-approval trap). This is a design constraint, not a missing component.

### P1 — High (build first)
1. **Realize the 9 agencies** (replace heuristics with subagent/Hermes-driven execution).
2. **User Simulation Agent** backed by Hermes cloud-browser.
3. **Test Orchestration** (extend `WorkflowManager` or add a `TestOrchestratorService`).
4. **Structured Evidence schema** (`TestingEvidence` dataclass: perspective, target, actions[], observations[], severity, proof[]).
5. **Council critique stage** adopting KKC/EVC techniques (anonymized cross-ranking + dissenter-override).
6. **Test-environment isolation** (worktree/container per test run).

### P2 — Medium
7. Security/Adversarial real execution (SkillSpecTor gate + pentester worker).
8. Performance/Accessibility real execution.
9. AI-generated regression suites.
10. Data-correctness + reproducibility.

### P3 — Low / Optional
11. MOA synthesis technique (off by default).
12. Caveman payload compression (flagged).

### Future / REFERENCE
- Ruflo, Loop Eng, Prompt Hub, Superpowers, Book-to-Skill, ECC, FreeCC, Caveman.

---

## 4. SPECIAL ATTENTION GAPS (PART 10 mandated)

| Concern | Status | Note |
|---|---|---|
| Browser automation | **P1 gap** | Hermes cloud-browser is the only viable substrate; no AI-OS-native browser. |
| User simulation | **P1 gap** | Requires Hermes browser + a distinct user-role agent (not a developer persona). |
| Test environment isolation | **P1 partial** | Agent quotas insufficient; need worktree/container per run (Loop Eng/Hermes ref). |
| Sandboxing | **P1 partial** | Same as above. |
| Security testing | **P2** | SkillSpecTor gate + pentester worker. |
| Evidence capture | **P1** | Loose dicts today; needs typed schema + screenshots/provenance. |
| Independent verification | **P1 (design rule)** | Independence model is the keystone (see ADR). |
| Test reproducibility | **P2 gap** | No fixture/seed model; must be designed. |
| External agent integration | **P1** | Hermes via ACP/MCP; agency-agents via SKILL.md adapter. |
| Council synthesis | **P1 technique** | KKC/EVC techniques into existing `CouncilManager`. |

---

## 5. WHAT V1 ALREADY COVERS (NOT GAPS)

- 9 agency *roles* + `AIAgencyService` ✅ (intensify, don't rebuild)
- `TestingService` + test events ✅ (intensify)
- `CouncilManager` + 5 consensus algos + dissent ✅ (extend with critique stage)
- `FinalJudgeAgency` ✅ (realize)
- Closed-loop failure recovery ✅
- 802/802 regression suite ✅
- SecurityManager ✅ (add SkillSpecTor gate)

---

*End of updated gap analysis. Testing work is mostly intensification of an existing, verified scaffold — low Frankenstein risk.*
