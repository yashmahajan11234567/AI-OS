# T1 AUDIT REPORT — Single Next Architectural Dependency

**Audit Scope:** Terminal 1 (QA/Audit Only) — NO modifications, NO fixes, NO commits, NO pushes.
**Date:** 2026-09-16
**Objective:** Determine the SINGLE next architectural dependency for the native multi-provider expansion/control-plane.

---

## A. Repository State Observed

| Area | Status | Key Files |
|------|--------|-----------|
| **A. Provider ABC contract** | Defined | `src/aios/core/provider.py` (97 lines) — `Provider(ABC)` with `@abstractmethod async generate()`, optional `configure()`/`reload_credentials()` no-op defaults |
| **B. ProviderRegistry** | Defined, duck-typed | `src/aios/core/provider_registry.py` (835 lines) — `register_provider(provider_id, provider)` accepts any object; NO `isinstance(provider, Provider)` enforcement; uses `hasattr`-based dispatch |
| **C. ModelRouter dispatch** | Defined, duck-typed | `src/aios/core/model_router.py` (465 lines) — `_call_model()` calls `provider.generate(request)` directly via `ProviderRegistry.get_provider()`; has legacy `_freellmapi_provider` fallback |
| **D. Native adapters** | NIM compliant; FreeLLMAPI non-compliant | `src/aios/adapters/nim.py` (220 lines) — `NimProvider(Provider)` ✅ subclasses Provider. `src/aios/adapters/freellmapi.py` (225 lines) — `FreeLLMAPIProvider` ❌ does NOT subclass Provider (plain class) |
| **E. Security allow-rules** | Asymmetric | `src/aios/core/kernel.py:2933-2982` — NIM has lifecycle rules (`provider.configure/enable/disable`); FreeLLMAPI has ONLY `secret.rotate`; NIM and FreeLLMAPI both have `secret.rotate` |
| **F. Configuration namespace** | llm.providers.* schema defined | `src/aios/core/configuration_manager.py` — schema defines `llm.providers` with `openai.apiKey`; `is_secret_path()` recognizes "apiKey" via token splitting; `rotate_secret()` uses path pattern `llm.providers.{id}.apiKey`; hardcoded `n` in `_notify_provider_credential_rotation` |
| **G. Integration mode framework** | Canonical registry present | `src/aios/integrations/config.py:252` — `CANONICAL_INTEGRATIONS` tuple includes `freellmapi`, `anthropic`, `openai` (NO `nim`, NO `kilo`, NO `agnes`, NO `gemini`, NO `ollama`); `config/integrations.yaml` has `nim` and `freellmapi` entries but no future providers |
| **H. Dashboard service** | Found at `src/aios/services/dashboard_service.py` | Contains `_INTEGRATION_INVENTORY` dict (line 1057) with metadata for 14 integrations; merges with `CANONICAL_INTEGRATIONS`; `_execute_provider_action` handles `provider.configure/enable/disable/secret.rotate`; uses dynamic path construction `config:llm.providers.{provider_id}` (generalized for any provider) |

---

## B. Areas A–H Analysis

### Area A: Provider ABC Contract
- **Status:** COMPLETE and AUTHORITATIVE.
- `Provider(ABC)` in `provider.py` defines the canonical contract: `@abstractmethod async generate()`, optional `configure()` and `reload_credentials()` defaults.
- **Compliant:** `NimProvider` correctly subclasses `Provider`.
- **Non-compliant:** `FreeLLMAPIProvider` is a plain class — does NOT subclass `Provider`. However, this is a latent risk only; both `ProviderRegistry` and `ModelRouter` use duck-typing (hasattr-based dispatch) rather than `isinstance` checks, so this does not block registration or dispatch today.

### Area B: ProviderRegistry
- **Status:** COMPLETE. Uses duck-typing; `register_provider` does not enforce ABC compliance. This is a design decision (flexibility), not a gap that blocks expansion.

### Area C: ModelRouter Dispatch
- **Status:** COMPLETE. Dispatches via `ProviderRegistry.get_provider()` → `provider.generate(request)`. Has a legacy backward-compat fallback for FreeLLMAPI via `_freellmapi_provider` attribute. The dispatch chain is provider-agnostic.

### Area D: Native Adapters
- **Status:** NimProvider is compliant; FreeLLMAPI is non-compliant but functionally working via duck-typing. For multi-provider expansion, each new adapter (Kilo, Agnes, Gemini, Ollama Cloud) must subclass `Provider`. This is a per-adapter concern, addressed at adapter implementation time — NOT an architectural dependency.

### Area E: Security Allow-Rules
- **THE CRITICAL GAP.** The kernel's `_init_dashboard_backend()` (kernel.py:2933-2982) registers allow-rules **explicitly and individually per provider**:
  - **NIM:** Has `secret.rotate`, `provider.configure`, `provider.enable`, `provider.disable` — full lifecycle coverage.
  - **FreeLLMAPI:** Has `secret.rotate` ONLY — NO lifecycle rules (`provider.configure/enable/disable` absent).
