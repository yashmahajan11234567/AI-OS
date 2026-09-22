# Terminal 1 Architecture Audit: Replacing FreeLLMAPI-dependent Provider Configuration with Native Multi-Provider Model

## 1. Current ModelRouter architecture
AI-OS Hermes Kernel features a capability-based `ModelRouter` that selects models via routing hints (required capabilities, preferred provider/model) and falls back to a priority-scored default chain. The router maintains a registry of `ModelConfig` objects (model_id, provider enum, name, capabilities, cost/performance metrics, priority flag) and implements a deterministic `_select_best()` scoring function using priority, cost, and capability match. The single global instance (`INV-002`) is initialized during kernel boot via `_init_model_router()` (not shown in sources but implied by imports and usage) and exposed through `Kernel.model_manager`. Model registration occurs via `register_model()` with thread-safe stats tracking. Currently, the router only dispatches to a real provider backend when `_freellmapi_provider` is set AND the routed model's config contains `{"freellmapi": True}`; all other models (including standard Anthropic/OpenAI) fall through to a deterministic mock response `[Mock response from ...]`. This makes FreeLLMAPI the *sole* wired provider despite the router's abstraction supporting multiple providers.

## 2. Provider abstraction vs. FreeLLMAPI specialization
The existing abstraction defines a `ModelProvider` enum (ANTHROPIC, OPENAI, LOCAL, OLLAMA, VLLM, BEDROCK, VERTEX) and `ModelConfig.provider` field, suggesting a pluggable provider interface. However, the `ModelRouter._call_model()` method contains a hard-coded special case *only* for FreeLLMAPI: it checks `getattr(self, "_freellmapi_provider", None)` and `model.config.get("freellmapi")`. There is no generic provider dispatch loop or registry. Providers like anthropic/openai exist in the enum but have no corresponding `_anthropic_provider` attribute or registration path. The FreeLLMAPI adapter (`register_freellmapi_provider()`) both registers a model (with `config={"freellmapi": True}`) *and* stores the provider instance on the router as `_freellmapi_provider`. Thus, the current provider abstraction is **not** a true multi-provider dispatch mechanism—it is a FreeLLMAPI-specific hook masquerading as generic provider support. The router's capability routing and fallback chains remain functional, but the provider layer is effectively single-provider (FreeLLMAPI only) with all others falling back to mock.

## 3. Integration framework gating (REAL vs. mock)
The integration framework (config/integrations.py, state.py, validation.py) provides a fail-closed gating system controlling whether an integration may perform REAL external operations. Key mechanisms:
- `IntegrationConfig.mode` (MOCK/REAL, defaults MOCK)
- `IntegrationConfig.real_gated` (boolean, defaults TRUE)
- `IntegrationConfig.requires_user_resource` (boolean, defaults TRUE)
- `IntegrationConfig.user_resource_present` (boolean, set ONLY after verifiable detection)
- `real_allowed()` method: returns TRUE iff `mode == REAL` AND (not gated OR env gate `AIOS_REAL_INTEGRATION_ENABLED` set) AND user resource present
- `assert_real_allowed(name)`: raises RuntimeError unless REAL operation permitted
- Framework integrates with validation (`ValidationRegistry`) and state machine (7-state lifecycle: ABSENT → CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED)
In `kernel._init_freellmapi()`, the framework is consulted via `load_integrations_config()` and `registry.get("freellmapi").real_allowed()` before provider registration. If the integration is not REAL-allowed (due to mock mode, closed env gate, or absent user resource), registration is skipped and FreeLLMAPI remains mock-only. This gating pattern is replicated for other integrations (e.g., `_init_agent_reach()`), proving the framework is generic and applies uniformly across all integrations—including potential future providers.

