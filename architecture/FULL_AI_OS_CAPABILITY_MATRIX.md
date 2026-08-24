# FULL AI-OS CAPABILITY MATRIX

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23

This matrix extracts capabilities across AI-OS, Hermes, the ecosystem repositories, and maps each to AI-OS architecture. Status vocabulary:

- `IMPLEMENTED` — AI-OS V1 provides it
- `PROVIDED (ext)` — an external repository provides it
- `DUPLICATED` — provided by AI-OS AND external(s)
- `PARTIAL` — AI-OS partially implements
- `MISSING` — not in AI-OS, available externally
- `UNCLEAR` — insufficient evidence
- `N/A` — not applicable

---

## 1. CAPABILITY × SOURCE MATRIX

Legend columns:
`AIOS` = AI-OS V1 · `HER` = Hermes (local) · `RUF` = Ruflo · `AGA` = agency-agents · `ARE` = Agent-Reach · `B2S` = Book-to-Skill · `SKS` = SkillSpecTor · `LOE` = Loop Engineering · `PEH` = Prompt Eng Hub · `FLA` = FreeLLMAPI · `FCC` = Free Claude Code · `GRA` = Graphify · `VER` = Vercel Skills · `SUP` = Superpowers · `CAV` = Caveman · `ECC` = Everything Claude Code

| Capability | AIOS | HER | RUF | AGA | ARE | B2S | SKS | LOE | PEH | FLA | FCC | GRA | VER | SUP | CAV | ECC | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PLANNING | ✅ | | | | | | | ◐ | ◐ | | | | | ✅ | | ✅ | IMPLEMENTED + REFERENCE |
| REASONING | ✅ | ✅ | ✅ | | | | | | ◐ | | | | | | | ✅ | DUPLICATED |
| COUNCILS | ✅ | ◐(MOA) | ✅(swarm) | | | | | | | | | | | | | ✅(orch) | IMPLEMENTED + REFERENCE |
| MULTI-AGENT | ✅ | ✅ | ✅ | | | | | ✅ | | | | | | | | ✅ | DUPLICATED |
| EXECUTION | ✅ | ✅ | ✅ | | | | | ✅ | | | | | | | | ✅ | DUPLICATED |
| VERIFICATION | ✅ | | | | | | ✅ | ◐(gate) | | | | | | | | ✅(AgentShield) | IMPLEMENTED + INTEGRATION |
| FAILURE RECOVERY | ✅ | ◐ | | | | | | ✅ | | | | | | | | | IMPLEMENTED (AI-OS deeper) |
| ROOT CAUSE ANALYSIS | ✅ | | | | | | | | | | | | | | | | IMPLEMENTED |
| LEARNING | ✅ | ✅ | ✅ | ◐ | | | | | | | | | | | | ✅(instincts) | DUPLICATED |
| MEMORY | ✅(5-tier) | ✅(SQLite) | ✅(vector) | ◐ | | | | ✅(STATE.md) | | | | ✅(graph) | | | ✅(CCR) | ✅(vault) | DUPLICATED |
| SKILLS | ✅ | ✅ | ✅ | ✅ | | ✅ | | | | | | | ✅ | ✅ | ✅ | ✅ | DUPLICATED |
| MCP | ✅ | ✅ | ✅ | ◐(builder) | ✅ | | ✅ | ✅ | | ✅ | | ✅ | | | ✅ | ✅ | DUPLICATED |
| TOOLS | ✅ | ✅ | ✅ | | ✅ | | | ✅ | | ✅ | | | | | ✅ | ✅ | DUPLICATED |
| WEB ACCESS | ❌ | ✅(browser) | | | ✅ | | | | | | | | | | | ✅ | MISSING → INTEGRATION (Agent-Reach) |
| BROWSER | ❌ | ✅ | | | | | | | | | | | | | | ✅ | MISSING (external only) |
| CODE EXECUTION | ✅ | ✅ | ✅ | | | | | ✅ | | | | | | | ✅ | ✅ | DUPLICATED |
| MODEL ROUTING | ◐ | ✅ | ✅ | | | | | | | ✅ | ✅ | | | | | ✅ | PARTIAL → INTEGRATION |
| MODEL PROVIDERS | ◐ | ✅(multi) | ✅(5) | | | | | | | ✅(29) | ✅(49) | | | | | ✅ | PARTIAL → INTEGRATION |
| SUBAGENTS | ✅ | ✅ | | | | | | ✅ | | | | | | | | ✅ | DUPLICATED |
| PROMPT ENGINEERING | ◐ | ✅ | | | | | | | ✅ | | | | | | | ✅ | PARTIAL + REFERENCE |
| EVALUATION | ✅(11-layer) | ◐(evals/) | | | | | ✅(scanner) | | | | | | | | | ✅ | IMPLEMENTED + INTEGRATION |
| SELF-CRITIQUE | ◐ | ✅(MOA) | ✅ | | | | | | ◐ | | | | | | | ✅ | PARTIAL + REFERENCE |
| SELF-IMPROVEMENT | ✅ | ✅(skills) | ✅ | | | | | | | | | | | | | ✅ | DUPLICATED |
| OBSERVABILITY | ✅ | ✅(OTLP) | ✅ | | | | | | | | | | | | | ✅ | DUPLICATED |
| SECURITY | ✅(SecurityMgr) | ✅(estop) | ✅ | ◐ | | | ✅ | ◐ | | | | | | | | ✅(AgentShield) | IMPLEMENTED + INTEGRATION |
| SANDBOXING | ◐(agent quotas) | ◐(estop/wt) | ✅(WASM) | | | | | ✅(worktree) | | | | | | | | | PARTIAL + REFERENCE |
| PERSISTENCE | ✅(StorageMgr) | ✅(SQLite-WAL) | ✅(Mongo) | | | | | ✅(STATE.md) | | ✅(SQLite) | | ✅ | | | ✅(SQLite) | ✅ | DUPLICATED |
| KNOWLEDGE GRAPH | ❌ | | | | | | | | | | | ✅(AST) | | | | | MISSING → INTEGRATION (Graphify) |
| DOCUMENTATION GEN | ✅ | ✅ | ✅ | | | ✅ | | | | | | | | | | ✅ | DUPLICATED |
| DEVELOPER WORKFLOW | ✅(CLI) | ✅(CLI/TUI) | ✅ | ✅ | | ✅ | | ✅ | | | ✅ | | ✅ | ✅ | ✅ | ✅ | DUPLICATED |
| AUTOMATION | ✅ | ✅(cron) | ✅ | | | | | | | | | | | | | ✅ | DUPLICATED |
| TOKEN COMPRESSION | ❌ | ◐(context) | | | | | | | | | | | | | ✅ | | MISSING → OPTIONAL (Caveman) |

