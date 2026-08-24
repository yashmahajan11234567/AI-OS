# FULL AI-OS V1 → V2 GAP ANALYSIS

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23

Compares the full discovered architecture against the verified V1 baseline. Priority vocabulary: **P0** (blocker/critical), **P1** (high), **P2** (medium), **P3** (low), **Future** (defer).

> V1 baseline is treated as AUTHORITATIVE per task statement (M0–M3 ✅, 802/802 tests, 12/12 gates, Terminal 3 QA passed). `[AI-OS SOURCE]`

---

## GAP TABLE

| Capability | V1 State | Architecture Requires | External Resource Available | Gap | Priority | Evidence |
|---|---|---|---|---|---|---|
| Knowledge-graph memory tier | Absent (no AST graph) | Useful for root-cause/planning navigation | Graphify (INTEGRATION) | Missing runtime graph | P1 | `[EXTERNAL]` `[AI-OS SOURCE]` |
| Canonical skill format | Internal model only | Cross-agent portability | Vercel Skills `SKILL.md` (INTEGRATION) | Format not standardized | P1 | `[EXTERNAL]` |
| Skill/MCP security vetting | SecurityManager present, no skill scanner | Pre-install poisoning/injection gate | SkillSpecTor (INTEGRATION) | Missing dedicated gate | P1 | `[EXTERNAL]` `[AI-OS SOURCE]` |
| Provider-abstracted model layer | Partial (Part 10 AI Runtime) | Vendor decoupling + free tiers | FreeLLMAPI (INTEGRATION) | Partial model routing | P2 | `[EXTERNAL]` `[AI-OS SOURCE]` |
| Web/social tool access | Absent | External ingestion for agents | Agent-Reach (INTEGRATION, MCP) | Missing web tool | P2 | `[EXTERNAL]` |
| External agent-runtime bridge | Absent | Leverage mature agent engine | Hermes (INTEGRATION, MCP/ACP) | No bridge | P2 | `[LOCAL]` |
| Council multi-perspective synthesis | Councils present (governance) | Richer decision synthesis | Hermes MOA (REF technique) | Technique not adopted | P2 | `[LOCAL]` `[AI-OS SOURCE]` |
| Skill content library | SkillService empty of content | Seed persona/skills | agency-agents (INTEGRATION) | No seeded content | P2 | `[EXTERNAL]` |
| Offline skill authoring | Absent | Author skills from docs | Book-to-Skill (REFERENCE) | Missing authoring path | P3 | `[EXTERNAL]` |
| Token compression | Absent | Cost reduction on payloads | Caveman (OPTIONAL) | Missing compressor | P3 | `[EXTERNAL]` |
| Loop pattern primitives | Closed loop verified | Cross-check gate/sandbox | Loop Engineering (REFERENCE) | N/A (own loop verified) | Future | `[EXTERNAL]` `[AI-OS SOURCE]` |
| Prompt-engineering patterns | Implicit in services | Improve planning prompts | Prompt Eng Hub (REFERENCE) | N/A (low value) | Future | `[EXTERNAL]` |
| Agent-OS kernel (Ruflo) | N/A | — | Ruflo (REFERENCE only) | Explicitly NOT adopted | REJECT | `[EXTERNAL]` |
| Instagram resource | UNVERIFIED | Unknown | Instagram (UNVERIFIED) | No evidence | UNKNOWN | `[EXTERNAL]` |

---

## GAP SUMMARY BY PRIORITY

### P1 — High (build first in V2)
1. **Knowledge-graph memory tier** — mount Graphify as MCP server; seed AI-OS knowledge-graph memory tier for root-cause/planning.
2. **Canonical `SKILL.md` skill format** — align `SkillService` model to Vercel/agentskills.io frontmatter for import/export portability.
3. **Skill/MCP security vetting gate** — wire SkillSpecTor as a SecurityManager pre-install gate (static + optional LLM; disable LLM egress outside trust boundary).

### P2 — Medium
4. Provider-abstracted model layer (FreeLLMAPI behind `mcp_manager`).
5. Web/social tool access (Agent-Reach via MCP).
6. External agent-runtime bridge (Hermes via MCP/ACP).
7. Council multi-perspective synthesis technique (Hermes MOA as internal reasoning technique).

### P3 — Low
8. Skill content seeding (agency-agents personas).
9. Offline skill authoring (Book-to-Skill).
10. Token compression (Caveman — BSL-1.1 engine caveat).

### Future / REFERENCE (no build yet)
- Loop Engineering primitives (own loop verified).
- Prompt Eng Hub patterns.
- Ruflo (REJECT as core).
- Instagram (UNVERIFIED).

---

## WHAT V1 ALREADY COVERS (NOT GAPS)

Per verified baseline, these are NOT gaps — do not re-build:
- Event architecture / EventBus ✅
- Kernel lifecycle + 9 Core Managers ✅
- 9 governance Councils + CouncilManager ✅
- 9 AI Agency agents ✅
- 5-tier memory ✅
- Skills registry/runtime (SkillService) ✅ — *format standardization is the gap, not the service*
- MCP manager ✅ — *providers are the gap, not the manager*
- 11-layer validation ✅
- Observability ✅
- Closed-loop execution + failure recovery (root_cause/retry/learning) ✅
- SecurityManager ✅ — *skill/MCP vetting gate is the gap, not the manager*

---

## PRIORITY RATIONALE

- **P1 items are not "missing features" but missing INTEGRATION BOUNDARIES** that unlock external value safely: a graph memory tier (Graphify), a portable skill standard (Vercel), and a security gate (SkillSpecTor). These are low-risk, high-leverage, and align to existing AI-OS services.
- **P2 items extend reach** (models, web, external agent runtime) without changing core architecture — all enter via MCP/ACP.
- **P3/Optional items are cost/quality niceties** (token compression) or content seeding — valuable but not architecturally load-bearing.
- **Ruflo is explicitly rejected** as a core because it competes with the verified AI-OS kernel (Frankenstein risk). `[INFERENCE]`

---

*End of gap analysis.*
