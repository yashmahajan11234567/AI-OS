"""
Autonomy Fallback Coordinator for AI-OS M10.

System-wide advisory-mode coordinator that disables autonomous services on triggers:
- Security violation
- Bound exceeded
- System instability
- Manual override

This is M10-N12 implementation per M10-IMPLEMENTATION-SPEC.md §11.12.
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


class FallbackTrigger(str, Enum):
    """Triggers for advisory-mode fallback."""
    SECURITY_VIOLATION = "security_violation"
    BOUND_EXCEEDED = "bound_exceeded"
    SYSTEM_INSTABILITY = "system_instability"
    MANUAL_OVERRIDE = "manual_override"


class FallbackState(str, Enum):
    """Fallback system state."""
    NORMAL = "normal"  # Autonomous features active
    ADVISORY_ONLY = "advisory_only"  # Fallback active
    RECOVERING = "recovering"  # Attempting to restore autonomy


@dataclass
class AutonomyFallbackConfig:
    """Configuration for autonomy fallback system."""
    enabled: bool = True
    auto_fallback_on_security: bool = True
    auto_fallback_on_bounds: bool = True
    auto_fallback_on_instability: bool = True
    recovery_check_interval: int = 60  # Seconds between recovery checks
    require_manual_recovery: bool = True  # Manual intervention required to exit fallback


@dataclass
class FallbackEvent:
    """Record of a fallback activation."""
    event_id: str
    trigger: FallbackTrigger
    description: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolved_at: datetime | None = None
    resolved_by: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AutonomyFallbackService(BaseService):
    """
    System-wide advisory-mode coordinator for graceful degradation.

    M10-N12: Fallback to Advisory Mode (GAP-M10-11)
    - Triggers: security violation, bound exceeded, system instability, manual override
    - Action: Disables autonomous services, enables advisory-only paths
    - Verification test: System gracefully degrades to M9 advisory-only behavior
    """

    name = "autonomy_fallback"
    version = "1.0.0"
    description = "Graceful degradation to advisory-only mode for autonomous system"
    depends_on: list[str] = []

    def __init__(
        self,
        config: AutonomyFallbackConfig | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or AutonomyFallbackConfig()
        self._fallback_state = FallbackState.NORMAL
        self._fallback_events: list[FallbackEvent] = []
        self._event_bus = get_core_event_bus()
        self._recovery_task: Any | None = None

    @property
    def config(self) -> AutonomyFallbackConfig:
        return self._config

    @property
    def fallback_state(self) -> FallbackState:
        return self._fallback_state

    async def on_start(self) -> None:
        logger.info(f"AutonomyFallbackService.on_start called, state={self._fallback_state.value}")
        if self._config.enabled:
            # Subscribe to trigger events using canonical EventTypes
            self.subscribe(self._on_security_violation, EventType.SECURITY_ISSUE_FOUND)
            self.subscribe(self._on_resource_exhausted, EventType.RESOURCE_EXHAUSTED)
            self.subscribe(self._on_human_escalation, EventType.HUMAN_ESCALATION_REQUIRED)
            logger.info("AutonomyFallbackService subscribed to trigger events")

    async def on_stop(self) -> None:
        if self._recovery_task:
            self._recovery_task.cancel()
        logger.info("AutonomyFallbackService stopped")

    async def _on_security_violation(self, event: Event) -> None:
        """Handle security violation trigger."""
        if self._config.auto_fallback_on_security:
            payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
            await self.trigger_fallback(
                trigger=FallbackTrigger.SECURITY_VIOLATION,
                description=f"Security violation: {payload.get('violation', 'unknown')}",
                metadata=payload,
            )

    async def _on_resource_exhausted(self, event: Event) -> None:
        """Handle resource exhaustion trigger."""
        if self._config.auto_fallback_on_bounds:
            payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
            await self.trigger_fallback(
                trigger=FallbackTrigger.BOUND_EXCEEDED,
                description=f"Resource exhausted: {payload.get('resource_type', 'unknown')}",
                metadata=payload,
            )

    async def _on_human_escalation(self, event: Event) -> None:
        """Handle human escalation trigger (bound exhaustion from self-prompting)."""
        if self._config.auto_fallback_on_instability:
            payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
            await self.trigger_fallback(
                trigger=FallbackTrigger.SYSTEM_INSTABILITY,
                description=f"Human escalation required: {payload.get('reason', 'bound_exhaustion')}",
                metadata=payload,
            )

    async def trigger_fallback(
        self,
        trigger: FallbackTrigger,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger fallback to advisory-only mode.

        Returns status dict with event_id and new state.
        """
        if self._fallback_state == FallbackState.ADVISORY_ONLY:
            return {
                "status": "already_in_fallback",
                "current_state": self._fallback_state.value,
            }

        self._fallback_state = FallbackState.ADVISORY_ONLY

        event_id = f"fallback_{len(self._fallback_events) + 1}"
        fallback_event = FallbackEvent(
            event_id=event_id,
            trigger=trigger,
            description=description,
            metadata=metadata or {},
        )
        self._fallback_events.append(fallback_event)

        # Disable all autonomous services
        await self._disable_autonomous_services()

        # Emit fallback activated event
        await self._emit_fallback_event("fallback_activated", fallback_event)

        logger.warning(f"FALLBACK ACTIVATED: {trigger.value} - {description}")

        return {
            "status": "fallback_activated",
            "event_id": event_id,
            "trigger": trigger.value,
            "description": description,
            "state": self._fallback_state.value,
            "timestamp": fallback_event.timestamp.isoformat(),
        }

    async def trigger_manual_fallback(self, description: str = "Manual fallback triggered") -> dict[str, Any]:
        """Manually trigger fallback via human override."""
        return await self.trigger_fallback(
            trigger=FallbackTrigger.MANUAL_OVERRIDE,
            description=description,
        )

    async def attempt_recovery(self, triggered_by: str = "human") -> dict[str, Any]:
        """
        Attempt to recover from fallback to normal autonomy.

        If require_manual_recovery is True, this only works with manual trigger.
        """
        if self._fallback_state != FallbackState.ADVISORY_ONLY:
            return {
                "status": "not_in_fallback",
                "current_state": self._fallback_state.value,
            }

        if self._config.require_manual_recovery and triggered_by != "human":
            return {
                "status": "manual_recovery_required",
                "message": "Manual intervention required to exit fallback mode",
            }

        self._fallback_state = FallbackState.RECOVERING

        # Attempt to re-enable autonomous services
        success = await self._enable_autonomous_services()

        # Also re-enable autonomy in the override service
        if success:
            try:
                from aios.services.autonomy_override import get_autonomy_override
                override_svc = get_autonomy_override()
                if override_svc.current_state != override_svc.current_state.ENABLED:
                    await override_svc.enable_autonomy(triggered_by=triggered_by, description="Recovery from fallback")
            except Exception as e:
                logger.debug(f"Could not re-enable autonomy override: {e}")

        if success:
            # Mark latest fallback event as resolved
            for event in reversed(self._fallback_events):
                if not event.resolved:
                    event.resolved = True
                    event.resolved_at = datetime.utcnow()
                    event.resolved_by = triggered_by
                    break

            self._fallback_state = FallbackState.NORMAL

            # Emit recovery event
            await self._emit_fallback_event("fallback_recovered", FallbackEvent(
                event_id=f"recovery_{len(self._fallback_events)}",
                trigger=FallbackTrigger.MANUAL_OVERRIDE,
                description=f"Recovery initiated by {triggered_by}",
            ))

            logger.info(f"FALLBACK RECOVERED: autonomy restored by {triggered_by}")
            return {
                "status": "recovered",
                "state": self._fallback_state.value,
                "recovered_by": triggered_by,
            }
        else:
            self._fallback_state = FallbackState.ADVISORY_ONLY
            return {
                "status": "recovery_failed",
                "state": self._fallback_state.value,
            }

    async def _disable_autonomous_services(self) -> None:
        """Disable all autonomous services."""
        autonomous_services = [
            "objective_generator",
            "replan_detector",
            "autonomous_judge",
        ]

        for svc_name in autonomous_services:
            try:
                # Use service registry if available
                if hasattr(self, '_service_registry') and self._service_registry:
                    svc = self._service_registry.get_service(f"engineering.{svc_name}")
                else:
                    # Try global getter
                    if svc_name == "objective_generator":
                        from aios.services.objective_generator import get_objective_generator
                        svc = get_objective_generator()
                    elif svc_name == "replan_detector":
                        from aios.services.replan_detector import get_replan_detector
                        svc = get_replan_detector()
                    elif svc_name == "autonomous_judge":
                        from aios.services.autonomous_judge import get_autonomous_judge
                        svc = get_autonomous_judge()
                    else:
                        svc = None

                if svc and hasattr(svc, 'config'):
                    if hasattr(svc.config, 'enabled'):
                        svc.config.enabled = False
                    elif hasattr(svc.config, 'mode'):
                        from aios.services.autonomous_judge import AutonomousJudgeMode
                        svc.config.mode = AutonomousJudgeMode.ADVISORY_ONLY
                    logger.info(f"Disabled autonomous service: {svc_name}")
            except Exception as e:
                logger.debug(f"Could not disable {svc_name}: {e}")

    async def _enable_autonomous_services(self) -> bool:
        """Re-enable autonomous services. Returns True if all succeeded."""
        all_succeeded = True
        autonomous_services = [
            "objective_generator",
            "replan_detector",
            "autonomous_judge",
        ]

        for svc_name in autonomous_services:
            try:
                if hasattr(self, '_service_registry') and self._service_registry:
                    svc = self._service_registry.get_service(f"engineering.{svc_name}")
                else:
                    if svc_name == "objective_generator":
                        from aios.services.objective_generator import get_objective_generator
                        svc = get_objective_generator()
                    elif svc_name == "replan_detector":
                        from aios.services.replan_detector import get_replan_detector
                        svc = get_replan_detector()
                    elif svc_name == "autonomous_judge":
                        from aios.services.autonomous_judge import get_autonomous_judge
                        svc = get_autonomous_judge()
                    else:
                        svc = None

                if svc and hasattr(svc, 'config'):
                    if hasattr(svc.config, 'enabled'):
                        svc.config.enabled = True
                    elif hasattr(svc.config, 'mode'):
                        from aios.services.autonomous_judge import AutonomousJudgeMode
                        svc.config.mode = AutonomousJudgeMode.AUTONOMOUS_ENABLED
                    logger.info(f"Re-enabled autonomous service: {svc_name}")
            except Exception as e:
                logger.error(f"Could not re-enable {svc_name}: {e}")
                all_succeeded = False

        return all_succeeded

    async def _emit_fallback_event(self, event_name: str, fallback_event: FallbackEvent) -> None:
        """Emit fallback state change event."""
        if self._event_bus is None:
            return

        import uuid
        correlation_id = uuid.uuid4()

        core_event = CoreEvent(
            eventType=EventType.AI_AGENT_AUDIT_EMITTED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "event_name": event_name,
                "fallback_event_id": fallback_event.event_id,
                "trigger": fallback_event.trigger.value,
                "description": fallback_event.description,
                "state": self._fallback_state.value,
                "occurred_at": fallback_event.timestamp.isoformat(),
                "metadata": fallback_event.metadata,
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(EventType.AI_AGENT_AUDIT_EMITTED),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit fallback event: {e}")

    def get_fallback_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get fallback event history."""
        return [
            {
                "event_id": e.event_id,
                "trigger": e.trigger.value,
                "description": e.description,
                "timestamp": e.timestamp.isoformat(),
                "resolved": e.resolved,
                "resolved_at": e.resolved_at.isoformat() if e.resolved_at else None,
                "resolved_by": e.resolved_by,
            }
            for e in self._fallback_events[-limit:]
        ]

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "fallback_state": self._fallback_state.value,
            "total_fallback_events": len(self._fallback_events),
            "active_fallback": sum(1 for e in self._fallback_events if not e.resolved),
            "config": {
                "enabled": self._config.enabled,
                "auto_fallback_on_security": self._config.auto_fallback_on_security,
                "auto_fallback_on_bounds": self._config.auto_fallback_on_bounds,
                "auto_fallback_on_instability": self._config.auto_fallback_on_instability,
                "require_manual_recovery": self._config.require_manual_recovery,
            },
        })
        return stats


# Global instance
_global_autonomy_fallback: AutonomyFallbackService | None = None


def get_autonomy_fallback(
    config: AutonomyFallbackConfig | None = None,
) -> AutonomyFallbackService:
    """Get or create the global AutonomyFallbackService."""
    global _global_autonomy_fallback
    if _global_autonomy_fallback is None:
        _global_autonomy_fallback = AutonomyFallbackService(config=config)
    return _global_autonomy_fallback


def set_autonomy_fallback(service: AutonomyFallbackService) -> None:
    """Set the global AutonomyFallbackService."""
    global _global_autonomy_fallback
    _global_autonomy_fallback = service


__all__ = [
    "AutonomyFallbackService",
    "AutonomyFallbackConfig",
    "FallbackTrigger",
    "FallbackState",
    "FallbackEvent",
    "get_autonomy_fallback",
    "set_autonomy_fallback",
]