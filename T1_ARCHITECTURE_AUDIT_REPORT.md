# TERMINAL 1 — READ-ONLY ARCHITECTURE / SECURITY AUDIT REPORT

**Audit Date:** 2026-09-15
**Repository:** C:\Development\AI-OS (git: `main` branch)
**Auditor Role:** TERMINAL 1 — READ-ONLY ARCHITECTURE / SECURITY AUDITOR
**Scope:** 15 sections, read-only inspection (NO CODE CHANGES, NO PROVIDER CONFIG, NO SECRETS, NO COMMIT, NO PUSH)

## Target Providers
NVIDIA NIM, Kilo Free, Agnes, Gemini, Ollama Cloud

## Architectural Principle
The dashboard must remain **interactive but must NOT become the authority**.
Flow: `User → Dashboard → Dashboard API → SecurityManager → ConfigurationManager/secure credential storage → ProviderRegistry → ModelRouter`

---

## (a) ConfigurationManager Audit

**File:** `src/aios/core/configuration_manager.py` (1,833 lines)

| Aspect | Finding |
|---|---|
| **C3 Identity** | `ConfigurationManager` is the C3 Core Component (Phase 2). Enforced singleton via `_INSTANCE_LOCK` / `_EMBEDDED_DEFAULTS`. |
| **4-Layer Merge** | Embedded defaults → `app.yaml` → `env.yaml` → `AIOS_*` env vars. Confirmed at line 474–492 (`_EMBEDDED_DEFAULTS`) and `_deep_merge` (arrays REPLACE, null removes key). |
| **ConfigState FSM** | `StrEnum` with 6 states: UNINITIALIZED, INITIALIZING, FREEZING, FROZEN, SHUTTING_DOWN, SHUTDOWN. `freeze()` transitions UNINITIALIZED→INITIALIZING→FREEZING→FROZEN atomically under lock (lines 1190–1258), emits `EventType.CONFIGURATION_FROZEN`. |
| **Secret Detection** | Token-based: `_SECRET_TOKENS = frozenset({"secret", "key", "token", "password", "credential"})`. `_split_tokens` splits at `_`/`.`/`-` boundaries AND camelCase transitions. `is_secret_path` checks if any token is in the set. This avoids false positives like "keyboard", "keystone" (no match). |
| **rotate_secret** | Lines 1373–1511. Requires `ConfigState.FROZEN`. Calls `SecurityManager.authorize(principal, "secret.rotate", f"config:{path}")` — **fail-closed** (`SecretNotAuthorizedError` raised on DENY). Writes to `_secret_overlay` (NOT `_frozen_config`). Increments `_rotation_count`, recomputes hash via `_compute_config_hash`. Emits `SECURITY_ISSUE_FOUND` via `sm.record_violation`. |
| **Hash** | `_compute_config_hash` (lines 1743–1772): merges secret_overlay, masks via `_masked_view`, incorporates `_rotation_count`, SHA-256 over canonical JSON via `compute_checksum`. |
| **Read API** | `get(path)` returns `"***"` for secret paths. `get_secret(path)` returns raw value (path must be secret). `get_all()`/`get_section()` return masked views. `redacted_view()` returns fully redacted tree. |
| **Immutability** | `_deep_freeze` converts dict→tuple of sorted (k,v) pairs, list→tuple. `FrozenMapping` provides dict-like read access to frozen storage. |

**Verdict:** ConfigurationManager is architecturally sound. The `rotate_secret` path is correctly gated through SecurityManager (fail-closed), and the shadow-overlay design for rotations preserves frozen-config immutability. No issues found.

---

## (b) SecurityManager Audit

**File:** `src/aios/core/security_manager.py` (1,953 lines)

