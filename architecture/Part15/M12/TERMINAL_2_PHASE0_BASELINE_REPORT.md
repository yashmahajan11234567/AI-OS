# Terminal 2 — FINAL EXTERNAL ECOSYSTEM INTEGRATION: PHASE 0 BASELINE & GAP REPORT

**Date:** 2026-08-27
**Authority:** Terminal 2 — Implementation Authority
**Status:** BASELINE ESTABLISHED — NO PRODUCTION CODE CHANGED YET

---

## 0. METHOD

Read all five authoritative documents (SPEC, MATRIX, OPERATIONAL_TEST_PLAN, USER_CHECKLIST,
READINESS_REPORT) plus the prior planning artifact `REAL_EXTERNAL_INTEGRATIONS_IMPLEMENTATION_PLAN.md`,
then performed direct code inspection (targeted `Read`/`Grep`/`Bash`) of the security subsystem,
integration adapters, kernel boot sequence, and config. Three fan-out explore agents were launched
but failed due to API overload (529); all findings below were gathered by direct inspection and are
cited with exact file:line.

**No code or configuration was modified during PHASE 0.**

---

## 1. EXISTING SUBSYSTEM STATE (verified)

### Adapters (all IMPLEMENTED at `src/aios/adapters/`)
| File | Class | Notes |
|------|-------|-------|
| acp_adapter.py | `AcPAdapter` | ACP stdio transport to hermes-agent |
| hermes_bridge.py | `HermesBridge` | ACP preferred / MCP fallback orchestration |
| playwright_mcp_adapter.py | `PlaywrightMCPAdapter` | @playwright/mcp (test path gates; direct path does not — S2) |
| graphify_adapter.py | `GraphifyAdapter` | knowledge graph |
| notion_adapter.py | `NotionAdapter` | planning |
| obsidian_adapter.py | `ObsidianAdapter` | filesystem primary + MCP secondary |
| claude_mem_adapter.py | `ClaudeMemAdapter` | contextual memory (advisory) |
| agent_reach.py | `AgentReach` | agent comm protocol |
| freellmapi.py | `FreeLLMAPIDataSource` (provider) | ModelRouter provider, dev/test only, NOT registered at boot (needs G1) |
| base.py | `BaseExecutionAdapter` | base pattern |

### Mock servers (preserved infra)
`mock_hermes_server.py`, `mock_hermes_acp_server.py`, `mock_obsidian_server.py`,
`mock_notion_server.py`, `mock_graphify_server.py`, `mock_claude_mem_server.py`,
`mock_agent_reach_server.py`, `mock_playwright_mcp_server.py`.

### MCP configs (`config/mcp/*.json`) — ALL POINT AT MOCKS
`hermes_agent_ext_mcp.json` → `mock_hermes_server`, `obsidian_mcp.json` → `mock_obsidian_server`,
`notion_mcp.json` → `mock_notion_server`, `graphify_mcp.json` → `mock_graphify_server`,
`claude_mem_mcp.json` → `mock_claude_mem_server`, `agent_reach_mcp.json` → `mock_agent_reach_server`.
**`playwright_mcp.json` does NOT exist** (adapter uses injected MCPManager or direct stdio).

### Config
- `config/defaults.yaml`: `capabilities.adapter_allowlist` (6 adapters), `acp.session_ttl_seconds: 0`,
  `services.autonomy.enabled: false`.
- `config/mcps.yaml`: EMPTY. `config/secrets.example.yaml`: EMPTY. `ai-os.manifest.yaml`: 0 bytes.

### Test harness (already present — reuse, do not reinvent)
- `pyproject.toml`: `gated` + `external` markers registered.
- `tests/integration/conftest.py:500` `is_gated_enabled(env_var)`, `:506` `gated(env_var)` skipif helper.
- Baseline: **1745 tests collected**.

