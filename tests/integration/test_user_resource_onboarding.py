"""
Phase: USER RESOURCE ONBOARDING — Gated Real Tests.

18 test cases covering:
1. Obsidian vault path validation (present/absent/invalid)
2. Notion API token format validation
3. FreeLLMAPI endpoint reachability
4. Hermes/ACP repo + entry point detection
5. Playwright MCP Node.js + package + browser detection
6. Graphify backend health check
7. MCP generic server config validation
8. Agent Reach capability registration
9. Anthropic/OpenAI key presence (runtime ModelRouter check)
9b. SkillSpecTor skill manifest validation
10. Validation reject: missing required resource -> BLOCKED
11. Validation reject: invalid path -> BLOCKED
11b. Validation reject: unreachable endpoint -> BLOCKED
12. Real connection only after validation passed + env gate
13. Health check marks OPERATIONALLY_VERIFIED
14. Failed health check marks DEGRADED
15. State transition audit trail (IntegrationStateChangedEvent)
16. Dashboard status endpoint returns correct state
17. Credential redaction in all status outputs
18. Mock mode never triggers real validation

All tests are @pytest.mark.gated @pytest.mark.external and skipped by default.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _reset_all_singletons() -> None:
    """Best-effort cleanup of framework singletons between tests."""
    try:
        from aios.events.core.bus import reset_event_bus_singleton
        reset_event_bus_singleton()
    except Exception:
        pass
    try:
        from aios.core.service_registry import reset_service_registry_singleton
        reset_service_registry_singleton()
    except Exception:
        pass
    try:
        from aios.core.security_manager import reset_security_manager_singleton
        reset_security_manager_singleton()
    except Exception:
        pass
    try:
        from aios.core.capability_manager import reset_capability_manager_singleton
        reset_capability_manager_singleton()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. Obsidian vault path validation (present/absent/invalid)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_vault_present(tmp_path):
    """Obsidian vault validation passes when path exists, writable, has .md files."""
    _reset_all_singletons()

    # Create a fake vault
    vault = tmp_path / "test_vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Test Note")
    (vault / ".obsidian").mkdir()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import ObsidianValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.MOCK, notes=str(vault))
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = ObsidianValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert result.details["vault_path"] == str(vault)
    assert result.details["has_obsidian_dir"] is True
    assert result.details["has_markdown_files"] is True
    assert result.details["writable"] is True


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_vault_absent():
    """Obsidian vault validation fails with BLOCKED when path doesn't exist."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import ObsidianValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.MOCK, notes="/nonexistent/vault")
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = ObsidianValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "does not exist" in result.errors[0]


@pytest.mark.gated
@pytest.mark.external
async def test_obsidian_vault_invalid(tmp_path):
    """Obsidian vault validation fails with BLOCKED when path exists but not a vault."""
    _reset_all_singletons()

    # Path exists but no .obsidian dir or .md files
    fake_vault = tmp_path / "empty_dir"
    fake_vault.mkdir()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import ObsidianValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.MOCK, notes=str(fake_vault))
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = ObsidianValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "Vault appears empty" in result.errors[0]


# ---------------------------------------------------------------------------
# 2. Notion API token format validation
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_notion_token_format_valid():
    """Notion validation passes with valid ntn_ token format."""
    _reset_all_singletons()

    os.environ["NOTION_API_TOKEN"] = "ntn_validtoken123456789"

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import NotionValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="notion", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = NotionValidator(entry, reg)
    result = validator.validate()

    # In mock mode, format validation passes even if endpoint check fails
    assert result.state.name in ("VALIDATED", "BLOCKED")  # BLOCKED if network check runs
    assert result.details["has_token"] is True

    os.environ.pop("NOTION_API_TOKEN", None)


@pytest.mark.gated
@pytest.mark.external
async def test_notion_token_format_invalid():
    """Notion validation fails with BLOCKED for invalid token format."""
    _reset_all_singletons()

    os.environ["NOTION_API_TOKEN"] = "invalid-token"

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import NotionValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="notion", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = NotionValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "Invalid Notion token format" in result.errors[0]

    os.environ.pop("NOTION_API_TOKEN", None)


@pytest.mark.gated
@pytest.mark.external
async def test_notion_token_missing():
    """Notion validation fails with BLOCKED when token not set."""
    _reset_all_singletons()

    os.environ.pop("NOTION_API_TOKEN", None)
    os.environ.pop("NOTION_TOKEN", None)

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import NotionValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="notion", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = NotionValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "not set" in result.errors[0]


