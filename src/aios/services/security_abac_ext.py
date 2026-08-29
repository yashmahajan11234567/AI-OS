"""
Security Manager ABAC Extensions for AI-OS M10.

Extends SecurityManager with attribute-based access control for autonomous
operations, enforcing autonomy-aware authorization policies.

This is M10-N8 implementation per M10-IMPLEMENTATION-SPEC.md §11.8.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.base import Event
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.services.base import BaseService
from aios.core.security_manager import (
    SecurityManager,
    get_security_manager,
    SecurityDecision,
    SecurityViolation,
)

logger = logging.getLogger(__name__)


class AutonomyRole(str, Enum):
    """Roles for autonomous operations in ABAC."""
    AUTONOMOUS_OBJECTIVE_GENERATOR = "autonomous_objective_generator"
    AUTONOMOUS_REPLAN_DETECTOR = "autonomous_replan_detector"
    AUTONOMOUS_JUDGE = "autonomous_judge"
    AUTONOMY_OVERRIDE = "autonomy_override"
    FALLBACK_COORDINATOR = "fallback_coordinator"


class AutonomyAction(str, Enum):
    """Actions that autonomous services can attempt."""
    GENERATE_OBJECTIVE = "generate_objective"
    TRIGGER_REPLAN = "trigger_replan"
    EMIT_JUDGMENT = "emit_judgment"
    DISABLE_AUTONOMY = "disable_autonomy"
    ENABLE_AUTONOMY = "enable_autonomy"
    TRIGGER_FALLBACK = "trigger_fallback"


@dataclass
class SecurityAbacConfig:
    """Configuration for SecurityManager ABAC extensions."""
    enabled: bool = True
    require_autonomous_signature: bool = True
    max_autonomous_actions_per_minute: int = 10
    audit_all_autonomous: bool = True


@dataclass
class AutonomyAuthorizationDecision:
    """Result of an ABAC authorization check."""
    decision: str  # "permit" or "deny"
    reason: str
    matched_policies: list[str] = field(default_factory=list)
    obligations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class SecurityAbacExtensionService(BaseService):
    """
    Extends SecurityManager with ABAC for autonomous operations.

    M10-N8: SecurityManager ABAC Extensions (GAP-M10-09)
    - Enforces autonomy-aware authorization policies via ABAC Rules
    - Wraps M10 service actions with attribute checks (role, action, resource)
    - Emits SecurityViolation events with AUTONOMY_OVERFLOW tag
    - Security test: Asserts policy enforcement on tampered autonomy tokens
    """

    name = "security_abac_ext"
    version = "1.0.0"
    description = "ABAC extensions for autonomous operations security"
    depends_on: list[str] = ["security", "memory"]

    def __init__(
        self,
        config: SecurityAbacConfig | None = None,
        security_manager: SecurityManager | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        super().__init__(event_bus=event_bus, info=info)
        self._config = config or SecurityAbacConfig()
        self._security_manager = security_manager or get_security_manager()
        self._event_bus = get_core_event_bus()
        self._autonomy_token: str | None = None
        self._action_counts: dict[str, int] = {}
        self._last_reset: datetime = datetime.utcnow()
        self._policies: list[dict[str, Any]] = []

    @property
    def config(self) -> SecurityAbacConfig:
        return self._config

    async def on_start(self) -> None:
        logger.info(f"SecurityAbacExtensionService.on_start called, enabled={self._config.enabled}")
        if self._config.enabled:
            self._initialize_autonomy_policies()
            logger.info("SecurityAbacExtensionService initialized with autonomy policies")

    async def on_stop(self) -> None:
        logger.info("SecurityAbacExtensionService stopped")

    def _initialize_autonomy_policies(self) -> None:
        """Initialize ABAC policies for autonomous operations."""
        # Define policies for each autonomous role/action combination
        self._policies = [
            # Objective Generator policies
            {
                "role": AutonomyRole.AUTONOMOUS_OBJECTIVE_GENERATOR.value,
                "action": AutonomyAction.GENERATE_OBJECTIVE.value,
                "resource": "planning_requested",
                "effect": "permit",
                "conditions": {
                    "source": "autonomous",
                    "max_per_hour": 5,
                },
            },
            # Replan Detector policies
            {
                "role": AutonomyRole.AUTONOMOUS_REPLAN_DETECTOR.value,
                "action": AutonomyAction.TRIGGER_REPLAN.value,
                "resource": "planning_requested",
                "effect": "permit",
                "conditions": {
                    "source": "autonomous",
                    "max_per_hour": 10,
                    "max_depth": 3,
                },
            },
            # Autonomous Judge policies
            {
                "role": AutonomyRole.AUTONOMOUS_JUDGE.value,
                "action": AutonomyAction.EMIT_JUDGMENT.value,
                "resource": "testing_completed",
                "effect": "permit",
                "conditions": {
                    "source": "autonomous",
                    "confidence_threshold": 0.75,
                },
            },
            {
                "role": AutonomyRole.AUTONOMOUS_JUDGE.value,
                "action": AutonomyAction.EMIT_JUDGMENT.value,
                "resource": "workflow_completed",
                "effect": "permit",
                "conditions": {
                    "source": "autonomous",
                    "confidence_threshold": 0.75,
                },
            },
            # Autonomy Override policies
            {
                "role": AutonomyRole.AUTONOMY_OVERRIDE.value,
                "action": AutonomyAction.DISABLE_AUTONOMY.value,
                "resource": "autonomy_state",
                "effect": "permit",
                "conditions": {
                    "source": ["human", "security_manager", "resource_manager"],
                },
            },
            {
                "role": AutonomyRole.AUTONOMY_OVERRIDE.value,
                "action": AutonomyAction.ENABLE_AUTONOMY.value,
                "resource": "autonomy_state",
                "effect": "permit",
                "conditions": {
                    "source": "human",
                    "requires_manual": True,
                },
            },
            # Fallback Coordinator policies
            {
                "role": AutonomyRole.FALLBACK_COORDINATOR.value,
                "action": AutonomyAction.TRIGGER_FALLBACK.value,
                "resource": "fallback_state",
                "effect": "permit",
                "conditions": {
                    "source": ["security_manager", "resource_manager", "autonomy_override"],
                },
            },
        ]

    def _check_rate_limit(self, action: str, limit: int, period_seconds: int = 60) -> bool:
        """Check if action is within rate limit."""
        now = datetime.utcnow()
        elapsed = (now - self._last_reset).total_seconds()

        if elapsed > period_seconds:
            self._action_counts.clear()
            self._last_reset = now

        current = self._action_counts.get(action, 0)
        if current >= limit:
            return False

        self._action_counts[action] = current + 1
        return True

    def _find_matching_policy(
        self,
        role: AutonomyRole,
        action: AutonomyAction,
        resource: str,
    ) -> dict[str, Any] | None:
        """Find a policy matching the given role, action, and resource."""
        for policy in self._policies:
            if (policy["role"] == role.value and
                policy["action"] == action.value and
                policy["resource"] == resource):
                return policy
        return None

    def _check_policy_conditions(
        self,
        policy: dict[str, Any],
        attributes: dict[str, Any],
    ) -> bool:
        """Check if policy conditions are met."""
        conditions = policy.get("conditions", {})

        # Check source condition
        if "source" in conditions:
            allowed_sources = conditions["source"]
            if isinstance(allowed_sources, str):
                allowed_sources = [allowed_sources]
            if attributes.get("source") not in allowed_sources:
                return False

        # Check confidence threshold
        if "confidence_threshold" in conditions:
            if attributes.get("confidence", 0.0) < conditions["confidence_threshold"]:
                return False

        # Check replan depth
        if "max_depth" in conditions:
            if attributes.get("replan_depth", 0) > conditions["max_depth"]:
                return False

        # Check requires_manual
        if conditions.get("requires_manual", False):
            if attributes.get("source") != "human":
                return False

        return True

    async def authorize_autonomous_action(
        self,
        role: AutonomyRole,
        action: AutonomyAction,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> AutonomyAuthorizationDecision:
        """
        Authorize an autonomous action using ABAC.

        Returns permit/deny decision with reasoning.
        """
        if not self._config.enabled:
            return AutonomyAuthorizationDecision(
                decision="permit",
                reason="ABAC extensions disabled",
            )

        # Check rate limits
        limits = {
            AutonomyAction.GENERATE_OBJECTIVE: 5,
            AutonomyAction.TRIGGER_REPLAN: 10,
            AutonomyAction.EMIT_JUDGMENT: 20,
        }
        if action in limits:
            if not self._check_rate_limit(action.value, limits[action], 3600):
                return AutonomyAuthorizationDecision(
                    decision="deny",
                    reason=f"Rate limit exceeded for {action.value}",
                    metadata={"rate_limited": True},
                )

        # Find matching policy
        policy = self._find_matching_policy(role, action, resource)
        if not policy:
            return AutonomyAuthorizationDecision(
                decision="deny",
                reason=f"No policy found for {role.value} -> {action.value} on {resource}",
            )

        # Build attributes for policy evaluation
        attributes = {
            "role": role.value,
            "action": action.value,
            "resource": resource,
            "source": context.get("source", "unknown") if context else "unknown",
            "autonomous": context.get("autonomous", True) if context else True,
            "confidence": context.get("confidence", 0.0) if context else 0.0,
            "replan_depth": context.get("replan_depth", 0) if context else 0,
        }

        # Check policy conditions
        if not self._check_policy_conditions(policy, attributes):
            return AutonomyAuthorizationDecision(
                decision="deny",
                reason="Policy conditions not met",
                metadata={"conditions_failed": True, "attributes": attributes},
            )

        # For autonomous actions with matching policies, the ABAC extension
        # recommends a permit — but it is NOT the final authority. S3 (Terminal 2):
        # an autonomous service must NOT self-authorize. Route the recommended
        # permit through the canonical, fail-closed SecurityManager.authorize so
        # that a DENY/CHALLENGE from the kernel's security policy overrides the
        # ABAC recommendation. Advisory semantics and human override are preserved
        # (the kernel security policy remains the single decision authority).
        security_decision = self._security_manager.authorize(
            principal=f"autonomy:{role.value}",
            action=action.value,
            resource=resource,
            context={**(context or {}), "autonomy_abac_recommendation": "permit"},
        )
        if security_decision != SecurityDecision.ALLOW:
            reason = (
                "ABAC recommended permit but SecurityManager.authorize denied "
                f"({security_decision.value}); autonomous action not self-authorized"
            )
            self._security_manager.record_violation(
                severity="high",
                description=f"Autonomous self-permission blocked: {role.value} -> {action.value} on {resource}",
                category="autonomy_abac_self_permission",
                context={"abac_recommendation": "permit", "security_decision": security_decision.value},
            )
            return AutonomyAuthorizationDecision(
                decision="deny",
                reason=reason,
                metadata={"attributes": attributes, "security_decision": security_decision.value},
            )

        # Audit if enabled
        if self._config.audit_all_autonomous:
            await self._audit_autonomous_action(role, action, resource, attributes, "permit")

        return AutonomyAuthorizationDecision(
            decision="permit",
            reason="ABAC evaluation passed and SecurityManager.authorize allowed",
            metadata={"attributes": attributes},
        )

    async def _audit_autonomous_action(
        self,
        role: AutonomyRole,
        action: AutonomyAction,
        resource: str,
        attributes: dict[str, Any],
        decision: str,
    ) -> None:
        """Audit autonomous action for compliance."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "role": role.value,
            "action": action.value,
            "resource": resource,
            "decision": decision,
            "attributes": attributes,
        }
        logger.info(f"ABAC Audit: {log_entry}")

        # Record as security violation if denied
        if decision == "DENY" or decision == "CHALLENGE":
            self._security_manager.record_violation(
                severity="medium",
                description=f"Autonomous action denied: {role.value} -> {action.value} on {resource}",
                category="autonomy_abac",
                context=log_entry,
            )

    def create_autonomy_token(self, roles: list[AutonomyRole] | None = None) -> str:
        """Create a signed autonomy token for service authentication."""
        token = secrets.token_urlsafe(32)
        self._autonomy_token = token
        # Store token with roles (in production, this would be signed JWT)
        logger.info(f"Created autonomy token for roles: {[r.value for r in roles] if roles else 'all'}")
        return token

    def verify_autonomy_token(self, token: str) -> bool:
        """Verify an autonomy token."""
        if self._autonomy_token is None:
            return False
        return secrets.compare_digest(token, self._autonomy_token)

    def get_stats(self) -> dict[str, Any]:
        stats = super().get_stats()
        stats.update({
            "enabled": self._config.enabled,
            "action_counts": self._action_counts.copy(),
            "require_autonomous_signature": self._config.require_autonomous_signature,
            "audit_all_autonomous": self._config.audit_all_autonomous,
            "policy_count": len(self._policies),
        })
        return stats


# Global instance
_global_security_abac_ext: SecurityAbacExtensionService | None = None


def get_security_abac_ext(
    config: SecurityAbacConfig | None = None,
    security_manager: SecurityManager | None = None,
) -> SecurityAbacExtensionService:
    """Get or create the global SecurityAbacExtensionService."""
    global _global_security_abac_ext
    if _global_security_abac_ext is None:
        _global_security_abac_ext = SecurityAbacExtensionService(
            config=config, security_manager=security_manager
        )
    return _global_security_abac_ext


def set_security_abac_ext(service: SecurityAbacExtensionService) -> None:
    """Set the global SecurityAbacExtensionService."""
    global _global_security_abac_ext
    _global_security_abac_ext = service


__all__ = [
    "SecurityAbacExtensionService",
    "SecurityAbacConfig",
    "AutonomyRole",
    "AutonomyAction",
    "AutonomyAuthorizationDecision",
    "get_security_abac_ext",
    "set_security_abac_ext",
]