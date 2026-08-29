"""
M10 Autonomy Services Unit Tests.

Tests for all 12 M10-N# services per M10-IMPLEMENTATION-SPEC.md §11.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock

from aios.services.objective_generator import (
    AutonomousObjectiveGenerator,
    ObjectiveConfig,
    get_objective_generator,
    set_objective_generator,
)
from aios.services.replan_detector import (
    AdaptiveReplanDetector,
    ReplanDetectorConfig,
    get_replan_detector,
    set_replan_detector,
)
from aios.services.autonomous_judge import (
    AutonomousFinalJudge,
    AutonomousJudgeConfig,
    AutonomousJudgeMode,
    JudgmentSource,
    get_autonomous_judge,
    set_autonomous_judge,
)
from aios.services.self_prompting_autonomous import (
    SelfPromptingAutonomousService,
    AutonomousSelfPromptingConfig,
    ConvergenceAction,
    get_self_prompting_autonomous,
    set_self_prompting_autonomous,
)
from aios.services.learning_apply import (
    LearningApplyService,
    LearningApplyConfig,
    get_learning_apply,
    set_learning_apply,
)
from aios.services.capability_provenance_ext import (
    CapabilityProvenanceExtensionService,
    CapabilityProvenanceConfig,
    ProvenanceAuthority,
    get_capability_provenance_ext,
    set_capability_provenance_ext,
)
from aios.services.state_verification import (
    StateVerificationService,
    StateVerificationConfig,
    get_state_verification,
    set_state_verification,
)
from aios.services.security_abac_ext import (
    SecurityAbacExtensionService,
    SecurityAbacConfig,
    AutonomyRole,
    AutonomyAction,
    get_security_abac_ext,
    set_security_abac_ext,
)
from aios.services.resource_manager_quota import (
    ResourceManagerQuotaService,
    AutonomousQuotaConfig,
    get_resource_manager_quota,
    set_resource_manager_quota,
)
from aios.services.autonomy_override import (
    AutonomyOverrideService,
    AutonomyOverrideConfig,
    AutonomyState,
    OverrideReason,
    get_autonomy_override,
    set_autonomy_override,
)
from aios.services.audit_trail import (
    AuditTrailService,
    AuditConfig,
    AuditEventType,
    get_audit_trail,
    set_audit_trail,
)
from aios.services.autonomy_fallback import (
    AutonomyFallbackService,
    AutonomyFallbackConfig,
    FallbackTrigger,
    FallbackState,
    get_autonomy_fallback,
    set_autonomy_fallback,
)
from aios.core.state import StateManager, StateScope, get_state_manager, reset_state_manager_singleton
from aios.core.council_manager import CouncilManager, get_council_manager, set_council_manager
from aios.core.security_manager import SecurityManager, get_security_manager, reset_security_manager_singleton
from aios.core.resource_manager import (
    ResourceManager, ResourceType, ResourceLimit, get_resource_manager, reset_resource_manager_singleton
)
from aios.events.core.bus import EventBus, EventBusConfig, get_core_event_bus


# Global event bus for tests
_test_event_bus: EventBus | None = None


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all singletons before each test."""
    reset_state_manager_singleton()
    set_objective_generator(None)
    set_replan_detector(None)
    set_autonomous_judge(None)
    set_self_prompting_autonomous(None)
    set_learning_apply(None)
    set_capability_provenance_ext(None)
    set_state_verification(None)
    set_security_abac_ext(None)
    set_resource_manager_quota(None)
    set_autonomy_override(None)
    set_audit_trail(None)
    set_autonomy_fallback(None)
    set_council_manager(None)
    reset_security_manager_singleton()
    reset_resource_manager_singleton()
    yield
    # Cleanup after test
    reset_state_manager_singleton()
    set_objective_generator(None)
    set_replan_detector(None)
    set_autonomous_judge(None)
    set_self_prompting_autonomous(None)
    set_learning_apply(None)
    set_capability_provenance_ext(None)
    set_state_verification(None)
    set_security_abac_ext(None)
    set_resource_manager_quota(None)
    set_autonomy_override(None)
    set_audit_trail(None)
    set_autonomy_fallback(None)
    set_council_manager(None)
    reset_security_manager_singleton()
    reset_resource_manager_singleton()


