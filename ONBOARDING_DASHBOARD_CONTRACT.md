# USER RESOURCE ONBOARDING — Dashboard Contract

**Version:** 1.0.0  
**Date:** 2026-08-28  
**Milestone:** M12  
**Status:** Production Ready — For Frontend Integration  

---

## Overview

This document defines the **Dashboard Backend Contract** for the AI-OS Integration Status Dashboard. The backend service is `IntegrationStatusService` registered as `core.integration_status` in the ServiceRegistry.

Frontend dashboards should use this contract to display real-time integration status, trigger onboarding actions, and subscribe to live updates.

---

## Service Registration

```python
# Kernel initialization (src/aios/core/kernel.py)
async def _init_integration_status(self):
    from aios.services.integration_status import (
        IntegrationStatusService,
        create_integration_status_service,
        SERVICE_KEY,
    )
    self._integration_status_service = await create_integration_status_service(
        config=self._config.get("services", {}).get("integration_status", {}),
        event_bus=self._event_bus,
    )
    self._service_registry.register(SERVICE_KEY, self._integration_status_service)
```

**Service Key**: `core.integration_status`  
**Factory**: `create_integration_status_service(config, event_bus)`  
**Config Section**: `services.integration_status` (in `config/defaults.yaml`)

---

## Configuration (config/defaults.yaml)

```yaml
services:
  integration_status:
    health_check_interval_seconds: 60  # Periodic health check interval
    # Additional config options can be added here
```

---

## REST-like API (Programmatic)

The service exposes the following async methods for frontend consumption:

### `get_all_status() → List[IntegrationStatusReport]`

Returns status reports for all 14 canonical integrations.

```python
service = service_registry.get("core.integration_status")
reports = await service.get_all_status()
# Returns: List[IntegrationStatusReport]
```

### `get_status(name: str) → IntegrationStatusReport | None`

Returns status for a single integration.

```python
report = await service.get_status("obsidian")
# Returns: IntegrationStatusReport | None
```

### `get_all_status_dict(redact_secrets: bool = True) → List[dict]`

Machine-readable dict format (redacted by default).

```python
data = service.get_all_status_dict(redact_secrets=True)
# Returns: List[dict] with keys matching IntegrationStatusReport fields
```

### `get_status_dict(name: str, redact_secrets: bool = True) → dict | None`

Single integration as dict (redacted by default).

```python
data = service.get_status_dict("obsidian", redact_secrets=True)
# Returns: dict | None
```

---

## Data Models

### IntegrationStatusReport (Primary)

```python
@dataclass
class IntegrationStatusReport:
    integration_name: str                    # Canonical ID (e.g., "obsidian")
    state: IntegrationState                  # Current state enum
    mode: str                                # "mock" | "real"
    real_allowed: bool                       # All three gates pass?
    user_resource_present: bool              # User has verified resource
    real_gated: bool                         # Requires env gate
    requires_user_resource: bool             # This integration needs user resource
    last_validated: datetime | None          # Timestamp of last validation
    last_health_check: datetime | None       # Timestamp of last health check
    validation_details: dict                 # Validator output details
    health_details: dict                     # Health check output details
    errors: list[str]                        # Validation/connection errors
    warnings: list[str]                      # Non-fatal warnings
    provenance: dict                         # C14 advisory provenance
```

### IntegrationState Enum

```python
class IntegrationState(str, Enum):
    ABSENT = "absent"
    CONFIGURED = "configured"
    VALIDATED = "validated"
    CONNECTED = "connected"
    OPERATIONALLY_VERIFIED = "operationally_verified"
    BLOCKED = "blocked"
    DEGRADED = "degraded"
```

### Dict Output Format (for JSON serialization)

```json
{
  "integration_name": "obsidian",
  "state": "validated",
  "mode": "real",
  "real_allowed": true,
  "user_resource_present": true,
  "real_gated": true,
  "requires_user_resource": true,
  "last_validated": "2026-08-28T12:00:00.000000",
  "last_health_check": "2026-08-28T12:05:00.000000",
  "validation_details": {
    "vault_path": "/path/to/vault",
    "writable": true,
    "has_obsidian_dir": true,
    "has_md_files": true
  },
  "health_details": {},
  "errors": [],
  "warnings": [],
  "provenance": {
    "validator": "ObsidianValidator",
    "c14_advisory": true,
    "timestamp": "2026-08-28T12:00:00.000000"
  }
}
```

