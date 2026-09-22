#!/usr/bin/env python3
"""
Verification test for the ModelRouter provider registry boolean check fix.
"""

import asyncio
from aios.core.model_router import ModelRouter, ModelConfig, ModelRequest, ModelProvider, ModelCapability, ModelResponse
from aios.core.provider import Provider
from aios.core.provider_registry import ProviderRegistry

class TestProvider(Provider):
    """Simple test provider."""

    def __init__(self, name: str):
        self.name = name
        self.call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.call_count += 1
        return ModelResponse(
            content=f"Response from {self.name}",
            model_id=request.preferred_model or "test",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 5, "output": 3},
            cost=0.001
        )

async def test_empty_registry_boolean_check():
    """Test that ModelRouter works with an empty provider registry."""
    print("Creating ModelRouter with empty provider registry...")

    # Create an empty provider registry (this is the scenario that was broken)
    registry = ProviderRegistry()

    # Verify the registry is empty but not None
    print(f"Registry is None: {registry is None}")
    print(f"Registry length: {len(list(registry._providers.keys()))}")
    print(f"Boolean check (old way): {bool(registry)}")  # This was the problem!
    print(f"Boolean check (new way): {registry is not None}")  # This is the fix

    # Create ModelRouter with the empty registry
    router = ModelRouter(provider_registry=registry)

    # Register a test model
    test_model = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "test-provider"}  # This will be looked up in the registry
    )
    router.register_model(test_model)

    # Register our test provider with the registry
    test_provider = TestProvider("test-provider")
    registry.register_provider("test-provider", test_provider)

    # Make a request
    request = ModelRequest(
        prompt="test prompt",
        required_capabilities=[ModelCapability.TEXT_GENERATION],
        preferred_model="test-model"
    )

    print(f"Making request to {request.preferred_model}...")
    response = await router.generate(request)

    print(f"Response: {response.content}")
    print(f"Provider called: {test_provider.call_count} times")

    # Verify it worked
    assert test_provider.call_count == 1, f"Expected provider to be called once, but was called {test_provider.call_count} times"
    assert "Response from test-provider" in response.content, f"Unexpected response: {response.content}"

    print("TEST PASSED: The boolean check fix works correctly.")
    return True

if __name__ == "__main__":
    try:
        result = asyncio.run(test_empty_registry_boolean_check())
        if result:
            print("\nVERIFICATION SUCCESSFUL: The fix resolves the issue!")
        else:
            print("\nVERIFICATION FAILED")
            exit(1)
    except Exception as e:
        print(f"\nVERIFICATION ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)