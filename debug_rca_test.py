"""Minimal reproduction of the ROOT_CAUSE_ANALYZED event capture issue."""

import asyncio
import tempfile
import shutil
from pathlib import Path
from uuid import uuid4

from aios.core import HermesKernel, KernelConfig
from aios.core.kernel_management import create_kernel, stop_kernel
from aios.core.lifecycle_manager import LifecycleState
from aios.core.workflow import WorkflowManager, WorkflowDefinition, WorkflowStep, WorkflowStatus
from aios.events.core.bus import get_core_event_bus, reset_event_bus_singleton
from aios.events.core.types import EventType, SemanticVersion
from aios.events.core.subscription import HandlerPriority
from aios.events.core.manager import SubscribeOptions
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.payload import EventPayload
from aios.events.core.category import category_for_event_type
from aios.events.core.priority import EventPriority
from aios.core.council_manager import get_council_manager, set_council_manager
from aios.core.mcp_manager import get_mcp_manager, set_mcp_manager
from aios.core.skill_manager import get_skill_manager, set_skill_manager
from aios.core.memory import get_memory_manager, set_memory_manager
from aios.core.root_cause import get_root_cause_analyzer, set_root_cause_analyzer
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
from aios.core.mcp_manager import MCPManager, MCPServerConfig, MCPTransport

async def reset_all_singletons():
    from aios.core.observability_manager import reset_observability_manager_singleton
    from aios.core.capability_manager import reset_capability_manager_singleton
    from aios.core.security_manager import reset_security_manager_singleton
    from aios.core.health_manager import reset_health_manager_singleton
    from aios.core.resource_manager import reset_resource_manager_singleton
    from aios.core.workflow import reset_workflow_manager_singleton
    from aios.core.storage import reset_storage_manager_singleton
    from aios.core.state import reset_state_manager_singleton
    from aios.core.lifecycle_manager import reset_lifecycle_manager_singleton
    from aios.core.structured_logger import reset_structured_logger_singleton
    from aios.core.configuration_manager import reset_configuration_manager_singleton
    from aios.core.service_registry import reset_service_registry_singleton
    reset_event_bus_singleton()
    set_council_manager(None)
    set_mcp_manager(None)
    set_skill_manager(None)
    set_memory_manager(None)
    set_root_cause_analyzer(None)

_failure_events = []