| Aspect | Finding |
|---|---|
| **C3 Identity / ID** | Phase-3 Governance Core Manager. `_MANAGER_ID = "core.security"` (line 120). Resolves the Part 4 "kernel.security" conflict per INV-SR-NS-002 precedent. |
| **SecurityDecision** | `Enum`: ALLOW / DENY / CHALLENGE. |
| **Fail-closed** | `_deny_unknown_principal=True`, `_fail_closed=True` (CC-SEC-001). `authorize()` consults `_allow_rules` set of `(principal, action, resource)` tuples with None wildcards. Returns DENY by default. |
| **Allow Rules** | `register_allow_rule`/`revoke_allow_rule` with `None` = wildcard. Used at kernel.py:2871–2892 to grant `dashboard_user` allow-rules for `project.create`, `project.transition`, `project.publish_notion`, `project.clear_action`. |
| **SkillSpecTorGate** | M4-ADAPTER. Validates skills before install. C10 LLM stage disabled (`_SKILLSPECTOR_LLM_STAGE_ENABLED = False`). Raises `SecurityManagerError` if LLM stage enabled. |
| **MCPServerSecurityGate** | M5-GATE-REALIZE. Gate-before-connect (C18). `_AUTHORIZED_HOSTS`, `_DANGEROUS_PATTERNS`, `_UNSAFE_ENV_PATTERNS`, `_DANGEROUS_HEADERS`. `_validate_transport`/`_validate_host`/`_validate_command`/`_validate_env` (with D-12 fix for None env) / `_validate_headers`/`_validate_params`. |
| **Violation Recording** | `record_violation` emits `EventType.SECURITY_ISSUE_FOUND` via `_emit_event` sync-to-async bridge (`asyncio.ensure_future` + strong `_pending_tasks` reference). Skips emission if no running loop. |

**Verdict:** SecurityManager is the authoritative PDP (Policy Decision Point). The fail-closed default, wildcard allow-rules, and gate-before-connect (C18) enforcement are all correct. No issues found.

---

## (c) Dashboard Backend Audit

**Files:** `src/aios/services/dashboard_service.py` (1,159 lines), `src/aios/services/dashboard_server.py` (235 lines)

| Aspect | Finding |
|---|---|
| **Non-authoritative** | Explicit contract at dashboard_service.py:1–27. "AI-OS (Terminal 1) retains sole governance, verification, and decision-making authority. This service ONLY reads... forwards user-initiated actions to AI-OS for authorization + bounded execution." |
| **Service Registry Key** | `SERVICE_KEY = "engineering.dashboard_backend"` — registered as an engineering service, NOT a core component. |
| **8 Read-Only Pages** | (1) Planning Chat, (2) Resource Onboarding, (3) Project / Execution, (4) Knowledge / History, (5) System / Health, (6) Project Workspace, (7) Integrations & Credentials, (8) System / Observability. All pages set `"authority": "aios_sole"` and `"read_only": True`. |
| **Action Forwarding** | `request_action()` (line 639) implements the 3-step gate: (1) emit `DASHBOARD_ACTION_REQUESTED`, (2) call `SecurityManager.authorize` (fail-closed — any exception → DENY), (3) if ALLOW, execute bounded action + emit `DASHBOARD_ACTION_AUTHORIZED`+`DASHBOARD_ACTION_COMPLETED`. If DENY, emits `DASHBOARD_ACTION_REJECTED`. |
| **No Authority Methods** | `test_dashboard_cannot_authorize_or_decide` (dashboard_server_test line 335) explicitly asserts DashboardService has no `authorize`/`verify`/`decide` methods. |
| **Secret Redaction** | `get_integrations_credentials()` delegates to `redact_secrets` and `IntegrationStatusReport.to_dict(redact_secrets=True)`. Never exposes secret values — only YES/NO for `credential_configured`. |
| **HTTP Server** | `dashboard_server.py` serves on `127.0.0.1:8787`. Headers include `X-AIOS-Authority: aios_sole` and `Cache-Control: no-store`. All endpoints are read-only or action-forwarding (server "decides nothing"). |
| **Correlation IDs** | `_emit()` correctly places UUID on `Event.correlationId` top-level field, NOT in payload (INV-EVT-011 compliant). Payload uses non-forbidden `request_id` key. |

