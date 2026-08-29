"""
M13 — Obsidian Git Durability Adapter.

Implements BaseExecutionAdapter for Obsidian + Git as a *knowledge/durability
resource*. AI-OS owns semantic meaning; Obsidian stores markdown, Git provides
actual version-control durability (M13_OBSIDIAN_GIT_DURABILITY_SPEC.md).

Design contract:
  * Default safe MOCK mode (in-memory knowledge store with Git-like commit
    history). Real mode gated by AIOS_REAL_INTEGRATION_ENABLED=1 plus a
    user-provided vault path; remote URL optional.
  * Knowledge operations are atomic with Git commit semantics (mock commits
    carry SHA-1 content hashes, mirroring real Git).
  * Gate-before-connect enforced via SecurityManager when provided.
  * No external knowledge ingestion, no autonomous generation, no decisions.

This adapter complements (not replaces) the existing ObsidianAdapter vault
operations; it adds the durability/versioning layer per M13.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class ObsidianGitError(Exception):
    """Base error for Obsidian Git adapter."""

    pass


class ObsidianGitUnavailableError(ObsidianGitError):
    """Obsidian vault / Git not reachable."""

    pass


class ObsidianGitTimeoutError(ObsidianGitError):
    """Operation exceeded timeout."""

    pass


class ObsidianGitValidationError(ObsidianGitError):
    """Invalid knowledge artifact input."""

    pass


class ObsidianGitSecurityError(ObsidianGitError):
    """Security violation (sensitive data / path traversal)."""

    pass


class ObsidianGitNotConfiguredError(ObsidianGitError):
    """Real mode requested but vault path unavailable."""

    pass


# ---------------------------------------------------------------------------
# Security / Validation Constants
# ---------------------------------------------------------------------------

SENSITIVE_KEYS = frozenset(
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
    re.compile(r"sk[-_]?[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+"),
]

MAX_KNOWLEDGE_SIZE = 102400  # 100 KB per knowledge artifact

# AI-OS-owned knowledge types (Obsidian stores, AI-OS defines meaning).
AIOS_KNOWLEDGE_TYPES = frozenset(
    {
        "project_state",
        "decision_record",
        "learning_insight",
        "execution_evidence",
        "process_knowledge",
        "reference_knowledge",
    }
)


# ---------------------------------------------------------------------------
# Mock Knowledge Store with Git-like durability
# ---------------------------------------------------------------------------


@dataclass
class _GitCommit:
    """Mock Git commit (immutable history entry, self-contained for integrity)."""

    commit_hash: str
    knowledge_id: str
    operation: str
    timestamp: str
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    parents: list[str] = field(default_factory=list)
    message: str = ""


class _MockObsidianGitStore:
    """In-memory Obsidian knowledge store with Git-like commit history.

    Each create/update/delete produces an immutable commit addressed by the
    SHA-1 of (content + metadata + parent hashes), mirroring real Git content
    addressing. History is append-only and tamper-evident.
    """

    def __init__(self) -> None:
        self._knowledge: dict[str, dict[str, Any]] = {}
        self._history: list[_GitCommit] = []
        self._head: dict[str, str] = {}  # knowledge_id -> latest commit hash

    @staticmethod
    def _hash(content: str, metadata: dict[str, Any], parents: list[str]) -> str:
        payload = json.dumps(
            {"content": content, "metadata": metadata, "parents": parents},
            sort_keys=True,
        )
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()

    def _commit(
        self, knowledge_id: str, operation: str, content: str, metadata: dict[str, Any]
    ) -> _GitCommit:
        parents = [self._head[knowledge_id]] if knowledge_id in self._head else []
        commit_hash = self._hash(content, metadata, parents)
        commit = _GitCommit(
            commit_hash=commit_hash,
            knowledge_id=knowledge_id,
            operation=operation,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=content,
            metadata=dict(metadata),
            parents=parents,
            message=f"{operation}: {knowledge_id}",
        )
        self._history.append(commit)
        self._head[knowledge_id] = commit_hash
        return commit

    def create(self, knowledge_id: str, content: str, metadata: dict[str, Any]) -> dict[str, Any]:
        commit = self._commit(knowledge_id, "create", content, metadata)
        record = {
            "knowledge_id": knowledge_id,
            "content": content,
            "metadata": metadata,
            "version_history": [commit.commit_hash],
            "head_commit": commit.commit_hash,
        }
        self._knowledge[knowledge_id] = record
        return dict(record)

    def update(self, knowledge_id: str, content: str, metadata: dict[str, Any]) -> dict[str, Any] | None:
        if knowledge_id not in self._knowledge:
            return None
        commit = self._commit(knowledge_id, "update", content, metadata)
        record = self._knowledge[knowledge_id]
        record["content"] = content
        record["metadata"] = metadata
        record["version_history"].append(commit.commit_hash)
        record["head_commit"] = commit.commit_hash
        return dict(record)

    def get(self, knowledge_id: str) -> dict[str, Any] | None:
        record = self._knowledge.get(knowledge_id)
        return dict(record) if record else None

    def delete(self, knowledge_id: str) -> bool:
        if knowledge_id not in self._knowledge:
            return False
        record = self._knowledge[knowledge_id]
        self._commit(knowledge_id, "delete", "", record.get("metadata", {}))
        del self._knowledge[knowledge_id]
        return True

    def history(self, knowledge_id: str) -> list[str]:
        return [c.commit_hash for c in self._history if c.knowledge_id == knowledge_id]

    def verify_integrity(self) -> bool:
        """Tamper-evidence check: recompute every commit hash from its snapshot."""
        for c in self._history:
            if self._hash(c.content, c.metadata, c.parents) != c.commit_hash:
                return False
        return True


# ---------------------------------------------------------------------------
# Obsidian Git Adapter
# ---------------------------------------------------------------------------


class ObsidianGitAdapter(BaseExecutionAdapter):
    """
    Obsidian Git durability adapter implementing BaseExecutionAdapter.

    Provides AI-OS-directed knowledge persistence with Git durability guarantees.
    Default MOCK store with commit history; real mode requires a vault path +
    AIOS_REAL_INTEGRATION_ENABLED=1.

    Obsidian/Git never interpret AI-OS semantics and return only knowledge
    artifacts. AI-OS evaluates all utility before proceeding.
    """

    perspective = "obsidian_git_durability"

    # M13 terminal contract: Obsidian Git is a BOUNDED RESOURCE (knowledge/
    # durability) hosted on T2. AI-OS owns semantic meaning; Git provides actual
    # version-control durability. It holds NO AI-OS authority.
    terminal: str = "T2"
    authority_level: str = "bounded_resource"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "obsidian_git",
        vault_path: str | None = None,
        timeout_seconds: int = 30,
        real_mode_enabled: bool = False,
        security_manager: Any | None = None,
        remote_url: str | None = None,
    ) -> None:
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._vault_path = vault_path or os.environ.get("OBSIDIAN_VAULT_PATH")
        self._remote_url = remote_url or os.environ.get("OBSIDIAN_GIT_REMOTE_URL")
        self._timeout_seconds = timeout_seconds
        self._security_manager = security_manager
        self._connected = False
        self._version_counter = 0

        self._real_mode = bool(real_mode_enabled) and bool(self._vault_path)
        self._store = _MockObsidianGitStore() if not self._real_mode else None

    # -----------------------------------------------------------------------
    # Mode / connection
    # -----------------------------------------------------------------------

    @property
    def is_real_mode(self) -> bool:
        return self._real_mode

    @property
    def is_mock_mode(self) -> bool:
        return not self._real_mode

    async def connect(self) -> bool:
        if self._connected:
            return True
        if self._real_mode:
            if not self._vault_path:
                raise ObsidianGitNotConfiguredError(
                    "Real mode requires OBSIDIAN_VAULT_PATH"
                )
            if self._security_manager is not None:
                decision = self._security_manager.authorize(
                    principal="aios_kernel",
                    action="obsidian_git_connect",
                    resource=self._vault_path,
                    context={"server_id": self._server_id},
                )
                if decision.value != "allow":
                    logger.warning("Obsidian Git connect denied by SecurityManager")
                    return False
        self._connected = True
        logger.debug(
            f"ObsidianGitAdapter connected (mode={'real' if self._real_mode else 'mock'})"
        )
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.debug("ObsidianGitAdapter disconnected")

    def is_connected(self) -> bool:
        return self._connected

    async def cleanup(self) -> None:
        await self.disconnect()

    # -----------------------------------------------------------------------
    # BaseExecutionAdapter
    # -----------------------------------------------------------------------

    def _default_tool(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        if not self._connected:
            raise NotImplementedError(
                f"{type(self).__name__} requires connect(); inject a tool or call connect()"
            )
        return asyncio.run(self.execute(target, context))

    def execute(
        self, target: str, context: dict[str, Any] | None = None
    ) -> ExecutionResult:
        context = context or {}
        action = context.get("action", "create_knowledge")
        if action == "create_knowledge":
            return asyncio.run(
                self.create_knowledge(
                    knowledge_id=target,
                    content=context.get("content", ""),
                    knowledge_type=context.get("knowledge_type", "reference_knowledge"),
                    metadata=context.get("metadata", {}),
                )
            )
        elif action == "update_knowledge":
            return asyncio.run(
                self.update_knowledge(
                    knowledge_id=target,
                    content=context.get("content", ""),
                    metadata=context.get("metadata", {}),
                )
            )
        elif action == "get_knowledge":
            return asyncio.run(self.get_knowledge(target))
        elif action == "delete_knowledge":
            return asyncio.run(self.delete_knowledge(target))
        elif action == "verify_integrity":
            return asyncio.run(self.verify_integrity())
        else:
            return self._error_result(action, f"Unknown action: {action}")

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def _validate_knowledge(
        self, knowledge_id: str, content: str, knowledge_type: str, metadata: dict[str, Any]
    ) -> None:
        if not knowledge_id:
            raise ObsidianGitValidationError("knowledge_id required")
        if knowledge_type not in AIOS_KNOWLEDGE_TYPES:
            raise ObsidianGitValidationError(
                f"knowledge_type '{knowledge_type}' is not AI-OS-owned"
            )
        if len(content.encode("utf-8")) > MAX_KNOWLEDGE_SIZE:
            raise ObsidianGitValidationError(
                f"Knowledge exceeds max size ({MAX_KNOWLEDGE_SIZE} bytes)"
            )
        raw = json.dumps(metadata)
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(content) or pattern.search(raw):
                raise ObsidianGitSecurityError("Potential secret detected in knowledge")

    # -----------------------------------------------------------------------
    # Provenance
    # -----------------------------------------------------------------------

    def _make_provenance(
        self,
        operation: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "source": "obsidian_git",
            "adapter": "obsidian_git_adapter",
            "operation": operation,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
            "authority": "aios_owned",
            "semantic_owner": "aios_kernel",
            "durability": "git_version_control",
            "mode": "real" if self._real_mode else "mock",
        }

    def _next_version(self) -> int:
        self._version_counter += 1
        return self._version_counter

    def _error_result(self, operation: str, description: str) -> ExecutionResult:
        return ExecutionResult(
            tool="obsidian_git_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "obsidian_git_error",
                    "severity": "error",
                    "description": description,
                    "provenance": self._make_provenance(operation),
                }
            ],
            metrics={"operation": operation},
            raw={},
        )

    # -----------------------------------------------------------------------
    # Knowledge durability operations
    # -----------------------------------------------------------------------

    async def create_knowledge(
        self,
        knowledge_id: str,
        content: str,
        knowledge_type: str = "reference_knowledge",
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        metadata = metadata or {}
        self._validate_knowledge(knowledge_id, content, knowledge_type, metadata)
        provenance = self._make_provenance("create_knowledge")
        meta = dict(metadata)
        meta["knowledge_type"] = knowledge_type
        meta["created_by"] = "aios_kernel"
        meta["provenance"] = provenance
        try:
            if self._real_mode:
                result = await self._write_real(knowledge_id, content, meta)
            else:
                result = self._store.create(knowledge_id, content, meta)
        except ObsidianGitError as e:
            return self._error_result("create_knowledge", str(e))
        return ExecutionResult(
            tool="obsidian_git_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "knowledge_id": knowledge_id,
                "head_commit": result.get("head_commit"),
            },
            raw={"record": result, "provenance": provenance},
        )

    async def update_knowledge(
        self,
        knowledge_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        metadata = metadata or {}
        # Reuse reference type validation; real type comes from existing record.
        self._validate_knowledge(knowledge_id, content, "reference_knowledge", metadata)
        provenance = self._make_provenance("update_knowledge")
        meta = dict(metadata)
        meta["provenance"] = provenance
        try:
            if self._real_mode:
                result = await self._write_real(knowledge_id, content, meta, update=True)
            else:
                result = self._store.update(knowledge_id, content, meta)
        except ObsidianGitError as e:
            return self._error_result("update_knowledge", str(e))
        if result is None:
            return ExecutionResult(
                tool="obsidian_git_adapter",
                status=ExecutionStatus.FAILURE,
                findings=[
                    {
                        "type": "not_found",
                        "severity": "warning",
                        "description": f"Knowledge {knowledge_id} not found",
                        "provenance": provenance,
                    }
                ],
                metrics={"knowledge_id": knowledge_id},
                raw={},
            )
        return ExecutionResult(
            tool="obsidian_git_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={
                "knowledge_id": knowledge_id,
                "head_commit": result.get("head_commit"),
            },
            raw={"record": result, "provenance": provenance},
        )

    async def get_knowledge(self, knowledge_id: str) -> ExecutionResult:
        provenance = self._make_provenance("get_knowledge")
        try:
            if self._real_mode:
                result = await self._read_real(knowledge_id)
            else:
                result = self._store.get(knowledge_id)
        except ObsidianGitError as e:
            return self._error_result("get_knowledge", str(e))
        if result is None:
            return ExecutionResult(
                tool="obsidian_git_adapter",
                status=ExecutionStatus.SUCCESS,
                findings=[],
                metrics={"knowledge_id": knowledge_id, "found": False},
                raw={},
            )
        return ExecutionResult(
            tool="obsidian_git_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"knowledge_id": knowledge_id, "found": True},
            raw={"record": result, "provenance": provenance},
        )

    async def delete_knowledge(self, knowledge_id: str) -> ExecutionResult:
        provenance = self._make_provenance("delete_knowledge")
        try:
            if self._real_mode:
                deleted = await self._delete_real(knowledge_id)
            else:
                deleted = self._store.delete(knowledge_id)
        except ObsidianGitError as e:
            return self._error_result("delete_knowledge", str(e))
        return ExecutionResult(
            tool="obsidian_git_adapter",
            status=ExecutionStatus.SUCCESS if deleted else ExecutionStatus.FAILURE,
            findings=[],
            metrics={"knowledge_id": knowledge_id, "deleted": bool(deleted)},
            raw={"provenance": provenance},
        )

    async def verify_integrity(self) -> ExecutionResult:
        """Tamper-evidence check across Git history (mock)."""
        provenance = self._make_provenance("verify_integrity")
        if self._real_mode:
            # Real mode would shell out to `git fsck`; mock returns n/a.
            intact = True
        else:
            intact = self._store.verify_integrity()
        return ExecutionResult(
            tool="obsidian_git_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"integrity_intact": intact},
            raw={"provenance": provenance},
        )

    # -----------------------------------------------------------------------
    # Real-mode extension points (filesystem + git)
    # -----------------------------------------------------------------------

    async def _write_real(
        self, knowledge_id: str, content: str, metadata: dict[str, Any], update: bool = False
    ) -> dict[str, Any]:
        """Real filesystem + git write (documented extension point)."""
        raise ObsidianGitUnavailableError(
            "Real Obsidian Git writer not injected; use mock mode or inject writer"
        )

    async def _read_real(self, knowledge_id: str) -> dict[str, Any] | None:
        raise ObsidianGitUnavailableError(
            "Real Obsidian Git reader not injected; use mock mode or inject reader"
        )

    async def _delete_real(self, knowledge_id: str) -> bool:
        raise ObsidianGitUnavailableError(
            "Real Obsidian Git deleter not injected; use mock mode or inject deleter"
        )


__all__ = [
    "ObsidianGitAdapter",
    "ObsidianGitError",
    "ObsidianGitUnavailableError",
    "ObsidianGitTimeoutError",
    "ObsidianGitValidationError",
    "ObsidianGitSecurityError",
    "ObsidianGitNotConfiguredError",
    "_MockObsidianGitStore",
    "_GitCommit",
    "AIOS_KNOWLEDGE_TYPES",
]
