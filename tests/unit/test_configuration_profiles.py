"""
M10 Deployment/Configuration Foundation Tests

Tests for:
- Environment profile configuration files (development, test, production)
- Four-layer configuration precedence
- Secret redaction in inspection views
- Startup validation
- Configuration layer inspection
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

import pytest

from aios.core.configuration_manager import (
    ConfigurationError,
    ConfigurationFrozenError,
    ConfigState,
    KernelConfigSchema,
    _deep_merge,
    _EMBEDDED_DEFAULTS,
    get_configuration_manager,
    reset_configuration_manager_singleton,
)
from aios.events.core import EventBus, EventBusConfig


@pytest.fixture
def bus():
    b = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    return b


@pytest.fixture(autouse=True)
def _reset():
    reset_configuration_manager_singleton()
    yield
    reset_configuration_manager_singleton()


def _init_and_freeze(mgr, bus):
    async def _run():
        await bus.initialize()
        await mgr.initialize()
        mgr.freeze()
        await bus.drain()
    asyncio.run(_run())


def _seed_and_freeze(mgr, bus, merged):
    """Seed merged config and freeze directly."""
    with mgr._lock:
        mgr._merged = merged
    mgr.freeze()
    # Need to drain the bus
    asyncio.run(bus.drain())


class TestEnvironmentProfiles:
    """Test environment profile configuration loading."""

    def test_development_profile_exists(self):
        """Verify development.yaml exists and is valid YAML."""
        path = Path("config/env/development.yaml")
        assert path.exists(), "config/env/development.yaml should exist"
        import yaml
        with open(path) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert config.get("kernel", {}).get("environment") == "development"
        assert config.get("kernel", {}).get("log_level") == "DEBUG"

    def test_test_profile_exists(self):
        """Verify test.yaml exists and is valid YAML."""
        path = Path("config/env/test.yaml")
        assert path.exists(), "config/env/test.yaml should exist"
        import yaml
        with open(path) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert config.get("kernel", {}).get("environment") == "test"
        assert config.get("kernel", {}).get("log_level") == "WARNING"

    def test_production_profile_exists(self):
        """Verify production.yaml exists and is valid YAML."""
        path = Path("config/env/production.yaml")
        assert path.exists(), "config/env/production.yaml should exist"
        import yaml
        with open(path) as f:
            config = yaml.safe_load(f)
        assert config is not None
        assert config.get("kernel", {}).get("environment") == "production"
        assert config.get("kernel", {}).get("log_level") == "INFO"

    def test_all_profiles_have_required_sections(self):
        """All profiles should have kernel, services, and security sections."""
        for profile in ["development.yaml", "test.yaml", "production.yaml"]:
            path = Path(f"config/env/{profile}")
            import yaml
            with open(path) as f:
                config = yaml.safe_load(f)
            assert "kernel" in config, f"{profile} missing kernel section"
            assert "services" in config, f"{profile} missing services section"
            assert "security" in config, f"{profile} missing security section"


class TestConfigurationPrecedence:
    """Test four-layer configuration precedence."""

    def test_layer_precedence_basic(self):
        """Layer 4 (env vars) > Layer 3 (env.yaml) > Layer 2 (app.yaml) > Layer 1 (defaults)."""
        base = {"kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"}}
        layer2 = {"kernel": {"logLevel": "WARNING"}}
        layer3 = {"kernel": {"logLevel": "DEBUG"}}
        layer4 = {"kernel": {"logLevel": "ERROR"}}

        merged = _deep_merge(base, layer2)
        merged = _deep_merge(merged, layer3)
        merged = _deep_merge(merged, layer4)

        assert merged["kernel"]["logLevel"] == "ERROR"

    def test_env_var_overrides_yaml(self, monkeypatch, bus):
        """AIOS_ env vars should override app.yaml and env.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            app_yaml = tmpdir / "app.yaml"
            app_yaml.write_text("kernel:\n  name: AppName\n  environment: test\n  logLevel: INFO\n")
            env_yaml = tmpdir / "app.test.yaml"
            env_yaml.write_text("kernel:\n  logLevel: DEBUG\n")

            monkeypatch.setenv("AIOS_KERNEL_LOG_LEVEL", "CRITICAL")

            mgr = get_configuration_manager(event_bus=bus, config_path=app_yaml)
            _init_and_freeze(mgr, bus)

            assert mgr.get("kernel.logLevel") == "CRITICAL"
            assert mgr.get("kernel.name") == "AppName"
            assert mgr.get("kernel.environment") == "test"

    def test_env_yaml_overrides_app_yaml(self, bus):
        """env.yaml (Layer 3) should override app.yaml (Layer 2)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            app_yaml = tmpdir / "app.yaml"
            app_yaml.write_text("kernel:\n  name: AppName\n  environment: staging\n  logLevel: INFO\n")
            env_yaml = tmpdir / "app.staging.yaml"
            env_yaml.write_text("kernel:\n  logLevel: WARNING\n")

            mgr = get_configuration_manager(event_bus=bus, config_path=app_yaml)
            _init_and_freeze(mgr, bus)

            assert mgr.get("kernel.logLevel") == "WARNING"
            assert mgr.get("kernel.name") == "AppName"

    def test_defaults_as_baseline(self):
        """Embedded defaults should provide baseline for all required fields."""
        assert "kernel" in _EMBEDDED_DEFAULTS
        assert "name" in _EMBEDDED_DEFAULTS["kernel"]
        assert "version" in _EMBEDDED_DEFAULTS["kernel"]
        assert "logLevel" in _EMBEDDED_DEFAULTS["kernel"]


class TestSecretRedaction:
    """Test secret detection and redaction in configuration views."""

    def test_secret_masking_in_get_all(self, bus):
        """Secrets should be masked in get_all() output."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "super-secret-value"},
            "llm": {"providers": {"openai": {"apiKey": "sk-12345"}}},
        })
        allcfg = mgr.get_all()
        assert allcfg["security"]["jwtSecret"] == "***"
        assert allcfg["llm"]["providers"]["openai"]["apiKey"] == "***"

    def test_secret_masking_in_get_section(self, bus):
        """Secrets should be masked in get_section() output."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "topsecret", "other": "value"},
        })
        section = mgr.get_section("security")
        assert section["jwtSecret"] == "***"
        assert section["other"] == "value"

    def test_secret_masking_in_inspect(self, bus):
        """inspect() should mask secrets by default."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "inspect-secret"},
        })
        result = mgr.inspect(include_secrets=False)
        assert result["config"]["security"]["jwtSecret"] == "***"

    def test_inspect_with_secrets_includes_raw(self, bus):
        """inspect(include_secrets=True) should include raw secret values."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "raw-secret-value"},
        })
        result = mgr.inspect(include_secrets=True)
        assert result["config"]["security"]["jwtSecret"] == "raw-secret-value"

    def test_redacted_view_masks_secrets_and_custom(self, bus):
        """redacted_view() should mask secrets and custom paths."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "secret1", "apiKey": "secret2"},
            "custom": {"sensitive": "value"},
        })
        redacted = mgr.redacted_view(paths=["custom.sensitive"])
        assert redacted["security"]["jwtSecret"] == "***"
        assert redacted["security"]["apiKey"] == "***"
        assert redacted["custom"]["sensitive"] == "***"
        assert redacted["kernel"]["name"] == "Hermes"

    def test_get_secret_returns_raw(self, bus):
        """get_secret() should return raw secret value."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "security": {"jwtSecret": "rawsecret"},
        })
        assert mgr.get_secret("security.jwtSecret") == "rawsecret"

    def test_git_secret_detection(self):
        """Test various secret key patterns are detected."""
        from aios.core.configuration_manager import is_secret_path
        assert is_secret_path(["security", "jwtSecret"])
        assert is_secret_path(["llm", "providers", "openai", "apiKey"])
        assert is_secret_path(["db", "password"])
        assert is_secret_path(["x", "authToken"])
        assert is_secret_path(["x", "dbCredential"])
        assert is_secret_path(["x", "clientSecret"])
        assert not is_secret_path(["kernel", "keyboard"])
        assert not is_secret_path(["kernel", "logLevel"])
        assert not is_secret_path(["ui", "keystone"])


class TestStartupValidation:
    """Test startup validation of required configuration."""

    def test_validate_startup_success(self, bus):
        """validate_startup should pass with complete configuration."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "configuration": {"freeze_on_initialize": True},
            "security": {"strict_mode": True},
            "capabilities": {"enabled": True},
            "services": {"autonomy": {"enabled": False}, "real_integration_enabled": False},
        })
        errors = mgr.validate_startup()
        assert len(errors) == 0

    def test_validate_startup_missing_kernel_name(self, bus):
        """validate_startup should fail if kernel.name is missing."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"version": "1.0.0", "logLevel": "INFO"},
            "configuration": {"freeze_on_initialize": True},
            "security": {"strict_mode": True},
            "capabilities": {"enabled": True},
        })
        errors = mgr.validate_startup()
        assert any("kernel.name" in e for e in errors)

    def test_validate_startup_missing_kernel_version(self, bus):
        """validate_startup should fail if kernel.version is missing."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "logLevel": "INFO"},
            "configuration": {"freeze_on_initialize": True},
            "security": {"strict_mode": True},
            "capabilities": {"enabled": True},
        })
        errors = mgr.validate_startup()
        assert any("kernel.version" in e for e in errors)

    def test_validate_startup_missing_log_level(self, bus):
        """validate_startup should fail if kernel.logLevel is missing."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0"},
            "configuration": {"freeze_on_initialize": True},
            "security": {"strict_mode": True},
            "capabilities": {"enabled": True},
        })
        errors = mgr.validate_startup()
        assert any("kernel.logLevel" in e for e in errors)

    def test_validate_startup_requires_freeze(self, bus):
        """validate_startup should require frozen configuration."""
        mgr = get_configuration_manager(event_bus=bus)
        mgr._state = ConfigState.INITIALIZING
        with pytest.raises(ConfigurationError):
            mgr.validate_startup()

    def test_validate_startup_warns_on_autonomy_enabled(self, bus, caplog):
        """validate_startup should warn if autonomy is enabled."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "configuration": {"freeze_on_initialize": True},
            "security": {"strict_mode": True},
            "capabilities": {"enabled": True},
            "services": {"autonomy": {"enabled": True}},
        })
        mgr.validate_startup()
        assert any("Autonomy services enabled" in r.message for r in caplog.records)


