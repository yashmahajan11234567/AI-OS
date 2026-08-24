"""
Memory Manager for AI-OS Hermes Kernel.

Manages multiple memory systems:
- Working Memory: Short-term, session-scoped
- Claude Memory: Session persistence
- Engineering Intelligence: Long-term learnings
- Obsidian: Knowledge vault integration
- Graphify: Knowledge graph
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

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
        for file in self._path.rglob("*.json"):
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
        # Ensure parent directories exist for keys with slashes
        file_path.parent.mkdir(parents=True, exist_ok=True)
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


class GraphifyBackend(MemoryBackend):
    """Graphify knowledge graph memory backend for AI-OS M5-GATE-REALIZE.

    Implements MemoryBackend for MemoryType.GRAPHIFY using MCP connection to
    Graphify server. Provides graph operations:
    - query_graph: Query the knowledge graph
    - shortest_path: Find shortest path between entities

    Inferred edges remain advisory per architecture (C14).
    All inferred relationships are explicitly marked with provenance indicating
    their advisory nature and must not be treated as authoritative/canonical data.
    """

    def __init__(
        self,
        mcp_manager,
        server_id: str = "graphify",
    ) -> None:
        """Initialize Graphify backend.

        Args:
            mcp_manager: MCPManager instance for communicating with Graphify server
            server_id: MCP server identifier for Graphify
        """
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._connected = False

    def _mark_advisory(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Mark metadata as advisory/inferred per C14.

        All Graphify inferred edges and relationships must carry explicit
        provenance indicating their advisory nature.
        """
        marked = dict(metadata)
        marked["provenance"] = marked.get("provenance", {})
        marked["provenance"]["source"] = "graphify_inferred"
        marked["provenance"]["advisory"] = True
        marked["provenance"]["authority"] = "advisory_only"
        marked["provenance"]["graphify_timestamp"] = datetime.utcnow().isoformat()
        return marked

    async def connect(self) -> bool:
        """Connect to Graphify MCP server."""
        if self._connected:
            return True

        try:
            result = await self._mcp_manager.connect(self._server_id)
            self._connected = result
            return result
        except Exception as e:
            logger.warning(f"Failed to connect to Graphify server: {e}")
            return False

    async def _ensure_connected(self) -> bool:
        """Ensure connection to Graphify server."""
        if not self._connected:
            return await self.connect()
        return self._connected

    async def store(self, entry: MemoryEntry) -> bool:
        """Store an entry as a node in the knowledge graph."""
        if not await self._ensure_connected():
            return False

        try:
            # Store as node in graph via add_node tool
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "add_node",
                {
                    "node_id": entry.key,
                    "label": entry.key,
                    "properties": {
                        **entry.metadata,
                        "value": str(entry.value),
                        "memory_type": entry.memory_type.value,
                        "tags": entry.tags,
                        "created_at": entry.created_at.isoformat(),
                        "updated_at": entry.updated_at.isoformat(),
                    },
                },
            )
            return result.get("success", False)
        except Exception as e:
            logger.warning(f"Failed to store in Graphify: {e}")
            return False

    async def retrieve(self, key: str) -> MemoryEntry | None:
        """Retrieve a node from the knowledge graph.

        C14: Retrieved data from Graphify is marked as advisory/inferred.
        """
        if not await self._ensure_connected():
            return None

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "get_node",
                {"node_id": key},
            )

            if not result.get("success") or not result.get("result"):
                return None

            node_data = result["result"]
            properties = node_data.get("properties", {})
            # C14: Mark retrieved data as advisory
            marked_metadata = self._mark_advisory(
                {k: v for k, v in properties.items() if k not in ("value", "tags", "memory_type")}
            )
            return MemoryEntry(
                key=key,
                value=properties.get("value", ""),
                memory_type=MemoryType.GRAPHIFY,
                tags=properties.get("tags", []),
                metadata=marked_metadata,
                created_at=datetime.fromisoformat(properties.get("created_at", datetime.utcnow().isoformat())),
                updated_at=datetime.fromisoformat(properties.get("updated_at", datetime.utcnow().isoformat())),
            )
        except Exception as e:
            logger.warning(f"Failed to retrieve from Graphify: {e}")
            return None

    async def update(
        self, key: str, value: Any, metadata: dict | None = None
    ) -> bool:
        """Update a node in the knowledge graph."""
        if not await self._ensure_connected():
            return False

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "update_node",
                {
                    "node_id": key,
                    "properties": {
                        "value": str(value),
                        **(metadata or {}),
                        "updated_at": datetime.utcnow().isoformat(),
                    },
                },
            )
            return result.get("success", False)
        except Exception as e:
            logger.warning(f"Failed to update in Graphify: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete a node from the knowledge graph."""
        if not await self._ensure_connected():
            return False

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "delete_node",
                {"node_id": key},
            )
            return result.get("success", False)
        except Exception as e:
            logger.warning(f"Failed to delete from Graphify: {e}")
            return False

    async def query(
        self,
        tags: list[str] | None = None,
        filter_fn: callable = None,
        limit: int = 100,
    ) -> list[MemoryEntry]:
        """Query the knowledge graph (uses query_graph operation).

        All returned entries are marked as advisory per C14 - Graphify inferred
        edges and relationships are advisory only, not authoritative.
        """
        if not await self._ensure_connected():
            return []

        try:
            # Build Cypher-like query
            query_parts = []
            if tags:
                query_parts.append(f"MATCH (n) WHERE {' AND '.join([f'n.tags CONTAINS \"{tag}\"' for tag in tags])}")
            else:
                query_parts.append("MATCH (n)")

            query_parts.append(f"RETURN n LIMIT {limit}")
            query = " ".join(query_parts)

            result = await self._mcp_manager.call_tool(
                self._server_id,
                "query_graph",
                {"query": query},
            )

            if not result.get("success") or not result.get("result"):
                return []

            entries = []
            for node_data in result["result"].get("nodes", []):
                properties = node_data.get("properties", {})
                # C14: Mark all graph-queried data as advisory/inferred
                marked_metadata = self._mark_advisory(
                    {k: v for k, v in properties.items() if k not in ("value", "tags")}
                )
                entry = MemoryEntry(
                    key=node_data.get("id", ""),
                    value=properties.get("value", ""),
                    memory_type=MemoryType.GRAPHIFY,
                    tags=properties.get("tags", []),
                    metadata=marked_metadata,
                    created_at=datetime.fromisoformat(properties.get("created_at", datetime.utcnow().isoformat())),
                    updated_at=datetime.fromisoformat(properties.get("updated_at", datetime.utcnow().isoformat())),
                )
                entries.append(entry)

            return entries
        except Exception as e:
            logger.warning(f"Failed to query Graphify: {e}")
            return []

    async def clear(self) -> int:
        """Clear all nodes (not recommended for production Graphify)."""
        # Graphify clear would require a different approach
        # For now, return 0 to indicate not implemented
        logger.warning("GraphifyBackend.clear() not fully implemented - use direct MCP tools")
        return 0

    # Graphify-specific operations
    async def query_graph(self, query: str) -> dict[str, Any]:
        """Execute a custom graph query.

        C14: Results from Graphify are advisory/inferred and must not be
        treated as authoritative.
        """
        if not await self._ensure_connected():
            return {"success": False, "error": "Not connected"}

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "query_graph",
                {"query": query},
            )
            return result.get("result", {})
        except Exception as e:
            logger.warning(f"Graphify query failed: {e}")
            return {"success": False, "error": str(e)}

    async def shortest_path(
        self, from_node: str, to_node: str, max_depth: int = 10
    ) -> list[str]:
        """Find shortest path between two nodes.

        C14: The returned path is based on Graphify inferred edges and is advisory only.
        Must not be treated as authoritative routing/dependency information.
        """
        if not await self._ensure_connected():
            return []

        try:
            result = await self._mcp_manager.call_tool(
                self._server_id,
                "shortest_path",
                {
                    "from_node": from_node,
                    "to_node": to_node,
                    "max_depth": max_depth,
                },
            )

            if not result.get("success") or not result.get("result"):
                return []

            # C14: Return path with advisory metadata
            path = result["result"].get("path", [])
            # The path itself is a list of node IDs - the advisory nature is documented
            # in the method docstring and that it comes from Graphify inference.
            return path
        except Exception as e:
            logger.warning(f"Graphify shortest_path failed: {e}")
            return []


