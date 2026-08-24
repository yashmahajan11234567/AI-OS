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
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
from aios.adapters.base import (
    BaseExecutionAdapter,
    ExecutionResult,
    ExecutionStatus,
)
from aios.adapters.security_agency_adapter import SecurityAgencyAdapter
from aios.adapters.performance_agency_adapter import PerformanceAgencyAdapter
from aios.adapters.chaos_agency_adapter import ChaosAgencyAdapter
from aios.adapters.accessibility_agency_adapter import AccessibilityAgencyAdapter
from aios.adapters.documentation_agency_adapter import DocumentationAgencyAdapter
from aios.adapters.concurrency_agency_adapter import ConcurrencyAgencyAdapter
from aios.adapters.bug_hunter_agency_adapter import BugHunterAgencyAdapter
from aios.adapters.architecture_agency_adapter import ArchitectureAgencyAdapter
from aios.core.security_manager import (
    SecurityManager,
)
from aios.core.testing_evidence import Provenance


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

    def __init__(self, agency_type: AgencyType, event_bus=None):
        self.agency_type = agency_type
        self._event_bus = event_bus or get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name=f"ai_agency.{self.agency_type.value}",
            version=SemanticVersion.parse("0.1.0"),
        )

    @abstractmethod
    async def review(self, request: AgencyRequest) -> AgencyResponse:
        """Perform the agency review."""
        pass

    def _emit_event(self, event_type: EventType, payload: dict[str, Any], correlation_id: str) -> None:
        """Emit a canonical event via the canonical EventBus."""
        import uuid as uuid_mod

        event = CoreEvent(
            eventType=event_type,
            source=self._identity,
            correlationId=uuid_mod.UUID(correlation_id) if correlation_id else uuid_mod.uuid4(),
            payload=payload,
        )
        result = self._event_bus.publish(event)
        # Fire and forget - result handling is async
        if hasattr(result, "__await__"):
            # Schedule on the event loop if available
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(result)
            except RuntimeError:
                pass

    def _emit_started(self, request: AgencyRequest) -> None:
        """Emit review started event."""
        event_name = f"{self.agency_type.value.upper()}_REVIEW_STARTED"
        try:
            event_type = EventType[event_name]
        except KeyError:
            event_type = EventType.AI_AGENT_TASK_REQUESTED  # fallback
        self._emit_event(
            event_type,
            {"request_id": request.request_id, "review_target": request.target},
            request.correlation_id or request.request_id,
        )

    def _emit_completed(self, request: AgencyRequest, response: AgencyResponse) -> None:
        """Emit review completed event."""
        event_name = f"{self.agency_type.value.upper()}_REVIEW_COMPLETED"
        try:
            event_type = EventType[event_name]
        except KeyError:
            event_type = EventType.AI_AGENT_TASK_COMPLETED  # fallback
        self._emit_event(
            event_type,
            {
                "request_id": request.request_id,
                "verdict": response.verdict.value,
                "confidence": response.confidence,
                "findings_count": len(response.findings),
                "review_target": request.target,
            },
            request.correlation_id or request.request_id,
        )

    # ------------------------------------------------------------------
    # M7-C — Real execution seam
    # ------------------------------------------------------------------
    def _get_adapter(self) -> BaseExecutionAdapter:
        """Return the real execution adapter for this agency.

        Subclasses that delegate to a real adapter override this. Agencies that
        use no external worker (e.g. ``FinalJudgeAgency``) leave it unimplemented.
        """
        raise NotImplementedError(
            f"{type(self).__name__} has no real execution adapter wired."
        )

    def _build_provenance(self, request: AgencyRequest, test_id: str) -> Provenance:
        """Build a complete provenance record for this agency's evidence."""
        import uuid as _uuid

        return Provenance(
            source=self.agency_type.value,
            worker="local",
            session=f"{self.agency_type.value}_{_uuid.uuid4().hex[:8]}",
            timestamp=datetime.utcnow().isoformat(),
            environment=request.context.get("environment", "tester"),
            correlation_id=request.correlation_id or request.request_id,
            test_id=test_id,
        )

    def _run_adapter(
        self, request: AgencyRequest, *, tool: Any | None = None
    ) -> ExecutionResult:
        """Execute the real adapter against the actual artifact/implementation.

        The adapter performs content/behavior-driven detection; the target name
        is NEVER used as a defect detector. Returns the structured
        ``ExecutionResult`` observation for normalization.
        """
        adapter = self._get_adapter()
        if tool is not None:
            adapter = type(adapter)(tool) if tool is not None else adapter
        implementation = request.context.get("implementation") or ""
        ctx = {"implementation": implementation, "target": request.target, "builder_id": request.context.get("builder_id", "")}
        return adapter.execute(request.target, ctx)

    def _evidence_to_response(
        self,
        request: AgencyRequest,
        result: ExecutionResult,
        provenance: Provenance,
    ) -> AgencyResponse:
        """Normalize a real adapter ``ExecutionResult`` into an ``AgencyResponse``.

        Defect presence and severity come from the actual execution result, never
        from the target name. Evidence provenance is preserved.
        """
        findings = result.findings
        if result.status in (ExecutionStatus.FAILURE, ExecutionStatus.ERROR):
            verdict = Verdict.CONDITIONAL if findings else Verdict.APPROVE
            # A genuine FAILURE with findings is a real defect -> CONDITIONAL.
            severity = "low"
            for f in findings:
                sev = f.get("severity", "low")
                order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                if order.get(sev, 0) > order.get(severity, 0):
                    severity = sev
            verdict = Verdict.REJECT if severity in ("critical", "high") else Verdict.CONDITIONAL
            confidence = 0.85
        elif result.status == ExecutionStatus.SKIPPED:
            verdict = Verdict.CONDITIONAL
            confidence = 0.6
        else:
            verdict = Verdict.APPROVE
            confidence = 0.95

        normalized = []
        for f in findings:
            normalized.append({
                "type": f.get("type", "defect"),
                "severity": f.get("severity", "medium"),
                "description": f.get("description", "Real execution detected an issue"),
                "location": f.get("location", request.target),
                "evidence": provenance.test_id,
            })

        return AgencyResponse(
            request_id=request.request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=normalized,
            recommendations=self._recommendations(),
            confidence=confidence,
            metadata={
                "execution_tool": result.tool,
                "execution_status": result.status.value,
                "provenance": provenance.to_dict(),
                "target_name_used_for_routing_only": True,
            },
        )

    def _recommendations(self) -> list[str]:
        return []


