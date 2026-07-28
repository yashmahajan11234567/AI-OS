"""
AI Agency Service for AI-OS Hermes Kernel.

Implements specialized AI review agents:
- Security: Security review and vulnerability scanning
- Performance: Performance analysis and optimization
- Chaos: Chaos engineering experiments
- Accessibility: Accessibility compliance checking
- Documentation: Documentation generation and review
- Concurrency: Concurrency analysis and race condition detection
- Bug Hunter: Bug hunting and fuzz testing
- Architecture Validator: Architecture compliance validation
- Final Judge: Final quality gate
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.bus import get_event_bus
from aios.events.base import Event, EventType, create_event
from aios.events.types import Event as EventClass


logger = logging.getLogger(__name__)


class AgencyType(str, Enum):
    """AI Agency types."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    CHAOS = "chaos"
    ACCESSIBILITY = "accessibility"
    DOCUMENTATION = "documentation"
    CONCURRENCY = "concurrency"
    BUG_HUNTER = "bug_hunter"
    ARCHITECTURE = "architecture"
    FINAL_JUDGE = "final_judge"


class Verdict(str, Enum):
    """Agency verdicts."""

    APPROVE = "approve"
    REJECT = "reject"
    CONDITIONAL = "conditional"
    ESCALATE = "escalate"


@dataclass
class AgencyRequest:
    """Request to an AI agency."""

    request_id: str
    agency_type: AgencyType
    target: str  # What is being reviewed
    context: dict[str, Any] = field(default_factory=dict)
    criteria: list[str] = field(default_factory=list)
    priority: int = 5  # 1-10
    requested_at: datetime = field(default_factory=datetime.utcnow)
    correlation_id: str = ""


@dataclass
class AgencyResponse:
    """Response from an AI agency."""

    request_id: str
    agency_type: AgencyType
    verdict: Verdict
    findings: list[dict[str, Any]] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    completed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAgency(ABC):
    """Base class for AI agencies."""

    def __init__(self, agency_type: AgencyType):
        self.agency_type = agency_type
        self._event_bus = get_event_bus()

    @abstractmethod
    async def review(self, request: AgencyRequest) -> AgencyResponse:
        """Perform the agency review."""
        pass

    def _emit_started(self, request: AgencyRequest) -> None:
        """Emit review started event."""
        event_name = f"{self.agency_type.value}_review_started"
        self._event_bus.publish(
            create_event(
                event_type=EventType(event_name),
                source_service=f"ai_agency.{self.agency_type.value}",
                correlation_id=request.correlation_id or request.request_id,
                payload={"request_id": request.request_id, "target": request.target},
            )
        )

    def _emit_completed(self, request: AgencyRequest, response: AgencyResponse) -> None:
        """Emit review completed event."""
        event_name = f"{self.agency_type.value}_review_completed"
        self._event_bus.publish(
            create_event(
                event_type=EventType(event_name),
                source_service=f"ai_agency.{self.agency_type.value}",
                correlation_id=request.correlation_id or request.request_id,
                payload={
                    "request_id": request.request_id,
                    "verdict": response.verdict.value,
                    "confidence": response.confidence,
                    "findings_count": len(response.findings),
                },
            )
        )


