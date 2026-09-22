"""
Debug test for ModelRouter provider calls.
"""

from __future__ import annotations

import asyncio

from aios.core.model_router import ModelRouter, ModelConfig, ModelRequest, ModelResponse, ModelProvider, ModelCapability
from aios.core.provider import Provider


class MockProvider(Provider):
    """Mock provider for testing."""

    def __init__(self, return_content: str = "mock-success"):
        self.return_content = return_content
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1
        print(f"MockProvider.generate called #{self.generate_call_count}")

        return ModelResponse(
            content=self.return_content,
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 10, "output": 5},
            cost=0.001
        )


def test_provider_call():
    """Test that provider calls work."""
    router = ModelRouter()

    # Create and register provider
    provider = MockProvider("provider-success")

    # Register model that uses the provider (backward compatibility approach)
    model_config = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True}  # This triggers backward compatibility
    )
    router.register_model(model_config)

    # Set the provider on the router
    router._freellmapi_provider = provider

    # Make a request
    async def make_request():
        request = ModelRequest(
            prompt="test prompt",
            required_capabilities=[ModelCapability.TEXT_GENERATION]
        )
        response = await router.generate(request)
        print(f"Response: {response.content}")
        print(f"Provider calls: {provider.generate_call_count}")
        assert provider.generate_call_count == 1
        assert "provider-success" in response.content

    # Run the async function
    asyncio.run(make_request())
    print("Provider call test passed!")


if __name__ == "__main__":
    test_provider_call()