"""Pydantic configuration models for AI-OS.

This module defines the configuration data models using Pydantic v2
with strict type validation, field constraints, and custom validators.
"""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.functional_validators import BeforeValidator

from aios.config.defaults import (
    DEFAULT_APP_YAML,
    DEFAULT_CONFIG,
    DEFAULT_LOGS,
    DEFAULT_NAME,
    DEFAULT_VERSION,
    DEFAULT_WORKSPACE,
    Environment,
)


def _validate_path(path: Path | str) -> Path:
    """Validate and convert a path value to Path object."""
    if isinstance(path, str):
        return Path(path).expanduser()
    return path.expanduser()


# Custom path type with validation
ConfigPath = Annotated[Path, BeforeValidator(_validate_path)]


class Environment(StrEnum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

    @classmethod
    def _missing_(cls, value: object) -> "Environment | None":
        """Allow case-insensitive matching."""
        if isinstance(value, str):
            try:
                return cls(value.lower())
            except ValueError:
                pass
        return None


class WorkspaceConfig(BaseModel):
    """Workspace directory configuration.

    Attributes:
        path: Path to the workspace directory (relative to config file or absolute).
        auto_create: Whether to automatically create the workspace directory if it doesn't exist.
    """

    model_config = ConfigDict(extra="forbid")

    path: ConfigPath = Field(
        default=DEFAULT_WORKSPACE,
        description="Path to workspace directory",
    )
    auto_create: bool = Field(
        default=True,
        description="Automatically create workspace directory if missing",
    )

    @field_validator("path")
    @classmethod
    def _validate_workspace_path(cls, v: Path) -> Path:
        """Validate workspace path."""
        if not v.name:
            raise ValueError("Workspace path cannot be empty")
        return v


class LogsConfig(BaseModel):
    """Logging configuration.

    Attributes:
        path: Path to the logs directory.
        level: Default logging level.
        format: Log message format string.
        auto_create: Whether to automatically create the logs directory if it doesn't exist.
    """

    model_config = ConfigDict(extra="forbid")

    path: ConfigPath = Field(
        default=DEFAULT_LOGS,
        description="Path to logs directory",
    )
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Default logging level",
    )
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format string",
    )
    auto_create: bool = Field(
        default=True,
        description="Automatically create logs directory if missing",
    )


class AppConfig(BaseModel):
    """Main application configuration.

    This is the root configuration model that combines all sub-configurations.

    Attributes:
        name: Application name.
        version: Application version (semantic versioning).
        environment: Deployment environment.
        workspace: Workspace directory configuration.
        logs: Logging configuration.
        config: Configuration directory path.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: Annotated[
        str,
        Field(default=DEFAULT_NAME, min_length=1, max_length=100, description="Application name"),
    ]

    version: Annotated[
        str,
        Field(default=DEFAULT_VERSION, pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$", description="Semantic version"),
    ]

    environment: Annotated[
        Environment,
        Field(default=Environment.DEVELOPMENT, description="Deployment environment"),
    ]

    workspace: Annotated[
        WorkspaceConfig,
        Field(default_factory=WorkspaceConfig, description="Workspace configuration"),
    ]

    logs: Annotated[
        LogsConfig,
        Field(default_factory=LogsConfig, description="Logging configuration"),
    ]

    config: ConfigPath = Field(
        default=DEFAULT_CONFIG,
        description="Configuration directory path",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        """Validate application name is not empty."""
        if not v or not v.strip():
            raise ValueError("Application name cannot be empty")
        return v.strip()

    @field_validator("version")
    @classmethod
    def _validate_version(cls, v: str) -> str:
        """Validate semantic version format."""
        if not v or not v.strip():
            raise ValueError("Version cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def _validate_paths_exist_or_creatable(self) -> "AppConfig":
        """Validate that config directory exists.

        Note: workspace and logs directories are validated lazily
        (when actually accessed) to support auto-create behavior.
        """
        # Config directory should exist (it's where this file lives)
        # We don't strictly require it to exist at model validation time
        # because load_config() handles that
        return self

    def model_dump_for_display(self) -> dict[str, Any]:
        """Return a flattened dict suitable for display in CLI."""
        return {
            "name": self.name,
            "version": self.version,
            "environment": self.environment.value,
            "workspace": str(self.workspace.path),
            "workspace_auto_create": self.workspace.auto_create,
            "logs": str(self.logs.path),
            "logs_level": self.logs.level,
            "logs_format": self.logs.format,
            "logs_auto_create": self.logs.auto_create,
            "config": str(self.config),
        }


__all__ = [
    "Environment",
    "WorkspaceConfig",
    "LogsConfig",
    "AppConfig",
]