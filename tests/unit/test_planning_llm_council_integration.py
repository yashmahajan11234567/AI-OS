import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from aios.events.core.event import Event as CoreEvent
from aios.events.core.types import EventType
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.priority import EventPriority
from aios.events.core.category import category_for_event_type
from aios.events.core.types import SemanticVersion

from aios.services.planning import PlanningService


class TestPlanningServiceLLMCouncilIntegration(unittest.IsolatedAsyncioTestCase):
    """Tests for B1-R1 remediation: PlanningService + LLMCouncil integration."""

    def _make_event(self, event_type: EventType, payload: dict, correlation_id: UUID | None = None) -> CoreEvent:
        """Helper to create a CoreEvent for testing."""
        if correlation_id is None:
            from uuid import uuid4
            correlation_id = uuid4()
        return CoreEvent(
            eventType=event_type,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="test_source",
                version=SemanticVersion(1, 0, 0),
            ),
            correlationId=correlation_id,
            causationId=correlation_id,
            payload=EventPayload(payload),
            priority=EventPriority.NORMAL,
            category=category_for_event_type(event_type),
        )

    @patch('aios.services.planning.LLMCouncil')
    async def test_planning_requests_council_review(self, mock_council_class):
        """Test that PlanningService requests council review for deterministic plans."""
        # Setup
        mock_council = MagicMock()
        mock_council_class.return_value = mock_council

        # Mock deliberate_and_propose to return success
        mock_session = MagicMock()
        mock_session.council_id = "council-123"
        mock_proposal = MagicMock()
        mock_proposal.metadata = {"llm_role": "analyst"}
        mock_proposal.options = [{"id": "approve", "description": "Approve"}]
        mock_proposal.selected_option = "approve"
        mock_council.deliberate_and_propose = AsyncMock(return_value=(mock_session, [mock_proposal]))

        service = PlanningService()
        service.emit = AsyncMock(return_value=1)
        service._llm_council = mock_council

        # Create a planning request event
        event = self._make_event(
            EventType.PLANNING_REQUESTED,
            {
                "planning_id": "plan-1",
                "objective": "Build a feature",
                "constraints": ["time", "budget"],
                "context": {"project_id": "proj-1"}
            }
        )

        # Execute
        await service.handle_planning_requested(event)

        # Verify council was consulted
        mock_council.deliberate_and_propose.assert_called_once()
        call_args = mock_council.deliberate_and_propose.call_args
        self.assertIn("Review deterministic plan", call_args.kwargs.get("topic", ""))
        self.assertEqual(call_args.kwargs.get("builder_excluded"), True)

        # Verify PlanningCompleted was emitted
        service.emit.assert_called_once()
        emitted_event = service.emit.call_args[0][0]
        self.assertEqual(emitted_event.eventType, EventType.PLANNING_COMPLETED)

        # Verify advisory is attached
        payload = emitted_event.payload.to_dict()
        self.assertIn("llm_council_advisory", payload)
        self.assertIsNotNone(payload["llm_council_advisory"])
        self.assertEqual(payload["llm_council_advisory"]["council_session_id"], "council-123")

    @patch('aios.services.planning.LLMCouncil')
    async def test_planning_handles_council_failure(self, mock_council_class):
        """Test that planning continues when council review fails (no fabrication)."""
        # Setup
        mock_council = MagicMock()
        mock_council_class.return_value = mock_council

        # Mock council to raise an exception
        mock_council.deliberate_and_propose = AsyncMock(side_effect=Exception("Council unavailable"))

        service = PlanningService()
        service.emit = AsyncMock(return_value=1)
        service._llm_council = mock_council

        # Create a planning request event
        event = self._make_event(
            EventType.PLANNING_REQUESTED,
            {
                "planning_id": "plan-2",
                "objective": "Build a feature",
                "constraints": [],
                "context": {"project_id": "proj-2"}
            }
        )

        # Execute - should not raise, should continue with advisory indicating failure
        await service.handle_planning_requested(event)

        # Verify PlanningCompleted still emitted (deterministic plan preserved)
        service.emit.assert_called_once()
        emitted_event = service.emit.call_args[0][0]
        payload = emitted_event.payload.to_dict()

        # Verify advisory indicates failure without fabricating success
        self.assertIn("llm_council_advisory", payload)
        advisory = payload["llm_council_advisory"]
        self.assertEqual(advisory["error"], "Council unavailable")
        self.assertEqual(advisory["council_metadata"]["review_failed"], True)
        self.assertEqual(advisory["council_metadata"]["authority"], "advisory_only")

    @patch('aios.services.planning.LLMCouncil')
    async def test_council_advisory_is_marked_as_advisory_only(self, mock_council_class):
        """Test that council advisory is explicitly marked as advisory-only per ADR #10."""
        # Setup
        mock_council = MagicMock()
        mock_council_class.return_value = mock_council
        mock_session = MagicMock()
        mock_session.council_id = "council-test"
        mock_proposal = MagicMock()
        mock_proposal.metadata = {"llm_role": "skeptic"}
        mock_proposal.options = []
        mock_proposal.selected_option = "conditional"
        mock_council.deliberate_and_propose = AsyncMock(return_value=(mock_session, [mock_proposal]))

        service = PlanningService()
        service.emit = AsyncMock(return_value=1)
        service._llm_council = mock_council

        # Create event
        event = self._make_event(
            EventType.PLANNING_REQUESTED,
            {
                "planning_id": "plan-3",
                "objective": "Test advisory marking",
                "constraints": [],
                "context": {}
            }
        )

        # Execute
        await service.handle_planning_requested(event)

        # Verify
        payload = service.emit.call_args[0][0].payload.to_dict()
        advisory = payload["llm_council_advisory"]
        self.assertEqual(advisory["council_metadata"]["advisory_status"], True)
        self.assertEqual(advisory["council_metadata"]["authority"], "advisory_only")
        self.assertIn("roles_consulted", advisory["council_metadata"])
        self.assertEqual(len(advisory["council_metadata"]["roles_consulted"]), 6)

    @patch('aios.services.planning.LLMCouncil')
    async def test_council_not_called_on_none_plan(self, mock_council_class):
        """Test that council is not consulted when deterministic planner returns None."""
        # Setup - council should not be initialized if plan is None
        mock_council = MagicMock()
        mock_council_class.return_value = mock_council

        service = PlanningService()
        service.emit = AsyncMock(return_value=1)
        service._llm_council = mock_council

        # Create event that will produce None plan
        event = self._make_event(
            EventType.PLANNING_REQUESTED,
            {
                "planning_id": "plan-4",
                "objective": "",  # Will cause plan to fail
                "constraints": [],
                "context": {}
            }
        )

        # Execute
        await service.handle_planning_requested(event)

        # Verify PlanningFailed was emitted (not PlanningCompleted)
        emitted_event = service.emit.call_args[0][0]
        self.assertEqual(emitted_event.eventType, EventType.PLANNING_FAILED)

        # Verify council was NOT consulted
        mock_council.deliberate_and_propose.assert_not_called()

    @patch('aios.services.planning.LLMCouncil')
    async def test_correlation_id_preserved_through_council_review(self, mock_council_class):
        """Test that correlation_id is preserved through council review flow."""
        from uuid import uuid4
        original_correlation_id = uuid4()

        # Setup
        mock_council = MagicMock()
        mock_council_class.return_value = mock_council
        mock_session = MagicMock()
        mock_session.council_id = "council-id"
        mock_proposal = MagicMock()
        mock_proposal.metadata = {"llm_role": "simplifier"}
        mock_proposal.options = []
        mock_proposal.selected_option = "approve"
        mock_council.deliberate_and_propose = AsyncMock(return_value=(mock_session, [mock_proposal]))

        service = PlanningService()
        service.emit = AsyncMock(return_value=1)
        service._llm_council = mock_council

        # Create event with specific correlation_id
        event = self._make_event(
            EventType.PLANNING_REQUESTED,
            {
                "planning_id": "plan-5",
                "objective": "Preserve correlation",
                "constraints": [],
                "context": {"correlation_id": str(original_correlation_id)}
            },
            correlation_id=original_correlation_id
        )

        # Execute
        await service.handle_planning_requested(event)

        # Verify correlation_id is preserved in output
        emitted_event = service.emit.call_args[0][0]
        self.assertEqual(emitted_event.correlationId, original_correlation_id)
        self.assertEqual(emitted_event.causationId, original_correlation_id)

    def test_council_property_accessible(self):
        """Test that LLMCouncil is accessible via property."""
        service = PlanningService()
        # Check that the property exists on the class
        self.assertTrue(hasattr(service.__class__, 'llm_council'))
        # Check that it's a property
        import inspect
        self.assertTrue(isinstance(getattr(service.__class__, 'llm_council'), property))


if __name__ == "__main__":
    unittest.main()
