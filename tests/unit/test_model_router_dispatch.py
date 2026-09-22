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
from aios.core.provider_registry import ProviderRegistry


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
    print("DEBUG: Starting test_dispatches_to_freellmapi_provider_when_marked")
    provider = FakeProvider(content="real-dispatch")
    router._freellmapi_provider = provider
    _freellmapi_model(router)

    print(f"DEBUG: About to call router.generate with provider.calls={provider.calls}")
    resp = await router.generate(
        ModelRequest(prompt="hello world", preferred_model="freellmapi-default")
    )
    print(f"DEBUG: After router.generate, provider.calls={provider.calls}")

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


@pytest.mark.asyncio
async def test_disabled_provider_not_dispatched_via_registry():
    """Test that a disabled provider is not dispatched when looked up via ProviderRegistry."""
    # Create router with a provider registry
    provider_registry = ProviderRegistry()
    router = ModelRouter(provider_registry=provider_registry)

    # Create a mock provider
    class MockProvider:
        def __init__(self):
            self.generate_called = False

        async def generate(self, request):
            self.generate_called = True
            print(f"MockProvider.generate called with prompt: {request.prompt[:20]}...")
            return ModelResponse(
                content="mock response",
                model_id=request.preferred_model or "test",
                provider=ModelProvider.LOCAL,
            )

    mock_provider = MockProvider()
    provider_registry.register_provider("test-provider", mock_provider)

    # Register a model that uses this provider - mimic the existing test pattern
    model_config = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "test-provider"}  # This tells the router to use ProviderRegistry
    )
    router.register_model(model_config)

    # Debug: Check what actually got registered
    print(f"All models in router: {list(router._models.keys())}")
    if "test-model" in router._models:
        registered_model = router._models["test-model"]
        print(f"Registered model config: {registered_model.config}")
        print(f"Registered model provider: {registered_model.provider}")
        assert registered_model.config.get("provider") == "test-provider"
    else:
        print("ERROR: test-model not found in router._models")
        # Let's see what models ARE registered
        for model_id, model_config in router._models.items():
            print(f"  {model_id}: provider={model_config.provider}, config={model_config.config}")

    # Verify provider works when enabled
    print("Testing with ENABLED provider...")
    request = ModelRequest(prompt="test", preferred_model="test-model")
    response = await router.generate(request)
    print(f"Response from enabled provider: {response.content}")
    print(f"Mock provider generate_called: {mock_provider.generate_called}")

    assert mock_provider.generate_called == True, f"Expected generate to be called, got {mock_provider.generate_called}"
    assert response.content == "mock response", f"Expected 'mock response', got {response.content}"

    # Reset for next test
    mock_provider.generate_called = False

    # Disable the provider
    result = provider_registry.disable_provider("test-provider")
    assert result == True, "Failed to disable provider"

    # Debug: Check provider health state
    health = provider_registry._provider_health.get("test-provider")
    print(f"After disable - provider health: {health}")
    if health:
        print(f"After disable - provider enabled: {health.enabled}")

    # Verify provider is NOT dispatched when disabled
    print("Testing with DISABLED provider...")
    response = await router.generate(request)
    print(f"Response from disabled provider: {response.content}")
    print(f"Mock provider generate_called: {mock_provider.generate_called}")

    assert mock_provider.generate_called == False, f"Expected generate NOT to be called, got {mock_provider.generate_called}"
    assert "Mock response" in response.content, f"Expected 'Mock response' in content, got {response.content}"
    """Test that a disabled provider is not dispatched when looked up via ProviderRegistry."""
    # Create router with a provider registry
    provider_registry = ProviderRegistry()
    router = ModelRouter(provider_registry=provider_registry)

    # Create a mock provider
    class MockProvider:
        def __init__(self):
            self.generate_called = False

        async def generate(self, request):
            self.generate_called = True
            print(f"MockProvider.generate called with prompt: {request.prompt[:20]}...")
            return ModelResponse(
                content="mock response",
                model_id=request.preferred_model or "test",
                provider=ModelProvider.LOCAL,
            )

    mock_provider = MockProvider()
    provider_registry.register_provider("test-provider", mock_provider)

    # Register a model that uses this provider - mimic the existing test pattern
    model_config = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "test-provider"}  # This tells the router to use ProviderRegistry
    )
    router.register_model(model_config)

    # Debug: Check what actually got registered
    print(f"All models in router: {list(router._models.keys())}")
    if "test-model" in router._models:
        registered_model = router._models["test-model"]
        print(f"Registered model config: {registered_model.config}")
        print(f"Registered model provider: {registered_model.provider}")
        assert registered_model.config.get("provider") == "test-provider"
    else:
        print("ERROR: test-model not found in router._models")
        # Let's see what models ARE registered
        for model_id, model_config in router._models.items():
            print(f"  {model_id}: provider={model_config.provider}, config={model_config.config}")

    # Verify provider works when enabled
    print("Testing with ENABLED provider...")
    request = ModelRequest(prompt="test", preferred_model="test-model")
    response = await router.generate(request)
    print(f"Response from enabled provider: {response.content}")
    print(f"Mock provider generate_called: {mock_provider.generate_called}")

    assert mock_provider.generate_called == True, f"Expected generate to be called, got {mock_provider.generate_called}"
    assert response.content == "mock response", f"Expected 'mock response', got {response.content}"

    # Reset for next test
    mock_provider.generate_called = False

    # Disable the provider
    result = provider_registry.disable_provider("test-provider")
    assert result == True, "Failed to disable provider"

    # Debug: Check provider health state
    health = provider_registry._provider_health.get("test-provider")
    print(f"After disable - provider health: {health}")
    if health:
        print(f"After disable - provider enabled: {health.enabled}")

    # Verify provider is NOT dispatched when disabled
    print("Testing with DISABLED provider...")
    response = await router.generate(request)
    print(f"Response from disabled provider: {response.content}")
    print(f"Mock provider generate_called: {mock_provider.generate_called}")

    assert mock_provider.generate_called == False, f"Expected generate NOT to be called, got {mock_provider.generate_called}"
    assert "Mock response" in response.content, f"Expected 'Mock response' in content, got {response.content}"