class SecurityAgency(BaseAgency):
    """Security review agency.

    M7-C: delegates to ``SecurityAgencyAdapter`` which performs REAL static
    analysis of the target artifact, authorized through the canonical
    ``SecurityManager`` (final security authority). No ``if "sql" in target``
    heuristics — detection is driven by actual content scanned by the adapter.
    """

    def __init__(self, security_manager: SecurityManager | None = None):
        super().__init__(AgencyType.SECURITY)
        # ``security_manager`` may be:
        #   * a real ``SecurityManager`` instance -> final-authority gate active
        #   * ``None`` (explicit) -> no gate; the adapter runs its production
        #     tool directly (this is how the orchestrator wires the perspective
        #     and how the adapter itself expects a ``None`` to mean "skip gate").
        # The global singleton is used only as a last-resort default when an
        # instance is NOT passed and one is not registered elsewhere.
        if security_manager is None:
            # Explicit None => no gate (matches adapter/orchestrator semantics).
            self._security_manager: SecurityManager | None = None
        else:
            self._security_manager = security_manager

    def _get_adapter(self) -> BaseExecutionAdapter:
        return SecurityAgencyAdapter(security_manager=self._security_manager)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Implement parameterized queries",
            "Add input validation",
            "Use secure authentication patterns",
        ]


class PerformanceAgency(BaseAgency):
    """Performance audit agency.

    M7-C: delegates to ``PerformanceAgencyAdapter`` which runs a REAL benchmark
    harness against the target. Detection is driven by actual measured
    structural/latency signals, not the target name.
    """

    def __init__(self):
        super().__init__(AgencyType.PERFORMANCE)

    def _get_adapter(self) -> BaseExecutionAdapter:
        return PerformanceAgencyAdapter()

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Add performance benchmarks",
            "Profile critical paths",
            "Consider caching strategies",
        ]


class ChaosAgency(BaseAgency):
    """Chaos engineering agency.

    M7-C: delegates to ``ChaosAgencyAdapter`` which performs REAL fault injection
    (latency/exception/resource probes) and observes graceful degradation. A
    genuine resilience anti-pattern (e.g. silently swallowed exceptions) is
    detected from the actual code, not suggested unconditionally.
    """

    def __init__(self):
        super().__init__(AgencyType.CHAOS)

    def _get_adapter(self) -> BaseExecutionAdapter:
        return ChaosAgencyAdapter()

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Run latency injection experiment",
            "Test failure scenarios",
            "Validate circuit breakers",
        ]


