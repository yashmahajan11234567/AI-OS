"""Council Service.

Engineering Service wrapping the Kernel's CouncilManager behind an event-driven
facade. Manages multi-agent council deliberation/consensus; exposes
convene/propose/vote/decide/dissent and emits CouncilConvened/CouncilDeliberated/
CouncilDecided/CouncilDissented (legacy events).
Also emits canonical Council events via CoreEvent.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4, UUID

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
from aios.events.core.bus import get_core_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import EventCategory, category_for_event_type
from aios.events.core.priority import EventPriority
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

    async def _emit_legacy_event(self, event: Event) -> int:
        """Emit a legacy event by converting to CoreEvent.

        This is a compatibility wrapper that wraps the legacy event
        in a CoreEvent for the canonical event bus.
        """
        # Convert legacy event to CoreEvent
        # Legacy events have event_type, source_service, correlation_id, payload
        legacy_event_type = event.event_type

        # Map to canonical EventType if possible
        from aios.services.base import BaseService
        from aios.events.core.types import EventType as CanonicalEventType
        from aios.events.base import EventType as LegacyEventType

        # If legacy_event_type is already a canonical EventType, use it directly
        if isinstance(legacy_event_type, CanonicalEventType):
            canonical_type = legacy_event_type
        else:
            # Otherwise look up in the legacy mapping
            canonical_type = BaseService._LEGACY_TO_CANONICAL.get(legacy_event_type)
            if canonical_type is None:
                logger.warning(f"No canonical mapping for legacy event type: {legacy_event_type}")
                # Fallback - use a generic event type
                canonical_type = CanonicalEventType.AI_AGENT_AUDIT_EMITTED

        # Always generate a proper UUID for correlationId
        # Legacy correlation_ids may not be valid UUID strings
        import uuid
        correlation_uuid = uuid.uuid4()

        core_event = CoreEvent(
            eventType=canonical_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name=self.name,
                version=SemanticVersion.parse(self.version),
            ),
            correlationId=correlation_uuid,
            causationId=uuid.uuid4(),
            payload=EventPayload(event.payload),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(canonical_type),
        )

        result = await self.emit(core_event)
        logger.info(f"CouncilService emit legacy event {legacy_event_type} -> {canonical_type}: {result}")
        return result

    async def convene(self, topic: str, members: list[CouncilMember], **kwargs: Any):
        session = await self._manager.convene(topic=topic, members=members, **kwargs)
        await self._emit_legacy_event(
            CouncilConvened(
                source_service=self.name,
                correlation_id=str(session.council_id if hasattr(session, "council_id") else uuid4().hex[:8]),
                payload={"council_id": getattr(session, "council_id", ""), "topic": topic},
            )
        )
        return session

    async def propose(self, council_id: str, title: str, description: str, proposer: str, **kwargs: Any):
        proposal = await self._manager.propose(
            council_id=council_id, title=title, description=description, proposer=proposer, **kwargs
        )
        await self._emit_legacy_event(
            CouncilDeliberated(
                source_service=self.name,
                correlation_id=str(getattr(proposal, "proposal_id", uuid4().hex[:8])),
                payload={"council_id": council_id, "proposal_id": getattr(proposal, "proposal_id", "")},
            )
        )
        return proposal

    async def vote(self, proposal_id: str, member_id: str, option_id: str, **kwargs: Any):
        return await self._manager.vote(proposal_id=proposal_id, member_id=member_id, option_id=option_id, **kwargs)

    async def decide(self, proposal_id: str, votes=None):
        decision = await self._manager.decide(proposal_id=proposal_id, votes=votes)
        await self._emit_legacy_event(
            CouncilDecided(
                source_service=self.name,
                correlation_id=str(getattr(decision, "proposal_id", proposal_id)),
                payload={"proposal_id": proposal_id, "decision": getattr(decision, "outcome", "")},
            )
        )
        return decision

    async def dissent(self, council_id: str, member_id: str, proposal_id: str, reason: str) -> bool:
        ok = await self._manager.dissent(council_id, member_id, proposal_id, reason)
        await self._emit_legacy_event(
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
