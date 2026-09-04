"""Configuration loader for AI-OS.

This module handles loading YAML configuration files, merging configurations,
and providing useful error messages.
"""

import os
from pathlib import Path
from typing import Any

import yaml

from aios.config.defaults import (
    DEFAULT_APP_YAML,
    DEFAULT_CONFIG,
    DEFAULT_LOGS,
    DEFAULT_NAME,
    DEFAULT_VERSION,
    DEFAULT_WORKSPACE,
    Environment,
)
from aios.config.models import AppConfig, LogsConfig, WorkspaceConfig


class ConfigLoadError(Exception):
    """Raised when configuration loading fails.

    Attributes:
        path: Path to the configuration file that failed to load.
        reason: Human-readable error reason.
    """

    def __init__(self, path: Path, reason: str, original_error: Exception | None = None):
        self.path = path
        self.reason = reason
        self.original_error = original_error
        message = f"Failed to load config from {path}: {reason}"
        if original_error:
            message += f" ({original_error})"
        super().__init__(message)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a YAML file safely.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed YAML content as dictionary.

    Raises:
        ConfigLoadError: If file not found, not readable, or invalid YAML.
    """
    if not path.exists():
        raise ConfigLoadError(path, "File not found")

    if not path.is_file():
        raise ConfigLoadError(path, "Path is not a file")

    try:
        with path.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigLoadError(path, "Invalid YAML syntax", e)
    except OSError as e:
        raise ConfigLoadError(path, "File read error", e)

    if content is None:
        return {}

    if not isinstance(content, dict):
        raise ConfigLoadError(path, "YAML root must be a mapping (dictionary)")

    return content


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary (will be mutated).
        override: Dictionary with values to override.

    Returns:
        Merged dictionary (base is modified and returned).
    """
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _merge_dicts(base[key], value)
        else:
            base[key] = value
    return base


def _get_env_overrides() -> dict[str, Any]:
    """Get configuration overrides from environment variables.

    Environment variables should be prefixed with AIOS_ and use
    double underscore for nested keys (e.g., AIOS_WORKSPACE__PATH).

    Returns:
        Dictionary of configuration overrides.
    """
    overrides: dict[str, Any] = {}
    prefix = "AIOS_"

    for key, value in os.environ.items():
        if key.startswith(prefix):
            # Remove prefix and split by double underscore
            config_key = key[len(prefix):].lower()
            parts = config_key.split("__")

            # Build nested dict
            current = overrides
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value

    return overrides


def _apply_env_overrides(config: dict[str, Any]) -> dict[str, Any]:
    """Apply environment variable overrides to configuration.

    Args:
        config: Base configuration dictionary.

    Returns:
        Configuration with environment overrides applied.
    """
    overrides = _get_env_overrides()
    return _merge_dicts(config, overrides)


def _dict_to_app_config(config_dict: dict[str, Any]) -> AppConfig:
    """Convert a configuration dictionary to AppConfig model.

    Args:
        config_dict: Dictionary with configuration values.

    Returns:
        Validated AppConfig instance.
    """
    # Extract nested configurations
    workspace_value = config_dict.pop("workspace", {})
    logs_value = config_dict.pop("logs", {})
    obsidian_value = config_dict.pop("obsidian", {})
    notion_value = config_dict.pop("notion", {})
    claude_mem_value = config_dict.pop("claude_mem", {})

    # Backwards-compat: allow bare strings (e.g. `workspace: ./workspace`)
    # by coercing them into the nested mapping the Pydantic models expect.
    workspace_dict = (
        {"path": workspace_value} if isinstance(workspace_value, str) else workspace_value
    )
    logs_dict = (
        {"path": logs_value} if isinstance(logs_value, str) else logs_value
    )

    # Create sub-configs with defaults
    workspace = WorkspaceConfig(**workspace_dict) if workspace_dict else WorkspaceConfig()
    logs = LogsConfig(**logs_dict) if logs_dict else LogsConfig()
    obsidian = ObsidianConfig(**obsidian_value) if obsidian_value else ObsidianConfig()
    notion = NotionConfig(**notion_value) if notion_value else NotionConfig()
    claude_mem = ClaudeMemConfig(**claude_mem_value) if claude_mem_value else ClaudeMemConfig()

    # Create main config
    return AppConfig(
        workspace=workspace,
        logs=logs,
        obsidian=obsidian,
        notion=notion,
        claude_mem=claude_mem,
        **config_dict,
    )


def load_config(path: Path | str | None = None) -> AppConfig:
    """Load and validate configuration.

    This function loads configuration in the following order:
    1. Default values (from defaults module)
    2. App YAML file (required)
    3. Environment-specific YAML file (e.g., app.production.yaml)
    4. Environment variable overrides (AIOS_*)

    Args:
        path: Path to the main configuration file (default: ./config/app.yaml).
              If None, uses DEFAULT_APP_YAML.

    Returns:
        Validated AppConfig instance with all settings resolved.

    Raises:
        ConfigLoadError: If required config file not found or invalid.
        ConfigValidationError: If configuration validation fails.
    """
    target_path = Path(path) if path else DEFAULT_APP_YAML

    # Load default configuration
    config_data: dict[str, Any] = {
        "name": DEFAULT_NAME,
        "version": DEFAULT_VERSION,
        "environment": Environment.DEVELOPMENT.value,
        "config": str(DEFAULT_CONFIG),
    }

    # Load main app.yaml (required)
    app_config = _load_yaml_file(target_path)
    _merge_dicts(config_data, app_config)

    # Try to load environment-specific config
    env = config_data.get("environment", Environment.DEVELOPMENT.value)
    env_filename = f"app.{env}.yaml"
    env_path = target_path.parent / env_filename
    if env_path.exists() and env_path != target_path:
        env_config = _load_yaml_file(env_path)
        _merge_dicts(config_data, env_config)

    # Apply environment variable overrides
    config_data = _apply_env_overrides(config_data)

    # Convert to Pydantic model
    return _dict_to_app_config(config_data)


def load_config_or_default(path: Path | str | None = None) -> AppConfig:
    """Load configuration or return default if file doesn't exist.

    Unlike load_config(), this function will not raise an error if the
    configuration file is not found. Instead, it returns a configuration
    with all default values.

    Args:
        path: Path to the configuration file (default: ./config/app.yaml).

    Returns:
        AppConfig instance (loaded or default).
    """
    target_path = Path(path) if path else DEFAULT_APP_YAML

    if not target_path.exists():
        return AppConfig()

    return load_config(target_path)


def create_default_config(path: Path | None = None) -> Path:
    """Create a default configuration file at the specified path.

    Args:
        path: Path where to create the config file (default: ./config/app.yaml).

    Returns:
        Path to the created configuration file.
    """
    target_path = Path(path) if path else DEFAULT_APP_YAML

    # Ensure parent directory exists
    target_path.parent.mkdir(parents=True, exist_ok=True)

    # Default configuration
    config_data = {
        "name": DEFAULT_NAME,
        "version": DEFAULT_VERSION,
        "environment": Environment.DEVELOPMENT.value,
        "workspace": "./workspace",
        "logs": "./logs",
        "config": "./config",
    }

    with target_path.open("w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    return target_path


__all__ = [
    "ConfigLoadError",
    "load_config",
    "load_config_or_default",
    "create_default_config",
]
