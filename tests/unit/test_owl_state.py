"""
Tests for Owl State Mapping.
"""

import pytest
from aios.cli.owl.state import (
    OwlState,
    OwlStateContext,
    OwlStateMapper,
    create_status_context,
)
from aios.core.lifecycle_manager import LifecycleState
from aios.core.health_manager import HealthStatus, HealthManager
from unittest.mock import MagicMock


class TestOwlState:
    """Test owl state enum."""

    def test_all_states_exist(self):
        """All required owl states exist."""
        expected = [
            "IDLE", "PLANNING", "EXECUTING", "REVIEWING",
            "VERIFYING", "LEARNING", "ESCALATING", "COMPLETE"
        ]
        for exp in expected:
            assert hasattr(OwlState, exp)

    def test_state_values(self):
        """State values are correct strings."""
        assert OwlState.IDLE.value == "idle"
        assert OwlState.PLANNING.value == "planning"
        assert OwlState.EXECUTING.value == "executing"
        assert OwlState.REVIEWING.value == "reviewing"
        assert OwlState.VERIFYING.value == "verifying"
        assert OwlState.LEARNING.value == "learning"
        assert OwlState.ESCALATING.value == "escalating"
        assert OwlState.COMPLETE.value == "complete"


class TestOwlStateContext:
    """Test owl state context."""

    def test_default_context(self):
        """Default context has sensible defaults."""
        ctx = OwlStateContext()
        assert ctx.lifecycle_state is None
        assert ctx.health_status is None
        assert ctx.has_active_workflow is False
        assert ctx.workflow_phase is None
        assert ctx.human_escalation_required is False
        assert ctx.is_shutting_down is False
        assert ctx.is_terminated is False
        assert ctx.completion_result is None

    def test_context_with_values(self):
        """Context can be created with values."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
            has_active_workflow=True,
            workflow_phase="executing",
        )
        assert ctx.lifecycle_state == LifecycleState.OPERATIONAL
        assert ctx.health_status == HealthStatus.HEALTHY
        assert ctx.has_active_workflow is True
        assert ctx.workflow_phase == "executing"


class TestOwlStateMapper:
    """Test deterministic state mapping."""

    def test_priority_1_human_escalation(self):
        """Human escalation overrides everything."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
            has_active_workflow=True,
            workflow_phase="executing",
            human_escalation_required=True,
        )
        assert OwlStateMapper.map(ctx) == OwlState.ESCALATING

    def test_priority_2_complete(self):
        """Completion overrides active workflow."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
            has_active_workflow=True,
            workflow_phase="executing",
            completion_result="PASS",
        )
        assert OwlStateMapper.map(ctx) == OwlState.COMPLETE

    def test_priority_3_unhealthy(self):
        """Unhealthy health status triggers escalation."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.UNHEALTHY,
            has_active_workflow=True,
            workflow_phase="executing",
        )
        assert OwlStateMapper.map(ctx) == OwlState.ESCALATING

    def test_priority_4_degraded(self):
        """Degraded health status triggers escalation."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.DEGRADED,
        )
        assert OwlStateMapper.map(ctx) == OwlState.ESCALATING

        # Also from lifecycle
        ctx2 = OwlStateContext(
            lifecycle_state=LifecycleState.DEGRADED,
            health_status=HealthStatus.HEALTHY,
        )
        assert OwlStateMapper.map(ctx2) == OwlState.ESCALATING

    def test_priority_5_active_workflow(self):
        """Active workflow maps to workflow phase."""
        phases = {
            "planning": OwlState.PLANNING,
            "executing": OwlState.EXECUTING,
            "reviewing": OwlState.REVIEWING,
            "verifying": OwlState.VERIFYING,
            "learning": OwlState.LEARNING,
        }
        for phase, expected in phases.items():
            ctx = OwlStateContext(
                lifecycle_state=LifecycleState.OPERATIONAL,
                health_status=HealthStatus.HEALTHY,
                has_active_workflow=True,
                workflow_phase=phase,
            )
            assert OwlStateMapper.map(ctx) == expected, f"Phase {phase} failed"

    def test_priority_6_idle_healthy(self):
        """No workflow + healthy = IDLE."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
            has_active_workflow=False,
        )
        assert OwlStateMapper.map(ctx) == OwlState.IDLE

        # Also with UNKNOWN health
        ctx2 = OwlStateContext(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.UNKNOWN,
            has_active_workflow=False,
        )
        assert OwlStateMapper.map(ctx2) == OwlState.IDLE

    def test_priority_7_shutting_down(self):
        """Shutting down/terminated = IDLE static."""
        ctx = OwlStateContext(
            lifecycle_state=LifecycleState.SHUTTING_DOWN,
            health_status=HealthStatus.HEALTHY,
            is_shutting_down=True,
        )
        assert OwlStateMapper.map(ctx) == OwlState.IDLE

        ctx2 = OwlStateContext(
            lifecycle_state=LifecycleState.TERMINATED,
            health_status=HealthStatus.HEALTHY,
            is_terminated=True,
        )
        assert OwlStateMapper.map(ctx2) == OwlState.IDLE

    def test_lifecycle_mapping(self):
        """Lifecycle states map correctly when no workflow."""
        mappings = {
            LifecycleState.UNINITIALIZED: OwlState.IDLE,
            LifecycleState.INITIALIZING: OwlState.PLANNING,
            LifecycleState.OPERATIONAL: OwlState.IDLE,
            LifecycleState.DEGRADED: OwlState.ESCALATING,
            LifecycleState.SHUTTING_DOWN: OwlState.IDLE,
            LifecycleState.TERMINATED: OwlState.IDLE,
            LifecycleState.ROLLBACK_IN_PROGRESS: OwlState.ESCALATING,
            LifecycleState.RECOVERY_IN_PROGRESS: OwlState.LEARNING,
        }
        for lifecycle, expected in mappings.items():
            ctx = OwlStateContext(
                lifecycle_state=lifecycle,
                health_status=HealthStatus.HEALTHY,
                has_active_workflow=False,
            )
            result = OwlStateMapper.map(ctx)
            assert result == expected, f"Lifecycle {lifecycle.value} -> {result.value}, expected {expected.value}"

    def test_should_animate(self):
        """Animation decision per state."""
        assert OwlStateMapper.should_animate(OwlState.IDLE) is False
        assert OwlStateMapper.should_animate(OwlState.PLANNING) is True
        assert OwlStateMapper.should_animate(OwlState.EXECUTING) is True
        assert OwlStateMapper.should_animate(OwlState.REVIEWING) is True
        assert OwlStateMapper.should_animate(OwlState.VERIFYING) is True
        assert OwlStateMapper.should_animate(OwlState.LEARNING) is True
        assert OwlStateMapper.should_animate(OwlState.ESCALATING) is True
        assert OwlStateMapper.should_animate(OwlState.COMPLETE) is False

    def test_is_interruptible(self):
        """Interruptibility rules."""
        # Escalation always interrupts
        assert OwlStateMapper.is_interruptible(OwlState.PLANNING, OwlState.ESCALATING) is True
        assert OwlStateMapper.is_interruptible(OwlState.EXECUTING, OwlState.ESCALATING) is True

        # Completion interrupts
        assert OwlStateMapper.is_interruptible(OwlState.PLANNING, OwlState.COMPLETE) is True

        # Shutdown (IDLE) interrupts active
        assert OwlStateMapper.is_interruptible(OwlState.PLANNING, OwlState.IDLE) is True

        # Same state doesn't restart
        assert OwlStateMapper.is_interruptible(OwlState.PLANNING, OwlState.PLANNING) is False

        # Different active states interrupt
        assert OwlStateMapper.is_interruptible(OwlState.PLANNING, OwlState.EXECUTING) is True

    def test_from_kernel_state_convenience(self):
        """Convenience method works."""
        state = OwlStateMapper.from_kernel_state(
            lifecycle_state=LifecycleState.OPERATIONAL,
            health_status=HealthStatus.HEALTHY,
            has_active_workflow=False,
        )
        assert state == OwlState.IDLE

    def test_describe_state(self):
        """State descriptions are readable."""
        for state in OwlState:
            desc = OwlStateMapper.describe_state(state)
            assert isinstance(desc, str)
            assert len(desc) > 0