**All secrets redacted** (tokens, keys, passwords → `***REDACTED***`)

---

## Real-Time Updates: Event Subscription

Frontend should subscribe to `INTEGRATION_STATUS_CHANGED` events via EventBus.

### Event Type

```python
EventType.INTEGRATION_STATUS_CHANGED  # "INTEGRATION_STATUS_CHANGED"
```

### Event Category

```python
EventCategory.DIAGNOSTIC
```

### Event Payload

```json
{
  "integration_name": "obsidian",
  "previous_state": "validated",
  "new_state": "connected",
  "changed_at": "2026-08-28T12:00:00.000000",
  "details": {
    "connection_method": "local_fs",
    "adapter": "ObsidianAdapter"
  }
}
```

### Subscription Example (Pseudo-code)

```javascript
// Frontend EventBus subscription
eventBus.subscribe("INTEGRATION_STATUS_CHANGED", (event) => {
  const { integration_name, previous_state, new_state, changed_at, details } = event.payload;
  
  // Update UI for this integration
  updateIntegrationCard(integration_name, {
    state: new_state,
    previousState: previous_state,
    lastChange: changed_at,
    details
  });
  
  // Optional: Show toast/notification
  if (new_state === "operationally_verified") {
    showSuccess(`${integration_name} is now operational`);
  } else if (new_state === "degraded") {
    showWarning(`${integration_name} degraded`);
  } else if (new_state === "blocked") {
    showError(`${integration_name} blocked: ${details?.error || "unknown"}`);
  }
});
```

---

## CLI Bridge for Dashboard Actions

Dashboard can shell out to CLI for user-triggered actions:

| Action | CLI Command | Notes |
|--------|-------------|-------|
| Validate | `aios onboard validate <name>` | Safe, read-only |
| Connect (real) | `AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard connect <name>` | Requires env gate |
| Health check | `AIOS_REAL_INTEGRATION_ENABLED=1 aios onboard health <name>` | Safe |
| Enable real mode | `aios onboard enable <name> --confirm` | Requires confirmation |
| Disable real mode | `aios onboard disable <name>` | Safe |
| Full status | `aios onboard status --json` | Machine-readable |

**Security**: All real operations require `AIOS_REAL_INTEGRATION_ENABLED=1` env var.

---

## Frontend Integration Guide

### 1. Initial Load

```python
# On dashboard mount
async def load_dashboard():
    reports = service.get_all_status_dict(redact_secrets=True)
    for report in reports:
        render_integration_card(report)
    # Subscribe to live updates
    event_bus.subscribe("INTEGRATION_STATUS_CHANGED", handle_state_change)
```

### 2. Integration Card Component

```tsx
interface IntegrationCardProps {
  integrationName: string;
  state: IntegrationState;
  mode: "mock" | "real";
  realAllowed: boolean;
  userResourcePresent: boolean;
  lastValidated: string | null;
  lastHealthCheck: string | null;
  errors: string[];
  warnings: string[];
  validationDetails: Record<string, any>;
}

function IntegrationCard({...}: IntegrationCardProps) {
  const stateColors = {
    absent: "gray",
    configured: "blue",
    validated: "green",
    connected: "purple",
    operationally_verified: "emerald",
    blocked: "red",
    degraded: "amber"
  };
  
  return (
    <Card className={`border-l-4 border-${stateColors[state]}-500`}>
      <CardHeader>
        <h3>{integrationName}</h3>
        <Badge variant={mode === "real" ? "default" : "secondary"}>
          {mode}
        </Badge>
      </CardHeader>
      <CardContent>
        <StateBadge state={state} />
        {realAllowed && <GreenDot title="Real operations permitted" />}
        {userResourcePresent && <CheckIcon title="User resource verified" />}
        {errors.length > 0 && (
          <Alert variant="destructive">{errors.join(", ")}</Alert>
        )}
        <DetailsPanel details={validationDetails} />
      </CardContent>
      <CardFooter>
        <Button onClick={() => validate(integrationName)} disabled={state === "validated"}>
          Validate
        </Button>
        <Button onClick={() => connect(integrationName)} disabled={state !== "validated" || !realAllowed}>
          Connect
        </Button>
        <Button onClick={() => healthCheck(integrationName)} disabled={state !== "connected" && state !== "operationally_verified"}>
          Health Check
        </Button>
      </CardFooter>
    </Card>
  );
}
```