@pytest.fixture
async def event_bus():
    """Create and initialize an EventBus for tests."""
    global _test_event_bus
    bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()
    _test_event_bus = bus
    yield bus
    await bus.shutdown()
    _test_event_bus = None


# ============================================================
# M10-N1: Autonomous Objective Generator Tests
# ============================================================

def test_objective_generator_creation():
    """Test objective generator instantiation with config."""
    config = ObjectiveConfig(enabled=True, min_interval_seconds=3600, max_concurrent_objectives=3)
    generator = AutonomousObjectiveGenerator(config=config)

    assert generator.name == "objective_generator"
    assert generator.config.enabled is True
    assert generator.config.min_interval_seconds == 3600
    assert generator.config.max_concurrent_objectives == 3


def test_objective_generator_can_generate():
    """Test _can_generate logic with interval and concurrent limits."""
    config = ObjectiveConfig(enabled=True, min_interval_seconds=1, max_concurrent_objectives=2)
    generator = AutonomousObjectiveGenerator(config=config)

    # Should be able to generate initially
    assert generator._can_generate() is True

    # Add active objectives
    from aios.services.objective_generator import ObjectiveCandidate
    generator._active_objectives["obj1"] = ObjectiveCandidate(
        objective_id="obj1", goal="test", reason="test", priority=0.5
    )
    assert generator._can_generate() is True

    # Fill concurrent limit
    generator._active_objectives["obj2"] = ObjectiveCandidate(
        objective_id="obj2", goal="test", reason="test", priority=0.5
    )
    assert generator._can_generate() is False  # At limit


@pytest.mark.asyncio
async def test_objective_generator_emit_planning(event_bus):
    """Test PlanningRequested emission with autonomous provenance."""
    config = ObjectiveConfig(enabled=True)
    generator = AutonomousObjectiveGenerator(config=config)

    from aios.services.objective_generator import ObjectiveCandidate
    candidate = ObjectiveCandidate(
        objective_id="test_obj",
        goal="Test goal",
        reason="test",
        priority=0.8,
    )

    # Mock event bus publish
    published = []
    original_publish = generator._event_bus.publish
    async def mock_publish(event):
        published.append(event)
        return True
    generator._event_bus.publish = mock_publish

    await generator._emit_planning_requested(candidate)

    assert len(published) == 1
    event = published[0]
    payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)

    assert payload.get("origin") == "autonomous"
    assert payload.get("objective_id") == "test_obj"
    assert payload.get("autonomous") is True
    assert payload.get("authority_level") == "autonomous"


# ============================================================
# M10-N2: Adaptive Replan Detector Tests
# ============================================================

def test_replan_detector_creation():
    """Test replan detector instantiation with config."""
    config = ReplanDetectorConfig(
        enabled=True, sensitivity=0.7, min_workflows_for_analysis=3, max_replan_depth=3, stagnation_window=5
    )
    detector = AdaptiveReplanDetector(config=config)

    assert detector.name == "replan_detector"
    assert detector.config.sensitivity == 0.7
    assert detector.config.max_replan_depth == 3


def test_replan_detector_stagnation_detection():
    """Test stagnation detection logic."""
    config = ReplanDetectorConfig(
        enabled=True, sensitivity=0.7, min_workflows_for_analysis=3, max_replan_depth=3, stagnation_window=5
    )
    detector = AdaptiveReplanDetector(config=config)

    from aios.services.replan_detector import WorkflowExecutionRecord

    # Add failure records with repeating pattern
    for i in range(3):
        record = WorkflowExecutionRecord(
            execution_id=f"exec_{i}",
            workflow_id="test_wf",
            status="failed",
            failed_steps=["step_1", "step_2"],
            duration_seconds=5.0,
        )
        detector._execution_history.append(record)

    is_stagnant, reason, score = detector._detect_stagnation("test_wf")
    assert is_stagnant is True
    assert reason in ["repeating_failure_pattern", "high_failure_rate"]


@pytest.mark.asyncio
async def test_replan_detector_emit_autonomous_replan(event_bus):
    """Test PlanningRequested emission for autonomous replan."""
    config = ReplanDetectorConfig(enabled=True)
    detector = AdaptiveReplanDetector(config=config)

    published = []
    async def mock_publish(event):
        published.append(event)
        return True
    detector._event_bus.publish = mock_publish

    await detector._trigger_autonomous_replan("test_wf", "repeating_failure", 0.8, 1)

    assert len(published) == 1
    event = published[0]
    payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)

    assert payload.get("origin") == "autonomous"
    assert payload.get("trigger_reason") == "repeating_failure"
    assert payload.get("replan_depth") == 1
    assert payload.get("autonomous") is True
    assert payload.get("authority_level") == "autonomous"


