"""
Model Router for AI-OS Hermes Kernel.

Routes LLM requests to appropriate models (Claude, local, cloud) with fallback,
caching, and cost optimization.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, List, Optional
from uuid import uuid4

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.core.provider import Provider
from aios.core.provider_registry import get_provider_registry, ProviderSelectionPolicy
from aios.core.model_types import ModelStatus, ProviderSelectionPolicy
from aios.core.provider_failures import ProviderFailure, classify_failure, FailureCategory
from aios.core.retry import get_retry_manager
from aios.events.core.types import EventType
from aios.core.configuration_manager import get_configuration_manager
from aios.core.rate_limit_quota_manager import get_rate_limit_quota_manager

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """Model provider types."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    LOCAL = "local"
    OLLAMA = "ollama"
    VLLM = "vllm"
    BEDROCK = "bedrock"
    VERTEX = "vertex"
    NIM = "nim"
    KILO = "kilo"
    AGNES = "agnes"
    GEMINI = "gemini"
    OLLAMA_CLOUD = "ollama_cloud"


class ModelCapability(str, Enum):
    """Model capabilities."""

    TEXT_GENERATION = "text_generation"
    CODE_GENERATION = "code_generation"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"


@dataclass
class ModelConfig:
    """Model configuration."""

    model_id: str
    provider: ModelProvider
    name: str
    capabilities: list[ModelCapability] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    priority: int = 100
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelRequest:
    """Model request with routing hints."""

    prompt: str
    system_prompt: str | None = None
    required_capabilities: list[ModelCapability] = field(default_factory=list)
    preferred_model: str | None = None
    preferred_provider: ModelProvider | None = None
    max_tokens: int | None = None
    temperature: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))


@dataclass
class ModelResponse:
    """Model response."""

    content: str
    model_id: str
    provider: ModelProvider
    tokens_used: dict[str, int] = field(default_factory=dict)
    cost: float = 0.0
    latency_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageRecord:
    """Timestamped usage record for model requests."""
    timestamp: datetime  # timezone-aware UTC
    provider_id: str
    model_id: str
    request_count: int = 1
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    cost: float = 0.0
    latency_ms: int = 0
    success: bool = True