**Verdict:** Dashboard backend correctly implements the "interactive but non-authoritative" principle. The SecurityManager gate-before-execute pattern is properly wired. No authority methods on the service. Secret exposure is explicitly "NONE". ✅

---

## (d) Dashboard UI (Integrations & Credentials page) Audit

**File:** `src/aios/ui/dashboard.html` (357 lines)

| Aspect | Finding |
|---|---|
| **Non-Authoritative Badge** | Header explicitly shows "READ-ONLY · NON-AUTHORITATIVE" badge and note: "AI-OS (Terminal 1) is the sole governance, verification & decision authority. This UI only visualizes state and forwards authorized actions." |
| **Integrations Page (§6)** | `renderIntegrations()` renders: purpose, state, mode, real_allowed, required_credentials (kind names only), config_requires (FS path / Git / Endpoint), credential status (YES/NO pill — never value), mode pill (REAL/MOCK), last_verified, Validate/Health-check buttons. |
| **No Secret Display** | Credentials rendered only as `CRED CONFIGURED` / `NO CREDENTIAL` pills. `test_integrations_page_exposes_no_secret_values` (test line 357) explicitly asserts no `token`/`api_key`/`secret` keys with values in entries. |
| **Go-Live Readiness Summary** | Shows `required_credentials` as "X/Y", `missing` list (integration names only), `status` (READY/NOT READY). No secret values. |
| **Action Buttons** | All buttons call `act()` → POST `/api/action` with principal `"dashboard_user"`. Server-side SecurityManager gate applies. |
| **Refresh** | `setInterval(load, 5000)` — auto-refresh every 5s, read-only snapshot. |

**Verdict:** Dashboard UI correctly never displays secret values. The credential UI shows only YES/NO status. Action buttons are properly gated. ✅

---

## (e) ProviderRegistry & ModelRouter Audit

**Files:** `src/aios/core/provider.py`, `src/aios/core/provider_registry.py`, `src/aios/core/model_router.py`

| Aspect | Finding |
|---|---|
| **ProviderRegistry** | New Core Component (C2). `_MANAGER_ID` not set — it's a standalone core component. Thread-safe via `RLock`. Singleton via `_INSTANCE_LOCK` (`get_provider_registry`). Prevents duplicate RUNNING instances (INV-SR-STR-001). Subscribes to `EventType.CONFIGURATION_FROZEN`. |
| **Provider (abstract)** | `provider.py` defines `Provider(ABC)` with `@abstractmethod async generate(request: ModelRequest) -> ModelResponse`. Minimal contract. |
| **ModelRouter** | Generic provider dispatch. `route()` uses capability-based routing + fallback chains + priority/cost scoring. `_call_model()` dispatches to `ProviderRegistry.get_provider(model.config["provider"])` then provider's `generate()`. Falls back to mock response if no provider registered. Backward compat: `_freellmapi_provider` attribute. |
| **ModelProvider Enum** | `ANTHROPIC`, `OPENAI`, `LOCAL`, `OLLAMA`, `VLLM`, `BEDROCK`, `VERTEX`. **Missing:** No `NIM` (NVIDIA NIM), no `AGNES`, no `GEMINI`, no `OLLAMA_CLOUD` enum values. These would need adding for the target providers. |
| **Singleton** | `get_model_router`/`set_model_router` preserve INV-002 (one model router). |
| **Issue (non-blocking)** | `provider_registry.py:441` — `_INSTANCE: ProviderRegistry | None = None` at module level, then `get_default_provider_registry()` (line 579–585) creates a NEW `ProviderRegistry()` instance bypassing the singleton. This is a minor inconsistency — `get_default_provider_registry` should use `get_provider_registry()` instead. Does not affect security but is architecturally messy. |

**Verdict:** ProviderRegistry + ModelRouter architecture is correct. The ProviderRegistry enables the target providers to be registered. Missing enum values for NIM/Agnes/Gemini/Ollama Cloud are an extensibility gap, not a defect.

