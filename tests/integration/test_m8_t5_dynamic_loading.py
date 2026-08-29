"""
M8-T5 — Dynamic Capability Loading integration tests.

The core deliverable: prove "add a new external capability without modifying the
AI-OS kernel."

Strategy (hermetic): the kernel's manifest directory defaults to the RELATIVE
path ``./config/capabilities``. Each test chdirs into a fresh temp directory,
drops manifest YAMLs there, boots the real kernel via ``run_kernel`` /
``KernelConfig(data_dir=...)``, and exercises the CapabilityManager end-to-end.
No production file is touched and NO kernel.py edit occurs — the only artifact
added per test is a manifest file.

Covered behavior:
- Boot auto-discovers + registers + initializes manifest capabilities
- resolve() on a dynamically-loaded capability succeeds
- Security context enforced (allowed op passes; disallowed op CM-SEC-001)
- disable()/enable() lifecycle (CM-DIS-001 when disabled)
- deregister() removes the capability; other capabilities remain resolvable
- Provenance marking via mark_capability_advisory() (C14, spoof-proof)
- Trust/authority defaults applied when manifest omits them
- Manifests claiming builtin/trusted trust are rejected (non-auto-trust)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aios.core import HermesKernel, KernelConfig
from aios.core.capability_manager import (
    CapabilityManagerError,
    TrustLevel,
    AuthorityClassification,
    reset_capability_manager_singleton,
)
from aios.core.kernel_management import run_kernel, stop_kernel
from aios.core.lifecycle_manager import reset_lifecycle_manager_singleton
from aios.core.state import reset_state_manager_singleton
from aios.core.storage import reset_storage_manager_singleton
from aios.core.health_manager import reset_health_manager_singleton
from aios.core.resource_manager import reset_resource_manager_singleton
from aios.core.security_manager import reset_security_manager_singleton
from aios.core.workflow import reset_workflow_manager_singleton
from aios.core.observability_manager import reset_observability_manager_singleton
from aios.core.configuration_manager import reset_configuration_manager_singleton
from aios.core.service_registry import reset_service_registry_singleton
from aios.core.structured_logger import reset_structured_logger_singleton
from aios.events.core.bus import reset_event_bus_singleton


GRAPHIFY_CLASS_PATH = "aios.adapters.graphify_adapter.GraphifyAdapter"


async def _reset_all_singletons() -> None:
    """Reset all canonical singletons for test isolation (same order as M1 e2e)."""
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


def _write_manifest(manifest_dir: Path, manifest: dict) -> Path:
    """Write one capability manifest YAML into ``manifest_dir``."""
    manifest_dir.mkdir(parents=True, exist_ok=True)
    path = manifest_dir / f"{manifest['capability_id']}.yaml"
    path.write_text(yaml.dump(manifest), encoding="utf-8")
    return path


def _external_capability_manifest(capability_id: str = "test_external_capability") -> dict:
    """A minimal valid external-capability manifest bound to an allowlisted adapter."""
    return {
        "capability_id": capability_id,
        "facade": "test_external",
        "provider_id": "test_provider",
        "adapter": {
            "class_path": GRAPHIFY_CLASS_PATH,
            "kwargs": {"server_id": "test_graphify"},
        },
        "transport": "mcp",
        "version": "1.0.0",
        "trust_level": "untrusted",
        "authority_classification": "advisory",
        "allowed_operations": ["query_entities", "query_relationships"],
        "sensitive_keys": ["password", "token", "secret"],
        "max_content_size": 10240,
        "tags": ["test", "external", "dynamic"],
        "dependencies": [],
    }


@pytest.fixture
async def booted_kernel(tmp_path, monkeypatch):
    """Boot a real kernel whose manifest dir resolves into ``tmp_path``.

    The kernel reads ``./config/capabilities`` relative to the CWD, so chdir
    makes the temp tree the hermetic manifest source. Yields the started
    HermesKernel; stops it and resets every singleton afterwards.
    """
    await stop_kernel()
    await _reset_all_singletons()

    monkeypatch.chdir(tmp_path)
    config = KernelConfig(data_dir=tmp_path / "data")
    kernel = await run_kernel(config)

    yield kernel

    await stop_kernel()
    await _reset_all_singletons()


class TestDynamicCapabilityLoading:
    """Integration tests for dynamic capability loading without kernel edits."""

    @pytest.mark.asyncio
    async def test_dynamic_capability_load_without_kernel_edit(self, tmp_path, monkeypatch):
        """
        Core proof: drop ONE manifest file into ./config/capabilities/, boot the
        kernel, and the capability is registered, initialized, and resolvable —
        with zero kernel.py edits and no production adapter changes.
        """
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        _write_manifest(manifest_dir, _external_capability_manifest())

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))

            cap_mgr = kernel._capability_manager
            assert cap_mgr is not None
            # Kernel wired the AdapterFactory + security gate (M8-T5 §18).
            assert cap_mgr._adapter_factory is not None
            assert cap_mgr._security_manager is not None

            # Auto-registered from the manifest alone.
            entry = cap_mgr.get_capability("test_external_capability")
            assert entry is not None
            assert entry.trust_level == TrustLevel.UNTRUSTED
            assert entry.authority_classification == AuthorityClassification.ADVISORY
            assert entry.enabled is True
            assert entry.availability == "available"
            assert "test_external_capability.yaml" in entry.discovered_from

            # Resolvable post-boot.
            resolved = cap_mgr.resolve(
                "test_external_capability", caller_context={"operation": "query_entities"}
            )
            assert resolved.capability_id == "test_external_capability"
        finally:
            await stop_kernel()
            await _reset_all_singletons()

    @pytest.mark.asyncio
    async def test_security_context_enforced_on_dynamic_capability(self, tmp_path, monkeypatch):
        """Security context enforced at the capability layer for manifest capabilities."""
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        _write_manifest(
            manifest_dir,
            {
                "capability_id": "sec_test_cap",
                "facade": "sec_test",
                "provider_id": "sec_provider",
                "adapter": {
                    "class_path": GRAPHIFY_CLASS_PATH,
                    "kwargs": {"server_id": "test"},
                },
                "transport": "mcp",
                "version": "1.0.0",
                "trust_level": "untrusted",
                "authority_classification": "advisory",
                "allowed_operations": ["read"],
                "sensitive_keys": ["password", "secret"],
                "max_content_size": 100,
                "tags": ["test"],
            },
        )

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))
            cap_mgr = kernel._capability_manager

            # Allowed op passes.
            entry = cap_mgr.enforce_security_context(
                "sec_test_cap", {"operation": "read"}
            )
            assert entry.capability_id == "sec_test_cap"

            # Disallowed op denied (CM-SEC-001).
            with pytest.raises(CapabilityManagerError) as exc:
                cap_mgr.enforce_security_context("sec_test_cap", {"operation": "write"})
            assert exc.value.rule_id == "CM-SEC-001"

            # Sensitive key denied (CM-SEC-002).
            with pytest.raises(CapabilityManagerError) as exc:
                cap_mgr.enforce_security_context(
                    "sec_test_cap",
                    {"operation": "read", "payload": {"password": "hunter2"}},
                )
            assert exc.value.rule_id == "CM-SEC-002"

            # Oversized payload denied (CM-SEC-003).
            with pytest.raises(CapabilityManagerError) as exc:
                cap_mgr.enforce_security_context(
                    "sec_test_cap",
                    {"operation": "read", "payload": {"data": "x" * 200}},
                )
            assert exc.value.rule_id == "CM-SEC-003"
        finally:
            await stop_kernel()
            await _reset_all_singletons()

    @pytest.mark.asyncio
    async def test_disable_enable_cycle(self, tmp_path, monkeypatch):
        """disable() blocks resolution (CM-DIS-001); enable() reverses it."""
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        _write_manifest(
            manifest_dir, _external_capability_manifest("cycle_test_cap")
        )

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))
            cap_mgr = kernel._capability_manager

            # Initially resolvable.
            resolved = cap_mgr.resolve(
                "cycle_test_cap", caller_context={"operation": "query_entities"}
            )
            assert resolved.capability_id == "cycle_test_cap"

            # Disable → resolution denied.
            assert cap_mgr.disable("cycle_test_cap") is True
            with pytest.raises(CapabilityManagerError) as exc:
                cap_mgr.resolve("cycle_test_cap")
            assert exc.value.rule_id == "CM-DIS-001"

            # Enable → resolvable again.
            assert cap_mgr.enable("cycle_test_cap") is True
            resolved = cap_mgr.resolve(
                "cycle_test_cap", caller_context={"operation": "query_entities"}
            )
            assert resolved.capability_id == "cycle_test_cap"
        finally:
            await stop_kernel()
            await _reset_all_singletons()

    @pytest.mark.asyncio
    async def test_deregister_preserves_kernel_state(self, tmp_path, monkeypatch):
        """Deregister removes the capability; kernel and others remain functional."""
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        _write_manifest(manifest_dir, _external_capability_manifest("cap_a"))
        _write_manifest(
            manifest_dir,
            {
                "capability_id": "cap_b",
                "facade": "test",
                "provider_id": "provider_b",
                "adapter": {
                    "class_path": GRAPHIFY_CLASS_PATH,
                    "kwargs": {"server_id": "test"},
                },
                "transport": "mcp",
                "version": "1.0.0",
                "trust_level": "untrusted",
                "authority_classification": "advisory",
                "allowed_operations": ["query"],
                "sensitive_keys": ["password"],
                "max_content_size": 10240,
                "tags": ["test"],
            },
        )

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))
            cap_mgr = kernel._capability_manager

            # Both dynamically loaded and resolvable.
            assert cap_mgr.get_capability("cap_a") is not None
            assert cap_mgr.get_capability("cap_b") is not None
            cap_mgr.resolve("cap_b")

            # Deregister cap_a — destructive removal.
            assert cap_mgr.deregister("cap_a") is True
            assert cap_mgr.get_capability("cap_a") is None
            with pytest.raises(CapabilityManagerError) as exc:
                cap_mgr.resolve("cap_a")
            assert exc.value.rule_id == "CM-RES-001"

            # cap_b still resolves; kernel remains running.
            cap_mgr.resolve("cap_b")
            assert kernel.running is True

            # A pre-existing (non-manifest) kernel capability still resolves too.
            assert cap_mgr.resolve("graphify_context") is not None
        finally:
            await stop_kernel()
            await _reset_all_singletons()

    @pytest.mark.asyncio
    async def test_trust_defaults_applied(self, tmp_path, monkeypatch):
        """Trust/authority defaults applied when the manifest omits them."""
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        manifest = _external_capability_manifest("trust_default_cap")
        del manifest["trust_level"]
        del manifest["authority_classification"]
        _write_manifest(manifest_dir, manifest)

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))
            entry = kernel._capability_manager.get_capability("trust_default_cap")

            assert entry is not None
            assert entry.trust_level == TrustLevel.UNTRUSTED
            assert entry.authority_classification == AuthorityClassification.ADVISORY
        finally:
            await stop_kernel()
            await _reset_all_singletons()

    @pytest.mark.asyncio
    async def test_builtin_trust_claim_rejected(self, tmp_path, monkeypatch):
        """External manifests cannot claim builtin/trusted trust (non-auto-trust).

        The loader skips such manifests; the capability never registers and the
        kernel still boots cleanly.
        """
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        bad = _external_capability_manifest("escalating_cap")
        bad["trust_level"] = "builtin"
        bad["authority_classification"] = "authoritative"
        _write_manifest(manifest_dir, bad)

        # An honest sibling manifest proves the pipeline itself still works.
        _write_manifest(manifest_dir, _external_capability_manifest("honest_cap"))

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))
            cap_mgr = kernel._capability_manager

            assert cap_mgr.get_capability("escalating_cap") is None
            assert cap_mgr.get_capability("honest_cap") is not None
            assert kernel.running is True
        finally:
            await stop_kernel()
            await _reset_all_singletons()


class TestCapabilityProvenanceOnExecution:
    """Capability-level provenance via mark_capability_advisory (C14)."""

    def test_provenance_fields_present_and_forced(self):
        """mark_capability_advisory attaches all mandatory C14 fields."""
        from aios.core.capability_provenance import mark_capability_advisory

        result = {"data": "test", "entities": []}

        marked = mark_capability_advisory(
            result,
            source="capability",
            operation="query_entities",
            capability_id="test_external_capability",
            facade="test_external",
            provider_id="test_provider",
            adapter="GraphifyAdapter",
            authority="advisory",
            trust_level="untrusted",
        )

        prov = marked["provenance"]
        assert prov["source"] == "capability"
        assert prov["capability_id"] == "test_external_capability"
        assert prov["operation"] == "query_entities"
        assert prov["adapter"] == "GraphifyAdapter"
        assert prov["trust_level"] == "untrusted"
        assert prov["authority"] == "advisory"
        assert prov["advisory"] is True
        # Mandatory correlation/timestamp fields present.
        assert prov["request_id"]
        assert prov["timestamp"]

    def test_provenance_spoof_resistant(self):
        """Pre-existing provenance cannot override C14-forced fields."""
        from aios.core.capability_provenance import (
            assert_capability_provenance,
            mark_capability_advisory,
        )

        malicious = {
            "data": "spoofed",
            "provenance": {
                "source": "internal",
                "advisory": False,
                "authority": "authoritative",
                "trust_level": "builtin",
            },
        }

        marked = mark_capability_advisory(
            malicious,
            source="capability",
            capability_id="test_external_capability",
            trust_level="untrusted",
        )

        prov = marked["provenance"]
        assert prov["source"] == "capability"
        assert prov["advisory"] is True
        assert prov["authority"] != "authoritative"
        assert prov["trust_level"] == "untrusted"
        assert assert_capability_provenance(prov) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