async def main():
    await reset_all_singletons()

    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)

    kernel = await create_kernel(config)
    await kernel.start()
    assert kernel._running is True
    assert kernel._lifecycle.state == LifecycleState.OPERATIONAL

    event_bus = get_core_event_bus()
    print(f"EventBus: {event_bus}")

    async def capture_event(event):
        _failure_events.append({
            "eventType": event.eventType,
            "source": event.source.component_name if event.source else None,
            "correlationId": str(event.correlationId) if event.correlationId else None,
            "payload": dict(event.payload) if event.payload else {},
        })
        print(f"CAPTURED: {event.eventType} from {event.source.component_name if event.source else 'unknown'}")

    sub_id = event_bus.subscribe(SubscribeOptions(
        subscriber=ComponentIdentity(
            component_type=ComponentType.ENGINEERING_SERVICE,
            component_name="test_tracker",
            version=SemanticVersion.parse("1.0.0"),
        ),
        event_types=list(EventType),
        handler=capture_event,
        priority=HandlerPriority.LOW,
    ))

    try:
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
                await services[name].start()

        workflow_manager = kernel._workflow_manager
        council_manager = get_council_manager()
        mcp_manager = get_mcp_manager()
        root_cause_analyzer = get_root_cause_analyzer()
        learning_service = services["learning"]

        mock_mcp_config = MCPServerConfig(
            server_id="test_mcp",
            name="TestMCP",
            transport=MCPTransport.STDIO,
            command=["echo", "mock"],
        )
        mcp_manager.add_server(mock_mcp_config)

        root_cause_analyzer._subscribe_to_events()
        assert root_cause_analyzer._subscribed, "RootCauseAnalyzer failed to subscribe to events"

        print(f"EventBus: {event_bus}")
        print(f"RootCauseAnalyzer identity: {root_cause_analyzer._identity}")

        task_id = f"task_{uuid4().hex[:8]}"
        goal = "Deploy a service that will initially fail due to configuration error"

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

        workflow_manager.register_workflow(workflow)

        execution_history = []

        async def coding_handler(payload):
            await asyncio.sleep(0.05)
            execution_history.append({"step": "coding", "status": "success"})
            return {"status": "success", "output": "service.py created"}

        async def review_handler(payload):
            await asyncio.sleep(0.05)
            execution_history.append({"step": "review", "status": "success"})
            return {"status": "success", "issues": []}

        async def testing_handler(payload):
            print(f"TESTING HANDLER: Called with payload: {payload}")
            await asyncio.sleep(0.05)
            if payload.get("force_failure", False):
                print("TESTING HANDLER: Forcing failure")
                execution_history.append({"step": "testing", "status": "failed", "error": "ConfigurationError: Missing required env var DATABASE_URL"})
                raise Exception("ConfigurationError: Missing required env var DATABASE_URL")
            print("TESTING HANDLER: Returning success")
            execution_history.append({"step": "testing", "status": "success"})
            return {"status": "success", "tests_passed": 5}

        async def deployment_handler(payload):
            await asyncio.sleep(0.05)
            execution_history.append({"step": "deployment", "status": "success"})
            return {"status": "success", "deployed_url": "http://service.local"}

        workflow_manager.register_step_handler("coding", coding_handler)
        workflow_manager.register_step_handler("review", review_handler)
        workflow_manager.register_step_handler("testing", testing_handler)
        workflow_manager.register_step_handler("deployment", deployment_handler)

        print(f"TEST: Starting workflow with task_id={task_id}")
        print(f"TEST: Workflow ID: {workflow.workflow_id}")
        execution_id = await workflow_manager.start_workflow(
            workflow.workflow_id,
            initial_payload={"task_id": task_id, "goal": goal, "force_failure": True},
        )
        print(f"TEST: Workflow started with execution_id={execution_id}")

        print("TEST: Waiting for workflow to fail...")
        await asyncio.sleep(10.0)
        print("TEST: Done waiting")

        print("TEST: Draining event bus (1st)")
        count = await event_bus.drain()
        print(f"TEST: Event bus drained (1st), dispatched {count} events")

        await asyncio.sleep(1.0)

        print("TEST: Draining event bus (2nd)")
        count = await event_bus.drain()
        print(f"TEST: Event bus drained (2nd), dispatched {count} events")

        for i in range(3):
            print(f"TEST: Draining event bus (3rd+{i})")
            count = await event_bus.drain()
            print(f"TEST: Event bus drained (3rd+{i}), dispatched {count} events")
            await asyncio.sleep(0.1)

        print("=== DEBUG: All captured events ===")
        for e in _failure_events:
            print(f"  EventType: {e.get('eventType')}, Source: {e.get('source')}")

        rca_events = [e for e in _failure_events
                     if e.get("eventType") == EventType.ROOT_CAUSE_ANALYZED
                     and e.get("payload", {}).get("failure_category") is not None]
        print(f"=== DEBUG: RCA events found: {len(rca_events)} ===")
        for e in rca_events:
            print(f"  RCA: {e}")

        if len(rca_events) >= 1:
            print("SUCCESS: RootCauseAnalyzed event captured!")
        else:
            print("FAILURE: RootCauseAnalyzed event NOT captured!")

    finally:
        from aios.events.core.bus import UnsubscribeOptions
        event_bus.unsubscribe(UnsubscribeOptions(subscriptionId=sub_id, immediate=True))
        await kernel.stop()
        await stop_kernel()
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(main())