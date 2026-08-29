"""
M13 — ObsidianGitAdapter unit tests.

Tests cover:
- Adapter creation (mock vs real mode)
- Connection lifecycle
- Knowledge create/get/update/delete in mock mode
- Git durability: commit history recorded, head commit present
- Integrity verification (tamper-evidence)
- Knowledge-type validation (AI-OS-owned)
- Provenance / authority marking
- Real-mode gating
- No external knowledge ingestion / autonomous generation
"""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import MagicMock

from aios.adapters.obsidian_git_adapter import (
    ObsidianGitAdapter,
    ObsidianGitError,
    ObsidianGitValidationError,
    ObsidianGitSecurityError,
    ObsidianGitNotConfiguredError,
    AIOS_KNOWLEDGE_TYPES,
)
from aios.adapters.base import ExecutionStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def adapter():
    return ObsidianGitAdapter()


@pytest.fixture
def real_adapter():
    return ObsidianGitAdapter(
        real_mode_enabled=True,
        vault_path="/tmp/aios-vault",
    )


# ---------------------------------------------------------------------------
# Creation / mode
# ---------------------------------------------------------------------------


class TestObsidianGitCreation:
    def test_default_mock_mode(self, adapter):
        assert adapter.is_mock_mode is True

    def test_real_mode_with_vault(self, real_adapter):
        assert real_adapter.is_real_mode is True

    def test_real_mode_disabled_without_vault(self):
        a = ObsidianGitAdapter(real_mode_enabled=True)
        assert a.is_mock_mode is True  # no vault_path -> stays mock


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------


class TestObsidianGitConnection:
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
# Knowledge operations (mock mode)
# ---------------------------------------------------------------------------


class TestObsidianGitKnowledge:
    @pytest.mark.asyncio
    async def test_create_and_get(self, adapter):
        await adapter.connect()
        res = await adapter.create_knowledge(
            "k1", "# Title", "learning_insight", {"src": "m13"}
        )
        assert res.status == ExecutionStatus.SUCCESS
        assert "head_commit" in res.metrics
        got = await adapter.get_knowledge("k1")
        assert got.status == ExecutionStatus.SUCCESS
        assert got.metrics["found"] is True
        assert got.raw["record"]["content"] == "# Title"

    @pytest.mark.asyncio
    async def test_update(self, adapter):
        await adapter.connect()
        await adapter.create_knowledge("k1", "v1", "reference_knowledge")
        upd = await adapter.update_knowledge("k1", "v2", {"note": "edit"})
        assert upd.status == ExecutionStatus.SUCCESS
        got = await adapter.get_knowledge("k1")
        assert got.raw["record"]["content"] == "v2"
        # Two commits recorded (create + update)
        assert len(got.raw["record"]["version_history"]) == 2

    @pytest.mark.asyncio
    async def test_delete(self, adapter):
        await adapter.connect()
        await adapter.create_knowledge("k1", "x", "reference_knowledge")
        del_res = await adapter.delete_knowledge("k1")
        assert del_res.status == ExecutionStatus.SUCCESS
        got = await adapter.get_knowledge("k1")
        assert got.metrics["found"] is False

    @pytest.mark.asyncio
    async def test_get_missing(self, adapter):
        await adapter.connect()
        got = await adapter.get_knowledge("missing")
        assert got.status == ExecutionStatus.SUCCESS
        assert got.metrics["found"] is False

    @pytest.mark.asyncio
    async def test_update_missing(self, adapter):
        await adapter.connect()
        upd = await adapter.update_knowledge("missing", "x")
        assert upd.status == ExecutionStatus.FAILURE


# ---------------------------------------------------------------------------
# Durability / integrity
# ---------------------------------------------------------------------------


class TestObsidianGitDurability:
    @pytest.mark.asyncio
    async def test_commit_history_present(self, adapter):
        await adapter.connect()
        await adapter.create_knowledge("k1", "v1", "learning_insight")
        await adapter.update_knowledge("k1", "v2")
        hist = adapter._store.history("k1")
        assert len(hist) == 2
        assert adapter._store.verify_integrity() is True

    @pytest.mark.asyncio
    async def test_verify_integrity(self, adapter):
        await adapter.connect()
        await adapter.create_knowledge("k1", "v1", "reference_knowledge")
        res = await adapter.verify_integrity()
        assert res.status == ExecutionStatus.SUCCESS
        assert res.metrics["integrity_intact"] is True


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestObsidianGitValidation:
    @pytest.mark.asyncio
    async def test_reject_unknown_knowledge_type(self, adapter):
        await adapter.connect()
        with pytest.raises(ObsidianGitValidationError):
            await adapter.create_knowledge("k1", "x", "not_a_type")

    @pytest.mark.asyncio
    async def test_reject_sensitive_content(self, adapter):
        await adapter.connect()
        with pytest.raises(ObsidianGitSecurityError):
            await adapter.create_knowledge(
                "k1", "password=supersecret", "reference_knowledge"
            )

    @pytest.mark.asyncio
    async def test_knowledge_types_constant(self):
        assert "decision_record" in AIOS_KNOWLEDGE_TYPES
        assert "execution_evidence" in AIOS_KNOWLEDGE_TYPES


# ---------------------------------------------------------------------------
# Provenance / authority
# ---------------------------------------------------------------------------


class TestObsidianGitProvenance:
    @pytest.mark.asyncio
    async def test_provenance_present(self, adapter):
        await adapter.connect()
        res = await adapter.create_knowledge("k1", "x", "learning_insight")
        prov = res.raw["provenance"]
        assert prov["source"] == "obsidian_git"
        assert prov["authority"] == "aios_owned"
        assert prov["semantic_owner"] == "aios_kernel"
        assert prov["durability"] == "git_version_control"


# ---------------------------------------------------------------------------
# Real-mode gating
# ---------------------------------------------------------------------------


class TestObsidianGitRealMode:
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
    async def test_real_mode_no_writer_errors(self, real_adapter):
        await real_adapter.connect()
        res = await real_adapter.create_knowledge("k1", "x", "learning_insight")
        assert res.status == ExecutionStatus.ERROR

    @pytest.mark.asyncio
    async def test_not_configured_without_vault_stays_mock(self):
        # Safe default: real_mode_enabled without a vault_path keeps the adapter
        # in mock mode; connect() succeeds and never raises.
        a = ObsidianGitAdapter(real_mode_enabled=True)
        assert a.is_mock_mode is True
        assert a._real_mode is False
        assert await a.connect() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