### Security subsystem
- `src/aios/core/security_manager.py:1437` `validate_mcp_server_before_connect(config)` — the canonical gate.
- `src/aios/core/mcp_manager.py:254` MCPManager.connect already routes through the gate (C18 gate-before-connect).
- `MCPServerSecurityGate` (security_manager.py:571) validates transport/host/command/env/headers/params, fail-closed.

---

## 2. INTEGRATION STATE MATRIX (PHASE 0 — verified by inspection)

| Integration | IMPLEMENTED | CONFIGURED | CONNECTED | OPERATIONALLY VERIFIED | Current State |
|---|:--:|:--:|:--:|:--:|---|
| Hermes/ACP | ✅ | ✅(allowlist) | ❌ | ❌ | BLOCKED by S1 + cwd path |
| Hermes/MCP | ✅ | ✅(mock) | ❌ | ❌ | mock only |
| Playwright MCP | ✅ | ✅(mock) | ❌ | ❌ | BLOCKED by S2 + Node/browser |
| MCP Generic | ✅ | ✅(mock) | ❌ | ❌ | framework; mock servers only |
| Agent Reach | ✅ | ❌ | ❌ | ❌ | OPTIONAL, not registered as cap |
| SkillSpecTor | ✅ | ✅ | ❌ | ❌ | framework |
| Obsidian | ✅ | ✅(mock+fs code) | ⚠️(fs code, no vault) | ❌ | needs vault path |
| Graphify | ✅ | ✅(mock) | ❌ | ❌ | needs real server |
| Claude-Mem | ✅ | ✅(mock) | ❌ | ❌ | scope contradiction |
| Notion | ✅ | ✅(mock) | ❌ | ❌ | needs token + server choice |
| GSD Core | ✅ | ❌ | ❌ | ❌ | OPTIONAL/reference |
| FreeLLMAPI | ✅(code) | ⚠️(not at boot) | ❌ | ❌ | needs G1 boot wiring + endpoint |
| Anthropic/OpenAI | ✅ | ✅ | ⚠️(runtime, needs key) | ⚠️(needs user key) | real if key present |
| LLM/Review/Karpathy/Council Review | ✅ | ✅ | ❌ | ❌ | technique/perspective only |
| Reference repos (Ruflo…) | — | — | — | — | REFERENCE ONLY |

**0 integrations OPERATIONALLY VERIFIED with real external services.**

---

## 3. SECURITY GAP CONFIRMATION (S1–S5)

### S1 — ACP subprocess bypasses the gate  ✅ CONFIRMED
`AcPAdapter.connect()` (src/aios/adapters/acp_adapter.py:**185**) validates cwd + scrubs env, then
spawns the hermes-agent subprocess at line **220** (`asyncio.create_subprocess_exec`) with **no**
`validate_mcp_server_before_connect()` call. The gate is bypassed for the production ACP path.
**Remediation:** synthesize an `MCPServerConfig` from the resolved command/cwd and call
`get_security_manager().validate_mcp_server_before_connect(config)` immediately before line 220; fail
closed on `not result.passed`.

### S2 — Playwright direct connection bypasses the gate  ✅ CONFIRMED
`PlaywrightMCPAdapter._connect_direct()` (src/aios/adapters/playwright_mcp_adapter.py:**185**) spawns
`@playwright/mcp` at line **197** with **no** gate. The injected-MCPManager test path (line 159) *does*
gate; the production direct path does not.
**Remediation:** synthesize `MCPServerConfig` and gate before line 197; fail closed.

### S3 — M10 autonomy self-permission bypasses SecurityManager.authorize  ✅ CONFIRMED
`security_abac_ext.py:265 authorize_autonomous_action` returns `permit` on ABAC policy match and at
lines **324–325** explicitly SKIPS `SecurityManager.authorize` ("which has fail-closed default").
Autonomous actions can thus authorize themselves via ABAC without the canonical fail-closed path.
**Remediation:** after ABAC permit, perform a fail-closed `SecurityManager.authorize(...)` check; if
it denies, deny and record (preserve advisory semantics, human override, existing M10 tests, default-off).

