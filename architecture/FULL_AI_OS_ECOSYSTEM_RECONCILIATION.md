# FULL AI-OS ECOSYSTEM DISCOVERY & ARCHITECTURE RECONCILIATION

**Terminal 1 — Read-Only Reconnaissance**
**Date:** 2026-08-23
**Scope:** Discovery and reconciliation of the full AI-OS ecosystem. No implementation, no modification, no installation.

---

## 0. EVIDENCE RULE & STATUS LEGEND

Every major conclusion is tagged with its evidence source:

- `[AI-OS SOURCE]` — verified against the local AI-OS repository source/docs
- `[LOCAL REPOSITORY]` — verified against a local repository on this machine (Hermes)
- `[EXTERNAL REPOSITORY]` — verified against public GitHub content / API
- `[DOCUMENTATION]` — AI-OS architecture documentation (Parts 0–15)
- `[INFERENCE]` — reasoned from evidence, not directly verified

Recommended-status vocabulary (only these used):

- `CORE` — required by AI-OS architecture
- `INTEGRATION` — useful capability sourced from an existing repository, consumable without core change
- `OPTIONAL` — interesting, not a core dependency yet
- `REFERENCE` — design/knowledge reference only, no integration
- `EXPERIMENTAL` — unproven, evaluate before trusting
- `REJECT` — should not be integrated
- `UNKNOWN` — insufficient evidence

> **Baseline note (authoritative):** The task states Part 15 V1 is complete and independently verified: M0–M3 ✅, 802/802 tests passing, 12/12 V1 release gates passing, Terminal 3 QA passed, verdict "READY WITH NON-BLOCKING DEBT." This report treats that verified V1 baseline as authoritative. Older root-level QA artifacts in the working tree (`FINAL_RELEASE_QA_REPORT.md`, `RELEASE_READINESS_AUDIT.md`, etc.) are **stale historical artifacts** from a pre-V1 state and are NOT treated as current status. `[AI-OS SOURCE]`

---

## PART 1 — CURRENT AI-OS REPOSITORY (DISCOVERY)

**Authoritative architecture documents identified** `[AI-OS SOURCE]` `[DOCUMENTATION]`:

| Artifact | Path | Role |
|---|---|---|
| Master Architecture Map | `architecture/AI-OS_MASTER_ARCHITECTURE_MAP.md` (76.6 KB) | **Single source of truth / navigation hub** for all Parts |
| Part 0 — Frozen Foundation | `architecture/Part00/ARCHITECTURE_SPEC_PART0.md` | Terminology, principles, conformance levels L1–L4, extension points, ADR process — **FROZEN** |
| Master Architecture Roadmap | `architecture/Common/MASTER_ARCHITECTURE_ROADMAP.md` | Authoritative 15-part roadmap, shared components, JSON schemas, ADR map, invariants |
| Project Knowledge — Master Context | `architecture/project-knowledge/AI_OS_MASTER_CONTEXT.md` | Architecture narrative "definitive source of truth" |
| Project Knowledge — Roadmap | `architecture/project-knowledge/ROADMAP.md` | Near/mid/long-term roadmap, milestones through 2031 |

**Parts 1–15** (`architecture/Part01` … `Part15`): Parts 1–14 are complete and substantive (Part 4 alone is 251.8 KB across PART4/A/B/C). Part 15 ("Architecture Evolution & Extensibility") is the verified V1 baseline per task statement. `[DOCUMENTATION]`

**Council specification** — `architecture/project-knowledge/COUNCILS.md` is the primary council spec; Part 13 (Governance Architecture) contains the full governance treatment. `[AI-OS SOURCE]`

**Hermes Kernel spec** — `architecture/Part03/ARCHITECTURE_SPEC_PART3.md` (74.6 KB). The "Hermes Kernel" here is an **internal AI-OS kernel abstraction** (EventBus, ServiceRegistry, ConfigurationManager, StructuredLogger + 9 core managers), **not** the downloaded `hermes-agent` repository (see Part 8). `[DOCUMENTATION]`

**AI Agency spec** — `architecture/project-knowledge/AI_AGENCY.md`; Part 11 (Agent & Cognitive Architecture); Part 12 (Multi-Agent Collaboration). `[AI-OS SOURCE]`

**Memory / Skills / MCP specs** — `architecture/project-knowledge/MEMORY_ARCHITECTURE.md`, `SKILLS_ECOSYSTEM.md`, `MCP_ECOSYSTEM.md`. `[AI-OS SOURCE]`

**V1 release documentation** — `architecture/Part15/` (verified baseline). Root-level `RELEASE_READINESS_AUDIT.md`, `FINAL_RELEASE_QA_REPORT.md` etc. are **stale** pre-V1 artifacts. `[AI-OS SOURCE]`

**Deferred-work documentation** — `TASK_10_ARCHITECTURE_REVIEW.md` (StateManager upgrade), `TASK_13_*.md`, `M3_FINAL_REMEDIATION_QA_REPORT.md`, `EVENT_CORE_FINAL_REMEDIATION_REPORT.md`. `[AI-OS SOURCE]`

---

## PART 2 — HERMES AGENT (LOCAL)

**Found at:** `C:\Development\AI-OS\hermes-agent` `[LOCAL REPOSITORY]`
**Version/commit:** `v2026.8.13-103-gc896c09c4` (HEAD `c896c09c4`) `[LOCAL REPOSITORY]`
**Language:** Python (UV/pip managed; also ships JS/TS gateway + Docker) `[LOCAL REPOSITORY]`
**License:** Present (`LICENSE`); permissive family (MIT-style per `package.json`/`pyproject.toml` metadata) — exact text to be confirmed by reading `LICENSE` before any integration. `[LOCAL REPOSITORY]` (unverified license text)

**Entry points** (confirmed by direct read): `cli.py` (875 KB), `run_agent.py` (378 KB), `mcp_serve.py` (36 KB), launcher `hermes`, `hermes_cli/main.py` (`main.py:11583`, ~50 CLI subcommands: `chat`, `gateway`, `cron`, `model`, `moa`, `fallback`, `kanban`, `skills`, `plugins`, `send`, `webhook`, `verify`, `security`, `checkpoints`, `acp`, `oneshot`, …). `[LOCAL REPOSITORY]`

**What Hermes ACTUALLY provides** (capability inventory, from source reads):

| Capability | Evidence | Real? |
|---|---|---|
| Autonomous agent runtime (multi-turn) | `agent/conversation_loop.py:1494`, `IterationBudget` (default 90) | ✅ Yes |
| Multi-provider model routing | `agent/transports/` (`anthropic.py`, `codex.py`, `gemini_native_adapter.py`, `vertex_adapter.py`, `azure_identity_adapter.py`) | ✅ Yes |
| Parallel tool batch execution | `conversation_loop.py` ThreadPoolExecutor (up to 8 workers) | ✅ Yes |
| Retry / fallback / overload classification | `agent/error_classifier.py`, fallback-model chain | ✅ Yes |
| Subagent delegation | `delegate_task`, `agent/delegation_context.py`, daemon threads, `tools/async_delegation.py`, git-worktree isolation, `MAX_DEPTH` configurable (default 1) | ✅ Yes |
| Runtime context compression | `agent/context_compressor.py` (in-place / session-rotation, cooldown/anti-thrash) | ✅ Yes (corrected: NOT batch-only) |
| Offline trajectory compression | `trajectory_compressor.py` (training-data prep) | ✅ Yes (research pipeline) |
| Memory | `agent/memory_manager.py`, `agent/memory_provider.py`; `hermes_state.py` (SQLite-WAL + FTS5 + Honcho) | ✅ Yes |
| Self-improvement (non-ML) | agent-authored skills + memory over SQLite | ✅ Yes |
| Learning graph | `agent/learning_graph.py`, `learning_mutations.py` | ✅ Yes |
| Mixture-of-Agents | `agent/moa_loop.py`, `moa_trace.py` | ✅ Yes |
| MCP serving | `mcp_serve.py` | ✅ Yes |
| ACP (Agent Client Protocol) | `acp_adapter/` (server, session, tools, permissions, provenance) | ✅ Yes |
| Gateway / multi-platform | `gateway/`, `web/`, `tui_gateway/`, `ui-tui/` | ✅ Yes |
| Plugins / skills | `plugins/`, `skills/`, `optional-skills/`, `optional-mcps/` | ✅ Yes |
| Safety (estop) | `agent/estop.py` | ✅ Yes |
| Browser / image gen | `agent/browser_provider.py`, `image_gen_provider.py` | ✅ Yes |

