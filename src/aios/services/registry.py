"""
Service Registry Compatibility Layer for AI-OS Engineering Services.

This module provides the legacy ServiceRegistry API surface while delegating to the
canonical ServiceRegistry (C2, Task 6) to eliminate the split-brain architecture
where two ServiceRegistry instances existed concurrently (INV-SR-STR-001).

All new code should import from aios.core.service_registry directly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from aios.core.service_registry import (
    ServiceRegistry as CoreServiceRegistry,
    ServiceType as CoreServiceType,
    ServiceLifecycleState as CoreServiceLifecycleState,
    ServiceRegistration as CoreServiceRegistration,
    ServiceRegistryHealth as CoreServiceRegistryHealth,
    ServiceRegistryError,
    get_service_registry as get_core_service_registry,
    reset_service_registry_singleton,
    set_service_registry as set_core_service_registry,
)
from aios.events.core.bus import EventBus as CoreEventBus
from aios.events.core.types import EventType
from aios.services.base import BaseService, ServiceStatus

logger = logging.getLogger(__name__)


class ServiceNotFoundError(KeyError):
    """Raised when a requested service is not registered."""


# Legacy compatibility wrapper class (Rule 8 — permitted to remain as a
# compatibility surface AS LONG AS it does not create a second runtime
# authority). This class delegates every operation to the canonical
# aios.core.service_registry.ServiceRegistry singleton; it never constructs or
# holds its own registry instance. The ``get_service_registry()`` accessor (below)
# returns the canonical singleton directly so that
# ``kernel.service_registry is get_service_registry()`` holds (Rule 10).
class ServiceRegistry:
    """Legacy-compatible ServiceRegistry wrapper delegating to canonical C2."""

    def __init__(self, event_bus: Any | None = None):
        # The canonical ServiceRegistry is a singleton managed by the kernel.
        # This wrapper does NOT create its own instance.
        self._event_bus = event_bus

    @staticmethod
    def _run_sync(coro: Any) -> Any:
        """Run a coroutine to completion from a synchronous legacy call site.

        The canonical ServiceRegistry exposes an async ``register`` (matching the
        Task-5 EventBus Core Component pattern). Legacy callers invoke
        ``register`` synchronously; this bridges the coroutine to completion
        without creating a second runtime authority. If a loop is already
        running in this thread (e.g. an async test), the coroutine is driven on
        a dedicated thread with its own loop so it still completes synchronously
        from the caller's perspective.
        """
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is None:
            return asyncio.run(coro)
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(asyncio.run, coro).result()

    # --- registration ----------------------------------------------
    def register(self, service: BaseService) -> BaseService:
        """Register a service. Re-registering replaces the old instance."""
        core_registry = self._get_core_registry()
        if core_registry is None:
            logger.warning("Canonical ServiceRegistry not initialized; deferring registration")
            return service

        self._run_sync(
            core_registry.register(
                service,
                service_id=f"engineering.{service.name}",
                service_type=CoreServiceType.ENGINEERING,
                metadata={"version": service.version, "description": service.description},
            )
        )
        logger.info("Registered service '%s' (v%s) in canonical registry", service.name, service.version)
        return service

    def unregister(self, name: str) -> bool:
        """Remove a service from the registry (does not stop it)."""
        core_registry = self._get_core_registry()
        if core_registry is None:
            return False
        try:
            return core_registry.unregister(f"engineering.{name}")
        except ServiceRegistryError:
            return False

    # --- lookup ----------------------------------------------------
    def get(self, name: str) -> BaseService:
        core_registry = self._get_core_registry()
        if core_registry is None:
            raise ServiceNotFoundError(name)
        svc = core_registry.get_service(f"engineering.{name}")
        if svc is None:
            raise ServiceNotFoundError(name)
        return svc

    def has(self, name: str) -> bool:
        core_registry = self._get_core_registry()
        if core_registry is None:
            return False
        return core_registry.get_service(f"engineering.{name}") is not None

    def list_services(self) -> list[str]:
        core_registry = self._get_core_registry()
        if core_registry is None:
            return []
        engineering_services = core_registry.get_services_by_type(CoreServiceType.ENGINEERING)
        return [svc.name for svc in engineering_services]

    def all_services(self) -> list[BaseService]:
        core_registry = self._get_core_registry()
        if core_registry is None:
            return []
        return core_registry.get_services_by_type(CoreServiceType.ENGINEERING)

    # --- dependency-ordered startup --------------------------------
    def _start_order(self) -> list[BaseService]:
        """Topologically order services by depends_on (best-effort)."""
        # The canonical registry handles topological ordering
        # Return all engineering services in their dependency order
        core_registry = self._get_core_registry()
        if core_registry is None:
            return []
        # Get init plan from canonical registry
        try:
            plan = core_registry.compute_initialization_plan()
            services = []
            for batch in plan:
                for sid in batch:
                    if sid.startswith("engineering."):
                        svc = core_registry.get_service(sid)
                        if svc:
                            services.append(svc)
            return services
        except Exception:
            # Fallback to all engineering services
            return self.all_services()

    async def start_all(self) -> dict[str, bool]:
        """Start all services in dependency order."""
        core_registry = self._get_core_registry()
        if core_registry is None:
            # Kernel not started; services will be started by kernel
            return {}

        results: dict[str, bool] = {}
        for srv in self._start_order():
            try:
                await srv.start()
                # Mark as running in canonical registry
                await core_registry.mark_service_running(f"engineering.{srv.name}")
                results[srv.name] = True
                logger.info("Started service '%s'", srv.name)
            except Exception as e:  # noqa: BLE001
                results[srv.name] = False
                logger.exception("Failed to start service '%s': %s", srv.name, e)
                await core_registry.mark_service_failed(f"engineering.{srv.name}", str(e))
        return results

    async def stop_all(self) -> dict[str, bool]:
        """Stop all services in reverse start order."""
        core_registry = self._get_core_registry()
        if core_registry is None:
            return {}

        results: dict[str, bool] = {}
        for srv in reversed(self._start_order()):
            try:
                await srv.stop()
                results[srv.name] = True
                logger.info("Stopped service '%s'", srv.name)
            except Exception as e:  # noqa: BLE001
                results[srv.name] = False
                logger.exception("Error stopping service '%s': %s", srv.name, e)
        return results

    async def start(self, name: str) -> bool:
        core_registry = self._get_core_registry()
        if core_registry is None:
            return False
        svc = self.get(name)
        await svc.start()
        await core_registry.mark_service_running(f"engineering.{name}")
        return True

    async def stop(self, name: str) -> bool:
        core_registry = self._get_core_registry()
        if core_registry is None:
            return False
        svc = self.get(name)
        await svc.stop()
        await core_registry.mark_service_shutdown(f"engineering.{name}")
        return True

    async def health_check(self) -> dict[str, bool]:
        """Run every service's health check."""
        core_registry = self._get_core_registry()
        if core_registry is None:
            return {}

        report: dict[str, bool] = {}
        for srv in self.all_services():
            if srv.status == ServiceStatus.STOPPED:
                report[srv.name] = False
                continue
            try:
                ok = await srv.on_health_check()
            except Exception as e:  # noqa: BLE001
                ok = False
                srv._error = str(e)
            report[srv.name] = bool(ok)
            await core_registry.update_health(f"engineering.{srv.name}", bool(ok), error=srv._error if not ok else None)
        return report

    def get_stats(self) -> dict[str, Any]:
        core_registry = self._get_core_registry()
        if core_registry is None:
            return {"total": 0, "running": 0, "services": {}}
        stats = core_registry.get_stats()
        # Filter to just engineering services for legacy compatibility
        engineering_services = core_registry.get_services_by_type(CoreServiceType.ENGINEERING)
        return {
            "total": len(engineering_services),
            "running": sum(1 for s in engineering_services if s.is_running),
            "services": {name: s.get_stats() for name, s in {svc.name: svc for svc in engineering_services}.items()},
        }

    def _get_core_registry(self) -> CoreServiceRegistry | None:
        """Get the canonical ServiceRegistry."""
        return get_core_service_registry()


# Legacy accessor: returns the canonical ServiceRegistry singleton
# (INV-SR-STR-001 — exactly one ServiceRegistry instance per process). The kernel
# constructs and owns that singleton; this accessor exposes the SAME object so
# ``kernel.service_registry is get_service_registry()`` holds (Rule 10). No
# separate legacy runtime authority is created.
def get_service_registry(event_bus: Any | None = None) -> ServiceRegistry:
    """Get the canonical ServiceRegistry singleton (Rule 8 / Rule 10)."""
    return get_core_service_registry(event_bus=event_bus)


def set_service_registry(registry: ServiceRegistry) -> None:
    """Set the canonical ServiceRegistry singleton (kernel-owned construction)."""
    set_core_service_registry(registry)


__all__ = [
    "ServiceRegistry",
    "ServiceNotFoundError",
    "get_service_registry",
    "set_service_registry",
]