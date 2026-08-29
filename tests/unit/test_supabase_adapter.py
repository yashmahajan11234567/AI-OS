"""
M13 — SupabaseAdapter unit tests.

Tests cover:
- Adapter creation (mock vs real mode)
- Connection lifecycle
- CRUD operations (insert/get/update/delete/query) in mock mode
- Schema validation (AI-OS-owned enforcement)
- Provenance tracking
- Security (sensitive key / secret rejection)
- Default safe mock mode (no credentials)
- Real-mode gating
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from aios.adapters.supabase_adapter import (
    SupabaseAdapter,
    SupabaseError,
    SupabaseValidationError,
    SupabaseSecurityError,
    SupabaseNotConfiguredError,
    AIOS_OWNED_SCHEMAS,
)
from aios.adapters.base import ExecutionStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    """Create a SupabaseAdapter in default safe mock mode."""
    return SupabaseAdapter()


@pytest.fixture
def real_adapter():
    """Create a SupabaseAdapter with credentials (real-mode-capable)."""
    return SupabaseAdapter(
        real_mode_enabled=True,
        url="https://example.supabase.co",
        anon_key="public-anon-key",
    )


# ---------------------------------------------------------------------------
# Creation / mode
# ---------------------------------------------------------------------------


class TestSupabaseCreation:
    def test_default_mock_mode(self, adapter):
        assert adapter.is_mock_mode is True
        assert adapter.is_real_mode is False

    def test_real_mode_with_credentials(self, real_adapter):
        assert real_adapter.is_real_mode is True
        assert real_adapter.is_mock_mode is False

    def test_real_mode_disabled_without_credentials(self):
        a = SupabaseAdapter(real_mode_enabled=True)
        assert a.is_real_mode is False  # no url/key -> stays mock

    def test_default_mock_without_env(self, monkeypatch):
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        a = SupabaseAdapter(real_mode_enabled=True)
        assert a.is_mock_mode is True


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class TestSupabaseConnection:
    @pytest.mark.asyncio
    async def test_connect_mock(self, adapter):
        assert await adapter.connect() is True
        assert adapter.is_connected() is True

    @pytest.mark.asyncio
    async def test_disconnect(self, adapter):
        await adapter.connect()
        await adapter.disconnect()
        assert adapter.is_connected() is False

    @pytest.mark.asyncio
    async def test_double_connect_idempotent(self, adapter):
        assert await adapter.connect() is True
        assert await adapter.connect() is True


# ---------------------------------------------------------------------------
# CRUD (mock mode)
# ---------------------------------------------------------------------------


class TestSupabaseCRUD:
    @pytest.mark.asyncio
    async def test_insert_and_get(self, adapter):
        await adapter.connect()
        ins = await adapter.insert("project_state", {"id": "p1", "name": "demo"})
        assert ins.status == ExecutionStatus.SUCCESS
        assert ins.metrics["row_id"] == "p1"
        got = await adapter.get("project_state", "p1")
        assert got.status == ExecutionStatus.SUCCESS
        assert got.metrics["found"] is True
        assert got.raw["row"]["name"] == "demo"

    @pytest.mark.asyncio
    async def test_get_missing(self, adapter):
        await adapter.connect()
        got = await adapter.get("project_state", "nope")
        assert got.status == ExecutionStatus.SUCCESS
        assert got.metrics["found"] is False

    @pytest.mark.asyncio
    async def test_update(self, adapter):
        await adapter.connect()
        await adapter.insert("project_state", {"id": "p1", "name": "old"})
        upd = await adapter.update("project_state", "p1", {"name": "new"})
        assert upd.status == ExecutionStatus.SUCCESS
        got = await adapter.get("project_state", "p1")
        assert got.raw["row"]["name"] == "new"

    @pytest.mark.asyncio
    async def test_update_missing(self, adapter):
        await adapter.connect()
        upd = await adapter.update("project_state", "missing", {"x": 1})
        assert upd.status == ExecutionStatus.FAILURE

    @pytest.mark.asyncio
    async def test_delete(self, adapter):
        await adapter.connect()
        await adapter.insert("project_state", {"id": "p1"})
        deleted = await adapter.delete("project_state", "p1")
        assert deleted.status == ExecutionStatus.SUCCESS
        assert deleted.metrics["deleted"] is True
        got = await adapter.get("project_state", "p1")
        assert got.metrics["found"] is False

    @pytest.mark.asyncio
    async def test_query(self, adapter):
        await adapter.connect()
        await adapter.insert("project_state", {"id": "a", "tag": "x"})
        await adapter.insert("project_state", {"id": "b", "tag": "y"})
        await adapter.insert("project_state", {"id": "c", "tag": "x"})
        q = await adapter.query("project_state", {"tag": "x"})
        assert q.status == ExecutionStatus.SUCCESS
        assert q.metrics["rows_returned"] == 2


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestSupabaseValidation:
    @pytest.mark.asyncio
    async def test_reject_unknown_schema(self, adapter):
        await adapter.connect()
        with pytest.raises(SupabaseValidationError):
            await adapter.insert("not_a_schema", {"id": "1"})

    @pytest.mark.asyncio
    async def test_reject_sensitive_key(self, adapter):
        await adapter.connect()
        with pytest.raises(SupabaseSecurityError):
            await adapter.insert("project_state", {"id": "1", "password": "x"})

    @pytest.mark.asyncio
    async def test_reject_secret_pattern(self, adapter):
        await adapter.connect()
        with pytest.raises(SupabaseSecurityError):
            await adapter.insert("project_state", {"id": "1", "token": "sk-abcdefghijklmnopqrstuvwx"})

    @pytest.mark.asyncio
    async def test_validate_schema_constant(self):
        assert "project_state" in AIOS_OWNED_SCHEMAS
        assert "dashboard_state" in AIOS_OWNED_SCHEMAS


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


class TestSupabaseProvenance:
    @pytest.mark.asyncio
    async def test_provenance_present(self, adapter):
        await adapter.connect()
        ins = await adapter.insert("project_state", {"id": "p1"})
        prov = ins.raw["provenance"]
        assert prov["source"] == "supabase"
        assert prov["semantic_owner"] == "aios_kernel"
        assert prov["authority"] == "aios_owned"
        assert prov["mode"] == "mock"


# ---------------------------------------------------------------------------
# Real-mode gating
# ---------------------------------------------------------------------------


class TestSupabaseRealMode:
    @pytest.mark.asyncio
    async def test_real_connect_requires_security_allow(self, real_adapter):
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
    async def test_real_mode_no_client_raises(self, real_adapter):
        await real_adapter.connect()
        # No injected REST client -> safe degradation error, not network call
        res = await real_adapter.insert("project_state", {"id": "p1"})
        assert res.status == ExecutionStatus.ERROR

    def test_not_configured_without_url_stays_mock(self):
        # Safe default: real_mode_enabled without a URL keeps the adapter in mock
        # mode; connect() succeeds and never raises. Real dispatch degrades
        # gracefully only once credentials are present AND _real_mode is True.
        a = SupabaseAdapter(real_mode_enabled=True, anon_key="k")
        assert a.is_mock_mode is True
        assert a._real_mode is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
