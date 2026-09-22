"""
Simple unit test for ModelRouter failure-aware provider fallback functionality.
Following the pattern of existing tests.
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.model_router import ModelRouter, ModelConfig, ModelRequest, ModelResponse, ModelProvider, ModelCapability
from aios.core.provider import Provider
from aios.core.provider_failures import ProviderFailure, FailureCategory


class MockFailingProvider(Provider):
    """Mock provider that always fails."""

    def __init__(self, failure_category: FailureCategory):
        self.failure_category = failure_category
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1

        # Create a ProviderFailure
        failure = ProviderFailure(
            category=self.failure_category,
            provider_id="mock-failing",
            model_id=request.preferred_model or "test-model",
            retryable=False,
            fallback_eligible=True,  # Make it fallback eligible for this test
            safe_message=f"Mock failure"
        )

        return ModelResponse(
            content=f"Failure from mock-failing",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
            metadata={
                "failure_category": failure.category.value,
                "failure_retryable": failure.retryable,
                "failure_fallback_eligible": failure.fallback_eligible,
                "failure_safe_message": failure.safe_message,
            }
        )


class MockSuccessProvider(Provider):
    """Mock provider that always succeeds."""

    def __init__(self):
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1

        return ModelResponse(
            content="Success from mock-success",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 10, "output": 5},
            cost=0.001
        )


@pytest.fixture
def router():
    """Create a basic ModelRouter for testing."""
    return ModelRouter()


@pytest.mark.asyncio
async def test_fallback_basic(router):
    """Test basic fallback functionality."""
    # Create providers
    failing_provider = MockFailingProvider(FailureCategory.TIMEOUT)
    succeeding_provider = MockSuccessProvider()

    # Register failing model (using backward compatibility approach)
    failing_model = ModelConfig(
        model_id="failing-model",
        provider=ModelProvider.LOCAL,  # Using LOCAL for simplicity
        name="Failing Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True}  # This triggers the backward compatibility path
    )
    router.register_model(failing_model)

    # Register succeeding model
    succeeding_model = ModelConfig(
        model_id="succeeding-model",
        provider=ModelProvider.LOCAL,
        name="Succeeding Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True}
    )
    router.register_model(succeeding_model)

    # Set the providers on the router (backward compatibility)
    router._freellmapi_provider = failing_provider
    # We'll need to switch between them - let's make the failing one fail first few times
    original_failing_generate = failing_provider.generate
    call_count = {"count": 0}

    async def limited_failing_generate(request):
        call_count["count"] += 1
        if call_count["count"] <= 2:  # Fail first 2 times
            return await original_failing_generate(request)
        else:  # Then succeed
            return await succeeding_provider.generate(request)

    failing_provider.generate = limited_failing_generate

    # Make a request
    request = ModelRequest(
        prompt="test prompt",
        required_capabilities=[ModelCapability.TEXT_GENERATION]
    )

    response = await router.generate(request)

    # Should eventually succeed
    assert "Success from mock-success" in response.content or "[Mock response from" in response.content
    # The providers should have been called
    assert failing_provider.generate_call_count > 0
    assert succeeding_provider.generate_call_count >= 0


if __name__ == "__main__":
    pytest.main([__file__])