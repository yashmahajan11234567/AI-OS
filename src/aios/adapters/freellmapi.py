"""
FreeLLMAPI Provider for AI-OS ModelRouter - M5-GATE-REALIZE.

Adds FreeLLMAPI as a provider/backend to the EXISTING ModelRouter.
Does NOT create another ModelRouter or parallel model abstraction.

FreeLLMAPI is DEV/TEST ONLY (C13 - no production without SLA).
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

from aios.core.model_router import ModelConfig, ModelProvider, ModelCapability, ModelRequest, ModelResponse


@dataclass
class FreeLLMAPIConfig:
    """FreeLLMAPI configuration."""

    base_url: str = "http://localhost:8080"  # Default local FreeLLMAPI endpoint
    api_key: str | None = None
    timeout_seconds: int = 30
    default_model: str = "freellmapi-default"


class FreeLLMAPIProvider:
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

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate response via FreeLLMAPI."""
        await self._ensure_session()

        import time
        start = time.perf_counter()

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

        try:
            async with self._session.post(
                f"{self._config.base_url}/v1/chat/completions",
                json=payload,
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise RuntimeError(f"FreeLLMAPI error {resp.status}: {error_text}")

                data = await resp.json()

                # Extract response content
                content = ""
                if "choices" in data and data["choices"]:
                    content = data["choices"][0].get("message", {}).get("content", "")

                # Extract token usage
                usage = data.get("usage", {})
                tokens_in = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)

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
            return ModelResponse(
                content=f"FreeLLMAPI error: {e}",
                model_id=request.preferred_model or self._config.default_model,
                provider=ModelProvider.LOCAL,
                tokens_used={},
                cost=0.0,
                latency_ms=int((time.perf_counter() - start) * 1000),
                metadata={"error": str(e)},
            )


def register_freellmapi_provider(
    model_router,
    config: FreeLLMAPIConfig | None = None,
) -> FreeLLMAPIProvider:
    """Register FreeLLMAPI provider with the existing ModelRouter.

    This is the ONLY way to add FreeLLMAPI - through the existing ModelRouter.
    Does NOT create a second ModelRouter.

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
        config={"freellmapi": True},
    )

    model_router.register_model(model_config)

    # Store provider reference for actual calls
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