## 4. New components required for native multi-provider support
To replace the FreeLLMAPI-specific hook with a native multi-provider model, the following components are required:
- **ProviderRegistry**: A new service (or extension to ConfigurationManager/CapabilityManager) that manages provider lifecycle, configuration, and health state. Should support registration/deregistration of provider backends (e.g., `register_anthropic_provider()`, `register_openai_provider()`) and store provider instances keyed by provider ID.
- **ProviderConfig dataclasses**: Per-provider configuration (e.g., `AnthropicConfig`, `OpenAIConfig`) read from `llm.providers.*` in configuration layers, with secret handling via ConfigurationManager's secret path detection.
- **Provider interface**: Abstract base class defining `generate(request: ModelRequest) -> ModelResponse` contract (already implied by FreeLLMAPIProvider).
- **Router modification**: Replace the FreeLLMAPI-specific check in `ModelRouter._call_model()` with a loop over registered providers: for the routed model, iterate through its `config` keys that map to providers (e.g., if `model.config.get("anthropic")` is True, call the anthropic provider). Priority/cost/scoring logic can remain in `route()`; `_call_model()` becomes a simple dispatcher.
- **Kernel integration**: New `_init_*_provider()` methods mirroring `_init_freellmapi()` but using the ProviderRegistry and gated by the integration framework (e.g., `anthropic` integration in `config/integrations.yaml`).
- **Secret handling**: Leverage existing ConfigurationManager secret detection (`is_secret_path()`) for fields like `llm.providers.anthropic.apiKey`. No new secret logic needed.
The core ModelRouter abstraction (capability routing, fallback chains, usage stats) can be retained; only the provider dispatch layer requires replacement.

## 5. Secret injection and protection
Secrets enter the system via the four-layer configuration merge (defaults → app → env → `AIOS_*` env vars). The ConfigurationManager (`src/aios/core/configuration_manager.py`) implements:
- `is_secret_path()`: detects secret keys by vocabulary (`secret`, `key`, `token`, `password`, `credential`)
- `_match_secret()`: case-insensitive match against vocabulary
- `get()`: returns `***` for secret paths (masked)
- `get_secret()`: returns raw secret value (fail-closed via SecurityManager authorization)
- `rotate_secret()`: fail-closed overlay mechanism
- Secret overlay (`_secret_overlay`) shadows rotated values without mutating base config
- `inspect(include_secrets=True)`: returns raw secrets only when authorized
In `model_router.py`, secrets like `llm.providers.openai.apiKey` are registered in `KernelConfigSchema` (lines 271-293) with `description="OpenAI API key (secret)"`. The ConfigurationManager automatically masks these in logs, exceptions, and outputs via `redact_secrets()` (from `src/aios/security/secrets.py`). The FreeLLMAPI provider already demonstrates secret safety: it reads `api_key` from config/environment but never logs or exposes it in error responses (verified by `test_freellmapi_secrets.py`). The same protection extends to any new provider using the existing secret infrastructure.

## 6. Health, quota, and retry integration
- **Health**: The generic `HealthManager` (Phase 3, C12) tracks component health via `register_check()` and `record_health()`. It emits canonical `HEALTH_CHECK_*` events and exposes HTTP `/health` & `/ready` endpoints. Provider health can be integrated by having each provider backend report health status (e.g., via a `ping()` method) and the HealthManager aggregating results. No provider-specific health infrastructure exists today; this would be a new addition.
- **Quota/rate limit**: The `ResourceManager` (Phase 3, C13) manages `ResourceType.API_QUOTA` and `ResourceType.RATE_LIMIT` with allocations, wait-queues, and canonical events (`QUOTA_EXCEEDED`, `RESOURCE_ALLOCATED`). However, it is not LLM/provider-aware—quotas are generic resources. To make them provider-aware, either extend ResourceManager with provider-scoped quotas (e.g., `ResourceType.LLM_QUOTA_anthropic`) or create a new `LLMQuotaManager` that delegates to ResourceManager. The existing infrastructure supports the concept but lacks LLM-specific bindings.
- **Retry**: The generic `RetryManager` (`src/aios/core/retry.py`) provides `RetryPolicy` (max_retries, backoff strategies, jitter) and `RetryBudget`. It executes via `execute_with_retry()` and emits canonical events (`RETRY_EXECUTED`, `RETRY_BUDGET_EXHAUSTED`). Provider-specific retry policies can be applied by wrapping provider calls in `execute_with_retry()` with a policy derived from config (e.g., `llm.providers.anthropic.retry.max_retries`). The retry layer is already generic and provider-agnostic—no changes needed to integrate with new providers.

