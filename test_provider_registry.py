#!/usr/bin/env python3
"""Test script to verify ProviderRegistry functionality."""

import asyncio
from aios.core.provider import Provider
from aios.core.provider_registry import ProviderRegistry
from aios.core.model_router import ModelRequest, ModelResponse, ModelProvider, ModelConfig


class TestProvider(Provider):
    """A simple test provider."""

    def __init__(self, name: str = "test"):
        self.name = name
        self.generate_called = False
        self.last_request = None

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a test response."""
        self.generate_called = True
        self.last_request = request
        return ModelResponse(
            content=f"Response from {self.name}",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
        )


async def test_provider_registry():
    """Test ProviderRegistry functionality."""
    print("Testing ProviderRegistry...")

    # Create registry
    registry = ProviderRegistry()

    # Test initial state
    assert len(registry.list_providers()) == 0
    assert not registry.has_provider("test-provider")
    assert registry.get_provider("test-provider") is None
    print("[PASS] Initial state correct")

    # Register provider
    provider = TestProvider("test-provider")
    registry.register_provider("test-provider", provider)

    # Test after registration
    assert len(registry.list_providers()) == 1
    assert registry.has_provider("test-provider")
    retrieved_provider = registry.get_provider("test-provider")
    assert retrieved_provider is provider
    print("[PASS] Provider registration and retrieval works")

    # Test provider functionality
    request = ModelRequest(prompt="test prompt")
    response = await provider.generate(request)
    assert provider.generate_called
    assert provider.last_request == request
    assert response.content == "Response from test-provider"
    print("[PASS] Provider generate method works")

    # Test unregistration
    result = registry.unregister_provider("test-provider")
    assert result
    assert len(registry.list_providers()) == 0
    assert not registry.has_provider("test-provider")
    assert registry.get_provider("test-provider") is None
    print("[PASS] Provider unregistration works")

    # Test unregistering non-existent provider
    result = registry.unregister_provider("non-existent")
    assert not result
    print("[PASS] Unregistering non-existent provider returns False")

    print("[PASS] All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_provider_registry())