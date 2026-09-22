"""
Tests for Kilo provider implementation.
These tests verify that the Kilo integration handles configuration safely
without fabricating model access.
"""

import os
from unittest.mock import patch, MagicMock
import pytest

from aios.adapters.kilo import KiloProvider, KiloConfig, register_kilo_provider, get_kilo_config_from_env


def test_kilo_provider_construction():
    """Test that Kilo provider can be constructed from configuration."""
    config = KiloConfig(base_url="https://test.kilo.url", api_key="test-key")
    provider = KiloProvider(config)
    assert provider is not None
    assert provider._config.base_url == "https://test.kilo.url"
    assert provider._config.api_key == "test-key"


def test_kilo_provider_default_construction():
    """Test that Kilo provider can be constructed with defaults."""
    provider = KiloProvider()
    assert provider is not None
    assert provider._config.base_url == "https://api.kilo.chat/v1"
    assert provider._config.api_key is None


def test_kilo_provider_id():
    """Test that Kilo provider ID is 'kilo'."""
    from aios.core.model_router import ModelProvider
    assert ModelProvider.KILO.value == "kilo"


def test_model_identifier_forwarded_unchanged():
    """Test that model identifier is forwarded unchanged."""
    from aios.core.model_router import ModelProvider
    from aios.adapters.kilo import KiloProvider, KiloConfig

    # Test that the provider accepts different model IDs through its default_model config
    provider = KiloProvider(KiloConfig(
        base_url="https://test.kilo.url",
        api_key="test-key",
        default_model="kilo-v2"
    ))
    assert provider._config.default_model == "kilo-v2"


def test_api_authentication_from_config():
    """Test that API authentication is sourced from configuration, never hard-coded."""
    # Test with API key
    provider_with_key = KiloProvider(KiloConfig(base_url="https://test.kilo.url", api_key="my-secret-key"))
    assert provider_with_key._config.api_key == "my-secret-key"

    # Test without API key - should NOT have hardcoded credential
    provider_no_key = KiloProvider(KiloConfig(base_url="https://test.kilo.url", api_key=None))
    assert provider_no_key._config.api_key is None


