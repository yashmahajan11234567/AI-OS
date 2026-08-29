# AI-OS User Resource Onboarding Guide

**Version:** 1.0.0  
**Status:** Production Ready  
**Part of:** AI-OS External Ecosystem Integration Framework (M12)

---

## Overview

The AI-OS External Ecosystem Integration Framework provides a **production-safe onboarding layer** that allows users to configure real external resources through existing architecture mechanisms without bypassing security gates or authority boundaries.

### Key Principles

1. **Fail-Closed Defaults** — All integrations default to `mock` mode; `real` mode requires explicit opt-in
2. **Gate-Before-Connect** — SecurityManager validates every external connection before it's established
3. **Secret Redaction** — All status outputs automatically redact sensitive data
4. **No Credential Fabrication** — The system NEVER provides or mocks credentials; users must supply them
5. **Real/Mock Separation** — Clear boundary; mock path always functional for development

---

## Architecture

### 7-State Integration State Machine

Each integration transitions through the following states:

```
ABSENT → CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED
                ↓           ↓           ↓              ↓
              BLOCKED ←────────────────────────────── DEGRADED
```

| State | Description |
|-------|-------------|
| `ABSENT` | Integration not configured |
| `CONFIGURED` | Basic config present, no validation run |
| `VALIDATED` | Resource validation passed (paths exist, endpoints reachable, etc.) |
| `CONNECTED` | Real connection established (requires validation + env gate + user resource) |
| `OPERATIONALLY_VERIFIED` | Health check passes; integration fully operational |
| `BLOCKED` | Validation failed or real connection not permitted |
| `DEGRADED` | Was operational but health check failed |

### State Transition Rules

- **ABSENT → CONFIGURED**: `load_integrations_config()` seeds all 14 canonical integrations
- **CONFIGURED → VALIDATED**: `validate_resources()` succeeds
- **CONFIGURED → BLOCKED**: `validate_resources()` fails
- **VALIDATED → CONNECTED**: `attempt_connection()` succeeds (requires `real_allowed()` = true)
- **VALIDATED → BLOCKED**: `attempt_connection()` fails or `real_allowed()` = false
- **CONNECTED → OPERATIONALLY_VERIFIED**: `run_health_check()` passes
- **CONNECTED/OPERATIONALLY_VERIFIED → DEGRADED**: `run_health_check()` fails
- **Any → BLOCKED**: Security gate failure, missing resource, etc.

---

## Canonical Integrations (14)

| Integration | ID | Resource Type | Validation |
|-------------|-----|---------------|------------|
| Hermes Agent (ACP) | `hermes_agent_acp` | Repo path + entry point | Path exists, `entry.py` present, Python available |
| Hermes Agent (MCP) | `hermes_agent_ext` | MCP stdio server | Transport works, `tools/list` succeeds |
| Playwright MCP | `playwright_mcp` | Node.js + browsers | `node --version`, `npx @playwright/mcp --version`, `playwright install --dry-run` |
| Obsidian | `obsidian` | Vault path | Path exists, writable, contains `.obsidian` or `.md` files |
| Graphify | `graphify` | Backend endpoint | HTTP `GET /health`, namespace isolation |
| Claude-Mem | `claude_mem` | Architecture decision | Document local vs external; design config accordingly |
| Notion | `notion` | API token + parent DB | Token format `ntn_*`, endpoint reachable |
| Agent Reach | `agent_reach` | Capability manifest | Capability registration validation |
| FreeLLMAPI | `freellmapi` | Endpoint + creds | HTTP `GET /health` or `/v1/models` |
| Anthropic | `anthropic` | API key (runtime) | ModelRouter checks at use time |
| OpenAI | `openai` | API key (runtime) | ModelRouter checks at use time |
| Generic MCP | `generic_mcp` | MCP server config | Command exists, transport valid, `tools/list` works |

---

## Quick Start

### 1. List All Integrations

```bash
aios onboard list
```

Output shows all 14 integrations with current state, mode, and resource status.

### 2. Validate a Specific Integration

```bash
# Validate Obsidian (checks vault path exists and is writable)
aios onboard validate obsidian

# Validate all configured integrations
aios onboard validate --all
```

### 3. Enable Real Mode (Requires Confirmation)