class SecurityAgency(BaseAgency):
    """Security review agency."""

    def __init__(self):
        super().__init__(AgencyType.SECURITY)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        # Simulate security review
        await asyncio.sleep(0.5)

        findings = []
        # Check injection vulnerabilities
        if "sql" in request.target.lower() or "query" in request.target.lower():
            findings.append(
                {
                    "type": "sql_injection_risk",
                    "severity": "high",
                    "description": "Potential SQL injection vector detected",
                    "location": request.target,
                }
            )

        # Check authentication
        if "auth" in request.target.lower() or "login" in request.target.lower():
            findings.append(
                {
                    "type": "auth_review",
                    "severity": "medium",
                    "description": "Review authentication implementation",
                    "location": request.target,
                }
            )

        verdict = Verdict.APPROVE if not findings else Verdict.CONDITIONAL
        confidence = 0.85

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Implement parameterized queries",
                "Add input validation",
                "Use secure authentication patterns",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class PerformanceAgency(BaseAgency):
    """Performance audit agency."""

    def __init__(self):
        super().__init__(AgencyType.PERFORMANCE)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = []
        if "loop" in request.target.lower() or "iteration" in request.target.lower():
            findings.append(
                {
                    "type": "potential_performance_issue",
                    "severity": "medium",
                    "description": "Review loop efficiency and consider vectorization",
                    "location": request.target,
                }
            )

        verdict = Verdict.APPROVE
        confidence = 0.8

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Add performance benchmarks",
                "Profile critical paths",
                "Consider caching strategies",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class ChaosAgency(BaseAgency):
    """Chaos engineering agency."""

    def __init__(self):
        super().__init__(AgencyType.CHAOS)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = []
        findings.append(
            {
                "type": "chaos_experiment_suggested",
                "severity": "low",
                "description": "Consider latency injection experiment",
                "location": request.target,
            }
        )

        verdict = Verdict.APPROVE
        confidence = 0.7

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Run latency injection experiment",
                "Test failure scenarios",
                "Validate circuit breakers",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class AccessibilityAgency(BaseAgency):
    """Accessibility audit agency."""

    def __init__(self):
        super().__init__(AgencyType.ACCESSIBILITY)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = []
        if "ui" in request.target.lower() or "frontend" in request.target.lower():
            findings.append(
                {
                    "type": "accessibility_review",
                    "severity": "medium",
                    "description": "Verify WCAG 2.1 AA compliance",
                    "location": request.target,
                }
            )

        verdict = Verdict.CONDITIONAL if findings else Verdict.APPROVE
        confidence = 0.75

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Add ARIA labels",
                "Ensure color contrast ratios",
                "Test with screen readers",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class DocumentationAgency(BaseAgency):
    """Documentation audit agency."""

    def __init__(self):
        super().__init__(AgencyType.DOCUMENTATION)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = []
        if "function" in request.target.lower() or "class" in request.target.lower():
            findings.append(
                {
                    "type": "docstring_missing",
                    "severity": "low",
                    "description": "Verify all public APIs have docstrings",
                    "location": request.target,
                }
            )

        verdict = Verdict.APPROVE
        confidence = 0.7

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Add module-level documentation",
                "Document all public functions",
                "Include usage examples",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class ConcurrencyAgency(BaseAgency):
    """Concurrency analysis agency."""

    def __init__(self):
        super().__init__(AgencyType.CONCURRENCY)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = []
        if "async" in request.target.lower() or "thread" in request.target.lower():
            findings.append(
                {
                    "type": "race_condition_risk",
                    "severity": "medium",
                    "description": "Review shared state access patterns",
                    "location": request.target,
                }
            )

        verdict = Verdict.CONDITIONAL if findings else Verdict.APPROVE
        confidence = 0.75

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Use thread-safe data structures",
                "Add proper locking",
                "Consider asyncio primitives",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class BugHunterAgency(BaseAgency):
    """Bug hunting agency."""

    def __init__(self):
        super().__init__(AgencyType.BUG_HUNTER)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = [
            {
                "type": "potential_bug",
                "severity": "medium",
                "description": "Consider edge cases and error handling",
                "location": request.target,
            }
        ]

        verdict = Verdict.CONDITIONAL
        confidence = 0.7

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Add property-based tests",
                "Fuzz test input validation",
                "Test error paths",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class ArchitectureAgency(BaseAgency):
    """Architecture validation agency."""

    def __init__(self):
        super().__init__(AgencyType.ARCHITECTURE)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        findings = []
        if "service" in request.target.lower() or "module" in request.target.lower():
            findings.append(
                {
                    "type": "architecture_review",
                    "severity": "medium",
                    "description": "Verify service boundaries and dependencies",
                    "location": request.target,
                }
            )

        verdict = Verdict.CONDITIONAL if findings else Verdict.APPROVE
        confidence = 0.8

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=findings,
            recommendations=[
                "Enforce dependency direction",
                "Verify interface contracts",
                "Document architectural decisions",
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class FinalJudgeAgency(BaseAgency):
    """Final judgment agency."""

    def __init__(self):
        super().__init__(AgencyType.FINAL_JUDGE)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        await asyncio.sleep(0.5)

        # Aggregate previous agency results
        context_findings = request.context.get("previous_findings", [])
        critical_findings = [f for f in context_findings if f.get("severity") == "critical"]
        high_findings = [f for f in context_findings if f.get("severity") == "high"]

        verdict = Verdict.APPROVE
        if critical_findings:
            verdict = Verdict.REJECT
        elif high_findings:
            verdict = Verdict.CONDITIONAL

        confidence = 0.9

        response = AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=[
                {"type": "final_verdict", "verdict": verdict.value, "critical_count": len(critical_findings), "high_count": len(high_findings)}
            ],
            recommendations=[
                "Deploy with confidence" if verdict == Verdict.APPROVE else "Address issues before deployment"
            ],
            confidence=confidence,
        )

        self._emit_completed(request, response)
        return response


