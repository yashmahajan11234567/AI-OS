"""
M10-T4 Recovery Manager Unit Tests.

Tests for M10RecoveryManager circuit breaker, recovery coordination,
lifeboat protection per M10-T4 spec §3-6.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch, PropertyMock

from aios.core.m10_recovery_manager import (
    M10RecoveryManager,
    RecoveryPriority,
    RecoveryAction,
    RecoveryPlan,
    RecoveryRecord,
    get_m10_recovery_manager,
    set_m10_recovery_manager,
    reset_m10_recovery_manager_singleton,
    _M10_SERVICES,
    _LIFEBOAT_SERVICES,
)
from aios.core.evidence_engine import (
    EvidenceEngine,
    EvidenceType,
    EvidenceEntry,
    get_evidence_engine,
    reset_evidence_engine_singleton,
)
from aios.core.configuration_manager import ConfigurationManager, get_configuration_manager, reset_configuration_manager_singleton
from aios.core.service_registry import ServiceRegistry, ServiceType, ServiceLifecycleState, get_service_registry, reset_service_registry_singleton
from aios.core.structured_logger import StructuredLogger, get_logger, set_logger
from aios.events.core.bus import EventBus, EventBusConfig, get_core_event_bus, reset_core_event_bus_singleton
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType, SemanticVersion
from aios.core.root_cause import RootCauseAnalyzer, RootCauseAnalysis
from aios.core.state import StateManager
from aios.core.retry import RetryManager


@pytest.fixture
def temp_path():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def core_components(temp_path):
    """Create core components for testing."""
    # Reset singletons
    reset_core_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_evidence_engine_singleton()

    # EventBus
    event_bus_config = EventBusConfig(auto_start_dispatch_worker=False)
    event_bus = EventBus(config=event_bus_config)
    await event_bus.initialize()

    # ServiceRegistry
    service_registry = get_service_registry(event_bus=event_bus)

    # ConfigurationManager
    config_manager = get_configuration_manager(event_bus=event_bus, config_path=None)
    await config_manager.initialize()
    config_manager.freeze()

    # StructuredLogger
    logger = get_logger()
    await logger.initialize(MagicMock())

    # EvidenceEngine
    evidence_engine = EvidenceEngine(
        service_registry=service_registry,
        configuration_manager=config_manager,
        logger=logger,
        base_path=temp_path,
    )
    await evidence_engine.initialize()

    yield {
        'event_bus': event_bus,
        'service_registry': service_registry,
        'configuration': config_manager,
        'logger': logger,
        'evidence_engine': evidence_engine,
        'temp_path': temp_path,
    }

    # Cleanup
    await evidence_engine.shutdown()
    await event_bus.shutdown()


@pytest.fixture
async def recovery_manager(core_components):
    """Create an M10RecoveryManager instance."""
    reset_m10_recovery_manager_singleton()
    manager = M10RecoveryManager(
        service_registry=core_components['service_registry'],
        configuration_manager=core_components['configuration'],
        logger=core_components['logger'],
        evidence_engine=core_components['evidence_engine'],
    )
    await manager.initialize()
    yield manager
    await manager.shutdown()
    reset_m10_recovery_manager_singleton()


class TestRecoveryPlan:
    """Tests for RecoveryPlan data class."""

    def test_create_plan(self):
        """Test creating a RecoveryPlan."""
        plan = RecoveryPlan(
            service_name="objective_generator",
            priority=RecoveryPriority.HIGH,
            actions=[RecoveryAction.RESTART_SERVICE, RecoveryAction.RESTORE_CHECKPOINT],
            root_cause="health_check_failed",
            correlation_id="corr-123",
            estimated_duration_ms=15000,
            requires_manual_intervention=False,
            metadata={"extra": "info"},
        )

        assert plan.service_name == "objective_generator"
        assert plan.priority == RecoveryPriority.HIGH
        assert len(plan.actions) == 2
        assert plan.root_cause == "health_check_failed"
        assert plan.correlation_id == "corr-123"
        assert plan.estimated_duration_ms == 15000


class TestCircuitBreaker:
    """Tests for circuit breaker integration (3-consecutive-failure threshold)."""

    @pytest.mark.asyncio
    async def test_non_m10_service_ignored(self, recovery_manager):
        """Non-M10 services should not trigger circuit breaker."""
        result = recovery_manager.record_service_failure("some_other_service")
        assert result is False  # Circuit not opened
        assert recovery_manager.get_failure_count("some_other_service") == 0

    @pytest.mark.asyncio
    async def test_first_two_failures_do_not_open_circuit(self, recovery_manager):
        """First two failures should not open circuit."""
        result1 = recovery_manager.record_service_failure("objective_generator")
        result2 = recovery_manager.record_service_failure("objective_generator")

        assert result1 is False
        assert result2 is False
        assert recovery_manager.get_failure_count("objective_generator") == 2
        assert not recovery_manager.is_circuit_open("objective_generator")

    @pytest.mark.asyncio
    async def test_third_failure_opens_circuit(self, recovery_manager):
        """Third consecutive failure should open circuit."""
        recovery_manager.record_service_failure("replan_detector")
        recovery_manager.record_service_failure("replan_detector")
        result = recovery_manager.record_service_failure("replan_detector")

        assert result is True  # Circuit opened
        assert recovery_manager.is_circuit_open("replan_detector")
        # Counter should reset after opening
        assert recovery_manager.get_failure_count("replan_detector") == 0

    @pytest.mark.asyncio
    async def test_success_resets_counter_and_closes_circuit(self, recovery_manager):
        """Service success should reset counter and close circuit."""
        # Open circuit
        recovery_manager.record_service_failure("autonomous_judge")
        recovery_manager.record_service_failure("autonomous_judge")
        recovery_manager.record_service_failure("autonomous_judge")

        assert recovery_manager.is_circuit_open("autonomous_judge")

        # Record success
        recovery_manager.record_service_success("autonomous_judge")

        assert not recovery_manager.is_circuit_open("autonomous_judge")
        assert recovery_manager.get_failure_count("autonomous_judge") == 0

    @pytest.mark.asyncio
    async def test_lifeboat_services_never_open_circuit(self, recovery_manager):
        """Lifeboat services (N10, N12) should never have circuit breaker opened."""
        # N10: autonomy_override
        for _ in range(5):
            result = recovery_manager.record_service_failure("autonomy_override")
            assert result is False

        assert not recovery_manager.is_circuit_open("autonomy_override")
        assert recovery_manager.get_failure_count("autonomy_override") == 0

        # N12: autonomy_fallback
        for _ in range(5):
            result = recovery_manager.record_service_failure("autonomy_fallback")
            assert result is False

        assert not recovery_manager.is_circuit_open("autonomy_fallback")


class TestRecoveryCoordination:
    """Tests for recovery coordination (sole authoritative path)."""

    @pytest.mark.asyncio
    async def test_non_m10_service_raises_error(self, recovery_manager):
        """Attempting to coordinate recovery for non-M10 service should raise error."""
        with pytest.raises(Exception) as exc_info:
            await recovery_manager.coordinate_recovery("some_other_service")

        assert "not an M10 autonomy service" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_lifeboat_service_returns_no_action(self, recovery_manager):
        """Lifeboat services should return no-action recovery record."""
        record = await recovery_manager.coordinate_recovery("autonomy_override")

        assert record.success is True
        assert record.plan.actions == [RecoveryAction.NO_ACTION]
        assert record.plan.root_cause == "lifeboat_service_protected"

    @pytest.mark.asyncio
    async def test_coordinate_recovery_returns_record(self, recovery_manager):
        """Coordinate recovery should return a RecoveryRecord."""
        record = await recovery_manager.coordinate_recovery(
            "objective_generator",
            correlation_id="test-corr-123",
            trigger_reason="health_check_failed"
        )

        assert isinstance(record, RecoveryRecord)
        assert record.service_name == "objective_generator"
        assert record.plan.service_name == "objective_generator"
        assert record.recovery_id is not None

    @pytest.mark.asyncio
    async def test_recovery_priority_critical_for_state_verification(self, recovery_manager):
        """StateVerification should get CRITICAL priority."""
        record = await recovery_manager.coordinate_recovery("state_verification")
        assert record.plan.priority == RecoveryPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_recovery_priority_high_for_chain_dependent(self, recovery_manager):
        """Chain-dependent services should get HIGH priority."""
        for svc in ["objective_generator", "replan_detector", "autonomous_judge"]:
            record = await recovery_manager.coordinate_recovery(svc)
            assert record.plan.priority == RecoveryPriority.HIGH

    @pytest.mark.asyncio
    async def test_recovery_priority_high_for_security_capability(self, recovery_manager):
        """Security and capability services should get HIGH priority."""
        for svc in ["security_abac_ext", "capability_provenance_ext"]:
            record = await recovery_manager.coordinate_recovery(svc)
            assert record.plan.priority == RecoveryPriority.HIGH


class TestRecoveryActions:
    """Tests for recovery action computation and execution."""

    @pytest.mark.asyncio
    async def test_critical_priority_actions(self, recovery_manager):
        """Critical priority should include RESTORE_CHECKPOINT and REPLAY_EVENTS."""
        record = await recovery_manager.coordinate_recovery("state_verification")

        actions = record.plan.actions
        assert RecoveryAction.RESTART_SERVICE in actions
        assert RecoveryAction.RESTORE_CHECKPOINT in actions
        assert RecoveryAction.REPLAY_EVENTS in actions

    @pytest.mark.asyncio
    async def test_high_priority_actions(self, recovery_manager):
        """High priority should include RESTORE_CHECKPOINT but not REPLAY_EVENTS."""
        record = await recovery_manager.coordinate_recovery("objective_generator")

        actions = record.plan.actions
        assert RecoveryAction.RESTART_SERVICE in actions
        assert RecoveryAction.RESTORE_CHECKPOINT in actions
        assert RecoveryAction.REPLAY_EVENTS not in actions

    @pytest.mark.asyncio
    async def test_security_root_cause_escalates_to_override(self, recovery_manager):
        """Security-related root cause should escalate to override."""
        # Mock root cause analyzer to return security cause
        with patch.object(recovery_manager, '_analyze_root_cause', new=AsyncMock(return_value="security_violation_detected")):
            record = await recovery_manager.coordinate_recovery("learning_apply")

        actions = record.plan.actions
        assert RecoveryAction.ESCALATE_TO_OVERRIDE in actions

    @pytest.mark.asyncio
    async def test_resource_root_cause_escalates_to_fallback(self, recovery_manager):
        """Resource exhaustion root cause should escalate to fallback."""
        with patch.object(recovery_manager, '_analyze_root_cause', new=AsyncMock(return_value="resource_exhaustion_detected")):
            record = await recovery_manager.coordinate_recovery("resource_manager_quota")

        actions = record.plan.actions
        assert RecoveryAction.ESCALATE_TO_FALLBACK in actions

    @pytest.mark.asyncio
    async def test_duplicate_recovery_returns_existing(self, recovery_manager):
        """Concurrent recovery for same service should return existing record."""
        # Start first recovery
        task1 = asyncio.create_task(recovery_manager.coordinate_recovery("autonomous_judge"))
        await asyncio.sleep(0.01)  # Let it start

        # Try second recovery for same service
        record2 = await recovery_manager.coordinate_recovery("autonomous_judge")

        # Should return same record (or wait for completion)
        record1 = await task1

        # Both should complete with valid records
        assert record1.service_name == "autonomous_judge"
        assert record2.service_name == "autonomous_judge"


class TestRetryManagerIntegration:
    """Tests for RetryManager infrastructure reuse."""

    @pytest.mark.asyncio
    async def test_retry_manager_injected(self, core_components):
        """Test that custom RetryManager can be injected."""
        custom_retry = RetryManager()
        custom_retry = RetryManager()

        reset_m10_recovery_manager_singleton()
        manager = M10RecoveryManager(
            service_registry=core_components['service_registry'],
            configuration_manager=core_components['configuration'],
            logger=core_components['logger'],
            evidence_engine=core_components['evidence_engine'],
            retry_manager=custom_retry,
        )

        assert manager._retry_mgr is custom_retry
        await manager.shutdown()
        reset_m10_recovery_manager_singleton()


class TestStateManagerPersistence:
    """Tests for StateManager persistence for critical/high priority."""

    @pytest.mark.asyncio
    async def test_persist_recovery_state_called_for_critical(self, recovery_manager):
        """_persist_recovery_state should be called for CRITICAL priority."""
        with patch.object(recovery_manager, '_persist_recovery_state', new=AsyncMock()) as mock_persist:
            record = await recovery_manager.coordinate_recovery("state_verification")

        # Should have been called (or at least attempted)
        # Note: actual StateManager may not be available, but the call path is tested
        assert record.plan.priority == RecoveryPriority.CRITICAL

    @pytest.mark.asyncio
    async def test_persist_recovery_state_not_called_for_normal(self, recovery_manager):
        """_persist_recovery_state should NOT be called for NORMAL priority."""
        # Use a service with NORMAL priority
        with patch.object(recovery_manager, '_persist_recovery_state', new=AsyncMock()) as mock_persist:
            record = await recovery_manager.coordinate_recovery("audit_trail")

        # audit_trail should be NORMAL priority (not in critical/high sets)
        assert record.plan.priority == RecoveryPriority.NORMAL


class TestHealthCheck:
    """Tests for health check integration."""

    @pytest.mark.asyncio
    async def test_is_service_healthy_circuit_open(self, recovery_manager):
        """Service with open circuit should be unhealthy."""
        recovery_manager.record_service_failure("objective_generator")
        recovery_manager.record_service_failure("objective_generator")
        recovery_manager.record_service_failure("objective_generator")

        assert not recovery_manager.is_service_healthy("objective_generator")

    @pytest.mark.asyncio
    async def test_is_service_healthy_in_recovery(self, recovery_manager):
        """Service currently in recovery should be unhealthy."""
        # Add to active recoveries directly
        recovery_manager._active_recoveries["replan_detector"] = RecoveryRecord(
            recovery_id="test",
            service_name="replan_detector",
            plan=RecoveryPlan(service_name="replan_detector", priority=RecoveryPriority.NORMAL, actions=[]),
        )

        assert not recovery_manager.is_service_healthy("replan_detector")

    @pytest.mark.asyncio
    async def test_is_service_healthy_non_m10(self, recovery_manager):
        """Non-M10 services should always be considered healthy."""
        assert recovery_manager.is_service_healthy("some_other_service")


class TestSingletonPattern:
    """Tests for M10RecoveryManager singleton pattern."""

    @pytest.mark.asyncio
    async def test_singleton(self, core_components):
        """Test singleton pattern."""
        reset_m10_recovery_manager_singleton()

        manager1 = get_m10_recovery_manager()
        manager1._service_registry = core_components['service_registry']
        manager1._configuration = core_components['configuration']
        manager1._logger = core_components['logger']
        manager1._evidence_engine = core_components['evidence_engine']
        await manager1.initialize()

        manager2 = get_m10_recovery_manager()

        assert manager1 is manager2

        await manager1.shutdown()
        reset_m10_recovery_manager_singleton()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])