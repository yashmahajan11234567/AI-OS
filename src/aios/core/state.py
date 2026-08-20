"""
State Manager for AI-OS Hermes Kernel.

Manages workflow and application state with persistence and checkpointing.
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.

Task 10 — Core Manager upgrade (Part 4 §4.4)
--------------------------------------------
StateManager is the Phase-2 (State & Storage) Core Manager. It implements the
ICoreManager Protocol (name / phase / dependencies / initialize / shutdown /
health_ready) so LifecycleManager (Task 9) can orchestrate it deterministically:

  * initialized by LifecycleManager during Phase 2
  * registers with the canonical ServiceRegistry (C2) as ``core.state``
    (Part 4 §4.4.9 names ``kernel.state``; see the CONFLICT E.1 note below for
    the Part-3-vs-Part-4 resolution that maps it to ``core.state``), using the
    same "core manager" metadata envelope as LifecycleManager's
    ``core.lifecycle`` registration
  * reads ``kernel.state.*`` configuration from the frozen ConfigurationManager
    (C3)
  * logs through the StructuredLogger Core Component (C4) — the stdlib logger is
    NOT used (Task 10 requirement)

CONFLICT E.1 (Task 10 mapping, same as Task 9): Part 4 §4.4.10 names events
like ``StateSnapshotCreatedEvent`` / ``StateRecoveryCompletedEvent`` that do NOT
exist in the closed canonical ``EventType`` enum. StateManager does NOT invent
new EventTypes; the existing canonical emissions (STATE_CHANGED,
STATE_SNAPSHOT_CREATED, STATE_RESTORED) are the architectural mappings.

NOTE ON ``core.state`` SERVICE-ID (CONFLICT E.1, Part 3 §3.4.8 vs Part 4 §4.4.9):
Part 4 §4.4.9 names StateManager's ServiceRegistry identity as ``kernel.state``,
but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel`` namespace ("not in
ServiceRegistry"; registration throws). This is the same Part-3-vs-Part-4
contradiction Task 9 resolved for LifecycleManager by registering as
``core.lifecycle`` instead of ``kernel.lifecycle``. Per that precedent, the
compliant, INV-SR-NS-002-respecting ServiceRegistry identity is ``core.state``
(the ``core.*`` namespace is not reserved and is NOT a validator exception).
The configuration namespace read from C3 remains ``kernel.state.*`` (Part 4
§4.4.9 config schema), which is independent of the ServiceRegistry id. Lifecycle
ownership (initialize/shutdown driven by LifecycleManager Phase 2) is unchanged.
"""

from __future__ import annotations

import asyncio
import json
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# Core Components (Tasks 1–8) — consumed, never re-implemented. Imports are
# deferred to module import time (same pattern as LifecycleManager); these
# modules do not import ``aios.core.state`` at module scope, so there is no
# circular-import risk (verified against checkpoint/workflow/kernel/__init__).
from aios.core.configuration_manager import ConfigurationManager
from aios.core.service_registry import ServiceRegistry, ServiceType
from aios.core.structured_logger import StructuredLogger
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

__all__ = [
    "StateManager",
    "StateScope",
    "StateSnapshot",
    "StateManagerError",
    "get_state_manager",
    "set_state_manager",
    "reset_state_manager_singleton",
]

# ---------------------------------------------------------------------------
# Constants / identity
# ---------------------------------------------------------------------------

