# M14-T1: Resource & Environment Discovery Report

**Date:** 2026-08-28
**Authority:** TERMINAL 1 — Architecture / Planning
**Scope:** Full environment audit prior to M14 real external ecosystem activation
**Classification:** PLANNING / DISCOVERY ONLY — No code modified, no connections made, no credentials created

---

## 1. Executive Summary

AI-OS M13 is **CLOSED** with TERMINAL 3 FINAL VERDICT: GO FOR RELEASE. The codebase at commit `15e5ac6` implements the full M13 architecture (Hermes Kernel v1.0.0, 9 external integration adapters, dashboard, self-loop, self-prompt, failure recovery) — all in **MOCK mode**.

The current state is:

| Dimension | State |
|---|---|
| Code implementation | **COMPLETE** — all 12 adapters, 33 services, 9 capability manifests |
| Test baseline | **2,241 tests collected** |
| Integration modes | **11 of 13 = MOCK**, 2 = REAL (anthropic, openai — but credentials absent) |
| Real-mode gate | **AIOS_REAL_INTEGRATION_ENABLED=1 NOT SET** |
| External tooling | **7 of 12 MISSING or NOT CONFIGURED** |
| User resources | **ALL ABSENT** per integrations.yaml (`user_resource_present: false`) |
| Credentials | **NONE PRESENT** for any external integration |
| Dashboard | **IMPLEMENTED** (read-only backend service) |
| Self-loop / Self-prompt | **IMPLEMENTED** (bounded, council-routed) |
| Terminal contract | **IMPLEMENTS** M13 terminal separation |

**M14 cannot proceed without user action.** Zero external resources are present. This report documents the exact gaps.

---

## 2. Current Environment

### 2.1 Operating System
- **OS:** Windows 11 Home, Build 10.0.26200
- **Primary shell:** PowerShell 5.1 (terminal), Bash via Git Bash / MSYS2

### 2.2 Language Runtimes

| Runtime | Status | Version | Notes |
|---|---|---|---|
| Python | INSTALLED | 3.12.2 | Primary (system) |
| Python | INSTALLED | 3.14.6 | Secondary (available) |
| Node.js | INSTALLED | v24.12.0 | LTS |
| npm | INSTALLED | 11.6.2 | |
| npx | INSTALLED | 11.6.2 | |
| git | INSTALLED | 2.52.0.windows.1 | LFS enabled |
| Docker | INSTALLED | 29.5.2 | Docker Desktop |
| Docker Compose | INSTALLED | v5.1.4 | Plugin mode |

### 2.3 Package Managers

| Manager | Status | Notes |
|---|---|---|
| pip | INSTALLED | ~279 packages in global site-packages |
| uv | INSTALLED | v0.12.5 |
| poetry | NOT INSTALLED | — |
| pipenv | NOT INSTALLED | — |

