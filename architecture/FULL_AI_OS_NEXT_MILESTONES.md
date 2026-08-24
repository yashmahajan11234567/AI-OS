# FULL AI-OS NEXT DEVELOPMENT MILESTONES (V2)

**Terminal 1 — Read-Only Reconciliation**
**Date:** 2026-08-23

Proposes the smallest number of meaningful milestones building on the **verified V1 baseline** (M0–M3 ✅, 802/802 tests, 12/12 gates). No implementation performed here — these are proposals for future work.

> All milestones consume external capabilities **via the existing `mcp_manager` (or ACP for Hermes)** — no change to the AI-OS kernel, councils, validation, or closed loop. `[AI-OS SOURCE]`

---

## M4 — SKILL & SECURITY STANDARDIZATION (P1 foundation)

**Objective:** Make AI-OS skills portable and safe to ingest from the open ecosystem.

**Architecture requirements:**
- Align `SkillService` `Skill` model to the open `SKILL.md` standard (Vercel/agentskills.io frontmatter: `name`, `description`, `allowed-tools`, `Hooks`). `[INFERENCE]`
- Add a SecurityManager pre-install gate using NVIDIA SkillSpecTor (static AST/YARA scan + OSV CVE; optional LLM stage disabled or self-hosted within trust boundary). `[EXTERNAL]`

**Components involved:** `services/skill.py`, `core/skill_manager.py` (or equivalent), `services/mcp.py`, `SecurityManager`. `[AI-OS SOURCE]`
**Repositories involved:** Vercel Skills (spec), NVIDIA SkillSpecTor (gate), agency-agents (seed content), Book-to-Skill (authoring reference). `[EXTERNAL]`
**Dependencies:** V1 baseline; SkillSpecTor install (future, out of scope now).
**Implementation scope:**
- Define canonical `SKILL.md` adapter in `SkillService` (import/export).
- Register SkillSpecTor as a SecurityManager verification stage for skill/MCP registration.
- Seed `SkillService` with a curated subset of agency-agents personas (imported via adapter).
**Tests:** skill import/export round-trip; SecurityManager gate rejects a known-poisoned skill fixture; gate passes a clean skill.
**QA requirements:** All V1 gates remain green; new unit + integration tests for adapter and gate.
**Acceptance criteria:** AI-OS can load an external `SKILL.md` from any agentskills.io-compatible source; no skill registers without passing the SkillSpecTor gate.
**Deliberately does NOT implement:** a new skill authoring tool (Book-to-Skill stays REFERENCE), full marketplace UI, agent runtime changes.

---

## M5 — KNOWLEDGE-GRAPH MEMORY & INTEGRATION BACKBONE (P1+P2)

**Objective:** Add a runtime knowledge-graph memory tier and wire external MCP capabilities through it.

**Architecture requirements:**
- Mount Graphify as an MCP server feeding a new knowledge-graph memory tier; expose `query_graph`/`shortest_path` to planning/root-cause services. `[EXTERNAL]`
- Stand up the MCP integration backbone: Agent-Reach (web/social), FreeLLMAPI (model routing) behind `mcp_manager`. `[EXTERNAL]`
- Bridge Hermes as an external agent runtime via MCP/ACP. `[LOCAL]`

**Components involved:** `services/memory.py`, `core/root_cause.py` (or equivalent), `services/mcp.py`, `services/planning.py`, AI Runtime (Part 10). `[AI-OS SOURCE]`
**Repositories involved:** Graphify, Agent-Reach, FreeLLMAPI, Hermes. `[EXTERNAL]` `[LOCAL]`
**Dependencies:** M4 (skill/standard gate reused for MCP server vetting); provider credentials for FreeLLMAPI/Agent-Reach (future).
**Implementation scope:**
- Graphify MCP adapter → knowledge-graph memory tier; root-cause/planning query hooks.
- Agent-Reach MCP adapter (web/social ingestion).
- FreeLLMAPI MCP adapter (model-health routing behind AI Runtime).
- Hermes MCP/ACP bridge (spawn Hermes workers for agency tasks).
- Reuse SkillSpecTor gate for each new MCP server registration.
**Tests:** MCP server registration passes security gate; Graphify query returns edges for a known code path; Agent-Reach fetch returns page content; FreeLLMAPI routes a chat call; Hermes worker completes a delegated task.
**QA requirements:** V1 gates green; integration tests for each adapter; no production provider dependency required for CI (use local/mock).
**Acceptance criteria:** AI-OS can query a code knowledge graph, fetch web content, route a model call via FreeLLMAPI, and delegate a task to Hermes — all through `mcp_manager` with security gating.
**Deliberately does NOT implement:** replacing AI-OS memory core with Graphify (Graphify is an added tier); adopting Ruflo; changing the kernel.