### 3. State Change Handler

```python
def handle_state_change(event):
    integration_name = event.payload["integration_name"]
    new_state = event.payload["new_state"]
    previous_state = event.payload["previous_state"]
    
    # Update card state
    card = get_card(integration_name)
    card.update_state(new_state)
    
    # Show transition animation
    animate_transition(previous_state, new_state)
    
    # Log to activity feed
    add_activity(f"{integration_name}: {previous_state} → {new_state}")
```

---

## Integration Matrix (14 Canonical)

| Integration | ID | Requires User Resource | Typical State Flow |
|-------------|-----|------------------------|-------------------|
| Hermes Agent (ACP) | `hermes_agent_acp` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Hermes Agent (MCP) | `hermes_agent_ext` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Playwright MCP | `playwright_mcp` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Obsidian | `obsidian` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Graphify | `graphify` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Claude-Mem | `claude_mem` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Notion | `notion` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Agent Reach | `agent_reach` | **No** | CONFIGURED → VALIDATED → OPERATIONALLY_VERIFIED |
| FreeLLMAPI | `freellmapi` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |
| Anthropic | `anthropic` | Yes (runtime) | CONFIGURED → VALIDATED (runtime) |
| OpenAI | `openai` | Yes (runtime) | CONFIGURED → VALIDATED (runtime) |
| Generic MCP | `generic_mcp` | Yes | CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED |

---

## Error Handling

### Common Error Patterns

| Scenario | State | Errors Array | User Action |
|----------|-------|--------------|-------------|
| Missing resource | `BLOCKED` | `["user resource absent: vault path not configured"]` | Set `user_resource_present: true` in config |
| Invalid path | `BLOCKED` | `["validation failed: path does not exist"]` | Fix path in config |
| Unreachable endpoint | `BLOCKED` | `["validation failed: connection refused"]` | Check service running |
| Env gate closed | `BLOCKED` | `["REAL connection not permitted: env gate closed"]` | Set `AIOS_REAL_INTEGRATION_ENABLED=1` |
| Security gate fail | `BLOCKED` | `["MCP security validation failed: ..."]` | Check MCP config |
| Health check fail | `DEGRADED` | `["health check failed: timeout"]` | Check external service |

---

## Performance Considerations

| Metric | Target | Notes |
|--------|--------|-------|
| `get_all_status_dict()` latency | < 10ms | In-memory registry, no I/O |
| Periodic health check interval | 60s (configurable) | Only runs on REAL + CONNECTED |
| Event emission latency | < 5ms | Direct EventBus publish |
| Memory footprint | ~50KB | 14 IntegrationStatusReport objects |

---

## Testing the Contract

### Backend Service Tests

```bash
# Unit tests
pytest tests/unit/test_integration_status_service.py -v

# Integration tests (gated)
AIOS_REAL_INTEGRATION_ENABLED=1 pytest tests/integration/test_dashboard_contract.py -v
```

### Expected Test Coverage

| Test | Coverage |
|------|----------|
| Service registration in kernel | ✅ |
| `get_all_status()` returns 14 items | ✅ |
| `get_status(name)` returns correct report | ✅ |
| Dict output redacted by default | ✅ |
| Event emitted on state change | ✅ |
| Event payload matches contract | ✅ |
| Periodic health checks run | ✅ |
| Health check only on REAL+CONNECTED | ✅ |

---

## Version Compatibility

| Contract Version | AI-OS Version | Breaking Changes |
|------------------|---------------|------------------|
| 1.0.0 | M12 (v1.0.0) | Initial release |

**Breaking Change Policy**: Contract version bumped on any field removal/type change. New fields added as optional.

---

## Support

For dashboard integration issues:
1. Check this contract matches `IntegrationStatusReport` dataclass
2. Verify EventBus subscription to `INTEGRATION_STATUS_CHANGED`
3. Confirm `redact_secrets=True` for all user-facing outputs
4. Report discrepancies with: expected vs actual payload, integration name, state

---

**Contract Authority**: This document defines the binding interface between `IntegrationStatusService` and frontend dashboards. Changes require M13+ milestone planning.