class TestConfigurationInspection:
    """Test configuration inspection and layer debugging."""

    def test_inspect_includes_metadata(self, bus):
        """inspect() should include metadata about layers and validation."""
        mgr = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
            "configuration": {"freeze_on_initialize": True},
            "security": {"strict_mode": True},
            "capabilities": {"enabled": True},
        })
        result = mgr.inspect(include_metadata=True)
        assert "metadata" in result
        assert "layer_sources" in result["metadata"]
        assert "precedence_order" in result["metadata"]
        assert "validation" in result["metadata"]

    def test_get_layer_1_defaults(self, bus):
        """get_layer(1) should return embedded defaults."""
        mgr = get_configuration_manager(event_bus=bus)
        layer = mgr.get_layer(1)
        assert layer is not None
        assert "kernel" in layer
        assert layer["kernel"]["name"] == "Hermes"

    def test_get_layer_2_app(self, bus, tmp_path):
        """get_layer(2) should return app.yaml config."""
        app_yaml = tmp_path / "app.yaml"
        app_yaml.write_text("kernel:\n  name: TestApp\n")
        mgr = get_configuration_manager(event_bus=bus, config_path=app_yaml)
        layer = mgr.get_layer(2)
        assert layer is not None
        assert layer.get("kernel", {}).get("name") == "TestApp"

    def test_get_layer_3_env(self, bus, tmp_path):
        """get_layer(3) should return env-specific config."""
        app_yaml = tmp_path / "app.yaml"
        app_yaml.write_text("kernel:\n  environment: test\n")
        env_yaml = tmp_path / "app.test.yaml"
        env_yaml.write_text("kernel:\n  logLevel: WARNING\n")
        mgr = get_configuration_manager(event_bus=bus, config_path=app_yaml)
        _init_and_freeze(mgr, bus)
        layer = mgr.get_layer(3)
        assert layer is not None
        assert layer.get("kernel", {}).get("logLevel") == "WARNING"

    def test_get_layer_4_env_vars(self, monkeypatch, bus):
        """get_layer(4) should return AIOS_* env var config."""
        monkeypatch.setenv("AIOS_KERNEL_LOG_LEVEL", "DEBUG")
        mgr = get_configuration_manager(event_bus=bus)
        layer = mgr.get_layer(4)
        assert layer is not None
        assert layer.get("kernel", {}).get("logLevel") == "DEBUG"


class TestDeterministicHash:
    """Test deterministic configuration hashing."""

    def test_identical_config_identical_hash(self, bus):
        """Identical configs should produce identical hashes."""
        mgr1 = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr1, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
        })
        h1 = mgr1.config_hash

        reset_configuration_manager_singleton()
        mgr2 = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr2, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
        })
        assert mgr2.config_hash == h1

    def test_changed_config_changed_hash(self, bus):
        """Changed configs should produce different hashes."""
        mgr1 = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr1, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "INFO"},
        })
        h1 = mgr1.config_hash

        reset_configuration_manager_singleton()
        mgr2 = get_configuration_manager(event_bus=bus)
        _seed_and_freeze(mgr2, bus, {
            "kernel": {"name": "Hermes", "version": "1.0.0", "logLevel": "WARNING"},
        })
        assert mgr2.config_hash != h1