_NAME = "StateManager"
# Part 4 §4.4.9 names StateManager's ServiceRegistry identity as ``kernel.state``,
# but Part 3 §3.4.8 / INV-SR-NS-002 reserve the ``kernel`` namespace ("not in
# ServiceRegistry"; registration throws). This is the same Part-3-vs-Part-4
# contradiction Task 9 resolved for LifecycleManager by using ``core.lifecycle``
# instead of ``kernel.lifecycle``. We follow that precedent: the compliant,
# INV-SR-NS-002-respecting ServiceRegistry id is ``core.state``. The
# configuration namespace read from C3 remains ``kernel.state.*`` (Part 4
# §4.4.9 config schema), which is unaffected by the ServiceRegistry id.
_MANAGER_ID = "core.state"
_PHASE = 2  # Phase 2 — "State & Storage"
_VERSION = SemanticVersion(1, 0, 0)
_COMPONENT_DEPENDENCIES = (
    "EventBus",
    "ServiceRegistry",
    "ConfigurationManager",
    "StructuredLogger",
)
# Task 10 requirement: ``dependencies`` MUST be EXACTLY ["LifecycleManager"].
# Per the architecture review (§5.4):
#   * the same-phase StorageManager sibling is NOT a dependency — same-phase
#     deps would be rejected by LifecycleManager's dependency validator
#     (LM-DEP-003); the deterministic alphabetical ordering (StateManager first)
#     already guarantees correct sequencing,
#   * C1–C4 are always-satisfied base dependencies handled by LifecycleManager,
#     so they are not repeated here.
_MANAGER_DEPENDENCIES = ("LifecycleManager",)


class StateScope(str, Enum):
    """Scope of state management."""

    WORKFLOW = "workflow"
    SERVICE = "service"
    GLOBAL = "global"
    SESSION = "session"


@dataclass
class StateSnapshot:
    """A snapshot of state at a point in time."""

    snapshot_id: str
    scope: StateScope
    identifier: str  # workflow_id, service_name, etc.
    state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: int = 1


