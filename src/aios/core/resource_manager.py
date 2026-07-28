"""
Resource Manager for AI-OS Hermes Kernel.

Manages compute, memory, API quotas, and other resources with scheduling and limits.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Types of managed resources."""

    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    DISK = "disk"
    NETWORK = "network"
    API_QUOTA = "api_quota"
    RATE_LIMIT = "rate_limit"
    CUSTOM = "custom"


@dataclass
class ResourceLimit:
    """Resource limit configuration."""

    resource_type: ResourceType
    limit: float
    unit: str
    description: str = ""
    warning_threshold: float = 0.8  # 80%
    critical_threshold: float = 0.95  # 95%


@dataclass
class ResourceAllocation:
    """Resource allocation record."""

    allocation_id: str
    resource_type: ResourceType
    amount: float
    requestor: str
    purpose: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceUsage:
    """Current resource usage."""

    resource_type: ResourceType
    used: float
    limit: float
    available: float
    unit: str
    allocations: list[ResourceAllocation] = field(default_factory=list)


class ResourceManager:
    """
    Manages system resources with limits, quotas, and scheduling.

    Features:
    - Resource limits and quotas
    - Allocation tracking
    - Usage monitoring
    - Wait queues for contested resources
    - Automatic cleanup of expired allocations
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize the Resource Manager.

        Args:
            config: Configuration with resource limits
        """
        self._config = config or {}
        self._limits: dict[ResourceType, ResourceLimit] = {}
        self._allocations: dict[ResourceType, list[ResourceAllocation]] = {}
        self._wait_queues: dict[ResourceType, list[tuple[str, asyncio.Future]]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

        # Initialize default limits
        self._init_default_limits()

    def _init_default_limits(self) -> None:
        """Initialize default resource limits."""
        defaults = [
            ResourceLimit(ResourceType.CPU, 80, "percent", "CPU utilization limit"),
            ResourceLimit(ResourceType.MEMORY, 8192, "MB", "Memory limit"),
            ResourceLimit(ResourceType.GPU, 1, "count", "GPU count limit"),
            ResourceLimit(ResourceType.DISK, 10240, "MB", "Disk space limit"),
            ResourceLimit(ResourceType.API_QUOTA, 10000, "requests/day", "API request quota"),
            ResourceLimit(ResourceType.RATE_LIMIT, 100, "requests/min", "Rate limit"),
        ]

        for limit in defaults:
            self.set_limit(limit)

    def set_limit(self, limit: ResourceLimit) -> None:
        """Set a resource limit."""
        self._limits[limit.resource_type] = limit
        logger.info(f"Set {limit.resource_type.value} limit: {limit.limit} {limit.unit}")

    def get_limit(self, resource_type: ResourceType) -> ResourceLimit | None:
        """Get a resource limit."""
        return self._limits.get(resource_type)

    async def allocate(
        self,
        resource_type: ResourceType,
        amount: float,
        requestor: str,
        purpose: str = "",
        ttl_seconds: int | None = None,
        timeout: float = 30.0,
    ) -> ResourceAllocation:
        """
        Allocate a resource.

        Args:
            resource_type: Type of resource
            amount: Amount to allocate
            requestor: Requestor identifier
            purpose: Purpose of allocation
            ttl_seconds: Time to live in seconds
            timeout: Maximum time to wait for allocation

        Returns:
            ResourceAllocation record

        Raises:
            ResourceExhausted: If resource unavailable and timeout reached
        """
        async with self._lock:
            if await self._can_allocate(resource_type, amount):
                return self._do_allocate(resource_type, amount, requestor, purpose, ttl_seconds)

        # Wait for resource
        future = asyncio.get_event_loop().create_future()
        async with self._lock:
            if resource_type not in self._wait_queues:
                self._wait_queues[resource_type] = []
            self._wait_queues[resource_type].append((requestor, future))

        try:
            allocation = await asyncio.wait_for(future, timeout=timeout)
            return allocation
        except asyncio.TimeoutError:
            async with self._lock:
                # Remove from wait queue
                queue = self._wait_queues.get(resource_type, [])
                self._wait_queues[resource_type] = [
                    (r, f) for r, f in queue if f != future
                ]
            raise ResourceExhausted(
                f"Timeout waiting for {resource_type.value}: {amount} {self._limits[resource_type].unit}"
            )

    def _can_allocate(self, resource_type: ResourceType, amount: float) -> bool:
        """Check if resource can be allocated."""
        limit = self._limits.get(resource_type)
        if not limit:
            return True  # No limit = unlimited

        used = sum(a.amount for a in self._allocations.get(resource_type, []))
        return (used + amount) <= limit.limit

    def _do_allocate(
        self,
        resource_type: ResourceType,
        amount: float,
        requestor: str,
        purpose: str,
        ttl_seconds: int | None,
    ) -> ResourceAllocation:
        """Perform the allocation."""
        from uuid import uuid4

        expires_at = None
        if ttl_seconds:
            from datetime import timedelta

            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        allocation = ResourceAllocation(
            allocation_id=str(uuid4()),
            resource_type=resource_type,
            amount=amount,
            requestor=requestor,
            purpose=purpose,
            expires_at=expires_at,
        )

        if resource_type not in self._allocations:
            self._allocations[resource_type] = []
        if resource_type not in self._allocations:
            self._allocations[resource_type] = []
        self._allocations[resource_type].append(allocation)

        # Check thresholds and warn
        limit = self._limits.get(resource_type)
        if limit:
            used = sum(a.amount for a in self._allocations[resource_type])
            usage_ratio = used / limit.limit
            if usage_ratio >= limit.critical_threshold:
                logger.critical(
                    f"Critical {resource_type.value} usage: {usage_ratio:.1%}"
                )
            elif usage_ratio >= limit.warning_threshold:
                logger.warning(
                    f"High {resource_type.value} usage: {usage_ratio:.1%}"
                )

        return allocation

    def release(self, allocation_id: str) -> bool:
        """
        Release a resource allocation.

        Args:
            allocation_id: Allocation ID to release

        Returns:
            True if released, False if not found
        """
        for resource_type, allocations in self._allocations.items():
            for i, alloc in enumerate(allocations):
                if alloc.allocation_id == allocation_id:
                    allocations.pop(i)

                    # Check wait queue
                    self._process_wait_queue(resource_type)
                    return True

        return False

    def _process_wait_queue(self, resource_type: ResourceType) -> None:
        """Process wait queue for a resource."""
        queue = self._wait_queues.get(resource_type, [])
        if not queue:
            return

        new_queue = []
        for requestor, future in queue:
            if future.done():
                continue

            # Check if can allocate (simplified - first in queue gets priority)
            limit = self._limits.get(resource_type)
            if not limit:
                continue

            used = sum(a.amount for a in self._allocations.get(resource_type, []))
            # We don't know the amount requested, so just notify
            future.set_result(None)

        self._wait_queues[resource_type] = new_queue

    def release_all_for_requestor(self, requestor: str) -> int:
        """Release all allocations for a requestor."""
        count = 0
        for resource_type, allocations in self._allocations.items():
            to_remove = [a for a in allocations if a.requestor == requestor]
            for alloc in to_remove:
                allocations.remove(alloc)
                count += 1
                self._process_wait_queue(resource_type)
        return count

    def get_usage(self, resource_type: ResourceType | None = None) -> dict[str, Any]:
        """Get current resource usage."""
        if resource_type:
            return self._get_resource_usage(resource_type).to_dict()

        return {
            rt.value: self._get_resource_usage(rt).to_dict()
            for rt in self._limits
        }

    def _get_resource_usage(self, resource_type: ResourceType) -> ResourceUsage:
        """Get usage for a specific resource."""
        limit = self._limits.get(resource_type)
        if not limit:
            return ResourceUsage(
                resource_type=resource_type,
                used=0,
                limit=0,
                available=0,
                unit="unknown",
            )

        allocations = self._allocations.get(resource_type, [])
        used = sum(a.amount for a in allocations)
        available = max(0, limit.limit - used)

        return ResourceUsage(
            resource_type=resource_type,
            used=used,
            limit=limit.limit,
            available=available,
            unit=limit.unit,
            allocations=allocations,
        )

    def add_allocation(self, allocation: ResourceAllocation) -> None:
        """Manually add an allocation (for tracking)."""
        if allocation.resource_type not in self._allocations:
            self._allocations[allocation.resource_type] = []
        self._allocations[allocation.resource_type].append(allocation)

    def start_cleanup_task(self, interval_seconds: int = 60) -> None:
        """Start background cleanup of expired allocations."""
        if self._cleanup_task:
            return

        async def cleanup():
            while True:
                await asyncio.sleep(interval_seconds)
                await self._cleanup_expired()

        self._cleanup_task = asyncio.create_task(cleanup())

    def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None

    async def _cleanup_expired(self) -> int:
        """Clean up expired allocations."""
        now = datetime.utcnow()
        cleaned = 0

        for resource_type, allocations in self._allocations.items():
            expired = [a for a in allocations if a.expires_at and a.expires_at < now]
            for alloc in expired:
                allocations.remove(alloc)
                cleaned += 1

            if expired:
                self._process_wait_queue(resource_type)

        if cleaned:
            logger.debug(f"Cleaned up {cleaned} expired allocations")

        return cleaned

    def get_stats(self) -> dict[str, Any]:
        """Get resource manager statistics."""
        return {
            "limits": {
                rt.value: {
                    "limit": lim.limit,
                    "unit": lim.unit,
                    "used": sum(a.amount for a in self._allocations.get(rt, [])),
                }
                for rt, lim in self._limits.items()
            },
            "total_allocations": sum(len(a) for a in self._allocations.values()),
            "waiting_requests": sum(len(q) for q in self._wait_queues.values()),
        }


class ResourceExhausted(Exception):
    """Raised when a resource is exhausted and cannot be allocated."""

    pass


# Global resource manager instance
_global_resource_manager: ResourceManager | None = None


def get_resource_manager(config: dict[str, Any] | None = None) -> ResourceManager:
    """Get or create the global resource manager."""
    global _global_resource_manager
    if _global_resource_manager is None:
        _global_resource_manager = ResourceManager(config)
    return _global_resource_manager


def set_resource_manager(manager: ResourceManager) -> None:
    """Set the global resource manager."""
    global _global_resource_manager
    _global_resource_manager = manager


# Add to_dict method to ResourceUsage
def _add_to_dict():
    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_type": self.resource_type.value,
            "used": self.used,
            "limit": self.limit,
            "available": self.available,
            "unit": self.unit,
            "utilization": self.used / self.limit if self.limit > 0 else 0,
            "allocations": [
                {
                    "allocation_id": a.allocation_id,
                    "amount": a.amount,
                    "requestor": a.requestor,
                    "purpose": a.purpose,
                    "expires_at": a.expires_at.isoformat() if a.expires_at else None,
                }
                for a in self.allocations
            ],
        }

    ResourceUsage.to_dict = to_dict


_add_to_dict()

__all__ = [
    "ResourceManager",
    "ResourceType",
    "ResourceLimit",
    "ResourceAllocation",
    "ResourceUsage",
    "ResourceExhausted",
    "get_resource_manager",
    "set_resource_manager",
]