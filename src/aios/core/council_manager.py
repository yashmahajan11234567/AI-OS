"""
Council Manager for AI-OS Hermes Kernel.

Manages multi-agent deliberation and consensus building.
Uses the canonical EventBus (C1, Task 5) and canonical EventType enum.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion

logger = logging.getLogger(__name__)


class CouncilRole(str, Enum):
    """Council member roles."""

    CHAIR = "chair"
    MEMBER = "member"
    ADVISOR = "advisor"
    OBSERVER = "observer"


class ConsensusAlgorithm(str, Enum):
    """Consensus algorithms."""

    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    SUPERMAJORITY = "supermajority"  # 2/3
    WEIGHTED = "weighted"
    RANKED_CHOICE = "ranked_choice"


@dataclass
class CouncilMember:
    """A council member."""

    member_id: str
    name: str
    role: CouncilRole = CouncilRole.MEMBER
    weight: float = 1.0
    expertise: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CouncilProposal:
    """A council proposal."""

    proposal_id: str
    council_id: str
    title: str
    description: str
    proposer: str
    options: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CouncilVote:
    """A council vote."""

    vote_id: str
    proposal_id: str
    member_id: str
    option_id: str
    weight: float = 1.0
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CouncilDecision:
    """A council decision."""

    decision_id: str
    council_id: str
    proposal_id: str
    outcome: str
    consensus: bool
    votes: list[CouncilVote]
    decided_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CouncilSession:
    """A council session."""

    council_id: str
    topic: str
    members: list[CouncilMember]
    algorithm: ConsensusAlgorithm = ConsensusAlgorithm.MAJORITY
    quorum: float = 0.5
    created_at: datetime = field(default_factory=datetime.utcnow)
    proposals: list[CouncilProposal] = field(default_factory=list)
    decisions: list[CouncilDecision] = field(default_factory=list)
    status: str = "active"
    metadata: dict[str, Any] = field(default_factory=dict)


class CouncilManager:
    """
    Manages council deliberation and consensus.

    Features:
    - Council convening with configurable members
    - Multiple consensus algorithms
    - Proposal and voting management
    - Decision recording
    - Dissent tracking
    """

    def __init__(self):
        self._councils: dict[str, CouncilSession] = {}
        self._event_bus = get_core_event_bus()
        if self._event_bus is None:
            raise RuntimeError("Canonical EventBus not initialized. Start the kernel first.")

        # Component identity for event emission
        self._identity = ComponentIdentity(
            component_type=ComponentType.CORE_MANAGER,
            component_name="CouncilManager",
            version=SemanticVersion.parse("0.1.0"),
        )

    def convene(
        self,
        topic: str,
        members: list[CouncilMember],
        algorithm: ConsensusAlgorithm = ConsensusAlgorithm.MAJORITY,
        quorum: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> CouncilSession:
        """
        Convene a new council.

        Args:
            topic: Council topic
            members: List of council members
            algorithm: Consensus algorithm
            quorum: Minimum participation for valid decision (0.0-1.0)
            metadata: Additional metadata

        Returns:
            Created CouncilSession
        """
        council_id = f"council_{uuid.uuid4().hex[:12]}"

        council = CouncilSession(
            council_id=council_id,
            topic=topic,
            members=members,
            algorithm=algorithm,
            quorum=quorum,
            metadata=metadata or {},
        )

        self._councils[council_id] = council

        self._emit_event(
            EventType.COUNCIL_CONVENED,
            {
                "council_id": council_id,
                "topic": topic,
                "members": [m.member_id for m in members],
                "algorithm": algorithm.value,
                "quorum": quorum,
            },
            council_id,
        )

        logger.info(f"Convened council {council_id}: {topic}")
        return council

    def propose(
        self,
        council_id: str,
        title: str,
        description: str,
        proposer: str,
        options: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CouncilProposal:
        """
        Create a proposal in a council.

        Args:
            council_id: Council identifier
            title: Proposal title
            description: Proposal description
            proposer: Proposer member ID
            options: Voting options
            metadata: Additional metadata

        Returns:
            Created CouncilProposal
        """
        council = self._councils.get(council_id)
        if not council:
            raise ValueError(f"Council {council_id} not found")

        proposal_id = f"prop_{uuid.uuid4().hex[:12]}"

        proposal = CouncilProposal(
            proposal_id=proposal_id,
            council_id=council_id,
            title=title,
            description=description,
            proposer=proposer,
            options=options or [],
            metadata=metadata or {},
        )

        council.proposals.append(proposal)

        self._emit_event(
            EventType.COUNCIL_PROPOSAL_SUBMITTED,
            {
                "council_id": council_id,
                "proposal_id": proposal_id,
                "title": title,
                "round": len(council.proposals),
            },
            council_id,
        )

        logger.info(f"Proposal {proposal_id} created in council {council_id}")
        return proposal

    def vote(
        self,
        proposal_id: str,
        member_id: str,
        option_id: str,
        reasoning: str = "",
        weight: float = 1.0,
    ) -> CouncilVote:
        """
        Cast a vote on a proposal.

        Args:
            proposal_id: Proposal identifier
            member_id: Voting member ID
            option_id: Selected option ID
            reasoning: Vote reasoning
            weight: Vote weight

        Returns:
            Cast CouncilVote
        """
        # Find council and proposal
        proposal = None
        council = None
        for c in self._councils.values():
            for p in c.proposals:
                if p.proposal_id == proposal_id:
                    proposal = p
                    council = c
                    break
            if council:
                break

        if not proposal or not council:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Verify member is in council
        member = next((m for m in council.members if m.member_id == member_id), None)
        if not member:
            raise ValueError(f"Member {member_id} not in council {council.council_id}")

        vote = CouncilVote(
            vote_id=f"vote_{uuid.uuid4().hex[:12]}",
            proposal_id=proposal_id,
            member_id=member_id,
            option_id=option_id,
            weight=weight * member.weight,
            reasoning=reasoning,
        )

        # Store vote (in a real implementation, this would be persisted)
        logger.info(f"Vote cast: {member_id} -> {option_id} on {proposal_id}")
        return vote

    def decide(
        self,
        proposal_id: str,
        votes: list[CouncilVote] | None = None,
    ) -> CouncilDecision:
        """
        Reach a decision on a proposal.

        Args:
            proposal_id: Proposal identifier
            votes: Optional list of votes (uses stored votes if not provided)

        Returns:
            CouncilDecision
        """
        # Find council and proposal
        proposal = None
        council = None
        for c in self._councils.values():
            for p in c.proposals:
                if p.proposal_id == proposal_id:
                    proposal = p
                    council = c
                    break
            if council:
                break

        if not proposal or not council:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Use provided votes or empty list
        vote_list = votes or []

        # Calculate outcome based on algorithm
        outcome = self._calculate_outcome(council, proposal, vote_list)

        decision = CouncilDecision(
            decision_id=f"dec_{uuid.uuid4().hex[:12]}",
            council_id=council.council_id,
            proposal_id=proposal_id,
            outcome=outcome,
            consensus=self._check_consensus(council, vote_list),
            votes=vote_list,
        )

        council.decisions.append(decision)

        self._event_bus.publish(
            CouncilDecided(
                source_service="council_manager",
                correlation_id=council.council_id,
                payload={
                    "council_id": council.council_id,
                    "proposal_id": proposal_id,
                    "decision_id": decision.decision_id,
                    "outcome": outcome,
                    "consensus": decision.consensus,
                    "vote_count": len(vote_list),
                },
            )
        )

        logger.info(
            f"Decision reached for {proposal_id}: {outcome} (consensus: {decision.consensus})"
        )
        return decision

    def _calculate_outcome(
        self, council: CouncilSession, proposal: CouncilProposal, votes: list[CouncilVote]
    ) -> str:
        """Calculate outcome based on votes and algorithm."""
        if not votes:
            return "no_votes"

        if council.algorithm == ConsensusAlgorithm.UNANIMOUS:
            # All must agree on same option
            if not votes:
                return "no_votes"
            first_vote = votes[0].option_id
            if all(v.option_id == first_vote for v in votes):
                return first_vote
            return "no_consensus"

        elif council.algorithm == ConsensusAlgorithm.MAJORITY:
            # Option with most weight
            tallies = {}
            for vote in votes:
                tallies[vote.option_id] = tallies.get(vote.option_id, 0) + vote.weight
            if tallies:
                return max(tallies, key=tallies.get)
            return "no_votes"

        elif council.algorithm == ConsensusAlgorithm.SUPERMAJORITY:
            # 2/3 weight threshold
            tallies = {}
            total_weight = sum(v.weight for v in votes)
            for vote in votes:
                tallies[vote.option_id] = tallies.get(vote.option_id, 0) + vote.weight
            for option, weight in tallies.items():
                if weight / total_weight >= 2 / 3:
                    return option
            return "no_consensus"

        elif council.algorithm == ConsensusAlgorithm.WEIGHTED:
            return self._calculate_outcome(council, proposal, votes)  # Same as majority

        return "unknown"

    def _check_consensus(
        self, council: CouncilSession, votes: list[CouncilVote]
    ) -> bool:
        """Check if consensus was reached."""
        if not votes:
            return False

        if council.algorithm == ConsensusAlgorithm.UNANIMOUS:
            first = votes[0].option_id
            return all(v.option_id == first for v in votes)

        # For other algorithms, check participation
        participant_weights = sum(v.weight for v in votes)
        total_weights = sum(m.weight for m in council.members)
        participation = participant_weights / total_weights if total_weights > 0 else 0

        return participation >= council.quorum

    def dissent(
        self, council_id: str, member_id: str, proposal_id: str, reason: str
    ) -> bool:
        """Record a dissenting opinion."""
        # In a real implementation, this would be stored
        logger.info(f"Dissent recorded: {member_id} on {proposal_id}: {reason}")

        self._event_bus.publish(
            CouncilDissented(
                source_service="council_manager",
                correlation_id=council_id,
                payload={
                    "council_id": council_id,
                    "member": member_id,
                    "proposal_id": proposal_id,
                    "reason": reason,
                },
            )
        )

        return True

    def get_council(self, council_id: str) -> CouncilSession | None:
        """Get a council session."""
        return self._councils.get(council_id)

    def list_councils(self, status: str | None = None) -> list[dict[str, Any]]:
        """List councils."""
        results = []
        for council in self._councils.values():
            if status and council.status != status:
                continue
            results.append(
                {
                    "council_id": council.council_id,
                    "topic": council.topic,
                    "members": len(council.members),
                    "proposals": len(council.proposals),
                    "decisions": len(council.decisions),
                    "status": council.status,
                    "created_at": council.created_at.isoformat(),
                }
            )
        return results

    def close_council(self, council_id: str) -> bool:
        """Close a council."""
        council = self._councils.get(council_id)
        if not council:
            return False

        council.status = "closed"
        return True

    def get_stats(self) -> dict[str, Any]:
        """Get council manager statistics."""
        return {
            "active_councils": sum(
                1 for c in self._councils.values() if c.status == "active"
            ),
            "total_councils": len(self._councils),
            "total_proposals": sum(len(c.proposals) for c in self._councils.values()),
            "total_decisions": sum(len(c.decisions) for c in self._councils.values()),
        }


# Global council manager
_global_council_manager: CouncilManager | None = None


def get_council_manager() -> CouncilManager:
    """Get or create the global council manager."""
    global _global_council_manager
    if _global_council_manager is None:
        _global_council_manager = CouncilManager()
    return _global_council_manager


def set_council_manager(manager: CouncilManager) -> None:
    """Set the global council manager."""
    global _global_council_manager
    _global_council_manager = manager


__all__ = [
    "CouncilManager",
    "CouncilMember",
    "CouncilProposal",
    "CouncilVote",
    "CouncilDecision",
    "CouncilSession",
    "CouncilRole",
    "ConsensusAlgorithm",
    "get_council_manager",
    "set_council_manager",
]