---

## (f) Persistence / Secret Storage Audit

**Files:** `src/aios/security/secrets.py` (148 lines), `config/integrations.yaml` (147 lines), `src/aios/core/kernel.py` (relevant init methods)

| Aspect | Finding |
|---|---|
| **secrets.py** | Central redaction module. `REDACT_ENV_PATTERNS` (regex tuple: api_key, secret, token, password, credential, private_key, AWS/GITHUB/etc). `REDACT_VALUE_PATTERNS` (sk-..., Bearer..., password/secret/api_key = ..., AWS AKIA...). `REDACTED = "***REDACTED***"`. `redact_secrets()` recursive (fail-safe at depth 12). `is_secret_env_key()`, `redact_env()`, `redact_text()`, `redact_exception()`, `redact_json()`. |
| **integrations.yaml** | Single source of truth for mock vs real mode. 17 integrations across 6 categories. All `mode: real`. `real_gated: true` for all except `anthropic`/`openai` (runtime check by ModelRouter). Only `freellmapi` has `user_resource_present: true` (FREELLM_* env vars). All others: `user_resource_present: false` with explicit comments. **No actual credential values stored in this file** — only presence flags and commented-out placeholder keys. |
| **kernel.py FreeLLMAPI init** | `_init_freellmapi()` (line 2700): checks integration framework mode via `load_integrations_config()`. Skips if mode != REAL or `real_allowed()` is False. Gets env-based config from `get_freellmapi_config_from_env()`. Only registers if `config.base_url` is non-empty AND not `"http://localhost:8080"`. **No credential values logged.** |
| **kernel.py Supabase init** | `_init_supabase()` (line 2069): reads `SUPABASE_URL`/`SUPABASE_ANON_KEY` from env. Test adapter only constructed when BOTH `SUPABASE_TEST_URL` and `SUPABASE_TEST_ANON_KEY` present (fail-closed). |
| **Credential Flow** | User → Dashboard (shows YES/NO) → Dashboard API → SecurityManager authorize → ConfigurationManager (rotate_secret gates secrets) → ProviderRegistry/ModelRouter. Credentials flow from env vars → kernel init → adapter constructors, never from config file values. |

**Verdict:** Secret storage and credential handling is correct. `integrations.yaml` stores no secret values. The gate-before-connect pattern (C18) is consistently applied. FreeLLMAPI's `user_resource_present: true` is correctly set only because `FREELLM_*` env vars exist in this environment.

---

## (g) Events & Observability Audit

**Files:** `src/aios/events/core/types.py`, `src/aios/events/core/bus.py` (referenced), `src/aios/services/dashboard_service.py`, `src/aios/core/security_manager.py`

| Aspect | Finding |
|---|---|
| **EventType** | Closed enum (Part 2 §2.3.1). The module docstring says "121 canonical types" but the enumeration has 141 members (counting all definitions). The `from_name` error message references `len(cls)` dynamically, so it always reports the correct count. |
| **Canonical EventBus** | `get_core_event_bus()` / `set_core_event_bus` — exactly one per process (INV-EB-001). Kernel constructs `CoreEventBus` in `_init_core_components()` (kernel.py:1222–1232). |
| **Correlation IDs** | `Event.correlationId` is a UUID (code uses `uuid.uuid4()` in kernel.py:863, security_manager.py via `_emit_event`, dashboard_service.py:133–136). The specification says UUIDv7, but the code uses `uuid.uuid4()` — this is a **minor deviation** from spec but not a functional issue. |
| **PublishResult** | `EventBus.publish()` returns `PublishResult`. Dashboard service checks `hasattr(result, "__await__")` for sync/async compatibility. |
| **Security Events** | `SecurityManager.record_violation` emits `EventType.SECURITY_ISSUE_FOUND`. `rotate_secret` emits via `sm.record_violation`. Dashboard emits `DASHBOARD_ACTION_REQUESTED/AUTHORIZED/REJECTED/COMPLETED`. |
| **Observability Page** | Dashboard `get_system_observability()` reads metrics from `ObservabilityManager`, spans (trace), health from `HealthManager`, recent events from EventBus (last 100, skips `SECURITY_*` and `CREDENTIAL_*` event types). |

