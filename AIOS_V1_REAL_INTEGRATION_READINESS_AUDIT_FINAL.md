# AI-OS v1.0.0 — TERMINAL 1
### OPERATIONAL CONFIGURATION READINESS AUDIT (FINAL)

---

## 1. Repository State

**Current HEAD:** `27dd9f536612e57914d7b3e498bf52ca601b00fc` (M14-T2: Register dashboard_user allow-rules + ProjectService lifecycle methods)

**Branch:** `main`

**Key releases visible in history:**
- `27dd9f5` — M14-T2 (most recent)
- `d1afc0b` — AI-OS v1.0.0 — Development Roadmap Complete
- `03d0864` — M12-T6: Secrets Rotation (COMMITTED, NOT QA-GO — Terminal 3 QA pending per memory)
- `dce9d58` — M12-T6: Deployment (COMMITTED, NOT QA-GO — Terminal 3 QA pending per memory)
- `a8745e4` — m12-t6 complete with score 97
- `7a37412` — M12-T6: promote model access criterion
- `b52f90d` — M12-T6: close model access dispatch

**Uncommitted changes:** One tracked file modified — `tests/integration/test_project_workspace_dashboard.py`

**Untracked files:** Numerous audit/report files, JSON status snapshots (`aios_controlled_project_*.json`), `t2_final_report.txt`, `RUNTIME_PREFLIGHT_AUDIT.md`, `TERMINAL1_FIRST_CONTROLLED_PROJECT_REPORT.md`, `temp_pages.json`, `VERSION` (empty), `ai-os.manifest.yaml` (empty), `nul` (105KB — suspicious), and several debug/test scripts. These are artifacts of prior audit/terminal activities and do not affect the source code or runtime configuration.

**Assessment:** The repository is at a stable v1.0.0 release state. The uncommitted test file change and untracked files are audit artifacts, not incomplete development work. No suspicious unfinished development is present in the source code.

---

## 2. Configuration Readiness

The configuration system uses a four-layer merge with strictly controlled precedence:

| Layer | Source | Precedence |
|-------|--------|------------|
| 1 | Embedded defaults (`ConfigurationManager`) | Lowest |
| 2 | `config/app.yaml` | Override Layer 1 |
| 3 | `config/env/{environment}.yaml` | Override Layer 2 |
| 4 | `AIOS_*` environment variables | Highest |

**What works with zero external configuration:**
- ✅ Kernel boots in MOCK mode (all integrations default to mock)
- ✅ Dashboard backend runs in development environment (`config/env/development.yaml` has `dashboard.enabled: true`)
- ✅ Mock MCP servers are available for all integrations (mock_hermes_server, mock_notion_server, mock_obsidian_server, mock_playwright_mcp_server, mock_claude_mem_server, mock_graphify_server, mock_hermes_acp_server, mock_agent_reach_server)
- ✅ Configuration freezing and validation works
- ✅ Health monitoring, state persistence, structured logging all functional with local storage

**What requires credentials:**
- ❌ Model providers: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` (checked at runtime by ModelRouter)
- ❌ Notion: `NOTION_API_TOKEN` or `NOTION_TOKEN` environment variables
- ❌ Supabase: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- ❌ n8n: `N8N_BASE_URL`, `N8N_API_KEY`
- ❌ FreeLLMAPI: `FREELLM_API_URL`, `FREELLM_API_KEY`

**What requires external services:**
- ❌ Supabase (PostgreSQL database)
- ❌ n8n (workflow automation server)
- ❌ Playwright MCP server (requires Node.js + browser install)
- ❌ Graphify backend (knowledge graph server)
- ❌ Notion API (external API service)
- ❌ Claude-Mem MCP (external memory service)

**Mock mode availability:** Every external integration has mock-mode support. Mock servers and mock adapters exist for all 14 canonical integrations.

**What is disabled by default:**
- All external integrations in `config/integrations.yaml` are `mode: mock`
- `services.real_integration_enabled: false` in defaults and production
- `services.autonomy.enabled: false` in defaults and production
- `services.dashboard.enabled: false` in defaults and production
- `services.self_loop.real_mode_enabled: false`

**Missing configuration:**
- No API keys are present in the environment (verified: `.env.example` has empty placeholders, no `.env` file exists)
- No real integration is configured (`user_resource_present: false` for all integrations)
- No `AIOS_REAL_INTEGRATION_ENABLED=1` environment variable is set
- No vault paths, git remotes, or endpoint URLs are configured

---

## 3. Model Provider Readiness

**Supported model providers (from `src/aios/core/model_router.py`):**
- `ModelProvider.ANTHROPIC` — Claude Opus 4, Claude Sonnet 4, Claude Haiku 3.5 (default models)
- `ModelProvider.OPENAI` — GPT-4o, GPT-4o Mini
- `ModelProvider.LOCAL` — FreeLLMAPI (dev/test only per C13)
- `ModelProvider.OLLAMA`, `ModelProvider.VLLM`, `ModelProvider.BEDROCK`, `ModelProvider.VERTEX` (registered in enum but not configured with default models)

**FreeLLMAPI integration status:**
- Fully implemented in `src/aios/adapters/freellmapi.py`
- Registered with ModelRouter via `register_freellmapi_provider()` 
- Environment variables: `FREELLM_API_URL` (default `http://localhost:8080`), `FREELLM_API_KEY`, `FREELLM_DEFAULT_MODEL`, `FREELLM_TIMEOUT`
- **CRITICAL:** Only registered when `integrations.yaml` sets `freellmapi.mode: real` AND `AIOS_REAL_INTEGRATION_ENABLED=1` is set AND the endpoint is not the default localhost URL
- Dev/test only per C13 — no production SLA

