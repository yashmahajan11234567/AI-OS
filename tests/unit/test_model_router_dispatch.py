"""
Unit tests for ModelRouter dispatch — M9 Model Access (#42).

Verifies that ModelRouter.generate() dispatches to a registered backend
provider (e.g. FreeLLMAPI) when the routed model is marked as a provider
model, and falls back to the deterministic mock path for non-provider models.

No real LLM backend is required: a fake provider is injected directly via the
``_freellmapi_provider`` attribute that ``register_freellmapi_provider``
sets, mirroring production wiring.
"""

from __future__ import annotations

import pytest

from aios.core.model_router import (
    ModelRouter,
    ModelConfig,
    ModelProvider,
    ModelCapability,
    ModelRequest,
    ModelResponse,
)
from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig


class FakeProvider:
    """Minimal stand-in for FreeLLMAPIProvider.generate."""

    def __init__(self, content="from-freellmapi"):
        self.calls = 0
        self._content = content

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(
            content=f"{self._content}: {request.prompt[:40]}",
            model_id=request.preferred_model or "freellmapi-default",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 10, "output": 20},
            cost=0.0,
            latency_ms=5,
            metadata={"provider": "fake"},
        )


@pytest.fixture
def router():
    r = ModelRouter()
    # Standard mock-only models present by default.
    return r


def _freellmapi_model(router: ModelRouter) -> ModelConfig:
    cfg = ModelConfig(
        model_id="freellmapi-default",
        provider=ModelProvider.LOCAL,
        name="FreeLLMAPI Default",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},
    )
    router.register_model(cfg)
    return cfg


@pytest.mark.asyncio
async def test_dispatches_to_freellmapi_provider_when_marked(router):
    """generate() must call the registered _freellmapi_provider.generate."""
    provider = FakeProvider(content="real-dispatch")
    router._freellmapi_provider = provider
    _freellmapi_model(router)

    resp = await router.generate(
        ModelRequest(prompt="hello world", preferred_model="freellmapi-default")
    )

    assert provider.calls == 1, "FreeLLMAPI provider was not invoked"
    assert resp.content.startswith("real-dispatch"), resp.content
    assert resp.metadata.get("provider") == "fake"
    # Latency field must be present and an int (dispatch contract).
    assert isinstance(resp.latency_ms, int)


@pytest.mark.asyncio
async def test_does_not_dispatch_to_freellmapi_when_config_missing(router):
    """A model not marked freellmapi must NOT call the provider even if set."""
    provider = FakeProvider()
    router._freellmapi_provider = provider
    # Register a NON-freellmapi model (default mock chain).
    # claude-sonnet-4 is in the default router already.
    resp = await router.generate(ModelRequest(prompt="mock me"))

    assert provider.calls == 0, "provider invoked for a non-freellmapi model"
    assert "Mock response" in resp.content, resp.content


@pytest.mark.asyncio
async def test_does_not_dispatch_when_provider_not_registered(router):
    """freellmapi-marked model with no _freellmapi_provider falls back to mock."""
    _freellmapi_model(router)
    assert not hasattr(router, "_freellmapi_provider") or getattr(
        router, "_freellmapi_provider", None
    ) is None

    resp = await router.generate(ModelRequest(prompt="no provider"))
    assert "Mock response" in resp.content, resp.content


@pytest.mark.asyncio
async def test_register_freellmapi_provider_wires_router_and_model(router):
    """register_freellmapi_provider must register model + store provider ref."""
    provider = FreeLLMAPIProvider(FreeLLMAPIConfig(base_url="http://example:1234"))
    register = __import__(
        "aios.adapters.freellmapi", fromlist=["register_freellmapi_provider"]
    )
    returned = register.register_freellmapi_provider(router, FreeLLMAPIConfig(base_url="http://example:1234"))

    assert returned is not None
    assert router._freellmapi_provider is returned
    assert "freellmapi-default" in router._models
    cfg = router._models["freellmapi-default"]
    assert cfg.config.get("freellmapi") is True
    assert cfg.provider is ModelProvider.LOCAL


@pytest.mark.asyncio
async def test_usage_stats_updated_on_dispatch(router):
    provider = FakeProvider(content="tracked")
    router._freellmapi_provider = provider
    _freellmapi_model(router)

    await router.generate(
        ModelRequest(prompt="track tokens", preferred_model="freellmapi-default")
    )
    stats = router.get_usage_stats("freellmapi-default")
    assert stats["requests"] == 1
    assert stats["tokens_in"] == 10
    assert stats["tokens_out"] == 20
    assert stats["total_cost"] == 0.0
