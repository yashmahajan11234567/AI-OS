"""
Debug test for ModelRouter provider calls with debugging.
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
        print(f"  Request model: {request.preferred_model}")

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
    print(f"Created provider: {provider}")

    # Register model that uses the provider (backward compatibility approach)
    model_config = ModelConfig(
        model_id="test-model",
        provider=ModelProvider.LOCAL,
        name="Test Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True}  # This triggers backward compatibility
    )
    print(f"Registering model: {model_config.model_id}")
    print(f"  Model config: {model_config.config}")
    router.register_model(model_config)
    print(f"  Registered models: {list(router._models.keys())}")
    if "test-model" in router._models:
        reg_model = router._models["test-model"]
        print(f"  Registered model config: {reg_model.config}")

    # Set the provider on the router
    router._freellmapi_provider = provider
    print(f"Set _freellmapi_provider: {router._freellmapi_provider is not None}")

    # Check what route selects
    request = ModelRequest(
        prompt="test prompt",
        required_capabilities=[ModelCapability.TEXT_GENERATION]
    )
    print(f"Making request for model: {request.preferred_model}")
    selected_model = router.route(request)
    print(f"Route selected: {selected_model.model_id}")
    print(f"  Selected model config: {selected_model.config}")
    print(f"  Selected model freellmapi flag: {selected_model.config.get('freellmapi')}")

    # Make a request for OUR model specifically
    request_with_preferred = ModelRequest(
        prompt="test prompt",
        preferred_model="test-model",  # Specify our model
        required_capabilities=[ModelCapability.TEXT_GENERATION]
    )

    async def make_request():
        print("About to call router.generate...")
        response = await router.generate(request_with_preferred)
        print(f"Response: {response.content}")
        print(f"Provider calls: {provider.generate_call_count}")
        assert provider.generate_call_count == 1
        assert "provider-success" in response.content

    # Run the async function
    asyncio.run(make_request())
    print("Provider call test completed!")


if __name__ == "__main__":
    test_provider_call()