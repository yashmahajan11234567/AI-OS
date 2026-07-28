"""
State Manager for AI-OS Hermes Kernel.

Manages workflow and application state with persistence and checkpointing.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.types import StateTransitioned, StateCheckpointed, StateRestored

logger = logging.getLogger(__name__)


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


class StateManager:
    """
    Manages application and workflow state.

    Provides:
    - State storage with scoping (workflow, service, global, session)
    - Atomic state transitions with event emission
    - Checkpointing for recovery
    - State queries and history
    """

    def __init__(self, persistence_path: Path | None = None):
        """
        Initialize the State Manager.

        Args:
            persistence_path: Optional path to persist state to disk
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
        self._event_bus = get_event_bus()

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
            self._event_bus.publish(
                StateTransitioned(
                    source_service="state_manager",
                    correlation_id=identifier,
                    payload={
                        "scope": scope.value,
                        "identifier": identifier,
                        "key": key,
                        "old_value": old_value,
                        "new_value": value,
                    },
                )
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
            emit_event: Whether to emit StateTransitioned events
        """
        state_key = self._get_scope_identifier(scope, identifier)
        old_state = self._state[state_key].copy()
        self._state[state_key].update(updates)

        if emit_event:
            for key, new_value in updates.items():
                old_value = old_state.get(key)
                if old_value != new_value:
                    self._event_bus.publish(
                        StateTransitioned(
                            source_service="state_manager",
                            correlation_id=identifier,
                            payload={
                                "scope": scope.value,
                                "identifier": identifier,
                                "key": key,
                                "old_value": old_value,
                                "new_value": new_value,
                            },
                        )
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

        self._event_bus.publish(
            StateCheckpointed(
                source_service="state_manager",
                correlation_id=identifier,
                payload={
                    "snapshot_id": snapshot.snapshot_id,
                    "scope": scope.value,
                    "identifier": identifier,
                    "metadata": snapshot.metadata,
                },
            )
        )

        logger.info(f"Created checkpoint {snapshot.snapshot_id} for {scope.value}:{identifier}")
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

        self._event_bus.publish(
            StateRestored(
                source_service="state_manager",
                correlation_id=identifier,
                payload={
                    "snapshot_id": snapshot.snapshot_id,
                    "scope": scope.value,
                    "identifier": identifier,
                },
            )
        )

        logger.info(f"Restored checkpoint {snapshot.snapshot_id} for {scope.value}:{identifier}")
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
            logger.error(f"Failed to persist snapshot: {e}")

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
                count += 1
            except Exception as e:
                logger.warning(f"Failed to load snapshot {file_path}: {e}")

        return count

    def clear_scope(self, scope: StateScope, identifier: str) -> None:
        """Clear all state and history for an identifier."""
        state_key = self._scope_index.get(scope, {}).pop(identifier, None)
        if state_key:
            self._state.pop(state_key, None)
            self._history.pop(state_key, None)


# Global state manager instance
_global_state_manager: StateManager | None = None


def get_state_manager(persistence_path: Path | None = None) -> StateManager:
    """Get or create the global state manager."""
    global _global_state_manager
    if _global_state_manager is None:
        _global_state_manager = StateManager(persistence_path)
    return _global_state_manager


def set_state_manager(manager: StateManager) -> None:
    """Set the global state manager."""
    global _global_state_manager
    _global_state_manager = manager


__all__ = [
    "StateManager",
    "StateScope",
    "StateSnapshot",
    "get_state_manager",
    "set_state_manager",
]