"""M8-T6 - Shared integration-test fixtures (spec S18).

Promotes the per-file ``MockMCPManager`` copies and singleton-reset harnesses
duplicated across the T1-T5 test files into one additive conftest. Existing
test files are untouched; they keep their local fixtures.

Fixture inventory (spec S18):
  * reset_singletons             (autouse) - full singleton reset before/after.
  * unified_mock_mcp_manager     - duck-typed manager over any in-process mock
                                   server (replaces the duplicated copies).
  * integration_mcp_manager      - REAL MCPManager over a temp config dir whose
                                   commands launch in-repo mock servers as
                                   production-style stdio subprocesses (S16.1).
  * kernel_with_all_capabilities - real booted kernel + connected MCPManager
                                   injected into its adapters (D-01 workaround).
  * temp_vault                   - temp Obsidian vault with sample notes.
  * seed_* helpers               - notion / obsidian / claude_mem seeding.
  * failure_injector             - context manager flipping a UnifiedMockMCPManager
                                   into error / timeout / malformed modes (F-1..F-16).
  * RealMCPManagerHarness        - class implementing spec S16.1.

All fixtures are function-scoped: the kernel boot pattern of T1-T5 resets every
singleton per test, so session/module scoping would leak state between tests.
"""

from __future__ import annotations

import asyncio
import json
import shutil
import os
import sys
import tempfile
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Singleton reset (canonical, reused from test_kernel_lifecycle_e2e.py S48)
# ---------------------------------------------------------------------------


def _reset_all_singletons() -> None:
    """Reset every canonical singleton for test isolation (spec S18.4)."""
    from aios.core.capability_manager import reset_capability_manager_singleton
    from aios.core.configuration_manager import reset_configuration_manager_singleton
    from aios.core.health_manager import reset_health_manager_singleton
    from aios.core.lifecycle_manager import reset_lifecycle_manager_singleton
    from aios.core.observability_manager import reset_observability_manager_singleton
    from aios.core.resource_manager import reset_resource_manager_singleton
    from aios.core.security_manager import reset_security_manager_singleton
    from aios.core.service_registry import reset_service_registry_singleton
    from aios.core.state import reset_state_manager_singleton
    from aios.core.storage import reset_storage_manager_singleton
    from aios.core.structured_logger import reset_structured_logger_singleton
    from aios.core.workflow import reset_workflow_manager_singleton
    from aios.events.core.bus import reset_event_bus_singleton
    from aios.core.mcp_manager import set_mcp_manager

    reset_observability_manager_singleton()
    reset_capability_manager_singleton()
    reset_security_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()
    reset_workflow_manager_singleton()
    reset_storage_manager_singleton()
    reset_state_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_structured_logger_singleton()
    reset_configuration_manager_singleton()
    reset_service_registry_singleton()
    reset_event_bus_singleton()
    set_mcp_manager(None)


@pytest.fixture(autouse=True)
async def reset_singletons():
    """Reset every canonical singleton before/after each integration test."""
    _reset_all_singletons()
    yield
    _reset_all_singletons()


# ---------------------------------------------------------------------------
# Mock server classes (in-process doubles reused across M8-T6 suites)
# ---------------------------------------------------------------------------


class UnifiedMockMCPManager:
    """Duck-typed MCPManager over an in-process mock server (spec S18.2).

    Replaces the 10+ duplicated ``MockMCPManager`` copies in T1-T5 test files.
    The in-process ``mock_server`` exposes an async ``handle_request`` that
    returns the MCP JSON-RPC dict (``{"result": ...}`` or ``{"error": ...}``).

    Failure injection (spec S8): ``set_fault(...)`` makes the next ``call_tool``
    raise / return an error / hang according to the injected fault mode.
    """

    def __init__(self, mock_server: Any, server_id: str = "mock") -> None:
        self._server = mock_server
        self._server_id = server_id
        self._servers: dict[str, dict[str, Any]] = {}
        self._fault: dict[str, Any] | None = None

    # -- connection surface ------------------------------------------------

    async def connect(self, server_id: str) -> bool:
        self._servers[server_id] = {"connected": True}
        return True

    async def disconnect(self, server_id: str) -> None:
        self._servers.pop(server_id, None)

    def get_server_status(self, server_id: str) -> Any:
        status = self._servers.get(server_id)
        if status is None:
            return None
        return type("Status", (), {"connected": status["connected"]})()

    def list_tools(self, server_id: str) -> list:
        from aios.core.mcp_manager import MCPTool

        return [MCPTool(name=n, description=n, input_schema={}, server_id=server_id)
                for n in getattr(self._server, "TOOL_NAMES", ())]

    # -- failure injection (spec S8 F-1..F-16) -----------------------------

    def set_fault(self, mode: str, *, detail: str = "injected fault") -> None:
        """Install a transient fault. ``mode`` in {error, malformed, timeout, down}."""
        self._fault = {"mode": mode, "detail": detail}

    def clear_fault(self) -> None:
        self._fault = None

    # -- tool dispatch ------------------------------------------------------

    async def call_tool(self, server_id: str, tool_name: str, args: dict[str, Any],
                        call_id: Any = None) -> dict[str, Any]:
        if self._fault is not None:
            mode = self._fault["mode"]
            if mode == "down":
                raise RuntimeError(self._fault["detail"])
            if mode == "error":
                return {"success": False, "error": self._fault["detail"]}
            if mode == "malformed":
                # A structurally broken response (no success flag).
                return {"unexpected": True, "raw": "not-a-valid-result"}
            if mode == "timeout":
                await asyncio.sleep(30)
            # unknown mode falls through to normal dispatch

        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list" if tool_name == "tools/list" else "tools/call",
            "params": {} if tool_name == "tools/list"
            else {"name": tool_name, "arguments": args},
        }
        # In-process mock servers are heterogeneous: MockGraphify/Notion/Obsidian/
        # ClaudeMem expose a *sync* handle_request; MockHermes/Playwright expose an
        # *async* one. Await only when the returned object is awaitable.
        response = self._server.handle_request(request)
        if asyncio.iscoroutine(response):
            response = await response
        if response is None:
            return {"success": True, "result": {}}
        if isinstance(response, dict) and "error" in response:
            raise RuntimeError(response["error"].get("message", "mock error"))
        return response.get("result", {"success": True, "result": {}})