**Capability gap:** Hermes is a **mature standalone autonomous-agent product**, not the AI-OS "Hermes Kernel." It overlaps AI-OS capabilities (agent runtime, model layer, memory, skills, MCP, delegation, safety) but is a *separate deployable system*. It does **not** implement: AI-OS governance Councils, the event-bus kernel topology, the 11-layer validation architecture, or the AI-OS closed-loop failure-recovery orchestration. `[INFERENCE]` from comparing `[LOCAL REPOSITORY]` to `[DOCUMENTATION]`.

**Recommended status:** `INTEGRATION` (external agent runtime / model-interface layer that can be driven by AI-OS) + `REFERENCE` (for agent-runtime, delegation, MOA, context-compression, model-routing patterns). See Part 8 for mapping.

---

## PART 3 — EXTERNAL REPOSITORIES PROVIDED BY THE USER

All 15 GitHub repos were inspected via README + GitHub API. Instagram was behind a login wall (UNVERIFIED). Star/commit figures are reported verbatim from the GitHub API; several are implausibly high for repos created in early 2026 and should be treated as "highly marketed/visible," not independently validated popularity. `[EXTERNAL REPOSITORY]`

Repository inventory and final recommended status (full field tables in PART 4):

| # | Name | URL | Status |
|---|---|---|---|
| 1 | agency-agents | github.com/msitarzewski/agency-agents | INTEGRATION |
| 2 | Ruflo | github.com/ruvnet/ruflo | REFERENCE |
| 3 | Agent-Reach | github.com/Panniantong/agent-reach | INTEGRATION |
| 4 | Book-to-Skill | github.com/virgiliojr94/book-to-skill | REFERENCE |
| 5 | NVIDIA SkillSpecTor | github.com/nvidia/skillspector | INTEGRATION |
| 6 | Loop Engineering | github.com/cobusgreyling/loop-engineering | REFERENCE |
| 7 | Prompt Engineering Techniques Hub | github.com/KalyanKS-NLP/Prompt-Engineering-Techniques-Hub | REFERENCE |
| 8 | FreeLLMAPI | github.com/tashfeenahmed/freellmapi | INTEGRATION |
| 9 | Free Claude Code | github.com/alishahryar1/free-claude-code | OPTIONAL |
| 10 | Graphify | github.com/Graphify-Labs/graphify | INTEGRATION |
| 11 | Vercel Skills | github.com/vercel-labs/skills | INTEGRATION |
| 12 | Superpowers | github.com/obra/superpowers | REFERENCE |
| 13 | Caveman | github.com/juliusbrussee/caveman | OPTIONAL |
| 14 | Everything Claude Code (ECC) | github.com/affaan-m/ECC (redirect from everything-claude-code) | REFERENCE |
| 15 | Instagram p/DaNYCILlDgO | instagram.com/p/DaNYCILlDgO | UNVERIFIED |

> **Instagram:** WebFetch returned only the literal text "Instagram" with no post content. Marked **UNVERIFIED** per the task rule — not guessed. `[EXTERNAL REPOSITORY]`

---

## PART 4 — REPOSITORY-BY-REPOSITORY ANALYSIS

### 1. agency-agents
- **URL:** github.com/msitarzewski/agency-agents · **Local copy:** No · **Version:** API created 2025-10-13, pushed 2026-08-06
- **Primary purpose:** Library of 230+ reusable AI-agent *persona/role* `.md` files installable into coding tools. `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Static role/persona definitions (engineering, design, sales, security, etc.); "Agents Orchestrator" + "Testing Division" = collections of role files. `[EXTERNAL REPOSITORY]`
- **Agent/Planning/Learning/Memory/Skill/Council/MCP:** Skills=persona `.md`; Memory="Learning Memory" (design note only); Council=Orchestrator (role collection); MCP=dedicated MCP Builder role. No runtime engine. `[EXTERNAL REPOSITORY]`
- **Tool execution:** `install.sh`/`convert.sh` copy/transform files to `~/.claude/agents/`, `.cursor/rules/`, etc. No agent-side runtime. `[EXTERNAL REPOSITORY]`
- **Model/API support:** Format conversions for Claude Code, Copilot, Gemini CLI, OpenCode, Cursor, Aider, Windsurf, Qwen, Kimi, Codex, Hermes, OpenClaw. `[EXTERNAL REPOSITORY]`
- **Evaluation/testing:** "Testing Division" = advisory quality gates, not automated suite. `[EXTERNAL REPOSITORY]`
- **Security/sandboxing:** "Security Division" personas are content, not enforcement. `[EXTERNAL REPOSITORY]`
- **Persistence:** Filesystem only. **Dependencies:** Unix shell, git. **Maturity:** High visibility. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Seeds `SkillService` (`src/aios/services/skill.py`) with 230+ role definitions + import toolchain. `[INFERENCE]`
- **Overlap:** AI-OS "Skill" (persona+process) concept only. **Risks:** No semantic versioning; personas may drift from AI-OS conventions; "Security Division" is not real enforcement.
- **Recommended status:** **INTEGRATION** (skill/persona content source feeding `SkillService`).

### 2. Ruflo
- **URL:** github.com/ruvnet/ruflo · **Local copy:** No · **Version:** API created 2025-06-02, pushed 2026-08-22
- **Primary purpose:** "Agent meta-harness" — control layer wrapping coding assistants (Agent = Model + Harness). `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Multi-agent orchestration, cross-machine messaging, adaptive recall, self-learning memory, RAG; native Claude Code/Codex/Hermes integration. `[EXTERNAL REPOSITORY]`
- **Agent/Planning/Learning/Memory/Skill/Council/MCP:** Planning=Goal UI via A*; Learning=neural pattern matching; Memory=vector index; Skills=30; MCP=MCP server (~210 UI tools); Council=multi-player swarms. `[EXTERNAL REPOSITORY]`
- **Model/API support:** 5 providers with failover; browser demo curates ~6 frontier models. `[EXTERNAL REPOSITORY]`
- **Security/sandboxing:** injection/leak guards; zero-trust federation (mTLS + WireGuard); WASM sandbox. Persistence: vector store, Mongo. `[EXTERNAL REPOSITORY]`
- **Dependencies:** Rust engine, npm, Docker, Supabase, Mongo. **Maturity:** High visibility, 831 open issues. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Highest conceptual overlap with AI-OS (mirrors council/mcp/memory/skill/workflow/kernel module map). **Overlap:** nearly all core managers + cross-machine federation. `[INFERENCE]`
- **Risks:** Broad marketing claims likely exceed delivered reality; heavy stack vs AI-OS Python; **competes** with AI-OS kernel rather than complements it.
- **Recommended status:** **REFERENCE** (architecture/benchmark reference). REJECT as drop-in core.

