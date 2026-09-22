"""
End-to-end tests for provider credential rotation flow.

Tests the complete flow from ConfigurationManager.rotate_secret()
through to Provider.reload_credentials() being called on live providers.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aios.core.configuration_manager import ConfigurationManager
from aios.core.provider_registry import get_provider_registry, reset_provider_registry_singleton
from aios.core.security_manager import SecurityDecision, SecurityManager, get_security_manager
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.types import EventType
from aios.core.structured_logger import get_logger
from aios.core.service_registry import get_service_registry, reset_service_registry_singleton
from aios.core.configuration_manager import reset_configuration_manager_singleton


@pytest.mark.asyncio
async def test_nim_provider_credential_rotation_flow():
    """Test end-to-end credential rotation flow for NIM provider."""
    # Setup singletons
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_provider_registry_singleton()

    try:
        # Initialize core components
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        await bus.initialize()

        sr = get_service_registry(event_bus=bus)
        cm = ConfigurationManager(event_bus=bus)
        logger = get_logger()

        # Initialize SecurityManager
        sm = SecurityManager(
            service_registry=sr,
            configuration_manager=cm,
            logger=logger,
        )
        await sm.initialize()

        # Initialize ConfigurationManager
        await cm.initialize()

        # Freeze the configuration (required for secret rotation)
        cm.freeze()

        # Create and register a NIM provider
        from aios.adapters.nim import NimProvider, NimConfig
        from aios.core.model_router import ModelRouter

        router = ModelRouter()
        nim_config = NimConfig(
            base_url="https://test.nim.url",
            api_key="original-key",
            timeout_seconds=30
        )
        nim_provider = NimProvider(nim_config)

        # Register with provider registry
        provider_registry = get_provider_registry()
        provider_registry.register_provider("nim", nim_provider)

        # Verify initial state
        assert nim_provider._config.api_key == "original-key"
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        nim_provider._session = mock_session

        # Rotate the secret via ConfigurationManager
        # This should trigger the provider credential reload
        principal = "test_principal"
        new_api_key = "rotated-key"

        # Register the provider credential rotation rules for the test principal
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        result = cm.rotate_secret(
            path="llm.providers.nim.apiKey",
            new_value=new_api_key,
            principal=principal,
            security_manager=sm
        )

        # Verify rotation succeeded
        assert result is True

        # Verify the secret was rotated in the configuration overlay
        assert cm.get_secret("llm.providers.nim.apiKey") == new_api_key

        # Give time for async notification to process
        await asyncio.sleep(0.1)

        # Verify that the provider's session was closed (to prevent use of old credentials)
        mock_session.close.assert_awaited_once()

        # Verify that the provider configuration would use the new key
        # (The actual session recreation happens lazily in _ensure_session)
        # We can verify this by checking that the session was cleared
        assert nim_provider._session is None  # Session was cleared in reload_credentials

    finally:
        # Cleanup
        await cm.shutdown()
        await sr.shutdown()
        await bus.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_provider_registry_singleton()


@pytest.mark.asyncio
async def test_freellmapi_provider_credential_rotation_flow():
    """Test end-to-end credential rotation flow for FreeLLMAPI provider."""
    # Setup singletons
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_provider_registry_singleton()

    try:
        # Initialize core components
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        await bus.initialize()

        sr = get_service_registry(event_bus=bus)
        cm = ConfigurationManager(event_bus=bus)
        logger = get_logger()

        # Initialize SecurityManager
        sm = SecurityManager(
            service_registry=sr,
            configuration_manager=cm,
            logger=logger,
        )
        await sm.initialize()

        # Initialize ConfigurationManager
        await cm.initialize()

        # Freeze the configuration (required for secret rotation)
        cm.freeze()

        # Create and register a FreeLLMAPI provider
        from aios.adapters.freellmapi import FreeLLMAPIProvider, FreeLLMAPIConfig
        from aios.core.model_router import ModelRouter

        router = ModelRouter()
        freellmapi_config = FreeLLMAPIConfig(
            base_url="http://test.freellmapi.url",
            api_key="original-key",
            timeout_seconds=30
        )
        freellmapi_provider = FreeLLMAPIProvider(freellmapi_config)

        # Register with provider registry
        provider_registry = get_provider_registry()
        provider_registry.register_provider("freellmapi", freellmapi_provider)

        # Verify initial state
        assert freellmapi_provider._config.api_key == "original-key"
        mock_session = MagicMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        freellmapi_provider._session = mock_session

        # Rotate the secret via ConfigurationManager
        # This should trigger the provider credential reload
        principal = "test_principal"
        new_api_key = "rotated-key"

        # Register the provider credential rotation rules for the test principal
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        result = cm.rotate_secret(
            path="llm.providers.freellmapi.apiKey",
            new_value=new_api_key,
            principal=principal,
            security_manager=sm
        )

        # Verify rotation succeeded
        assert result is True

        # Verify the secret was rotated in the configuration overlay
        assert cm.get_secret("llm.providers.freellmapi.apiKey") == new_api_key

        # Give time for async notification to process
        await asyncio.sleep(0.1)

        # Verify that the provider's session was closed (to prevent use of old credentials)
        mock_session.close.assert_awaited_once()

        # Verify that the provider configuration would use the new key
        # (The actual session recreation happens lazily in _ensure_session)
        # We can verify this by checking that the session was cleared
        assert freellmapi_provider._session is None  # Session was cleared in reload_credentials

    finally:
        # Cleanup
        await cm.shutdown()
        await sr.shutdown()
        await bus.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_provider_registry_singleton()


@pytest.mark.asyncio
async def test_unknown_provider_credential_rotation_safe():
    """Test that rotating credentials for unknown providers fails safely."""
    # Setup singletons
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_provider_registry_singleton()

    try:
        # Initialize core components
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        await bus.initialize()

        sr = get_service_registry(event_bus=bus)
        cm = ConfigurationManager(event_bus=bus)
        logger = get_logger()

        # Initialize SecurityManager
        sm = SecurityManager(
            service_registry=sr,
            configuration_manager=cm,
            logger=logger,
        )
        await sm.initialize()

        # Initialize ConfigurationManager
        await cm.initialize()

        # Freeze the configuration (required for secret rotation)
        cm.freeze()

        # Try to rotate a secret for an unknown provider
        principal = "test_principal"
        new_api_key = "rotated-key"

        # Register the provider credential rotation rules for the test principal (including unknown provider to test auth)
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")
        sm.register_allow_rule(principal=principal, action="secret.rotate", resource="config:llm.providers.unknown-provider.apiKey")

        
        # This should not crash even though no provider exists
        result = cm.rotate_secret(
            path="llm.providers.unknown-provider.apiKey",
            new_value=new_api_key,
            principal=principal,
            security_manager=sm
        )

        # Verify rotation succeeded (the rotation itself should work)
        assert result is True

        # Verify the secret was rotated in the configuration overlay
        assert cm.get_secret("llm.providers.unknown-provider.apiKey") == new_api_key

        # No provider notification should have happened (no crash)
        # This is tested by the fact that we didn't get an exception

    finally:
        # Cleanup
        await cm.shutdown()
        await sr.shutdown()
        await bus.shutdown()
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()
        reset_provider_registry_singleton()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])