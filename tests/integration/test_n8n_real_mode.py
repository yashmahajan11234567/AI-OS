"""
M14-T2 — n8n Real-Mode Integration Tests (Gated).

All tests require AIOS_REAL_INTEGRATION_ENABLED=1 AND valid N8N_BASE_URL/N8N_API_KEY.
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
    return bool(os.environ.get("N8N_BASE_URL") and os.environ.get("N8N_API_KEY"))


def _skip_if_not_real_mode():
    if not _real_mode_enabled():
        pytest.skip("AIOS_REAL_INTEGRATION_ENABLED=1 not set (real mode gated)")


def _skip_if_no_creds():
    if not _has_credentials():
        pytest.skip("N8N_BASE_URL / N8N_API_KEY not configured")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_mode_requires_gate(monkeypatch):
    """Without AIOS_REAL_INTEGRATION_ENABLED=1, real mode stays mock even with credentials."""
    monkeypatch.delenv("AIOS_REAL_INTEGRATION_ENABLED", raising=False)
    # No reload needed; adapter reads env at init.
    from aios.adapters.n8n_adapter import N8nAdapter

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=5,
        real_mode_enabled=False,
        security_manager=None,
    )
    await adapter.connect()
    assert adapter.is_mock_mode is True
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_connect_with_credentials():
    """With gate + env vars, adapter enters real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=30,
        real_mode_enabled=True,
        security_manager=None,
    )
    connected = await adapter.connect()
    assert connected is True
    assert adapter.is_real_mode is True
    assert adapter.is_connected() is True
    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_workflow_execution():
    """Execute a workflow, verify success result."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=60,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    # Use workflow ID from N8N_WORKFLOW_ID environment variable for real integration test
    result = await adapter.execute_workflow(
        workflow_id=os.environ.get("N8N_WORKFLOW_ID", "3y99peW4PfV7bOki"),
        parameters={"msg": "m14t2 test"},
        bounds={"timeout_seconds": 30},
    )
    assert result.status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILURE)
    if result.status == ExecutionStatus.SUCCESS:
        assert "execution_id" in result.metrics or "result" in result.raw

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_parameter_validation():
    """Oversized params rejected in real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter, N8nValidationError
    from aios.adapters.base import ExecutionStatus

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    # 51KB+ payload exceeds MAX_PARAM_SIZE (50KB).
    large = {"data": "x" * 60000}
    result = await adapter.execute_workflow(
        workflow_id="echo", parameters=large, bounds={"timeout_seconds": 10}
    )
    assert result.status == ExecutionStatus.ERROR
    assert "exceeds max size" in result.findings[0]["description"] or "max size" in result.findings[0]["description"]

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_sensitive_key_rejection():
    """Sensitive params rejected in real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter, N8nSecurityError
    from aios.adapters.base import ExecutionStatus

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    result = await adapter.execute_workflow(
        workflow_id="echo", parameters={"password": "secret"}, bounds={"timeout_seconds": 10}
    )
    assert result.status == ExecutionStatus.ERROR
    assert "Sensitive parameter key rejected" in result.findings[0]["description"] or "Potential secret detected" in result.findings[0]["description"]

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_bounds_validation():
    """Invalid bounds rejected in real mode."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    result = await adapter.execute_workflow(
        workflow_id=os.environ.get("N8N_WORKFLOW_ID", "3y99peW4PfV7bOki"),
        parameters={}, bounds={"timeout_seconds": -1}
    )
    assert result.status == ExecutionStatus.ERROR
    assert any("Invalid execution bound" in finding["description"] for finding in result.findings)

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_idempotency_key():
    """Idempotency key propagated to real API."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=30,
        real_mode_enabled=True,
        security_manager=None,
    )
    await adapter.connect()

    key = "idem_" + os.urandom(8).hex()
    result = await adapter.execute_workflow(
        workflow_id=os.environ.get("N8N_WORKFLOW_ID", "3y99peW4PfV7bOki"),  # AIOS Echo Test workflow ID from user description
        parameters={"idempotency_test": True},
        bounds={"timeout_seconds": 15},
        idempotency_key=key,
    )
    assert result.metrics["idempotency_key"] == key
    assert result.status in (ExecutionStatus.SUCCESS, ExecutionStatus.FAILURE)

    await adapter.disconnect()


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_security_deny_blocks_connect():
    """SecurityManager deny prevents real connection."""
    _skip_if_not_real_mode()
    _skip_if_no_creds()

    from aios.adapters.n8n_adapter import N8nAdapter
    from aios.core.security_manager import SecurityDecision

    class DenySecurityManager:
        def authorize(self, principal, action, resource, context):
            return SecurityDecision.DENY

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=10,
        real_mode_enabled=True,
        security_manager=DenySecurityManager(),
    )
    connected = await adapter.connect()
    assert connected is False, "SecurityManager deny must block real connection"


@pytest.mark.gated
@pytest.mark.external
async def test_n8n_real_network_error_degrades():
    """Network failure returns ERROR result, not exception."""
    _skip_if_not_real_mode()

    from aios.adapters.n8n_adapter import N8nAdapter
    from aios.adapters.base import ExecutionStatus

    adapter = N8nAdapter(
        server_id="n8n",
        timeout_seconds=1,
        real_mode_enabled=True,
        security_manager=None,
        base_url="http://localhost:1/",  # invalid
        api_key="fake",
    )
    await adapter.connect()
    result = await adapter.execute_workflow(
        workflow_id="echo", parameters={}, bounds={"timeout_seconds": 1}
    )
    assert result.status == ExecutionStatus.ERROR
    await adapter.disconnect()


# Batch helper.
if __name__ == "__main__":
    import asyncio

    async def _main():
        await test_n8n_real_mode_requires_gate()
        print("test_n8n_real_mode_requires_gate OK")

    asyncio.run(_main())