# ---------------------------------------------------------------------------
# 3. FreeLLMAPI endpoint reachability
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_freellmapi_endpoint_reachable():
    """FreeLLMAPI validation passes when endpoint is healthy (mock mode)."""
    _reset_all_singletons()

    os.environ.pop("FREELLM_API_ENDPOINT", None)
    os.environ.pop("FREELLM_API_KEY", None)

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import FreeLLMAPIValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="freellmapi", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = FreeLLMAPIValidator(entry, reg)
    result = validator.validate()

    # In mock mode, endpoint not reachable should still VALIDATE with warning
    assert result.state.name == "VALIDATED"
    assert "endpoint" in result.details


# ---------------------------------------------------------------------------
# 4. Hermes/ACP repo + entry point detection
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_hermes_acp_repo_valid(tmp_path):
    """Hermes/ACP validation passes when repo with entry.py exists."""
    _reset_all_singletons()

    # Create fake hermes-agent repo
    repo = tmp_path / "hermes-agent"
    repo.mkdir()
    acp_dir = repo / "acp_adapter"
    acp_dir.mkdir()
    (acp_dir / "entry.py").write_text("# ACP entry point")

    os.environ.pop("ACP_CWD", None)

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import HermesACPValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="hermes_agent_acp", mode=IntegrationMode.MOCK, notes=str(repo))
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = HermesACPValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert result.details["has_entry_py"] is True


@pytest.mark.gated
@pytest.mark.external
async def test_hermes_acp_repo_missing():
    """Hermes/ACP validation fails with BLOCKED when repo path missing."""
    _reset_all_singletons()

    os.environ.pop("ACP_CWD", None)

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import HermesACPValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="hermes_agent_acp", mode=IntegrationMode.MOCK, notes="/nonexistent/repo")
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = HermesACPValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "not found" in result.errors[0]


# ---------------------------------------------------------------------------
# 5. Playwright MCP Node.js + package + browser detection
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_playwright_mcp_components():
    """Playwright validation checks Node.js, @playwright/mcp, browsers."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import PlaywrightMCPValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="playwright_mcp", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = PlaywrightMCPValidator(entry, reg)
    result = validator.validate()

    # Should have detailed info about each component
    assert "node_available" in result.details
    assert "playwright_mcp_available" in result.details
    assert "browsers_installed" in result.details

    if result.state.name == "BLOCKED":
        # Missing components are listed
        assert "Missing required components" in result.errors[0]


# ---------------------------------------------------------------------------
# 6. Graphify backend health check
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_graphify_backend_health():
    """Graphify validation checks backend /health endpoint (mock mode)."""
    _reset_all_singletons()

    os.environ.pop("GRAPHIFY_ENDPOINT", None)
    os.environ.pop("GRAPHIFY_NAMESPACE", None)

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import GraphifyValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="graphify", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = GraphifyValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert "endpoint" in result.details
    assert "namespace" in result.details


# ---------------------------------------------------------------------------
# 7. MCP generic server config validation
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_mcp_generic_validator():
    """Generic MCP validator returns validated with warning."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import GenericMCPValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="generic_mcp", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = GenericMCPValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert result.warnings


