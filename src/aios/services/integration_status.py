"""
Integration Status Service for Dashboard Backend.

Provides programmatic access to integration status for frontend dashboards.
Registered as `core.integration_status` in ServiceRegistry.

Features:
- get_all_status() - list of all IntegrationStatusReport
- get_status(name) - single integration report
- Periodic health checks (configurable interval)
- Emits IntegrationStateChangedEvent on state transitions
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from aios.integrations import (
    load_integrations_config,
    CANONICAL_INTEGRATIONS,
    IntegrationConfigRegistry,
    ValidationRegistry,
)
from aios.integrations.state import IntegrationState, IntegrationStatusReport
from aios.events.core.bus import EventBus, EventType
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.event import Event
from aios.services.base import BaseService, ServiceStatus, ServiceInfo


logger = logging.getLogger(__name__)


@dataclass
class IntegrationStateChangedEvent:
    """Event emitted when an integration's state changes."""

    integration_name: str
    previous_state: IntegrationState
    new_state: IntegrationState
    timestamp: datetime = field(default_factory=datetime.now)
    details: dict[str, Any] = field(default_factory=dict)

    def to_event(self) -> Event:
        """Convert to canonical Event for EventBus."""
        return Event(
            eventType=EventType.INTEGRATION_STATUS_CHANGED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="integration_status",
            ),
            payload={
                "integration_name": self.integration_name,
                "previous_state": self.previous_state.value,
                "new_state": self.new_state.value,
                "changed_at": self.timestamp.isoformat(),
                "details": self.details,
            },
        )


