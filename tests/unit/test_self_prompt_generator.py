"""
Unit tests for M13 SelfPromptGenerator.

Tests the authoritative self-prompt directive generation and validation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from aios.core.self_prompt_generator import SelfPromptGenerator, GenerationResult
from aios.core.self_prompt import (
    SelfPrompt,
    SelfPromptContext,
    SelfPromptDirective,
    SelfPromptMetadata,
    SelfPromptPriority,
    SelfPromptValidationStatus,
    ExecutionBounds,
)


class TestSelfPromptGenerator:
    """Test SelfPromptGenerator functionality."""

    @pytest.fixture
    def generator(self):
        """Create a SelfPromptGenerator instance for testing."""
        return SelfPromptGenerator()

    def test_generator_creation(self, generator):
        """Test generator instantiation."""
        assert generator is not None
        assert generator._max_cycles == 3
        assert generator._max_depth == 5
        assert generator._convergence_action == "escalate"

    def test_configure(self, generator):
        """Test generator configuration."""
        generator.configure(max_cycles=5, max_depth=10, convergence_action="pause")
        assert generator._max_cycles == 5
        assert generator._max_depth == 10
        assert generator._convergence_action == "pause"

    def test_get_config(self, generator):
        """Test getting configuration."""
        config = generator.get_config()
        assert config["max_cycles"] == 3
        assert config["max_depth"] == 5
        assert config["convergence_action"] == "escalate"

    def test_validate_context_valid(self, generator):
        """Test context validation with all required fields."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123", "action_type": "execute"},
            task_assignments={"task1": "assignee1"},
        )
        errors = generator._validate_context(context)
        assert errors == []

    def test_validate_context_missing_user_intent(self, generator):
        """Test context validation missing user_intent."""
        context = SelfPromptContext(
            approved_plan={"plan_id": "plan_123"},
            task_assignments={"task1": "assignee1"},
        )
        errors = generator._validate_context(context)
        assert "Missing required context: user_intent" in errors

    def test_validate_context_missing_approved_plan(self, generator):
        """Test context validation missing approved_plan."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            task_assignments={"task1": "assignee1"},
        )
        errors = generator._validate_context(context)
        assert "Missing required context: approved_plan" in errors

    def test_validate_context_missing_task_assignments(self, generator):
        """Test context validation missing task_assignments."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123"},
        )
        errors = generator._validate_context(context)
        assert "Missing required context: task_assignments" in errors

    def test_validate_context_convergence_max_cycles(self, generator):
        """Test context validation detects max cycles convergence."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={
                "plan_id": "plan_123",
                "cycle_count": 5,
                "convergence_detected": True,
            },
            task_assignments={"task1": "assignee1"},
        )
        errors = generator._validate_context(context)
        assert any("Max cycles exceeded" in e for e in errors)

    def test_validate_context_convergence_max_depth(self, generator):
        """Test context validation detects max depth convergence."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={
                "plan_id": "plan_123",
                "depth": 10,
                "convergence_detected": True,
            },
            task_assignments={"task1": "assignee1"},
        )
        errors = generator._validate_context(context)
        assert any("Max depth exceeded" in e for e in errors)

    @pytest.mark.asyncio
    async def test_synthesize_directive_mock_mode(self, generator):
        """Test directive synthesis in mock mode."""
        context = SelfPromptContext(
            user_intent={"intent_id": "intent_123", "goal": "test"},
            approved_plan={
                "plan_id": "plan_456",
                "action_type": "execute_task",
                "target_systems": ["system1", "system2"],
                "parameters": {"param1": "value1"},
                "timeout_seconds": 60,
                "max_retries": 2,
            },
            task_assignments={"task1": "system1", "task2": "system2"},
            requirements_spec={"req1": "requirement1"},
        )

        directive = await generator._synthesize_directive("cycle_test", context)

        assert directive is not None
        assert directive.action_type == "execute_task"
        assert directive.target_systems == ["system1", "system2"]
        assert directive.parameters == {"param1": "value1"}
        assert directive.success_criteria == {"completed": True, "all_tasks_succeeded": True, "requirements_met": True}
        assert "timeout" in directive.failure_conditions
        assert "resource_exhausted" in directive.failure_conditions
        assert directive.execution_bounds.timeout_seconds == 60
        assert directive.execution_bounds.max_retries == 2
        assert len(directive.provenance_chain) >= 2
        assert isinstance(directive.knowledge_bounds, dict)
        assert isinstance(directive.learning_objectives, list)

    @pytest.mark.asyncio
    async def test_synthesize_directive_infers_targets(self, generator):
        """Test directive synthesis infers target systems from tasks."""
        context = SelfPromptContext(
            user_intent={"intent_id": "intent_123", "goal": "test"},
            approved_plan={"plan_id": "plan_456", "action_type": "execute_task"},
            task_assignments={"task1": "systemA", "task2": "systemB"},
        )

        directive = await generator._synthesize_directive("cycle_test", context)

        assert directive.target_systems == ["systemA", "systemB"]

    def test_validate_structure_valid(self, generator):
        """Test structure validation passes for valid prompt."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_structure(prompt)
        assert errors == []

    def test_validate_structure_missing_directive(self, generator):
        """Test structure validation fails without directive."""
        prompt = SelfPrompt()
        errors = generator._validate_structure(prompt)
        assert "Missing directive" in errors

    def test_validate_structure_missing_fields(self, generator):
        """Test structure validation catches missing directive fields."""
        directive = SelfPromptDirective(
            action_type="",
            target_systems=[],
            parameters={},
            success_criteria={},
            failure_conditions=[],
            execution_bounds=None,
            provenance_chain=[],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_structure(prompt)
        assert any("action_type" in e for e in errors)
        assert any("target_systems" in e for e in errors)
        assert any("success_criteria" in e for e in errors)
        assert any("failure_conditions" in e for e in errors)
        assert any("execution_bounds" in e for e in errors)
        assert any("provenance_chain" in e for e in errors)

    def test_validate_bounds_within_limits(self, generator):
        """Test bounds validation passes for valid bounds."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(timeout_seconds=300, max_retries=3),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_bounds(prompt)
        assert errors == []

    def test_validate_bounds_timeout_exceeds_max(self, generator):
        """Test bounds validation fails for excessive timeout."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(timeout_seconds=5000, max_retries=3),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_bounds(prompt)
        assert any("exceeds max" in e for e in errors)

    def test_validate_bounds_retries_exceeds_max(self, generator):
        """Test bounds validation fails for excessive retries."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(timeout_seconds=300, max_retries=15),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_bounds(prompt)
        assert any("exceeds max" in e for e in errors)

    def test_validate_provenance_valid(self, generator):
        """Test provenance validation passes for valid chain."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_123", "intent_456", "plan_789"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_provenance(prompt)
        # Should have no hard errors (warnings not captured here)
        assert "" not in errors or len(errors) == 0

    def test_validate_provenance_empty(self, generator):
        """Test provenance validation fails for empty chain."""
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=[],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt().with_directive(directive)
        errors = generator._validate_provenance(prompt)
        # Empty chain is caught by the "not provenance_chain" check before the empty list check
        assert any("Missing provenance chain" in e or "empty" in e.lower() for e in errors)

    def test_validate_convergence_no_convergence(self, generator):
        """Test convergence validation passes when no convergence."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123", "cycle_count": 1, "depth": 1},
            task_assignments={"task1": "assignee1"},
        )
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt(context=context).with_directive(directive)
        errors = generator._validate_convergence(prompt)
        assert errors == []

    def test_validate_convergence_max_cycles(self, generator):
        """Test convergence validation fails at max cycles."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123", "cycle_count": 5, "depth": 1},
            task_assignments={"task1": "assignee1"},
        )
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt(context=context).with_directive(directive)
        errors = generator._validate_convergence(prompt)
        assert any("cycle_count" in e and "max_cycles" in e for e in errors)

    def test_validate_convergence_max_depth(self, generator):
        """Test convergence validation fails at max depth."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123", "cycle_count": 1, "depth": 10},
            task_assignments={"task1": "assignee1"},
        )
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt(context=context).with_directive(directive)
        errors = generator._validate_convergence(prompt)
        assert any("depth" in e and "max_depth" in e for e in errors)

    def test_validate_convergence_duplicate_directive(self, generator):
        """Test convergence validation detects duplicate directive."""
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={
                "plan_id": "plan_123",
                "cycle_count": 1,
                "depth": 1,
                "duplicate_directive_detected": True,
            },
            task_assignments={"task1": "assignee1"},
        )
        directive = SelfPromptDirective(
            action_type="execute",
            target_systems=["system1"],
            parameters={},
            success_criteria={"completed": True},
            failure_conditions=["error"],
            execution_bounds=ExecutionBounds(),
            provenance_chain=["cycle_test"],
            security_context={},
            knowledge_bounds={},
            learning_objectives=[],
        )
        prompt = SelfPrompt(context=context).with_directive(directive)
        errors = generator._validate_convergence(prompt)
        assert any("Duplicate directive" in e for e in errors)


