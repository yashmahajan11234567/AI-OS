"""
Root Cause Analyzer for AI-OS Hermes Kernel.

Analyzes failures to determine root cause, responsible service, and recommended action.
Routes failures back to the earliest responsible service instead of restarting everything.
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.manager import SubscribeOptions
from aios.events.core.subscription import HandlerPriority
from aios.events.core.types import EventType, SemanticVersion
from aios.events.types import LearningCaptured
from aios.services.learning import LearningService, get_learning_service

logger = logging.getLogger(__name__)


class FailureCategory(str, Enum):
    """Categories of failures for routing decisions."""

    TRANSIENT = "transient"  # Temporary issue, retry likely to succeed
    CONFIGURATION = "configuration"  # Configuration issue, return to planning
    CODE_DEFECT = "code_defect"  # Bug in generated code, return to coding
    DEPENDENCY = "dependency"  # External dependency issue, check deployment/ops
    RESOURCE = "resource"  # Resource exhaustion (memory, CPU, quota)
    SECURITY = "security"  # Security issue, route to security review
    PERFORMANCE = "performance"  # Performance degradation, route to perf review
    LOGIC_ERROR = "logic_error"  # Logic error in implementation
    UNKNOWN = "unknown"  # Cannot classify, ask human


class FailureSeverity(str, Enum):
    """Failure severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryAction(str, Enum):
    """Recommended recovery actions."""

    RETRY = "retry"  # Retry the same operation
    RETRY_WITH_BACKOFF = "retry_with_backoff"  # Retry with exponential backoff
    RETURN_TO_PLANNING = "return_to_planning"  # Restart from planning phase
    RETURN_TO_CODING = "return_to_coding"  # Restart from coding phase
    RETURN_TO_REVIEW = "return_to_review"  # Restart from review phase
    ESCALATE_TO_HUMAN = "escalate_to_human"  # Require human intervention
    ROLLBACK = "rollback"  # Rollback to previous version
    RESTART_SERVICE = "restart_service"  # Restart the failing service
    SKIP_STEP = "skip_step"  # Skip this step and continue


