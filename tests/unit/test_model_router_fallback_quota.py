"""
Unit test for ModelRouter fallback on QUOTA_EXCEEDED (fallback eligible, non-retryable).
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.model_router import ModelRouter, ModelConfig, ModelRequest, ModelResponse, ModelProvider, ModelCapability
from aios.core.provider import Provider
from aios.core.provider_failures import ProviderFailure, FailureCategory
from aios.core.provider_registry import ProviderRegistry


class MockQuotaExceededProvider(Provider):
    """Mock provider that always fails with QUOTA_EXCEEDED."""

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1

        # QUOTA_EXCEEDED is fallback_eligible=True, retryable=False
        failure = ProviderFailure(
            category=FailureCategory.QUOTA_EXCEEDED,
            provider_id=self.provider_id,
            model_id=request.preferred_model or "test-model",
            retryable=False,
            fallback_eligible=True,
            safe_message=f"Quota exceeded from {self.provider_id}"
        )

        return ModelResponse(
            content=f"Quota exceeded from {self.provider_id}",
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

    def __init__(self, provider_id: str):
        self.provider_id = provider_id
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1

        return ModelResponse(
            content=f"Success from {self.provider_id}",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 10, "output": 5},
            cost=0.001
        )


@pytest.fixture
def registry_router():
    """Create a ModelRouter with a ProviderRegistry."""
    registry = ProviderRegistry()
    return ModelRouter(provider_registry=registry)


@pytest.mark.asyncio
async def test_fallback_on_quota_exceeded(registry_router):
    """Test that fallback occurs on QUOTA_EXCEEDED failure."""
    # Create a failing provider with QUOTA_EXCEEDED
    failing_provider = MockQuotaExceededProvider(
        provider_id="quota-failing-provider"
    )

    # Create a succeeding provider for fallback
    succeeding_provider = MockSuccessProvider(
        provider_id="success-fallback-provider"
    )

    # Register the failing model
    failing_model = ModelConfig(
        model_id="quota-failing-model",
        provider=ModelProvider.NIM,
        name="Quota Failing Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "nim"}
    )
    registry_router.register_model(failing_model)

    # Register the succeeding model
    succeeding_model = ModelConfig(
        model_id="success-fallback-model",
        provider=ModelProvider.KILO,
        name="Success Fallback Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"provider": "kilo"}
    )
    registry_router.register_model(succeeding_model)

    # Mock the provider registry to return our providers
    def mock_get_provider(provider_id):
        if provider_id == "nim":
            return failing_provider
        elif provider_id == "kilo":
            return succeeding_provider
        return None  # Return None for unknown providers

    registry_router._provider_registry.get_provider = mock_get_provider

    # Make a request - specify preferred_model to route to our test model
    request = ModelRequest(
        prompt="test prompt",
        required_capabilities=[ModelCapability.TEXT_GENERATION],
        preferred_model="quota-failing-model"
    )

    response = await registry_router.generate(request)

    # Should have succeeded via fallback since QUOTA_EXCEEDED is fallback_eligible
    # but not retryable, so it should go straight to fallback
    print(f"Response content: {response.content}")
    print(f"Failing provider calls: {failing_provider.generate_call_count}")
    print(f"Succeeding provider calls: {succeeding_provider.generate_call_count}")

    # Should have tried the failing provider once
    assert failing_provider.generate_call_count == 1, f"Expected 1 call to failing provider, got {failing_provider.generate_call_count}"

    # Should have tried the succeeding provider (fallback) since QUOTA_EXCEEDED is fallback_eligible
    assert succeeding_provider.generate_call_count == 1, f"Expected 1 call to succeeding provider (fallback), got {succeeding_provider.generate_call_count}"

    # Should have succeeded via fallback
    assert "Success from success-fallback-provider" in response.content, f"Expected fallback success, got: {response.content}"


if __name__ == "__main__":
    pytest.main([__file__])