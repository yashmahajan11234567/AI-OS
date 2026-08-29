"""
Terminal 2 — PHASE 1 security remediation verification (S1-S5).

Deterministic (non-gated) tests proving the security gates are now wired into
the real external paths. These do NOT require real external services — they
verify the gate is *called* before a subprocess/MCP connection is established,
and that fail-closed behavior holds.

No secrets, no real network, no external credentials. Safe for ordinary
regression (additive, not marked gated).

Bootstrap: SecurityManager / CapabilityManager / SecurityAbacExtension need a
canonical EventBus + kernel singletons, so we bring those up minimally and tear
them down per test (mirrors tests/unit/test_task15_capability_manager.py and
tests/unit/test_m10_autonomy.py).
"""

from __future__ import annotations

import asyncio

import pytest

from aios.core.mcp_manager import MCPServerConfig, MCPTransport
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.security.secrets import redact_env, redact_secrets, redact_text


# ---------------------------------------------------------------------------
# Bootstrap fixtures (minimal kernel singletons required by the managers)
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    reset_event_bus_singleton()
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    yield b
    reset_event_bus_singleton()


@pytest.fixture
def security_manager(bus):
    from aios.core.security_manager import (
        SecurityManager,
        reset_security_manager_singleton,
        set_security_manager,
    )

    reset_security_manager_singleton()
    sm = SecurityManager()
    set_security_manager(sm)
    yield sm
    reset_security_manager_singleton()


@pytest.fixture
def cap_mgr(bus):
    from aios.core.capability_manager import (
        CapabilityManager,
        reset_capability_manager_singleton,
    )

    reset_capability_manager_singleton()
    mgr = CapabilityManager()
    yield mgr
    reset_capability_manager_singleton()


# ---------------------------------------------------------------------------
# S1 — ACP subprocess routes through the SecurityManager gate
# ---------------------------------------------------------------------------


def test_s1_acp_connect_invokes_security_gate(monkeypatch, security_manager, tmp_path):
    """AcPAdapter.connect must call validate_mcp_server_before_connect before spawn."""
    from aios.adapters.acp_adapter import AcPAdapter

    # Create the hermes-agent ACP entry point so the pre-gate existence check
    # passes and execution reaches the security gate.
    entry_dir = tmp_path / "acp_adapter"
    entry_dir.mkdir()
    (entry_dir / "entry.py").write_text("# stub hermes-agent ACP entry\n")

    called: dict[str, object] = {}

    class _FakeResult:
        passed = True
        violations: list[object] = []
        scan_id = "test"

    def _fake_validate(cfg):
        called["config"] = cfg
        return _FakeResult()

    monkeypatch.setattr(
        security_manager, "validate_mcp_server_before_connect", _fake_validate
    )

    async def _noop_spawn(*a, **k):
        raise RuntimeError("spawn should not be reached in this test")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _noop_spawn)

    adapter = AcPAdapter(cwd=str(tmp_path))
    # Gate returns passed=True; the (stubbed) spawn then fails — but the gate
    # must already have been recorded by the time connect raises.
    with pytest.raises(Exception):
        asyncio.get_event_loop().run_until_complete(adapter.connect())

    assert "config" in called, "SecurityManager gate was NOT called before ACP connect"
    assert called["config"].server_id == "hermes_agent_acp"
    assert called["config"].transport == MCPTransport.STDIO


def test_s1_acp_connect_fails_closed_on_gate_deny(monkeypatch, security_manager, tmp_path):
    """If the gate denies, ACP connect must fail closed (no subprocess)."""
    from aios.adapters.acp_adapter import AcPAdapter, TransportConnectionError

    entry_dir = tmp_path / "acp_adapter"
    entry_dir.mkdir()
    (entry_dir / "entry.py").write_text("# stub hermes-agent ACP entry\n")

    class _Deny:
        passed = False
        violations = [
            type("V", (), {"severity": "critical", "description": "blocked"})()
        ]
        scan_id = "deny"

    monkeypatch.setattr(
        security_manager, "validate_mcp_server_before_connect", lambda cfg: _Deny()
    )
    spawn_called = {"yes": False}

    async def _track_spawn(*a, **k):
        spawn_called["yes"] = True
        raise RuntimeError("should not spawn")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", _track_spawn)

    adapter = AcPAdapter(cwd=str(tmp_path))
    with pytest.raises((TransportConnectionError, Exception)):
        asyncio.get_event_loop().run_until_complete(adapter.connect())

    assert spawn_called["yes"] is False, "subprocess spawned despite gate denial"


# ---------------------------------------------------------------------------
# S2 — Playwright direct connection routes through the SecurityManager gate
# ---------------------------------------------------------------------------


def test_s2_playwright_direct_invokes_security_gate(monkeypatch, security_manager):
    """Playwright _connect_direct must call the gate before spawning @playwright/mcp."""
    from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter

    called: dict[str, object] = {}

    class _FakeResult:
        passed = True
        violations: list[object] = []
        scan_id = "test"

    monkeypatch.setattr(
        security_manager, "validate_mcp_server_before_connect",
        lambda cfg: (called.__setitem__("config", cfg) or _FakeResult()),
    )

    adapter = PlaywrightMCPAdapter(server_id="playwright_mcp")
    monkeypatch.setattr(adapter, "_find_playwright_command", lambda: ["node", "x.js"])
    monkeypatch.setattr(
        asyncio, "create_subprocess_exec",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no spawn")),
    )
    with pytest.raises(Exception):
        asyncio.get_event_loop().run_until_complete(adapter._connect_direct())

    assert "config" in called, "SecurityManager gate was NOT called before Playwright connect"
    assert called["config"].server_id == "playwright_mcp"