class ModelRouter:
    """
    Routes model requests to the best available model.

    Features:
    - Capability-based routing
    - Cost optimization
    - Fallback chains
    - Load balancing
    - Usage tracking
    - Failure-aware provider fallback
    """

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        provider_registry: Any | None = None,
        model_catalog: ModelCatalog | None = None,
    ):
        """
        Initialize the Model Router.

        Args:
            config: Configuration dictionary
            provider_registry: ProviderRegistry instance for provider lookup
            model_catalog: ModelCatalog instance for model metadata (optional)
        """
        self._models: dict[str, ModelConfig] = {}
        self._fallback_chains: dict[str, list[str]] = {}
        self._usage_stats: dict[str, dict[str, Any]] = {}
        self._usage_records: deque[UsageRecord] = deque()
        self._usage_lock = __import__('threading').RLock()
        self._config = config or {}
        self._provider_registry = provider_registry if provider_registry is not None else get_provider_registry()
        self._model_catalog = model_catalog
        # Track attempted (provider_id, model_id) combinations per correlation_id to prevent loops
        self._attempted_combinations: dict[str, set[tuple[str, str]]] = {}

        # Load retention configuration
        config_manager = get_configuration_manager()
        self._retention_hours = config_manager.get("usage.retention_hours", 24.0)

        # Initialize Rate Limit Quota Manager
        self._quota_manager = get_rate_limit_quota_manager()

        # Load default models
        self._load_default_models()

    def _load_default_models(self) -> None:
        """Load default model configurations."""
        defaults = [
            ModelConfig(
                model_id="claude-opus-4",
                provider=ModelProvider.ANTHROPIC,
                name="Claude Opus 4",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.ANALYSIS,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=8192,
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                priority=10,
            ),
            ModelConfig(
                model_id="claude-sonnet-4",
                provider=ModelProvider.ANTHROPIC,
                name="Claude Sonnet 4",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=8192,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                priority=20,
            ),
            ModelConfig(
                model_id="claude-haiku-3.5",
                provider=ModelProvider.ANTHROPIC,
                name="Claude Haiku 3.5",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=4096,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                priority=30,
            ),
            ModelConfig(
                model_id="gpt-4o",
                provider=ModelProvider.OPENAI,
                name="GPT-4o",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.REASONING,
                    ModelCapability.FUNCTION_CALLING,
                    ModelCapability.VISION,
                ],
                max_tokens=4096,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                priority=15,
            ),
            ModelConfig(
                model_id="gpt-4o-mini",
                provider=ModelProvider.OPENAI,
                name="GPT-4o Mini",
                capabilities=[
                    ModelCapability.TEXT_GENERATION,
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.FUNCTION_CALLING,
                ],
                max_tokens=4096,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                priority=25,
            ),
        ]

        for model in defaults:
            self.register_model(model)

        # Default fallback chain
        self._fallback_chains["default"] = [
            "claude-sonnet-4",
            "claude-haiku-3.5",
            "gpt-4o-mini",
            "gpt-4o",
        ]

    def register_model(self, model: ModelConfig) -> None:
        """Register a model."""
        self._models[model.model_id] = model
        self._usage_stats[model.model_id] = {
            "requests": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "total_cost": 0.0,
            "errors": 0,
            "avg_latency_ms": 0,
        }
        logger.info(f"Registered model: {model.model_id} ({model.provider.value})")

        # Also register in model catalog if available
        if self._model_catalog is not None:
            # Import locally to avoid circular imports
            from aios.core.model_catalog import ModelMetadata, ModelStatus
            from aios.core.model_discovery import ModelCapability as CatalogCapability

            capabilities = [
                CatalogCapability(c.value if isinstance(c, str) else c)
                for c in model.capabilities
            ]
            catalog_model = ModelMetadata(
                model_id=model.model_id,
                provider_id=model.provider.value,
                display_name=model.name,
                capabilities=capabilities,
                status=ModelStatus.AVAILABLE if model.enabled else ModelStatus.UNAVAILABLE,
                limits=None,  # Could be populated from model.config
            )
            self._model_catalog.register_model(catalog_model)

    def unregister_model(self, model_id: str) -> bool:
        """Unregister a model."""
        if model_id in self._models:
            del self._models[model_id]
            del self._usage_stats[model_id]

            # Also unregister from model catalog if available
            if self._model_catalog is not None:
                self._model_catalog.unregister_model(model_id)

            return True
        return False

    def set_fallback_chain(self, name: str, model_ids: list[str]) -> None:
        """Set a fallback chain."""
        # Validate all models exist
        for mid in model_ids:
            if mid not in self._models:
                raise ValueError(f"Model {mid} not registered")
        self._fallback_chains[name] = model_ids

    def route(self, request: ModelRequest) -> ModelConfig:
        """
        Select the best model for a request.

        Args:
            request: Model request with requirements

        Returns:
            Selected model configuration
        """
        # If specific model requested and available
        if request.preferred_model and request.preferred_model in self._models:
            model = self._models[request.preferred_model]
            if model.enabled:
                return model

        # If provider preference
        if request.preferred_provider:
            candidates = [
                m for m in self._models.values()
                if m.provider == request.preferred_provider and m.enabled
            ]
            if candidates:
                return self._select_best(candidates, request)

        # Capability-based routing
        candidates = self._filter_by_capabilities(request.required_capabilities)
        if candidates:
            return self._select_best(candidates, request)

        # Fallback to default chain
        for mid in self._fallback_chains.get("default", []):
            if mid in self._models and self._models[mid].enabled:
                return self._models[mid]

        # Last resort: any enabled model
        enabled = [m for m in self._models.values() if m.enabled]
        if enabled:
            return enabled[0]

        raise ValueError("No available models")

    def _filter_by_capabilities(
        self, capabilities: list[ModelCapability]
    ) -> list[ModelConfig]:
        """Filter models by required capabilities."""
        if not capabilities:
            return list(self._models.values())

        return [
            m for m in self._models.values()
            if m.enabled and all(c in m.capabilities for c in capabilities)
        ]

    def _select_best(
        self, candidates: list[ModelConfig], request: ModelRequest
    ) -> ModelConfig:
        """Select best model from candidates."""
        # Sort by priority, then cost, then capability match
        def score(model: ModelConfig) -> tuple:
            cost = model.cost_per_1k_input + model.cost_per_1k_output
            cap_match = sum(1 for c in request.required_capabilities if c in model.capabilities)
            return (model.priority, cost, -cap_match)

        return min(candidates, key=score)

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """
        Generate response using routed model with failure-aware provider fallback.

        Args:
            request: Model request

        Returns:
            Model response
        """
        print(f"[generate] Called with correlation_id: {request.correlation_id}")
        correlation_id = request.correlation_id

        # Clear any previous attempt history for this correlation_id
        self._clear_attempted_combinations(correlation_id)

        try:
            return await self._generate_with_fallback(request, correlation_id)
        finally:
            # Clean up attempt history to prevent memory leaks
            self._clear_attempted_combinations(correlation_id)

    async def _generate_with_fallback(self, request: ModelRequest, correlation_id: str) -> ModelResponse:
        """
        Internal method to generate response with failure-aware fallback logic.

        Args:
            request: Model request
            correlation_id: Request correlation ID for tracking attempts

        Returns:
            Model response
        """
        print(f"[_generate_with_fallback] Starting for correlation_id: {correlation_id}")
        # Get initial model selection
        model = self.route(request)
        print(f"[_generate_with_fallback] Selected model: {model.model_id} ({model.provider})")

        # Track the initial attempt
        provider_id = model.config.get("provider", model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
        model_id = model.model_id
        print(f"[_generate_with_fallback] Tracking attempt: {provider_id}/{model_id}")
        self._mark_combination_attempted(correlation_id, provider_id, model_id)

        # Call the model with retry logic
        response = await self._call_model(model, request)
        print(f"[_generate_with_fallback] _call_model returned: success={self._is_successful_response(response)}")

        # Check if the call was successful
        is_success = self._is_successful_response(response)
        print(f"[_generate_with_fallback] Response success check: {is_success}")
        if is_success:
            return response

        # Extract failure information
        failure = self._extract_provider_failure(response)
        print(f"[_generate_with_fallback] Extracted failure: {failure}")
        if failure is None:
            # No failure metadata, return as-is
            print(f"[_generate_with_fallback] No failure metadata found")
            return response

        # Check if fallback is eligible
        print(f"[_generate_with_fallback] Fallback eligible check: {failure.fallback_eligible}")
        if not failure.fallback_eligible:
            # Not eligible for fallback, return the failure
            print(f"[_generate_with_fallback] Not eligible for fallback")
            return response

        # Fallback is eligible, try to find an alternative
        print(f"[_generate_with_fallback] Trying fallback providers...")
        fallback_response = await self._try_fallback_providers(
            request, correlation_id, model, failure
        )
        print(f"[_generate_with_fallback] Fallback response: {fallback_response}")

        # If fallback succeeded, return it
        if fallback_response and self._is_successful_response(fallback_response):
            print(f"[_generate_with_fallback] Fallback succeeded")
            return fallback_response

        # If fallback also failed but is fallback-eligible, we could continue chaining
        # For now, return the last response (could be enhanced to chain multiple fallbacks)
        if fallback_response:
            print(f"[_generate_with_fallback] Fallback also failed, returning it")
            return fallback_response

        # No fallback available or fallback failed, return original failure
        print(f"[_generate_with_fallback] No fallback available, returning original failure")
        return response

    async def _call_model(
        self, model: ModelConfig, request: ModelRequest
    ) -> ModelResponse:
        """Call the selected model with retry logic.

        Implements pre-routing rate-limit and quota enforcement via RateLimitQuotaManager.

        Dispatches to a registered provider backend when one is wired for the
        routed model (e.g. FreeLLMAPI via the ProviderRegistry). Falls back to
        a mock response for unregistered/local-only providers so that the
        kernel always returns a deterministic shape without a live LLM backend.

        Provider dispatch follows this chain:
            requested provider
                    ↓
            ProviderRegistry
                    ↓
            registered provider implementation
                    ↓
            provider call (with retry logic)
        """
        # Check if provider is available (not in cooldown)
        provider_id = model.config.get("provider")
        if provider_id and self._provider_registry is not None:
            provider = self._provider_registry.get_provider(provider_id)
            if provider is None:
                # Provider might be in cooldown or disabled
                provider_health = self._provider_registry._provider_health.get(provider_id)
                if provider_health is not None and self._provider_registry._is_in_cooldown(provider_health):
                    # Provider is in cooldown, return a failure response
                    remaining_cooldown = self._provider_registry.get_provider_cooldown_remaining(provider_id)
                    return ModelResponse(
                        content=f"Provider '{provider_id}' is in cooldown for {remaining_cooldown:.0f} more seconds",
                        model_id=model.model_id,
                        provider=model.provider,
                        latency_ms=0,
                        metadata={
                            "failure_category": "cooldown",
                            "failure_retryable": False,
                            "fallback_eligible": True,
                            "failure_safe_message": f"Provider in cooldown for {remaining_cooldown:.0f} seconds",
                        }
                    )
        # Dispatch to a real provider backend when the routed model declares one.
        # The provider ID is stored in model.config["provider"].
        provider_id = model.config.get("provider")

        # Apply provider group selection if applicable
        original_provider_id = provider_id
        selected_provider_id = self._select_provider_from_group(model.model_id, provider_id)
        if selected_provider_id is not None and selected_provider_id != provider_id:
            provider_id = selected_provider_id
            logger.debug(
                "Using provider group selection: %s -> %s for model %s",
                original_provider_id, provider_id, model.model_id
            )

        provider = None

        if provider_id and self._provider_registry is not None:
            provider = self._provider_registry.get_provider(provider_id)
            # Check if provider is enabled; if not, treat as unavailable
            if provider is not None:
                provider_health = self._provider_registry._provider_health.get(provider_id)
                if provider_health is not None and not provider_health.enabled:
                    provider = None

        # Backward compatibility: Check for legacy _freellmapi_provider attribute
        # and freellmapi=True config flag (used by register_freellmapi_provider
        # when ProviderRegistry is not explicitly set on the router).
        if provider is None:
            freellmapi_provider = getattr(self, "_freellmapi_provider", None)
            if freellmapi_provider is not None and model.config.get("freellmapi"):
                # Apply provider group selection for backward compatibility
                selected_provider_id = self._select_provider_from_group(
                    model.model_id,
                    freellmapi_provider.config.get("provider") if hasattr(freellmapi_provider, 'config') else None
                )
                if selected_provider_id is not None:
                    # Update the freellmapi provider's config to use the selected provider
                    if hasattr(freellmapi_provider, 'config'):
                        freellmapi_provider.config["provider"] = selected_provider_id
                    logger.debug(
                        "Using provider group selection for freellmapi: %s -> %s for model %s",
                        freellmapi_provider.config.get("provider") if hasattr(freellmapi_provider, 'config') else None,
                        selected_provider_id,
                        model.model_id
                    )
                provider = freellmapi_provider
                # Check if the freellmapi provider is in cooldown
                freellmapi_health = getattr(self, "_freellmapi_provider_health", None)
                if freellmapi_health is not None and self._is_freellmapi_in_cooldown(freellmapi_health):
                    # Provider is in cooldown, return a failure response
                    remaining_cooldown = self._get_freellmapi_cooldown_remaining(freellmapi_health)
                    return ModelResponse(
                        content=f"Freellmapi provider is in cooldown for {remaining_cooldown:.0f} more seconds",
                        model_id=model.model_id,
                        provider=model.provider,
                        latency_ms=0,
                        metadata={
                            "failure_category": "cooldown",
                            "failure_retryable": False,
                            "fallback_eligible": True,
                            "failure_safe_message": f"Provider in cooldown for {remaining_cooldown:.0f} seconds",
                        }
                    )

        # For mock responses, no retry needed
        if provider is None:
            # No real backend registered for this model — return a deterministic
            # mock response (dev/test fallback per C13: FreeLLMAPI is dev/test only).
            start = time.perf_counter()
            await asyncio.sleep(0.1)  # Simulate latency
            response = ModelResponse(
                content=f"[Mock response from {model.model_id}] {request.prompt[:100]}...",
                model_id=model.model_id,
                provider=model.provider,
                tokens_used={"input": 100, "output": 50},
                cost=0.001,
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

            # Ensure the model_id is reflected on the response (providers may
            # resolve a different id). Keep latency fresh.
            response.model_id = model.model_id
            response.provider = model.provider
            response.latency_ms = int((time.perf_counter() - start) * 1000)

            return response

        # For actual provider calls, implement retry logic
        retry_manager = get_retry_manager()

        # Create a task ID for tracking this specific model call
        task_id = f"model-call:{model.model_id}:{request.correlation_id}"

        # Get retry policy for the provider or use defaults
        retry_policy = retry_manager.get_policy(provider_id)

        # Create a retry budget for this call
        budget = retry_manager.create_budget(task_id, provider_id, retry_policy)

        # Track the last response for final return
        last_response: ModelResponse | None = None
        lease: Optional[Lease] = None

        # Initial attempt + retries = max_retries + 1 total attempts
        for attempt_num in range(retry_policy.max_retries + 1):
            start_time = time.perf_counter()

            # Pre-routing rate-limit and quota enforcement
            estimated_tokens = self.estimate_cost(
                model.model_id,
                request.max_tokens or model.max_tokens,
                request.max_tokens or model.max_tokens  # Rough estimate for completion tokens
            ) * 1000  # Convert to tokens

            lease, admission_failure = self._quota_manager.admit_request(
                provider_id=provider_id,
                model_id=model.model_id,
                estimated_tokens=max(0, int(estimated_tokens))
            )

            # If admission is denied, do not invoke the provider
            if admission_failure is not None:
                # Update usage stats for the denied request
                stats = self._usage_stats.setdefault(
                    model.model_id,
                    {
                        "requests": 0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "total_cost": 0.0,
                        "errors": 0,
                        "avg_latency_ms": 0,
                    },
                )
                stats["requests"] += 1
                # For denied requests, tokens and cost are zero
                stats["tokens_in"] += 0
                stats["tokens_out"] += 0
                stats["total_cost"] += 0.0
                # Rolling average latency (zero for denied requests)
                prev_total = stats["avg_latency_ms"] * (stats["requests"] - 1)
                stats["avg_latency_ms"] = int((prev_total + 0) / stats["requests"]) if stats["requests"] > 0 else 0

                # Record usage for timestamped accounting (denied request)
                self._record_usage(
                    model_id=model.model_id,
                    provider_id=provider_id,
                    input_tokens=0,
                    output_tokens=0,
                    cost=0.0,
                    latency_ms=0,
                    success=False
                )

                # Record the quota denial attempt in the retry budget
                error_msg = f"Provider failure: {admission_failure.safe_message}"
                retry_after_ms = None
                if admission_failure.retry_after is not None:
                    # Convert seconds to milliseconds for retry budget
                    retry_after_ms = admission_failure.retry_after * 1000

                budget.record_attempt(Exception(error_msg), type(Exception).__name__, retry_after_ms)

                return ModelResponse(
                    content=error_msg,
                    model_id=model.model_id,
                    provider=model.provider,
                    latency_ms=0,
                    metadata={
                        "failure_category": admission_failure.category.value,
                        "failure_retryable": admission_failure.retryable,
                        "fallback_eligible": admission_failure.fallback_eligible,
                        "failure_provider": admission_failure.provider_id,
                        "failure_model": admission_failure.model_id,
                        "failure_http_status": admission_failure.http_status,
                        "failure_provider_code": admission_failure.provider_error_code,
                        "failure_retry_after": admission_failure.retry_after,
                    }
                )

            # Make the provider call (only if admission succeeded)
            response = await provider.generate(request)

            # Calculate latency
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            response.latency_ms = latency_ms
            response.model_id = model.model_id
            response.provider = model.provider

            # Check if the response indicates a successful call
            is_success = self._is_successful_response(response)

            if is_success:
                # Success - mark the last attempt as succeeded if there were retries
                if budget.attempts:
                    budget.attempts[-1].succeeded = True
                # Update usage stats
                stats = self._usage_stats.setdefault(
                    model.model_id,
                    {
                        "requests": 0,
                        "tokens_in": 0,
                        "tokens_out": 0,
                        "total_cost": 0.0,
                        "errors": 0,
                        "avg_latency_ms": 0,
                    },
                )
                stats["requests"] += 1
                stats["tokens_in"] += response.tokens_used.get("input", 0)
                stats["tokens_out"] += response.tokens_used.get("output", 0)
                stats["total_cost"] += response.cost
                # Rolling average latency
                prev_total = stats["avg_latency_ms"] * (stats["requests"] - 1)
                stats["avg_latency_ms"] = int((prev_total + response.latency_ms) / stats["requests"])

                # Record usage for timestamped accounting
                provider_id = model.config.get("provider", model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
                self._record_usage(
                    model_id=model.model_id,
                    provider_id=provider_id,
                    input_tokens=response.tokens_used.get("input", 0),
                    output_tokens=response.tokens_used.get("output", 0),
                    cost=response.cost,
                    latency_ms=response.latency_ms,
                    success=True
                )

                # Release the lease
                if lease is not None:
                    self._quota_manager.release_lease(lease)

                return response

            # Response indicates a failure - check if it's retryable
            if attempt_num < retry_policy.max_retries:
                # Record the failure attempt
                error_msg = response.content or "Unknown provider error"
                # Extract ProviderFailure to get retry_after information
                provider_failure = self._extract_provider_failure(response)
                retry_after_ms = None
                if provider_failure and provider_failure.retry_after is not None:
                    # Convert seconds to milliseconds
                    retry_after_ms = provider_failure.retry_after * 1000

                attempt = budget.record_attempt(Exception(error_msg), type(Exception).__name__, retry_after_ms)

                # Check if the failure is retryable based on ProviderFailure classification
                is_retryable = self._is_retryable_failure(response)

                if not is_retryable:
                    # Non-retryable failure - return immediately
                    # Update usage stats
                    stats = self._usage_stats.setdefault(
                        model.model_id,
                        {
                            "requests": 0,
                            "tokens_in": 0,
                            "tokens_out": 0,
                            "total_cost": 0.0,
                            "errors": 0,
                            "avg_latency_ms": 0,
                        },
                    )
                    stats["requests"] += 1
                    stats["tokens_in"] += response.tokens_used.get("input", 0)
                    stats["tokens_out"] += response.tokens_used.get("output", 0)
                    stats["total_cost"] += response.cost
                    # Rolling average latency
                    prev_total = stats["avg_latency_ms"] * (stats["requests"] - 1)
                    stats["avg_latency_ms"] = int((prev_total + response.latency_ms) / stats["requests"])

                    # Record usage for timestamped accounting
                    provider_id = model.config.get("provider", model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
                    self._record_usage(
                        model_id=model.model_id,
                        provider_id=provider_id,
                        input_tokens=response.tokens_used.get("input", 0),
                        output_tokens=response.tokens_used.get("output", 0),
                        cost=response.cost,
                        latency_ms=response.latency_ms,
                        success=False
                    )

                    # Release the lease
                    if lease is not None:
                        self._quota_manager.release_lease(lease)

                    return response

                # Publish retry scheduled event
                await retry_manager._emit_event(
                    EventType.RETRY_SCHEDULED,
                    {
                        "task_id": task_id,
                        "service": provider_id,
                        "retry_count": attempt.attempt,
                        "delay_ms": attempt.delay_ms,
                    },
                    correlation_id=request.correlation_id
                )

                # Wait before retry
                await asyncio.sleep(attempt.delay_ms / 1000.0)

                # Publish retry executed event
                await retry_manager._emit_event(
                    EventType.RETRY_EXECUTED,
                    {
                        "task_id": task_id,
                        "service": provider_id,
                        "retry_count": attempt.attempt,
                    },
                    correlation_id=request.correlation_id
                )

                # Store the response for potential final return
                last_response = response
            else:
                # Max retries reached - store the final response and break
                last_response = response
                break

        # All retries exhausted - publish exhaustion event and return final response
        if last_response:
            await retry_manager.retry_budget_exhausted(task_id, provider_id, budget, request.correlation_id)

            # Publish task failed event
            await retry_manager._emit_event(
                EventType.TASK_FAILED,
                {
                    "task_id": task_id,
                    "service": provider_id,
                    "error": last_response.content or "Max retries exceeded",
                    "error_type": "ProviderFailure",
                    "retryable": True,
                    "retry_count": retry_policy.max_retries,
                },
                correlation_id=request.correlation_id
            )

            # Update usage stats
            stats = self._usage_stats.setdefault(
                model.model_id,
                {
                    "requests": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "total_cost": 0.0,
                    "errors": 0,
                    "avg_latency_ms": 0,
                },
            )
            stats["requests"] += 1
            stats["tokens_in"] += last_response.tokens_used.get("input", 0)
            stats["tokens_out"] += last_response.tokens_used.get("output", 0)
            stats["total_cost"] += last_response.cost
            # Rolling average latency
            prev_total = stats["avg_latency_ms"] * (stats["requests"] - 1)
            stats["avg_latency_ms"] = int((prev_total + last_response.latency_ms) / stats["requests"])

            # Record usage for timestamped accounting
            provider_id = model.config.get("provider", model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
            self._record_usage(
                model_id=model.model_id,
                provider_id=provider_id,
                input_tokens=last_response.tokens_used.get("input", 0),
                output_tokens=last_response.tokens_used.get("output", 0),
                cost=last_response.cost,
                latency_ms=last_response.latency_ms,
                success=False
            )

            # Release the lease
            if lease is not None:
                self._quota_manager.release_lease(lease)

            return last_response

        # Fallback (should not reach here)
        # Update usage stats for unexpected error
        stats = self._usage_stats.setdefault(
            model.model_id,
            {
                "requests": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "total_cost": 0.0,
                "errors": 0,
                "avg_latency_ms": 0,
            },
        )
        stats["requests"] += 1
        # For unexpected error response, tokens and cost are zero
        stats["tokens_in"] += 0
        stats["tokens_out"] += 0
        stats["total_cost"] += 0.0
        # Rolling average latency (zero for unexpected error)
        prev_total = stats["avg_latency_ms"] * (stats["requests"] - 1)
        stats["avg_latency_ms"] = int((prev_total + 0) / stats["requests"]) if stats["requests"] > 0 else 0

        # Record usage for timestamped accounting
        provider_id = model.config.get("provider", model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
        self._record_usage(
            model_id=model.model_id,
            provider_id=provider_id,
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
            latency_ms=0,
            success=False
        )

        # Release the lease
        if lease is not None:
            self._quota_manager.release_lease(lease)

        return ModelResponse(
            content="Unexpected error in retry logic",
            model_id=model.model_id,
            provider=model.provider,
        )

    def get_usage_stats(self, model_id: str | None = None) -> dict[str, Any]:
        """Get usage statistics."""
        if model_id:
            return self._usage_stats.get(model_id, {})
        return self._usage_stats

    @property
    def model_catalog(self) -> ModelCatalog | None:
        """Get the model catalog (if one is configured)."""
        return self._model_catalog

    def sync_model_from_catalog(self, model_id: str) -> bool:
        """
        Sync a model's status from the catalog to the router.

        This allows the router to reflect catalog changes without
        requiring full model re-registration.

        Args:
            model_id: Identifier of the model to sync

        Returns:
            True if model was found in catalog and synced, False otherwise
        """
        if self._model_catalog is None:
            return False

        catalog_model = self._model_catalog.get_model(model_id)
        if catalog_model is None:
            return False

        router_model = self._models.get(model_id)
        if router_model is None:
            return False

        # Update enabled status based on catalog availability
        router_model.enabled = catalog_model.status == ModelStatus.AVAILABLE
        return True

    def get_available_models(
        self, capability: ModelCapability | None = None
    ) -> list[ModelConfig]:
        """Get list of available models."""
        models = [m for m in self._models.values() if m.enabled]
        if capability:
            models = [m for m in models if capability in m.capabilities]
        return sorted(models, key=lambda m: m.priority)

    def _is_successful_response(self, response: ModelResponse) -> bool:
        """
        Determine if a ModelResponse represents a successful call.

        Args:
            response: The ModelResponse to check

        Returns:
            True if the response represents a successful call, False otherwise
        """
        # Check for explicit success indicators in metadata
        if response.metadata.get("failure_category") is None:
            # No failure category means it's likely successful
            # Additional check: if there's content and no explicit error markers
            content = response.content or ""
            if not content.startswith("error:") and "authentication failed" not in content.lower():
                return True

        # Check for explicit failure indicators
        failure_category = response.metadata.get("failure_category")
        if failure_category:
            # Non-retryable failures are still failures
            failure_retryable = response.metadata.get("failure_retryable", False)
            return False  # If we have a failure category, it's a failure

        # Default: treat as successful if we have content and no obvious error
        content = response.content or ""
        return bool(content and not content.startswith("error:"))

    def _is_retryable_failure(self, response: ModelResponse) -> bool:
        """
        Determine if a ModelResponse represents a retryable failure.

        Args:
            response: The ModelResponse to check

        Returns:
            True if the failure is retryable, False otherwise
        """
        # Check for explicit retryable flag in metadata
        failure_retryable = response.metadata.get("failure_retryable")
        if failure_retryable is not None:
            return bool(failure_retryable)

        # Check failure category from metadata
        failure_category_str = response.metadata.get("failure_category")
        if failure_category_str:
            try:
                from aios.core.provider_failures import FailureCategory
                failure_category = FailureCategory(failure_category_str)

                # Use the existing classification rules
                from aios.core.provider_failures import FAILURE_CLASSIFICATION_RULES
                rules = FAILURE_CLASSIFICATION_RULES.get(
                    failure_category,
                    FAILURE_CLASSIFICATION_RULES[FailureCategory.UNKNOWN]
                )
                return bool(rules["retryable"])
            except ValueError:
                # Unknown failure category, default to non-retryable for safety
                return False

        # Fallback: check content for common retryable error patterns
        content = (response.content or "").lower()

        # Non-retryable patterns
        if any(pattern in content for pattern in [
            "authentication failed",
            "invalid request",
            "invalid model",
            "quota exceeded"
        ]):
            return False

        # Retryable patterns
        if any(pattern in content for pattern in [
            "timeout",
            "network",
            "server error",
            "service unavailable",
            "rate limit"
        ]):
            return True

        # Default to non-retryable for safety
        return False

    def estimate_cost(
        self, model_id: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost for a request."""
        model = self._models.get(model_id)
        if not model:
            return 0.0
        return (
            (input_tokens / 1000) * model.cost_per_1k_input
            + (output_tokens / 1000) * model.cost_per_1k_output
        )

    def _extract_provider_failure(self, response: ModelResponse) -> ProviderFailure | None:
        """
        Extract ProviderFailure from ModelResponse metadata.

        Args:
            response: ModelResponse to extract failure from

        Returns:
            ProviderFailure if failure metadata exists, None otherwise
        """
        metadata = response.metadata
        if not metadata.get("failure_category"):
            return None

        try:
            failure_category = FailureCategory(metadata["failure_category"])
            return ProviderFailure(
                category=failure_category,
                provider_id=metadata.get("failure_provider", "unknown"),
                model_id=metadata.get("failure_model"),
                retryable=metadata.get("failure_retryable", False),
                fallback_eligible=metadata.get("failure_fallback_eligible", False),
                http_status=metadata.get("failure_http_status"),
                provider_error_code=metadata.get("failure_provider_code"),
                retry_after=metadata.get("failure_retry_after"),
                safe_message=metadata.get("failure_safe_message", ""),
            )
        except (ValueError, KeyError):
            # If we can't parse the failure, treat as unknown failure
            return ProviderFailure(
                category=FailureCategory.UNKNOWN,
                provider_id="unknown",
                model_id=None,
                retryable=False,
                fallback_eligible=False,
                safe_message="Failed to parse failure metadata",
            )

    def _is_combination_attempted(self, correlation_id: str, provider_id: str, model_id: str) -> bool:
        """
        Check if a provider/model combination has already been attempted for this correlation_id.

        Args:
            correlation_id: Request correlation ID
            provider_id: Provider identifier
            model_id: Model identifier

        Returns:
            True if combination was attempted, False otherwise
        """
        if correlation_id not in self._attempted_combinations:
            return False
        return (provider_id, model_id) in self._attempted_combinations[correlation_id]

    def _mark_combination_attempted(self, correlation_id: str, provider_id: str, model_id: str) -> None:
        """
        Mark a provider/model combination as attempted for this correlation_id.

        Args:
            correlation_id: Request correlation ID
            provider_id: Provider identifier
            model_id: Model identifier
        """
        if correlation_id not in self._attempted_combinations:
            self._attempted_combinations[correlation_id] = set()
        self._attempted_combinations[correlation_id].add((provider_id, model_id))

    def _clear_attempted_combinations(self, correlation_id: str) -> None:
        """
        Clear attempted combinations history for a correlation_id.

        Args:
            correlation_id: Request correlation ID to clear history for
        """
        if correlation_id in self._attempted_combinations:
            del self._attempted_combinations[correlation_id]

    def _select_provider_from_group(
        self,
        model_id: str,
        provider_id: str | None = None
    ) -> str | None:
        """
        Select a provider from a provider group if the provider_id refers to a group.

        Args:
            model_id: The model ID being requested
            provider_id: The provider ID or group ID to select from

        Returns:
            Selected provider ID, or None if no group selection was made
        """
        if not provider_id or not self._provider_registry:
            return None

        # Check if the provider_id is actually a group ID
        group = self._provider_registry.get_provider_group(provider_id)
        if group is None:
            # Not a group, return the original provider_id
            return provider_id

        # It's a group, select a provider using the group's policy
        selected_provider = self._provider_registry.select_provider_from_group(
            group_id=provider_id,
            model_id=model_id
        )

        if selected_provider is not None:
            logger.debug(
                "Selected provider '%s' from group '%s' for model '%s' using policy %s",
                selected_provider, provider_id, model_id, group.policy.value
            )
            # Emit observability event for group selection
            self._emit_provider_group_selection_event(
                group_id=provider_id,
                selected_provider=selected_provider,
                policy=group.policy,
                eligible_count=len(group.provider_ids),
                model_id=model_id
            )
            return selected_provider
        else:
            logger.warning(
                "No provider selected from group '%s' for model '%s'",
                provider_id, model_id
            )
            return None

    def _emit_provider_group_selection_event(
        self,
        group_id: str,
        selected_provider: str,
        policy: ProviderSelectionPolicy,
        eligible_count: int,
        model_id: str
    ) -> None:
        """
        Emit PROVIDER_GROUP_SELECTED event for observability.

        Args:
            group_id: The provider group ID
            selected_provider: The selected provider ID
            policy: The selection policy used
            eligible_count: Number of eligible providers in the group
            model_id: The model ID being requested
        """
        try:
            bus = get_core_event_bus()
            if bus is None:
                logger.debug("EventBus not available, skipping PROVIDER_GROUP_SELECTED event emission")
                return

            import uuid as uuid_mod
            correlation_uuid = uuid_mod.uuid4()

            event = CoreEvent(
                eventType=EventType.PROVIDER_GROUP_SELECTED,
                source=self._get_identity(),
                correlationId=correlation_uuid,
                payload={
                    "group_id": group_id,
                    "selected_provider": selected_provider,
                    "policy": policy.value,
                    "eligible_count": eligible_count,
                    "model_id": model_id,
                },
            )

            # Properly await the publish coroutine
            result = bus.publish(event)
            if hasattr(result, "__await__"):
                asyncio.create_task(result)  # Fire and don't wait to avoid blocking

        except Exception as e:
            logger.warning(f"Failed to emit PROVIDER_GROUP_SELECTED event: {e}")

    def _record_usage(
        self,
        model_id: str,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
        latency_ms: int,
        success: bool
    ) -> None:
        """Record a timestamped usage event."""
        # Extract provider ID from model config if available, otherwise use enum value
        if provider_id is None:
            # This shouldn't happen in normal flow, but as fallback
            model = self._models.get(model_id)
            if model:
                provider_id = model.config.get("provider", model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
            else:
                provider_id = "unknown"

        usage_record = UsageRecord(
            timestamp=datetime.now(timezone.utc),
            provider_id=provider_id,
            model_id=model_id,
            request_count=1,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost=cost,
            latency_ms=latency_ms,
            success=success
        )

        with self._usage_lock:
            self._usage_records.append(usage_record)
            # Cleanup old records periodically (every 100 records to avoid overhead on every call)
            if len(self._usage_records) >= 100:
                self._cleanup_expired_records()

    def _cleanup_expired_records(self) -> None:
        """Remove usage records older than the retention period."""
        if not self._usage_records:
            return

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self._retention_hours)

        # Remove from left side of deque (oldest first)
        while self._usage_records and self._usage_records[0].timestamp < cutoff_time:
            self._usage_records.popleft()

    def get_usage_in_time_window(
        self,
        model_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[UsageRecord]:
        """
        Get usage records within specified time window.

        Args:
            model_id: Filter by model ID (None for all models)
            start_time: Start of time window (None for no lower bound)
            end_time: End of time window (None for no upper bound)

        Returns:
            List of usage records matching the criteria
        """
        with self._usage_lock:
            # Apply retention cleanup first
            self._cleanup_expired_records()

            # Filter records
            filtered_records = []
            for record in self._usage_records:
                # Model filtering
                if model_id is not None and record.model_id != model_id:
                    continue

                # Time filtering
                record_time = record.timestamp
                if start_time is not None and record_time < start_time:
                    continue
                if end_time is not None and record_time > end_time:
                    continue

                filtered_records.append(record)

            return filtered_records

    def _emit_model_fallback_event(
        self,
        correlation_id: str,
        source_provider: str,
        source_model: str,
        fallback_provider: str,
        fallback_model: str,
        failure_category: str,
        attempt_number: int
    ) -> None:
        """
        Emit MODEL_FALLBACK event for observability.

        Args:
            correlation_id: Request correlation ID
            source_provider: Provider that failed
            source_model: Model that failed
            fallback_provider: Provider being tried as fallback
            fallback_model: Model being tried as fallback
            failure_category: Category of the failure that triggered fallback
            attempt_number: Number of attempts made on the failed provider/model
        """
        try:
            bus = get_core_event_bus()
            if bus is None:
                logger.debug("EventBus not available, skipping MODEL_FALLBACK event emission")
                return

            import uuid as uuid_mod
            correlation_uuid = uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4()

            event = CoreEvent(
                eventType=EventType.MODEL_FALLBACK,
                source=self._get_identity(),
                correlationId=correlation_uuid,
                payload={
                    "correlation_id": correlation_id,
                    "source_provider": source_provider,
                    "source_model": source_model,
                    "fallback_provider": fallback_provider,
                    "fallback_model": fallback_model,
                    "failure_category": failure_category,
                    "attempt_number": attempt_number,
                },
            )

            # Properly await the publish coroutine
            result = bus.publish(event)
            if hasattr(result, "__await__"):
                asyncio.create_task(result)  # Fire and don't wait to avoid blocking

        except Exception as e:
            logger.warning(f"Failed to emit MODEL_FALLBACK event: {e}")

    def _get_identity(self):
        """Get component identity for event emission."""
        # Try to get from provider registry or create a basic identity
        if hasattr(self._provider_registry, '_identity'):
            return self._provider_registry._identity
        # Fallback to a basic identity
        from aios.events.core.identity import ComponentIdentity, ComponentType
        return ComponentIdentity(
            componentType=ComponentType.MODEL_ROUTER,
            instanceId="model-router",
            version=None
        )

    def _is_freellmapi_in_cooldown(self, freellmapi_health) -> bool:
        """Check if the freellmapi provider is currently in cooldown.

        Args:
            freellmapi_health: Freellmapi provider health object to check

        Returns:
            True if provider is in cooldown, False otherwise
        """
        # For backward compatibility, we assume freellmapi_health has similar structure
        # to _ProviderHealth for cooldown tracking
        cooldown_until = getattr(freellmapi_health, 'cooldown_until', 0.0)
        if cooldown_until <= 0:
            return False
        return time.time() < cooldown_until

    def _get_freellmapi_cooldown_remaining(self, freellmapi_health) -> float:
        """Get remaining cooldown time for freellmapi provider in seconds.

        Args:
            freellmapi_health: Freellmapi provider health object to check

        Returns:
            Remaining cooldown time in seconds, 0 if not in cooldown
        """
        cooldown_until = getattr(freellmapi_health, 'cooldown_until', 0.0)
        if cooldown_until <= 0:
            return 0.0
        remaining = cooldown_until - time.time()
        return max(0.0, remaining)


    async def _try_fallback_providers(
        self,
        request: ModelRequest,
        correlation_id: str,
        failed_model: ModelConfig,
        failure: ProviderFailure
    ) -> ModelResponse | None:
        """
        Try to find and execute a fallback provider/model combination.

        Args:
            request: Original model request
            correlation_id: Request correlation ID
            failed_model: The model that failed
            failure: ProviderFailure from the failed model

        Returns:
            ModelResponse from fallback if successful, None if no fallback available
        """
        print(f"[DEBUG] _try_fallback_providers called:")
        print(f"  request.preferred_model: {request.preferred_model}")
        print(f"  correlation_id: {correlation_id}")
        print(f"  failed_model.model_id: {failed_model.model_id}")
        print(f"  failed_model.provider: {failed_model.provider}")
        # Get the failed provider and model IDs
        failed_provider_id = failed_model.config.get("provider",
                                                   failed_model.provider.value if hasattr(failed_model.provider, 'value') else str(failed_model.provider))
        failed_model_id = failed_model.model_id

        # Emit fallback start event
        self._emit_model_fallback_event(
            correlation_id=correlation_id,
            source_provider=failed_provider_id,
            source_model=failed_model_id,
            fallback_provider="",  # Will be updated when we select a candidate
            fallback_model="",     # Will be updated when we select a candidate
            failure_category=failure.category.value if failure.category else "unknown",
            attempt_number=0  # Will be updated when we know the attempt count
        )

        # Get all enabled models that satisfy the request's capabilities
        capable_models = self._filter_by_capabilities(request.required_capabilities)

        # Filter out already attempted combinations and the failed model itself
        available_models = []
        for model in capable_models:
            provider_id = model.config.get("provider",
                                         model.provider.value if hasattr(model.provider, 'value') else str(model.provider))
            model_id = model.model_id

            # Skip if already attempted
            if self._is_combination_attempted(correlation_id, provider_id, model_id):
                continue

            # Skip the exact failed combination
            if provider_id == failed_provider_id and model_id == failed_model_id:
                continue

            # Check if provider is available via registry
            provider = None
            if provider_id and self._provider_registry is not None:
                provider = self._provider_registry.get_provider(provider_id)
                # Check if provider is enabled; if not, treat as unavailable
                if provider is not None:
                    provider_health = self._provider_registry._provider_health.get(provider_id)
                    if provider_health is not None and not provider_health.enabled:
                        provider = None

            # Backward compatibility check for legacy freellmapi
            if provider is None:
                freellmapi_provider = getattr(self, "_freellmapi_provider", None)
                if freellmapi_provider is not None and model.config.get("freellmapi"):
                    provider = freellmapi_provider

            # Only consider models with available providers
            if provider is not None:
                available_models.append((model, provider_id))

        if not available_models:
            logger.debug("No fallback models available for correlation_id: %s", correlation_id)
            return None

        # Select the best fallback model using existing logic
        # Create a temporary request to reuse _select_best
        fallback_model, fallback_provider_id = self._select_best_fallback(
            available_models, request, failed_provider_id, failed_model_id
        )

        if fallback_model is None:
            logger.debug("No suitable fallback model selected for correlation_id: %s", correlation_id)
            return None

        # Track the fallback attempt
        fallback_model_id = fallback_model.model_id
        self._mark_combination_attempted(correlation_id, fallback_provider_id, fallback_model_id)

        # Update the fallback event with actual selected values
        # Note: In a more sophisticated implementation, we would update the existing event
        # For now, we'll emit a new event with the correct information
        self._emit_model_fallback_event(
            correlation_id=correlation_id,
            source_provider=failed_provider_id,
            source_model=failed_model_id,
            fallback_provider=fallback_provider_id,
            fallback_model=fallback_model_id,
            failure_category=failure.category.value if failure.category else "unknown",
            attempt_number=0  # Will be tracked in the retry logic below
        )

        logger.info(
            "Attempting fallback from %s/%s to %s/%s for correlation_id: %s",
            failed_provider_id, failed_model_id,
            fallback_provider_id, fallback_model_id,
            correlation_id
        )

        # Call the fallback model with its own retry budget
        return await self._call_model(fallback_model, request)

    def _select_best_fallback(
        self,
        available_models: list[tuple[ModelConfig, str]],
        request: ModelRequest,
        failed_provider_id: str,
        failed_model_id: str
    ) -> tuple[ModelConfig | None, str | None]:
        """
        Select the best fallback model from available options.

        Args:
            available_models: List of (model, provider_id) tuples that are candidates
            request: Original model request
            failed_provider_id: Provider ID that failed
            failed_model_id: Model ID that failed

        Returns:
            Tuple of (selected_model, provider_id) or (None, None) if no suitable fallback
        """
        if not available_models:
            return None, None

        # Extract just the models for existing selection logic
        models = [model for model, _ in available_models]

        # Use existing _select_best method which considers priority, cost, and capability match
        best_model = self._select_best(models, request)

        if best_model is None:
            return None, None

        # Find the provider_id for the selected model
        for model, provider_id in available_models:
            if model.model_id == best_model.model_id:
                return best_model, provider_id

        # Fallback (should not happen if available_models is correct)
        return models[0] if models else None, available_models[0][1] if available_models else None

import asyncio

# Global model router instance
_global_model_router: ModelRouter | None = None


def get_model_router(config: dict[str, Any] | None = None) -> ModelRouter:
    """Get or create the global model router."""
    global _global_model_router
    if _global_model_router is None:
        _global_model_router = ModelRouter(config)
    return _global_model_router


def set_model_router(router: ModelRouter) -> None:
    """Set the global model router."""
    global _global_model_router
    _global_model_router = router


__all__ = [
    "ModelRouter",
    "ModelConfig",
    "ModelRequest",
    "ModelResponse",
    "ModelProvider",
    "ModelCapability",
    "get_model_router",
    "set_model_router",
    "ModelCatalog",
    "ModelStatus",
]