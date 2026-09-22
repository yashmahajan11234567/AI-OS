"""
Tests for FreeLLMAPI failsafe behavior.
These tests verify that the FreeLLMAPI integration handles missing or
invalid configuration safely without fabricating model access.
"""

import os
from unittest.mock import patch
import pytest

from aios.core.model_router import ModelRouter, ModelRequest
from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig


class FailingFreeLLMAPIProvider:
    """FreeLLMAPI provider that simulates connection failures."""

    def __init__(self, failure_type="connection_error"):
        self.failure_type = failure_type
        self.generate_called = False

    async def generate(self, request):
        self.generate_called = True
        if self.failure_type == "connection_error":
            raise ConnectionError("Failed to connect to FreeLLMAPI server")
        elif self.failure_type == "timeout":
            raise TimeoutError("Request to FreeLLMAPI timed out")
        elif self.failure_type == "http_error":
            # Simulate HTTP error response
            raise RuntimeError("FreeLLMAPI error 500: Internal Server Error")
        else:
            raise ValueError(f"Unknown failure type: {self.failure_type}")


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
        config={"freellmapi": True},
    )


@pytest.mark.asyncio
async def test_freellmapi_safe_failure_when_base_url_missing(router, freellmapi_model):
    """Test that missing base_url results in safe failure."""
    # Register the FreeLLMAPI model
    router.register_model(freellmapi_model)

    # Test with missing base_url
    env_vars = {
        "FREELLM_API_URL": "",  # Empty URL
        "FREELLM_API_KEY": "test-key"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env, register_freellmapi_provider
        config = get_freellmapi_config_from_env()

        # Should get config with empty base_url
        assert config.base_url == ""
        assert config.api_key == "test-key"

        # Register provider - this should still succeed (registration doesn't validate connectivity)
        provider = register_freellmapi_provider(router, config)
        assert router._freellmapi_provider is provider

        # When we try to use it, it should handle the failure gracefully
        request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")
        response = await router.generate(request)

        # Should get an error response from the provider, not a mock response
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"
        # The FreeLLMAPIProvider should have attempted the call and returned an error
        # We can't easily check the internal state of the real provider, but we know it was called
        # because we didn't get a mock response


@pytest.mark.asyncio
async def test_freellmapi_safe_failure_when_base_url_is_default_localhost(router, freellmapi_model):
    """Test that default localhost base_url results in safe failure (no registration in kernel)."""
    # Register the FreeLLMAPI model
    router.register_model(freellmapi_model)

    # Test with default localhost URL (would skip registration in kernel)
    env_vars = {
        "FREELLM_API_URL": "http://localhost:8080",  # Default value
        "FREELLM_API_KEY": "test-key"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env
        config = get_freellmapi_config_from_env()

        # Should get the default config
        assert config.base_url == "http://localhost:8080"
        assert config.api_key == "test-key"

        # The _init_freellmapi method would skip registration in this case
        # Let's verify by checking what happens if we try to register anyway
        from aios.adapters.freellmapi import register_freellmapi_provider
        provider = register_freellmapi_provider(router, config)
        assert router._freellmapi_provider is provider  # Registration still works

        # But when we try to use it, it should attempt to connect to localhost:8080
        # and fail gracefully (since nothing is likely running there)
        request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")
        response = await router.generate(request)

        # Should get an error response, not a mock response
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"


@pytest.mark.asyncio
async def test_freellmapi_handles_connection_errors_gracefully(router, freellmapi_model):
    """Test that connection errors are handled safely."""
    # Register the FreeLLMAPI model
    router.register_model(freellmapi_model)

    # Patch the environment
    env_vars = {
        "FREELLM_API_URL": "http://nonexistent:9999",
        "FREELLM_API_KEY": "test-key"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env, register_freellmapi_provider
        config = get_freellmapi_config_from_env()
        provider = register_freellmapi_provider(router, config)
        assert router._freellmapi_provider is provider

        # Test the dispatch - we expect it to fail gracefully
        request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")
        response = await router.generate(request)

        # Should get an error response, not a mock response or crash
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"
        # The response should contain error information from the failed connection
        assert response.metadata.get("error") is not None
        error_str = str(response.metadata.get("error", ""))
        assert ("Failed to connect" in error_str or
                "ConnectionError" in error_str or
                "getaddrinfo failed" in error_str or
                "Nonexistent" in error_str)


@pytest.mark.asyncio
async def test_freellmapi_handles_http_errors_gracefully(router, freellmapi_model):
    """Test that HTTP errors are handled safely."""
    # Register the FreeLLMAPI model
    router.register_model(freellmapi_model)

    # Patch the environment
    env_vars = {
        "FREELLM_API_URL": "http://httpbin.org/status/500",
        "FREELLM_API_KEY": "test-key"
    }

    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env, register_freellmapi_provider
        config = get_freellmapi_config_from_env()
        provider = register_freellmapi_provider(router, config)
        assert router._freellmapi_provider is provider

        # Test the dispatch - we expect it to fail gracefully
        request = ModelRequest(prompt="test prompt", preferred_model="freellmapi-test")
        response = await router.generate(request)

        # Should get an error response, not a mock response or crash
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"
        # The response should contain error information from the failed HTTP request
        assert response.metadata.get("error") is not None
        error_str = str(response.metadata.get("error", ""))
        assert ("500" in error_str or
                "FreeLLMAPI error" in error_str or
                "RuntimeError" in error_str or
                "404" in error_str)  # httpbin might return 404 for /status/500 if it doesn't exist


@pytest.mark.asyncio
async def test_freellmapi_does_not_fabricate_responses_on_configuration_errors(router, freellmapi_model):
    """Test that configuration errors don't lead to fabricated model responses."""
    # Test scenario 1: Missing base_url
    env_vars = {"FREELLM_API_URL": "", "FREELLM_API_KEY": "test-key"}
    with patch.dict(os.environ, env_vars, clear=False):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env, register_freellmapi_provider
        config = get_freellmapi_config_from_env()
        router.register_model(freellmapi_model)
        provider = register_freellmapi_provider(router, config)
        request = ModelRequest(prompt="test prompt scenario 1", preferred_model="freellmapi-test")
        response = await router.generate(request)
        # Should NOT get the deterministic mock response from ModelRouter
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"
        assert len(response.content) > 0
        # Cleanup
        if hasattr(router, '_freellmapi_provider'):
            delattr(router, '_freellmapi_provider')
        if "freellmapi-test" in router._models:
            del router._models["freellmapi-test"]
        # Unregister provider from the router's registry to ensure test isolation
        provider_registry = getattr(router, "_provider_registry", None)
        if provider_registry is not None:
            provider_registry.unregister_provider("freellmapi")

    # Test scenario 2: No env vars (get defaults)
    env_vars = {}
    with patch.dict(os.environ, env_vars, clear=True):
        from aios.adapters.freellmapi import get_freellmapi_config_from_env, register_freellmapi_provider
        config = get_freellmapi_config_from_env()
        router.register_model(freellmapi_model)
        provider = register_freellmapi_provider(router, config)
        request = ModelRequest(prompt="test prompt scenario 2", preferred_model="freellmapi-test")
        response = await router.generate(request)
        # Should NOT get the deterministic mock response from ModelRouter
        assert "[Mock response from" not in response.content
        assert response.model_id == "freellmapi-test"
        assert len(response.content) > 0
        # Cleanup
        if hasattr(router, '_freellmapi_provider'):
            delattr(router, '_freellmapi_provider')
        if "freellmapi-test" in router._models:
            del router._models["freellmapi-test"]
        # Unregister provider from the router's registry to ensure test isolation
        provider_registry = getattr(router, "_provider_registry", None)
        if provider_registry is not None:
            provider_registry.unregister_provider("freellmapi")


def test_freellmapi_provider_configure_method():
    """Test that FreeLLMAPIProvider.configure updates non-secret configuration."""
    config = FreeLLMAPIConfig(
        base_url="http://original.example.com",
        default_model="original-model",
        timeout_seconds=30
    )
    provider = FreeLLMAPIProvider(config)

    # Verify initial state
    assert provider._config.base_url == "http://original.example.com"
    assert provider._config.default_model == "original-model"
    assert provider._config.timeout_seconds == 30

    # Configure new values
    provider.configure({
        "base_url": "http://new.example.com",
        "default_model": "new-model",
        "timeout_seconds": 60
    })

    # Verify configuration was updated
    assert provider._config.base_url == "http://new.example.com"
    assert provider._config.default_model == "new-model"
    assert provider._config.timeout_seconds == 60


def test_freellmapi_provider_configure_partial_update():
    """Test that FreeLLMAPIProvider.configure works with partial updates."""
    config = FreeLLMAPIConfig(
        base_url="http://original.example.com",
        default_model="original-model",
        timeout_seconds=30
    )
    provider = FreeLLMAPIProvider(config)

    # Update only base_url
    provider.configure({"base_url": "http://partial.example.com"})

    # Verify only base_url was updated
    assert provider._config.base_url == "http://partial.example.com"
    assert provider._config.default_model == "original-model"  # unchanged
    assert provider._config.timeout_seconds == 30  # unchanged


@pytest.mark.asyncio
async def test_freellmapi_provider_reload_credentials_closes_session():
    """Test that FreeLLMAPIProvider.reload_credentials closes existing session."""
    from unittest.mock import AsyncMock, MagicMock

    provider = FreeLLMAPIProvider(FreeLLMAPIConfig(base_url="http://test.example.com", api_key="test-key"))

    # Mock a session with async close method
    mock_session = MagicMock()
    mock_session.closed = False
    mock_session.close = AsyncMock()
    provider._session = mock_session

    # Call reload_credentials
    await provider.reload_credentials()

    # Verify session was closed
    mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_freellmapi_provider_reload_credentials_no_session():
    """Test that FreeLLMAPIProvider.reload_credentials handles no existing session."""
    provider = FreeLLMAPIProvider(FreeLLMAPIConfig(base_url="http://test.example.com", api_key="test-key"))

    # Ensure no session exists
    provider._session = None

    # Call reload_credentials - should not raise
    await provider.reload_credentials()

    # Verify still no session
    assert provider._session is None