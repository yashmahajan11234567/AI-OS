# REAL EXTERNAL INTEGRATIONS — IMPLEMENTATION PLAN

**AI-OS · Real External Integration Readiness + Connection Plan (companion to `REAL_EXTERNAL_INTEGRATIONS_READINESS_REPORT.md`)**
**Date:** 2026-08-27
**Author:** Terminal 2 — planning only. **No code or configuration was changed in producing this plan.**
**Principle:** IMPLEMENTED ≠ CONFIGURED ≠ CONNECTED ≠ OPERATIONALLY VERIFIED. Only a real successful external operation moves an integration to OPERATIONALLY VERIFIED.

---

## 0. READINESS SNAPSHOT (from the companion report)

| Integration | IMPLEMENTED | CONFIGURED | CONNECTED | OPERATIONALLY VERIFIED | Classification |
|---|:--:|:--:|:--:|:--:|:--|
| Notion | ✅ | ✅(mock) | ❌ | ❌ | E + G |
| Obsidian | ✅ | ✅(mock+real-fs path) | ⚠️(local fs code-complete) | ❌ | A |
| FreeLLM | ✅(code) | ⚠️(not at boot) | ❌ | ❌ | D + E + G |
| Hermes/ACP | ✅ | ✅(mock) | ❌ | ❌ | B + D |
| Graphify | ✅ | ✅(mock) | ❌ | ❌ | B + C + G |
| Claude-Mem | ✅ | ✅(mock) | ❌ | ❌ | A + G |
| Playwright | ✅ | ✅(mock) | ❌ | ❌ | B |
| ACP | ✅(code-complete) | ⚠️(allowlist) | ❌ | ❌ | B + D |

---

## 1. PRECONDITIONS (must hold before ANY real connection)

1. **No production code is modified during planning.** This plan is the artifact; execution is a separate, gated phase.
2. **Mock infrastructure is preserved.** Tier A/B tests (`tests/integration/test_m8_*.py`, `test_m8_t6_*.py`) must keep passing. Real-path tests are **additive** (`@pytest.mark.gated` + env-gated), never replacements.
3. **Security gaps S1–S3 (see §3) are closed before any Tier C / ungated real connection.** Closing them must not weaken existing tests.
4. **M7 frozen, M8–M12 boundaries preserved, no M13.**

---

## 2. SECURITY GAP REMEDIATION (do this FIRST — §3 of report)

| ID | Gap | Fix (code change, additive) | Where |
|---|---|---|---|
| **S1** | ACP subprocess path bypasses `validate_mcp_server_before_connect` | Route `AcPAdapter.connect` through `security_manager.validate_mcp_server_before_connect` before spawning the subprocess (reuse `MCPServerSecurityGate`). | `acp_adapter.py:185-227` |
| **S2** | Playwright `_connect_direct` bypasses the same gate | Invoke the gate on a synthesized `MCPServerConfig` before launching the real `@playwright/mcp` subprocess. | `playwright_mcp_adapter.py:185` |
| **S3** | M10 autonomy self-permits via ABAC, bypassing `SecurityManager.authorize` | Confirm acceptable (autonomy is gated `services.autonomy.enabled=False` by default) OR add a fail-closed `SecurityManager.authorize` check inside `authorize_autonomous_action`. | `security_abac_ext.py:324-325` |
| **S4** | No central secret redaction over `TestingEvidence`/exceptions | Add a `redact_secrets()` utility used by `testing_evidence.py` and exception formatting. | new util + `testing_evidence.py` |
| **S5** | Capability double-registration (kernel `.register` + manifest `register_capability`) | Make one path authoritative; skip manifest IDs already registered, or remove kernel `.register` calls. Verify no `CM-DUP-001`. | `kernel.py:1012-1108` |

> These are the **only** recommended code changes. They are security-hardening only — they do not alter adapter behavior or test expectations.

---

## 3. EXACT IMPLEMENTATION SEQUENCE

### PHASE A — Foundations (automated by Terminal 2, after user provides prereqs)