@pytest.fixture
def unified_mock_mcp_manager(request):
    """Build a UnifiedMockMCPManager bound to an in-process mock server.

    Parameterize with ``@pytest.mark.parametrize`` is unnecessary; callers pass
    the mock server directly as ``unified_mock_mcp_manager(mock_server)``.
    """
    def _factory(mock_server: Any, server_id: str = "mock") -> UnifiedMockMCPManager:
        return UnifiedMockMCPManager(mock_server, server_id=server_id)
    return _factory


# ---------------------------------------------------------------------------
# Spec S18.3: kernel_with_all_capabilities + S16.1 production harness
# ---------------------------------------------------------------------------


class RealMCPManagerHarness:
    """Spec S16.1 - real MCPManager over stdio subprocesses.

    Launches the in-repo mock servers (``mock_*_server.py``) as production-style
    stdio subprocesses through the *real* ``MCPManager``. This is distinct from
    both in-process doubles and true real-external services (which remain
    ``@pytest.mark.gated`` and unexecuted by default).
    """

    # server_id -> in-repo module path used to launch the subprocess.
    SERVER_MODULES = {
        "graphify": "aios.adapters.mock_graphify_server",
        "notion": "aios.adapters.mock_notion_server",
        "obsidian": "aios.adapters.mock_obsidian_server",
        "claude_mem": "aios.adapters.mock_claude_mem_server",
        "hermes_agent_ext": "aios.adapters.mock_hermes_server",
    }

    def __init__(self, server_ids: list[str] | None = None) -> None:
        self._server_ids = server_ids or list(self.SERVER_MODULES.keys())
        self._tmp: tempfile.TemporaryDirectory | None = None
        self._tmp_path: Path | None = None
        self.manager: Any = None

    def _python(self) -> str:
        import shutil as _sh

        return _sh.which("python") or _sh.which("python3") or sys.executable

    def _build_config(self, sid: str) -> Any:
        """Build a typed ``MCPServerConfig`` for a mock server subprocess.

        Uses the ``MCPTransport`` enum directly (not a JSON string) so the
        security gate's ``transport.value`` access resolves. Registering via
        ``MCPManager.add_server`` avoids the JSON-loader path. This is the
        M8-T6 D-01/D-11 workaround: it exercises the *real* MCPManager and its
        SecurityManager gate-before-connect without tripping the D-11 crash
        that the string-transport JSON config path would hit.
        """
        from aios.core.mcp_manager import MCPServerConfig, MCPTransport

        # NOTE: env must be a real dict, not {} and not None. An empty dict
        # (MCPServerConfig default) launches the subprocess with NO environment,
        # killing the child on Windows (M8-T6 D-12). None crashes the
        # SecurityManager gate's _validate_env (also D-12).
        #
        # We pass a FILTERED copy of os.environ: the SecurityManager
        # gate-before-connect (C18) rejects any env var whose name matches a
        # credential pattern (PASSWORD/SECRET/TOKEN/KEY/...). The parent process
        # legitimately carries ANTHROPIC_AUTH_TOKEN / CLAUDE_CODE_MESSAGING_TOKEN,
        # so passing the raw environment would trip the gate (a correct, desirable
        # security behavior — see security_integration SEC-3). The mock servers
        # need none of those secrets; PATH/SystemRoot are sufficient. This filter
        # is test-harness code (conftest), NOT production code.
        _UNSAFE = ("PASSWORD", "SECRET", "TOKEN", "KEY", "PRIVATE", "CREDENTIAL",
                   "AWS_SECRET", "GITHUB_TOKEN", "API_KEY", "DATABASE_URL",
                   "POSTGRES_PASSWORD", "MYSQL_PASSWORD", "MONGO_URI")
        safe_env = {
            k: v for k, v in os.environ.items()
            if not any(p in k.upper() for p in _UNSAFE)
        }

        return MCPServerConfig(
            server_id=sid,
            name=sid,
            transport=MCPTransport.STDIO,
            command=[self._python(), "-m", self.SERVER_MODULES[sid]],
            url=None,
            env=safe_env,
            headers={},
            timeout_seconds=30,
            auto_reconnect=True,
            max_retries=1,
            metadata={"description": f"M8-T6 subprocess mock for {sid}"},
        )

    async def __aenter__(self) -> "RealMCPManagerHarness":
        from aios.core.mcp_manager import MCPManager, set_mcp_manager

        self._tmp = tempfile.TemporaryDirectory(prefix="m8t6_mcp_")
        self._tmp_path = Path(self._tmp.name)
        self.manager = MCPManager(config_dir=self._tmp_path)
        set_mcp_manager(self.manager)
        for sid in self._server_ids:
            if sid not in self.SERVER_MODULES:
                continue
            # Register the typed config directly (D-11 workaround) then connect
            # through the real SecurityManager gate-before-connect path.
            self.manager.add_server(self._build_config(sid))
            try:
                await self.manager.connect(sid)
            except Exception as exc:  # noqa: BLE001 - surfaced by tests
                raise RuntimeError(f"M8-T6 harness failed to connect {sid}: {exc}") from exc
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self.manager is not None:
            try:
                await self.manager.disconnect_all()
            except Exception:  # noqa: BLE001
                pass
        from aios.core.mcp_manager import set_mcp_manager
        set_mcp_manager(None)
        if self._tmp is not None:
            self._tmp.cleanup()