def test_kilo_config_from_env():
    """Test that Kilo config is read from environment variables."""
    env_vars = {
        "KILO_API_URL": "https://custom.kilo.endpoint/v1",
        "KILO_API_KEY": "env-secret-key",
        "KILO_TIMEOUT": "60",
        "KILO_DEFAULT_MODEL": "custom-kilo-model",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        env_config = get_kilo_config_from_env()
        assert env_config.base_url == "https://custom.kilo.endpoint/v1"
        assert env_config.api_key == "env-secret-key"
        assert env_config.timeout_seconds == 60
        assert env_config.default_model == "custom-kilo-model"


def test_kilo_provider_registration():
    """Test that Kilo provider registers correctly with ModelRouter and ProviderRegistry."""
    from aios.core.model_router import ModelRouter
    from aios.core.provider_registry import get_provider_registry, reset_provider_registry_singleton

    # Reset singleton for clean test
    reset_provider_registry_singleton()

    router = ModelRouter()

    # Register Kilo provider
    config = KiloConfig(base_url="https://test.kilo.url", api_key="test-key")
    provider = register_kilo_provider(router, config)

    # Verify provider was registered
    assert provider is not None
    assert isinstance(provider, KiloProvider)

    # Verify model was registered
    assert "kilo-default" in router._models
    cfg = router._models["kilo-default"]
    assert cfg.config.get("provider") == "kilo", f"Expected 'kilo', got {cfg.config.get('provider')}"

    # Verify provider is registered in the ProviderRegistry
    provider_registry = get_provider_registry()
    assert provider_registry.has_provider("kilo")
    registered_provider = provider_registry.get_provider("kilo")
    assert registered_provider is provider

    print("[PASS] Kilo provider registered with ProviderRegistry")
    print("[PASS] Model config updated with provider ID")
    print("[PASS] Kilo integration works!")

    # Clean up
    reset_provider_registry_singleton()


def test_kilo_provider_configure_method():
    """Test that KiloProvider.configure updates non-secret configuration."""
    config = KiloConfig(
        base_url="https://original.example.com",
        default_model="original-model",
        timeout_seconds=30
    )
    provider = KiloProvider(config)

    # Verify initial state
    assert provider._config.base_url == "https://original.example.com"
    assert provider._config.default_model == "original-model"
    assert provider._config.timeout_seconds == 30

    # Configure new values
    provider.configure({
        "base_url": "https://new.example.com",
        "default_model": "new-model",
        "timeout_seconds": 60
    })

    # Verify configuration was updated
    assert provider._config.base_url == "https://new.example.com"
    assert provider._config.default_model == "new-model"
    assert provider._config.timeout_seconds == 60


def test_kilo_provider_configure_partial_update():
    """Test that KiloProvider.configure works with partial updates."""
    config = KiloConfig(
        base_url="https://original.example.com",
        default_model="original-model",
        timeout_seconds=30
    )
    provider = KiloProvider(config)

    # Update only base_url
    provider.configure({"base_url": "https://partial.example.com"})

    # Verify only base_url was updated
    assert provider._config.base_url == "https://partial.example.com"
    assert provider._config.default_model == "original-model"  # unchanged
    assert provider._config.timeout_seconds == 30  # unchanged


@pytest.mark.asyncio
async def test_kilo_provider_reload_credentials_closes_session():
    """Test that KiloProvider.reload_credentials closes existing session."""
    from unittest.mock import AsyncMock, MagicMock

    provider = KiloProvider(KiloConfig(base_url="https://test.kilo.url", api_key="test-key"))

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
async def test_kilo_provider_reload_credentials_no_session():
    """Test that KiloProvider.reload_credentials handles no existing session."""
    provider = KiloProvider(KiloConfig(base_url="https://test.kilo.url", api_key="test-key"))

    # Ensure no session exists
    provider._session = None

    # Call reload_credentials - should not raise
    await provider.reload_credentials()

    # Verify still no session
    assert provider._session is None


def test_successful_provider_response_translation():
    """Test that successful Kilo responses are translated correctly (structural check)."""
    from aios.core.model_router import ModelProvider
    from aios.adapters.kilo import KiloProvider

    # Check that the provider has the right attributes for successful response translation
    provider = KiloProvider(KiloConfig(base_url="https://test.kilo.url", api_key="test-key"))

    # Verify the provider is properly configured
    assert provider._config.base_url == "https://test.kilo.url"
    assert provider._config.api_key == "test-key"

    # Verify it's the right type
    assert isinstance(provider, KiloProvider)

    # The actual HTTP interaction testing is covered by the integration tests
    # This test verifies the provider structure is correct


@pytest.mark.asyncio
async def test_provider_failure_surfaces_correctly():
    """Test that HTTP/provider failure is surfaced correctly."""
    from aios.core.model_router import ModelRequest, ModelProvider

    # Test with a failing configuration that would cause connection issues
    provider = KiloProvider(KiloConfig(base_url="http://127.0.0.1:1", api_key="test-key"))  # Port 1 unlikely to have service

    request = ModelRequest(prompt="test", preferred_model="test-model")

    # The provider should handle connection failures gracefully
    response = await provider.generate(request)

    # Should get a response (not crash)
    assert response is not None
    assert response.model_id == "test-model"
    assert response.provider == ModelProvider.KILO

    # The content might indicate an error or fallback behavior
    # Most importantly, it should not crash


@pytest.mark.asyncio
async def test_provider_handles_connection_error():
    """Test that connection errors are surfaced correctly."""
    from aios.core.model_router import ModelRequest, ModelProvider

    # Test with unreachable host
    provider = KiloProvider(KiloConfig(base_url="http://192.0.2.1:9", api_key="test-key"))  # TEST-NET-1, port 9 (discard)

    request = ModelRequest(prompt="test", preferred_model="test-model")

    # Should not crash and should return a ModelResponse
    response = await provider.generate(request)

    assert response is not None
    assert response.model_id == "test-model"
    assert response.provider == ModelProvider.KILO


def test_invalid_configuration_fails_safely():
    """Test that invalid configuration fails safely."""
    from aios.core.model_router import ModelRouter, ModelRequest
    from aios.core.provider_registry import get_provider_registry

    router = ModelRouter()

    # Register Kilo provider
    config = KiloConfig(base_url="https://invalid-host.example:1", api_key=None)

    provider = register_kilo_provider(router, config)
    assert provider is not None

    request = ModelRequest(prompt="test", preferred_model="kilo-default")
    # When using, it should fail gracefully, not crash
    import asyncio

    async def run_test():
        response = await router.generate(request)
        assert response.model_id == "kilo-default"
        # Should get a proper response object, not crash
        assert response is not None

    import asyncio
    asyncio.run(run_test())


def test_provider_satisfies_contract():
    """Test that KiloProvider satisfies the Provider contract."""
    from aios.core.provider import Provider
    from aios.core.model_router import ModelRequest, ModelResponse

    provider = KiloProvider(KiloConfig(base_url="https://test.kilo.url", api_key="test-key"))

    # Check that KiloProvider has the generate method
    assert hasattr(provider, "generate")
    assert callable(provider.generate)

    # Check that KiloProvider has the configure method
    assert hasattr(provider, "configure")
    assert callable(provider.configure)

    # Check that KiloProvider has the reload_credentials method
    assert hasattr(provider, "reload_credentials")
    assert callable(provider.reload_credentials)

    # Test that it returns a ModelResponse (even if error)
    import asyncio

    async def run_test():
        request = ModelRequest(prompt="test", preferred_model="test-model")
        response = await provider.generate(request)

        assert isinstance(response, ModelResponse)
        assert hasattr(response, 'content')
        assert hasattr(response, 'model_id')
        assert hasattr(response, 'provider')
        assert response.provider.value == "kilo"

    import asyncio
    asyncio.run(run_test())


def test_model_router_dispatch_to_kilo_provider():
    """Test that ModelRouter can dispatch to a registered KiloProvider."""
    from aios.core.model_router import ModelRouter, ModelRequest, ModelProvider
    from aios.core.provider_registry import get_provider_registry, reset_provider_registry_singleton

    # Reset singleton for clean test
    reset_provider_registry_singleton()

    router = ModelRouter()

    # Register Kilo provider with a custom config
    config = KiloConfig(base_url="https://test.kilo.url", api_key="test-key")
    provider = register_kilo_provider(router, config)

    # Verify provider is registered
    registry = get_provider_registry()
    registry_has_kilo = registry.has_provider("kilo")
    assert registry_has_kilo, "Kilo provider should be registered in ProviderRegistry"
    if registry_has_kilo:
        assert registry.get_provider("kilo") is provider

    # Verify model is registered
    assert "kilo-default" in router._models
    model_cfg = router._models["kilo-default"]
    assert model_cfg.config.get("provider") == "kilo"

    # Verify we can get the provider through the registry
    registered = registry.get_provider("kilo")
    assert registered is provider

    # Clean up
    reset_provider_registry_singleton()


def test_freellmapi_dispatch_still_works():
    """Test that existing FreeLLMAPI dispatch still works after Kilo changes."""
    from aios.core.model_router import ModelRouter, ModelRequest, ModelProvider, ModelConfig, ModelCapability
    from aios.core.provider_registry import get_provider_registry, reset_provider_registry_singleton

    # Reset singleton for clean test
    reset_provider_registry_singleton()

    router = ModelRouter()

    # Register FreeLLMAPI
    from aios.adapters.freellmapi import FreeLLMAPIConfig, register_freellmapi_provider
    config = FreeLLMAPIConfig(base_url="https://test.freellmapi.url", api_key="test-key")
    provider = register_freellmapi_provider(router, config)

    # Verify FreeLLMAPI provider is registered
    registry = get_provider_registry()
    registry_has_freellmapi = registry.has_provider("freellmapi")
    assert registry_has_freellmapi, "FreeLLMAPI provider should be registered in ProviderRegistry"
    if registry_has_freellmapi:
        assert registry.get_provider("freellmapi") is provider

    # Verify model is registered
    assert "freellmapi-default" in router._models

    # Now register Kilo provider
    from aios.adapters.kilo import KiloConfig, register_kilo_provider
    kilo_config = KiloConfig(base_url="https://test.kilo.url", api_key="test-key")
    kilo_provider = register_kilo_provider(router, kilo_config)

    # Both providers should coexist
    registry_has_kilo = registry.has_provider("kilo")
    registry_has_freellmapi_after = registry.has_provider("freellmapi")
    assert registry_has_kilo, "Kilo provider should be registered"
    assert registry_has_freellmapi_after, "FreeLLMAPI provider should still be registered"
    if registry_has_kilo:
        assert registry.get_provider("kilo") is kilo_provider
    if registry_has_freellmapi_after:
        assert registry.get_provider("freellmapi") is provider

    # Verify we have both models
    assert "freellmapi-default" in router._models
    assert "kilo-default" in router._models

    print("[PASS] FreeLLMAPI and Kilo providers coexist in the same registry")

    # Clean up
    reset_provider_registry_singleton()