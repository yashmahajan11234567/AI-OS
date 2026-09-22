"""
Unit tests for dashboard User allow-rule registration in SecurityManager.

Tests the specific allow-rules registered for dashboard_user to enable
the four required project actions:
- project.create
- project.transition
- project.publish_notion
- project.clear_action

These tests verify the SecurityManager registration works correctly
and maintains the fail-closed security model.
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
    """A SecurityManager wired to real canonical C1–C4, uninitialized."""
    mgr = SecurityManager(
        service_registry=service_registry,
        configuration_manager=configuration_manager,
        logger=logger,
    )
    yield mgr
    # Cleanup is handled by the individual fixtures


async def test_security_manager_allow_rule_wildcard_resource():
    """Test that None in resource position acts as wildcard."""
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
        # Register rule with None resource (wildcard)
        sm.register_allow_rule(principal="test_user", action="test_action", resource=None)

        # Should match any resource
        assert sm.authorize("test_user", "test_action", "any_resource") == SecurityDecision.ALLOW
        assert sm.authorize("test_user", "test_action", "another_resource") == SecurityDecision.ALLOW
        assert sm.authorize("test_user", "test_action", "") == SecurityDecision.ALLOW

        # Should not match different principal or action
        assert sm.authorize("wrong_user", "test_action", "any_resource") == SecurityDecision.DENY
        assert sm.authorize("test_user", "wrong_action", "any_resource") == SecurityDecision.DENY

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_dashboard_user_project_actions_allowed():
    """Test that dashboard_user can perform the four required project actions."""
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
        # Register the exact four dashboard_user project action rules
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Test all four actions are ALLOWed
        assert sm.authorize("dashboard_user", "project.create", "any_project") == SecurityDecision.ALLOW
        assert sm.authorize("dashboard_user", "project.transition", "any_project") == SecurityDecision.ALLOW
        assert sm.authorize("dashboard_user", "project.publish_notion", "any_project") == SecurityDecision.ALLOW
        assert sm.authorize("dashboard_user", "project.clear_action", "any_project") == SecurityDecision.ALLOW

        # Test with specific resources
        assert sm.authorize("dashboard_user", "project.create", "project_123") == SecurityDecision.ALLOW
        assert sm.authorize("dashboard_user", "project.transition", "project_456") == SecurityDecision.ALLOW

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_dashboard_user_unrelated_action_denied():
    """Test that dashboard_user cannot perform unrelated actions (fail-closed)."""
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
        # Register only the four project actions
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Test unrelated actions are DENYed (fail-closed)
        assert sm.authorize("dashboard_user", "integration.validate", "any_resource") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "self_loop.control", "any_resource") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "failure_recovery.trigger", "any_resource") == SecurityDecision.DENY
        assert sm.authorize("dashboard_user", "unknown.action", "any_resource") == SecurityDecision.DENY

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_other_principals_denied_by_default():
    """Test that unknown principals remain DENYed by default (fail-closed preserved)."""
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
        # Register dashboard_user rules
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.transition", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.publish_notion", resource=None)
        sm.register_allow_rule(principal="dashboard_user", action="project.clear_action", resource=None)

        # Test other principals are still DENYed (fail-closed)
        assert sm.authorize("unknown_user", "project.create", "any_resource") == SecurityDecision.DENY
        assert sm.authorize("another_user", "project.transition", "any_resource") == SecurityDecision.DENY
        assert sm.authorize("", "project.create", "any_resource") == SecurityDecision.DENY  # empty principal
        assert sm.authorize(None, "project.create", "any_resource") == SecurityDecision.DENY  # None principal

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


async def test_security_manager_revoke_allow_rule():
    """Test that revoking allow-rules works correctly."""
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
        # Register rule
        sm.register_allow_rule(principal="dashboard_user", action="project.create", resource=None)

        # Should be allowed
        assert sm.authorize("dashboard_user", "project.create", "any_resource") == SecurityDecision.ALLOW

        # Revoke rule
        sm.revoke_allow_rule(principal="dashboard_user", action="project.create", resource=None)

        # Should be denied after revocation (fail-closed)
        assert sm.authorize("dashboard_user", "project.create", "any_resource") == SecurityDecision.DENY

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()


def test_security_manager_fail_closed_preserved():
    """Test that SecurityManager fail-closed behavior is preserved by default."""
    # Setup
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    sr = get_service_registry(event_bus=bus)
    cm = ConfigurationManager(event_bus=bus)
    logger = get_logger()

    sm = SecurityManager(
        service_registry=sr,
        configuration_manager=cm,
        logger=logger,
    )

    try:
        # With no rules registered, everything should be DENYed (fail-closed)
        assert sm.authorize("any_principal", "any_action", "any_resource") == SecurityDecision.DENY
        assert sm.authorize(None, "any_action", "any_resource") == SecurityDecision.DENY  # unknown principal
        assert sm.authorize("", "any_action", "any_resource") == SecurityDecision.DENY  # empty principal

    finally:
        reset_event_bus_singleton()
        reset_service_registry_singleton()
        reset_configuration_manager_singleton()