"""
LifecycleManager — the first Core Manager (Part 4 §4.3).

This module implements the **sole authoritative controller** of the Hermes
Kernel's operational lifecycle, per Part 4 §4.3. It owns the kernel lifecycle
state machine, phase-execution sequencing, initialization ordering, shutdown
ordering, rollback coordination, and recovery coordination.

Scope (Task 9)
--------------
Task 9 owns LifecycleManager *only*. It does NOT own, implement, or migrate any
other Core Manager (StateManager, StorageManager, SecurityManager,
ResourceManager, HealthManager, CapabilityManager, WorkflowManager,
ObservabilityManager) or IdentityProvider. Those are later tasks. Where the
architecture references a manager that does not yet exist, LifecycleManager:

  * declares that manager's phase topology / dependency metadata (so the
    sequencing model is stable and deterministic), but
  * does NOT instantiate or fake it,
  * defers empty phases with an explicit, logged boundary, and
  * reaches OPERATIONAL once all *present* managers are ready and the
    readiness gate passes (the multi-manager HealthManager gate becomes active
    once HealthManager is implemented in a later task).

Integration with the completed Core Components (Tasks 1–8)
----------------------------------------------------------
LifecycleManager consumes (never re-implements) the four Core Components:

  * EventBus (C1)            — emits lifecycle / phase events.
  * ServiceRegistry (C2)     — registers itself as ``core.lifecycle``.
  * ConfigurationManager (C3)— reads ``kernel.lifecycle.*`` configuration.
  * StructuredLogger (C4)    — structured diagnostics.

Event-type conflict (documented, not silently resolved)
-------------------------------------------------------
Part 4 §4.3.10 names ``KernelLifecycleEvent``, ``KernelPhaseCompletedEvent``,
``KernelDegradedEvent``, ``KernelRecoveryEvent``. These names do NOT exist in
the closed canonical ``EventType`` enum (Task 2, Part 2 §2.3.1). Part 14
documents this as CONFLICT E.1. Per the Task-9 CRITICAL EVENT TYPE RULE,
LifecycleManager does NOT invent new EventTypes. Instead it maps each lifecycle
emission to the closest *canonical* EventType that is architecturally valid and
records the intended Part-4 name in the event payload (``event_name``). The two
transitions with no canonical equivalent (RECOVERY_IN_PROGRESS; rollback target
UNINITIALIZED) emit no fabricated event and are reported in the conflict log.

No ICoreManager interface exists anywhere in the repository, so a minimal
:class:`ICoreManager` Protocol is defined here (Task-9 scope only — no broad
framework is invented).
"""

from __future__ import annotations

import asyncio
import threading
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol, runtime_checkable


@dataclass
class LifecycleConfig:
    """Configuration for LifecycleManager (test compatibility)."""
    pass

# Core Components (Tasks 1–8) — consumed, never re-implemented.
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import EventBus
from aios.events.core.event import Event
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "LifecycleState",
    "LifecycleConfig",
    "LifecycleManagerError",
    "CoreManagerPhase",
    "ICoreManager",
    "LifecycleManager",
    "get_lifecycle_manager",
    "set_lifecycle_manager",
    "reset_lifecycle_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "LifecycleManager"
_MANAGER_ID = "core.lifecycle"  # Part 4 says "kernel.lifecycle"; the
# ServiceRegistry reserves the `kernel` namespace (INV-SR-NS-002), so we use
# `core.lifecycle`. See Architecture Conflicts in the task report.
_PHASE = 1
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)

# Canonical-event mapping tables are defined AFTER LifecycleState (below), since
# they reference it at module import time.


# ---------------------------------------------------------------------------
# Lifecycle state machine (Part 4 §4.3.3)
# ---------------------------------------------------------------------------


class LifecycleState(str, Enum):  # noqa: UP042 -- matches canonical EventType (str, Enum) form
    """Kernel lifecycle states (Part 4 §4.3.3).

    The single source of truth for kernel lifecycle state is owned exclusively
    by LifecycleManager; no other component mutates it.
    """

    UNINITIALIZED = "UNINITIALIZED"
    INITIALIZING = "INITIALIZING"
    OPERATIONAL = "OPERATIONAL"
    DEGRADED = "DEGRADED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    TERMINATED = "TERMINATED"
    ROLLBACK_IN_PROGRESS = "ROLLBACK_IN_PROGRESS"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"


