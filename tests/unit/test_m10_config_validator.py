"""
Unit tests for M10-T8 Configuration Validator.

Tests the existing implementation in src/aios/config/validator.py
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from aios.config.validator import (
    ConfigValidationError,
    validate_config,
    validate_config_file,
    validate_python_version,
)
from aios.config.models import AppConfig, Environment
from aios.config.defaults import (
    DEFAULT_NAME,
    DEFAULT_VERSION,
    DEFAULT_WORKSPACE,
    DEFAULT_LOGS,
    DEFAULT_CONFIG,
    MIN_PYTHON_VERSION,
)


class TestConfigValidationError:
    """Test ConfigValidationError exception behavior."""

    def test_init_with_errors_only(self):
        """Test ConfigValidationError initialization with errors list only."""
        errors = ["Error 1", "Error 2"]
        exc = ConfigValidationError(errors)

        assert exc.errors == errors
        assert exc.config_path is None
        assert "Configuration validation failed:" in str(exc)
        assert "Error 1" in str(exc)
        assert "Error 2" in str(exc)

    def test_init_with_errors_and_config_path(self):
        """Test ConfigValidationError initialization with errors and config path."""
        errors = ["Error 1"]
        config_path = Path("/test/config.yaml")
        exc = ConfigValidationError(errors, config_path)

        assert exc.errors == errors
        assert exc.config_path == config_path
        assert f"Config file: {config_path}" in str(exc)
        assert "Configuration validation failed:" in str(exc)
        assert "Error 1" in str(exc)


class TestValidatePythonVersion:
    """Test validate_python_version function."""

    def test_valid_python_version_passes(self):
        """Test that valid Python version passes without raising."""
        # Current test environment should have Python 3.12+
        # which meets the minimum requirement
        try:
            validate_python_version()
        except ConfigValidationError:
            pytest.fail("validate_python_version() raised ConfigValidationError unexpectedly")

    def test_invalid_python_version_raises(self):
        """Test that invalid Python version raises ConfigValidationError."""
        # Mock sys.version_info to simulate an old Python version
        # Create a proper tuple-like object for version_info
        class MockVersionInfo:
            def __init__(self, major, minor):
                self.major = major
                self.minor = minor

            def __lt__(self, other):
                return (self.major, self.minor) < (other[0], other[1])

            def __ge__(self, other):
                return (self.major, self.minor) >= (other[0], other[1])

        with patch('sys.version_info', MockVersionInfo(3, 10)):
            with pytest.raises(ConfigValidationError) as exc_info:
                validate_python_version()

            assert "Python 3.12+ required" in str(exc_info.value)
            assert "found 3.10" in str(exc_info.value)


class TestValidateConfig:
    """Test validate_config function."""

    def test_valid_config_passes(self):
        """Test that a valid AppConfig passes validation."""
        config = AppConfig(
            name="TestApp",
            version="1.0.0",
            environment=Environment.DEVELOPMENT,
        )

        # Should not raise
        result = validate_config(config)

        # Should return validated config with resolved paths
        assert isinstance(result, AppConfig)
        assert result.name == "TestApp"
        assert result.version == "1.0.0"
        assert result.environment == Environment.DEVELOPMENT

    def test_invalid_version_format_raises(self):
        """Test that invalid version format raises ConfigValidationError."""
        # Bypass Pydantic validation by creating object directly and setting invalid version
        config = AppConfig.model_construct(
            name="TestApp",
            version="invalid-version",  # Not semantic version
            environment=Environment.DEVELOPMENT,
            workspace=None,
            logs=None,
            config=None,
        )
        # Manually set the fields that would normally be set by constructors
        from aios.config.models import WorkspaceConfig, LogsConfig
        config.workspace = WorkspaceConfig()
        config.logs = LogsConfig()
        from aios.config.defaults import DEFAULT_CONFIG
        config.config = DEFAULT_CONFIG

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)

        assert "version:" in str(exc_info.value)
        assert "does not match semantic versioning pattern" in str(exc_info.value)

    def test_missing_required_fields_handled_by_pydantic(self):
        """Test that Pydantic handles missing required fields before validation."""
        # Pydantic validation happens first, so we test what gets through to our validator
        # Let's test with valid Pydantic fields but invalid values that our validator catches

        # Test empty name (should be caught by Pydantic field validator)
        with pytest.raises(Exception):  # Pydantic ValidationError
            AppConfig(
                name="",  # Empty name
                version="1.0.0",
                environment=Environment.DEVELOPMENT,
            )

        # Test empty version (should be caught by Pydantic field validator)
        with pytest.raises(Exception):  # Pydantic ValidationError
            AppConfig(
                name="TestApp",
                version="",  # Empty version
                environment=Environment.DEVELOPMENT,
            )

    def test_production_environment_path_validation(self, tmp_path):
        """Test that production environment validates path existence."""
        # Create a config pointing to non-existent paths in production
        nonexistent_workspace = tmp_path / "nonexistent_workspace"
        nonexistent_logs = tmp_path / "nonexistent_logs"

        # Use model_construct to bypass some Pydantic validation, then set paths manually
        config = AppConfig.model_construct(
            name="TestApp",
            version="1.0.0",
            environment=Environment.PRODUCTION,
            workspace=None,
            logs=None,
            config=None,
        )
        # Manually set the fields
        from aios.config.models import WorkspaceConfig, LogsConfig
        config.workspace = WorkspaceConfig(path=nonexistent_workspace, auto_create=False)
        config.logs = LogsConfig(path=nonexistent_logs, auto_create=False)
        from aios.config.defaults import DEFAULT_CONFIG
        config.config = DEFAULT_CONFIG

        # This should fail because paths don't exist in production
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)

        error_str = str(exc_info.value)
        assert "workspace: Must exist in production environment" in error_str
        assert "logs: Must exist in production environment" in error_str

    def test_path_resolution_and_writability(self, tmp_path):
        """Test that paths are resolved and writability is checked."""
        # Create a valid config with relative paths
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        # Also create the config directory that the config path points to
        (config_dir / "config").mkdir()

        # Use model_construct to bypass Pydantic validation issues
        config = AppConfig.model_construct(
            name="TestApp",
            version="1.0.0",
            environment=Environment.DEVELOPMENT,
            workspace=None,
            logs=None,
            config=None,
        )
        # Manually set the fields with relative paths
        from aios.config.models import WorkspaceConfig, LogsConfig
        config.workspace = WorkspaceConfig(path=Path("workspace"), auto_create=True)
        config.logs = LogsConfig(path=Path("logs"), auto_create=True)
        config.config = Path("config")

        # Should pass validation and return resolved paths
        result = validate_config(config, config_path=config_dir / "app.yaml")

        assert isinstance(result, AppConfig)
        assert result.workspace.path.is_absolute()
        assert result.logs.path.is_absolute()
        assert result.config.is_absolute()

    def test_nonexistent_config_directory_raises(self, tmp_path):
        """Test that nonexistent config directory raises validation error."""
        nonexistent_config = tmp_path / "nonexistent_config"

        # Use model_construct to bypass Pydantic validation
        config = AppConfig.model_construct(
            name="TestApp",
            version="1.0.0",
            environment=Environment.DEVELOPMENT,
            workspace=None,
            logs=None,
            config=None,
        )
        # Manually set the fields
        from aios.config.models import WorkspaceConfig, LogsConfig
        config.workspace = WorkspaceConfig()
        config.logs = LogsConfig()
        config.config = nonexistent_config

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)

        assert "Config directory does not exist:" in str(exc_info.value)
        assert str(nonexistent_config) in str(exc_info.value)

    def test_config_path_is_file_not_directory_raises(self, tmp_path):
        """Test that config path being a file (not directory) raises validation error."""
        config_file = tmp_path / "config.txt"
        config_file.write_text("not a directory")

        # Use model_construct to bypass Pydantic validation
        config = AppConfig.model_construct(
            name="TestApp",
            version="1.0.0",
            environment=Environment.DEVELOPMENT,
            workspace=None,
            logs=None,
            config=None,
        )
        # Manually set the fields
        from aios.config.models import WorkspaceConfig, LogsConfig
        config.workspace = WorkspaceConfig()
        config.logs = LogsConfig()
        config.config = config_file

        with pytest.raises(ConfigValidationError) as exc_info:
            validate_config(config)

        assert "Config path is not a directory:" in str(exc_info.value)
        assert str(config_file) in str(exc_info.value)


class TestValidateConfigFile:
    """Test validate_config_file function."""

    def test_nonexistent_file_raises(self):
        """Test that nonexistent file raises appropriate error."""
        nonexistent_file = Path("/nonexistent/path/app.yaml")

        with pytest.raises(Exception) as exc_info:  # Could be ConfigValidationError or ConfigLoadError
            validate_config_file(nonexistent_file)

        # Should indicate file not found or loading issue
        assert "not found" in str(exc_info.value).lower() or "no such file" in str(exc_info.value).lower()

    def test_malformed_yaml_raises(self, tmp_path):
        """Test that malformed YAML raises appropriate error."""
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("invalid: yaml: content: [")

        with pytest.raises(Exception) as exc_info:  # Could be ConfigValidationError or ConfigLoadError
            validate_config_file(config_file)

        # Should indicate YAML parsing issue
        assert "yaml" in str(exc_info.value).lower() or "invalid" in str(exc_info.value).lower()