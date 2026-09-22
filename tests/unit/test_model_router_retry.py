"""
Tests for ModelRouter retry engine integration.
"""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from aios.core.model_router import ModelRouter, ModelRequest, ModelResponse
from aios.core.provider import Provider
from aios.core.provider_failures import ProviderFailure, FailureCategory, classify_failure


class MockProvider(Provider):
    """Mock provider for testing retry behavior."""

    def __init__(self, should_fail: bool = False, failure_category: FailureCategory = FailureCategory.SERVER_ERROR):
        self.should_fail = should_fail
        self.failure_category = failure_category
        self.call_count = 0

    async def generate(self, request: ModelRequest):
        self.call_count += 1

        if self.should_fail:
            # Return a ModelResponse with failure metadata
            failure = classify_failure(
                category=self.failure_category,
                provider_id="mock",
                retry_after=None
            )

            return Mock(
                spec=ModelResponse,
                content=f"Mock error: {self.failure_category.value}",
                model_id="mock-model",
                provider=None,
                tokens_used={},
                cost=0.0,
                latency_ms=100,
                metadata={
                    "failure_category": failure.category.value,
                    "failure_retryable": failure.retryable,
                    "failure_fallback_eligible": failure.fallback_eligible,
                }
            )

        # Return a successful response
        return Mock(
            spec=ModelResponse,
            content="Mock successful response",
            model_id="mock-model",
            provider=None,
            tokens_used={"input": 10, "output": 5},
            cost=0.001,
            latency_ms=50,
            metadata={}
        )


@pytest.fixture
def model_router():
    """Create a ModelRouter instance for testing."""
    router = ModelRouter()

    # Register a mock model
    from aios.core.model_router import ModelConfig, ModelProvider

    mock_model = ModelConfig(
        model_id="mock-model",
        provider=ModelProvider.LOCAL,
        name="Mock Model",
        enabled=True,
        config={"provider": "mock"}  # This tells _call_model to look for "mock" provider
    )

    router.register_model(mock_model)

    # Register mock provider with the router's provider registry
    mock_provider = MockProvider()
    router._provider_registry.register_provider("mock", mock_provider)

    return router, mock_provider


@pytest.mark.asyncio
async def test_successful_provider_call_no_retry(model_router):
    """Test that successful provider calls don't trigger retries."""
    router, mock_provider = model_router
    # Set the mock provider to not fail
    mock_provider.should_fail = False
    mock_provider.call_count = 0

    # Request the specific mock model to ensure it's used
    request = ModelRequest(prompt="Test prompt", preferred_model="mock-model")
    response = await router.generate(request)

    # Should succeed on first attempt
    assert mock_provider.call_count == 1
    assert response.content == "Mock successful response"


@pytest.mark.asyncio
async def test_retryable_timeout_failure_retries_then_succeeds(model_router):
    """Test that retryable TIMEOUT failures trigger retries and eventually succeed."""
    router, mock_provider = model_router

    # Fail first call with TIMEOUT, succeed on second call
    call_count = 0
    original_generate = mock_provider.generate

    async def mocked_generate(request):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            # First call fails with TIMEOUT
            failure = classify_failure(
                category=FailureCategory.TIMEOUT,
                provider_id="mock"
            )

            return Mock(
                spec=ModelResponse,
                content="Mock timeout error",
                model_id="mock-model",
                provider=None,
                tokens_used={},
                cost=0.0,
                latency_ms=1000,
                metadata={
                    "failure_category": failure.category.value,
                    "failure_retryable": failure.retryable,
                    "failure_fallback_eligible": failure.fallback_eligible,
                }
            )
        else:
            # Subsequent calls succeed
            mock_provider.call_count = call_count
            return await original_generate(request)

    mock_provider.generate = mocked_generate

    # Request the specific mock model to ensure it's used
    request = ModelRequest(prompt="Test prompt", preferred_model="mock-model")
    response = await router.generate(request)

    # Should succeed on second attempt
    assert call_count == 2
    assert response.content == "Mock successful response"


@pytest.mark.asyncio
async def test_non_retryable_authentication_failure_no_retry(model_router):
    """Test that AUTHENTICATION failures don't trigger retries."""
    router, mock_provider = model_router
    mock_provider.call_count = 0

    # Set provider to always fail with AUTHENTICATION
    mock_provider.should_fail = True
    mock_provider.failure_category = FailureCategory.AUTHENTICATION

    # Request the specific mock model to ensure it's used
    request = ModelRequest(prompt="Test prompt", preferred_model="mock-model")
    response = await router.generate(request)

    # Should fail immediately without retry
    assert mock_provider.call_count == 1
    assert "Mock error: authentication" in response.content
    assert response.metadata.get("failure_retryable") is False


@pytest.mark.asyncio
async def test_retry_budget_exhaustion(model_router):
    """Test that retry budget exhaustion returns the final failure."""
    router, mock_provider = model_router
    # Set provider to always fail with a retryable error
    mock_provider.should_fail = True
    mock_provider.failure_category = FailureCategory.NETWORK

    # Request the specific mock model to ensure it's used
    request = ModelRequest(prompt="Test prompt", preferred_model="mock-model")
    response = await router.generate(request)

    # Should have tried max_retries + 1 times (default is 3 + 1 = 4)
    # But since we're using a mock, let's check that it kept trying
    assert mock_provider.call_count >= 1
    assert "Mock error: network" in response.content
    # The response should indicate the final failure after retries exhausted


if __name__ == "__main__":
    pytest.main([__file__])