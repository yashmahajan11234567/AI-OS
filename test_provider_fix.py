#!/usr/bin/env python3
"""
Simple test to verify the provider disable fix works.
"""

import asyncio
from aios.core.model_router import ModelRouter, ModelConfig, ModelProvider, ModelCapability, ModelRequest, ModelResponse
from aios.core.provider_registry import ProviderRegistry


class MockProvider:
    def __init__(self):
        self.generate_called = False

    async def generate(self, request):
        self.generate_called = True
        print(f"MockProvider.generate called!")
        return ModelResponse(
            content="mock response",
            model_id=request.preferred_model or "test",
            provider=ModelProvider.LOCAL,
        )


async def test_provider_disable_fix():
    print("=== Testing Provider Disable Fix ===")

    # Create router with a provider registry
    provider_registry = ProviderRegistry()
    print(f"Initial provider_registry bool: {bool(provider_registry)}")
    print(f"Initial provider_registry len: {len(provider_registry)}")
    router = ModelRouter(provider_registry=provider_registry)
    print(f"Router's _provider_registry bool: {bool(router._provider_registry)}")
    print(f"Router's _provider_registry len: {len(router._provider_registry)}")

    # Create a mock provider
    mock_provider = MockProvider()
    print(f"Before registering provider - registry length: {len(provider_registry)}")
    provider_registry.register_provider("test-provider", mock_provider)
    print(f"After registering provider - registry length: {len(provider_registry)}")
    print(f"Providers in registry: {list(provider_registry._providers.keys())}")
    print(f"Router's registry length after registration: {len(router._provider_registry)}")
    print(f"Router's registry providers: {list(router._provider_registry._providers.keys())}")

    # Register a model that uses this provider
    model_config = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "test-provider"}
    )
    router.register_model(model_config)

    print(f"Registered models: {list(router._models.keys())}")
    if "test-model" in router._models:
        reg_model = router._models["test-model"]
        print(f"Model config: {reg_model.config}")

    # Test 1: Provider works when enabled
    print("\n--- Test 1: Enabled Provider ---")
    mock_provider.generate_called = False
    request = ModelRequest(prompt="test", preferred_model="test-model")
    response = await router.generate(request)

    print(f"Mock provider called: {mock_provider.generate_called}")
    print(f"Response: {response.content}")

    assert mock_provider.generate_called == True, "Provider should have been called when enabled"
    assert response.content == "mock response", "Should get mock response from provider"
    print("Enabled provider works correctly")

    # Test 2: Provider NOT called when disabled
    print("\n--- Test 2: Disabled Provider ---")
    mock_provider.generate_called = False
    provider_registry.disable_provider("test-provider")

    # Check health state
    health = provider_registry._provider_health.get("test-provider")
    print(f"Provider health after disable: {health}")
    if health:
        print(f"Provider enabled state: {health.enabled}")

    response = await router.generate(request)

    print(f"Mock provider called: {mock_provider.generate_called}")
    print(f"Response: {response.content}")

    assert mock_provider.generate_called == False, "Provider should NOT have been called when disabled"
    assert "Mock response" in response.content, "Should fall back to mock response when provider disabled"
    print("Disabled provider correctly not dispatched")

    # Test 3: Provider works again when re-enabled
    print("\n--- Test 3: Re-enabled Provider ---")
    mock_provider.generate_called = False
    provider_registry.enable_provider("test-provider")

    # Check health state
    health = provider_registry._provider_health.get("test-provider")
    print(f"Provider health after re-enable: {health}")
    if health:
        print(f"Provider enabled state: {health.enabled}")

    response = await router.generate(request)

    print(f"Mock provider called: {mock_provider.generate_called}")
    print(f"Response: {response.content}")

    assert mock_provider.generate_called == True, "Provider should have been called when re-enabled"
    assert response.content == "mock response", "Should get mock response from provider when re-enabled"
    print("Re-enabled provider works correctly")

    print("\nAll tests passed!")


if __name__ == "__main__":
    asyncio.run(test_provider_disable_fix())