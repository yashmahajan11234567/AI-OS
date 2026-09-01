"""
M13 — N8nAdapter unit tests.

Tests cover:
- Adapter creation (mock vs real mode)
- Connection lifecycle
- Workflow execution in mock mode (success/failure)
- Parameter validation (size, sensitive keys)
- Bound validation (timeout)
- Idempotency key passthrough
- Provenance / authority marking
- Real-mode gating
- No autonomous initiation (result-only interface)
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock

from aios.adapters.n8n_adapter import (
    N8nAdapter,
    N8nError,
    N8nNotConfiguredError,
    MOCK_WORKFLOWS,
)
from aios.adapters.base import ExecutionStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    return N8nAdapter()


@pytest.fixture
def real_adapter():
    return N8nAdapter(
        real_mode_enabled=True,
        base_url="http://localhost:5678",
        api_key="test-api-key",
    )


# ---------------------------------------------------------------------------
# Creation / mode
# ---------------------------------------------------------------------------


class TestN8nCreation:
    def test_default_mock_mode(self, adapter):
        assert adapter.is_mock_mode is True

    def test_real_mode_with_credentials(self, real_adapter):
        assert real_adapter.is_real_mode is True

    def test_real_mode_disabled_without_credentials(self, monkeypatch):
        # Clear relevant environment variables to ensure clean state.
        # M14-T2 added N8N_WEBHOOK_URL — it also gates real mode, so it must be cleared here.
        monkeypatch.delenv("N8N_BASE_URL", raising=False)
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)
        a = N8nAdapter(real_mode_enabled=True)
        assert a.is_mock_mode is True


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class TestN8nConnection:
    @pytest.mark.asyncio
    async def test_connect_mock(self, adapter):
        assert await adapter.connect() is True
        assert adapter.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        await adapter.connect()
        await adapter.disconnect()
        assert adapter.is_connected() is False


# ---------------------------------------------------------------------------
# Workflow execution (mock mode)
# ---------------------------------------------------------------------------


class TestN8nExecution:
    @pytest.mark.asyncio
    async def test_echo_workflow_success(self, adapter):
        await adapter.connect()
        res = await adapter.execute_workflow("echo", {"x": 1})
        assert res.status == ExecutionStatus.SUCCESS
        assert res.metrics["status"] == "success"
        assert res.raw["result"]["output"]["echoed"] == {"x": 1}

    @pytest.mark.asyncio
    async def test_noop_workflow(self, adapter):
        await adapter.connect()
        res = await adapter.execute_workflow("noop", {})
        assert res.status == ExecutionStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_mock_data_transform(self, adapter):
        await adapter.connect()
        res = await adapter.execute_workflow(
            "mock_data_transform", {"records": [1, 2, 3]}
        )
        assert res.status == ExecutionStatus.SUCCESS
        assert res.raw["result"]["output"]["record_count"] == 3

    @pytest.mark.asyncio
    async def test_unknown_workflow_failure(self, adapter):
        await adapter.connect()
        res = await adapter.execute_workflow("does_not_exist", {})
        assert res.status == ExecutionStatus.FAILURE
        assert res.metrics["status"] == "failure"

    @pytest.mark.asyncio
    async def test_idempotency_key_propagates(self, adapter):
        await adapter.connect()
        res = await adapter.execute_workflow(
            "echo", {}, idempotency_key="idem-123"
        )
        assert res.metrics["idempotency_key"] == "idem-123"

    @pytest.mark.asyncio
    async def test_validates_known_mock_workflows(self):
        assert "echo" in MOCK_WORKFLOWS
        assert "noop" in MOCK_WORKFLOWS


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestN8nValidation:
    @pytest.mark.asyncio
    async def test_reject_oversized_params(self, adapter):
        await adapter.connect()
        big = {"data": "x" * 60000}
        result = await adapter.execute_workflow("echo", big)
        assert result.status == ExecutionStatus.ERROR
        assert any(
            "exceeds max size" in finding["description"]
            or "max size" in finding["description"]
            for finding in result.findings
        )

    @pytest.mark.asyncio
    async def test_reject_sensitive_param(self, adapter):
        await adapter.connect()
        result = await adapter.execute_workflow("echo", {"password": "s3cret"})
        assert result.status == ExecutionStatus.ERROR
        assert any(
            "Sensitive parameter key rejected" in finding["description"]
            or "Potential secret detected" in finding["description"]
            for finding in result.findings
        )

    @pytest.mark.asyncio
    async def test_reject_bad_bounds(self, adapter):
        await adapter.connect()
        result = await adapter.execute_workflow(
            "echo", {}, bounds={"timeout_seconds": -5}
        )
        assert result.status == ExecutionStatus.ERROR
        assert any(
            "Invalid execution bound" in finding["description"]
            for finding in result.findings
        )


# ---------------------------------------------------------------------------
# Provenance / authority
# ---------------------------------------------------------------------------


class TestN8nProvenance:
    @pytest.mark.asyncio
    async def test_provenance_present(self, adapter):
        await adapter.connect()
        res = await adapter.execute_workflow("echo", {"x": 1})
        prov = res.raw["provenance_echo"]
        assert prov["source"] == "n8n"
        assert prov["authority"] == "aios_directed"
        assert prov["mode"] == "mock"


# ---------------------------------------------------------------------------
# Real-mode gating
# ---------------------------------------------------------------------------


class TestN8nRealMode:
    @pytest.mark.asyncio
    async def test_real_connect_security_deny(self, real_adapter):
        sec = MagicMock()
        sec.authorize.return_value = MagicMock(value="deny")
        real_adapter._security_manager = sec
        assert await real_adapter.connect() is False

    @pytest.mark.asyncio
    async def test_real_connect_security_allow(self, real_adapter):
        sec = MagicMock()
        sec.authorize.return_value = MagicMock(value="allow")
        real_adapter._security_manager = sec
        assert await real_adapter.connect() is True

    @pytest.mark.asyncio
    async def test_real_mode_no_client_errors(self, real_adapter):
        await real_adapter.connect()
        res = await real_adapter.execute_workflow("echo", {"x": 1})
        assert res.status == ExecutionStatus.ERROR

    @pytest.mark.asyncio
    async def test_not_configured_without_url_stays_mock(self, monkeypatch):
        # Clear relevant environment variables to ensure clean state.
        # M14-T2 added N8N_WEBHOOK_URL — it also gates real mode, so it must be cleared here.
        monkeypatch.delenv("N8N_BASE_URL", raising=False)
        monkeypatch.delenv("N8N_API_KEY", raising=False)
        monkeypatch.delenv("N8N_WEBHOOK_URL", raising=False)
        # Safe default: real_mode_enabled without a base_url keeps the adapter in
        # mock mode; connect() succeeds and never raises.
        a = N8nAdapter(real_mode_enabled=True, api_key="k")
        assert a.is_mock_mode is True
        assert a._real_mode is False
        assert await a.connect() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