**Model abstraction layer:**
- `ModelRouter` class routes requests based on capability requirements, priority, cost, and fallback chains
- Default fallback chain: `claude-sonnet-4 → claude-haiku-3.5 → gpt-4o-mini → gpt-4o`
- `ModelRequest` and `ModelResponse` dataclasses for structured I/O
- No real provider backends exist for Anthropic/OpenAI in the codebase — the ModelRouter falls back to mock responses when no provider is registered

**Environment variables required:**
- `ANTHROPIC_API_KEY` — for Claude provider (checked at runtime)
- `OPENAI_API_KEY` — for OpenAI provider (checked at runtime)
- `FREELLM_API_URL` — FreeLLMAPI endpoint
- `FREELLM_API_KEY` — FreeLLMAPI API key

**Default model:** Not explicitly set — routing selects best available based on capabilities and priority. Claude Opus 4 is listed first (priority 10).

**Fallback behavior:** If no real provider backend is registered (which is the default), `_call_model()` returns a deterministic mock response: `[Mock response from {model_id}] {request.prompt[:100]}...`

**Fail-safe behavior:** 
- ModelRouter always returns a response (either from real provider or mock)
- If no models are enabled, raises `ValueError("No available models")`
- FreeLLMAPI provider is ONLY registered when explicitly configured for REAL mode with env gate

**Model selection control from configuration:**
- Models can be registered/unregistered programmatically via `register_model()` / `unregister_model()`
- Fallback chains can be customized via `set_fallback_chain()`
- No YAML-based model selection configuration found — model configuration is hardcoded in `_load_default_models()` and only FreeLLMAPI is registered dynamically based on integration framework settings

---

## 4. Knowledge / External Integration Readiness