```bash
# Enable real mode for Obsidian
aios onboard enable obsidian --confirm

# This updates config/integrations.yaml:
# integrations:
#   obsidian:
#     mode: real
#     user_resource_present: true   # Must be set after you verify the vault path
```

### 4. Attempt Real Connection (Requires Env Gate)

```bash
# Set env gate AND ensure user resource is present
AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard connect obsidian
```

### 5. Run Health Check

```bash
AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard health obsidian
```

### 6. Get Full Status (Dashboard Ready)

```bash
# Human-readable
aios onboard status

# Machine-readable JSON
aios onboard status --json
```

---

## Configuration

### Config File: `config/integrations.yaml`

```yaml
integrations:
  obsidian:
    mode: real                          # "mock" or "real" (default: mock)
    user_resource_present: true         # Set ONLY after YOU verify the resource
    real_gated: true                    # Requires AIOS_REAL_INTEGRATION_ENABLED=1
    requires_user_resource: true        # This integration needs user resource
    notes: "Vault at /home/user/vault"  # Free-text notes
  
  notion:
    mode: real
    # user_resource_present: true      # Set after you provide valid token
  
  playwright_mcp:
    mode: mock                          # Default; safe for CI
```

### Environment Gate

```bash
# Enable real external operations (required for real connections)
export AIOS_REAL_INTEGRATION_ENABLED=1
```

**Security Note**: This env var is REQUIRED even when `mode: real` is set in config. It's a second gate preventing accidental real connections in CI.

---

## Per-Integration Setup

### Obsidian (Local Knowledge Vault)

**Resource**: Local filesystem vault path

1. Create/locate your Obsidian vault: `/path/to/vault`
2. Verify it contains `.obsidian/` directory or `.md` files
3. Configure:
   ```yaml
   integrations:
     obsidian:
       mode: real
       user_resource_present: true
   ```
4. Validate: `aios onboard validate obsidian`
5. Connect: `AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard connect obsidian`

### Notion (Planning Database)

**Resource**: Notion API token + parent database/page ID

1. Get Notion internal integration token (format: `ntn_*`)
2. Create a database or page for AI-OS to use
3. Configure:
   ```yaml
   integrations:
     notion:
       mode: real
       user_resource_present: true
       notes: "token=ntn_..., parent=db-id"
   ```
4. Validate: `aios onboard validate notion` (checks token format + endpoint)

**Security**: Never commit tokens to version control. Use environment variables or secret manager.

### FreeLLMAPI (Local LLM Provider)

**Resource**: HTTP endpoint (e.g., `http://localhost:8000`)

1. Start your FreeLLMAPI server
2. Verify `/health` or `/v1/models` endpoint responds
3. Configure:
   ```yaml
   integrations:
     freellmapi:
       mode: real
       user_resource_present: true
       notes: "endpoint=http://localhost:8000"
   ```
4. Validate: `aios onboard validate freellmapi`

### Hermes Agent (ACP Worker)

**Resource**: Local `hermes-agent` repository with `acp_adapter/entry.py`

1. Clone hermes-agent repo
2. Verify `acp_adapter/entry.py` exists
3. Configure:
   ```yaml
   integrations:
     hermes_agent_acp:
       mode: real
       user_resource_present: true
       notes: "repo_path=/path/to/hermes-agent"
   ```
4. Validate: `aios onboard validate hermes_agent_acp`

### Hermes Agent (MCP Fallback)

**Resource**: Running MCP server via stdio

1. Start the hermes-agent MCP server
2. Configure:
   ```yaml
   integrations:
     hermes_agent_ext:
       mode: real
       user_resource_present: true
   ```
3. Validate: `aios onboard validate hermes_agent_ext`

### Playwright MCP (Browser Automation)

**Resource**: Node.js + `@playwright/mcp` + installed browsers

1. Install Node.js (≥18)
2. Install Playwright MCP: `npm install -g @playwright/mcp`
3. Install browsers: `npx playwright install`
4. Configure:
   ```yaml
   integrations:
     playwright_mcp:
       mode: real
       user_resource_present: true
   ```
5. Validate: `aios onboard validate playwright_mcp`

### Graphify (Knowledge Graph)

**Resource**: Graphify backend HTTP endpoint

