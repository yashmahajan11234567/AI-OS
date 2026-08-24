"""
LLMCouncil façade for AI-OS Hermes Kernel.

Façade over CouncilManager for the REASONING / SELF-PROMPTING domain
(COUNCIL 1 LLM Council, FINAL PART XVI). SIX roles only.
Does NOT replace Verification or the Testing Council.
Single CouncilManager substrate; this is one council session family.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from aios.core.council_manager import (
    CouncilManager,
    CouncilMember,
    CouncilRole,
    CouncilSession,
    ConsensusAlgorithm,
    get_council_manager,
)


class LLMRole(str, Enum):
    """The six cognitive roles of the LLM Council (FINAL PART XVI)."""

    ANALYST = "analyst"
    CONTRARIAN = "contrarian"
    OUTSIDER = "outsider"
    SKEPTIC = "skeptic"
    SPECIALIST = "specialist"
    SIMPLIFIER = "simplifier"


# Role expertise descriptions for diverse perspectives (EVC worldview-diverse advisors)
_ROLE_EXPERTISE = {
    LLMRole.ANALYST: [
        "systematic_analysis",
        "evidence_evaluation",
        "logical_reasoning",
        "structured_thinking",
    ],
    LLMRole.CONTRARIAN: [
        "devils_advocate",
        "assumption_challenge",
        "counter_argument",
        "bias_detection",
    ],
    LLMRole.OUTSIDER: [
        "external_perspective",
        "novice_viewpoint",
        "unconstrained_thinking",
        "cross_domain_insight",
    ],
    LLMRole.SKEPTIC: [
        "critical_thinking",
        "claim_verification",
        "risk_identification",
        "evidence_scrutiny",
    ],
    LLMRole.SPECIALIST: [
        "domain_expertise",
        "technical_depth",
        "best_practices",
        "implementation_detail",
    ],
    LLMRole.SIMPLIFIER: [
        "complexity_reduction",
        "essentialism",
        "clarity_focus",
        "maintainability",
    ],
}


@dataclass
class LLMCouncilConfig:
    """Configuration for LLMCouncil."""

    default_algorithm: ConsensusAlgorithm = ConsensusAlgorithm.WEIGHTED
    default_quorum: float = 0.5
    include_all_roles: bool = True


class LLMCouncil:
    """
    Façade over CouncilManager for the REASONING / SELF-PROMPTING domain
    (COUNCIL 1 LLM Council, FINAL PART XVI). SIX roles only.

    Does NOT replace Verification or the Testing Council.
    Single CouncilManager substrate; this is one council session family.
    """

    def __init__(
        self,
        manager: CouncilManager | None = None,
        config: LLMCouncilConfig | None = None,
    ) -> None:
        """
        Initialize the LLM Council façade.

        Args:
            manager: CouncilManager instance (defaults to global get_council_manager())
            config: Configuration for the council
        """
        self._manager = manager or get_council_manager()
        self._config = config or LLMCouncilConfig()

    @property
    def manager(self) -> CouncilManager:
        """Get the underlying CouncilManager."""
        return self._manager

    def _create_role_member(
        self, role: LLMRole, member_id: str | None = None
    ) -> CouncilMember:
        """Create a CouncilMember for an LLM role."""
        return CouncilMember(
            member_id=member_id or f"llm_{role.value}_{uuid.uuid4().hex[:8]}",
            name=f"LLM {role.value.title()}",
            role=CouncilRole.MEMBER,
            weight=1.0,
            expertise=_ROLE_EXPERTISE.get(role, []),
            metadata={
                "llm_role": role.value,
                "council_type": "llm_council",
            },
        )

    async def deliberate(
        self,
        topic: str,
        *,
        objective_id: str,
        roles: list[LLMRole] | None = None,
        builder_excluded: bool = True,
    ) -> CouncilSession:
        """
        Convene an LLM Council session with the six cognitive roles.

        Args:
            topic: The topic for deliberation
            objective_id: The objective ID that this deliberation serves (ADR #10)
            roles: Specific roles to include (default: all 6)
            builder_excluded: Exclude the builder/originator from voting (INV-009, builder cannot self-approve)

        Returns:
            CouncilSession ready for propose/critique/synthesize flow
        """
        # Determine which roles to use
        active_roles = roles or list(LLMRole)
        if self._config.include_all_roles and len(active_roles) < len(LLMRole):
            # Ensure all 6 roles are present unless explicitly limited
            active_roles = list(LLMRole)

        # Create council members for each role
        members = [self._create_role_member(role) for role in active_roles]

        # Builder exclusion: the originator of the self-prompt is not a voting member
        # This is enforced by not including them in the members list
        # The builder_excluded parameter is a contract assertion
        if not builder_excluded:
            # Log warning but still proceed - architecture mandates exclusion
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "builder_excluded=False violates INV-009 (builder cannot self-approve). "
                "LLM Council architecture requires builder exclusion."
            )

        # Convene the council
        session = await self._manager.convene(
            topic=f"LLM Council: {topic}",
            members=members,
            algorithm=self._config.default_algorithm,
            quorum=self._config.default_quorum,
            metadata={
                "council_type": "llm_council",
                "objective_id": objective_id,
                "roles": [r.value for r in active_roles],
                "builder_excluded": builder_excluded,
            },
        )

        return session

    async def deliberate_and_propose(
        self,
        topic: str,
        proposal_title: str,
        proposal_description: str,
        *,
        objective_id: str,
        options: list[dict[str, Any]] | None = None,
        roles: list[LLMRole] | None = None,
        builder_excluded: bool = True,
    ) -> tuple[CouncilSession, list[Any]]:
        """
        Convenience: convene and have each role submit an independent proposal (blind).

        This implements Stage 1 of council synthesis (COUNCIL_SYNTHESIS §2):
        each perspective submits independently.

        Args:
            topic: Council topic
            proposal_title: Title for proposals
            proposal_description: Description for proposals
            objective_id: Objective ID (ADR #10)
            options: Voting options (default: approve/reject)
            roles: Roles to include
            builder_excluded: Builder exclusion flag

        Returns:
            Tuple of (CouncilSession, list of proposals)
        """
        session = await self.deliberate(
            topic=topic,
            objective_id=objective_id,
            roles=roles,
            builder_excluded=builder_excluded,
        )

        # Each role proposes independently (blind submission)
        proposals = []
        default_options = options or [
            {"id": "approve", "description": "Approve the proposal"},
            {"id": "reject", "description": "Reject the proposal"},
            {"id": "conditional", "description": "Approve with conditions"},
        ]

        for member in session.members:
            proposal = await self._manager.propose(
                council_id=session.council_id,
                title=proposal_title,
                description=f"{proposal_description}\n\n[Perspective: {member.metadata.get('llm_role', 'unknown')}]",
                proposer=member.member_id,
                options=default_options,
                metadata={
                    "objective_id": objective_id,
                    "llm_role": member.metadata.get("llm_role"),
                    "independent_proposal": True,
                },
            )
            proposals.append(proposal)

        return session, proposals

    def get_available_roles(self) -> list[LLMRole]:
        """Get list of available LLM roles."""
        return list(LLMRole)


__all__ = [
    "LLMCouncil",
    "LLMRole",
    "LLMCouncilConfig",
]