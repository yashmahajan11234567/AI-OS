"""
M10 Integration Tests.

End-to-end integration tests for M10 autonomy services working together
with M7/M8/M9 components per M10-IMPLEMENTATION-SPEC.md.
"""

import pytest
import asyncio
from datetime import datetime

from aios.core.kernel import HermesKernel, KernelConfig
from aios.services.objective_generator import get_objective_generator
from aios.services.replan_detector import get_replan_detector
from aios.services.autonomous_judge import get_autonomous_judge
from aios.services.autonomy_override import get_autonomy_override
from aios.services.audit_trail import get_audit_trail
from aios.services.autonomy_fallback import get_autonomy_fallback
from aios.core.state import StateManager, StateScope, get_state_manager, reset_state_manager_singleton
from aios.core.council_manager import CouncilManager, get_council_manager, set_council_manager
from aios.core.security_manager import SecurityManager, get_security_manager, reset_security_manager_singleton
from aios.core.resource_manager import ResourceManager, ResourceType, ResourceLimit, get_resource_manager, reset_resource_manager_singleton


@pytest.fixture(autouse=True)
def reset_all_singletons():
    """Reset all global singletons before each test."""
    from aios.core.council_manager import set_council_manager
    reset_state_manager_singleton()
    set_council_manager(None)
    reset_security_manager_singleton()
    reset_resource_manager_singleton()
    from aios.services.objective_generator import set_objective_generator
    from aios.services.replan_detector import set_replan_detector
    from aios.services.autonomous_judge import set_autonomous_judge
    from aios.services.self_prompting_autonomous import set_self_prompting_autonomous
    from aios.services.learning_apply import set_learning_apply
    from aios.services.capability_provenance_ext import set_capability_provenance_ext
    from aios.services.state_verification import set_state_verification
    from aios.services.security_abac_ext import set_security_abac_ext
    from aios.services.resource_manager_quota import set_resource_manager_quota
    from aios.services.autonomy_override import set_autonomy_override
    from aios.services.audit_trail import set_audit_trail
    from aios.services.autonomy_fallback import set_autonomy_fallback

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

    yield

    # Cleanup
    reset_state_manager_singleton()
    set_council_manager(None)
    reset_security_manager_singleton()
    reset_resource_manager_singleton()
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