### 3. Agent-Reach
- **URL:** github.com/Panniantong/agent-reach · **Local copy:** No · **Version:** API created 2026-02-24, pushed 2026-08-12
- **Primary purpose:** CLI capability layer giving agents web/social access (Twitter, Reddit, YouTube, GitHub, Bilibili, XHS) — "one CLI, zero API fees." `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Zero-config reading of webpages/YouTube/RSS/GitHub/Bilibili; login-gated channels; ordered backend fallbacks; `doctor` diagnostics. `[EXTERNAL REPOSITORY]`
- **Agent/Skill/MCP:** Not an agent framework — a *tool* any command-line agent calls. MCP via `mcporter` (Exa search + LinkedIn/XHS). `[EXTERNAL REPOSITORY]`
- **Model/API support:** Open-source/free APIs, many keyless (Jina, Exa MCP). **Security:** local-only credentials, default non-modifying, `chmod 600` config. `[EXTERNAL REPOSITORY]`
- **Dependencies:** Python ≥3.10, Node, gh CLI, mcporter, per-channel tools. **Maturity:** High visibility. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Clean fit as MCP web/social ingestion tool behind `mcp_manager` (`src/aios/services/mcp.py`). `[INFERENCE]`
- **Overlap:** AI-OS MCP/external-tool surface only. **Risks:** scraping ToS/legal + breakage; free-tier fragility.
- **Recommended status:** **INTEGRATION** (MCP/web-ingestion tool).

### 4. Book-to-Skill
- **URL:** github.com/virgiliojr94/book-to-skill · **Local copy:** No
- **Primary purpose:** Converts owned PDFs/books into Claude Code skills ("Turn any technical book PDF into a Claude Code skill"). `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Text extraction (PDF/EPUB/DOCX/HTML/RTF/MOBI/TXT); generates `SKILL.md` + chapter/glossary/patterns/cheatsheet; modes analyze/update/fold-in/publish; validation. `[EXTERNAL REPOSITORY]`
- **Skill definition:** `SKILL.md` + supporting markdown conforming to the **open Agent Skills standard** (Claude Code, Copilot CLI, Amp). `[EXTERNAL REPOSITORY]`
- **Tool execution:** local extraction (`pdftotext`, `docling`, `ebooklib`). Model/API: local processing, no LLM required. **Evaluation:** pytest; token-reduction claims. `[EXTERNAL REPOSITORY]`
- **Security:** local-only, files never uploaded. **Persistence:** `~/.claude/skills/<slug>/`. **Dependencies:** poppler, pypdf, docling, etc. **License:** MIT (code). `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Offline skill-authoring in the open `SKILL.md` standard; bridge to import documented knowledge as AI-OS skills. `[INFERENCE]`
- **Overlap:** Skill concept only (file-format level); no runtime/loop/kernel. **Risks:** ⚠️ Star/commit figures implausible for a personal repo (unverified); tied to Anthropic Agent Skills standard; copyright on ingested books.
- **Recommended status:** **REFERENCE** (skill-format reference + offline authoring).

### 5. NVIDIA SkillSpecTor
- **URL:** github.com/nvidia/skillspector · **Local copy:** No · **Version:** 369 commits, NVIDIA-official
- **Primary purpose:** Security scanner for AI agent skills — detects malicious patterns/supply-chain risk *before* install. `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Multi-format input (SKILL.md, Python, requirements.txt, dirs, zips, Git URLs); ~70 vuln patterns across 17 categories; two-stage static (regex/AST/YARA) + optional LLM eval; OSV.dev CVE lookups; 0–100 risk score; SARIF/JSON/MD output. `[EXTERNAL REPOSITORY]`
- **MCP:** runs as MCP server (`skillspector mcp`) exposing `scan_skill`; detects MCP least-privilege + tool-poisoning. Detects (not implements) memory poisoning, rogue-agent patterns. `[EXTERNAL REPOSITORY]`
- **Model/API support:** openai/anthropic/bedrock/ollama/etc. for optional LLM stage. **Security:** "defense-in-depth, not a sandbox"; LLM stage sends file contents to provider. `[EXTERNAL REPOSITORY]`
- **Dependencies:** Python 3.12+, uv/pip, Docker, FastMCP, boto3, LangGraph. **Maturity:** High, active. **License:** Apache-2.0. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Directly hardens AI-OS `SecurityManager` skill/MCP ingestion against prompt-injection / tool-poisoning / memory-poisoning. `[INFERENCE]`
- **Overlap:** SecurityManager scope (skill/MCP trust, poisoning detection). **Risks:** Apache-2.0 fine; optional LLM stage exfiltrates content (disable/self-host in trust boundary); needs AI-OS's own sandbox still.
- **Recommended status:** **INTEGRATION** (pre-install security gate for skills/MCP).

### 6. Loop Engineering
- **URL:** github.com/cobusgreyling/loop-engineering · **Local copy:** No
- **Primary purpose:** Patterns/starters/CLIs to build systems orchestrating agents via a closed loop ("Stop prompting. Design the loop. Get a score."). `[EXTERNAL REPOSITORY]`
- **Core capabilities:** `loop`/`loop-audit`/`loop-init` npm tools; "Loop Ready" score; `doctor`/`sync`/`gate`/`sandbox`/`worktree`; MCP server. 7 documented loop patterns. `[EXTERNAL REPOSITORY]`
- **Agent/Planning/Memory/Skill/MCP:** maker/checker sub-agents; L1–L3 autonomy; durable `STATE.md` memory + circuit breaker; skills hold project knowledge; MCP connectors with scoped reach. **Council:** none. `[EXTERNAL REPOSITORY]`
- **Closed-loop:** schedule→triage→state→worktree→implement→verify→MCP→human gate→commit→repeat (code + patterns). **Overlap:** directly with AI-OS closed-loop/failure-recovery. `[INFERENCE]`
- **Model/API:** `--tool` swap grok/claude/codex/opencode. **Security:** `gate.yaml` denylist+allowlist; `loop-sandbox` worktree isolation. **Dependencies:** Node/npm. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Lighter/pattern-grade vs AI-OS's own closed loop (kernel lifecycle, WorkflowManager, root_cause, retry, learning). `[INFERENCE]`
- **Risks:** conceptual/starter maturity; companion-repo sprawl; Node vs AI-OS Python.
- **Recommended status:** **REFERENCE** (pattern cross-check + candidate gate/sandbox/worktree/MCP primitives).

### 7. Prompt Engineering Techniques Hub
- **URL:** github.com/KalyanKS-NLP/Prompt-Engineering-Techniques-Hub · **Local copy:** No · ~475 stars
- **Primary purpose:** Reference catalog of 25+ prompt-engineering techniques (29 documented: Zero-shot, Role, Few-Shot, Reasoning, Self-Refine, Chain of Verification, etc.). `[EXTERNAL REPOSITORY]`
- **Capabilities:** Static Markdown patterns only — no agent, MCP, memory, skill/council runtime. Prompt-level analogues (Plan-and-Solve, Self-Refine). `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Low; could inform `planning.py`/`learning.py`/`root_cause.py` prompt design. **License:** Apache-2.0. **Risks:** no code = no supply-chain risk, low dependency value.
- **Recommended status:** **REFERENCE**.

### 8. FreeLLMAPI
- **URL:** github.com/tashfeenahmed/freellmapi · **Local copy:** No · ~19.4k stars
- **Primary purpose:** OpenAI-compatible API proxy/router stacking ~29 free LLM providers (~4B tokens/month) behind one `/v1` endpoint with smart routing/failover. `[EXTERNAL REPOSITORY]`
- **Core capabilities:** All OpenAI surfaces + Anthropic Messages wire + native Gemini + Ollama emulation + Fusion multi-model synthesis + prompt compression + admin dashboard analytics. 251 model families / 358 endpoints. `[EXTERNAL REPOSITORY]`
- **MCP:** doubles as MCP server at `/mcp` (model introspection, provider health, routing). **Tool execution:** OpenAI-style tool round-trip across providers. `[EXTERNAL REPOSITORY]`
- **Model/API (critical):** Code MIT, "free forever"; **free = third-party provider free tiers, not Anthropic**. 29 free providers + custom endpoints; 6 smart routing strategies; failover on 429/5xx; "no frontier models, variable latency, no SLA." `[EXTERNAL REPOSITORY]`
- **Security:** provider keys AES-256-GCM encrypted in SQLite; local-first, single-user. **Dependencies:** Node 20+, Docker. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Provider-abstraction layer behind `mcp_manager`; `/mcp` for model-health routing; cost-free dev/test access. `[INFERENCE]`
- **Overlap:** AI-OS MCP + model-routing concerns (complementary layer). **Risks:** no SLA/no frontier → not production-grade; external free accounts needed.
- **Recommended status:** **INTEGRATION**.

### 9. Free Claude Code
- **URL:** github.com/alishahryar1/free-claude-code · **Local copy:** No · ~47.7k stars
- **Primary purpose:** Proxy/launcher unifying ~49 model providers behind one catalog with fallback, so coding agents run via free/cheap tiers. `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Terminal-output token reduction (~90%); voice input; streaming; images; "thinking" preserved; 9 external agents runnable (Claude Code, Codex, Pi, OpenCode, Cline, Hermes, DeepSeek, Grok, Muse). `[EXTERNAL REPOSITORY]`
- **Model/API (critical):** MIT; **"Independent open-source project. Not affiliated with or endorsed by Anthropic."** Free = 49 ToS-friendly provider free tiers; multi-provider billing risk on failure. `[EXTERNAL REPOSITORY]`
- **Security:** absolute "Allowed Directory" restriction; optional proxy bearer auth; no true sandbox. **Dependencies:** Python 3.14 (bleeding-edge). **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Moderate; reference pattern for multi-provider fallback; could host AI-OS agents or inform AI-OS routing. `[INFERENCE]`
- **Overlap:** provider abstraction + fallback (different altitude). **Risks:** name misleading (no free Claude/Anthropic); multi-provider billing leak; Python 3.14.
- **Recommended status:** **OPTIONAL**.

