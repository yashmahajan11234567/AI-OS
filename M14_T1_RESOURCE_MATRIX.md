# M14-T1: Resource Matrix

**Date:** 2026-08-28
**Scope:** All external resources and dependencies for M14 real ecosystem activation
**States used:** IMPLEMENTED | INSTALLED | CONFIGURED | RESOURCE PRESENT | CONNECTED | OPERATIONALLY VERIFIED | MOCK | ABSENT | UNKNOWN | NOT READY

---

## Component Resource Matrix

| Component | Role | Implementation | Installed | Configured | Resource Present | Credentials Present | Service Running | Connection Possible | Operationally Verified | Mode | Blocker | Required User Action | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Hermes Agent (ACP)** | Execution worker — ACP subprocess | IMPLEMENTED | INSTALLED (v0.20.4) | PARTIALLY (cwd empty) | RESOURCE PRESENT (binary) | ABSENT (no auth needed) | NOT RUNNING (on-demand) | CONNECTED (mock) | NOT OPERATIONALLY VERIFIED | MOCK (subprocess unconditional) | `acp.cwd` not set | Set `acp.cwd` in defaults.yaml to hermes-agent repo path | `hermes.exe` at `~/.hermes/hermes-agent/bin/`; `hermes --version` → v0.20.4 |
| **Hermes Agent (MCP)** | Execution worker — MCP fallback | IMPLEMENTED | INSTALLED (binary) | CONFIGURED (mock server) | RESOURCE PRESENT | ABSENT | NOT RUNNING | CONNECTED (mock) | NOT OPERATIONALLY VERIFIED | MOCK | None (mock already works) | Set `acp.cwd` for real ACP path; install hermes MCP server for real MCP path | `config/mcp/hermes_agent_ext_mcp.json` → `mock_hermes_server` |
| **Playwright MCP** | Browser automation substrate | IMPLEMENTED | NOT INSTALLED | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | `@playwright/mcp` not installed; browser binaries absent | `npm install -g @playwright/mcp` + `npx playwright install` | `playwright` Python module: ModuleNotFoundError; npm global: no @playwright/mcp |
| **Obsidian** | Knowledge layer (MCP + filesystem) | IMPLEMENTED | NOT INSTALLED | PARTIALLY (MCP mock) | ABSENT (no vault) | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | Obsidian app not installed; no vault path | Install Obsidian; create vault; set `OBSIDIAN_VAULT_PATH` env var | `config/mcp/obsidian_mcp.json` → `mock_obsidian_server`; `data/obsidian/` empty dir |
| **Obsidian Git** | Knowledge durability (Git-backed vault) | IMPLEMENTED | Git: INSTALLED | PARTIALLY (Git present, vault absent) | ABSENT (no vault) | ABSENT (git creds via WM) | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No vault path; no git remote for vault | Create vault; set `OBSIDIAN_VAULT_PATH` + `OBSIDIAN_GIT_REMOTE_URL`; enable real mode | `obsidian_git_adapter.py` has `real_mode_enabled` + `vault_path` gates; Git credential helper = `manager` |
| **Supabase** | Persistent storage layer | IMPLEMENTED | NOT INSTALLED (CLI) | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No Supabase project; no URL/keys | Create Supabase project; set `SUPABASE_URL` + `SUPABASE_ANON_KEY`; run migrations | `supabase_adapter.py` real `_call_rest()` raises `SupabaseUnavailableError`; `config/capabilities/supabase_persistence.yaml` present |
| **n8n** | Bounded automation/execution | IMPLEMENTED | NOT INSTALLED | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No n8n instance; no URL/key | Deploy n8n (Docker or cloud); set `N8N_BASE_URL` + `N8N_API_KEY`; define workflows | `n8n_adapter.py` real `_call_rest()` raises `N8nUnavailableError`; `config/capabilities/n8n_execution.yaml` present |
| **Notion** | Planning advisory layer | IMPLEMENTED | NOT INSTALLED | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No Notion API token; no MCP server | Create Notion integration; set `NOTION_API_TOKEN`; identify `NOTION_DATABASE_ID` | `config/mcp/notion_mcp.json` → `mock_notion_server`; `config/capabilities/notion_planning.yaml` present |
| **Graphify** | Relationship/knowledge graph | IMPLEMENTED | NOT INSTALLED | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No Graphify service; no endpoint | Deploy GraphifyBackend; set `GRAPHIFY_ENDPOINT`; `GRAPHIFY_NAMESPACE` | `config/mcp/graphify_mcp.json` → `mock_graphify_server`; `data/graphify/` empty dir |
| **Claude-Mem** | Contextual memory retrieval | IMPLEMENTED | NOT INSTALLED | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No Claude-Mem service; no endpoint | Deploy Claude-Mem service; configure endpoint | `config/mcp/claude_mem_mcp.json` → `mock_claude_mem_server`; `config/capabilities/claude_mem_context.yaml` present |
| **Agent Reach** | Web/social content ingestion | IMPLEMENTED | NOT INSTALLED | CONFIGURED (mock) | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No Agent Reach service; no MCP server | Deploy Agent Reach MCP server; configure endpoint; add capability manifest | `config/mcp/agent_reach_mcp.json` → `mock_agent_reach_server`; no capability manifest in `config/capabilities/` |
| **FreeLLMAPI** | Local LLM provider (dev/test) | IMPLEMENTED | NOT INSTALLED | NOT CONFIGURED | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | MOCK | No FreeLLMAPI server; no env vars | Deploy FreeLLMAPI; set `FREELLM_API_URL` + `FREELLM_API_KEY`; add capability manifest | `freellmapi.py` connects to `localhost:8080` by default; no capability manifest |
| **Anthropic** | Model provider | IMPLEMENTED | N/A (API) | PARTIALLY (proxy relay) | RESOURCE PRESENT (proxy) | ABSENT (direct key) | NOT RUNNING (proxy exists) | CONNECTED (via proxy) | NOT OPERATIONALLY VERIFIED (direct) | REAL (gated, proxy relay) | No direct `ANTHROPIC_API_KEY`; only proxy at 127.0.0.1:8082 | Set `ANTHROPIC_API_KEY` for direct access; or keep proxy | `ANTHROPIC_BASE_URL=http://127.0.0.1:8082`; `ANTHROPIC_AUTH_TOKEN=freecc` (proxy) |
| **OpenAI** | Model provider | IMPLEMENTED | N/A (API) | NOT CONFIGURED | ABSENT | ABSENT | NOT RUNNING | NOT CONNECTED | NOT OPERATIONALLY VERIFIED | REAL (gated) | No `OPENAI_API_KEY` | Set `OPENAI_API_KEY` env var | `integrations.yaml`: `mode: real`, `user_resource_present: false` |
| **Dashboard (backend)** | Read-only UI backend | IMPLEMENTED | N/A (Python service) | CONFIGURED | RESOURCE PRESENT (code) | ABSENT (no secrets) | NOT RUNNING (not started) | N/A (internal) | NOT OPERATIONALLY VERIFIED | REAL (no external deps) | None | `dashboard_service.py` (22.8KB); `dashboard_server.py` (6.2KB); reads kernel state only |
| **Self-Loop Engine** | Autonomous decision-making | IMPLEMENTED | N/A (Python module) | CONFIGURED | RESOURCE PRESENT (code) | ABSENT | NOT RUNNING (event-driven) | N/A (internal) | NOT OPERATIONALLY VERIFIED | REAL (internal, bounded) | None | `self_loop_engine.py` (29KB); wired into `HermesKernel._init_self_loop()` |
| **Self-Prompt Generator** | Internal directive generation | IMPLEMENTED | N/A (Python module) | CONFIGURED | RESOURCE PRESENT (code) | ABSENT | NOT RUNNING (event-driven) | N/A (internal) | NOT OPERATIONALLY VERIFIED | REAL (internal, bounded) | None | `self_prompt_generator.py` (21KB); `self_prompting.py` (25.8KB) |
| **Git (source control)** | Repository management | INSTALLED | INSTALLED (2.52.0) | CONFIGURED | RESOURCE PRESENT | PARTIALLY (WM helper) | N/A | N/A | N/A | N/A | None | Remote: `origin → https://github.com/yashmahajan11234567/AI-OS.git`; credential.helper=manager | `git remote -v`; `git config --list --global` |