**STEP A1 — Close security gaps S1–S5** (§2). Run full regression; all existing tests must stay green. *No new integration yet.*
**STEP A2 — Create the gated real-test harness.** Add `tests/integration/real/` with one env-gated test per integration (`HERMES_ACP_TEST`, `PLAYWRIGHT_E2E_TEST`, `GRAPHIFY_E2E_TEST`, `NOTION_REAL_TEST`, `OBSIDIAN_REAL_TEST`, `CLAUDE_MEM_REAL_TEST`, `FREELLM_REAL_TEST`). Each `@pytest.mark.gated` + skips unless its env flag is set. These tests are committed but **never execute by default**.

### PHASE B — Obsidian (the only Tier-B-ready, no-credential integration)

**STEP B1 (USER)** — Create or designate a real local Obsidian vault directory (e.g. `./data/vaults/default`). Populate with a few harmless `.md` notes.
**STEP B2 (TERMINAL 2)** — Set `obsidian.vault_path` in app config to that directory (`kernel.py:1287` reads it). Do **not** remove the mock MCP json; the adapter tries MCP then falls back to filesystem (`obsidian_adapter.py:187`).
**STEP B3** — Run the Obsidian real-filesystem gated test (`search_notes`/`get_note` against the real vault).
**STEP B4 (TERMINAL 2)** — Confirm `retrieval_path="filesystem"`, `trust_level=trusted_contextual`, path-traversal blocked. Collect evidence.
**STEP B5 (TERMINAL 3)** — Independently verify the real vault read. **This is the first achievable OPERATIONALLY VERIFIED integration** (Tier B, local-only, no external service).

### PHASE C — Playwright (Tier B, needs local install)

**STEP C1 (USER)** — Install Node.js; `npm i -g @playwright/mcp`; `pip install .[browser]`; `playwright install` (download browser binaries).
**STEP C2 (TERMINAL 2)** — Ensure `HERMES_MOCK_PLAYWRIGHT` is **unset** so `_find_playwright_command` picks the real server (`playwright_mcp_adapter.py:697-709`). Optionally add `config/mcp/playwright_mcp.json` if the injected-MCPManager path is desired.
**STEP C3** — Run `test_real_browser_e2e` with `PLAYWRIGHT_E2E_TEST=1`: navigate to a safe local/example page, screenshot, cleanup.
**STEP C4 (TERMINAL 3)** — Verify real browser session + cleanup. **→ OPERATIONALLY VERIFIED (Tier B).**

### PHASE D — Hermes / ACP (Tier B, code-complete, unconfigured)

**STEP D1 (USER)** — Confirm `hermes-agent/` is present (it is, gitignored). Optionally `pip install agent-client-protocol` (the `acp` SDK) into the AI-OS env.
**STEP D2 (TERMINAL 2)** — Construct `HermesBridge` with `cwd=<hermes-agent repo root>` and `protocol="acp"` (`hermes_bridge.py:139`, `acp_adapter.py:210`). Today the kernel passes **no `cwd`** (`kernel.py:959-963`), forcing the mock-MCP fallback — this is the one-line config/construction change needed.
**STEP D3** — After S1 is fixed, run `test_real_hermes_acp_conditional` with `HERMES_ACP_TEST=1` (currently a stub at `test_m8_hermes_acp.py:307-312` — must be implemented to drive the real `acp_adapter.entry`).
**STEP D4 (TERMINAL 3)** — Verify ACP handshake + session TTL + no verdict authority. **→ OPERATIONALLY VERIFIED (Tier B).** Cloud browser (Browserbase) stays Tier C / out of scope unless user provides creds.

### PHASE E — Graphify (Tier B/C, needs real server)

**STEP E1 (USER / clarification G)** — Confirm the real Graphify upstream (docs say `github.com/davioud/graphify` but **"(assumed)"**). User must confirm or supply the real Graphify MCP server.
**STEP E2 (USER)** — Install/launch the real Graphify MCP server locally.
**STEP E3 (TERMINAL 2)** — Point `config/mcp/graphify_mcp.json` `command` at the real server (`graphify_adapter.py` already connects via MCPManager).
**STEP E4** — Run Graphify gated E2E (`GRAPHIFY_E2E_TEST=1`) with `add_node`+`get_node` round-trip.
**STEP E5 (TERMINAL 3)** — Verify `authority=advisory_only`, `trust_level=untrusted`. **→ OPERATIONALLY VERIFIED.**

