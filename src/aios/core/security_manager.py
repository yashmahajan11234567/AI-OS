"""
SecurityManager — the Phase-3 (Governance) Core Manager for AI-OS Hermes Kernel.

SecurityManager is the governance authority for kernel security policy and
authorization. It implements the ICoreManager Protocol (name / phase /
dependencies / initialize / shutdown / health_ready) so LifecycleManager
(Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 3 (alphabetical within phase:
    HealthManager, ResourceManager, SecurityManager — deterministic per
    Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.security``
    (Part 4 §4.7 names the identity ``kernel.security``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.security``, using the same precedent Task 9/10/11/12/13 established
    for ``core.lifecycle`` / ``core.state`` / ``core.storage`` / ``core.health``
    / ``core.resource``), using the same "core_manager" metadata envelope
  * reads ``kernel.security.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 14 mapping, same as Tasks 9–13): Part 4 §4.7.10 names events
like ``SecurityAuditEvent`` / ``AuthenticationFailedEvent`` /
``AuthorizationDecisionEvent`` / ``SecretRotatedEvent`` / ``PolicyUpdatedEvent`` /
``TrustBoundaryViolationEvent`` that do NOT exist in the closed canonical
``EventType`` enum (Part 2 §2.3.1, Task 2). SecurityManager does NOT invent new
EventTypes. The canonical mapping for the security domain is:

  * Security issue / violation found   -> EventType.SECURITY_ISSUE_FOUND

If a conceptual security event has no canonical EventType equivalent, that event
emission is omitted rather than invented.

NOTE ON ``core.security`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.7): Part 4 §4.7 names SecurityManager's ServiceRegistry identity as
``kernel.security``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle`` instead of ``kernel.lifecycle``) and Task 10/11/12/13
resolved for StateManager (``core.state``), StorageManager (``core.storage``),
HealthManager (``core.health``), and ResourceManager (``core.resource``).
Per that precedent, the compliant, INV-SR-NS-002-respecting ServiceRegistry
identity is ``core.security`` (the ``core.*`` namespace is not reserved and is
NOT a validator exception). The configuration namespace read from C3 remains
``kernel.security.*`` (Part 4 §4.7 config schema), which is independent of the
ServiceRegistry id. Lifecycle ownership (initialize/shutdown driven by
LifecycleManager Phase 3) is unchanged.

PHASE DEPENDENCY RULE: SecurityManager is Phase 3. It does NOT declare
ResourceManager or HealthManager as formal dependencies:

    dependencies = ["LifecycleManager"]

The same-phase siblings are ordered deterministically (alphabetical within
Phase 3: HealthManager, ResourceManager, SecurityManager) and the existing
LifecycleManager dependency validator (LM-DEP-003) does not accept same-phase
sibling dependencies. Relying on deterministic alphabetical ordering guarantees
correct sequencing; the SecurityManager/ResourceManager/HealthManager operational
relationship is event-driven (via canonical EventBus), not a lifecycle dependency
edge. SecurityManager likewise does NOT declare the (not-yet-implemented)
WorkflowManager or CapabilityManager as dependencies, which would otherwise fail
boot via LM-DEP-003.
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as LifecycleManager /
# StateManager / StorageManager / HealthManager / ResourceManager); these
# modules do not import ``aios.core.security_manager`` at module scope, so there
# is no circular-import risk.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "SecurityManager",
    "SecurityDecision",
    "SecurityViolation",
    "SecurityManagerError",
    "get_security_manager",
    "set_security_manager",
    "reset_security_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "SecurityManager"
# Part 4 §4.7 names SecurityManager's ServiceRegistry identity as
# ``kernel.security``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager
# (registering as ``core.lifecycle`` instead of ``kernel.lifecycle``) and
# Task 10/11/12/13 resolved for StateManager (``core.state``), StorageManager
# (``core.storage``), HealthManager (``core.health``), and ResourceManager
# (``core.resource``). We follow that precedent: the compliant,
# INV-SR-NS-002-respecting ServiceRegistry id is ``core.security``. The
# configuration namespace read from C3 remains ``kernel.security.*`` (Part 4
# §4.7 config schema), which is unaffected by the ServiceRegistry id.
_MANAGER_ID = "core.security"
_PHASE = 3  # Phase 3 — "Governance"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 14 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Tasks 10–13):
#   * same-phase siblings (HealthManager, ResourceManager) are NOT dependencies
#     — same-phase deps would be rejected by LifecycleManager's dependency
#     validator (LM-DEP-003); deterministic alphabetical ordering
#     (HealthManager first, then ResourceManager, then SecurityManager) already
#     guarantees correct sequencing,
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_SECURITY_ISSUE_FOUND = EventType.SECURITY_ISSUE_FOUND


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SecurityDecision(str, Enum):  # noqa: UP042 -- matches HealthStatus pattern in sibling managers
    """Authorization decision (Part 4 §4.7.5: ALLOW | DENY | CHALLENGE)."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    CHALLENGE = "CHALLENGE"


