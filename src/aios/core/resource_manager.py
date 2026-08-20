"""
Resource Manager for AI-OS Hermes Kernel.

Manages compute, memory, API quotas, and other resources with scheduling and
limits.

Task 13 — Core Manager upgrade (Part 4 §4.7)
----------------------------------------------
ResourceManager is upgraded from a plain manager into the Phase-3 (Governance)
Core Manager, alongside HealthManager and SecurityManager (Part 4 §4.2.3). It
implements the ICoreManager Protocol (name / phase / dependencies / manager_id /
initialize / shutdown / health_ready) so LifecycleManager (Task 9) can
orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 3 (alphabetical within phase:
    HealthManager, ResourceManager, SecurityManager — deterministic per
    Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.resource``
    (Part 4 §4.7 names the identity ``kernel.resource``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.resource``, using the same precedent Task 9/10/11/12 established for
    ``core.lifecycle`` / ``core.state`` / ``core.storage`` / ``core.health``),
    using the same "core_manager" metadata envelope
  * reads ``kernel.resource.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used (Task 13 requirement, matching Tasks 10–12)

CONFLICT E.1 (Task 13 mapping, same as Tasks 9–12): Part 4 §4.7.10 names events
like ``ResourceAllocatedEvent`` / ``ResourceReleasedEvent`` /
``QuotaExceededEvent`` / ``ResourceExhaustedEvent`` (roughly ten conceptual
ResourceManager events) that do NOT exist in the closed canonical ``EventType``
enum (Part 2 §2.3.1, Task 2). ResourceManager does NOT invent new EventTypes.
The canonical mappings for the resource domain are (verified against
``src/aios/events/core/types.py``):

  * Resource allocated           -> EventType.RESOURCE_ALLOCATED
  * Resource released            -> EventType.RESOURCE_RELEASED
  * Resource exhausted / timeout -> EventType.RESOURCE_EXHAUSTED
  * Requested amount > hard limit (quota breach) -> EventType.QUOTA_EXCEEDED

If a conceptual resource event has no canonical EventType equivalent, that event
emission is omitted rather than invented.

NOTE ON ``core.resource`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.7): Part 4 §4.7 names ResourceManager's ServiceRegistry identity as
``kernel.resource``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle`` instead of ``kernel.lifecycle``) and Task 10/11/12 resolved
for StateManager (``core.state``), StorageManager (``core.storage``), and
HealthManager (``core.health``). Per that precedent, the compliant,
INV-SR-NS-002-respecting ServiceRegistry identity is ``core.resource`` (the
``core.*`` namespace is not reserved and is NOT a validator exception). The
configuration namespace read from C3 remains ``kernel.resource.*`` (Part 4 §4.7
config schema), which is independent of the ServiceRegistry id. Lifecycle
ownership (initialize/shutdown driven by LifecycleManager Phase 3) is unchanged.

PHASE DEPENDENCY RULE: ResourceManager is Phase 3. It does NOT declare
HealthManager or SecurityManager as formal dependencies:

    dependencies = ["LifecycleManager"]

The same-phase siblings are ordered deterministically (alphabetical within
Phase 3: HealthManager, ResourceManager, SecurityManager) and the existing
LifecycleManager dependency validator (LM-DEP-003) does not accept same-phase
sibling dependencies. Relying on deterministic alphabetical ordering guarantees
correct sequencing; the ResourceManager/HealthManager/SecurityManager operational
relationship is event-driven (via canonical EventBus), not a lifecycle dependency
edge.

BUSINESS BEHAVIOR: the existing resource-management domain behavior (limits,
allocation, release, exhaustion/quota handling, wait queues, cleanup, tracking)
is preserved and upgraded into the Core Manager architecture. The public
ResourceManager business APIs (allocate / release / release_all_for_requestor /
get_usage / set_limit / get_limit / add_allocation / get_stats / start_cleanup_task
/ stop_cleanup_task / _cleanup_expired) remain intact unless the architecture
explicitly requires a compatibility change (only the constructor gains the
Core-Manager DI signature and logging moves to StructuredLogger).
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as LifecycleManager /
# StateManager / StorageManager / HealthManager); these modules do not import
# ``aios.core.resource_manager`` at module scope, so there is no circular-import
# risk (verified against checkpoint/workflow/kernel/__init__).
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "ResourceManager",
    "ResourceType",
    "ResourceLimit",
    "ResourceAllocation",
    "ResourceUsage",
    "ResourceExhausted",
    "ResourceManagerError",
    "get_resource_manager",
    "set_resource_manager",
    "reset_resource_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "ResourceManager"
# Part 4 §4.7 names ResourceManager's ServiceRegistry identity as
# ``kernel.resource``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager
# (registering as ``core.lifecycle`` instead of ``kernel.lifecycle``) and
# Task 10/11/12 resolved for StateManager (``core.state``), StorageManager
# (``core.storage``), and HealthManager (``core.health``). We follow that
# precedent: the compliant, INV-SR-NS-002-respecting ServiceRegistry id is
# ``core.resource``. The configuration namespace read from C3 remains
# ``kernel.resource.*`` (Part 4 §4.7 config schema), which is unaffected by the
# ServiceRegistry id.
_MANAGER_ID = "core.resource"
_PHASE = 3  # Phase 3 — "Governance"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 13 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10/11/12):
#   * same-phase siblings (HealthManager, SecurityManager) are NOT dependencies
#     — same-phase deps would be rejected by LifecycleManager's dependency
#     validator (LM-DEP-003); deterministic alphabetical ordering
#     (HealthManager first, then ResourceManager, then SecurityManager) already
#     guarantees correct sequencing,
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_RESOURCE_ALLOCATED = EventType.RESOURCE_ALLOCATED
_RESOURCE_RELEASED = EventType.RESOURCE_RELEASED
_RESOURCE_EXHAUSTED = EventType.RESOURCE_EXHAUSTED
_QUOTA_EXCEEDED = EventType.QUOTA_EXCEEDED


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ResourceType(str, Enum):  # noqa: UP042 -- matches LifecycleState / HealthStatus pattern in sibling managers
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

    def to_dict(self) -> dict[str, Any]:
        """Serialize usage to a JSON-safe dict (Part 2 §2.2.8)."""
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


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class ResourceExhausted(Exception):
    """Raised when a resource is exhausted and cannot be allocated."""

    pass


class ResourceManagerError(Exception):
    """ResourceManager failure (Part 4 §4.7.11).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` / ``HealthManagerError`` (Tasks 9/10/11/12).
    """

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += (
                f" [original_error={type(self.original_error).__name__}:"
                f" {self.original_error}]"
            )
        return base


# ---------------------------------------------------------------------------
# ResourceManager
# ---------------------------------------------------------------------------


class ResourceManager:
    """Phase-3 (Governance) resource authority for the Hermes Kernel.

    Manages compute, memory, API quotas, and other resources with limits,
    quotas, allocation tracking, wait queues, and automatic cleanup of expired
    allocations. The resource-management domain behavior is preserved from the
    pre-Task-13 implementation and upgraded into the Core Manager architecture.

    Architecture contract (mirrors StateManager / StorageManager / HealthManager):
    - Consumes the four Core Components (C1–C4) via DI.
    - Does NOT construct its own EventBus / ServiceRegistry /
      ConfigurationManager / StructuredLogger.
    - Uses only canonical EventTypes (CONFLICT E.1).
    - Lifecycle is owned by LifecycleManager (NOT routed through
      _start_services / _stop_engineering_services in the kernel for its
      initialize()/shutdown() — those engineering-service hooks only drive the
      background cleanup task for backward compatibility; see the kernel
      integration note).
    """

    def __init__(
        self,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize the Resource Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_resource_event`` bridge keep working unchanged.

        The legacy ``config`` argument (a plain dict) is preserved for backward
        compatibility with pre-Task-13 callers; when provided, any per-resource
        limits it describes are applied as overrides after the safe defaults.
        """
        # C2/C3/C4 — injected via DI (Task 13).
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError(
                "Canonical EventBus not initialized. Start the kernel first."
            )

        # Strong references for sync-path publish tasks (FIX-FIND-01): coroutines
        # scheduled from synchronous business APIs are awaited on the running loop
        # and held here until complete so they are never garbage-collected or left
        # un-awaited. Mirrors the ConfigurationManager ``_pending_tasks`` pattern
        # (Task 7) / StateManager / StorageManager / HealthManager patterns.
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.7).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 13).
        self._initialized = False
        self._registered_with_sr = False

        # Legacy configuration compatibility shim (preserved, documented).
        self._legacy_config: dict[str, Any] = dict(config or {})

        # Resource bookkeeping.
        self._limits: dict[ResourceType, ResourceLimit] = {}
        self._allocations: dict[ResourceType, list[ResourceAllocation]] = {}
        self._wait_queues: dict[ResourceType, list[tuple[str, asyncio.Future[Any]]]] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task[Any] | None = None

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        # Defaults are safe; misconfiguration is diagnosable, never silently hidden.
        self._cleanup_interval_seconds = 60
        self._warning_threshold = 0.8
        self._critical_threshold = 0.95

        # Initialize default limits (preserves pre-Task-13 domain behavior).
        self._init_default_limits()

        # Apply any legacy config overrides (backward-compatible shim).
        self._apply_legacy_config()

    def _init_default_limits(self) -> None:
        """Initialize default resource limits (preserved domain behavior)."""
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

    def _apply_legacy_config(self) -> None:
        """Apply legacy ``config`` dict overrides (backward-compatible shim).

        Pre-Task-13 callers could pass a ``config`` dict; we honor any
        ``limits`` entries it carries (a list of ResourceLimit-like dicts) by
        constructing ResourceLimit objects. This preserves the legacy contract
        without creating a second configuration system.
        """
        legacy_limits = self._legacy_config.get("limits")
        if not isinstance(legacy_limits, list):
            return
        for entry in legacy_limits:
            if not isinstance(entry, dict):
                continue
            try:
                rt = ResourceType(entry["resource_type"])
                self.set_limit(
                    ResourceLimit(
                        resource_type=rt,
                        limit=float(entry["limit"]),
                        unit=str(entry.get("unit", "")),
                        description=str(entry.get("description", "")),
                        warning_threshold=float(entry.get("warning_threshold", 0.8)),
                        critical_threshold=float(entry.get("critical_threshold", 0.95)),
                    )
                )
            except (KeyError, ValueError, TypeError):
                # Legacy override malformed — skip it rather than crash, but
                # make the miswire diagnosable (Task 13: failures must be
                # diagnosable rather than silently hidden).
                self._log_warning(
                    f"Legacy resource config override skipped (malformed): {entry!r}"
                )

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 13 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 3 — Governance, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.resource``; Part 4 §4.7 names
        ``kernel.resource`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors LifecycleManager.health_ready / StateManager.health_ready /
        StorageManager.health_ready / HealthManager.health_ready: ready by
        construction once the manager has completed its own initialization.
        Returns False before ``initialize()`` and after ``shutdown()``.
        """
        return self._initialized and self._event_bus is not None

    # ------------------------------------------------------------------
    # ICoreManager: initialization / shutdown
    # ------------------------------------------------------------------

    def _read_config_str(self, path: str, default: str) -> str:
        """Read a string config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return str(val) if val is not None else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_int(self, path: str, default: int) -> int:
        """Read an int config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_float(self, path: str, default: float) -> float:
        """Read a float config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return float(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_bool(self, path: str, default: bool) -> bool:
        """Read a bool config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:  # noqa: BLE001
            return default

    async def initialize(self) -> None:
        """Phase 3 initialization (called by LifecycleManager).

        Follows the Core Manager pattern (mirrors StateManager.initialize /
        StorageManager.initialize / HealthManager.initialize): reads
        ``kernel.resource.*`` configuration from the frozen C3, wires the
        StructuredLogger (C4), registers this manager with the canonical
        ServiceRegistry (C2) as ``core.resource``, and marks the manager
        initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._cleanup_interval_seconds = self._read_config_int(
            "kernel.resource.cleanupIntervalSeconds", self._cleanup_interval_seconds
        )
        self._warning_threshold = self._read_config_float(
            "kernel.resource.warningThreshold", self._warning_threshold
        )
        self._critical_threshold = self._read_config_float(
            "kernel.resource.criticalThreshold", self._critical_threshold
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.resource``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"ResourceManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 3 (reverse) shutdown (called by LifecycleManager).

        Stops the background cleanup task, clears allocation/wait-queue tracking,
        marks ``core.resource`` SHUTDOWN in the canonical ServiceRegistry (C2),
        and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Stop background cleanup (self-contained; the kernel's engineering
        #    service stop hook also calls this, but it is idempotent).
        self.stop_cleanup_task()

        # 2. Clear resource tracking.
        self._allocations = {}
        self._wait_queues = {}

        # 3. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 4. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("ResourceManager shut down.")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror StateManager / StorageManager /
    # HealthManager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register ResourceManager with the ServiceRegistry (C2, Part 4 §4.7).

        Registered as ``core.resource`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering ResourceManager.")
            return
        try:
            await sr.register(
                self,
                service_id=_MANAGER_ID,
                service_type=ServiceType.ENGINEERING,
                metadata={
                    "kind": "core_manager",
                    "manager": _NAME,
                    "phase": _PHASE,
                    "lifecycle_state": "INITIALIZED",
                },
            )
            self._registered_with_sr = True
            self._log_info(f"Registered with ServiceRegistry as '{_MANAGER_ID}'.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry registration failed: {exc}")

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.resource`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister.")
            return
        try:
            await sr.mark_service_shutdown(_MANAGER_ID)
            self._registered_with_sr = False
            self._log_info(f"Marked '{_MANAGER_ID}' SHUTDOWN in ServiceRegistry.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(
                f"ServiceRegistry shutdown-mark failed for '{_MANAGER_ID}': {exc}"
            )

    # ------------------------------------------------------------------
    # Business API — preserved from pre-Task-13 ResourceManager
    # ------------------------------------------------------------------

    def set_limit(self, limit: ResourceLimit) -> None:
        """Set a resource limit."""
        self._limits[limit.resource_type] = limit
        self._log_info(f"Set {limit.resource_type.value} limit: {limit.limit} {limit.unit}")

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
            ResourceExhausted: If resource unavailable and timeout reached, or if
                the requested amount exceeds the hard limit (quota breach)
        """
        # Canonical event mapping (CONFLICT E.1): a request that exceeds the hard
        # limit is a quota breach -> QUOTA_EXCEEDED (never an invented EventType).
        limit = self._limits.get(resource_type)
        if limit is not None and amount > limit.limit:
            self._emit_resource_event(
                _QUOTA_EXCEEDED,
                {
                    "resource_type": resource_type.value,
                    "amount": amount,
                    "limit": limit.limit,
                    "unit": limit.unit,
                    "requestor": requestor,
                },
            )
            raise ResourceExhausted(
                f"Requested {amount} {limit.unit} of {resource_type.value} exceeds "
                f"hard limit {limit.limit} {limit.unit} (quota breach)."
            )

        async with self._lock:
            if self._can_allocate(resource_type, amount):
                allocation = self._do_allocate(
                    resource_type, amount, requestor, purpose, ttl_seconds
                )
                # Canonical event mapping: successful allocation.
                self._emit_resource_event(
                    _RESOURCE_ALLOCATED,
                    {
                        "allocation_id": allocation.allocation_id,
                        "resource_type": resource_type.value,
                        "amount": amount,
                        "requestor": requestor,
                        "purpose": purpose,
                    },
                )
                return allocation

        # Wait for resource
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        async with self._lock:
            if resource_type not in self._wait_queues:
                self._wait_queues[resource_type] = []
            self._wait_queues[resource_type].append((requestor, future))

        try:
            allocation = await asyncio.wait_for(future, timeout=timeout)
            # Canonical event mapping: allocation satisfied from wait queue.
            self._emit_resource_event(
                _RESOURCE_ALLOCATED,
                {
                    "allocation_id": allocation.allocation_id,
                    "resource_type": resource_type.value,
                    "amount": amount,
                    "requestor": requestor,
                    "purpose": purpose,
                },
            )
            return allocation
        except TimeoutError:
            async with self._lock:
                # Remove from wait queue
                queue = self._wait_queues.get(resource_type, [])
                self._wait_queues[resource_type] = [
                    (r, f) for r, f in queue if f != future
                ]
            # Canonical event mapping: exhausted (timeout waiting).
            self._emit_resource_event(
                _RESOURCE_EXHAUSTED,
                {
                    "resource_type": resource_type.value,
                    "amount": amount,
                    "requestor": requestor,
                    "reason": "timeout",
                },
            )
            raise ResourceExhausted(
                f"Timeout waiting for {resource_type.value}: {amount} "
                f"{self._limits[resource_type].unit}"
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
        from datetime import timedelta
        from uuid import uuid4

        expires_at = None
        if ttl_seconds:
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
        self._allocations[resource_type].append(allocation)

        # Check thresholds and warn (uses configured global thresholds).
        limit = self._limits.get(resource_type)
        if limit:
            used = sum(a.amount for a in self._allocations[resource_type])
            usage_ratio = used / limit.limit
            if usage_ratio >= self._critical_threshold:
                self._log_error(
                    f"Critical {resource_type.value} usage: {usage_ratio:.1%}"
                )
            elif usage_ratio >= self._warning_threshold:
                self._log_warning(
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

                    # Canonical event mapping: successful release.
                    self._emit_resource_event(
                        _RESOURCE_RELEASED,
                        {
                            "allocation_id": allocation_id,
                            "resource_type": resource_type.value,
                            "requestor": alloc.requestor,
                        },
                    )
                    return True

        return False

    def _process_wait_queue(self, resource_type: ResourceType) -> None:
        """Process wait queue for a resource."""
        queue = self._wait_queues.get(resource_type, [])
        if not queue:
            return

        new_queue: list[tuple[str, asyncio.Future[Any]]] = []
        for requestor, future in queue:
            if future.done():
                continue

            # Check if can allocate (simplified - first in queue gets priority)
            limit = self._limits.get(resource_type)
            if not limit:
                continue

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
                # Canonical event mapping: each released allocation.
                self._emit_resource_event(
                    _RESOURCE_RELEASED,
                    {
                        "allocation_id": alloc.allocation_id,
                        "resource_type": resource_type.value,
                        "requestor": requestor,
                    },
                )
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

    def start_cleanup_task(self, interval_seconds: int | None = None) -> None:
        """Start background cleanup of expired allocations."""
        if self._cleanup_task is not None:
            return
        if interval_seconds is not None:
            interval = interval_seconds
        else:
            interval = self._cleanup_interval_seconds

        async def cleanup() -> None:
            while True:
                await asyncio.sleep(interval)
                await self._cleanup_expired()

        self._cleanup_task = asyncio.ensure_future(cleanup())

    def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task is not None:
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
                # Canonical event mapping: expired allocations are released.
                self._emit_resource_event(
                    _RESOURCE_RELEASED,
                    {
                        "allocation_id": alloc.allocation_id,
                        "resource_type": resource_type.value,
                        "requestor": alloc.requestor,
                        "reason": "expired",
                    },
                )

            if expired:
                self._process_wait_queue(resource_type)

        if cleaned:
            self._log_debug(f"Cleaned up {cleaned} expired allocations")

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

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_resource_event(
        self, event_type: EventType, payload: dict[str, Any]
    ) -> None:
        """Emit a canonical resource event via the canonical EventBus.

        The canonical Task-5 ``EventBus.publish`` is async (returns a coroutine).
        From a synchronous business-API call site (e.g. ``release`` /
        ``release_all_for_requestor``) we cannot ``await`` it, so this method
        bridges to the async bus deterministically using the architecture-approved
        sync-to-async bridge established in ``ConfigurationManager._run_emission``
        (Task 7) and mirrored by StateManager / StorageManager / HealthManager
        (Tasks 10/11/12):

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion). The event is enqueued on the bus deterministically
          before the next ``await`` yields.
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note. The canonical bus requires a running loop to enqueue;
          synchronously dropping here avoids the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited``
          and never leaves a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.7.10 names
        like ``ResourceAllocatedEvent`` / ``QuotaExceededEvent`` have no canonical
        equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

        # Embed manager identity + avoid INV-EVT-011 forbidden payload keys.
        full_payload = {
            "manager": _NAME,
            "manager_id": _MANAGER_ID,
            **payload,
        }

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=full_payload,
        )

        # FIX-FIND-01: deterministic sync→async bridge. ONLY create the publish
        # coroutine when there is a loop to drive it; never hand an un-awaited
        # coroutine to the GC (that is the bug under FIND-01).
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — there is nowhere to enqueue the coroutine.
            # Skip rather than leak an un-awaited coroutine.
            self._log_debug(
                f"Event {event_type.name} not dispatched (no running event loop).",
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        # Strong reference so the task is never GC'd before the bus drains it.
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 13 — replaces stdlib logging)
    # ------------------------------------------------------------------

    def _log_debug(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.debug(message, manager=_NAME, **fields)

    def _log_info(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.info(message, manager=_NAME, **fields)

    def _log_warning(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.warning(message, manager=_NAME, **fields)

    def _log_error(self, message: str, **fields: Any) -> None:
        if self._logger is not None:
            self._logger.error(message, manager=_NAME, **fields)


# ---------------------------------------------------------------------------
# Global ResourceManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_resource_manager: ResourceManager | None = None
_resource_singleton_lock = threading.Lock()


def get_resource_manager() -> ResourceManager:
    """Get or create the global ResourceManager singleton.

    Uses the same lock-guarded pattern as StateManager / StorageManager /
    HealthManager (Tasks 10/11/12) and the C1–C4 singletons, so concurrent
    callers cannot double-construct.

    Note: unlike a plain ``ResourceManager()`` call, this accessor does not
    inject Core-Component dependencies; production wiring is performed by the
    kernel via :func:`set_resource_manager`. The companion
    :func:`reset_resource_manager_singleton` supports hermetic tests.
    """
    global _global_resource_manager
    with _resource_singleton_lock:
        if _global_resource_manager is None:
            _global_resource_manager = ResourceManager()
        return _global_resource_manager


def set_resource_manager(manager: ResourceManager) -> None:
    """Set the global ResourceManager singleton (kernel-owned construction)."""
    global _global_resource_manager
    with _resource_singleton_lock:
        _global_resource_manager = manager


def reset_resource_manager_singleton() -> None:
    """Reset the process-wide ResourceManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` /
    ``reset_state_manager_singleton`` / ``reset_storage_manager_singleton`` /
    ``reset_health_manager_singleton`` / C2–C4 resets.
    """
    global _global_resource_manager
    with _resource_singleton_lock:
        _global_resource_manager = None
