"""
M8-T4 — Obsidian Persistent Knowledge Vault Adapter.

Implements BaseExecutionAdapter for the Obsidian MCP server with
filesystem fallback. Provides vault operations: search, get, list, read.
All results marked advisory per C14 - Obsidian is TRUSTED_CONTEXTUAL knowledge.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class ObsidianError(Exception):
    """Base error for Obsidian adapter."""

    pass


class ObsidianUnavailableError(ObsidianError):
    """Obsidian MCP server not reachable."""

    pass


class ObsidianTimeoutError(ObsidianError):
    """Operation exceeded timeout."""

    pass


class ObsidianValidationError(ObsidianError):
    """Invalid input for Obsidian operation."""

    pass


class ObsidianSecurityError(ObsidianError):
    """Security violation (path traversal, sensitive data)."""

    pass


class ObsidianVaultNotFoundError(ObsidianError):
    """Configured vault path not found or inaccessible."""

    pass


class MalformedObsidianResponseError(ObsidianError):
    """Malformed response from Obsidian MCP."""

    pass


# ---------------------------------------------------------------------------
# Security / Validation Constants
# ---------------------------------------------------------------------------

SENSITIVE_PROPERTY_KEYS = frozenset(
    [
        "password",
        "token",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "private_key",
        "access_token",
    ]
)

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk[-_]?[a-zA-Z0-9]{20,}"),  # API keys
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),  # Bearer tokens
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+"),  # password assignments
]

MAX_NOTE_SIZE = 10240  # 10 KB
MAX_QUERY_LENGTH = 1000
MAX_SEARCH_RESULTS = 100
DEFAULT_VAULT_PATH = ""


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass
class Note:
    """Parsed Obsidian note with frontmatter and content."""

    path: str
    title: str
    content: str  # Body without frontmatter
    frontmatter: dict[str, Any]
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    provenance: dict[str, Any]


# ---------------------------------------------------------------------------
# Obsidian Adapter
# ---------------------------------------------------------------------------


class ObsidianAdapter(BaseExecutionAdapter):
    """
    Obsidian dual-path adapter implementing BaseExecutionAdapter.

    Path A: MCP server (when available)
    Path B: Direct filesystem access to local vault (fallback)

    Provides vault operations for persistent knowledge storage.

    All retrieved data is marked advisory per C14:
    - source=obsidian
    - advisory=True
    - authority=contextual
    - trust_level=trusted_contextual (local filesystem, but markdown can contain arbitrary text)
    """

    perspective = "obsidian_knowledge"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "obsidian",
        vault_path: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        """
        Initialize Obsidian adapter.

        Args:
            mcp_manager: MCPManager instance (deferred import).
                         If None, adapter operates in test/disconnected mode.
            server_id: MCP server identifier for Obsidian (default: "obsidian").
            vault_path: Direct filesystem path to Obsidian vault for fallback.
            timeout_seconds: Default timeout for Obsidian operations.
        """
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._vault_path = Path(vault_path) if vault_path else None
        self._timeout_seconds = timeout_seconds
        self._connected = False  # MCP path
        self._version_counter = 0
        self._tools_discovered = False

    # -----------------------------------------------------------------------
    # BaseExecutionAdapter implementation
    # -----------------------------------------------------------------------

    def _default_tool(
        self, target: str, context: dict[str, Any]
    ) -> ExecutionResult:
        """Production execution path - raises if neither path available."""
        if not self._connected and not self._vault_path:
            raise NotImplementedError(
                f"{type(self).__name__} requires either MCP connection or vault_path; "
                "inject a test tool, call connect(), or configure vault_path first"
            )
        # Default tries MCP first, then falls back to filesystem
        return asyncio.run(self.search_notes(target))

    def execute(
        self, target: str, context: dict[str, Any] | None = None
    ) -> ExecutionResult:
        """Execute Obsidian operation based on context action."""
        context = context or {}
        action = context.get("action", "search_notes")

        if action == "search_notes":
            return asyncio.run(
                self.search_notes(
                    target,
                    context.get("directory", "."),
                    context.get("limit", 50),
                )
            )
        elif action == "get_note":
            return asyncio.run(self.get_note(target))
        elif action == "list_notes":
            return asyncio.run(
                self.list_notes(context.get("directory", "."), context.get("limit", 100))
            )
        elif action == "read_note":
            return asyncio.run(self.read_note(target))
        else:
            return self._default_tool(target, context)

    # -----------------------------------------------------------------------
    # Connection Management
    # -----------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to Obsidian MCP server via MCPManager."""
        if self._connected:
            return True

        if self._mcp_manager is None:
            logger.warning("ObsidianAdapter: No MCPManager provided; cannot connect via MCP")
            return False

        try:
            result = await self._mcp_manager.connect(self._server_id)
            if result:
                self._connected = True
                await self._discover_tools()
                logger.info(f"ObsidianAdapter connected to '{self._server_id}'")
            return result
        except Exception as e:
            logger.warning(f"Failed to connect to Obsidian server: {e}")
            raise ObsidianUnavailableError(f"Failed to connect: {e}") from e

    async def _discover_tools(self) -> None:
        """Discover available Obsidian tools via tools/list."""
        if self._tools_discovered:
            return

        try:
            tools_result = await asyncio.wait_for(
                self._mcp_manager.call_tool(self._server_id, "tools/list", {}),
                timeout=self._timeout_seconds,
            )
            if tools_result.get("success"):
                tools = tools_result.get("result", {})
                logger.debug(f"Obsidian tools discovered: {list(tools.keys())}")
                self._tools_discovered = True
            else:
                logger.warning("Obsidian tools discovery returned no result")
        except Exception as e:
            logger.warning(f"Failed to discover Obsidian tools: {e}")

    async def disconnect(self) -> None:
        """Disconnect from Obsidian MCP server."""
        if self._mcp_manager:
            try:
                await self._mcp_manager.disconnect(self._server_id)
            except Exception as e:
                logger.warning(f"Error disconnecting Obsidian: {e}")
        self._connected = False
        self._tools_discovered = False
        logger.debug("ObsidianAdapter disconnected (MCP path)")

    def is_connected(self) -> bool:
        """Check if adapter is connected via MCP."""
        return self._connected

    async def cleanup(self) -> None:
        """Clean up resources."""
        await self.disconnect()

    # -----------------------------------------------------------------------
    # Version Counter
    # -----------------------------------------------------------------------

    def _next_version(self) -> int:
        """Generate monotonically increasing version counter."""
        self._version_counter += 1
        return self._version_counter

    # -----------------------------------------------------------------------
    # Provenance Tracking
    # -----------------------------------------------------------------------

    def _make_provenance(
        self,
        operation: str,
        execution_id: str | None = None,
        task_id: str | None = None,
        correlation_id: str | None = None,
        source_path: str | None = "mcp",
    ) -> dict[str, Any]:
        """Create provenance metadata for an Obsidian operation."""
        return {
            "source": "obsidian",
            "adapter": "obsidian_adapter",
            "operation": operation,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "execution_id": execution_id,
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
            "authority": "contextual",
            "advisory": True,
            "trust_level": "trusted_contextual",
            "retrieval_path": source_path,  # "mcp" or "filesystem"
        }

    def _mark_advisory(
        self, metadata: dict[str, Any], operation: str | None = None
    ) -> dict[str, Any]:
        """Mark metadata as advisory/contextual per C14 with full provenance."""
        marked = dict(metadata)
        # Start from a full provenance base so externally-sourced results carry
        # the complete required field set, not just the C14 markers.
        provenance = self._make_provenance(
            operation or "external_read",
            source_path=metadata.get("retrieval_path", "mcp"),
        )
        # Existing caller-supplied provenance takes precedence over defaults.
        provenance.update(marked.get("provenance", {}))
        # Re-apply C14 constants so they cannot be overridden by external data.
        provenance.update(
            {
                "source": "obsidian",
                "advisory": True,
                "authority": "contextual",
                "trust_level": "trusted_contextual",
                "obsidian_timestamp": datetime.utcnow().isoformat(),
            }
        )
        marked["provenance"] = provenance
        return marked

    # -----------------------------------------------------------------------
    # Security Validation
    # -----------------------------------------------------------------------

    def _validate_path(self, path: str) -> Path:
        """Validate and resolve path against vault boundary."""
        if not self._vault_path:
            raise ObsidianVaultNotFoundError("Vault path not configured")

        # Resolve the requested path
        try:
            requested = (self._vault_path / path).resolve()
            vault_root = self._vault_path.resolve()

            # Check for path traversal - requested must be within vault_root
            if not requested.is_relative_to(vault_root):
                raise ObsidianSecurityError(
                    f"Path traversal attempt detected: {path}"
                )

            # Block access to .obsidian directory
            if ".obsidian" in requested.parts:
                raise ObsidianSecurityError(
                    f"Access to .obsidian directory is forbidden: {path}"
                )

            return requested
        except ValueError as e:
            raise ObsidianSecurityError(f"Invalid path: {path}") from e

    def _validate_content(self, content: dict[str, Any]) -> None:
        """Validate content for size and sensitive data."""
        # Check property keys
        for key in content:
            key_lower = key.lower()
            if key_lower in SENSITIVE_PROPERTY_KEYS:
                raise ObsidianSecurityError(
                    f"Sensitive property key rejected: '{key}'"
                )

        # Check value sizes and secret patterns
        str_content = json.dumps(content)
        if len(str_content.encode("utf-8")) > MAX_NOTE_SIZE:
            raise ObsidianValidationError(
                f"Content exceeds max size ({MAX_NOTE_SIZE} bytes)"
            )

        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(str_content):
                raise ObsidianSecurityError(
                    f"Potential secret detected in content"
                )

    def _validate_query(self, query: str) -> None:
        """Validate query string."""
        if len(query) > MAX_QUERY_LENGTH:
            raise ObsidianValidationError(
                f"Query exceeds max length ({MAX_QUERY_LENGTH} chars)"
            )

    # -----------------------------------------------------------------------
    # Frontmatter Parsing
    # -----------------------------------------------------------------------

    def _parse_frontmatter(self, content: str) -> tuple[dict[str, Any], str]:
        """Parse YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return {}, content

        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}, content

        try:
            frontmatter = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\n")
        except yaml.YAMLError:
            return {}, content

        return frontmatter, body

    def _extract_tags(self, frontmatter: dict[str, Any], body: str) -> list[str]:
        """Extract tags from frontmatter and body."""
        tags = set()

        # From frontmatter
        fm_tags = frontmatter.get("tags", [])
        if isinstance(fm_tags, list):
            tags.update(fm_tags)
        elif isinstance(fm_tags, str):
            tags.add(fm_tags)

        # From body (hashtags)
        import re
        tag_pattern = re.compile(r"#([a-zA-Z0-9_\-]+)")
        tags.update(tag_pattern.findall(body))

        return sorted(tags)

    # -----------------------------------------------------------------------
    # MCP Tool Call Wrapper
    # -----------------------------------------------------------------------

    async def _call_tool(
        self, tool_name: str, arguments: dict[str, Any], operation: str
    ) -> dict[str, Any]:
        """Call an Obsidian MCP tool with error handling."""
        if not self._connected:
            raise ObsidianUnavailableError("Not connected to Obsidian server")

        try:
            result = await asyncio.wait_for(
                self._mcp_manager.call_tool(
                    self._server_id, tool_name, arguments
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            raise ObsidianTimeoutError(
                f"Obsidian tool '{tool_name}' timed out after {self._timeout_seconds}s"
            ) from None
        except Exception as e:
            raise ObsidianTimeoutError(f"Obsidian tool '{tool_name}' failed: {e}") from e

        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            if "not found" in error_msg.lower():
                return {"success": False, "not_found": True, "error": error_msg}
            raise MalformedObsidianResponseError(
                f"Obsidian tool '{tool_name}' returned error: {error_msg}"
            )

        return result.get("result", {})

    # -----------------------------------------------------------------------
    # Filesystem Operations (Fallback Path)
    # -----------------------------------------------------------------------

    async def _read_local(self, path: str) -> Note:
        """Read a note from local filesystem vault."""
        resolved_path = self._validate_path(path)

        if not resolved_path.exists():
            raise FileNotFoundError(f"Note not found: {path}")

        content = resolved_path.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(content)

        stat = resolved_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)

        tags = self._extract_tags(frontmatter, body)
        title = frontmatter.get("title", resolved_path.stem)

        provenance = self._make_provenance(
            "read_note",
            source_path="filesystem"
        )

        return Note(
            path=path,
            title=title,
            content=body,
            frontmatter=frontmatter,
            tags=tags,
            created_at=created_at,
            updated_at=updated_at,
            provenance=provenance,
        )

    async def _search_local(
        self, query: str, directory: str = ".", limit: int = 50
    ) -> list[Note]:
        """Search notes in local filesystem vault."""
        self._validate_query(query)
        limit = min(limit, MAX_SEARCH_RESULTS)

        vault_dir = self._vault_path
        if directory != ".":
            vault_dir = self._validate_path(directory)

        results = []
        query_lower = query.lower()

        for md_file in vault_dir.rglob("*.md"):
            # Check path traversal
            try:
                rel_path = str(md_file.relative_to(self._vault_path))
            except ValueError:
                continue

            # Skip .obsidian
            if ".obsidian" in md_file.parts:
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                frontmatter, body = self._parse_frontmatter(content)

                # Search in title, body, tags (lowercased copies for matching;
                # the note itself keeps its original casing)
                full_title = str(frontmatter.get("title", md_file.stem))
                title_lower = full_title.lower()
                tags = self._extract_tags(frontmatter, body)
                tags_lower = " ".join(tags).lower()

                if (
                    query_lower in title_lower
                    or query_lower in body.lower()
                    or query_lower in tags_lower
                ):
                    stat = md_file.stat()
                    created_at = datetime.fromtimestamp(stat.st_ctime)
                    updated_at = datetime.fromtimestamp(stat.st_mtime)

                    provenance = self._make_provenance(
                        "search_notes",
                        source_path="filesystem"
                    )

                    note = Note(
                        path=rel_path,
                        title=full_title,
                        content=body,
                        frontmatter=frontmatter,
                        tags=tags,
                        created_at=created_at,
                        updated_at=updated_at,
                        provenance=provenance,
                    )
                    results.append(note)

                    if len(results) >= limit:
                        break
            except Exception as e:
                logger.warning(f"Failed to read {md_file}: {e}")
                continue

        return results

    async def _list_local(
        self, directory: str = ".", limit: int = 100
    ) -> list[dict[str, Any]]:
        """List notes in local filesystem vault directory."""
        vault_dir = self._vault_path
        if directory != ".":
            vault_dir = self._validate_path(directory)

        results = []
        for md_file in vault_dir.rglob("*.md"):
            # Skip .obsidian
            if ".obsidian" in md_file.parts:
                continue

            try:
                rel_path = str(md_file.relative_to(self._vault_path))
                content = md_file.read_text(encoding="utf-8")
                frontmatter, body = self._parse_frontmatter(content)
                title = frontmatter.get("title", md_file.stem)
                tags = self._extract_tags(frontmatter, body)
                stat = md_file.stat()

                provenance = self._make_provenance(
                    "list_notes",
                    source_path="filesystem"
                )

                results.append({
                    "path": rel_path,
                    "title": title,
                    "tags": tags,
                    "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "provenance": provenance,
                })

                if len(results) >= limit:
                    break
            except Exception as e:
                logger.warning(f"Failed to read {md_file}: {e}")
                continue

        return results

    # -----------------------------------------------------------------------
    # Unified Operations (MCP primary, filesystem fallback)
    # -----------------------------------------------------------------------

    async def search_notes(
        self, query: str, directory: str = ".", limit: int = 50
    ) -> ExecutionResult:
        """Search Obsidian notes by query (MCP first, fallback to filesystem)."""
        self._validate_query(query)
        limit = min(limit, MAX_SEARCH_RESULTS)
        provenance = self._make_provenance("search_notes")

        # Try MCP path first
        if self._connected:
            try:
                result = await self._call_tool(
                    "search_notes",
                    {"query": query, "directory": directory, "limit": limit},
                    "search_notes",
                )

                notes = result.get("notes", [])
                marked_notes = [
                    self._mark_advisory(note, operation="search_notes") for note in notes
                ]

                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={
                        "query": query,
                        "directory": directory,
                        "notes_returned": len(marked_notes),
                        "retrieval_path": "mcp",
                    },
                    raw={"notes": marked_notes},
                )
            except (ObsidianUnavailableError, ObsidianTimeoutError, MalformedObsidianResponseError) as e:
                logger.warning(f"Obsidian MCP search failed, falling back to filesystem: {e}")

        # Fallback to filesystem
        if self._vault_path and self._vault_path.exists():
            try:
                local_notes = await self._search_local(query, directory, limit)
                marked_notes = [
                    self._mark_advisory(note.__dict__, operation="search_notes")
                    for note in local_notes
                ]

                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={
                        "query": query,
                        "directory": directory,
                        "notes_returned": len(marked_notes),
                        "retrieval_path": "filesystem_fallback",
                    },
                    raw={"notes": marked_notes},
                )
            except Exception as e:
                logger.error(f"Obsidian filesystem search failed: {e}")
                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.ERROR,
                    findings=[
                        {
                            "type": "search_failed",
                            "severity": "error",
                            "description": f"Both MCP and filesystem search failed: {e}",
                            "provenance": provenance,
                        }
                    ],
                    metrics={"query": query},
                    raw={},
                )

        # Neither path available
        return ExecutionResult(
            tool="obsidian_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "unavailable",
                    "severity": "error",
                    "description": "Obsidian unavailable: not connected to MCP and no vault_path configured",
                    "provenance": provenance,
                }
            ],
            metrics={"query": query},
            raw={},
        )

    async def get_note(self, path: str) -> ExecutionResult:
        """Get an Obsidian note by path (MCP first, fallback to filesystem)."""
        provenance = self._make_provenance("get_note")

        # Try MCP path first
        if self._connected:
            try:
                result = await self._call_tool(
                    "get_note", {"path": path}, "get_note"
                )

                if isinstance(result, dict) and result.get("not_found"):
                    return ExecutionResult(
                        tool="obsidian_adapter",
                        status=ExecutionStatus.SUCCESS,
                        findings=[],
                        metrics={"path": path, "found": False},
                        raw={},
                    )

                if result:
                    marked_result = self._mark_advisory(result, operation="get_note")
                    return ExecutionResult(
                        tool="obsidian_adapter",
                        status=ExecutionStatus.SUCCESS,
                        findings=[],
                        metrics={"path": path, "found": True, "retrieval_path": "mcp"},
                        raw=marked_result,
                    )
            except (ObsidianUnavailableError, ObsidianTimeoutError, MalformedObsidianResponseError) as e:
                logger.warning(f"Obsidian MCP get_note failed, falling back to filesystem: {e}")

        # Fallback to filesystem
        if self._vault_path and self._vault_path.exists():
            try:
                note = await self._read_local(path)
                marked_note = self._mark_advisory(note.__dict__, operation="get_note")

                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={"path": path, "found": True, "retrieval_path": "filesystem_fallback"},
                    raw=marked_note,
                )
            except FileNotFoundError:
                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={"path": path, "found": False, "retrieval_path": "filesystem_fallback"},
                    raw={},
                )
            except ObsidianVaultNotFoundError:
                pass  # Fall through to error
            except Exception as e:
                logger.error(f"Obsidian filesystem get_note failed: {e}")

        # Neither path available or both failed
        return ExecutionResult(
            tool="obsidian_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "unavailable",
                    "severity": "error",
                    "description": "Obsidian unavailable: not connected to MCP and no vault_path configured",
                    "provenance": provenance,
                }
            ],
            metrics={"path": path},
            raw={},
        )

    async def list_notes(
        self, directory: str = ".", limit: int = 100
    ) -> ExecutionResult:
        """List notes in a directory (MCP first, fallback to filesystem)."""
        provenance = self._make_provenance("list_notes")

        # Try MCP path first
        if self._connected:
            try:
                result = await self._call_tool(
                    "list_notes",
                    {"directory": directory, "limit": limit},
                    "list_notes",
                )

                notes = result.get("notes", [])
                marked_notes = [
                    self._mark_advisory(note, operation="list_notes") for note in notes
                ]

                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={
                        "directory": directory,
                        "notes_returned": len(marked_notes),
                        "retrieval_path": "mcp",
                    },
                    raw={"notes": marked_notes},
                )
            except (ObsidianUnavailableError, ObsidianTimeoutError, MalformedObsidianResponseError) as e:
                logger.warning(f"Obsidian MCP list_notes failed, falling back to filesystem: {e}")

        # Fallback to filesystem
        if self._vault_path and self._vault_path.exists():
            try:
                local_notes = await self._list_local(directory, limit)
                # M9-N8 / D-06: the filesystem fallback previously bypassed
                # ``_mark_advisory`` — notes carried only ``_make_provenance``
                # without the C14 marker set (no ``obsidian_timestamp``). Route
                # every fallback note through the canonical advisory gate.
                marked_local = [
                    self._mark_advisory(note, operation="list_notes")
                    for note in local_notes
                ]

                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={
                        "directory": directory,
                        "notes_returned": len(marked_local),
                        "retrieval_path": "filesystem_fallback",
                    },
                    raw={"notes": marked_local},
                )
            except Exception as e:
                logger.error(f"Obsidian filesystem list_notes failed: {e}")
                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.ERROR,
                    findings=[
                        {
                            "type": "list_failed",
                            "severity": "error",
                            "description": f"Both MCP and filesystem list failed: {e}",
                            "provenance": provenance,
                        }
                    ],
                    metrics={"directory": directory},
                    raw={},
                )

        # Neither path available
        return ExecutionResult(
            tool="obsidian_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "unavailable",
                    "severity": "error",
                    "description": "Obsidian unavailable: not connected to MCP and no vault_path configured",
                    "provenance": provenance,
                }
            ],
            metrics={"directory": directory},
            raw={},
        )

    async def read_note(self, path: str) -> ExecutionResult:
        """Read an Obsidian note with full content (MCP first, fallback to filesystem)."""
        provenance = self._make_provenance("read_note")

        # Try MCP path first
        if self._connected:
            try:
                result = await self._call_tool(
                    "read_note", {"path": path}, "read_note"
                )

                if isinstance(result, dict) and result.get("not_found"):
                    return ExecutionResult(
                        tool="obsidian_adapter",
                        status=ExecutionStatus.SUCCESS,
                        findings=[],
                        metrics={"path": path, "found": False},
                        raw={},
                    )

                if result:
                    marked_result = self._mark_advisory(result, operation="read_note")
                    return ExecutionResult(
                        tool="obsidian_adapter",
                        status=ExecutionStatus.SUCCESS,
                        findings=[],
                        metrics={"path": path, "found": True, "retrieval_path": "mcp"},
                        raw=marked_result,
                    )
            except (ObsidianUnavailableError, ObsidianTimeoutError, MalformedObsidianResponseError) as e:
                logger.warning(f"Obsidian MCP read_note failed, falling back to filesystem: {e}")

        # Fallback to filesystem
        if self._vault_path and self._vault_path.exists():
            try:
                note = await self._read_local(path)
                marked_note = self._mark_advisory(note.__dict__, operation="read_note")

                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={"path": path, "found": True, "retrieval_path": "filesystem_fallback"},
                    raw=marked_note,
                )
            except FileNotFoundError:
                return ExecutionResult(
                    tool="obsidian_adapter",
                    status=ExecutionStatus.SUCCESS,
                    findings=[],
                    metrics={"path": path, "found": False, "retrieval_path": "filesystem_fallback"},
                    raw={},
                )
            except ObsidianVaultNotFoundError:
                pass  # Fall through to error
            except Exception as e:
                logger.error(f"Obsidian filesystem read_note failed: {e}")

        # Neither path available or both failed
        return ExecutionResult(
            tool="obsidian_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "unavailable",
                    "severity": "error",
                    "description": "Obsidian unavailable: not connected to MCP and no vault_path configured",
                    "provenance": provenance,
                }
            ],
            metrics={"path": path},
            raw={},
        )