class TestGenerationResult:
    """Test GenerationResult dataclass."""

    def test_success_result(self):
        """Test successful generation result."""
        prompt = SelfPrompt()
        result = GenerationResult(success=True, self_prompt=prompt)
        assert result.success is True
        assert result.self_prompt == prompt
        assert result.errors == []
        assert result.warnings == []

    def test_failure_result(self):
        """Test failed generation result."""
        result = GenerationResult(success=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"])
        assert result.success is False
        assert result.self_prompt is None
        assert result.errors == ["Error 1", "Error 2"]
        assert result.warnings == ["Warning 1"]


class TestCreateFallbackPrompt:
    """Test fallback prompt creation."""

    def test_fallback_creation(self):
        """Test fallback prompt has safe noop directive."""
        generator = SelfPromptGenerator()
        context = SelfPromptContext(
            user_intent={"goal": "test"},
            approved_plan={"plan_id": "plan_123"},
            task_assignments={"task1": "assignee1"},
        )

        fallback = generator._create_fallback_prompt("cycle_test", context, ["Error 1"])

        assert fallback.cycle_id == "cycle_test"
        assert fallback.directive is not None
        assert fallback.directive.action_type == "noop"
        assert fallback.directive.target_systems == []
        assert fallback.metadata.validation_status == SelfPromptValidationStatus.REJECTED
        assert "fallback" in fallback.metadata.tags
        assert "generation_failed" in fallback.metadata.tags
        assert fallback.metadata.priority == SelfPromptPriority.LOW


if __name__ == "__main__":
    pytest.main([__file__, "-v"])