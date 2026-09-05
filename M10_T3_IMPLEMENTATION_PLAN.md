# M10-T3 Health & Readiness Implementation Plan

## Overview
Implement distinct liveness, readiness, and startup semantics with unified operational health reporting for AI-OS kernel.

## Key Files to Modify
1. `src/aios/core/kernel.py` - Main kernel with health state management
2. `src/aios/core/health_manager.py` - HealthManager integration
3. `src/aios/core/lifecycle_manager.py` - LifecycleManager integration
4. `src/aios/cli/commands/kernel/__init__.py` - CLI commands
5. `src/aios/services/dashboard_server.py` - HTTP endpoints
6. `tests/unit/test_m10_t3_health_readiness.py` - New tests

## Implementation Steps

### Step 1: Define Canonical Health State Vocabulary (in kernel.py)
```python
class CanonicalHealthState(Enum):
    STARTING = "starting"        # Kernel initialization in progress
    READY = "ready"              # Startup complete, LifecycleManager readiness gate passed
    RUNNING = "running"          # Fully operational
    DEGRADED = "degraded"        # Operational but with non-critical issues
    UNHEALTHY = "unhealthy"      # Critical issues, not fit for work
    STOPPING = "stopping"        # Graceful shutdown in progress
    STOPPED = "stopped"          # Graceful shutdown complete
    ERROR = "error"              # Unrecoverable error state
```

### Step 2: Map Existing States to Canonical States
- LifecycleState.UNINITIALIZED → STARTING
- LifecycleState.OPERATIONAL → RUNNING (or READY if startup just complete)
- LifecycleState.DEGRADED → DEGRADED
- LifecycleState.RECOVERY_IN_PROGRESS → RUNNING (or DEGRADED)
- LifecycleState.TERMINATED → STOPPED

### Step 3: Kernel Health File Enhancement
- Add canonical state to kernel.health JSON
- Include timestamp for staleness detection
- Add liveness/readiness sub-status
- Include dependency health summary

### Step 4: LifecycleManager Integration
- Add readiness_gate() method
- Track Phase 0-3 manager health_ready() status
- Emit events on state transitions

### Step 5: HealthManager Integration
- Aggregate dependency health
- Track overall_status as canonical state source
- Heartbeat mechanism

### Step 6: Heartbeat / Stale-State Detection
- Background task with configurable interval
- Update kernel.health timestamp
- Detect stale health (> 2x interval)

### Step 7: Shutdown State Handling
- Set state to STOPPING on shutdown start
- Set state to STOPPED on completion
- Write final health file before exit

### Step 8: CLI Commands
- `kernel alive` - liveness check (exit 0 if responsive)
- `kernel ready` - readiness check (exit 0 if ready for work)
- `kernel health` - enhanced with canonical state, liveness, readiness, staleness

### Step 9: HTTP Endpoints
- GET /alive - liveness
- GET /ready - readiness
- GET /health - detailed health JSON

### Step 10: Docker HEALTHCHECK Compatibility
- Ensure `aios kernel health` works as before
- Exit codes: 0=healthy/degraded, 1=unhealthy/stopping/stopped/error

### Step 11: Tests (~25 tests)
- Canonical state vocabulary tests
- State mapping tests
- CLI command tests
- HTTP endpoint tests
- Heartbeat/staleness tests
- Shutdown state tests
- Integration tests

### Step 12: Regression Test
- Run full test suite

### Step 13: Architectural Check
- Verify autonomy remains OFF
- Verify no governance/remediation authority
- Verify valid transition checking

## Timeline
- Steps 1-6: Core implementation (2-3 hours)
- Steps 7-10: CLI/HTTP/Docker (1-2 hours)
- Steps 11-13: Tests and validation (1-2 hours)