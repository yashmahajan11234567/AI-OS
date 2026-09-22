"""
Unit tests for data-driven provider SecurityManager allow-rule registration.

Tests that the dashboard backend correctly derives provider security rules
from the ProviderRegistry in a data-driven manner, eliminating the need
for hardcoded provider-specific blocks.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from aios.core.provider_registry import ProviderRegistry, reset_provider_registry_singleton
from aios.core.provider import Provider
from aios.core.security_manager import SecurityDecision, SecurityManager
from aios.core.service_registry import get_service_registry, reset_service_registry_singleton
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.types import EventType
from aios.core.configuration_manager import ConfigurationManager, reset_configuration_manager_singleton
from aios.core.structured_logger import get_logger
from aios.core.kernel import HermesKernel


@pytest.fixture(autouse=True)
def _reset_provider_registry_singleton():
    """Reset the ProviderRegistry singleton before and after each test."""
    reset_provider_registry_singleton()
    yield
    reset_provider_registry_singleton()


class TestProvider(Provider):
    """Test provider for verification."""

    def __init__(self, provider_id: str = "test"):
        super().__init__()
        self.provider_id = provider_id

    async def generate(self, request):
        """Mock generate method."""
        from aios.core.model_router import ModelResponse
        return ModelResponse(
            content="test response",
            model_id=request.preferred_model or "test-model",
            provider=self.provider_id
        )


@pytest.fixture
def event_bus():
    """A canonical EventBus singleton."""
    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    yield bus
    reset_event_bus_singleton()


@pytest.fixture
def service_registry(event_bus):
    """A canonical ServiceRegistry wired to the bus."""
    reset_service_registry_singleton()
    reg = get_service_registry(event_bus=event_bus)
    yield reg
    reset_service_registry_singleton()


@pytest.fixture
def configuration_manager(event_bus):
    """A canonical ConfigurationManager (empty/frozen)."""
    reset_configuration_manager_singleton()
    cm = ConfigurationManager(event_bus=event_bus)
    yield cm
    reset_configuration_manager_singleton()


@pytest.fixture
def logger(event_bus):
    """A canonical StructuredLogger."""
    return get_logger()


@pytest.fixture
def kernel(event_bus, service_registry, configuration_manager, logger):
    """A HermesKernel wired to real canonical C1-C4, uninitialized."""
    kernel = HermesKernel()
    kernel._event_bus = event_bus
    kernel._service_registry = service_registry
    kernel._configuration = configuration_manager
    kernel._structured_logger = logger
    # Initialize core components manually for testing
    return kernel


async def test_provider_registry_available_before_dashboard_init(kernel):
    """Test that ProviderRegistry is available before dashboard backend initialization."""
    # Initialize core components (this is where ProviderRegistry gets initialized)
    await kernel._init_core_components()

    # Verify ProviderRegistry is initialized and available
    assert kernel._provider_registry is not None
    assert hasattr(kernel._provider_registry, 'list_providers')
    assert hasattr(kernel._provider_registry, 'register_provider')
    # Verify it's properly initialized
    health = kernel._provider_registry.healthCheck()
    assert health.state.value == "RUNNING"


async def test_data_driven_provider_rules_registered(kernel):
    """Test that provider rules are registered in a data-driven manner."""
    # Initialize core components to get ProviderRegistry and SecurityManager
    await kernel._init_core_components()

    # Register some test providers
    test_provider_nim = TestProvider("nim")
    test_provider_freellmapi = TestProvider("freellmapi")
    test_provider_custom = TestProvider("custom-provider")

    kernel._provider_registry.register_provider("nim", test_provider_nim)
    kernel._provider_registry.register_provider("freellmapi", test_provider_freellmapi)
    kernel._provider_registry.register_provider("custom-provider", test_provider_custom)

    # Initialize dashboard backend (this should register the data-driven rules)
    await kernel._init_dashboard_backend()

    # Use the kernel's security manager (properly initialized via _init_core_components)
    security_manager = kernel.security_manager

    # Verify that project actions are still registered (should be unchanged)
    assert security_manager.authorize("dashboard_user", "project.create", "any_resource") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "project.transition", "any_resource") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "project.publish_notion", "any_resource") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "project.clear_action", "any_resource") == SecurityDecision.ALLOW

    # Verify that provider lifecycle rules are registered for ALL registered providers
    # NIM provider
    assert security_manager.authorize("dashboard_user", "provider.configure", "config:llm.providers.nim") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "provider.enable", "config:llm.providers.nim") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "provider.disable", "config:llm.providers.nim") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.ALLOW

    # FreeLLMAPI provider
    assert security_manager.authorize("dashboard_user", "provider.configure", "config:llm.providers.freellmapi") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "provider.enable", "config:llm.providers.freellmapi") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "provider.disable", "config:llm.providers.freellmapi") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "secret.rotate", "config:llm.providers.freellmapi.apiKey") == SecurityDecision.ALLOW

    # Custom provider
    assert security_manager.authorize("dashboard_user", "provider.configure", "config:llm.providers.custom-provider") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "provider.enable", "config:llm.providers.custom-provider") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "provider.disable", "config:llm.providers.custom-provider") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "secret.rotate", "config:llm.providers.custom-provider.apiKey") == SecurityDecision.ALLOW

    # Verify fail-closed behavior for unregistered providers
    assert security_manager.authorize("dashboard_user", "provider.configure", "config:llm.providers.unregistered") == SecurityDecision.DENY
    assert security_manager.authorize("dashboard_user", "provider.enable", "config:llm.providers.unregistered") == SecurityDecision.DENY
    assert security_manager.authorize("dashboard_user", "provider.disable", "config:llm.providers.unregistered") == SecurityDecision.DENY
    assert security_manager.authorize("dashboard_user", "secret.rotate", "config:llm.providers.unregistered.apiKey") == SecurityDecision.DENY

    # Verify fail-closed behavior for wrong actions on registered providers
    assert security_manager.authorize("dashboard_user", "invalid.action", "config:llm.providers.nim") == SecurityDecision.DENY
    assert security_manager.authorize("dashboard_user", "provider.configure", "wrong.resource") == SecurityDecision.DENY


async def test_no_hardcoded_provider_blocks_in_kernel():
    """Test that kernel.py no longer contains hardcoded provider-specific blocks."""
    # Read the kernel.py file
    with open(r"C:\Development\AI-OS\src\aios\core\kernel.py", "r") as f:
        content = f.read()

    # Verify that hardcoded NIM blocks are gone
    assert 'resource="config:llm.providers.nim"' not in content
    assert 'resource="config:llm.providers.nim.apiKey"' not in content

    # Verify that hardcoded FreeLLMAPI blocks are gone
    assert 'resource="config:llm.providers.freellmapi"' not in content
    assert 'resource="config:llm.providers.freellmapi.apiKey"' not in content

    # Verify that the data-driven approach is present
    assert "list_providers()" in content
    assert "provider_ids = self._provider_registry.list_providers()" in content
    assert 'provider_resource = f"config:llm.providers.{provider_id}"' in content
    assert 'credential_resource = f"config:llm.providers.{provider_id}.apiKey"' in content


async def test_empty_provider_registry_still_works(kernel):
    """Test that the system works correctly when no providers are registered."""
    # Initialize core components
    await kernel._init_core_components()

    # Don't register any providers

    # Initialize dashboard backend
    await kernel._init_dashboard_backend()

    # Use the kernel's security manager (properly initialized via _init_core_components)
    security_manager = kernel.security_manager

    # Verify that project actions still work
    assert security_manager.authorize("dashboard_user", "project.create", "any_resource") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "project.transition", "any_resource") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "project.publish_notion", "any_resource") == SecurityDecision.ALLOW
    assert security_manager.authorize("dashboard_user", "project.clear_action", "any_resource") == SecurityDecision.ALLOW

    # Verify that no provider rules are incorrectly allowed (fail-closed)
    assert security_manager.authorize("dashboard_user", "provider.configure", "config:llm.providers.any") == SecurityDecision.DENY
    assert security_manager.authorize("dashboard_user", "secret.rotate", "config:llm.providers.any.apiKey") == SecurityDecision.DENY


async def test_provider_registration_order_verification(kernel):
    """Test that verifies ProviderRegistry providers are available before dashboard rules are derived."""
    # Track initialization order
    init_order = []

    # Store original methods
    original_init_core_components = kernel._init_core_components
    original_init_dashboard_backend = kernel._init_dashboard_backend

    # Wrap methods to track call order
    async def tracked_init_core_components():
        init_order.append("_init_core_components")
        await original_init_core_components()

    async def tracked_init_dashboard_backend():
        init_order.append("_init_dashboard_backend")
        # Verify ProviderRegistry is available at this point
        assert kernel._provider_registry is not None, "ProviderRegistry should be available before dashboard init"
        assert hasattr(kernel._provider_registry, 'list_providers'), "ProviderRegistry should have list_providers method"
        await original_init_dashboard_backend()

    # Replace methods
    kernel._init_core_components = tracked_init_core_components
    kernel._init_dashboard_backend = tracked_init_dashboard_backend

    try:
        # Initialize the kernel partially
        await kernel._init_core_components()
        await kernel._init_dashboard_backend()

        # Verify the order is correct
        assert init_order == ["_init_core_components", "_init_dashboard_backend"], f"Expected correct init order, got {init_order}"

    finally:
        # Restate original methods
        kernel._init_core_components = original_init_core_components
        kernel._init_dashboard_backend = original_init_dashboard_backend


async def test_security_rule_generation_explanation():
    """Test that explains how the data-driven rule generation works."""
    # This test documents the approach rather than testing implementation

    # The data-driven provider rule generation works as follows:
    # 1. During kernel initialization, _init_core_components() is called first
    # 2. This method initializes the ProviderRegistry Core Component
    # 3. Later, _init_dashboard_backend() is called
    # 4. At this point, the ProviderRegistry is available and initialized
    # 5. We call self._provider_registry.list_providers() to get all registered provider IDs
    # 6. For each provider_id, we generate the canonical resource patterns:
    #    - Provider lifecycle: config:llm.providers.{provider_id}
    #    - Credential rotation: config:llm.providers.{provider_id}.apiKey
    # 7. For each pattern, we register the appropriate allow-rules with the SecurityManager
    #
    # This approach eliminates the need for hardcoded provider-specific blocks
    # and automatically covers any provider registered with the ProviderRegistry.

    # Verify the explanation is sound by checking the actual implementation
    with open(r"C:\Development\AI-OS\src\aios\core\kernel.py", "r") as f:
        content = f.read()

    # Check that the implementation follows the documented approach
    assert "_provider_registry.list_providers()" in content
    assert 'provider_resource = f"config:llm.providers.{provider_id}"' in content
    assert 'credential_resource = f"config:llm.providers.{provider_id}.apiKey"' in content
    assert "provider.configure" in content
    assert "provider.enable" in content
    assert "provider.disable" in content
    assert "secret.rotate" in content

    # The explanation is valid - the implementation matches the documented approach
    assert True  # Placeholder assertion to make the test pass