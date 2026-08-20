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

# Kernel uses CANONICAL Core Components (Task 5/6/7/8 — single authority per process)
from aios.events.core.bus import (
    EventBus as CoreEventBus,
    EventBusConfig,
    reset_event_bus_singleton as reset_core_event_bus_singleton,
)
from aios.core.service_registry import (
    ServiceRegistry as CoreServiceRegistry,
    get_service_registry as get_core_service_registry,
    reset_service_registry_singleton as reset_core_service_registry_singleton,
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
# Task 9 — LifecycleManager (first Core Manager, Part 4 §4.3). Minimal kernel
# integration: the kernel owns its construction/integration so LifecycleManager
# (which is NOT a Core Component) can drive the kernel lifecycle state machine.
# The kernel retains ownership of EventBus / StructuredLogger shutdown order
# (§3.7.4) and does NOT delegate Core Component teardown to LifecycleManager.
from aios.core.lifecycle_manager import (
    LifecycleManager,
    get_lifecycle_manager,
    set_lifecycle_manager,
    reset_lifecycle_manager_singleton,
)
# Managers (these use canonical EventBus / ServiceRegistry via global singletons)
from aios.core.state import StateManager, get_state_manager, set_state_manager
from aios.core.storage import (
    StorageManager,
    get_storage_manager,
    set_storage_manager,
)
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
# Task 12 — HealthManager (Phase-3 Governance Core Manager). Constructed in
# _init_core_components(); LifecycleManager (constructed in _init_lifecycle_manager)
# drives its initialize()/shutdown() via Phase-3 phase topology. It is NOT added
# to _start_services/_stop_engineering_services (same-phase sibling of
# ResourceManager; alphabetical ordering within Phase 3 is deterministic).
from aios.core.health_manager import (
    HealthManager,
    get_health_manager,
    set_health_manager,
)
# Engineering services use the canonical ServiceRegistry
from aios.services.base import BaseService
from aios.events.core.types import EventType

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
    - Event Bus for inter-service communication (CANONICAL C1)
    - Service Registry for core services (CANONICAL C2)
    - Configuration Manager (C3)
    - Structured Logger (C4)
    - State Manager for workflow/application state
    - Workflow Manager for DAG-based workflows
    - Resource Manager for quotas
    - Lifecycle Manager (first Core Manager)
    - Engineering Services (registered in canonical C2)
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

        # Core Components (C1–C4) — CANONICAL AUTHORITIES (single instance per process)
        self._event_bus: CoreEventBus | None = None          # C1 — canonical EventBus (Task 5)
        self._service_registry: CoreServiceRegistry | None = None  # C2 — canonical ServiceRegistry (Task 6)
        self._configuration: ConfigurationManager | None = None   # C3 — ConfigurationManager (Task 7)
        self._structured_logger: StructuredLogger | None = None   # C4 — StructuredLogger (Task 8)

        # Core Manager (Task 9)
        self._lifecycle: LifecycleManager | None = None

        # Managers (constructed after C1–C4, use canonical singletons)
        self._state_manager: StateManager | None = None
        self._storage_manager: StorageManager | None = None
        self._workflow_manager: WorkflowManager | None = None
        self._resource_manager: ResourceManager | None = None
        self._health_manager: HealthManager | None = None

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
    def event_bus(self) -> CoreEventBus | None:
        """Get the CANONICAL EventBus (C1 — Task 5 authoritative implementation)."""
        return self._event_bus

    @property
    def state_manager(self) -> StateManager | None:
        """Get state manager."""
        return self._state_manager

    @property
    def storage_manager(self) -> StorageManager | None:
        """Get the StorageManager Core Manager (Part 4 §4.5, Task 11)."""
        return self._storage_manager

    @property
    def workflow_manager(self) -> WorkflowManager | None:
        """Get workflow manager."""
        return self._workflow_manager

    @property
    def resource_manager(self) -> ResourceManager | None:
        """Get resource manager."""
        return self._resource_manager

    @property
    def health_manager(self) -> HealthManager | None:
        """Get the HealthManager Core Manager (Part 4 §4.6, Task 12)."""
        return self._health_manager

    @property
    def configuration(self) -> ConfigurationManager | None:
        """Get the ConfigurationManager Core Component (C3, Part 3 §3.5)."""
        return self._configuration

    @property
    def service_registry(self) -> CoreServiceRegistry | None:
        """Get the CANONICAL ServiceRegistry (C2 — Task 6 authoritative implementation)."""
        return self._service_registry

    @property
    def logger(self) -> StructuredLogger | None:
        """Get the StructuredLogger Core Component (C4, Part 3 §3.6)."""
        return self._structured_logger

    @property
    def lifecycle(self) -> LifecycleManager | None:
        """Get the LifecycleManager Core Manager (Part 4 §4.3, Task 9)."""
        return self._lifecycle

    def register_service(self, service: BaseService) -> BaseService:
        """Register an Engineering Service with the kernel (canonical C2 registry).

        Synchronous, preserving the pre-Task-9 public contract: before the kernel
        is started (registry not yet initialized) this raises ``RuntimeError``
        immediately; after initialization it registers through the canonical
        ServiceRegistry. The canonical ``register`` is a coroutine (Core Component
        pattern), so it is driven to completion via :func:`_run_sync`.
        """
        if self._service_registry:
            # Register using canonical ServiceRegistry with proper namespacing.
            from aios.core.service_registry import ServiceType
            _run_sync(
                self._service_registry.register(
                    service,
                    service_id=f"engineering.{service.name}",
                    service_type=ServiceType.ENGINEERING,
                    metadata={"version": service.version, "description": service.description},
                )
            )
            logger.debug(f"Registered engineering service '{service.name}' in canonical registry")
            return service
        raise RuntimeError("Canonical service registry not initialized. Start kernel first.")

    def get_service(self, name: str) -> BaseService:
        """Get a registered Engineering Service (canonical C2 registry)."""
        if self._service_registry:
            # Look up by namespaced ID
            svc = self._service_registry.get_service(f"engineering.{name}")
            if svc is not None:
                return svc
        raise RuntimeError(f"Engineering service '{name}' not found or registry not initialized")

    async def start(self) -> None:
        """Start the kernel and all core services."""
        if self._running:
            logger.warning("Kernel already running")
            return

        logger.info("Starting Hermes Kernel...")

        # Initialize core components (canonical C1–C4)
        await self._init_core_components()

        # Task 9 — construct + integrate the LifecycleManager Core Manager
        # (Part 4 §4.3). It is the authoritative kernel-lifecycle state machine.
        # Phase-1 wiring only; later managers are registered as they land (Tasks 10+).
        # The kernel retains ownership of Core Component shutdown order.
        await self._init_lifecycle_manager()

        # Start services if enabled
        if self._config.auto_start_services:
            await self._start_services()

        # Emit kernel started event using canonical C1 EventBus
        # Map KernelStarted -> KERNEL_READY (canonical EventType)
        if self._event_bus:
            from aios.events.core.identity import ComponentIdentity, ComponentType
            from aios.events.core.event import Event
            from aios.events.core.types import SemanticVersion

            kernel_identity = ComponentIdentity(
                component_type=ComponentType.CORE_COMPONENT,
                component_name="HermesKernel",
                version=SemanticVersion(0, 1, 0),
            )

            event = Event(
                eventType=EventType.KERNEL_READY,
                source=kernel_identity,
                correlationId=__import__('uuid').uuid4(),
                payload={
                    "kernel_name": self._config.name,
                    "kernel_version": self._config.version,
                    "services_started": list(self._services.keys()),
                },
            )
            await self._event_bus.publish(event)

        self._running = True
        self._start_time = datetime.utcnow()

        logger.info("Hermes Kernel started successfully")

    async def stop(self) -> None:
        """Stop the kernel and all services."""
        if not self._running:
            logger.warning("Kernel not running")
            return

        logger.info("Stopping Hermes Kernel...")

        # Stop engineering services via LifecycleManager / canonical C2
        await self._stop_engineering_services()

        # Task 9 — drive the LifecycleManager to TERMINATED (kernel lifecycle
        # authority). LifecycleManager does NOT shut down C1–C4; the kernel owns
        # those teardown orderings (§3.7.4). This only finalizes lifecycle state
        # so StructuredLogger can still log the transition.
        await self._shutdown_lifecycle_manager()

        # StructuredLogger shutdown (Phase S3 — FIRST Core Component to shut
        # down, §3.7.4). Flushes remaining logs before other components (the
        # EventBus, which drains last in S0) are torn down.
        await self._shutdown_structured_logger()

        # Emit kernel stopped event using canonical C1 EventBus
        # Map KernelStopped -> KERNEL_SHUTDOWN_STARTED (canonical EventType)
        if self._event_bus:
            from aios.events.core.identity import ComponentIdentity, ComponentType
            from aios.events.core.event import Event
            from aios.events.core.types import SemanticVersion

            kernel_identity = ComponentIdentity(
                component_type=ComponentType.CORE_COMPONENT,
                component_name="HermesKernel",
                version=SemanticVersion(0, 1, 0),
            )

            event = Event(
                eventType=EventType.KERNEL_SHUTDOWN_STARTED,
                source=kernel_identity,
                correlationId=__import__('uuid').uuid4(),
                payload={
                    "kernel_name": self._config.name,
                    "uptime_seconds": (
                        datetime.utcnow() - self._start_time
                    ).total_seconds()
                    if self._start_time
                    else 0,
                },
            )
            await self._event_bus.publish(event)

        # Shutdown canonical EventBus (async await) - LAST per shutdown order
        if self._event_bus:
            await self._event_bus.shutdown()

        self._running = False

        logger.info("Hermes Kernel stopped")

    async def _init_core_components(self) -> None:
        """Initialize all canonical Core Components (C1–C4)."""
        logger.debug("Initializing canonical core components...")

        # C1: Canonical EventBus (Task 5) — exactly one per process (INV-EB-001)
        # Must be RUNNING before any component that publishes to it.
        reset_core_event_bus_singleton()
        self._event_bus = CoreEventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        await self._event_bus.initialize()

        # C2: Canonical ServiceRegistry (Phase 1) — depends on canonical EventBus
        reset_core_service_registry_singleton()
        self._service_registry = get_core_service_registry(event_bus=self._event_bus)

        # C3: ConfigurationManager (Phase 2) — depends on canonical EventBus
        self._configuration = get_configuration_manager(
            event_bus=self._event_bus,
            config_path=self._config.config_path,
        )
        set_configuration_manager(self._configuration)
        await self._configuration.initialize()
        # Phase 2 -> 3 freeze boundary: freeze configuration before any Core
        # Manager (Phase 4+) or Service (Phase 9+) can read it.
        self._configuration.freeze()

        # C4: StructuredLogger (Phase 3 — last Core Component, §3.6 / §3.7.3).
        # Depends on canonical EventBus, canonical ServiceRegistry (lazy via kernel),
        # and frozen ConfigurationManager.
        self._structured_logger = get_logger()
        set_logger(self._structured_logger)
        await self._structured_logger.initialize(self)

        # Managers (constructed after C1–C4, use canonical singletons).
        # Task 10 — StateManager is a Phase-2 Core Manager; it receives the
        # canonical C2/C3/C4 refs via DI so its initialize() can register with
        # ServiceRegistry, read frozen ConfigurationManager, and log through
        # StructuredLogger. LifecycleManager (constructed next) will register
        # and drive it.
        self._state_manager = StateManager(
            persistence_path=self._config.data_dir / "state",
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_state_manager(self._state_manager)

        # Task 11 — StorageManager is a Phase-2 Core Manager (Part 4 §4.5, "State &
        # Storage" phase, alongside StateManager). It receives the canonical
        # C2/C3/C4 refs via DI so its initialize() can register with
        # ServiceRegistry, read frozen ConfigurationManager, and log through
        # StructuredLogger. LifecycleManager (constructed next) will register and
        # drive it. Per the Phase Dependency Rule, StorageManager does NOT declare
        # StateManager as a formal dependency — deterministic alphabetical ordering
        # within Phase 2 (StateManager before StorageManager) guarantees correct
        # sequencing, and their operational coordination is event-driven (EventBus),
        # not a lifecycle dependency edge.
        self._storage_manager = StorageManager(
            persistence_path=self._config.data_dir / "storage",
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_storage_manager(self._storage_manager)

        self._workflow_manager = WorkflowManager(self._state_manager)
        set_workflow_manager(self._workflow_manager)

        # Task 13 — ResourceManager is a Phase-3 (Governance) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.resource``, read frozen
        # ConfigurationManager (``kernel.resource.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register
        # and drive it. Per the Phase Dependency Rule, ResourceManager does NOT
        # declare HealthManager or SecurityManager as formal dependencies —
        # deterministic alphabetical ordering within Phase 3 (HealthManager,
        # ResourceManager, SecurityManager) guarantees correct sequencing.
        self._resource_manager = ResourceManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_resource_manager(self._resource_manager)

        # Task 12 — HealthManager is a Phase-3 (Governance) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.health``, read frozen
        # ConfigurationManager (``kernel.health.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register
        # and drive it. Per the Phase Dependency Rule, HealthManager does NOT
        # declare ResourceManager or SecurityManager as formal dependencies —
        # deterministic alphabetical ordering within Phase 3 (HealthManager,
        # ResourceManager, SecurityManager) guarantees correct sequencing.
        self._health_manager = HealthManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_health_manager(self._health_manager)

        logger.debug("Canonical core components initialized")

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

    async def _shutdown_lifecycle_manager(self) -> None:
        """Task 9 — finalize the LifecycleManager lifecycle state.

        Drives the LifecycleManager to TERMINATED. It does NOT shut down the Core
        Components (C1–C4); the kernel owns those teardown orderings (§3.7.4).
        Errors are logged and swallowed (lifecycle teardown must not block kernel
        shutdown), matching the StructuredLogger-shutdown precedent.
        """
        lm = self._lifecycle
        if lm is None:
            return
        try:
            await lm.shutdown()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error shutting down LifecycleManager: {e}")
        finally:
            self._lifecycle = None

    async def _init_lifecycle_manager(self) -> None:
        """Task 9 — construct + integrate the LifecycleManager Core Manager.

        Builds the LifecycleManager wired to the four Core Components (C1–C4),
        registers it with the canonical ServiceRegistry (as ``core.lifecycle``),
        sets the global singleton, and drives initialization to OPERATIONAL.
        Later Core Managers are registered with ``lifecycle.register_manager``
        as they are implemented in subsequent tasks.

        The kernel owns Core Component shutdown order (§3.7.4); LifecycleManager
        is the lifecycle *authority* but does not tear down C1–C4 here.
        """
        logger.debug("Initializing LifecycleManager (Task 9)...")

        reset_lifecycle_manager_singleton()
        lm = get_lifecycle_manager(
            event_bus=self._event_bus,              # Canonical C1
            service_registry=self._service_registry,  # Canonical C2
            configuration_manager=self._configuration,  # C3
            logger=self._structured_logger,           # C4 (already initialized)
            kernel=self,
        )
        set_lifecycle_manager(lm)
        self._lifecycle = lm
        await lm.register_with_service_registry()

        # Task 10 — register the StateManager Core Manager (Phase 2, "State &
        # Storage") for LifecycleManager orchestration. StateManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's phase topology, NOT by the engineering
        # service start/stop loops.
        if self._state_manager is not None:
            lm.register_manager(self._state_manager)
            logger.debug("Registered StateManager with LifecycleManager (Phase 2).")

        # Task 11 — register the StorageManager Core Manager (Phase 2, "State &
        # Storage") for LifecycleManager orchestration. StorageManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's phase topology, NOT by the engineering
        # service start/stop loops. Phase-2 ordering is deterministic (alphabetical:
        # StateManager before StorageManager).
        if self._storage_manager is not None:
            lm.register_manager(self._storage_manager)
            logger.debug("Registered StorageManager with LifecycleManager (Phase 2).")

        # Task 12 — register the HealthManager Core Manager (Phase 3, "Governance")
        # for LifecycleManager orchestration. HealthManager was constructed in
        # _init_core_components(); its initialize()/shutdown() are driven by
        # LifecycleManager's Phase-3 phase topology, NOT by the engineering service
        # start/stop loops. Phase-3 ordering is deterministic (alphabetical:
        # HealthManager, ResourceManager, SecurityManager).
        if self._health_manager is not None:
            lm.register_manager(self._health_manager)
            logger.debug("Registered HealthManager with LifecycleManager (Phase 3).")

        # Task 13 — register the ResourceManager Core Manager (Phase 3,
        # "Governance") for LifecycleManager orchestration. ResourceManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's Phase-3 phase topology, NOT by the
        # engineering service start/stop loops (only its background cleanup task
        # is started/stopped by the engineering-service hooks for backward
        # compatibility). Phase-3 ordering is deterministic (alphabetical:
        # HealthManager, ResourceManager, SecurityManager).
        if self._resource_manager is not None:
            lm.register_manager(self._resource_manager)
            logger.debug("Registered ResourceManager with LifecycleManager (Phase 3).")

        try:
            await lm.initialize()
        except Exception as exc:  # noqa: BLE001
            # Initialization coordinated rollback internally; surface clearly.
            logger.error(f"LifecycleManager initialization failed: {exc}")
            raise
        logger.debug("LifecycleManager initialized -> OPERATIONAL")

    async def _start_services(self) -> None:
        """Start all registered services."""
        logger.debug("Starting services...")

        # Start core services first (canonical managers). NOTE: StateManager is
        # NOT started here — as a Phase-2 Core Manager (Task 10) its lifecycle is
        # owned by LifecycleManager (initialized during Phase 2, shut down in
        # reverse phase order). It is thus excluded from the engineering-service
        # startup path per the Core Manager topology (Part 4 §4.2.3).
        services = [
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

        # Start Engineering Services via canonical C2 ServiceRegistry.
        #
        # Engineering services are registered under the reserved ``engineering.``
        # namespace prefix (Part 3 §3.4.8, INV-SR-NS-001 / INV-SR-NS-002). Core
        # Components / Core Managers are ALSO visible through the canonical
        # registry (they share the ``ServiceType.ENGINEERING`` classification
        # envelope so they remain discoverable there), but their lifecycle is
        # owned by the dedicated lifecycle/phase mechanism — NOT by the
        # engineering service start/stop loops. We therefore filter the
        # ENGINEERING-typed listing by the kernel's own canonical service-id
        # convention (``engineering.<name>``, see ``register_service``): an entry
        # that is not present under that id (e.g. ``core.lifecycle``) is a Core
        # Component / Core Manager and is left to its dedicated lifecycle path.
        if self._service_registry:
            from aios.core.service_registry import ServiceType

            engineering_services = [
                svc
                for svc in self._service_registry.get_services_by_type(
                    ServiceType.ENGINEERING
                )
                if self._service_registry.get_registration(
                    f"engineering.{svc.name}"
                )
                is not None
            ]

            # Start each engineering service
            for svc in engineering_services:
                try:
                    await svc.start()
                    self._services[svc.name] = ServiceStatus(
                        name=svc.name,
                        started=True,
                        healthy=True,
                        started_at=datetime.utcnow(),
                    )
                    # Mark as RUNNING in canonical registry
                    await self._service_registry.mark_service_running(f"engineering.{svc.name}")
                    logger.debug(f"Started Engineering Service: {svc.name}")
                except Exception as e:
                    self._services[svc.name] = ServiceStatus(
                        name=svc.name,
                        started=False,
                        healthy=False,
                        last_error=str(e),
                    )
                    logger.error(f"Failed to start Engineering Service: {svc.name}: {e}")

    async def _stop_services(self) -> None:
        """Stop core services in reverse order."""
        logger.debug("Stopping core services...")

        stop_order = [
            "resource_manager",
            "workflow_manager",
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

    async def _stop_engineering_services(self) -> None:
        """Stop all engineering services via canonical registry.

        Symmetric to :meth:`_start_services`: only entries with the canonical
        ``engineering.`` namespace prefix (``Part 3 §3.4.8``,
        ``INV-SR-NS-001``) are stopped — Core Components / Core Managers are
        NOT touched here. Lifecycle for those is owned by the dedicated
        lifecycle/phase mechanism.
        """
        logger.debug("Stopping engineering services...")
        if self._service_registry:
            from aios.core.service_registry import ServiceType

            # Same discriminator as ``_start_services``: only entries present
            # under the canonical ``engineering.<name>`` service-id are stopped.
            # Core Components / Core Managers (e.g. ``core.lifecycle``) are not
            # touched here — their lifecycle is owned by the dedicated
            # lifecycle/phase mechanism.
            engineering_services = [
                svc
                for svc in self._service_registry.get_services_by_type(
                    ServiceType.ENGINEERING
                )
                if self._service_registry.get_registration(
                    f"engineering.{svc.name}"
                )
                is not None
            ]

            for svc in engineering_services:
                try:
                    await svc.stop()
                    # Mark as SHUTDOWN in canonical registry
                    await self._service_registry.mark_service_shutdown(f"engineering.{svc.name}")
                    logger.debug(f"Stopped Engineering Service: {svc.name}")
                except Exception as e:
                    logger.error(f"Error stopping engineering service {svc.name}: {e}")

    # Service start/stop methods
    async def _start_workflow_manager(self) -> None:
        pass

    async def _start_resource_manager(self) -> None:
        self._resource_manager.start_cleanup_task()

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
            "service_registry": self._service_registry.get_stats() if self._service_registry else None,
            "resource_manager": (
                self._resource_manager.get_stats() if self._resource_manager else None
            ),
       }


def _run_sync(coro: Any) -> Any:
    """Run a coroutine to completion from a synchronous call site.

    The canonical Core Components (EventBus, ServiceRegistry, ...) expose async
    lifecycle/registration methods (Core Component pattern). The kernel's public
    ``register_service`` is synchronous (pre-Task-9 contract), so the canonical
    coroutine is bridged here — same approach as the Task 6 legacy compatibility
    layer (``aios/services/registry.py:_run_sync``). If a loop is already running
    in this thread (e.g. an async test), the coroutine is driven on a dedicated
    thread with its own loop so it still completes synchronously from the
    caller's perspective.
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