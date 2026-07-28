"""Council Service.

Engineering Service wrapping the Kernel's CouncilManager behind an event-driven
facade. Manages multi-agent council deliberation/consensus; exposes
convene/propose/vote/decide/dissent and emits CouncilConvened/CouncilDeliberated/
CouncilDecided/CouncilDissented.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aios.core.council_manager import (
    CouncilManager,
    CouncilMember,
    ConsensusAlgorithm,
    get_council_manager,
)
from aios.events.base import Event
from aios.events.types import (
    CouncilConvened,
    CouncilDecided,
    CouncilDeliberated,
    CouncilDissented,
)
from aios.services.base import BaseService

logger = logging.getLogger(__name__)


class CouncilService(BaseService):
    """Event-driven facade over the Kernel CouncilManager."""

    name = "council"
    version = "1.0.0"
    description = "Multi-agent deliberation and consensus"
    depends_on: list[str] = []

    def __init__(self, *args, manager: CouncilManager | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager = manager or get_council_manager()

    @property
    def manager(self) -> CouncilManager:
        return self._manager

    async def on_start(self) -> None:
        pass

    def convene(self, topic: str, members: list[CouncilMember], **kwargs: Any):
        session = self._manager.convene(topic=topic, members=members, **kwargs)
        self.emit(
            CouncilConvened(
                source_service=self.name,
                correlation_id=str(session.id if hasattr(session, "id") else uuid4().hex[:8]),
                payload={"council_id": getattr(session, "id", ""), "topic": topic},
            )
        )
        return session

    def propose(self, council_id: str, title: str, description: str, proposer: str, **kwargs: Any):
        proposal = self._manager.propose(
            council_id=council_id, title=title, description=description, proposer=proposer, **kwargs
        )
        self.emit(
            CouncilDeliberated(
                source_service=self.name,
                correlation_id=str(getattr(proposal, "id", uuid4().hex[:8])),
                payload={"council_id": council_id, "proposal_id": getattr(proposal, "id", "")},
            )
        )
        return proposal

    def vote(self, proposal_id: str, member_id: str, option_id: str, **kwargs: Any):
        return self._manager.vote(proposal_id=proposal_id, member_id=member_id, option_id=option_id, **kwargs)

    def decide(self, proposal_id: str, votes=None):
        decision = self._manager.decide(proposal_id=proposal_id, votes=votes)
        self.emit(
            CouncilDecided(
                source_service=self.name,
                correlation_id=str(getattr(decision, "proposal_id", proposal_id)),
                payload={"proposal_id": proposal_id, "decision": getattr(decision, "decision", "")},
            )
        )
        return decision

    def dissent(self, council_id: str, member_id: str, proposal_id: str, reason: str) -> bool:
        ok = self._manager.dissent(council_id, member_id, proposal_id, reason)
        self.emit(
            CouncilDissented(
                source_service=self.name,
                correlation_id=council_id,
                payload={"council_id": council_id, "proposal_id": proposal_id, "member_id": member_id},
            )
        )
        return ok

    def list_councils(self, status: str | None = None):
        return self._manager.list_councils(status=status)

    def close_council(self, council_id: str) -> bool:
        return self._manager.close_council(council_id)

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        base["manager"] = self._manager.get_stats()
        return base


__all__ = ["CouncilService"]