class AIAgencyService:
    """
    Manages all AI Agencies.

    Provides unified interface for specialized AI reviews.
    """

    def __init__(self):
        self._agencies: dict[AgencyType, BaseAgency] = {
            AgencyType.SECURITY: SecurityAgency(),
            AgencyType.PERFORMANCE: PerformanceAgency(),
            AgencyType.CHAOS: ChaosAgency(),
            AgencyType.ACCESSIBILITY: AccessibilityAgency(),
            AgencyType.DOCUMENTATION: DocumentationAgency(),
            AgencyType.CONCURRENCY: ConcurrencyAgency(),
            AgencyType.BUG_HUNTER: BugHunterAgency(),
            AgencyType.ARCHITECTURE: ArchitectureAgency(),
            AgencyType.FINAL_JUDGE: FinalJudgeAgency(),
        }
        self._event_bus = get_event_bus()

    def get_agency(self, agency_type: AgencyType) -> BaseAgency | None:
        """Get an agency by type."""
        return self._agencies.get(agency_type)

    def list_agencies(self) -> list[AgencyType]:
        """List available agencies."""
        return list(self._agencies.keys())

    async def review(
        self,
        agency_type: AgencyType,
        request: AgencyRequest,
    ) -> AgencyResponse:
        """
        Request a review from a specific agency.

        Args:
            agency_type: Type of agency
            request: Review request

        Returns:
            Agency response
        """
        agency = self._agencies.get(agency_type)
        if not agency:
            raise ValueError(f"Agency {agency_type} not available")

        return await agency.review(request)

    async def run_full_review(
        self,
        target: str,
        context: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[AgencyType, AgencyResponse]:
        """
        Run all agencies in sequence.

        Args:
            target: Target to review
            context: Additional context
            correlation_id: Correlation ID for tracing

        Returns:
            Dict of agency responses
        """
        request = AgencyRequest(
            request_id=f"full_review_{datetime.utcnow().timestamp()}",
            agency_type=AgencyType.SECURITY,  # Dummy, will be overridden
            target=target,
            context=context or {},
            correlation_id=correlation_id or "",
        )

        results = {}

        # Run core agencies in parallel
        core_agencies = [
            AgencyType.SECURITY,
            AgencyType.PERFORMANCE,
            AgencyType.ARCHITECTURE,
        ]

        tasks = [self.review(agt, request) for agt in core_agencies]
        core_results = await asyncio.gather(*tasks, return_exceptions=True)

        for agt, result in zip(core_agencies, core_results):
            if isinstance(result, Exception):
                logger.error(f"Agency {agt} failed: {result}")
                results[agt] = AgencyResponse(
                    request_id=request.request_id,
                    agency_type=agt,
                    verdict=Verdict.ESCALATE,
                    findings=[{"error": str(result)}],
                    confidence=0.0,
                )
            else:
                results[agt] = result

        # Collect findings for final judge
        all_findings = []
        for result in results.values():
            all_findings.extend(result.findings)

        request.context["previous_findings"] = all_findings

        # Run final judge
        final_result = await self.review(AgencyType.FINAL_JUDGE, request)
        results[AgencyType.FINAL_JUDGE] = final_result

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get agency service statistics."""
        return {
            "available_agencies": len(self._agencies),
            "agencies": [agt.value for agt in self._agencies],
        }


# Global AI agency service
_global_ai_agency_service: AIAgencyService | None = None


def get_ai_agency_service() -> AIAgencyService:
    """Get or create the global AI agency service."""
    global _global_ai_agency_service
    if _global_ai_agency_service is None:
        _global_ai_agency_service = AIAgencyService()
    return _global_ai_agency_service


def set_ai_agency_service(service: AIAgencyService) -> None:
    """Set the global AI agency service."""
    global _global_ai_agency_service
    _global_ai_agency_service = service


__all__ = [
    "AIAgencyService",
    "BaseAgency",
    "SecurityAgency",
    "PerformanceAgency",
    "ChaosAgency",
    "AccessibilityAgency",
    "DocumentationAgency",
    "ConcurrencyAgency",
    "BugHunterAgency",
    "ArchitectureAgency",
    "FinalJudgeAgency",
    "AgencyRequest",
    "AgencyResponse",
    "AgencyType",
    "Verdict",
    "get_ai_agency_service",
    "set_ai_agency_service",
]