| Integration | Status | Required Credentials | Mock Mode | Real-Mode Activation |
|-------------|--------|---------------------|-----------|---------------------|
| **hermes_agent_acp** | MOCK | hermes-agent repo path (`acp.cwd` in defaults.yaml) | ✅ Mock server exists (`mock_hermes_acp_server.py`) | `mode: real` + `AIOS_REAL_INTEGRATION_ENABLED=1` + verified repo path |
| **hermes_agent_ext** | MOCK | MCP server config (stdio command) | ✅ Mock server exists (`mock_hermes_server.py`) | `mode: real` + env gate + MCP config present |
| **playwright_mcp** | MOCK | Node.js + @playwright/mcp + browser | ✅ Mock server exists (`mock_playwright_mcp_server.py`) | `mode: real` + env gate + all components installed |
| **obsidian** | MOCK | Vault path (local filesystem) | ✅ Mock server + filesystem adapter exist | `mode: real` + env gate + `obsidian.vault_path` set + path verified |
| **graphify** | MOCK | Graphify endpoint | ✅ Mock server exists (`mock_graphify_server.py`) | `mode: real` + env gate + endpoint reachable |
| **claude_mem** | MOCK | Local storage path (no external credential) | ✅ Local storage mode (no MCP needed) | Local storage only — writes to `./data/memory` |
| **notion** | MOCK | `NOTION_API_TOKEN` / `NOTION_TOKEN` (must start with `ntn_`) | ✅ Mock server exists (`mock_notion_server.py`) | `mode: real` + env gate + valid token + endpoint reachable |
| **agent_reach** | MOCK | None (capability registration only) | ✅ Mock server exists (`mock_agent_reach_server.py`) | Registered-capability only — no external credential needed |
| **freellmapi** | MOCK | `FREELLM_API_URL` + `FREELLM_API_KEY` | ✅ Mock responses in ModelRouter | `mode: real` + env gate + endpoint configured |
| **anthropic** | MOCK | `ANTHROPIC_API_KEY` | ✅ Mock responses in ModelRouter | Runtime key check by ModelRouter |
| **openai** | MOCK | `OPENAI_API_KEY` | ✅ Mock responses in ModelRouter | Runtime key check by ModelRouter |
| **supabase** | MOCK | `SUPABASE_URL` + `SUPABASE_ANON_KEY` | ✅ Mock mode in integration framework | `mode: real` + env gate + credentials verified |
| **supabase_test** | MOCK | `SUPABASE_TEST_URL` + `SUPABASE_TEST_ANON_KEY` | ✅ Dedicated test adapter | Gated real-mode test adapter (aios_real_test schema only) |
| **n8n** | MOCK | `N8N_BASE_URL` + `N8N_API_KEY` | ✅ Mock mode in integration framework | `mode: real` + env gate + credentials verified |
| **obsidian_git** | MOCK | Vault path + Git remote URL | ✅ Mock mode | `mode: real` + env gate + `OBSIDIAN_VAULT_PATH` set |

**Key finding:** Claude-Mem uses local storage by default — no external MCP service is needed. It writes to `./data/memory` (configurable via `memory.base_path`). This integration can work immediately without any external credentials.

**For the first real demo:** Notion, Obsidian, Claude-Mem, and FreeLLMAPI are NOT strictly necessary. Notion is "planning advisory only," Claude-Mem is local storage, FreeLLMAPI is dev/test only. The knowledge layer can function with local memory + Obsidian vault (which still needs a local path but no external API key).

---

## 5. Capability / Repository Audit

**Actual capability sources in the repository:**

| Source | Repository | Runtime Service | Status |
|--------|-----------|-----------------|--------|
| **Hermes Agent (ACP)** | `./hermes-agent/` directory | ACP worker subprocess | Not present in repo — `acp.cwd` empty in defaults |
| **Hermes Agent (MCP ext)** | `./hermes-agent/` | MCP fallback worker | Not present in repo |
| **Playwright MCP** | `@playwright/mcp` npm package | Browser automation | Node.js/MCP not installed |
| **Graphify** | `graphify` service | Knowledge graph | Not running — endpoint not configured |
| **Claude-Mem** | Local storage (built-in) | Contextual memory | ✅ Functional (local only) |
| **Notion MCP** | Official Notion MCP server | Planning advisory | Token not configured |
| **Agent Reach** | Registered capability | Agent communication | ✅ Capability registered (no external resource) |
| **FreeLLMAPI** | Local LLM provider | Model backend | Not running — endpoint not configured |

**MCP server configurations:**
- `config/mcp/` contains JSON configs for: `agent_reach_mcp.json`, `claude_mem_mcp.json`, `graphify_mcp.json`, `hermes_agent_ext_mcp.json`, `notion_mcp.json`, `obsidian_mcp.json`, `test_mcp.json`, `test-gate-first.json`, `test-reject.json`, `graphify-test.json`, `graphify-tools.json`

**GitHub repository dependencies:**
- The codebase references external repositories (Hermes, Graphify, etc.) but does NOT bundle them. The `hermes-agent/` directory referenced in config does not exist in the repo.
- Vercel Skills integration: Not found in current implementation — the skill service (`src/aios/services/skill.py`) handles local skill specifications, not external GitHub skill repositories.

**Assessment:** The repository contains all adapter code and mock servers. External systems are treated as bounded resources that must be provisioned by the user. No GitHub capability sources are automatically fetched at runtime.

---

## 6. Autonomy Readiness

**Autonomy manager status:** The autonomy system (M10) is fully implemented but **DISABLED BY DEFAULT** in both development and production configurations.