✅ = provides · ◐ = partial/related · ❌ = absent · blank = not offered

---

## 2. CAPABILITY DETERMINATION (per task categories)

| Capability | Determined as | Evidence |
|---|---|---|
| PLANNING | Implemented (AI-OS) + Reference patterns (Superpowers/ECC) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| REASONING | Implemented + duplicated (Hermes/Ruflo) | `[AI-OS SOURCE]` `[LOCAL]` `[EXTERNAL]` |
| COUNCILS | Implemented (CouncilManager) + Reference (Ruflo/ECC/Hermes MOA) | `[AI-OS SOURCE]` |
| MULTI-AGENT | Implemented + duplicated (Hermes delegation/Ruflo) | `[AI-OS SOURCE]` `[LOCAL]` |
| EXECUTION | Implemented + duplicated (Hermes/Loop Eng) | `[AI-OS SOURCE]` `[LOCAL]` |
| VERIFICATION | Implemented (11-layer) + Integration (SkillSpecTor) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| FAILURE RECOVERY | Implemented (AI-OS deeper than Loop Eng) | `[AI-OS SOURCE]` |
| RCA | Implemented | `[AI-OS SOURCE]` |
| LEARNING | Implemented + duplicated (Hermes/ECC) | `[AI-OS SOURCE]` `[LOCAL]` |
| MEMORY | Implemented (5-tier) + duplicated (Hermes/Graphify) | `[AI-OS SOURCE]` `[LOCAL]` `[EXTERNAL]` |
| SKILLS | Implemented + duplicated (many) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| MCP | Implemented + duplicated (many providers) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| TOOLS | Implemented + duplicated | `[AI-OS SOURCE]` `[EXTERNAL]` |
| WEB ACCESS | Missing → Integration (Agent-Reach) | `[EXTERNAL]` |
| BROWSER | Missing (external only) | `[LOCAL]` `[EXTERNAL]` |
| CODE EXECUTION | Implemented + duplicated | `[AI-OS SOURCE]` `[LOCAL]` |
| MODEL ROUTING | Partial → Integration (FreeLLMAPI) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| MODEL PROVIDERS | Partial → Integration | `[AI-OS SOURCE]` `[EXTERNAL]` |
| SUBAGENTS | Implemented + duplicated (Hermes) | `[AI-OS SOURCE]` `[LOCAL]` |
| PROMPT ENGINEERING | Partial + Reference (Prompt Eng Hub) | `[EXTERNAL]` |
| EVALUATION | Implemented + Integration (SkillSpecTor/AgentShield) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| SELF-CRITIQUE | Partial + Reference (MOA/ECC) | `[LOCAL]` `[EXTERNAL]` |
| SELF-IMPROVEMENT | Implemented + duplicated (Hermes/ECC) | `[AI-OS SOURCE]` `[LOCAL]` |
| OBSERVABILITY | Implemented + duplicated (Hermes OTLP) | `[AI-OS SOURCE]` `[LOCAL]` |
| SECURITY | Implemented + Integration (SkillSpecTor/AgentShield) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| SANDBOXING | Partial + Reference (Loop Eng worktree/WASM) | `[AI-OS SOURCE]` `[EXTERNAL]` |
| PERSISTENCE | Implemented + duplicated | `[AI-OS SOURCE]` `[LOCAL]` |
| KNOWLEDGE GRAPH | Missing → Integration (Graphify) | `[EXTERNAL]` |
| DOCUMENTATION | Implemented + duplicated | `[AI-OS SOURCE]` `[EXTERNAL]` |
| DEVELOPER WORKFLOW | Implemented + duplicated | `[AI-OS SOURCE]` `[EXTERNAL]` |
| AUTOMATION | Implemented + duplicated | `[AI-OS SOURCE]` `[EXTERNAL]` |
| TOKEN COMPRESSION | Missing → Optional (Caveman) | `[EXTERNAL]` |