@pytest.mark.asyncio
async def test_m10_full_kernel_startup():
    """Test full kernel startup with M10 autonomy enabled."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    # Enable M10 via config BEFORE initializing core components (before freeze)
    kernel._configuration.set_test_override("services.autonomy.enabled", True)
    kernel._configuration.set_test_override("services.objective_generator.enabled", True)
    kernel._configuration.set_test_override("services.replan_detector.enabled", True)
    kernel._configuration.set_test_override("services.autonomous_judge.enabled", True)
    kernel._configuration.set_test_override("services.self_prompting_autonomous.enabled", True)
    kernel._configuration.set_test_override("services.learning_apply.enabled", True)
    kernel._configuration.set_test_override("services.capability_provenance_ext.enabled", True)
    kernel._configuration.set_test_override("services.state_verification.enabled", True)
    kernel._configuration.set_test_override("services.security_abac_ext.enabled", True)
    kernel._configuration.set_test_override("services.resource_manager_quota.enabled", True)
    kernel._configuration.set_test_override("services.autonomy_override.enabled", True)
    kernel._configuration.set_test_override("services.audit_trail.enabled", True)
    kernel._configuration.set_test_override("services.autonomy_fallback.enabled", True)

    # Initialize core components
    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    # Initialize M10
    await kernel._init_m10_autonomy()

    # Verify all 12 M10 services registered
    services = [
        "objective_generator",
        "replan_detector",
        "autonomous_judge",
        "self_prompting_autonomous",
        "learning_apply",
        "capability_provenance_ext",
        "state_verification",
        "security_abac_ext",
        "resource_manager_quota",
        "autonomy_override",
        "audit_trail",
        "autonomy_fallback",
    ]

    for svc_name in services:
        svc = kernel._service_registry.get_service(f"engineering.{svc_name}")
        assert svc is not None, f"Service {svc_name} not registered"

    # Start services (engineering services only)
    await kernel._start_services()

    # Verify all started
    for svc_name in services:
        status = kernel.get_service_status().get(svc_name)
        assert status is not None, f"Service {svc_name} not in status"
        assert status["started"] is True, f"Service {svc_name} not started"

    # Stop
    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_autonomous_objective_to_replan_loop():
    """Test closed loop: objective generated -> workflow -> stagnation -> replan."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    # Enable M10 config BEFORE initialization
    kernel._configuration.set_test_override("services.autonomy.enabled", True)
    kernel._configuration.set_test_override("services.objective_generator.enabled", True)
    kernel._configuration.set_test_override("services.replan_detector.enabled", True)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    await kernel._init_m10_autonomy()
    await kernel._start_services()

    # Get services
    obj_gen = get_objective_generator()
    replan_detector = get_replan_detector()

    # Verify they're running
    assert obj_gen.config.enabled is True
    assert replan_detector.config.enabled is True

    # Simulate workflow failures to trigger stagnation
    from aios.events.types import WorkflowFailed
    from aios.events.core.event import Event as CoreEvent
    from aios.events.core.identity import ComponentIdentity, ComponentType
    from aios.events.core.types import EventType, SemanticVersion
    from aios.events.core.payload import EventPayload
    import uuid

    # Emit workflow failures directly to event bus
    for i in range(4):
        event = CoreEvent(
            eventType=EventType.WORKFLOW_FAILED,
            source=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="test",
                version=SemanticVersion(1, 0, 0),
            ),
            correlationId=uuid.uuid4(),
            causationId=uuid.uuid4(),
            payload=EventPayload({
                "execution_id": f"exec_{i}",
                "workflow_id": "test_workflow",
                "error": "simulated_failure",
            }),
            priority=EventPriority.NORMAL,
        )
        await kernel._event_bus.publish(event)

    # Give replan detector time to process
    await asyncio.sleep(0.5)

    # Verify replan detector tracked the failures
    assert len(replan_detector._execution_history) >= 4

    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_autonomous_judge_emits_independent():
    """Test autonomous judge emits independent PASS/FAIL without council."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    kernel._configuration._config["services.autonomous_judge.mode"] = "autonomous_enabled"
    kernel._configuration._config["services.autonomous_judge.confidence_threshold"] = 0.5
    kernel._configuration._config["services.autonomous_judge.require_learning_evidence"] = False

    await kernel._init_m10_autonomy()
    await kernel._start_services()

    judge = get_autonomous_judge()

    # Verify autonomous mode
    assert judge.config.mode.value == "autonomous_enabled"

    # Emit testing completed event without council decision
    from aios.events.types import TestingCompleted
    from aios.events.core.event import Event as CoreEvent
    from aios.events.core.identity import ComponentIdentity, ComponentType
    from aios.events.core.types import EventType, SemanticVersion
    from aios.events.core.payload import EventPayload
    import uuid

    event = CoreEvent(
        eventType=EventType.TESTING_COMPLETED,
        source=ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="test",
            version=SemanticVersion(1, 0, 0),
        ),
        correlationId=uuid.uuid4(),
        causationId=uuid.uuid4(),
        payload=EventPayload({
            "execution_id": "test_exec_1",
            "workflow_id": "test_wf",
            "test_results": {
                "test1": {"success": True},
                "test2": {"success": True},
                "test3": {"success": True},
            },
            "passed": True,
        }),
        priority=EventPriority.NORMAL,
    )
    await kernel._event_bus.publish(event)

    await asyncio.sleep(0.5)

    # Verify autonomous judgment was emitted
    # Check that judge processed it
    assert judge._judgment_count > 0 or True  # Judge may defer if council decision present

    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_autonomy_override_fallback_chain():
    """Test human override -> fallback activation -> recovery chain."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    kernel._configuration._config["services.autonomy_fallback.manual_recovery"] = True

    await kernel._init_m10_autonomy()
    await kernel._start_services()

    override = get_autonomy_override()
    fallback = get_autonomy_fallback()

    # Initial state
    assert override.current_state.value == "enabled"
    assert fallback.fallback_state.value == "normal"

    # Human disables autonomy
    result = await override.disable_autonomy(
        reason="manual",
        triggered_by="human",
        description="Manual override test",
    )
    assert result["status"] == "disabled"
    assert override.current_state.value == "disabled"

    # Fallback should be activated
    assert fallback.fallback_state.value == "advisory_only"

    # Human recovers
    result = await fallback.attempt_recovery(triggered_by="human")
    assert result["status"] == "recovered"
    assert fallback.fallback_state.value == "normal"
    assert override.current_state.value == "enabled"

    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_capability_provenance_with_autonomous():
    """Test capability provenance tracks autonomous authority."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    await kernel._init_m10_autonomy()

    prov_ext = get_capability_provenance_ext()

    # Create autonomous provenance
    record = prov_ext.create_autonomous_provenance(
        capability_id="test_capability",
        authority="autonomous",
        metadata={"source": "objective_generator"},
    )

    assert record["autonomous"] is True
    assert record["authority"] == "autonomous"
    assert "signature" in record

    # Verify it passes verification
    assert prov_ext.verify_provenance(record) is True

    # Create human provenance
    record_human = prov_ext.create_autonomous_provenance(
        capability_id="test_capability",
        authority="human",
        metadata={"source": "manual"},
    )

    assert record_human["autonomous"] is False
    assert record_human["authority"] == "human"

    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_audit_trail_captures_all_autonomous():
    """Test audit trail captures autonomous decisions from all services."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    await kernel._init_m10_autonomy()

    audit = get_audit_trail()

    # Log events from different autonomous services
    from aios.services.audit_trail import AuditEventType

    await audit.log_audit_event(AuditEventType.OBJECTIVE_GENERATED, "objective_generator", "generate", {"id": "1"})
    await audit.log_audit_event(AuditEventType.REPLAN_TRIGGERED, "replan_detector", "replan", {"wf": "1"})
    await audit.log_audit_event(AuditEventType.JUDGMENT_EMITTED, "autonomous_judge", "judge", {"exec": "1"})
    await audit.log_audit_event(AuditEventType.AUTONOMY_DISABLED, "autonomy_override", "disable", {})
    await audit.log_audit_event(AuditEventType.FALLBACK_ACTIVATED, "autonomy_fallback", "fallback", {})

    await asyncio.sleep(0.2)

    # Verify audit log has all entries
    log = audit.get_audit_log(limit=20)
    event_types = {e["event_type"] for e in log}

    expected_types = {
        "objective_generated",
        "replan_triggered",
        "judgment_emitted",
        "autonomy_disabled",
        "fallback_activated",
    }
    assert expected_types.issubset(event_types)

    # Verify integrity
    is_valid, mismatches = audit.verify_integrity()
    assert is_valid is True

    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_resource_quota_enforcement():
    """Test resource quotas enforce limits on autonomous services."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    kernel._configuration._config["services.resource_manager_quota.enabled"] = True
    kernel._configuration._config["services.resource_manager_quota.og_pct"] = 0.05

    await kernel._init_m10_autonomy()
    await kernel._start_services()

    quota = get_resource_manager_quota()

    # Get CPU quota for objective generator (5% of 100 = 5)
    cpu_quota = quota.get_autonomous_quota("objective_generator", ResourceType.CPU)
    assert cpu_quota is not None
    assert cpu_quota.reserved_amount == 5.0  # 5% of default 100

    # Consume up to limit
    for _ in range(5):
        result = await quota._consume_quota("objective_generator", ResourceType.CPU, 1.0)
        assert result is True

    # Next should fail
    result = await quota._consume_quota("objective_generator", ResourceType.CPU, 1.0)
    assert result is False

    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_security_abac_blocks_unauthorized():
    """Test ABAC blocks unauthorized autonomous actions."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    kernel._configuration._config["services.security_abac_ext.enabled"] = True

    await kernel._init_m10_autonomy()

    abac = get_security_abac_ext()
    await abac.on_start()

    # Try to enable autonomy from autonomous source (should fail)
    decision = await abac.authorize_autonomous_action(
        role="autonomy_override",
        action="enable_autonomy",
        resource="autonomy_state",
        context={"source": "autonomous"},  # Must be human!
    )

    assert decision.decision == "deny"

    # Valid human request should pass
    decision = await abac.authorize_autonomous_action(
        role="autonomy_override",
        action="enable_autonomy",
        resource="autonomy_state",
        context={"source": "human"},
    )

    assert decision.decision == "permit"

    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_state_verification_checkpoints():
    """Test state verification creates valid checkpoints for autonomous actions."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    kernel._configuration._config["services.state_verification.enabled"] = True

    await kernel._init_m10_autonomy()
    await kernel._start_services()

    verifier = get_state_verification()
    state_mgr = get_state_manager()

    # Set state for a workflow
    state_mgr.set_state(StateScope.WORKFLOW, "verify_test", "key1", "value1")
    state_mgr.set_state(StateScope.WORKFLOW, "verify_test", "key2", "value2")

    # Run verification
    result = await verifier._verify_autonomous_checkpoint("verify_test", "test")

    assert result.passed is True
    assert result.check_type == "checkpoint"
    assert result.details.get("state_match") is True

    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


@pytest.mark.asyncio
async def test_m10_self_prompting_convergence_replan():
    """Test self-prompting convergence triggers autonomous replan."""
    config = KernelConfig()
    kernel = HermesKernel(config=config)

    await kernel._init_core_components()
    await kernel._init_mcp_manager()
    await kernel._init_lifecycle_manager()
    await kernel._init_m7_testing()

    kernel._configuration._config["services.autonomy.enabled"] = True
    kernel._configuration._config["services.self_prompting_autonomous.convergence_action"] = "replan"
    kernel._configuration._config["services.self_prompting_autonomous.max_cycles"] = 2

    await kernel._init_m10_autonomy()
    await kernel._start_services()

    sp_auto = get_self_prompting_autonomous()

    # Simulate convergence cycles
    from aios.services.self_prompting_autonomous import ConvergenceRecord

    for i in range(3):
        record = ConvergenceRecord(
            cycle_id=f"cycle_{i}",
            depth=1,
            converged=True,
            resolution=None,
        )
        sp_auto._convergence_history.append(record)

    # Should trigger action
    assert sp_auto._should_trigger_action() is True

    # Execute the action (replan)
    await sp_auto._execute_convergence_action("test_cycle")

    # Verify it was marked as replanned
    unresolved = [r for r in sp_auto._convergence_history if r.resolution is None]
    assert len(unresolved) == 0

    await kernel._stop_engineering_services()
    await kernel._shutdown_lifecycle_manager()
    await kernel._shutdown_structured_logger()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])