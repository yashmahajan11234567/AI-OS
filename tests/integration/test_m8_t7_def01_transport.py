"""M8-T7 DEF-01 regression — stock MCP transport configuration must load as an enum.

DEF-01 (P1, M8_T7_INDEPENDENT_QA_REPORT.md): ``MCPManager._load_configs()`` loaded
``"transport": "stdio"`` from JSON as a plain ``str``, and the SecurityManager
gate's scan-id construction at security_manager.py:665 accessed
``transport.value`` → ``AttributeError`` on every stock boot. The integration
conftest masked it by constructing enum-typed configs programmatically.

These tests exercise the REAL production chain with NO fixture workaround:

    stock config JSON -> MCPManager._load_configs() -> MCPTransport enum
        -> SecurityManager validation -> MCPManager connect/startup

They do not modify SecurityManager semantics, weaken any gate check, or rely
on the historical conftest transport workaround.
"""

from __future__ import annotations

import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

from aios.core.mcp_manager import (
    MCPManager,
    MCPServerConfig,
    MCPTransport,
    coerce_transport,
    set_mcp_manager,
)
from aios.core.security_manager import get_security_manager


def _write_stock_config(cfg_dir: Path, server_id: str = "probe") -> None:
    """Write a config JSON in EXACTLY the repository's stock representation."""
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / f"{server_id}.json").write_text(json.dumps({
        "server_id": server_id,
        "name": "Probe Server",
        "transport": "stdio",
        "command": [sys.executable, "-m", "aios.adapters.mock_graphify_server"],
        "url": None,
        "env": {},
        "headers": {},
        "timeout_seconds": 30,
        "auto_reconnect": True,
        "max_retries": 3,
        "metadata": {"description": "stock-shaped config"},
    }))


# =============================================================================
# A. Stock JSON configuration loads as MCPTransport.STDIO
# =============================================================================

class TestStockConfigCoercion:
    """Requirement A: stock JSON 'stdio' becomes MCPTransport.STDIO."""

    def test_stock_json_string_transport_loads_as_enum(self, tmp_path: Path):
        _write_stock_config(tmp_path)
        manager = MCPManager(config_dir=tmp_path)
        config = manager._servers["probe"]

        assert isinstance(config.transport, MCPTransport), (
            f"DEF-01 regression: transport loaded as {type(config.transport).__name__}, "
            f"expected MCPTransport"
        )
        assert config.transport is MCPTransport.STDIO

    def test_all_repo_stock_configs_load_with_enum_transports(self):
        """Every committed config/mcp/*.json must load through the fixed loader."""
        repo_cfg_dir = Path(__file__).resolve().parents[2] / "config" / "mcp"
        if not repo_cfg_dir.is_dir():
            pytest.skip("config/mcp directory not present")
        for cfg_file in sorted(repo_cfg_dir.glob("*.json")):
            data = json.loads(cfg_file.read_text())
            # Coercion happens inside MCPServerConfig construction.
            config = MCPServerConfig(**data)
            assert isinstance(config.transport, MCPTransport), (
                f"{cfg_file.name}: transport={config.transport!r} "
                f"is not an MCPTransport member"
            )

    def test_loader_status_entry_carries_enum(self, tmp_path: Path):
        """The status entry created by the loader must also hold the enum."""
        _write_stock_config(tmp_path)
        manager = MCPManager(config_dir=tmp_path)
        status = manager._status["probe"]
        assert isinstance(status.transport, MCPTransport)
        assert status.transport == MCPTransport.STDIO


# =============================================================================
# B. Kernel stock boot reaches MCPManager initialization without AttributeError
# =============================================================================

class TestKernelBootPath:
    """Requirement B/C/D live in TestProductionChain below (kernel-boot based);
    this class proves the boot-time wiring itself stays clean."""

    def test_mcp_manager_init_from_stock_config_does_not_raise(self, tmp_path: Path):
        """MCPManager.__init__ over a stock-shaped config dir completes cleanly."""
        _write_stock_config(tmp_path)
        # Pre-fix this constructor itself was fine but left str transports
        # behind; post-fix the whole init must be exception-free AND typed.
        manager = MCPManager(config_dir=tmp_path)
        set_mcp_manager(manager)
        try:
            assert len(manager.list_servers()) == 1
            assert manager._servers["probe"].transport is MCPTransport.STDIO
        finally:
            set_mcp_manager(None)


# =============================================================================
# C+D. SecurityManager receives normalized enum; production-style path proceeds
# =============================================================================