### 10. Graphify
- **URL:** github.com/Graphify-Labs/graphify · **Local copy:** No · default branch `v8`, pushed 2026-08-20
- **Primary purpose:** "Turn any codebase + docs + SQL + configs + PDFs into a queryable knowledge graph… local deterministic AST parsing, every edge explained, no vector store." `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Local tree-sitter AST across ~40 languages (no LLM); edges tagged `EXTRACTED`/`INFERRED`; `query`/`path`/`explain`/`reflect`/god-node/community detection (Leiden). `[EXTERNAL REPOSITORY]`
- **MCP:** stdio + HTTP server with `query_graph`/`get_node`/`get_neighbors`/`shortest_path`. **Skill:** `/graphify` slash skill for Claude Code/Cursor/Codex/Gemini. **Memory/Learning:** `reflect`+`save-result` work-memory overlay. `[EXTERNAL REPOSITORY]`
- **Model/API:** model-agnostic summarization (gemini/kimi/claude/openai/deepseek/ollama/bedrock); parsing needs no model. **Hooks:** PreToolUse nudges graph-query before raw source read. `[EXTERNAL REPOSITORY]`
- **Security:** local-first, no telemetry; `INFERRED` edges are transparency, not isolation. **Persistence:** `graphify-out/` + `~/.graphify/`. **Dependencies:** Python 3.10+, tree-sitter. **License:** Apache-2.0 (dual Apache/MIT noted). `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** MCP knowledge-graph provider feeding planning/root-cause; could seed AI-OS knowledge-graph memory tier. `[INFERENCE]`
- **Overlap:** partial with `memory.py` + `root_cause.py`; AI-OS has no built-in AST graph → complementary. **Risks:** `INFERRED` edges non-deterministic; `v8` fast-moving; model config needed to avoid egress.
- **Recommended status:** **INTEGRATION**.

### 11. Vercel Skills
- **URL:** github.com/vercel-labs/skills · **Local copy:** No · ~29.5k stars
- **Primary purpose:** CLI for the open agent-skills ecosystem (`npx skills`), supporting OpenCode/Claude Code/Codex/Cursor/73+ agents. `[EXTERNAL REPOSITORY]`
- **Skill definition:** reusable instruction sets in `SKILL.md` with YAML `name`+`description` frontmatter; cross-agent compatible via agentskills.io spec. `[EXTERNAL REPOSITORY]`
- **Core capabilities:** `add`/`use`/`list`/`find`/`remove`/`update`/`init`; marketplace discovery via `.claude-plugin/marketplace.json`; `allowed-tools` gate; `Hooks` inside skills. `[EXTERNAL REPOSITORY]`
- **Model/API:** GitHub/GitLab/git auth, `GITHUB_TOKEN`. **Security:** download cap 10 MiB; trust-on-install (no runtime sandbox). **Persistence:** symlink/copy install. **Dependencies:** Node/npx. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** De-facto cross-agent `SKILL.md` spec; AI-OS `SkillService`/`SkillManager` should align its `Skill` model to it for portability. `[INFERENCE]`
- **Overlap:** direct with `services/skill.py` (registry/load/execute/marketplace) — complementary if spec aligned. **Risks:** trust-on-install attack surface; spec governance external.
- **Recommended status:** **INTEGRATION** (spec adoption).

### 12. Superpowers
- **URL:** github.com/obra/superpowers · **Local copy:** No · ~276.5k stars
- **Primary purpose:** "Agentic skills framework & software development methodology" — composable skills that auto-trigger as mandatory workflows. `[EXTERNAL REPOSITORY]`
- **Core capabilities (skills):** brainstorming, git-worktrees, writing-plans, subagent-dev, TDD (RED-GREEN-REFACTOR), code-review, branch-finishing, debugging, collaboration, writing-skills. `[EXTERNAL REPOSITORY]`
- **Agent/Planning:** subagent-driven dev with two-stage review (spec + quality); explicit planning workflow. **Skill:** core unit (same `SKILL.md` style). **MCP/Council/Learning/Memory:** none. `[EXTERNAL REPOSITORY]`
- **Hooks:** session-start/post-compaction inject bootstrap; `.claude-plugin`/`.codex-plugin` hosts. **Eval:** "drill eval harness." **Security:** git worktree isolation; trust-on-install. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Methodology reference for `planning.py`/`council.py`/`skill.py` (mandatory triggers, two-stage review, TDD plans). `[INFERENCE]`
- **Overlap:** conceptual with planning/council/skill services; no runtime. **Risks:** pure prompt-methodology, host-dependent; porting "mandatory" triggers into event-driven kernel = re-implementation.
- **Recommended status:** **REFERENCE**.

