"""
Unit tests for M13 SelfLoopEngine.

Tests the 19-phase canonical self-loop lifecycle orchestrator.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aios.core.self_loop_engine import (
    SelfLoopEngine,
    SelfLoopPhase,
    SelfLoopState,
    SelfLoopCycle,
    PhaseResult,
)
from aios.core.self_prompt import (
    SelfPrompt,
    SelfPromptContext,
    SelfPromptDirective,
    SelfPromptMetadata,
    SelfPromptPriority,
    SelfPromptValidationStatus,
    ExecutionBounds,
)


class TestSelfLoopPhase:
    """Test SelfLoopPhase enum completeness."""

    def test_all_19_phases_defined(self):
        """Verify all 19 canonical phases are defined."""
        phases = list(SelfLoopPhase)
        assert len(phases) == 19

        expected_phases = [
            "USER_INTENT",
            "PLANNING",
            "RESEARCH",
            "REQUIREMENTS",
            "COUNCILS_REVIEWS",
            "PLAN",
            "TASKS",
            "SELF_PROMPT",
            "BOUNDED_EXECUTION",
            "TEST",
            "REVIEW",
            "VERIFICATION",
            "FINAL_JUDGMENT",
            "DECISION",
            "EVIDENCE",
            "LEARNING",
            "MEMORY_KNOWLEDGE",
            "PERSISTENCE",
            "NEXT_SELF_PROMPT",
        ]
        for expected in expected_phases:
            assert any(p.name == expected for p in phases)

    def test_phase_order_is_canonical(self):
        """Verify PHASE_ORDER matches canonical sequence."""
        engine = SelfLoopEngine()
        expected_order = list(SelfLoopPhase)
        assert engine.PHASE_ORDER == expected_order


class TestSelfLoopState:
    """Test SelfLoopState enum."""

    def test_states_defined(self):
        """Verify all states are defined."""
        states = list(SelfLoopState)
        expected = ["IDLE", "RUNNING", "PAUSED", "COMPLETED_CYCLE", "FAILED", "DEGRADED", "RECOVERING"]
        assert len(states) == len(expected)
        for e in expected:
            assert any(s.name == e for s in states)


class TestPhaseResult:
    """Test PhaseResult dataclass."""

    def test_phase_result_creation(self):
        """Test basic PhaseResult creation."""
        result = PhaseResult(
            phase=SelfLoopPhase.PLANNING,
            success=True,
            output={"plan": "test"},
            duration_ms=100.0,
        )
        assert result.phase == SelfLoopPhase.PLANNING
        assert result.success is True
        assert result.output == {"plan": "test"}
        assert result.duration_ms == 100.0
        assert result.error is None
        assert result.provenance_id is not None

    def test_phase_result_with_error(self):
        """Test PhaseResult with error."""
        result = PhaseResult(
            phase=SelfLoopPhase.RESEARCH,
            success=False,
            error="Network timeout",
            duration_ms=5000.0,
        )
        assert result.success is False
        assert result.error == "Network timeout"


class TestSelfLoopCycle:
    """Test SelfLoopCycle dataclass."""

    def test_cycle_creation(self):
        """Test SelfLoopCycle creation."""
        from datetime import datetime, timezone

        cycle = SelfLoopCycle(
            cycle_id="cycle_test123",
            start_time=datetime.now(timezone.utc),
        )
        assert cycle.cycle_id == "cycle_test123"
        assert cycle.state == SelfLoopState.IDLE
        assert cycle.phase_results == {}
        assert cycle.self_prompt is None


class TestSelfLoopEngine:
    """Test SelfLoopEngine functionality."""

    @pytest.fixture
    def engine(self):
        """Create a SelfLoopEngine instance for testing."""
        return SelfLoopEngine()

    def test_engine_creation(self, engine):
        """Test engine instantiation."""
        assert engine is not None
        assert engine.cycle_count == 0
        assert engine.is_running is False
        assert engine.is_paused is False
        assert engine.mock_mode is True
        assert engine.current_cycle is None

    def test_phase_handlers_registered(self, engine):
        """Test all 19 phases have mock handlers."""
        for phase in SelfLoopPhase:
            assert phase in engine._phase_handlers
            assert callable(engine._phase_handlers[phase])

    def test_register_custom_handler(self, engine):
        """Test custom phase handler registration."""
        custom_handler = AsyncMock(return_value={"custom": True})
        engine.register_phase_handler(SelfLoopPhase.PLANNING, custom_handler)
        assert engine._phase_handlers[SelfLoopPhase.PLANNING] == custom_handler

    def test_set_mock_mode(self, engine):
        """Test mock mode toggle."""
        engine.set_mock_mode(False)
        assert engine.mock_mode is False

        engine.set_mock_mode(True)
        assert engine.mock_mode is True

    @pytest.mark.asyncio
    async def test_start_cycle(self, engine):
        """Test starting a new cycle."""
        user_intent = {"intent": "test", "goal": "verify cycle start"}
        cycle = await engine.start_cycle(user_intent)

        assert cycle is not None
        assert cycle.cycle_id.startswith("cycle_")
        assert cycle.state == SelfLoopState.RUNNING
        assert engine.is_running is True
        assert engine.is_paused is False
        assert engine.current_cycle == cycle

    @pytest.mark.asyncio
    async def test_start_cycle_already_running(self, engine):
        """Test error when starting cycle while running."""
        await engine.start_cycle({"test": "intent"})
        with pytest.raises(RuntimeError, match="already running"):
            await engine.start_cycle({"test": "intent2"})

    @pytest.mark.asyncio
    async def test_pause_resume(self, engine):
        """Test pause and resume."""
        await engine.start_cycle({"test": "intent"})
        assert engine.is_paused is False

        await engine.pause()
        assert engine.is_paused is True

        await engine.resume()
        assert engine.is_paused is False

    @pytest.mark.asyncio
    async def test_stop(self, engine):
        """Test stopping the engine."""
        await engine.start_cycle({"test": "intent"})
        await engine.stop()
        assert engine.is_running is False
        assert engine.is_paused is False

    @pytest.mark.asyncio
    async def test_mock_cycle_execution(self, engine):
        """Test full cycle execution in mock mode."""
        user_intent = {"intent": "test_mock_cycle", "goal": "verify all phases complete"}
        cycle = await engine.execute_cycle(user_intent)

        assert cycle.state == SelfLoopState.COMPLETED_CYCLE
        assert cycle.end_time is not None
        assert len(cycle.phase_results) == 19
        assert engine.cycle_count == 1

        # Verify all phases completed
        for phase in SelfLoopPhase:
            assert phase in cycle.phase_results
            result = cycle.phase_results[phase]
            assert result.success is True  # Mock mode always succeeds

    @pytest.mark.asyncio
    async def test_self_prompt_generated_in_cycle(self, engine):
        """Test that self-prompt is generated during cycle."""
        user_intent = {"intent": "test_prompt", "goal": "verify prompt generation"}
        cycle = await engine.execute_cycle(user_intent)

        assert cycle.self_prompt is not None
        assert isinstance(cycle.self_prompt, SelfPrompt)
        assert cycle.self_prompt.cycle_id == cycle.cycle_id

    def test_get_status(self, engine):
        """Test status reporting."""
        status = engine.get_status()
        assert status["running"] is False
        assert status["paused"] is False
        assert status["cycle_count"] == 0
        assert status["mock_mode"] is True


class TestExecutionBounds:
    """Test ExecutionBounds dataclass."""

    def test_default_bounds(self):
        """Test default execution bounds."""
        bounds = ExecutionBounds()
        assert bounds.timeout_seconds == 300
        assert bounds.max_retries == 3
        assert bounds.resource_limits == {}
        assert bounds.allowed_operations == []
        assert bounds.prohibited_operations == []

    def test_custom_bounds(self):
        """Test custom execution bounds."""
        bounds = ExecutionBounds(
            timeout_seconds=600,
            max_retries=5,
            resource_limits={"memory_mb": 1024},
            allowed_operations=["read", "write", "execute"],
            prohibited_operations=["delete", "admin"],
        )
        assert bounds.timeout_seconds == 600
        assert bounds.max_retries == 5
        assert bounds.resource_limits == {"memory_mb": 1024}
        assert bounds.allowed_operations == ["read", "write", "execute"]
        assert bounds.prohibited_operations == ["delete", "admin"]


class TestSelfPromptContext:
    """Test SelfPromptContext dataclass."""

    def test_default_context(self):
        """Test default context creation."""
        context = SelfPromptContext()
        assert context.user_intent == {}
        assert context.approved_plan == {}
        assert context.task_assignments == {}
        assert context.current_aios_state == {}

    def test_context_with_values(self):
        """Test context with initial values."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123"},
            task_assignments={"task1": "assignee1"},
        )
        assert context.user_intent == {"goal": "test"}
        assert context.approved_plan == {"plan_id": "plan_123"}
        assert context.task_assignments == {"task1": "assignee1"}


