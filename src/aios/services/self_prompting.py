"""
SelfPromptingService for AI-OS Hermes Kernel.

Bounded, traceable, objective-linked self-questioning (FINAL PART VI / ADR #10).
Routes self-questioning into LLMCouncil for bounded reasoning/synthesis.

Requirements (ADR #10, FINAL):
- bounded self-prompting
- explicit maximum recursion/depth bound
- explicit token/budget bound
- objective-cited operation
- complete traceability
- routing through LLMCouncil
- no uncontrolled recursion
- no open-ended autonomous loop

Every self-prompting operation must be bounded and auditable.
The implementation MUST NOT permit:
- infinite recursion
- unbounded self-improvement loops
- uncontrolled prompt generation
- recursive spawning without a bound
- bypassing the council
- bypassing security controls

The service must fail safely when bounds are exceeded.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aios.core.council_manager import CouncilManager, CouncilSession, get_council_manager
from aios.core.llm_council import LLMCouncil, LLMRole, LLMCouncilConfig
from aios.services.base import BaseService, ServiceStatus


@dataclass
class SelfPromptConfig:
    """Configuration for SelfPromptingService bounds (ADR #10)."""

    max_depth: int = 5  # ADR #10 bound: maximum recursion depth
    token_budget: int = 4000  # ADR #10 bound: maximum tokens per operation
    require_objective_cite: bool = True  # Must cite objective_id
    allow_open_recursion: bool = False  # Explicitly forbidden (ADR #10)
    max_tokens_per_prompt: int = 800  # Token budget per prompt


@dataclass
class PromptTrace:
    """Trace record for a single self-prompt operation."""

    prompt_id: str
    objective: str
    objective_id: str
    seed_question: str
    depth: int
    council_id: str | None = None
    proposal_ids: list[str] = field(default_factory=list)
    critique_result_id: str | None = None
    decision_id: str | None = None
    outcome: dict[str, Any] | None = None
    tokens_used: int = 0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None


@dataclass
class SelfPromptResult:
    """Result of a bounded self-prompting operation."""

    objective: str
    objective_id: str
    traces: list[PromptTrace]
    total_tokens_used: int
    max_depth_reached: int
    bounded: bool  # True if bounds were enforced
    completed_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


class SelfPromptingService(BaseService):
    """
    Bounded, traceable, objective-linked self-questioning (FINAL PART VI / ADR #10).

    Routes self-questioning through LLMCouncil with hard bounds:
    - Depth capped at config.max_depth
    - Token budget enforced per operation
    - Every prompt MUST cite objective_id
    - No open recursion (allow_open_recursion=False always)
    - Returns traceable record of prompts + council outcomes
    """

    name = "self_prompting"
    version = "1.0.0"
    description = "Bounded self-prompting service for AI-OS reasoning and self-correction"

    def __init__(
        self,
        council: LLMCouncil | None = None,
        config: SelfPromptConfig | None = None,
        event_bus=None,
        info=None,
        **kwargs,
    ):
        # Pass event_bus and info to parent
        super().__init__(event_bus=event_bus, info=info)
        self._council = council or LLMCouncil()
        self._config = config or SelfPromptConfig()
        self._traces: list[PromptTrace] = []
        self._total_tokens = 0

    @property
    def council(self) -> LLMCouncil:
        """Get the LLMCouncil instance."""
        return self._council

    @property
    def config(self) -> SelfPromptConfig:
        """Get the self-prompting configuration."""
        return self._config

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ~ 1 token)."""
        return max(1, len(text) // 4)

    def _check_bounds(self, depth: int, tokens_so_far: int, objective_id: str) -> None:
        """Check bounds and raise if exceeded (fail-closed)."""
        if depth > self._config.max_depth:
            raise ValueError(
                f"Self-prompting depth {depth} exceeds maximum {self._config.max_depth}. "
                f"ADR #10: bounded self-prompting required."
            )

        if tokens_so_far > self._config.token_budget:
            raise ValueError(
                f"Self-prompting token budget exceeded: {tokens_so_far} > {self._config.token_budget}. "
                f"ADR #10: token budget enforcement required."
            )

        if self._config.require_objective_cite and not objective_id:
            raise ValueError(
                "Self-prompting requires objective_id citation. "
                "ADR #10: objective-cited operation required."
            )

        if self._config.allow_open_recursion:
            raise ValueError(
                "allow_open_recursion=True violates ADR #10. "
                "Self-prompting must not permit uncontrolled recursion."
            )

    async def prompt(
        self,
        objective: str,
        objective_id: str,
        *,
        seed_questions: list[str] | None = None,
        depth: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Bounded self-questioning loop routed into LLMCouncil.

        Args:
            objective: The objective/goal for this self-prompting session
            objective_id: Unique identifier for the objective (must be cited, ADR #10)
            seed_questions: Initial questions to explore (default: generate from objective)
            depth: Current recursion depth (internal use)

        Returns:
            List of traceable records: {prompt, depth, council_id, outcome}

        Raises:
            ValueError: If bounds are exceeded (fail-closed per ADR #10)
        """
        # Check bounds at entry
        tokens_so_far = self._estimate_tokens(objective)
        self._check_bounds(depth, tokens_so_far, objective_id)

        # Generate seed questions if not provided
        if seed_questions is None:
            seed_questions = self._generate_seed_questions(objective)

        traces = []

        for question in seed_questions:
            # Check bounds for each question
            question_tokens = self._estimate_tokens(question)
            tokens_so_far += question_tokens
            self._check_bounds(depth, tokens_so_far, objective_id)

            # Create trace record
            trace = PromptTrace(
                prompt_id=f"prompt_{uuid.uuid4().hex[:12]}",
                objective=objective,
                objective_id=objective_id,
                seed_question=question,
                depth=depth,
            )

            try:
                # Route through LLMCouncil for deliberation
                session = await self._council.deliberate(
                    topic=f"Self-Prompt: {question[:100]}",
                    objective_id=objective_id,
                    builder_excluded=True,  # Builder cannot self-approve (INV-009)
                )

                trace.council_id = session.council_id

                # Have each role propose independently (Stage 1)
                session, proposals = await self._council.deliberate_and_propose(
                    topic=f"Self-Prompt: {question[:100]}",
                    proposal_title=f"Analysis: {question}",
                    proposal_description=f"Objective: {objective}\nQuestion: {question}",
                    objective_id=objective_id,
                    builder_excluded=True,
                )

                trace.proposal_ids = [p.proposal_id for p in proposals]

                # For self-prompting, we simulate the critique/synthesis flow
                # In a full implementation, this would use real model responses
                # For now, we create mock accuracy/insight scores per role

                member_ids = [m.member_id for m in session.members]
                accuracy_scores = {mid: 0.7 + (hash(mid) % 30) / 100.0 for mid in member_ids}
                insight_scores = {mid: 0.6 + (hash(mid + "insight") % 40) / 100.0 for mid in member_ids}

                # Get the underlying council manager
                council_manager = self._council.manager

                # Run critique stage (Stage 2)
                critique_result = await council_manager.critique(
                    council_id=session.council_id,
                    accuracy_scores=accuracy_scores,
                    insight_scores=insight_scores,
                    relabel_rounds=1,
                )

                trace.critique_result_id = critique_result.council_id

                # Run synthesis stage (Stage 3)
                decision = await council_manager.synthesize(
                    council_id=session.council_id,
                    critique=critique_result,
                )

                trace.decision_id = decision.decision_id

                # Build outcome
                trace.outcome = {
                    "decision": decision.outcome,
                    "consensus": decision.consensus,
                    "dissenter_override": critique_result.dissenter_override,
                    "override_member": critique_result.override_member_label,
                    "rankings_count": len(critique_result.rankings),
                    "dissent_preserved": len(critique_result.dissent_preserved),
                }

                # Update token count
                response_tokens = self._estimate_tokens(str(trace.outcome))
                trace.tokens_used = question_tokens + response_tokens
                tokens_so_far += response_tokens
                self._total_tokens += trace.tokens_used

            except Exception as e:
                trace.error = str(e)
                trace.outcome = {"error": str(e)}

            finally:
                trace.completed_at = datetime.utcnow()
                traces.append(trace)
                self._traces.append(trace)

        # Recursive continuation (bounded)
        deeper_traces: list[dict[str, Any]] = []
        if depth < self._config.max_depth and seed_questions:
            # Generate follow-up questions based on outcomes (simulated)
            follow_up = self._generate_followup_questions(traces)
            if follow_up:
                # Recursive call with incremented depth. The recursive call
                # returns already-rendered dicts, so we keep them separate from
                # the local ``traces`` PromptTrace list (which is re-rendered
                # below). Mixing the two would crash the final render pass.
                deeper_traces = await self.prompt(
                    objective=objective,
                    objective_id=objective_id,
                    seed_questions=follow_up,
                    depth=depth + 1,
                )

        return [
            {
                "prompt_id": t.prompt_id,
                "objective": t.objective,
                "objective_id": t.objective_id,
                "seed_question": t.seed_question,
                "depth": t.depth,
                "council_id": t.council_id,
                "proposal_ids": t.proposal_ids,
                "critique_result_id": t.critique_result_id,
                "decision_id": t.decision_id,
                "outcome": t.outcome,
                "tokens_used": t.tokens_used,
                "started_at": t.started_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "error": t.error,
            }
            for t in traces
        ] + deeper_traces

    def _generate_seed_questions(self, objective: str) -> list[str]:
        """Generate initial seed questions from objective."""
        return [
            f"What are the key risks in achieving: {objective}?",
            f"What assumptions underlie: {objective}?",
            f"What alternative approaches exist for: {objective}?",
            f"What evidence would validate: {objective}?",
        ]

    def _generate_followup_questions(self, traces: list[PromptTrace]) -> list[str]:
        """Generate follow-up questions based on trace outcomes (simulated)."""
        followups = []
        for trace in traces:
            if trace.outcome and not trace.error:
                if trace.outcome.get("dissenter_override"):
                    followups.append(
                        f"Explore dissenter perspective on: {trace.seed_question}"
                    )
                if trace.outcome.get("consensus") is False:
                    followups.append(
                        f"Resolve lack of consensus on: {trace.seed_question}"
                    )
        return followups[:2]  # Limit to 2 follow-ups per level

    def get_traces(self) -> list[PromptTrace]:
        """Get all trace records."""
        return list(self._traces)

    def get_total_tokens(self) -> int:
        """Get total tokens used."""
        return self._total_tokens

    def reset_traces(self) -> None:
        """Reset trace history."""
        self._traces.clear()
        self._total_tokens = 0

    async def on_start(self) -> None:
        """Start the service."""
        await super().on_start()
        # No event subscriptions needed for self-prompting service

    async def on_stop(self) -> None:
        """Stop the service."""
        await super().on_stop()

    async def on_health_check(self) -> bool:
        """Health check."""
        return self._status == ServiceStatus.RUNNING

    def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        stats = super().get_stats()
        stats.update(
            {
                "config": {
                    "max_depth": self._config.max_depth,
                    "token_budget": self._config.token_budget,
                    "require_objective_cite": self._config.require_objective_cite,
                    "allow_open_recursion": self._config.allow_open_recursion,
                },
                "total_traces": len(self._traces),
                "total_tokens": self._total_tokens,
            }
        )
        return stats


# Global instance
_global_self_prompting_service: SelfPromptingService | None = None


def get_self_prompting_service(
    council: LLMCouncil | None = None,
    config: SelfPromptConfig | None = None,
) -> SelfPromptingService:
    """Get or create the global SelfPromptingService."""
    global _global_self_prompting_service
    if _global_self_prompting_service is None:
        _global_self_prompting_service = SelfPromptingService(
            council=council, config=config
        )
    return _global_self_prompting_service


def set_self_prompting_service(service: SelfPromptingService) -> None:
    """Set the global SelfPromptingService."""
    global _global_self_prompting_service
    _global_self_prompting_service = service


__all__ = [
    "SelfPromptingService",
    "SelfPromptConfig",
    "PromptTrace",
    "SelfPromptResult",
    "get_self_prompting_service",
    "set_self_prompting_service",
]