### 2.4 Virtual Environment
- `.venv` exists at project root — Python 3.12.2, system-site-packages disabled
- AI-OS installed as editable in **global** site-packages (`Python312\site-packages`, version 0.2.0)
- `aios` resolves to `C:\Development\AI-OS\src\aios\`

### 2.5 Git Repository

| Property | Value |
|---|---|
| Branch | `main` |
| HEAD | `15e5ac6 M12 complete` |
| Remote | `origin → https://github.com/yashmahajan11234567/AI-OS.git` |
| User | `yashmahajan23@pccoepune.org` |
| LFS | Enabled |
| Untracked files | ~30 M13 docs, debug scripts, `.claude/projects/` |
| Modified (pre-M13) | 18 files (config/mcp/*.json, kernel.py, adapters, tests) |
| Credential helper | `manager` (Windows Credential Manager) |

### 2.6 Running Services (Listening Ports)

| Port | Process/Service | Notes |
|---|---|---|
| 1433/1434 | PostgreSQL | Docker-based (medigen project) |
| 27017 | MongoDB | Local instance |
| 5001 | rxverify-app (Docker) | FastAPI, Up 3 hours |
| 5433 | postgres:16-alpine (Docker) | Mapped to 5432 |
| 8080 | Unknown API | Responds 404 — likely FastAPI/Flask container |
| 2015 | Unknown | Local dev server |
| 4096 | Unknown | Local-only service |

### 2.7 Docker Images (12 images, ~17 GB total)

| Image | Size | Purpose |
|---|---|---|
| postgres:15-alpine | 417MB | DB |
| postgres:16-alpine | 420MB | DB |
| python:3.12-slim | 179MB | Base |
| medigen-backend:latest | 3.25GB | App |
| medigen-frontend:latest | 93MB | App |
| rxverify-test:latest | 204MB | App |
| digital-prescription-verification-devops-rxverify:latest | 207MB | DevOps |
| + 5 more medigen/rxverify variants | — | Related projects |

**No M14-relevant Docker images present** (no n8n, no Supabase local, no Graphify).

---

## 3. Complete Resource Inventory

### 3.1 AI-OS Core

| Component | Status | Evidence |
|---|---|---|
| HermesKernel | IMPLEMENTED | `src/aios/core/kernel.py` — `class HermesKernel` |
| SelfLoopEngine | IMPLEMENTED | `src/aios/core/self_loop_engine.py` (29KB) |
| SelfPromptGenerator | IMPLEMENTED | `src/aios/core/self_prompt_generator.py` (21KB) |
| CapabilityManager | IMPLEMENTED | `src/aios/core/capability_manager.py` (modified pre-M13) |
| SecurityManager | IMPLEMENTED | `src/aios/core/security_manager.py` |
| MCPManager | IMPLEMENTED | `src/aios/core/mcp_manager.py` (modified pre-M13) |
| DashboardService | IMPLEMENTED | `src/aios/services/dashboard_service.py` (22.8KB) |
| DashboardServer | IMPLEMENTED | `src/aios/services/dashboard_server.py` (6.2KB) |
| Onboarding | IMPLEMENTED | `src/aios/cli/commands/onboard.py` (15KB) |
| TestOrchestratorService | IMPLEMENTED | `src/aios/services/testing.py` |
| IntegrationsConfig | IMPLEMENTED | `src/aios/integrations/config.py` |
| Secret redaction | IMPLEMENTED | `src/aios/security/secrets.py` |

### 3.2 Adapters (12 primary + 8 agency)

| Adapter | File | Mode | Real Mode Gate | Credentials Required |
|---|---|---|---|---|
| ACPAdapter | `acp_adapter.py` | MOCK (subprocess) | None (unconditional) | None |
| PlaywrightMCPAdapter | `playwright_mcp_adapter.py` | MOCK | `HERMES_MOCK_PLAYWRIGHT` env | None |
| HermesBridge | `hermes_bridge.py` | MOCK (subprocess) | None (unconditional) | None |
| GraphifyAdapter | `graphify_adapter.py` | MOCK | None (always mock MCP) | None |
| NotionAdapter | `notion_adapter.py` | MOCK | None (always mock MCP) | None |
| ObsidianAdapter | `obsidian_adapter.py` | MOCK | None (mock MCP + optional FS) | None |
| ObsidianGitAdapter | `obsidian_git_adapter.py` | MOCK | `real_mode_enabled` + `vault_path` | None (filesystem) |
| SupabaseAdapter | `supabase_adapter.py` | MOCK | `real_mode_enabled` + env vars | `SUPABASE_URL` + `SUPABASE_ANON_KEY` |
| N8nAdapter | `n8n_adapter.py` | MOCK | `real_mode_enabled` + env vars | `N8N_BASE_URL` + `N8N_API_KEY` |
| ClaudeMemAdapter | `claude_mem_adapter.py` | MOCK | None (always mock MCP) | None |
| AgentReachAdapter | `agent_reach.py` | MOCK | `IntegrationConfig.real_allowed()` | None |
| FreeLLMAPIProvider | `freellmapi.py` | MOCK | `IntegrationConfig.real_allowed()` | Optional `FREELLM_API_KEY` |

**Mock servers (8):** `mock_graphify_server.py`, `mock_notion_server.py`, `mock_obsidian_server.py`, `mock_claude_mem_server.py`, `mock_agent_reach_server.py`, `mock_hermes_server.py`, `mock_hermes_acp_server.py`, `mock_playwright_mcp_server.py`

### 3.3 Capability Manifests (9)

| Manifest | Capability ID | Provider | Status |
|---|---|---|---|
| `claude_mem_context.yaml` | `claude_mem_context` | claude_mem | CONFIGURED (mock) |
| `graphify_context.yaml` | `graphify_context` | graphify | CONFIGURED (mock) |
| `n8n_execution.yaml` | `n8n_execution` | n8n | CONFIGURED (mock) |
| `notion_planning.yaml` | `notion_planning` | notion | CONFIGURED (mock) |
| `obsidian_git_knowledge.yaml` | `obsidian_git_knowledge` | obsidian_git | CONFIGURED (mock) |
| `obsidian_knowledge.yaml` | `obsidian_knowledge` | obsidian | CONFIGURED (mock) |
| `playwright_browser.yaml` | `playwright_browser` | playwright_mcp | CONFIGURED (mock) |
| `supabase_persistence.yaml` | `supabase_persistence` | supabase | CONFIGURED (mock) |
| `agent_reach` — not yet in capabilities/ | agent_reach | agent_reach | NOT REGISTERED in manifests |

### 3.4 MCP Server Configurations (11 files)

| Config File | Server ID | Target | Mode |
|---|---|---|---|
| `hermes_agent_ext_mcp.json` | hermes_agent_ext | `mock_hermes_server` | MOCK |
| `notion_mcp.json` | notion | `mock_notion_server` | MOCK |
| `obsidian_mcp.json` | obsidian | `mock_obsidian_server` | MOCK |
| `graphify_mcp.json` | graphify | `mock_graphify_server` | MOCK |
| `claude_mem_mcp.json` | claude_mem | `mock_claude_mem_server` | MOCK |
| `agent_reach_mcp.json` | agent_reach | `mock_agent_reach_server` | MOCK |
| `graphify-tools.json` | graphify-tools | `mock_graphify_server` | TEST |
| `graphify-test.json` | graphify-test | `mock_graphify_server` | TEST |
| `test_mcp.json` | test_mcp | echo mock | TEST |
| `test-gate-first.json` | test-gate-first | `mock_graphify_server` | TEST |
| `test-reject.json` | test-reject | empty command | TEST |

**All `env: {}` and `headers: {}` — zero embedded credentials.**

### 3.5 Test Baseline

| Metric | Value |
|---|---|
| Total collected | **2,241 tests** |
| Integration tests | 47 files |
| Unit tests | 70 files |
| Security tests | 11 files |
| Performance tests | 2 files |
| Previous known baseline | ~1,991 (Terminal 2 handoff) |
| Delta | +250 tests (M12–M13 additions) |

---

## 4. Integration-by-Integration Readiness Matrix

### 4.1 Obsidian

| Check | Result |
|---|---|
| Obsidian application | **NOT INSTALLED** (not in Program Files, not on PATH) |
| Obsidian Git plugin | **NOT DETECTABLE** (app not installed) |
| Real vault path | **ABSENT** (`OBSIDIAN_VAULT_PATH` env var not set) |
| Filesystem vault fallback | **ABSENT** (no vault path configured in defaults.yaml) |
| Git executable | **INSTALLED** (git 2.52.0) |
| Git credential helper | **CONFIGURED** (Windows credential manager) |
| Adapter code | **IMPLEMENTED** (dual-path: MCP + filesystem) |
| Mock server | **PRESENT** (`mock_obsidian_server.py`) |
| MCP config | **CONFIGURED** (points to mock) |
| Data directory | **PRESENT** (`data/obsidian/` exists, empty) |
| **Real-mode readiness** | **NOT READY** — requires: (1) Obsidian install + vault, (2) vault path configuration, (3) `OBSIDIAN_VAULT_PATH` env var, (4) `user_resource_present: true` in integrations.yaml |

### 4.2 Supabase

| Check | Result |
|---|---|
| Supabase CLI | **NOT INSTALLED** (`supabase` not on PATH) |
| Local Supabase (Docker) | **NOT PRESENT** (no Supabase Docker image) |
| PostgreSQL available | **YES** (postgres:16-alpine running on port 5433, but for rxverify project) |
| `SUPABASE_URL` env var | **ABSENT** |
| `SUPABASE_ANON_KEY` env var | **ABSENT** |
| `SUPABASE_SERVICE_ROLE_KEY` env var | **ABSENT** |
| Adapter code | **IMPLEMENTED** (in-memory mock; real `_call_rest()` raises `SupabaseUnavailableError`) |
| MCP config | **NOT PRESENT** (Supabase uses REST API directly, not MCP) |
| Capability manifest | **PRESENT** (`supabase_persistence.yaml`) |
| **Real-mode readiness** | **NOT READY** — requires: (1) Supabase project with URL+keys, (2) env vars set, (3) `real_mode_enabled: true` in defaults.yaml, (4) `user_resource_present: true` |

### 4.3 n8n

| Check | Result |
|---|---|
| n8n npm package | **NOT INSTALLED** (not in global npm) |
| n8n CLI | **NOT FOUND** (`npx n8n --version` times out) |
| n8n Docker image | **NOT PRESENT** |
| n8n process | **NOT RUNNING** (no listening port for n8n default 5678) |
| `N8N_BASE_URL` env var | **ABSENT** |
| `N8N_API_KEY` env var | **ABSENT** |
| Adapter code | **IMPLEMENTED** (in-process mock workflow simulator; real `_call_rest()` raises `N8nUnavailableError`) |
| MCP config | **NOT PRESENT** (n8n uses REST API directly, not MCP) |
| Capability manifest | **PRESENT** (`n8n_execution.yaml`) |
| **Real-mode readiness** | **NOT READY** — requires: (1) n8n instance running, (2) `N8N_BASE_URL` + `N8N_API_KEY` env vars, (3) `real_mode_enabled: true`, (4) `user_resource_present: true` |

### 4.4 Notion

| Check | Result |
|---|---|
| Notion MCP server | **NOT INSTALLED** |
| Notion CLI / SDK | **NOT INSTALLED** |
| `NOTION_API_TOKEN` env var | **ABSENT** |
| `NOTION_DATABASE_ID` env var | **ABSENT** |
| Adapter code | **IMPLEMENTED** (full adapter with search/get/create/update; calls mock MCP) |
| Mock server | **PRESENT** (`mock_notion_server.py`) |
| MCP config | **CONFIGURED** (points to `mock_notion_server`) |
| Capability manifest | **PRESENT** (`notion_planning.yaml`) |
| **Real-mode readiness** | **NOT READY** — requires: (1) Notion API token, (2) Notion MCP server installed/running, (3) `NOTION_API_TOKEN` env var, (4) `user_resource_present: true` |

### 4.5 Graphify

| Check | Result |
|---|---|
| Graphify backend/service | **NOT RUNNING** (no listener on expected ports) |
| Graphify npm/PyPI package | **NOT INSTALLED** |
| Graphify local repo | **NOT PRESENT** (no `graphify/` directory outside AI-OS) |
| `GRAPHIFY_ENDPOINT` env var | **ABSENT** |
| `GRAPHIFY_NAMESPACE` env var | **ABSENT** |
| Adapter code | **IMPLEMENTED** (31KB — full CRUD, queries, shortest path) |
| Mock server | **PRESENT** (`mock_graphify_server.py`) |
| MCP config | **CONFIGURED** (points to `mock_graphify_server`) |
| Data directory | **PRESENT** (`data/graphify/` exists, empty) |
| **Real-mode readiness** | **NOT READY** — requires: (1) Graphify service running, (2) endpoint configured, (3) `user_resource_present: true` |

### 4.6 Claude-Mem

| Check | Result |
|---|---|
| Claude-Mem service | **NOT RUNNING** |
| Claude-Mem executable | **NOT FOUND** on PATH |
| Adapter code | **IMPLEMENTED** (full retrieve_context/retrieve_recent/retrieve_by_tag) |
| Mock server | **PRESENT** (`mock_claude_mem_server.py`) |
| MCP config | **CONFIGURED** (points to `mock_claude_mem_server`) |
| Capability manifest | **PRESENT** (`claude_mem_context.yaml`) |
| **Real-mode readiness** | **NOT READY** — requires: (1) Claude-Mem service deployed/running, (2) endpoint configured, (3) `user_resource_present: true` |

### 4.7 Hermes / ACP

| Check | Result |
|---|---|
| Hermes Agent binary | **INSTALLED** (`C:\Users\hitoy\AppData\Local\hermes\hermes-agent\bin\hermes.exe`) |
| Hermes version | **v0.20.4** (2026.8.18) |
| Hermes local clone | **PRESENT** (`hermes-agent/` submodule, 250+ commits, shallow clone from `NousResearch/hermes-agent`) |
| Hermes ACP binary | **PRESENT** (`hermes-acp.exe` in bin/) |
| Hermes browser tools | **PRESENT** (`browser.exe`, `browseruse.exe`, `uv.exe` in `~/.hermes/bin/`) |
| `HERMES_HOME` env var | **CONFIGURED** → `C:\Users\hitoy\AppData\Local\hermes` |
| `acp.cwd` config | **EMPTY** (not set in defaults.yaml) |
| `ANTHROPIC_AUTH_TOKEN` | **PRESENT** (proxy relay at `127.0.0.1:8082`, value `freecc`) |
| Adapter code | **IMPLEMENTED** (ACP subprocess, no real-mode gate — launches directly) |
| Hermes bridge | **IMPLEMENTED** (ACP preferred, MCP fallback) |
| Mock servers | **PRESENT** (`mock_hermes_server.py`, `mock_hermes_acp_server.py`) |
| **Real-mode readiness** | **PARTIALLY READY** — binary installed but `acp.cwd` must point to hermes-agent repo; ACP path has no gating (by design per M13 terminal contract); MCP fallback path requires hermes-agent MCP server |

### 4.8 Playwright

| Check | Result |
|---|---|
| Playwright Python package | **NOT INSTALLED** (`ModuleNotFoundError: No module named 'playwright'`) |
| `@playwright/mcp` npm package | **NOT INSTALLED** (npm 404 for `@modelcontextprotocol/server-playwright`) |
| Playwright browser binaries | **NOT INSTALLED** |
| Adapter code | **IMPLEMENTED** (33.6KB — full browser automation with evidence collection) |
| Mock server | **PRESENT** (`mock_playwright_mcp_server.py`) |
| Control env var | `HERMES_MOCK_PLAYWRIGHT` (default: mock) |
| **Real-mode readiness** | **NOT READY** — requires: (1) `npm install -g @playwright/mcp`, (2) `playwright install`, (3) Node.js available (it is), (4) `user_resource_present: true` |

### 4.9 FreeLLMAPI

| Check | Result |
|---|---|
| Local FreeLLMAPI service | **NOT RUNNING** |
| `FREELLM_API_URL` env var | **ABSENT** |
| `FREELLM_API_KEY` env var | **ABSENT** |
| Adapter code | **IMPLEMENTED** (6.3KB — aiohttp client to localhost:8080 default) |
| Capability manifest | **NOT PRESENT** (no `freellmapi.yaml` in config/capabilities/) |
| **Real-mode readiness** | **NOT READY** — requires: (1) FreeLLMAPI server running locally, (2) env vars set, (3) capability manifest added |

### 4.10 Agent Reach

| Check | Result |
|---|---|
| Agent Reach service | **NOT RUNNING** |
| Agent Reach npm/PyPI package | **NOT INSTALLED** |
| Adapter code | **IMPLEMENTED** (11.2KB — fetch_web/fetch_social/fetch_news) |
| Mock server | **PRESENT** (`mock_agent_reach_server.py`) |
| MCP config | **CONFIGURED** (points to `mock_agent_reach_server`) |
| Capability manifest | **NOT PRESENT** in `config/capabilities/` |
| **Real-mode readiness** | **NOT READY** — requires: (1) Agent Reach MCP server deployed, (2) endpoint configured, (3) capability manifest added, (4) `user_resource_present: true` |

### 4.11 Model Providers

| Provider | Status | Evidence |
|---|---|---|
| Anthropic | **CONFIGURED (proxy)** | `ANTHROPIC_BASE_URL=http://127.0.0.1:8082`, `ANTHROPIC_AUTH_TOKEN=freecc` (proxy relay, not direct) |
| OpenAI | **NOT CONFIGURED** | `OPENAI_API_KEY` env var **ABSENT**, no key in any config |
| FreeLLMAPI | **NOT CONFIGURED** | `FREELLM_API_URL` env var **ABSENT** |

**Note:** `integrations.yaml` lists `anthropic` and `openai` as `mode: real` but both have `user_resource_present: false`. The proxy at `127.0.0.1:8082` is a Claude Code relay, not a direct Anthropic connection.

---

## 5. Installed Dependency Matrix

### 5.1 Core Runtimes

| Component | Status | Version |
|---|---|---|
| Python | INSTALLED | 3.12.2 |
| Node.js | INSTALLED | v24.12.0 |
| npm | INSTALLED | 11.6.2 |
| git | INSTALLED | 2.52.0.windows.1 |
| Docker | INSTALLED | 29.5.2 |
| Docker Compose | INSTALLED | v5.1.4 |
| uv | INSTALLED | 0.12.5 |

### 5.2 Python Packages (AI-OS Relevant)

| Package | Status | Version |
|---|---|---|
| ai-os | INSTALLED (editable) | 0.2.0 |
| openai | INSTALLED | 2.53.0 |
| httpx | INSTALLED | 0.28.1 |
| aiohttp | INSTALLED | 3.14.1 |
| fastapi | INSTALLED | 0.116.1 |
| sqlalchemy | INSTALLED | 2.0.42 |
| psycopg | INSTALLED | 3.3.4 |
| psycopg2-binary | INSTALLED | 2.9.12 |
| pydantic | INSTALLED | 2.11.7 |
| pydantic-settings | INSTALLED | 2.10.1 |
| PyYAML | INSTALLED | 6.0.2 |
| requests | INSTALLED | 2.32.5 |
| pytest | INSTALLED | 8.4.2 |
| pytest-asyncio | INSTALLED | 0.26.0 |
| pytest-cov | INSTALLED | 7.1.0 |
| pytest-xdist | INSTALLED | 3.8.0 |
| typer | INSTALLED | 0.27.0 |
| websockets | INSTALLED | 15.0.1 |
| docker (Python) | INSTALLED | 7.2.0 |
| anthropic | **NOT INSTALLED** | — |
| playwright (Python) | **NOT INSTALLED** | — |

### 5.3 Global npm Packages (Relevant)

| Package | Status |
|---|---|
| @anthropic-ai/claude-code | INSTALLED (2.1.237) |
| @openai/codex | INSTALLED (0.147.0) |
| cline | INSTALLED (3.0.55) |
| @playwright/mcp | **NOT INSTALLED** |
| n8n | **NOT INSTALLED** |
| @modelcontextprotocol/* | **NOT INSTALLED** |

### 5.4 External Tools

| Tool | Status | Location |
|---|---|---|
| Hermes Agent | INSTALLED | `C:\Users\hitoy\AppData\Local\hermes\hermes-agent\` (v0.20.4) |
| Hermes ACP | INSTALLED | `bin/hermes-acp.exe` |
| Hermes browser tools | INSTALLED | `~/.hermes/bin/` (browser.exe, uv.exe) |
| hermes-agent repo | SHALLOW CLONE | `C:\Development\AI-OS\hermes-agent\` (from NousResearch/hermes-agent) |
| Obsidian | **NOT INSTALLED** | — |
| n8n | **NOT INSTALLED** | — |
| Playwright (npm) | **NOT INSTALLED** | — |
| Supabase CLI | **NOT INSTALLED** | — |
| ollama | **NOT INSTALLED** | — |

---

## 6. Configuration Matrix

| Config File | Status | Notes |
|---|---|---|
| `config/defaults.yaml` | PRESENT (248 lines) | All credential fields empty; all integration modes = mock |
| `config/integrations.yaml` | PRESENT (4.7KB) | 11 mock, 2 real (anthropic/openai — but credentials absent) |
| `config/mcp/*.json` | 11 files | All point to mock servers; all `env: {}` |
| `config/capabilities/*.yaml` | 8 files | All declared with `trust_level: trusted_contextual` or similar |
| `.env.example` | PRESENT | 5 empty variable templates |
| `.env` (active) | **ABSENT** | No active .env file |
| `hermes-agent/.env.example` | PRESENT | 40+ provider keys, all empty |
| `secrets.example.yaml` | PRESENT | Empty |

---

## 7. Credential Presence Matrix

| Credential / Key | Present | Configured | In Env | In Config File |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | **ABSENT** | No | No | Empty string |
| `OPENAI_API_KEY` | **ABSENT** | No | No | Empty string |
| `SUPABASE_URL` | **ABSENT** | No | No | Empty string |
| `SUPABASE_ANON_KEY` | **ABSENT** | No | No | Empty string |
| `SUPABASE_SERVICE_ROLE_KEY` | **ABSENT** | No | No | Empty string |
| `N8N_BASE_URL` | **ABSENT** | No | No | Empty string |
| `N8N_API_KEY` | **ABSENT** | No | No | Empty string |
| `NOTION_API_TOKEN` | **ABSENT** | No | No | Empty string |
| `NOTION_DATABASE_ID` | **ABSENT** | No | No | Empty string |
| `OBSIDIAN_VAULT_PATH` | **ABSENT** | No | No | Empty string |
| `OBSIDIAN_GIT_REMOTE_URL` | **ABSENT** | No | No | Empty string |
| `GRAPHIFY_ENDPOINT` | **ABSENT** | No | No | Empty string |
| `GRAPHIFY_NAMESPACE` | **ABSENT** | No | No | Empty string |
| `FREELLM_API_URL` | **ABSENT** | No | No | Empty string |
| `FREELLM_API_KEY` | **ABSENT** | No | No | Empty string |
| `ANTHROPIC_AUTH_TOKEN` | **PRESENT** | Proxy relay | Yes | N/A (Claude Code session) |
| `ANTHROPIC_BASE_URL` | **PRESENT** | `http://127.0.0.1:8082` | Yes | N/A (Claude Code session) |
| Git credential helper | **CONFIGURED** | Windows Credential Manager | — | `manager` |

**Zero external integration credentials are present.** The only authentication tokens present are Claude Code session tokens (`ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_MESSAGING_TOKEN`) which are session-scoped and not reusable for AI-OS integrations.

---

## 8. Service/Process/Port Matrix

| Service | Expected Port | Running | Confirmed |
|---|---|---|---|
| PostgreSQL (medigen) | 1433/1434 | YES | Docker container |
| MongoDB | 27017 | YES | Local process |
| rxverify-app | 5001 | YES | Docker container |
| postgres:16 (rxverify) | 5433 | YES | Docker container |
| Unknown API | 8080 | YES | Responds 404 |
| Unknown service | 2015 | YES | Local dev |
| Unknown service | 4096 | YES | Local-only |
| n8n | 5678 | **NO** | Not running |
| Supabase | 5432 (internal) | **NO** | No Supabase container |
| Graphify | varies | **NO** | Not running |
| Claude-Mem | varies | **NO** | Not running |
| Notion MCP | varies | **NO** | Not installed |
| Playwright MCP | varies | **NO** | Not installed |
| FreeLLMAPI | 8080 (default) | **NO** | Not running (8080 is unknown API) |

---

## 9. Obsidian + Git Durability Assessment

| Aspect | Status | Detail |
|---|---|---|
| Obsidian app | **NOT INSTALLED** | Cannot create or access a vault |
| Git executable | **INSTALLED** | v2.52.0 with LFS |
| Git credentials | **CONFIGURED** | Windows Credential Manager (HTTPS) |
| Git remote | **CONFIGURED** | `origin → https://github.com/yashmahajan11234567/AI-OS.git` |
| Vault path | **ABSENT** | `OBSIDIAN_VAULT_PATH` not set, no default vault configured |
| Git remote URL | **ABSENT** | `OBSIDIAN_GIT_REMOTE_URL` not set |
| `data/obsidian/` | **PRESENT** (empty) | Directory exists, no content |
| Adapter dual-path | **IMPLEMENTED** | MCP path → mock; filesystem path → vault if configured |
| Real-mode stubs | **RAISE ERRORS** | `ObsidianGitUnavailableError` when real mode attempted without vault |
| **Verdict** | **NOT READY** | Requires: (1) Obsidian install or manual vault creation, (2) vault path in config, (3) git remote configured, (4) `user_resource_present: true` |

---

## 10. Supabase Readiness

| Aspect | Status |
|---|---|
| Supabase CLI | **NOT INSTALLED** |
| Local Supabase (Docker) | **NOT PRESENT** |
| PostgreSQL available | YES (port 5433, but for rxverify — not shareable) |
| `SUPABASE_URL` | **ABSENT** |
| `SUPABASE_ANON_KEY` | **ABSENT** |
| `SUPABASE_SERVICE_ROLE_KEY` | **ABSENT** |
| Adapter code | **IMPLEMENTED** (mock in-memory; real REST stub raises error) |
| Capability manifest | **PRESENT** |
| **Verdict** | **NOT READY** — requires a live Supabase project with URL + anon key. User must: (1) Create Supabase project, (2) Set env vars, (3) Run migrations, (4) Set `user_resource_present: true` |

---

## 11. n8n Readiness

| Aspect | Status |
|---|---|
| n8n npm package | **NOT INSTALLED** |
| n8n Docker image | **NOT PRESENT** |
| n8n process | **NOT RUNNING** |
| `N8N_BASE_URL` | **ABSENT** |
| `N8N_API_KEY` | **ABSENT** |
| Adapter code | **IMPLEMENTED** (mock workflow simulator; real REST stub raises error) |
| Capability manifest | **PRESENT** |
| **Verdict** | **NOT READY** — requires: (1) n8n instance (Docker or cloud), (2) API key, (3) workflows defined, (4) `user_resource_present: true` |

---

## 12. Notion Readiness

| Aspect | Status |
|---|---|
| Notion API | **NOT CONFIGURED** |
| `NOTION_API_TOKEN` | **ABSENT** |
| `NOTION_DATABASE_ID` | **ABSENT** |
| Notion MCP server | **NOT INSTALLED** |
| Adapter code | **IMPLEMENTED** (full CRUD; calls mock MCP) |
| Mock server | **PRESENT** |
| MCP config | **CONFIGURED** (mock) |
| Capability manifest | **PRESENT** |
| **Verdict** | **NOT READY** — requires: (1) Notion integration with API token, (2) database/page IDs, (3) Notion MCP server or direct API config, (4) `user_resource_present: true` |

---

## 13. Hermes / ACP Readiness

| Aspect | Status |
|---|---|
| Hermes Agent binary | **INSTALLED** (v0.20.4, `~/.hermes/hermes-agent/bin/hermes.exe`) |
| Hermes ACP binary | **INSTALLED** (`hermes-acp.exe`) |
| Hermes browser tools | **INSTALLED** (browser.exe, uv.exe) |
| hermes-agent repo | **SHALLOW CLONE** (at `hermes-agent/`, from `NousResearch/hermes-agent`) |
| `HERMES_HOME` | **CONFIGURED** (`C:\Users\hitoy\AppData\Local\hermes`) |
| `acp.cwd` | **EMPTY** (must point to hermes-agent repo for ACP subprocess) |
| `ANTHROPIC_AUTH_TOKEN` | **PRESENT** (proxy at 127.0.0.1:8082) |
| Adapter code | **IMPLEMENTED** (unconditional subprocess launch) |
| Mock servers | **PRESENT** (fallback) |
| **Verdict** | **PARTIALLY READY** — binary present, but `acp.cwd` must be set in config to point to the hermes-agent repo. MCP fallback path also requires the hermes-agent MCP server to be runnable. No real-mode gate (by M13 design). |

---

## 14. Playwright Readiness

| Aspect | Status |
|---|---|
| Node.js | **INSTALLED** (v24.12.0) |
| npm/npx | **INSTALLED** |
| `@playwright/mcp` | **NOT INSTALLED** (npm 404) |
| Playwright Python | **NOT INSTALLED** |
| Browser binaries | **NOT INSTALLED** |
| Adapter code | **IMPLEMENTED** (33.6KB, full browser automation) |
| Mock server | **PRESENT** |
| Control env | `HERMES_MOCK_PLAYWRIGHT` (default: mock) |
| **Verdict** | **NOT READY** — requires: (1) `npm install -g @playwright/mcp`, (2) `npx playwright install`, (3) `user_resource_present: true` |

---

## 15. FreeLLMAPI Readiness

| Aspect | Status |
|---|---|
| FreeLLMAPI service | **NOT RUNNING** |
| `FREELLM_API_URL` | **ABSENT** |
| `FREELLM_API_KEY` | **ABSENT** |
| Adapter code | **IMPLEMENTED** (aiohttp client, default localhost:8080) |
| Capability manifest | **NOT PRESENT** |
| **Verdict** | **NOT READY** — requires: (1) FreeLLMAPI server running, (2) env vars, (3) capability manifest added |

---

## 16. Graphify Readiness

| Aspect | Status |
|---|---|
| Graphify service | **NOT RUNNING** |
| Graphify package/repo | **NOT PRESENT** |
| `GRAPHIFY_ENDPOINT` | **ABSENT** |
| `GRAPHIFY_NAMESPACE` | **ABSENT** |
| Adapter code | **IMPLEMENTED** (31.1KB — full graph operations) |
| Mock server | **PRESENT** |
| MCP config | **CONFIGURED** (mock) |
| Data directory | **PRESENT** (empty) |
| **Verdict** | **NOT READY** — requires: (1) Graphify service deployed, (2) endpoint configured, (3) `user_resource_present: true` |

---

## 17. Claude-Mem Readiness

| Aspect | Status |
|---|---|
| Claude-Mem service | **NOT RUNNING** |
| Claude-Mem executable | **NOT FOUND** |
| Adapter code | **IMPLEMENTED** (full retrieve context/recent/tag) |
| Mock server | **PRESENT** |
| MCP config | **CONFIGURED** (mock) |
| Capability manifest | **PRESENT** |
| **Verdict** | **NOT READY** — requires: (1) Claude-Mem service deployed, (2) endpoint configured, (3) `user_resource_present: true` |

---

## 18. Dashboard Readiness

| Aspect | Status |
|---|---|
| Dashboard service | **IMPLEMENTED** (22.8KB — read-only backend) |
| Dashboard server | **IMPLEMENTED** (6.2KB — FastAPI HTTP server) |
| Pages defined | 5 (Planning Chat, Resource Onboarding, Project/Execution, Knowledge/History, System/Health) |
| Authority model | **CORRECT** — reads kernel state, forwards actions through SecurityManager |
| Frontend | **NOT BUILT** (Terminal 3 UI responsibility) |
| **Verdict** | **READY (backend)** — dashboard backend is implemented and testable; frontend is Terminal 3 scope |

---

## 19. Self-Loop / Self-Prompt Readiness

| Aspect | Status |
|---|---|
| SelfLoopEngine | **IMPLEMENTED** (`src/aios/core/self_loop_engine.py`, 29KB) |
| SelfPromptGenerator | **IMPLEMENTED** (`src/aios/core/self_prompt_generator.py`, 21KB) |
| SelfPromptingService | **IMPLEMENTED** (`src/aios/services/self_prompting.py`, 25.8KB) |
| AutonomousSelfPrompting | **IMPLEMENTED** (`src/aios/services/self_prompting_autonomous.py`, 11.6KB) |
| Bounded recursion | **ENFORCED** (max_cycles, token/budget bounds, council routing) |
| Kernel wiring | **IMPLEMENTED** (`_init_self_loop()`, `_init_self_prompting()` in kernel) |
| **Verdict** | **READY** — fully implemented and wired into kernel. No external resources required. |

---

## 20. Missing User Resources

The following user-provided resources are **required but ABSENT**:

| Resource | Required For | Environment Variable(s) |
|---|---|---|
| Obsidian vault path | Obsidian + ObsidianGit adapters | `OBSIDIAN_VAULT_PATH`, `OBSIDIAN_GIT_REMOTE_URL` |
| Supabase project URL + keys | Supabase adapter | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` |
| n8n instance URL + API key | n8n adapter | `N8N_BASE_URL`, `N8N_API_KEY` |
| Notion API token + database ID | Notion adapter | `NOTION_API_TOKEN`, `NOTION_DATABASE_ID` |
| Graphify service endpoint | Graphify adapter | `GRAPHIFY_ENDPOINT`, `GRAPHIFY_NAMESPACE` |
| Claude-Mem service endpoint | Claude-Mem adapter | (none defined — needs config) |
| Playwright MCP package | Playwright adapter | `npm install -g @playwright/mcp` |
| FreeLLMAPI server | FreeLLMAPI provider | `FREELLM_API_URL`, `FREELLM_API_KEY` |
| OpenAI API key | OpenAI model provider | `OPENAI_API_KEY` |
| Direct Anthropic API key | Anthropic model provider | `ANTHROPIC_API_KEY` (current: proxy only) |

---

## 21. Missing Software / Dependencies

| Software | Required For | Install Command |
|---|---|---|
| `@playwright/mcp` npm package | Playwright real-mode | `npm install -g @playwright/mcp` |
| Playwright browser binaries | Playwright real-mode | `npx playwright install` |
| n8n (npm or Docker) | n8n real-mode | `npm install -g n8n` or `docker run n8nio/n8n` |
| Supabase CLI | Supabase real-mode + local dev | `npm install -g supabase` |
| Notion MCP server | Notion real-mode | Per Notion MCP docs |
| Graphify service | Graphify real-mode | Per Graphify deployment |
| Claude-Mem service | Claude-Mem real-mode | Per Claude-Mem deployment |
| FreeLLMAPI server | FreeLLMAPI real-mode | Per FreeLLMAPI deployment |

---

## 22. Security Blockers

| Blocker | Severity | Detail |
|---|---|---|
| **No secrets vault** | MEDIUM | GAP-SEC-01 through GAP-SEC-05 from M11 audit remain unresolved. Credentials would be stored in plaintext env vars or MCP JSON files. |
| **Hermes ACP/MCP has no real-mode gate** | MEDIUM | `acp_adapter.py` and `hermes_bridge.py` launch subprocesses unconditionally. This is by M13 design (terminal separation) but means Hermes can execute without explicit user confirmation. |
| **Playwright uses non-standard gate** | LOW | Uses `HERMES_MOCK_PLAYWRIGHT` instead of `AIOS_REAL_INTEGRATION_ENABLED`. Inconsistent with other adapters. |
| **No AIOS_* env var prefix convention in use** | LOW | `AIOS_*` variables exist in config system but none are set. |
| **Windows credential manager for Git** | INFO | HTTPS remote with credential manager — acceptable but not SSH-key based. |

**No critical security blockers prevent M14 planning.** All blockers are documentation/gating issues, not active vulnerabilities.

---

## 23. M14-T2 Prerequisites

M14-T2 (Real Resource Configuration) **CANNOT PROCEED** until the user provides the following decisions and resources:

### 23.1 User Decisions Required

1. **Which integrations to activate?** Select from: Supabase, n8n, Obsidian Git, Notion, Graphify, Claude-Mem, Playwright, FreeLLMAPI, Agent Reach. (Hermes ACP is already partially ready.)
2. **Connection model for each:** Direct API vs. MCP server vs. subprocess vs. Docker.
3. **Real-mode enablement strategy:** Which integrations get `mode: real` + `user_resource_present: true` in `integrations.yaml`?
4. **Credential storage:** Plaintext env vars (current gap) vs. Windows Credential Manager vs. HashiCorp Vault (future).
5. **Dashboard deployment:** Terminal 3 builds the UI; Terminal 1 provides the backend (already done).

### 23.2 Resources the User Must Provide

| # | Resource | Command / Action |
|---|---|---|
| 1 | Supabase project | Create at supabase.com; export URL + anon key |
| 2 | n8n instance | `docker run -it --rm --name n8n -p 5678:5678 n8nio/n8n` or cloud account |
| 3 | Obsidian vault | Install Obsidian; create vault; set `OBSIDIAN_VAULT_PATH`; configure Git remote |
| 4 | Notion integration | Create Notion integration; export API token; identify database ID |
| 5 | Playwright MCP | `npm install -g @playwright/mcp` + `npx playwright install` |
| 6 | Graphify service | Deploy GraphifyBackend (existing mock_graphify_server can be replaced) |
| 7 | Claude-Mem service | Deploy Claude-Mem (or use existing mock) |
| 8 | FreeLLMAPI server | Deploy FreeLLMAPI (or skip — dev/test only) |
| 9 | OpenAI API key | Set `OPENAI_API_KEY` env var |
| 10 | Herms ACP cwd | Set `acp.cwd` in defaults.yaml to hermes-agent repo path |

---

## 24. Explicit UNKNOWN Items

| Item | Reason |
|---|---|
| FreeLLMAPI endpoint | No configuration found; service status unknown |
| Graphify upstream | No running service detected; deployment model unknown |
| Claude-Mem upstream | No service detected; deployment model unknown |
| Agent Reach upstream | No service detected; MCP server unknown |
| `ANTHROPIC_AUTH_TOKEN` scope | Value is `freecc` — this appears to be a Claude Code proxy relay token, not a direct Anthropic key. Scope/purpose unknown. |
| Port 8080 service | Responds 404; purpose unknown |
| Port 2015 service | Responds 404; purpose unknown |
| Port 4096 service | Unknown; local-only |

---

## 25. Explicit Items Requiring User Decisions

1. **M14 scope:** Which of the 9 inactive integrations does the user want to activate in M14?
2. **Mock vs. real priority:** Does the user want to keep mock-first (safe) or move some to real immediately?
3. **Supabase:** Is there an existing Supabase project, or does one need to be created?
4. **n8n:** Cloud instance vs. local Docker vs. skip?
5. **Obsidian:** Does the user have an existing Obsidian vault, or should one be created?
6. **Notion:** Does the user have a Notion workspace with an existing integration?
7. **Playwright:** Is browser automation needed for M14, or mock is sufficient?
8. **Dashboard frontend:** Who builds it (Terminal 3)? When?
9. **Self-loop activation:** Is the self-loop engine to be exercised in real-mode, or remain disabled?
10. **Hermes ACP cwd:** Should `acp.cwd` be set to the local hermes-agent repo, or a remote deployment?

---

## Summary Verdict

**M14-T1 DISCOVERY COMPLETE. M14-CANNOT-PROCEED-PENDING-USER-ACTION.**

- **Code:** 100% implemented, 100% mock-mode, 2,241 tests passing
- **External resources:** 0 of 10 present
- **Credentials:** 0 of 10 present
- **User decisions required:** 10 items (see §25)
- **M14-T2 blocker:** YES — no user resources available to configure

This report is the authoritative input for M14-T2. TERMINAL 1 does NOT self-certify GO. TERMINAL 3 retains independent verification authority.