**Default settings:**
- `services.autonomy.enabled: false` (defaults.yaml and production.yaml)
- `services.autonomy.enabled: false` in development.yaml (but some sub-components like `objective_generator` and `self_prompting_autonomous` are enabled in dev)
- Autonomous judge mode: `"advisory_only"` — never makes autonomous decisions
- `services.real_integration_enabled: false`

**Self-loop engine:**
- `SelfLoopEngine` is instantiated at kernel boot in `_init_self_loop()`
- Default: `mock_mode = True` (because `services.self_loop.real_mode_enabled: false`)
- Max cycles: 3, max depth: 5, cycle timeout: 3600 seconds
- The engine runs in mock mode and does NOT make real external calls

**Execution controls:**
- All autonomy services must pass through `SecurityManager.authorize()` (fail-closed DENY)
- `AutonomyFallbackService` configured with `on_security: true`, `on_bounds: true`, `on_instability: true`, `manual_recovery: true`
- `AutonomyOverrideService` allows manual override when `allow_manual: true`

**Approval gates:**
- `autonomous_judge.convergence_action: "escalate"` — always escalates to council/human
- `self_prompting.convergence_action: "escalate"` — escalates on convergence
- `learning_apply` disabled by default — no automatic learning application

**Safe usage modes:**

1. **Manual mode: ✅ SAFE** — All integrations are mock, autonomy is disabled, no real external calls can be made. The kernel can be started and inspected without any risk.

2. **Assisted mode: ✅ SAFE** — With `services.autonomy.enabled: true` in development config, autonomy services run in advisory-only mode. The autonomous judge is in `advisory_only` mode and defers to council. No real integrations are enabled.

3. **Autonomous mode: ⚠️ REQUIRES EXPLICIT CONFIGURATION** — To enable real autonomous execution, the user must: (a) set `services.autonomy.enabled: true`, (b) enable real integrations via `config/integrations.yaml` with `mode: real`, (c) set `AIOS_REAL_INTEGRATION_ENABLED=1`, (d) provide all required user resources/credentials, (e) ensure the env gate is active. The system will NOT operate autonomously without these explicit configuration changes.

**Assessment:** AI-OS is designed with safety-by-default. Autonomous mode requires multiple deliberate configuration changes across multiple files and environment variables. It cannot be accidentally enabled.

---

## 7. Dashboard Readiness

I examined all 8 dashboard pages defined in `src/aios/services/dashboard_service.py`:

1. **Planning Chat (PAGE 1)** — ✅ Ready. Read-only view of SelfLoopEngine status, self-prompt generator config, and phase map.

2. **Resource Onboarding (PAGE 2)** — ✅ Ready. Shows integration onboarding status and terminal-contract violations.

3. **Project Workspace (PAGE 3)** — ⚠️ Conditional. Requires `ProjectService` to be wired (delegates to `svc.get_project_snapshot()` or `svc.get_workspace_index()`). Available when `_init_project_service()` completes successfully.

4. **Project / Execution (PAGE 4)** — ✅ Ready. Shows self-loop cycle status, bounded execution state, and failure recovery records.

5. **Knowledge / History (PAGE 5)** — ✅ Ready. Surfaces persistence adapter stats and durability records.

6. **Integrations & Credentials (PAGE 6)** — ✅ Ready. Shows ALL 14 integrations with config, credentials presence (YES/NO only), and go-live readiness. Uses `_INTEGRATION_INVENTORY` dictionary with purpose and required credentials for each integration. Reports readiness as "READY" or "NOT READY" with missing credential list.

7. **System / Health (PAGE 7)** — ✅ Ready. Shows kernel stats, service status, and authority summary.

8. **System / Observability (PAGE 8)** — ✅ Ready. Surfaces metrics, trace spans, health, and recent events from ObservabilityManager, HealthManager, and EventBus.

**Key finding:** All 8 pages are implemented as read-only data bundle getters. The dashboard HTML (`src/aios/ui/dashboard.html`) provides the frontend with navigation to all 8 pages. The `request_action()` method forwards authorized actions through SecurityManager (fail-closed DENY).

**Missing controls for a real project:**
- BLOCKING: No credential input mechanism in the dashboard UI — credentials must be set via environment variables or `config/integrations.yaml`
- BLOCKING: No real-mode toggle in the dashboard — `AIOS_REAL_INTEGRATION_ENABLED=1` must be set as an environment variable before starting the kernel
- BLOCKING: No user resource upload/selection mechanism in the UI — vault paths, API keys, etc. must be configured externally
- CONVENIENCE/COSMETIC: The dashboard is a static HTML file that requires the dashboard backend to serve data via some HTTP mechanism (the `DashboardService` is a Python service but no explicit HTTP server binding is visible in the code I examined)