# Valid transitions per Part 4 §4.3.3 table (deterministic, closed).
_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.UNINITIALIZED: frozenset(
        {
            LifecycleState.INITIALIZING,
            LifecycleState.SHUTTING_DOWN,
            LifecycleState.TERMINATED,
        }
    ),
    LifecycleState.INITIALIZING: frozenset(
        {
            LifecycleState.OPERATIONAL,
            LifecycleState.ROLLBACK_IN_PROGRESS,
            LifecycleState.TERMINATED,
        }
    ),
    LifecycleState.OPERATIONAL: frozenset(
        {
            LifecycleState.DEGRADED,
            LifecycleState.SHUTTING_DOWN,
            LifecycleState.ROLLBACK_IN_PROGRESS,
        }
    ),
    LifecycleState.DEGRADED: frozenset(
        {
            LifecycleState.OPERATIONAL,
            LifecycleState.RECOVERY_IN_PROGRESS,
            LifecycleState.SHUTTING_DOWN,
        }
    ),
    LifecycleState.SHUTTING_DOWN: frozenset({LifecycleState.TERMINATED}),
    LifecycleState.TERMINATED: frozenset(),  # terminal
    LifecycleState.ROLLBACK_IN_PROGRESS: frozenset(
        {LifecycleState.UNINITIALIZED, LifecycleState.TERMINATED}
    ),
    LifecycleState.RECOVERY_IN_PROGRESS: frozenset(
        {
            LifecycleState.OPERATIONAL,
            LifecycleState.DEGRADED,
            LifecycleState.SHUTTING_DOWN,
        }
    ),
}


# Canonical EventType mapped to each lifecycle state on entry. ``None`` means no
# canonical Part-2 event exists for that transition (documented conflict E.1);
# LifecycleManager emits no fabricated event and records the intended Part-4
# name in the transition payload instead.
_STATE_TO_EVENT: dict[LifecycleState, EventType | None] = {
    LifecycleState.UNINITIALIZED: None,  # rollback target; no canonical event
    LifecycleState.INITIALIZING: EventType.KERNEL_INITIALIZATION_STARTED,
    LifecycleState.OPERATIONAL: EventType.KERNEL_READY,
    LifecycleState.DEGRADED: EventType.CORE_MANAGER_DEGRADED,
    LifecycleState.SHUTTING_DOWN: EventType.KERNEL_SHUTDOWN_STARTED,
    LifecycleState.TERMINATED: EventType.KERNEL_TERMINATED,
    LifecycleState.ROLLBACK_IN_PROGRESS: EventType.KERNEL_INITIALIZATION_FAILED,
    LifecycleState.RECOVERY_IN_PROGRESS: None,  # no canonical recovery event (E.1)
}