---

## 3. CAPABILITY CLUSTERS → AI-OS LAYER

| Cluster | AI-OS Layer | External providers (status) |
|---|---|---|
| Planning/Reasoning | planning service (Part 10) | Superpowers, ECC (REFERENCE); Hermes MOA (REF technique) |
| Councils | CouncilManager (core) | Ruflo (REF), ECC orch (REF), Hermes MOA (REF technique) |
| Multi-agent/Execution | AI Agency + kernel | Hermes (INTEGRATION), Ruflo (REF) |
| Verification/Eval | validation (11 layers) | SkillSpecTor (INTEGRATION), ECC AgentShield (REF) |
| Failure Recovery/RCA | core (root_cause/retry) | Loop Eng (REF) |
| Learning | learning service | Hermes (INTEGRATION/REF), ECC instincts (REF) |
| Memory | 5-tier | Hermes SQLite (REF), Graphify (INTEGRATION) |
| Skills | SkillService | Vercel spec (INTEGRATION), Book-to-Skill (REF), agency-agents (INTEGRATION), Superpowers (REF) |
| MCP | mcp_manager | Agent-Reach, Graphify, FreeLLMAPI, SkillSpecTor, Hermes (all INTEGRATION) |
| Model Layer | Part 10 AI Runtime | FreeLLMAPI (INTEGRATION), Free Claude Code (OPTIONAL), Hermes transports (INTEGRATION) |
| Observability | ObservabilityManager | Hermes OTLP (REF) |
| Security | SecurityManager | SkillSpecTor (INTEGRATION), AgentShield (REF), Hermes estop (REF) |
| Sandboxing | agent quotas | Loop Eng worktree (REF), Ruflo WASM (REF) |
| Knowledge Graph | (none) | Graphify (INTEGRATION) — fills gap |
| Token Compression | (none) | Caveman (OPTIONAL) — fills gap |
| Web/Social | (none) | Agent-Reach (INTEGRATION) — fills gap |

---

## 4. CONSOLIDATION RULES (avoid Frankenstein)

1. **One kernel** — AI-OS. Ruflo is REFERENCE, not core.
2. **One council layer** — CouncilManager. Hermes MOA is a synthesis technique, not a second council.
3. **One skill format** — adopt open `SKILL.md` (Vercel de-facto). All skill repos align to it.
4. **One model-routing path** — FreeLLMAPI behind `mcp_manager`. Free Claude Code is OPTIONAL reference.
5. **One memory core** — AI-OS 5-tier; Graphify adds an MCP graph tier; Hermes SQLite is a separate runtime.
6. **MCP as the only integration boundary** — every external capability enters via `mcp_manager` (or ACP for Hermes).

---

*End of capability matrix.*