@dataclass
class FailureContext:
    """Context information about a failure."""

    failure_id: str
    event_type: str
    error: str
    error_type: str
    stack_trace: str | None = None
    service: str = ""
    task_id: str = ""
    workflow_id: str = ""
    correlation_id: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    attempt_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class RootCauseAnalysis:
    """Result of root cause analysis."""

    analysis_id: str
    failure_id: str
    category: FailureCategory
    severity: FailureSeverity
    root_cause: str
    responsible_service: str
    contributing_factors: list[str] = field(default_factory=list)
    recommended_action: RecoveryAction = RecoveryAction.ESCALATE_TO_HUMAN
    confidence: float = 0.0  # 0.0 to 1.0
    similar_failures: list[str] = field(default_factory=list)
    preventive_measures: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class RootCauseAnalyzer:
    """
    Analyzes failures to determine root cause and recommend recovery actions.

    Uses pattern matching, error classification, and historical data to:
    1. Classify the failure category
    2. Identify the responsible service
    3. Determine the best recovery action
    4. Route to the earliest responsible service
    """

    def __init__(self):
        # FIX 9: Use canonical EventBus (C1, Task 5) — single authority per process
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            logger.warning("Canonical EventBus not yet initialized; event subscriptions will be deferred")
        self._analyses: dict[str, RootCauseAnalysis] = {}
        self._failure_patterns: dict[str, dict] = {}
        self._service_responsibility: dict[str, list[str]] = {
            "planning": ["planning", "plan", "specification", "requirements"],
            "coding": ["coding", "code", "generation", "implementation", "syntax"],
            "review": ["review", "lint", "type", "security", "architecture", "performance"],
            "testing": ["test", "testing", "coverage", "assertion", "unit", "integration"],
            "deployment": ["deploy", "deployment", "container", "kubernetes", "infrastructure"],
            "operations": ["operations", "monitoring", "metrics", "logs", "alert", "incident"],
            "memory": ["memory", "storage", "cache", "retrieval", "consolidation"],
            "skills": ["skill", "skill_", "capability"],
            "mcp": ["mcp", "tool", "server", "client"],
            "council": ["council", "consensus", "deliberation", "vote"],
        }

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="RootCauseAnalyzer",
            version=SemanticVersion.parse("0.1.0"),
        )

        # Subscribe to failure events (only if event bus is available)
        self._subscribed = False
        if self._event_bus is not None:
            logger.debug("RootCauseAnalyzer subscribing to failure events")
            self._subscribe_to_events()
        else:
            logger.warning("Canonical EventBus not available; RCA subscriptions deferred")

    async def shutdown(self) -> None:
        """
        Shutdown the RootCauseAnalyzer, unsubscribing from all EventBus events.

        This ensures clean test isolation by removing handlers from the EventBus
        before the singleton is reset or the EventBus is shut down.
        """
        try:
            if self._event_bus is not None and self._subscribed:
                # Use UnsubscribeOptions to unsubscribe all events for this subscriber
                from aios.events.core.bus import UnsubscribeOptions
                self._event_bus.unsubscribe(UnsubscribeOptions(
                    subscriptionId=None,
                    eventTypes=None,
                    all_=True,
                    immediate=True,
                ))
                logger.debug("RootCauseAnalyzer unsubscribed from all events")
                self._subscribed = False
        except Exception as e:
            logger.warning(f"Error during RootCauseAnalyzer shutdown unsubscribe: {e}")

        self._event_bus = None

    def _subscribe_to_events(self) -> None:
        """Subscribe to failure events."""
        if self._event_bus is not None and not self._subscribed:
            self._event_bus.subscribe(
                SubscribeOptions(
                    subscriber=self._identity,
                    event_types=[EventType.RETRY_BUDGET_EXHAUSTED],
                    handler=self._on_retry_budget_exhausted,
                    handler_type="async",
                    priority=HandlerPriority.NORMAL,
                    metadata={"service_name": "root_cause_analyzer"},
                )
            )
            self._event_bus.subscribe(
                SubscribeOptions(
                    subscriber=self._identity,
                    event_types=[EventType.TASK_FAILED],
                    handler=self._on_task_failed,
                    handler_type="async",
                    priority=HandlerPriority.NORMAL,
                    metadata={"service_name": "root_cause_analyzer"},
                )
            )
            self._subscribed = True
            logger.debug("RootCauseAnalyzer subscribed to failure events")

    async def _on_retry_budget_exhausted(self, event: CoreEvent) -> None:
        """Handle RetryBudgetExhausted event."""
        try:
            logger.info(f"RootCauseAnalyzer received RETRY_BUDGET_EXHAUSTED event: {event.eventType}")
            payload = event.payload
            context = FailureContext(
                failure_id=payload.get("task_id", "unknown"),
                event_type="retry.budget_exhausted",
                error=payload.get("final_error", "Retry budget exhausted"),
                error_type="RetryBudgetExhausted",
                service=payload.get("service", "unknown"),
                task_id=payload.get("task_id", ""),
                correlation_id=str(event.correlationId) if event.correlationId else "",
                payload=payload,
                attempt_history=[],  # Could be populated from retry manager
            )
            await self.analyze(context, retry_budget_exhausted=True)
        except Exception as e:
            logger.exception("RCA handler failed for RETRY_BUDGET_EXHAUSTED: %s", e)

    async def _on_task_failed(self, event: CoreEvent) -> None:
        """Handle TaskFailed event."""
        try:
            logger.info(f"RootCauseAnalyzer received TASK_FAILED event: {event.eventType}")
            payload = event.payload
            context = FailureContext(
                failure_id=payload.get("task_id", "unknown"),
                event_type="task.failed",
                error=payload.get("error", "Unknown error"),
                error_type=payload.get("error_type", "UnknownError"),
                service=payload.get("service", "unknown"),
                task_id=payload.get("task_id", ""),
                correlation_id=str(event.correlationId) if event.correlationId else "",
                payload=payload,
            )
            await self.analyze(context, retry_budget_exhausted=payload.get("retryable", False) and payload.get("retry_count", 0) >= 3)
        except Exception as e:
            logger.exception("RCA handler failed for TASK_FAILED: %s", e)

    async def analyze(
        self,
        context: FailureContext,
        retry_budget_exhausted: bool = False,
    ) -> RootCauseAnalysis:
        """
        Analyze a failure and determine root cause.

        Args:
            context: Failure context
            retry_budget_exhausted: Whether retry budget is exhausted

        Returns:
            Root cause analysis
        """
        analysis_id = f"analysis_{context.failure_id}"
        logger.info(f"Analyzing failure {context.failure_id}: {context.error_type}")

        # Classify failure
        category = self._classify_failure(context)
        severity = self._assess_severity(context, category)

        # Identify responsible service
        responsible_service = self._identify_responsible_service(context, category)

        # Determine root cause
        root_cause = self._determine_root_cause(context, category)

        # Determine recovery action
        recommended_action = self._recommend_action(
            context, category, responsible_service, retry_budget_exhausted
        )

        # Calculate confidence
        confidence = self._calculate_confidence(context, category)

        # Find similar failures
        similar = self._find_similar_failures(context)

        # Generate preventive measures
        preventive = self._generate_preventive_measures(category, responsible_service)

        analysis = RootCauseAnalysis(
            analysis_id=analysis_id,
            failure_id=context.failure_id,
            category=category,
            severity=severity,
            root_cause=root_cause,
            responsible_service=responsible_service,
            recommended_action=recommended_action,
            confidence=confidence,
            similar_failures=similar,
            preventive_measures=preventive,
        )

        self._analyses[analysis_id] = analysis
        self._update_failure_patterns(context, analysis)

        # Emit events using canonical CoreEvent
        # NOTE: 'category' and 'service' are reserved base-contract fields (INV-EVT-011)
        # Use 'failure_category' and 'responsible_service' instead
        await self._emit_event(
            EventType.ROOT_CAUSE_ANALYZED,
            {
                "analysis_id": analysis_id,
                "failure_id": context.failure_id,
                "failure_category": category.value,
                "severity": severity.value,
                "root_cause": root_cause,
                "responsible_service": responsible_service,
                "recommended_action": recommended_action.value,
                "confidence": confidence,
            },
            context.correlation_id or context.failure_id,
        )

        await self._emit_event(
            EventType.FAILURE_CLASSIFIED,
            {
                "failure_id": context.failure_id,
                "failure_category": category.value,
                "severity": severity.value,
                "responsible_service": responsible_service,
            },
            context.correlation_id or context.failure_id,
        )

        # M9-N4 (spec §11.4) — RCA→Learning handoff.
        #
        # analyze() IS a coroutine, so when the bootstrap-created
        # LearningService is present we simply await the capture on the running
        # loop. The prior implementation juggled ``loop.create_task`` /
        # ``asyncio.run`` fallback chains inside an async method — fire-and-
        # forget tasks raced test teardown and ``asyncio.run`` inside a running
        # loop raises. Failures here are logged and swallowed ONLY in the sense
        # that analysis must still return: learning capture is advisory input
        # to planning (M9 §16), never a gate on RCA itself.
        try:
            learning_service = get_learning_service()
        except RuntimeError:
            # LearningService absent (minimal kernel / pre-bootstrap): fall back
            # to emitting the audit event so the capture can still happen
            # event-driven via MemoryService.handle_learning_captured consumers.
            await self._emit_event(
                EventType.AI_AGENT_AUDIT_EMITTED,  # LearningCaptured maps here
                {
                    "learning_id": f"learn_{analysis_id}",
                    "type": "failure_resolution",
                    "analysis_id": analysis_id,
                    "resolution": recommended_action.value,
                    "preventive_measures": preventive,
                    "captured_at": time.time(),
                },
                context.correlation_id or context.failure_id,
            )
        else:
            try:
                await learning_service.capture_learning_from_analysis(
                    analysis_id=analysis_id,
                    failure_category=category.value,
                    recommended_action=recommended_action.value,
                    root_cause=root_cause,
                    preventive_measures=preventive,
                )
            except Exception as exc:  # noqa: BLE001 — log + continue (spec §11.4)
                logger.warning(
                    "Failed to capture learning for %s via LearningService: %s",
                    analysis_id,
                    exc,
                )
                await self._emit_event(
                    EventType.AI_AGENT_AUDIT_EMITTED,
                    {
                        "learning_id": f"learn_{analysis_id}",
                        "type": "failure_resolution",
                        "analysis_id": analysis_id,
                        "resolution": recommended_action.value,
                        "preventive_measures": preventive,
                        "captured_at": time.time(),
                    },
                    context.correlation_id or context.failure_id,
                )

        logger.info(
            f"Root cause analysis complete: {category.value} -> {responsible_service} -> {recommended_action.value}"
        )
        return analysis

    def _classify_failure(self, context: FailureContext) -> FailureCategory:
        """Classify failure based on error type and context."""
        error_lower = context.error.lower()
        error_type_lower = context.error_type.lower()

        # Security keywords
        security_keywords = [
            "sql injection", "xss", "csrf", "authentication", "authorization",
            "permission", "access denied", "unauthorized", "vulnerability",
            "cve", "exploit", "injection", "path traversal",
        ]
        if any(kw in error_lower for kw in security_keywords):
            return FailureCategory.SECURITY

        # Transient errors (check early for timeout)
        transient_keywords = [
            "temporary", "transient", "retry", "intermittent", "flaky",
            "network", "connection reset", "timed out", "timeout",
        ]
        if any(kw in error_lower for kw in transient_keywords):
            return FailureCategory.TRANSIENT

        # Resource keywords
        resource_keywords = [
            "memory", "oom", "out of memory", "disk", "quota", "limit exceeded",
            "rate limit", "deadlock", "cpu",
        ]
        if any(kw in error_lower for kw in resource_keywords):
            return FailureCategory.RESOURCE

        # Configuration keywords
        config_keywords = [
            "config", "configuration", "setting", "env", "environment",
            "missing", "not found", "malformed",
        ]
        if any(kw in error_lower for kw in config_keywords):
            return FailureCategory.CONFIGURATION

        # Dependency keywords
        dep_keywords = [
            "connection", "network", "dns", "unreachable", "refused",
            "service unavailable", "dependency", "import",
            "module not found", "package", "version conflict",
        ]
        if any(kw in error_lower for kw in dep_keywords):
            return FailureCategory.DEPENDENCY

        # Performance keywords
        perf_keywords = [
            "slow", "performance", "latency", "throughput", "bottleneck",
            "degradation", "regression",
        ]
        if any(kw in error_lower for kw in perf_keywords):
            return FailureCategory.PERFORMANCE

        # Code defect keywords
        code_keywords = [
            "syntax", "type error", "attribute", "undefined", "null",
            "exception", "assertion", "logic", "bug", "crash",
            "index", "key", "value error",
        ]
        if any(kw in error_lower for kw in code_keywords):
            return FailureCategory.CODE_DEFECT

        return FailureCategory.UNKNOWN

    def _assess_severity(
        self, context: FailureContext, category: FailureCategory
    ) -> FailureSeverity:
        """Assess failure severity."""
        if category == FailureCategory.SECURITY:
            return FailureSeverity.CRITICAL

        if category == FailureCategory.RESOURCE:
            return FailureSeverity.HIGH

        if context.attempt_history and len(context.attempt_history) >= 3:
            return FailureSeverity.HIGH

        if category in [FailureCategory.CODE_DEFECT, FailureCategory.DEPENDENCY]:
            return FailureSeverity.MEDIUM

        if category == FailureCategory.TRANSIENT:
            return FailureSeverity.LOW

        return FailureSeverity.MEDIUM

    def _identify_responsible_service(
        self, context: FailureContext, category: FailureCategory
    ) -> str:
        """Identify the service responsible for the failure."""
        # Category-based attribution takes precedence over context.service
        # context.service is where the failure MANIFESTED, not where it originated
        category_services = {
            FailureCategory.CONFIGURATION: "planning",
            FailureCategory.CODE_DEFECT: "coding",
            FailureCategory.SECURITY: "review",
            FailureCategory.PERFORMANCE: "review",
            FailureCategory.DEPENDENCY: "deployment",
            FailureCategory.RESOURCE: "operations",
            FailureCategory.TRANSIENT: context.service or "unknown",
        }

        if category in category_services:
            return category_services[category]

        # Keyword-based attribution
        for service, keywords in self._service_responsibility.items():
            if any(kw in context.error.lower() for kw in keywords):
                return service

        # Fallback to context.service only if no category mapping
        return context.service or "unknown"

    def _determine_root_cause(
        self, context: FailureContext, category: FailureCategory
    ) -> str:
        """Determine the root cause description."""
        causes = {
            FailureCategory.CONFIGURATION: "Incorrect or missing configuration",
            FailureCategory.CODE_DEFECT: f"Code defect: {context.error_type}",
            FailureCategory.SECURITY: "Security vulnerability detected",
            FailureCategory.PERFORMANCE: "Performance degradation identified",
            FailureCategory.DEPENDENCY: "External dependency failure",
            FailureCategory.RESOURCE: f"Resource exhaustion: {context.error}",
            FailureCategory.TRANSIENT: "Transient infrastructure issue",
            FailureCategory.LOGIC_ERROR: "Logic error in implementation",
        }
        return causes.get(category, f"Unknown failure: {context.error}")

    def _recommend_action(
        self,
        context: FailureContext,
        category: FailureCategory,
        responsible_service: str,
        retry_budget_exhausted: bool,
    ) -> RecoveryAction:
        """Recommend recovery action based on analysis."""
        if retry_budget_exhausted:
            # Budget exhausted - route to responsible service
            service_actions = {
                "planning": RecoveryAction.RETURN_TO_PLANNING,
                "coding": RecoveryAction.RETURN_TO_CODING,
                "review": RecoveryAction.RETURN_TO_REVIEW,
                "testing": RecoveryAction.RETURN_TO_CODING,
                "deployment": RecoveryAction.ROLLBACK,
                "operations": RecoveryAction.RESTART_SERVICE,
                "memory": RecoveryAction.RETRY_WITH_BACKOFF,
                "skills": RecoveryAction.SKIP_STEP,
                "mcp": RecoveryAction.RETRY_WITH_BACKOFF,
                "council": RecoveryAction.RETURN_TO_PLANNING,
            }
            return service_actions.get(responsible_service, RecoveryAction.ESCALATE_TO_HUMAN)

        # Budget not exhausted - prefer retry
        if category == FailureCategory.TRANSIENT:
            return RecoveryAction.RETRY_WITH_BACKOFF

        if category == FailureCategory.RESOURCE:
            return RecoveryAction.RETRY_WITH_BACKOFF

        if category == FailureCategory.CONFIGURATION:
            return RecoveryAction.RETURN_TO_PLANNING

        if category == FailureCategory.CODE_DEFECT:
            return RecoveryAction.RETURN_TO_CODING

        if category == FailureCategory.SECURITY:
            return RecoveryAction.ESCALATE_TO_HUMAN

        if category == FailureCategory.PERFORMANCE:
            return RecoveryAction.RETURN_TO_REVIEW

        if category == FailureCategory.DEPENDENCY:
            return RecoveryAction.RETRY_WITH_BACKOFF

        return RecoveryAction.ESCALATE_TO_HUMAN

    def _calculate_confidence(
        self, context: FailureContext, category: FailureCategory
    ) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.5

        # Higher confidence with more context
        if context.stack_trace:
            confidence += 0.2
        if context.attempt_history:
            confidence += 0.1
        if context.service:
            confidence += 0.1
        if category != FailureCategory.UNKNOWN:
            confidence += 0.1

        return min(confidence, 1.0)

    def _find_similar_failures(self, context: FailureContext) -> list[str]:
        """Find similar historical failures."""
        error_signature = f"{context.error_type}:{context.error[:100]}"
        return self._failure_patterns.get(error_signature, [])[:5]

    def _generate_preventive_measures(
        self, category: FailureCategory, service: str
    ) -> list[str]:
        """Generate preventive measures."""
        measures = {
            FailureCategory.CONFIGURATION: [
                "Add configuration validation in planning",
                "Use configuration schemas with required fields",
            ],
            FailureCategory.CODE_DEFECT: [
                "Add more comprehensive unit tests",
                "Enable stricter type checking",
                "Add code review for generated code",
            ],
            FailureCategory.SECURITY: [
                "Integrate security scanning in CI/CD",
                "Add security review gate",
            ],
            FailureCategory.PERFORMANCE: [
                "Add performance benchmarks",
                "Implement performance regression testing",
            ],
            FailureCategory.DEPENDENCY: [
                "Add dependency health checks",
                "Implement circuit breakers",
            ],
            FailureCategory.RESOURCE: [
                "Add resource monitoring and alerts",
                "Implement auto-scaling",
            ],
            FailureCategory.TRANSIENT: [
                "Add retry policies with exponential backoff",
                "Implement idempotency for operations",
            ],
        }
        return measures.get(category, ["Investigate root cause and add monitoring"])

    def _update_failure_patterns(
        self, context: FailureContext, analysis: RootCauseAnalysis
    ) -> None:
        """Update failure pattern database."""
        error_signature = f"{context.error_type}:{context.error[:100]}"
        if error_signature not in self._failure_patterns:
            self._failure_patterns[error_signature] = []

        self._failure_patterns[error_signature].append(analysis.analysis_id)

    async def _emit_event(
        self, event_type: EventType, payload: dict[str, Any], correlation_id: str
    ) -> None:
        """Emit a canonical event via the canonical EventBus."""
        # Ensure EventBus is available (lazy initialization)
        if self._event_bus is None:
            from aios.events.core.bus import get_core_event_bus
            self._event_bus = get_core_event_bus()

        if self._event_bus is None:
            logger.debug("EventBus not available, skipping event emission")
            return

        # Subscribe to events if not already subscribed
        if not getattr(self, '_subscribed', False):
            self._subscribe_to_events()

        import uuid as uuid_mod

        # Handle invalid UUID strings by generating a new one
        try:
            correlation_uuid = uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4()
        except ValueError:
            logger.warning(f"Invalid UUID string for correlation_id: {correlation_id!r}. Generating a new UUID.")
            correlation_uuid = uuid_mod.uuid4()

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=correlation_uuid,
            payload=payload,
        )
        result = self._event_bus.publish(event)
        # Properly await the publish coroutine
        if hasattr(result, "__await__"):
            await result

    async def resolve_analysis(
        self, analysis_id: str, resolution: str, preventive: list[str] | None = None
    ) -> RootCauseAnalysis | None:
        """Mark an analysis as resolved."""
        analysis = self._analyses.get(analysis_id)
        if not analysis:
            return None

        analysis.root_cause = f"{analysis.root_cause} [RESOLVED: {resolution}]"
        if preventive:
            analysis.preventive_measures.extend(preventive)

        # ROOT_CAUSE_RESOLVED was removed from Enum (not in Part 2 §2.3.1 canonical enumeration)
        # Emit as FAILURE_CLASSIFIED instead
        await self._emit_event(
            EventType.FAILURE_CLASSIFIED,
            {
                "analysis_id": analysis_id,
                "failure_id": analysis.failure_id,
                "resolution": resolution,
                "preventive_measures": preventive or [],
                "status": "resolved",
            },
            analysis.failure_id,
        )

        return analysis

    def get_analysis(self, analysis_id: str) -> RootCauseAnalysis | None:
        """Get analysis by ID."""
        return self._analyses.get(analysis_id)

    def get_stats(self) -> dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "total_analyses": len(self._analyses),
            "patterns_learned": len(self._failure_patterns),
            "categories": {
                cat.value: sum(1 for a in self._analyses.values() if a.category == cat)
                for cat in FailureCategory
            },
        }


