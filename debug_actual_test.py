#!/usr/bin/env python3
import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

# Import the same modules as the actual test
from aios.core import HermesKernel, KernelConfig
from aios.core.kernel_management import run_kernel, stop_kernel, create_kernel
from aios.core.lifecycle_manager import LifecycleManager, LifecycleState, reset_lifecycle_manager_singleton
from aios.core.state import StateManager, StateScope, reset_state_manager_singleton
from aios.core.storage import StorageManager, reset_storage_manager_singleton
from aios.core.health_manager import HealthManager, reset_health_manager_singleton
from aios.core.resource_manager import ResourceManager, reset_resource_manager_singleton
from aios.core.security_manager import SecurityManager, reset_security_manager_singleton
from aios.core.capability_manager import CapabilityManager, reset_capability_manager_singleton
from aios.core.workflow import (
    WorkflowManager,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
    reset_workflow_manager_singleton,
)
from aios.core.observability_manager import ObservabilityManager, reset_observability_manager_singleton
from aios.core.configuration_manager import reset_configuration_manager_singleton
from aios.core.service_registry import reset_service_registry_singleton
from aios.core.structured_logger import reset_structured_logger_singleton
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.subscription import HandlerPriority
from aios.events.core.manager import SubscribeOptions
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload

# Services
from aios.services.planning import PlanningService
from aios.services.council import CouncilService
from aios.services.learning import LearningService
from aios.services.mcp import MCPService
from aios.services.skill import SkillService
from aios.services.memory import MemoryService
from aios.services.coding import CodingService
from aios.services.review import ReviewService
from aios.services.testing import TestingService
from aios.services.deployment import DeploymentService
from aios.services.operations import OperationsService

# Core managers
from aios.core.council_manager import CouncilManager, CouncilMember, ConsensusAlgorithm, get_council_manager, set_council_manager
from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport, get_mcp_manager, set_mcp_manager
from aios.core.skill_manager import SkillManager, get_skill_manager, set_skill_manager
from aios.core.memory import MemoryManager, get_memory_manager, set_memory_manager
from aios.core.root_cause import (
    RootCauseAnalyzer,
    FailureContext,
    FailureCategory,
    FailureSeverity,
    RecoveryAction,
    get_root_cause_analyzer,
    set_root_cause_analyzer,
)

# Event tracking
_failure_events = []

async def _reset_all_singletons():
    """Reset all global singletons for test isolation."""
    reset_observability_manager_singleton()
    reset_capability_manager_singleton()
    reset_security_manager_singleton()
    reset_health_manager_singleton()
    reset_resource_manager_singleton()
    reset_workflow_manager_singleton()
    reset_storage_manager_singleton()
    reset_state_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_structured_logger_singleton()
    reset_configuration_manager_singleton()
    reset_service_registry_singleton()
    reset_event_bus_singleton()
    # Council, MCP, Skill, Memory, RootCause don't have reset functions - use set_* with None
    set_council_manager(None)
    set_mcp_manager(None)
    set_skill_manager(None)
    set_memory_manager(None)
    set_root_cause_analyzer(None)


async def capture_event(event):
    """Capture events for verification - EXACT COPY FROM ACTUAL TEST."""
    _failure_events.append({
        "eventType": event.eventType,
        "source": event.source.component_name if event.source else None,
        "correlationId": str(event.correlationId) if event.correlationId else None,
        "payload": dict(event.payload) if event.payload else {},
    })
    print(f"CAPTURED EVENT: {event.eventType}")