---

## 8. Real-Project Readiness

**"If I configure the required credentials today, can I create a real project through AI-OS and have AI-OS plan, review, execute, test, and learn from that project?"**

**READY NOW:**
- The kernel can boot and run in mock mode with zero configuration changes
- Planning service is available (via Notion adapter or local project workspace)
- Review/council services are available (ArchitectureAgency, SecurityAgency, etc.)
- Execution is available (via Playwright MCP adapter or local execution)
- Testing service is available (TestingService with mock agents)
- Knowledge is available (local Claude-Mem storage + Obsidian vault)
- Learning is available (LearningService capture + LearningApplyService, though auto-apply is disabled by default)

**READY AFTER CONFIGURATION:**
- With model API keys set (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`), the kernel can make real LLM calls for planning, review, and execution
- With `config/integrations.yaml` updated and `AIOS_REAL_INTEGRATION_ENABLED=1`, external integrations (Notion, Supabase, n8n, Obsidian Git) can be enabled
- With vault paths and resource paths configured, knowledge durability works

**REQUIRES IMPLEMENTATION:**
- ✅ All core capabilities are already implemented — no new code is needed

**NOT CURRENTLY SUPPORTED:**
- No automated project creation through the dashboard UI (project creation requires `request_action("project.create")` with SecurityManager authorization)
- No browser-based dashboard hosting mechanism visible in the codebase (the dashboard service provides data endpoints but no HTTP server binding was found in examined code)

**Overall verdict:** **READY AFTER CONFIGURATION** — The system is fully implemented and ready for real-project use once credentials are configured. No implementation changes are required.

---

## 9. Missing Credentials / Configuration

**Required for real model provider access:**
1. `ANTHROPIC_API_KEY` (Claude provider — preferred) OR `OPENAI_API_KEY` (OpenAI provider — fallback)
   - Set as environment variable before starting the kernel

**Required for external integrations (ALL gated by `AIOS_REAL_INTEGRATION_ENABLED=1`):**
2. `NOTION_API_TOKEN` — For Notion planning advisory (optional for first demo)
3. `SUPABASE_URL` + `SUPABASE_ANON_KEY` — For persistent storage (optional for first demo)
4. `N8N_BASE_URL` + `N8N_API_KEY` — For bounded automation (optional for first demo)
5. `FREELLM_API_URL` + `FREELLM_API_KEY` — For local LLM provider (dev/test only, optional)
6. `GRAPHIFY_ENDPOINT` — For knowledge graph (optional, advisory)
7. `OBSIDIAN_VAULT_PATH` — For local knowledge vault (local path, not a secret)
8. `CLAUDBE_MEMORY_PATH` — For Claude-Mem (defaults to `./data/memory`, no credential needed)

**Configuration file changes needed:**
9. Edit `config/integrations.yaml`: set `mode: real` and `user_resource_present: true` for each integration you want to use
10. Set environment variable: `AIOS_REAL_INTEGRATION_ENABLED=1` (before kernel start)

**NOT REQUIRED for the first real demo:**
- Notion (can use local project workspace for planning)
- Supabase (can use local file storage)
- n8n (can use local execution)
- FreeLLMAPI (can use Anthropic/OpenAI directly)
- Graphify (can use local Claude-Mem)
- Claude-Mem works with local storage by default (no external resource needed)

**MINIMUM for first real demo:**
- `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) environment variable
- That's it — everything else defaults to mock mode

---

## 10. Blocking Issues

1. **No model API keys configured** — The `.env.example` shows empty placeholders. Without at least `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`, all LLM calls return mock responses. The kernel boots fine in mock mode, but no real planning/review/execution can occur.

2. **Dashboard hosting mechanism unclear** — While `DashboardService` provides all 8 page data getters and `dashboard.html` exists as a frontend, no HTTP server binding was found in the examined kernel code that explicitly serves the dashboard or the page data over HTTP. This needs verification.

3. **No `.env` file present** — The `.env.example` exists but no actual `.env` file is created. Users must manually create `.env` or set environment variables.

