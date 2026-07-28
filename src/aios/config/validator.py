"""Configuration validator for AI-OS.

This module provides validation logic for configuration values,
including path validation, required fields, and cross-field consistency.
"""

import re
import sys
from pathlib import Path
from typing import Any

from aios.config.defaults import (
    DEFAULT_APP_YAML,
    DEFAULT_CONFIG,
    DEFAULT_LOGS,
    DEFAULT_WORKSPACE,
    MIN_PYTHON_VERSION,
    VERSION_PATTERN,
)
from aios.config.models import AppConfig, Environment


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    def __init__(self, errors: list[str], config_path: Path | None = None):
        self.errors = errors
        self.config_path = config_path
        message = "Configuration validation failed:\n" + "\n".join(
            f"  - {error}" for error in errors
        )
        if config_path:
            message = f"Config file: {config_path}\n{message}"
        super().__init__(message)


def validate_python_version() -> None:
    """Validate that Python version meets minimum requirement.

    Raises:
        ConfigValidationError: If Python version is too old.
    """
    if sys.version_info < MIN_PYTHON_VERSION:
        raise ConfigValidationError(
            [f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required, "
             f"found {sys.version_info.major}.{sys.version_info.minor}"],
            config_path=None,
        )


def _resolve_path(path: Path, base_dir: Path) -> Path:
    """Resolve a path relative to the base directory."""
    if path.is_absolute():
        return path.resolve()
    return (base_dir / path).resolve()


def _check_path_writable(path: Path, create: bool = True) -> list[str]:
    """Check if a path is writable or can be created.

    Args:
        path: Path to check.
        create: Whether to attempt creating the directory.

    Returns:
        List of error messages (empty if writable).
    """
    errors: list[str] = []

    try:
        if create:
            path.mkdir(parents=True, exist_ok=True)
        # Test write permission
        test_file = path / ".aios_write_test"
        test_file.touch()
        test_file.unlink()
    except (OSError, PermissionError) as e:
        errors.append(f"Path not writable: {path} ({e})")

    return errors


def validate_config(config: AppConfig, config_path: Path | None = None) -> AppConfig:
    """Validate a complete AppConfig instance.

    Performs:
    - Python version check
    - Version format validation
    - Path resolution and writability checks
    - Environment-specific validation

    Args:
        config: The configuration to validate.
        config_path: Optional path to the config file (for error reporting and path resolution).

    Returns:
        The validated configuration with resolved absolute paths.

    Raises:
        ConfigValidationError: If validation fails.
    """
    errors: list[str] = []

    # Validate Python version
    try:
        validate_python_version()
    except ConfigValidationError as e:
        errors.extend(e.errors)

    # Validate version format
    if not re.match(VERSION_PATTERN, config.version):
        errors.append(
            f"version: '{config.version}' does not match semantic versioning pattern "
            f"(MAJOR.MINOR.PATCH)"
        )

    # Resolve base directory for relative paths
    base_dir = config_path.parent if config_path else Path.cwd()

    # Resolve and validate workspace path
    workspace_path = _resolve_path(config.workspace.path, base_dir)
    errors.extend(_check_path_writable(workspace_path, config.workspace.auto_create))

    # Resolve and validate logs path
    logs_path = _resolve_path(config.logs.path, base_dir)
    errors.extend(_check_path_writable(logs_path, config.logs.auto_create))

    # Resolve and validate config path
    config_path_resolved = _resolve_path(config.config, base_dir)
    if not config_path_resolved.exists():
        errors.append(f"config: Config directory does not exist: {config_path_resolved}")
    elif not config_path_resolved.is_dir():
        errors.append(f"config: Config path is not a directory: {config_path_resolved}")

    # Environment-specific validation
    if config.environment == Environment.PRODUCTION:
        if not workspace_path.exists():
            errors.append("workspace: Must exist in production environment")
        if not logs_path.exists():
            errors.append("logs: Must exist in production environment")

    if errors:
        raise ConfigValidationError(errors, config_path)

    # Return validated config with resolved absolute paths
    return AppConfig(
        name=config.name,
        version=config.version,
        environment=config.environment,
        workspace=config.workspace.model_copy(update={"path": workspace_path}),
        logs=config.logs.model_copy(update={"path": logs_path}),
        config=config_path_resolved,
    )


def validate_config_file(config_path: Path) -> AppConfig:
    """Load and validate a configuration file.

    Convenience function that combines loading and validation.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Validated AppConfig instance.

    Raises:
        ConfigValidationError: If file not found, YAML invalid, or validation fails.
        ConfigLoadError: If loading fails.
    """
    from aios.config.loader import load_config

    config = load_config(config_path)
    return validate_config(config, config_path)


__all__ = [
    "ConfigValidationError",
    "validate_config",
    "validate_config_file",
    "validate_python_version",
]