### 13. Caveman
- **URL:** github.com/juliusbrussee/caveman · **Local copy:** No · ~100.5k stars, pushed 2026-08-23
- **Primary purpose:** Token-reduction layer for AI coding agents ("few token do trick") — compresses agent replies (~65%) + tool/input tokens (~33%). `[EXTERNAL REPOSITORY]`
- **Core capabilities:** skill rewriting replies in compressed dialect; proxy shrinking reads/tool output; CLI `learn`/`explore`/`shrink`/`browse`/`mem`/`trial`/`toon`/`stats`; modes lite/full/ultra/wenyan. `[EXTERNAL REPOSITORY]`
- **MCP:** MCP server (compress, retrieve, stats, toon encode/decode). **Learning:** `caveman learn` ranks token sinks. **Memory:** durable SQLite (CCR). **Model/API:** Anthropic/OpenAI/Google via baseURL swap. **License:** MIT (skill/CLI) + **BSL-1.1** (engine — source-available, not permissive). `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Apply compression to event payloads/agent replies/tool output (memory + council services generate large payloads). `[INFERENCE]`
- **Overlap:** partial with memory persistence (SQLite) + MCP surface. **Risks:** BSL-1.1 engine restricts deep embedding; dialect may degrade structured output; proxy network hop.
- **Recommended status:** **OPTIONAL** (token-optimization adapter; review BSL-1.1 before embedding engine).

### 14. Everything Claude Code (ECC)
- **URL:** github.com/affaan-m/ECC (supplied `everything-claude-code` redirects here) · **Local copy:** No · ~242.4k stars
- **Primary purpose:** "Agent harness performance optimization system" — installable coordinated engineering toolkit (68 agents, 286 skills, 94 commands, hooks, rules, memory). `[EXTERNAL REPOSITORY]`
- **Core capabilities:** Planning, TDD, fresh-context code review, build repair, security auditing, doc generation, continuous learning. `[EXTERNAL REPOSITORY]`
- **Agents/Planning:** `planner`, `architect`, `code-reviewer`, `security-reviewer`, `orch-*` orchestrators; `/ecc:plan` + Plan Canvas. **Learning:** instinct extraction w/ confidence (`continuous-learning-v2`). **Memory:** "Unified Memory Vault" (`.ecc/memory/`). **Council:** multi-agent `/multi-*`, `orch-*`. **MCP:** `chrome-devtools` default + `ecc-memory-mcp` stdio. `[EXTERNAL REPOSITORY]`
- **Model/API:** Claude Code (best), Codex/Cursor/OpenCode/Gemini/Zed/Kimi/Qwen; self-hosted via gateway. **Security:** AgentShield scans prompts/hooks/MCP/permissions/secrets. **License:** MIT. `[EXTERNAL REPOSITORY]`
- **AI-OS relevance:** Closest conceptual cousin to AI-OS (agents↔services, orchestrators↔council_manager, memory vault↔memory core, instincts↔learning) — but harness config, not a kernel. `[INFERENCE]`
- **Overlap:** high conceptual (different layer: declarative harness config vs runtime kernel). **Risks:** harness-coupled; pattern translation needed; rapid churn.
- **Recommended status:** **REFERENCE**.

### 15. Instagram p/DaNYCILlDgO
- **Status:** **UNVERIFIED** — login wall, could not inspect. Not guessed. `[EXTERNAL REPOSITORY]`

---

## PART 5 — CAPABILITY EXTRACTION (MATRIX → see separate file)

Full capability matrix is delivered in **`FULL_AI_OS_CAPABILITY_MATRIX.md`**.

Summary of determinations across AI-OS + Hermes + ecosystem:

| Capability | AI-OS | External source | Status |
|---|---|---|---|
| PLANNING | ✅ (planning service, Part 10) | Superpowers/ECC (methodology) | Implemented + Reference patterns |
| COUNCILS | ✅ (CouncilManager, 9 councils) | Ruflo/MOA (swarm) | Implemented; external REFERENCE only |
| MULTI-AGENT | ✅ (AI Agency, 9 agents) | Hermes (delegation), Ruflo | Implemented + Integration/Reference |
| EXECUTION | ✅ (kernel, WorkflowManager) | Hermes (conversation_loop), Loop Eng | Implemented + Reference |
| CLOSED LOOP / FAILURE RECOVERY | ✅ (root_cause, retry, learning, tests) | Loop Engineering | Implemented; external lighter |
| LEARNING | ✅ (learning service) | Hermes (skills/memory), ECC (instincts) | Implemented + Integration/Reference |
| MEMORY | ✅ (5-tier) | Hermes (SQLite), Graphify | Implemented + Integration |
| SKILLS | ✅ (SkillService) | agency-agents, Vercel, Book-to-Skill, Superpowers | Implemented + Integration/Reference |
| MCP | ✅ (mcp_manager) | Agent-Reach, Graphify, FreeLLMAPI, SkillSpecTor, Hermes | Implemented + Integration |
| MODEL ROUTING | Partial (Part 10 AI Runtime) | FreeLLMAPI, Free Claude Code, Hermes transports | Partial + Integration/Optional |
| SUBAGENTS | ✅ (AI Agency) | Hermes (delegate_task) | Implemented + Integration |
| PROMPT ENGINEERING | Implicit | Prompt Eng Hub | Reference only |
| EVALUATION | ✅ (validation architecture, 11 layers) | SkillSpecTor (security), ECC AgentShield | Implemented + Integration |
| OBSERVABILITY | ✅ (ObservabilityManager, Part 9) | Hermes (monitoring/OTLP) | Implemented + Reference |
| SECURITY | ✅ (SecurityManager) | SkillSpecTor, AgentShield, Hermes estop | Implemented + Integration/Reference |
| SANDBOXING | Partial (agent quotas) | Loop Eng (worktree), SkillSpecTor (static only) | Partial + Reference |
| PERSISTENCE | ✅ (StorageManager) | Hermes (SQLite-WAL/FTS5) | Implemented + Reference |
| KNOWLEDGE GRAPH | ❌ (no AST graph) | Graphify | **Missing → Integration** |
| TOKEN COMPRESSION | ❌ (not explicit) | Caveman | **Missing → Optional** |
| WEB/SOCIAL ACCESS | ❌ | Agent-Reach | **Missing → Integration** |

---

## PART 6 — AI-OS ARCHITECTURE MAPPING

| AI-OS Layer | Existing Implementation | External Resource | Status | Notes |
|---|---|---|---|---|
| Planning | planning service (Part 10) | Superpowers, ECC | Implemented | Adopt methodology patterns |
| Councils / Decision | CouncilManager + 9 councils (COUNCILS.md) | Ruflo swarm, Hermes MOA | Implemented | External REFERENCE only |
| Agency | 9 specialized agents (AI_AGENCY.md) | Hermes (delegate_task), agency-agents personas | Implemented | Hermes = worker engine; agency-agents = skill content |
| Learning | learning service | Hermes skills/memory, ECC instincts | Implemented | Hermes self-improvement integrable |
| Memory | 5-tier (MEMORY_ARCHITECTURE.md) | Hermes SQLite, Graphify, Obsidian | Implemented | Graphify adds AST graph tier |
| Skills | SkillService (services/skill.py) | Vercel Skills spec, Book-to-Skill, agency-agents, Superpowers | Implemented | Align to SKILL.md standard |
| Execution | kernel + WorkflowManager | Hermes conversation_loop, Loop Eng | Implemented | AI-OS owns deeper closed loop |
| Verification | 11-layer validation (VALIDATION_ARCHITECTURE.md) | SkillSpecTor, ECC AgentShield | Implemented | SkillSpecTor = skill/MCP gate |
| Failure Recovery | root_cause, retry (src/aios/core/) | Loop Eng gate/sandbox | Implemented | Verified closed loop |
| MCP | mcp_manager (services/mcp.py) | Agent-Reach, Graphify, FreeLLMAPI, SkillSpecTor, Hermes mcp_serve | Implemented | Multiple Integration providers |
| Model Layer | Part 10 AI Runtime | FreeLLMAPI, Free Claude Code, Hermes transports | Partial | Provider abstraction gap |
| Tool Layer | capability facades (Part 6) | Agent-Reach, Hermes tools | Implemented | — |
| Event Architecture | EventBus (Part 2/3) | — | Implemented | Core; no external needed |
| Core Managers | 9 managers (Part 4) | Ruflo (competitor) | Implemented | Do not adopt Ruflo as core |
| Governance | Part 13 + 9 councils | ECC orchestrators | Implemented | — |
| Security | SecurityManager | SkillSpecTor, AgentShield, Hermes estop | Implemented | SkillSpecTor INTEGRATION gate |
| Observability | ObservabilityManager (Part 9) | Hermes monitoring/OTLP | Implemented | — |
| Knowledge Mgmt | Engineering Intelligence tier | Graphify (AST graph) | Partial | **Graphify fills gap** |
| Developer Env | CLI (Part 8) | ECC, Superpowers, agency-agents | Implemented | Dev-tooling, not runtime |
| UI / CLI | Part 8 CLI | Hermes TUI/web gateway | Implemented | Separate products |

---

## PART 7 — THE COUNCIL SYSTEM

**What AI-OS specifies** `[AI-OS SOURCE]` `[DOCUMENTATION]`:
- 9 governance councils (Architecture Review Board, Engineering, AI Governance, Security, Runtime, Validation, Release, Ethics, Future Research) — `COUNCILS.md`, Part 13.
- Consensus algorithms: MAJORITY, UNANIMOUS, WEIGHTED, RANKED_CHOICE, CONSENT.
- `CouncilManager` is implemented as a core manager (`src/aios/core/council_manager.py` present and modified in working tree — code exists; behavior verified under V1 baseline).
- Decision synthesis, independent review, confidence, verification are first-class concepts in the validation architecture (11 layers, L1–L4 conformance).

**Is it implemented?** Yes — CouncilManager + council specs exist in code and docs; V1 baseline verified. `[AI-OS SOURCE]`

**External council providers?**
- Ruflo "multi-player swarms" — competitor agent OS, not a clean council service. REFERENCE only.
- Hermes `moa_loop.py` (Mixture-of-Agents) — a *reasoning* pattern (multiple model opinions synthesized), not a governance council. Could inform AI-OS council synthesis as a reference, but is model-level, not governance-level. `[LOCAL REPOSITORY]`
- ECC `orch-*` orchestrators — harness config, REFERENCE.
- **No external repository provides a drop-in governance Council system matching AI-OS's 9-council spec.**

**Most suitable external?** None are purpose-built for AI-OS councils. Hermes MOA is the closest *synthesis* analogue (multi-perspective reasoning) and is INTEGRATION-grade as an execution engine, but it does not replace the governance council layer. `[INFERENCE]`

**Should multiple council systems coexist?** No — keep ONE governance council layer (CouncilManager). Use Hermes MOA only as an *internal reasoning technique* inside council synthesis if desired, not as a parallel system. `[INFERENCE]`

**Separate agents or a service?** AI-OS already models councils as a *service* (CouncilManager) coordinating specialized agents. Keep that. External "agents" (agency-agents personas, Hermes workers) are *inputs/executors*, not the council authority. `[INFERENCE]`

**Interaction with the closed loop:** Councils participate **both before and after execution** — pre-execution (architecture/security/release gates, plan validation) and post-execution (validation council, FinalJudge arbitration, learning review). This is already specified; no change needed. `[DOCUMENTATION]`

**What is missing:** A canonical *implementation* of council synthesis using multi-model/multi-agent perspectives (Hermes MOA is a candidate technique). SkillSpecTor-style adversarial review could strengthen the Security Council's pre-install gate. `[INFERENCE]`

> Do NOT design a new Council architecture — reconcile only. AI-OS's council architecture is complete and verified; external systems are REFERENCE/INTEGRATION inputs, not replacements.

---

## PART 8 — HERMES (MAPPING)

Hermes (`C:\Development\AI-OS\hermes-agent`, v2026.8.13) is a **standalone mature autonomous-agent product**, not the AI-OS Hermes Kernel. Mapping by evidence:

| Hermes capability | AI-OS requirement | Architectural layer | Integration point | Dependency | Conflict/overlap |
|---|---|---|---|---|---|
| Multi-provider model routing (`transports/`) | Model abstraction (Part 10) | Model Layer | `mcp_manager` / AI Runtime | provider keys | Overlaps AI Runtime model concern |
| Autonomous runtime (`conversation_loop.py`) | Agent execution | Agency / Execution | drive as AI-OS worker | Hermes process | Overlaps AI Agency agents |
| Delegation (`delegate_task`) | Subagents | Agency | spawn Hermes workers | git-worktree | Overlaps AI Agency |
| Memory (SQLite-WAL/FTS5) | 5-tier memory | Memory | memory tier / MCP | SQLite | Overlaps MemoryManager |
| Skills/memory self-improvement | Learning/Skills | Learning/Skills | SkillService import | — | Complements learning |
| MOA (`moa_loop.py`) | Multi-perspective synthesis | Councils/Reasoning | council synthesis technique | — | Reference only |
| MCP serve (`mcp_serve.py`) | MCP | MCP | mcp_manager | — | Complements |
| ACP (`acp_adapter/`) | Agent protocol | Integration | external agent bridge | — | New interface |
| Estop (`estop.py`) | Safety | Security | safety gate | — | Complements |
| Gateway/TUI/web | UI | UI/CLI | separate product | — | No core need |

**Recommended Hermes role:** `INTEGRATION` as an **external autonomous-agent runtime / model-interface engine** that AI-OS can drive (via MCP or ACP) to execute agency tasks and provide multi-provider model routing; plus `REFERENCE` for agent-runtime, delegation, MOA, context-compression, and model-routing patterns. **Not CORE** — AI-OS retains its own kernel, councils, validation, and closed loop.

---

## PART 9 — AI-AGENCY ECOSYSTEM

Treated as a possible ecosystem, not a package `[INFERENCE]`:

| Repo | Provides | AI-OS treatment |
|---|---|---|
| agency-agents | 230+ persona/skill `.md` | INTEGRATION (skill content) |
| Hermes | full agent runtime + delegation | INTEGRATION (worker engine) / REFERENCE |
| Ruflo | agent meta-harness (competitor) | REFERENCE (architecture) |
| ECC | 68 agents/286 skills harness toolkit | REFERENCE (patterns) |
| Superpowers | composable skill methodology | REFERENCE (methodology) |
| Agent-Reach | web/social tool | INTEGRATION (MCP) |
| Loop Engineering | loop patterns | REFERENCE |
| FreeLLMAPI / Free Claude Code | model routing | INTEGRATION / OPTIONAL |
| Vercel Skills / Book-to-Skill | skill authoring/spec | INTEGRATION (spec) |
| Graphify | knowledge graph | INTEGRATION (MCP) |
| SkillSpecTor | skill/MCP security | INTEGRATION (gate) |
| Caveman | token compression | OPTIONAL |
| Prompt Eng Hub | prompt patterns | REFERENCE |
| Instagram | unknown | UNVERIFIED |

None should be force-combined into one "agency package." AI-OS's own 9-agent AI Agency (`AI_AGENCY.md`) is the canonical agency layer; external repos feed it as content (agency-agents), engines (Hermes), tools (Agent-Reach), or references (Ruflo/ECC/Superpowers).

---

## PART 10 — PLANNING / ORGANIZATION TOOLS

**Obsidian & Graphify** — primarily planning/organization/knowledge-structuring.

- **Obsidian:** listed in AI-OS 5-tier memory as the "Structured knowledge base, markdown vault" tier (`MEMORY_ARCHITECTURE.md`). It is a **personal knowledge-management (PKM) tool**, developer/planning infrastructure, **NOT an AI-OS runtime component**. `[AI-OS SOURCE]` `[DOCUMENTATION]`
- **Graphify:** a code/knowledge **graph generator** exposing an MCP server. Unlike Obsidian, Graphify is **runtime-relevant** — it can be mounted as an MCP server feeding AI-OS planning/root-cause a queryable AST graph. `[EXTERNAL REPOSITORY]`

**Verdict:** Obsidian = **OUTSIDE AI-OS** (development/planning infrastructure; dev-tool only). Graphify = **INSIDE AI-OS runtime** as an optional MCP knowledge-graph provider (INTEGRATION). Do not automatically treat every useful developer tool as a runtime component — Obsidian is the counterexample. `[INFERENCE]`

---

## PART 11 — FREE MODEL / EXECUTION INFRASTRUCTURE

- **FreeLLMAPI:** MIT proxy; "free" = ~29 third-party provider free tiers (~4B tokens/month), NOT Anthropic. OpenAI-compatible + Anthropic wire + Gemini + Ollama + MCP server. No frontier models, no SLA, variable latency. AES-256-GCM key storage. → **INTEGRATION** (dev/test model layer; provider abstraction). `[EXTERNAL REPOSITORY]`
- **Free Claude Code:** MIT launcher; **explicitly unaffiliated with Anthropic**; "free" = 49 ToS-friendly provider tiers; multi-provider billing-leak risk on failure; Python 3.14. → **OPTIONAL** (reference pattern / downstream host). `[EXTERNAL REPOSITORY]`
- **NVIDIA model access:** SkillSpecTor runs on NVIDIA infra but is a scanner, not a model provider. No dedicated NVIDIA model-routing repo provided. `[INFERENCE]`
- **Runtime vs dev:** Both are **runtime infrastructure** (local proxy servers agents connect to) requiring external API keys/accounts — not build-time dev tools. They are INTEGRATION/OPTIONAL, not REQUIRED. `[INFERENCE]`
- **Do NOT configure or install anything** (task rule). Findings only.

---

## PART 12 — SKILLS ECOSYSTEM

**What is a "skill" in each system?**

| System | Skill definition | Compatible? |
|---|---|---|
| AI-OS SkillService | Registry/load/execute/marketplace of skills (`services/skill.py`) | internal model |
| Vercel Skills | `SKILL.md` + YAML frontmatter (`name`,`description`,`allowed-tools`,`Hooks`); agentskills.io spec | **de-facto standard** |
| Book-to-Skill | `SKILL.md` + chapter/glossary/patterns (open Agent Skills standard) | aligns to Vercel spec |
| agency-agents | persona/role `.md` (process + deliverables) | persona-style, importable as content |
| Superpowers | composable `SKILL.md`-style skills, mandatory triggers | aligns to Vercel spec |
| Hermes | agent-authored skills over SQLite | internal |
| Caveman | compression skill (Claude Code skill) | Claude Code skill format |
| ECC | 286 skills (primary workflow surface) | Claude Code skill format |

**Format compatibility:** Vercel Skills / Book-to-Skill / Superpowers / Caveman / ECC all converge on the **`SKILL.md` open Agent Skills standard**. AI-OS `SkillService` should align its `Skill` model to that frontmatter so skills are importable/exportable across 73+ agents. `[INFERENCE]`

**Which can be imported/adapted:** agency-agents (personas), Vercel marketplace skills, Book-to-Skill outputs, Superpowers skills — all via the `SKILL.md` standard. `[INFERENCE]`

**Developer-only:** agency-agents, Book-to-Skill, Superpowers, Caveman, ECC all target Claude Code/harness — they are authoring/reference, not AI-OS runtime skills until bridged. `[INFERENCE]`

**Can become AI-OS capabilities:** via SkillService import + SecurityManager gate (SkillSpecTor). `[INFERENCE]`

**Overlap:** all overlap AI-OS SkillService at the *file-format* level; no external repo replaces the runtime. `[INFERENCE]`

**Canonical format needed?** Yes — AI-OS should adopt the **open `SKILL.md` standard** as its canonical skill format (Vercel Skills is the de-facto reference). Do NOT design a new one yet (task rule). `[INFERENCE]`

---

## PART 13 — LOOP ENGINEERING

- Loop Engineering implements a closed loop: schedule→triage→state→worktree→implement→verify→MCP→human gate→commit→repeat (code + 7 patterns). `[EXTERNAL REPOSITORY]`
- **Overlap with M3 (AI-OS closed loop):** direct — AI-OS has kernel lifecycle, WorkflowManager, root_cause, retry, learning, failure recovery (`tests/integration/test_closed_loop.py`, `test_failure_recovery.py`). `[AI-OS SOURCE]` `[INFERENCE]`
- **Does it improve the current loop?** Partially — its `gate`/`sandbox`/`worktree` primitives and "Loop Ready" scoring are useful pattern checks, but AI-OS already owns deeper coverage (root cause, retry, learning). `[INFERENCE]`
- **Should it replace anything?** No. Part 15's closed loop is verified; do not recommend replacement without concrete evidence. Loop Engineering = **REFERENCE** for pattern cross-check and candidate primitives. `[AI-OS SOURCE]` (V1 verified)

---

## PART 14 — OVERLAP / DUPLICATION ANALYSIS

| Capability | Option A | Option B | Option C | AI-OS choice | Reason |
|---|---|---|---|---|---|
| Agent OS / kernel | AI-OS kernel | Ruflo | Hermes | **AI-OS kernel** | Ruflo competes; Hermes is worker engine, not kernel |
| Skill format | AI-OS internal | Vercel `SKILL.md` | — | **Adopt Vercel `SKILL.md`** | De-facto cross-agent standard; portability |
| Skill content | AI-OS authored | agency-agents | Superpowers | **Import both via spec** | Complementary content sources |
| Memory store | AI-OS 5-tier | Hermes SQLite | Graphify | **AI-OS 5-tier + Graphify MCP** | Graphify adds AST graph; Hermes is separate runtime |
| Model routing | AI-OS Part 10 | FreeLLMAPI | Free Claude Code | **FreeLLMAPI (INTEGRATION)** | Richer (MCP, encryption, analytics); FreeCC unaffiliated + billing risk |
| Web/social tool | none | Agent-Reach | — | **Agent-Reach (INTEGRATION)** | Only candidate; narrow, free |
| Knowledge graph | none | Graphify | Obsidian | **Graphify (MCP)** | Obsidian is dev PKM, not runtime |
| Security gate | AI-OS SecurityManager | SkillSpecTor | ECC AgentShield | **SecurityManager + SkillSpecTor gate** | SkillSpecTor purpose-built for skill/MCP vetting |
| Council synthesis | CouncilManager | Hermes MOA | Ruflo swarm | **CouncilManager (+MOA technique ref)** | Governance is AI-OS-owned; MOA is reasoning technique |
| Token compression | none | Caveman | — | **Caveman (OPTIONAL)** | Nice-to-have; BSL-1.1 engine caveat |
| Loop framework | AI-OS closed loop | Loop Engineering | — | **AI-OS closed loop** | Verified; Loop Eng is REFERENCE |

**Objective:** avoid a Frankenstein system — ONE kernel (AI-OS), ONE council layer (CouncilManager), ONE skill format (`SKILL.md`), ONE model-routing path (FreeLLMAPI behind mcp_manager). External repos feed as INTEGRATION inputs or REFERENCE, never as parallel cores.

---

## PART 15 — TRUST / RISK ANALYSIS

| Dependency | License | Maint. | Security | Supply-chain | Network | Code-exec | Creds | Sandbox | Privacy | Provider-dep | Lock-in | Overall |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hermes (local) | MIT-style* | High | Med | Med | Yes | Yes | Yes | Partial (estop) | Local SQLite | Multi | Low | **MEDIUM** |
| agency-agents | MIT | High-vis | Low | Low | No | No (files) | No | No | Local | No | Low | **LOW** |
| Ruflo | MIT | Uncertain | Med | Med | Yes | Yes | Yes | WASM | Mongo | Yes | Med | **MEDIUM** |
| Agent-Reach | MIT | High-vis | Med | Low | Yes | Via shell | Local cfg | No | Local creds | Free tiers | Low | **MEDIUM** |
| Book-to-Skill | MIT | Uncertain | Low | Low | No | Local | No | No | Local | No | Low | **LOW** |
| SkillSpecTor | Apache-2.0 | High (NVIDIA) | High | Low | Optional LLM | Static only | No | No (not sandbox) | LLM stage egress | Opt | Low | **MEDIUM** |
| Loop Engineering | MIT | Active | Med | Low | Yes | Yes | No | worktree | Local | No | Low | **LOW** |
| Prompt Eng Hub | Apache-2.0 | Low | High | None | No | No | No | No | None | No | None | **LOW** |
| FreeLLMAPI | MIT | High | Med | Med | Yes | Via proxy | AES-256-GCM | No | Encrypted keys | 29 free tiers | Med | **MEDIUM** |
| Free Claude Code | MIT | High | Low | Med | Yes | Via wrapped agent | Local cfg | Dir-only | Local | 49 tiers | Med | **MEDIUM** |
| Graphify | Apache-2.0 | High | High | Low | Local (model opt) | Local parse | No | No | Local-first | Opt model | Low | **LOW** |
| Vercel Skills | MIT | High | Med | Med | Yes (git) | Trust-on-install | GH token | No | Repo public | GitHub | Low | **MEDIUM** |
| Superpowers | MIT | High-vis | Med | Low | No | Trust-on-install | No | worktree | Local | No | Low | **LOW** |
| Caveman | MIT + **BSL-1.1** | High | Med | Med | Yes (proxy) | Yes | No | Local | Local SQLite | Multi | Low | **MEDIUM** (engine license risk) |
| ECC | MIT | High | Med | Low | Yes | Via hooks | Local | No | Local vault | Multi | Low | **LOW** |

\*Hermes `LICENSE` text not read verbatim in this pass — confirm before integration. `[LOCAL REPOSITORY]`

Key risks:
- **Caveman BSL-1.1 engine** — source-available, restricts deep embedding of the compression engine (MIT covers skill/CLI only).
- **SkillSpecTor / FreeLLMAPI LLM stages** — send content to external providers; disable or self-host within AI-OS trust boundary.
- **Free Claude Code** — unaffiliated with Anthropic; multi-provider billing-leak on failure.
- **agency-agents / Vercel / Superpowers trust-on-install** — imported skills are an execution attack surface; gate via SecurityManager + SkillSpecTor.
- **Star counts** across several repos are implausibly high for 2026-created repos — treat as marketing visibility, not validated popularity.

---

## PART 16 — WHAT IS ACTUALLY REQUIRED?

### REQUIRED FOR AI-OS (architecture mandates)
Hermes Kernel (EventBus/ServiceRegistry/Config/Logger), 9 Core Managers, 9 Councils (CouncilManager), 9 AI Agency agents, 5-tier Memory, Skills ecosystem, MCP ecosystem, 11-layer Validation, closed-loop execution w/ failure recovery, Observability, Security. All present in V1 baseline. `[AI-OS SOURCE]`

### ALREADY SATISFIED (implemented in V1)
Event architecture, kernel lifecycle, 9 core managers, councils, agency, planning, skills registry, MCP manager, validation, observability, closed loop + failure recovery (root_cause/retry/learning), security manager. `[AI-OS SOURCE]`

### EXTERNAL CAPABILITIES TO INTEGRATE (useful, from existing repos)
- **SkillSpecTor** — skill/MCP security vetting gate (SecurityManager).
- **Vercel Skills `SKILL.md` spec** — canonical skill format adoption.
- **Graphify** — MCP knowledge-graph provider (memory/root-cause).
- **Agent-Reach** — MCP web/social ingestion.
- **FreeLLMAPI** — model-routing/provider abstraction (dev/test + fallback).
- **Hermes** — external autonomous-agent runtime / model-interface engine.
- **agency-agents** — skill/persona content import.

### OPTIONAL / EXPERIMENTAL (not core yet)
- **Caveman** — token compression (BSL-1.1 engine caveat).
- **Free Claude Code** — provider-fallback launcher (unaffiliated, billing risk).
- **Book-to-Skill** — offline skill authoring (REFERENCE-grade but useful).
- **Loop Engineering** — loop primitives (REFERENCE).

### NOT NEEDED (do not integrate)
- **Ruflo** — competes with AI-OS kernel; REFERENCE only.
- **Instagram p/DaNYCILlDgO** — UNVERIFIED, no evidence of relevance.
- Multiple parallel kernels / council layers / skill formats / model routers — explicitly rejected (Frankenstein risk).

---

## PART 17 — FULL SYSTEM ARCHITECTURE (VERIFIED)

```
                         USER / GOAL
                              │
                              ▼
                    AI-OS ENTRY (CLI, Part 8)
                              │
                              ▼
                    PLANNING (planning service, Part 10)
                              │
                              ▼
              COUNCILS / REVIEW (CouncilManager + 9 councils)  ◄── Hermes MOA (technique ref)
                              │                                        Ruflo/ECC (REFERENCE only)
                              ▼
                   CAPABILITY SELECT (CapabilityManager)
                              │
                              ▼
                      SKILL LAYER (SkillService)
                       │  adopts Vercel SKILL.md spec
                       │  imports: agency-agents, Book-to-Skill, Superpowers
                       │  gates:    SkillSpecTor ──────────────┐
                       ▼                                        │
                    MCP / TOOLS (mcp_manager)                   │
          ┌────────────┬─────────────┬──────────┐              │
       Agent-Reach  Graphify(MCP)  FreeLLMAPI  Hermes(mcp_serve)│
       (web/social) (know-graph)  (model route) (agent runtime)│
                              │                                  │
                              ▼                                  │
                    EXECUTION (kernel + WorkflowManager)        │
              agency agents ── Hermes workers (delegate_task) ──┘
                              │
                              ▼
                 VERIFICATION (11-layer validation)
                  /          \
               PASS          FAIL
                │              │
               DONE          RCA (root_cause)
                            │
                      LEARNING (learning service)
                            │  ◄── Hermes skills/memory self-improvement (ref)
                            ▼
                         MEMORY (5-tier; Graphify AST graph tier)
                            │
                          REPLAN
                            │
                            └──────► EXECUTION
