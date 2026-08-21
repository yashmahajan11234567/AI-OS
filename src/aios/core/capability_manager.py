"""
CapabilityManager — the Phase-4 (Execution) Core Manager for AI-OS Hermes Kernel.

CapabilityManager is the capability registry for the kernel. It implements the
ICoreManager Protocol (name / phase / dependencies / initialize / shutdown /
health_ready) so LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 4 (alphabetical within phase:
    CapabilityManager, WorkflowManager — deterministic per Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.capability``
    (Part 4 §4.8 names the identity ``kernel.capability``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.capability``, using the same precedent Task 9/10/11/12/13 established
    for ``core.lifecycle`` / ``core.state`` / ``core.storage`` / ``core.health``
    / ``core.resource`` / ``core.security``), using the same "core_manager"
    metadata envelope
  * reads ``kernel.capability.*`` configuration from the frozen
    ConfigurationManager (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 15 mapping, same as Tasks 9–14): Part 4 §4.8.11 names events
like ``CapabilityRegisteredEvent`` / ``CapabilityDeprecatedEvent`` /
``CapabilityRemovedEvent`` / ``CapabilityInvocationEvent`` /
``CapabilityConflictEvent`` that do NOT exist in the closed canonical
``EventType`` enum (Part 2 §2.3.1, Task 2). CapabilityManager does NOT invent
new EventTypes. The canonical mappings for the capability domain are (verified
against ``src/aios/events/core/types.py``):

  * Capability registered      -> EventType.SERVICE_STARTED
  * Capability removed         -> EventType.SERVICE_STOPPED
  * Capability invoked         -> EventType.SKILL_EXECUTED
  * Capability invocation error -> EventType.SKILL_FAILED

If a conceptual capability event has no canonical EventType equivalent, that
event emission is omitted rather than invented.

NOTE ON ``core.capability`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.8): Part 4 §4.8 names CapabilityManager's ServiceRegistry identity as
``kernel.capability``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle``) and Task 10/11/12/13 resolved for StateManager,
StorageManager, HealthManager, ResourceManager, and SecurityManager. Per that
precedent, the compliant, INV-SR-NS-002-respecting ServiceRegistry identity is
``core.capability``. The configuration namespace read from C3 remains
``kernel.capability.*`` (Part 4 §4.8 config schema), which is independent of the
ServiceRegistry id. Lifecycle ownership (initialize/shutdown driven by
LifecycleManager Phase 4) is unchanged.

PHASE DEPENDENCY RULE: CapabilityManager is Phase 4. It declares ONLY Phase-1
LifecycleManager as a formal dependency:

    dependencies = ["LifecycleManager"]

It does NOT declare WorkflowManager, SecurityManager, StateManager, or any other
manager as a formal dependency. The (not-yet-implemented) WorkflowManager is a
same-phase sibling (declaring it would be rejected by LifecycleManager's
dependency validator LM-DEP-003 and would break kernel boot, since WorkflowManager
is not currently registered with LifecycleManager); the SecurityManager
authorization gate and StateManager registry backing are operational
relationships that are event-driven (via canonical EventBus), not lifecycle
dependency edges. C1–C4 are always-satisfied base dependencies handled by
LifecycleManager.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as the other Core Managers); these
# modules do not import ``aios.core.capability_manager`` at module scope, so
# there is no circular-import risk.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "CapabilityManager",
    "CapabilityRegistryEntry",
    "CapabilityManagerError",
    "get_capability_manager",
    "set_capability_manager",
    "reset_capability_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "CapabilityManager"
# Part 4 §4.8 names CapabilityManager's ServiceRegistry identity as
# ``kernel.capability``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
# as ``core.lifecycle``) and Task 10/11/12/13 resolved for StateManager,
# StorageManager, HealthManager, ResourceManager, and SecurityManager. We follow
# that precedent: the compliant, INV-SR-NS-002-respecting ServiceRegistry id is
# ``core.capability``. The configuration namespace read from C3 remains
# ``kernel.capability.*`` (Part 4 §4.8 config schema), which is unaffected by the
# ServiceRegistry id.
_MANAGER_ID = "core.capability"
_PHASE = 4  # Phase 4 — "Execution"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 15 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10–14):
#   * same-phase siblings (WorkflowManager) and cross-phase managers (e.g.
#     SecurityManager, StateManager) are NOT declared as dependencies — they
#     would be rejected by LifecycleManager's dependency validator (LM-DEP-003)
#     and could break kernel boot (WorkflowManager is not currently registered
#     with LifecycleManager). Deterministic alphabetical ordering (Phase 4:
#     CapabilityManager, WorkflowManager) already guarantees correct sequencing,
#     and the operational relationships (authorization gate, registry backing)
#     are event-driven (via canonical EventBus), not lifecycle dependency edges.
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_CAPABILITY_REGISTERED = EventType.SERVICE_STARTED
_CAPABILITY_REMOVED = EventType.SERVICE_STOPPED
_CAPABILITY_INVOKED = EventType.SKILL_EXECUTED
_CAPABILITY_INVOCATION_FAILED = EventType.SKILL_FAILED


# ---------------------------------------------------------------------------
# Enumerations / value objects
# ---------------------------------------------------------------------------


class CapabilityState(str, Enum):  # noqa: UP042 -- matches sibling manager enums
    """Lifecycle state of a registered capability (Part 4 §4.8.2)."""

    REGISTERED = "REGISTERED"
    DEPRECATED = "DEPRECATED"
    REMOVED = "REMOVED"


@dataclass
class CapabilityRegistryEntry:
    """A registered capability (Part 4 §4.8.2 registry entry)."""

    capability_id: str
    facade: str
    provider_id: str
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    state: CapabilityState = CapabilityState.REGISTERED
    security_context: dict[str, Any] = field(default_factory=dict)
    resource_profile: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry to a JSON-safe dict (Part 2 §2.2.8)."""
        return {
            "capability_id": self.capability_id,
            "facade": self.facade,
            "provider_id": self.provider_id,
            "provider_metadata": self.provider_metadata,
            "version": self.version,
            "state": self.state.value,
            "security_context": self.security_context,
            "resource_profile": self.resource_profile,
            "tags": list(self.tags),
        }


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CapabilityManagerError(Exception):
    """CapabilityManager failure (Part 4 §4.8.12).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` / ``HealthManagerError`` / ``ResourceManagerError`` /
    ``SecurityManagerError`` (Tasks 9/10/11/12/13/14).
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
# CapabilityManager
# ---------------------------------------------------------------------------


class CapabilityManager:
    """Phase-4 (Execution) capability registry for the Hermes Kernel.

    Provides the kernel capability-management surface:
    - Capability registration / deregistration (single registry; SI-CM-01).
    - Discovery by facade / tags / security level.
    - Invocation routing metadata resolution (returns the bound provider
      endpoint for a registered capability) and execution emission.
    - ICoreManager Core-Manager lifecycle (Task 15 — orchestrated by
      LifecycleManager).

    Architecture contract (mirrors StateManager / StorageManager / HealthManager
    / ResourceManager / SecurityManager):
    - Consumes the four Core Components (C1–C4) via DI.
    - Does NOT construct its own EventBus / ServiceRegistry /
      ConfigurationManager / StructuredLogger.
    - Uses only canonical EventTypes (CONFLICT E.1).
    - Lifecycle is owned by LifecycleManager (NOT routed through
      _start_services / _stop_engineering_services in the kernel).
    """

    def __init__(
        self,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """
        Initialize the Capability Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.
        """
        # C2/C3/C4 — injected via DI (Task 15).
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly.
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError(
                "Canonical EventBus not initialized. Start the kernel first."
            )

        # Strong references for sync-path publish tasks (FIX-FIND-01).
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.8).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 15).
        self._initialized = False
        self._registered_with_sr = False

        # Capability registry.
        self._registry: dict[str, CapabilityRegistryEntry] = {}
        self._registry_lock = threading.RLock()

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._enforce_authorization = True
        self._reject_duplicate_provider = True

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 15 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 4 — Execution, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.capability``; Part 4 §4.8 names
        ``kernel.capability`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors the sibling Core Managers' health_ready: ready by construction
        once the manager has completed its own initialization. Returns False
        before ``initialize()`` and after ``shutdown()``.
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
        """Phase 4 initialization (called by LifecycleManager).

        Follows the Core Manager pattern: reads ``kernel.capability.*``
        configuration from the frozen C3, registers this manager with the
        canonical ServiceRegistry (C2) as ``core.capability``, and marks the
        manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._enforce_authorization = self._read_config_bool(
            "kernel.capability.enforceAuthorization", self._enforce_authorization
        )
        self._reject_duplicate_provider = self._read_config_bool(
            "kernel.capability.rejectDuplicateProvider", self._reject_duplicate_provider
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.capability``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"CapabilityManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 4 (reverse) shutdown (called by LifecycleManager).

        Clears the capability registry, marks ``core.capability`` SHUTDOWN in the
        canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear the capability registry.
        with self._registry_lock:
            self._registry.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("CapabilityManager shut down.")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror sibling Core Manager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register CapabilityManager with the ServiceRegistry (C2, Part 4 §4.8).

        Registered as ``core.capability`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering CapabilityManager.")
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
        """Mark ``core.capability`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
        sr = self._service_registry
        if sr is None:
            self._log_debug("ServiceRegistry unavailable; nothing to deregister")
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
    # Business API — capability registry
    # ------------------------------------------------------------------

    def register(
        self,
        capability_id: str,
        facade: str,
        provider_id: str,
        *,
        provider_metadata: dict[str, Any] | None = None,
        version: str = "1.0.0",
        security_context: dict[str, Any] | None = None,
        resource_profile: dict[str, Any] | None = None,
        tags: tuple[str, ...] = (),
    ) -> CapabilityRegistryEntry:
        """Register a capability (Part 4 §4.8.3).

        Returns the created registry entry and emits the canonical
        ``SERVICE_STARTED`` event (mapping CapabilityRegisteredEvent, CONFLICT E.1).
        Rejects duplicate provider ids when ``reject_duplicate_provider`` is set
        (SI-CM-01 single-registry invariant) and the id is already present.
        """
        if (
            self._reject_duplicate_provider
            and capability_id in self._registry
        ):
            raise CapabilityManagerError(
                f"Capability '{capability_id}' is already registered.",
                rule_id="CM-DUP-001",
            )

        entry = CapabilityRegistryEntry(
            capability_id=capability_id,
            facade=facade,
            provider_id=provider_id,
            provider_metadata=dict(provider_metadata or {}),
            version=version,
            state=CapabilityState.REGISTERED,
            security_context=dict(security_context or {}),
            resource_profile=dict(resource_profile or {}),
            tags=tuple(tags),
        )
        with self._registry_lock:
            self._registry[capability_id] = entry

        self._emit_event(
            _CAPABILITY_REGISTERED,
            {
                "capability_id": capability_id,
                "facade": facade,
                "provider_id": provider_id,
                "version": version,
            },
        )
        self._log_debug(f"Registered capability: {capability_id} (facade={facade})")
        return entry

    def deregister(self, capability_id: str) -> bool:
        """Deregister a capability (Part 4 §4.8.3). Returns True if removed."""
        with self._registry_lock:
            entry = self._registry.pop(capability_id, None)
        if entry is None:
            return False
        entry.state = CapabilityState.REMOVED
        self._emit_event(
            _CAPABILITY_REMOVED,
            {
                "capability_id": capability_id,
                "facade": entry.facade,
                "provider_id": entry.provider_id,
            },
        )
        self._log_debug(f"Deregistered capability: {capability_id}")
        return True

    def get_capability(self, capability_id: str) -> CapabilityRegistryEntry | None:
        """Look up a registered capability by id."""
        with self._registry_lock:
            return self._registry.get(capability_id)

    def list_capabilities(self) -> list[CapabilityRegistryEntry]:
        """List all registered capabilities (snapshot)."""
        with self._registry_lock:
            return list(self._registry.values())

    def discover_by_facade(self, facade: str) -> list[CapabilityRegistryEntry]:
        """Discover capabilities matching a facade id (Part 4 §4.8.4)."""
        with self._registry_lock:
            return [e for e in self._registry.values() if e.facade == facade]

    def discover_by_tags(self, required_tags: tuple[str, ...]) -> list[CapabilityRegistryEntry]:
        """Discover capabilities carrying all of the required tags (Part 4 §4.8.4)."""
        if not required_tags:
            with self._registry_lock:
                return list(self._registry.values())
        with self._registry_lock:
            return [
                e
                for e in self._registry.values()
                if all(t in e.tags for t in required_tags)
            ]

    def resolve(
        self,
        capability_id: str,
        *,
        caller_context: dict[str, Any] | None = None,
    ) -> CapabilityRegistryEntry:
        """Resolve a capability to its bound provider endpoint (Part 4 §4.8.5).

        Raises CapabilityManagerError if the capability is not registered. The
        Authorization gate (SI-CM-04) is owned by the kernel's SecurityManager;
        this manager exposes the resolution metadata. The mapping to a
        registered provider is gated by the registry (SI-CM-01), and an
        unregistered capability therefore cannot be resolved, which surfaces as a
        CapabilityManagerError rather than a bypass (SI-CM-05).
        """
        with self._registry_lock:
            entry = self._registry.get(capability_id)
        if entry is None:
            raise CapabilityManagerError(
                f"Capability '{capability_id}' is not registered; cannot resolve.",
                rule_id="CM-RES-001",
            )
        return entry

    def invoke(
        self,
        capability_id: str,
        *,
        input_payload: dict[str, Any] | None = None,
        caller_context: dict[str, Any] | None = None,
    ) -> CapabilityRegistryEntry:
        """Invoke a capability (Part 4 §4.8.6).

        Resolves the capability (failing if not registered — no bypass,
        SI-CM-05) and emits the canonical ``SKILL_EXECUTED`` event (mapping
        CapabilityInvocationEvent, CONFLICT E.1). Returns the resolved entry.

        The actual provider execution is delegated to the kernel's execution
        layer; this manager owns only the registry/routing/emit contract and does
        not fabricate an execution result. Callers awaiting a result should use
        the resolved entry to drive the owning provider.
        """
        try:
            entry = self.resolve(capability_id, caller_context=caller_context)
        except CapabilityManagerError as exc:
            self._emit_event(
                _CAPABILITY_INVOCATION_FAILED,
                {
                    "capability_id": capability_id,
                    "error": str(exc),
                },
            )
            raise

        self._emit_event(
            _CAPABILITY_INVOKED,
            {
                "capability_id": capability_id,
                "facade": entry.facade,
                "provider_id": entry.provider_id,
                "version": entry.version,
            },
        )
        self._log_debug(f"Invoked capability: {capability_id}")
        return entry

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_event(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit a canonical capability event via the canonical EventBus.

        The canonical ``EventBus.publish`` is async (returns a coroutine). From a
        synchronous business-API call site we cannot ``await`` it, so this method
        bridges to the async bus deterministically using the architecture-approved
        sync-to-async bridge (FIX-FIND-01) established by the sibling Core
        Managers:

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion).
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note — avoiding the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited`` and
          never leaving a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.8.11 names
        like ``CapabilityRegisteredEvent`` / ``CapabilityConflictEvent`` have no
        canonical equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

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

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
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
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 15 — replaces stdlib logging)
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
# Global CapabilityManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_capability_manager: CapabilityManager | None = None
_capability_singleton_lock = threading.Lock()


def get_capability_manager() -> CapabilityManager:
    """Get or create the global CapabilityManager singleton.

    Uses the same lock-guarded pattern as the other Core Managers (Tasks 9–14)
    and the C1–C4 singletons, so concurrent callers cannot double-construct.
    """
    global _global_capability_manager
    with _capability_singleton_lock:
        if _global_capability_manager is None:
            _global_capability_manager = CapabilityManager()
        return _global_capability_manager


def set_capability_manager(manager: CapabilityManager) -> None:
    """Set the global CapabilityManager singleton."""
    global _global_capability_manager
    with _capability_singleton_lock:
        _global_capability_manager = manager


def reset_capability_manager_singleton() -> None:
    """Reset the process-wide CapabilityManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` / ``reset_state_manager_singleton``
    / ``reset_storage_manager_singleton`` / ``reset_health_manager_singleton`` /
    ``reset_resource_manager_singleton`` / ``reset_security_manager_singleton`` /
    C2–C4 resets.
    """
    global _global_capability_manager
    with _capability_singleton_lock:
        _global_capability_manager = None