# Intended Part-4 event name per state (for payload traceability only).
_STATE_TO_INTENDED_EVENT: dict[LifecycleState, str] = {
    LifecycleState.UNINITIALIZED: "KernelLifecycleEvent",
    LifecycleState.INITIALIZING: "KernelLifecycleEvent",
    LifecycleState.OPERATIONAL: "KernelLifecycleEvent",
    LifecycleState.DEGRADED: "KernelDegradedEvent",
    LifecycleState.SHUTTING_DOWN: "KernelLifecycleEvent",
    LifecycleState.TERMINATED: "KernelLifecycleEvent",
    LifecycleState.ROLLBACK_IN_PROGRESS: "KernelLifecycleEvent",
    LifecycleState.RECOVERY_IN_PROGRESS: "KernelRecoveryEvent",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class LifecycleManagerError(Exception):
    """LifecycleManager failure (Part 4 §4.3.11).

    Carries optional diagnostic context: ``original_error`` (the error that
    triggered a rollback, if any) and ``rollback_errors`` (errors encountered
    while rolling back, kept distinct from the original failure per §4.3.7).
    """

    def __init__(
        self,
        message: str,
        *,
        rule_id: str | None = None,
        original_error: BaseException | None = None,
        rollback_errors: list[BaseException] | None = None,
    ) -> None:
        self.rule_id = rule_id
        self.original_error = original_error
        self.rollback_errors: list[BaseException] = list(rollback_errors or [])
        super().__init__(message)

    def __str__(self) -> str:
        base = super().__str__()
        if self.original_error is not None:
            base += f" [original_error={type(self.original_error).__name__}: {self.original_error}]"
        if self.rollback_errors:
            base += (
                " [rollback_errors="
                + "; ".join(f"{type(e).__name__}: {e}" for e in self.rollback_errors)
                + "]"
            )
        return base


# ---------------------------------------------------------------------------
# Core Manager contract (minimal; no formal ICoreManager exists in repo)
# ---------------------------------------------------------------------------


@runtime_checkable
class ICoreManager(Protocol):
    """Minimal Core Manager contract (Task-9 scope).

    Future Core Managers (Tasks 10+) are expected to satisfy this surface so
    LifecycleManager can orchestrate them deterministically. No broad framework
    is invented here.
    """

    @property
    def name(self) -> str: ...

    @property
    def phase(self) -> int: ...

    @property
    def dependencies(self) -> list[str]: ...

    async def initialize(self) -> Any: ...

    async def shutdown(self) -> Any: ...

    def health_ready(self) -> bool: ...


# ---------------------------------------------------------------------------
# Phase topology (Part 4 §4.2.3 / §4.2.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoreManagerPhase:
    """Declarative description of one Core Manager initialization/shutdown phase.

    Manager names are declared so sequencing is deterministic; the actual
    manager objects are resolved at runtime from the manager registry (populated
    by the kernel as later managers are implemented). Phases with no present
    managers are deferred (owned by future tasks).
    """

    phase: int
    name: str
    managers: tuple[str, ...]
    depends_on: tuple[int, ...] = ()


def _build_phase_topology() -> list[CoreManagerPhase]:
    """The five Core Manager phases (Part 4 §4.2.3), in strict order."""
    return [
        CoreManagerPhase(1, "Foundation", ("LifecycleManager",), ()),
        CoreManagerPhase(
            2, "State & Storage", ("StateManager", "StorageManager"), (1,)
        ),
        CoreManagerPhase(
            3,
            "Governance",
            ("SecurityManager", "ResourceManager", "HealthManager"),
            (1, 2),
        ),
        CoreManagerPhase(
            4, "Execution", ("CapabilityManager", "WorkflowManager"), (1, 2, 3)
        ),
        CoreManagerPhase(5, "Observability", ("ObservabilityManager",), (1, 2, 3, 4)),
    ]


# ---------------------------------------------------------------------------
# LifecycleManager
# ---------------------------------------------------------------------------


class LifecycleManager:
    """Sole authoritative controller of kernel lifecycle (Part 4 §4.3).

    Thread-safety: an :class:`asyncio.Lock` serializes lifecycle operations
    (initialize / shutdown / rollback / recovery) so concurrent initialize and
    shutdown cannot interleave; a :class:`threading.Lock` guards synchronous
    reads of ``state``.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus | None = None,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
        kernel: Any | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._service_registry = service_registry
        self._configuration = configuration_manager
        self._logger = logger
        self._kernel = kernel

        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        self._state = LifecycleState.UNINITIALIZED
        self._state_lock = threading.Lock()
        self._op_lock = asyncio.Lock()

        # Registered Core Managers keyed by name (the kernel populates these as
        # later managers are implemented). LifecycleManager itself is the
        # orchestrator AND the sole present Phase-1 (Foundation) manager in Task 9,
        # so it self-registers to keep phase-1 sequencing/events deterministic.
        self._managers: dict[str, ICoreManager] = {_NAME: self}

        # Deterministic snapshot of initialization order: list of phases, each a
        # list of manager names in alphabetical (within-phase) order. Drives
        # reverse-order shutdown.
        self._initialized_order: list[list[str]] = []

        # Phase topology (declarative; phases with no present managers deferred).
        self._phase_topology = _build_phase_topology()

        # Configuration (read once from frozen ConfigurationManager; never mutated).
        self._shutdown_timeout_ms = self._read_config_int(
            "kernel.lifecycle.shutdownTimeoutMs", 30000
        )
        self._rollback_target = self._read_config_str(
            "kernel.lifecycle.rollbackTarget", "UNINITIALIZED"
        )

        # Diagnostic context.
        self._last_rollback_errors: list[BaseException] = []
        self._last_original_error: BaseException | None = None
        self._registered_with_sr = False

    # --- ICoreManager surface (LifecycleManager is also a managed phase-1 mgr) -

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """LifecycleManager is Phase 1 (Foundation, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Components LifecycleManager consumes (Tasks 1–8)."""
        return list(_COMPONENT_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.lifecycle``; see conflict report)."""
        return _MANAGER_ID

    def health_ready(self) -> bool:
        """ICoreManager readiness probe.

        LifecycleManager is the orchestrator and is ready by construction (it is
        running the lifecycle). It is never "not ready", so this always returns
        True — the readiness gate gates on *other* registered managers.
        """
        return True

    # --- state (thread-safe read) -------------------------------------------

    @property
    def state(self) -> LifecycleState:
        """Current kernel lifecycle state (single source of truth)."""
        with self._state_lock:
            return self._state

    @property
    def is_operational(self) -> bool:
        return self.state is LifecycleState.OPERATIONAL

    @property
    def is_terminated(self) -> bool:
        return self.state is LifecycleState.TERMINATED

    @property
    def is_initialized(self) -> bool:
        """True once the manager has left UNINITIALIZED (init or rollback done)."""
        with self._state_lock:
            return self._state is not LifecycleState.UNINITIALIZED

    @property
    def phase_plan(self) -> list[dict[str, Any]]:
        """Declarative phase topology (diagnostics / tests)."""
        return [
            {
                "phase": p.phase,
                "name": p.name,
                "managers": list(p.managers),
                "depends_on": list(p.depends_on),
            }
            for p in self._phase_topology
        ]

    @property
    def initialized_managers(self) -> list[str]:
        """Flat list of managers initialized, in execution order."""
        out: list[str] = []
        for phase in self._initialized_order:
            out.extend(phase)
        return out

    async def start(self) -> None:
        """Start the LifecycleManager (alias for initialize)."""
        await self.initialize()

    async def stop(self) -> None:
        """Stop the LifecycleManager (alias for shutdown)."""
        await self.shutdown()

    # --- manager registry (extension point for future managers) ------------

    def register_manager(self, manager: ICoreManager) -> None:
        """Register a Core Manager for orchestration (kernel populates later tasks).

        The manager's name must appear in the declared phase topology
        (Part 4 §4.2.3); otherwise it is rejected (unknown manager).
        """
        mgr_name = manager.name
        declared = {m for p in self._phase_topology for m in p.managers}
        if mgr_name not in declared:
            raise LifecycleManagerError(
                f"Manager '{mgr_name}' is not part of the declared Core Manager "
                f"topology; cannot be orchestrated by LifecycleManager.",
                rule_id="LM-REG-001",
            )
        self._managers[mgr_name] = manager

    def unregister_manager(self, manager_name: str) -> bool:
        """Remove a previously registered manager (no-op if absent)."""
        return self._managers.pop(manager_name, None) is not None

    # --- lifecycle operations ----------------------------------------------

    async def initialize(self) -> LifecycleState:
        """Initialize the kernel lifecycle (Part 4 §4.3.4 / §4.3.5).

        Executes phases in strict deterministic order. Phases with no present
        managers are deferred (owned by future tasks). Reaches OPERATIONAL once
        all present managers are ready and the readiness gate passes.

        Raises:
            LifecycleManagerError: if already initialized / terminated, or if
                initialization fails (after coordinating rollback).
        """
        # Serialize against concurrent lifecycle operations. The lock-free
        # worker (_do_initialize) is what must run under the lock so that the
        # rollback coordination path (which calls _do_rollback) never re-enters
        # the non-reentrant asyncio.Lock.
        async with self._op_lock:
            return await self._do_initialize()

    async def _do_initialize(self) -> LifecycleState:
        """Lock-free initialization body (caller holds ``_op_lock``)."""
        cur = self.state
        if cur is LifecycleState.OPERATIONAL:
            raise LifecycleManagerError(
                "LifecycleManager already initialized (OPERATIONAL).",
                rule_id="LM-INIT-001",
            )
        if cur is LifecycleState.TERMINATED:
            raise LifecycleManagerError(
                "LifecycleManager already terminated; cannot re-initialize.",
                rule_id="LM-INIT-002",
            )
        if cur is not LifecycleState.UNINITIALIZED:
            raise LifecycleManagerError(
                f"Cannot initialize from state {cur.value}.",
                rule_id="LM-INIT-003",
            )

        try:
            await self._transition(LifecycleState.INITIALIZING)
            self._validate_topology_acyclic()
            self._initialized_order = []

            for phase in self._phase_topology:
                present = self._resolve_phase_managers(phase)
                if not present:
                    # No manager from this phase is implemented yet
                    # (future task). Defer explicitly; do not fake it.
                    self._log_info(
                        f"Phase {phase.phase} ({phase.name}) deferred: "
                        f"no present managers "
                        f"{list(phase.managers)} (owned by a later task)."
                    )
                    continue

                # 1. pre-phase dependency validation
                self._validate_phase_dependencies(phase, present)
                # 2-3. initialize each manager (alphabetical within phase)
                for mgr in present:
                    if mgr is self:
                        # The orchestrator does not re-initialize itself; it is
                        # already running the lifecycle. Phase-1 completion is
                        # still recorded/emitted below for deterministic events.
                        continue
                    self._log_info(
                        f"Initializing manager '{mgr.name}' (phase {phase.phase})."
                    )
                    await mgr.initialize()
                # 4. post-phase readiness validation
                self._validate_phase_readiness(phase, present)
                # 5. phase completion event
                await self._emit_phase_completed(phase, present)
                # 6. record deterministic init order (alphabetical within phase)
                self._initialized_order.append([m.name for m in present])

            # Health gate: only gates on managers that are present. The
            # HealthManager-dependent gate becomes active once HealthManager
            # is implemented (later task); for Task 9 only LifecycleManager
            # exists and ready by construction.
            await self._readiness_gate()

            await self._transition(LifecycleState.OPERATIONAL)
            self._log_info("Kernel lifecycle OPERATIONAL.")
            return self.state
        except BaseException as exc:  # noqa: BLE001
            await self._coordinate_rollback(original_error=exc)
            raise LifecycleManagerError(
                f"Kernel lifecycle initialization failed: {exc}",
                rule_id="LM-INIT-FAIL-001",
                original_error=exc,
            ) from exc

    async def _coordinate_rollback(self, *, original_error: BaseException) -> None:
        """Rollback on init failure (§4.3.7). Re-raises after coordination.

        The caller (``_do_initialize``) already holds ``_op_lock``; this calls
        the lock-free ``_do_rollback`` directly to avoid re-entering the
        non-reentrant lock.
        """
        try:
            await self._do_rollback(original_error=original_error)
        except LifecycleManagerError as rb_exc:
            # Attach the original error so callers can distinguish causes.
            rb_exc.original_error = original_error
            raise rb_exc from original_error
        except Exception as rb_exc:  # noqa: BLE001
            wrapped = LifecycleManagerError(
                f"Rollback failed after init failure: {rb_exc}",
                rule_id="LM-RB-001",
                original_error=original_error,
                rollback_errors=[rb_exc],
            )
            raise wrapped from original_error

    async def shutdown(self) -> LifecycleState:
        """Shut down the kernel lifecycle (Part 4 §4.3.6).

        Transitions to SHUTTING_DOWN, executes shutdown phases in strict reverse
        order, emits phase-completion events, then transitions to TERMINATED.
        Does NOT shut down EventBus or StructuredLogger (owned by the kernel).
        """
        async with self._op_lock:
            return await self._do_shutdown()

    async def _do_shutdown(self) -> LifecycleState:
        """Lock-free shutdown body (caller holds ``_op_lock``)."""
        cur = self.state
        if cur is LifecycleState.TERMINATED:
            return self.state  # idempotent
        if cur is LifecycleState.UNINITIALIZED:
            # Nothing was initialized; go straight to TERMINATED.
            await self._transition(LifecycleState.SHUTTING_DOWN)
            await self._transition(LifecycleState.TERMINATED)
            return self.state

        await self._transition(LifecycleState.SHUTTING_DOWN)
        # Reverse phase order; reverse within phase.
        for phase in reversed(self._phase_topology):
            present = self._resolve_phase_managers(phase)
            if not present:
                continue
            for mgr in reversed(present):
                if mgr is self:
                    # The orchestrator does not shut itself down here; the kernel
                    # owns LifecycleManager teardown. Still emit the phase event.
                    continue
                try:
                    self._log_info(
                        f"Shutting down manager '{mgr.name}' (phase {phase.phase})."
                    )
                    await mgr.shutdown()
                except Exception as exc:  # noqa: BLE001
                    self._log_error(f"Manager '{mgr.name}' shutdown error: {exc}")
            await self._emit_phase_shutdown(phase, present)
        self._initialized_order = []
        await self._transition(LifecycleState.TERMINATED)
        self._log_info("Kernel lifecycle TERMINATED.")
        return self.state

    async def rollback(self, original_error: BaseException | None = None) -> LifecycleState:
        """Coordinate rollback to a prior consistent state (Part 4 §4.3.7).

        Idempotent: re-entry while ROLLBACK_IN_PROGRESS, or after reaching
        UNINITIALIZED/TERMINATED, is a no-op returning the current state.

        StorageManager.rollback() / StateManager.restore() referenced by the
        architecture are NOT implemented in Task 9 (they belong to later tasks);
        that dependency boundary is explicit and logged, not faked.
        """
        async with self._op_lock:
            return await self._do_rollback(original_error=original_error)

    async def _do_rollback(
        self, original_error: BaseException | None = None
    ) -> LifecycleState:
        """Lock-free rollback body (caller holds ``_op_lock``)."""
        cur = self.state
        if cur in (
            LifecycleState.ROLLBACK_IN_PROGRESS,
            LifecycleState.UNINITIALIZED,
            LifecycleState.TERMINATED,
        ):
            return self.state  # idempotent

        self._last_original_error = original_error
        self._last_rollback_errors = []
        await self._transition(LifecycleState.ROLLBACK_IN_PROGRESS)

        # Shut down initialized managers in reverse phase order, reverse
        # within phase (§4.3.7 steps 2-3).
        for phase in reversed(self._initialized_order):
            for name in reversed(phase):
                mgr = self._managers.get(name)
                if mgr is None:
                    continue
                if mgr is self:
                    # The orchestrator does not shut itself down here; the
                    # kernel owns LifecycleManager teardown.
                    continue
                try:
                    await mgr.shutdown()
                except Exception as exc:  # noqa: BLE001
                    self._last_rollback_errors.append(exc)
                    self._log_error(f"Rollback shutdown of '{name}' failed: {exc}")

        # §4.3.7 steps 4-5: StorageManager.rollback() / StateManager.restore().
        # Not available in Task 9 — explicit boundary, not faked.
        self._log_info(
            "Rollback storage/state restore deferred: StorageManager and "
            "StateManager are not implemented in Task 9 (later tasks)."
        )

        self._initialized_order = []
        target = (
            LifecycleState.TERMINATED
            if self._rollback_target == "TERMINATED"
            else LifecycleState.UNINITIALIZED
        )
        await self._transition(target)
        self._log_info(f"Rollback complete -> {target.value}.")
        # If any manager failed to shut down during rollback, surface a distinct
        # error (kept separate from any original init error) so callers can tell
        # "rollback itself failed" from "rollback succeeded but cleanup had errors".
        if self._last_rollback_errors:
            raise LifecycleManagerError(
                "Rollback completed but one or more managers failed to shut down.",
                rule_id="LM-RB-FAIL-001",
                rollback_errors=list(self._last_rollback_errors),
                original_error=original_error,
            )
        return self.state

    async def mark_degraded(self, affected: list[str] | None = None) -> LifecycleState:
        """Transition to DEGRADED (Part 4 §4.3.8).

        Valid from OPERATIONAL or RECOVERY_IN_PROGRESS. Emits the canonical
        degraded signal (mapped from KernelDegradedEvent).
        """
        async with self._op_lock:
            await self._transition(
                LifecycleState.DEGRADED, affected=list(affected or [])
            )
            return self.state

    async def begin_recovery(self, affected: list[str] | None = None) -> LifecycleState:
        """Transition DEGRADED -> RECOVERY_IN_PROGRESS (Part 4 §4.3.8).

        The recovery *strategy* itself is coordinated by HealthManager (later
        task). No canonical recovery event exists (conflict E.1); none emitted.
        """
        async with self._op_lock:
            cur = self.state
            if cur is not LifecycleState.DEGRADED:
                raise LifecycleManagerError(
                    f"begin_recovery requires DEGRADED state, got {cur.value}.",
                    rule_id="LM-REC-001",
                )
            await self._transition(
                LifecycleState.RECOVERY_IN_PROGRESS, affected=list(affected or [])
            )
            return self.state

    async def complete_recovery(self, success: bool = True) -> LifecycleState:
        """Finish recovery: RECOVERY_IN_PROGRESS -> OPERATIONAL or DEGRADED.

        Per Part 4 §4.3.8 step 5.
        """
        async with self._op_lock:
            if success:
                await self._transition(LifecycleState.OPERATIONAL)
            else:
                await self._transition(LifecycleState.DEGRADED)
            return self.state

    # --- state transition (atomic + event) --------------------------------

    async def _transition(
        self, to: LifecycleState, *, affected: list[str] | None = None
    ) -> None:
        """Validate and apply a lifecycle transition; emit the canonical event.

        Raises:
            LifecycleManagerError: on an invalid transition.
        """
        with self._state_lock:
            cur = self._state
            allowed = _TRANSITIONS.get(cur, frozenset())
            if to not in allowed:
                raise LifecycleManagerError(
                    f"Invalid lifecycle transition {cur.value} -> {to.value}.",
                    rule_id="LM-TRANS-001",
                )
            from_state = cur
            self._state = to

        self._log_debug(f"Lifecycle {from_state.value} -> {to.value}.")
        event_type = _STATE_TO_EVENT.get(to)
        if event_type is not None:
            await self._publish(
                event_type,
                {
                    "lifecycle_state": to.value,
                    "from_state": from_state.value,
                    "to_state": to.value,
                    "event_name": _STATE_TO_INTENDED_EVENT.get(to, "KernelLifecycleEvent"),
                    "manager": _NAME,
                    "affected_managers": list(affected or []),
                    "intended_event_note": (
                        "Mapped from Part 4 PascalCase event name (CONFLICT E.1); "
                        "canonical EventType used."
                    ),
                },
            )
        else:
            # Documented conflict: no canonical event for this transition.
            self._log_info(
                f"No canonical EventType for transition -> {to.value} "
                f"(intended Part-4 name "
                f"'{_STATE_TO_INTENDED_EVENT.get(to, 'KernelLifecycleEvent')}'); "
                f"emitting no fabricated event (CONFLICT E.1)."
            )

    # --- validation --------------------------------------------------------

    def _validate_topology_acyclic(self) -> None:
        """Static validation: phase dependency graph must be acyclic (§4.3.9)."""
        by_phase = {p.phase: p for p in self._phase_topology}
        for p in self._phase_topology:
            for dep in p.depends_on:
                if dep not in by_phase:
                    raise LifecycleManagerError(
                        f"Phase {p.phase} depends on unknown phase {dep}.",
                        rule_id="LM-DEP-001",
                    )
                if dep >= p.phase:
                    raise LifecycleManagerError(
                        f"Phase {p.phase} depends on non-earlier phase {dep} "
                        f"(cycle / ordering violation).",
                        rule_id="LM-DEP-002",
                    )

    def _validate_phase_dependencies(
        self, phase: CoreManagerPhase, present: list[ICoreManager]
    ) -> None:
        """Runtime validation: each present manager's deps must be satisfied."""
        satisfied: set[str] = set(_COMPONENT_DEPENDENCIES)
        for earlier in self._initialized_order:
            satisfied.update(earlier)
        for mgr in present:
            for dep in mgr.dependencies:
                if dep not in satisfied:
                    raise LifecycleManagerError(
                        f"Manager '{mgr.name}' dependency '{dep}' not satisfied "
                        f"before phase {phase.phase}.",
                        rule_id="LM-DEP-003",
                    )

    def _validate_phase_readiness(
        self, phase: CoreManagerPhase, present: list[ICoreManager]
    ) -> None:
        """Post-phase readiness: every present manager must report ready."""
        for mgr in present:
            if not mgr.health_ready():
                raise LifecycleManagerError(
                    f"Manager '{mgr.name}' not READY after phase {phase.phase} init.",
                    rule_id="LM-READY-001",
                )

    async def _readiness_gate(self) -> None:
        """Health gate (§4.3.8): all present managers ready before OPERATIONAL.

        The HealthManager-dependent gate is a later-task dependency; for Task 9
        only LifecycleManager (ready by construction) is present.
        """
        for phase in self._initialized_order:
            for name in phase:
                mgr = self._managers.get(name)
                if mgr is not None and not mgr.health_ready():
                    raise LifecycleManagerError(
                        f"Readiness gate failed: manager '{name}' not READY.",
                        rule_id="LM-GATE-001",
                    )

    # --- helpers -----------------------------------------------------------

    def _resolve_phase_managers(self, phase: CoreManagerPhase) -> list[ICoreManager]:
        """Present (registered) managers for a phase, alphabetical by name."""
        names = sorted(n for n in phase.managers if n in self._managers)
        return [self._managers[n] for n in names]

    def _read_config_int(self, path: str, default: int) -> int:
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_str(self, path: str, default: str) -> str:
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return str(val) if val is not None else default
        except Exception:  # noqa: BLE001
            return default

    # --- EventBus integration ---------------------------------------------

    def _make_event(self, event_type: EventType, payload: dict[str, Any]) -> Any:
        return Event(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid.uuid4(),
            payload=payload,
        )

    async def _publish(self, event_type: EventType, payload: dict[str, Any]) -> None:
        """Emit a canonical event via EventBus (C1). No-op if bus absent."""
        bus = self._event_bus
        if bus is None:
            self._log_warning(
                "EventBus unavailable; lifecycle event "
                f"{event_type.name} not emitted (kernel owns terminate policy)."
            )
            return
        try:
            await bus.publish(self._make_event(event_type, payload))
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"Lifecycle event {event_type.name} publish failed: {exc}")

    async def _emit_phase_completed(
        self, phase: CoreManagerPhase, present: list[ICoreManager]
    ) -> None:
        """Phase completion (KernelPhaseCompletedEvent -> CORE_MANAGER_INITIALIZED)."""
        await self._publish(
            EventType.CORE_MANAGER_INITIALIZED,
            {
                "phase": phase.phase,
                "phase_name": phase.name,
                "managers": [m.name for m in present],
                "event_name": "KernelPhaseCompletedEvent",
                "intended_event_note": (
                    "Mapped from Part 4 PascalCase name (CONFLICT E.1)."
                ),
            },
        )

    async def _emit_phase_shutdown(
        self, phase: CoreManagerPhase, present: list[ICoreManager]
    ) -> None:
        await self._publish(
            EventType.CORE_MANAGER_SHUTDOWN,
            {
                "phase": phase.phase,
                "phase_name": phase.name,
                "managers": [m.name for m in present],
                "event_name": "KernelPhaseCompletedEvent",
            },
        )

    # --- ServiceRegistry integration ---------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register LifecycleManager with the ServiceRegistry (C2, Part 4 §4.3.10).

        Registered as ``core.lifecycle`` (the ``kernel`` namespace is reserved by
        the ServiceRegistry, INV-SR-NS-002; see conflict report).
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering LifecycleManager.")
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
                    "lifecycle_state": self.state.value,
                },
            )
            self._registered_with_sr = True
            self._log_info(f"Registered with ServiceRegistry as '{_MANAGER_ID}'.")
        except Exception as exc:  # noqa: BLE001
            self._log_warning(f"ServiceRegistry registration failed: {exc}")

    # --- StructuredLogger integration --------------------------------------

    def _log_debug(self, message: str) -> None:
        if self._logger is not None:
            self._logger.debug(message, manager=_NAME)

    def _log_info(self, message: str) -> None:
        if self._logger is not None:
            self._logger.info(message, manager=_NAME)

    def _log_warning(self, message: str) -> None:
        if self._logger is not None:
            self._logger.warning(message, manager=_NAME)

    def _log_error(self, message: str) -> None:
        if self._logger is not None:
            self._logger.error(message, manager=_NAME)


