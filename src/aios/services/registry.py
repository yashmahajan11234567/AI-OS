"""Service Registry for AI-OS Engineering Services.

The registry owns the lifecycle of all Engineering Services for the Kernel:
register, resolve, start (in dependency order), stop (reverse order), and
observe health. Services are still isolated from each other - the registry
only manages lifecycle and introspection, never brokers inter-service calls.
"""

from __future__ import annotations

import logging
from typing import Any

from aios.events.bus import EventBus, get_event_bus
from aios.events.types import ServiceStarted, ServiceStopped, ServiceHealthy, ServiceUnhealthy
from aios.services.base import BaseService, ServiceStatus

logger = logging.getLogger(__name__)


class ServiceNotFoundError(KeyError):
    """Raised when a requested service is not registered."""


class ServiceRegistry:
    """Manages the lifecycle of all Engineering Services."""

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus or get_event_bus()
        self._services: dict[str, BaseService] = {}

    # ----- registration ----------------------------------------------
    def register(self, service: BaseService) -> BaseService:
        """Register a service. Re-registering replaces the old instance."""
        if service.name in self._services:
            logger.warning("Replacing already-registered service '%s'", service.name)
        self._services[service.name] = service
        logger.info("Registered service '%s' (v%s)", service.name, service.version)
        return service

    def unregister(self, name: str) -> bool:
        """Remove a service from the registry (does not stop it)."""
        return self._services.pop(name) is not None

    # ----- lookup ----------------------------------------------------
    def get(self, name: str) -> BaseService:
        srv = self._services.get(name)
        if srv is None:
            raise ServiceNotFoundError(name)
        return srv

    def has(self, name: str) -> bool:
        return name in self._services

    def list_services(self) -> list[str]:
        return list(self._services.keys())

    def all_services(self) -> list[BaseService]:
        return list(self._services.values())

    # ----- dependency-ordered startup --------------------------------
    def _start_order(self) -> list[BaseService]:
        """Topologically order services by depends_on (best-effort)."""
        ordered: list[BaseService] = []
        seen: set[str] = set()
        visiting: set[str] = set()

        def visit(svc: BaseService) -> None:
            if svc.name in seen:
                return
            if svc.name in visiting:
                logger.warning("Circular dependency detected at '%s'", svc.name)
                return
            visiting.add(svc.name)
            for dep in svc.depends_on:
                dep_svc = self._services.get(dep)
                if dep_svc is not None:
                    visit(dep_svc)
            visiting.discard(svc.name)
            seen.add(svc.name)
            ordered.append(svc)

        for svc in self._services.values():
            visit(svc)
        return ordered

    async def start_all(self) -> dict[str, bool]:
        """Start all services in dependency order."""
        results: dict[str, bool] = {}
        for srv in self._start_order():
            try:
                await srv.start()
                results[srv.name] = True
                self._event_bus.publish(
                    ServiceStarted(
                        source_service="service_registry",
                        correlation_id=f"svc_{srv.name}",
                        payload={"service": srv.name, "version": srv.version},
                    )
                )
            except Exception as e:  # noqa: BLE001
                results[srv.name] = False
                logger.exception("Failed to start service '%s': %s", srv.name, e)
                self._event_bus.publish(
                    ServiceUnhealthy(
                        source_service="service_registry",
                        correlation_id=f"svc_{srv.name}",
                        payload={"service": srv.name, "error": str(e)},
                    )
                )
        return results

    async def stop_all(self) -> dict[str, bool]:
        """Stop all services in reverse start order."""
        results: dict[str, bool] = {}
        for srv in reversed(self._start_order()):
            try:
                await srv.stop()
                results[srv.name] = True
                self._event_bus.publish(
                    ServiceStopped(
                        source_service="service_registry",
                        correlation_id=f"svc_{srv.name}",
                        payload={"service": srv.name},
                    )
                )
            except Exception as e:  # noqa: BLE001
                results[srv.name] = False
                logger.exception("Error stopping service '%s': %s", srv.name, e)
        return results

    async def start(self, name: str) -> bool:
        await self.get(name).start()
        return True

    async def stop(self, name: str) -> bool:
        await self.get(name).stop()
        return True

    async def health_check(self) -> dict[str, bool]:
        """Run every service'''s health check."""
        report: dict[str, bool] = {}
        for srv in self._services.values():
            if srv.status == ServiceStatus.STOPPED:
                report[srv.name] = False
                continue
            try:
                ok = await srv.on_health_check()
            except Exception as e:  # noqa: BLE001
                ok = False
                srv._error = str(e)
            report[srv.name] = bool(ok)
            self._event_bus.publish(
                (ServiceHealthy if ok else ServiceUnhealthy)(
                    source_service="service_registry",
                    correlation_id=f"health_{srv.name}",
                    payload={"service": srv.name},
                )
            )
        return report

    def get_stats(self) -> dict[str, Any]:
        return {
            "total": len(self._services),
            "running": sum(1 for s in self._services.values() if s.is_running),
            "services": {name: s.get_stats() for name, s in self._services.items()},
        }


# Global registry (lazily created; the Kernel owns services via the registry)
_global_registry: ServiceRegistry | None = None


def get_service_registry(event_bus: EventBus | None = None) -> ServiceRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ServiceRegistry(event_bus)
    return _global_registry


def set_service_registry(registry: ServiceRegistry) -> None:
    global _global_registry
    _global_registry = registry


__all__ = [
    "ServiceRegistry",
    "ServiceNotFoundError",
    "get_service_registry",
    "set_service_registry",
]