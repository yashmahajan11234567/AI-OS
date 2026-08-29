# REAL EXTERNAL INTEGRATIONS — READINESS REPORT

**AI-OS · Real External Integration Readiness + Connection Plan**
**Date:** 2026-08-27
**Author:** Terminal 2 (audit author) — NOT a self-certification
**Methodology:** Repository-grounded analysis only. **No external connections were made. No credentials fabricated. No production code or configuration was changed.** Every claim carries a `file:line` reference.
**Companion document:** `REAL_EXTERNAL_INTEGRATIONS_IMPLEMENTATION_PLAN.md`

---

## 0. THE ONE SENTENCE ANSWER

> **AI-OS is IMPLEMENTED and CONFIGURED for external integrations, but it is NOT CONNECTED and NOT OPERATIONALLY VERIFIED for any of the 8 selected integrations.** All 8 currently run against in-repo mock servers over stdio. Moving any integration to OPERATIONALLY VERIFIED requires a real credential, a real service/endpoint, or a real local binary — none of which are present in this repository.

`IMPLEMENTED`, `CONFIGURED`, `CONNECTED`, and `OPERATIONALLY VERIFIED` are **four distinct states that must not be conflated**. The table below is the spine of this report.

| Integration | IMPLEMENTED | CONFIGURED | CONNECTED | OPERATIONALLY VERIFIED |
|---|:--:|:--:|:--:|:--:|
| Notion | ✅ | ✅ (mock) | ❌ | ❌ |
| Obsidian | ✅ | ✅ (mock + real filesystem path) | ⚠️ (filesystem path works locally) | ❌ (no real vault configured) |
| FreeLLM API | ✅ (code only) | ⚠️ (not registered at boot) | ❌ | ❌ |
| Hermes / hermes-agent(EXT) | ✅ | ✅ (mock) | ❌ | ❌ |
| Graphify | ✅ | ✅ (mock) | ❌ | ❌ |
| Claude-Mem | ✅ | ✅ (mock) | ❌ | ❌ |
| Playwright | ✅ | ✅ (mock) | ❌ | ❌ |
| ACP | ✅ (code-complete, unconfigured) | ⚠️ (allowlisted only) | ❌ | ❌ |

---

## 1. SCOPE & BOUNDARIES HONORED

This audit did **not**:
- Modify production code or configuration.
- Claim an integration is operational without a verified real connection.
- Replace any real integration with a mock.
- Delete or weaken existing mock infrastructure (Tier A/B testing depends on it).
- Weaken, remove, or reinterpret any existing test.
- Start M13. (M7 frozen; M8/M9/M10/M11/M12 boundaries preserved.)
- Invent credentials, endpoints, repositories, packages, or services.
- Print or expose any secret value.

Terminal 2 does **not** self-certify. Terminal 3 remains the final QA / closure authority (per the standing operating rule).

---

## 2. REPOSITORY + ARCHITECTURE RECONCILIATION (PHASE 1)

### 2.1 How every integration is wired today