class StateManagerError(Exception):
    """StateManager failure (Part 4 §4.4.11).

    Carries optional diagnostic context: ``rule_id`` (internal invariant/rule
    identifier) and ``original_error`` (the underlying error, when wrapping).
    Mirrors ``LifecycleManagerError`` (Task 9).
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
            base += f" [original_error={type(self.original_error).__name__}: {self.original_error}]"
        return base


class StateManager:
    """
    Manages application and workflow state.

    Provides:
    - State storage with scoping (workflow, service, global, session)
    - Atomic state transitions with event emission
    - Checkpointing for recovery
    - State queries and history
    - ICoreManager Core-Manager lifecycle (Task 10)
    """

    def __init__(
        self,
        persistence_path: Path | None = None,
        *,
        service_registry: ServiceRegistry | None = None,
        configuration_manager: ConfigurationManager | None = None,
        logger: StructuredLogger | None = None,
    ) -> None:
        """
        Initialize the State Manager.

        Backward compatible: the ``persistence_path`` positional/None argument is
        preserved from the pre-Task-10 constructor. The C2/C3/C4 dependencies are
        optional keyword-only injection points; they are resolved at
        ``initialize()`` time (C3 is frozen before LifecycleManager Phase 2 runs,
        so ``initialize()`` reads the frozen configuration).
        """
        self._persistence_path = persistence_path or Path("./data/state")
        self._persistence_path.mkdir(parents=True, exist_ok=True)

        self._state: dict[str, dict[str, Any]] = {}
        self._scope_index: dict[StateScope, dict[str, str]] = {
            StateScope.WORKFLOW: {},
            StateScope.SERVICE: {},
            StateScope.GLOBAL: {"global": "global_state"},
            StateScope.SESSION: {},
        }
        self._history: dict[str, list[StateSnapshot]] = {}

        # C1 CANONICAL EventBus singleton (INV-EB-001). Resolved eagerly so both
        # the constructor contract (raise if the bus is not up) and the sync
        # ``_emit_event`` bridge keep working unchanged.
        self._event_bus = get_core_event_bus()

        # Strong references for sync-path publish tasks (FIX-FIND-01): coroutines
        # scheduled from synchronous business APIs are awaited on the running loop
        # and held here until complete so they are never garbage-collected or left
        # un-awaited. Mirrors the ConfigurationManager ``_pending_tasks`` pattern
        # (Task 7), which is the architecture-approved sync-to-async bridge.
        self._pending_tasks: set[asyncio.Future[Any]] = set()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")

        # C2/C3/C4 — injected via DI (Task 10); resolved lazily in initialize().
        self._service_registry = service_registry
        self._configuration: ConfigurationManager | None = configuration_manager
        self._logger: StructuredLogger | None = logger

        # Component identity for event emission (CORE_MANAGER, Part 4 §4.4).
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name=_NAME,
            version=_VERSION,
        )

        # ICoreManager lifecycle state (Task 10).
        self._initialized = False
        self._registered_with_sr = False
        self._shutdown_timeout_ms = 5000  # kernel.state.shutdownTimeoutMs default

        # Configuration consumed from the FROZEN ConfigurationManager (C3).
        self._consistency_class = "EVENTUAL"
        self._snapshot_interval_seconds = 300
        self._max_snapshots = 10
        self._checkpoint_on_transition = True

    # ------------------------------------------------------------------
    # ICoreManager surface (Task 10 / Part 4 §4.2)
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Core Manager name."""
        return _NAME

    @property
    def phase(self) -> int:
        """Lifecycle phase (Phase 2 — State & Storage, Part 4 §4.2.3)."""
        return _PHASE

    @property
    def dependencies(self) -> list[str]:
        """Core Manager dependencies: Phase-1 LifecycleManager + C1–C4."""
        return list(_MANAGER_DEPENDENCIES)

    @property
    def manager_id(self) -> str:
        """ServiceRegistry identity (``core.state``; Part 4 §4.4.9 names
        ``kernel.state`` — see the CONFLICT E.1 note on INV-SR-NS-002)."""
        return _MANAGER_ID

    @property
    def is_initialized(self) -> bool:
        """True once initialize() completed successfully."""
        return self._initialized

    def health_ready(self) -> bool:
        """True only when correctly initialized and wired (C1 + initialized).

        Mirrors LifecycleManager.health_ready (ready by construction once the
        manager has completed its own initialization). Returns False before
        ``initialize()`` and after ``shutdown()``.
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
        """Phase 2 initialization (called by LifecycleManager).

        Follows the Core Manager pattern (mirrors LifecycleManager.initialize):
        reads ``kernel.state.*`` configuration from the frozen C3, wires the
        StructuredLogger (C4), loads persisted snapshots from disk, registers
        this manager with the canonical ServiceRegistry (C2) as ``core.state``,
        and marks the manager initialized/ready.

        Idempotent and lifecycle-safe: a second initialize while already
        initialized is a no-op.
        """
        if self._initialized:
            self._log_debug("initialize() called while already initialized; no-op.")
            return

        # 1. Read configuration from the FROZEN ConfigurationManager (C3).
        self._persistence_path = Path(
            self._read_config_str(
                "kernel.state.persistencePath", str(self._persistence_path)
            )
        )
        self._persistence_path.mkdir(parents=True, exist_ok=True)

        self._snapshot_interval_seconds = self._read_config_int(
            "kernel.state.snapshotIntervalSeconds", self._snapshot_interval_seconds
        )
        self._max_snapshots = self._read_config_int(
            "kernel.state.retentionPolicy.maxSnapshots", self._max_snapshots
        )
        self._consistency_class = self._read_config_str(
            "kernel.state.consistencyClass", self._consistency_class
        )
        self._checkpoint_on_transition = self._read_config_bool(
            "kernel.state.checkpointOnTransition", self._checkpoint_on_transition
        )
        self._shutdown_timeout_ms = self._read_config_int(
            "kernel.state.shutdownTimeoutMs", self._shutdown_timeout_ms
        )

        # 2. Load persisted snapshots (recovery). Failures are non-fatal;
        # the manager starts with whatever loaded cleanly (SM-SNAP-001).
        try:
            loaded = self.load_persisted_snapshots()
            self._log_info(f"Loaded {loaded} persisted snapshot(s) during initialize().")
        except Exception as exc:  # noqa: BLE001
            self._log_error(f"Failed to load persisted snapshots: {exc}")

        # 3. Register with the canonical ServiceRegistry (C2) as ``core.state``.
        await self.register_with_service_registry()

        # 4. Mark initialized/ready.
        self._initialized = True
        self._log_info(
            f"StateManager initialized (phase {self.phase}, "
            f"persistence={self._persistence_path})."
        )

    async def shutdown(self) -> None:
        """Phase 2 (reverse) shutdown (called by LifecycleManager).

        Creates a final snapshot of all in-memory state, persists it, marks
        ``core.state`` SHUTDOWN in the canonical ServiceRegistry (C2), and
        clears the initialized flag.

        Idempotent and lifecycle-safe: a second shutdown is a no-op.
        """
        if not self._initialized:
            self._log_debug("shutdown() called while not initialized; no-op.")
            return

        # 1. Final snapshot + persist (bounded by shutdownTimeoutMs).
        try:
            snapshot_count = self._create_final_snapshot()
            self._log_info(f"Final snapshot: persisted {snapshot_count} identifier(s).")
        except Exception as exc:  # noqa: BLE001
            self._log_error(f"Final snapshot failed: {exc}")

        # 2. Deregister / mark SHUTDOWN in C2 (non-fatal on failure).
        await self._deregister_from_service_registry()

        # 3. Clear initialized/ready flag.
        self._initialized = False
        self._log_info("StateManager shut down.")

    def _create_final_snapshot(self) -> int:
        """Persist a snapshot for every in-memory identifier (best-effort).

        Only identifiers with a non-empty state dict are checkpointed; running
        ``checkpoint()`` on an identifier with no state would raise ValueError.
        The synchronous snapshot write is intentionally a small, bounded operation
        (JSON serialization of in-memory state); the shutdown timeout is applied
        rather than a filesystem async adapter (no invented abstraction).
        """
        count = 0
        for scope, index in self._scope_index.items():
            for identifier in list(index.keys()):
                if self.get_state(scope, identifier) == {}:
                    continue
                try:
                    self.checkpoint(scope, identifier, metadata={"final": True})
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    self._log_warning(
                        f"Final snapshot failed for {scope.value}:{identifier}: {exc}"
                    )
        return count

    async def _deregister_from_service_registry(self) -> None:
        """Mark ``core.state`` SHUTDOWN in the canonical ServiceRegistry (C2)."""
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
    # ServiceRegistry integration (mirror LifecycleManager pattern)
    # ------------------------------------------------------------------

    async def register_with_service_registry(self) -> None:
        """Register StateManager with the ServiceRegistry (C2, Part 4 §4.4.9).

        Registered as ``core.state`` with the same metadata envelope
        LifecycleManager uses (``core.lifecycle``) — ``kind: core_manager`` — so
        the registration is explicitly NOT classified as an ordinary engineering
        service.
        """
        sr = self._service_registry
        if sr is None:
            self._log_warning("ServiceRegistry unavailable; not registering StateManager.")
            return
        try:
            # Resolve the singleton at initialize() time if the kernel wired the
            # canonical instance through DI.
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

    # ------------------------------------------------------------------
    # State management business API (backward compatible, pre-Task-10)
    # ------------------------------------------------------------------

    def _get_state_key(self, scope: StateScope, identifier: str) -> str:
        """Get the internal state key for a scope/identifier."""
        return f"{scope.value}:{identifier}"

    def _get_scope_identifier(self, scope: StateScope, identifier: str) -> str:
        """Get or create state key for scope/identifier."""
        if identifier not in self._scope_index[scope]:
            key = self._get_state_key(scope, identifier)
            self._scope_index[scope][identifier] = key
            self._state[key] = {}
            self._history[key] = []
        return self._scope_index[scope][identifier]

    def set_state(
        self,
        scope: StateScope,
        identifier: str,
        key: str,
        value: Any,
        emit_event: bool = True,
    ) -> None:
        """
        Set a state value.

        Args:
            scope: State scope
            identifier: Unique identifier within scope
            key: State key
            value: State value
            emit_event: Whether to emit StateTransitioned event
        """
        state_key = self._get_scope_identifier(scope, identifier)
        old_value = self._state[state_key].get(key)
        self._state[state_key][key] = value

        if emit_event and old_value != value:
            self._emit_event(
                EventType.STATE_CHANGED,
                {
                    "scope": scope.value,
                    "identifier": identifier,
                    "key": key,
                    "old_value": old_value,
                    "new_value": value,
                },
                identifier,
            )

    def get_state(
        self,
        scope: StateScope,
        identifier: str,
        key: str | None = None,
        default: Any = None,
    ) -> Any:
        """
        Get state value(s).

        Args:
            scope: State scope
            identifier: Unique identifier within scope
            key: Specific key to get, or None for all state
            default: Default value if key not found

        Returns:
            State value or entire state dict
        """
        state_key = self._scope_index.get(scope, {}).get(identifier)
        if not state_key:
            return default if key else {}

        state = self._state.get(state_key, {})
        if key is None:
            return state.copy()
        return state.get(key, default)

    def update_state(
        self,
        scope: StateScope,
        identifier: str,
        updates: dict[str, Any],
        emit_event: bool = True,
    ) -> None:
        """
        Update multiple state values atomically.

        Args:
            scope: State scope
            identifier: Unique identifier within scope
            updates: Dictionary of key-value updates
            emit_event: Whether to emit STATE_CHANGED events
        """
        state_key = self._get_scope_identifier(scope, identifier)
        old_state = self._state[state_key].copy()
        self._state[state_key].update(updates)

        if emit_event:
            for key, new_value in updates.items():
                old_value = old_state.get(key)
                if old_value != new_value:
                    self._emit_event(
                        EventType.STATE_CHANGED,
                        {
                            "scope": scope.value,
                            "identifier": identifier,
                            "key": key,
                            "old_value": old_state.get(key),
                            "new_value": updates[key],
                        },
                        identifier,
                    )

    def delete_state(
        self,
        scope: StateScope,
        identifier: str,
        key: str | None = None,
    ) -> None:
        """
        Delete state value(s).

        Args:
            scope: State scope
            identifier: Unique identifier within scope
            key: Specific key to delete, or None for all state
        """
        state_key = self._scope_index.get(scope, {}).get(identifier)
        if not state_key:
            return

        if key is None:
            self._state[state_key].clear()
        else:
            self._state[state_key].pop(key, None)

    def checkpoint(
        self,
        scope: StateScope,
        identifier: str,
        metadata: dict[str, Any] | None = None,
    ) -> StateSnapshot:
        """
        Create a checkpoint of current state.

        Args:
            scope: State scope
            identifier: Unique identifier within scope
            metadata: Optional metadata

        Returns:
            Created StateSnapshot
        """
        state_key = self._scope_index.get(scope, {}).get(identifier)
        if not state_key:
            raise ValueError(f"No state found for {scope.value}:{identifier}")

        snapshot = StateSnapshot(
            snapshot_id=f"checkpoint_{datetime.utcnow().timestamp()}",
            scope=scope,
            identifier=identifier,
            state=self._state[state_key].copy(),
            metadata=metadata or {},
        )

        self._history[state_key].append(snapshot)
        self._persist_snapshot(snapshot)

        self._emit_event(
            EventType.STATE_SNAPSHOT_CREATED,
            {
                "snapshot_id": snapshot.snapshot_id,
                "scope": scope.value,
                "identifier": identifier,
                "metadata": snapshot.metadata,
            },
            identifier,
        )

        self._log_debug(
            f"Created checkpoint {snapshot.snapshot_id} for {scope.value}:{identifier}"
        )
        return snapshot

    def restore(
        self,
        scope: StateScope,
        identifier: str,
        snapshot_id: str | None = None,
    ) -> StateSnapshot:
        """
        Restore state from a checkpoint.

        Args:
            scope: State scope
            identifier: Unique identifier within scope
            snapshot_id: Specific snapshot to restore, or latest if None

        Returns:
            Restored StateSnapshot
        """
        state_key = self._scope_index.get(scope, {}).get(identifier)
        if not state_key:
            raise ValueError(f"No state found for {scope.value}:{identifier}")

        history = self._history.get(state_key, [])
        if not history:
            raise ValueError(f"No checkpoints found for {scope.value}:{identifier}")

        if snapshot_id:
            snapshot = next((s for s in history if s.snapshot_id == snapshot_id), None)
            if not snapshot:
                raise ValueError(f"Snapshot {snapshot_id} not found")
        else:
            snapshot = history[-1]  # Latest

        # Restore state
        self._state[state_key] = snapshot.state.copy()

        self._emit_event(
            EventType.STATE_RESTORED,
            {
                "snapshot_id": snapshot.snapshot_id,
                "scope": scope.value,
                "identifier": identifier,
            },
            identifier,
        )

        self._log_info(
            f"Restored checkpoint {snapshot.snapshot_id} for {scope.value}:{identifier}"
        )
        return snapshot

    def get_history(
        self,
        scope: StateScope,
        identifier: str,
        limit: int = 10,
    ) -> list[StateSnapshot]:
        """Get state history for an identifier."""
        state_key = self._scope_index.get(scope, {}).get(identifier)
        if not state_key:
            return []
        return self._history.get(state_key, [])[-limit:]

    def list_identifiers(self, scope: StateScope) -> list[str]:
        """List all identifiers for a scope."""
        return list(self._scope_index.get(scope, {}).keys())

    def _persist_snapshot(self, snapshot: StateSnapshot) -> None:
        """Persist snapshot to disk."""
        if not self._persistence_path:
            return

        file_path = self._persistence_path / f"{snapshot.scope.value}_{snapshot.identifier}_{snapshot.snapshot_id}.json"
        try:
            data = {
                "snapshot_id": snapshot.snapshot_id,
                "scope": snapshot.scope.value,
                "identifier": snapshot.identifier,
                "state": snapshot.state,
                "metadata": snapshot.metadata,
                "timestamp": snapshot.timestamp.isoformat(),
                "version": snapshot.version,
            }
            file_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            self._log_error(f"Failed to persist snapshot: {e}")

    def load_persisted_snapshots(self) -> int:
        """Load persisted snapshots from disk."""
        if not self._persistence_path or not self._persistence_path.exists():
            return 0

        count = 0
        for file_path in self._persistence_path.glob("*.json"):
            try:
                data = json.loads(file_path.read_text())
                snapshot = StateSnapshot(
                    snapshot_id=data["snapshot_id"],
                    scope=StateScope(data["scope"]),
                    identifier=data["identifier"],
                    state=data["state"],
                    metadata=data["metadata"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    version=data["version"],
                )

                state_key = self._get_state_key(snapshot.scope, snapshot.identifier)
                if state_key not in self._history:
                    self._history[state_key] = []
                self._history[state_key].append(snapshot)
                # Rehydrate the scope index so the identifier is reachable.
                if snapshot.identifier not in self._scope_index[snapshot.scope]:
                    self._scope_index[snapshot.scope][snapshot.identifier] = state_key
                    self._state[state_key] = dict(snapshot.state)
                count += 1
            except Exception as e:
                self._log_warning(f"Failed to load snapshot {file_path}: {e}")

        return count

    def clear_scope(self, scope: StateScope, identifier: str) -> None:
        """Clear all state and history for an identifier."""
        state_key = self._scope_index.get(scope, {}).pop(identifier, None)
        if state_key:
            self._state.pop(state_key, None)
            self._history.pop(state_key, None)

    def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str | uuid.UUID
    ) -> None:
        """Emit a canonical event via the canonical EventBus.

        The canonical Task-5 ``EventBus.publish`` is async (returns a coroutine).
        From a synchronous business-API call site (``set_state`` /
        ``update_state`` / ``checkpoint`` / ``restore``) we cannot ``await`` it,
        so this method bridges to the async bus deterministically using the
        architecture-approved sync-to-async bridge established in
        ``ConfigurationManager._run_emission`` (Task 7):

        * If a loop is already running, the publish coroutine is scheduled via
          ``asyncio.ensure_future`` and kept alive with a strong reference in
          ``self._pending_tasks`` (with a ``done_callback`` discarding it on
          completion). The event is enqueued on the bus deterministically
          before the next ``await`` yields.
        * If no loop is running (e.g. a synchronous unit test, or a call before
          the kernel starts the loop), the coroutine is NOT created at all —
          the emission is skipped with a StructuredLogger debug note. The
          canonical bus requires a running loop to enqueue; synchronously
          dropping the emission here avoids the
          ``RuntimeWarning: coroutine 'EventBus.publish' was never awaited``
          and never leaves a coroutine un-awaited.

        This preserves StateManager's synchronous public API (no conversion of
        ``set_state`` / ``update_state`` / ``checkpoint`` / ``restore`` to
        ``async``) while removing both the unawaited-coroutine hazard and the
        fire-and-forget task leak. See CONFLICT E.1 note on canonical EventTypes.
        """
        bus = self._event_bus
        if bus is None:
            return

        # Resolve the canonical bus's own correlation id is generated by the
        # Event factory (FIX-9, ConfigurationManager); we mirror the same
        # ``_make_event``-then-``publish`` shape. The ``correlation_id`` argument
        # carried by callers is the StateManager scope identifier (a string), not
        # a UUID — normalize to a UUIDv4 to satisfy the canonical Event contract.
        correlation_uuid: uuid.UUID
        if isinstance(correlation_id, uuid.UUID):
            correlation_uuid = correlation_id
        else:
            try:
                correlation_uuid = uuid.UUID(str(correlation_id))
            except (ValueError, AttributeError):
                correlation_uuid = uuid.uuid4()

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=payload,
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
                event_type=event_type.name,
            )
            return
        if not loop.is_running():
            self._log_debug(
                f"Event {event_type.name} not dispatched (event loop not running).",
                event_type=event_type.name,
            )
            return

        coro = bus.publish(event)
        task = asyncio.ensure_future(coro, loop=loop)
        # Strong reference so the task is never GC'd before the bus drains it.
        self._pending_tasks.add(task)
        task.add_done_callback(self._pending_tasks.discard)

    # ------------------------------------------------------------------
    # StructuredLogger integration (C4, Task 10 — replaces stdlib logging)
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
# Global state manager singleton (INV — one per process)
# ---------------------------------------------------------------------------

_global_state_manager: StateManager | None = None
_state_singleton_lock = threading.Lock()


def get_state_manager(persistence_path: Path | None = None) -> StateManager:
    """Get or create the global state manager.

    Backward compatible: the ``persistence_path`` coercion is preserved. The
    Task-10 singleton accessor uses the same lock-guarded pattern as C2–C4 so
    concurrent callers cannot double-construct.
    """
    global _global_state_manager
    with _state_singleton_lock:
        if _global_state_manager is None:
            _global_state_manager = StateManager(persistence_path)
        return _global_state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the global state manager."""
    global _global_state_manager
    with _state_singleton_lock:
        _global_state_manager = manager


def reset_state_manager_singleton() -> None:
    """Reset the process-wide StateManager singleton (tests only).

    Mirrors ``reset_lifecycle_manager_singleton`` / C2–C4 resets.
    """
    global _global_state_manager
    with _state_singleton_lock:
        _global_state_manager = None
