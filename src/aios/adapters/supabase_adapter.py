"""
M13 — Supabase Persistent Storage Adapter.

Implements BaseExecutionAdapter for Supabase as a *bounded persistence resource*.
AI-OS retains semantic ownership of all stored data; Supabase stores dumb bytes
and provides durability (M13_SUPABASE_INTEGRATION_SPEC.md).

Design contract (mirrors NotionAdapter / ObsidianAdapter conventions):
  * Default safe MOCK mode (in-memory store). Real mode gated by
    AIOS_REAL_INTEGRATION_ENABLED=1 and requires user-provided credentials.
  * All reads/writes go through AI-OS-owned schemas (provenance carried).
  * Gate-before-connect enforced via SecurityManager when provided.
  * No second authority, no autonomous triggers, no external interpretation.
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


class SupabaseError(Exception):
    """Base error for Supabase adapter."""

    pass


class SupabaseUnavailableError(SupabaseError):
    """Supabase endpoint not reachable."""

    pass


class SupabaseTimeoutError(SupabaseError):
    """Operation exceeded timeout."""

    pass


class SupabaseValidationError(SupabaseError):
    """Invalid input for Supabase operation."""

    pass


class SupabaseSecurityError(SupabaseError):
    """Security violation (sensitive data attempt)."""

    pass


class SupabaseNotConfiguredError(SupabaseError):
    """Real mode requested but credentials unavailable."""

    pass


class MalformedSupabaseResponseError(SupabaseError):
    """Malformed response from Supabase."""

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
        "service_role_key",
    ]
)

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk[-_]?[a-zA-Z0-9]{20,}"),  # API keys
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),  # Bearer tokens
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+"),  # password assignments
    re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),  # JWT
]

MAX_CONTENT_SIZE = 102400  # 100 KB (project/execution state docs)
MAX_QUERY_LENGTH = 2000

# AI-OS-owned logical schemas (Supabase is a passive storage target).
AIOS_OWNED_SCHEMAS = frozenset(
    {
        "project_state",
        "execution_state",
        "evidence_learning",
        "integration_state",
        "dashboard_state",
    }
)


# ---------------------------------------------------------------------------
# Mock Store (safe in-memory fallback)
# ---------------------------------------------------------------------------


class _MockSupabaseStore:
    """In-memory Supabase simulator preserving the adapter's API contract.

    Data lives only for the process lifetime. Mimics table/row semantics with
    provenance preservation. Used when no real Supabase instance is configured.
    """

    def __init__(self) -> None:
        self._tables: dict[str, dict[str, dict[str, Any]]] = {}

    def _ensure_table(self, table: str) -> dict[str, dict[str, Any]]:
        return self._tables.setdefault(table, {})

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        rows = self._ensure_table(table)
        row_id = row.get("id") or str(uuid.uuid4())
        row = dict(row)
        row["id"] = row_id
        row["_mock_created_at"] = datetime.now(timezone.utc).isoformat()
        rows[row_id] = row
        return dict(row)

    def get(self, table: str, row_id: str) -> dict[str, Any] | None:
        row = self._tables.get(table, {}).get(row_id)
        return dict(row) if row else None

    def update(self, table: str, row_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
        rows = self._ensure_table(table)
        if row_id not in rows:
            return None
        rows[row_id].update(patch)
        rows[row_id]["_mock_updated_at"] = datetime.now(timezone.utc).isoformat()
        return dict(rows[row_id])

    def delete(self, table: str, row_id: str) -> bool:
        return self._tables.get(table, {}).pop(row_id, None) is not None

    def query(self, table: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self._tables.get(table, {}).values()
        result = []
        for row in rows:
            if all(row.get(k) == v for k, v in filters.items()):
                result.append(dict(row))
        return result

    def list_tables(self) -> list[str]:
        return list(self._tables.keys())


# ---------------------------------------------------------------------------
# Supabase Adapter
# ---------------------------------------------------------------------------


class SupabaseAdapter(BaseExecutionAdapter):
    """
    Supabase persistent storage adapter implementing BaseExecutionAdapter.

    Maps AI-OS-owned schemas to Supabase tables. Default MOCK store; real mode
    requires credentials + AIOS_REAL_INTEGRATION_ENABLED=1.

    All stored data carries AI-OS provenance; Supabase never interprets semantics.
    """

    perspective = "supabase_persistence"

    # M13 terminal contract: Supabase is a BOUNDED RESOURCE hosted on T2 (External
    # Integration Endpoints). It holds NO AI-OS authority. AI-OS owns semantic
    # meaning; Supabase stores dumb bytes.
    terminal: str = "T2"
    authority_level: str = "bounded_resource"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "supabase",
        timeout_seconds: int = 30,
        real_mode_enabled: bool = False,
        security_manager: Any | None = None,
        url: str | None = None,
        anon_key: str | None = None,
    ) -> None:
        """Initialize Supabase adapter.

        Args:
            mcp_manager: Optional MCPManager (unused for direct REST; kept for
                         interface symmetry with other adapters).
            server_id: Logical server identifier.
            timeout_seconds: Operation timeout.
            real_mode_enabled: When True and credentials present, attempts real
                               Supabase REST access. Otherwise uses mock store.
            security_manager: Optional SecurityManager for gate-before-connect.
            url: Supabase project URL (real mode). Read from env if omitted.
            anon_key: Supabase anon/public key (real mode). Read from env if omitted.
        """
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._security_manager = security_manager
        self._connected = False
        self._version_counter = 0

        # Resolve credentials from env (never from config files).
        self._url = url or os.environ.get("SUPABASE_URL")
        self._anon_key = anon_key or os.environ.get("SUPABASE_ANON_KEY")

        # Real mode requires explicit enable + usable credentials.
        self._real_mode = bool(real_mode_enabled) and bool(self._url) and bool(self._anon_key)
        self._store = _MockSupabaseStore() if not self._real_mode else None

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
        """Connect (mock store always succeeds; real validates reachability)."""
        if self._connected:
            return True
        if self._real_mode:
            # Real mode reachability gate. No network call in mock.
            if not self._url or not self._anon_key:
                raise SupabaseNotConfiguredError(
                    "Real mode requires SUPABASE_URL and SUPABASE_ANON_KEY"
                )
            # Gate-before-connect via SecurityManager.
            if self._security_manager is not None:
                decision = self._security_manager.authorize(
                    principal="aios_kernel",
                    action="supabase_connect",
                    resource=self._url,
                    context={"server_id": self._server_id},
                )
                if decision.value != "allow":
                    logger.warning("Supabase connect denied by SecurityManager")
                    return False
            # In a real deployment an aiohttp/requests health-check would run here.
            # We mark connected; actual REST calls happen in _call_rest.
        self._connected = True
        logger.debug(
            f"SupabaseAdapter connected (mode={'real' if self._real_mode else 'mock'})"
        )
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.debug("SupabaseAdapter disconnected")

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
        action = context.get("action", "insert")
        schema = context.get("schema", "project_state")
        self._validate_schema(schema)
        try:
            if action == "insert":
                return asyncio.run(self.insert(schema, context.get("row", {})))
            elif action == "get":
                return asyncio.run(self.get(schema, target))
            elif action == "update":
                return asyncio.run(
                    self.update(schema, target, context.get("patch", {}))
                )
            elif action == "delete":
                return asyncio.run(self.delete(schema, target))
            elif action == "query":
                return asyncio.run(self.query(schema, context.get("filters", {})))
            else:
                return self._error_result(action, f"Unknown action: {action}")
        except SupabaseError as e:
            return self._error_result(action, str(e))

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def _validate_schema(self, schema: str) -> None:
        if schema not in AIOS_OWNED_SCHEMAS:
            raise SupabaseValidationError(
                f"Schema '{schema}' is not AI-OS-owned; refusing operation"
            )

    def _validate_row(self, row: dict[str, Any]) -> None:
        for key in row:
            if key.lower() in SENSITIVE_PROPERTY_KEYS:
                raise SupabaseSecurityError(f"Sensitive key rejected: '{key}'")
        raw = json.dumps(row)
        if len(raw.encode("utf-8")) > MAX_CONTENT_SIZE:
            raise SupabaseValidationError(
                f"Row exceeds max size ({MAX_CONTENT_SIZE} bytes)"
            )
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(raw):
                raise SupabaseSecurityError("Potential secret detected in row")

    # -----------------------------------------------------------------------
    # Provenance
    # -----------------------------------------------------------------------

    def _make_provenance(
        self,
        operation: str,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "source": "supabase",
            "adapter": "supabase_adapter",
            "operation": operation,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
            "authority": "aios_owned",
            "semantic_owner": "aios_kernel",
            "mode": "real" if self._real_mode else "mock",
        }

    def _next_version(self) -> int:
        self._version_counter += 1
        return self._version_counter

    def _error_result(self, operation: str, description: str) -> ExecutionResult:
        return ExecutionResult(
            tool="supabase_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "supabase_error",
                    "severity": "error",
                    "description": description,
                    "provenance": self._make_provenance(operation),
                }
            ],
            metrics={"operation": operation},
            raw={},
        )

    # -----------------------------------------------------------------------
    # Mock / Real dispatch
    # -----------------------------------------------------------------------

    async def _dispatch(self, method: str, *args: Any) -> Any:
        """Route to mock store or real REST call.

        Real REST path is a documented extension point; the mock store is the
        default safe path used in all unit/integration tests.
        """
        if self._real_mode:
            return await self._call_rest(method, *args)
        store_method = getattr(self._store, method)
        return store_method(*args)

    async def _call_rest(self, method: str, *args: Any) -> Any:
        """Real Supabase REST dispatch (bounded resource).

        Intentionally minimal: real deployments inject an HTTP client. The
        kernel never stores credentials; only env-supplied values are used.
        Raises SupabaseUnavailableError on missing client to degrade safely.
        """
        raise SupabaseUnavailableError(
            "Real Supabase REST client not injected; use mock mode or inject client"
        )

    # -----------------------------------------------------------------------
    # CRUD operations (AI-OS-owned schema semantics)
    # -----------------------------------------------------------------------

    async def insert(self, schema: str, row: dict[str, Any]) -> ExecutionResult:
        self._validate_schema(schema)
        self._validate_row(row)
        provenance = self._make_provenance("insert")
        row = dict(row)
        row["_aios_provenance"] = provenance
        try:
            result = await self._dispatch("insert", schema, row)
        except SupabaseError as e:
            return self._error_result("insert", str(e))
        return ExecutionResult(
            tool="supabase_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"schema": schema, "row_id": result.get("id")},
            raw={"row": result, "provenance": provenance},
        )

    async def get(self, schema: str, row_id: str) -> ExecutionResult:
        self._validate_schema(schema)
        provenance = self._make_provenance("get")
        try:
            result = await self._dispatch("get", schema, row_id)
        except SupabaseError as e:
            return self._error_result("get", str(e))
        if result is None:
            return ExecutionResult(
                tool="supabase_adapter",
                status=ExecutionStatus.SUCCESS,
                findings=[],
                metrics={"schema": schema, "row_id": row_id, "found": False},
                raw={},
            )
        return ExecutionResult(
            tool="supabase_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"schema": schema, "row_id": row_id, "found": True},
            raw={"row": result, "provenance": provenance},
        )

    async def update(self, schema: str, row_id: str, patch: dict[str, Any]) -> ExecutionResult:
        self._validate_schema(schema)
        self._validate_row(patch)
        provenance = self._make_provenance("update")
        try:
            result = await self._dispatch("update", schema, row_id, patch)
        except SupabaseError as e:
            return self._error_result("update", str(e))
        if result is None:
            return ExecutionResult(
                tool="supabase_adapter",
                status=ExecutionStatus.FAILURE,
                findings=[
                    {
                        "type": "not_found",
                        "severity": "warning",
                        "description": f"Row {row_id} not found in {schema}",
                        "provenance": provenance,
                    }
                ],
                metrics={"schema": schema, "row_id": row_id},
                raw={},
            )
        return ExecutionResult(
            tool="supabase_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"schema": schema, "row_id": row_id},
            raw={"row": result, "provenance": provenance},
        )

    async def delete(self, schema: str, row_id: str) -> ExecutionResult:
        self._validate_schema(schema)
        provenance = self._make_provenance("delete")
        try:
            deleted = await self._dispatch("delete", schema, row_id)
        except SupabaseError as e:
            return self._error_result("delete", str(e))
        return ExecutionResult(
            tool="supabase_adapter",
            status=ExecutionStatus.SUCCESS if deleted else ExecutionStatus.FAILURE,
            findings=[],
            metrics={"schema": schema, "row_id": row_id, "deleted": bool(deleted)},
            raw={"provenance": provenance},
        )

    async def query(self, schema: str, filters: dict[str, Any]) -> ExecutionResult:
        self._validate_schema(schema)
        provenance = self._make_provenance("query")
        try:
            results = await self._dispatch("query", schema, filters)
        except SupabaseError as e:
            return self._error_result("query", str(e))
        return ExecutionResult(
            tool="supabase_adapter",
            status=ExecutionStatus.SUCCESS,
            findings=[],
            metrics={"schema": schema, "rows_returned": len(results)},
            raw={"rows": results, "provenance": provenance},
        )


__all__ = [
    "SupabaseAdapter",
    "SupabaseError",
    "SupabaseUnavailableError",
    "SupabaseTimeoutError",
    "SupabaseValidationError",
    "SupabaseSecurityError",
    "SupabaseNotConfiguredError",
    "MalformedSupabaseResponseError",
    "_MockSupabaseStore",
    "AIOS_OWNED_SCHEMAS",
]