```

**Tiering:**
- **AI-OS CORE:** Kernel, Core Managers, Councils, Agency, Planning, Skills registry, MCP manager, Validation, Observability, Security, closed loop, Memory.
- **AI-OS RUNTIME INTEGRATIONS:** SkillSpecTor (gate), Graphify (MCP), Agent-Reach (MCP), FreeLLMAPI (model route), Hermes (agent runtime via MCP/ACP).
- **DEVELOPMENT TOOLS (outside runtime):** Obsidian (PKM), agency-agents authoring, Book-to-Skill, Superpowers, ECC, Loop Engineering, Prompt Eng Hub, Caveman (optional), Free Claude Code (optional).
- **EXTERNAL SERVICES:** 29/49 provider free tiers (FreeLLMAPI/FreeCC), NVIDIA (SkillSpecTor infra).
- **OPTIONAL COMPONENTS:** Caveman, Free Claude Code.

---

## PART 18 — V1 → V2 GAP ANALYSIS (→ see separate file)

Full gap table delivered in **`FULL_AI_OS_V1_V2_GAP_ANALYSIS.md`**.

Headline gaps (capability missing or partial in V1):
- Knowledge-graph memory tier (Graphify) — **P1**
- Canonical `SKILL.md` skill format + cross-agent marketplace (Vercel) — **P1**
- Skill/MCP security vetting gate (SkillSpecTor) — **P1**
- Provider-abstracted model layer (FreeLLMAPI) — **P2**
- Web/social tool access (Agent-Reach) — **P2**
- External autonomous-agent runtime bridge (Hermes via MCP/ACP) — **P2**
- Token compression (Caveman) — **P3**
- Council multi-perspective synthesis technique (Hermes MOA) — **P2 (technique)**

---

## PART 19 — NEXT DEVELOPMENT MILESTONES (→ see separate file)

Full milestone plan delivered in **`FULL_AI_OS_NEXT_MILESTONES.md`** (M4–M6, building on verified V1 baseline).

---

## PART 20 — DO NOT IMPLEMENT YET

This report is DISCOVERY ONLY. No install, copy, modify, integrate, symlink, config, package, test, or delete was performed. Output tells what we ACTUALLY HAVE before deciding what to build next.

---

## PART 21 — DELIVERABLES

- `architecture/FULL_AI_OS_ECOSYSTEM_RECONCILIATION.md` (this file)
- `architecture/FULL_AI_OS_CAPABILITY_MATRIX.md`
- `architecture/FULL_AI_OS_V1_V2_GAP_ANALYSIS.md`
- `architecture/FULL_AI_OS_NEXT_MILESTONES.md`

---

## FINAL REPORT — EXECUTIVE SUMMARY

1. **What is AI-OS today?** A verified V1 artificial-intelligence operating system: Hermes Kernel (EventBus/ServiceRegistry/Config/Logger + 9 Core Managers), 9 governance Councils, 9 specialized AI Agency agents, a 5-tier memory system, skills + MCP ecosystems, an 11-layer validation architecture, and a verified closed-loop execution model with failure recovery. `[AI-OS SOURCE]`
2. **What did Part 15 V1 complete?** The closed-loop execution foundation: M0–M3 milestones, 802/802 tests, 12/12 V1 gates, independent Terminal 3 QA passed; verdict "READY WITH NON-BLOCKING DEBT." `[AI-OS SOURCE]` (per task-asserted verified baseline)
3. **Where does Hermes fit?** `C:\Development\AI-OS\hermes-agent` (v2026.8.13) is a **separate mature autonomous-agent product** (multi-provider runtime, delegation, MOA, memory, MCP, ACP, estop) — NOT the AI-OS Hermes Kernel. Role: **INTEGRATION** as an external agent-runtime/model-interface engine behind AI-OS (via MCP/ACP) + **REFERENCE** for agent-runtime patterns. Never CORE. `[LOCAL REPOSITORY]`
4. **Where do Councils fit?** AI-OS already owns a complete, verified Council system (CouncilManager + 9 councils, 5 consensus algorithms). External "councils" (Ruflo swarm, Hermes MOA, ECC orchestrators) are REFERENCE only; Hermes MOA is a *reasoning technique* that may inform council synthesis, not a governance replacement. `[AI-OS SOURCE]`
5. **What is AI-agency?** AI-OS's own 9-agent specialized agency (`AI_AGENCY.md`) is canonical. External repos feed it: agency-agents (persona content), Hermes (worker engine), Agent-Reach (tools), Ruflo/ECC/Superpowers (REFERENCE). Not a single package. `[INFERENCE]`
6. **Which repos provide useful skills?** Vercel Skills (`SKILL.md` spec), Book-to-Skill (authoring), agency-agents (personas), Superpowers (methodology), Caveman/ECC (Claude Code skills). All converge on the open `SKILL.md` standard. `[EXTERNAL REPOSITORY]`
7. **Which are dev tools, not runtime?** Obsidian (PKM — explicitly OUTSIDE runtime), agency-agents, Book-to-Skill, Superpowers, ECC, Loop Engineering, Prompt Eng Hub, Caveman (optional), Free Claude Code (optional). `[INFERENCE]`
8. **Role of Graphify/Obsidian?** Obsidian = dev/planning PKM (outside runtime). Graphify = runtime MCP knowledge-graph provider (fills AI-OS's missing AST-graph memory tier). `[INFERENCE]`
9. **Role of MCP?** The integration backbone. AI-OS `mcp_manager` consumes external capabilities as MCP servers: Agent-Reach (web), Graphify (graph), FreeLLMAPI (models), SkillSpecTor (security), Hermes (agent runtime). `[AI-OS SOURCE]`
10. **What overlaps?** Agent-OS/kernel (Ruflo vs AI-OS), skill formats (many → consolidate to `SKILL.md`), memory stores (Hermes/Graphify vs AI-OS 5-tier), model routers (FreeLLMAPI/FreeCC), council layers (keep ONE). Avoid Frankenstein. `[INFERENCE]`
11. **What should NOT be integrated?** Ruflo (competitor kernel), Instagram (UNVERIFIED), any parallel kernel/council/skill-format/model-router. `[INFERENCE]`
12. **What is genuinely missing?** AST knowledge-graph memory tier, canonical cross-agent skill format, skill/MCP security vetting gate, provider-abstracted model layer, web/social tool access, external agent-runtime bridge, token compression. `[INFERENCE]`
13. **What should V2 build first?** (a) canonical `SKILL.md` skill format + SkillSpecTor security gate; (b) Graphify MCP knowledge-graph memory tier; (c) provider-abstracted model layer (FreeLLMAPI). See milestones M4–M6. `[INFERENCE]`
14. **What should remain optional?** Caveman (token compression), Free Claude Code (provider launcher). `[INFERENCE]`
15. **What should never be core?** Ruflo (kernel competitor), Instagram (unverified), any external kernel/council/council-synthesis replacement. `[INFERENCE]`
16. **Recommended complete architecture:** ONE AI-OS core (kernel/managers/councils/agency/planning/skills/MCP/validation/observability/security/closed-loop/memory) + targeted RUNTIME INTEGRATIONS (SkillSpecTor, Graphify, Agent-Reach, FreeLLMAPI, Hermes) consumed via MCP/ACP + DEV/REFERENCE tools kept outside runtime + OPTIONAL components (Caveman, FreeCC). No parallel cores.

---

*End of reconciliation. All conclusions tagged by evidence source. No implementation performed.*
