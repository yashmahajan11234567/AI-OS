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
    AIOS_TEST_SCHEMA,
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
def real_adapter(monkeypatch):
    """Create a SupabaseAdapter with credentials (real-mode-capable)."""
    monkeypatch.setenv("AIOS_REAL_INTEGRATION_ENABLED", "1")
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

    def test_real_mode_disabled_without_credentials(self, monkeypatch):
        # Isolate from environment contamination (SUPABASE_URL/SUPABASE_ANON_KEY may be set)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
        monkeypatch.delenv("AIOS_REAL_INTEGRATION_ENABLED", raising=False)
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

    def test_not_configured_without_url_stays_mock(self, monkeypatch):
        # Safe default: real_mode_enabled without a URL keeps the adapter in mock
        # mode; connect() succeeds and never raises. Real dispatch degrades
        # gracefully only once credentials are present AND _real_mode is True.
        # Isolate from environment contamination (SUPABASE_URL may be set)
        monkeypatch.delenv("SUPABASE_URL", raising=False)
        monkeypatch.setenv("AIOS_REAL_INTEGRATION_ENABLED", "1")
        a = SupabaseAdapter(real_mode_enabled=True, anon_key="k")
        assert a.is_mock_mode is True
        assert a._real_mode is False

    @pytest.mark.asyncio
    async def test_real_insert_404_table_missing_raises_unavailable(self, monkeypatch):
        """Real INSERT against a missing table must surface as a clear ERROR
        result, not silently return None and crash insert() with AttributeError.

        Regression for the production bug where `_rest_request` mapped a 404 on
        POST/PATCH to `None`, causing `insert()` to do `None.get("id")`.
        """
        monkeypatch.setenv("AIOS_REAL_INTEGRATION_ENABLED", "1")
        a = SupabaseAdapter(
            real_mode_enabled=True,
            url="https://example.supabase.co",
            anon_key="public-anon-key",
        )
        await a.connect()

        class _FakeResp:
            status = 404
            content_length = 0

            async def json(self):
                return None

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        class _FakeSession:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def request(self, *args, **kwargs):
                return _FakeResp()

        import aiohttp as _aiohttp

        monkeypatch.setattr(_aiohttp, "ClientSession", _FakeSession)

        result = await a.insert("project_state", {"id": "x", "k": 1})
        assert result.status == ExecutionStatus.ERROR
        assert "not found" in result.findings[0]["description"]
        # Critical: no AttributeError, no crash, metrics dict still valid.
        assert isinstance(result.metrics, dict)


# ---------------------------------------------------------------------------
# M14-T2 Test Adapter Tests
# ---------------------------------------------------------------------------


