"""Default configuration values for AI-OS.

This module provides centralized default values for all configuration options.
Using a single source of truth for defaults ensures consistency across the
application and makes it easy to modify default behavior.
"""

from enum import StrEnum
from pathlib import Path


class Environment(StrEnum):
    """Deployment environment enumeration.

    Using StrEnum ensures string representation matches the enum value,
    which is ideal for YAML serialization and comparison.
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# Application identity defaults
DEFAULT_NAME: str = "AI-OS"
DEFAULT_VERSION: str = "0.1.0"

# Environment default
DEFAULT_ENVIRONMENT: Environment = Environment.DEVELOPMENT

# Path defaults (relative to project root)
DEFAULT_WORKSPACE: Path = Path("./workspace")
DEFAULT_LOGS: Path = Path("./logs")
DEFAULT_CONFIG: Path = Path("./config")

# Default configuration file location
DEFAULT_APP_YAML: Path = Path("./config/app.yaml")

# Semantic version pattern for validation
VERSION_PATTERN: str = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"

# Minimum required Python version
MIN_PYTHON_VERSION: tuple[int, int] = (3, 12)

# Default logging configuration
DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

__all__ = [
    "Environment",
    "DEFAULT_NAME",
    "DEFAULT_VERSION",
    "DEFAULT_ENVIRONMENT",
    "DEFAULT_WORKSPACE",
    "DEFAULT_LOGS",
    "DEFAULT_CONFIG",
    "DEFAULT_APP_YAML",
    "VERSION_PATTERN",
    "MIN_PYTHON_VERSION",
    "DEFAULT_LOG_LEVEL",
    "DEFAULT_LOG_FORMAT",
]
