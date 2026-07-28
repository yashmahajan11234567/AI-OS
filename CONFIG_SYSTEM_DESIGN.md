
 # AI-OS Configuration System Design

 ## Overview
 This document describes the configuration system for AI-OS Phase 2.

 ## Architecture
 The configuration package is located at `src/aios/config/` with the following modules:

 - `__init__.py` - Public exports
 - `defaults.py` - Default configuration values
 - `models.py` - Pydantic models with strong typing and validation
   - `AppConfig` - Main application configuration
   - `WorkspaceConfig` - Workspace paths
   - `LogsConfig` - Logging configuration
   - `Environment` - Enum for environment types
 - `validator.py` - Validation logic
   - Path validation (existence, permissions)
   - Required field validation
   - Cross-field consistency validation
 - `loader.py` - YAML loading and merging
   - Load YAML files
   - Merge multiple configs (if needed)
   - Raise useful errors with context

 ## Models (models.py)
 Using Pydantic v2 with:
 - Strict type hints
 - Field validation with `Field()`
 - Custom validators with `@field_validator` and `@model_validator`
 - `ConfigDict` with `extra='forbid'` for strictness
 - `StrEnum` for environment enum

 ### AppConfig (main model)
 ```python
 class AppConfig(BaseModel):
     name: str = Field(default=DEFAULT_NAME, min_length=1)
     version: str = Field(default=DEFAULT_VERSION, pattern=r"^\d+\.\d+\.\d+$")
     environment: Environment = Field(default=Environment.DEVELOPMENT)
     workspace: Path = Field(default=DEFAULT_WORKSPACE)
     logs: Path = Field(default=DEFAULT_LOGS)
     config: Path = Field(default=DEFAULT_CONFIG)
 ```

 ### Environment Enum
 ```python
 class Environment(StrEnum):
     DEVELOPMENT = "development"
     STAGING = "staging"
     PRODUCTION = "production"
     TESTING = "testing"
 ```

 ## Defaults (defaults.py)
 ```python
 DEFAULT_NAME = "AI-OS"
 DEFAULT_VERSION = "0.1.0"
 DEFAULT_ENVIRONMENT = Environment.DEVELOPMENT
 DEFAULT_WORKSPACE = Path("./workspace")
 DEFAULT_LOGS = Path("./logs")
 DEFAULT_CONFIG = Path("./config")
 DEFAULT_APP_YAML = Path("./config/app.yaml")
 ```

 ## Validator (validator.py)
 ### Path Validation
 - Check path exists (or can be created)
 - Check write permissions for workspace/logs/config dirs
 - Convert relative paths to absolute (relative to config file)

 ### Required Fields
 - `name`, `version`, `environment` are required
 - Paths have sensible defaults

 ### Cross-field Validation
 - `workspace`, `logs`, `config` should be subdirectories of workspace root (or at least writable)
 - `version` must match semver pattern
 - `environment` affects defaults (e.g., production requires certain paths)

 ## Loader (loader.py)
 ### Responsibilities
 1. Load YAML from file path
 2. Merge with defaults
 3. Validate with validator
 4. Return validated `AppConfig` model

 ### Error Handling
 - Clear error messages with file path and line number (via YAML)
 - Validation errors include field path and reason
 - Missing file errors suggest creating from template

 ### API
 ```python
 def load_config(path: Path | str = DEFAULT_APP_YAML) -> AppConfig:
     \"\"\"Load, merge, and validate configuration.\"\"\"
 ```

 ## CLI Command: aios doctor
 ### Location
 `src/aios/cli/commands/doctor/__init__.py` or similar

 ### Behavior
 1. Load `config/app.yaml`
 2. Validate it
 3. Print formatted configuration using Rich
 4. Exit with code 0 on success, non-zero on error

 ### Output Format
 Rich table showing all config values with types and sources (default/file)

 ## Configuration File: config/app.yaml
 ```yaml
 name: AI-OS
 version: 0.1.0
 environment: development
 workspace: ./workspace
 logs: ./logs
 config: ./config
 ```

 ## Testing Strategy
 - Unit tests per module (models, validator, defaults, loader)
 - Integration test for full load -> validate -> print flow
 - Fixture-based YAML configs for test isolation
 - Property-based testing for validators

 ## Future Extension Points
 - Multiple config files (apps.yaml, logging.yaml, etc.) merged by loader
 - Environment variable overrides (via pydantic-settings)
 - Remote config sources (Consul, etcd)
 - Config validation schemas (JSON Schema export)
 - Config diff tool (compare environments)
 - Hot reload support

 ## Dependencies
 - Python 3.12+
 - Pydantic v2
 - PyYAML
 - Rich (for CLI output)
 - Typer (for CLI)

 ## Code Quality
 - Type hints everywhere
 - Google-style docstrings
 - Ruff for linting
 - mypy for type checking
 - pytest for testing