1. Deploy Graphify backend
2. Verify `/health` endpoint and namespace isolation
3. Configure:
   ```yaml
   integrations:
     graphify:
       mode: real
       user_resource_present: true
       notes: "endpoint=http://localhost:8080, namespace=aios"
   ```
4. Validate: `aios onboard validate graphify`

### Claude-Mem (Memory Retrieval)

**Resource**: Architecture decision required first

Document whether you're using:
- **Local storage** (SQLite/filesystem) — configure path
- **External MCP** — configure MCP server

```yaml
integrations:
  claude_mem:
    mode: real
    user_resource_present: true
    notes: "local_storage=/path/to/storage"
    # OR
    # notes: "mcp_server=stdio://..."
```

### Agent Reach (Agent Communication)

**Resource**: Capability registration only (no external resource)

This integration validates capability manifest registration — no user resource needed.

```yaml
integrations:
  agent_reach:
    mode: real
    requires_user_resource: false  # No external resource needed
```

### Generic MCP Server

**Resource**: MCP server configuration (command + args)

```yaml
integrations:
  generic_mcp:
    mode: real
    user_resource_present: true
    notes: "command=my-mcp-server, args=--port 3000"
```

### Anthropic / OpenAI (Model Providers)

**Resource**: API key (checked at runtime by ModelRouter, not at onboarding)

```yaml
integrations:
  anthropic:
    mode: real
    user_resource_present: true   # Set after you verify ANTHROPIC_API_KEY env var
  
  openai:
    mode: real
    user_resource_present: true   # Set after you verify OPENAI_API_KEY env var
```

---

## Security Model

### Fail-Closed Behavior

1. **Default mode is `mock`** — No real external calls without explicit config
2. **Real mode requires THREE conditions**:
   - `mode: real` in config
   - `AIOS_REAL_INTEGRATION_ENABLED=1` environment variable set
   - `user_resource_present: true` (you verified the resource)
3. **SecurityManager gates ALL MCP/ACP connections** before they're established
4. **CapabilityManager controls** which adapters can be instantiated (trust levels: BUILTIN, TRUSTED, TRUSTED_CONTEXTUAL, UNTRUSTED)

### Secret Handling

- **All status outputs use `redact_secrets=True` by default**
- Secrets (API keys, tokens) are replaced with `***REDACTED***` in:
  - CLI output (`aios onboard status`)
  - Dashboard API (`IntegrationStatusService.get_all_status_dict()`)
  - Event payloads (`INTEGRATION_STATUS_CHANGED`)
- The `redact_text()` and `redact_env()` functions from `aios.security.secrets` are used centrally

### Authority Boundaries

- **Terminal 2 (Implementation)**: Builds the onboarding layer, prepares evidence artifacts
- **Terminal 3 (Verification)**: Retains INDEPENDENT verification authority
- **Terminal 3 does NOT self-certify** — these are evidence artifacts, not certifications

---

## Dashboard Integration

### Backend Service: `IntegrationStatusService`

Registered as `core.integration_status` in ServiceRegistry.

**API**:
```python
# Get all integrations status
service.get_all_status()  # → List[IntegrationStatusReport]

# Get single integration
service.get_status("obsidian")  # → IntegrationStatusReport | None

# Dict format (redacted by default)
service.get_all_status_dict(redact_secrets=True)  # → List[dict]
service.get_status_dict("obsidian", redact_secrets=True)  # → dict | None
```

**Status Report Fields**:
```python
@dataclass
class IntegrationStatusReport:
    integration_name: str
    state: IntegrationState
    mode: str                    # "mock" | "real"
    real_allowed: bool           # All three gates pass?
    user_resource_present: bool
    real_gated: bool
    requires_user_resource: bool
    last_validated: datetime | None
    last_health_check: datetime | None
    validation_details: dict
    health_details: dict
    errors: list[str]
    warnings: list[str]
    provenance: dict             # C14 advisory provenance
```

### Real-Time Updates

State changes emit `INTEGRATION_STATUS_CHANGED` events via EventBus:

```python
# Event payload
{
    "integration_name": "obsidian",
    "previous_state": "VALIDATED",
    "new_state": "CONNECTED",
    "changed_at": "2026-08-28T12:00:00Z",
    "details": {...}
}
```