| Integration | Adapter (file:line) | Current Mode | Capability ID | Registration (file:line) | Current Endpoint/Command | Points at Mock? |
|---|---|---|---|---|---|---|
| Notion | `notion_adapter.py:101` | MCP stdio → mock | `notion_planning` | `kernel.py:1225` → reg `:1245` | `config/mcp/notion_mcp.json` → `python -m aios.adapters.mock_notion_server` | ✅ YES |
| Obsidian | `obsidian_adapter.py:130` | MCP stdio → mock **+ local filesystem fallback** | `obsidian_knowledge` | `kernel.py:1272` → reg `:1299` | `config/mcp/obsidian_mcp.json` → `python -m aios.adapters.mock_obsidian_server` (+ `vault_path`) | ✅ (MCP); ⚠️ filesystem path is REAL |
| FreeLLM | `freellmapi.py:30` | HTTP, default `localhost:8080` | (ModelRouter model `freellmapi-default`, NOT a capability) | **NEVER registered at boot** — `register_freellmapi_provider` only called from `tests/unit/test_m5_gate.py` | `FREELLM_API_URL` (default `http://localhost:8080`) | ⚠️ points at localhost, no real cloud endpoint |
| Hermes | `hermes_bridge.py:119` (+ `UserSimulationAgent` `kernel.py:959-964`) | MCP stdio → mock (ACP real path code-complete, unconfigured) | (MCP server `hermes_agent_ext`; no capability_id) | `kernel.py:959` constructs bridge (no `cwd` ⇒ falls back to mock MCP) | `config/mcp/hermes_agent_ext_mcp.json` → `python -m aios.adapters.mock_hermes_server` | ✅ YES |
| Graphify | `graphify_adapter.py:109` | MCP stdio → mock | `graphify_context` | `kernel.py:1144` → reg `:1163` | `config/mcp/graphify_mcp.json` → `python -m aios.adapters.mock_graphify_server` | ✅ YES |
| Claude-Mem | `claude_mem_adapter.py:117` | MCP stdio → mock | `claude_mem_context` | `kernel.py:1326` → reg `:1346` | `config/mcp/claude_mem_mcp.json` → `python -m aios.adapters.mock_claude_mem_server` | ✅ YES |
| Playwright | `playwright_mcp_adapter.py:93` | MCP stdio → mock (or direct `@playwright/mcp` subprocess) | `playwright_browser` | `kernel.py:1185` → reg `:1204` | env-gated: `HERMES_MOCK_PLAYWRIGHT=1` → `mock_playwright_mcp_server.py` (`:697`) | ✅ (default mock) |
| ACP | `acp_adapter.py:99` (via `HermesBridge`) | ACP over stdio subprocess (code-complete, unconfigured) | (allowlisted `kernel.py:1053`; no capability_id) | allowlist only — not instantiated at boot | real: `python -m acp_adapter.entry` (from `hermes-agent/` cwd) | ✅ (mock ACP server gated by `HERMES_MOCK_ACP`) |

**Confirmation that every MCP config points at a mock** — verified by reading each file:
`notion_mcp.json`, `obsidian_mcp.json`, `graphify_mcp.json`, `claude_mem_mcp.json`, `hermes_agent_ext_mcp.json`, `agent_reach_mcp.json` → all `command: ["python","-m","aios.adapters.mock_*_server"]`.
`mcps.yaml` is empty. `ai-os.manifest.yaml` is **0 bytes** (no real manifest payload).

### 2.2 Connection is LAZY — boot proves nothing about connectivity

None of the `_init_*` methods call `connect()`. Kernel docstring at `kernel.py:770-774` states: *"Connections are NOT made here… each adapter connects lazily via its own `connect()`."* Therefore a clean stock boot succeeding tells you **nothing** about whether any external system is reachable. This is correct, fail-safe design — but it is also why "it boots" must never be read as "it is connected."

### 2.3 Tier classification

| Tier | Definition | Applies to |
|---|---|---|
| **A** | In-process / mock | All 8 by default |
| **B** | Local real subprocess (real binary, local filesystem) | Obsidian (real vault), Playwright (real `@playwright/mcp`), Hermes/ACP (real `hermes-agent/` if `cwd` set), FreeLLM (real local proxy at `localhost:8080`) |
| **C** | Real external service / remote API / cloud | **NONE currently reachable** — Notion (SaaS), Claude-Mem (local-only per docs), Graphify (real Graphify server), FreeLLM (real hosted API), Hermes cloud browser (Browserbase) |

**Tier C is where the user's "genuinely operational" bar lives, and it is entirely unmet today.**

---

## 3. INTENDED REPOSITORIES / SERVICES (PHASE 2)

Identified from authoritative architecture docs (`architecture/V2_ARCHITECTURE_DECISION_RECORD.md`, `architecture/EXTERNAL_REPOSITORY_RECONCILIATION.md`, `AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md` §19.1, `architecture/Part15/M8/*`). Confidence stated honestly.