# ============================================================
# M10-N3: Autonomous Final Judge Tests
# ============================================================

def test_autonomous_judge_creation():
    """Test autonomous judge instantiation with config."""
    config = AutonomousJudgeConfig(
        mode=AutonomousJudgeMode.AUTONOMOUS_ENABLED,
        confidence_threshold=0.75,
        require_learning_evidence=True,
    )
    # Mock CouncilManager to avoid EventBus initialization
    class MockCouncilManager:
        pass
    judge = AutonomousFinalJudge(config=config, council_manager=MockCouncilManager())

    assert judge.name == "autonomous_judge"
    assert judge.config.confidence_threshold == 0.75
    assert judge.config.mode == AutonomousJudgeMode.AUTONOMOUS_ENABLED


def test_autonomous_judge_confidence_calculation():
    """Test confidence calculation for judgments."""
    config = AutonomousJudgeConfig(mode=AutonomousJudgeMode.AUTONOMOUS_ENABLED)
    class MockCouncilManager:
        pass
    judge = AutonomousFinalJudge(config=config, council_manager=MockCouncilManager())

    # Test with successful results
    test_results = {
        "test1": {"success": True},
        "test2": {"success": True},
        "test3": {"success": True},
    }
    confidence = judge._calculate_confidence(test_results, passed=True)
    assert confidence > 0.6
    assert confidence <= 1.0

    # Test with failed results
    test_results = {
        "test1": {"success": False},
        "test2": {"success": False},
    }
    confidence = judge._calculate_confidence(test_results, passed=False)
    assert confidence > 0.5


@pytest.mark.asyncio
async def test_autonomous_judge_emit_judgment(event_bus):
    """Test autonomous judgment event emission with provenance."""
    config = AutonomousJudgeConfig(
        mode=AutonomousJudgeMode.AUTONOMOUS_ENABLED,
        confidence_threshold=0.5,
        require_learning_evidence=False,
    )
    class MockCouncilManager:
        pass
    judge = AutonomousFinalJudge(config=config, council_manager=MockCouncilManager())

    published = []
    async def mock_publish(event):
        published.append(event)
        return True
    judge._event_bus.publish = mock_publish

    # Trigger judgment
    test_results = {"test1": {"success": True}, "test2": {"success": True}}
    judge._judgment_count = 0
    await judge._emit_autonomous_judgment(
        execution_id="test_exec",
        workflow_id="test_wf",
        test_results=test_results,
        passed=True,
        event_type="testing",
    )

    assert len(published) == 1
    event = published[0]
    payload = event.payload.to_dict() if hasattr(event.payload, 'to_dict') else dict(event.payload)

    assert payload.get("autonomous") is True
    assert payload.get("authority_level") == "autonomous"
    assert payload.get("judgment_source") == "autonomous_independent"
    assert "provenance" in payload
    assert payload["provenance"]["autonomous"] is True


# ============================================================
# M10-N4: Self-Prompting Autonomous Tests
# ============================================================

def test_self_prompting_autonomous_convergence():
    """Test convergence action trigger logic."""
    config = AutonomousSelfPromptingConfig(
        enabled=True,
        convergence_action=ConvergenceAction.REPLAN,
        max_convergence_cycles=2,
        forced_escalation_depth=5,
    )
    # Mock SelfPromptingService to avoid LLMCouncil dependency
    class MockSelfPromptingService:
        pass
    service = SelfPromptingAutonomousService(config=config, self_prompting_service=MockSelfPromptingService())

    from aios.services.self_prompting_autonomous import ConvergenceRecord

    # Add unresolved convergences
    for i in range(2):
        record = ConvergenceRecord(
            cycle_id=f"cycle_{i}",
            depth=1,
            converged=True,
            resolution=None,
        )
        service._convergence_history.append(record)

    assert service._should_trigger_action() is True


# ============================================================
# M10-N5: Learning Apply Tests
# ============================================================

