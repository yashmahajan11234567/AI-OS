"""
M13 — Terminal Architecture & Separation contract tests.

Verifies the four-terminal authority model from
``M13_TERMINAL_HANDOFF_CONTRACT.md`` is enforced in code:

  * T1 holds sole AUTHORITATIVE authority.
  * T2 bounded-resource adapters (Supabase, n8n, Obsidian Git, and the rest of
    the external ecosystem) hold only bounded authority and never AUTHORITATIVE.
  * T3 (dashboard/UI) is USER_INTERFACE only.
  * T4 (dev/test) is DEVELOPMENT_TESTING only.
  * Authority-preservation validation rejects any illegal claim (e.g. a
    non-T1 component asserting AUTHORITATIVE).
  * The live kernel wires the M13 adapters and boots with zero contract
    violations.
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
from aios.architecture.terminal_contract import (
    TerminalId,
    AuthorityLevel,
    TerminalContract,
    AuthorityViolation,
    TERMINAL_ASSIGNMENTS,
    TERMINAL_AUTHORITY,
    BOUNDED_RESOURCE_ADAPTERS,
    describe_terminal,
    adapter_terminal,
    authority_level_for_adapter,
    validate_authority_preservation,
)
from aios.adapters.supabase_adapter import SupabaseAdapter
from aios.adapters.n8n_adapter import N8nAdapter
from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter


# ---------------------------------------------------------------------------
# Terminal authority taxonomy
# ---------------------------------------------------------------------------


class TestTerminalAuthorityTaxonomy:
    def test_t1_is_authoritative_only(self):
        assert TERMINAL_AUTHORITY[TerminalId.T1_CORE] == AuthorityLevel.AUTHORITATIVE

    def test_t2_is_bounded_resource(self):
        assert TERMINAL_AUTHORITY[TerminalId.T2_EXTERNAL] == AuthorityLevel.BOUNDED_RESOURCE

    def test_t3_is_user_interface(self):
        assert TERMINAL_AUTHORITY[TerminalId.T3_UI] == AuthorityLevel.USER_INTERFACE

    def test_t4_is_development_testing(self):
        assert TERMINAL_AUTHORITY[TerminalId.T4_DEV] == AuthorityLevel.DEVELOPMENT_TESTING

    def test_describe_terminal(self):
        assert "sole authoritative" in describe_terminal(TerminalId.T1_CORE).lower()
        assert "bounded resource" in describe_terminal(TerminalId.T2_EXTERNAL).lower()
        assert "no authority" in describe_terminal(TerminalId.T3_UI).lower()


# ---------------------------------------------------------------------------
# Adapter terminal placement
# ---------------------------------------------------------------------------


class TestAdapterTerminalPlacement:
    def test_m13_adapters_hosted_on_t2(self):
        assert adapter_terminal(
            "aios.adapters.supabase_adapter.SupabaseAdapter"
        ) == TerminalId.T2_EXTERNAL
        assert adapter_terminal(
            "aios.adapters.n8n_adapter.N8nAdapter"
        ) == TerminalId.T2_EXTERNAL
        assert adapter_terminal(
            "aios.adapters.obsidian_git_adapter.ObsidianGitAdapter"
        ) == TerminalId.T2_EXTERNAL

    def test_authority_level_for_m13_adapters_is_bounded(self):
        for path in BOUNDED_RESOURCE_ADAPTERS:
            lvl = authority_level_for_adapter(path)
            assert lvl in (
                AuthorityLevel.BOUNDED_RESOURCE,
                AuthorityLevel.BOUNDED_EXECUTION,
            )
            assert lvl != AuthorityLevel.AUTHORITATIVE

    def test_supabase_adapter_metadata(self):
        a = SupabaseAdapter()
        assert a.terminal == "T2"
        assert a.authority_level == "bounded_resource"

    def test_n8n_adapter_metadata(self):
        a = N8nAdapter()
        assert a.terminal == "T2"
        assert a.authority_level == "bounded_resource"

    def test_obsidian_git_adapter_metadata(self):
        a = ObsidianGitAdapter()
        assert a.terminal == "T2"
        assert a.authority_level == "bounded_resource"


# ---------------------------------------------------------------------------
# Authority preservation validation
# ---------------------------------------------------------------------------


class TestAuthorityPreservation:
    def test_t1_authoritative_is_compliant(self):
        v = validate_authority_preservation(
            component="aios.core.kernel.HermesKernel",
            terminal=TerminalId.T1_CORE,
            claimed_level=AuthorityLevel.AUTHORITATIVE,
        )
        assert v is None

    def test_non_t1_claiming_authoritative_is_violation(self):
        v = validate_authority_preservation(
            component="some.external.Adapter",
            terminal=TerminalId.T2_EXTERNAL,
            claimed_level=AuthorityLevel.AUTHORITATIVE,
        )
        assert isinstance(v, AuthorityViolation)
        assert v.terminal == "T2"
        assert "AUTHORITATIVE" in v.detail

    def test_t3_claiming_authoritative_is_violation(self):
        v = validate_authority_preservation(
            component="dashboard",
            terminal=TerminalId.T3_UI,
            claimed_level=AuthorityLevel.AUTHORITATIVE,
        )
        assert isinstance(v, AuthorityViolation)

    def test_t2_claiming_wrong_level_is_violation(self):
        # T2 may only hold BOUNDED_RESOURCE/BOUNDED_EXECUTION, never USER_INTERFACE.
        v = validate_authority_preservation(
            component="external.endpoint",
            terminal=TerminalId.T2_EXTERNAL,
            claimed_level=AuthorityLevel.USER_INTERFACE,
        )
        assert isinstance(v, AuthorityViolation)

    def test_t3_user_interface_is_compliant(self):
        v = validate_authority_preservation(
            component="dashboard",
            terminal=TerminalId.T3_UI,
            claimed_level=AuthorityLevel.USER_INTERFACE,
        )
        assert v is None

    def test_violation_serializes(self):
        v = AuthorityViolation(
            terminal="T2", component="x", claimed_level="authoritative",
            detail="d",
        )
        d = v.to_dict()
        assert d["terminal"] == "T2"
        assert d["claimed_level"] == "authoritative"


# ---------------------------------------------------------------------------
# TerminalContract runtime validator
# ---------------------------------------------------------------------------


class TestTerminalContractRuntime:
    def test_check_all_adapters_compliant(self):
        contract = TerminalContract()
        violations = contract.check_all_adapters()
        assert violations == []
        assert contract.is_compliant() is True

    def test_check_known_adapter_returns_none(self):
        contract = TerminalContract()
        assert contract.check_adapter(
            "aios.adapters.supabase_adapter.SupabaseAdapter"
        ) is None


# ---------------------------------------------------------------------------
# Kernel boot integration
# ---------------------------------------------------------------------------


async def _reset_all_singletons():
    """Reset all global singletons for kernel-boot test isolation.

    An earlier test in the full unit suite may have already frozen the
    shared ConfigurationManager (and other) singletons; the kernel re-freezes
    them at boot, which raises ConfigurationFrozenError. Resetting first gives
    the boot a clean slate regardless of collection order.
    """
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


class TestKernelTerminalContract:
    """Validate the live kernel wires M13 adapters with zero authority violations."""

    @pytest.mark.asyncio
    async def test_kernel_boots_without_terminal_violations(self):
        from aios.core.kernel import HermesKernel, KernelConfig

        await _reset_all_singletons()
        temp_dir = Path(tempfile.mkdtemp())
        try:
            kernel = HermesKernel(config=KernelConfig(data_dir=temp_dir))
            await kernel.start()
            try:
                # No bounded resource may have claimed AI-OS authority at boot.
                assert kernel.terminal_contract_violations == [], (
                    kernel.terminal_contract_violations
                )
                # M13 adapters are wired and marked T2/bounded.
                assert kernel.supabase_adapter is not None
                assert kernel.supabase_adapter.terminal == "T2"
                assert kernel.n8n_adapter is not None
                assert kernel.n8n_adapter.terminal == "T2"
                assert kernel.obsidian_git_adapter is not None
                assert kernel.obsidian_git_adapter.terminal == "T2"
            finally:
                await kernel.stop()
        finally:
            await _reset_all_singletons()
            shutil.rmtree(temp_dir, ignore_errors=True)