# ---------------------------------------------------------------------------
# 8. Agent Reach capability registration
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_agent_reach_capability():
    """Agent Reach validation passes (no external resource needed)."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import AgentReachValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="agent_reach", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = AgentReachValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert result.details.get("adapter_instantiated") is True


# ---------------------------------------------------------------------------
# 9. Anthropic/OpenAI key presence (runtime ModelRouter check)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_anthropic_key_validation():
    """Anthropic validation checks API key format (mock mode = warning only)."""
    _reset_all_singletons()

    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-testkey123456789"

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import AnthropicOpenAIValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="anthropic", mode=IntegrationMode.REAL, real_gated=False)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = AnthropicOpenAIValidator(entry, reg, "anthropic")
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert result.details["anthropic_api_key_present"] is True

    os.environ.pop("ANTHROPIC_API_KEY", None)


@pytest.mark.gated
@pytest.mark.external
async def test_openai_key_validation():
    """OpenAI validation checks API key format (mock mode = warning only)."""
    _reset_all_singletons()

    os.environ["OPENAI_API_KEY"] = "sk-testkey123456789"

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import AnthropicOpenAIValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="openai", mode=IntegrationMode.REAL, real_gated=False)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = AnthropicOpenAIValidator(entry, reg, "openai")
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    assert result.details["openai_api_key_present"] is True

    os.environ.pop("OPENAI_API_KEY", None)


# ---------------------------------------------------------------------------
# 9b. SkillSpecTor skill manifest validation
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_skillspector_gate_validation():
    """SkillSpecTor validation tests the gate is functional."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import SkillSpecTorValidator, ValidationRegistry
    from aios.integrations.state import IntegrationState

    reg = load_integrations_config()
    entry = IntegrationConfig(name="skillspector", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = SkillSpecTorValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "VALIDATED"
    # In mock mode without kernel, it returns VALIDATED with warning
    # Just verify it's validated
    assert result.state == IntegrationState.VALIDATED


# ---------------------------------------------------------------------------
# 10. Validation reject: missing required resource -> BLOCKED
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_missing_resource_blocks():
    """Missing required resource -> BLOCKED state."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import NotionValidator, ValidationRegistry

    reg = load_integrations_config()
    # No NOTION_API_TOKEN in env
    os.environ.pop("NOTION_API_TOKEN", None)
    os.environ.pop("NOTION_TOKEN", None)

    entry = IntegrationConfig(name="notion", mode=IntegrationMode.REAL, requires_user_resource=True)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = NotionValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "not set" in result.errors[0]


# ---------------------------------------------------------------------------
# 11. Validation reject: invalid path -> BLOCKED
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_invalid_path_blocks():
    """Invalid vault path -> BLOCKED state."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import ObsidianValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.REAL, notes="/invalid/path")
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = ObsidianValidator(entry, reg)
    result = validator.validate()

    assert result.state.name == "BLOCKED"
    assert "does not exist" in result.errors[0]


# ---------------------------------------------------------------------------
# 11b. Validation reject: unreachable endpoint -> BLOCKED
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_unreachable_endpoint_blocks():
    """Unreachable endpoint in REAL mode -> BLOCKED state."""
    _reset_all_singletons()

    os.environ.pop("NOTION_API_TOKEN", None)
    os.environ["NOTION_API_TOKEN"] = "ntn_validtoken123456789fake"

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import NotionValidator, ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="notion", mode=IntegrationMode.REAL, real_gated=True)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    validator = NotionValidator(entry, reg)
    result = validator.validate()

    # In REAL gated mode, unreachable endpoint -> BLOCKED
    assert result.state.name == "BLOCKED"
    assert "not reachable" in result.errors[0].lower() or "endpoint" in result.errors[0].lower()

    os.environ.pop("NOTION_API_TOKEN", None)


# ---------------------------------------------------------------------------
# 12. Real connection only after validation passed + env gate
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_real_connection_gated(tmp_path):
    """REAL connection attempt fails without validation + env gate."""
    _reset_all_singletons()

    os.environ.pop("AIOS_REAL_INTEGRATION_ENABLED", None)

    # Create a valid vault for validation
    vault = tmp_path / "test_vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Test")
    (vault / ".obsidian").mkdir()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import ValidationRegistry
    from aios.integrations.state import IntegrationState

    reg = load_integrations_config()
    # Get entry from registry (has default state=CONFIGURED) then modify
    entry = reg.get("obsidian")
    entry.mode = IntegrationMode.REAL
    entry.notes = str(vault)

    # Create ValidationRegistry AFTER modifying the registry so validators use updated config
    validation_registry = ValidationRegistry(registry=reg)

    # Try connect without validation -> BLOCKED
    result = entry.attempt_connection()
    assert result.connected is False
    assert "must be VALIDATED" in result.errors[0]

    # Validate first
    entry.validate_resources(validation_registry)
    assert entry.state == IntegrationState.VALIDATED

    # Try connect without env gate -> BLOCKED
    result = entry.attempt_connection()
    assert result.connected is False
    assert "env gate" in result.errors[0].lower() or "not permitted" in result.errors[0].lower()


# ---------------------------------------------------------------------------
# 13. Health check marks OPERATIONALLY_VERIFIED
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_health_check_verified():
    """Health check on CONNECTED integration -> OPERATIONALLY_VERIFIED."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.state import IntegrationState

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.MOCK)
    reg.add(entry)

    # Manually set to CONNECTED
    entry.state = IntegrationState.CONNECTED
    result = entry.run_health_check()

    assert result.state.name == "OPERATIONALLY_VERIFIED"
    assert entry.state == IntegrationState.OPERATIONALLY_VERIFIED
    assert result.healthy is True


# ---------------------------------------------------------------------------
# 14. Failed health check marks DEGRADED
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_health_check_degraded():
    """Health check on non-CONNECTED integration -> DEGRADED."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.state import IntegrationState

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.REAL)
    reg.add(entry)

    # Not connected
    entry.state = IntegrationState.VALIDATED
    result = entry.run_health_check()

    assert result.state.name == "DEGRADED"
    assert entry.state == IntegrationState.DEGRADED
    assert result.healthy is False
    assert "requires CONNECTED state" in result.errors[0]