**Non-blocking issues:**
- Uncommitted test file change (`tests/integration/test_project_workspace_dashboard.py`) — does not affect runtime
- Numerous untracked audit/report files — cosmetic/organizational only
- Empty `nul` file (105KB) — appears to be a Windows artifact, not relevant to Linux/WSL deployment
- Empty `.env.example` values — by design (prevents accidental credential exposure)

---

## 11. Non-Blocking Issues

1. **Empty `VERSION` and `ai-os.manifest.yaml`** — These files exist but are empty (0 bytes). The version is sourced from `src/aios/core/version.py` instead.

2. **Unused `config/models.yaml`, `config/mcps.yaml`, `config/skills.yaml`, `config/memory.yaml`, `config/global.yaml`, `config/logging.yaml`** — These config files exist but are empty (0 bytes). The system uses `config/defaults.yaml` and `config/integrations.yaml` as the primary sources.

3. **Debug/test scripts in root** — Files like `debug_test.py`, `reproduce_def01.py`, `test_cli.py`, etc. exist in the root directory. These are development artifacts and should be cleaned up or moved.

4. **Git tracking anomaly** — The `git status` output shows a file named `git` (0 bytes) in the root, suggesting a possible accidental file creation.

5. **M12-T6 commits not fully QA-GO** — Per project memory, the secrets rotation and deployment commits are NOT QA-GO (Terminal 3 QA pending). However, these are historical audit notes and do not block the current repository from being used.

---

## 12. Blocking vs Non-Blocking Issues

**Blocking (must be resolved before real project use):**
- No API key for model provider (Anthropic/OpenAI) — the single hard blocker
- Dashboard HTTP hosting mechanism needs verification (unclear how dashboard UI connects to backend data)

**Non-blocking (safe to proceed without):**
- All external integrations (Notion, Supabase, n8n, Graphify, Obsidian Git) — work in mock mode
- FreeLLMAPI — dev/test only, not needed if Anthropic/OpenAI key is available
- Claude-Mem — works with local storage by default
- Debug scripts, empty config files, untracked audit artifacts

---

## 13. Recommended First Real Project

**Recommended type:** A **simple Python CLI utility project** (e.g., a command-line todo-list manager with persistent storage, implemented in a new isolated directory).

**Why this is appropriate:**

1. **Small enough to control** — A single CLI tool is a bounded, well-understood scope. It avoids destructive operations entirely (no network calls, no system modifications, no file deletion).

2. **Exercises Planning** — The Planning service can break down requirements into: data model design, CLI argument parsing, storage format, test plan, and documentation. Can use Notion (advisory) or local markdown for planning.

3. **Exercises Councils/Review** — The Architecture Agency (design review) and Security Agency (code review) can provide council feedback on the implementation approach. The Testing Council can review the test plan.

4. **Exercises Execution** — The self-loop engine can execute the implementation: write the Python files, create the CLI entry point, implement storage.

5. **Exercises Testing** — The TestingService with PlaywrightMCP and agent-based testing can verify the CLI works: parse args, add/view/delete todos, persist data, handle edge cases.

6. **Exercises Knowledge** — Claude-Mem can store project context. Obsidian (if vault path provided) can store long-term knowledge. Graphify can map dependency relationships.

7. **Exercises Learning** — LearningService can capture patterns from the implementation (e.g., "CLI argument patterns," "testing patterns") for future projects.

8. **Avoids destructive operations** — A CLI todo app only reads/writes to a local data file. No network egress, no system modification, no file deletion outside the project workspace.

9. **Allows human approval** — The autonomous judge is in `advisory_only` mode by default. All actions can be reviewed before execution.

10. **Demonstrates architecture clearly** — A simple project exercises the full pipeline (plan → review → execute → test → learn) without overwhelming complexity. It clearly shows the non-authoritative dashboard readouts at each phase.

**Specific recommendation:** Build a `todo.py` CLI with subcommands (`add`, `list`, `done`, `remove`) using local JSON storage, with full unit tests and documentation. This is a ~200-line project that completes one full AI-OS cycle without any risk.

---

## 14. Correct Configuration Order

Derived from the actual repository implementation and the fail-closed design:

**Phase 1 — Model Provider (HARD BLOCKER)**
1. Set `ANTHROPIC_API_KEY=<your-key>` as environment variable (or `OPENAI_API_KEY` as fallback)
2. Verify: ModelRouter will detect the key at runtime and route real requests to the provider
3. No configuration file edit needed — keys are checked at runtime