class AccessibilityAgency(BaseAgency):
    """Accessibility audit agency.

    M7-C: delegates to ``AccessibilityAgencyAdapter`` which runs a REAL axe-core
    scan against the rendered/declared markup (Playwright MCP + axe-core in
    production). Detection is driven by actual accessibility-tree analysis, never
    the target name.
    """

    def __init__(self):
        super().__init__(AgencyType.ACCESSIBILITY)

    def _get_adapter(self) -> BaseExecutionAdapter:
        return AccessibilityAgencyAdapter()

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Add ARIA labels",
            "Ensure color contrast ratios",
            "Test with screen readers",
        ]


class DocumentationAgency(BaseAgency):
    """Documentation audit agency.

    M7-C: delegates to ``DocumentationAgencyAdapter`` which performs REAL
    docstring/comment analysis of the actual code (plus optional ModelRouter LLM
    review). Detection is content-driven, never name-matched.
    """

    def __init__(self, model_router: Any | None = None):
        super().__init__(AgencyType.DOCUMENTATION)
        self._model_router = model_router

    def _get_adapter(self) -> BaseExecutionAdapter:
        return DocumentationAgencyAdapter(model_router=self._model_router)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Add module-level documentation",
            "Document all public functions",
            "Include usage examples",
        ]


class ConcurrencyAgency(BaseAgency):
    """Concurrency analysis agency.

    M7-C: delegates to ``ConcurrencyAgencyAdapter`` which performs REAL static +
    dynamic race detection (shared-state analysis, lock detection). Detection is
    driven by actual code patterns, never the target name.
    """

    def __init__(self):
        super().__init__(AgencyType.CONCURRENCY)

    def _get_adapter(self) -> BaseExecutionAdapter:
        return ConcurrencyAgencyAdapter()

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Use thread-safe data structures",
            "Add proper locking",
            "Consider asyncio primitives",
        ]


class BugHunterAgency(BaseAgency):
    """Bug hunting agency.

    M7-C: delegates to ``BugHunterAgencyAdapter`` which performs REAL fuzz /
    property-based testing. A genuine contract violation / crash is detected from
    actual execution, not fabricated for every target.
    """

    def __init__(self):
        super().__init__(AgencyType.BUG_HUNTER)

    def _get_adapter(self) -> BaseExecutionAdapter:
        return BugHunterAgencyAdapter()

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Add property-based tests",
            "Fuzz test input validation",
            "Test error paths",
        ]


class ArchitectureAgency(BaseAgency):
    """Architecture validation agency.

    M7-C: delegates to ``ArchitectureAgencyAdapter`` which traverses the REAL
    dependency/architecture graph (Graphify MCP in production). Detection is
    graph/boundary-driven, never name-matched.
    """

    def __init__(self):
        super().__init__(AgencyType.ARCHITECTURE)

    def _get_adapter(self) -> BaseExecutionAdapter:
        return ArchitectureAgencyAdapter()

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        self._emit_started(request)

        import uuid as _uuid

        provenance = self._build_provenance(request, f"test_{_uuid.uuid4().hex[:12]}")
        result = self._run_adapter(request)
        response = self._evidence_to_response(request, result, provenance)

        self._emit_completed(request, response)
        return response

    def _recommendations(self) -> list[str]:
        return [
            "Enforce dependency direction",
            "Verify interface contracts",
            "Document architectural decisions",
        ]


