"""
Integration Configuration Types.

Core dataclasses and enums for integration configuration.
This module is dependency-free to avoid circular imports.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from aios.integrations.state import IntegrationState
else:
    # Runtime placeholder to avoid circular imports
    IntegrationState = None  # type: ignore


class IntegrationMode(str, Enum):
    """Per-integration execution mode."""

    MOCK = "mock"
    REAL = "real"

    @classmethod
    def coerce(cls, value: Any) -> "IntegrationMode":
        if isinstance(value, IntegrationMode):
            return value
        if value is None:
            return cls.MOCK
        s = str(value).strip().lower()
        if s in ("real", "live", "true"):
            return cls.REAL
        return cls.MOCK


# Environment-variable gate used by gated real-operational tests (PHASE 6).
# When unset (the default), no REAL external operation is performed even if the
# integration is configured ``mode: real`` — the gate keeps CI/regression safe.
REAL_OPERATION_ENV = "AIOS_REAL_INTEGRATION_ENABLED"


@dataclass
class IntegrationConfig:
    """
    Resolved configuration for one external integration.

    Attributes:
        name: integration id (matches MCP ``server_id`` / kernel capability id).
        mode: ``mock`` or ``real``. Default ``mock`` (fail-closed).
        real_gated: if True, a REAL connection also requires the env gate
            ``AIOS_REAL_INTEGRATION_ENABLED`` to be set (used by gated tests).
        requires_user_resource: human-supplied resource (vault path, API key,
            subprocess repo, browser, etc.) that is ABSENT by default. The
            integration can never be CONNECTED/OPERATIONALLY VERIFIED until the
            user provides this. Terminal 2 never fabricates it.
        user_resource_present: whether the user-supplied resource has been
            detected as present in this environment (PRESENT / ABSENT / UNKNOWN
            — we only ever set PRESENT via explicit, verifiable detection).
        notes: free-text status note for the matrix.
        state: current lifecycle state (VALIDATED, CONNECTED, etc.)
        validation_result: most recent validation outcome
        last_validated: timestamp of last validation
        health_check_result: most recent health check outcome
        last_health_check: timestamp of last health check
    """

    name: str
    mode: IntegrationMode = IntegrationMode.MOCK
    real_gated: bool = True
    requires_user_resource: bool = True
    user_resource_present: bool = False
    notes: str = ""
    state: "IntegrationState" = None  # type: ignore[assignment]  # default to CONFIGURED in __post_init__
    validation_result: "ValidationResult" = None  # type: ignore[assignment]
    last_validated: datetime | None = None
    health_check_result: "HealthCheckResult" = None  # type: ignore[assignment]
    last_health_check: datetime | None = None

    @property
    def is_real(self) -> bool:
        return self.mode == IntegrationMode.REAL

    @property
    def is_mock(self) -> bool:
        return self.mode == IntegrationMode.MOCK

    def real_allowed(self) -> bool:
        """
        Return True only if a REAL external connection is currently permitted.

        Fail-closed: REAL is allowed iff ``mode == real`` AND (not gated OR the
        env gate is set) AND the required user resource is present.
        """
        if not self.is_real:
            return False
        if self.real_gated and os.environ.get(REAL_OPERATION_ENV, "").lower() not in (
            "1", "true", "yes", "on",
        ):
            return False
        if self.requires_user_resource and not self.user_resource_present:
            return False
        return True

    def status_label(self) -> str:
        """Human-readable pipeline state for the integration matrix."""
        if self.is_mock:
            return "CONFIGURED (mock)"
        if not self.real_allowed():
            if not self.user_resource_present:
                return "CONFIGURED (real) - BLOCKED: user resource absent"
            return "CONFIGURED (real) - BLOCKED: env gate closed"
        return "REAL OPERATION PERMITTED"

    def validate_resources(self, validation_registry: "ValidationRegistry" = None) -> "ValidationResult":
        """Run resource validation for this integration."""
        from aios.integrations.state import IntegrationState, can_transition
        if validation_registry is None:
            from aios.integrations.validation import ValidationRegistry
            validation_registry = ValidationRegistry()
        result = validation_registry.validate(self.name)

        # Update state if validating from CONFIGURED or BLOCKED
        if self.state in (IntegrationState.CONFIGURED, IntegrationState.BLOCKED):
            if can_transition(self.state, result.state):
                self.state = result.state
        self.validation_result = result
        self.last_validated = result.validated_at
        return result

    def attempt_connection(self) -> "ConnectionResult":
        """Attempt REAL connection if validated and permitted. Fail-closed."""
        from aios.integrations.state import IntegrationState, ConnectionResult

        # Fail-closed: require validation passed and real_allowed
        if self.state != IntegrationState.VALIDATED:  # type: ignore
            return ConnectionResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.name,
                connected=False,
                errors=[f"Cannot connect from state {self.state.value}; must be VALIDATED"],
            )

        if not self.real_allowed():
            return ConnectionResult(
                state=IntegrationState.BLOCKED,
                integration_name=self.name,
                connected=False,
                errors=["REAL connection not permitted: check mode, env gate, and user resource"],
            )

        # This is a placeholder - actual connection logic lives in adapters
        return ConnectionResult(
            state=IntegrationState.CONNECTED if self.real_allowed() else IntegrationState.BLOCKED,
            integration_name=self.name,
            connected=self.real_allowed(),
            details={"message": "Connection delegated to adapter; this is a framework placeholder"},
        )

    def run_health_check(self) -> "HealthCheckResult":
        """Run operational health check. Updates state to OPERATIONALLY_VERIFIED or DEGRADED."""
        from aios.integrations.state import IntegrationState, HealthCheckResult, can_transition

        # Placeholder - actual health checks implemented per-adapter
        if self.state not in (IntegrationState.CONNECTED, IntegrationState.OPERATIONALLY_VERIFIED):  # type: ignore
            result = HealthCheckResult(
                state=IntegrationState.DEGRADED,
                integration_name=self.name,
                healthy=False,
                errors=[f"Health check requires CONNECTED state; currently {self.state.value}"],
            )
        else:
            # In mock mode, health check passes
            if self.is_mock:
                result = HealthCheckResult(
                    state=IntegrationState.OPERATIONALLY_VERIFIED,
                    integration_name=self.name,
                    healthy=True,
                    details={"mode": "mock", "note": "Mock mode always healthy"},
                )
            else:
                # REAL mode: delegate to adapter
                result = HealthCheckResult(
                    state=IntegrationState.OPERATIONALLY_VERIFIED,
                    integration_name=self.name,
                    healthy=True,
                    details={"mode": "real", "note": "Health check delegated to adapter"},
                )

        if can_transition(self.state, result.state):  # type: ignore
            self.state = result.state  # type: ignore
        self.health_check_result = result
        self.last_health_check = result.checked_at
        return result

    def get_status_report(self) -> "IntegrationStatusReport":
        """Generate a clean status report for dashboard consumption."""
        from aios.integrations.state import IntegrationStatusReport

        return IntegrationStatusReport(
            integration_name=self.name,
            state=self.state,  # type: ignore
            mode=self.mode.value,
            real_allowed=self.real_allowed(),
            user_resource_present=self.user_resource_present,
            real_gated=self.real_gated,
            requires_user_resource=self.requires_user_resource,
            last_validated=self.last_validated,
            last_health_check=self.last_health_check,
            validation_details=self.validation_result.details if self.validation_result else {},
            health_details=self.health_check_result.details if self.health_check_result else {},
            errors=self.validation_result.errors if self.validation_result else [],
            warnings=self.validation_result.warnings if self.validation_result else [],
            provenance=self.validation_result.provenance if self.validation_result else {},
        )


@dataclass
class IntegrationConfigRegistry:
    """In-memory registry of per-integration resolved configs."""

    _entries: dict[str, IntegrationConfig] = field(default_factory=dict)

    def add(self, cfg: IntegrationConfig) -> None:
        self._entries[cfg.name] = cfg

    def get(self, name: str) -> IntegrationConfig | None:
        return self._entries.get(name)

    def resolve_mode(self, name: str) -> IntegrationMode:
        entry = self._entries.get(name)
        if entry is None:
            return IntegrationMode.MOCK  # fail-closed default
        return entry.mode

    def real_allowed(self, name: str) -> bool:
        entry = self._entries.get(name)
        if entry is None:
            return False  # fail-closed default
        return entry.real_allowed()

    def all(self) -> dict[str, IntegrationConfig]:
        return dict(self._entries)


# Canonical integration ids (mirrors the FINAL integration matrix).
CANONICAL_INTEGRATIONS = (
    "hermes_agent_acp",   # ACP worker subprocess
    "hermes_agent_ext",   # MCP fallback worker
    "playwright_mcp",     # @playwright/mcp browser automation
    "obsidian",           # local knowledge vault
    "graphify",           # derived knowledge graph
    "claude_mem",         # contextual memory retrieval
    "notion",             # planning (advisory)
    "agent_reach",        # agent communication protocol
    "freellmapi",         # local LLM provider (dev/test only)
    "anthropic",          # standard model provider
    "openai",             # standard model provider
)


DEFAULT_CONFIG_PATH = Path("config/integrations.yaml")


def load_integrations_config(path: Path = DEFAULT_CONFIG_PATH) -> IntegrationConfigRegistry:
    """
    Load per-integration modes from ``config/integrations.yaml``.

    File format (all keys optional; anything omitted defaults to mock +
    requires_user_resource + gated). Example::

        integrations:
          obsidian:
            mode: real
            user_resource_present: true   # set ONLY after verifiable detection
          notion:
            mode: real

    Fail-closed: an integration named in the file but missing ``mode`` defaults
    to mock. A parsed ``mode: real`` is honored but ``real_allowed()`` still
    enforces the env gate + user-resource presence.
    """
    from aios.config.loader import _load_yaml_file
    from aios.integrations.state import IntegrationState

    registry = IntegrationConfigRegistry()
    data: dict[str, Any] = {}
    try:
        # Accept both str and Path for backwards compatibility with callers.
        _path = Path(path) if isinstance(path, str) else path
        data = _load_yaml_file(_path) or {}
    except Exception:
        data = {}

    integrations = data.get("integrations", {}) if isinstance(data, dict) else {}

    # Seed every canonical integration with fail-closed defaults.
    for name in CANONICAL_INTEGRATIONS:
        registry.add(
            IntegrationConfig(
                name=name,
                mode=IntegrationMode.MOCK,
                real_gated=True,
                requires_user_resource=True,
                user_resource_present=False,
                state=IntegrationState.CONFIGURED,
            )
        )

    if isinstance(integrations, dict):
        for name, spec in integrations.items():
            spec = spec or {}
            entry = registry.get(name) or IntegrationConfig(name=name, state=IntegrationState.CONFIGURED)
            entry.mode = IntegrationMode.coerce(spec.get("mode"))
            # user_resource_present is only ever true when the operator has set
            # it explicitly AND it is verifiable; we never auto-detect it here.
            entry.user_resource_present = bool(spec.get("user_resource_present", False))
            entry.real_gated = bool(spec.get("real_gated", True))
            entry.requires_user_resource = bool(spec.get("requires_user_resource", True))
            entry.notes = str(spec.get("notes", ""))
            registry.add(entry)

    return registry


def assert_real_allowed(registry: IntegrationConfigRegistry, name: str) -> None:
    """
    Raise ``RuntimeError`` unless a REAL external connection is currently permitted.

    Adapters call this immediately before establishing any live connection so a
    misconfiguration / missing env gate fails closed instead of reaching a real
    external endpoint.
    """
    entry = registry.get(name)
    if entry is None or not entry.real_allowed():
        reason = entry.status_label() if entry else "integration unknown (fail-closed)"
        raise RuntimeError(
            f"REAL external operation for '{name}' is NOT permitted: {reason}. "
            f"Set mode: real in {DEFAULT_CONFIG_PATH} and enable the env gate "
            f"{REAL_OPERATION_ENV} (and provide the required user resource) to proceed."
        )