class TestSelfPromptDirective:
    """Test SelfPromptDirective dataclass."""

    def test_directive_creation(self):
        """Test directive creation."""
        bounds = ExecutionBounds(timeout_seconds=60)
        directive = SelfPromptDirective(
            action_type="execute_task",
            target_systems=["system1", "system2"],
            parameters={"param1": "value1"},
            success_criteria={"completed": True},
            failure_conditions=["timeout", "error"],
            execution_bounds=bounds,
            provenance_chain=["cycle_123", "intent_456"],
            security_context={"level": "standard"},
            knowledge_bounds={"domain": "testing"},
            learning_objectives=["pattern_recognition"],
        )
        assert directive.action_type == "execute_task"
        assert directive.target_systems == ["system1", "system2"]
        assert directive.parameters == {"param1": "value1"}
        assert directive.execution_bounds.timeout_seconds == 60


class TestSelfPrompt:
    """Test SelfPrompt dataclass."""

    def test_self_prompt_creation(self):
        """Test SelfPrompt creation."""
        prompt = SelfPrompt()
        assert prompt.prompt_id is not None
        assert prompt.cycle_id.startswith("cycle_")
        assert prompt.timestamp is not None
        assert prompt.metadata.version == "1.0"
        assert prompt.directive is None

    def test_self_prompt_with_directive(self):
        """Test SelfPrompt with directive."""
        directive = SelfPromptDirective(
            action_type="noop",
            target_systems=[],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=[],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        assert prompt.directive == directive

    def test_self_prompt_validation_status(self):
        """Test validation status transitions."""
        directive = SelfPromptDirective(
            action_type="noop",
            target_systems=[],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=[],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        assert not prompt.is_valid()  # PENDING status

        validated = prompt.with_validation(SelfPromptValidationStatus.VALIDATED)
        assert validated.is_valid()

        rejected = prompt.with_validation(SelfPromptValidationStatus.REJECTED)
        assert not rejected.is_valid()

    def test_self_prompt_expiration(self):
        """Test self-prompt expiration."""
        from datetime import datetime, timedelta, timezone
        directive = SelfPromptDirective(
            action_type="noop",
            target_systems=[],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=[],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        # Expired prompt
        expired = SelfPrompt().with_directive(directive).with_validation(
            SelfPromptValidationStatus.VALIDATED,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert not expired.is_valid()

        # Valid future expiration
        valid = SelfPrompt().with_directive(directive).with_validation(
            SelfPromptValidationStatus.VALIDATED,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert valid.is_valid()

    def test_to_dict(self):
        """Test serialization to dictionary."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={"key": "value"},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(timeout_seconds=60),
            provenance_chain=["cycle_123"],
            security_context={"level": "high"},
            knowledge_bounds={"domain": "test"},
            learning_objectives=["objective1"],
        )
        prompt = SelfPrompt(
            prompt_id="prompt_test",
            cycle_id="cycle_test",
            directive=directive,
        )
        data = prompt.to_dict()

        assert data["prompt_id"] == "prompt_test"
        assert data["cycle_id"] == "cycle_test"
        assert data["directive"]["action_type"] == "execute"
        assert data["directive"]["target_systems"] == ["system1"]
        assert data["directive"]["execution_bounds"]["timeout_seconds"] == 60


class TestSelfPromptFactory:
    """Test SelfPrompt factory methods."""

    def test_create_empty(self):
        """Test creating empty self-prompt for cycle."""
        prompt = SelfPrompt.create_empty("cycle_123")
        assert prompt.cycle_id == "cycle_123"
        assert prompt.directive is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])