"""AI-OS Configuration System.

This package provides configuration loading, validation, and management
for the AI-OS platform.
"""

from aios.config.defaults import (
    DEFAULT_APP_YAML,
    DEFAULT_CONFIG,
    DEFAULT_LOGS,
    DEFAULT_NAME,
    DEFAULT_VERSION,
    DEFAULT_WORKSPACE,
    Environment,
)
from aios.config.loader import ConfigLoadError, load_config, load_config_or_default, create_default_config
from aios.config.models import AppConfig, Environment, WorkspaceConfig, LogsConfig
from aios.config.validator import ConfigValidationError, validate_config, validate_config_file, validate_python_version

__all__ = [
    "DEFAULT_APP_YAML",
    "DEFAULT_CONFIG",
    "DEFAULT_LOGS",
    "DEFAULT_NAME",
    "DEFAULT_VERSION",
    "DEFAULT_WORKSPACE",
    "Environment",
    "AppConfig",
    "WorkspaceConfig",
    "LogsConfig",
    "ConfigLoadError",
    "ConfigValidationError",
    "load_config",
    "load_config_or_default",
    "create_default_config",
    "validate_config",
    "validate_config_file",
    "validate_python_version",
]

__version__ = "0.1.0"