### PHASE F — Claude-Mem (Tier B, scope decision required — G)

**STEP F1 (USER decision)** — Resolve the master-plan contradiction: §14.2:455 / §20.3:746 say **"Do NOT integrate"** Claude-Mem, yet M8-T4 shipped `ClaudeMemAdapter` + `claude_mem_context`. Options: (a) keep it and treat as a real local tool, or (b) drop the adapter. This plan assumes (a) pending user confirmation.
**STEP F2 (USER)** — If kept: install/run the real `thedotmack/claude-mem` server locally.
**STEP F3 (TERMINAL 2)** — Point `config/mcp/claude_mem_mcp.json` `command` at the real server.
**STEP F4** — Run gated test; verify `trust_level=untrusted`, no kernel mutation.
**STEP F5 (TERMINAL 3)** — Verify. **→ OPERATIONALLY VERIFIED.**

### PHASE G — FreeLLM (Tier D/E, needs boot wiring + real endpoint)

**STEP G1 (TERMINAL 2, code change)** — Wire `register_freellmapi_provider(model_router, get_freellmapi_config_from_env())` into kernel/ModelRouter init so FreeLLM is actually registered (today it is **never called at boot** — only from `tests/unit/test_m5_gate.py`). Add `FREELLM_API_KEY`/`FREELLM_API_URL` to `.env.example`.
**STEP G2 (USER, clarification G)** — Confirm the real FreeLLM endpoint (docs "(assumed)" `github.com/free-llm-api`; it is an OpenAI-compatible proxy, dev/test-only per C13).
**STEP G3 (USER)** — Provide a running FreeLLM-compatible server at `FREELLM_API_URL` + `FREELLM_API_KEY`.
**STEP G4** — Run gated test: minimal chat completion.
**STEP G5 (TERMINAL 3)** — Verify response + error-path returns `ERROR` result. **→ OPERATIONALLY VERIFIED.**

### PHASE H — Notion (Tier C, needs account + credential — E/G)

**STEP H1 (USER, clarification G)** — Choose the real Notion integration target (official `makenotion/notion-mcp` vs REST). Docs only say `notion.so`.
**STEP H2 (USER)** — Create a Notion integration, obtain `NOTION_TOKEN`, grant access to a test page.
**STEP H3 (TERMINAL 2)** — Add `NOTION_TOKEN` to `config/mcp/notion_mcp.json` `env` and point `command` at the real server (tool schema must match `search_pages`/`get_page`/`create_page`/`update_page`/`query_database` — `notion_adapter.py:437-650`).
**STEP H4** — Run gated test: safe `search_pages` read.
**STEP H5 (TERMINAL 3)** — Verify response + no `NOTION_TOKEN` leakage. **→ OPERATIONALLY VERIFIED (Tier C).**

---

## 4. FINAL OUTPUT — ANSWERS A–O

**A. Integration status matrix** — see §0 snapshot + companion report §0/§2.1.

**B. Missing credentials**
- `NOTION_TOKEN` (ABSENT)
- `FREELLM_API_KEY` (ABSENT; also omitted from `.env.example`)
- `FREELLM_API_URL` (ABSENT)
- `OBSIDIAN_VAULT_PATH` (ABSENT — but no secret; just a directory)
- Graphify / Hermes / Claude-Mem / ACP / Playwright: no secret credentials required for the local Tier-B paths.

**C. Missing software / repositories**
- Node.js + `@playwright/mcp` + browser binaries (Playwright)
- `agent-client-protocol` SDK (Hermes ACP)
- Real Graphify MCP server (unconfirmed upstream)
- Real Claude-Mem server (`thedotmack/claude-mem`) — pending scope decision
- Real FreeLLM-compatible server (unconfirmed upstream)
- `hermes-agent/` is present but unreferenced by running code

**D. Missing configuration**
- `obsidian.vault_path` unset
- All `config/mcp/*.json` point at mocks
- `mcps.yaml` empty; `ai-os.manifest.yaml` 0 bytes
- Hermes bridge constructed without `cwd`/`protocol` (`kernel.py:959-963`)
- FreeLLM never registered at boot