# Global root cause analyzer instance
_global_root_cause_analyzer: RootCauseAnalyzer | None = None


def get_root_cause_analyzer() -> RootCauseAnalyzer:
    """Get or create the global root cause analyzer."""
    global _global_root_cause_analyzer
    if _global_root_cause_analyzer is None:
        _global_root_cause_analyzer = RootCauseAnalyzer()
    return _global_root_cause_analyzer


def set_root_cause_analyzer(analyzer: RootCauseAnalyzer | None) -> None:
    """Set the global root cause analyzer, shutting down the previous instance if any."""
    global _global_root_cause_analyzer
    if _global_root_cause_analyzer is not None and _global_root_cause_analyzer is not analyzer:
        # Shutdown the old analyzer to unsubscribe from EventBus
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(_global_root_cause_analyzer.shutdown())
            else:
                loop.run_until_complete(_global_root_cause_analyzer.shutdown())
        except RuntimeError:
            # No event loop, run in new loop
            asyncio.run(_global_root_cause_analyzer.shutdown())
        except Exception as e:
            logger.warning(f"Error shutting down previous RootCauseAnalyzer: {e}")
    _global_root_cause_analyzer = analyzer


__all__ = [
    "RootCauseAnalyzer",
    "FailureContext",
    "RootCauseAnalysis",
    "FailureCategory",
    "FailureSeverity",
    "RecoveryAction",
    "get_root_cause_analyzer",
    "set_root_cause_analyzer",
]
