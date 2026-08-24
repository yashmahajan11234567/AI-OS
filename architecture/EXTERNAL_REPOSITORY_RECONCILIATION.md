# EXTERNAL REPOSITORY RECONCILIATION — V2 TESTING EXTENSION

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23
**Scope:** Classify every external repository for the V2 multi-perspective testing + User Simulation requirement. Each repo gets EXACTLY ONE classification.

> Classifications: `CORE` (required by AI-OS arch) · `INTEGRATION` (consumable without core change) · `ADAPTER` (thin translation layer) · `TECHNIQUE` (method/patterns to re-implement) · `SKILL/PERSONA SOURCE` (content feed) · `REFERENCE` (design knowledge only) · `OPTIONAL` (interesting, not core) · `REJECT` (do not integrate).
>
> Evidence: `[LOCAL REPOSITORY]` (Hermes), `[EXTERNAL REPOSITORY]` (web), `[AI-OS SOURCE]` (verified V1), `[INFERENCE]`.

---

## 1. CLASSIFICATION TABLE

| # | Repository | Classification | Why | Testing relevance |
|---|---|---|---|---|
| 1 | **Hermes** (local) | `INTEGRATION` + `REFERENCE` | Mature standalone agent runtime; AI-OS drives it via MCP/ACP as a worker engine. Never CORE. `[LOCAL REPOSITORY]` | **User Simulation + browser testing execution engine**; MOA = synthesis technique; delegation = tester workers |
| 2 | **agency-agents** | `SKILL/PERSONA SOURCE` | 230+ MIT persona `.md`; Testing + Security Divisions are drop-in tester/security/architecture roles. `[EXTERNAL REPOSITORY]` | Seeds `AIAgencyService` member roles (api-tester, pentester, benchmarker, evidence-collector, architect) |
| 3 | **Ruflo** | `REFERENCE` | Agent meta-OS; competes with AI-OS kernel. `[EXTERNAL]` | Reject as core; architecture cross-check only |
| 4 | **Agent-Reach** | `INTEGRATION` | MCP web/social ingestion tool. `[EXTERNAL]` | Indirect: environment/content ingestion for tests |
| 5 | **Book-to-Skill** | `REFERENCE` | Offline `SKILL.md` authoring. `[EXTERNAL]` | Author test-skill personas offline |
| 6 | **NVIDIA SkillSpecTor** | `INTEGRATION` (gate) | Static/LLM skill+MCP security scanner. `[EXTERNAL]` | Security/Adversarial testing gate for test artifacts & target MCPs |
| 7 | **Loop Engineering** | `REFERENCE` | Loop patterns/primitives; AI-OS loop verified. `[EXTERNAL]` | Sandbox/worktree/gate patterns for test isolation |
| 8 | **Prompt Engineering Hub** | `REFERENCE` | Static prompt patterns. `[EXTERNAL]` | Improve tester/planner prompts |
| 9 | **FreeLLMAPI** | `INTEGRATION` | Provider-abstract model router (MCP). `[EXTERNAL]` | Model routing for test subagents (dev/test) |
| 10 | **Free Claude Code** | `OPTIONAL` | Unaffiliated provider launcher; billing risk. `[EXTERNAL]` | Optional model fallback only |
| 11 | **Graphify** | `INTEGRATION` (MCP) | AST knowledge-graph provider. `[EXTERNAL]` | Root-cause/test-navigation graph; architecture-review evidence |
| 12 | **Vercel Skills** | `INTEGRATION` (spec) | De-facto `SKILL.md` standard. `[EXTERNAL]` | Canonical test-persona skill format |
| 13 | **Superpowers** | `REFERENCE` | Composable skill methodology. `[EXTERNAL]` | Two-stage review methodology for testers |
| 14 | **Caveman** | `OPTIONAL` | Token compression (BSL-1.1 engine). `[EXTERNAL]` | Compress large test/agent payloads |
| 15 | **Everything Claude Code (ECC)** | `REFERENCE` | 68-agent harness toolkit patterns. `[EXTERNAL]` | chrome-devtools MCP = browser testing reference; AgentShield = security ref |
| 16 | **Karpathy LLM Council** | `TECHNIQUE` | Local multi-LLM web app ("Saturday hack", unlicensed). NOT a subsystem. `[EXTERNAL]` | Adopt: anonymized cross-ranking (accuracy+insight) + separate chairman synthesis |
| 17 | **evisoft Council** | `TECHNIQUE` | Claude Code SKILL.md prompt-templates (3 commits, no license). NOT a subsystem. `[EXTERNAL]` | Adopt: worldview-diverse advisors + relabel-then-review + "side with dissenter" adjudication |

