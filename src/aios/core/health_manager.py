"""
HealthManager — the Phase-3 (Governance) Core Manager for AI-OS Hermes Kernel.

HealthManager is the governance authority for kernel-component and
service health. It maintains health-check records, runs (or proxies)
checks against registered components, and emits canonical health events.

Task 12 — Core Manager creation (Part 4 §4.6)
----------------------------------------------
HealthManager is the Phase-3 (Governance) Core Manager, alongside
SecurityManager and ResourceManager. It implements the ICoreManager Protocol
(name / phase / dependencies / initialize / shutdown / health_ready) so
LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 3 (alphabetical within phase:
    HealthManager, ResourceManager, SecurityManager — deterministic per
    Part 4 §4.3.4)
  * registers with the canonical ServiceRegistry (C2) as ``core.health``
    (Part 4 §4.6.1 names the identity ``kernel.health``; see the CONFLICT E.1
    note below for the Part-3-vs-Part-4 resolution that maps it to
    ``core.health``, using the same precedent Task 9/10/11 established for
    ``core.lifecycle`` / ``core.state`` / ``core.storage``), using the same
    "core_manager" metadata envelope
  * reads ``kernel.health.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used

CONFLICT E.1 (Task 12 mapping, same as Task 9/10/11): Part 4 §4.6.10 names
events like ``HealthCheckStartedEvent`` / ``ComponentHealthChangedEvent`` /
``SystemHealthComputedEvent`` that do NOT exist in the closed canonical
``EventType`` enum (Part 2 §2.3.1, Task 2). HealthManager does NOT invent new
EventTypes. The canonical mappings for the health domain are:

  * Health check passed   -> EventType.HEALTH_CHECK_PASSED
  * Health check failed   -> EventType.HEALTH_CHECK_FAILED
  * Manager/component     -> EventType.CORE_MANAGER_DEGRADED
  *   degradation

If a conceptual health event has no canonical EventType equivalent, that event
emission is omitted rather than invented.

NOTE ON ``core.health`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4
§4.6.1): Part 4 §4.6.1 names HealthManager's ServiceRegistry identity as
``kernel.health``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
namespace ("not in ServiceRegistry"; registration throws). This is the same
Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager (registering
as ``core.lifecycle`` instead of ``kernel.lifecycle``) and Task 10/11 resolved
for StateManager (``core.state``) and StorageManager (``core.storage``).
Per that precedent, the compliant, INV-SR-NS-002-respecting ServiceRegistry
identity is ``core.health`` (the ``core.*`` namespace is not reserved and is
NOT a validator exception). The configuration namespace read from C3 remains
``kernel.health.*`` (Part 4 §4.6.1 config schema), which is independent of the
ServiceRegistry id. Lifecycle ownership (initialize/shutdown driven by
LifecycleManager Phase 3) is unchanged.

PHASE DEPENDENCY RULE: HealthManager is Phase 3. It does NOT declare
ResourceManager or SecurityManager as formal dependencies:

    dependencies = ["LifecycleManager"]

The same-phase siblings are ordered deterministically (alphabetical within
Phase 3: HealthManager, ResourceManager, SecurityManager) and the existing
LifecycleManager dependency validator (LM-DEP-003) does not accept same-phase
sibling dependencies. Relying on deterministic alphabetical ordering guarantees
correct sequencing; the HealthManager/ResourceManager/SecurityManager
operational relationship is event-driven (via canonical EventBus), not a
lifecycle dependency edge.
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
# StateManager / StorageManager); these modules do not import
# ``aios.core.health_manager`` at module scope, so there is no circular-import
# risk (verified against checkpoint/workflow/kernel/__init__).
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "HealthManager",
    "HealthStatus",
    "HealthCheck",
    "HealthCheckResult",
    "HealthManagerError",
    "get_health_manager",
    "set_health_manager",
    "reset_health_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "HealthManager"
# Part 4 §4.6.1 names HealthManager's ServiceRegistry identity as
# ``kernel.health``, but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel``
# namespace ("not in ServiceRegistry"; registration throws). This is the same
# Part-3-vs-Part-4 contradiction Task 9 resolved for LifecycleManager
# (registering as ``core.lifecycle`` instead of ``kernel.lifecycle``) and
# Task 10/11 resolved for StateManager (``core.state``) and StorageManager
# (``core.storage``). We follow that precedent: the compliant,
# INV-SR-NS-002-respecting ServiceRegistry id is ``core.health``. The
# configuration namespace read from C3 remains ``kernel.health.*`` (Part 4
# §4.6.1 config schema), which is unaffected by the ServiceRegistry id.
_MANAGER_ID = "core.health"
_PHASE = 3  # Phase 3 — "Governance"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 12 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4, same as Task 10/11):
#   * same-phase siblings (ResourceManager, SecurityManager) are NOT dependencies
#     — same-phase deps would be rejected by LifecycleManager's dependency
#     validator (LM-DEP-003); deterministic alphabetical ordering (HealthManager
#     first) already guarantees correct sequencing,
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)

# Canonical event mapping (no invented EventTypes; see CONFLICT E.1 note).
_HEALTH_CHECK_PASSED = EventType.HEALTH_CHECK_PASSED
_HEALTH_CHECK_FAILED = EventType.HEALTH_CHECK_FAILED
_CORE_MANAGER_DEGRADED = EventType.CORE_MANAGER_DEGRADED


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):  # noqa: UP042 -- matches LifecycleState pattern in lifecycle_manager.py
    """Canonical health status (Part 4 §4.6.2)."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass
