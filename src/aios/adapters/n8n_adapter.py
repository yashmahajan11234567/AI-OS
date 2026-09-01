"""
M13 — n8n Bounded Automation / Execution Adapter.

Implements BaseExecutionAdapter for n8n as a *bounded execution resource*.
AI-OS directs n8n to run approved workflows and evaluates results
(M13_N8N_INTEGRATION_SPEC.md).

Design contract:
  * Default safe MOCK mode (in-process workflow simulator). Real mode gated by
    AIOS_REAL_INTEGRATION_ENABLED=1 + user-provided N8N_BASE_URL / N8N_API_KEY.
  * n8n returns only execution results (status/output/errors/artifacts), never
    directives. No autonomous initiation, no state persistence beyond workflow.
  * Gate-before-connect enforced via SecurityManager when provided.
  * Idempotency keys supported for safe retries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import aiohttp

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------


class N8nError(Exception):
    """Base error for n8n adapter."""

    pass


class N8nUnavailableError(N8nError):
    """n8n instance not reachable."""

    pass


class N8nTimeoutError(N8nError):
    """Workflow execution exceeded timeout."""

    pass


class N8nValidationError(N8nError):
    """Invalid input for n8n operation."""

    pass


class N8nSecurityError(N8nError):
    """Security violation (unauthorized workflow / parameter injection)."""

    pass


class N8nNotConfiguredError(N8nError):
    """Real mode requested but credentials unavailable."""

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
        "n8n_api_key",
    ]
)

SECRET_VALUE_PATTERNS = [
    re.compile(r"sk[-_]?[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9._-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+"),
]

MAX_PARAM_SIZE = 51200  # 50 KB per workflow parameter payload

# Mock workflows recognized by the in-memory simulator.
MOCK_WORKFLOWS = frozenset(
    {
        "echo",
        "noop",
        "mock_data_transform",
        "mock_notify",
    }
)


# ---------------------------------------------------------------------------
# Mock Workflow Engine (safe in-process simulator)
# ---------------------------------------------------------------------------


class _MockN8nEngine:
    """In-memory n8n workflow simulator.

    Executes only pre-approved mock workflows. Returns structured results
    matching the real n8n completion-response contract. No network, no state
    persistence between executions.
    """

    async def execute_workflow(
        self, workflow_id: str, parameters: dict[str, Any], bounds: dict[str, Any]
    ) -> dict[str, Any]:
        started = datetime.now(timezone.utc)
        if workflow_id not in MOCK_WORKFLOWS:
            return {
                "execution_id": str(uuid.uuid4()),
                "workflow_id": workflow_id,
                "status": "failure",
                "output": {},
                "errors": [
                    {
                        "type": "unknown_workflow",
                        "description": f"Mock engine has no workflow '{workflow_id}'",
                    }
                ],
                "artifacts": [],
                "metrics": {
                    "execution_time_ms": 1,
                    "retries_attempted": 0,
                    "started_at": started.isoformat(),
                    "completed_at": started.isoformat(),
                },
            }

        # Simulate bounded execution. Echo/transform return deterministic output.
        if workflow_id == "echo":
            output = {"echoed": parameters}
        elif workflow_id == "noop":
            output = {}
        elif workflow_id == "mock_data_transform":
            output = {
                "transformed": bool(parameters),
                "record_count": len(parameters.get("records", [])),
            }
        elif workflow_id == "mock_notify":
            output = {"notified": True, "channel": parameters.get("channel", "log")}
        else:  # unreachable
            output = {}

        completed = datetime.now(timezone.utc)
        return {
            "execution_id": str(uuid.uuid4()),
            "workflow_id": workflow_id,
            "status": "success",
            "output": output,
            "errors": [],
            "artifacts": [],
            "metrics": {
                "execution_time_ms": int(
                    (completed - started).total_seconds() * 1000
                )
                + 1,
                "retries_attempted": 0,
                "started_at": started.isoformat(),
                "completed_at": completed.isoformat(),
            },
        }


# ---------------------------------------------------------------------------
# n8n Adapter
# ---------------------------------------------------------------------------


class N8nAdapter(BaseExecutionAdapter):
    """
    n8n bounded execution adapter implementing BaseExecutionAdapter.

    Maps AI-OS self-prompt bounded-execution directives to n8n workflow runs.
    Default MOCK engine; real mode requires credentials + AIOS_REAL_INTEGRATION_ENABLED=1.

    n8n never interprets AI-OS semantics and returns only execution results.
    """

    perspective = "n8n_execution"

    # M13 terminal contract: n8n is a BOUNDED EXECUTION resource hosted on T2.
    # It executes only workflows explicitly directed by AI-OS and returns only
    # execution results. It holds NO AI-OS authority.
    terminal: str = "T2"
    authority_level: str = "bounded_resource"

    def __init__(
        self,
        mcp_manager: Any | None = None,
        server_id: str = "n8n",
        timeout_seconds: int = 300,
        real_mode_enabled: bool = False,
        security_manager: Any | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        webhook_url: str | None = None,
    ) -> None:
        super().__init__(tool=None)
        self._mcp_manager = mcp_manager
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._security_manager = security_manager
        self._connected = False
        self._version_counter = 0

        # REST endpoint config. base_url/api_key are read from constructor
        # first, then env. Record whether base_url was provided explicitly so
        # we can prefer the user-intent path below.
        self._base_url = base_url or os.environ.get("N8N_BASE_URL")
        self._api_key = api_key or os.environ.get("N8N_API_KEY")
        base_url_explicit = base_url is not None

        # Webhook URL is the production-webhook dispatch path (n8n-activated
        # workflow webhook). Honored only when the caller did NOT pass an
        # explicit base_url — explicit base_url means the caller wants REST
        # dispatch (e.g. tests forcing the REST path with a broken URL).
        if webhook_url is not None:
            self._webhook_url = webhook_url
        elif not base_url_explicit:
            self._webhook_url = os.environ.get("N8N_WEBHOOK_URL")
        else:
            self._webhook_url = None

        # Real mode requires explicit enablement plus SOMETHING to dispatch to:
        # either the legacy REST endpoint (base_url + api_key) or a configured
        # production webhook (webhook_url). Webhook-only is a valid bounded path.
        has_rest = bool(self._base_url) and bool(self._api_key)
        has_webhook = bool(self._webhook_url)
        self._real_mode = bool(real_mode_enabled) and (has_rest or has_webhook)
        self._engine = _MockN8nEngine() if not self._real_mode else None

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
            if not self._base_url or not self._api_key:
                raise N8nNotConfiguredError(
                    "Real mode requires N8N_BASE_URL and N8N_API_KEY"
                )
            if self._security_manager is not None:
                decision = self._security_manager.authorize(
                    principal="aios_kernel",
                    action="n8n_connect",
                    resource=self._base_url,
                    context={"server_id": self._server_id},
                )
                if decision.value != "allow":
                    logger.warning("n8n connect denied by SecurityManager")
                    return False
        self._connected = True
        logger.debug(
            f"N8nAdapter connected (mode={'real' if self._real_mode else 'mock'})"
        )
        return True

    async def disconnect(self) -> None:
        self._connected = False
        logger.debug("N8nAdapter disconnected")

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
        action = context.get("action", "execute_workflow")
        if action == "execute_workflow":
            return asyncio.run(
                self.execute_workflow(
                    workflow_id=target,
                    parameters=context.get("parameters", {}),
                    bounds=context.get("bounds", {}),
                    idempotency_key=context.get("idempotency_key"),
                )
            )
        return self._error_result(action, f"Unknown action: {action}")

    # -----------------------------------------------------------------------
    # Validation
    # -----------------------------------------------------------------------

    def _validate_parameters(self, parameters: dict[str, Any]) -> None:
        raw = json.dumps(parameters)
        if len(raw.encode("utf-8")) > MAX_PARAM_SIZE:
            raise N8nValidationError(
                f"Parameters exceed max size ({MAX_PARAM_SIZE} bytes)"
            )
        for key in parameters:
            if key.lower() in SENSITIVE_KEYS:
                raise N8nSecurityError(f"Sensitive parameter key rejected: '{key}'")
        for pattern in SECRET_VALUE_PATTERNS:
            if pattern.search(raw):
                raise N8nSecurityError("Potential secret detected in parameters")

    def _validate_bounds(self, bounds: dict[str, Any]) -> None:
        timeout = bounds.get("timeout_seconds", self._timeout_seconds)
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise N8nValidationError("Invalid execution bound: timeout_seconds")

    # -----------------------------------------------------------------------
    # Provenance
    # -----------------------------------------------------------------------

    def _make_provenance(
        self,
        operation: str,
        correlation_id: str | None = None,
        workflow_id: str | None = None,
        execution_id: str | None = None,
    ) -> dict[str, Any]:
        provenance = {
            "source": "n8n",
            "adapter": "n8n_adapter",
            "operation": operation,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4()),
            "version": self._next_version(),
            "authority": "aios_directed",
            "mode": "real" if self._real_mode else "mock",
        }
        # Real-mode provenance fields (M14-T2 spec §11.5). Mock provenance
        # shape is unchanged for stable consumer expectation.
        if self._real_mode:
            if workflow_id is not None:
                provenance["workflow_id"] = workflow_id
            if execution_id is not None:
                provenance["execution_id"] = execution_id
        return provenance

    def _next_version(self) -> int:
        self._version_counter += 1
        return self._version_counter

    def _error_result(self, operation: str, description: str) -> ExecutionResult:
        return ExecutionResult(
            tool="n8n_adapter",
            status=ExecutionStatus.ERROR,
            findings=[
                {
                    "type": "n8n_error",
                    "severity": "error",
                    "description": description,
                    "provenance": self._make_provenance(operation),
                }
            ],
            metrics={"operation": operation},
            raw={},
        )

    # -----------------------------------------------------------------------
    # Workflow execution (bounded resource)
    # -----------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow_id: str,
        parameters: dict[str, Any] | None = None,
        bounds: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> ExecutionResult:
        parameters = parameters or {}
        bounds = bounds or {}
        # Provenance before call so we can attach real-mode fields from reply.
        provenance = self._make_provenance(
            "execute_workflow",
            workflow_id=workflow_id,
        )

        # Append AI-OS provenance_echo expectation into bounds context.
        bounds = dict(bounds)
        bounds["bounded_by"] = "aios_kernel"

        try:
            self._validate_parameters(parameters)
            self._validate_bounds(bounds)

            if self._real_mode:
                if self._webhook_url:
                    result = await self._call_webhook(
                        workflow_id, parameters, bounds, idempotency_key
                    )
                else:
                    result = await self._call_rest(
                        workflow_id, parameters, bounds, idempotency_key
                    )
            else:
                result = await self._engine.execute_workflow(workflow_id, parameters, bounds)
        except N8nError as e:
            return self._error_result("execute_workflow", str(e))

        # Enrich provenance with real execution ID if present.
        exec_id = result.get("execution_id")
        if self._real_mode and exec_id:
            provenance["execution_id"] = exec_id

        status = result.get("status", "failure")
        exec_status = (
            ExecutionStatus.SUCCESS if status == "success" else ExecutionStatus.FAILURE
        )
        return ExecutionResult(
            tool="n8n_adapter",
            status=exec_status,
            findings=(
                []
                if status == "success"
                else [
                    {
                        "type": "workflow_failure",
                        "severity": "error" if status == "failure" else "warning",
                        "description": f"n8n workflow '{workflow_id}' -> {status}",
                        "provenance": provenance,
                    }
                ]
            ),
            metrics={
                "workflow_id": workflow_id,
                "status": status,
                "execution_time_ms": result.get("metrics", {}).get("execution_time_ms"),
                "idempotency_key": idempotency_key,
            },
            raw={"result": result, "provenance_echo": provenance},
        )

    async def _call_rest(
        self,
        workflow_id: str,
        parameters: dict[str, Any],
        bounds: dict[str, Any],
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Real n8n REST dispatch (bounded resource).

        Executes workflow via n8n REST API:
          POST {base_url}/api/v1/executions
          Header: X-N8n-API-Key
          Body: n8n webhook execution format.

        Credentials only from constructor/env; API key never logged or in errors.
        """
        if not self._base_url or not self._api_key:
            raise N8nNotConfiguredError(
                "Real mode requires N8N_BASE_URL and N8N_API_KEY"
            )

        base = f"{self._base_url.rstrip('/')}/api/v1/executions"
        timeout_val = bounds.get("timeout_seconds", self._timeout_seconds)
        if not isinstance(timeout_val, (int, float)) or timeout_val <= 0:
            timeout_val = self._timeout_seconds
        timeout = aiohttp.ClientTimeout(total=timeout_val)
        headers = {
            "X-N8n-API-Key": self._api_key,
            "Content-Type": "application/json",
        }
        body = {
            "workflowId": workflow_id,
            "data": {"main": [[{"json": parameters}]]},
        }
        if idempotency_key:
            body["idempotencyKey"] = idempotency_key

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(base, headers=headers, json=body) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except (aiohttp.ContentTypeError, ValueError) as e:
                            raise N8nUnavailableError(
                                "Malformed JSON from n8n execution endpoint"
                            ) from e
                    if response.status == 401:
                        raise N8nSecurityError("n8n API key invalid or missing")
                    if response.status == 403:
                        raise N8nSecurityError("n8n workflow execution forbidden")
                    if response.status == 404:
                        raise N8nNotConfiguredError(f"n8n workflow '{workflow_id}' not found")
                    if response.status == 429:
                        raise N8nTimeoutError("n8n rate limit exceeded (429)")
                    if response.status in (500, 502, 503, 504):
                        raise N8nUnavailableError("n8n endpoint unavailable")
                    raise N8nUnavailableError(
                        f"Unexpected n8n status {response.status}"
                    )
        except asyncio.TimeoutError:
            raise N8nTimeoutError(
                f"n8n execution exceeded {timeout_val}s bound"
            ) from None
        except aiohttp.ClientError as e:
            # Never log base URL or API key.
            raise N8nUnavailableError("n8n endpoint unreachable") from e

    async def _call_webhook(
        self,
        workflow_id: str,
        parameters: dict[str, Any],
        bounds: dict[str, Any],
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        """Real n8n production-webhook dispatch (bounded resource).

        Posts to the configured N8N_WEBHOOK_URL — the production webhook URL
        that n8n publishes for an activated workflow (e.g.
        http://host/webhook/aios-echo). Distinct from the legacy REST execution
        endpoint used by `_call_rest`. Used when N8N_WEBHOOK_URL is configured;
        the REST path is preserved unchanged when it is not.

        Webhooks in n8n are public POST endpoints; API-key auth is not part of
        the webhook contract. The same security/provenance/bounds/idempotency
        contract applies — webhook payload contents are still validated, the
        AI-OS provenance echo is still attached, and the URL is never logged.
        """
        if not self._webhook_url:
            raise N8nNotConfiguredError(
                "Webhook dispatch requires N8N_WEBHOOK_URL"
            )

        webhook = self._webhook_url.rstrip("/")
        timeout_val = bounds.get("timeout_seconds", self._timeout_seconds)
        if not isinstance(timeout_val, (int, float)) or timeout_val <= 0:
            timeout_val = self._timeout_seconds
        timeout = aiohttp.ClientTimeout(total=timeout_val)
        headers = {"Content-Type": "application/json"}
        body: dict[str, Any] = {
            "workflowId": workflow_id,
            "data": parameters,
        }
        if idempotency_key:
            body["idempotencyKey"] = idempotency_key

        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook, headers=headers, json=body) as response:
                    text = await response.text()
                    if response.status == 200:
                        try:
                            payload = json.loads(text) if text else {}
                        except ValueError as e:
                            raise N8nUnavailableError(
                                "Malformed JSON from n8n webhook"
                            ) from e
                        # Normalize webhook reply into the same result shape the
                        # REST path returns, so downstream provenance/status
                        # handling is identical.
                        return {
                            "execution_id": str(uuid.uuid4()),
                            "workflow_id": workflow_id,
                            "status": "success",
                            "output": payload if isinstance(payload, dict) else {"data": payload},
                            "errors": [],
                            "artifacts": [],
                            "metrics": {
                                "execution_time_ms": 0,
                                "retries_attempted": 0,
                                "started_at": datetime.now(timezone.utc).isoformat(),
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                            },
                        }
                    if response.status == 404:
                        raise N8nNotConfiguredError(
                            f"n8n webhook not found for workflow '{workflow_id}'"
                        )
                    if response.status == 429:
                        raise N8nTimeoutError("n8n webhook rate limit exceeded (429)")
                    if response.status in (500, 502, 503, 504):
                        raise N8nUnavailableError("n8n webhook endpoint unavailable")
                    raise N8nUnavailableError(
                        f"Unexpected n8n status {response.status}"
                    )
        except asyncio.TimeoutError:
            raise N8nTimeoutError(
                f"n8n webhook execution exceeded {timeout_val}s bound"
            ) from None
        except aiohttp.ClientError as e:
            # Never log webhook URL or API key.
            raise N8nUnavailableError("n8n webhook unreachable") from e


__all__ = [
    "N8nAdapter",
    "N8nError",
    "N8nUnavailableError",
    "N8nTimeoutError",
    "N8nValidationError",
    "N8nSecurityError",
    "N8nNotConfiguredError",
    "_MockN8nEngine",
    "MOCK_WORKFLOWS",
]