def test_learning_apply_creation():
    """Test learning apply service creation."""
    config = LearningApplyConfig(enabled=True, confidence_threshold=0.6)
    # Mock LearningService to avoid initialization requirement
    class MockLearningService:
        def get_learnings(self, limit=50):
            return []
    service = LearningApplyService(config=config, learning_service=MockLearningService())

    assert service.name == "learning_apply"
    assert service.config.confidence_threshold == 0.6


# ============================================================
# M10-N6: Capability Provenance Extensions Tests
# ============================================================

def test_capability_provenance_autonomous():
    """Test autonomous provenance creation and verification."""
    config = CapabilityProvenanceConfig(enabled=True, require_autonomous_signature=True)
    ext = CapabilityProvenanceExtensionService(config=config)

    # Create autonomous provenance
    record = ext.create_autonomous_provenance(
        capability_id="test_capability",
        authority=ProvenanceAuthority.AUTONOMOUS,
        metadata={"test": "value"},
    )

    assert record["authority"] == "autonomous"
    assert record["autonomous"] is True
    assert "signature" in record
    assert "payload_hash" in record

    # Verify signature
    assert ext.verify_provenance(record) is True


def test_capability_provenance_tamper_detection():
    """Test tampered provenance fails verification."""
    config = CapabilityProvenanceConfig(enabled=True)
    ext = CapabilityProvenanceExtensionService(config=config)

    record = ext.create_autonomous_provenance(
        capability_id="test_capability",
        authority=ProvenanceAuthority.AUTONOMOUS,
    )

    # Tamper with record - modify the actual data that gets hashed
    record["metadata"]["tampered"] = True

    # Should fail verification
    assert ext.verify_provenance(record) is False


# ============================================================
# M10-N7: State Verification Tests
# ============================================================

@pytest.mark.asyncio
async def test_state_verification_checkpoint(event_bus):
    """Test state checkpoint and restore verification."""
    # Create StateManager (it will use the initialized event bus)
    state_manager = StateManager()

    config = StateVerificationConfig(enabled=True, verify_on_autonomous_action=True)
    verifier = StateVerificationService(config=config, state_manager=state_manager)

    # Set some state
    state_manager.set_state(StateScope.WORKFLOW, "test_wf", "key1", "value1")
    state_manager.set_state(StateScope.WORKFLOW, "test_wf", "key2", "value2")

    # Verify checkpoint
    result = await verifier._verify_autonomous_checkpoint("test_wf", "test")

    assert result.check_type == "checkpoint"
    assert result.passed is True
    assert result.details.get("state_match") is True


# ============================================================
# M10-N8: Security ABAC Extensions Tests
# ============================================================

@pytest.mark.asyncio
async def test_security_abac_authorize_autonomous(event_bus):
    """S3 (Terminal 2): an ABAC-permitted autonomous action must NOT self-authorize.

    The SecurityAbacExtensionService may *recommend* a permit, but the canonical
    fail-closed SecurityManager.authorize is the single decision authority. With a
    bare (fail-closed) SecurityManager and no kernel owning-policy authorizing the
    ``autonomy:*`` principal, the action is DENIED. Autonomous self-permission is
    removed (pre-S3 the matching ABAC policy alone yielded permit).
    """
    reset_security_manager_singleton()

    # Create SecurityManager (it will use the initialized event bus)
    security_manager = SecurityManager()

    config = SecurityAbacConfig(enabled=True)
    abac = SecurityAbacExtensionService(config=config, security_manager=security_manager)

    # Initialize policies
    await abac.on_start()

    # Even a permitted action (matching ABAC policy) is denied because the
    # kernel's SecurityManager is fail-closed and no out-of-band allow rule exists.
    decision = await abac.authorize_autonomous_action(
        role=AutonomyRole.AUTONOMOUS_OBJECTIVE_GENERATOR,
        action=AutonomyAction.GENERATE_OBJECTIVE,
        resource="planning_requested",
        context={"source": "autonomous"},
    )

    assert decision.decision == "deny"
    assert "self-author" in decision.reason.lower() or "SecurityManager" in decision.reason