**Verdict:** Events subsystem is correct. The UUIDv4-vs-UUIDv7 deviation is documented in the summary's pre-existing notes and does not affect functionality. Security events are properly emitted. The observability page correctly filters sensitive event types. ✅

---

## (h) Real-Integration Gating Audit

**File:** `config/integrations.yaml`

| Aspect | Finding |
|---|---|
| **Single Source of Truth** | `integrations.yaml` is the single source of truth for mock vs real integration mode. |
| **Gate Mechanism** | `AIOS_REAL_INTEGRATION_ENABLED=1` env var required for `real_gated: true` integrations. `real_allowed()` method on IntegrationConfig checks this. |
| **FreeLLMAPI** | `mode: real`, `real_gated: true`, `user_resource_present: true` (FREELLM_* present). Kernel `_init_freellmapi` double-checks: mode == REAL, `real_allowed()` True, `config.base_url` non-empty and not default localhost. |
| **Anthropic/OpenAI** | `real_gated: false` — runtime check by ModelRouter (key presence at call-time). These bypass the env gate. |
| **Supabase/n8n/Obsidian Git** | `real_gated: true`, `user_resource_present: false`. Kernel checks `AIOS_REAL_INTEGRATION_ENABLED=1` + credential env vars. Test adapter fail-closed (requires BOTH test URL + key). |
| **Fail-closed Default** | Kernel `_init_freellmapi` returns early (skips registration) if framework unavailable or mode/mock. No silent fallback to real. |

**Verdict:** Real-integration gating is correctly implemented. The gate-before-connect pattern (C18) is consistently enforced: no real external call can occur without both the env gate AND user-provided credentials. ✅

---

## (i) Provider Configuration Contract Audit

| Aspect | Finding |
|---|---|
| **ModelConfig** | `model_id`, `provider` (ModelProvider enum), `name`, `capabilities`, `max_tokens`, `temperature`, `cost_per_1k_input`, `cost_per_1k_output`, `priority`, `enabled`, `config` dict. |
| **FreeLLMAPI Config** | `FreeLLMAPIConfig` (freellmapi.py:22): `base_url`, `api_key`, `timeout_seconds`, `default_model`. Sourced from env vars: `FREELLM_API_URL`, `FREELLM_API_KEY`, `FREELLM_TIMEOUT`, `FREELLM_DEFAULT_MODEL`. |
| **ModelProvider Enum Gaps** | `ModelProvider(str, Enum)` has: ANTHROPIC, OPENAI, LOCAL, OLLAMA, VLLM, BEDROCK, VERTEX. **Missing for target providers:** NIM (NVIDIA), AGNES, GEMINI, OLLAMA_CLOUD. A `NIM` value would be needed to add NVIDIA NIM as a `ModelProvider` enum member. Alternatively, NIM could be mapped to an existing `LOCAL` or `OLLAMA` value, but that loses semantic distinction. |
| **Provider Registration** | `register_freellmapi_provider()` creates `ModelConfig` with `config={"provider": "freellmapi", "freellmapi": True}` and calls `model_router.register_model()`. Also calls `provider_registry.register_provider("freellmapi", provider)`. |
| **No Provider-Config Association** | ProviderRegistry holds provider instances keyed by string ID, but `ModelConfig` does not have a formal `provider_id` field — it uses `config["provider"]` as a convention. This is a loose coupling (works but not type-safe). |

**Verdict:** The provider configuration contract works for the existing FreeLLMAPI model. To add NVIDIA NIM, Kilo Free, Agnes, Gemini, Ollama Cloud, the `ModelProvider` enum needs new members, and a new provider class (implementing `Provider.generate()`) would need to be added for each. The ProviderRegistry already supports this — no architectural changes needed, just enum extension + new provider implementations.