### S4 — No central secret redaction  ✅ CONFIRMED
Each adapter re-implements redaction ad hoc (`acp_adapter.py:167`, `hermes_bridge.py:289`,
`playwright_mcp_adapter.py:654/673/683`). There is **no** shared util and **no** `aios/security/`
package. TestingEvidence exceptions/provenance are not centrally scrubbed.
**Remediation:** create `src/aios/security/secrets.py` with `redact_secrets()` + regex patterns;
apply to `testing_evidence.py` formatting, exception `__str__`, and subprocess-failure reporting.
Do not weaken existing secret tests.

### S5 — Capability double-registration hazard  ✅ CONFIRMED
Same five ids (`graphify_context`, `playwright_browser`, `notion_planning`, `obsidian_knowledge`,
`claude_mem_context`) are registered by **two parallel paths**:
1. kernel `_init_graphify/_init_playwright/_init_notion/_init_obsidian/_init_claude_mem`
   (kernel.py:**469–477**) via `self._capability_manager.register(capability_id=...)`.
2. kernel `_init_capability_manifests` (kernel.py:**480**) via `register_capability(spec)` from
   `config/capabilities/*.yaml` (same ids).
`CapabilityManager.register()` (capability_manager.py:**605**) raises `CM-DUP-001` when
`reject_duplicate_provider` and id present; `register_capability` (line 666/723) handles collisions
differently → asymmetric, fragile. Trust precedence not guaranteed.
**Remediation:** make the manifest loader the single canonical path; have kernel `_init_*` methods
skip ids already present (or delegate entirely to the manifest). Preserve legitimate registration +
trust precedence. No new authority.

---

## 4. USER-RESOURCE ABSENCE (NOT FABRICATED)

All ABSENT unless noted. Status is PRESENT/ABSENT/UNKNOWN per the spec; no secret values sought.

| Resource | Status | Why |
|---|---|---|
| hermes-agent cwd path | PRESENT (dir exists, gitignored) / UNREFERENCED at boot | kernel builds HermesBridge w/o cwd/protocol |
| Obsidian vault path | ABSENT | no real vault configured |
| Notion token | ABSENT | user must create integration |
| Notion MCP server choice | UNKNOWN | upstream unconfirmed; CONFIGURATION REQUIRED |
| Graphify endpoint/auth | ABSENT | upstream `"(assumed)"`; unconfirmed |
| Claude-Mem server | ABSENT | scope contradiction in master plan |
| FreeLLM endpoint/key | ABSENT | omitted from .env.example |
| Node + @playwright/mcp + browsers | ABSENT in this env | software install required |
| agent-client-protocol SDK | ABSENT in env | needed for real ACP |
| Anthropic/OpenAI keys | ABSENT in env | runtime-only, user-provided |

---

## 5. GAP REPORT SUMMARY (pre-implementation)

| Gap | Severity | Fix location | Blocks real connect? |
|---|---|---|---|
| S1 ACP gate bypass | HIGH | acp_adapter.py:185/220 | Yes (Hermes/ACP) |
| S2 Playwright gate bypass | HIGH | playwright_mcp_adapter.py:185/197 | Yes (Playwright) |
| S3 M10 self-permission | HIGH | security_abac_ext.py:324 | Authority-invariant concern |
| S4 Central redaction | MED | NEW src/aios/security/secrets.py | Secret-leak concern |
| S5 Cap double-reg | MED | kernel.py:469-480 + capability_manager | Trust-precedence concern |
| G1 FreeLLM boot wiring | MED | freellmapi.py + kernel init | FreeLLM registration |
| Mock→real config (all) | — | config/mcp/*.json | all real modes |
| User resources | — | env/paths | all real modes |

---

*PHASE 0 complete. Implementation (PHASE 1 S1–S5) begins next. No operational claims made.*