@pytest.mark.asyncio
async def test_security_abac_deny_unauthorized(event_bus):
    """Test ABAC denies unauthorized autonomous actions."""
    reset_security_manager_singleton()

    security_manager = SecurityManager()

    config = SecurityAbacConfig(enabled=True)
    abac = SecurityAbacExtensionService(config=config, security_manager=security_manager)

    await abac.on_start()

    # Test denied action (human trying to enable autonomy without proper source)
    decision = await abac.authorize_autonomous_action(
        role=AutonomyRole.AUTONOMY_OVERRIDE,
        action=AutonomyAction.ENABLE_AUTONOMY,
        resource="autonomy_state",
        context={"source": "autonomous"},  # Wrong source!
    )

    assert decision.decision == "deny"


# ============================================================
# M10-N9: Resource Manager Quota Tests
# ============================================================

@pytest.mark.asyncio
async def test_resource_manager_quota_consumption(event_bus):
    """Test autonomous quota consumption and exhaustion."""
    reset_resource_manager_singleton()

    # Create ResourceManager (it will use the initialized event bus)
    resource_manager = ResourceManager()
    resource_manager.set_limit(ResourceLimit(ResourceType.CPU, 100, "percent", "CPU limit"))

    config = AutonomousQuotaConfig(enabled=True)
    quota_service = ResourceManagerQuotaService(config=config, resource_manager=resource_manager)
    await quota_service.on_start()

    # Consume quota (5% of 100 = 5, so 1.0 is fine)
    result = await quota_service._consume_quota("objective_generator", ResourceType.CPU, 1.0)
    assert result is True

    # Exhaust quota (5% of 100 = 5)
    for _ in range(4):  # Already consumed 1.0, need 4 more to reach 5
        await quota_service._consume_quota("objective_generator", ResourceType.CPU, 1.0)

    # Next consumption should fail
    result = await quota_service._consume_quota("objective_generator", ResourceType.CPU, 1.0)
    assert result is False


# ============================================================
# M10-N10: Autonomy Override Tests
# ============================================================

@pytest.mark.asyncio
async def test_autonomy_override_disable_enable(event_bus):
    """Test autonomy override disable/enable cycle."""
    config = AutonomyOverrideConfig(allow_manual_override=True)
    override = AutonomyOverrideService(config=config)

    # Initially enabled
    assert override.current_state == AutonomyState.ENABLED

    # Disable
    result = await override.disable_autonomy(
        reason=OverrideReason.MANUAL,
        triggered_by="test",
        description="Test disable",
    )
    assert result["status"] == "disabled"
    assert override.current_state == AutonomyState.DISABLED

    # Enable
    result = await override.enable_autonomy(triggered_by="test", description="Test enable")
    assert result["status"] == "enabled"
    assert override.current_state == AutonomyState.ENABLED


# ============================================================
# M10-N11: Audit Trail Tests
# ============================================================

def test_audit_trail_hash_chain():
    """Test tamper-evident hash chain integrity."""
    config = AuditConfig(enabled=True, chain_hashes=True)
    audit = AuditTrailService(config=config)

    # Log multiple events
    asyncio.run(audit.log_audit_event(
        AuditEventType.OBJECTIVE_GENERATED,
        "objective_generator",
        "generate",
        {"objective_id": "obj1"},
    ))
    asyncio.run(audit.log_audit_event(
        AuditEventType.REPLAN_TRIGGERED,
        "replan_detector",
        "replan",
        {"workflow_id": "wf1"},
    ))

    # Verify integrity
    is_valid, mismatches = audit.verify_integrity()
    assert is_valid is True
    assert len(mismatches) == 0


def test_audit_trail_tamper_detection():
    """Test tampered audit log detection."""
    config = AuditConfig(enabled=True, chain_hashes=True)
    audit = AuditTrailService(config=config)

    # Add two entries to create a chain
    asyncio.run(audit.log_audit_event(
        AuditEventType.OBJECTIVE_GENERATED,
        "objective_generator",
        "generate",
        {"objective_id": "obj1"},
    ))
    asyncio.run(audit.log_audit_event(
        AuditEventType.REPLAN_TRIGGERED,
        "replan_detector",
        "replan",
        {"workflow_id": "wf1"},
    ))

    # Tamper with the second entry's details (which are part of the hash)
    entry = audit._audit_log[-1]
    entry.details["tampered"] = True

    is_valid, mismatches = audit.verify_integrity()
    assert is_valid is False
    assert len(mismatches) > 0


# ============================================================
# M10-N12: Autonomy Fallback Tests
# ============================================================