| Integration | Intended upstream | Confidence | Install / runtime | Local vs remote | Notes / ambiguities |
|---|---|---|---|---|---|
| Notion | `notion.so` SaaS | Low — **no concrete MCP server named** in any doc (master plan §19.1 gives only `notion.so`) | Not specified (MCP adapter or REST) | Remote SaaS + API key | Ambiguity: official `makenotion/notion-mcp` vs REST never chosen. |
| Obsidian | `github.com/obsidianmd/obsidian` (desktop app) + local vault; optional Obsidian MCP server | High for local vault; Low for real MCP server (generic "Obsidian MCP Server" only) | Desktop app + vault dir; no install for filesystem path | Local | The **filesystem path needs no external repo at all.** |
| FreeLLM API | `github.com/free-llm-api` **(assumed)** | **Low — explicitly hedged "(assumed)"** in master plan §19.1 | Unspecified; defaults to `localhost:8080` | Local dev proxy (docstring: "DEV/TEST ONLY, C13, no production without SLA") | Not a named public vendor. Could be any OpenAI-compatible endpoint. |
| Hermes / hermes-agent(EXT) | `github.com/NousResearch/hermes-agent` **(confirmed via git remote of vendored `hermes-agent/`)** | High | Python project, gitignored external repo; launched as subprocess (`acp_adapter/entry.py`) | Local subprocess (cloud browser via Browserbase creds) | `hermes-agent/` is vendored but **not referenced by running AI-OS code** — only the documented `cwd` target. |
| Graphify | `github.com/davioud/graphify` **(assumed)** | **Low — explicitly hedged "(assumed)"** | Unspecified | Local graph generator | No real Graphify server configured; only mock exists. |
| Claude-Mem | `github.com/thedotmack/claude-mem` | High | Local dev tool, no network | Local | **Contradiction:** master plan §14.2:455 / §20.3:746 say "Do NOT integrate", yet M8-T4 shipped a full adapter. Clarification needed. |
| Playwright | `github.com/microsoft/playwright` + npm `@playwright/mcp` | High (named, documented install) | **Node.js** + `@playwright/mcp` + browser binaries | Local subprocess | Only integration with a concretely named, installable upstream. **Not installed in this env.** |
| ACP | `agent-client-protocol` PyPI SDK (Agent Client Protocol) | Medium — package named, but never attributed to Anthropic/Chromium by name in docs | Python + `acp` SDK + `hermes-agent/` repo | Local subprocess | Protocol rides on Hermes; not a standalone integration. |

**Ambiguity STOP points (do not invent):**
- **FreeLLM** and **Graphify** upstreams are "(assumed)" in the master plan and were never verified. If a real connection is required, the user must confirm the exact service/endpoint — Terminal 2 will not invent one.
- **Notion** has no named MCP server package in any doc.
- **Claude-Mem** is explicitly "Do NOT integrate" in the master plan while code integrates it — this is a scope decision the user must resolve (see §7, classification G).

---

## 4. CREDENTIAL + SECRET INVENTORY (PHASE 3)

All checks performed by **name only**; no values were read or printed. Environment snapshot taken from the live shell (no `.env` file exists).

| Credential / env var | Status | Where it should live (per security architecture) |
|---|---|---|
| `NOTION_TOKEN` | **NOT CONFIGURED** (ABSENT) | MCP server `env` block in `config/mcp/notion_mcp.json` (`"env": {}` today) |
| `OBSIDIAN_VAULT_PATH` | **NOT CONFIGURED** (ABSENT) | `app_config.obsidian.vault_path` (`kernel.py:1287`); read at boot, defaults `None` |
| `FREELLM_API_KEY` | **NOT CONFIGURED** (ABSENT) | `freellmapi.py:179` reads it; **NOT in `.env.example`** (omitted entirely) |
| `FREELLM_API_URL` | **NOT CONFIGURED** (ABSENT) | `freellmapi.py:178`; defaults to `http://localhost:8080` |
| `FREELLM_TIMEOUT` / `FREELLM_DEFAULT_MODEL` | NOT CONFIGURED (ABSENT) | `freellmapi.py:180-181` |
| Graphify credentials | **NOT CONFIGURED** (N/A — no real server) | would go in `config/mcp/graphify_mcp.json` `env`/`headers` (currently `{}`) |
| Hermes credentials | **NOT CONFIGURED** (ABSENT) | real hermes-agent reads `~/.hermes/.env` independently; AI-OS side passes none |
| `HERMES_AGENT_URL` | **NOT CONFIGURED** (ABSENT) | n/a — bridge uses `server_id`, not a URL |
| Claude-Mem credentials | **NOT CONFIGURED** (N/A — local tool) | n/a |
| ACP credentials | **NOT CONFIGURED** (N/A — protocol) | n/a; env is scrubbed before subprocess (`acp_adapter.py:153`, `hermes_bridge.py:276`) |
| `PLAYWRIGHT_WS_ENDPOINT` | NOT CONFIGURED (ABSENT) | n/a — local browser |
| `HERMES_MOCK_ACP` / `HERMES_MOCK_PLAYWRIGHT` | NOT SET (mock-enabling flags) | env toggle, not a secret |