Frontend dashboards can subscribe to this event for live updates.

---

## CLI Reference

### `aios onboard list`

List all integrations with current status.

```bash
aios onboard list
# Optional: --json for machine output
```

### `aios onboard validate`

Run resource validation.

```bash
aios onboard validate <name>      # Single integration
aios onboard validate --all       # All integrations
aios onboard validate --json      # JSON output
```

### `aios onboard connect`

Attempt REAL connection (requires validation passed + env gate).

```bash
AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard connect <name>
aios onboard connect <name> --json
```

### `aios onboard health`

Run operational health check.

```bash
AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard health <name>
aios onboard health <name> --json
```

### `aios onboard status`

Full status report for dashboard.

```bash
aios onboard status              # Human-readable table
aios onboard status --json       # Machine-readable JSON
```

### `aios onboard enable`

Set integration to `mode: real` in config (requires `--confirm`).

```bash
aios onboard enable <name> --confirm
aios onboard enable <name> --confirm --notes "vault at /path"
```

### `aios onboard disable`

Set integration to `mode: mock` in config.

```bash
aios onboard disable <name>
```

---

## Testing

### Unit Tests (No Env Gate Required)

```bash
# Validation logic tests
python -m pytest tests/unit/test_*onboarding* -v

# State machine tests
python -m pytest tests/unit/test_integration_state.py -v
```

### Gated Integration Tests (Require Real Resources + Env Gate)

```bash
# Set up real resources first, then:
export AIOS_REAL_INTEGRATION_ENABLED=1

# Run all 18 gated test cases
python -m pytest tests/integration/test_user_resource_onboarding.py -v

# Test 1: Obsidian vault path validation (present/absent/invalid)
# Test 2: Notion API token format validation
# Test 3: FreeLLMAPI endpoint reachability
# Test 4: Hermes/ACP repo + entry point detection
# Test 5: Playwright MCP Node.js + package + browser detection
# Test 6: Graphify backend health check
# Test 7: MCP generic server config validation
# Test 8: Agent Reach capability registration
# Test 9: Anthropic/OpenAI key presence (ModelRouter check)
# Test 10: SkillSpecTor skill manifest validation
# Test 11: Validation reject: missing required resource → BLOCKED
# Test 12: Validation reject: invalid path → BLOCKED
# Test 13: Validation reject: unreachable endpoint → BLOCKED
# Test 14: Real connection only after validation + env gate
# Test 15: Health check marks OPERATIONALLY_VERIFIED
# Test 16: Failed health check marks DEGRADED
# Test 17: State transition audit trail (INTEGRATION_STATUS_CHANGED event)
# Test 18: Dashboard status endpoint returns correct state
# Test 19: Credential redaction in all status outputs
# Test 20: Mock mode never triggers real validation
```

### Regression Tests

```bash
# Full suite (excludes known M10 failures)
python -m pytest tests/ --ignore=tests/integration/test_m10_autonomy.py --ignore=tests/integration/test_m10_authority_boundary.py --ignore=tests/integration/test_m10_integration.py --ignore=tests/security/test_m10_security.py
```

**Expected**: 2017+ passed, 3 skipped

---

## Troubleshooting

### "Integration not found"

```bash
aios onboard list  # Check exact name from CANONICAL_INTEGRATIONS
```

### "Validation failed: user resource absent"

```bash
# You must set user_resource_present: true in integrations.yaml
# AFTER you verify the resource actually exists
integrations:
  obsidian:
    user_resource_present: true
```

### "Real connection not permitted"

Check all three gates:
1. `mode: real` in config?
2. `AIOS_REAL_INTEGRATION_ENABLED=1` in environment?
3. `user_resource_present: true` in config?

```bash
# Debug
aios onboard status --json | jq '.[] | select(.integration_name=="obsidian")'
```

### "Security gate validation failed"

The SecurityManager's MCPServerSecurityGate (S1/S2) rejected the connection. Check:
- MCP server config in `config/mcp/*.json`
- `SecurityManager.validate_mcp_server_before_connect()` logs

### Secrets appearing in output

All outputs use `redact_secrets=True` by default. If you see real secrets:
1. Check if you called with `redact_secrets=False`
2. Report as security bug

---

