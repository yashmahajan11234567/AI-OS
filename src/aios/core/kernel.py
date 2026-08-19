"""
Hermes Kernel - The Core Orchestrator for AI-OS.

The Kernel is the central coordination component that manages the Event Bus,
Workflow Manager, State Manager, and Resource Manager.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aios.config.loader import load_config
from aios.config.models import AppConfig
from aios.events.bus import EventBus, get_event_bus, set_event_bus
from aios.events.types import KernelStarted, KernelStopped

# The Kernel owns the single global event bus and registers every manager
# as its global singleton. This guarantees that all managers (which call
# get_event_bus()/get_state_manager()/...) share the SAME instances the
# Kernel created, instead of silently constructing their own and emitting
# events into a disconnected bus.
from aios.core.state import StateManager, get_state_manager, set_state_manager
from aios.core.workflow import (
    WorkflowManager,
    get_workflow_manager,
    set_workflow_manager,
)
from aios.core.resource_manager import (
    ResourceManager,
    get_resource_manager,
    set_resource_manager,
)
from aios.core.configuration_manager import (
    ConfigurationManager,
    get_configuration_manager,
    set_configuration_manager,
)
from aios.core.structured_logger import (
    StructuredLogger,
    get_logger,
    set_logger,
)
from aios.services.registry import ServiceRegistry, get_service_registry, set_service_registry
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class KernelConfig:
    """Kernel configuration."""
    name: str = "Hermes"
    version: str = "0.1.0"
    config_path: Path | None = None
    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    event_bus_max_history: int = 10000
    auto_start_services: bool = True


@dataclass
class ServiceStatus:
    """Service status tracking."""
    name: str
    started: bool = False
    healthy: bool = True
    started_at: datetime | None = None
    last_error: str | None = None


class HermesKernel:
    """
    Hermes Kernel - The central orchestrator for AI-OS.

    The Kernel manages:
    - Event Bus for inter-service communication
    - State Manager for workflow/application state
    - Workflow Manager for DAG-based workflows
    - Resource Manager for quotas
    """

    def __init__(
        self,
        config: KernelConfig | None = None,
        app_config: AppConfig | None = None,
    ):
        """
        Initialize the Hermes Kernel.

        Args:
            config: Kernel configuration
            app_config: Application configuration
        """
        self._config = config or KernelConfig()
        self._app_config = app_config
        self._running = False
        self._start_time: datetime | None = None

        # Core components (only the four required components)
        self._event_bus: EventBus | None = None
        self._state_manager: StateManager | None = None
        self._workflow_manager: WorkflowManager | None = None
        self._resource_manager: ResourceManager | None = None
        # ServiceRegistry (C2, Phase 1) is created during start(); initialize the
        # field so the accessor raises a clear RuntimeError before initialization
        # rather than AttributeError (FIX 8).
        self._service_registry: ServiceRegistry | None = None
        # C3 ConfigurationManager — authoritative configuration authority
        # (Phase 2). Constructed and owned exclusively by HermesKernel.
        self._configuration: ConfigurationManager | None = None
        # C4 StructuredLogger — observability substrate (Phase 3, §3.6).
        # Constructed and owned exclusively by HermesKernel; set as the global
        # singleton so all components resolve the SAME instance via
        # ``kernel.logger``. Initialize it in Phase 3 (after EventBus,
        # ServiceRegistry, ConfigurationManager) and shut it down first in
        # Phase S3.
        self._structured_logger: StructuredLogger | None = None

        # Removed managers (now accessed via capability services):
        # - CheckpointManager -> via CheckpointService (if created) or WorkflowManager
        # - RetryManager -> via RetryService (if created)
        # - RootCauseAnalyzer -> via RootCauseService (if created)
        # - ModelRouter -> via ModelRouterService (if created)
        # - MemoryManager -> via MemoryService
        # - SkillManager -> via SkillService
        # - MCPManager -> via MCPService
        # - AIAgencyService -> via AIAgencyService
        # - CouncilManager -> via CouncilService
        # - StructuredLogger -> stdlib logging

        # Service tracking
        self._services: dict[str, ServiceStatus] = {}

        # Ensure data directory exists
        self._config.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> KernelConfig:
        """Get kernel configuration."""
        return self._config

    @property
    def app_config(self) -> AppConfig | None:
        """Get application configuration."""
        return self._app_config

    @property
    def running(self) -> bool:
        """Check if kernel is running."""
        return self._running

    @property
    def event_bus(self) -> EventBus | None:
        """Get event bus."""
        return self._event_bus

    @property
    def state_manager(self) -> StateManager | None:
        """Get state manager."""
        return self._state_manager

    @property
    def workflow_manager(self) -> WorkflowManager | None:
        """Get workflow manager."""
        return self._workflow_manager

    @property
    def resource_manager(self) -> ResourceManager | None:
        """Get resource manager."""
        return self._resource_manager

    @property
    def configuration(self) -> ConfigurationManager | None:
        """Get the ConfigurationManager Core Component (C3, Part 3 §3.5)."""
        return self._configuration

    @property
    def service_registry(self) -> ServiceRegistry | None:
        """Get service registry."""
        return self._service_registry

    @property
    def logger(self) -> StructuredLogger | None:
        """Get the StructuredLogger Core Component (C4, Part 3 §3.6)."""
        return self._structured_logger

    def register_service(self, service: BaseService) -> BaseService:
        """Register an Engineering Service with the kernel."""
        if self._service_registry:
            return self._service_registry.register(service)
        raise RuntimeError("Service registry not initialized. Start kernel first.")

    def get_service(self, name: str) -> BaseService:
        """Get a registered Engineering Service."""
        if self._service_registry:
            return self._service_registry.get(name)
        raise RuntimeError("Service registry not initialized. Start kernel first.")

    async def start(self) -> None:
        """Start the kernel and all core services."""
        if self._running:
            logger.warning("Kernel already running")
            return

        logger.info("Starting Hermes Kernel...")

        # Initialize core components
        await self._init_core_components()

        # Initialize Service Registry
        await self._init_service_registry()

        # Start services if enabled
        if self._config.auto_start_services:
            await self._start_services()

        # Emit kernel started event
        self._event_bus.publish(
            KernelStarted(
                source_service="kernel",
                correlation_id=f"kernel_start_{datetime.utcnow().timestamp()}",
                payload={
                    "kernel_name": self._config.name,
                    "kernel_version": self._config.version,
                    "services_started": list(self._services.keys()),
                },
            )
        )

        self._running = True
        self._start_time = datetime.utcnow()

        logger.info("Hermes Kernel started successfully")

    async def stop(self) -> None:
        """Stop the kernel and all services."""
        if not self._running:
            logger.warning("Kernel not running")
            return

        logger.info("Stopping Hermes Kernel...")

        # Stop services
        await self._stop_services()

        # StructuredLogger shutdown (Phase S3 — FIRST Core Component to shut
        # down, §3.7.4). Flushes remaining logs before other components (the
        # EventBus, which drains last in S0) are torn down. The kernel owns the
        # lifecycle; no LifecycleManager is invented.
        await self._shutdown_structured_logger()

        # Emit kernel stopped event
        if self._event_bus:
            self._event_bus.publish(
                KernelStopped(
                    source_service="kernel",
                    correlation_id=f"kernel_stop_{datetime.utcnow().timestamp()}",
                    payload={
                        "kernel_name": self._config.name,
                        "uptime_seconds": (
                            datetime.utcnow() - self._start_time
                        ).total_seconds()
                        if self._start_time
                        else 0,
                    },
                )
            )

        # Shutdown event bus
        if self._event_bus:
            self._event_bus.shutdown()

        self._running = False

        logger.info("Hermes Kernel stopped")

    async def _init_core_components(self) -> None:
        """Initialize all core components."""
        logger.debug("Initializing core components...")

        # Event Bus - the Kernel owns the SINGLE global bus. Every manager
        # below calls get_event_bus() at construction, so they must be created
        # AFTER we publish the bus as the global singleton. Otherwise they
        # would bind to a different bus and events would never cross.
        self._event_bus = EventBus(max_history=self._config.event_bus_max_history)
        set_event_bus(self._event_bus)
        await self._event_bus.start()

        # ConfigurationManager (C3, Phase 2) — depends on EventBus (§3.5).
        # Constructed and owned by the kernel; set as the global singleton so
        # other components resolve the SAME instance. Loads + merges the four
        # configuration layers and validates schema during initialize(), then
        # is frozen at the Phase 2->3 boundary below (INV-CM-FRZ-001/002).
        self._configuration = get_configuration_manager(
            event_bus=self._event_bus,
            config_path=self._config.config_path,
        )
        set_configuration_manager(self._configuration)
        await self._configuration.initialize()
        # Phase 2 -> 3 freeze boundary: freeze configuration before any Core
        # Manager (Phase 4+) or Service (Phase 9+) can read it. This is the
        # existing repository's freeze hook; no LifecycleManager is invented.
        self._configuration.freeze()

        # StructuredLogger (C4, Phase 3 — last Core Component, §3.6 / §3.7.3).
        # Depends on EventBus, ServiceRegistry (constructed below), and the now
        # frozen ConfigurationManager. Constructed and owned exclusively by the
        # kernel; set as the global singleton so every component resolves the
        # same instance. Initializes after the ConfigurationManager freeze
        # (INV-CC-INIT-003 / INV-CC-LC-005). ServiceRegistry is constructed
        # during _init_service_registry (Phase 1 in the architecture); we inject
        # the already-built EventBus + ConfigurationManager here and let the
        # logger resolve ServiceRegistry lazily via the kernel accessor.
        self._structured_logger = get_logger()
        set_logger(self._structured_logger)
        await self._structured_logger.initialize(self)

        # State Manager
        self._state_manager = StateManager(
            persistence_path=self._config.data_dir / "state"
        )
        set_state_manager(self._state_manager)

        # Workflow Manager (shares state_manager + event bus)
        self._workflow_manager = WorkflowManager(self._state_manager)
        set_workflow_manager(self._workflow_manager)

        # Resource Manager
        self._resource_manager = ResourceManager()
        set_resource_manager(self._resource_manager)

        logger.debug("Core components initialized")

    async def _shutdown_structured_logger(self) -> None:
        """Shut down the StructuredLogger Core Component (Phase S3, §3.7.4)."""
        sl = self._structured_logger
        if sl is None:
            return
        try:
            await sl.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down StructuredLogger: {e}")
        finally:
            self._structured_logger = None

    async def _init_service_registry(self) -> None:
        """Initialize the Service Registry and register it as global singleton."""
        logger.debug("Initializing Service Registry...")
        self._service_registry = ServiceRegistry(self._event_bus)
        set_service_registry(self._service_registry)
        logger.debug("Service Registry initialized")

    async def _start_services(self) -> None:
        """Start all registered services."""
        logger.debug("Starting services...")

        # Start core services first
        services = [
            ("event_bus", self._start_event_bus),
            ("state_manager", self._start_state_manager),
            ("workflow_manager", self._start_workflow_manager),
            ("resource_manager", self._start_resource_manager),
        ]

        for name, start_func in services:
            try:
                await start_func()
                self._services[name] = ServiceStatus(
                    name=name,
                    started=True,
                    started_at=datetime.utcnow(),
                )
                logger.debug(f"Started service: {name}")
            except Exception as e:
                logger.error(f"Failed to start service {name}: {e}")
                self._services[name] = ServiceStatus(
                    name=name,
                    started=False,
                    healthy=False,
                    last_error=str(e),
                )

        # Start Engineering Services via Service Registry
        if self._service_registry:
            results = await self._service_registry.start_all()
            for name, success in results.items():
                status = ServiceStatus(
                    name=name,
                    started=success,
                    healthy=success,
                    started_at=datetime.utcnow() if success else None,
                )
                self._services[name] = status
                if success:
                    logger.debug(f"Started Engineering Service: {name}")
                else:
                    logger.error(f"Failed to start Engineering Service: {name}")

    async def _stop_services(self) -> None:
        """Stop all running services."""
        logger.debug("Stopping services...")

        # Stop in reverse order
        stop_order = [
            "resource_manager",
            "workflow_manager",
            "state_manager",
            "event_bus",
        ]

        for name in stop_order:
            if name in self._services and self._services[name].started:
                try:
                    stop_func = getattr(self, f"_stop_{name}", None)
                    if stop_func:
                        await stop_func()
                    self._services[name].started = False
                    logger.debug(f"Stopped service: {name}")
                except Exception as e:
                    logger.error(f"Error stopping service {name}: {e}")

    # Service start/stop methods
    async def _start_event_bus(self) -> None:
        pass  # Already started in init

    async def _start_state_manager(self) -> None:
        self._state_manager.load_persisted_snapshots()

    async def _start_workflow_manager(self) -> None:
        pass

    async def _start_resource_manager(self) -> None:
        self._resource_manager.start_cleanup_task()

    async def _stop_event_bus(self) -> None:
        if self._event_bus:
            self._event_bus.shutdown()

    async def _stop_resource_manager(self) -> None:
        self._resource_manager.stop_cleanup_task()

    def get_service_status(self) -> dict[str, Any]:
        """Get status of all services."""
        return {
            name: {
                "started": status.started,
                "healthy": status.healthy,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "last_error": status.last_error,
            }
            for name, status in self._services.items()
       }

    def get_stats(self) -> dict[str, Any]:
        """Get kernel statistics."""
        statuses = self.get_service_status()
        total_services = len(statuses)
        healthy_services = sum(1 for s in statuses.values() if s.get("started") and s.get("healthy"))
        uptime = (
            (datetime.utcnow() - self._start_time).total_seconds()
            if self._start_time
            else 0
       )
        return {
           "kernel": {
                "name": self._config.name,
                "version": self._config.version,
                "running": self._running,
                "start_time": self._start_time.isoformat() if self._start_time else None,
                "uptime_seconds": uptime,
                "services": total_services,
                "healthy_services": healthy_services,
            },
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "services": statuses,
            "service_count": total_services,
            "healthy_services": healthy_services,
            "event_bus": self._event_bus.get_stats() if self._event_bus else None,
            "resource_manager": (
                self._resource_manager.get_stats() if self._resource_manager else None
            ),
       }


# Global kernel instance
_global_kernel: HermesKernel | None = None


def get_kernel() -> HermesKernel | None:
    """Get the global kernel instance."""
    return _global_kernel


def set_kernel(kernel: HermesKernel) -> None:
    """Set the global kernel instance."""
    global _global_kernel
    _global_kernel = kernel


async def create_kernel(
    config: KernelConfig | None = None,
    app_config: AppConfig | None = None,
) -> HermesKernel:
    """Create a kernel instance."""
    return HermesKernel(config=config, app_config=app_config)


__all__ = [
    "HermesKernel",
    "KernelConfig",
    "ServiceStatus",
    "get_kernel",
    "set_kernel",
    "create_kernel",
]