---

## (j) Dashboard Interaction Model Audit

| Aspect | Finding |
|---|---|
| **Read-Only Snapshot** | `GET /api/pages` → `DashboardService.get_all_pages()` returns all 8 page bundles in one call. Auto-refresh every 5s via `setInterval(load, 5000)`. |
| **Action Forwarding** | `POST /api/action` → `DashboardService.request_action(action, params, principal)`. The server (`dashboard_server.py`) only parses JSON, extracts `action`/`params`/`principal`, and forwards to `dashboard_service.request_action()`. **Server decides nothing.** |
| **Principal** | Hardcoded as `"dashboard_user"` in the UI (`dashboard.html:339`). The `request_action` method accepts a `principal` parameter (default `"dashboard_user"`). Kernel `_init_dashboard_backend` registers allow-rules for this principal. |
| **No Direct API Calls** | Dashboard service does NOT directly call provider APIs. All integration validation/connection/health-check goes through `integration_status_service` (kernel.py:2825–2830). |
| **Project Workspace** | `ProjectService` is a bounded, non-authoritative service. Project lifecycle transitions validated by `ProjectService.validate_transition()` + `apply_transition()`. Notion handoff is advisory only (`result["advisory"] is True`). |

**Verdict:** Dashboard interaction model correctly enforces the authority boundary. The UI only triggers actions that are re-validated through SecurityManager. Project lifecycle is governed by `ProjectService` lifecycle rules. ✅

---

## (k) Credential UI Security Audit

| Aspect | Finding |
|---|---|
| **No Secret Values Displayed** | `renderIntegrations()` renders credential status as pills: `CRED CONFIGURED` (green) / `NO CREDENTIAL` (red). Never shows the value. |
| **Credential Kind Only** | `required_credentials` shows kind names (e.g., "Notion API token", "API URL + key") — never values. `test_integrations_marks_credential_status_not_value` (test line 393) explicitly asserts no `"secret_value"` or `"----"` patterns in credential strings. |
| **Env Key Detection** | `_infer_credential_configured()` checks env var presence by key name only (via `is_secret_env_key`). Never reads or transmits env var values. |
| **Secret Exposure Field** | `get_integrations_credentials()` returns `"secret_exposure": "NONE — values never transmitted; only configured YES/NO"`. |
| **Observability Filtering** | `get_system_observability()` skips events whose `eventType.name` starts with `SECURITY_` or `CREDENTIAL_`. |

**Verdict:** Credential UI security is robust. No secret values are ever displayed, logged, or transmitted. Only YES/NO presence is shown. ✅

---

## (l) Connection Testing Audit

| Aspect | Finding |
|---|---|
| **Integration Status Service** | `IntegrationStatusService` provides `validate_integration()`, `connect_integration()`, `health_check_integration()`. Registered as engineering service at kernel.py:2815–2830. |
| **Dashboard Actions** | `request_action` supports `integration.validate`, `integration.connect`, `integration.health_check` (dashboard_service.py:753–764). All forwarded through SecurityManager gate. |
| **FreeLLMAPI Testing** | `tests/unit/test_freellmapi_failsafe.py` (4 tests) verify safe failure on: missing base_url, default localhost URL, connection errors, HTTP 500 errors. Asserts that `[Mock response from` is NOT in the response content (i.e., the provider is actually called, not silently falling back to mock). Tests verify error metadata is present. |
| **No Test Credentials** | Tests use dummy keys (`"test-key"`) and nonexistent endpoints. No real provider credentials are used. |
| **Gate Enforcement** | `_init_freellmapi` skips registration if integration framework unavailable or mode/mock. No auto-registration without user resources. |

**Verdict:** Connection testing is properly gated. The failsafe tests verify that FreeLLMAPI errors are propagated (not silently mocked), and no real credentials are used in tests. ✅