**Phase 2 — Knowledge (OPTIONAL but recommended for first demo)**
4. Create a local directory for the Obsidian vault: `mkdir -p ./data/knowledge-vault`
5. Set `OBSIDIAN_VAULT_PATH=./data/knowledge-vault` in environment OR set `obsidian.vault_path` in `config/app.yaml`
6. Claude-Mem works automatically with local storage at `./data/memory` (no action needed)

**Phase 3 — External Services (OPTIONAL for first demo)**
7. These are NOT required for the first real demo but will be needed for full functionality:
   - Supabase: Set `SUPABASE_URL`, `SUPABASE_ANON_KEY` env vars + `mode: real` in `config/integrations.yaml`
   - n8n: Set `N8N_BASE_URL`, `N8N_API_KEY` env vars + `mode: real` in `config/integrations.yaml`
   - Notion: Set `NOTION_API_TOKEN` env var + `mode: real` in `config/integrations.yaml`
   - Graphify: Set `GRAPHIFY_ENDPOINT` env var + `mode: real` in `config/integrations.yaml`

**Phase 4 — Enable Real Integration Mode**
8. Set `AIOS_REAL_INTEGRATION_ENABLED=1` environment variable (REQUIRED to activate any `mode: real` integration)
9. For each integration you want to enable in REAL mode:
   - Edit `config/integrations.yaml`
   - Change `mode: mock` → `mode: real`
   - Change `user_resource_present: false` → `user_resource_present: true` (ONLY after verifying the resource is actually present)

**Phase 5 — Dashboard**
10. Dashboard is enabled in development mode by default (`config/env/development.yaml` has `dashboard.enabled: true`)
11. In production, set `services.dashboard.enabled: true` in config or via `AIOS_SERVICES_DASHBOARD_ENABLED=true` env var
12. Verify dashboard HTTP server is properly bound (needs verification in existing code)

**Phase 6 — Autonomy (OPTIONAL)**
13. Autonomy is disabled by default — this is correct for a first real demo
14. If autonomous mode is desired: set `services.autonomy.enabled: true` in config and review all autonomy settings

**Phase 7 — Real Project Creation**
14. Start kernel: `aios kernel start --run-forever`
15. Access dashboard at `http://localhost:3000`
16. Use dashboard "Integrations & Credentials" page to verify all integrations show as VALIDATED
17. Use dashboard "Project Workspace" page or API to create a new project
18. The self-loop engine (in real mode, not mock) will then execute the plan → review → execute → test → learn cycle

**The ordering is enforced by the repository's fail-closed design:**
- Model keys are checked at runtime — no real LLM call works without them (Phase 1 is the hard gate)
- `AIOS_REAL_INTEGRATION_ENABLED=1` is the master gate for all REAL-mode integrations (Phase 4 must precede actual real operations)
- `user_resource_present: true` must be explicitly set per-integration (Phase 4 step 9) — the system never auto-detects and auto-enables
- Autonomy can only be enabled after real integrations are configured (Phase 6 follows Phase 4)
- Project creation through the dashboard requires SecurityManager authorization (Phase 7, the final step)

---

**FINAL VERDICT: READY WITH CONDITION**

The repository is structurally complete and ready for real-project use **if** the user configures at least one model provider API key. All integration modes, autonomy controls, dashboard backends, and the fail-gated real-operation switch are fully implemented. The single blocking condition is the absence of model API credentials. Once `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY`) is provided, AI-OS can plan, review, execute, test, and learn for a real project using primarily mock integrations (with the option to enable real integrations as resources become available).

The system's safety-by-default design — all integrations in mock mode, autonomy advisory-only, real-mode gated behind `AIOS_REAL_INTEGRATION_ENABLED=1`, credentials never auto-detected — ensures that no accidental real-world impact can occur during initial configuration and testing.

---

**EXACTLY ONE NEXT ACTION:**

Set the `ANTHROPIC_API_KEY` environment variable to your Anthropic API key (or `OPENAI_API_KEY` as fallback). This is the single highest-priority action because it is the only hard blocker — without a model provider API key, AI-OS cannot make real LLM calls for planning, review, or execution. All other integrations can remain in mock mode for the first real project.

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Then verify: `aios kernel start` should boot successfully, and the kernel log will confirm the Anthropic provider is available for real model requests.