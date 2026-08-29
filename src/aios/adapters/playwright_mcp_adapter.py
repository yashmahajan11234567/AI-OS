"""
Playwright MCP Adapter for AI-OS M8-T2.

Implements BaseExecutionAdapter with real Playwright MCP browser execution.
Uses MCPManager (stdio) to connect to @playwright/mcp server.
Session isolation via PlaywrightSessionRegistry.
Deferred import of playwright — not at module scope.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from aios.adapters.base import BaseExecutionAdapter, ExecutionResult, ExecutionStatus
from aios.adapters.playwright_session import (
    PlaywrightSessionError,
    PlaywrightSessionNotFoundError,
    PlaywrightSessionRegistry,
)
from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport
# S2 (Terminal 2): route the real @playwright/mcp subprocess through the same
# canonical SecurityManager gate as MCPManager (C18 gate-before-connect). The
# injected-MCPManager path already gates; the production direct path must too.
from aios.core.security_manager import get_security_manager
# S4 (Terminal 2): central secret redaction for subprocess stderr / failures.
from aios.security.secrets import redact_text

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error classification (mirrors M8-T1 acp_adapter.py pattern)
# ---------------------------------------------------------------------------

class PlaywrightError(Exception):
    """Base error for Playwright MCP adapter."""


class PlaywrightInfrastructureError(PlaywrightError):
    """MCP connection, process, or transport failures."""


class PlaywrightSessionErrorEx(PlaywrightError):
    """Session lifecycle failures."""


class PlaywrightActionError(PlaywrightError):
    """Browser action failures (navigation, click, type, etc.)."""


class PlaywrightEvidenceError(PlaywrightError):
    """Evidence capture failures."""


class PlaywrightSecurityError(PlaywrightError):
    """Security violations (secret leakage, unauthorized navigation)."""


# ---------------------------------------------------------------------------
# Security constants
# ---------------------------------------------------------------------------

# Environment variable patterns to scrub (same as M8-T1)
_ENV_SCRUB_PATTERNS = (
    re.compile(r"(.*_)?(api[_-]?key)(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?secret(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?token(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?password(_.*)?$", re.IGNORECASE),
    re.compile(r"(.*_)?credential(_.*)?$", re.IGNORECASE),
)

# Sensitive query parameters to redact from URLs
SENSITIVE_QUERY_PARAMS = {"token", "key", "secret", "password", "auth", "credential", "api_key"}

# DOM content secret patterns to redact
_SECRET_PATTERNS = [
    re.compile(r'(?:sk[-_]?[a-zA-Z0-9]{20,})', re.IGNORECASE),  # API keys
    re.compile(r'(?:Bearer\s+[a-zA-Z0-9._-]+)', re.IGNORECASE),  # Bearer tokens
    re.compile(r'(?:password\s*[:=]\s*\S+)', re.IGNORECASE),       # password assignments
    re.compile(r'(?:api[_-]?key\s*[:=]\s*\S+)', re.IGNORECASE),   # API key assignments
]


# ---------------------------------------------------------------------------
# PlaywrightMCPAdapter
# ---------------------------------------------------------------------------

class PlaywrightMCPAdapter(BaseExecutionAdapter):
    """Playwright MCP adapter implementing BaseExecutionAdapter.

    Uses MCPManager (stdio) to connect to @playwright/mcp server.
    Manages browser sessions via PlaywrightSessionRegistry.
    Returns ExecutionResult observations — never verdicts.
    """

    perspective = "playwright_browser"

    def __init__(
        self,
        tool: Any | None = None,
        server_id: str = "playwright_mcp",
        timeout_seconds: int = 30,
        allowed_domains: tuple[str, ...] | None = None,
        headless: bool = True,
        mcp_manager: MCPManager | None = None,
        session_registry: PlaywrightSessionRegistry | None = None,
    ) -> None:
        """Initialize Playwright MCP adapter.

        Args:
            tool: Injected tool callable for testability (BaseExecutionAdapter pattern).
            server_id: MCP server ID to connect to.
            timeout_seconds: Default timeout for browser actions.
            allowed_domains: If set, restrict navigation to these domains only.
            headless: Run browser in headless mode.
            mcp_manager: Injected MCPManager for testing.
            session_registry: Injected session registry for testing.
        """
        super().__init__(tool)
        self._server_id = server_id
        self._timeout_seconds = timeout_seconds
        self._allowed_domains = allowed_domains
        self._headless = headless
        self._mcp_manager = mcp_manager
        self._session_registry = session_registry or PlaywrightSessionRegistry()
        self._connected = False
        self._discovered_tools: list[str] = []
        self._process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._request_counter = 0
        self._pending_requests: dict[int, asyncio.Future] = {}
        self._background_tasks: set[asyncio.Task] = set()

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Connect to Playwright MCP server via MCPManager or direct stdio.

        If mcp_manager is injected (test path), uses it directly.
        Otherwise launches the @playwright/mcp subprocess.

        Returns:
            True if connected successfully.

        Raises:
            PlaywrightInfrastructureError: If connection fails.
        """
        if self._connected:
            return True

        if self._mcp_manager is not None:
            # Test path: use injected MCPManager
            success = await self._mcp_manager.connect(self._server_id)
            if success:
                self._connected = True
                self._discovered_tools = [
                    t.name for t in self._mcp_manager.list_tools(self._server_id)
                ]
            else:
                raise PlaywrightInfrastructureError(
                    f"Failed to connect to {self._server_id} via MCPManager"
                )
            return self._connected

    async def _connect_direct(self) -> bool:
        """Direct stdio connection to @playwright/mcp (production path)."""
        # Find the mock server first, then real one
        command = self._find_playwright_command()
        if command is None:
            raise PlaywrightInfrastructureError(
                "Playwright MCP server not found. Install with: npm install -g @playwright/mcp"
            )

        # S2 (Terminal 2): Gate-before-connect. The real @playwright/mcp
        # subprocess is an external process and MUST pass the canonical
        # SecurityManager.validate_mcp_server_before_connect gate. No bypass path.
        server_config = MCPServerConfig(
            server_id=self._server_id,
            name="Playwright MCP (subprocess)",
            transport=MCPTransport.STDIO,
            command=list(command),
            url=None,
            env={},
            headers={},
            timeout_seconds=self._timeout_seconds,
            auto_reconnect=False,
            max_retries=0,
            metadata={"mode": "playwright_direct"},
        )
        security_manager = get_security_manager()
        validation_result = security_manager.validate_mcp_server_before_connect(server_config)
        if not validation_result.passed:
            violation_summaries = "; ".join(
                f"{v.severity}:{v.description}" for v in validation_result.violations
                if v.severity in ("high", "critical")
            )
            raise PlaywrightInfrastructureError(
                f"Playwright MCP subprocess blocked by SecurityManager gate "
                f"({self._server_id}): {violation_summaries}"
            )

        env = self._scrub_env()

        try:
            self._process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except FileNotFoundError as e:
            raise PlaywrightInfrastructureError(
                f"Playwright MCP command not found: {command}: {e}"
            )
        except Exception as e:
            raise PlaywrightInfrastructureError(f"Failed to start Playwright MCP: {e}")

        self._reader = self._process.stdout
        self._writer = self._process.stdin

        # Start background tasks
        stderr_task = asyncio.create_task(self._read_stderr())
        self._background_tasks.add(stderr_task)
        stderr_task.add_done_callback(self._background_tasks.discard)

        response_task = asyncio.create_task(self._read_responses())
        self._background_tasks.add(response_task)
        response_task.add_done_callback(self._background_tasks.discard)

        # Wait briefly for process to start
        await asyncio.sleep(0.3)

        if self._process.returncode is not None:
            stderr_output = ""
            if self._process.stderr:
                stderr_data = await self._process.stderr.read()
                stderr_output = stderr_data.decode() if stderr_data else ""
            raise PlaywrightInfrastructureError(
                f"Playwright MCP exited immediately with code "
                f"{self._process.returncode}: {redact_text(stderr_output)}"
            )

        # Send initialize
        try:
            req_id = await self._send_request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "AI-OS PlaywrightAdapter", "version": "0.1.0"},
            })
            response = await asyncio.wait_for(
                self._wait_for_response(req_id), timeout=self._timeout_seconds
            )
            if "error" in response:
                raise PlaywrightInfrastructureError(
                    f"Playwright MCP initialize failed: {response['error']}"
                )
        except asyncio.TimeoutError:
            await self._direct_disconnect()
            raise PlaywrightInfrastructureError(
                f"Playwright MCP initialize timed out after {self._timeout_seconds}s"
            )

        # Send initialized notification
        await self._send_request("notifications/initialized", None)

        # Discover tools
        await self._discover_tools_direct()

        self._connected = True
        logger.info("Playwright MCP connected")
        return True

    async def disconnect(self) -> None:
        """Disconnect from Playwright MCP server."""
        if self._mcp_manager is not None:
            await self._mcp_manager.disconnect(self._server_id)
        else:
            await self._direct_disconnect()
        self._connected = False
        self._discovered_tools = []

    async def _discover_tools_direct(self) -> None:
        """Discover available tools from Playwright MCP server."""
        try:
            req_id = await self._send_request("tools/list", {})
            response = await asyncio.wait_for(
                self._wait_for_response(req_id), timeout=self._timeout_seconds
            )
            if "result" in response:
                for tool in response["result"].get("tools", []):
                    self._discovered_tools.append(tool.get("name", ""))
        except Exception as e:
            logger.warning(f"Failed to discover Playwright MCP tools: {e}")

    async def _direct_disconnect(self) -> None:
        """Disconnect direct stdio connection."""
        for task in self._background_tasks:
            task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        if self._process:
            try:
                self._process.terminate()
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                if self._process:
                    self._process.kill()
                    await self._process.wait()
            except Exception:
                pass
            self._process = None
        self._reader = None
        self._writer = None
        self._pending_requests.clear()

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def create_session(self, execution_id: str | None = None) -> str:
        """Create a new isolated browser session.

        Args:
            execution_id: Optional caller-provided execution identifier.

        Returns:
            Session ID.

        Raises:
            PlaywrightSessionErrorEx: If session creation fails.
        """
        if not self._connected:
            await self.connect()

        session_id = await self._session_registry.create(execution_id)

        # Create browser context via MCP
        try:
            result = await self._call_tool("browser_new_context", {
                "headless": self._headless,
            })
            context_id = result.get("context_id", "")
            self._session_registry._sessions[session_id]["context_id"] = context_id
        except Exception as e:
            await self._session_registry.close(session_id)
            raise PlaywrightSessionErrorEx(f"Failed to create browser context: {e}")

        logger.debug(f"Created Playwright session: {session_id}")
        return session_id

    async def close_session(self, session_id: str) -> None:
        """Close a browser session. Idempotent."""
        await self._session_registry.close(session_id)

    def is_session_active(self, session_id: str) -> bool:
        """Check if a session is active."""
        return self._session_registry.is_active(session_id)

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs."""
        return self._session_registry.get_active()

    # ------------------------------------------------------------------
    # Browser actions
    # ------------------------------------------------------------------

    async def execute_action(
        self, session_id: str, action: str, args: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a browser action on a session.

        Args:
            session_id: Active session ID.
            action: Action name (navigate, click, type_text, etc.).
            args: Action arguments.

        Returns:
            Tool result dict.

        Raises:
            PlaywrightSessionErrorEx: If session is not active.
            PlaywrightActionError: If action fails.
            PlaywrightSecurityError: If security violation detected.
        """
        await self._session_registry.validate_isolation(session_id)

        # Map action to tool name (for security checks)
        tool_map = {
            "navigate": "browser_navigate",
            "click": "browser_click",
            "type": "browser_type_text",
            "press_key": "browser_press_key",
            "snapshot": "browser_snapshot",
            "screenshot": "browser_take_screenshot",
            "new_context": "browser_new_context",
            "close_context": "browser_close_context",
            "close": "browser_close",
        }
        mapped_tool = tool_map.get(action)

        # Security: check allowed domains
        if mapped_tool == "browser_navigate" and self._allowed_domains:
            url = args.get("url", "")
            domain = self._extract_domain(url)
            if domain not in self._allowed_domains:
                raise PlaywrightSecurityError(
                    f"Navigation to domain '{domain}' not allowed. "
                    f"Allowed: {self._allowed_domains}"
                )

        # Security: block file:// protocol
        if url := args.get("url", ""):
            if url.startswith("file://"):
                raise PlaywrightSecurityError("file:// protocol is blocked")

        tool_name = tool_map.get(action)
        if not tool_name:
            raise PlaywrightActionError(f"Unknown action: {action}")

        # Add session_id to args if not present
        if "session_id" not in args:
            args["session_id"] = session_id

        try:
            result = await self._call_tool(tool_name, args)
            # M9-N8 / D-05: results previously carried no provenance at all.
            # Mark every action result as C14-advisory (external browser
            # observation). The marker lives under the ``provenance`` key —
            # the result must NOT gain a top-level ``authority`` field (P-8:
            # Playwright is execution/observation-only, never authoritative).
            result["provenance"] = self._make_action_provenance(
                session_id, action, tool_name
            )
            return result
        except Exception as e:
            raise PlaywrightActionError(f"Action '{action}' failed: {e}")

    def _make_action_provenance(
        self, session_id: str, action: str, tool_name: str
    ) -> dict[str, Any]:
        """C14 advisory provenance for a browser action result.

        Uses ``mark_capability_advisory`` so source/advisory/authority/
        trust_level are force-asserted regardless of tool output content.
        The correlation_id resolves from the ambient C4 CorrelationContext
        when an orchestrator supplied one (M9-N8 / D-04).
        """
        from aios.core.capability_provenance import mark_capability_advisory
        from aios.core.structured_logger import get_correlation_context

        ctx = None
        try:
            ctx = get_correlation_context()
        except Exception:  # noqa: BLE001 — provenance must never fail on lookup
            ctx = None

        marked = mark_capability_advisory(
            {
                "operation": action,
                "session_id": session_id,
                "tool": tool_name,
                **(
                    {"correlation_id": str(ctx.correlation_id)}
                    if ctx is not None and ctx.correlation_id
                    else {}
                ),
            },
            source="playwright_mcp",
            operation=action,
            adapter="PlaywrightMCPAdapter",
            capability_id="m8t2_playwright_browser",
            authority="advisory_only",
        )
        # ``mark_capability_advisory`` nests the C14 constants under a
        # ``provenance`` key; flatten them to the top level so the result
        # exposes ONE flat provenance block.
        nested = marked.pop("provenance", {})
        for key, value in nested.items():
            marked.setdefault(key, value)
        return marked

    # ------------------------------------------------------------------
    # Evidence collection
    # ------------------------------------------------------------------

    async def collect_evidence(
        self, session_id: str, *, include_accessibility: bool = False
    ) -> dict[str, Any]:
        """Collect evidence from a browser session.

        Args:
            session_id: Active session ID.
            include_accessibility: Whether to include accessibility tree.

        Returns:
            Evidence dict with screenshot, DOM snapshot, page metadata.
        """
        await self._session_registry.validate_isolation(session_id)

        evidence: dict[str, Any] = {}

        # Screenshot (required)
        try:
            screenshot_result = await self.execute_action(session_id, "screenshot", {})
            evidence["screenshot"] = screenshot_result.get("screenshot", "")
            evidence["screenshot_format"] = screenshot_result.get("format", "png")
            evidence["screenshot_available"] = bool(evidence["screenshot"])
        except Exception as e:
            logger.warning(f"Screenshot capture failed: {e}")
            evidence["screenshot"] = ""
            evidence["screenshot_available"] = False

        # DOM snapshot (required)
        try:
            snapshot_result = await self.execute_action(session_id, "snapshot", {})
            evidence["snapshot"] = snapshot_result.get("snapshot", {})
            evidence["snapshot_available"] = True
        except Exception as e:
            logger.warning(f"Snapshot capture failed: {e}")
            evidence["snapshot"] = {}
            evidence["snapshot_available"] = False

        # Page metadata (required)
        session_meta = self._session_registry._sessions.get(session_id, {})
        evidence["page_state"] = {
            "url": session_meta.get("url", ""),
            "title": session_meta.get("title", ""),
            "load_state": "loaded",
        }

        # Accessibility (optional)
        if include_accessibility:
            try:
                acc_result = await self.execute_action(session_id, "snapshot", {})
                evidence["accessibility_tree"] = acc_result.get("snapshot", {})
            except Exception as e:
                logger.warning(f"Accessibility capture failed: {e}")
                evidence["accessibility_tree"] = {}

        evidence["evidence_count"] = sum([
            evidence.get("screenshot_available", False),
            evidence.get("snapshot_available", False),
            bool(evidence.get("accessibility_tree")),
        ])

        return evidence

    # ------------------------------------------------------------------
    # MCP communication (direct stdio path)
    # ------------------------------------------------------------------

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call an MCP tool. Works with both injected MCPManager and direct stdio."""
        if self._mcp_manager is not None:
            # Test path: use injected MCPManager
            return await self._mcp_manager.call_tool(
                self._server_id, tool_name, arguments
            )

        # Production path: direct stdio
        if not self._connected:
            raise PlaywrightInfrastructureError("Not connected to Playwright MCP")

        req_id = await self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

        try:
            response = await asyncio.wait_for(
                self._wait_for_response(req_id), timeout=self._timeout_seconds
            )
        except asyncio.TimeoutError:
            raise PlaywrightActionError(f"Tool call '{tool_name}' timed out")

        if "error" in response:
            error_msg = response["error"].get("message", str(response["error"]))
            if "not found" in error_msg.lower():
                raise PlaywrightActionError(f"Tool '{tool_name}' not found")
            raise PlaywrightActionError(f"Tool '{tool_name}' failed: {error_msg}")

        return response.get("result", {})

    async def _send_request(self, method: str, params: dict[str, Any] | None) -> int:
        """Send JSON-RPC request over stdio."""
        if not self._writer:
            raise PlaywrightInfrastructureError("Not connected")

        self._request_counter += 1
        req_id = self._request_counter
        request = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            request["params"] = params

        try:
            self._writer.write((json.dumps(request) + "\n").encode())
            await self._writer.drain()
        except Exception as e:
            raise PlaywrightInfrastructureError(f"Failed to send request: {e}")

        return req_id

    async def _wait_for_response(self, req_id: int, timeout: float | None = None) -> dict[str, Any]:
        """Wait for a response to a request."""
        future = asyncio.Future()
        self._pending_requests[req_id] = future
        try:
            if timeout:
                return await asyncio.wait_for(future, timeout=timeout)
            return await future
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise
        except Exception:
            self._pending_requests.pop(req_id, None)
            raise

    async def _read_responses(self) -> None:
        """Read JSON-RPC responses from stdio."""
        if not self._reader:
            return
        while True:
            try:
                line = await self._reader.readline()
                if not line:
                    break
                line = line.decode().strip()
                if not line:
                    continue
                response = json.loads(line)
                resp_id = response.get("id")
                if resp_id is not None and resp_id in self._pending_requests:
                    future = self._pending_requests.pop(resp_id)
                    if not future.done():
                        future.set_result(response)
            except json.JSONDecodeError:
                continue
            except Exception:
                break

    async def _read_stderr(self) -> None:
        """Read stderr from subprocess."""
        if not self._process or not self._process.stderr:
            return
        try:
            while True:
                line = await self._process.stderr.readline()
                if not line:
                    break
                logger.debug(f"Playwright MCP stderr: {redact_text(line.decode().strip())}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Security helpers
    # ------------------------------------------------------------------

    def _scrub_env(self, env: dict[str, str] | None = None) -> dict[str, str]:
        """Scrub sensitive environment variables."""
        source_env = env or dict(os.environ)
        scrubbed = {}
        for key, value in source_env.items():
            should_scrub = False
            for pattern in _ENV_SCRUB_PATTERNS:
                if pattern.match(key):
                    should_scrub = True
                    break
            scrubbed[key] = "***REDACTED***" if should_scrub else value
        return scrubbed

    def _hash_parameters(self, params: dict[str, Any]) -> str:
        """SHA-256 hash of parameters for provenance (no secrets)."""
        serialized = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def _redact_url(self, url: str) -> str:
        """Redact sensitive query parameters from URL."""
        if "?" not in url:
            return url
        base, query = url.split("?", 1)
        parts = query.split("&")
        clean_parts = []
        for part in parts:
            if "=" in part:
                key = part.split("=")[0].lower()
                if key in SENSITIVE_QUERY_PARAMS:
                    clean_parts.append(f"{key}=***REDACTED***")
                else:
                    clean_parts.append(part)
            else:
                clean_parts.append(part)
        return f"{base}?{'&'.join(clean_parts)}"

    def _redact_dom(self, html: str) -> str:
        """Redact secret patterns from DOM content."""
        for pattern in _SECRET_PATTERNS:
            html = pattern.sub("***REDACTED***", html)
        return html

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return url

    def _find_playwright_command(self) -> list[str] | None:
        """Find the Playwright MCP server command."""
        # Check for mock server first
        if os.environ.get("HERMES_MOCK_PLAYWRIGHT", "").lower() in ("1", "true", "yes"):
            mock_script = os.path.join(
                os.path.dirname(__file__), "mock_playwright_mcp_server.py"
            )
            python = shutil.which("python") or shutil.which("python3")
            if python:
                return [python, mock_script]

        # Try real Playwright MCP
        candidates = [
            ["node", "node_modules/@playwright/mcp/index.js"],
            ["npx", "@playwright/mcp"],
        ]
        for cmd in candidates:
            try:
                if shutil.which(cmd[0]):
                    return cmd
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def cleanup_all(self) -> None:
        """Cleanup all sessions and disconnect."""
        await self._session_registry.cleanup_all()
        await self.disconnect()

    # ------------------------------------------------------------------
    # BaseExecutionAdapter interface
    # ------------------------------------------------------------------

    def _default_tool(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        """Default tool implementation (raises — must be overridden or injected).

        This adapter uses async browser actions, not the synchronous BaseExecutionAdapter
        tool pattern. The execute() method from BaseExecutionAdapter is not used directly;
        instead, callers use create_session() → execute_action() → collect_evidence().
        """
        raise NotImplementedError(
            "PlaywrightMCPAdapter uses async session-based API, not sync tool callable. "
            "Use create_session() + execute_action() + collect_evidence()."
        )


# ---------------------------------------------------------------------------
# Convenience class for simple execution (mirrors BaseExecutionAdapter pattern)
# ---------------------------------------------------------------------------

class PlaywrightBrowserAdapter(PlaywrightMCPAdapter):
    """Convenience adapter that wraps PlaywrightMCPAdapter with BaseExecutionAdapter interface.

    For use when the BaseExecutionAdapter sync interface is required (e.g. by
    agency adapters that expect a synchronous tool callable).
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._last_session_id: str | None = None

    def _default_tool(self, target: str, context: dict[str, Any]) -> ExecutionResult:
        """Run a single browser action and return ExecutionResult.

        Args:
            target: Action name (navigate, click, type, screenshot).
            context: Action arguments plus optional session_id, execution_id.

        Returns:
            ExecutionResult with observation data.
        """
        try:
            # Use sync wrapper — in production, this would be called from async context
            import asyncio
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async def _run() -> ExecutionResult:
            execution_id = context.get("execution_id", str(uuid.uuid4()))
            session_id = context.get("session_id")

            if not session_id:
                session_id = await self.create_session(execution_id)
                self._last_session_id = session_id

            try:
                action = target
                args = {k: v for k, v in context.items() if k not in ("execution_id", "session_id", "target")}
                result = await self.execute_action(session_id, action, args)

                # Collect evidence
                evidence = await self.collect_evidence(session_id)

                return ExecutionResult(
                    tool="playwright_mcp",
                    status=ExecutionStatus.SUCCESS,
                    findings=[
                        {"type": action, "description": f"Browser action '{action}' succeeded"},
                    ],
                    metrics={
                        "session_id": session_id,
                        "action": action,
                        "result": result,
                        "evidence": {
                            "screenshot_available": evidence.get("screenshot_available", False),
                            "snapshot_available": evidence.get("snapshot_available", False),
                        },
                    },
                    raw={"result": result, "evidence": evidence},
                )
            except PlaywrightError as e:
                return ExecutionResult(
                    tool="playwright_mcp",
                    status=ExecutionStatus.ERROR,
                    findings=[{"type": "playwright_error", "description": str(e)}],
                    raw={"error": str(e)},
                )
            finally:
                if session_id and self._last_session_id == session_id:
                    try:
                        await self.close_session(session_id)
                    except Exception:
                        pass

        return loop.run_until_complete(_run())
