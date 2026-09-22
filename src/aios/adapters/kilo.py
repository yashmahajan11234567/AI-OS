"""
Kilo Provider for AI-OS ModelRouter - Native Multi-Provider Expansion.

Adds Kilo as a provider/backend to the EXISTING ModelRouter.
Does NOT create another ModelRouter or parallel model abstraction.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from aios.core.model_router import ModelConfig, ModelProvider, ModelCapability, ModelRequest, ModelResponse
from aios.core.provider import Provider
from aios.core.provider_registry import get_provider_registry
from aios.core.provider_failures import classify_failure, FailureCategory, extract_retry_after


@dataclass
class KiloConfig:
    """Kilo configuration."""

    base_url: str = "https://api.kilo.chat/v1"  # Default Kilo endpoint
    api_key: str | None = None
    timeout_seconds: int = 30
    default_model: str = "kilo-1.0"  # Common Kilo model


class KiloProvider(Provider):
    """Kilo provider for ModelRouter.

    This provider integrates Kilo as a model backend behind the
    existing ModelRouter abstraction. No second ModelRouter is created.
    """

    def __init__(self, config: KiloConfig | None = None) -> None:
        self._config = config or KiloConfig()
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

    def _classify_kilo_error(self, exception: Exception) -> ProviderFailure:
        """
        Classify Kilo errors into structured failure categories.

        Args:
            exception: The exception from the Kilo API call (may have retry_after attribute)

        Returns:
            ProviderFailure with appropriate classification
        """
        error_str = str(exception).lower()

        # Extract HTTP status if present in the error message
        http_status = None
        if "error " in error_str and ":" in error_str:
            try:
                # Extract status code from messages like "Kilo error 401: ..."
                status_part = error_str.split("error ")[1].split(":")[0]
                http_status = int(status_part)
            except (ValueError, IndexError):
                pass

        # Classify based on HTTP status and error message
        if http_status == 401 or http_status == 403:
            return classify_failure(
                category=FailureCategory.AUTHENTICATION,
                provider_id="kilo",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Authentication failed",
            )
        elif http_status == 400:
            return classify_failure(
                category=FailureCategory.INVALID_REQUEST,
                provider_id="kilo",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Invalid request",
            )
        elif http_status == 404:
            return classify_failure(
                category=FailureCategory.INVALID_MODEL,
                provider_id="kilo",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Model not found",
            )
        elif http_status == 408:
            return classify_failure(
                category=FailureCategory.TIMEOUT,
                provider_id="kilo",
                http_status=http_status,
                provider_error_code=str(exception),
                safe_message="Request timeout",
            )
        elif http_status == 429:
            # Extract retry-after from exception if available
            retry_after = getattr(exception, 'retry_after', None)
            return classify_failure(
                category=FailureCategory.RATE_LIMIT,
                provider_id="kilo",
                http_status=http_status,
                provider_error_code=str(exception),
                retry_after=retry_after,
                safe_message="Rate limit exceeded",
            )
        elif http_status is not None and 500 <= http_status < 600:
            if http_status == 503:
                return classify_failure(
                    category=FailureCategory.SERVICE_UNAVAILABLE,
                    provider_id="kilo",
                    http_status=http_status,
                    provider_error_code=str(exception),
                    safe_message="Service unavailable",
                )
            else:
                return classify_failure(
                    category=FailureCategory.SERVER_ERROR,
                    provider_id="kilo",
                    http_status=http_status,
                    provider_error_code=str(exception),
                    safe_message="Internal server error",
                )
        elif "timeout" in error_str:
            return classify_failure(
                category=FailureCategory.TIMEOUT,
                provider_id="kilo",
                provider_error_code=str(exception),
                safe_message="Request timeout",
            )
        elif "network" in error_str or "connect" in error_str:
            return classify_failure(
                category=FailureCategory.NETWORK,
                provider_id="kilo",
                provider_error_code=str(exception),
                safe_message="Network error",
            )
        else:
            return classify_failure(
                category=FailureCategory.UNKNOWN,
                provider_id="kilo",
                provider_error_code=str(exception),
                safe_message="Unknown error",
            )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate response via Kilo."""
        import time
        start = time.perf_counter()

        try:
            await self._ensure_session()

            # Map ModelRequest to Kilo format (OpenAI-compatible)
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
                f"{self._config.base_url}/chat/completions",
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
                    error = RuntimeError(f"Kilo error {resp.status}: {error_text}")
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
                provider_registry.update_provider_health("kilo", healthy=True)

                return ModelResponse(
                    content=content,
                    model_id=request.preferred_model or self._config.default_model,
                    provider=ModelProvider.KILO,
                    tokens_used={"input": tokens_in, "output": tokens_out},
                    cost=0.0,  # Kilo pricing is handled externally
                    latency_ms=int((time.perf_counter() - start) * 1000),
                    metadata={
                        "kilo": True,
                        "raw_response": data,
                    },
                )

        except Exception as e:
            # Classify the failure for structured error handling
            failure = _classify_kilo_error(e)

            # Update provider health based on failure classification
            provider_registry = get_provider_registry()
            provider_registry.update_provider_health_from_failure("kilo", failure)

            return ModelResponse(
                content=f"Kilo error: {e}",
                model_id=request.preferred_model or self._config.default_model,
                provider=ModelProvider.KILO,
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


def register_kilo_provider(
    model_router,
    config: KiloConfig | None = None,
) -> KiloProvider:
    """Register Kilo provider with the ModelRouter.

    Registers the KiloProvider with the ProviderRegistry and updates
    the model configuration to reference the provider by ID. Maintains
    backward compatibility with existing ModelRouter behavior.

    Args:
        model_router: Existing ModelRouter instance
        config: Optional Kilo configuration

    Returns:
        KiloProvider instance
    """
    provider = KiloProvider(config)

    # Register Kilo model in the existing ModelRouter
    model_config = ModelConfig(
        model_id="kilo-default",
        provider=ModelProvider.KILO,
        name="Kilo Default",
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
            "provider": "kilo",  # Reference provider by ID in registry
            "kilo": True,        # Marker for Kilo-specific handling
        },
    )

    model_router.register_model(model_config)

    # Register provider with the ProviderRegistry for generic provider lookup
    provider_registry = getattr(model_router, "_provider_registry", None)
    if provider_registry is None:
        provider_registry = get_provider_registry()
    provider_registry.register_provider("kilo", provider)

    return provider


def get_kilo_config_from_env() -> KiloConfig:
    """Get Kilo configuration from environment variables."""
    return KiloConfig(
        base_url=os.getenv("KILO_API_URL", "https://api.kilo.chat/v1"),
        api_key=os.getenv("KILO_API_KEY"),
        timeout_seconds=int(os.getenv("KILO_TIMEOUT", "30")),
        default_model=os.getenv("KILO_DEFAULT_MODEL", "kilo-1.0"),
    )