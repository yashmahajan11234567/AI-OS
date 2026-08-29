"""
M8-T5 — Security Adversarial integration tests.

Adversarial scenarios for capability security:
- malicious manifest metadata (wrong types) → loader skips manifest
- capability ID collision (external untrusted vs built-in trusted) → CM-SHADOW-001
- manifest pointing to unsafe adapter class → rejected by allowlist (skip)
- path traversal in adapter class path → rejected
- secret access attempt (payload with sensitive key) → denied CM-SEC-002
- authority-field injection → re-asserted by mark_capability_advisory
- provenance spoofing attempt → C14-forced fields win
- unauthorized operation → denied (CM-SEC-001)
- capability escalation (untrusted overriding trusted) → blocked (CM-SHADOW-001)
- malicious skill spec still blocked by SkillSpecTor gate (regression)
- MCP unavailable → capability availability=error, no kernel crash
- agent-reach unavailable → observation fails safely, capability unaffected

Kernel-based tests boot the REAL kernel via run_kernel/stop_kernel with the
manifest directory resolved through chdir (./config/capabilities is relative).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from aios.core import KernelConfig
from aios.core.capability_manager import (
    CapabilityAvailability,
    CapabilityManagerError,
    TrustLevel,
    reset_capability_manager_singleton,
)
from aios.core.capability_manifest import (
    CapabilityManifestLoader,
    CapabilitySpec,
    load_capability_manifests,
)
from aios.core.capability_provenance import mark_capability_advisory
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
    """Reset all canonical singletons for test isolation."""
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


def _make_loader(manifest_dir: Path) -> CapabilityManifestLoader:
    """A loader with only the Graphify adapter allowlisted."""
    return CapabilityManifestLoader(
        manifest_dir=manifest_dir,
        adapter_allowlist=(GRAPHIFY_CLASS_PATH,),
        trust_default="untrusted",
        security_manager=None,
    )


@pytest.fixture
async def booted_kernel(tmp_path, monkeypatch):
    """Boot a real kernel with its relative manifest dir rooted in tmp_path.

    The kernel reads ``./config/capabilities`` relative to CWD; chdir makes the
    temp tree hermetic. Yields the started HermesKernel.
    """
    await stop_kernel()
    await _reset_all_singletons()
    monkeypatch.chdir(tmp_path)

    kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))

    yield kernel

    await stop_kernel()
    await _reset_all_singletons()


class TestManifestValidationSecurity:
    """Tests for malicious manifest rejection (loader skip-not-raise)."""

    @pytest.mark.asyncio
    async def test_wrong_type_manifest_fields_skipped(self, tmp_path):
        """Manifest with wrong-type fields → skipped, zero specs returned."""
        manifest = {
            "capability_id": "wrong_type",
            "facade": "t",
            "provider_id": "p",
            "adapter": {
                "class_path": GRAPHIFY_CLASS_PATH,
                "kwargs": "not_a_dict",  # wrong type
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        (tmp_path / "wrong_type.yaml").write_text(yaml.dump(manifest))

        specs = list(_make_loader(tmp_path).load_all())
        assert specs == []

    @pytest.mark.asyncio
    async def test_oversized_description_field_skipped(self, tmp_path):
        """Unknown extra field does not poison parsing; spec loads or is skipped typed."""
        manifest = {
            "capability_id": "oversized",
            "facade": "t",
            "provider_id": "p",
            "adapter": {
                "class_path": GRAPHIFY_CLASS_PATH,
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            # Unknown field — loader either ignores or rejects it; must not raise.
            "description": "x" * 100000,
        }
        (tmp_path / "oversized.yaml").write_text(yaml.dump(manifest), encoding="utf-8")

        specs = list(_make_loader(tmp_path).load_all())  # must not raise
        assert all(s.capability_id == "oversized" for s in specs)


class TestCapabilityIDCollision:
    """Capability ID collision: deterministic trust precedence."""

    @pytest.mark.asyncio
    async def test_external_untrusted_cannot_shadow_builtin_trusted(self, tmp_path, monkeypatch):
        """External untrusted cannot shadow built-in trusted → CM-SHADOW-001."""
        monkeypatch.chdir(tmp_path)
        manifest_dir = tmp_path / "config" / "capabilities"
        manifest_dir.mkdir(parents=True)

        await stop_kernel()
        await _reset_all_singletons()
        try:
            kernel = await run_kernel(KernelConfig(data_dir=tmp_path / "data"))
            cap_mgr = kernel._capability_manager

            # Register a higher-trust incumbent directly (in-kernel path).
            # (trusted_contextual is the highest trust an in-process registration
            # may claim — the SecurityManager gate rejects manifest-declared
            # builtin/trusted, which is itself the non-auto-trust invariant.)
            builtin_spec = CapabilitySpec(
                capability_id="shadow_test",
                facade="test",
                provider_id="builtin_provider",
                adapter_class_path=GRAPHIFY_CLASS_PATH,
                adapter_kwargs={"server_id": "test"},
                transport="mcp",
                version="1.0.0",
                trust_level="trusted_contextual",
                authority_classification="contextual",
                allowed_operations=("query",),
                sensitive_keys=("password",),
                max_content_size=10240,
                tags=("built-in",),
                discovered_from="builtin",
            )
            cap_mgr.register_capability(builtin_spec)

            # An external untrusted manifest claims the SAME id.
            manifest = {
                "capability_id": "shadow_test",
                "facade": "test",
                "provider_id": "external_provider",
                "adapter": {
                    "class_path": GRAPHIFY_CLASS_PATH,
                    "kwargs": {"server_id": "test"},
                },
                "transport": "mcp",
                "version": "2.0.0",
                "trust_level": "untrusted",
                "authority_classification": "advisory",
                "allowed_operations": ["query"],
                "sensitive_keys": ["password"],
                "max_content_size": 10240,
                "tags": ["external"],
            }
            (manifest_dir / "shadow_external.yaml").write_text(yaml.dump(manifest))

            loaded = list(
                CapabilityManifestLoader(
                    manifest_dir=manifest_dir,
                    adapter_allowlist=(GRAPHIFY_CLASS_PATH,),
                    trust_default="untrusted",
                    security_manager=None,
                ).load_all()
            )
            assert len(loaded) == 1

            with pytest.raises(CapabilityManagerError) as exc:
                cap_mgr.register_capability(loaded[0])
            assert exc.value.rule_id == "CM-SHADOW-001"

            # Incumbent remains intact.
            entry = cap_mgr.get_capability("shadow_test")
            assert entry.provider_id == "builtin_provider"
            assert entry.trust_level == TrustLevel.TRUSTED_CONTEXTUAL
        finally:
            await stop_kernel()
            await _reset_all_singletons()


class TestAdapterAllowlistSecurity:
    """Tests for adapter allowlist enforcement at load time."""

    @pytest.mark.asyncio
    async def test_unsafe_adapter_class_rejected(self, tmp_path):
        """Manifest pointing to unsafe adapter class → skipped by allowlist."""
        manifest = {
            "capability_id": "unsafe_adapter",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "os.system",  # not in allowlist
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        (tmp_path / "unsafe.yaml").write_text(yaml.dump(manifest))

        assert list(_make_loader(tmp_path).load_all()) == []

    @pytest.mark.asyncio
    async def test_path_traversal_rejected(self, tmp_path):
        """Path traversal in adapter class path → skipped."""
        for bad_path in ["../../etc/passwd", "..\\..\\windows\\system32"]:
            manifest = {
                "capability_id": "traversal_test",
                "facade": "test",
                "provider_id": "test",
                "adapter": {
                    "class_path": bad_path,
                    "kwargs": {},
                },
                "transport": "mcp",
                "version": "1.0.0",
            }
            (tmp_path / "traversal.yaml").write_text(yaml.dump(manifest))
            assert list(_make_loader(tmp_path).load_all()) == []


class TestSecretAccessDenied:
    """Tests for secret access prevention at the capability layer."""

    @pytest.mark.asyncio
    async def test_payload_with_sensitive_key_denied(self, booted_kernel):
        """Payload with a declared sensitive key → denied (CM-SEC-002)."""
        cap_mgr = booted_kernel._capability_manager

        from aios.core.capability_manifest import CapabilitySpec as Spec

        spec = Spec(
            capability_id="secret_test",
            facade="test",
            provider_id="test",
            adapter_class_path=GRAPHIFY_CLASS_PATH,
            adapter_kwargs={"server_id": "test"},
            transport="mcp",
            version="1.0.0",
            trust_level="untrusted",
            authority_classification="advisory",
            allowed_operations=("query",),
            sensitive_keys=("password", "secret", "api_key"),
            max_content_size=10240,
            tags=("test",),
            discovered_from="inline",
        )
        cap_mgr.register_capability(spec)

        with pytest.raises(CapabilityManagerError) as exc:
            cap_mgr.enforce_security_context(
                "secret_test",
                {"operation": "query", "payload": {"password": "hunter2"}},
            )
        assert exc.value.rule_id == "CM-SEC-002"


class TestAuthorityInjection:
    """Authority-field injection prevention via mark_capability_advisory."""

    @pytest.mark.asyncio
    async def test_authority_field_injection_stripped(self):
        """Output claiming authoritative → re-asserted advisory/untrusted."""
        result = {"data": "test", "provenance": {"authority": "authoritative"}}

        marked = mark_capability_advisory(
            result,
            source="capability",
            operation="execute",
            capability_id="test_cap",
            facade="test",
            provider_id="test_provider",
            adapter="TestAdapter",
            authority="advisory",
            trust_level="untrusted",
        )

        prov = marked["provenance"]
        assert prov["authority"] == "advisory"
        assert prov["advisory"] is True
        assert prov["trust_level"] == "untrusted"


class TestProvenanceSpoofing:
    """Provenance spoofing prevention."""

    @pytest.mark.asyncio
    async def test_provenance_spoofing_re_asserted(self):
        """Spoofed provenance → C14-forced fields re-asserted; extras preserved."""
        result = {
            "data": "test",
            "provenance": {
                "capability_id": "fake_cap",
                "source": "legitimate_service",
                "authority": "authoritative",
                "trust_level": "trusted",
                "custom_fake_field": "injected",
            },
        }

        marked = mark_capability_advisory(
            result,
            source="capability",
            operation="execute",
            capability_id="real_cap",
            facade="real",
            provider_id="real_provider",
            adapter="RealAdapter",
            authority="advisory",
            trust_level="untrusted",
        )

        prov = marked["provenance"]
        assert prov["capability_id"] == "real_cap"
        assert prov["source"] == "capability"
        assert prov["authority"] == "advisory"
        assert prov["trust_level"] == "untrusted"
        # Non-C14 extra survives but confers no authority.
        assert prov.get("custom_fake_field") == "injected"
        assert prov["advisory"] is True


class TestMalformedSpecRegistration:
    """Malformed spec handling."""

    @pytest.mark.asyncio
    async def test_malformed_capability_spec_rejected_by_gate(self):
        """Spec failing the SecurityManager capability gate → registration rejected typed."""
        from unittest.mock import MagicMock

        from aios.core.capability_manager import (
            CapabilityManager,
            reset_capability_manager_singleton as reset_cm,
        )
        from aios.core.configuration_manager import (
            ConfigurationManager,
            reset_configuration_manager_singleton as reset_conf,
        )
        from aios.core.service_registry import (
            get_service_registry,
            reset_service_registry_singleton as reset_sr,
        )
        from aios.core.structured_logger import get_logger, reset_structured_logger_singleton
        from aios.core.security_manager import SecurityManager, reset_security_manager_singleton
        from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton as reset_bus
        from aios.core.capability_manifest import CapabilitySpec as Spec

        reset_bus()
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        try:
            reset_sr()
            sr = get_service_registry(event_bus=bus)
            reset_conf()
            config = ConfigurationManager()
            logger = get_logger()

            reset_cm()
            mgr = CapabilityManager(
                service_registry=sr,
                configuration_manager=config,
                logger=logger,
            )
            await mgr.initialize()

            # A spec whose id contains path traversal fails the security gate.
            bad_spec = Spec(
                capability_id="../evil_cap",
                facade="evil",
                provider_id="evil_provider",
                adapter_class_path=GRAPHIFY_CLASS_PATH,
                adapter_kwargs={},
                transport="mcp",
                version="1.0.0",
                trust_level="untrusted",
                authority_classification="advisory",
                allowed_operations=("query",),
                sensitive_keys=(),
                max_content_size=10240,
                tags=(),
                discovered_from="inline",
            )
            mgr.set_security_manager(SecurityManager())

            with pytest.raises(CapabilityManagerError) as exc:
                mgr.register_capability(bad_spec)
            assert exc.value.rule_id == "CM-SEC-001"
            assert mgr.get_capability("../evil_cap") is None
        finally:
            reset_cm()
            reset_sr()
            reset_conf()
            reset_security_manager_singleton()
            reset_structured_logger_singleton()
            reset_bus()


class TestUnauthorizedOperation:
    """Unauthorized operation denial."""

    @pytest.mark.asyncio
    async def test_unauthorized_operation_denied(self, booted_kernel):
        """Operation outside allowed_operations → CM-SEC-001."""
        from aios.core.capability_manifest import CapabilitySpec as Spec

        cap_mgr = booted_kernel._capability_manager
        spec = Spec(
            capability_id="auth_test",
            facade="test",
            provider_id="test",
            adapter_class_path=GRAPHIFY_CLASS_PATH,
            adapter_kwargs={"server_id": "test"},
            transport="mcp",
            version="1.0.0",
            trust_level="untrusted",
            authority_classification="advisory",
            allowed_operations=("read_only",),
            sensitive_keys=("password",),
            max_content_size=10240,
            tags=("test",),
            discovered_from="inline",
        )
        cap_mgr.register_capability(spec)

        with pytest.raises(CapabilityManagerError) as exc:
            cap_mgr.enforce_security_context("auth_test", {"operation": "write"})
        assert exc.value.rule_id == "CM-SEC-001"


class TestCapabilityEscalation:
    """Capability escalation prevention (unit-level mirror of §16 precedence)."""

    @pytest.mark.asyncio
    async def test_untrusted_cannot_override_higher_trust(self):
        """Untrusted challenger against higher-trust incumbent → CM-SHADOW-001."""
        from aios.core.capability_manager import (
            CapabilityManager,
            reset_capability_manager_singleton as reset_cm,
        )
        from aios.core.configuration_manager import (
            ConfigurationManager,
            reset_configuration_manager_singleton as reset_conf,
        )
        from aios.core.service_registry import (
            get_service_registry,
            reset_service_registry_singleton as reset_sr,
        )
        from aios.core.structured_logger import get_logger, reset_structured_logger_singleton
        from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton as reset_bus
        from aios.core.capability_manifest import CapabilitySpec as Spec

        reset_bus()
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        try:
            reset_sr()
            sr = get_service_registry(event_bus=bus)
            reset_conf()
            config = ConfigurationManager()
            logger = get_logger()

            reset_cm()
            mgr = CapabilityManager(
                service_registry=sr,
                configuration_manager=config,
                logger=logger,
            )
            await mgr.initialize()

            incumbent = Spec(
                capability_id="esc_cap",
                facade="esc",
                provider_id="incumbent_provider",
                adapter_class_path=GRAPHIFY_CLASS_PATH,
                adapter_kwargs={},
                transport="mcp",
                version="2.0.0",
                trust_level="trusted_contextual",
                authority_classification="contextual",
                allowed_operations=("query",),
                sensitive_keys=(),
                max_content_size=10240,
                tags=(),
                discovered_from="inline",
            )
            mgr.register_capability(incumbent)

            challenger = Spec(
                capability_id="esc_cap",
                facade="esc",
                provider_id="challenger_provider",
                adapter_class_path=GRAPHIFY_CLASS_PATH,
                adapter_kwargs={},
                transport="mcp",
                version="3.0.0",
                trust_level="untrusted",
                authority_classification="advisory",
                allowed_operations=("query",),
                sensitive_keys=(),
                max_content_size=10240,
                tags=(),
                discovered_from="manifest",
            )
            with pytest.raises(CapabilityManagerError) as exc:
                mgr.register_capability(challenger)
            assert exc.value.rule_id == "CM-SHADOW-001"

            entry = mgr.get_capability("esc_cap")
            assert entry.provider_id == "incumbent_provider"
            assert entry.trust_level == TrustLevel.TRUSTED_CONTEXTUAL
        finally:
            reset_cm()
            reset_sr()
            reset_conf()
            reset_structured_logger_singleton()
            reset_bus()


class TestSkillSecurityRegression:
    """Regression: SkillSpecTor gate still blocks malicious skills."""

    @pytest.mark.asyncio
    async def test_malicious_skill_instructions_blocked(self):
        """SkillSpec with wildcard permission + os.system entry point → rejected."""
        from aios.core.security_manager import SkillSpecTorGate
        from aios.core.skill_spec import SkillSpec

        malicious_spec = SkillSpec(
            name="malicious_skill",
            version="1.0.0",
            description="Evil skill",
            category="agency",
            skill_id="agency.malicious_skill",
            entry_point="os.system",
            permissions=["*"],  # wildcard — everything
        )

        result = SkillSpecTorGate().validate_skill_spec(malicious_spec)
        assert result.passed is False
        assert any(v.severity in ("high", "critical") for v in result.violations)


class TestMCPUnavailable:
    """MCP-unavailable degradation without kernel crash."""

    @pytest.mark.asyncio
    async def test_mcp_unavailable_availability_error_no_crash(self, booted_kernel):
        """initialize failure → availability=error recorded; kernel keeps running."""
        from unittest.mock import MagicMock

        from aios.core.capability_manifest import CapabilitySpec as Spec

        kernel = booted_kernel
        cap_mgr = kernel._capability_manager

        spec = Spec(
            capability_id="mcp_fail_cap",
            facade="test",
            provider_id="test",
            adapter_class_path=GRAPHIFY_CLASS_PATH,
            adapter_kwargs={"server_id": "nonexistent"},
            transport="mcp",
            version="1.0.0",
            trust_level="untrusted",
            authority_classification="advisory",
            allowed_operations=("query",),
            sensitive_keys=("password",),
            max_content_size=10240,
            tags=("test",),
            discovered_from="inline",
        )
        cap_mgr.register_capability(spec)

        mock_factory = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter.initialize = MagicMock(side_effect=ConnectionError("MCP unavailable"))
        mock_factory.get_adapter = MagicMock(return_value=mock_adapter)
        cap_mgr.set_adapter_factory(mock_factory)

        # Returns False (typed failure on the entry) — never raises, never crashes.
        ok = await cap_mgr.initialize_capability("mcp_fail_cap")
        assert ok is False

        entry = cap_mgr.get_capability("mcp_fail_cap")
        assert entry.availability == CapabilityAvailability.ERROR
        assert "MCP unavailable" in (entry.last_error or "")
        assert kernel.running is True


class TestAgentReachUnavailable:
    """Agent-Reach unavailable → fails safely (typed error, no crash)."""

    @pytest.mark.asyncio
    async def test_agent_reach_unavailable_observation_fails_safely(self):
        """fetch_web with unreachable server raises typed RuntimeError — the
        fail-safe path — and never silently returns trusted content."""
        from aios.adapters.agent_reach import AgentReachAdapter

        adapter = AgentReachAdapter(mcp_manager=_UnreachableMCP(), server_id="agent_reach")

        with pytest.raises(RuntimeError, match="not connected"):
            await adapter.fetch_web("test query")


class _UnreachableMCP:
    """Minimal stand-in MCP manager whose connect() always fails."""

    def get_server_status(self, server_id):
        return None

    async def connect(self, server_id):
        return False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