## Troubleshooting State Transitions

| Current State | Action | Expected Next State | If Stuck... |
|---------------|--------|---------------------|-------------|
| `CONFIGURED` | `validate` | `VALIDATED` or `BLOCKED` | Check validation errors in status |
| `VALIDATED` | `connect` | `CONNECTED` or `BLOCKED` | Check `real_allowed()` gates |
| `CONNECTED` | `health` | `OPERATIONALLY_VERIFIED` or `DEGRADED` | Check adapter health check impl |
| `OPERATIONALLY_VERIFIED` | `health` (fails) | `DEGRADED` | Check adapter/external service |
| `DEGRADED` | `health` (passes) | `OPERATIONALLY_VERIFIED` | Auto-recovers on next success |
| `BLOCKED` | `validate` (fix) | `VALIDATED` | Fix root cause, re-validate |

---

## Developer Guide

### Adding a New Integration

1. **Add to `CANONICAL_INTEGRATIONS`** in `src/aios/integrations/config.py`
2. **Create validator** in `src/aios/integrations/validation.py` extending `ResourceValidator`
3. **Register validator** in `ValidationRegistry._validators`
4. **Add adapter** (if real connection needed) extending `BaseExecutionAdapter`
5. **Register adapter** in CapabilityManager with appropriate trust level
6. **Add tests** in `tests/integration/test_user_resource_onboarding.py`

### Extending ValidationRegistry

```python
from aios.integrations.validation import ValidationRegistry, ResourceValidator, ValidationResult

class MyValidator(ResourceValidator):
    integration_name = "my_integration"
    
    def validate(self) -> ValidationResult:
        # Your validation logic here
        # Return ValidationResult with state, details, errors, warnings, provenance
        pass

# Register
ValidationRegistry._validators["my_integration"] = MyValidator()
```

### Custom Health Checks

Override `run_health_check()` in your adapter or integration config:

```python
class MyAdapter(BaseExecutionAdapter):
    async def health_check(self) -> HealthCheckResult:
        # Your health check logic
        return HealthCheckResult(
            state=IntegrationState.OPERATIONALLY_VERIFIED,
            integration_name=self.name,
            healthy=True,
            details={...}
        )
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `src/aios/integrations/config.py` | IntegrationConfig, Registry, loading from YAML |
| `src/aios/integrations/validation.py` | ResourceValidator classes, ValidationRegistry |
| `src/aios/integrations/state.py` | IntegrationState enum, result dataclasses |
| `src/aios/integrations/__init__.py` | Public API exports |
| `src/aios/cli/commands/onboard.py` | CLI command implementations |
| `src/aios/cli/main.py` | CLI entry point (typer → argparse bridge) |
| `src/aios/services/integration_status.py` | Dashboard backend service |
| `src/aios/events/core/types.py` | EventType.INTEGRATION_STATUS_CHANGED |
| `src/aios/events/core/category.py` | Category mapping for new event type |
| `src/aios/core/kernel.py` | Kernel boot wiring for IntegrationStatusService |
| `config/integrations.yaml` | Per-integration mode/user resource config |
| `config/defaults.yaml` | Service config for integration_status |
| `tests/integration/test_user_resource_onboarding.py` | 20 gated integration tests |
| `tests/unit/test_event_type.py` | EventType count (133) |
| `tests/unit/test_event_type_registry.py` | Registry count (133) |

---

## Terminal 3 Handoff Artifacts

| Artifact | Purpose |
|----------|---------|
| `ONBOARDING_IMPLEMENTATION_REPORT.md` | Complete implementation summary |
| `ONBOARDING_TEST_RESULTS.json` | Test results for all 20 gated tests |
| `ONBOARDING_SECURITY_AUDIT.md` | Security gate verification |
| `ONBOARDING_DASHBOARD_CONTRACT.md` | Status service API for frontend |

**Terminal 3 retains independent verification authority** — these are evidence artifacts, not certifications.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-08-28 | Initial production release (M12) |

---

## Support

For issues with the onboarding layer:
1. Check this guide's Troubleshooting section
2. Run `aios onboard status --json` for current state
3. Check kernel logs for SecurityManager/CapabilityManager decisions
4. File issue with: integration name, state, validation errors, config snippet (redacted)