- **Problem:** Each `register_allow_rule()` call in `_init_dashboard_backend()` is a **hardcoded, per-provider statement**. Adding a new provider (Kilo, Agnes, Gemini, Ollama Cloud) requires **modifying `kernel.py`** source code to add new `register_allow_rule` calls. This is the architectural bottleneck: the security policy is **not data-driven** — it is **source-driven** per provider.

### Area F: Configuration Namespace
- **Status:** The `llm.providers.*` namespace exists and is recognized by `is_secret_path()` (token "key" matches "apiKey"). `ConfigurationManager.rotate_secret()` uses path pattern `llm.providers.{provider_id}.apiKey` and `_notify_provider_credential_rotation()` extracts the provider ID from the path. This mechanism is **already provider-agnostic** — it works for any provider ID at the config/credential layer. The gap is NOT in configuration — it is in **security allow-rule registration** in the kernel.

### Area G: Integration Mode Framework
- **Status:** `CANONICAL_INTEGRATIONS` tuple in `config.py:252` lists 14 integrations. Notably, it includes `freellmapi`, `anthropic`, `openai` but **excludes `nim`** (even though NIM has security rules and a real adapter). The tuple also has no entries for `kilo`, `agnes`, `gemini`, or `ollama-cloud`.
- However, the dashboard service's `_execute_provider_action()` (dashboard_service.py:874-1007) already uses **dynamic resource path construction**: `config:llm.providers.{provider_id}` — it does NOT hardcode per-provider resource paths. This means the dashboard service is **already provider-agnostic** for lifecycle actions.

### Area H: Dashboard Service
- **Status:** Found and functional. The dashboard service already supports generic provider lifecycle actions via dynamic path construction. The `_INTEGRATION_INVENTORY` dict is a **static metadata table** for dashboard display purposes.

---

## C. Dependency Order (Areas A–H)

| Priority | Area | Dependency Nature | Blocking Expansion? |
|----------|------|-------------------|----------------------|
| 1 | **E — Security allow-rules** | Hardcoded per-provider rules in kernel.py require source modification for each new provider | ✅ YES — this is the bottleneck |
| 2 | A — Provider ABC compliance | Per-adapter concern; FreeLLMAPI non-compliance is latent (duck-typed) | ❌ No — duck-typing bypasses ABC enforcement |
| 3 | G — CANONICAL_INTEGRATIONS | Missing providers in inventory; updateable without touching kernel core | ❌ No — data update, not code bottleneck |
| 4 | F — Configuration namespace | Already provider-agnostic (`llm.providers.{id}.apiKey` pattern) | ❌ No — already generic |
| 5 | H — Dashboard service | Already uses dynamic resource path construction | ❌ No — already generic |
| 6 | B/C/D — Registry/dispatch | Duck-typed, already generic | ❌ No |

**Key Finding:** The ONLY place in the entire stack that requires **hardcoded per-provider source code changes** for each new native provider is the **security allow-rule registration in `kernel.py` (`_init_dashboard_backend`)**, lines 2955-2981. Every other layer (ProviderRegistry, ModelRouter, ConfigurationManager, DashboardService) is already provider-agnostic via duck-typing or dynamic path construction.

---

## D. The Single Architectural Dependency

**The security allow-rule registration system is the SINGLE next architectural dependency.**

The current design hardcodes per-provider allow-rules in `kernel.py` `_init_dashboard_backend()`:
```python
# Lines 2956-2981 — PER-PROVIDER, source-level hardcoding
self._security_manager.register_allow_rule(
    principal="dashboard_user", action="secret.rotate",
    resource="config:llm.providers.nim.apiKey")
self._security_manager.register_allow_rule(
    principal="dashboard_user", action="provider.configure",
    resource="config:llm.providers.nim")
self._security_manager.register_allow_rule(
    principal="dashboard_user", action="provider.enable",
    resource="config:llm.providers.nim")
# ... etc, repeated for each provider
```

This means:
1. **Every native provider added (Kilo, Agnes, Gemini, Ollama Cloud) requires a kernel.py source edit** to register its allow-rules.
2. **FreeLLMAPI is already in an incomplete state** — it has `secret.rotate` but NO lifecycle rules (`provider.configure/enable/disable`), creating an asymmetric security posture.
3. The **resource path pattern** (`config:llm.providers.{provider_id}`) is already canonical and provider-agnostic at the ConfigurationManager level, but the **allow-rule registration is NOT**.

---

## E. What Must Be Built (T2 Implementation Task)

The security allow-rule registration must be **data-driven and provider-agnostic**. Instead of hardcoding each provider's allow-rules in `kernel.py`, the kernel should derive allow-rules from the canonical provider registry (ProviderRegistry) and configuration namespace.

**The mechanism already exists partially:**
- `ProviderRegistry` knows all registered provider IDs (via `list_providers()`)
- `ConfigurationManager` already uses the `llm.providers.{provider_id}.apiKey` pattern for secret rotation
- `DashboardService._execute_provider_action()` already uses dynamic path construction for any provider
- `is_secret_path()` already recognizes "apiKey" generically