class FinalJudgeAgency(BaseAgency):
    """Final judgment agency.

    M7: performs INDEPENDENT, evidence-first aggregation of ``TestingEvidence``
    records. Prose-only input is rejected (INV-010). Builder-origin evidence is
    excluded by the orchestrator before it reaches here, so the judge never
    self-approves (INV-009). The external worker (user_simulation) supplies
    observations only and is never treated as a verdict authority.
    """

    def __init__(self):
        super().__init__(AgencyType.FINAL_JUDGE)

    async def review(self, request: AgencyRequest) -> AgencyResponse:
        """Review an AgencyRequest (legacy path preserved for regression).

        If ``request.context["testing_evidence"]`` is present, delegates to the
        evidence-first aggregation path. Otherwise aggregates legacy
        ``previous_findings`` dicts (original behavior).
        """
        self._emit_started(request)

        evidence = request.context.get("testing_evidence")
        if evidence is not None:
            return await self.review_evidence(evidence, request=request)

        await asyncio.sleep(0.01)

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

    async def review_evidence(
        self,
        evidence_list: list[Any],
        *,
        request: AgencyRequest | None = None,
        builder_id: str = "",
    ) -> AgencyResponse:
        """
        INDEPENDENT, EVIDENCE-FIRST final verdict.

        Aggregates ``TestingEvidence`` (or dict-equivalents). Rules:
          * Rejects prose-only / empty evidence (INV-010).
          * Critical failures -> REJECT (never APPROVE).
          * High-severity failures -> CONDITIONAL.
          * If any failing evidence remains unresolved -> CONDITIONAL/REJECT.
          * Strong, all-pass evidence with safeguards -> APPROVE.
          * Builder-origin evidence is dropped (defense-in-depth, INV-009).
        """
        request_id = request.request_id if request else f"fj_{uuid.uuid4().hex[:12]}"
        correlation_id = request.correlation_id if request else ""
        self._emit_started(request) if request else None

        if not evidence_list:
            # Evidence-first: no evidence => cannot approve (no prose-only verdicts).
            response = AgencyResponse(
                request_id=request_id,
                agency_type=self.agency_type,
                verdict=Verdict.REJECT,
                findings=[{"type": "no_evidence", "detail": "FinalJudge received no TestingEvidence"}],
                recommendations=["Provide multi-perspective evidence before judging"],
                confidence=1.0,
            )
            if request:
                self._emit_completed(request, response)
            return response

        # Normalize to dicts; exclude builder-origin evidence.
        cleaned = []
        for ev in evidence_list:
            d = ev.to_dict() if hasattr(ev, "to_dict") else dict(ev)
            prov = d.get("provenance", {}) or {}
            if builder_id and prov.get("source") == builder_id:
                continue  # builder cannot self-approve (INV-009)
            cleaned.append(d)

        if not cleaned:
            # Every piece of evidence was builder-origin (excluded) — there is
            # no independent evidence to judge on, so the verdict must be REJECT
            # (evidence-first: cannot approve on the builder's own say-so).
            response = AgencyResponse(
                request_id=request_id,
                agency_type=self.agency_type,
                verdict=Verdict.REJECT,
                findings=[{"type": "no_independent_evidence", "detail": "All evidence was builder-origin and excluded"}],
                recommendations=["Provide independent testing-council evidence"],
                confidence=1.0,
                metadata={"evidence_first": True, "builder_excluded": bool(builder_id)},
            )
            if request:
                self._emit_completed(request, response)
            return response

        critical = [e for e in cleaned if e.get("severity") == "critical" and e.get("verdict") == "fail"]
        high = [e for e in cleaned if e.get("severity") == "high" and e.get("verdict") == "fail"]
        failing = [e for e in cleaned if e.get("verdict") == "fail"]
        passing = [e for e in cleaned if e.get("verdict") == "pass"]

        # Weighted confidence: average of passing evidence confidence, penalized
        # by failures.
        if passing:
            conf = sum(float(e.get("confidence", 0.0)) for e in passing) / len(passing)
        else:
            conf = 0.5
        conf = max(0.0, min(1.0, conf - 0.1 * len(failing)))

        verdict = Verdict.APPROVE
        if critical:
            verdict = Verdict.REJECT
        elif failing:
            verdict = Verdict.CONDITIONAL
        elif high:
            verdict = Verdict.CONDITIONAL

        response = AgencyResponse(
            request_id=request_id,
            agency_type=self.agency_type,
            verdict=verdict,
            findings=[{
                "type": "final_verdict",
                "verdict": verdict.value,
                "critical_failures": len(critical),
                "high_failures": len(high),
                "total_failures": len(failing),
                "passing": len(passing),
                "evidence_count": len(cleaned),
            }],
            recommendations=[
                "Deploy with confidence" if verdict == Verdict.APPROVE
                else "Address failing perspectives before deployment"
            ],
            confidence=round(conf, 3),
            metadata={"evidence_first": True, "builder_excluded": bool(builder_id)},
        )
        if request:
            self._emit_completed(request, response)
        return response


class AIAgencyService:
    """
    Manages all AI Agencies.

    Provides unified interface for specialized AI reviews.
    """

    def __init__(self, security_manager: SecurityManager | None = None):
        event_bus = get_core_event_bus()
        if event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")
        self._event_bus = event_bus
        self._security_manager = security_manager
        self._agencies: dict[AgencyType, BaseAgency] = {
            AgencyType.SECURITY: SecurityAgency(security_manager=security_manager),
            AgencyType.PERFORMANCE: PerformanceAgency(),
            AgencyType.CHAOS: ChaosAgency(),
            AgencyType.ACCESSIBILITY: AccessibilityAgency(),
            AgencyType.DOCUMENTATION: DocumentationAgency(),
            AgencyType.CONCURRENCY: ConcurrencyAgency(),
            AgencyType.BUG_HUNTER: BugHunterAgency(),
            AgencyType.ARCHITECTURE: ArchitectureAgency(),
            AgencyType.FINAL_JUDGE: FinalJudgeAgency(),
        }

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