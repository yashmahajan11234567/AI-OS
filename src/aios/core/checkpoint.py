"""
Checkpoint Manager for AI-OS Hermes Kernel.

Manages workflow checkpoints for recovery and replay capabilities.
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aios.core.state import StateManager, StateScope, get_state_manager
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

logger = logging.getLogger(__name__)


@dataclass
class Checkpoint:
    """A workflow checkpoint."""

    checkpoint_id: str
    workflow_id: str
    execution_id: str
    step: int
    state: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: list[str] = field(default_factory=list)


class CheckpointManager:
    """
    Manages workflow checkpoints for recovery and replay.

    Features:
    - Automatic checkpointing after each step
    - Manual checkpoint creation
    - Checkpoint listing and querying
    - Restore from checkpoint
    - Checkpoint cleanup/retention policies
    """

    def __init__(
        self,
        state_manager: StateManager | None = None,
        checkpoint_dir: Path | None = None,
        max_checkpoints_per_workflow: int = 100,
        auto_checkpoint: bool = True,
    ):
        """
        Initialize the Checkpoint Manager.

        Args:
            state_manager: State manager instance
            checkpoint_dir: Directory to store checkpoints
            max_checkpoints_per_workflow: Max checkpoints per workflow
            auto_checkpoint: Whether to auto-checkpoint after steps
        """
        self._state_manager = state_manager or get_state_manager()
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")
        self._checkpoint_dir = checkpoint_dir or Path("./data/checkpoints")
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._max_checkpoints = max_checkpoints_per_workflow
        self._auto_checkpoint = auto_checkpoint

        self._checkpoints: dict[str, list[Checkpoint]] = {}

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="CheckpointManager",
            version=SemanticVersion.parse("0.1.0"),
        )

    def create_checkpoint(
        self,
        execution_id: str,
        step: int,
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> Checkpoint:
        """
        Create a checkpoint for a workflow execution.

        Args:
            execution_id: Workflow execution ID
            step: Current step number
            metadata: Additional metadata
            tags: Tags for querying

        Returns:
            Created Checkpoint
        """
        workflow_state = self._state_manager.get_state(
            StateScope.WORKFLOW, execution_id, "workflow"
        )
        if not workflow_state:
            raise ValueError(f"No workflow state found for {execution_id}")

        workflow_id = workflow_state.get("workflow_id", "unknown")

        checkpoint = Checkpoint(
            checkpoint_id=f"cp_{datetime.utcnow().timestamp()}_{execution_id[:8]}",
            workflow_id=workflow_id,
            execution_id=execution_id,
            step=step,
            state=workflow_state,
            metadata=metadata or {},
            tags=tags or [],
        )

        # Store in memory
        if execution_id not in self._checkpoints:
            self._checkpoints[execution_id] = []
        self._checkpoints[execution_id].append(checkpoint)

        # Prune old checkpoints
        self._prune_checkpoints(execution_id)

        # Persist to disk
        self._persist_checkpoint(checkpoint)

        # Emit event using canonical CoreEvent
        self._emit_event(
            EventType.CHECKPOINT_CREATED,
            {
                "checkpoint_id": checkpoint.checkpoint_id,
                "workflow_id": workflow_id,
                "execution_id": execution_id,
                "step": step,
                "tags": checkpoint.tags,
            },
            execution_id,
        )

        logger.info(f"Created checkpoint {checkpoint.checkpoint_id} at step {step}")
        return checkpoint

    def restore_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str | None = None,
    ) -> Checkpoint:
        """
        Restore workflow state from a checkpoint.

        Args:
            execution_id: Workflow execution ID
            checkpoint_id: Specific checkpoint ID, or latest if None

        Returns:
            Restored Checkpoint
        """
        checkpoints = self._checkpoints.get(execution_id, [])
        if not checkpoints:
            # Try loading from disk
            self._load_checkpoints(execution_id)
            checkpoints = self._checkpoints.get(execution_id, [])

        if not checkpoints:
            raise ValueError(f"No checkpoints found for {execution_id}")

        if checkpoint_id:
            checkpoint = next((c for c in checkpoints if c.checkpoint_id == checkpoint_id), None)
            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
        else:
            checkpoint = checkpoints[-1]  # Latest

        # Restore state
        self._state_manager.set_state(
            StateScope.WORKFLOW, execution_id, "workflow", checkpoint.state
        )

        # Restore step results
        step_results = checkpoint.state.get("step_results", {})
        for step_id, result in step_results.items():
            self._state_manager.set_state(
                StateScope.WORKFLOW, execution_id, f"step_results.{step_id}", result
            )

        # Emit event using canonical CoreEvent
        self._emit_event(
            EventType.CHECKPOINT_RESTORED,
            {
                "checkpoint_id": checkpoint.checkpoint_id,
                "workflow_id": checkpoint.workflow_id,
                "execution_id": execution_id,
                "step": checkpoint.step,
            },
            execution_id,
        )

        logger.info(f"Restored checkpoint {checkpoint.checkpoint_id} for {execution_id}")
        return checkpoint

    def list_checkpoints(
        self,
        execution_id: str | None = None,
        workflow_id: str | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[Checkpoint]:
        """
        List checkpoints with optional filters.

        Args:
            execution_id: Filter by execution ID
            workflow_id: Filter by workflow ID
            tags: Filter by tags (all must match)
            limit: Maximum results

        Returns:
            List of matching checkpoints (newest first)
        """
        results = []

        if execution_id:
            checkpoints = self._checkpoints.get(execution_id, [])
            if not checkpoints:
                self._load_checkpoints(execution_id)
                checkpoints = self._checkpoints.get(execution_id, [])
            results = checkpoints
        else:
            for cps in self._checkpoints.values():
                results.extend(cps)

        # Apply filters
        if workflow_id:
            results = [c for c in results if c.workflow_id == workflow_id]
        if tags:
            results = [c for c in results if all(tag in c.tags for tag in tags)]

        # Sort by timestamp (newest first) and limit
        results.sort(key=lambda c: c.timestamp, reverse=True)
        return results[:limit]

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to delete

        Returns:
            True if deleted, False if not found
        """
        for execution_id, checkpoints in self._checkpoints.items():
            for i, cp in enumerate(checkpoints):
                if cp.checkpoint_id == checkpoint_id:
                    checkpoints.pop(i)
                    self._delete_persisted_checkpoint(checkpoint_id)

                    self._emit_event(
                        EventType.CHECKPOINT_PRUNED,
                        {
                            "checkpoint_id": checkpoint_id,
                        },
                        execution_id,
                    )
                    return True

        return False

    def delete_execution_checkpoints(self, execution_id: str) -> int:
        """
        Delete all checkpoints for an execution.

        Args:
            execution_id: Execution ID

        Returns:
            Number of checkpoints deleted
        """
        checkpoints = self._checkpoints.pop(execution_id, [])
        count = len(checkpoints)

        for cp in checkpoints:
            self._delete_persisted_checkpoint(cp.checkpoint_id)

        return count

    def _prune_checkpoints(self, execution_id: str) -> None:
        """Prune old checkpoints beyond max limit."""
        checkpoints = self._checkpoints.get(execution_id, [])
        if len(checkpoints) > self._max_checkpoints:
            to_remove = checkpoints[: -self._max_checkpoints]
            for cp in to_remove:
                self._delete_persisted_checkpoint(cp.checkpoint_id)
            self._checkpoints[execution_id] = checkpoints[-self._max_checkpoints :]

    def _persist_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Persist checkpoint to disk."""
        file_path = self._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
        try:
            data = {
                "checkpoint_id": checkpoint.checkpoint_id,
                "workflow_id": checkpoint.workflow_id,
                "execution_id": checkpoint.execution_id,
                "step": checkpoint.step,
                "state": checkpoint.state,
                "metadata": checkpoint.metadata,
                "timestamp": checkpoint.timestamp.isoformat(),
                "tags": checkpoint.tags,
            }
            file_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to persist checkpoint: {e}")

    def _load_checkpoints(self, execution_id: str) -> None:
        """Load checkpoints for an execution from disk."""
        self._checkpoints[execution_id] = []
        for file_path in self._checkpoint_dir.glob(f"*{execution_id[:8]}*.json"):
            try:
                data = json.loads(file_path.read_text())
                checkpoint = Checkpoint(
                    checkpoint_id=data["checkpoint_id"],
                    workflow_id=data["workflow_id"],
                    execution_id=data["execution_id"],
                    step=data["step"],
                    state=data["state"],
                    metadata=data["metadata"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    tags=data.get("tags", []),
                )
                self._checkpoints[execution_id].append(checkpoint)
            except Exception as e:
                logger.warning(f"Failed to load checkpoint {file_path}: {e}")

    def _delete_persisted_checkpoint(self, checkpoint_id: str) -> None:
        """Delete persisted checkpoint file."""
        file_path = self._checkpoint_dir / f"{checkpoint_id}.json"
        if file_path.exists():
            file_path.unlink()

    def cleanup_old_checkpoints(self, max_age_days: int = 30) -> int:
        """
        Clean up checkpoints older than max_age_days.

        Args:
            max_age_days: Maximum age in days

        Returns:
            Number of checkpoints deleted
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        deleted = 0

        for execution_id, checkpoints in list(self._checkpoints.items()):
            remaining = []
            for cp in checkpoints:
                if cp.timestamp < cutoff:
                    self._delete_persisted_checkpoint(cp.checkpoint_id)
                    deleted += 1
                else:
                    remaining.append(cp)
            self._checkpoints[execution_id] = remaining

        return deleted

    def get_stats(self) -> dict[str, Any]:
        """Get checkpoint statistics."""
        total = sum(len(cps) for cps in self._checkpoints.values())
        return {
            "total_checkpoints": total,
            "executions_with_checkpoints": len(self._checkpoints),
            "max_checkpoints_per_workflow": self._max_checkpoints,
            "auto_checkpoint": self._auto_checkpoint,
            "checkpoint_dir": str(self._checkpoint_dir),
        }


# Global checkpoint manager instance
_global_checkpoint_manager: CheckpointManager | None = None


def get_checkpoint_manager(
    state_manager: StateManager | None = None,
    checkpoint_dir: Path | None = None,
) -> CheckpointManager:
    """Get or create the global checkpoint manager."""
    global _global_checkpoint_manager
    if _global_checkpoint_manager is None:
        _global_checkpoint_manager = CheckpointManager(state_manager, checkpoint_dir)
    return _global_checkpoint_manager


def set_checkpoint_manager(manager: CheckpointManager) -> None:
    """Set the global checkpoint manager."""
    global _global_checkpoint_manager
    _global_checkpoint_manager = manager


def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str
    ) -> None:
        """Emit a canonical event via the canonical EventBus."""
        import uuid as uuid_mod

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4(),
            payload=payload,
        )
        result = self._event_bus.publish(event)
        # Fire and forget - result handling is async
        if hasattr(result, "__await__"):
            # Schedule on the event loop if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass


__all__ = [
    "CheckpointManager",
    "Checkpoint",
    "get_checkpoint_manager",
    "set_checkpoint_manager",
]