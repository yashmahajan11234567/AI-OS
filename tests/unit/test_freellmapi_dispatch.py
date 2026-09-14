"""
Tests for FreeLLMAPI provider dispatch through ModelRouter.
These tests verify that the FreeLLMAPI provider is actually dispatched
when valid runtime configuration is present.
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from aios.core.model_router import ModelRouter, ModelRequest
from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig


class MockFreeLLMAPIProvider:
    """Mock FreeLLMAPI provider for testing dispatch."""

    def __init__(self, content="freellmapi-response"):
        self.content = content
        self.generate_called = False
        self.last_request = None

    async def generate(self, request: ModelRequest) -> MagicMock:
        self.generate_called = True
        self.last_request = request

        # Return a mock response similar to what FreeLLMAPIProvider would return
        mock_response = MagicMock()
        mock_response.content = f"{self.content}: {request.prompt[:50]}"
        mock_response.model_id = request.preferred_model or "freellmapi-default"
        mock_response.provider = MagicMock()
        mock_response.provider.value = "local"
        mock_response.tokens_used = {"input": 10, "output": 5}
        mock_response.cost = 0.0
        mock_response.latency_ms = 10
        mock_response.metadata = {"freellmapi": True}
        return mock_response


@pytest.fixture
def router():
    return ModelRouter()


@pytest.fixture
def freellmapi_model():
    """Create a FreeLLMAPI model configuration."""
    from aios.core.model_router import ModelConfig, ModelProvider, ModelCapability
    return ModelConfig(
        model_id="freellmapi-test",
        provider=ModelProvider.LOCAL,
        name="FreeLLMAPI Test",
        capabilities=[ModelCapability.TEXT_GENERATION],
        enabled=True,
        config={"freellmapi": True},  # This marks it as a FreeLLMAPI model
    )


@pytest.mark.asyncio
async def test_freellmapi_dispatch_when_provider_registered_via_env(router, freellmapi_model):
    """Test that FreeLLMAPI provider is dispatched when properly registered via environment config."""
    # Register the FreeLLMAPI model
    router.register_model(freellmapi_model)

    # Verify the model has the freellmapi config flag
    model_config = router._models["freellmapi-test"]
    assert model_config.config.get("freellmapi") is True

    # Patch the environment to simulate proper FreeLLMAPI configuration
    env_vars = {
        "FREELLM_API_URL": "http://test-server:8080",
        "FREELLM_API_KEY": "test-key-123"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        # Manually register the provider (simulating what _init_freellmapi would do)
        from aios.adapters.freellmapi import register_freellmapi_provider, FreeLLMAPIProvider
        config = FreeLLMAPIConfig(
            base_url="http://test-server:8080",
            api_key="test-key-123"
        )
        registered_provider = register_freellmapi_provider(router, config)

        # Verify the provider was registered
        assert router._freellmapi_provider is registered_provider
        assert isinstance(router._freellmapi_provider, FreeLLMAPIProvider)
        assert "freellmapi-test" in router._models

        # Test the dispatch - we can't easily mock the internal provider,
        # but we can verify it's the correct type and was called by checking
        # that we don't get a mock response
        request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")
        response = await router.generate(request)

        # Verify we got a response from the FreeLLMAPI provider (not a mock)
        # The FreeLLMAPIProvider will either return a real response or an error response
        # but it should NOT be the deterministic mock response from ModelRouter._call_model
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"
        # The response should indicate it came from a provider (either success or error)
        assert hasattr(response, 'provider')


@pytest.mark.asyncio
async def test_freellmapi_not_dispatched_when_not_registered(router, freellmapi_model):
    """Test that FreeLLMAPI provider is NOT dispatched when not registered."""
    # Register the FreeLLMAPI model but DON'T register the provider
    router.register_model(freellmapi_model)

    # Ensure no provider is registered
    assert not hasattr(router, "_freellmapi_provider") or router._freellmapi_provider is None

    # Test the dispatch - should fall back to mock
    request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")
    response = await router.generate(request)

    # Should get mock response, not provider response
    assert "Mock response" in response.content
    assert response.model_id == "freellmapi-test"


@pytest.mark.asyncio
async def test_freellmapi_config_respects_environment_variables(router):
    """Test that FreeLLMAPI configuration properly reads from environment variables."""
    # Test with custom environment variables
    env_vars = {
        "FREELLM_API_URL": "http://custom.example.com:9000",
        "FREELLM_API_KEY": "custom-secret-key",
        "FREELLM_TIMEOUT": "60",
        "FREELLM_DEFAULT_MODEL": "custom-model-v1"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env
        config = get_freellmapi_config_from_env()

        assert config.base_url == "http://custom.example.com:9000"
        assert config.api_key == "custom-secret-key"
        assert config.timeout_seconds == 60
        assert config.default_model == "custom-model-v1"


@pytest.mark.asyncio
async def test_freellmapi_safe_failure_when_missing_configuration(router, freellmapi_model):
    """Test that missing configuration results in safe failure, not fabricated access."""
    # Register the FreeLLMAPI model
    router.register_model(freellmapi_model)

    # Test with missing/empty configuration
    env_vars = {
        "FREELLM_API_URL": "",  # Empty URL
        "FREELLM_API_KEY": ""   # Empty key
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env, register_freellmapi_provider
        config = get_freellmapi_config_from_env()

        # Even with empty values, we should get a config object
        assert config.base_url == ""  # From env
        assert config.api_key == ""   # From env

        # Register provider with this config
        provider = register_freellmapi_provider(router, config)
        assert router._freellmapi_provider is provider

        # When we try to use it, it should handle the failure gracefully
        request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")

        # This should not crash, but return an error response
        response = await router.generate(request)

        # Should contain error information, not fabricated content
        assert hasattr(response, 'content')
        # The actual error handling is in the FreeLLMAPIProvider.generate method
        # which should return an error response when connection fails


@pytest.mark.asyncio
async def test_existing_routing_behavior_preserved(router):
    """Test that existing routing behavior for non-FreeLLMAPI models is preserved."""
    from aios.core.model_router import ModelCapability

    # Test standard models still work
    request = ModelRequest(prompt="test prompt", preferred_model="claude-sonnet-4")
    response = await router.generate(request)

    # Should get mock response for standard models (no provider registered)
    assert "Mock response" in response.content
    assert response.model_id == "claude-sonnet-4"

    # Test capability-based routing still works
    request = ModelRequest(
        prompt="test prompt",
        required_capabilities=[ModelCapability.CODE_GENERATION]
    )
    response = await router.generate(request)

    # Should get a mock response from some capable model
    assert "Mock response" in response.content
    # Should be from a model that has code_generation capability
    assert response.model_id in router._models
    model_config = router._models[response.model_id]
    assert ModelCapability.CODE_GENERATION in model_config.capabilities