---

## 2. THE TWO NEW REPOSITORIES — TECHNIQUE, NOT SUBSYSTEM (PART 5)

### Karpathy `llm-council`
- **What it IS:** A local web app (FastAPI + React) that sends one prompt to many OpenRouter LLMs in parallel, then synthesizes. Self-described "99% vibe coded as a fun Saturday hack." No license file.
- **Techniques (re-implement, do NOT vendor):**
  1. **Independent first-opinions** — each model answers independently (shown in tabs = perspective isolation).
  2. **Blind/anonymized cross-ranking** — identities stripped so models rank peers on *accuracy* and *insight* (two axes).
  3. **Separate chairman model** — a distinct configured model merges into a final answer.
- **Why TECHNIQUE not INTEGRATION:** No reusable library boundary, no license clarity, immature. The *ideas* map cleanly onto `CouncilManager` synthesis (`CouncilMember.expertise`, anonymized `CouncilVote`, separate `chair` role).
- **Adoption target:** a `synthesize()` stage inside `CouncilManager` — add `anonymize=True` + two-axis ranking + dedicated chairman member.

### evisoft `council`
- **What it IS:** Six Claude Code `SKILL.md` prompt-template folders scripting a deliberation flow. No code. ~10 stars, no license.
- **Techniques (re-implement):**
  1. **Worldview-diverse advisors** — 5 contradictory-stance advisors dispatched in one message (parallel, isolated).
  2. **Relabel-before-review** — replies randomly renamed A–E to break authority bias (cross-review).
  3. **Side-with-dissenter** — chairman may adopt a minority reasoning if it beats the majority.
  4. **Staged flow** — frame → parallel advisors → anonymize → peer review → chairman verdict.
- **Why TECHNIQUE not INTEGRATION:** Prompt templates, not a runtime; could be referenced as `SKILL.md` council-role prompts but the *logic* is what matters.
- **Adoption target:** a `critique()` stage in `CouncilManager` — assign advisors diverse stances, relabel for blind review, add dissenter-override rule.

> **Both are REFERENCE-grade techniques.** They must NOT become a second `CouncilManager`, a second council kernel, or a competing orchestration layer. They enrich the EXISTING `CouncilManager.synthesize/critique` paths.

---

## 3. HERMES — THE EXECUTION ENGINE FOR USER SIMULATION (PART 7)

Determined precisely from local source (`C:\Development\AI-OS\hermes-agent`):

| Hermes capability | Evidence | Use for testing |
|---|---|---|
| **Cloud browser automation** | `agent/browser_provider.py:50` `BrowserProvider` ABC — backends Browserbase / Browser-Use / Firecrawl, CDP websocket sessions | **User Simulation Agent execution substrate** — navigate, click, fill, screenshot, observe real UI |
| **Multi-provider model routing** | `agent/transports/` | Model layer for test subagents (dev/test) |
| **Delegation workers** | `agent/delegation_context.py`, `tools/async_delegation.py`, `delegate_task`, git-worktree isolation | Spawn per-perspective tester workers (security/perf/UX) |
| **MOA synthesis** | `agent/moa_loop.py` (117KB) — parallel reference opinions → aggregator | Synthesis/Judge technique for `CouncilManager` |
| **MCP serving** | `mcp_serve.py` | AI-OS drives Hermes as an MCP tool server |
| **ACP** | `acp_adapter/` (server, session, tools, permissions, provenance) | Preferred protocol for worker/runtime relationship (richer than MCP for agent execution + provenance) |
| **Estop / safety** | `agent/estop.py` | Safety gate for autonomous test workers |

