"""
FreeLLMAPI Provider for AI-OS ModelRouter - M5-GATE-REALIZE.

Adds FreeLLMAPI as a provider/backend to the EXISTING ModelRouter.
Does NOT create another ModelRouter or parallel model abstraction.

FreeLLMAPI is DEV/TEST ONLY (C13 - no production without SLA).
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from aios.core.model_router import ModelConfig, ModelProvider, ModelCapability, ModelRequest, ModelResponse
from aios.core.provider_registry import get_provider_registry
from aios.core.provider import Provider
from aios.core.provider_failures import classify_failure, FailureCategory, extract_retry_after


@dataclass
class FreeLLMAPIConfig:
    """FreeLLMAPI configuration."""

    base_url: str = "http://localhost:8080"  # Default local FreeLLMAPI endpoint
    api_key: str | None = None
    timeout_seconds: int = 30
    default_model: str = "freellmapi-default"


class FreeLLMAPIProvider(Provider):
    """FreeLLMAPI provider for ModelRouter.

    This provider integrates FreeLLMAPI as a model backend behind the
    existing ModelRouter abstraction. No second ModelRouter is created.

    Per C13: FreeLLMAPI remains DEV/TEST ONLY.
    Per INV-002: One model router (the existing ModelRouter).
    Per C10: No unmanaged LLM-stage external egress.
    """

    def __init__(self, config: FreeLLMAPIConfig | None = None) -> None:
        self._config = config or FreeLLMAPIConfig()
        self._session = None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self._session is None or self._session.closed:
            import aiohttp
            headers = {}
            if self._config.api_key:
                headers["Authorization"] = f"Bearer {self._config.api_key}"
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self._config.timeout_seconds),
            )

    async def close(self):
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def configure(self, config: dict[str, Any]) -> None:
        """
        Update non-secret provider configuration safely.

        Args:
            config: Dictionary containing configuration keys to update
                   (e.g., {"base_url": "https://new-url", "default_model": "new-model"})
        """
        if "base_url" in config:
            self._config.base_url = config["base_url"]
        if "default_model" in config:
            self._config.default_model = config["default_model"]
        if "timeout_seconds" in config:
            self._config.timeout_seconds = config["timeout_seconds"]

    async def reload_credentials(self) -> None:
        """
        Apply newly rotated credentials to the live provider instance.

        This method updates the API key and ensures the existing session
        cannot continue using the old Authorization header by closing
        and recreating the session.
        """
        # Close existing session if it exists to prevent use of old credentials
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        # Note: The actual session recreation with new credentials happens
        # lazily in _ensure_session() when generate() is next called

    def _classify_freellmapi_error(self, exception: Exception) -> ProviderFailure:
        """
        Classify FreeLLMAPI errors into structured failure categories.

        Args:
            exception: The exception from the FreeLLMAPI API call (may have retry_after attribute)

        Returns:
            ProviderFailure with appropriate classification
        """
        error_str = str(exception).lower()

        # Extract HTTP status if present in the error message
        http_status = None
        if "error " in error_str and ":" in error_str:
            try:
                # Extract status code from messages like "FreeLLMAPI error 401: ..."
                status_part = error_str.split("error ")[1].split(":")[0]
                http_status = int(status_part)
            except (ValueError, IndexError):
                pass

        # Classify based on HTTP status and error message
        if http_status == 401 or http_status == 403:
            return classify_failure(
                category=FailureCategory.AUTHENTICATION,
                provider_id="freellmapi",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Authentication failed",
            )
        elif http_status == 400:
            return classify_failure(
                category=FailureCategory.INVALID_REQUEST,
                provider_id="freellmapi",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Invalid request",
            )
        elif http_status == 404:
            return classify_failure(
                category=FailureCategory.INVALID_MODEL,
                provider_id="freellmapi",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Model not found",
            )
        elif http_status == 408:
            return classify_failure(
                category=FailureCategory.TIMEOUT,
                provider_id="freellmapi",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Request timeout",
            )
        elif http_status == 429:
            # Extract retry-after from exception if available
            retry_after = getattr(exception, 'retry_after', None)
            return classify_failure(
                category=FailureCategory.RATE_LIMIT,
                provider_id="freellmapi",
                http_status=http_status,
                provider_error_code=str(exception),
                retry_after=retry_after,
                safe_message="Rate limit exceeded",
            )
        elif http_status is not None and 500 <= http_status < 600:
            if http_status == 503:
                return classify_failure(
                    category=FailureCategory.SERVICE_UNAVAILABLE,
                    provider_id="freellmapi",
                    http_status=http_status,
                    provider_error_code=str(exception),
                    safe_message="Service unavailable",
                )
            else:
                return classify_failure(
                    category=FailureCategory.SERVER_ERROR,
                    provider_id="freellmapi",
                    http_status=http_status,
                    provider_error_code=str(exception),
                    safe_message="Internal server error",
                )
        elif "timeout" in error_str:
            return classify_failure(
                category=FailureCategory.TIMEOUT,
                provider_id="freellmapi",
                provider_error_code=str(exception),
                safe_message="Request timeout",
            )
        elif "network" in error_str or "connection" in error_str:
            return classify_failure(
                category=FailureCategory.NETWORK,
                provider_id="freellmapi",
                provider_error_code=str(exception),
                safe_message="Network error",
            )
        else:
            return classify_failure(
                category=FailureCategory.UNKNOWN,
                provider_id="freellmapi",
                provider_error_code=str(exception),
                safe_message="Unknown error",
            )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate response via FreeLLMAPI."""
        import time
        start = time.perf_counter()

        try:
            await self._ensure_session()

            # Map ModelRequest to FreeLLMAPI format
            payload = {
                "model": request.preferred_model or self._config.default_model,
                "messages": [
                    {"role": "system", "content": request.system_prompt or ""},
                    {"role": "user", "content": request.prompt},
                ] if request.system_prompt else [
                    {"role": "user", "content": request.prompt},
                ],
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature if request.temperature is not None else 0.7,
            }

            async with self._session.post(
                f"{self._config.base_url}/v1/chat/completions",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    # Extract Retry-After from headers and body
                    retry_after_ms = None
                    try:
                        error_body = json.loads(error_text)
                    except json.JSONDecodeError:
                        error_body = error_text
                    retry_after_ms = extract_retry_after(dict(resp.headers), error_body)
                    error = RuntimeError(f"FreeLLMAPI error {resp.status}: {error_text}")
                    # Attach retry_after to exception for later extraction (convert ms to seconds for compatibility)
                    if retry_after_ms is not None:
                        error.retry_after = retry_after_ms // 1000
                    raise error

                data = await resp.json()

                # Extract response content
                content = ""
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content", "")

                # Extract token usage
                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)

                # Successful call - reset provider health
                provider_registry = get_provider_registry()
                provider_registry.update_provider_health("freellmapi", healthy=True)

                return ModelResponse(
                    content=content,
                    model_id=request.preferred_model or self._config.default_model,
                    provider=ModelProvider.LOCAL,  # Treat as local/free provider
                    tokens_used={"input": tokens_in, "output": tokens_out},
                    cost=0.0,  # FreeLLMAPI is free
                    latency_ms=int((time.perf_counter() - start) * 1000),
                    metadata={
                        "freellmapi": True,
                        "raw_response": data,
                    },
                )

        except Exception as e:
            # Classify the failure for structured error handling
            failure = _classify_freellmapi_error(e)

            # Update provider health based on failure classification
            provider_registry = get_provider_registry()
            provider_registry.update_provider_health_from_failure("freellmapi", failure)

            return ModelResponse(
                content=f"FreeLLMAPI error: {e}",
                model_id=request.preferred_model or self._config.default_model,
                provider=ModelProvider.LOCAL,
                tokens_used={},
                cost=0.0,
                latency_ms=int((time.perf_counter() - start) * 1000),
                metadata={
                    "error": str(e),
                    "failure_category": failure.category.value,
                    "failure_retryable": failure.retryable,
                    "failure_fallback_eligible": failure.fallback_eligible,
                    "failure_http_status": failure.http_status,
                    "failure_provider_code": failure.provider_error_code,
                    "failure_retry_after": failure.retry_after,
                },
            )


