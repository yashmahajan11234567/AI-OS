# USER SIMULATION AGENT — SPECIFICATION

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Specification for the final "User" testing perspective (PART 3 / PART 14). The agent must behave as close to an actual *user* as possible — not a developer or generic QA agent.

> Evidence: Hermes cloud-browser (`hermes-agent/agent/browser_provider.py:50`) is the only viable execution substrate. AI-OS has no native browser. `[LOCAL REPOSITORY]`
> No code changed.

---

## 1. WHY A DEDICATED USER SIMULATION AGENT (not just another QA agent)

Generic QA agents test *against a spec*. A user does not read the spec — they **discover** how the app works by using it, make mistakes, get confused, and judge whether it *accomplishes their goal*. The task explicitly requires this final perspective to:

1. Enter/use the application.
2. Discover usage **without relying entirely on implementation knowledge**.
3. Perform realistic workflows.
4. Try expected user actions.
5. Try confused/incorrect actions.
6. Try edge-case workflows.
7. Observe errors and usability problems.
8. Determine whether the app accomplishes its intended goal.
9. Report the experience **independently**.
10. Feed findings into verification/council.

This is a *behavioral* perspective, orthogonal to functional/security/perf testing. It must be a **first-class, isolated testing perspective** — not folded into BugHunter or Accessibility.

---

## 2. ARCHITECTURE DECISION (PART 3)

**Recommendation: a dedicated `UserSimulationAgent` (new AI-OS agency type) backed by Hermes cloud-browser via ACP.** Combination of: dedicated agent + external browser runtime (Hermes) + curated UX persona (agency-agents `design-ux-researcher`).

| Option | Verdict | Reason |
|---|---|---|
| Dedicated User Simulation Agent (AI-OS) + Hermes browser | ✅ **CHOSEN** | AI-OS owns the persona/evidence; Hermes provides real browser execution via ACP. Independence preserved. |
| Generic AI Agency persona | ❌ | No browser substrate; would be another spec-based QA agent. |
| External agent runtime only (Hermes alone) | ❌ | Hermes would become a decider; violates "AI-OS decides" rule. |
| Browser-capable infra without AI-OS agent | ❌ | Evidence wouldn't be structured/normalized into AI-OS verification. |
| Agent-Reach | ❌ | Web/social *content* ingestion, not interactive browser control. |
| Hermes alone as the user | ❌ | Hermes is a worker, not an AI-OS council member; its findings wouldn't enter CouncilManager natively. |

**Model:** `UserSimulationAgent` (AI-OS) formulates the *user intent + exploration strategy* and emits structured UX evidence. Hermes (external worker, ACP) performs the *physical browser actions* (navigate/click/fill/screenshot/read-DOM) inside an isolated session. The boundary crossing: AI-OS sends `{app_url, user_goal, exploration_brief}` → Hermes returns `{actions[], dom_snapshots[], screenshots[], errors[], observations[]}` with provenance → `UserSimulationAgent` evaluates against the user goal and emits `UserSimulationCompleted` evidence.

---

## 3. USER-SIMULATION AGENT BEHAVIOR SPEC

The agent operates in **user cognitive mode**, not developer mode:

- **No implementation knowledge as primary input.** It may be given the app's *purpose* and *intended user goal* (what a real user would know: "this is a todo app; I want to add and complete tasks"), but NOT the source code or internal API contracts.
- **Discovery-first.** Before acting, it explores: "Where do I start? What are my options on this screen?" — mirroring a first-time user.
- **Realistic workflows.** Completes the intended goal via the UI the way a user would (click visible controls, read labels, follow flows).
- **Confused/incorrect actions.** Deliberately tries: mistyped inputs, wrong buttons, unexpected sequences, refreshing mid-flow, using browser back/forward, submitting empty forms.
- **Edge-case workflows.** Boundary values, very long input, rapid repeated actions, interrupted sessions.
- **Observation.** Records: did the UI give feedback? Was an error clear? Did navigation make sense? Were there dead-ends or confusing states?
- **Goal judgment.** Explicitly answers: *did the app let me accomplish my goal?* — not "does it match the spec?"

---

## 4. ACCEPTANCE MODEL (PART 14) — OBJECTIVE EVIDENCE

The agent must NOT merely assert "the app works." It emits structured, verifiable evidence:

| Evidence dimension | Objective signal |
|---|---|
| Task completion | % of intended goal steps completed unassisted |
| Workflow success | Did the primary workflow reach its end state? (bool + trace) |
| Unexpected errors | Uncaught exceptions, 500s, blank screens, console errors (captured) |
| Usability blockers | Dead-ends, no-path-to-goal, required action undiscoverable |
| Navigation failures | Broken links, lost state on back/refresh, orphan screens |
| Confusing states | Ambiguous labels, no confirmation, unclear next-step |
| Missing feedback | Action with no visible result, no loading/error state |
| Invalid inputs | How the app handled mistyped/wrong/empty input (graceful vs crash) |
| Recovery behavior | Could the user recover from an error without restart? |
| Expected vs observed | Stated app promise vs actual behavior (reality-check) |

Each signal becomes a field in the `UserSimulationCompleted` evidence payload (typed, with `proof` = screenshot/DOM snapshot/trace + `provenance` = Hermes session id).

---

## 5. EVIDENCE → STRUCTURED → VERIFIABLE

```
UserSimulationAgent (AI-OS)
   │  formulates: user_goal + exploration_brief
   ▼
Hermes cloud-browser worker (ACP session, isolated)
   │  actions: navigate/click/fill/observe/screenshot
   ▼
raw trace: {actions[], dom[], screenshots[], errors[], observations[]}
   │
   ▼
UserSimulationAgent evaluates vs user_goal
   │  emits: UserSimulationCompleted {
   │     goal_completion_pct,
   │     workflow_success,
   │     usability_blockers[],
   │     confusing_states[],
   │     recovery_behavior,
   │     expected_vs_observed,
   │     proof[] (screenshots + dom + session_id)
   │  }
   ▼
TestOrchestratorService.normalize() → TestingEvidence
   ▼
CouncilManager (TestingCouncil) ← one perspective among many
   ▼
AI-OS Verification → PASS/FAIL
```

The evidence is **machine-checkable** (completion %, bool flags, captured errors) — not prose opinion — so `CouncilManager` and verification can act on it deterministically.

---

## 6. INDEPENDENCE (ties to PART 13)

- The `UserSimulationAgent` is a *tester*, never the implementation builder.
- It receives the **target under test** (the running app), not the source.
- It cannot vote in its own favor; it contributes one perspective to `CouncilManager`, which decides.
- Hermes (the browser worker) has **no decision authority** — it returns raw observations, not verdicts.

---

## 7. ACCEPTANCE CRITERIA (for the future M7 build)

1. Given a fixture app with a *seeded usability defect*, the User Simulation Agent completes the happy path but **reports the defect** (usability blocker + screenshot proof) — it does not declare "works."
2. Given a confused-input sequence (empty submit, wrong button), the agent records the app's handling as evidence.
3. The agent's output is structured `UserSimulationCompleted` consumable by `TestOrchestratorService` and `CouncilManager`.
4. The agent runs in an isolated Hermes ACP session; no source-code access; no cross-contamination with builder.
5. On FAIL, findings route into the existing RCA→Learning→Replan→Re-execute loop.

---

*End of User Simulation Agent spec. Conceptual; Hermes cloud-browser is the execution substrate, AI-OS owns the agent + evidence.*
