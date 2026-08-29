"""
Human Override Mechanism for AI-OS M10.

Provides human interface for autonomous mode control:
- disable_autonomy: Immediate fallback to advisory-only mode
- enable_autonomy: Re-enable autonomous services
- get_autonomy_status: Query current autonomy state

This is M10-N10 implementation per M10-IMPLEMENTATION-SPEC.md §11.10.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.base import Event
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class AutonomyState(str, Enum):
    """System autonomy state."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEGRADED = "degraded"  # Some autonomous features disabled


class OverrideReason(str, Enum):
    """Reason for autonomy override."""
    MANUAL = "manual"
    SECURITY_VIOLATION = "security_violation"
    BOUND_EXCEEDED = "bound_exceeded"
    SYSTEM_INSTABILITY = "system_instability"


@dataclass
class AutonomyOverrideConfig:
    """Configuration for autonomy override system."""
    allow_manual_override: bool = True
    auto_disable_on_security_violation: bool = True
    auto_disable_on_bound_exceeded: bool = True
    auto_disable_on_instability: bool = True
    notify_on_override: bool = True


@dataclass
class OverrideRecord:
    """Record of an autonomy override action."""
    override_id: str
    reason: OverrideReason
    previous_state: AutonomyState
    new_state: AutonomyState
    triggered_by: str
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class AutonomyOverrideService(BaseService):
    """
    Human interface for autonomous mode control.

    M10-N10: Human Override Mechanism (GAP-M10-12)
    - Commands: disable_autonomy, enable_autonomy, get_autonomy_status
    - Override triggers immediate fallback to advisory-only mode
    - Integration test: Human override stops autonomous replan mid-cycle
    """

    name = "autonomy_override"
    version = "1.0.0"
    description = "Human override control for autonomous system operations"
    depends_on: list[str] = []

    def __init__(
        self,
        config: AutonomyOverrideConfig | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or AutonomyOverrideConfig()
        self._current_state = AutonomyState.ENABLED
        self._override_history: list[OverrideRecord] = []
        self._event_bus = get_core_event_bus()
        self._disabled_services: set[str] = set()

    @property
    def config(self) -> AutonomyOverrideConfig:
        return self._config

    @property
    def current_state(self) -> AutonomyState:
        return self._current_state

    async def on_start(self) -> None:
        logger.info(f"AutonomyOverrideService.on_start called, initial_state={self._current_state.value}")
        # Subscribe to security/bound events that may trigger auto-disable
        from aios.events.types import SecurityViolation, ResourceExhausted
        self.subscribe(self._on_security_violation, SecurityViolation)
        self.subscribe(self._on_resource_exhausted, ResourceExhausted)

    async def on_stop(self) -> None:
        logger.info("AutonomyOverrideService stopped")

    async def _on_security_violation(self, event: Event) -> None:
        """Handle security violation - auto-disable if configured."""
        if self._config.auto_disable_on_security_violation:
            payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
            await self.disable_autonomy(
                reason=OverrideReason.SECURITY_VIOLATION,
                triggered_by="security_manager",
                description=f"Security violation: {payload.get('violation', 'unknown')}",
            )

    async def _on_resource_exhausted(self, event: Event) -> None:
        """Handle resource exhaustion - auto-disable if configured."""
        if self._config.auto_disable_on_bound_exceeded:
            payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
            await self.disable_autonomy(
                reason=OverrideReason.BOUND_EXCEEDED,
                triggered_by="resource_manager",
                description=f"Resource exhausted: {payload.get('resource_type', 'unknown')}",
            )

    async def disable_autonomy(
        self,
        reason: OverrideReason = OverrideReason.MANUAL,
        triggered_by: str = "human",
        description: str = "",
    ) -> dict[str, Any]:
        """
        Disable autonomous operations - immediate fallback to advisory-only mode.

        Returns status dict with previous_state, new_state, and override_id.
        """
        if self._current_state == AutonomyState.DISABLED:
            return {
                "status": "already_disabled",
                "current_state": self._current_state.value,
            }

        previous_state = self._current_state
        self._current_state = AutonomyState.DISABLED

        override_id = f"override_{len(self._override_history) + 1}"
        record = OverrideRecord(
            override_id=override_id,
            reason=reason,
            previous_state=previous_state,
            new_state=AutonomyState.DISABLED,
            triggered_by=triggered_by,
            description=description,
        )
        self._override_history.append(record)

        # Emit autonomy disabled event
        await self._emit_autonomy_event("autonomy_disabled", record)

        # Disable autonomous services
        await self._disable_autonomous_services()

        if self._config.notify_on_override:
            logger.warning(f"AUTONOMY DISABLED by {triggered_by}: {description}")

        return {
            "status": "disabled",
            "previous_state": previous_state.value,
            "new_state": self._current_state.value,
            "override_id": override_id,
            "reason": reason.value,
            "timestamp": record.timestamp.isoformat(),
        }

    async def enable_autonomy(
        self,
        triggered_by: str = "human",
        description: str = "",
    ) -> dict[str, Any]:
        """
        Re-enable autonomous operations.

        Returns status dict with previous_state, new_state.
        """
        if self._current_state == AutonomyState.ENABLED:
            return {
                "status": "already_enabled",
                "current_state": self._current_state.value,
            }

        previous_state = self._current_state
        self._current_state = AutonomyState.ENABLED

        override_id = f"override_{len(self._override_history) + 1}"
        record = OverrideRecord(
            override_id=override_id,
            reason=OverrideReason.MANUAL,
            previous_state=previous_state,
            new_state=AutonomyState.ENABLED,
            triggered_by=triggered_by,
            description=description,
        )
        self._override_history.append(record)

        # Emit autonomy enabled event
        await self._emit_autonomy_event("autonomy_enabled", record)

        # Re-enable autonomous services
        await self._enable_autonomous_services()

        if self._config.notify_on_override:
            logger.info(f"AUTONOMY ENABLED by {triggered_by}: {description}")

        return {
            "status": "enabled",
            "previous_state": previous_state.value,
            "new_state": self._current_state.value,
            "override_id": override_id,
            "timestamp": record.timestamp.isoformat(),
        }

    async def get_autonomy_status(self) -> dict[str, Any]:
        """Get current autonomy system status."""
        return {
            "state": self._current_state.value,
            "disabled_services": list(self._disabled_services),
            "override_history": [
                {
                    "override_id": r.override_id,
                    "reason": r.reason.value,
                    "previous_state": r.previous_state.value,
                    "new_state": r.new_state.value,
                    "triggered_by": r.triggered_by,
                    "description": r.description,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in self._override_history[-10:]  # Last 10 overrides
            ],
            "config": {
                "allow_manual_override": self._config.allow_manual_override,
                "auto_disable_on_security_violation": self._config.auto_disable_on_security_violation,
                "auto_disable_on_bound_exceeded": self._config.auto_disable_on_bound_exceeded,
                "auto_disable_on_instability": self._config.auto_disable_on_instability,
            },
        }

    async def _disable_autonomous_services(self) -> None:
        """Disable all known autonomous services."""
        autonomous_services = [
            "objective_generator",
            "replan_detector",
            "autonomous_judge",
        ]
        for svc_name in autonomous_services:
            try:
                svc = self._service_registry.get_service(f"engineering.{svc_name}")
                if svc and hasattr(svc, 'config'):
                    # Disable by setting config
                    if hasattr(svc.config, 'enabled'):
                        svc.config.enabled = False
                    elif hasattr(svc.config, 'mode'):
                        from aios.services.autonomous_judge import AutonomousJudgeMode
                        svc.config.mode = AutonomousJudgeMode.ADVISORY_ONLY
                    self._disabled_services.add(svc_name)
                    logger.info(f"Disabled autonomous service: {svc_name}")
            except Exception as e:
                logger.debug(f"Could not disable {svc_name}: {e}")

    async def _enable_autonomous_services(self) -> None:
        """Re-enable previously disabled autonomous services."""
        for svc_name in list(self._disabled_services):
            try:
                svc = self._service_registry.get_service(f"engineering.{svc_name}")
                if svc and hasattr(svc, 'config'):
                    if hasattr(svc.config, 'enabled'):
                        svc.config.enabled = True
                    elif hasattr(svc.config, 'mode'):
                        from aios.services.autonomous_judge import AutonomousJudgeMode
                        svc.config.mode = AutonomousJudgeMode.AUTONOMOUS_ENABLED
                    self._disabled_services.discard(svc_name)
                    logger.info(f"Re-enabled autonomous service: {svc_name}")
            except Exception as e:
                logger.debug(f"Could not re-enable {svc_name}: {e}")

    async def _emit_autonomy_event(self, event_name: str, record: OverrideRecord) -> None:
        """Emit autonomy state change event."""
        if self._event_bus is None:
            return

        correlation_id = __import__('uuid').uuid4()

        core_event = CoreEvent(
            eventType=EventType.AI_AGENT_AUDIT_EMITTED,  # Reuse existing event type
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "event_name": event_name,
                "override_id": record.override_id,
                "reason": record.reason.value,
                "previous_state": record.previous_state.value,
                "new_state": record.new_state.value,
                "triggered_by": record.triggered_by,
                "description": record.description,
                "occurred_at": record.timestamp.isoformat(),
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(EventType.AI_AGENT_AUDIT_EMITTED),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit autonomy event: {e}")

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "current_state": self._current_state.value,
            "total_overrides": len(self._override_history),
            "disabled_services_count": len(self._disabled_services),
        })
        return stats


# Global instance
_global_autonomy_override: AutonomyOverrideService | None = None


def get_autonomy_override(
    config: AutonomyOverrideConfig | None = None,
) -> AutonomyOverrideService:
    """Get or create the global AutonomyOverrideService."""
    global _global_autonomy_override
    if _global_autonomy_override is None:
        _global_autonomy_override = AutonomyOverrideService(config=config)
    return _global_autonomy_override


def set_autonomy_override(service: AutonomyOverrideService) -> None:
    """Set the global AutonomyOverrideService."""
    global _global_autonomy_override
    _global_autonomy_override = service


__all__ = [
    "AutonomyOverrideService",
    "AutonomyOverrideConfig",
    "AutonomyState",
    "OverrideReason",
    "OverrideRecord",
    "get_autonomy_override",
    "set_autonomy_override",
]