class HealthCheckResult:
    """Result of a single health check run."""

    component: str
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component": self.component,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "error": self.error,
        }


@dataclass
class HealthCheck:
    """A registered health check callback for a component."""

    component: str
    check_id: str
    enabled: bool = True
    interval_seconds: int = 30
    timeout_seconds: float = 5.0
    last_result: HealthCheckResult | None = None
    consecutive_failures: int = 0


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class HealthManagerError(Exception):
    """HealthManager failure (Part 4 §4.6.11).

    Carries optional diagnostic context: ``rule_id`` (internal
    invariant/rule identifier) and ``original_error`` (the underlying error,
    when wrapping). Mirrors ``LifecycleManagerError`` / ``StateManagerError`` /
    ``StorageManagerError`` (Tasks 9/10/11).
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
# HealthManager
# ---------------------------------------------------------------------------


class HealthManager:
    """Phase-3 (Governance) health authority for the Hermes Kernel.

    Provides:
    - Registration of health-check callbacks for components/services
    - Execution of health checks (sync and async callbacks)
    - Health status tracking (per-component and aggregate)
    - Canonical health-event emission (HEALTH_CHECK_PASSED / FAILED,
      CORE_MANAGER_DEGRADED) via the canonical EventBus
    - ICoreManager Core-Manager lifecycle (Task 12 — orchestrated by
      LifecycleManager)

    Architecture contract (mirrors StateManager / StorageManager):
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
        Initialize the Health Manager.

        C2/C3/C4 dependencies are injected (kernel wires the canonical instances).
        C1 (EventBus) is resolved eagerly from the canonical singleton so both the
        constructor contract (raise if the bus is not up) and the sync
        ``_emit_event`` bridge keep working unchanged.
        """
        # C2/C3/C4 — injected via DI (Task 12).
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
        # (Task 7) / StateManager pattern (Task 10).
        self._pending_tasks: set[asyncio.Future[Any]] = set()

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.6).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 12).
        self._initialized = False
        self._registered_with_sr = False

        # Health-check registry: check_id -> HealthCheck.
        # Keyed by a composite of component + check_id to allow multiple
        # checks per component.
        self._checks: dict[str, HealthCheck] = {}
        self._checks_lock = threading.RLock()

        # Aggregate health state.
        self._overall_status: HealthStatus = HealthStatus.UNKNOWN
        self._status_lock = threading.RLock()

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._default_interval_seconds = 30
        self._default_timeout_seconds = 5.0
        self._failure_threshold = 3
        self._shutdown_timeout_ms = 5000

        # M12-T6 #53 — kernel lifecycle recovery integration. The kernel wires
        # the authoritative LifecycleManager here (see
        # ``HermesKernel._init_lifecycle_manager``); HealthManager never
        # constructs or imports a second one (single-lifecycle-authority
        # invariant). Kept ``None``-able so the Task-12 constructor contract
        # (C1 raise-on-missing only) is unchanged for pre-boot/test callers.
        self._lifecycle_manager: Any | None = None

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 12 / Part 4 §4.2)
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
        """ServiceRegistry identity (``core.health``; Part 4 §4.6.1 names
        ``kernel.health`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    @property
    def overall_status(self) -> HealthStatus:
        """Aggregate health status across all registered checks."""
        with self._status_lock:
            return self._overall_status

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors LifecycleManager.health_ready / StateManager.health_ready:
        ready by construction once the manager has completed its own
        initialization. Returns False before ``initialize()`` and after
        ``shutdown()``.
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
        StateManager.initialize): reads ``kernel.health.*`` configuration from
        the frozen C3, wires the StructuredLogger (C4), registers this manager
        with the canonical ServiceRegistry (C2) as ``core.health``, and marks
        the manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._default_interval_seconds = self._read_config_int(
            "kernel.health.defaultIntervalSeconds", self._default_interval_seconds
        )
        self._default_timeout_seconds = float(
            self._read_config_int(
                "kernel.health.defaultTimeoutSeconds",
                int(self._default_timeout_seconds),
            )
        )
        self._failure_threshold = self._read_config_int(
            "kernel.health.failureThreshold", self._failure_threshold
        )
        self._shutdown_timeout_ms = self._read_config_int(
            "kernel.health.shutdownTimeoutMs", self._shutdown_timeout_ms
        )

        # 2. Register with the canonical ServiceRegistry (C2) as ``core.health``.
        await self.register_with_service_registry()

        # 3. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"HealthManager initialized (phase {self.phase}, "
            f"manager_id={_MANAGER_ID})."
        )

    async def shutdown(self) -> None:
        """Phase 3 (reverse) shutdown (called by LifecycleManager).

        Clears registered health checks, marks ``core.health`` SHUTDOWN in the
        canonical ServiceRegistry (C2), and clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Clear registered checks.
        with self._checks_lock:
            self._checks.clear()

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("HealthManager shut down.")

    # ------------------------------------------------------------------
    # M12-T6 #53 — kernel lifecycle recovery integration
    # ------------------------------------------------------------------

    def set_lifecycle_manager_ref(self, lifecycle_manager: Any) -> None:
        """Wire the authoritative LifecycleManager for recovery coordination.

        Called by the kernel (production) in ``_init_lifecycle_manager`` once both
        the LifecycleManager (Phase 1) and HealthManager (Phase 3) exist.
        HealthManager only *calls into* the LifecycleManager's published recovery
        API (``mark_degraded`` / ``begin_recovery`` / ``complete_recovery``) —
        it never mutates lifecycle state itself, so the sole-lifecycle-authority
        invariant (Part 4 §4.3.3) is preserved. This is the same
        kernel-owned-construction DI pattern the other Core Managers use.
        """
        if self._lifecycle_manager is not None and self._lifecycle_manager is not lifecycle_manager:
            self._log_debug(
                "set_lifecycle_manager_ref: replacing previously wired LifecycleManager."
            )
        self._lifecycle_manager = lifecycle_manager

    def _trigger_lifecycle_degraded(self, affected_components: list[str]) -> None:
        """M12-T6 #53 — production degraded trigger (OPERATIONAL -> DEGRADED).

        When the health aggregate is DEGRADED and the kernel lifecycle is still
        OPERATIONAL, drive the authoritative LifecycleManager into DEGRADED via
        its async ``mark_degraded`` API. This is the sync business-API bridge:

        * A running loop exists -> the coroutine is scheduled deterministically
          (same ``_pending_tasks`` strong-reference pattern as ``_emit_health_event``).
        * No running loop -> the trigger cannot run; log (debug) and return
          (HealthManager has no thread of its own; the caller owns the loop).

        Guarded: no-op unless the lifecycle is currently OPERATIONAL, so repeated
        DEGRADED health records never attempt an invalid lifecycle transition
        (DEGRADED -> DEGRADED) and never re-enter while DEGRADED/RECOVERY (the
        LifecycleManager remains the transition validator of record).
        """
        lm = self._lifecycle_manager
        if lm is None:
            return
        try:
            # Import locally: read-only state inspection only (no authority transfer).
            from aios.core.lifecycle_manager import LifecycleState

            if lm.state is not LifecycleState.OPERATIONAL:
                return
            coro = lm.mark_degraded(affected=affected_components)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                self._log_debug(
                    "DEGRADED health recorded but no running loop; lifecycle "
                    "degraded trigger deferred to the next call site with a loop."
                )
                return
            if not loop.is_running():
                return
            task = asyncio.ensure_future(coro, loop=loop)
            self._pending_tasks.add(task)
            task.add_done_callback(self._pending_tasks.discard)
            self._log_info(
                "DEGRADED health aggregate triggered lifecycle mark_degraded "
                f"(affected={affected_components})."
            )
        except Exception as exc:  # noqa: BLE001
            # The degraded signal itself must never take the health path down.
            self._log_warning(f"Lifecycle mark_degraded trigger failed: {exc}")

    async def trigger_recovery(
        self, affected: list[str] | None = None
    ) -> dict[str, Any]:
        """M12-T6 #53 — coordinate kernel lifecycle recovery (production path).

        This is the HealthManager-coordinated recovery strategy that
        ``LifecycleManager.begin_recovery``'s docstring deferred to ("later
        task"). Flow (all transitions still owned by LifecycleManager):

        1. Verify the HealthManager is initialized and a lifecycle ref is wired
           (fail loud — never silently claim recovery).
        2. ``begin_recovery(affected)`` — DEGRADED -> RECOVERY_IN_PROGRESS.
        3. Attempt a real recovery action using existing AI-OS mechanisms only:
           for every affected engineering service discoverable in the canonical
           ServiceRegistry, re-probe ``on_health_check()`` and restart
           (``stop()`` then ``start()`` — the same BaseService primitives
           ``_start_services`` uses) when the probe fails.
        4. Verify recovery by re-probing every affected service after restart.
        5. ``complete_recovery(success=verified)`` — OPERATIONAL on verified
           success, DEGRADED otherwise (explicit, never falsely operational).

        Returns a diagnostic record (component names probed/restarted, verdict).

        Scope guards:
        * Recursion guard: no-op record if the lifecycle is already
          RECOVERY_IN_PROGRESS (recovery is never re-entered recursively).
        * The recovery action targets ONLY engineering services registered in
          the canonical ServiceRegistry; it does not touch Core Managers
          (LifecycleManager owns their phases), M10 autonomy services
          (M10RecoveryManager's scope), or M13 bounded external resources
          (FailureRecoveryManager's scope).
        * No security boundary is crossed: restarting the kernel's own already-
          authorized engineering services is kernel-internal runtime authority
          (the same authority ``_start_services`` exercises at boot).
        """
        lm = self._lifecycle_manager
        if lm is None or not self._initialized:
            raise HealthManagerError(
                "trigger_recovery requires an initialized HealthManager with a "
                "kernel-wired LifecycleManager (start the kernel first).",
                rule_id="HM-REC-001",
            )

        # Read-only state inspection (lifecycle transition validation stays in LM).
        from aios.core.lifecycle_manager import LifecycleState

        cur = lm.state
        if cur is LifecycleState.RECOVERY_IN_PROGRESS:
            self._log_debug("Recovery already in progress; no re-entry.")
            return {"status": "already_in_progress", "affected": list(affected or [])}
        if cur is not LifecycleState.DEGRADED:
            # Same rule the LifecycleManager enforces (LM-REC-001); surfaced as
            # an explicit no-op record rather than an exception so periodic
            # health loops never crash on a healthy kernel.
            self._log_info(
                f"trigger_recovery no-op: lifecycle state is {cur.value}, "
                "not DEGRADED."
            )
            return {"status": "not_degraded", "affected": list(affected or [])}

        affected_list = list(affected or [])

        # 2. DEGRADED -> RECOVERY_IN_PROGRESS (LifecycleManager authority).
        await lm.begin_recovery(affected=affected_list)
        self._log_info(
            f"Kernel lifecycle recovery started (affected={affected_list})."
        )

        record: dict[str, Any] = {
            "status": "attempted",
            "affected": affected_list,
            "probed": [],
            "restarted": [],
            "verified": [],
            "failed": [],
        }

        # 3. Attempt the recovery action using existing AI-OS mechanisms: for
        #    each affected engineering service visible in the canonical C2, stop
        #    and restart it via its own BaseService lifecycle primitives.
        sr = self._service_registry
        for component in affected_list:
            service_id = f"engineering.{component}"
            svc = sr.get_service(service_id) if sr is not None else None
            if svc is None:
                # Not an engineering service in C2 (Core Manager, external
                # resource, or unknown): out of this recovery action's scope —
                # recorded, not faked.
                record["failed"].append(component)
                self._log_debug(
                    f"Recovery action skipped for '{component}': no engineering "
                    "service in the canonical ServiceRegistry (out of kernel "
                    "lifecycle recovery scope)."
                )
                continue
            record["probed"].append(component)
            try:
                try:
                    healthy = await svc.on_health_check()
                except Exception:  # noqa: BLE001
                    healthy = False
                if healthy:
                    # Service self-recovered; no restart needed.
                    record["verified"].append(component)
                    continue
                await svc.stop()
                await svc.start()
                record["restarted"].append(component)
            except Exception as exc:  # noqa: BLE001
                record["failed"].append(component)
                self._log_warning(
                    f"Recovery restart failed for '{component}': {exc}"
                )

        # 4. Verify recovery: re-probe every affected service that has a probe.
        verified_all = True
        for component in [c for c in record["probed"] if c not in record["failed"]]:
            svc = sr.get_service(f"engineering.{component}") if sr is not None else None
            if svc is None:
                # Service no longer discoverable after restart — cannot verify.
                verified_all = False
                record["failed"].append(component)
                continue
            try:
                if await svc.on_health_check():
                    record["verified"].append(component)
                else:
                    verified_all = False
                    record["failed"].append(component)
            except Exception:  # noqa: BLE001
                verified_all = False
                record["failed"].append(component)

        # Any affected component with no actionable in-scope service and no
        # verification cannot be counted as recovered — the kernel stays honest.
        verified = (
            verified_all
            and len(record["failed"]) == 0
            and len(record["verified"]) == len(affected_list)
        )

        # 5. RECOVERY_IN_PROGRESS -> OPERATIONAL | DEGRADED (LM authority).
        await lm.complete_recovery(success=verified)
        record["status"] = "recovered" if verified else "recovery_failed"
        self._log_info(
            f"Kernel lifecycle recovery "
            f"{'verified' if verified else 'FAILED'} "
            f"(restarted={record['restarted']}, verified={record['verified']}, "
            f"failed={record['failed']})."
        )
        return record

    # ------------------------------------------------------------------
    # ServiceRegistry integration (mirror StateManager / StorageManager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register HealthManager with the ServiceRegistry (C2, Part 4 §4.6.9).

        Registered as ``core.health`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering HealthManager.")
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
        """Mark ``core.health`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
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
    # Health management business API
    # ------------------------------------------------------------------

    def _check_key(self, component: str, check_id: str) -> str:
        """Build the registry key for a check."""
        return f"{component}:{check_id}"

    def register_check(
        self,
        component: str,
        check_id: str,
        enabled: bool = True,
        interval_seconds: int | None = None,
        timeout_seconds: float | None = None,
    ) -> HealthCheck:
        """Register a health check for a component (Part 4 §4.6.3).

        Returns the created HealthCheck entry. The actual check callback is
        invoked via ``run_check``; this only registers metadata so the manager
        can track expected checks and their cadence.
        """
        key = self._check_key(component, check_id)
        with self._checks_lock:
            hc = HealthCheck(
                component=component,
                check_id=check_id,
                enabled=enabled,
                interval_seconds=interval_seconds or self._default_interval_seconds,
                timeout_seconds=timeout_seconds or self._default_timeout_seconds,
            )
            self._checks[key] = hc
        self._log_debug(f"Registered health check: {component}.{check_id}")
        return hc

    def unregister_check(self, component: str, check_id: str) -> bool:
        """Remove a previously registered health check. Returns True if removed."""
        key = self._check_key(component, check_id)
        with self._checks_lock:
            return self._checks.pop(key, None) is not None

    def list_checks(self) -> list[HealthCheck]:
        """List all registered health checks (snapshot)."""
        with self._checks_lock:
            return list(self._checks.values())

    def get_check(self, component: str, check_id: str) -> HealthCheck | None:
        """Look up a registered health check by component + check_id."""
        key = self._check_key(component, check_id)
        with self._checks_lock:
            return self._checks.get(key)

    def get_component_health(self, component: str) -> dict[str, Any] | None:
        """Get the latest health status for a component.

        Returns the most recent HealthCheckResult for any check registered
        against ``component``, or None if no checks are registered.
        """
        with self._checks_lock:
            results = [
                hc.last_result
                for hc in self._checks.values()
                if hc.component == component and hc.last_result is not None
            ]
        if not results:
            return None
        # Most recent by timestamp.
        latest = max(results, key=lambda r: r.timestamp)
        return latest.to_dict()

    def get_all_health(self) -> dict[str, Any]:
        """Get aggregate health snapshot for all registered components.

        Returns a dict with:
        - ``overall``: aggregate HealthStatus
        - ``components``: per-component latest status
        - ``total_checks``: number of registered checks
        - ``healthy_checks``: number of checks whose last result was HEALTHY
        - ``degraded_checks``: number of checks in DEGRADED state
        - ``unhealthy_checks``: number of checks in UNHEALTHY state
        """
        with self._checks_lock:
            checks = list(self._checks.values())
        component_status: dict[str, str] = {}
        healthy = degraded = unhealthy = unknown = 0
        for hc in checks:
            if hc.last_result is None:
                unknown += 1
                component_status.setdefault(hc.component, HealthStatus.UNKNOWN.value)
                continue
            status = hc.last_result.status
            component_status[hc.component] = status.value
            if status is HealthStatus.HEALTHY:
                healthy += 1
            elif status is HealthStatus.DEGRADED:
                degraded += 1
            elif status is HealthStatus.UNHEALTHY:
                unhealthy += 1
            else:
                unknown += 1
        with self._status_lock:
            overall = self._overall_status
        return {
            "overall": overall.value,
            "components": component_status,
            "total_checks": len(checks),
            "healthy_checks": healthy,
            "degraded_checks": degraded,
            "unhealthy_checks": unhealthy,
            "unknown_checks": unknown,
        }

    def record_health(
        self,
        component: str,
        check_id: str,
        status: HealthStatus,
        *,
        message: str = "",
        error: str | None = None,
    ) -> HealthCheckResult:
        """Record a health check result (Part 4 §4.6.4).

        This is the synchronous entry point used by components to report
        their own health. The result is stored and the appropriate canonical
        event is emitted via the sync-to-async EventBus bridge.

        Returns the recorded HealthCheckResult.
        """
        result = HealthCheckResult(
            component=component,
            status=status,
            message=message,
            error=error,
        )
        key = self._check_key(component, check_id)
        with self._checks_lock:
            hc = self._checks.get(key)
            if hc is None:
                # Auto-register a check if none exists for this component/id.
                hc = HealthCheck(component=component, check_id=check_id)
            hc.last_result = result
            if status is HealthStatus.HEALTHY:
                hc.consecutive_failures = 0
            else:
                hc.consecutive_failures += 1
            self._checks[key] = hc

        # Update aggregate status (deterministic: UNHEALTHY > DEGRADED > HEALTHY > UNKNOWN).
        self._recompute_overall()

        # M12-T6 #53 — production degraded trigger: when the health aggregate
        # is DEGRADED and the kernel lifecycle is still OPERATIONAL, drive the
        # authoritative LifecycleManager into DEGRADED (guarded no-op otherwise,
        # including when the aggregate is UNHEALTHY — UNHEALTHY is a terminal
        # canonical-health condition, not a recoverable degraded state).
        if status is HealthStatus.DEGRADED and self.overall_status is HealthStatus.DEGRADED:
            with self._checks_lock:
                degraded_components = sorted(
                    {
                        hc.component
                        for hc in self._checks.values()
                        if hc.last_result is not None
                        and hc.last_result.status is HealthStatus.DEGRADED
                    }
                )
            self._trigger_lifecycle_degraded(degraded_components)

        # Emit canonical health event (CONFLICT E.1: only canonical EventTypes).
        if status is HealthStatus.HEALTHY:
            self._emit_health_event(_HEALTH_CHECK_PASSED, result)
        elif status is HealthStatus.UNHEALTHY:
            self._emit_health_event(_HEALTH_CHECK_FAILED, result)
        elif status is HealthStatus.DEGRADED:
            self._emit_health_event(_CORE_MANAGER_DEGRADED, result)

        self._log_debug(
            f"Health recorded: {component}.{check_id} -> {status.value}",
            component=component,
            check_id=check_id,
            status=status.value,
        )
        return result

    def degraded_components(self) -> list[str]:
        """Components whose latest recorded result is DEGRADED (M12-T6 #53).

        Snapshot accessor used by the kernel's recovery entry point to determine
        the default ``affected`` set for a recovery attempt. Read-only.
        """
        with self._checks_lock:
            return sorted(
                {
                    hc.component
                    for hc in self._checks.values()
                    if hc.last_result is not None
                    and hc.last_result.status is HealthStatus.DEGRADED
                }
            )

    async def drain_pending_tasks(self) -> None:
        """Await all in-flight sync-bridge tasks (event emissions, M12-T6
        lifecycle triggers) scheduled from synchronous business API calls.

        Callers of ``record_health`` that need to observe the triggered lifecycle
        transition deterministically await this. No-op when nothing is pending.
        """
        pending = [t for t in list(self._pending_tasks) if not t.done()]
        for t in pending:
            try:
                await t
            except Exception:  # noqa: BLE001
                # Bridge tasks are fire-and-forget by design; a failed emission
                # or trigger is logged at its call site. Never re-raise here.
                pass

    def _recompute_overall(self) -> None:
        """Recompute the aggregate health status from all check results.

        Precedence (worst-wins): UNHEALTHY > DEGRADED > HEALTHY > UNKNOWN.
        """
        with self._checks_lock:
            statuses = [
                hc.last_result.status
                for hc in self._checks.values()
                if hc.last_result is not None
            ]
        if not statuses:
            new_status = HealthStatus.UNKNOWN
        elif HealthStatus.UNHEALTHY in statuses:
            new_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            new_status = HealthStatus.DEGRADED
        elif HealthStatus.HEALTHY in statuses:
            new_status = HealthStatus.HEALTHY
        else:
            new_status = HealthStatus.UNKNOWN
        with self._status_lock:
            self._overall_status = new_status

    # ------------------------------------------------------------------
    # Event emission (canonical EventTypes only; CONFLICT E.1)
    # ------------------------------------------------------------------

    def _emit_health_event(self, event_type: EventType, result: HealthCheckResult) -> None:
        """Emit a canonical health event via the canonical EventBus.

        The canonical Task-5 ``EventBus.publish`` is async (returns a coroutine).
        From a synchronous business-API call site (e.g. ``record_health``)
        we cannot ``await`` it, so this method bridges to the async bus
        deterministically using the architecture-approved sync-to-async bridge
        established in ``ConfigurationManager._run_emission`` (Task 7) and
        mirrored by StateManager / StorageManager (Tasks 10/11):

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

        Only canonical EventTypes are emitted (CONFLICT E.1: Part 4 §4.6.10
        names like ``HealthCheckStartedEvent`` / ``ComponentHealthChangedEvent``
        have no canonical equivalent and are omitted, not invented).
        """
        bus = self._event_bus
        if bus is None:
            return

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload={
                "component": result.component,
                "status": result.status.value,
                "message": result.message,
                "error": result.error,
                "checked_at": result.timestamp.isoformat(),
                "manager": _NAME,
                "manager_id": _MANAGER_ID,
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
    # StructuredLogger integration (C4, Task 12 — replaces stdlib logging)
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
# Global HealthManager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_health_manager: HealthManager | None = None
_health_singleton_lock = threading.Lock()


def get_health_manager() -> HealthManager:
    """Get or create the global HealthManager singleton.

    Uses the same lock-guarded pattern as StateManager / StorageManager
    (Tasks 10/11) and the C1–C4 singletons, so concurrent callers cannot
    double-construct.
    """
    global _global_health_manager
    with _health_singleton_lock:
        if _global_health_manager is None:
            _global_health_manager = HealthManager()
        return _global_health_manager


def set_health_manager(manager: HealthManager) -> None:
    """Set the global HealthManager singleton."""
    global _global_health_manager
    with _health_singleton_lock:
        _global_health_manager = manager


def reset_health_manager_singleton() -> None:
    """Reset the process-wide HealthManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` /
    ``reset_state_manager_singleton`` / ``reset_storage_manager_singleton`` /
    C2–C4 resets.
    """
    global _global_health_manager
    with _health_singleton_lock:
        _global_health_manager = None
