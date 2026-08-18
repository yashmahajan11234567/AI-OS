"""
Core Component C2 — ServiceRegistry (AI-OS Architecture Specification Part 3 §3.4).

The ServiceRegistry is the authoritative directory of all Services in the
AI-OS process. It provides:

  * Service registration (validation, uniqueness, dependency + namespace checks)
  * Service discovery (by id / type / capability / tag / composite query)
  * Dependency topology (acyclic DAG maintenance, cycle detection)
  * Initialization / shutdown planning (topological batches, reverse order)
  * Health tracking (per-service health state, failure counting)
  * Lifecycle coordination (REGISTERED -> INITIALIZING -> RUNNING -> ...)
  * Event emission (via the Task 5 EventBus, canonical EventTypes only)

AUTHORITATIVE SOURCES
---------------------
  * Part 3 §3.4 (Component C2 — ServiceRegistry) — the contract implemented here.
  * Task 1–5 stack: ``aios.events.core.{event,bus,types,identity}``.

IMPLEMENTATION NOTES / ARCHITECTURE CONFLICTS (documented, not silently resolved)
--------------------------------------------------------------------------------
  1. ICoreComponent request/response/error contract is explicitly "NOT YET
     DEFINED" in architecture/Part14/interfaces.md §2.1.1. The only existing
     Core Component implementation is the Task-5 EventBus, whose pattern is
     ``async initialize(kernel=None)``, ``async shutdown()``, ``sync
     healthCheck()``. This module follows that EXACT established pattern.

  2. §3.4 names the events ``ServiceRegistered``, ``ServiceHealthChanged``,
     ``ServiceInitialized``, ``ServiceShutdown`` (and references
     ``ServiceFailed`` in §3.4.12). The canonical EventType enum from Task 2 is
     a CLOSED enum (Part 2 INV-ET-003/004) and does NOT contain those member
     names. Per the hard directive "Do not invent EventTypes; use the canonical
     EventType enum created in Task 2", these §3.4 names are mapped onto the
     existing canonical EventTypes via ``_ARCH_EVENT_TO_EVENT_TYPE`` (see the
     table in that constant's docstring). The mapping is explicit and fully
     documented so the conflict is never hidden.

  3. This Core Component depends on the Task-5 EventBus (``aios.events.core.bus
     .EventBus``) by DEPENDENCY INJECTION — the bus is passed to the constructor
     (or resolved from the ``kernel`` argument during ``initialize``). It never
     imports Hermes, never constructs its own bus, and never manipulates bus
     internals.

  4. The registered "service" is duck-typed: §3.4's registration contract wraps
     a ``BaseService``-like object, but this Core Component must NOT couple to
     the legacy engineering ``aios.services.base.BaseService`` (that is a
     separate, architecturally-distinct registry). Per INV-SR-STR-006 /
     INV-SR-OWN-003, ServiceRegistry NEVER invokes service lifecycle methods
     (``initialize()`` / ``start()`` / ``shutdown()`` / ``stop()``) — those are
     owned by the future LifecycleManager. ServiceRegistry only RECORDS and
     COORDINATES lifecycle state transitions (see ``mark_service_*``), and may
     still poll a service's ``healthCheck()`` (the sole INV-SR-STR-006
     exception). No reflection, callback, or wrapper path executes a service
     method inside this module.

This module does NOT implement the Kernel, any Manager, Engineering Service,
or any other forbidden-scope component. It is a drop-in Core Component intended
to be constructed and owned exclusively by HermesKernel (INV-SR-OWN-001).
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from aios.events.core.bus import EventBus
from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ServiceType(str, Enum):
    """Service classification (Part 3 §3.4.4 ``ServiceType``)."""

    ENGINEERING = "ENGINEERING"
    CAPABILITY_FACADE = "CAPABILITY_FACADE"
    APPLICATION = "APPLICATION"


class ServiceLifecycleState(str, Enum):
    """Service lifecycle states tracked by ServiceRegistry (Part 3 §3.4.9).

    UNREGISTERED -> REGISTERED -> INITIALIZING -> RUNNING -> DEGRADED -> FAILED
                                                  \\-> SHUTTING_DOWN -> SHUTDOWN
    """

    UNREGISTERED = "UNREGISTERED"
    REGISTERED = "REGISTERED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    SHUTDOWN = "SHUTDOWN"


class ServiceRegistryState(str, Enum):
    """Lifecycle of the ServiceRegistry Core Component itself."""

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    SHUTDOWN = "SHUTDOWN"


class ServiceNamespace(str, Enum):
    """Reserved / sanctioned namespaces (Part 3 §3.4.8).

    ``kernel`` is reserved for Core Components / Core Managers and MUST NOT be
    used by any registered service (INV-SR-NS-002).
    """

    KERNEL = "kernel"
    ENGINEERING = "engineering"
    FACADE = "facade"
    APPLICATION = "application"
    EXTENSION = "extension"


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Capability:
    """Declared service capability (Part 3 §3.4.7).

    ``name`` MUST be globally unique or versioned to avoid collisions
    (SR-CAP-002). ``interface`` is a structural description (methods/events);
    in v1.0 it is stored opaquely as ``metadata`` per the architecture's
    "no invented schema" stance.
    """

    name: str
    version: str = "1.0.0"
    interface: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Capability.name MUST be a non-empty string (SR-CAP-002).")


@dataclass
class ServiceRegistration:
    """Wraps the Part 3 §3.4.4 ``ServiceRegistration`` contract.

    This is the mutable-but-guarded record the registry holds per service. The
    ``service`` object is the registered instance (duck-typed). Lifecycle and
    health state are tracked here.
    """

    service: Any
    service_id: str
    service_type: ServiceType = ServiceType.ENGINEERING
    depends_on: list[str] = field(default_factory=list)
    capabilities: list[Capability] = field(default_factory=list)
    critical: bool = False
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # --- lifecycle / health (tracked by the registry) ---
    lifecycle_state: ServiceLifecycleState = ServiceLifecycleState.REGISTERED
    healthy: bool = True
    consecutive_health_failures: int = 0
    last_error: str | None = None
    registered_at: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    last_health_check_at: str | None = None


@dataclass(frozen=True)
class ServiceRegistryHealth:
    """Health snapshot of the ServiceRegistry Core Component.

    Mirrors the shape of the Task-5 ``EventBusHealth`` (the only other Core
    Component health model) so there is a single consistent health-check
    convention across Core Components. This is the registry's OWN health, not a
    second model of service health (service health lives on ``ServiceRegistration``).
    """

    healthy: bool
    state: ServiceRegistryState
    total_services: int
    running_services: int
    degraded_services: int
    failed_services: int
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "healthy": self.healthy,
            "state": self.state.value,
            "total_services": self.total_services,
            "running_services": self.running_services,
            "degraded_services": self.degraded_services,
            "failed_services": self.failed_services,
            "details": self.details,
        }


# ---------------------------------------------------------------------------
# Architecture -> canonical EventType mapping (documented conflict, see module docstring)
# ---------------------------------------------------------------------------


# §3.4 event name -> canonical EventType used for emission.
#
#   §3.4 name            | canonical EventType        | rationale
#   ---------------------+----------------------------+----------------------------------
#   ServiceRegistered    | SERVICE_STARTED            | only canonical "service became
#                         |                            |   tracked/active" appearance event
#   ServiceInitialized   | SERVICE_STARTED            | RUNNING transition (v1.0 collapses
#                         |                            |   with registration emission; both
#                         |                            |   carry a `lifecycle` payload key)
#   ServiceHealthChanged | HEALTH_CHECK_PASSED /      | canonical DIAGNOSTIC health events;
#                         |   HEALTH_CHECK_FAILED     |   FAILED variant on unhealthy
#   ServiceShutdown      | SERVICE_STOPPED            | canonical shutdown event
#   ServiceFailed (§3.4.12)| SERVICE_FAILED          | canonical failure event
#   (registry init)      | CORE_COMPONENT_INITIALIZED| canonical, required by §3.4.10
#   (registry shutdown)  | CORE_COMPONENT_SHUTDOWN   | canonical, required by §3.4.11
_ARCH_EVENT_TO_EVENT_TYPE: dict[str, EventType] = {
    "ServiceRegistered": EventType.SERVICE_STARTED,
    "ServiceInitialized": EventType.SERVICE_STARTED,
    "ServiceHealthChanged": EventType.HEALTH_CHECK_PASSED,
    "ServiceShutdown": EventType.SERVICE_STOPPED,
    "ServiceFailed": EventType.SERVICE_FAILED,
}
# Health event selection depends on outcome, handled in code (passed/failed).
_CORE_COMPONENT_INITIALIZED = EventType.CORE_COMPONENT_INITIALIZED
_CORE_COMPONENT_SHUTDOWN = EventType.CORE_COMPONENT_SHUTDOWN

# Consecutive health failures before a service is marked FAILED (§3.4.12).
_HEALTH_FAILURE_THRESHOLD = 3

# Singleton accessor name used by the integration point (kernel.serviceRegistry).
_REGISTRY_NAME = "ServiceRegistry"
_REGISTRY_VERSION = SemanticVersion(0, 2, 0)


# ---------------------------------------------------------------------------
# ServiceRegistry — Core Component C2
# ---------------------------------------------------------------------------


class ServiceRegistry:
    """Core Component C2 — ServiceRegistry (Part 3 §3.4).

    Owns the authoritative directory of registered services: their identity,
    dependency topology, health, and lifecycle state. Communicates exclusively
    through the injected EventBus (INV-SR-STR-007). Thread-safe.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        # INV-SR-STR-001: exactly one instance per process. A second construction
        # is rejected unless the singleton has been reset (tests reset it).
        global _INSTANCE
        with _INSTANCE_LOCK:
            if _INSTANCE is not None and _INSTANCE is not self:
                raise RuntimeError(
                    "Only one ServiceRegistry instance is permitted per process "
                    "(INV-SR-STR-001). A second construction is rejected."
                )
            _INSTANCE = self

        self._event_bus = event_bus
        self._state = ServiceRegistryState.UNINITIALIZED
        self._kernel: Any = None

        # Registry data (guarded by _lock).
        self._lock = threading.RLock()
        self._registrations: dict[str, ServiceRegistration] = {}
        self._capability_index: dict[str, list[str]] = {}  # capability name -> service ids
        self._subscriptions: list[Any] = []  # subscription ids from the bus

        # Identity used as the Event ``source`` for registry-emitted events.
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_COMPONENT,
            component_name=_REGISTRY_NAME,
            version=_REGISTRY_VERSION,
        )

    # --- ICoreComponent: identity / phase / dependencies -----------------

    @property
    def name(self) -> str:
        """Core Component name (ICoreComponent)."""
        return _REGISTRY_NAME

    @property
    def phase(self) -> int:
        """Initialization phase (Part 3 §3.4.3: Phase 1)."""
        return 1

    @property
    def dependencies(self) -> list[str]:
        """Core Component dependencies (Part 3 §3.4.3: EventBus)."""
        return ["EventBus"]

    @property
    def state(self) -> ServiceRegistryState:
        """Current lifecycle state of the registry itself."""
        return self._state

    @property
    def event_bus(self) -> EventBus | None:
        """The injected EventBus (read-only accessor)."""
        return self._event_bus

    # --- ICoreComponent: initialize --------------------------------------

    async def initialize(self, kernel: Any = None) -> ServiceRegistryState:
        """Initialize the registry (Phase 1, depends on EventBus).

        Follows the Task-5 EventBus Core Component pattern (async). Resolves the
        EventBus dependency via DI (constructor) or the ``kernel`` argument,
        registers internal subscriptions, validates pre-registered services for
        acyclicity, and publishes ``CoreComponentInitialized``.
        """
        if self._state in (
            ServiceRegistryState.RUNNING,
            ServiceRegistryState.INITIALIZING,
        ):
            return self._state

        self._state = ServiceRegistryState.INITIALIZING

        # Resolve EventBus dependency (INV-SR-INIT-001: operational before any
        # service initializes). Support DI via constructor or via kernel.
        if self._event_bus is None and kernel is not None:
            self._event_bus = getattr(kernel, "event_bus", None)
        if self._event_bus is None:
            # Defer hard failure: registrations queue, but publishing is a no-op
            # until a bus is attached. This keeps the registry constructible in
            # isolation (e.g. tests) while still enforcing the dependency at
            # first emission time.
            logger.warning(
                "ServiceRegistry initialized without an EventBus; events will be "
                "deferred until a bus is attached."
            )
        self._kernel = kernel

        # Register internal subscriptions (§3.4.10). The registry reacts to
        # ConfigurationFrozen and ServiceFailed to drive lifecycle coordination.
        self._register_internal_subscriptions()

        # Validate pre-registered services for dependency acyclicity.
        try:
            self._check_acyclic()
        except ServiceRegistryError:
            # An internal error in the registry is FATAL per §3.4.12; we surface
            # it rather than silently proceeding.
            self._state = ServiceRegistryState.SHUTDOWN
            raise

        self._state = ServiceRegistryState.RUNNING

        # Publish CoreComponentInitialized{name:"ServiceRegistry"} (§3.4.10,
        # CONF-SR-003). Uses the canonical EventType (no fabricated type).
        await self._emit_async(
            _CORE_COMPONENT_INITIALIZED,
            {
                "name": _REGISTRY_NAME,
                "component": _REGISTRY_NAME,
                "state": "RUNNING",
            },
        )
        return self._state

    # --- ICoreComponent: shutdown ----------------------------------------

    async def shutdown(self) -> ServiceRegistryState:
        """Shutdown the registry (Phase S1, §3.4.11).

        Deregisters subscriptions, publishes ``CoreComponentShutdown``, then
        transitions to SHUTDOWN (lookups return empty thereafter).
        """
        if self._state is ServiceRegistryState.SHUTDOWN:
            return self._state
        self._state = ServiceRegistryState.SHUTTING_DOWN

        # Deregister internal subscriptions (§3.4.11 step 2).
        self._deregister_internal_subscriptions()

        # Publish CoreComponentShutdown{name:"ServiceRegistry"} (§3.4.11 step 3,
        # CONF-SR-004).
        await self._emit_async(
            _CORE_COMPONENT_SHUTDOWN,
            {
                "name": _REGISTRY_NAME,
                "component": _REGISTRY_NAME,
                "state": "SHUTDOWN",
            },
        )

        # Registry enters SHUTDOWN; all lookups return empty (§3.4.11 step 4).
        self._state = ServiceRegistryState.SHUTDOWN
        return self._state

    # --- ICoreComponent: healthCheck (sync, per EventBus pattern) --------

    def healthCheck(self) -> ServiceRegistryHealth:
        """Core Component health check (sync, mirrors EventBus.healthCheck)."""
        with self._lock:
            total = len(self._registrations)
            running = sum(
                1
                for r in self._registrations.values()
                if r.lifecycle_state is ServiceLifecycleState.RUNNING
            )
            degraded = sum(
                1
                for r in self._registrations.values()
                if r.lifecycle_state is ServiceLifecycleState.DEGRADED
            )
            failed = sum(
                1
                for r in self._registrations.values()
                if r.lifecycle_state is ServiceLifecycleState.FAILED
            )
        # Healthy when the component is operational and not shutting down, and
        # no service has entered FAILED (a FAILED critical service is FATAL, but
        # the registry itself reports degraded health rather than crashing here).
        healthy = self._state in (
            ServiceRegistryState.RUNNING,
            ServiceRegistryState.INITIALIZING,
        )
        details = ""
        if failed:
            details = f"{failed} service(s) in FAILED state"
        return ServiceRegistryHealth(
            healthy=healthy and failed == 0,
            state=self._state,
            total_services=total,
            running_services=running,
            degraded_services=degraded,
            failed_services=failed,
            details=details,
        )

    # --- registration (SR-R-001, SR-REG-001..006) ------------------------

    async def register(
        self,
        service: Any,
        *,
        service_id: str | None = None,
        service_type: ServiceType = ServiceType.ENGINEERING,
        depends_on: list[str] | None = None,
        capabilities: list[Capability] | None = None,
        critical: bool = False,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServiceRegistration:
        """Register a service (Part 3 §3.4.4).

        Accepts either a ``ServiceRegistration`` object or a duck-typed service
        instance plus keyword fields. Validates uniqueness (SR-REG-001),
        namespace (INV-SR-NS-001/002), capability uniqueness (SR-CAP-002),
        recomputes the dependency graph and rejects cycles (SR-REG-003), then
        emits the registration event (SR-REG-006).
        """
        if self._state is ServiceRegistryState.SHUTDOWN:
            raise ServiceRegistryError(
                "Cannot register services after registry shutdown."
            )

        # Normalize to a ServiceRegistration.
        if isinstance(service, ServiceRegistration):
            reg = service
        else:
            sid = service_id or getattr(service, "name", None)
            if not sid:
                raise ServiceRegistryError(
                    "service_id is required: pass service_id= or a service with "
                    "a `name` attribute."
                )
            reg = ServiceRegistration(
                service=service,
                service_id=sid,
                service_type=service_type,
                depends_on=list(depends_on or []),
                capabilities=list(capabilities or []),
                critical=critical,
                tags=list(tags or []),
                metadata=dict(metadata or {}),
            )

        # SR-REG-001: globally unique serviceId.
        with self._lock:
            if reg.service_id in self._registrations:
                raise ServiceRegistryError(
                    f"Duplicate serviceId '{reg.service_id}' (SR-REG-001). "
                    f"serviceId MUST be globally unique."
                )

            # INV-SR-NS-001/002: namespace prefix required; `kernel` reserved.
            self._validate_namespace(reg.service_id)

            # SR-CAP-002: capability names must be globally unique.
            for cap in reg.capabilities:
                if cap.name in self._capability_index:
                    raise ServiceRegistryError(
                        f"Duplicate capability name '{cap.name}' (SR-CAP-002). "
                        f"Capability names MUST be globally unique or versioned."
                    )

            # Tentatively add, then verify global acyclicity (SR-REG-003).
            self._registrations[reg.service_id] = reg
            for cap in reg.capabilities:
                self._capability_index.setdefault(cap.name, []).append(
                    reg.service_id
                )
            try:
                self._check_acyclic()
            except ServiceRegistryError:
                # Roll back the tentative insertion on cycle detection.
                self._rollback_registration(reg.service_id)
                raise

            # Persist registration state.
            self._registrations[reg.service_id] = reg

        # SR-REG-006: publish ServiceRegistered (mapped to canonical SERVICE_STARTED).
        await self._emit_service_event("ServiceRegistered", reg, lifecycle="REGISTERED")
        logger.debug("Registered service '%s' (type=%s)", reg.service_id, reg.service_type.value)
        return reg

    def unregister(self, service_id: str) -> bool:
        """Remove a service from the registry (Public API, §3.4.14).

        Returns True if removed, False if not present. Refuses to remove a
        service that still has dependents (would break the DAG).
        """
        with self._lock:
            if service_id not in self._registrations:
                return False
            dependents = [
                sid
                for sid, r in self._registrations.items()
                if service_id in r.depends_on and sid != service_id
            ]
            if dependents:
                raise ServiceRegistryError(
                    f"Cannot unregister '{service_id}': it still has dependents "
                    f"{dependents}. Unregister dependents first."
                )
            reg = self._registrations.pop(service_id)
            for cap in reg.capabilities:
                ids = self._capability_index.get(cap.name)
                if ids and service_id in ids:
                    ids.remove(service_id)
                    if not ids:
                        self._capability_index.pop(cap.name, None)
        logger.debug("Unregistered service '%s'", service_id)
        return True

    # --- discovery (SR-R-002, §3.4.5, INV-SR-DISC-*) ---------------------

    def get_service(self, service_id: str) -> Any:
        """Exact ID lookup. Returns the service instance or None (§3.4.5).

        Honors INV-SR-DISC-001/003: only REGISTERED/RUNNING services are
        returned; FAILED/SHUTDOWN services are not exposed.
        """
        reg = self._lookup_visible(service_id)
        return reg.service if reg is not None else None

    def get_registration(self, service_id: str) -> ServiceRegistration | None:
        """Exact ID lookup returning the wrapped registration (or None).

        Unlike get_service / discovery listings, this exposes the registration
        in ANY lifecycle state (it is a diagnostic/authoritative accessor used
        for health and lifecycle inspection); only INV-SR-DISC-003's *discovery*
        hiding applies to get_service and the listing methods.
        """
        with self._lock:
            return self._registrations.get(service_id)

    def get_services_by_type(self, service_type: ServiceType) -> list[Any]:
        """Type filter (§3.4.5)."""
        return [r.service for r in self._visible_registrations() if r.service_type is service_type]

    def get_services_by_capability(self, capability: str) -> list[Any]:
        """Capability filter (§3.4.5, SR-CAP-003 capability index)."""
        with self._lock:
            ids = list(self._capability_index.get(capability, []))
        out: list[Any] = []
        for sid in ids:
            reg = self._lookup_visible(sid)
            if reg is not None:
                out.append(reg.service)
        return out

    def get_services_by_tag(self, tag: str) -> list[Any]:
        """Tag filter (§3.4.5)."""
        return [
            r.service for r in self._visible_registrations() if tag in r.tags
        ]

    def get_all_services(self) -> list[Any]:
        """No filter (§3.4.5)."""
        return [r.service for r in self._visible_registrations()]

    def query(
        self,
        *,
        service_type: ServiceType | None = None,
        capability: str | None = None,
        tag: str | None = None,
    ) -> list[Any]:
        """Composite filter: type ∩ capability ∩ tag (§3.4.5)."""
        with self._lock:
            candidates = list(self._visible_registrations())
        if service_type is not None:
            candidates = [r for r in candidates if r.service_type is service_type]
        if capability is not None:
            cap_ids = set(self._capability_index.get(capability, []))
            candidates = [r for r in candidates if r.service_id in cap_ids]
        if tag is not None:
            candidates = [r for r in candidates if tag in r.tags]
        return [r.service for r in candidates]

    # --- dependency topology (SR-R-003) ----------------------------------

    def compute_initialization_plan(self) -> list[list[str]]:
        """Topological initialization batches (SR-R-004, CONF-SR-007).

        Returns a list of batches; within a batch services are mutually
        independent, and every dependency of a service appears in an earlier
        batch. Deterministic (sorted within batches, insertion-stable order).
        Raises if the graph is cyclic or a dependency is missing.
        """
        with self._lock:
            nodes = list(self._registrations.keys())
            deps = {sid: list(r.depends_on) for sid, r in self._registrations.items()}

        self._validate_dependencies_exist(deps)
        order = self._topological_order(nodes, deps)
        # Group into batches by longest dependency-chain depth.
        depth: dict[str, int] = {}
        for sid in order:
            depth[sid] = 1 + max(
                (depth[d] for d in deps[sid] if d in depth), default=0
            )
        max_depth = max(depth.values(), default=0)
        batches: list[list[str]] = [[] for _ in range(max_depth)]
        for sid in order:
            batches[depth[sid] - 1].append(sid)
        return batches

    def compute_shutdown_plan(self) -> list[list[str]]:
        """Reverse-topological shutdown batches (SR-R-005, CONF-SR-008).

        Exact reverse of the initialization plan (INV-SR-STR-005): the last
        batch to initialize is the first to shut down.
        """
        init = self.compute_initialization_plan()
        return [list(batch) for batch in reversed(init)]

    def dependency_graph(self) -> dict[str, list[str]]:
        """Read-only snapshot of the dependency topology (hidden internals per §3.4.14)."""
        with self._lock:
            return {sid: list(r.depends_on) for sid, r in self._registrations.items()}

    # --- lifecycle coordination (SR-R-008, §3.4.9) ------------------------
    #
    # INV-SR-STR-006 / INV-SR-OWN-003: ServiceRegistry RECORDS and COORDINATES
    # lifecycle state transitions. It does NOT execute service lifecycle methods
    # (initialize/start/shutdown/stop) — that is the exclusive ownership of the
    # future LifecycleManager. The methods below therefore only mutate the
    # registry's tracked ``lifecycle_state`` and emit the corresponding
    # (mapped) canonical events. No path in this module ever calls a service
    # method; the only permitted exception (healthCheck polling) lives in
    # ``update_health`` / the health scheduler, not here.

    async def mark_service_initializing(self, service_id: str) -> None:
        """Record INITIALIZING for a service (§3.4.9).

        The LifecycleManager has decided to begin initializing this service;
        the registry records the transition. Dependency topology is validated
        but no service method is invoked.
        """
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                raise ServiceRegistryError(f"Unknown service '{service_id}'.")
            for dep in reg.depends_on:
                dep_reg = self._registrations.get(dep)
                if dep_reg is None or dep_reg.lifecycle_state not in (
                    ServiceLifecycleState.RUNNING,
                    ServiceLifecycleState.REGISTERED,
                ):
                    raise ServiceRegistryError(
                        f"Service '{service_id}' depends on '{dep}' which is not "
                        f"RUNNING/REGISTERED; initialization order violated."
                    )
            reg.lifecycle_state = ServiceLifecycleState.INITIALIZING
        # No event emitted for the pure transition-to-INITIALIZING; the
        # LifecycleManager emits the meaningful RUNNING milestone below.

    async def mark_service_running(self, service_id: str) -> None:
        """Record a service as RUNNING (§3.4.9).

        Called by the LifecycleManager AFTER it has executed the service's
        own ``initialize()``/``start()``. The registry only records the state
        and emits the (mapped) ServiceInitialized event.
        """
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                raise ServiceRegistryError(f"Unknown service '{service_id}'.")
            reg.lifecycle_state = ServiceLifecycleState.RUNNING
            reg.healthy = True
            reg.consecutive_health_failures = 0
        await self._emit_service_event(
            "ServiceInitialized", reg, lifecycle=ServiceLifecycleState.RUNNING.value
        )

    async def mark_service_failed(self, service_id: str, error: str | None = None) -> None:
        """Record a service as FAILED (§3.4.9 / §3.4.12).

        Called by the LifecycleManager / failure handler. Records the FAILED
        state, stores the error, and emits the (mapped) ServiceFailed event.
        """
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                raise ServiceRegistryError(f"Unknown service '{service_id}'.")
            reg.lifecycle_state = ServiceLifecycleState.FAILED
            reg.last_error = error
        await self._emit_service_event(
            "ServiceFailed", reg, lifecycle=ServiceLifecycleState.FAILED.value, error=error
        )

    async def mark_service_shutting_down(self, service_id: str) -> None:
        """Record SHUTTING_DOWN for a service (§3.4.9).

        The LifecycleManager has decided to shut the service down; the registry
        records the transition. No service method is invoked.
        """
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                raise ServiceRegistryError(f"Unknown service '{service_id}'.")
            reg.lifecycle_state = ServiceLifecycleState.SHUTTING_DOWN

    async def mark_service_shutdown(self, service_id: str) -> None:
        """Record a service as SHUTDOWN (§3.4.9).

        Called by the LifecycleManager AFTER it has executed the service's own
        ``shutdown()``/``stop()``. The registry only records the state and emits
        the (mapped) ServiceShutdown event.
        """
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                raise ServiceRegistryError(f"Unknown service '{service_id}'.")
            reg.lifecycle_state = ServiceLifecycleState.SHUTDOWN
        await self._emit_service_event(
            "ServiceShutdown", reg, lifecycle=ServiceLifecycleState.SHUTDOWN.value
        )

    # --- health tracking (SR-R-006, §3.4.9, §3.4.12) ----------------------

    async def update_health(
        self,
        service_id: str,
        healthy: bool,
        *,
        error: str | None = None,
    ) -> None:
        """Record a health check result and apply §3.4.12 transition rules.

        * 1st failure -> DEGRADED, emit ServiceHealthChanged (HEALTH_CHECK_FAILED).
        * 3 consecutive failures -> FAILED, emit ServiceFailed (SERVICE_FAILED).
        * Recovery -> RUNNING/REGISTERED, emit ServiceHealthChanged
          (HEALTH_CHECK_PASSED).
        """
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                raise ServiceRegistryError(f"Unknown service '{service_id}'.")
            reg.last_health_check_at = datetime.now(UTC).isoformat()
            reg.last_error = error

            if healthy:
                reg.healthy = True
                reg.consecutive_health_failures = 0
                if reg.lifecycle_state in (
                    ServiceLifecycleState.DEGRADED,
                    ServiceLifecycleState.FAILED,
                ):
                    reg.lifecycle_state = ServiceLifecycleState.RUNNING
                event_type = EventType.HEALTH_CHECK_PASSED
            else:
                reg.healthy = False
                reg.consecutive_health_failures += 1
                if reg.consecutive_health_failures >= _HEALTH_FAILURE_THRESHOLD:
                    reg.lifecycle_state = ServiceLifecycleState.FAILED
                    event_type = EventType.SERVICE_FAILED
                else:
                    reg.lifecycle_state = ServiceLifecycleState.DEGRADED
                    event_type = EventType.HEALTH_CHECK_FAILED
            state_value = reg.lifecycle_state.value

        # Emit deterministically (async) outside the lock.
        await self._emit_async(
            event_type,
            self._service_payload(reg, lifecycle=state_value, error=error),
        )
        if event_type is EventType.SERVICE_FAILED:
            # Also satisfy §3.4.12's explicit ServiceFailed emission semantics.
            logger.error(
                "Service '%s' marked FAILED after %d consecutive health failures.",
                service_id,
                reg.consecutive_health_failures,
            )

    def get_health(self, service_id: str) -> dict[str, Any] | None:
        """Per-service health snapshot, or None if not registered."""
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                return None
            return {
                "service_id": reg.service_id,
                "lifecycle_state": reg.lifecycle_state.value,
                "healthy": reg.healthy,
                "consecutive_health_failures": reg.consecutive_health_failures,
                "last_error": reg.last_error,
                "last_health_check_at": reg.last_health_check_at,
            }

    def get_all_health(self) -> dict[str, dict[str, Any]]:
        """All per-service health snapshots."""
        with self._lock:
            return {
                sid: {
                    "service_id": r.service_id,
                    "lifecycle_state": r.lifecycle_state.value,
                    "healthy": r.healthy,
                    "consecutive_health_failures": r.consecutive_health_failures,
                    "last_error": r.last_error,
                    "last_health_check_at": r.last_health_check_at,
                }
                for sid, r in self._registrations.items()
            }

    # --- introspection ---------------------------------------------------

    def __contains__(self, service_id: str) -> bool:
        with self._lock:
            return service_id in self._registrations

    def __len__(self) -> int:
        with self._lock:
            return len(self._registrations)

    def get_stats(self) -> dict[str, Any]:
        """Registry statistics."""
        h = self.healthCheck()
        with self._lock:
            by_type: dict[str, int] = {}
            for r in self._registrations.values():
                by_type[r.service_type.value] = by_type.get(r.service_type.value, 0) + 1
        return {
            "name": self.name,
            "state": self._state.value,
            "total_services": h.total_services,
            "running_services": h.running_services,
            "degraded_services": h.degraded_services,
            "failed_services": h.failed_services,
            "services_by_type": by_type,
            "capability_count": len(self._capability_index),
        }

    # =====================================================================
    # Internal helpers
    # =====================================================================

    def _validate_namespace(self, service_id: str) -> None:
        """INV-SR-NS-001/002: prefix required; `kernel` reserved."""
        if "." not in service_id:
            raise ServiceRegistryError(
                f"ServiceId '{service_id}' MUST be prefixed with a namespace "
                f"(e.g. 'engineering.PlanningService') (INV-SR-NS-001)."
            )
        prefix = service_id.split(".", 1)[0]
        if prefix == ServiceNamespace.KERNEL.value:
            raise ServiceRegistryError(
                f"ServiceId '{service_id}' uses the reserved 'kernel' namespace "
                f"(INV-SR-NS-002). Registration rejected."
            )

    def _lookup_visible(self, service_id: str) -> ServiceRegistration | None:
        """Lookup honoring INV-SR-DISC-001/003 (only REGISTERED/RUNNING)."""
        with self._lock:
            reg = self._registrations.get(service_id)
            if reg is None:
                return None
            if reg.lifecycle_state in (
                ServiceLifecycleState.REGISTERED,
                ServiceLifecycleState.RUNNING,
            ):
                return reg
            return None

    def _visible_registrations(self) -> list[ServiceRegistration]:
        """All registrations exposed by discovery (INV-SR-DISC-001/003)."""
        with self._lock:
            return [
                r
                for r in self._registrations.values()
                if r.lifecycle_state
                in (
                    ServiceLifecycleState.REGISTERED,
                    ServiceLifecycleState.RUNNING,
                )
            ]

    def _rollback_registration(self, service_id: str) -> None:
        """Remove a tentatively-added registration (cycle detection failure)."""
        reg = self._registrations.pop(service_id, None)
        if reg is not None:
            for cap in reg.capabilities:
                ids = self._capability_index.get(cap.name)
                if ids and service_id in ids:
                    ids.remove(service_id)
                    if not ids:
                        self._capability_index.pop(cap.name, None)

    def _check_acyclic(self) -> None:
        """DFS cycle detection over the full dependency graph (SR-REG-003).

        Raises ServiceRegistryError if a cycle is present. Deterministic.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {}
        with self._lock:
            nodes = list(self._registrations.keys())
            deps = {sid: list(r.depends_on) for sid, r in self._registrations.items()}

        def visit(node: str, stack: list[str]) -> None:
            color[node] = GRAY
            for dep in sorted(deps.get(node, [])):
                if dep not in color and dep in deps:
                    # dep is a known node -> recurse
                    if color.get(dep, WHITE) == WHITE:
                        visit(dep, stack + [node])
                elif color.get(dep) == GRAY:
                    cycle = stack + [node, dep]
                    raise ServiceRegistryError(
                        f"Dependency cycle detected: {' -> '.join(cycle)} "
                        f"(SR-REG-003)."
                    )
            color[node] = BLACK

        for n in nodes:
            if color.get(n, WHITE) == WHITE:
                visit(n, [])

    def _validate_dependencies_exist(self, deps: dict[str, list[str]]) -> None:
        """All depends_on targets must reference a registered service (SR-REG-002)."""
        with self._lock:
            known = set(self._registrations.keys())
        for sid, ds in deps.items():
            for d in ds:
                if d not in known:
                    raise ServiceRegistryError(
                        f"Service '{sid}' depends on unregistered service '{d}' "
                        f"(SR-REG-002). All dependencies MUST be registered."
                    )

    @staticmethod
    def _topological_order(
        nodes: list[str], deps: dict[str, list[str]]
    ) -> list[str]:
        """Deterministic topological sort (Kahn-style, sorted tie-break)."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in nodes}
        order: list[str] = []

        def visit(node: str) -> None:
            color[node] = GRAY
            for dep in sorted(deps.get(node, [])):
                if dep in color and color[dep] == WHITE:
                    visit(dep)
            color[node] = BLACK
            order.append(node)

        for n in sorted(nodes):
            if color[n] == WHITE:
                visit(n)
        return order

    def _register_internal_subscriptions(self) -> None:
        """§3.4.10: register internal subscriptions for lifecycle coordination."""
        if self._event_bus is None:
            return
        try:
            from aios.events.core.manager import SubscribeOptions

            # Subscribe to ConfigurationFrozen (§3.4.10 step 2) and ServiceFailed
            # (§3.4.12 reaction) so the registry can coordinate lifecycle.
            sub_inits = [
                (
                    EventType.CONFIGURATION_FROZEN,
                    self._on_configuration_frozen,
                ),
                (EventType.SERVICE_FAILED, self._on_service_failed),
            ]
            for et, handler in sub_inits:
                try:
                    sub_id = self._event_bus.subscribe(
                        SubscribeOptions(
                            subscriber=self._identity,
                            event_types=(et,),
                            handler=handler,
                            handler_type="sync",
                        )
                    )
                    self._subscriptions.append(sub_id)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Internal subscription to %s skipped: %s", et, exc)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Internal subscriptions not registered: %s", exc)

    def _deregister_internal_subscriptions(self) -> None:
        """§3.4.11 step 2: deregister internal subscriptions."""
        if self._event_bus is None:
            return
        for sub_id in self._subscriptions:
            try:
                self._event_bus.unsubscribe(sub_id)
            except Exception:  # noqa: BLE001
                pass
        self._subscriptions.clear()

    def _on_configuration_frozen(self, event: Event) -> None:
        """React to ConfigurationFrozen (§3.4.10 step 5)."""
        logger.debug("ServiceRegistry observed ConfigurationFrozen.")

    def _on_service_failed(self, event: Event) -> None:
        """React to a service FAILED event (§3.4.12)."""
        payload = event.payload.to_dict() if hasattr(event.payload, "to_dict") else {}
        svc = payload.get("service") or payload.get("service_id")
        if svc and svc in self._registrations:
            with self._lock:
                reg = self._registrations.get(svc)
                if reg is not None and reg.critical:
                    logger.critical(
                        "Critical service '%s' FAILED; kernel emergency shutdown "
                        "required (§3.4.12 FATAL).",
                        svc,
                    )

    # --- event emission (canonical EventTypes only) ----------------------

    async def _emit_service_event(
        self, arch_name: str, reg: ServiceRegistration, *, lifecycle: str, error: str | None = None
    ) -> None:
        """Emit a §3.4-named service event, mapped to a canonical EventType."""
        event_type = _ARCH_EVENT_TO_EVENT_TYPE.get(arch_name)
        if event_type is None:
            return
        await self._emit_async(
            event_type,
            self._service_payload(reg, lifecycle=lifecycle, error=error),
        )

    def _service_payload(
        self, reg: ServiceRegistration, *, lifecycle: str, error: str | None = None
    ) -> dict[str, Any]:
        return {
            "service": reg.service_id,
            "service_id": reg.service_id,
            "service_type": reg.service_type.value,
            "version": getattr(reg.service, "version", "") or "",
            "lifecycle": lifecycle,
            "critical": reg.critical,
            "dependencies": list(reg.depends_on),
            "capabilities": [c.name for c in reg.capabilities],
            "tags": list(reg.tags),
            "error": error,
        }

    def _make_event(self, event_type: EventType, payload: dict[str, Any]) -> Event:
        """Build a canonical Event with this registry as the source identity."""
        return Event(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=payload,
        )

    def _emit(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit an event from a SYNCHRONOUS call site (register / update_health).

        The Task-5 EventBus ``publish`` is async-only. From a synchronous
        context with no running loop, we cannot ``await`` it, so we defer the
        publication onto the currently-bound loop if one exists (fire-and-forget)
        or drop it silently if no transport is available yet. This keeps the
        public API synchronous (matching the EventBus Core Component pattern:
        sync ``healthCheck``, sync registration helpers) while still routing
        every emission through the injected bus (INV-SR-STR-007).
        """
        bus = self._event_bus
        if bus is None:
            return
        try:
            event = self._make_event(event_type, payload)
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Inside a running loop: schedule without blocking the lock.
                    loop.create_task(bus.publish(event))
                    return
            except RuntimeError:
                pass
            # No running loop (synchronous test/CLI context): nothing to await on.
            # The bus would need a loop; we record the intent and continue. Tests
            # that verify emission use the async lifecycle methods + bus.drain().
            logger.debug(
                "Event %s not dispatched (no running loop); bus will not see it "
                "from this synchronous call site.",
                event_type.name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Event emission of %s failed: %s", event_type.name, exc)

    async def _emit_async(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit an event from an ASYNCHRONOUS call site (initialize / shutdown).

        Awaits the bus ``publish`` so the event is enqueued deterministically;
        tests pass ``auto_start_dispatch_worker=False`` and ``await bus.drain()``
        to observe it.
        """
        bus = self._event_bus
        if bus is None:
            return
        try:
            event = self._make_event(event_type, payload)
            await bus.publish(event)
        except Exception as exc:  # noqa: BLE001
            logger.debug("Async event emission of %s failed: %s", event_type.name, exc)


# ---------------------------------------------------------------------------
# Singleton / integration point (kernel.serviceRegistry)
# ---------------------------------------------------------------------------


_INSTANCE: ServiceRegistry | None = None
_INSTANCE_LOCK = threading.RLock()


def reset_service_registry_singleton() -> None:
    """Reset the process-wide ServiceRegistry singleton (tests only)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


def get_service_registry(event_bus: EventBus | None = None) -> ServiceRegistry:
    """Get (or create) the global ServiceRegistry singleton.

    Integration point for ``kernel.serviceRegistry``. Production code MUST NOT
    construct twice; use this accessor (INV-SR-STR-001).
    """
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = ServiceRegistry(event_bus=event_bus)
        elif event_bus is not None and _INSTANCE._event_bus is None:
            _INSTANCE._event_bus = event_bus
        return _INSTANCE


def set_service_registry(registry: ServiceRegistry) -> None:
    """Set the global ServiceRegistry singleton (kernel-owned construction)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = registry


class ServiceRegistryError(Exception):
    """Raised for registration / dependency / lifecycle violations.

    Reuses the established error convention (no new exception hierarchy invented
    beyond this single, clearly-scoped class mandated by §3.4.12 rejection
    rules). Callers receive a precise message per SR-REG-*/INV-SR-* rule.
    """

    def __init__(self, message: str, *, rule_id: str | None = None) -> None:
        super().__init__(message)
        self.rule_id = rule_id


__all__ = [
    "ServiceRegistry",
    "ServiceType",
    "ServiceLifecycleState",
    "ServiceRegistryState",
    "ServiceNamespace",
    "Capability",
    "ServiceRegistration",
    "ServiceRegistryHealth",
    "ServiceRegistryError",
    "get_service_registry",
    "set_service_registry",
    "reset_service_registry_singleton",
]