@pytest.fixture
async def integration_mcp_manager():
    """Real MCPManager with mock servers launched as stdio subprocesses (S16.1)."""
    async with RealMCPManagerHarness() as harness:
        yield harness.manager


@pytest.fixture
async def m8t6_harness():
    """Yield the harness object itself (for tests that need connect/disconnect)."""
    async with RealMCPManagerHarness() as harness:
        yield harness


@pytest.fixture
async def kernel_with_all_capabilities():
    """Boot a real kernel with all capabilities and a CONNECTED MCPManager.

    Works around D-01 by injecting the connected ``RealMCPManagerHarness`` manager
    into every MCP-bound adapter after boot (spec S16.1, S18.3). This is the only
    way to exercise the intended production call path in CI, since the kernel
    never assigns ``_mcp_manager`` itself (D-01).
    """
    from aios.core import HermesKernel, KernelConfig
    from aios.core.kernel_management import run_kernel, stop_kernel

    _reset_all_singletons()
    tmp_dir = tempfile.mkdtemp(prefix="m8t6_kernel_")
    try:
        config = KernelConfig(data_dir=Path(tmp_dir))
        kernel = await run_kernel(config)
        # The kernel must be up (EventBus/global singletons initialized) BEFORE
        # we connect the MCPManager, since MCPManager.connect lazily publishes
        # events through the canonical EventBus (D-01 boot-order dependency).
        harness = RealMCPManagerHarness()
        await harness.__aenter__()
        # D-01 workaround: inject the connected manager into every MCP-bound adapter.
        for adapter in (
            kernel._graphify_adapter,
            kernel._notion_adapter,
            kernel._obsidian_adapter,
            kernel._claude_mem_adapter,
        ):
            if adapter is not None:
                adapter._mcp_manager = harness.manager
                # The harness has ALREADY connected each server through the real
                # MCPManager (D-01/D-12 workarounds). Re-calling adapter.connect()
                # would trigger a second handshake on an already-connected
                # subprocess and fail. Instead we flip the adapter's own
                # connected flag so its _call_tool path is usable — the kernel
                # boot never sets this (D-01's root cause).
                adapter._connected = True
        # HermesBridge also needs the manager (it uses get_mcp_manager() global).
        if kernel._user_simulation_agent is not None:
            kernel._user_simulation_agent._bridge._mcp_manager = harness.manager
        yield kernel
    finally:
        await stop_kernel()
        if "harness" in dir() and harness is not None:
            await harness.__aexit__(None, None, None)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        _reset_all_singletons()