class MemoryManager:
    """
    Manages multiple memory systems.

    Each memory type has a different responsibility:
    - Working: Short-term, ephemeral, session-scoped
    - Claude: Persisted across sessions for continuity
    - Engineering: Long-term learnings, patterns, decisions
    - Obsidian: Knowledge vault, notes, documentation
    - Graphify: Knowledge graph, relationships, entities (advisory per C14)
    """

    def __init__(
        self,
        base_path: Path | None = None,
        backends: dict[MemoryType, MemoryBackend] | None = None,
        mcp_manager: Optional[Any] = None,
    ):
        # FIX 9: Use canonical EventBus (C1, Task 5)
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            logger.warning("Canonical EventBus not yet initialized; events will be deferred")
        self._base_path = base_path or Path("./data/memory")
        self._base_path.mkdir(parents=True, exist_ok=True)

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="MemoryManager",
            version=SemanticVersion.parse("0.1.0"),
        )

        self._backends: dict[MemoryType, MemoryBackend] = backends or {}
        self._mcp_manager = mcp_manager
        self._init_default_backends()

    def _init_default_backends(self) -> None:
        """Initialize default file-based backends, with Graphify wiring if MCP available."""
        for mem_type in MemoryType:
            if mem_type not in self._backends:
                if mem_type == MemoryType.GRAPHIFY and self._mcp_manager is not None:
                    # Try to use GraphifyBackend if MCP manager is available
                    self._backends[mem_type] = GraphifyBackend(self._mcp_manager)
                    logger.info("GraphifyBackend wired for MemoryType.GRAPHIFY via MCPManager")
                else:
                    path = self._base_path / mem_type.value
                    self._backends[mem_type] = FileMemoryBackend(path)

    def get_backend(self, memory_type: MemoryType) -> MemoryBackend:
        """Get backend for a memory type."""
        return self._backends[memory_type]

    def _emit_event(self, event_type: EventType, payload: dict[str, Any], correlation_id: str) -> None:
        """Emit a canonical event via the canonical EventBus."""
        # Ensure correlation_id is a valid UUID - generate one if it's not
        try:
            corr_uuid = uuid.UUID(correlation_id) if correlation_id else uuid.uuid4()
        except ValueError:
            # Not a valid UUID, generate a deterministic one from the string
            corr_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, correlation_id)
        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=corr_uuid,
            payload=payload,
        )
        result = self._event_bus.publish(event) if self._event_bus else None
        # Fire and forget - result handling is async
        if result and hasattr(result, "__await__"):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

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

        self._emit_event(
            EventType.MEMORY_STORED,
            {
                "memory_id": key,
                "memory_type": memory_type.value,
                "key": key,
                "tags": tags or [],
            },
            f"{memory_type.value}:{key}",
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
            self._emit_event(
                EventType.MEMORY_RETRIEVED,
                {
                    "memory_id": key,
                    "memory_type": memory_type.value,
                    "key": key,
                    "found": True,
                },
                f"{memory_type.value}:{key}",
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
            self._emit_event(
                EventType.MEMORY_UPDATED,
                {
                    "memory_id": key,
                    "memory_type": memory_type.value,
                    "key": key,
                    "changes": {"value": "updated"},
                },
                f"{memory_type.value}:{key}",
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
            self._emit_event(
                EventType.MEMORY_CONSOLIDATED,
                {
                    "source_type": from_type.value,
                    "target_type": to_type.value,
                    "count": count,
                },
                f"consolidate:{from_type.value}:{to_type.value}",
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
    mcp_manager: Optional[Any] = None,
) -> MemoryManager:
    """Get or create the global memory manager."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = MemoryManager(base_path, mcp_manager=mcp_manager)
    elif mcp_manager is not None and _global_memory_manager._mcp_manager is None:
        # Update existing manager with MCP manager if not already set
        _global_memory_manager._mcp_manager = mcp_manager
        # Re-initialize backends if Graphify was using file-based
        if isinstance(_global_memory_manager._backends.get(MemoryType.GRAPHIFY), FileMemoryBackend):
            _global_memory_manager._backends[MemoryType.GRAPHIFY] = GraphifyBackend(mcp_manager)
            logger.info("GraphifyBackend wired for MemoryType.GRAPHIFY via MCPManager (deferred)")
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
    "GraphifyBackend",
    "get_memory_manager",
    "set_memory_manager",
]