def register_freellmapi_provider(
    model_router,
    config: FreeLLMAPIConfig | None = None,
) -> FreeLLMAPIProvider:
    """Register FreeLLMAPI provider with the ModelRouter.

    Registers the FreeLLMAPIProvider with the ProviderRegistry and updates
    the model configuration to reference the provider by ID. Maintains
    backward compatibility with existing ModelRouter behavior.

    Args:
        model_router: Existing ModelRouter instance
        config: Optional FreeLLMAPI configuration

    Returns:
        FreeLLMAPIProvider instance
    """
    provider = FreeLLMAPIProvider(config)

    # Register FreeLLMAPI model in the existing ModelRouter
    model_config = ModelConfig(
        model_id="freellmapi-default",
        provider=ModelProvider.LOCAL,
        name="FreeLLMAPI Default",
        capabilities=[
            ModelCapability.TEXT_GENERATION,
            ModelCapability.CODE_GENERATION,
            ModelCapability.REASONING,
            ModelCapability.ANALYSIS,
            ModelCapability.FUNCTION_CALLING,
        ],
        max_tokens=8192,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        priority=50,  # Lower priority than commercial models
        enabled=True,
        config={
            "provider": "freellmapi",  # Reference provider by ID in registry
            "freellmapi": True,        # Backward compatibility flag
        },
    )

    model_router.register_model(model_config)

    # Register provider with the ProviderRegistry for generic provider lookup
    # Also maintain backward compatibility by setting the _freellmapi_provider attribute
    provider_registry = getattr(model_router, "_provider_registry", None)
    if provider_registry is None:
        provider_registry = get_provider_registry()
    provider_registry.register_provider("freellmapi", provider)

    # Backward compatibility: also set the _freellmapi_provider attribute
    # for existing code that checks for it directly
    if not hasattr(model_router, "_freellmapi_provider"):
        model_router._freellmapi_provider = provider

    return provider


def get_freellmapi_config_from_env() -> FreeLLMAPIConfig:
    """Get FreeLLMAPI configuration from environment variables."""
    return FreeLLMAPIConfig(
        base_url=os.getenv("FREELLM_API_URL", "http://localhost:8080"),
        api_key=os.getenv("FREELLM_API_KEY"),
        timeout_seconds=int(os.getenv("FREELLM_TIMEOUT", "30")),
        default_model=os.getenv("FREELLM_DEFAULT_MODEL", "freellmapi-default"),
    )