class IntegrationStatusService(BaseService):
    """
    Service for tracking and exposing integration status.

    - Periodically runs health checks on configured REAL integrations
    - Exposes status via get_all_status() and get_status()
    - Emits state change events for real-time dashboard updates
    """

    name = "integration_status"
    version = "1.0.0"
    description = "Integration status tracking for dashboard"

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        event_bus: Optional[EventBus] = None,
        registry: Optional[IntegrationConfigRegistry] = None,
        info: Optional[ServiceInfo] = None,
    ):
        super().__init__(
            event_bus=event_bus,
            info=info,
        )
        self._config = config or {}
        self._registry = registry or load_integrations_config()
        self._validation_registry = ValidationRegistry()
        self._health_check_interval = self._config.get("health_check_interval_seconds", 60)
        self._health_check_task: Optional[asyncio.Task] = None
        self._state_lock = threading.RLock()
        self._last_states: dict[str, IntegrationState] = {}

    async def initialize(self) -> None:
        await super().initialize()
        # Record initial states
        with self._state_lock:
            for name in CANONICAL_INTEGRATIONS:
                entry = self._registry.get(name)
                if entry:
                    self._last_states[name] = entry.state
        # Start periodic health checks
        if self._health_check_interval > 0:
            self._health_check_task = asyncio.create_task(self._periodic_health_checks())
        logger.info("IntegrationStatusService initialized")

    async def shutdown(self) -> None:
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        await super().shutdown()
        logger.info("IntegrationStatusService shut down")

    async def _periodic_health_checks(self) -> None:
        """Run health checks periodically for REAL integrations."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._run_all_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic health check error: {e}")

    async def _run_all_health_checks(self) -> None:
        """Run health checks on all REAL integrations that are connected."""
        for name in CANONICAL_INTEGRATIONS:
            entry = self._registry.get(name)
            if not entry:
                continue

            # Only run health checks on REAL integrations that are connected/verified
            if entry.is_real and entry.state in (IntegrationState.CONNECTED, IntegrationState.OPERATIONALLY_VERIFIED):
                try:
                    await self._check_and_emit(name, entry)
                except Exception as e:
                    logger.error(f"Health check failed for {name}: {e}")

    async def _check_and_emit(self, name: str, entry) -> None:
        """Run health check and emit event if state changed."""
        previous_state = entry.state
        result = entry.run_health_check()

        # Check if state changed
        if previous_state != entry.state:
            event = IntegrationStateChangedEvent(
                integration_name=name,
                previous_state=previous_state,
                new_state=entry.state,
                details=result.details,
            )
            if self._event_bus:
                await self._event_bus.publish(event.to_event())
            logger.info(f"Integration {name}: {previous_state.value} -> {entry.state.value}")

            # Update last known state
            with self._state_lock:
                self._last_states[name] = entry.state

    # ============================================================
    # Public API for Dashboard
    # ============================================================

    def get_all_status(self) -> list[IntegrationStatusReport]:
        """
        Get status reports for all integrations.

        Returns list of IntegrationStatusReport suitable for dashboard rendering.
        """
        reports = []
        for name in CANONICAL_INTEGRATIONS:
            entry = self._registry.get(name)
            if entry:
                reports.append(entry.get_status_report())
        return reports

    def get_status(self, name: str) -> Optional[IntegrationStatusReport]:
        """Get status report for a single integration."""
        entry = self._registry.get(name)
        if entry:
            return entry.get_status_report()
        return None

    def get_status_dict(self, name: str, redact_secrets: bool = True) -> Optional[dict[str, Any]]:
        """Get status as dict (redacted by default for safety)."""
        report = self.get_status(name)
        if report:
            return report.to_dict(redact_secrets=redact_secrets)
        return None

    def get_all_status_dict(self, redact_secrets: bool = True) -> list[dict[str, Any]]:
        """Get all statuses as dicts (redacted by default)."""
        return [r.to_dict(redact_secrets=redact_secrets) for r in self.get_all_status()]

    # ============================================================
    # Manual Operations (called by CLI)
    # ============================================================

    async def validate_integration(self, name: str) -> IntegrationStatusReport:
        """Manually trigger validation for an integration."""
        entry = self._registry.get(name)
        if not entry:
            raise ValueError(f"Integration not found: {name}")

        previous_state = entry.state
        entry.validate_resources(self._validation_registry)

        if previous_state != entry.state:
            event = IntegrationStateChangedEvent(
                integration_name=name,
                previous_state=previous_state,
                new_state=entry.state,
                details=entry.validation_result.details if entry.validation_result else {},
            )
            if self._event_bus:
                await self._event_bus.publish(event.to_event())
            with self._state_lock:
                self._last_states[name] = entry.state

        return entry.get_status_report()

    async def connect_integration(self, name: str) -> IntegrationStatusReport:
        """Manually trigger REAL connection attempt (gated)."""
        entry = self._registry.get(name)
        if not entry:
            raise ValueError(f"Integration not found: {name}")

        previous_state = entry.state
        result = entry.attempt_connection()

        if previous_state != entry.state:
            event = IntegrationStateChangedEvent(
                integration_name=name,
                previous_state=previous_state,
                new_state=entry.state,
                details=result.details,
            )
            if self._event_bus:
                await self._event_bus.publish(event.to_event())
            with self._state_lock:
                self._last_states[name] = entry.state

        return entry.get_status_report()

    async def health_check_integration(self, name: str) -> IntegrationStatusReport:
        """Manually trigger health check for an integration."""
        entry = self._registry.get(name)
        if not entry:
            raise ValueError(f"Integration not found: {name}")

        previous_state = entry.state
        entry.run_health_check()

        if previous_state != entry.state:
            event = IntegrationStateChangedEvent(
                integration_name=name,
                previous_state=previous_state,
                new_state=entry.state,
                details=entry.health_check_result.details if entry.health_check_result else {},
            )
            if self._event_bus:
                await self._event_bus.publish(event.to_event())
            with self._state_lock:
                self._last_states[name] = entry.state

        return entry.get_status_report()


# Service registry key
SERVICE_KEY = "core.integration_status"


async def create_integration_status_service(config: dict[str, Any], event_bus: EventBus) -> IntegrationStatusService:
    """Factory function for ServiceRegistry registration."""
    return IntegrationStatusService(config=config, event_bus=event_bus)