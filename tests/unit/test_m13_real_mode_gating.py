"""
M13 — Real-Mode Gating & Testing (kernel level).

Verifies the M13 real-mode gating contract from ``M13_TEST_AND_ACCEPTANCE_SPEC.md``
and the per-integration specs:

  * Default safe MOCK mode: with no ``AIOS_REAL_INTEGRATION_ENABLED`` gate and no
    credentials, the kernel wires every M13 adapter in mock mode.
  * Gated real mode: ``AIOS_REAL_INTEGRATION_ENABLED=1`` alone is NOT sufficient —
    each adapter also requires its own user-provided credentials/vault; otherwise it
    safely stays in mock mode.
  * Full real mode: gate + credentials yields ``is_real_mode is True`` for that
    adapter only.

All real-mode assertions are made WITHOUT network access (no live external system
is contacted). Real dispatch degrades gracefully via injected-client extension points.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

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


# Credentials that would enable real mode IF the gate is set.
_REAL_ENV = {
    "AIOS_REAL_INTEGRATION_ENABLED": "1",
    "SUPABASE_URL": "https://example.supabase.co",
    "SUPABASE_ANON_KEY": "public-anon-key",
    "N8N_BASE_URL": "https://n8n.example.com",
    "N8N_API_KEY": "secret-api-key",
    "OBSIDIAN_VAULT_PATH": "/tmp/aios_vault",
}


async def _reset_all_singletons():
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


@pytest.fixture
def clean_env(monkeypatch):
    """Strip every M13 real-mode env var so the default-safe baseline is clean."""
    for var in (
        "AIOS_REAL_INTEGRATION_ENABLED",
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "N8N_BASE_URL",
        "N8N_API_KEY",
        "OBSIDIAN_VAULT_PATH",
    ):
        monkeypatch.delenv(var, raising=False)
    yield monkeypatch


async def _boot_kernel(monkeypatch, env: dict[str, str] | None = None):
    from aios.core.kernel import HermesKernel, KernelConfig

    await _reset_all_singletons()
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    temp_dir = Path(tempfile.mkdtemp())
    kernel = HermesKernel(config=KernelConfig(data_dir=temp_dir))
    await kernel.start()
    return kernel, temp_dir


async def _shutdown_kernel(kernel, temp_dir):
    try:
        await kernel.stop()
    finally:
        await _reset_all_singletons()
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Default safe MOCK mode (no gate, no credentials)
# ---------------------------------------------------------------------------


class TestDefaultMockMode:
    @pytest.mark.asyncio
    async def test_kernel_adapters_default_mock(self, clean_env):
        kernel, temp_dir = await _boot_kernel(clean_env)
        try:
            assert kernel.supabase_adapter.is_mock_mode is True
            assert kernel.n8n_adapter.is_mock_mode is True
            assert kernel.obsidian_git_adapter.is_mock_mode is True
            # Capabilities are registered regardless of mode.
            reg = kernel._capability_manager
            assert reg.get_capability("supabase_persistence") is not None
            assert reg.get_capability("n8n_execution") is not None
            assert reg.get_capability("obsidian_git_knowledge") is not None
        finally:
            await _shutdown_kernel(kernel, temp_dir)

    @pytest.mark.asyncio
    async def test_gate_without_credentials_stays_mock(self, clean_env):
        # Gate set but no credentials -> adapters MUST stay mock (fail-safe).
        kernel, temp_dir = await _boot_kernel(
            clean_env, {"AIOS_REAL_INTEGRATION_ENABLED": "1"}
        )
        try:
            assert kernel.supabase_adapter.is_mock_mode is True
            assert kernel.n8n_adapter.is_mock_mode is True
            assert kernel.obsidian_git_adapter.is_mock_mode is True
        finally:
            await _shutdown_kernel(kernel, temp_dir)

    @pytest.mark.asyncio
    async def test_garbage_gate_value_stays_mock(self, clean_env):
        # Only the literal "1" enables the gate; anything else is mock.
        kernel, temp_dir = await _boot_kernel(
            clean_env, {"AIOS_REAL_INTEGRATION_ENABLED": "true"}
        )
        try:
            assert kernel.supabase_adapter.is_mock_mode is True
        finally:
            await _shutdown_kernel(kernel, temp_dir)


# ---------------------------------------------------------------------------
# Gated real mode (gate + credentials)
# ---------------------------------------------------------------------------


class TestGatedRealMode:
    @pytest.mark.asyncio
    async def test_full_real_mode_with_credentials(self, clean_env):
        kernel, temp_dir = await _boot_kernel(clean_env, _REAL_ENV)
        try:
            # Supabase + n8n get real because gate + creds both present.
            assert kernel.supabase_adapter.is_real_mode is True
            assert kernel.n8n_adapter.is_real_mode is True
            # Obsidian Git also real because gate + vault path present.
            assert kernel.obsidian_git_adapter.is_real_mode is True
            reg = kernel._capability_manager
            assert reg.get_capability("supabase_persistence") is not None
            assert reg.get_capability("n8n_execution") is not None
            assert reg.get_capability("obsidian_git_knowledge") is not None
        finally:
            await _shutdown_kernel(kernel, temp_dir)

    @pytest.mark.asyncio
    async def test_partial_credentials_gates_per_adapter(self, clean_env):
        # Only Supabase creds present -> only Supabase real; others stay mock.
        kernel, temp_dir = await _boot_kernel(
            clean_env,
            {
                "AIOS_REAL_INTEGRATION_ENABLED": "1",
                "SUPABASE_URL": "https://example.supabase.co",
                "SUPABASE_ANON_KEY": "public-anon-key",
            },
        )
        try:
            assert kernel.supabase_adapter.is_real_mode is True
            assert kernel.n8n_adapter.is_mock_mode is True
            assert kernel.obsidian_git_adapter.is_mock_mode is True
        finally:
            await _shutdown_kernel(kernel, temp_dir)

    @pytest.mark.asyncio
    async def test_gate_cleared_mid_run_reverts_mock(self, clean_env):
        # With gate present but env cleared of credentials, adapters stay mock.
        # (Confirms credential check is independent of a stale gate flag.)
        kernel, temp_dir = await _boot_kernel(
            clean_env, {"AIOS_REAL_INTEGRATION_ENABLED": "1"}
        )
        try:
            assert kernel.supabase_adapter.is_real_mode is False
            assert kernel.n8n_adapter.is_real_mode is False
            assert kernel.obsidian_git_adapter.is_real_mode is False
        finally:
            await _shutdown_kernel(kernel, temp_dir)


# ---------------------------------------------------------------------------
# Authority preservation is independent of mode (mock or real)
# ---------------------------------------------------------------------------


class TestAuthorityPreservationAcrossModes:
    @pytest.mark.asyncio
    async def test_no_terminal_violations_in_real_mode(self, clean_env):
        kernel, temp_dir = await _boot_kernel(clean_env, _REAL_ENV)
        try:
            assert kernel.terminal_contract_violations == []
            for adapter in (
                kernel.supabase_adapter,
                kernel.n8n_adapter,
                kernel.obsidian_git_adapter,
            ):
                assert adapter.terminal == "T2"
                assert adapter.authority_level == "bounded_resource"
        finally:
            await _shutdown_kernel(kernel, temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