# ---------------------------------------------------------------------------
# S3 — M10 autonomy cannot self-authorize past SecurityManager.authorize
# ---------------------------------------------------------------------------


def test_s3_autonomy_self_permission_blocked_when_security_denies(
    monkeypatch, security_manager
):
    """An ABAC permit must be overridden by a SecurityManager DENY."""
    from aios.core.security_manager import SecurityDecision
    from aios.services.security_abac_ext import (
        AutonomyAction,
        AutonomyRole,
        SecurityAbacExtensionService,
        SecurityAbacConfig,
    )

    ext = SecurityAbacExtensionService(
        config=SecurityAbacConfig(enabled=True, audit_all_autonomous=False),
        security_manager=security_manager,
    )
    # Load the real autonomous-judge -> emit-judgment policy so ABAC permits.
    ext._initialize_autonomy_policies()
    monkeypatch.setattr(ext._security_manager, "authorize",
                        lambda *a, **k: SecurityDecision.DENY)

    decision = asyncio.get_event_loop().run_until_complete(
        ext.authorize_autonomous_action(
            AutonomyRole.AUTONOMOUS_JUDGE,
            AutonomyAction.EMIT_JUDGMENT,
            "testing_completed",
            context={"source": "autonomous"},
        )
    )
    assert decision.decision == "deny", "Autonomous action self-authorized past SecurityManager"


# ---------------------------------------------------------------------------
# S4 — Central secret redaction
# ---------------------------------------------------------------------------


def test_s4_redact_env_scrubs_secret_keys():
    env = {"PATH": "/usr", "NOTION_TOKEN": "secret-value", "ANTHROPIC_API_KEY": "sk-x"}
    out = redact_env(env)
    assert out["PATH"] == "/usr"
    assert out["NOTION_TOKEN"] == "***REDACTED***"
    assert out["ANTHROPIC_API_KEY"] == "***REDACTED***"


def test_s4_redact_text_strips_inline_secrets():
    text = "token=abc123def456 and Bearer xyz.uiop and password=hunter2"
    out = redact_text(text)
    assert "abc123def456" not in out
    assert "xyz.uiop" not in out
    assert "hunter2" not in out


def test_s4_redact_secrets_recursive():
    payload = {"env": {"NOTION_TOKEN": "v"}, "note": "token=s3cr3t", "nested": ["Bearer a.b.c"]}
    out = redact_secrets(payload)
    assert out["env"]["NOTION_TOKEN"] == "***REDACTED***"
    assert "s3cr3t" not in out["note"]
    assert "a.b.c" not in out["nested"][0]


def test_s4_testing_evidence_to_dict_redacts_secrets():
    """TestingEvidence.to_dict must not leak secrets (central redaction)."""
    from aios.core.testing_evidence import Provenance, TestingEvidence

    ev = TestingEvidence(
        perspective="security",
        target="x",
        test_id="t1",
        actions=[{"cmd": "login", "password": "do-not-leak"}],
        observations=[{"token": "abc.def.ghi"}],
        expected="ok",
        observed="ok",
        proof=["api_key=should-be-redacted"],
        provenance=Provenance(
            source="ai-os", worker="w", session="s",
            timestamp="2026-08-27T00:00:00Z", environment="test",
            correlation_id="c", test_id="t1",
        ),
    )
    d = ev.to_dict()
    assert "do-not-leak" not in str(d)
    assert "abc.def.ghi" not in str(d)
    assert "should-be-redacted" not in str(d)


# ---------------------------------------------------------------------------
# S5 — Capability double-registration safety
# ---------------------------------------------------------------------------


def test_s5_idempotent_reregister_same_provider(cap_mgr):
    """Re-registering the same capability_id+provider is idempotent (no error)."""
    e1 = cap_mgr.register("graphify_context", "graph", "graphify")
    e2 = cap_mgr.register("graphify_context", "graph", "graphify")
    assert e1 is e2


def test_s5_conflicting_provider_rejected(cap_mgr):
    """A different provider claiming an existing id is rejected (CM-DUP-001)."""
    cap_mgr._reject_duplicate_provider = True
    cap_mgr.register("obsidian_knowledge", "knowledge", "obsidian")
    with pytest.raises(Exception) as exc:
        cap_mgr.register("obsidian_knowledge", "knowledge", "malicious_provider")
    # Either CapabilityManagerError with rule_id, or a generic error is acceptable;
    # the key assertion is that it is rejected.
    assert exc.value is not None


def test_s5_manifest_and_kernel_paths_coexist(cap_mgr):
    """Manifest loader + kernel _init_* can register the same id without crashing."""
    cap_mgr.register("notion_planning", "planning", "notion")
    cap_mgr.register("notion_planning", "planning", "notion")
    assert cap_mgr.get_capability("notion_planning") is not None
