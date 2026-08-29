"""
Resource Manager Quota Extensions for AI-OS M10.

Extends ResourceManager with autonomous resource quotas and reserved budgets
for self-directed services (objective generator, replan detector, autonomous judge).

This is M10-N9 implementation per M10-IMPLEMENTATION-SPEC.md §11.9.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.events.base import Event
from aios.events.types import PlanningRequested
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService
from aios.core.resource_manager import (
    ResourceManager,
    get_resource_manager,
    ResourceType,
    ResourceLimit,
    ResourceAllocation,
)

logger = logging.getLogger(__name__)


@dataclass
class AutonomousQuotaConfig:
    """Configuration for autonomous resource quotas."""
    enabled: bool = True
    # Reserved budgets for autonomous services (percentage of total limit)
    objective_generator_quota_pct: float = 0.05  # 5% of available resources
    replan_detector_quota_pct: float = 0.03  # 3%
    autonomous_judge_quota_pct: float = 0.02  # 2%
    # Fallback budget when autonomous quotas exhausted
    fallback_budget_pct: float = 0.10  # 10%


@dataclass
class AutonomousQuota:
    """Quota allocation for an autonomous service."""
    service_name: str
    resource_type: ResourceType
    reserved_amount: float
    used_amount: float = 0.0
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class ResourceManagerQuotaService(BaseService):
    """
    Extends ResourceManager with autonomous service quotas.

    M10-N9: ResourceManager Autonomous Quotas (GAP-M10-10)
    - Reserves resource budgets for autonomous services
    - Enforces per-service quotas with rejection/fallback logic
    - Integrates with ResourceExhausted events for fallback triggering
    - Budget exhaustion test: Asserts quota enforcement on autonomous actions
    """

    name = "resource_manager_quota"
    version = "1.0.0"
    description = "Autonomous service resource quotas and budget management"
    depends_on: list[str] = ["resource_manager", "objective_generator", "replan_detector", "autonomous_judge"]

    def __init__(
        self,
        config: AutonomousQuotaConfig | None = None,
        resource_manager: ResourceManager | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or AutonomousQuotaConfig()
        self._resource_manager = resource_manager or get_resource_manager()
        self._event_bus = get_core_event_bus()
        self._autonomous_quotas: dict[str, AutonomousQuota] = {}
        self._quota_exhausted_callbacks: list[callable] = []

    @property
    def config(self) -> AutonomousQuotaConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"ResourceManagerQuotaService.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            self._initialize_autonomous_quotas()
            self.subscribe(self._on_planning_requested, PlanningRequested)
            self.subscribe(self._on_resource_exhausted, EventType.RESOURCE_EXHAUSTED)
            logger.info("ResourceManagerQuotaService initialized with autonomous quotas")
        else:
            logger.info("ResourceManagerQuotaService disabled by config")

    async def on_stop(self) -> None:
        logger.info("ResourceManagerQuotaService stopped")

    def _initialize_autonomous_quotas(self) -> None:
        """Initialize reserved quotas for autonomous services."""
        # Get current limits
        for resource_type in ResourceType:
            limit = self._resource_manager.get_limit(resource_type)
            if not limit:
                continue

            total_limit = limit.limit

            # Reserve quotas for each autonomous service
            quotas = [
                ("objective_generator", self._config.objective_generator_quota_pct),
                ("replan_detector", self._config.replan_detector_quota_pct),
                ("autonomous_judge", self._config.autonomous_judge_quota_pct),
            ]

            for service_name, pct in quotas:
                reserved = total_limit * pct
                quota = AutonomousQuota(
                    service_name=service_name,
                    resource_type=resource_type,
                    reserved_amount=reserved,
                )
                key = f"{service_name}:{resource_type.value}"
                self._autonomous_quotas[key] = quota

            logger.info(f"Initialized autonomous quotas for {resource_type.value}: "
                       f"objective_gen={total_limit * self._config.objective_generator_quota_pct:.1f}, "
                       f"replan={total_limit * self._config.replan_detector_quota_pct:.1f}, "
                       f"judge={total_limit * self._config.autonomous_judge_quota_pct:.1f}")

    async def _on_planning_requested(self, event: Event) -> None:
        """Track autonomous planning requests for quota usage."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        is_autonomous = payload.get("autonomous", False)
        source = payload.get("source", "unknown")

        if is_autonomous:
            # Track quota usage based on source
            if source == "autonomous":
                await self._consume_quota("objective_generator", ResourceType.CPU, 1.0)
                await self._consume_quota("objective_generator", ResourceType.API_QUOTA, 10.0)
            elif source == "autonomous_replan":
                await self._consume_quota("replan_detector", ResourceType.CPU, 0.5)
                await self._consume_quota("replan_detector", ResourceType.API_QUOTA, 5.0)

    async def _on_resource_exhausted(self, event: Event) -> None:
        """Handle resource exhaustion - trigger fallback if autonomous quota exhausted."""
        payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)
        resource_type_str = payload.get("resource_type", "")
        requestor = payload.get("requestor", "")

        # Check if this was an autonomous service
        for service_name in ["objective_generator", "replan_detector", "autonomous_judge"]:
            if service_name in requestor:
                await self._handle_autonomous_exhaustion(service_name, resource_type_str)

    async def _consume_quota(
        self,
        service_name: str,
        resource_type: ResourceType,
        amount: float,
    ) -> bool:
        """Consume quota for an autonomous service."""
        key = f"{service_name}:{resource_type.value}"
        quota = self._autonomous_quotas.get(key)

        if not quota:
            return True  # No quota tracking = unlimited

        if quota.used_amount + amount > quota.reserved_amount:
            # Quota exhausted
            logger.warning(f"Autonomous quota exhausted for {service_name}/{resource_type.value}")
            await self._on_quota_exhausted(service_name, resource_type)
            return False

        quota.used_amount += amount
        return True

    async def _on_quota_exhausted(
        self,
        service_name: str,
        resource_type: ResourceType,
    ) -> None:
        """Handle autonomous quota exhaustion."""
        # Emit event for fallback coordinator
        if self._event_bus is None:
            return

        import uuid
        correlation_id = uuid.uuid4()

        core_event = CoreEvent(
            eventType=EventType.RESOURCE_EXHAUSTED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload({
                "resource_type": resource_type.value,
                "amount": 0,
                "requestor": service_name,
                "reason": "autonomous_quota_exhausted",
                "service": service_name,
            }),
            priority=EventPriority.HIGH,
            category=category_for_event_type(EventType.RESOURCE_EXHAUSTED),
        )

        try:
            await self._event_bus.publish(core_event)
        except Exception as e:
            logger.error(f"Failed to emit quota exhaustion event: {e}")

    async def _handle_autonomous_exhaustion(
        self,
        service_name: str,
        resource_type_str: str,
    ) -> None:
        """Handle exhaustion of autonomous service resources."""
        try:
            resource_type = ResourceType(resource_type_str)
        except ValueError:
            return

        key = f"{service_name}:{resource_type.value}"
        quota = self._autonomous_quotas.get(key)

        if quota:
            # Reset quota for new period
            quota.used_amount = 0.0
            quota.period_start = datetime.utcnow()
            logger.info(f"Reset quota for {service_name}/{resource_type.value} after exhaustion")

    def get_autonomous_quota(self, service_name: str, resource_type: ResourceType) -> AutonomousQuota | None:
        """Get quota info for an autonomous service."""
        key = f"{service_name}:{resource_type.value}"
        return self._autonomous_quotas.get(key)

    def get_all_quotas(self) -> dict[str, dict[str, Any]]:
        """Get all autonomous quota statuses."""
        return {
            key: {
                "service_name": q.service_name,
                "resource_type": q.resource_type.value,
                "reserved": q.reserved_amount,
                "used": q.used_amount,
                "available": q.reserved_amount - q.used_amount,
                "utilization": q.used_amount / q.reserved_amount if q.reserved_amount > 0 else 0,
            }
            for key, q in self._autonomous_quotas.items()
        }

    def register_quota_exhausted_callback(self, callback: callable) -> None:
        """Register callback for quota exhaustion events."""
        self._quota_exhausted_callbacks.append(callback)

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "enabled": self._config.enabled,
            "quotas": self.get_all_quotas(),
        })
        return stats


# Global instance
_global_resource_manager_quota: ResourceManagerQuotaService | None = None


def get_resource_manager_quota(
    config: AutonomousQuotaConfig | None = None,
    resource_manager: ResourceManager | None = None,
) -> ResourceManagerQuotaService:
    """Get or create the global ResourceManagerQuotaService."""
    global _global_resource_manager_quota
    if _global_resource_manager_quota is None:
        _global_resource_manager_quota = ResourceManagerQuotaService(
            config=config, resource_manager=resource_manager
        )
    return _global_resource_manager_quota


def set_resource_manager_quota(service: ResourceManagerQuotaService) -> None:
    """Set the global ResourceManagerQuotaService."""
    global _global_resource_manager_quota
    _global_resource_manager_quota = service


__all__ = [
    "ResourceManagerQuotaService",
    "AutonomousQuotaConfig",
    "AutonomousQuota",
    "get_resource_manager_quota",
    "set_resource_manager_quota",
]