class TestSupabaseTestAdapter:
    """Tests for the isolated test adapter (M14-T2)."""

    def test_test_adapter_creation_with_credentials(self, monkeypatch):
        """Test adapter can be created with explicit test credentials."""
        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-anon-key")
        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        assert adapter._project_classification == "test"
        assert adapter._schema_allowlist == AIOS_TEST_SCHEMA
        assert adapter._url == "https://test.supabase.co"
        assert adapter._anon_key == "test-anon-key"

    def test_test_adapter_creation_without_credentials_stays_mock(self):
        """Test adapter without credentials stays in mock mode."""
        adapter = SupabaseAdapter(
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        assert adapter.is_mock_mode is True
        assert adapter._real_mode is False

    def test_production_default_uses_aios_owned_schemas(self):
        """Production adapter defaults to AIOS_OWNED_SCHEMAS."""
        adapter = SupabaseAdapter()
        assert adapter._project_classification == "production"
        assert adapter._schema_allowlist == AIOS_OWNED_SCHEMAS

    @pytest.mark.asyncio
    async def test_production_rejects_test_schema(self, adapter):
        """Production adapter rejects aios_real_test schema."""
        await adapter.connect()
        with pytest.raises(SupabaseValidationError) as exc_info:
            await adapter.insert("aios_real_test", {"id": "1"})
        assert "not allowed" in str(exc_info.value)
        assert "project_classification=production" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_test_adapter_accepts_test_schema(self, monkeypatch):
        """Test adapter accepts aios_real_test schema."""
        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-key")
        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        await adapter.connect()
        # Schema validation should pass
        adapter._validate_schema("aios_real_test")  # Should not raise

    @pytest.mark.asyncio
    async def test_test_adapter_rejects_production_schema(self, monkeypatch):
        """Test adapter rejects production schemas."""
        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-key")
        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        await adapter.connect()
        with pytest.raises(SupabaseValidationError) as exc_info:
            await adapter.insert("project_state", {"id": "1"})
        assert "not allowed" in str(exc_info.value)
        assert "project_classification=test" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_master_gate_blocks_real_mode(self, monkeypatch):
        """Without AIOS_REAL_INTEGRATION_ENABLED=1, real mode stays mock."""
        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-key")
        monkeypatch.delenv("AIOS_REAL_INTEGRATION_ENABLED", raising=False)
        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        # real_mode_enabled=True but env gate is off -> stays mock
        assert adapter.is_mock_mode is True
        assert adapter._real_mode is False

    def test_credential_isolation_production(self, monkeypatch):
        """Production adapter uses only SUPABASE_URL/SUPABASE_ANON_KEY."""
        monkeypatch.setenv("SUPABASE_URL", "https://prod.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "prod-key")
        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-key")

        prod_adapter = SupabaseAdapter(project_classification="production")
        assert prod_adapter._url == "https://prod.supabase.co"
        assert prod_adapter._anon_key == "prod-key"

    def test_credential_isolation_test(self, monkeypatch):
        """Test adapter uses only SUPABASE_TEST_URL/SUPABASE_TEST_ANON_KEY."""
        monkeypatch.setenv("SUPABASE_URL", "https://prod.supabase.co")
        monkeypatch.setenv("SUPABASE_ANON_KEY", "prod-key")
        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-key")

        test_adapter = SupabaseAdapter(project_classification="test")
        assert test_adapter._url == "https://test.supabase.co"
        assert test_adapter._anon_key == "test-key"

    @pytest.mark.asyncio
    async def test_provenance_production(self, adapter):
        """Production adapter provenance has project_classification=production."""
        await adapter.connect()
        ins = await adapter.insert("project_state", {"id": "p1"})
        prov = ins.raw["provenance"]
        assert prov["project_classification"] == "production"
        assert prov["resource_type"] == "supabase_project"

    @pytest.mark.asyncio
    async def test_provenance_test(self, monkeypatch):
        """Test adapter provenance has project_classification=test."""
        # Force mock mode for unit test (no real network calls)
        monkeypatch.delenv("AIOS_REAL_INTEGRATION_ENABLED", raising=False)
        monkeypatch.delenv("SUPABASE_TEST_URL", raising=False)
        monkeypatch.delenv("SUPABASE_TEST_ANON_KEY", raising=False)
        adapter = SupabaseAdapter(
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        await adapter.connect()
        ins = await adapter.insert("aios_real_test", {"id": "t1"})
        prov = ins.raw["provenance"]
        assert prov["project_classification"] == "test"
        assert prov["resource_type"] == "supabase_project"

    @pytest.mark.asyncio
    async def test_security_deny_blocks_connect(self, monkeypatch):
        """SecurityManager DENY prevents connection."""
        from unittest.mock import MagicMock

        monkeypatch.setenv("SUPABASE_TEST_URL", "https://test.supabase.co")
        monkeypatch.setenv("SUPABASE_TEST_ANON_KEY", "test-key")
        monkeypatch.setenv("AIOS_REAL_INTEGRATION_ENABLED", "1")

        sec = MagicMock()
        sec.authorize.return_value = MagicMock(value="deny")

        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
            security_manager=sec,
        )
        assert await adapter.connect() is False

    def test_missing_test_credentials_adapter_not_real(self, monkeypatch):
        """Missing test credentials -> adapter stays in mock mode."""
        monkeypatch.delenv("SUPABASE_TEST_URL", raising=False)
        monkeypatch.delenv("SUPABASE_TEST_ANON_KEY", raising=False)

        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            project_classification="test",
            schema_allowlist=AIOS_TEST_SCHEMA,
        )
        assert adapter.is_mock_mode is True
        assert adapter._real_mode is False


# ---------------------------------------------------------------------------
# Real-mode REST response handling (status codes)
# ---------------------------------------------------------------------------


class TestSupabaseRestStatusCodes:
    """Tests for _rest_request status-code handling."""

    @pytest.mark.asyncio
    async def test_delete_204_success(self, monkeypatch):
        """DELETE returning HTTP 204 No Content must be treated as success.

        Regression: Previously only 200/201 were accepted. Supabase with
        Prefer: return=minimal returns 204 on successful DELETE with no body.
        """
        monkeypatch.setenv("AIOS_REAL_INTEGRATION_ENABLED", "1")
        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            url="https://example.supabase.co",
            anon_key="public-anon-key",
        )
        await adapter.connect()

        class _FakeResp:
            status = 204
            content_length = 0

            async def json(self):
                # Should never be called for DELETE
                raise AssertionError("DELETE 204 should not try to parse JSON")

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        class _FakeSession:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def request(self, *args, **kwargs):
                return _FakeResp()

        import aiohttp as _aiohttp

        monkeypatch.setattr(_aiohttp, "ClientSession", _FakeSession)

        result = await adapter.delete("project_state", "row-123")
        assert result.status == ExecutionStatus.SUCCESS
        assert result.metrics["deleted"] is True
        assert result.metrics["row_id"] == "row-123"
        assert "provenance" in result.raw

    @pytest.mark.asyncio
    async def test_delete_200_success(self, monkeypatch):
        """DELETE returning HTTP 200 must also be treated as success."""
        monkeypatch.setenv("AIOS_REAL_INTEGRATION_ENABLED", "1")
        adapter = SupabaseAdapter(
            real_mode_enabled=True,
            url="https://example.supabase.co",
            anon_key="public-anon-key",
        )
        await adapter.connect()

        class _FakeResp:
            status = 200
            content_length = 0

            async def json(self):
                return []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        class _FakeSession:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def request(self, *args, **kwargs):
                return _FakeResp()

        import aiohttp as _aiohttp

        monkeypatch.setattr(_aiohttp, "ClientSession", _FakeSession)

        result = await adapter.delete("project_state", "row-123")
        assert result.status == ExecutionStatus.SUCCESS
        assert result.metrics["deleted"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
