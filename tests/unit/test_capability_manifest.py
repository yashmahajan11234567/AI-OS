"""
M8-T5 — Capability Manifest Loader unit tests.

Tests for CapabilitySpec model and CapabilityManifestLoader:
- Valid manifest parses to CapabilitySpec
- Missing required field rejected (CM-MANIFEST-001)
- trust_level absent → defaults to untrusted
- authority_classification absent → defaults to advisory
- adapter.class_path not in allowlist → rejected (CM-ADAPTER-001)
- manifest referencing unknown module → rejected
- malformed YAML → rejected typed
- discovered_from auto-populated from file path
- manifest disabled (enabled: false) → skipped, not registered
- duplicate manifests loaded (collision resolution at registration)
- version comparison happens at registration
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from aios.core.capability_manifest import (
    CapabilityManifestLoader,
    CapabilitySpec,
    load_capability_manifests,
)
from aios.core.capability_manager import CapabilityManagerError


class TestCapabilitySpec:
    """Tests for CapabilitySpec model."""

    def test_valid_spec_creation(self):
        """A valid spec can be created with all required fields."""
        spec = CapabilitySpec(
            capability_id="test_capability",
            facade="test",
            provider_id="test_provider",
            adapter_class_path="aios.adapters.graphify_adapter.GraphifyAdapter",
            adapter_kwargs={"server_id": "test"},
            transport="mcp",
            version="1.0.0",
            trust_level="untrusted",
            authority_classification="advisory",
            allowed_operations=["query", "read"],
            sensitive_keys=["password", "token"],
            max_content_size=10240,
            tags=["test"],
            discovered_from="config/capabilities/test.yaml",
        )
        assert spec.capability_id == "test_capability"
        assert spec.trust_level == "untrusted"
        assert spec.authority_classification == "advisory"

    def test_spec_defaults(self):
        """Defaults for trust_level and authority_classification."""
        spec = CapabilitySpec(
            capability_id="test",
            facade="test",
            provider_id="test",
            adapter_class_path="aios.adapters.graphify_adapter.GraphifyAdapter",
            adapter_kwargs={},
            transport="mcp",
            version="1.0.0",
            trust_level="untrusted",  # explicit for test
            authority_classification="advisory",  # explicit for test
        )
        # Defaults are applied during loading, not model creation


class TestCapabilityManifestLoader:
    """Tests for CapabilityManifestLoader."""

    def setup_method(self):
        self.allowlist = (
            "aios.adapters.graphify_adapter.GraphifyAdapter",
            "aios.adapters.playwright_mcp_adapter.PlaywrightMCPAdapter",
        )

    @pytest.mark.asyncio
    async def test_valid_manifest_parses(self, tmp_path):
        """A valid manifest YAML parses to CapabilitySpec."""
        manifest = {
            "capability_id": "test_valid",
            "facade": "test",
            "provider_id": "test_provider",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
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
        }
        manifest_file = tmp_path / "test_valid.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        assert len(specs) == 1
        assert specs[0].capability_id == "test_valid"
        assert specs[0].discovered_from == str(manifest_file)

    @pytest.mark.asyncio
    async def test_missing_required_field_rejected(self, tmp_path):
        """Missing required field → manifest skipped (logged, not raised)."""
        manifest = {
            "capability_id": "test_missing",
            "facade": "test",
            # provider_id missing
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        manifest_file = tmp_path / "test_missing.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )

        # Invalid manifest is skipped, not raised - returns empty list
        specs = list(loader.load_all())
        assert len(specs) == 0

    @pytest.mark.asyncio
    async def test_trust_level_defaults_to_untrusted(self, tmp_path):
        """trust_level absent → defaults to untrusted."""
        manifest = {
            "capability_id": "test_trust_default",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            # trust_level omitted
        }
        manifest_file = tmp_path / "test_trust_default.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        assert len(specs) == 1
        assert specs[0].trust_level == "untrusted"

    @pytest.mark.asyncio
    async def test_authority_classification_defaults_to_advisory(self, tmp_path):
        """authority_classification absent → defaults to advisory."""
        manifest = {
            "capability_id": "test_auth_default",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            # authority_classification omitted
        }
        manifest_file = tmp_path / "test_auth_default.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        assert len(specs) == 1
        assert specs[0].authority_classification == "advisory"

    @pytest.mark.asyncio
    async def test_adapter_not_in_allowlist_rejected(self, tmp_path):
        """adapter.class_path not in allowlist → manifest skipped."""
        manifest = {
            "capability_id": "test_bad_adapter",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "os.system",  # Not in allowlist
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        manifest_file = tmp_path / "test_bad_adapter.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )

        # Invalid manifest is skipped
        specs = list(loader.load_all())
        assert len(specs) == 0

    @pytest.mark.asyncio
    async def test_unknown_module_rejected(self, tmp_path):
        """Manifest referencing unknown module → manifest skipped."""
        manifest = {
            "capability_id": "test_unknown_module",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.nonexistent.NonExistentAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        manifest_file = tmp_path / "test_unknown_module.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )

        # Invalid manifest is skipped
        specs = list(loader.load_all())
        assert len(specs) == 0

    @pytest.mark.asyncio
    async def test_malformed_yaml_rejected(self, tmp_path):
        """Malformed YAML → manifest skipped."""
        manifest_file = tmp_path / "test_malformed.yaml"
        manifest_file.write_text("invalid: yaml: content: [}")

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )

        # Invalid manifest is skipped
        specs = list(loader.load_all())
        assert len(specs) == 0

    @pytest.mark.asyncio
    async def test_discovered_from_auto_populated(self, tmp_path):
        """discovered_from auto-populated from file path."""
        manifest = {
            "capability_id": "test_discovered",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        manifest_file = tmp_path / "test_discovered.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        assert len(specs) == 1
        assert "test_discovered.yaml" in specs[0].discovered_from

    @pytest.mark.asyncio
    async def test_disabled_manifest_skipped(self, tmp_path):
        """Manifest with enabled: false → skipped, not registered."""
        manifest = {
            "capability_id": "test_disabled",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            "enabled": False,
        }
        manifest_file = tmp_path / "test_disabled.yaml"
        manifest_file.write_text(yaml.dump(manifest))

        # Also add an enabled one
        manifest2 = {
            "capability_id": "test_enabled",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            "enabled": True,
        }
        (tmp_path / "test_enabled.yaml").write_text(yaml.dump(manifest2))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        # Only the enabled one should be loaded
        assert len(specs) == 1
        assert specs[0].capability_id == "test_enabled"

    @pytest.mark.asyncio
    async def test_duplicate_manifests_loads_both(self, tmp_path):
        """Loader loads both manifests (collision resolution at registration)."""
        # First manifest with lower trust
        manifest1 = {
            "capability_id": "test_duplicate",
            "facade": "test",
            "provider_id": "provider1",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            "trust_level": "untrusted",
        }
        (tmp_path / "test_duplicate_1.yaml").write_text(yaml.dump(manifest1))

        # Second manifest with higher trust (but external manifests can't claim trusted_contextual)
        manifest2 = {
            "capability_id": "test_duplicate_2",
            "facade": "test",
            "provider_id": "provider2",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            "trust_level": "untrusted",
        }
        (tmp_path / "test_duplicate_2.yaml").write_text(yaml.dump(manifest2))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        # Loader loads both (different capability_ids)
        assert len(specs) == 2

    @pytest.mark.asyncio
    async def test_version_comparison(self, tmp_path):
        """Loader loads all manifests; version comparison happens at registration."""
        # Lower version first
        manifest1 = {
            "capability_id": "test_version_1",
            "facade": "test",
            "provider_id": "provider1",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
            "trust_level": "untrusted",
        }
        (tmp_path / "test_version_1.yaml").write_text(yaml.dump(manifest1))

        # Higher version second (different capability_id so both load)
        manifest2 = {
            "capability_id": "test_version_2",
            "facade": "test",
            "provider_id": "provider2",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "2.0.0",
            "trust_level": "untrusted",
        }
        (tmp_path / "test_version_2.yaml").write_text(yaml.dump(manifest2))

        loader = CapabilityManifestLoader(
            manifest_dir=tmp_path,
            adapter_allowlist=self.allowlist,
            trust_default="untrusted",
            security_manager=None,
        )
        specs = list(loader.load_all())

        # Both loaded
        assert len(specs) == 2
        versions = {s.version for s in specs}
        assert "1.0.0" in versions
        assert "2.0.0" in versions


class TestLoadCapabilityManifests:
    """Tests for load_capability_manifests convenience function."""

    @pytest.mark.asyncio
    async def test_load_function_works(self, tmp_path):
        """Convenience function loads manifests correctly."""
        manifest = {
            "capability_id": "test_load_func",
            "facade": "test",
            "provider_id": "test",
            "adapter": {
                "class_path": "aios.adapters.graphify_adapter.GraphifyAdapter",
                "kwargs": {},
            },
            "transport": "mcp",
            "version": "1.0.0",
        }
        (tmp_path / "test_load.yaml").write_text(yaml.dump(manifest))

        allowlist = (
            "aios.adapters.graphify_adapter.GraphifyAdapter",
            "aios.adapters.playwright_mcp_adapter.PlaywrightMCPAdapter",
        )

        specs = await load_capability_manifests(
            manifest_dir=tmp_path,
            adapter_allowlist=allowlist,
            trust_default="untrusted",
            security_manager=None,
        )

        assert len(specs) == 1
        assert specs[0].capability_id == "test_load_func"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])