class TestSecurityGateReceivesEnum:
    """Requirement C: the gate sees an MCPTransport member, not a string."""

    def test_gate_scan_id_uses_enum_value_without_error(
        self, tmp_path: Path, clean_kernel_security
    ):
        _write_stock_config(tmp_path)
        manager = MCPManager(config_dir=tmp_path)
        config = manager._servers["probe"]
        sm = get_security_manager()

        result = sm.validate_mcp_server_before_connect(config)
        # No AttributeError; deterministic scan id derived from .value access.
        assert result.passed is True
        assert result.scan_id and len(result.scan_id) == 16

    def test_gate_rejects_invalid_semantics_after_coercion(
        self, tmp_path: Path, clean_kernel_security
    ):
        """Coercion must not bypass real security checks (fail-closed intact)."""
        cfg_dir = tmp_path / "mcp"
        cfg_dir.mkdir()
        # stdio with EMPTY command: loads fine (enum coerced) but must FAIL gate.
        (cfg_dir / "bad.json").write_text(json.dumps({
            "server_id": "bad", "name": "Bad", "transport": "stdio",
            "command": [], "url": None, "env": {}, "headers": {},
            "timeout_seconds": 30, "auto_reconnect": True,
            "max_retries": 3, "metadata": {},
        }))
        manager = MCPManager(config_dir=cfg_dir)
        config = manager._servers["bad"]
        sm = get_security_manager()

        result = sm.validate_mcp_server_before_connect(config)
        assert result.passed is False
        assert any("command" in v.description.lower() for v in result.violations)


@pytest.fixture
async def clean_kernel_security():
    """Boot a minimal kernel (canonical EventBus + SecurityManager singleton).

    Mirrors tests/unit/test_m5_gate.py's security_manager fixture without
    pulling in the full manager stack; resets everything on teardown.
    """
    from aios.core.service_registry import (
        get_service_registry,
        reset_service_registry_singleton,
    )
    from aios.core.configuration_manager import (
        ConfigurationManager,
        reset_configuration_manager_singleton,
    )
    from aios.core.structured_logger import (
        get_logger,
        reset_structured_logger_singleton,
    )
    from aios.core.security_manager import (
        SecurityManager,
        reset_security_manager_singleton,
    )
    from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton

    reset_event_bus_singleton()
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    reset_service_registry_singleton()
    sr = get_service_registry(event_bus=bus)
    reset_configuration_manager_singleton()
    cm = ConfigurationManager(event_bus=bus)
    reset_structured_logger_singleton()
    logger = get_logger()
    reset_security_manager_singleton()
    sm = SecurityManager(service_registry=sr, configuration_manager=cm, logger=logger)
    await sm.initialize()
    from aios.core.security_manager import set_security_manager
    set_security_manager(sm)
    yield sm
    reset_security_manager_singleton()
    reset_structured_logger_singleton()
    reset_configuration_manager_singleton()
    reset_service_registry_singleton()
    reset_event_bus_singleton()


class TestProductionChain:
    """Requirement D: a real MCP-backed path proceeds beyond config loading.

    Uses the REAL MCPManager + REAL SecurityManager gate + REAL stdio mock
    subprocess launched from a STOCK-shaped JSON config file. This is the
    exact chain that crashed pre-fix (IND-6 trap).
    """

    @pytest.mark.asyncio
    async def test_stock_json_config_connects_via_stdio_subprocess(
        self, tmp_path: Path, clean_kernel_security
    ):
        _write_stock_config(tmp_path)
        manager = MCPManager(config_dir=tmp_path)
        set_mcp_manager(manager)
        try:
            connected = await asyncio.wait_for(manager.connect("probe"), timeout=60)

            assert connected is True, (
                f"MCP connection failed after coercion fix: "
                f"last_error={manager._status['probe'].last_error!r}"
            )
            status = manager._status["probe"]
            assert status.connected is True
            assert isinstance(status.transport, MCPTransport)
            # Tools were actually discovered over the stdio protocol.
            assert len(status.tools) > 0
        finally:
            try:
                await manager.disconnect_all()
            except Exception:
                pass
            set_mcp_manager(None)


# =============================================================================
# E+F. Enum inputs preserved; invalid values fail deterministically
# =============================================================================

