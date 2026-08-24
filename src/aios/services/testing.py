"""
M7 — TestOrchestratorService.

Extends ``WorkflowManager`` (INV-015: inheritance, never duplication). It
orchestrates the multi-perspective testing flow:

    PLAN -> DISPATCH -> COLLECT -> NORMALIZE -> TESTING COUNCIL
         -> FINAL JUDGE -> SIMPLIFICATION GATE -> PASS | CLOSED LOOP

The service:
  * dispatches the 9 agency perspectives + UserSimulationAgent in parallel,
  * normalizes every result into an immutable ``TestingEvidence`` record with
    complete provenance,
  * submits evidence to the EXISTING ``CouncilManager`` (TestingCouncil is a
    session, not a second council),
  * aggregates the independent ``FinalJudgeAgency`` verdict,
  * runs the ``SimplificationGate`` before acceptance,
  * drives the bounded closed loop (FAIL -> RCA -> Learning -> Planning ->
    re-execute -> retest) reusing existing components.

All events are emitted via the canonical EventBus. No new EventType is created.
The builder is excluded from the TestingCouncil (INV-009).
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from aios.core.testing_evidence import (
    Provenance,
    TestingEvidence,
    UserSimulationCompleted,
    normalize_user_simulation,
)
from aios.core.user_simulation_agent import UserSimulationAgent
from aios.core.simplification_gate import SimplificationGate, GateVerdict
from aios.core.workflow import WorkflowManager
from aios.core.council_manager import (
    CouncilManager,
    CouncilMember,
    ConsensusAlgorithm,
    CritiqueResult,
    get_council_manager,
)
from aios.core.ai_agency import (
    AgencyRequest,
    AgencyResponse,
    AgencyType,
    FinalJudgeAgency,
    Verdict as AgencyVerdict,
)
from aios.adapters.base import ExecutionResult, ExecutionStatus
from aios.adapters.security_agency_adapter import SecurityAgencyAdapter
from aios.adapters.performance_agency_adapter import PerformanceAgencyAdapter
from aios.adapters.chaos_agency_adapter import ChaosAgencyAdapter
from aios.adapters.accessibility_agency_adapter import AccessibilityAgencyAdapter
from aios.adapters.documentation_agency_adapter import DocumentationAgencyAdapter
from aios.adapters.concurrency_agency_adapter import ConcurrencyAgencyAdapter
from aios.adapters.bug_hunter_agency_adapter import BugHunterAgencyAdapter
from aios.adapters.architecture_agency_adapter import ArchitectureAgencyAdapter

# Reuse the canonical event bus singleton accessor; no second bus is created.
from aios.events.core.bus import get_core_event_bus
from aios.events.core.types import EventType


__all__ = ["TestOrchestratorService", "TestingResult", "TestingStatus"]


class TestingStatus(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    EVIDENCE_COLLECTED = "evidence_collected"
    COUNCIL_CONVENED = "council_convened"
    JUDGED = "judged"
    GATE_PASSED = "gate_passed"
    PASSED = "passed"
    FAILED = "failed"
    CLOSED_LOOP = "closed_loop"


@dataclass
class TestingResult:
    """Aggregated outcome of a test orchestration run."""

    objective_id: str
    status: TestingStatus
    evidence: list[TestingEvidence] = field(default_factory=list)
    council_id: str = ""
    critique: CritiqueResult | None = None
    final_verdict: str = ""  # APPROVE | REJECT | CONDITIONAL
    gate_result: Any | None = None
    iterations: int = 0
    correlation_id: str = ""
    detail: str = ""


# Stable perspective identifiers (used for provenance + council membership).
PERSPECTIVE_IDS = [
    "security_agency",
    "performance_agency",
    "chaos_agency",
    "accessibility_agency",
    "documentation_agency",
    "concurrency_agency",
    "bug_hunter_agency",
    "architecture_agency",
    "user_simulation",
]


class TestOrchestratorService(WorkflowManager):
    """
    Orchestrates multi-perspective testing as a WorkflowManager extension.

    Construction is permissive about optional collaborators so that unit tests
    can inject deterministic doubles (adapters, bridge, council, judge, gate,
    security, learning, planning, RCA). Production wires the real singletons.
    """

    name = "test_orchestrator"
    version = "2.0.0"
    description = "Multi-perspective testing & user simulation orchestration"

    def __init__(
        self,
        state_manager=None,
        *,
        council_manager: CouncilManager | None = None,
        user_simulation_agent: UserSimulationAgent | None = None,
        final_judge: FinalJudgeAgency | None = None,
        simplification_gate: SimplificationGate | None = None,
        security_manager: Any | None = None,
        learning_service: Any | None = None,
        planning_service: Any | None = None,
        root_cause_analyzer: Any | None = None,
        adapters: dict[str, Any] | None = None,
    ) -> None:
        # WorkflowManager constructor (resolves canonical EventBus; requires it).
        super().__init__(state_manager)

        self._council = council_manager or get_council_manager()
        self._user_sim = user_simulation_agent
        self._final_judge = final_judge or FinalJudgeAgency()
        self._gate = simplification_gate or SimplificationGate()
        self._security = security_manager
        self._learning = learning_service
        self._planning = planning_service
        self._rca = root_cause_analyzer

        # Wire the 8 real agency execution adapters (DI-friendly).
        self._adapters = adapters or {
            "security_agency": SecurityAgencyAdapter(security_manager=self._security),
            "performance_agency": PerformanceAgencyAdapter(),
            "chaos_agency": ChaosAgencyAdapter(),
            "accessibility_agency": AccessibilityAgencyAdapter(),
            "documentation_agency": DocumentationAgencyAdapter(),
            "concurrency_agency": ConcurrencyAgencyAdapter(),
            "bug_hunter_agency": BugHunterAgencyAdapter(),
            "architecture_agency": ArchitectureAgencyAdapter(),
        }

        # Bounded closed-loop controls (INV-013).
        self._max_iterations = 5
        self._token_budget = 1_000_000
        self._results: dict[str, TestingResult] = {}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_correlation(self) -> str:
        return str(uuid.uuid4())

    def _make_provenance(
        self, perspective: str, correlation_id: str, test_id: str, environment: str
    ) -> Provenance:
        return Provenance(
            source=perspective,
            worker="local" if perspective != "user_simulation" else "hermes_agent_ext",
            session=f"{perspective}_{uuid.uuid4().hex[:8]}"
            if perspective != "user_simulation"
            else f"hermes_{uuid.uuid4().hex[:12]}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment=environment,
            correlation_id=correlation_id,
            test_id=test_id,
        )

    # ------------------------------------------------------------------
    # Orchestration entry point
    # ------------------------------------------------------------------

    async def orchestrate_test(
        self,
        objective: str,
        objective_id: str,
        target: str,
        perspectives: list[str] | None = None,
        builder_id: str = "",
        *,
        implementation: str = "",
        app_url: str = "",
        user_goal: str = "",
        exploration_brief: str = "",
        correlation_id: str | None = None,
        corrected_implementation_provider: Any | None = None,
    ) -> TestingResult:
        """
        Plan -> DISPATCH -> COLLECT -> NORMALIZE -> COUNCIL -> JUDGE -> GATE.

        Drives the bounded closed loop when the judge rejects. The optional
        ``corrected_implementation_provider`` is called with the failing
        evidence (and the failed implementation) to produce a corrected
        implementation for the next iteration. This is how the loop converges
        to PASS once the seeded defect is fixed — without inventing a second
        planner, the provider reuses existing PlanningService semantics.

        Bounded by ``_max_iterations`` + ``_token_budget`` (INV-013).
        """
        correlation_id = correlation_id or self._new_correlation()
        perspectives = perspectives or list(PERSPECTIVE_IDS)
        environment = "tester"  # tester environment identity (M7-E)

        self._emit_event(
            EventType.WORKFLOW_STARTED,
            {"objective_id": objective_id, "test_target": target, "builder_id": builder_id},
            correlation_id,
        )

        iterations = 0
        last_evidence: list[TestingEvidence] = []
        last_critique: CritiqueResult | None = None
        last_council_id = ""
        last_verdict = "unknown"
        while iterations < self._max_iterations:
            iterations += 1
            evidence = await self._dispatch_all(
                target=target,
                perspectives=perspectives,
                correlation_id=correlation_id,
                implementation=implementation,
                app_url=app_url,
                user_goal=user_goal,
                exploration_brief=exploration_brief,
                builder_id=builder_id,
            )

            critique, council_id = await self.submit_to_testing_council(
                evidence_list=evidence, builder_id=builder_id, correlation_id=correlation_id
            )

            judge_response = await self._run_final_judge(
                evidence=evidence, builder_id=builder_id, correlation_id=correlation_id
            )
            final_verdict = judge_response.verdict.value

            # Track the most recent iteration's state for honest terminal output.
            last_evidence = evidence
            last_critique = critique
            last_council_id = council_id
            last_verdict = final_verdict

            if final_verdict == AgencyVerdict.APPROVE.value:
                gate = self._gate.evaluate(implementation or target, evidence)
                if gate.verdict == GateVerdict.PASS:
                    result = TestingResult(
                        objective_id=objective_id,
                        status=TestingStatus.PASSED,
                        evidence=evidence,
                        council_id=council_id,
                        critique=critique,
                        final_verdict=final_verdict,
                        gate_result=gate,
                        iterations=iterations,
                        correlation_id=correlation_id,
                        detail="All gates passed.",
                    )
                    self._emit_event(
                        EventType.TESTING_COMPLETED,
                        {"objective_id": objective_id, "verdict": final_verdict, "iterations": iterations},
                        correlation_id,
                    )
                    self._results[objective_id] = result
                    return result
                # Simplification gate failed -> closed loop from planning.
                self._emit_event(
                    EventType.WORKFLOW_STEP_FAILED,
                    {"objective_id": objective_id, "reason": "simplification_gate_fail"},
                    correlation_id,
                )
                # (The corrected implementation would be supplied by the planner
                # in a real loop; here we record the gate failure and either
                # retry with a simplified implementation or terminate.)
                if iterations >= self._max_iterations:
                    return self._build_failed(
                        objective_id, evidence, council_id, critique, "approve",
                        "Simplification gate failed; iteration cap reached.", correlation_id, iterations,
                    )
                # Re-loop: planner/provider produces a simplified implementation.
                if corrected_implementation_provider is not None:
                    corrected = corrected_implementation_provider(
                        failed_evidence=evidence, failed_implementation=implementation
                    )
                    if corrected and corrected != implementation:
                        implementation = corrected
                self._emit_event(
                    EventType.COUNCIL_DECISION_FINALIZED,
                    {"objective_id": objective_id, "loop": "simplification_restart", "iteration": iterations},
                    correlation_id,
                )
                continue

            # REJECT / CONDITIONAL -> closed loop via RCA/Learning/Planning.
            closed = await self._closed_loop_step(
                objective_id=objective_id,
                target=target,
                evidence=evidence,
                final_verdict=final_verdict,
                correlation_id=correlation_id,
                iteration=iterations,
            )
            if not closed and iterations >= self._max_iterations:
                return self._build_failed(
                    objective_id, evidence, council_id, critique, final_verdict,
                    "Final judge rejected; iteration cap reached.", correlation_id, iterations,
                )
            # Re-plan: obtain a corrected implementation for the next iteration.
            if corrected_implementation_provider is not None:
                corrected = corrected_implementation_provider(
                    failed_evidence=evidence, failed_implementation=implementation
                )
                if corrected and corrected != implementation:
                    implementation = corrected
            # Continue loop (planner/provider supplies corrected implementation).
            continue

        return self._build_failed(
            objective_id, last_evidence, last_council_id, last_critique, last_verdict,
            "Iteration cap reached without PASS.", correlation_id, iterations,
        )

    # ------------------------------------------------------------------
    # Dispatch (parallel, provenance-preserving)
    # ------------------------------------------------------------------

    async def dispatch_perspective(
        self,
        perspective: str,
        target: str,
        correlation_id: str,
        *,
        implementation: str = "",
        app_url: str = "",
        user_goal: str = "",
        exploration_brief: str = "",
        builder_id: str = "",
    ) -> TestingEvidence:
        """Execute a single perspective and return NORMALIZED evidence."""
        self._emit_event(
            EventType.WORKFLOW_STEP_STARTED,
            {"perspective": perspective, "test_target": target},
            correlation_id,
        )

        test_id = f"test_{uuid.uuid4().hex[:12]}"
        provenance = self._make_provenance(perspective, correlation_id, test_id, "tester")

        if perspective == "user_simulation":
            if self._user_sim is None:
                raise RuntimeError("UserSimulationAgent not configured for this service")
            sim = await self._user_sim.simulate(
                app_url=app_url or target,
                user_goal=user_goal or f"Use {target}",
                exploration_brief=exploration_brief or "Explore as a new user.",
                correlation_id=correlation_id,
            )
            evidence = normalize_user_simulation(
                sim, target=target, test_id=test_id, provenance=provenance
            )
        else:
            adapter = self._adapters.get(perspective)
            if adapter is None:
                raise ValueError(f"No adapter for perspective: {perspective}")
            ctx = {"implementation": implementation, "target": target, "builder_id": builder_id}
            result = adapter.execute(target, ctx)
            evidence = self.normalize_evidence(result, perspective, target, provenance=provenance)

        return evidence

    async def _dispatch_all(
        self,
        *,
        target: str,
        perspectives: list[str],
        correlation_id: str,
        implementation: str,
        app_url: str,
        user_goal: str,
        exploration_brief: str,
        builder_id: str,
    ) -> list[TestingEvidence]:
        """DISPATCH independent perspectives in parallel (safe asyncio.gather)."""
        tasks = [
            self.dispatch_perspective(
                perspective=p,
                target=target,
                correlation_id=correlation_id,
                implementation=implementation,
                app_url=app_url,
                user_goal=user_goal,
                exploration_brief=exploration_brief,
                builder_id=builder_id,
            )
            for p in perspectives
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        evidence: list[TestingEvidence] = []
        for p, r in zip(perspectives, results):
            if isinstance(r, TestingEvidence):
                evidence.append(r)
            elif isinstance(r, Exception):
                # Preserve a failure evidence record (provenance intact).
                evidence.append(
                    TestingEvidence(
                        perspective=p,
                        target=target,
                        test_id=f"test_{uuid.uuid4().hex[:12]}",
                        expected="perspective executes",
                        observed=f"error: {r!r}",
                        severity="medium",
                        confidence=0.9,
                        provenance=self._make_provenance(p, correlation_id, f"err_{uuid.uuid4().hex[:8]}", "tester"),
                        verdict="fail",
                    )
                )
        return evidence

    # ------------------------------------------------------------------
    # Normalize
    # ------------------------------------------------------------------

    def normalize_evidence(
        self,
        raw_response: Any,
        perspective: str,
        target: str,
        *,
        provenance: Provenance | None = None,
        correlation_id: str = "",
    ) -> TestingEvidence:
        """
        Normalize a raw agency adapter result (ExecutionResult) into the
        canonical ``TestingEvidence`` schema with complete provenance.
        """
        test_id = f"test_{uuid.uuid4().hex[:12]}"
        prov = provenance or self._make_provenance(perspective, correlation_id, test_id, "tester")

        if isinstance(raw_response, UserSimulationCompleted):
            return normalize_user_simulation(raw_response, target=target, test_id=test_id, provenance=prov)

        if isinstance(raw_response, ExecutionResult):
            findings = raw_response.findings
            status = raw_response.status
            if status == ExecutionStatus.SUCCESS:
                verdict = "pass"
                severity = "low"
            elif status == ExecutionStatus.SKIPPED:
                verdict = "inconclusive"
                severity = "low"
            else:
                verdict = "fail"
                # Severity from the most severe finding.
                sev_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                severity = "low"
                for f in findings:
                    s = f.get("severity", "low")
                    if sev_order.get(s, 0) > sev_order.get(severity, 0):
                        severity = s
            return TestingEvidence(
                perspective=perspective,
                target=target,
                test_id=test_id,
                actions=[{"type": "execute", "tool": raw_response.tool}],
                observations=[{"tool": raw_response.tool, "status": status.value, "metrics": raw_response.metrics}],
                expected="No defects detected by this perspective",
                observed=(
                    "defects detected" if findings else "no defects detected"
                ),
                severity=severity,
                confidence=0.85 if findings else 0.95,
                proof=[f"tool:{raw_response.tool}"],
                provenance=prov,
                environment={"tool": raw_response.tool},
                timestamp=raw_response.executed_at,
                reproducibility=1.0,
                verdict=verdict,
            )

        # Fallback: treat as AgencyResponse-like dict.
        if isinstance(raw_response, dict):
            findings = raw_response.get("findings", [])
            verdict = "fail" if findings else "pass"
            return TestingEvidence(
                perspective=perspective,
                target=target,
                test_id=test_id,
                observations=findings,
                expected="No defects",
                observed="defects" if findings else "none",
                severity="medium" if findings else "low",
                confidence=0.7,
                provenance=prov,
                verdict=verdict,
            )

        raise TypeError(f"Cannot normalize response of type {type(raw_response)!r}")

    # ------------------------------------------------------------------
    # Testing Council (reuse existing CouncilManager)
    # ------------------------------------------------------------------

    async def submit_to_testing_council(
        self,
        evidence_list: list[TestingEvidence],
        builder_id: str = "",
        *,
        correlation_id: str = "",
    ) -> tuple[CritiqueResult, str]:
        """
        Convene the TestingCouncil (existing CouncilManager session) and run the
        M6 critique + synthesize. The builder is EXCLUDED from membership (INV-009).
        """
        members = self._build_council_members(builder_id=builder_id)
        council = await self._council.convene(
            topic="Multi-perspective testing verdict",
            members=members,
            algorithm=ConsensusAlgorithm.MAJORITY,
            quorum=0.5,
            metadata={"builder_excluded": builder_id or None, "perspective_count": len(members)},
        )
        self._emit_event(
            EventType.COUNCIL_CONVENED,
            {"council_id": council.council_id, "members": [m.member_id for m in members]},
            council.council_id,
        )

        # Stage 1: independent proposals (blind — each member submits on its own).
        await self._council.propose(
            council_id=council.council_id,
            title="Accept implementation?",
            description="Testing council deliberation on multi-perspective evidence",
            proposer="test_orchestrator",
            options=[{"id": "approve"}, {"id": "reject"}, {"id": "conditional"}],
        )

        # Stage 2: critique (M6 KKC/EVC). Accuracy/insight derived from evidence.
        accuracy = {}
        insight = {}
        dissent = []
        for i, ev in enumerate(evidence_list):
            mid = PERSPECTIVE_IDS[i] if i < len(PERSPECTIVE_IDS) else f"p{i}"
            acc = 0.5 + 0.5 * ev.confidence
            ins = 0.5 + 0.3 * ev.reproducibility
            if ev.severity == "critical":
                ins += 0.2
            accuracy[mid] = round(min(1.0, acc), 3)
            insight[mid] = round(min(1.0, ins), 3)
            # A dissenting minority: the lowest-confidence perspective dissents.
        if evidence_list:
            weakest = min(evidence_list, key=lambda e: e.confidence)
            dissent.append({
                "member_id": weakest.perspective,
                "proposal_id": "unknown",
                "reason": f"Low confidence ({weakest.confidence}) on {weakest.target}",
            })

        critique = await self._council.critique(
            council_id=council.council_id,
            accuracy_scores=accuracy,
            insight_scores=insight,
            dissent=dissent,
            relabel_rounds=2,
        )
        self._emit_event(
            EventType.COUNCIL_DISSENT_REGISTERED,
            {"council_id": council.council_id, "dissent_preserved": len(critique.dissent_preserved)},
            council.council_id,
        )

        # Stage 3: synthesize (M6).
        await self._council.synthesize(council_id=council.council_id, critique=critique)
        self._emit_event(
            EventType.COUNCIL_DECISION_FINALIZED,
            {"council_id": council.council_id, "dissenter_override": critique.dissenter_override},
            council.council_id,
        )
        return critique, council.council_id

    def _build_council_members(self, builder_id: str) -> list[CouncilMember]:
        """Build TestingCouncil members; EXCLUDE the builder (INV-009)."""
        specs = [
            ("security_agency", "Security", ["security"]),
            ("performance_agency", "Performance", ["performance"]),
            ("chaos_agency", "Chaos", ["chaos"]),
            ("accessibility_agency", "Accessibility", ["accessibility"]),
            ("documentation_agency", "Documentation", ["docs"]),
            ("concurrency_agency", "Concurrency", ["concurrency"]),
            ("bug_hunter_agency", "BugHunter", ["bugs"]),
            ("architecture_agency", "Architecture", ["architecture"]),
            ("user_simulation", "UserSimulation", ["ux"]),
        ]
        members = [
            CouncilMember(member_id=mid, name=name, expertise=exp)
            for mid, name, exp in specs
        ]
        # Explicitly drop any member equal to the builder.
        if builder_id:
            members = [m for m in members if m.member_id != builder_id]
        return members

    # ------------------------------------------------------------------
    # Final Judge (independent, evidence-first)
    # ------------------------------------------------------------------

    async def _run_final_judge(
        self,
        evidence: list[TestingEvidence],
        builder_id: str = "",
        *,
        correlation_id: str = "",
    ) -> AgencyResponse:
        """
        Run the independent FinalJudgeAgency. Builder-origin evidence is EXCLUDED
        (INV-009 / INV-007 evidence integrity: builder must not self-approve).
        The external worker (user_simulation) supplies observations only and is
        never treated as a verdict authority.
        """
        # Filter out any builder-origin evidence (defense-in-depth).
        clean = [e for e in evidence if e.provenance.source != builder_id]
        # Pass the actual evidence objects under the evidence-first key so that
        # FinalJudgeAgency.review_evidence runs (NOT the legacy prose path).
        request = AgencyRequest(
            request_id=f"fj_{uuid.uuid4().hex[:12]}",
            agency_type=AgencyType.FINAL_JUDGE,
            target="; ".join(sorted({e.target for e in clean})) or "unknown",
            context={"testing_evidence": clean},
            correlation_id=correlation_id or self._new_correlation(),
        )
        # Ensure a valid UUID correlation id for event emission.
        if not request.correlation_id:
            request.correlation_id = self._new_correlation()
        response = await self._final_judge.review(request)
        self._emit_event(
            EventType.TESTING_COMPLETED,
            {"final_verdict": response.verdict.value, "evidence_count": len(clean)},
            correlation_id or request.correlation_id,
        )
        return response

    # ------------------------------------------------------------------
    # Closed loop (reuse existing RCA / Learning / Planning)
    # ------------------------------------------------------------------

    async def _closed_loop_step(
        self,
        *,
        objective_id: str,
        target: str,
        evidence: list[TestingEvidence],
        final_verdict: str,
        correlation_id: str,
        iteration: int,
    ) -> bool:
        """
        FAIL -> RootCauseAnalyzer -> LearningService -> PlanningService -> re-execute.

        Returns True if the loop should continue (a corrected plan/impl is
        expected), False if it cannot (e.g. budget exhausted). Bounded.
        """
        self._emit_event(
            EventType.WORKFLOW_FAILED,
            {"objective_id": objective_id, "verdict": final_verdict, "iteration": iteration},
            correlation_id,
        )

        # Token budget guard (INV-013).
        if iteration * 200_000 > self._token_budget:
            return False

        # RootCauseAnalyzer (existing).
        if self._rca is not None:
            from aios.core.root_cause import FailureContext, FailureCategory
            ctx = FailureContext(
                failure_id=f"fail_{objective_id}_{iteration}",
                event_type="TESTING_FAILED",
                error=f"Final judge verdict: {final_verdict}",
                error_type="testing_rejection",
                service="test_orchestrator",
                task_id=objective_id,
            )
            analysis = await self._rca.analyze(ctx)
            self._emit_event(
                EventType.ROOT_CAUSE_ANALYZED,
                {"failure_id": ctx.failure_id, "category": analysis.category.value},
                correlation_id,
            )

        # LearningService (existing) — capture the failure pattern.
        if self._learning is not None:
            try:
                capturer = getattr(self._learning, "capture_failure_pattern", None)
                if capturer is not None:
                    capturer(
                        objective_id=objective_id,
                        verdict=final_verdict,
                        evidence=[e.to_dict() for e in evidence],
                    )
                # Emit LearningCaptured-equivalent canonical event (no new type).
                learn_type = getattr(EventType, "LEARNING_CAPTURED", None)
                if learn_type is None:
                    learn_type = EventType.AI_AGENT_AUDIT_EMITTED
                self._emit_event(
                    learn_type,
                    {"objective_id": objective_id, "kind": "failure_pattern"},
                    correlation_id,
                )
            except Exception:
                # Learning is best-effort; never block the loop on it.
                pass

        # PlanningService (existing) — produce a corrected plan (re-execute).
        if self._planning is not None:
            try:
                self._planning.plan({"objective_id": objective_id, "iteration": iteration})
            except Exception:
                pass

        # Regression guard: without a genuinely corrected implementation the
        # loop will not silently converge. Caller supplies the corrected input.
        return True

    def _build_failed(
        self, objective_id, evidence, council_id, critique, verdict, detail, correlation_id, iterations
    ) -> TestingResult:
        self._emit_event(
            EventType.TESTING_FAILED,
            {"objective_id": objective_id, "detail": detail},
            correlation_id,
        )
        result = TestingResult(
            objective_id=objective_id,
            status=TestingStatus.FAILED,
            evidence=evidence,
            council_id=council_id,
            critique=critique,
            final_verdict=verdict,
            iterations=iterations,
            correlation_id=correlation_id,
            detail=detail,
        )
        self._results[objective_id] = result
        return result

    # ------------------------------------------------------------------
    # Retest coordination
    # ------------------------------------------------------------------

    async def coordinate_retest(
        self,
        failed_evidence: list[TestingEvidence],
        correlation_id: str,
    ) -> list[TestingEvidence]:
        """
        Re-execute the perspectives whose evidence failed, returning updated
        (normalized) evidence. Preserves provenance + correlation id.
        """
        retested: list[TestingEvidence] = []
        for ev in failed_evidence:
            if ev.verdict != "fail":
                retested.append(ev)
                continue
            updated = await self.dispatch_perspective(
                perspective=ev.perspective,
                target=ev.target,
                correlation_id=correlation_id,
                builder_id=ev.provenance.source,
            )
            retested.append(updated)
        return retested

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_result(self, objective_id: str) -> TestingResult | None:
        return self._results.get(objective_id)