**E. Required code changes** (security-hardening only; no adapter behavior change)
- S1: gate ACP subprocess (`acp_adapter.py:185`)
- S2: gate Playwright direct path (`playwright_mcp_adapter.py:185`)
- S3: confirm/close M10 self-permit (`security_abac_ext.py:324`)
- S4: central secret redaction (`testing_evidence.py` + exceptions)
- S5: capability double-registration (`kernel.py:1012-1108`)
- G1: wire FreeLLM at boot (`freellmapi.py` + kernel init)

**F. Required installation steps** — see Phases C1, D1, E1–E2, F2, G3.

**G. Required environment variables (names only)** — `NOTION_TOKEN`, `FREELLM_API_KEY`, `FREELLM_API_URL`, `FREELLM_TIMEOUT`, `FREELLM_DEFAULT_MODEL`, `OBSIDIAN_VAULT_PATH`, `HERMES_ACP_TEST`, `PLAYWRIGHT_E2E_TEST`, `GRAPHIFY_E2E_TEST`, `NOTION_REAL_TEST`, `OBSIDIAN_REAL_TEST`, `CLAUDE_MEM_REAL_TEST`, `FREELLM_REAL_TEST`, `HERMES_MOCK_PLAYWRIGHT` (unset for real).

**H. Real endpoints / commands**
- Obsidian: real vault dir via `obsidian.vault_path`
- Playwright: `node node_modules/@playwright/mcp/index.js` (unset `HERMES_MOCK_PLAYWRIGHT`)
- Hermes/ACP: `python -m acp_adapter.entry` (cwd=`hermes-agent/`)
- Graphify: real Graphify MCP server command in `graphify_mcp.json`
- Claude-Mem: real server command in `claude_mem_mcp.json`
- FreeLLM: `FREELLM_API_URL`/v1/chat/completions (OpenAI-compatible)
- Notion: real Notion MCP server command in `notion_mcp.json` + `NOTION_TOKEN`

**I. Operational test plan** — see companion report §6; one gated test per integration, all `@pytest.mark.gated` + env-gated, committed but never run by default.

**J. Security verification plan** — companion report §7 (13 checks) + gaps S1–S5 closed and re-verified; M7 boundaries untouched; M10 gated off by default.

**K. Exact implementation order** — A (security) → B (Obsidian, first verifiable) → C (Playwright) → D (Hermes/ACP) → E (Graphify) → F (Claude-Mem, post-decision) → G (FreeLLM) → H (Notion). Terminal 3 verifies after each phase.

**L. Expected blockers**
- Notion/FreeLLM/Graphify upstream identity unconfirmed (docs "(assumed)") → **user clarification required** (G).
- Claude-Mem scope contradiction (doc "do not integrate" vs shipped adapter) → **user decision required** (G).
- No real credentials/accounts → **user action required** (E).
- Playwright Node + browsers not installed in this env.

**M. What I (user) need to do manually**
- Create Notion integration + `NOTION_TOKEN`.
- Provide/confirm FreeLLM endpoint + `FREELLM_API_KEY`.
- Install Node + Playwright + browsers.
- Confirm or supply Graphify / Claude-Mem real servers.
- Create a real local Obsidian vault for the filesystem path.
- Resolve the four clarification items (G).

**N. What Terminal 2 can implement automatically**
- Close security gaps S1–S5 (after user prereqs).
- Add the gated real-test harness (additive, never default-running).
- Edit config files (mock→real command) once user supplies targets/creds.
- Wire FreeLLM at boot (G1).
- Collect operational evidence per phase.

**O. What Terminal 3 must independently verify**
- Each phase's real operation actually hit a **real** service/binary (not a mock).
- No secret leakage in logs/provenance/TestingEvidence.
- Security gates S1–S5 hold under real load.
- M7/M8–M12 boundaries preserved; no test weakened.
- Final OPERATIONALLY VERIFIED status per integration is earned, not asserted.

---

## 5. WHAT THIS PLAN DOES NOT DO

- It does **not** claim any integration is operational.
- It does **not** modify production code or configuration (planning artifact only).
- It does **not** replace mocks with real connections.
- It does **not** invent credentials, endpoints, repos, or services.
- It does **not** start M13 or touch M7.

**Only real, successful external operations — independently verified by Terminal 3 — move an integration from IMPLEMENTED/CONFIGURED to CONNECTED to OPERATIONALLY VERIFIED.**
