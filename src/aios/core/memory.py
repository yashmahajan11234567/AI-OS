"""
Memory Manager for AI-OS Hermes Kernel.

Manages multiple memory systems:
- Working Memory: Short-term, session-scoped
- Claude Memory: Session persistence
- Engineering Intelligence: Long-term learnings
- Obsidian: Knowledge vault integration
- Graphify: Knowledge graph
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.types import (
    MemoryStored,
    MemoryRetrieved,
    MemoryUpdated,
    MemoryConsolidated,
)

logger = logging.getLogger(__name__)


class MemoryType(str, Enum):
    """Types of memory systems."""

    WORKING = "working"  # Short-term, session scope
    CLAUDE = "claude"  # Session persistence
    ENGINEERING = "engineering"  # Long-term learnings
    OBSIDIAN = "obsidian"  # Knowledge vault
    GRAPHIFY = "graphify"  # Knowledge graph


@dataclass
class MemoryEntry:
    """A memory entry."""

    key: str
    value: Any
    memory_type: MemoryType
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    expires_at: datetime | None = None


class MemoryBackend(ABC):
    """Abstract memory backend."""

    @abstractmethod
    async def store(self, entry: MemoryEntry) -> bool:
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> MemoryEntry | None:
        pass

    @abstractmethod
    async def update(self, key: str, value: Any, metadata: dict | None = None) -> bool:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def query(
        self,
        tags: list[str] | None = None,
        filter_fn: callable = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        pass

    @abstractmethod
    async def clear(self) -> int:
        pass


class FileMemoryBackend(MemoryBackend):
    """File-based memory backend."""

    def __init__(self, path: Path):
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, MemoryEntry] = {}
        self._load_index()

    def _load_index(self) -> None:
        for file in self._path.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                entry = MemoryEntry(
                    key=data["key"],
                    value=data["value"],
                    memory_type=MemoryType(data["memory_type"]),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    access_count=data.get("access_count", 0),
                    expires_at=(
                        datetime.fromisoformat(data["expires_at"])
                        if data.get("expires_at")
                        else None
                    ),
                )
                self._index[entry.key] = entry
            except Exception as e:
                logger.warning(f"Failed to load memory entry {file}: {e}")

    def _save_entry(self, entry: MemoryEntry) -> None:
        file_path = self._path / f"{entry.key}.json"
        data = {
            "key": entry.key,
            "value": entry.value,
            "memory_type": entry.memory_type.value,
            "tags": entry.tags,
            "metadata": entry.metadata,
            "created_at": entry.created_at.isoformat(),
            "updated_at": entry.updated_at.isoformat(),
            "access_count": entry.access_count,
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        }
        file_path.write_text(json.dumps(data, default=str))

    async def store(self, entry: MemoryEntry) -> bool:
        self._index[entry.key] = entry
        self._save_entry(entry)
        return True

    async def retrieve(self, key: str) -> MemoryEntry | None:
        entry = self._index.get(key)
        if entry and entry.expires_at and entry.expires_at < datetime.utcnow():
            await self.delete(key)
            return None
        if entry:
            entry.access_count += 1
            entry.updated_at = datetime.utcnow()
            self._save_entry(entry)
        return entry

    async def update(
        self, key: str, value: Any, metadata: dict | None = None
    ) -> bool:
        entry = self._index.get(key)
        if not entry:
            return False
        entry.value = value
        entry.updated_at = datetime.utcnow()
        if metadata:
            entry.metadata.update(metadata)
        self._save_entry(entry)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._index:
            del self._index[key]
            file_path = self._path / f"{key}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    async def query(
        self,
        tags: list[str] | None = None,
        filter_fn: callable = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        results = []
        for entry in self._index.values():
            if tags and not all(tag in entry.tags for tag in tags):
                continue
            if filter_fn and not filter_fn(entry):
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    async def clear(self) -> int:
        count = len(self._index)
        for file in self._path.glob("*.json"):
            file.unlink()
        self._index.clear()
        return count


class InMemoryBackend(MemoryBackend):
    """In-memory memory backend for testing."""

    def __init__(self):
        self._store: dict[str, MemoryEntry] = {}

    async def store(self, entry: MemoryEntry) -> bool:
        self._store[entry.key] = entry
        return True

    async def retrieve(self, key: str) -> MemoryEntry | None:
        entry = self._store.get(key)
        if entry and entry.expires_at and entry.expires_at < datetime.utcnow():
            await self.delete(key)
            return None
        if entry:
            entry.access_count += 1
            entry.updated_at = datetime.utcnow()
        return entry

    async def update(
        self, key: str, value: Any, metadata: dict | None = None
    ) -> bool:
        entry = self._store.get(key)
        if not entry:
            return False
        entry.value = value
        entry.updated_at = datetime.utcnow()
        if metadata:
            entry.metadata.update(metadata)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def query(
        self,
        tags: list[str] | None = None,
        filter_fn: callable = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        results = []
        for entry in self._store.values():
            if tags and not all(tag in entry.tags for tag in tags):
                continue
            if filter_fn and not filter_fn(entry):
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count


class MemoryManager:
    """
    Manages multiple memory systems.

    Each memory type has a different responsibility:
    - Working: Short-term, ephemeral, session-scoped
    - Claude: Persisted across sessions for continuity
    - Engineering: Long-term learnings, patterns, decisions
    - Obsidian: Knowledge vault, notes, documentation
    - Graphify: Knowledge graph, relationships, entities
    """

    def __init__(
        self,
        base_path: Path | None = None,
        backends: dict[MemoryType, MemoryBackend] | None = None,
    ):
        self._event_bus = get_event_bus()
        self._base_path = base_path or Path("./data/memory")
        self._base_path.mkdir(parents=True, exist_ok=True)

        self._backends: dict[MemoryType, MemoryBackend] = backends or {}
        self._init_default_backends()

    def _init_default_backends(self) -> None:
        """Initialize default file-based backends."""
        for mem_type in MemoryType:
            if mem_type not in self._backends:
                path = self._base_path / mem_type.value
                self._backends[mem_type] = FileMemoryBackend(path)

    def get_backend(self, memory_type: MemoryType) -> MemoryBackend:
        """Get backend for a memory type."""
        return self._backends[memory_type]

    def set_backend(self, memory_type: MemoryType, backend: MemoryBackend) -> None:
        """Set custom backend for a memory type."""
        self._backends[memory_type] = backend

    async def store(
        self,
        memory_type: MemoryType,
        key: str,
        value: Any,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
    ) -> MemoryEntry:
        """Store a value in memory."""
        entry = MemoryEntry(
            key=key,
            value=value,
            memory_type=memory_type,
            tags=tags or [],
            metadata=metadata or {},
            expires_at=expires_at,
        )

        backend = self._backends[memory_type]
        await backend.store(entry)

        self._event_bus.publish(
            MemoryStored(
                source_service="memory_manager",
                correlation_id=f"{memory_type.value}:{key}",
                payload={
                    "memory_id": key,
                    "memory_type": memory_type.value,
                    "key": key,
                    "tags": tags or [],
                },
            )
        )

        logger.debug(f"Stored in {memory_type.value}: {key}")
        return entry

    async def retrieve(
        self, memory_type: MemoryType, key: str
    ) -> MemoryEntry | None:
        """Retrieve a value from memory."""
        backend = self._backends[memory_type]
        entry = await backend.retrieve(key)

        if entry:
            self._event_bus.publish(
                MemoryRetrieved(
                    source_service="memory_manager",
                    correlation_id=f"{memory_type.value}:{key}",
                    payload={
                        "memory_id": key,
                        "memory_type": memory_type.value,
                        "key": key,
                        "found": True,
                    },
                )
            )

        return entry

    async def update(
        self,
        memory_type: MemoryType,
        key: str,
        value: Any,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Update a memory entry."""
        backend = self._backends[memory_type]
        result = await backend.update(key, value, metadata)

        if result:
            self._event_bus.publish(
                MemoryUpdated(
                    source_service="memory_manager",
                    correlation_id=f"{memory_type.value}:{key}",
                    payload={
                        "memory_id": key,
                        "memory_type": memory_type.value,
                        "key": key,
                        "changes": {"value": "updated"},
                    },
                )
            )

        return result

    async def delete(self, memory_type: MemoryType, key: str) -> bool:
        """Delete a memory entry."""
        backend = self._backends[memory_type]
        return await backend.delete(key)

    async def query(
        self,
        memory_type: MemoryType,
        tags: list[str] | None = None,
        filter_fn: callable = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Query memory entries."""
        backend = self._backends[memory_type]
        return await backend.query(tags, filter_fn, limit)

    async def consolidate(
        self,
        from_type: MemoryType,
        to_type: MemoryType,
        tags: list[str] | None = None,
        filter_fn: callable = None,
    ) -> int:
        """
        Consolidate memories from one type to another.

        Used for moving working memory -> engineering intelligence.
        """
        entries = await self.query(from_type, tags, filter_fn)
        count = 0

        for entry in entries:
            # Create new entry in target type
            new_entry = MemoryEntry(
                key=f"{entry.key}_consolidated_{datetime.utcnow().timestamp()}",
                value=entry.value,
                memory_type=to_type,
                tags=entry.tags + ["consolidated"],
                metadata={
                    **entry.metadata,
                    "source_type": from_type.value,
                    "source_key": entry.key,
                    "consolidated_at": datetime.utcnow().isoformat(),
                },
            )
            await self._backends[to_type].store(new_entry)
            count += 1

        if count > 0:
            self._event_bus.publish(
                MemoryConsolidated(
                    source_service="memory_manager",
                    correlation_id=f"consolidate:{from_type.value}:{to_type.value}",
                    payload={
                        "source_type": from_type.value,
                        "target_type": to_type.value,
                        "count": count,
                    },
                )
            )

        logger.info(f"Consolidated {count} entries from {from_type.value} to {to_type.value}")
        return count

    async def clear(self, memory_type: MemoryType) -> int:
        """Clear all entries in a memory type."""
        backend = self._backends[memory_type]
        return await backend.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        stats = {}
        for mem_type, backend in self._backends.items():
            if hasattr(backend, "_index"):
                stats[mem_type.value] = {
                    "entries": len(backend._index),
                    "backend": type(backend).__name__,
                }
            elif hasattr(backend, "_store"):
                stats[mem_type.value] = {
                    "entries": len(backend._store),
                    "backend": type(backend).__name__,
                }
        return stats


# Global memory manager
_global_memory_manager: MemoryManager | None = None


def get_memory_manager(
    base_path: Path | None = None,
) -> MemoryManager:
    """Get or create the global memory manager."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager(base_path)
    return _global_memory_manager


def set_memory_manager(manager: MemoryManager) -> None:
    """Set the global memory manager."""
    global _global_memory_manager
    _global_memory_manager = manager


__all__ = [
    "MemoryManager",
    "MemoryType",
    "MemoryEntry",
    "MemoryBackend",
    "FileMemoryBackend",
    "InMemoryBackend",
    "get_memory_manager",
    "set_memory_manager",
]