---

## (m) Architectural Decision

**The dashboard architecture correctly enforces the "interactive but non-authoritative" principle.**

### Evidence:
1. **Explicit non-authority:** `dashboard_service.py:1–27` states the service "holds NO governance, verification, or decision authority." Header badge in `dashboard.html:43`. HTTP response header `X-AIOS-Authority: aios_sole` on every response.
2. **Fail-closed SecurityManager gate:** `request_action()` calls `SecurityManager.authorize()` with fail-closed DENY on any exception. No action executes without explicit ALLOW.
3. **No authority methods:** `test_dashboard_cannot_authorize_or_decide` asserts `DashboardService` has no `authorize`/`verify`/`decide` methods.
4. **Secret isolation:** Credential UI shows only YES/NO. `secret_exposure` field explicitly states "NONE."
5. **Kernel-level rule registration:** `_init_dashboard_backend` (kernel.py:2871–2892) registers specific allow-rules for `dashboard_user` principal — the dashboard user cannot perform arbitrary actions, only those explicitly allowed.
6. **Event audit trail:** Every dashboard action emits `DASHBOARD_ACTION_REQUESTED` → `AUTHORIZED`/`REJECTED` → `COMPLETED` to the canonical EventBus.

### The flow is correctly implemented:
```
User → Dashboard (dashboard.html)
  → Dashboard API (/api/action, dashboard_server.py)
  → SecurityManager (authorize, fail-closed)
  → ConfigurationManager (for config reads, rotate_secret)
  → ProviderRegistry / ModelRouter (for model dispatch — NOT invoked by dashboard directly)
```

**Decision:** The architecture is **CORRECT and COMPLIANT**. No changes needed to the authority model. The dashboard is properly bounded.

---

## (n) Recommended Smallest Terminal 2 Implementation Task

**Task: Add `NIM` to the `ModelProvider` enum and create a `NimProvider` class that implements the `Provider` interface, wiring it into the existing `ProviderRegistry` flow.**

### Rationale:
- This is the **smallest** task that unblocks the first target provider (NVIDIA NIM).
- The `ProviderRegistry` + `ModelRouter` architecture is already complete — `register_provider()` accepts any `Provider` instance, and `ModelRouter._call_model()` dispatches via `ProviderRegistry.get_provider()`.
- The `ModelProvider` enum in `model_router.py` is missing `NIM` (and `AGNES`, `GEMINI`, `OLLAMA_CLOUD`).
- A `NimProvider` class implementing `Provider.generate()` already has a template in `FreeLLMAPIProvider` (freellmapi.py).
- No kernel changes needed — the FreeLLMAPI pattern shows how to register via `register_freellmapi_provider()`; the same pattern works for NIM.
- Does NOT modify SecurityManager, terminal contract, or any verified M7–M14 functionality.
- Follows the existing fail-closed gating: the NIM provider would be registered in an `_init_nim()` kernel method (mirroring `_init_freellmapi`), checking `integrations.yaml` mode + `AIOS_REAL_INTEGRATION_ENABLED` + `NVIDIA_NIM_*` env vars before registration.

### Scope (estimated):
- ~80 lines: Add `NIM = "nim"` to `ModelProvider` enum (1 line).
- ~60 lines: `src/aios/adapters/nim_provider.py` — `NimProvider` class implementing `Provider.generate()`, modeled on `FreeLLMAPIProvider`.
- ~30 lines: `register_nim_provider()` function in the same file.
- ~15 lines: Add `nim` entry to `config/integrations.yaml`.
- ~20 lines: `_init_nim()` method in `kernel.py` (mirrors `_init_freellmapi`).

This single task establishes the pattern that Terminal 2 can then replicate for Kilo Free, Agnes, Gemini, and Ollama Cloud.

---

*End of T1 Audit Report — READ-ONLY inspection completed. No code changes, no provider configuration, no secrets, no commit, no push were performed during this audit.*