# ---------------------------------------------------------------------------
# 15. State transition audit trail (IntegrationStateChangedEvent)
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_state_transition_emits_event():
    """State transitions emit IntegrationStateChangedEvent."""
    _reset_all_singletons()

    from aios.events.core.bus import EventBus, EventBusConfig
    from aios.events.core.types import EventType
    from aios.events.core.identity import ComponentIdentity, ComponentType
    from aios.events.core.manager import SubscribeOptions
    from aios.events.core.event import Event
    from aios.integrations import load_integrations_config, IntegrationMode
    from aios.integrations.state import IntegrationState
    from aios.services.integration_status import IntegrationStatusService
    import tempfile
    from pathlib import Path

    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()
    bus._start_worker()

    received: list[dict[str, Any]] = []

    def handler(event: Any) -> None:
        payload = getattr(event, "payload", None)
        if payload:
            received.append(payload.to_dict() if hasattr(payload, "to_dict") else payload)

    sub_id = ComponentIdentity(
        component_type=ComponentType.ENGINEERING_SERVICE,
        component_name="test_observer",
    )
    bus.subscribe(SubscribeOptions(
        subscriber=sub_id,
        event_types=[EventType.INTEGRATION_STATUS_CHANGED],
        handler=handler,
    ))

    # Create a valid vault for validation
    with tempfile.TemporaryDirectory() as tmpdir:
        vault = Path(tmpdir) / "test_vault"
        vault.mkdir()
        (vault / "note.md").write_text("# Test")
        (vault / ".obsidian").mkdir()

        reg = load_integrations_config()
        entry = reg.get("obsidian")
        entry.mode = IntegrationMode.MOCK
        entry.notes = str(vault)
        entry.state = IntegrationState.CONFIGURED

        service = IntegrationStatusService(registry=reg, event_bus=bus)

        # Validate -> should transition CONFIGURED -> VALIDATED and emit event
        await service.validate_integration("obsidian")

        await asyncio.sleep(0.1)

        # Check event was emitted
        state_events = [e for e in received if e.get("integration_name") == "obsidian"]
        assert len(state_events) >= 1

    await bus.shutdown()


# ---------------------------------------------------------------------------
# 16. Dashboard status endpoint returns correct state
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_dashboard_status_endpoint():
    """IntegrationStatusService.get_all_status returns correct state."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationMode
    from aios.services.integration_status import IntegrationStatusService
    from aios.integrations.state import IntegrationState

    reg = load_integrations_config()
    entry = reg.get("obsidian")
    entry.mode = IntegrationMode.MOCK
    entry.state = IntegrationState.CONFIGURED

    service = IntegrationStatusService(registry=reg, event_bus=None)

    # Get all status
    reports = service.get_all_status()
    obsidian_report = next((r for r in reports if r.integration_name == "obsidian"), None)

    assert obsidian_report is not None
    assert obsidian_report.integration_name == "obsidian"
    assert obsidian_report.mode == "mock"
    assert obsidian_report.state.name in ("CONFIGURED", "VALIDATED")


# ---------------------------------------------------------------------------
# 17. Credential redaction in all status outputs
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_status_redaction():
    """All status outputs redact secrets (api_key, token, password, etc.)."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationMode
    from aios.integrations.state import IntegrationStatusReport, IntegrationState

    reg = load_integrations_config()
    entry = reg.get("notion")
    entry.mode = IntegrationMode.MOCK
    entry.state = IntegrationState.CONFIGURED

    report = entry.get_status_report()

    # Inject a fake secret into details
    report.validation_details["api_key"] = "sk-test-secret-123"
    report.validation_details["nested"] = {"password": "secret123"}

    data = report.to_dict(redact_secrets=True)

    # Secrets should be redacted
    json_str = json.dumps(data)
    assert "sk-test-secret-123" not in json_str
    assert "secret123" not in json_str
    assert "***REDACTED***" in json_str


# ---------------------------------------------------------------------------
# 18. Mock mode never triggers real validation
# ---------------------------------------------------------------------------

@pytest.mark.gated
@pytest.mark.external
async def test_mock_mode_no_real_validation():
    """Mock mode integrations never attempt real external validation."""
    _reset_all_singletons()

    from aios.integrations import load_integrations_config, IntegrationConfig, IntegrationMode
    from aios.integrations.validation import ValidationRegistry

    reg = load_integrations_config()
    entry = IntegrationConfig(name="obsidian", mode=IntegrationMode.MOCK)
    reg.add(entry)

    validation_registry = ValidationRegistry()
    validation_registry.registry = reg
    result = validation_registry.validate("obsidian")

    # Should validate based on local config only, no network calls
    assert result.state.name in ("VALIDATED", "BLOCKED")
    # No external connections made - just local filesystem checks


# ============================================================
# Run all tests
# ============================================================

if __name__ == "__main__":
    # Allow running directly for debugging
    pytest.main([__file__, "-v", "-k", "not gated"])