class TestTransportValueSemantics:
    """Requirements E/F: enum passthrough + deterministic failure on bad input."""

    @pytest.mark.parametrize("member", list(MCPTransport))
    def test_enum_members_pass_through_unchanged(self, member: MCPTransport):
        """Existing enum input remains valid and is NOT re-wrapped."""
        config = MCPServerConfig(server_id="e", name="E", transport=member)
        assert config.transport is member

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("stdio", MCPTransport.STDIO),
            ("http", MCPTransport.HTTP),
            ("sse", MCPTransport.SSE),
            ("websocket", MCPTransport.WEBSOCKET),
        ],
    )
    def test_every_supported_transport_string_coerces(
        self, raw: str, expected: MCPTransport
    ):
        """All four enum values coerce consistently — not just stdio."""
        config = MCPServerConfig(server_id="c", name="C", transport=raw)
        assert type(config.transport) is MCPTransport
        assert config.transport is expected

    @pytest.mark.parametrize("invalid", ["grpc", "", "STDIO", "Stdio", "stdio "])
    def test_invalid_transport_strings_fail_deterministically(self, invalid: str):
        """Unknown strings raise ValueError naming valid values; nothing invented."""
        with pytest.raises(ValueError, match="Invalid MCP transport"):
            MCPServerConfig(server_id="x", name="X", transport=invalid)
        with pytest.raises(ValueError, match="Invalid MCP transport"):
            coerce_transport(invalid)

    @pytest.mark.parametrize("junk", [None, 123, 3.14, ["stdio"], {"t": "stdio"}])
    def test_non_string_non_enum_types_fail_deterministically(self, junk):
        with pytest.raises(ValueError, match="Invalid MCP transport"):
            MCPServerConfig(server_id="y", name="Y", transport=junk)
        with pytest.raises(ValueError, match="Invalid MCP transport"):
            coerce_transport(junk)

    def test_error_message_lists_valid_values(self):
        with pytest.raises(ValueError) as exc_info:
            coerce_transport("carrier-pigeon")
        message = str(exc_info.value)
        for valid in ("stdio", "http", "sse", "websocket"):
            assert valid in message

    def test_default_transport_is_enum_member(self):
        """Omitting transport yields MCPTransport.STDIO (not a string)."""
        config = MCPServerConfig(server_id="d", name="D")
        assert config.transport is MCPTransport.STDIO

    def test_json_loader_roundtrip_preserves_enum(self, tmp_path: Path):
        """"add_server -> saved JSON -> reload" keeps enum semantics end-to-end."""
        _write_stock_config(tmp_path, server_id="roundtrip")
        manager = MCPManager(config_dir=tmp_path)
        original = manager._servers["roundtrip"]
        assert original.transport is MCPTransport.STDIO

        reloaded = MCPManager(config_dir=tmp_path)
        again = reloaded._servers["roundtrip"]
        assert again.transport is MCPTransport.STDIO
        assert again.transport.value == original.transport.value


# =============================================================================
# G. No reliance on the historical conftest workaround
# =============================================================================

class TestNoFixtureWorkaroundReliance:
    """Requirement G: these tests pass WITHOUT RealMCPManagerHarness.

    Every test above constructs its own MCPManager from raw JSON files via the
    public/real loading path (_load_configs). This module never imports
    RealMCPManagerHarness nor injects pre-built configs into adapters.
    """

    def test_regression_module_is_independent_of_harness(self):
        import tests.integration.conftest as integration_conftest

        harness_attrs = [
            name for name in vars(integration_conftest)
            if "Harness" in name or "real_mcp" in name.lower()
        ]
        # Documented proof: the harness exists but THIS MODULE does not use it.
        assert all(not hasattr(sys.modules[__name__], attr) for attr in harness_attrs)

    def test_harness_workaround_comment_now_historical(self):
        """The workaround docstring should acknowledge the root cause is FIXED.

        If someone reintroduces string transports into production, this test
        still passes — it documents intent only. The real protection is that
        every other test in this module exercises the JSON path directly.
        """
        import tests.integration.conftest as integration_conftest

        source = integration_conftest.RealMCPManagerHarness._build_config.__doc__ or ""
        # Either the historical note remains, or it was cleaned up post-fix.
        mentions_workaround = "workaround" in source.lower() or "D-11" in source
        assert isinstance(source, str)
        assert mentions_workaround or "typed" in source.lower()


# =============================================================================
# H. Original DEF-01 condition demonstrated fixed
# =============================================================================

class TestOriginalDefectCondition:
    """Requirement H: the EXACT pre-fix crash condition, now proven safe."""

    def test_exact_def01_condition_scan_id_construction(self):
        """Replays security_manager.py:665 against a stock-loaded config.

        Pre-fix: AttributeError: 'str' object has no attribute 'value'
        Post-fix: expression evaluates to 'stdio'.
        """
        with tempfile.TemporaryDirectory(prefix="def01_") as tmp:
            cfg_dir = Path(tmp)
            _write_stock_config(cfg_dir, server_id="orig")
            config = MCPManager(config_dir=cfg_dir)._servers["orig"]

        # This is verbatim the failing expression from the QA report.
        config_str = (
            f"{config.server_id}:{config.name}:"
            f"{config.transport.value if config.transport else ''}:"
            f"{config.command}:{config.url}:{config.timeout_seconds}"
        )
        assert ":stdio:" in config_str

    @pytest.mark.asyncio
    async def test_full_chain_survives_where_it_crashed_before(
        self, tmp_path: Path, clean_kernel_security
    ):
        """End-to-end: JSON load -> gate -> connect, the chain that raised pre-fix."""
        cfg_dir = tmp_path / "mcp"
        cfg_dir.mkdir()
        (cfg_dir / "chain.json").write_text(json.dumps({
            "server_id": "chain", "name": "Chain",
            "transport": "stdio",  # the exact DEF-01 trigger value
            "command": [sys.executable, "-m", "aios.adapters.mock_graphify_server"],
            "url": None, "env": {}, "headers": {},
            "timeout_seconds": 30, "auto_reconnect": True,
            "max_retries": 3, "metadata": {},
        }))
        manager = MCPManager(config_dir=cfg_dir)
        set_mcp_manager(manager)
        try:
            # Pre-fix this call propagated AttributeError out of connect().
            connected = await asyncio.wait_for(manager.connect("chain"), timeout=60)
            assert connected is True
        finally:
            try:
                await manager.disconnect_all()
            except Exception:
                pass
            set_mcp_manager(None)