## 7. Failover and fallback behavior
Failover and fallback are already partially implemented in the ModelRouter:
- **Fallback chains**: The `_fallback_chains` dictionary (default: `["claude-sonnet-4", "claude-haiku-3.5", "gpt-4o-mini", "gpt-4o"]`) is consulted when capability-based routing finds no candidates. The router iterates the chain and returns the first enabled model.
- **Capability-based routing**: The `route()` method filters models by `required_capabilities` and scores remaining candidates by priority, cost, and capability match.
- **Provider-level failover**: Not yet implemented. With a native multi-provider router, failover could occur at two levels:
  1. Model-level: If the selected model fails (e.g., provider error), retry with the next model in the fallback chain (same provider or different).
  2. Provider-level: If a provider backend fails (e.g., network error), attempt the same model with a different provider (if configured) before falling back to model chain.
The current FreeLLMAPI-specific hook lacks provider-level failover—it only dispatches to FreeLLMAPI or falls back to mock. A native design would need to define whether failover happens per-request (retry with alternative provider/model) or via circuit-breaker patterns (temporarily disable unhealthy provider). The HealthManager and ResourceManager could feed into such logic.

## 8. Testing coverage and gaps
Current test coverage for provider/dispatch logic:
- **Unit tests**:
  - `test_model_router_dispatch.py`: verifies dispatch to FreeLLMAPI when marked, no dispatch when config missing/provider not registered, usage stats updated.
  - `test_freellmapi_dispatch.py`: confirms provider dispatched when registered via env, not dispatched when not registered, config respects env vars, safe failure on missing config, existing routing preserved.
  - `test_freellmapi_secrets.py`: validates secrets not exposed in logs, exceptions, string repr, error responses.
  - `test_freellmapi_failsafe.py`: tests graceful handling of missing base_url, connection errors, HTTP errors, no fabricated responses.
- **Integration tests**:
  - `test_user_resource_onboarding.py`: includes FreeLLMAPI endpoint reachability validation (mock mode passes with warning; REAL mode would require env gate + user resource).
- **Gaps**:
  - No tests for multi-provider dispatch (does not exist yet).
  - No tests for provider-specific configuration loading (anthropic/openai) from `llm.providers.*`.
  - No tests for secret handling in new providers (though existing tests confirm the framework works).
  - No tests for health/quota/retry integration with providers.
  - No tests for fallback chains involving multiple providers.
The existing suite confirms the current FreeLLMAPI hook is well-tested and safe, but does not exercise the desired multi-provider behavior.

## 9. Alignment with documented architecture (C13, INV-002, M13, M14-T2)
- **C13 (FreeLLMAPI is dev/test only)**: Currently satisfied—FreeLLMAPI is the only wired provider and is dev/test only (no SLA). A native multi-provider design would keep FreeLLMAPI as an optional provider but allow production providers (anthropic/openai) to be wired for real mode.
- **INV-002 (one ModelRouter)**: Satisfied—the router remains a singleton. The proposed ProviderRegistry would be a separate service; the router would delegate to it but not duplicate routing logic.
- **M13 (Terminal Architecture)**: The integration framework's fail-closed gating (`real_allowed()`) is already M13-compliant and would apply to new providers without change.
- **M14-T2 (specification)**: The spec calls for implementing real REST/filesystem paths for Supabase, n8n, Obsidian Git. It does *not* require provider work; the model router remains as-is with FreeLLMAPI as dev/test only. Thus, the current architecture aligns with M14-T2 scope—no provider work is stubbed or required.
The proposed changes do not violate any documented invariants; they extend the existing provider hook into a true multi-provider system while preserving all current guarantees.

