"""Memory Service.

Engineering Service that wraps the Kernel's MemoryManager (in core/memory.py)
behind an event-driven facade. It preserves the existing manager and exposes:
  * an async API (store/retrieve/query/update/consolidate) the Kernel and
    Workflow can use; and
  * event subscriptions so that natural triggers (e.g. LearningCaptured ->
    Engineering Intelligence; CheckpointCreated -> Working Memory) update the
    right memory system without any service calling another directly.

The five memory systems (working / claude / engineering / obsidian / graphify)
each have a different responsibility and are not duplicated.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from aios.core.memory import MemoryEntry, MemoryManager, MemoryType, get_memory_manager
from aios.events.base import Event
from aios.events.types import (
    CheckpointCreated,
    LearningCaptured,
    MemoryConsolidated,
    MemoryRetrieved,
    MemoryStored,
    MemoryUpdated,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class MemoryService(BaseService):
    """Event-driven facade over the Kernel MemoryManager."""

    name = "memory"
    version = "1.0.0"
    description = "Working / Claude / Engineering / Obsidian / Graphify memory"
    depends_on: list[str] = []

    def __init__(self, *args, manager: MemoryManager | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager = manager or get_memory_manager()

    @property
    def manager(self) -> MemoryManager:
        return self._manager

    async def on_start(self) -> None:
        # Auto-routes: certain events imply a memory write to a specific store.
        self.subscribe(self.handle_learning_captured, LearningCaptured)
        self.subscribe(self.handle_checkpoint_created, CheckpointCreated)

    # ----- event handlers -------------------------------------------
    def handle_learning_captured(self, event: Event) -> None:
        # Learnings belong to Engineering Intelligence (the long-term store).
        self.store(
            memory_type=MemoryType.ENGINEERING,
            key=f"learning/{event.payload.get('learning_id', uuid4().hex[:8])}",
            value=event.payload,
            tags=["learning"],
            metadata={"kind": "learning"},
            correlation_id=event.correlation_id,
        )

    def handle_checkpoint_created(self, event: Event) -> None:
        # Record checkpoint metadata in Working Memory (short-term context).
        self.store(
            memory_type=MemoryType.WORKING,
            key=f"checkpoint/{event.payload.get('execution_id', 'unknown')}",
            value={
                "checkpoint_id": event.payload.get("checkpoint_id"),
                "step": event.payload.get("step"),
                "tags": event.payload.get("tags", []),
            },
            tags=["checkpoint"],
            metadata={"kind": "checkpoint"},
            correlation_id=event.correlation_id,
        )

    # ----- async API (delegates to the underlying manager) ----------
    def store(
        self,
        memory_type: MemoryType,
        key: str,
        value: Any,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> MemoryEntry:
        entry = self._manager.store(memory_type, key, value, tags=tags, metadata=metadata)
        self.emit(
            MemoryStored(
                source_service=self.name,
                correlation_id=correlation_id or key,
                payload={
                    "memory_type": memory_type.value,
                    "key": key,
                },
            )
        )
        return entry

    def retrieve(
        self,
        memory_type: MemoryType,
        key: str,
        correlation_id: str | None = None,
    ) -> MemoryEntry | None:
        entry = self._manager.retrieve(memory_type, key)
        self.emit(
            MemoryRetrieved(
                source_service=self.name,
                correlation_id=correlation_id or key,
                payload={
                    "memory_type": memory_type.value,
                    "key": key,
                    "found": entry is not None,
                },
            )
        )
        return entry

    def update(
        self,
        memory_type: MemoryType,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> bool:
        ok = self._manager.update(memory_type, key, value, metadata=metadata)
        self.emit(
            MemoryUpdated(
                source_service=self.name,
                correlation_id=correlation_id or key,
                payload={"memory_type": memory_type.value, "key": key, "success": ok},
            )
        )
        return ok

    def query(
        self,
        memory_type: MemoryType,
        tags: list[str] | None = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        return self._manager.query(memory_type, tags=tags, limit=limit)

    def consolidate(
        self,
        from_type: MemoryType,
        to_type: MemoryType,
        tags: list[str] | None = None,
        correlation_id: str | None = None,
    ) -> int:
        n = self._manager.consolidate(from_type, to_type, tags=tags)
        self.emit(
            MemoryConsolidated(
                source_service=self.name,
                correlation_id=correlation_id or from_type.value,
                payload={"from_type": from_type.value, "to_type": to_type.value, "count": n},
            )
        )
        return n

    def get_stats(self) -> dict[str, Any]:
        stats = self._manager.get_stats()
        base = super().get_stats()
        base["backends"] = stats
        return base


__all__ = ["MemoryService"]