class TestCreateStatusContext:
    """Test context creation from kernel components."""

    def test_from_mock_components(self):
        """Context created from mocked components."""
        # Mock lifecycle manager
        lm = MagicMock()
        lm.state = LifecycleState.OPERATIONAL

        # Mock health manager
        hm = MagicMock(spec=HealthManager)
        hm.overall_status = HealthStatus.HEALTHY

        # Mock kernel
        kernel = MagicMock()
        kernel.workflow_manager = MagicMock()
        kernel.workflow_manager._active_workflows = {}

        ctx = create_status_context(lm, hm, kernel)

        assert ctx.lifecycle_state == LifecycleState.OPERATIONAL
        assert ctx.health_status == HealthStatus.HEALTHY
        assert ctx.has_active_workflow is False

    def test_with_active_workflow(self):
        """Context detects active workflow."""
        lm = MagicMock()
        lm.state = LifecycleState.OPERATIONAL

        hm = MagicMock(spec=HealthManager)
        hm.overall_status = HealthStatus.HEALTHY

        kernel = MagicMock()
        kernel.workflow_manager = MagicMock()
        kernel.workflow_manager._active_workflows = {"wf1": MagicMock()}

        ctx = create_status_context(lm, hm, kernel)

        assert ctx.has_active_workflow is True

    def test_unhealthy_triggers_escalation(self):
        """Unhealthy health manager sets escalation flag."""
        lm = MagicMock()
        lm.state = LifecycleState.OPERATIONAL

        hm = MagicMock(spec=HealthManager)
        hm.overall_status = HealthStatus.UNHEALTHY

        ctx = create_status_context(lm, hm, None)

        assert ctx.human_escalation_required is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])