**The missing piece:** A **data-driven allow-rule derivation** that registers allow-rules for every provider known to `ProviderRegistry` at dashboard backend initialization time, using the canonical resource path pattern, without hardcoding any specific provider ID.

---

## F. Verification Evidence

| Evidence | Location | Confirms |
|----------|----------|----------|
| FreeLLMAPI lacks lifecycle rules | kernel.py:2955-2981 — only `secret.rotate` for freellmapi; full lifecycle for nim | Security rules are per-provider hardcoded |
| Dashboard uses dynamic paths | dashboard_service.py:895-895, 978, 983 — `config:llm.providers.{provider_id}.apiKey` constructed dynamically | Dashboard layer is already provider-agnostic |
| Config manager is provider-agnostic | configuration_manager.py:1418-1420 — path pattern `llm.providers.{provider_id}.{secret_key}` extracted dynamically | Config layer works for any provider |
| ProviderRegistry is duck-typed | provider_registry.py:306 — `register_provider(self, provider_id, provider)` with no isinstance check | Registry accepts any provider |
| CANONICAL_INTEGRATIONS excludes native providers | config.py:252 — has freellmapi/anthropic/openai, NO nim/kilo/agnes/gemini/ollama | Integration inventory is stale but not blocking |
| is_secret_path recognizes apiKey generically | configuration_manager.py:427-429 — `_SECRET_TOKENS` includes "key"; token splitter handles camelCase | Secret detection is provider-agnostic |
| Provider ABC exists but not enforced | provider.py:17 — `class Provider(ABC)`, but provider_registry.py:306 does not enforce isinstance | ABC compliance is latent, not blocking |

---

## G. Why Not Other Areas

- **Area A (Provider ABC):** `FreeLLMAPIProvider` not subclassing `Provider` is a code-quality issue. Because `ProviderRegistry.register_provider()` and `ModelRouter._call_model()` both use duck-typing (hasattr-based or direct method calls), this does not block any new provider from being registered or dispatched. A new provider that subclasses `Provider` works identically to FreeLLMAPI which doesn't. **Not blocking.**

- **Area B (ProviderRegistry):** Already fully provider-agnostic. `register_provider(provider_id, provider)` accepts any object. **Not blocking.**

- **Area C (ModelRouter dispatch):** Already provider-agnostic. Dispatches via `provider_id` → `ProviderRegistry.get_provider()` → `provider.generate(request)`. **Not blocking.**

- **Area D (Native adapters):** Each adapter is implemented independently. The pattern is established (`NimProvider(Provider)`). **Not an architectural dependency.**

- **Area F (Configuration namespace):** Already provider-agnostic. The `llm.providers.{provider_id}.apiKey` pattern works for any provider ID. Secret rotation and credential persistence are generic. **Not blocking.**

- **Area G (CANONICAL_INTEGRATIONS):** Missing providers in the inventory is a data-completeness issue. Adding entries is a config/data update, not a kernel architectural change. The integration framework itself is provider-agnostic. **Not blocking.**

- **Area H (Dashboard service):** Already uses dynamic resource path construction (`config:llm.providers.{provider_id}`) for all provider actions. No per-provider hardcoding exists in the dashboard's action execution path. **Not blocking.**

---

## H. Dependency Chain Summary

```
Native Multi-Provider Expansion requires:
  1. [BLOCKING] Security allow-rule registration → must be data-driven (kernel.py)
     └─ Currently hardcoded per-provider in _init_dashboard_backend()
  2. [NOT BLOCKING] Provider ABC enforcement → optional hardening
  3. [NOT BLOCKING] CANONICAL_INTEGRATIONS update → data/config change
  4. [NOT BLOCKING] New adapter implementation → per-provider task
     └─ Each new adapter just needs to subclass Provider and register
```

---

## I. Audit Constraints Compliance

- ✅ **No files modified** — Read-only inspection only
- ✅ **No fixes applied** — Gaps documented, not corrected
- ✅ **No commits** — Audit is observation-only
- ✅ **No pushes** — Audit is observation-only
- ✅ **Current repository inspected** — All findings grounded in actual source code

---

## J. Single Next T2 Task

**NEXT T2 TASK: Replace the hardcoded per-provider allow-rule registration in `kernel.py` (`_init_dashboard_backend`, lines 2955-2981) with a data-driven allow-rule derivation that iterates over all providers registered in `ProviderRegistry` and registers the canonical allow-rules (`secret.rotate`, `provider.configure`, `provider.enable`, `provider.disable`) for each provider ID using the canonical resource path pattern (`config:llm.providers.{provider_id}.apiKey` for secrets, `config:llm.providers.{provider_id}` for lifecycle), eliminating the need for kernel.py source edits when adding each new native provider (Kilo, Agnes, Gemini, Ollama Cloud) — and retroactively closing the FreeLLMAPI lifecycle-rules gap.