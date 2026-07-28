"""
Root Cause Analyzer for AI-OS Hermes Kernel.

Analyzes failures to determine root cause, responsible service, and recommended action.
Routes failures back to the earliest responsible service instead of restarting everything.
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.types import (
    RootCauseAnalyzed,
    RootCauseResolved,
    FailureClassified,
)

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
        self._event_bus = get_event_bus()
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

        # Subscribe to failure events
        self._event_bus.subscribe(
            handler=self._on_retry_budget_exhausted,
            event_types="retry.budget_exhausted",
        )
        self._event_bus.subscribe(
            handler=self._on_task_failed,
            event_types="task.failed",
        )

    async def _on_retry_budget_exhausted(self, event: Event) -> None:
        """Handle RetryBudgetExhausted event."""
        payload = event.payload
        context = FailureContext(
            failure_id=payload.get("task_id", "unknown"),
            event_type="retry.budget_exhausted",
            error=payload.get("final_error", "Retry budget exhausted"),
            error_type="RetryBudgetExhausted",
            service=payload.get("service", "unknown"),
            task_id=payload.get("task_id", ""),
            correlation_id=event.correlation_id,
            payload=payload,
            attempt_history=[],  # Could be populated from retry manager
        )
        self.analyze(context, retry_budget_exhausted=True)

    async def _on_task_failed(self, event: Event) -> None:
        """Handle TaskFailed event."""
        payload = event.payload
        context = FailureContext(
            failure_id=payload.get("task_id", "unknown"),
            event_type="task.failed",
            error=payload.get("error", "Unknown error"),
            error_type=payload.get("error_type", "UnknownError"),
            service=payload.get("service", "unknown"),
            task_id=payload.get("task_id", ""),
            correlation_id=event.correlation_id,
            payload=payload,
        )
        self.analyze(context, retry_budget_exhausted=payload.get("retryable", False) and payload.get("retry_count", 0) >= 3)

    def analyze(
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

        # Emit events
        self._event_bus.publish(
            RootCauseAnalyzed(
                source_service="root_cause_analyzer",
                correlation_id=context.correlation_id or context.failure_id,
                payload={
                    "analysis_id": analysis_id,
                    "failure_id": context.failure_id,
                    "category": category.value,
                    "severity": severity.value,
                    "root_cause": root_cause,
                    "responsible_service": responsible_service,
                    "recommended_action": recommended_action.value,
                    "confidence": confidence,
                },
            )
        )

        self._event_bus.publish(
            FailureClassified(
                source_service="root_cause_analyzer",
                correlation_id=context.correlation_id or context.failure_id,
                payload={
                    "failure_id": context.failure_id,
                    "category": category.value,
                    "severity": severity.value,
                    "service": responsible_service,
                },
            )
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

        # Resource keywords
        resource_keywords = [
            "memory", "oom", "out of memory", "disk", "quota", "limit exceeded",
            "rate limit", "timeout", "deadlock", "cpu",
        ]
        if any(kw in error_lower for kw in resource_keywords):
            return FailureCategory.RESOURCE

        # Configuration keywords
        config_keywords = [
            "config", "configuration", "setting", "env", "environment",
            "missing", "not found", "invalid", "malformed",
        ]
        if any(kw in error_lower for kw in config_keywords):
            if context.service in ["planning", "config"]:
                return FailureCategory.CONFIGURATION

        # Dependency keywords
        dep_keywords = [
            "connection", "network", "dns", "unreachable", "refused",
            "timeout", "service unavailable", "dependency", "import",
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
            if "test" in error_lower:
                return FailureCategory.CODE_DEFECT

        # Transient errors (default for many)
        transient_keywords = [
            "temporary", "transient", "retry", "intermittent", "flaky",
            "network", "connection reset", "timed out",
        ]
        if any(kw in error_lower for kw in transient_keywords):
            return FailureCategory.TRANSIENT

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
        # Direct service attribution
        if context.service:
            return context.service

        # Category-based attribution
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

        return "unknown"

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

    def resolve_analysis(
        self, analysis_id: str, resolution: str, preventive: list[str] | None = None
    ) -> RootCauseAnalysis | None:
        """Mark an analysis as resolved."""
        analysis = self._analyses.get(analysis_id)
        if not analysis:
            return None

        analysis.root_cause = f"{analysis.root_cause} [RESOLVED: {resolution}]"
        if preventive:
            analysis.preventive_measures.extend(preventive)

        self._event_bus.publish(
            RootCauseResolved(
                source_service="root_cause_analyzer",
                correlation_id=analysis.failure_id,
                payload={
                    "analysis_id": analysis_id,
                    "resolution": resolution,
                    "preventive_measures": preventive or [],
                },
            )
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


def set_root_cause_analyzer(analyzer: RootCauseAnalyzer) -> None:
    """Set the global root cause analyzer."""
    global _global_root_cause_analyzer
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
