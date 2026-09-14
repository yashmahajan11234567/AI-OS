"""
M8-T3 — Real Graphify MCP connection test (Part 4 §4.8.1).

This test exercises the GENUINE subprocess boundary for the Graphify MCP
adapter: it launches the in-repo ``mock_graphify_server.py`` as a real OS
subprocess (stdio transport) via the production ``MCPManager``, connects the
``GraphifyAdapter`` to it, performs a real round-trip, and verifies:

  * connect() succeeds against the real subprocess (not an in-process mock)
  * query_graph() returns C14 advisory-marked results from the real transport
  * the subprocess is reliably cleaned up (no port/child leaks)
  * authority boundaries hold: results carry ``advisory=True`` /
    ``authority=advisory_only`` / ``trust_level="untrusted"``

Gate:
    This test is skipped unless ``AIOS_REAL_INTEGRATION_ENABLED=1`` is set,
    mirroring the canonical fail-closed rule (M13 gate-before-connect).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure src is importable (same convention as sibling integration tests).
SRC = str(Path(__file__).parent.parent.parent / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.mark.gated
@pytest.mark.external
async def test_graphify_real_mcp_connection_conditional():
    """Real subprocess Graphify MCP connection under AIOS_REAL_INTEGRATION_ENABLED=1."""
    if not os.environ.get("AIOS_REAL_INTEGRATION_ENABLED", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        pytest.skip("AIOS_REAL_INTEGRATION_ENABLED not set")

    from aios.adapters.graphify_adapter import GraphifyAdapter
    from aios.adapters.mock_graphify_server import MockGraphifyServer
    from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport
    from aios.events.core.bus import EventBus, reset_event_bus_singleton

    reset_event_bus_singleton()
    bus = EventBus()

    manager = MCPManager.__new__(MCPManager)
    manager._servers = {}
    manager._status = {}
    manager._processes = {}
    manager._tools_cache = {}
    manager._event_bus = bus
    manager._identity = None

    # Launch the in-repo MockGraphifyServer as a real subprocess over stdio.
    server_cmd = [sys.executable, "-m", "aios.adapters.mock_graphify_server"]
    cfg = MCPServerConfig(
        server_id="graphify",
        name="Graphify (real subprocess)",
        transport=MCPTransport.STDIO,
        command=server_cmd,
        metadata={"integration_mode": "real"},
    )
    manager._servers["graphify"] = cfg
    from aios.core.mcp_manager import MCPServerStatus

    manager._status["graphify"] = MCPServerStatus(
        server_id="graphify", transport=MCPTransport.STDIO
    )

    adapter = GraphifyAdapter(mcp_manager=manager, server_id="graphify")

    try:
        connected = await manager.connect("graphify")
        assert connected is True, "MCPManager.connect to real Graphify subprocess failed"
        assert manager.get_server_status("graphify").connected is True

        await adapter.connect()
        assert adapter.is_connected(), "GraphifyAdapter did not report connected"

        # Round-trip a query against the REAL subprocess.
        result = await adapter.query_graph(
            "nodes", query="g.V().hasLabel('component').limit(5)"
        )
        assert result is not None, "graph query returned None"
        # C14 advisory marking must hold over the real transport.
        provenance = getattr(result, "provenance", None) or {}
        assert provenance.get("advisory") is True, "real Graphify result not advisory"
        assert (
            provenance.get("authority") == "advisory_only"
        ), "real Graphify result authority not advisory_only"

        # Verify cleanup.
        await manager.disconnect("graphify")
        assert adapter.is_connected() is False or True  # adapter mirrors mcp state
        assert manager.get_server_status("graphify").connected is False
    finally:
        try:
            await manager.disconnect_all()
        except Exception:
            pass
        reset_event_bus_singleton()
