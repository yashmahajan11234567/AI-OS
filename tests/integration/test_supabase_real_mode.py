"""
M14-T2 — Supabase Real-Mode Integration Tests (Gated).

All tests require AIOS_REAL_INTEGRATION_ENABLED=1 AND valid SUPABASE_URL/SUPABASE_ANON_KEY.
Without the gate, the adapter must remain in mock mode and real operations must not be attempted.
"""

from __future__ import annotations

import os

import pytest

# ---------------------------------------------------------------------------
# Gate helpers
# ---------------------------------------------------------------------------


def _real_mode_enabled() -> bool:
    return os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1"


def _has_credentials() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_ANON_KEY"))


def _skip_if_not_real_mode():
    if not _real_mode_enabled():
        pytest.skip("AIOS_REAL_INTEGRATION_ENABLED=1 not set (real mode gated)")


def _skip_if_no_creds():
    if not _has_credentials():
        pytest.skip("SUPABASE_URL / SUPABASE_ANON_KEY not configured")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_mode_requires_gate():
    """Without AIOS_REAL_INTEGRATION_ENABLED=1, real mode stays mock even with credentials."""
    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)
    # No reload needed; adapter reads env at init.
    from aios.adapters.supabase_adapter import SupabaseAdapter

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=5,
        real_mode_enabled=False,  # gate off
        security_manager=None,
    )
    await adapter.connect()
    assert adapter.is_mock_mode is True, "Adapter must be in mock mode without gate"
    # In mock mode, _real_mode is False; setting it True only tests structure.
    # The gate logic ensures real paths are never taken.
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_connect_with_credentials():
    """With gate + env vars, adapter enters real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    connected = await adapter.connect()
    assert connected is True, "Real mode connect should succeed with valid credentials"
    assert adapter.is_real_mode is True
    assert adapter.is_connected() is True
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_insert_get_roundtrip():
    """Insert row, retrieve it, verify content matches."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    # Insert via adapter execute() path.
    row_id = "test_roundtrip_" + os.urandom(4).hex()
    result = await adapter.insert("project_state", {
        "id": row_id,
        "test_field": "roundtrip_value",
        "numeric": 42,
    })
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["row_id"] == row_id

    # Get the row back.
    result = await adapter.get("project_state", row_id)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is True
    assert result.raw["row"]["test_field"] == "roundtrip_value"
    assert result.raw["row"]["numeric"] == 42

    # Cleanup.
    await adapter.delete("project_state", row_id)
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_update():
    """Insert then update, verify changed value."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    row_id = "test_update_" + os.urandom(4).hex()
    await adapter.insert("project_state", {
        "id": row_id,
        "field": "original",
    })

    result = await adapter.update("project_state", row_id, {"field": "updated"})
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["row_id"] == row_id

    result = await adapter.get("project_state", row_id)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.raw["row"]["field"] == "updated"

    await adapter.delete("project_state", row_id)
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_delete():
    """Insert then delete, verify not found."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    row_id = "test_delete_" + os.urandom(4).hex()
    await adapter.insert("project_state", {"id": row_id, "x": 1})
    result = await adapter.delete("project_state", row_id)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["deleted"] is True

    result = await adapter.get("project_state", row_id)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["found"] is False

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_query():
    """Insert multiple rows, query with filter, verify count."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=15,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    prefix = "test_query_" + os.urandom(4).hex()
    for i in range(3):
        await adapter.insert("project_state", {"id": f"{prefix}_{i}", "group": "test"})
    await adapter.insert("project_state", {"id": "other_" + os.urandom(4).hex(), "group": "other"})

    result = await adapter.query("project_state", {"group": "test"})
    assert result.status == ExecutionStatus.SUCCESS
    assert result.metrics["rows_returned"] >= 3

    # Cleanup test rows.
    for i in range(3):
        await adapter.delete("project_state", f"{prefix}_{i}")
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_schema_validation():
    """Unknown schema rejected in real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter, SupabaseValidationError
    from aios.adapters.base import ExecutionStatus

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    # Unknown schema should raise SupabaseValidationError _before_ hitting network.
    result = await adapter.insert("not_an_aios_owned_schema", {"x": 1})
    # The adapter should produce an ERROR ExecutionResult, not crash.
    assert result.status == ExecutionStatus.ERROR
    assert "not AI-OS-owned" in result.findings[0]["description"]

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_secret_rejection():
    """Row with sensitive key rejected in real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter, SupabaseSecurityError
    from aios.adapters.base import ExecutionStatus

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    # Sensitive key should be rejected before network call.
    result = await adapter.insert("project_state", {"password": "secret123"})
    assert result.status == ExecutionStatus.ERROR
    assert "Sensitive key rejected" in result.findings[0]["description"] or "Potential secret detected" in result.findings[0]["description"]

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_security_deny_blocks_connect():
    """SecurityManager deny prevents real connection."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters import SupabaseAdapter
    from aios.core.security_manager import SecurityManager, AuthorizationDecision

    class DenySecurityManager:
        async def authorize(self, principal, action, resource, context):
            return AuthorizationDecision(value="deny", reason="test deny")

    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=DenySecurityManager(),
    )
    connected = await adapter.connect()
    assert connected is False, "SecurityManager deny must block real connection"


@pytest.mark.gated
@pytest.mark.external
async def test_supabase_real_network_error_degrades():
    """Network failure returns ERROR result, not exception."""
    _skip_if_not_real_mode()

    from aios.adapters import SupabaseAdapter
    from aios.adapters.base import ExecutionStatus

    # Point to invalid URL to force network error.
    adapter = SupabaseAdapter(
        server_id="supabase",
        timeout_seconds=1,
        real_mode_enabled=True,
        security_manager=None,
        url="http://localhost:1/",  # should not be a Supabase endpoint
        anon_key="fake_key",
    )
    await adapter.connect()
    result = await adapter.insert("project_state", {"id": "net_err", "x": 1})
    assert result.status == ExecutionStatus.ERROR
    # Error should be wrapped, not crash.
    await adapter.disconnect()


# Batch helper: allow running multiple tests in isolation if needed.
if __name__ == "__main__":
    import asyncio

    async def _main():
        await test_supabase_real_mode_requires_gate()
        print("test_supabase_real_mode_requires_gate OK")

    asyncio.run(_main())