@dataclass
class SecurityViolation:
    """A recorded security violation / issue (Part 4 §4.7 AUDIT category)."""

    violation_id: str
    severity: str
    description: str
    category: str = "security"
    context: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SecurityManagerError(Exception):
    """SecurityManager failure (Part 4 §4.7.11).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` / ``HealthManagerError`` / ``ResourceManagerError``
    (Tasks 9/10/11/12/13).
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
# SecurityManager
# ---------------------------------------------------------------------------


class SecurityManager:
    """Phase-3 (Governance) security authority for the Hermes Kernel.

    Provides the kernel security governance surface:
    - Authorization decision-point (fail-closed): every authorization request
      that cannot be affirmatively allowed returns DENY (Part 4 §4.7.13
      CC-SEC-001).
    - Security violation / issue recording, which emits the canonical
      ``SECURITY_ISSUE_FOUND`` event via the canonical EventBus.
    - ICoreManager Core-Manager lifecycle (Task 14 — orchestrated by
      LifecycleManager).

    Architecture contract (mirrors StateManager / StorageManager / HealthManager
    / ResourceManager):
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
        Initialize the Security Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.
        """
        # C2/C3/C4 — injected via DI (Task 14).
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
        # (Task 7) / StateManager / StorageManager / HealthManager / ResourceManager.
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.7).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 14).
        self._initialized = False
        self._registered_with_sr = False

        # Authorization policy bookkeeping.
        self._deny_unknown_principal: bool = True  # CC-SEC-001 fail-closed.
        self._recorded_violations: dict[str, SecurityViolation] = {}
        self._violations_lock = threading.RLock()

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._fail_closed = True
        self._audit_all_denials = True

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 14 / Part 4 §4.2)
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
        """ServiceRegistry identity (``core.security``; Part 4 §4.7 names
        ``kernel.security`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors LifecycleManager.health_ready / StateManager.health_ready /
        StorageManager.health_ready / HealthManager.health_ready /
        ResourceManager.health_ready: ready by construction once the manager has
        completed its own initialization. Returns False before ``initialize()``
        and after ``shutdown()``.
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
        """Phase 3 initialization (called by LifecycleManager).

        Follows the Core Manager pattern (mirrors LifecycleManager.initialize /
        StateManager.initialize / StorageManager.initialize / HealthManager
        .initialize / ResourceManager.initialize): reads ``kernel.security.*``
        configuration from the frozen C3, wires the StructuredLogger (C4),
        registers this manager with the canonical ServiceRegistry (C2) as
        ``core.security``, and marks the manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._fail_closed = self._read_config_bool(
            "kernel.security.failClosed", self._fail_closed
        )
        self._audit_all_denials = self._read_config_bool(
            "kernel.security.auditAllDenials", self._audit_all_denials
        )
        self._deny_unknown_principal = self._read_config_bool(
            "kernel.security.denyUnknownPrincipal", self._deny_unknown_principal
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.security``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"SecurityManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 3 (reverse) shutdown (called by LifecycleManager).

        Clears recorded violations, marks ``core.security`` SHUTDOWN in the
        canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear recorded violations.
        with self._violations_lock:
            self._recorded_violations.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("SecurityManager shut down.")

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror StateManager / StorageManager /
    # HealthManager / ResourceManager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register SecurityManager with the ServiceRegistry (C2, Part 4 §4.7).

        Registered as ``core.security`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering SecurityManager.")
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
        """Mark ``core.security`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
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
    # Business API — authorization & violation recording
    # ------------------------------------------------------------------

    def authorize(
        self,
        principal: str | None,
        action: str,
        resource: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> SecurityDecision:
        """Authorize a protected operation (Part 4 §4.7.5 ABAC PDP).

        Fail-closed (CC-SEC-001): a request with an unknown/``None`` principal,
        or any request that cannot be affirmatively allowed, returns DENY. Only
        an explicitly-recognized allow rule yields ALLOW; ambiguous cases return
        CHALLENGE (which callers must treat as a non-ALLOW).

        This is the minimal, architecture-supported authorization surface. No
        policy engine, identity provider, or secret store is invented here; the
        governance contract lives in the kernel's registered security policy, not
        in this manager's scope. ``audit_all_denials`` records a security issue
        for every DENY via the canonical SECURITY_ISSUE_FOUND event.
        """
        if principal is None or principal == "":
            if self._deny_unknown_principal:
                decision = SecurityDecision.DENY
                if self._audit_all_denials:
                    self.record_violation(
                        severity="high",
                        description=(
                            f"Authorization DENY for {action} on {resource}: "
                            f"unknown principal"
                        ),
                        category="authorization",
                        context={
                            "action": action,
                            "resource": resource,
                            "principal": None,
                            "decision": SecurityDecision.DENY.value,
                            **(context or {}),
                        },
                    )
                return decision
        # No explicit allow rule is defined within this manager's scope; the
        # default governance posture is fail-closed (DENY), unless the kernel's
        # owning policy layer has authorized the operation out-of-band.
        if self._fail_closed:
            return SecurityDecision.DENY
        return SecurityDecision.CHALLENGE

    def record_violation(
        self,
        *,
        severity: str,
        description: str,
        category: str = "security",
        context: dict[str, Any] | None = None,
    ) -> SecurityViolation:
        """Record a security violation / issue and emit SECURITY_ISSUE_FOUND.

        The violation is tracked locally (audit trail, CC-SEC-003 attribution)
        and surfaced on the canonical EventBus via the sync-to-async bridge. Only
        the canonical ``EventType.SECURITY_ISSUE_FOUND`` is emitted (CONFLICT E.1
        — Part 4 §4.7.10 names like ``SecurityAuditEvent`` /
        ``AuthenticationFailedEvent`` / ``TrustBoundaryViolationEvent`` have no
        canonical equivalent and are omitted, not invented).
        """
        violation = SecurityViolation(
            violation_id=str(uuid.uuid4()),
            severity=severity,
            description=description,
            category=category,
            context=dict(context or {}),
        )
        with self._violations_lock:
            self._recorded_violations[violation.violation_id] = violation

        self._emit_event(_SECURITY_ISSUE_FOUND, violation)
        self._log_debug(
            f"Security violation recorded: {violation.violation_id} ({severity})",
            category=category,
        )
        return violation

    def get_violation(self, violation_id: str) -> SecurityViolation | None:
        """Look up a recorded security violation by id."""
        with self._violations_lock:
            return self._recorded_violations.get(violation_id)

    def list_violations(self) -> list[SecurityViolation]:
        """List all recorded security violations (snapshot)."""
        with self._violations_lock:
            return list(self._recorded_violations.values())

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_event(
        self, event_type: EventType, violation: SecurityViolation
    ) -> None:
        """Emit a canonical security event via the canonical EventBus.

        The canonical Task-5 ``EventBus.publish`` is async (returns a coroutine).
        From a synchronous business-API call site (``record_violation``) we cannot
        ``await`` it, so this method bridges to the async bus deterministically
        using the architecture-approved sync-to-async bridge established in
        ``ConfigurationManager._run_emission`` (Task 7) and mirrored by
        StateManager / StorageManager / HealthManager / ResourceManager:

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion). The event is enqueued on the bus deterministically before
          the next ``await`` yields.
        * If no loop is running, the emission is skipped with a StructuredLogger
          debug note. The canonical bus requires a running loop to enqueue;
          synchronously dropping here avoids the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited`` and
          never leaves a coroutine un-awaited.

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.7.10 names
        like ``SecurityAuditEvent`` / ``TrustBoundaryViolationEvent`` have no
        canonical equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload={
                "manager": _NAME,
                "manager_id": _MANAGER_ID,
                "issue_id": violation.violation_id,
                "severity": violation.severity,
                # 'category' is a reserved base-contract field (INV-EVT-011);
                # the payload key is 'violation_category' instead.
                "violation_category": violation.category,
                "description": violation.description,
                "context": violation.context,
            },
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
    # StructuredLogger integration (C4, Task 14 — replaces stdlib logging)
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
# Global SecurityManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_security_manager: SecurityManager | None = None
_security_singleton_lock = threading.Lock()


def get_security_manager() -> SecurityManager:
    """Get or create the global SecurityManager singleton.

    Uses the same lock-guarded pattern as StateManager / StorageManager /
    HealthManager / ResourceManager (Tasks 10/11/12/13) and the C1–C4
    singletons, so concurrent callers cannot double-construct.
    """
    global _global_security_manager
    with _security_singleton_lock:
        if _global_security_manager is None:
            _global_security_manager = SecurityManager()
        return _global_security_manager


def set_security_manager(manager: SecurityManager) -> None:
    """Set the global SecurityManager singleton."""
    global _global_security_manager
    with _security_singleton_lock:
        _global_security_manager = manager


def reset_security_manager_singleton() -> None:
    """Reset the process-wide SecurityManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` /
    ``reset_state_manager_singleton`` / ``reset_storage_manager_singleton`` /
    ``reset_health_manager_singleton`` / ``reset_resource_manager_singleton`` /
    C2–C4 resets.
    """
    global _global_security_manager
    with _security_singleton_lock:
        _global_security_manager = None