@pytest.mark.asyncio
async def test_autonomy_fallback_trigger(event_bus):
    """Test fallback trigger and recovery."""
    config = AutonomyFallbackConfig(
        enabled=True,
        auto_fallback_on_security=True,
        require_manual_recovery=True,
    )
    fallback = AutonomyFallbackService(config=config)

    # Initially normal
    assert fallback.fallback_state == FallbackState.NORMAL

    # Trigger fallback
    result = await fallback.trigger_fallback(
        trigger=FallbackTrigger.SECURITY_VIOLATION,
        description="Test security violation",
    )

    assert result["status"] == "fallback_activated"
    assert fallback.fallback_state == FallbackState.ADVISORY_ONLY

    # Attempt non-human recovery should fail
    result = await fallback.attempt_recovery(triggered_by="auto")
    assert result["status"] == "manual_recovery_required"

    # Human recovery should succeed
    result = await fallback.attempt_recovery(triggered_by="human")
    assert result["status"] == "recovered"
    assert fallback.fallback_state == FallbackState.NORMAL


# ============================================================
# Integration Tests
# ============================================================

@pytest.mark.asyncio
async def test_m10_services_registered_in_kernel(event_bus):
    """Test that M10 services can be registered with kernel."""
    from aios.core.kernel import HermesKernel, KernelConfig

    # Create kernel with autonomy enabled
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    # Mock core components to avoid full initialization
    kernel._event_bus = event_bus
    kernel._service_registry = AsyncMock()

    # Mock LearningService
    from aios.services.learning import set_learning_service_instance, LearningService
    mock_learning = MagicMock(spec=LearningService)
    set_learning_service_instance(mock_learning)

    # Track registered services
    registered_services = []
    async def mock_register(service, service_id, service_type, metadata):
        registered_services.append(service_id)
    kernel._service_registry.register = mock_register

    # Mock configuration methods to return proper values (they are sync in kernel)
    def mock_read_config_bool(key, default=False):
        config_map = {
            "services.objective_generator.enabled": True,
            "services.replan_detector.enabled": True,
            "services.autonomous_judge.enabled": True,
            "services.self_prompting_autonomous.enabled": True,
            "services.learning_apply.enabled": True,
            "services.capability_provenance_ext.enabled": True,
            "services.state_verification.enabled": True,
            "services.security_abac_ext.enabled": True,
            "services.resource_manager_quota.enabled": True,
            "services.autonomy_override.enabled": True,
            "services.audit_trail.enabled": True,
            "services.autonomy_fallback.enabled": True,
            # Master autonomy enable switch
            "services.autonomy.enabled": True,
            # state_verification verify_on_action
            "services.state_verification.verify_on_action": True,
            # learning_apply auto_apply
            "services.learning_apply.auto_apply": True,
            # capability_provenance_ext require_signature
            "services.capability_provenance_ext.require_signature": True,
        }
        return config_map.get(key, default)

    def mock_read_config_int(key, default=0):
        config_map = {
            "services.objective_generator.min_interval_seconds": 3600,
            "services.objective_generator.max_concurrent": 3,
            "services.replan_detector.min_workflows": 3,
            "services.replan_detector.max_depth": 3,
            "services.replan_detector.window": 5,
            "services.self_prompting_autonomous.max_cycles": 3,
            "services.self_prompting_autonomous.max_depth": 5,
        }
        return config_map.get(key, default)

    def mock_read_config_float(key, default=0.0):
        config_map = {
            "services.replan_detector.sensitivity": 0.7,
            "services.autonomous_judge.confidence_threshold": 0.75,
            "services.learning_apply.confidence_threshold": 0.6,
        }
        return config_map.get(key, default)

    def mock_read_config_str(key, default=""):
        config_map = {
            "services.autonomous_judge.mode": "advisory_only",
            "services.self_prompting_autonomous.convergence_action": "escalate",
        }
        return config_map.get(key, default)

    kernel._read_config_bool = mock_read_config_bool
    kernel._read_config_int = mock_read_config_int
    kernel._read_config_float = mock_read_config_float
    kernel._read_config_str = mock_read_config_str

    # Initialize M10 services
    await kernel._init_m10_autonomy()

    # Check services are registered
    print(f"Registered services: {registered_services}")

    assert "engineering.objective_generator" in registered_services
    assert "engineering.replan_detector" in registered_services
    assert "engineering.autonomous_judge" in registered_services


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])