async def main():
    print("=== STARTING DEBUG ACTUAL TEST ===")

    # Reset everything
    await _reset_all_singletons()

    temp_dir = Path(tempfile.mkdtemp())
    print(f"Using temp dir: {temp_dir}")
    config = KernelConfig(data_dir=temp_dir)

    # Create kernel WITHOUT starting it first (to match actual test fixture)
    kernel = await create_kernel(config)
    print(f"Kernel created: {kernel}")

    try:
        # Start kernel FIRST - this initializes the EventBus singleton
        print("Starting kernel...")
        await kernel.start()
        print(f"Kernel started: {kernel._running}")
        assert kernel._running is True
        assert kernel._lifecycle.state == LifecycleState.OPERATIONAL

        # NOW set up event tracking - EventBus is available
        print("Setting up event tracking...")
        event_bus = get_core_event_bus()
        print(f"Event bus: {event_bus}")

        event_bus.subscribe(SubscribeOptions(
            subscriber=ComponentIdentity(
                component_type=ComponentType.ENGINEERING_SERVICE,
                component_name="test_tracker",
                version=SemanticVersion.parse("1.0.0"),
            ),
            event_types=list(EventType),
            handler=capture_event,
            priority=HandlerPriority.LOW,
        ))
        print("Event subscription set up")

        # Register and start all engineering services through the kernel
        print("Registering services...")
        services = {}
        service_classes = {
            "planning": PlanningService,
            "council": CouncilService,
            "learning": LearningService,
            "mcp": MCPService,
            "skill": SkillService,
            "memory": MemoryService,
            "coding": CodingService,
            "review": ReviewService,
            "testing": TestingService,
            "deployment": DeploymentService,
            "operations": OperationsService,
        }

        for name, cls in service_classes.items():
            svc = cls()
            kernel.register_service(svc)
            services[name] = svc

        start_order = [
            "memory", "learning", "planning", "coding", "review",
            "testing", "deployment", "operations", "skill", "mcp", "council"
        ]
        for name in start_order:
            if name in services:
                print(f"Starting service: {name}")
                await services[name].start()

        print("Getting managers...")
        workflow_manager = kernel._workflow_manager
        council_manager = get_council_manager()
        mcp_manager = get_mcp_manager()
        root_cause_analyzer = get_root_cause_analyzer()
        learning_service = services["learning"]
        print(f"Root cause analyzer: {root_cause_analyzer}")

        # Register MCP server
        print("Registering MCP server...")
        mock_mcp_config = MCPServerConfig(
            server_id="test_mcp",
            name="TestMCP",
            transport=MCPTransport.STDIO,
            command=["echo", "mock"],
        )
        mcp_manager.add_server(mock_mcp_config)

        # Ensure RootCauseAnalyzer is subscribed to events (lazy subscription)
        # The RootCauseAnalyzer was created before kernel start, so we need to manually trigger subscription
        # now that EventBus is available
        print("Ensuring RootCauseAnalyzer is subscribed to events...")
        root_cause_analyzer._subscribe_to_events()

        # Verify subscription worked by checking the subscribed flag
        print(f"RootCauseAnalyzer subscribed flag: {root_cause_analyzer._subscribed}")
        assert root_cause_analyzer._subscribed, "RootCauseAnalyzer failed to subscribe to events"

        # Debug: verify the event bus has the subscription
        event_bus = get_core_event_bus()
        print(f"EventBus: {event_bus}")
        print(f"RootCauseAnalyzer identity: {root_cause_analyzer._identity}")

        # =====================================================================
        # ATTEMPT 1: Workflow execution that will fail
        # =====================================================================
        task_id = f"task_{uuid4().hex[:8]}"
        goal = "Deploy a service that will initially fail due to configuration error"
        print(f"Task ID: {task_id}")
        print(f"Goal: {goal}")

        # Create a workflow with a step that will fail
        workflow = WorkflowDefinition(
            workflow_id=f"wf_{uuid4().hex[:8]}",
            name=f"Execute with Failure",
            description=f"Test failure recovery for task {task_id}",
            steps=[
                WorkflowStep(
                    step_id="step_coding",
                    name="Coding",
                    service="coding",
                    event_type="coding.start",
                    payload={"task_id": task_id, "goal": goal},
                ),
                WorkflowStep(
                    step_id="step_review",
                    name="Review",
                    service="review",
                    event_type="review.start",
                    payload={"task_id": task_id, "goal": goal},
                    depends_on=["step_coding"],
                ),
                WorkflowStep(
                    step_id="step_testing",
                    name="Testing - Will Fail",
                    service="testing",
                    event_type="testing.start",
                    payload={"task_id": task_id, "goal": goal, "force_failure": True},
                    depends_on=["step_review"],
                ),
                WorkflowStep(
                    step_id="step_deployment",
                    name="Deployment",
                    service="deployment",
                    event_type="deployment.start",
                    payload={"task_id": task_id, "goal": goal},
                    depends_on=["step_testing"],
                ),
            ],
        )

        print(f"Workflow created: {workflow.workflow_id}")
        workflow_manager.register_workflow(workflow)

        # Track step execution
        execution_history = []

        async def coding_handler(payload):
            print(f"CODING HANDLER: Called with {payload}")
            await asyncio.sleep(0.05)
            execution_history.append({"step": "coding", "status": "success"})
            return {"status": "success", "output": "service.py created"}

        async def review_handler(payload):
            print(f"REVIEW HANDLER: Called with {payload}")
            await asyncio.sleep(0.05)
            execution_history.append({"step": "review", "status": "success"})
            return {"status": "success", "issues": []}

        async def testing_handler(payload):
            print(f"TESTING HANDLER: Called with {payload}")
            await asyncio.sleep(0.05)
            # Force failure on first attempt
            if payload.get("force_failure", False):
                print("TESTING HANDLER: Forcing failure")
                execution_history.append({"step": "testing", "status": "failed", "error": "ConfigurationError: Missing required env var DATABASE_URL"})
                raise Exception("ConfigurationError: Missing required env var DATABASE_URL")
            print("TESTING HANDLER: Returning success")
            execution_history.append({"step": "testing", "status": "success"})
            return {"status": "success", "tests_passed": 5}

        async def deployment_handler(payload):
            print(f"DEPLOYMENT HANDLER: Called with {payload}")
            await asyncio.sleep(0.05)
            execution_history.append({"step": "deployment", "status": "success"})
            return {"status": "success", "deployed_url": "http://service.local"}

        print("Registering step handlers...")
        workflow_manager.register_step_handler("coding", coding_handler)
        workflow_manager.register_step_handler("review", review_handler)
        workflow_manager.register_step_handler("testing", testing_handler)
        workflow_manager.register_step_handler("deployment", deployment_handler)

        # Start workflow (first attempt - will fail)
        print(f"Starting workflow with task_id={task_id}")
        print(f"Workflow ID: {workflow.workflow_id}")
        print(f"Initial payload: {{\"task_id\": \"{task_id}\", \"goal\": \"{goal}\", \"force_failure\": True}}")
        execution_id = await workflow_manager.start_workflow(
            workflow.workflow_id,
            initial_payload={"task_id": task_id, "goal": goal, "force_failure": True},
        )
        print(f"Workflow started with execution_id={execution_id}")

        # Wait for workflow to fail (retry logic: 3 retries with exponential backoff ~1s + 2s + 4s = ~7s total)
        print("Waiting for workflow to fail...")
        await asyncio.sleep(10.0)
        print("Done waiting")

        # Drain event bus to ensure all events are processed
        print("Draining event bus")
        await event_bus.drain()
        print("Event bus drained")

        # Verify workflow failed
        workflow_status = workflow_manager.get_workflow_status(execution_id)
        print(f"Workflow status: {workflow_status}")
        assert workflow_status is not None
        assert workflow_status.get("status") == WorkflowStatus.FAILED.value, \
            f"Expected workflow to fail, got: {workflow_status.get('status')}"
        print("Workflow correctly failed")

        # =====================================================================
        # STEP: RootCauseAnalyzer analyzes the failure
        # =====================================================================
        # The RootCauseAnalyzer subscribes to TASK_FAILED and RETRY_BUDGET_EXHAUSTED events
        # It should have analyzed the failure automatically

        # Wait for RootCauseAnalyzer to process
        print("Waiting for RootCauseAnalyzer to process...")
        await asyncio.sleep(0.5)
        print("Done waiting for RCA processing")

        # Drain event bus to capture any events emitted during processing
        print("Draining event bus after RCA processing...")
        await event_bus.drain()
        print("Event bus drained after RCA processing")

        # Debug: Let's see what events we've captured so far
        print(f"Total events captured so far: {len(_failure_events)}")
        for i, event in enumerate(_failure_events[-10:]):  # Show last 10 events
            print(f"  Event {len(_failure_events)-10+i}: {event.get('eventType')} from {event.get('source')}")

        # Verify RootCauseAnalysis event was emitted
        print("Checking for RootCauseAnalyzed events...")
        from aios.events.core.types import EventType as CoreEventType
        rca_events = [e for e in _failure_events
                     if e.get("eventType") == CoreEventType.ROOT_CAUSE_ANALYZED
                     and e.get("payload", {}).get("failure_category") is not None]
        print(f"Found {len(rca_events)} RootCauseAnalyzed events")
        for i, event in enumerate(rca_events):
            print(f"  RCA Event {i}: {event}")

        if len(rca_events) == 0:
            print("DEBUG: Let's check ALL events for ROOT_CAUSE_ANALYZED:")
            all_rca = [e for e in _failure_events if e.get("eventType") == CoreEventType.ROOT_CAUSE_ANALYZED]
            print(f"All ROOT_CAUSE_ANALYZED events ({len(all_rca)}):")
            for i, event in enumerate(all_rca):
                print(f"  {i}: {event}")
                if "payload" in event:
                    print(f"      Payload keys: {list(event['payload'].keys())}")
                    for k, v in event['payload'].items():
                        print(f"      {k}: {v} (type: {type(v)})")

        assert len(rca_events) >= 1, "RootCauseAnalyzed event not emitted"

        print("=== TEST COMPLETED SUCCESSFULLY ===")

    except Exception as e:
        print(f"=== TEST FAILED WITH ERROR: {e} ===")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Clean up
        print("Cleaning up...")
        await kernel.stop()
        await stop_kernel()
        await _reset_all_singletons()
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())