## 10. Rough order-of-magnitude effort estimate
Implementing a native multi-provider model would require approximately **2-3 weeks** of effort (5-8 story points), broken down as follows:
- **ProviderRegistry service** (3-5 days): design, implement, test (registration, health, config).
- **Provider interface and configs** (2-3 days): abstract base class, Anthropic/OpenAI config dataclasses, secret field mapping.
- **Router modification** (1-2 days): replace FreeLLMAPI hook with generic provider loop, update tests.
- **Kernel integration** (2-3 days): `_init_anthropic_provider()`, `_init_openai_provider()` mirroring `_init_freellmapi()`, wiring to integration framework.
- **Testing** (2-3 days): unit tests for multi-provider dispatch, config loading, secret safety, fallback chains, integration with HealthManager/ResourceManager/RetryManager.
- **Documentation** (1 day): update architecture docs, configuration examples.
This estimate assumes reuse of existing secret, health, quota, and retry infrastructure. No changes to kernel boot sequence or core singleton pattern are required.

## 11. Risks and mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing FreeLLMAPI tests/dev workflow | High | Low | Keep FreeLLMAPI as a registered provider; modification is additive (router now checks multiple providers). All existing tests pass if FreeLLMAPI remains configured. |
| Secret leakage in new provider configs | High | Low | Reuse ConfigurationManager secret detection (`is_secret_path()`) and `redact_secrets()`. No new secret handling needed. |
| Integration framework misconfiguration (real_allowed) | Medium | Low | The framework is well-tested and used by 12+ integrations. New providers follow same pattern (`assert_real_allowed()`). |
| Provider-specific error handling inconsistencies | Medium | Medium | Define a standard `Provider.generate()` contract; all providers must return `ModelResponse` with optional `metadata={"error": ...}` on failure. Router treats non-2xx as mock-equivalent (safe fallback). |
| Over-engineering for hypothetical providers | Low | Medium | Start with anthropic/openai as concrete implementations; YAGNI for others. Interface allows future additions. |
The largest risk is complacency—assuming the current hook is "good enough." The mitigation is to treat this as a strict architectural improvement: the router must dispatch to *any* configured provider, not just FreeLLMAPI.

## 12. Exactly one recommended next implementation task
**Implement a generic ProviderRegistry service and modify ModelRouter to dispatch to any registered provider (not just FreeLLMAPI)**.  
This task is the smallest correct change that enables a native multi-provider model while preserving all existing behavior. It includes:
- Creating `src/aios/core/provider_registry.py` with `ProviderRegistry` class (registration, health, config storage).
- Defining abstract `BaseProvider` in `src/aios/core/provider.py` with `generate()` method.
- Updating `ModelRouter._call_model()` to iterate over registered providers based on `model.config` flags (e.g., `if model.config.get("anthropic") and self._provider_registry.get("anthropic")`).
- Keeping FreeLLMAPI as a registered provider (no behavioral change).
- All tests must pass; FreeLLMAPI-specific tests validate no regression.
This task avoids touching configuration schema, secret handling, health/quota/retry integration, or kernel boot sequence—focusing solely on the provider dispatch gap. It establishes the foundation for adding anthropic/openai (or other providers) in subsequent work without reopening the router logic.

## FINAL VERDICT: NATIVE PROVIDER ARCHITECTURE READY FOR IMPLEMENTATION
The AI-OS codebase possesses all necessary foundations to replace the FreeLLMAPI-dependent provider configuration with a native multi-provider model:
- The `ModelRouter` already implements capability-based routing, priority/cost scoring, and fallback chains.
- The integration framework provides fail-closed gating (REAL vs. mock) that applies uniformly to all integrations.
- Secret detection, masking, and rotation are handled by ConfigurationManager with no provider-specific changes needed.
- Generic health, quota, and retry infrastructure exists and can be integrated with minimal effort.
- The provider abstraction (`ModelProvider` enum, `ModelConfig.provider`) is already present, though currently underutilized.
- No architectural invariants (INV-002, C13, M13, M14-T2) are violated by introducing a generic provider dispatch mechanism.
The sole missing piece is replacing the FreeLLMAPI-specific hook in `ModelRouter._call_model()` with a loop over registered providers. This is a localized, well-contained change that does not require modifying configuration schemas, secret handling, or core singleton patterns. Once implemented, adding production providers (anthropic/openai) becomes a matter of registering provider backends and configuring them via the existing `llm.providers.*` layers—all protected by the same fail-closed gating and secret safeguards used by FreeLLMAPI today.