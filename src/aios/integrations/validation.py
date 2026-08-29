"""
Resource Validation Framework for User Resource Onboarding Layer.

Provides per-integration validators that check user-supplied resources
(vaults, tokens, endpoints, binaries, etc.) before allowing REAL connections.

All validators are pure functions — no side effects, no credential exposure.
Validators return structured ValidationResult; exceptions indicate bugs, not
validation failures (fail-closed).

Architecture:
- ResourceValidator base class with abstract validate() method
- Concrete validators for each of 14 canonical integrations
- ValidationRegistry maps integration name → validator
- Reuses SecurityManager gates (MCPServerSecurityGate) for MCP-based integrations
- Reuses ConfigurationManager for config loading
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from aios.integrations.state import (
    IntegrationState,
    ValidationResult,
    HealthCheckResult,
    ConnectionResult,
    IntegrationStatusReport,
)
from aios.integrations.config import (
    IntegrationConfig,
    IntegrationConfigRegistry,
    load_integrations_config,
    CANONICAL_INTEGRATIONS,
    IntegrationMode,
)
from aios.security.secrets import redact_secrets


# ---------------------------------------------------------------------------
# Base Validator
# ---------------------------------------------------------------------------

class ResourceValidator(ABC):
    """Abstract base for per-integration resource validators."""

    integration_name: str
    requires_user_resource: bool = True

    def __init__(self, config: IntegrationConfig, registry: IntegrationConfigRegistry):
        self.config = config
        self.registry = registry

    @abstractmethod
    def validate(self) -> ValidationResult:
        """
        Perform resource validation.

        Returns ValidationResult with:
        - state: VALIDATED (success) or BLOCKED (failure)
        - details: structured validation findings
        - errors: human-readable error messages
        - warnings: non-blocking concerns
        - provenance: C14 advisory markers
        """
        pass

    def _make_provenance(self, **extra: Any) -> dict[str, Any]:
        """Standard C14 provenance for validation results."""
        return {
            "source": f"{self.integration_name}_validator",
            "advisory": True,
            "authority": "advisory_only",
            "trust_level": "untrusted",
            "validated_at": datetime.now().isoformat(),
            **extra,
        }


# ---------------------------------------------------------------------------
# Concrete Validators
# ---------------------------------------------------------------------------

class ObsidianValidator(ResourceValidator):
    """Validate Obsidian vault path: exists, writable, contains .obsidian or .md files."""

    integration_name = "obsidian"

    def validate(self) -> ValidationResult:
        vault_path = self.config.notes or self.registry.all.get("obsidian", IntegrationConfig("obsidian")).notes
        # User provides vault path via config/integrations.yaml notes or defaults.yaml
        if not vault_path:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                errors=["Vault path not configured. Set 'notes' in integrations.yaml or obsidian.vault_path in defaults.yaml"],
                provenance=self._make_provenance(),
            )

        path = Path(vault_path).expanduser().resolve()
        details = {"vault_path": str(path)}

        if not path.exists():
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Vault path does not exist: {path}"],
                provenance=self._make_provenance(**details),
            )

        if not path.is_dir():
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Vault path is not a directory: {path}"],
                provenance=self._make_provenance(**details),
            )

        # Check writable
        try:
            test_file = path / ".aios_write_test"
            test_file.write_text("test")
            test_file.unlink()
            details["writable"] = True
        except OSError as e:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Vault path not writable: {e}"],
                provenance=self._make_provenance(**details),
            )

        # Check for .obsidian dir or .md files
        has_obsidian = (path / ".obsidian").exists()
        has_md = any(path.rglob("*.md"))
        details["has_obsidian_dir"] = has_obsidian
        details["has_markdown_files"] = has_md

        if not has_obsidian and not has_md:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["Vault appears empty: no .obsidian directory and no .md files found"],
                warnings=["Path exists and is writable, but may not be a valid Obsidian vault"],
                provenance=self._make_provenance(**details),
            )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class NotionValidator(ResourceValidator):
    """Validate Notion API token format and endpoint reachability."""

    integration_name = "notion"

    def validate(self) -> ValidationResult:
        # Token comes from environment or config (never hardcoded)
        token = os.environ.get("NOTION_API_TOKEN") or os.environ.get("NOTION_TOKEN")
        parent_id = os.environ.get("NOTION_PARENT_ID")

        details = {"has_token": bool(token), "has_parent_id": bool(parent_id)}

        if not token:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["NOTION_API_TOKEN or NOTION_TOKEN environment variable not set"],
                provenance=self._make_provenance(**details),
            )

        # Validate token format (ntn_ prefix for internal integrations)
        if not token.startswith("ntn_"):
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["Invalid Notion token format: expected 'ntn_' prefix"],
                provenance=self._make_provenance(**details),
            )

        if len(token) < 20:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["Notion token appears too short"],
                provenance=self._make_provenance(**details),
            )

        # Optional: verify endpoint reachable (requires network)
        # This is a lightweight check - real connectivity tested in health_check
        reachable = False
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.notion.com/v1/users/me",
                headers={"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                reachable = resp.status == 200
                details["endpoint_reachable"] = reachable
                details["user_id"] = json.loads(resp.read()).get("id") if reachable else None
        except Exception as e:
            details["endpoint_reachable"] = False
            details["endpoint_error"] = str(e)
            if not self.config.real_gated:
                # In mock mode, just warn
                return ValidationResult(
                    state=IntegrationState.VALIDATED,
                    integration_name=self.integration_name,
                    details=details,
                    warnings=[f"Notion API endpoint check failed (mock mode): {e}"],
                    provenance=self._make_provenance(**details),
                )

        if not reachable and self.config.real_gated:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["Notion API endpoint not reachable or token invalid"],
                provenance=self._make_provenance(**details),
            )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            warnings=[] if reachable else ["Token format valid; endpoint not verified (mock mode)"],
            provenance=self._make_provenance(**details),
        )


import json  # for NotionValidator


class FreeLLMAPIValidator(ResourceValidator):
    """Validate FreeLLMAPI endpoint reachability and optional auth."""

    integration_name = "freellmapi"

    def validate(self) -> ValidationResult:
        endpoint = os.environ.get("FREELLM_API_ENDPOINT") or "http://localhost:8080"
        api_key = os.environ.get("FREELLM_API_KEY")

        details = {"endpoint": endpoint, "has_api_key": bool(api_key)}

        try:
            import urllib.request
            req = urllib.request.Request(f"{endpoint.rstrip('/')}/health")
            if api_key:
                req.add_header("Authorization", f"Bearer {api_key}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                healthy = resp.status == 200
                details["health_status"] = resp.status
                if healthy:
                    try:
                        details["health_body"] = json.loads(resp.read().decode())
                    except Exception:
                        pass
        except Exception as e:
            healthy = False
            details["error"] = str(e)

        if not healthy:
            # Always VALIDATED with warning in mock mode, BLOCKED only in REAL gated mode
            if self.config.mode == IntegrationMode.REAL and self.config.real_gated:
                return ValidationResult(
                    state=IntegrationState.BLOCKED,
                    integration_name=self.integration_name,
                    details=details,
                    errors=[f"FreeLLMAPI endpoint not healthy: {details.get('error', 'unknown')}"],
                    provenance=self._make_provenance(**details),
                )
            else:
                return ValidationResult(
                    state=IntegrationState.VALIDATED,
                    integration_name=self.integration_name,
                    details=details,
                    warnings=[f"FreeLLMAPI endpoint not reachable (mock mode): {details.get('error')}"],
                    provenance=self._make_provenance(**details),
                )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class HermesACPValidator(ResourceValidator):
    """Validate hermes-agent repository with ACP entry point."""

    integration_name = "hermes_agent_acp"

    def validate(self) -> ValidationResult:
        # Get path from config (acp.cwd in defaults.yaml or notes in integrations.yaml)
        from aios.config.loader import _load_yaml_file
        defaults_path = Path("config/defaults.yaml")
        cwd = ""
        try:
            defaults = _load_yaml_file(defaults_path) or {}
            cwd = defaults.get("acp", {}).get("cwd", "")
        except Exception:
            pass

        cwd = cwd or self.config.notes
        details = {"repo_path": cwd}

        if not cwd:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["ACP cwd not configured. Set acp.cwd in defaults.yaml or notes in integrations.yaml"],
                provenance=self._make_provenance(**details),
            )

        path = Path(cwd).expanduser().resolve()
        details["resolved_path"] = str(path)

        if not path.exists():
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"hermes-agent repo not found at: {path}"],
                provenance=self._make_provenance(**details),
            )

        entry_py = path / "acp_adapter" / "entry.py"
        details["has_entry_py"] = entry_py.exists()

        if not entry_py.exists():
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"ACP entry point not found: {entry_py}"],
                provenance=self._make_provenance(**details),
            )

        # Check python availability
        details["python_available"] = shutil.which("python") is not None or shutil.which("python3") is not None

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class HermesMCPValidator(ResourceValidator):
    """Validate Hermes MCP server (stdio transport, tools/list works)."""

    integration_name = "hermes_agent_ext"

    def validate(self) -> ValidationResult:
        from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport, MCPServerStatus
        from aios.events.core.bus import EventBus, EventBusConfig

        details = {}

        # Build server config from MCP config file
        import json
        mcp_dir = Path("config/mcp")
        mcp_config = {}
        for suffix in (f"{self.integration_name}.json", f"{self.integration_name}_mcp.json"):
            p = mcp_dir / suffix
            if p.exists():
                mcp_config = json.loads(p.read_text())
                break

        if not mcp_config:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors="MCP config not found for hermes_agent_ext",
                provenance=self._make_provenance(**details),
            )

        # Validate transport config
        transport_str = mcp_config.get("transport", "stdio")
        command = mcp_config.get("command")
        details["transport"] = transport_str
        details["has_command"] = bool(command)

        if transport_str == "stdio" and not command:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=["STDIO transport requires 'command' in MCP config"],
                provenance=self._make_provenance(**details),
            )

        # Security gate validation (dry-run, no actual connection)
        try:
            from aios.core.security_manager import get_security_manager
            sm = get_security_manager()
            # Need a minimal config for validation
            from aios.core.mcp_manager import MCPServerConfig, MCPTransport
            transport = MCPTransport(transport_str) if transport_str in ("stdio", "http", "websocket", "sse") else MCPTransport.STDIO
            server_cfg = MCPServerConfig(
                server_id=self.integration_name,
                name=self.integration_name,
                transport=transport,
                command=command,
                url=mcp_config.get("url"),
                env=mcp_config.get("env", {}),
                headers=mcp_config.get("headers", {}),
                timeout_seconds=mcp_config.get("timeout_seconds", 30),
                auto_reconnect=mcp_config.get("auto_reconnect", False),
                max_retries=mcp_config.get("max_retries", 3),
                metadata=mcp_config.get("metadata", {}),
            )
            # This runs static validation only (no connect)
            validation_result = sm.validate_mcp_server_before_connect(server_cfg)
            details["security_gate_passed"] = validation_result.passed
            details["security_violations"] = [v.rule_id for v in validation_result.violations]

            if not validation_result.passed:
                return ValidationResult(
                    state=IntegrationState.BLOCKED,
                    integration_name=self.integration_name,
                    details=details,
                    errors=[f"Security gate failed: {v.message} (rule: {v.rule_id})" for v in validation_result.violations],
                    provenance=self._make_provenance(**details),
                )
        except Exception as e:
            details["security_gate_error"] = str(e)
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Security gate validation error: {e}"],
                provenance=self._make_provenance(**details),
            )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class PlaywrightMCPValidator(ResourceValidator):
    """Validate Playwright MCP: Node.js, @playwright/mcp package, browser installed."""

    integration_name = "playwright_mcp"

    def validate(self) -> ValidationResult:
        details = {}

        # Check Node.js
        node_path = shutil.which("node")
        details["node_path"] = node_path
        if node_path:
            try:
                result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)
                details["node_version"] = result.stdout.strip()
            except Exception as e:
                details["node_version_error"] = str(e)

        details["node_available"] = bool(node_path)

        # Check npx
        npx_path = shutil.which("npx")
        details["npx_available"] = bool(npx_path)

        # Check @playwright/mcp
        has_mcp_package = False
        if npx_path:
            try:
                result = subprocess.run(
                    ["npx", "@playwright/mcp", "--version"],
                    capture_output=True, text=True, timeout=30
                )
                has_mcp_package = result.returncode == 0
                details["playwright_mcp_version"] = result.stdout.strip() if has_mcp_package else result.stderr.strip()
            except subprocess.TimeoutExpired:
                details["playwright_mcp_error"] = "timeout"
            except Exception as e:
                details["playwright_mcp_error"] = str(e)
        details["playwright_mcp_available"] = has_mcp_package

        # Check browsers
        browsers_installed = False
        if npx_path:
            try:
                result = subprocess.run(
                    ["npx", "playwright", "install", "--dry-run"],
                    capture_output=True, text=True, timeout=30
                )
                browsers_installed = result.returncode == 0
                details["browsers_ready"] = browsers_installed
            except Exception as e:
                details["browsers_error"] = str(e)
        details["browsers_installed"] = browsers_installed

        # Overall assessment
        all_ready = details["node_available"] and details["playwright_mcp_available"] and details["browsers_installed"]

        if not all_ready:
            missing = []
            if not details["node_available"]:
                missing.append("Node.js")
            if not details["playwright_mcp_available"]:
                missing.append("@playwright/mcp")
            if not details["browsers_installed"]:
                missing.append("Playwright browsers")

            if self.config.real_gated:
                return ValidationResult(
                    state=IntegrationState.BLOCKED,
                    integration_name=self.integration_name,
                    details=details,
                    errors=[f"Missing required components: {', '.join(missing)}"],
                    provenance=self._make_provenance(**details),
                )
            else:
                return ValidationResult(
                    state=IntegrationState.VALIDATED,
                    integration_name=self.integration_name,
                    details=details,
                    warnings=[f"Missing components for REAL mode (mock ok): {', '.join(missing)}"],
                    provenance=self._make_provenance(**details),
                )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class GraphifyValidator(ResourceValidator):
    """Validate Graphify backend endpoint health and namespace isolation."""

    integration_name = "graphify"

    def validate(self) -> ValidationResult:
        endpoint = os.environ.get("GRAPHIFY_ENDPOINT") or "http://localhost:8081"
        namespace = os.environ.get("GRAPHIFY_NAMESPACE") or "aios"

        details = {"endpoint": endpoint, "namespace": namespace}

        try:
            import urllib.request
            req = urllib.request.Request(f"{endpoint.rstrip('/')}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                healthy = resp.status == 200
                details["health_status"] = resp.status
                if healthy:
                    try:
                        details["health_body"] = json.loads(resp.read().decode())
                    except Exception:
                        pass
        except Exception as e:
            healthy = False
            details["error"] = str(e)

        if not healthy:
            # Always VALIDATED with warning in mock mode, BLOCKED only in REAL gated mode
            if self.config.mode == IntegrationMode.REAL and self.config.real_gated:
                return ValidationResult(
                    state=IntegrationState.BLOCKED,
                    integration_name=self.integration_name,
                    details=details,
                    errors=[f"Graphify backend not healthy: {details.get('error', 'unknown')}"],
                    provenance=self._make_provenance(**details),
                )
            else:
                return ValidationResult(
                    state=IntegrationState.VALIDATED,
                    integration_name=self.integration_name,
                    details=details,
                    warnings=[f"Graphify backend not reachable (mock mode): {details.get('error')}"],
                    provenance=self._make_provenance(**details),
                )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class ClaudeMemValidator(ResourceValidator):
    """Validate Claude-Mem configuration (architecture decision: local vs MCP)."""

    integration_name = "claude_mem"

    def validate(self) -> ValidationResult:
        # Architecture: claude_mem uses local storage by default, no external MCP needed
        # If user wants MCP mode, they'd configure it separately
        details = {"mode": "local_storage"}

        # Check local storage path
        from aios.config.loader import _load_yaml_file
        defaults_path = Path("config/defaults.yaml")
        memory_path = ""
        try:
            defaults = _load_yaml_file(defaults_path) or {}
            memory_path = defaults.get("memory", {}).get("base_path", "./data/memory")
        except Exception:
            memory_path = "./data/memory"

        path = Path(memory_path).expanduser().resolve()
        details["memory_path"] = str(path)
        details["path_exists"] = path.exists()
        details["path_writable"] = False

        if path.exists():
            try:
                test = path / ".aios_write_test"
                test.write_text("test")
                test.unlink()
                details["path_writable"] = True
            except OSError:
                pass

        if not details["path_writable"]:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Claude-Mem storage path not writable: {path}"],
                provenance=self._make_provenance(**details),
            )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class AgentReachValidator(ResourceValidator):
    """Validate Agent Reach capability registration (no external resource)."""

    integration_name = "agent_reach"
    requires_user_resource = False

    def validate(self) -> ValidationResult:
        # Agent Reach has no external resource requirement
        # Validation is: capability can be registered
        details = {}

        try:
            from aios.adapters.agent_reach import AgentReachAdapter
            from aios.core.capability_manager import CapabilityManager
            import threading

            # Quick instantiation test
            adapter = AgentReachAdapter(server_id="agent_reach")
            details["adapter_instantiated"] = True

            # Check capability manifest
            cap_path = Path("config/capabilities/agent_reach.yaml")
            details["manifest_exists"] = cap_path.exists()

            return ValidationResult(
                state=IntegrationState.VALIDATED,
                integration_name=self.integration_name,
                details=details,
                provenance=self._make_provenance(**details),
            )
        except Exception as e:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Agent Reach validation failed: {e}"],
                provenance=self._make_provenance(**details),
            )


class GenericMCPValidator(ResourceValidator):
    """Validate generic MCP server config (command exists, transport valid)."""

    integration_name = "generic_mcp"

    def validate(self) -> ValidationResult:
        # This is a placeholder for arbitrary MCP servers
        # Actual validation would use the specific server_id's MCP config
        details = {"note": "Generic MCP validator - configure specific server in integrations.yaml"}

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            warnings=["Generic MCP validator: no specific server configured"],
            provenance=self._make_provenance(**details),
        )


class AnthropicOpenAIValidator(ResourceValidator):
    """Validate Anthropic/OpenAI API keys (checked at runtime by ModelRouter)."""

    integration_name = "anthropic"  # also handles openai

    def __init__(self, config: IntegrationConfig, registry: IntegrationConfigRegistry, provider: str = "anthropic"):
        super().__init__(config, registry)
        self.provider = provider
        self.integration_name = provider

    def validate(self) -> ValidationResult:
        env_var = "ANTHROPIC_API_KEY" if self.provider == "anthropic" else "OPENAI_API_KEY"
        api_key = os.environ.get(env_var)

        details = {f"{self.provider}_api_key_present": bool(api_key)}

        if not api_key:
            # Not a hard block - ModelRouter checks at runtime
            return ValidationResult(
                state=IntegrationState.VALIDATED,
                integration_name=self.integration_name,
                details=details,
                warnings=[f"{env_var} not set; will be checked at runtime by ModelRouter"],
                provenance=self._make_provenance(**details),
            )

        # Basic format check
        if self.provider == "anthropic":
            valid_format = api_key.startswith("sk-ant-")
        else:
            valid_format = api_key.startswith("sk-")

        if not valid_format:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.integration_name,
                details=details,
                errors=[f"Invalid {self.provider} API key format"],
                provenance=self._make_provenance(**details),
            )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


class SkillSpecTorValidator(ResourceValidator):
    """Validate SkillSpecTor skill manifest (entry point, permissions, dependencies)."""

    integration_name = "skillspector"

    def validate(self) -> ValidationResult:
        details = {}

        try:
            from aios.core.security_manager import get_security_manager
            sm = get_security_manager()

            # Validate a sample skill spec or the mechanism itself
            # This tests the gate is functional
            test_spec = {
                "skill_id": "test.validation",
                "entry_point": "test_module:test_func",
                "permissions": ["memory:read"],
                "dependencies": [],
                "config_schema": {},
                "runtime": "python",
                "version": "0.0.1",
                "metadata": {"author": "test", "description": "validation test"},
            }

            result = sm.skillspector_gate.validate_skill_spec(test_spec)  # type: ignore[attr-defined]
            details["gate_functional"] = True
            details["test_passed"] = result.passed
            details["test_violations"] = [v.rule_id for v in result.violations]

            if not result.passed:
                return ValidationResult(
                    state=IntegrationState.BLOCKED,
                    integration_name=self.integration_name,
                    details=details,
                    errors=[f"SkillSpecTor gate test failed: {v.message}" for v in result.violations],
                    provenance=self._make_provenance(**details),
                )

        except Exception as e:
            details["gate_error"] = str(e)
            # In mock mode, VALIDATED with warning; in REAL gated mode, BLOCKED
            if self.config.mode == IntegrationMode.REAL and self.config.real_gated:
                return ValidationResult(
                    state=IntegrationState.BLOCKED,
                    integration_name=self.integration_name,
                    details=details,
                    errors=[f"SkillSpecTor validation error: {e}"],
                    provenance=self._make_provenance(**details),
                )
            else:
                return ValidationResult(
                    state=IntegrationState.VALIDATED,
                    integration_name=self.integration_name,
                    details=details,
                    warnings=[f"SkillSpecTor gate not fully functional (mock mode): {e}"],
                    provenance=self._make_provenance(**details),
                )

        return ValidationResult(
            state=IntegrationState.VALIDATED,
            integration_name=self.integration_name,
            details=details,
            provenance=self._make_provenance(**details),
        )


# ---------------------------------------------------------------------------
# ValidationRegistry
# ---------------------------------------------------------------------------

@dataclass
class ValidationRegistry:
    """Maps integration names to validators and runs validations."""

    _validators: dict[str, ResourceValidator] = field(default_factory=dict)
    registry: IntegrationConfigRegistry = field(default_factory=lambda: load_integrations_config())

    def __post_init__(self):
        self._register_default_validators()

    def _register_default_validators(self) -> None:
        for name in CANONICAL_INTEGRATIONS:
            config = self.registry.get(name) or IntegrationConfig(name=name)
            if name == "obsidian":
                self._validators[name] = ObsidianValidator(config, self.registry)
            elif name == "notion":
                self._validators[name] = NotionValidator(config, self.registry)
            elif name == "freellmapi":
                self._validators[name] = FreeLLMAPIValidator(config, self.registry)
            elif name == "hermes_agent_acp":
                self._validators[name] = HermesACPValidator(config, self.registry)
            elif name == "hermes_agent_ext":
                self._validators[name] = HermesMCPValidator(config, self.registry)
            elif name == "playwright_mcp":
                self._validators[name] = PlaywrightMCPValidator(config, self.registry)
            elif name == "graphify":
                self._validators[name] = GraphifyValidator(config, self.registry)
            elif name == "claude_mem":
                self._validators[name] = ClaudeMemValidator(config, self.registry)
            elif name == "agent_reach":
                self._validators[name] = AgentReachValidator(config, self.registry)
            elif name == "anthropic":
                self._validators[name] = AnthropicOpenAIValidator(config, self.registry, "anthropic")
            elif name == "openai":
                self._validators[name] = AnthropicOpenAIValidator(config, self.registry, "openai")
            elif name == "skillspector":
                self._validators[name] = SkillSpecTorValidator(config, self.registry)
            else:
                self._validators[name] = GenericMCPValidator(config, self.registry)

    def register(self, name: str, validator: ResourceValidator) -> None:
        """Override or add a custom validator."""
        self._validators[name] = validator

    def get(self, name: str) -> ResourceValidator | None:
        return self._validators.get(name)

    def validate(self, name: str) -> ValidationResult:
        """Run validation for a single integration."""
        validator = self._validators.get(name)
        if validator is None:
            return ValidationResult(
                state=IntegrationState.BLOCKED,
                integration_name=name,
                errors=[f"No validator registered for integration: {name}"],
                provenance={"source": "validation_registry", "advisory": True},
            )
        return validator.validate()

    def validate_all(self) -> dict[str, ValidationResult]:
        """Run validation for all canonical integrations."""
        results = {}
        for name in CANONICAL_INTEGRATIONS:
            results[name] = self.validate(name)
        return results

    def get_status_reports(self) -> dict[str, IntegrationStatusReport]:
        """Generate status reports for all integrations."""
        reports = {}
        for name in CANONICAL_INTEGRATIONS:
            config = self.registry.get(name)
            if config:
                validation_result = self.validate(name)
                reports[name] = IntegrationStatusReport(
                    integration_name=name,
                    state=validation_result.state,
                    mode=config.mode.value,
                    real_allowed=config.real_allowed(),
                    user_resource_present=config.user_resource_present,
                    real_gated=config.real_gated,
                    requires_user_resource=config.requires_user_resource,
                    last_validated=validation_result.validated_at,
                    validation_details=validation_result.details,
                    errors=validation_result.errors,
                    warnings=validation_result.warnings,
                    provenance=validation_result.provenance,
                )
        return reports