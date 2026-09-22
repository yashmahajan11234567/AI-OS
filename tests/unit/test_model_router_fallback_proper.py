"""
Proper unit test for ModelRouter fallback functionality.
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.model_router import ModelRouter, ModelConfig, ModelRequest, ModelResponse, ModelProvider, ModelCapability
from aios.core.provider import Provider
from aios.core.provider_failures import ProviderFailure, FailureCategory


class MockFailingProvider(Provider):
    """Mock provider that always fails with a specific failure."""

    def __init__(self, failure_category: FailureCategory, fail_content: str = "failure"):
        self.failure_category = failure_category
        self.fail_content = fail_content
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1

        # Determine if this failure should be retryable and fallback eligible
        retryable = self.failure_category in {
            FailureCategory.TIMEOUT,
            FailureCategory.NETWORK,
            FailureCategory.SERVER_ERROR,
            FailureCategory.SERVICE_UNAVAILABLE,
            FailureCategory.RATE_LIMIT
        }

        fallback_eligible = self.failure_category in {
            FailureCategory.TIMEOUT,
            FailureCategory.NETWORK,
            FailureCategory.SERVER_ERROR,
            FailureCategory.SERVICE_UNAVAILABLE,
            FailureCategory.RATE_LIMIT,
            FailureCategory.QUOTA_EXCEEDED,
            FailureCategory.AUTHENTICATION,
            FailureCategory.INVALID_MODEL
        }

        failure = ProviderFailure(
            category=self.failure_category,
            provider_id="mock-failing",
            model_id=request.preferred_model or "test-model",
            retryable=retryable,
            fallback_eligible=fallback_eligible,
            safe_message=f"Mock {self.failure_category.value} failure"
        )

        return ModelResponse(
            content=f"{self.fail_content} from mock-failing",
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

    def __init__(self, success_content: str = "success"):
        self.success_content = success_content
        self.generate_call_count = 0

    async def generate(self, request: ModelRequest) -> ModelResponse:
        self.generate_call_count += 1

        return ModelResponse(
            content=f"{self.success_content} from mock-success",
            model_id=request.preferred_model or "test-model",
            provider=ModelProvider.LOCAL,
            tokens_used={"input": 10, "output": 5},
            cost=0.001
        )


@pytest.fixture
def router_with_mock_providers():
    """Create a ModelRouter with mocked provider calls."""
    router = ModelRouter()

    # Store mock providers for access in tests
    mock_providers = {}

    return router


@pytest.mark.asyncio
async def test_fallback_on_quota_exceeded(router_with_mock_providers):
    """Test that fallback occurs on QUOTA_EXCEEDED failure (non-retryable, fallback-eligible)."""
    print("[TEST] Starting test_fallback_on_quota_exceeded")
    # Create providers
    failing_provider = MockFailingProvider(
        FailureCategory.QUOTA_EXCEEDED,
        "quota-exceeded"
    )
    succeeding_provider = MockSuccessProvider("fallback-success")

    # Register failing model
    failing_model = ModelConfig(
        model_id="failing-model",
        provider=ModelProvider.LOCAL,
        name="Failing Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},
        priority=1  # High priority (low number)
    )
    router_with_mock_providers.register_model(failing_model)

    # Register succeeding model with high priority
    succeeding_model = ModelConfig(
        model_id="succeeding-model",
        provider=ModelProvider.LOCAL,
        name="Succeeding Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},
        priority=1  # High priority (low number)
    )
    router_with_mock_providers.register_model(succeeding_model)

    # Set up backward compatibility - the router will use _freellmapi_provider
    # for models with freellmapi: True in their config
    # We'll need to dynamically switch it based on what's being called
    original_call_model = router_with_mock_providers._call_model

    async def intercepted_call_model(model: ModelConfig, request: ModelRequest):
        # Choose which mock provider to use based on the model ID
        if model.model_id == "failing-model":
            print(f"[TEST] Using failing provider for {model.model_id}")
            result = await failing_provider.generate(request)
            print(f"[TEST] Failing provider call #{failing_provider.generate_call_count}")
            return result
        elif model.model_id == "succeeding-model":
            print(f"[TEST] Using succeeding provider for {model.model_id}")
            result = await succeeding_provider.generate(request)
            print(f"[TEST] Succeeding provider call #{succeeding_provider.generate_call_count}")
            return result
        else:
            print(f"[TEST] Using original _call_model for {model.model_id}")
            return await original_call_model(model, request)

    router_with_mock_providers._call_model = intercepted_call_model

    # Make a request for the failing model
    request = ModelRequest(
        prompt="test prompt",
        preferred_model="failing-model",  # Request the failing model specifically
        required_capabilities=[ModelCapability.TEXT_GENERATION]
    )

    print(f"[TEST] Making request for model: {request.preferred_model}")
    response = await router_with_mock_providers.generate(request)
    print(f"[TEST] Got response: {response.content}")

    # QUOTA_EXCEEDED is fallback_eligible=True, retryable=False
    # So it should NOT retry, but SHOULD fallback to another provider
    print(f"[TEST] Response: {response.content}")
    print(f"[TEST] Failing provider calls: {failing_provider.generate_call_count}")
    print(f"[TEST] Succeeding provider calls: {succeeding_provider.generate_call_count}")

    # Should have tried the failing provider once
    assert failing_provider.generate_call_count == 1, f"Expected 1 call to failing provider, got {failing_provider.generate_call_count}"

    # Should have tried the succeeding provider (fallback)
    assert succeeding_provider.generate_call_count == 1, f"Expected 1 call to succeeding provider (fallback), got {succeeding_provider.generate_call_count}"

    # Should have succeeded via fallback
    assert "fallback-success from mock-success" in response.content, f"Expected fallback success, got: {response.content}"


@pytest.mark.asyncio
async def test_no_fallback_on_invalid_request(router_with_mock_providers):
    """Test that NO fallback occurs on INVALID_REQUEST (non-retryable, NOT fallback-eligible)."""
    print("[TEST] Starting test_no_fallback_on_invalid_request")
    # Create providers
    failing_provider = MockFailingProvider(
        FailureCategory.INVALID_REQUEST,
        "invalid-request"
    )
    succeeding_provider = MockSuccessProvider("fallback-success")

    # Register failing model
    failing_model = ModelConfig(
        model_id="failing-model",
        provider=ModelProvider.LOCAL,
        name="Failing Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True}
    )
    router_with_mock_providers.register_model(failing_model)

    # Register succeeding model with high priority
    succeeding_model = ModelConfig(
        model_id="succeeding-model",
        provider=ModelProvider.LOCAL,
        name="Succeeding Model",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},
        priority=1  # High priority (low number)
    )
    router_with_mock_providers.register_model(succeeding_model)

    # Set up backward compatibility - the router will use _freellmapi_provider
    # for models with freellmapi: True in their config
    # We'll need to dynamically switch it based on what's being called
    original_call_model = router_with_mock_providers._call_model

    async def intercepted_call_model(model: ModelConfig, request: ModelRequest):
        # Choose which mock provider to use based on the model ID
        if model.model_id == "failing-model":
            return await failing_provider.generate(request)
        elif model.model_id == "succeeding-model":
            return await succeeding_provider.generate(request)
        else:
            return await original_call_model(model, request)

    router_with_mock_providers._call_model = intercepted_call_model

    # Make a request for the failing model
    request = ModelRequest(
        prompt="test prompt",
        preferred_model="failing-model",  # Request the failing model specifically
        required_capabilities=[ModelCapability.TEXT_GENERATION]
    )

    response = await router_with_mock_providers.generate(request)

    # INVALID_REQUEST is fallback_eligible=False, retryable=False
    # So it should NOT retry and should NOT fallback
    print(f"Response: {response.content}")
    print(f"Failing provider calls: {failing_provider.generate_call_count}")
    print(f"Succeeding provider calls: {succeeding_provider.generate_call_count}")

    # Should have tried the failing provider exactly once
    assert failing_provider.generate_call_count == 1

    # Should NOT have tried the succeeding provider (no fallback)
    assert succeeding_provider.generate_call_count == 0

    # Should have failed with the original error
    assert "invalid-request from mock-failing" in response.content


if __name__ == "__main__":
    pytest.main([__file__])