**Decision:** Hermes = `INTEGRATION` (external agent-runtime driving browser/user-simulation + tester workers via **ACP preferred, MCP fallback**) + `REFERENCE` (MOA synthesis, delegation, context-compression patterns). AI-OS retains kernel, councils, verification, closed loop. Hermes is a **worker**, not a decider.

**What must cross the boundary:** task spec (perspective + target + constraints) → Hermes; structured evidence (actions, DOM snapshots, screenshots, errors, verdicts) + provenance → AI-OS. No AI-OS decision authority crosses to Hermes.

**MCP vs ACP:** ACP is preferable for the worker relationship (native agent-execution session model, permission + provenance tracking suits autonomous testers). MCP suffices for simpler tool calls. Both enter through AI-OS `mcp_manager`/integration layer — no kernel change.

---

## 4. AI AGENCY PERSONA RECONCILIATION (PART 6)

AI-OS `AIAgencyService` already defines 9 agency *types* (`core/ai_agency.py:37`). The external **agency-agents** Testing/Security Divisions supply **concrete role prompts** that can populate those types — avoiding blind import of all 230+ personas.

**Recommended curated testing-persona set (from agency-agents, MIT):**
- `testing-api-tester` → populate `PERFORMANCE`/`ARCHITECTURE` API+integration checks.
- `testing-performance-benchmarker` → populate `PERFORMANCE`.
- `testing-accessibility-auditor` → populate `ACCESSIBILITY`.
- `testing-evidence-collector` → evidence-collection skill for all testers.
- `testing-reality-checker` → adversarial claim-vs-behavior verification.
- `security-penetration-tester` → populate `SECURITY` (adversarial).
- `security-architect` / `engineering-code-reviewer` → populate `ARCHITECTURE`.
- `testing-test-automation-engineer` → regression-suite generation.
- `design-ux-researcher` → UX perspective (closest to User Simulation, but NOT a substitute — the actual simulator runs on Hermes browser).

**Overlap to avoid:** AI-OS already has the agency *roles*; agency-agents supplies *content*. Do NOT import the entire repo — curate ~8-10 personas via the `SKILL.md` adapter (M4). ECC/agency-agents personas that duplicate AI-OS agencies are dropped.

---

## 5. WHAT IS REJECTED / REFERENCE-ONLY (for testing)

- **Ruflo** — `REFERENCE` only (kernel competitor).
- **Karpathy LLM Council / evisoft Council** — `TECHNIQUE` only (not subsystems, not integrated as code).
- **Loop Engineering** — `REFERENCE` (sandbox/worktree patterns).
- **Prompt Hub / Superpowers / Book-to-Skill** — `REFERENCE` (methodology/authoring).
- **Caveman / Free Claude Code** — `OPTIONAL`.
- **Instagram** — `UNVERIFIED` (no evidence).

---

## 6. CLASSIFICATION SUMMARY (one line each)

- `INTEGRATION`: Hermes (worker+browser), Agent-Reach, Graphify, FreeLLMAPI, SkillSpecTor, Vercel Skills.
- `SKILL/PERSONA SOURCE`: agency-agents (curated personas).
- `TECHNIQUE`: Karpathy LLM Council, evisoft Council, Prompt Eng Hub.
- `REFERENCE`: Ruflo, Loop Engineering, Superpowers, Book-to-Skill, ECC.
- `OPTIONAL`: Caveman, Free Claude Code.
- `REJECT`: none new (Ruflo downgraded to REFERENCE; Instagram UNVERIFIED).

---

*End of external repository reconciliation. No code changed; techniques identified for later adoption into `CouncilManager`.*
