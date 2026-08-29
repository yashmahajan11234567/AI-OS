"""
Integration State Management for User Resource Onboarding Layer.

Defines the 7-state integration state machine and status report dataclasses
used throughout the onboarding workflow.

States:
    ABSENT              - Integration not configured at all
    CONFIGURED          - Integration present in config, mode set (mock/real)
    VALIDATED           - Resource validation passed (user resource detected)
    CONNECTED           - Real connection established (requires env gate)
    OPERATIONALLY_VERIFIED - Health check passed, fully operational
    BLOCKED             - Validation failed, cannot proceed
    DEGRADED            - Was operational, now failing health checks
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class IntegrationState(str, Enum):
    """7-state integration lifecycle state machine."""

    ABSENT = "absent"
    CONFIGURED = "configured"
    VALIDATED = "validated"
    CONNECTED = "connected"
    OPERATIONALLY_VERIFIED = "operationally_verified"
    BLOCKED = "blocked"
    DEGRADED = "degraded"

    # Terminal states for quick checks
    @property
    def is_terminal_success(self) -> bool:
        return self == IntegrationState.OPERATIONALLY_VERIFIED

    @property
    def is_terminal_failure(self) -> bool:
        return self in (IntegrationState.BLOCKED, IntegrationState.DEGRADED)

    @property
    def is_operational(self) -> bool:
        return self in (
            IntegrationState.CONNECTED,
            IntegrationState.OPERATIONALLY_VERIFIED,
        )

    @property
    def requires_user_action(self) -> bool:
        return self in (IntegrationState.BLOCKED, IntegrationState.DEGRADED)


# Success path ordering: ABSENT → CONFIGURED → VALIDATED → CONNECTED → OPERATIONALLY_VERIFIED
STATE_ORDER = [
    IntegrationState.ABSENT,
    IntegrationState.CONFIGURED,
    IntegrationState.VALIDATED,
    IntegrationState.CONNECTED,
    IntegrationState.OPERATIONALLY_VERIFIED,
]


def can_transition(from_state: IntegrationState, to_state: IntegrationState) -> bool:
    """
    Validate state transition per the state machine.

    Rules:
    - Can always go to BLOCKED or DEGRADED from any state (failure)
    - Success path must follow STATE_ORDER
    - Cannot skip states on success path
    - From DEGRADED can go back to VALIDATED (recovery)
    - From BLOCKED can go to CONFIGURED (retry after fix)
    """
    if to_state in (IntegrationState.BLOCKED, IntegrationState.DEGRADED):
        return True  # Failure transitions always allowed

    if from_state == IntegrationState.DEGRADED and to_state == IntegrationState.VALIDATED:
        return True  # Recovery path

    if from_state == IntegrationState.BLOCKED and to_state == IntegrationState.CONFIGURED:
        return True  # Retry path

    # Success path: must follow exact order
    try:
        from_idx = STATE_ORDER.index(from_state)
        to_idx = STATE_ORDER.index(to_state)
        return to_idx == from_idx + 1
    except ValueError:
        return False


@dataclass
class ValidationResult:
    """Result of a resource validation procedure."""

    state: IntegrationState
    integration_name: str
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validated_at: datetime = field(default_factory=datetime.now)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.state in (
            IntegrationState.VALIDATED,
            IntegrationState.CONNECTED,
            IntegrationState.OPERATIONALLY_VERIFIED,
        )

    @property
    def blocked(self) -> bool:
        return self.state == IntegrationState.BLOCKED


@dataclass
class HealthCheckResult:
    """Result of an operational health check."""

    state: IntegrationState
    integration_name: str
    healthy: bool
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionResult:
    """Result of a connection attempt."""

    state: IntegrationState
    integration_name: str
    connected: bool
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    connected_at: datetime = field(default_factory=datetime.now)
    provenance: dict[str, Any] = field(default_factory=dict)


@dataclass
class IntegrationStatusReport:
    """Complete status report for dashboard/external consumption."""

    integration_name: str
    state: IntegrationState
    mode: str  # "mock" | "real"
    real_allowed: bool
    user_resource_present: bool
    real_gated: bool
    requires_user_resource: bool
    last_validated: datetime | None = None
    last_health_check: datetime | None = None
    validation_details: dict[str, Any] = field(default_factory=dict)
    health_details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self, redact_secrets: bool = True) -> dict[str, Any]:
        """Serialize to dict, optionally redacting secrets."""
        from aios.security.secrets import redact_secrets as _redact_secrets

        data = {
            "integration_name": self.integration_name,
            "state": self.state.value,
            "mode": self.mode,
            "real_allowed": self.real_allowed,
            "user_resource_present": self.user_resource_present,
            "real_gated": self.real_gated,
            "requires_user_resource": self.requires_user_resource,
            "last_validated": self.last_validated.isoformat() if self.last_validated else None,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "validation_details": self.validation_details,
            "health_details": self.health_details,
            "errors": self.errors,
            "warnings": self.warnings,
            "provenance": self.provenance,
        }
        if redact_secrets:
            return _redact_secrets(data)
        return data