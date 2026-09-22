#!/usr/bin/env python3
"""Test script to verify FreeLLMAPI integration with ProviderRegistry."""

import asyncio
from aios.core.model_router import ModelRouter, ModelRequest, ModelResponse, ModelProvider
from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig, register_freellmapi_provider
from aios.core.provider_registry import ProviderRegistry
from aios.core.provider import Provider


class TestFakeProvider(Provider):
    """A minimal provider for testing dispatch."""

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


async def test_freellmapi_with_provider_registry():
    """Test FreeLLMAPI integration via ProviderRegistry."""
    print("Testing FreeLLMAPI integration with ProviderRegistry...")

    from aios.core.provider import Provider
    from aios.core.model_router import ModelResponse

    # Create router and register FreeLLMAPI
    router = ModelRouter()
    provider = register_freellmapi_provider(router, FreeLLMAPIConfig(base_url="http://test:1234"))

    # Verify provider was registered
    assert router._freellmapi_provider is provider
    assert isinstance(router._freellmapi_provider, FreeLLMAPIProvider)

    # Verify model was registered
    assert "freellmapi-default" in router._models
    cfg = router._models["freellmapi-default"]
    assert cfg.config.get("provider") == "freellmapi", f"Expected 'freellmapi', got {cfg.config.get('provider')}"

    # Verify provider is registered in the ProviderRegistry
    assert router._provider_registry.has_provider("freellmapi")
    registered_provider = router._provider_registry.get_provider("freellmapi")
    assert registered_provider is provider

    print("[PASS] Provider registered with ProviderRegistry")
    print("[PASS] Model config updated with provider ID")
    print("[PASS] FreeLLMAPI integration works!")


async def test_model_router_dispatch_via_provider_id():
    """Test that ModelRouter dispatches via provider ID."""
    print("\nTesting ModelRouter dispatch via ProviderRegistry...")

    from aios.core.model_router import ModelCapability, ModelProvider, ModelResponse, ModelConfig
    from aios.core.provider_registry import get_provider_registry, reset_provider_registry_singleton

    # Reset singleton for clean test
    reset_provider_registry_singleton()

    router = ModelRouter()

    # Create a fake provider and register it
    fake_provider = TestFakeProvider(content="via-registry")
    router._provider_registry.register_provider("my-fake-provider", fake_provider)

    # Register a model that uses our fake provider
    cfg = ModelConfig(
        model_id="fake-model",
        provider=ModelProvider.LOCAL,
        name="Fake Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "my-fake-provider"},
    )
    router.register_model(cfg)

    # Verify dispatch works
    request = ModelRequest(prompt="hello world", preferred_model="fake-model")
    response = await router.generate(request)

    assert fake_provider.calls == 1
    assert "via-registry" in response.content
    assert response.model_id == "fake-model"
    print("[PASS] ModelRouter dispatches via ProviderRegistry provider ID")

    # Clean up
    reset_provider_registry_singleton()


async def test_model_router_backward_compat():
    """Test that ModelRouter still works with legacy _freellmapi_provider."""
    print("\nTesting backward compatibility...")

    from aios.core.model_router import ModelCapability, ModelProvider, ModelConfig

    router = ModelRouter()

    # Register a legacy freellmapi model
    cfg = ModelConfig(
        model_id="legacy-freellmapi",
        provider=ModelProvider.LOCAL,
        name="Legacy FreeLLMAPI",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},  # Legacy flag
    )
    router.register_model(cfg)

    # Set _freellmapi_provider directly (backward compat path)
    fake_provider = TestFakeProvider(content="legacy-path")
    router._freellmapi_provider = fake_provider

    request = ModelRequest(prompt="hello", preferred_model="legacy-freellmapi")
    response = await router.generate(request)

    assert fake_provider.calls == 1
    assert "legacy-path" in response.content
    print("[PASS] Backward compatibility maintained")


async def test_model_router_no_provider():
    """Test that ModelRouter falls back to mock when no provider."""
    print("\nTesting ModelRouter mock fallback...")

    from aios.core.model_router import ModelCapability, ModelProvider, ModelConfig

    router = ModelRouter()

    # Register a model without any provider
    cfg = ModelConfig(
        model_id="no-provider",
        provider=ModelProvider.LOCAL,
        name="No Provider",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={},
    )
    router.register_model(cfg)

    request = ModelRequest(prompt="hello", preferred_model="no-provider")
    response = await router.generate(request)

    assert "Mock response" in response.content
    print("[PASS] Mock fallback works when no provider registered")


if __name__ == "__main__":
    from aios.core.provider_registry import reset_provider_registry_singleton

    # Reset singleton before each test that creates a ModelRouter
    reset_provider_registry_singleton()
    asyncio.run(test_freellmapi_with_provider_registry())

    reset_provider_registry_singleton()
    asyncio.run(test_model_router_dispatch_via_provider_id())

    reset_provider_registry_singleton()
    asyncio.run(test_model_router_backward_compat())

    reset_provider_registry_singleton()
    asyncio.run(test_model_router_no_provider())

    print("\n[PASS] All integration tests passed!")