---

## Integration Readiness Summary

| Integration | Code | Mock | Real Path | Resource | Credentials | Ready for M14-T2 |
|---|---|---|---|---|---|---|
| Hermes ACP | ✅ | ✅ | ⚠️ (cwd empty) | ⚠️ (binary yes, config partial) | ✅ (none needed) | PARTIALLY — needs `acp.cwd` |
| Hermes MCP | ✅ | ✅ | ⚠️ (needs hermes MCP server) | ✅ (binary) | ✅ (none needed) | MOCK OK; REAL needs server |
| Playwright | ✅ | ✅ | ❌ | ❌ | ✅ (none needed) | NOT READY — install required |
| Obsidian | ✅ | ✅ | ❌ | ❌ | ✅ (none needed) | NOT READY — app + vault required |
| Obsidian Git | ✅ | ✅ | ❌ | ❌ | ✅ (Git WM) | NOT READY — vault + remote required |
| Supabase | ✅ | ✅ | ❌ (stub raises) | ❌ | ❌ | NOT READY — project + keys required |
| n8n | ✅ | ✅ | ❌ (stub raises) | ❌ | ❌ | NOT READY — instance + key required |
| Notion | ✅ | ✅ | ❌ | ❌ | ❌ | NOT READY — token + DB ID required |
| Graphify | ✅ | ✅ | ❌ | ❌ | ✅ (none needed) | NOT READY — service required |
| Claude-Mem | ✅ | ✅ | ❌ | ❌ | ✅ (none needed) | NOT READY — service required |
| Agent Reach | ✅ | ✅ | ❌ | ❌ | ✅ (none needed) | NOT READY — service + manifest required |
| FreeLLMAPI | ✅ | ✅ | ⚠️ (client exists) | ❌ | ❌ | NOT READY — server + env vars required |
| Anthropic | ✅ | N/A | ✅ (proxy) | ⚠️ (proxy only) | ❌ (no direct key) | PARTIALLY — proxy works, direct key absent |
| OpenAI | ✅ | N/A | ❌ | ❌ | ❌ | NOT READY — API key required |
| Dashboard | ✅ | N/A | ✅ | ✅ | ✅ | READY |
| Self-Loop | ✅ | N/A | ✅ | ✅ | ✅ | READY |
| Self-Prompt | ✅ | N/A | ✅ | ✅ | ✅ | READY |

---

## Key Findings

1. **0 of 12 external integrations have real resources present.** All are MOCK.
2. **0 of 10 credential sets are configured.** Zero external API keys/tokens present.
3. **2 integrations are internally ready** (Dashboard, Self-Loop/Self-Prompt) — they require no external resources.
4. **1 integration is partially ready** (Hermes ACP) — binary present, config incomplete (`acp.cwd` empty).
5. **All adapter code is IMPLEMENTED.** The gap is purely in user-provided resources and credentials.
6. **All MCP configs point to mock servers.** No production MCP endpoints are configured.
7. **3 adapters have real-mode paths that raise errors** (Supabase, n8n, ObsidianGit) — stubs awaiting real implementation.
8. **Hermes ACP/MCP bypass the standard real-mode gate** — by M13 terminal-separation design, not a bug.
9. **Test baseline: 2,241 tests collected** across 130 test files (47 integration, 70 unit, 11 security, 2 performance).
10. **No security vault is configured** (GAP-SEC-01 through GAP-SEC-05 remain open from M11 audit).