# ---------------------------------------------------------------------------
# Singleton accessor (mirrors ServiceRegistry / ConfigurationManager pattern)
# ---------------------------------------------------------------------------

_INSTANCE: LifecycleManager | None = None
_INSTANCE_LOCK = threading.Lock()


def reset_lifecycle_manager_singleton() -> None:
    """Reset the process-wide LifecycleManager singleton (tests only)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = None


def get_lifecycle_manager(
    *,
    event_bus: EventBus | None = None,
    service_registry: ServiceRegistry | None = None,
    configuration_manager: ConfigurationManager | None = None,
    logger: StructuredLogger | None = None,
    kernel: Any | None = None,
) -> LifecycleManager:
    """Get (or create) the global LifecycleManager singleton.

    The kernel owns construction and should call :func:`set_lifecycle_manager`
    with a fully-wired instance. This accessor creates one on first use if none
    exists (deps optional; production must supply them or use ``set_``).
    """
    global _INSTANCE
    with _INSTANCE_LOCK:
        if _INSTANCE is None:
            _INSTANCE = LifecycleManager(
                event_bus=event_bus,
                service_registry=service_registry,
                configuration_manager=configuration_manager,
                logger=logger,
                kernel=kernel,
            )
        return _INSTANCE


def set_lifecycle_manager(manager: LifecycleManager) -> None:
    """Set the global LifecycleManager singleton (kernel-owned construction)."""
    global _INSTANCE
    with _INSTANCE_LOCK:
        _INSTANCE = manager