---

## M6 — COUNCIL SYNTHESIS & QUALITY HARDENING (P2 technique + P3)

**Objective:** Enrich council decision synthesis with multi-perspective reasoning and apply quality optimizations.

**Architecture requirements:**
- Adopt Hermes MOA (`moa_loop.py`) as an internal *reasoning technique* inside council synthesis (multi-model opinion synthesis) — NOT a second council layer. `[LOCAL]` `[AI-OS SOURCE]`
- Optional token-compression adapter (Caveman) for large event/agent payloads, respecting BSL-1.1 engine license (use MIT skill/CLI only, or review engine license before embedding). `[EXTERNAL]`

**Components involved:** `core/council_manager.py`, Council synthesis path, event/memory payload emitters. `[AI-OS SOURCE]`
**Repositories involved:** Hermes (MOA technique), Caveman (optional). `[LOCAL]` `[EXTERNAL]`
**Dependencies:** M5 (Hermes bridge available); Caveman license review.
**Implementation scope:**
- MOA synthesis helper callable from CouncilManager (configurable, off by default).
- Caveman compression wrapper for selected high-volume payloads (optional, feature-flagged).
**Tests:** MOA synthesis produces a merged decision for a known multi-perspective case; compression reduces payload tokens within fidelity bounds on structured output.
**QA requirements:** V1 gates green; MOA off by default (no behavior change); Caveman behind feature flag.
**Acceptance criteria:** Councils *may* use multi-perspective synthesis; large payloads *may* be compressed — both opt-in, neither alters verified behavior.
**Deliberately does NOT implement:** a parallel council system (Ruflo/ECC rejected as core); mandatory compression; any kernel change.

---

## MILESTONE DEPENDENCY GRAPH

```
V1 (verified)
   │
   ├──► M4 (SKILL.md standard + SkillSpecTor gate)  ──► seeds agency-agents
   │         │
   └─────────┴──► M5 (Graphify / Agent-Reach / FreeLLMAPI / Hermes via MCP)
                     │
                     └──► M6 (MOA council technique + Caveman optional)
```

M4 is the foundation (standard + gate reused by M5/M6). M5 delivers the integration backbone. M6 is technique/quality hardening.

---

## WHAT THESE MILESTONES DELIBERATELY EXCLUDE

- **Ruflo** — competitor kernel; REFERENCE only.
- **Loop Engineering** — own closed loop verified; pattern cross-check only.
- **Free Claude Code** — OPTIONAL provider launcher; not in M4–M6 (reference pattern).
- **Obsidian** — dev/planning PKM, outside runtime.
- **Instagram** — UNVERIFIED, no evidence of relevance.
- **Any new kernel / council layer / skill format / model router** — consolidation rules forbid Frankenstein systems.

---

## OPEN QUESTIONS FOR V2 PLANNING (evidence gaps)

1. Hermes `LICENSE` text not read verbatim — confirm permissive terms before M5 bridge. `[LOCAL]` (unverified license text)
2. Star/commit counts for several external repos are implausibly high for 2026-created repos — treat as marketing visibility, validate before trusting adoption claims. `[EXTERNAL]`
3. FreeLLMAPI/Free Claude Code free-tier reliability and ToS — pilot in dev/test only, never production without SLA. `[EXTERNAL]`
4. SkillSpecTor LLM stage egress — must be disabled or self-hosted within AI-OS trust boundary. `[EXTERNAL]`
5. Graphify `INFERRED` edge non-determinism — treat inferred edges as advisory, not authoritative. `[EXTERNAL]`

---

*End of next milestones.*