# ---------------------------------------------------------------------------
# Spec S18.5: temp_vault + S18.6 seed_* helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_vault():
    """Temporary filesystem vault with sample notes (reuse Obsidian test pattern)."""
    with tempfile.TemporaryDirectory(prefix="m8t6_vault_") as tmpdir:
        vault = Path(tmpdir)
        (vault / "arch.md").write_text(
            "---\ntitle: Architecture\ntags: [design, core]\n---\n\nKernel design notes"
        )
        (vault / "testing.md").write_text(
            "---\ntitle: Testing Guide\ntags: [qa]\n---\n\nHow to test the kernel"
        )
        sub = vault / "projects"
        sub.mkdir()
        (sub / "m8.md").write_text(
            "---\ntitle: M8 Plan\ntags: [planning]\n---\n\nExternal integrations milestone"
        )
        yield vault


def seed_notion(server: Any, page_id: str, title: str, content: dict,
                parent_id: str = "root") -> None:
    """Seed a page into an in-process MockNotionServer (server._pages)."""
    server._pages[page_id] = {
        "id": page_id,
        "title": title,
        "parent_id": parent_id,
        "content": content,
        "properties": {},
        "created_time": datetime.now(timezone.utc).isoformat(),
        "last_edited_time": datetime.now(timezone.utc).isoformat(),
    }


def seed_obsidian(server: Any, path: str, title: str, tags: list, content: str) -> None:
    """Seed a note into an in-process MockObsidianServer (server._notes)."""
    server._notes[path] = {
        "path": path,
        "title": title,
        "tags": tags,
        "content": content,
        "created_at": "2026-08-25T00:00:00",
        "updated_at": "2026-08-25T00:00:00",
    }


def seed_claude_mem(server: Any, mem_id: str, content: str, tags: list,
                    hours_ago: float = 0.0) -> None:
    """Seed a memory into an in-process MockClaudeMemServer (server._memories)."""
    created = (datetime.utcnow() - timedelta(hours=hours_ago)).isoformat()
    server._memories.append({
        "id": mem_id,
        "content": content,
        "tags": tags,
        "metadata": {},
        "created_at": created,
    })


def seed_graphify(store_fn: Any, *,
                  node_id: str, label: str, properties: dict | None = None) -> None:
    """Seed a node into an in-process MockGraphifyServer (store fn = adapter.store_node)."""
    import asyncio
    asyncio.get_event_loop() if False else None  # no-op to keep import local
    # store_fn is a coroutine; callers await it. Provided for clarity of intent.
    raise NotImplementedError(
        "seed_graphify is a no-op helper; call adapter.store_node directly in the test"
    )


# ---------------------------------------------------------------------------
# Spec S18.7: failure_injector (F-1..F-16)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def failure_injector(manager: UnifiedMockMCPManager, mode: str,
                           detail: str = "injected fault"):
    """Context manager that installs then clears a fault on a UnifiedMockMCPManager."""
    manager.set_fault(mode, detail=detail)
    try:
        yield manager
    finally:
        manager.clear_fault()


@pytest.fixture
def make_failure_injector():
    """Return the ``failure_injector`` async context manager (spec S18.7)."""
    return failure_injector


# ---------------------------------------------------------------------------
# Spec S18.8: mock_observation_factory (spoof-resistance fixtures, SEC-8)
# ---------------------------------------------------------------------------


def build_attacker_provenance(authority: str = "authoritative",
                              trust_level: str = "builtin") -> dict[str, Any]:
    """Build an externally-supplied provenance dict claiming high authority.

    Used by spoof-resistance tests (SEC-8, A-5, A-6): the adapter must overwrite
    these attacker-controlled fields when ``_mark_advisory`` / ``mark_capability_advisory``
    is applied.
    """
    return {
        "source": "attacker_controlled",
        "advisory": False,
        "authority": authority,
        "trust_level": trust_level,
        "injected_by": "external_system",
    }


@pytest.fixture
def mock_observation_factory():
    """Return helpers that build attacker-controlled provenance for spoof tests."""
    return build_attacker_provenance


# ---------------------------------------------------------------------------
# Spec S18.9: gated_marker - formalize env-gated real-external tests
# ---------------------------------------------------------------------------


def is_gated_enabled(env_var: str) -> bool:
    """Return True if a real-external gating env var is set to an enabled value."""
    val = __import__("os").environ.get(env_var, "")
    return val.strip().lower() in ("1", "true", "yes")


def gated(env_var: str):
    """Decorator: skip a test unless its real-external gating env var is enabled."""
    import os

    return pytest.mark.skipif(
        not is_gated_enabled(env_var),
        reason=f"real-external test gated behind {env_var} (spec S18.9)",
    )


@pytest.fixture
def gated_helper():
    """Expose the gating helpers to tests (spec S18.9)."""
    return {"skip_unless": gated, "is_enabled": is_gated_enabled}
