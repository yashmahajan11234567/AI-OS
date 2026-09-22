"""
Unit tests for provider credential rotation allow-rules in SecurityManager.

Tests the specific allow-rules registered for dashboard_user to enable
authorized secret rotation for provider API keys while preserving the
existing fail-closed security architecture.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from aios.core.security_manager import SecurityDecision, SecurityManager
from aios.core.service_registry import get_service_registry, reset_service_registry_singleton
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.events.core.types import EventType
from aios.core.configuration_manager import ConfigurationManager, reset_configuration_manager_singleton
from aios.core.structured_logger import get_logger


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
def security_manager(event_bus, service_registry, configuration_manager, logger):
    """A SecurityManager wired to real canonical C1-C4, uninitialized."""
    mgr = SecurityManager(
        service_registry=service_registry,
        configuration_manager=configuration_manager,
        logger=logger,
    )
    yield mgr
    # Cleanup is handled by the individual fixtures


async def test_dashboard_user_nim_credential_rotation_allowed():
    """Test that dashboard_user can rotate NIM provider API key."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register the dashboard_user project actions (existing)
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Register the new provider credential rotation rules (T2 requirement)
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        # Test NIM credential rotation is ALLOWed
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.ALLOW

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_dashboard_user_freellmapi_credential_rotation_allowed():
    """Test that dashboard_user can rotate FreeLLMAPI provider API key."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register the dashboard_user project actions (existing)
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Register the new provider credential rotation rules (T2 requirement)
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        # Test FreeLLMAPI credential rotation is ALLOWed
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.freellmapi.apiKey") == SecurityDecision.ALLOW

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_dashboard_user_unrelated_provider_credential_denied():
    """Test that dashboard_user cannot rotate unrelated provider API keys (fail-closed)."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register the dashboard_user project actions (existing)
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Register the new provider credential rotation rules (T2 requirement)
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        # Test unrelated provider credential rotation is DENYed (fail-closed)
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.openai.apiKey") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.anthropic.apiKey") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.google.apiKey") == SecurityDecision.DENY

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_unauthorized_principal_denied():
    """Test that unauthorized principals cannot perform provider credential rotation (fail-closed preserved)."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register the dashboard_user project actions (existing)
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Register the new provider credential rotation rules (T2 requirement)
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        # Test other principals are still DENYed (fail-closed)
        assert sm.authorize("unknown_user", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY
        assert sm.authorize("another_user", "secret.rotate", "config:llm.providers.freellmapi.apiKey") == SecurityDecision.DENY
        assert sm.authorize("", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY  # empty principal
        assert sm.authorize(None, "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY  # None principal

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_security_manager_revoke_provider_credential_rule():
    """Test that revoking provider credential rotation allow-rules works correctly."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register NIM rule
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")

        # Should be allowed
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.ALLOW

        # Revoke rule
        sm.revoke_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")

        # Should be denied after revocation (fail-closed)
        assert sm.authorize("dashboard_user", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_existing_security_manager_behavior_preserved():
    """Test that existing SecurityManager behavior remains intact."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()

    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # Register ONLY the new provider credential rotation rules (T2 requirement)
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.nim.apiKey")
        sm.register_allow_rule(principal="dashboard_user", action="secret.rotate", resource="config:llm.providers.freellmapi.apiKey")

        # Test that existing dashboard_user project actions are still DENYed (fail-closed preserved for non-registered actions)
        assert sm.authorize("dashboard_user", "project.create", "any_project") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "project.transition", "any_project") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "project.publish_notion", "any_project") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "project.clear_action", "any_project") == SecurityDecision.DENY

        # Test that unknown principals remain DENYed by default (fail-closed preserved)
        assert sm.authorize("unknown_user", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY
        assert sm.authorize("", "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY  # empty principal
        assert sm.authorize(None, "secret.rotate", "config:llm.providers.nim.apiKey") == SecurityDecision.DENY  # None principal

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()