**Leakage surface check (where secrets must NOT appear):**
- `.gitignore:13` ignores `.env`. `.gitignore:30` ignores `/hermes-agent/` (external repo).
- Provenance schema (`capability_provenance.py:50-72`) carries only `source/adapter/operation/correlation_id/...` — **no secret fields**.
- Per-adapter redaction: Notion `:74-88,378`, Obsidian `:83-90,382`, Graphify `:80-87,388`, Playwright `_redact_url`/`_redact_dom` `:662-697`, ACP `_scrub_env` `:153`, Hermes `_scrub_env` `:276-290`.
- **Caveat (flagged):** redaction is **per-adapter, not centralized**. There is no global secret-redaction layer over `TestingEvidence`, exception strings, or arbitrary logs. If a real integration raises an exception containing a credential, the adapter must already scrub it — this is convention + tests, not a structural guarantee.

---

## 5. REAL ENDPOINT CONFIGURATION (PHASE 4)

Proposed real mapping. **Nothing below was changed.** This is the blueprint the implementation plan (companion doc) will execute.

| Integration | CURRENT MOCK | REAL SERVICE | REAL COMMAND / ENDPOINT | AUTH CONFIG | CAPABILITY ID | SECURITY GATE | HEALTH CHECK |
|---|---|---|---|---|---|---|---|
| Notion | `mock_notion_server` | Notion SaaS (or local MCP server) | `config/mcp/notion_mcp.json` → real server binary; `env.NOTION_TOKEN` | `NOTION_TOKEN` in `env` | `notion_planning` | `validate_mcp_server_before_connect` (`mcp_manager.py:255`) | `connect()` → `tools/list` |
| Obsidian | `mock_obsidian_server` | **Local vault (Tier B)** OR real Obsidian MCP | set `obsidian.vault_path` → filesystem; OR swap MCP command | none | `obsidian_knowledge` | same gate (MCP path) | filesystem `is_connected()` |
| FreeLLM | `localhost:8080` (dead — not registered) | real OpenAI-compatible proxy | `register_freellmapi_provider(...)` at boot + `FREELLM_API_URL` | `FREELLM_API_KEY` bearer | ModelRouter model (not capability) | **NONE** (no SecurityManager path) | none |
| Hermes | `mock_hermes_server` | real `hermes-agent/` ACP | `python -m acp_adapter.entry` (cwd=`hermes-agent/`) | hermes-agent `~/.hermes/.env` | (`hermes_agent_ext` MCP; no capability) | **MCP gate only on fallback path** | `AcPSessionRegistry` TTL |
| Graphify | `mock_graphify_server` | real Graphify MCP server | `config/mcp/graphify_mcp.json` → real server | (server-defined) | `graphify_context` | `validate_mcp_server_before_connect` | `connect()` → `tools/list` |
| Claude-Mem | `mock_claude_mem_server` | real Claude-Mem server (or accept doc's "do not integrate") | `config/mcp/claude_mem_mcp.json` → real server | none (local) | `claude_mem_context` | same gate | `connect()` → `tools/list` |
| Playwright | `mock_playwright_mcp_server` (env-gated) | real `@playwright/mcp` | unset `HERMES_MOCK_PLAYWRIGHT` → `node …/@playwright/mcp` | none (local) | `playwright_browser` | **bypassed on direct path** (`_connect_direct`) | `initialize`+`tools/list` |
| ACP | `mock_hermes_acp_server` (gated `HERMES_MOCK_ACP`) | real `hermes-agent` ACP | `python -m acp_adapter.entry` | none | (allowlisted) | **NOT gated** (spawns subprocess directly) | session TTL |

---

## 6. REAL CONNECTIVITY TEST DESIGN (PHASE 5)

Each test must prove **actual external connectivity**, not adapter instantiation. Design only — not executed.

| Integration | Operational test (proves real connection) | Must assert |
|---|---|---|
| Notion | Auth + connect to real Notion MCP; `search_pages` safe read | response non-empty/structured; `authority=contextual`; `trust_level=untrusted`; no `NOTION_TOKEN` in provenance/logs |
| Obsidian | Point `vault_path` at a real local vault; `search_notes`/`get_note` | real file bytes returned; `retrieval_path="filesystem"`; path-traversal blocked |
| FreeLLM | Register provider at boot; POST minimal chat completion to real `FREELLM_API_URL` | model responds; `provider=LOCAL`; error path returns `ERROR` result not exception |
| Hermes | Set `cwd=hermes-agent/`; ACP `session/new` + `session/prompt` safe op | `HermesObservation` returned; `trust_level=untrusted`; **no verdict authority** |
| Graphify | Connect to real Graphify MCP; `add_node`+`get_node` round-trip | result returned; `authority=advisory_only`; `trust_level=untrusted` |
| Claude-Mem | Connect to real server; `retrieve_context` safe read | memories returned; `trust_level=untrusted`; no write-to-kernel |
| Playwright | Unset mock flag; launch real browser; `navigate`+`screenshot` safe op | page rendered; cleanup; `file://` blocked; URL redacted |
| ACP | Real ACP handshake; verify session lifecycle + TTL | handshake ok; TTL expiry fails closed; provenance intact |

**Reality check on the EXISTING "production" tests:** `tests/integration/test_m8_t6_production_paths.py` is labeled "real subprocess" but runs against the **mock stdio servers** (`:173` — *"It launched real subprocesses for the mock servers"*). Even `test_prod_security_gate_passed` (`:194`) asserts the **mock** config passed the gate. **None of these prove Tier C connectivity.** This is the precise gap the user flagged.

---

## 7. SECURITY VALIDATION (PHASE 6)

### 7.1 The 13 checks

| # | Requirement | Status in code | Evidence |
|---|---|---|---|
| 1 | SecurityManager authorization BEFORE external execution | ✅ MCP path | `mcp_manager.py:252-255` gates `connect()` |
| 2 | External data cannot become authoritative | ✅ | `mark_capability_advisory` force-sets `authority`, `capability_provenance.py:223-257` |
| 3 | Adapter cannot modify `trust_level` | ⚠️ adapters *set* per-result `untrusted` but cannot escalate; registered capability trust frozen at `capability_manager.py:751-752` | `_mark_advisory` re-asserts constants |
| 4 | Adapter cannot modify `authority_classification` | ✅ same as #3 | `capability_provenance.py:249-257` |
| 5 | Provenance remains intact | ✅ | `build_capability_provenance` `:167`; adapters nest provenance |
| 6 | `correlation_id` propagates | ✅ (mostly) | resolved via `get_correlation_context()`; **gap:** Claude-Mem does not forward it into the MCP call (`claude_mem_adapter.py:377-406`) |
| 7 | Secrets not leaked | ⚠️ per-adapter only | redaction spread across adapters; no central layer |
| 8 | External failures fail safely | ✅ | adapters return `ExecutionResult(status=ERROR)`; never silent success |
| 9 | Timeouts bounded | ✅ default 30s | `MCPServerConfig.timeout_seconds` (`mcp_manager.py:86`) |
| 10 | Untrusted content cannot trigger unauthorized execution | ✅ | advisory-only; no decision authority in any adapter |
| 11 | M10 autonomous services cannot bypass gates | ⚠️ **DIVERGENCE** | `security_abac_ext.py:324-325` self-permits instead of calling `SecurityManager.authorize` |
| 12 | Human override remains effective | ✅ (autonomy escape hatch) | `autonomy_override.py:51,158` |
| 13 | M7 authority boundaries untouched | ✅ | no change proposed; report is read-only |

### 7.2 Security gaps to fix BEFORE any real connection (do not weaken tests)

- **GAP-S1 (HIGH):** ACP subprocess path (`acp_adapter.py` → `python -m acp_adapter.entry`) does **NOT** pass through `SecurityManager.validate_mcp_server_before_connect`. Only the MCP fallback path is gated (`mcp_manager.py:255`). Real Hermes ACP would launch an ungated subprocess.
- **GAP-S2 (HIGH):** Playwright direct-stdio path (`_connect_direct`, `playwright_mcp_adapter.py:185`) bypasses the same gate.
- **GAP-S3 (MEDIUM):** M10 autonomous actions self-permit via ABAC extension, bypassing `SecurityManager.authorize` (`security_abac_ext.py:324-325`). Must be reaffirmed as acceptable or corrected before autonomous services touch real externals.
- **GAP-S4 (LOW):** No centralized secret redaction over `TestingEvidence`/exceptions/logs.
- **GAP-S5 (LOW):** Capability manifest double-registration hazard — kernel `.register()` (`kernel.py:1163-1346`) AND manifest `register_capability()` (`kernel.py:1096`) for identical IDs with `_reject_duplicate_provider=True` (`capability_manager.py:384`). Manifests may be rejected as `CM-DUP-001`. Should be reconciled.

**None of these gaps are fixed in this audit. They are items for the implementation plan, and fixing them must not weaken any existing passing test.**

---

## 8. IMPLEMENTATION READINESS CLASSIFICATION (PHASE 7)

| Letter | Meaning | Integrations |
|---|---|---|
| **A. READY — creds/config only** | Real path exists; only credentials/config needed | **Obsidian (filesystem, no creds)**, Claude-Mem (if keeping it) |
| **B. READY — minor install/config** | Real path coded; need local binary + config | **Playwright**, **Graphify**, **Hermes/ACP** |
| **C. REQUIRES EXTERNAL SERVICE INSTALL** | Need a running external service | **Notion** (SaaS/real MCP server), **Graphify** (real server), **Hermes cloud browser** |
| **D. REQUIRES EXTERNAL REPO SETUP** | Need a repo cloned/configured | **Hermes** (`hermes-agent/` present but unreferenced), **FreeLLM** (real proxy) |
| **E. BLOCKED — missing credential/service** | Cannot proceed without user action | **Notion** (needs `NOTION_TOKEN` + account), **FreeLLM** (needs real endpoint + `FREELLM_API_KEY`) |
| **F. ARCHITECTURALLY UNSUPPORTED** | — | none |
| **G. UNKNOWN — needs clarification** | Scope decision required | **Claude-Mem** (doc says "do not integrate" but code does), **FreeLLM** (upstream "(assumed)"), **Graphify** (upstream "(assumed)"), **Notion** (which MCP server?) |

**Per-integration letter:**
- Notion → **E + G**
- Obsidian → **A** (filesystem) / C (real MCP)
- FreeLLM → **D + E + G** (not even registered at boot → also needs code)
- Hermes/ACP → **B + D** (code-complete, unconfigured; vendored repo unreferenced)
- Graphify → **B + C + G**
- Claude-Mem → **A + G** (scope contradiction)
- Playwright → **B**
- ACP → **B + D**

---

## 9. FINAL DETERMINATION

**AI-OS is NOT genuinely operational with respect to the 8 selected external integrations.** It is mature *implementation + mock simulation* infrastructure, with two partial real-local paths (Obsidian filesystem, Playwright direct) that are code-complete but unconfigured and unverified.

To move any integration to **OPERATIONALLY VERIFIED**, a real, successful external operation must occur against a real service/binary — and today **zero** such operations exist in the repository. The companion `REAL_EXTERNAL_INTEGRATIONS_IMPLEMENTATION_PLAN.md` gives the exact sequence to change that, including the manual steps only the user can perform (credentials, accounts, external installs) and the automated steps Terminal 2 can perform (config edits, gated tests, security-gap fixes), with Terminal 3 as the independent verifier.

**This report is an audit, not a certification.** Terminal 3 must independently verify any claimed operational status.
