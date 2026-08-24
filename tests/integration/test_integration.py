"""Integration tests for AI-OS Hermes Kernel."""
import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
from pathlib import Path
from typing import List
import uuid
from aios.core.kernel import HermesKernel, KernelConfig
from aios.core.kernel_management import run_kernel, stop_kernel, get_kernel
from aios.core.workflow import (
    WorkflowManager,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
    get_workflow_manager,
)
from aios.core.retry import (
    RetryManager,
    RetryPolicy,
    RetryStrategy,
    get_retry_manager,
)
from aios.core.root_cause import (
    RootCauseAnalyzer,
    FailureContext,
    FailureCategory,
    FailureSeverity,
    RecoveryAction,
    get_root_cause_analyzer,
)
from aios.core.checkpoint import (
    CheckpointManager,
    get_checkpoint_manager,
)
from aios.core.state import StateManager, StateScope, get_state_manager
from aios.events.bus import EventBus, get_event_bus
from aios.events.core.event import Event as CoreEvent
from aios.events.core.identity import ComponentIdentity, ComponentType
from aios.events.core.types import EventType
from aios.events.core.payload import EventPayload
from aios.events.core.priority import EventPriority
from aios.services.registry import ServiceRegistry, get_service_registry
from aios.services.base import BaseService, ServiceStatus
# ===== Shared Fixtures =====
@pytest_asyncio.fixture
async def event_bus():
    """Create and start a canonical EventBus for testing."""
    from aios.events.core.bus import EventBus as CoreEventBus, EventBusConfig
    from aios.events.core.bus import reset_core_event_bus_singleton

    # Reset and create canonical EventBus
    reset_core_event_bus_singleton()
    bus = CoreEventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
    await bus.initialize()
    yield bus
    await bus.shutdown()


def _create_test_event(event_type: EventType, payload: dict | None = None) -> CoreEvent:
    """Create a canonical CoreEvent for testing with valid required fields."""
    return CoreEvent(
        eventType=event_type,
        eventVersion="1.0.0",
        source=ComponentIdentity(component_type=ComponentType.APPLICATION_SERVICE, component_name="test"),
        payload=EventPayload(payload or {}),
        correlationId=uuid.uuid4(),
        causationId=None,
        priority=EventPriority.NORMAL,
    )
@pytest_asyncio.fixture
async def kernel():
    """Create and start a kernel for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    config = KernelConfig(data_dir=temp_dir)
    kernel = await run_kernel(config)
    yield kernel
    await stop_kernel()
    shutil.rmtree(temp_dir, ignore_errors=True)
# ===== Test Classes =====
class TestEventBus:
    """Test EventBus functionality."""
    @pytest.mark.asyncio
    async def test_publish_subscribe(self, event_bus):
        """Test basic publish/subscribe."""
        received = []
        async def handler(event):
            received.append(event.payload.to_dict())
        from aios.events.core.manager import SubscribeOptions
        from aios.events.core.identity import ComponentIdentity, ComponentType
        from aios.events.core.subscription import HandlerPriority, RetryPolicy

        options = SubscribeOptions(
            subscriber=ComponentIdentity(component_type=ComponentType.APPLICATION_SERVICE, component_name="test-subscriber"),
            event_types=[EventType.TASK_CREATED],
            handler=handler,
            priority=HandlerPriority.NORMAL,
            retry_policy=RetryPolicy()
        )
        event_bus.subscribe(options)
        await event_bus.publish(_create_test_event(EventType.TASK_CREATED, {"data": "hello"}))
        await event_bus.drain()
        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0]["data"] == "hello"
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers receive the same event."""
        results = []
        async def handler1(event):
            results.append(1)
        async def handler2(event):
            results.append(2)
        from aios.events.core.manager import SubscribeOptions
        from aios.events.core.identity import ComponentIdentity, ComponentType
        from aios.events.core.subscription import HandlerPriority, RetryPolicy

        options1 = SubscribeOptions(
            subscriber=ComponentIdentity(component_type=ComponentType.APPLICATION_SERVICE, component_name="test-subscriber-1"),
            event_types=[EventType.WORKFLOW_STARTED],
            handler=handler1,
            priority=HandlerPriority.NORMAL,
            retry_policy=RetryPolicy()
        )
        options2 = SubscribeOptions(
            subscriber=ComponentIdentity(component_type=ComponentType.APPLICATION_SERVICE, component_name="test-subscriber-2"),
            event_types=[EventType.WORKFLOW_STARTED],
            handler=handler2,
            priority=HandlerPriority.NORMAL,
            retry_policy=RetryPolicy()
        )
        event_bus.subscribe(options1)
        event_bus.subscribe(options2)
        await event_bus.publish(_create_test_event(EventType.WORKFLOW_STARTED, {}))
        await event_bus.drain()
        await asyncio.sleep(0.1)
        assert len(results) == 2
        assert 1 in results and 2 in results
    @pytest.mark.asyncio
    async def test_event_history(self, event_bus):
        """Test event history is maintained."""
        for i in range(5):
            await event_bus.publish(_create_test_event(EventType.TASK_CREATED, {"index": i}))
            await event_bus.drain()
            await asyncio.sleep(0.01)
        history = event_bus.get_history(EventType.TASK_CREATED.name)
        assert len(history) == 5
class TestRetryManager:
    """Test RetryManager functionality."""
    @pytest.fixture
    def retry_manager(self):
        return RetryManager()
    @pytest.mark.asyncio
    async def test_successful_execution(self, retry_manager):
        """Test successful execution without retries."""
        call_count = 0
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        result = await retry_manager.execute_with_retry(
            task_id="task_1",
            service="test_service",
            func=success_func,
        )
        assert result == "success"
        assert call_count == 1
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, retry_manager):
        """Test retry on transient failure."""
        call_count = 0
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Attempt {call_count} failed")
            return "success"
        policy = RetryPolicy(max_retries=5, base_delay_ms=10, strategy=RetryStrategy.FIXED)
        result = await retry_manager.execute_with_retry(
            task_id="task_2",
            service="test_service",
            func=flaky_func,
            policy=policy,
        )
        assert result == "success"
        assert call_count == 3
    @pytest.mark.asyncio
    async def test_exhausted_retries(self, retry_manager):
        """Test retries exhausted raises exception."""
        call_count = 0
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"Attempt {call_count} failed")
        policy = RetryPolicy(max_retries=3, base_delay_ms=10, strategy=RetryStrategy.FIXED)
        with pytest.raises(ConnectionError):
            await retry_manager.execute_with_retry(
                task_id="task_3",
                service="test_service",
                func=always_fail,
                policy=policy,
            )
        assert call_count == 4
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self, retry_manager):
        """Test non-retryable exceptions fail immediately."""
        call_count = 0
        async def fail_fast():
            nonlocal call_count
            call_count += 1
            raise ValueError("Non-retryable error")
        policy = RetryPolicy(
            max_retries=3,
            base_delay_ms=10,
            non_retryable_exceptions=(ValueError,),
        )
        with pytest.raises(ValueError):
            await retry_manager.execute_with_retry(
                task_id="task_4",
                service="test_service",
                func=fail_fast,
                policy=policy,
            )
        assert call_count == 1
class TestWorkflowExecution:
    """Test Workflow execution with DAG."""
    @pytest_asyncio.fixture
    async def workflow_manager(self, kernel):
        return kernel.workflow_manager
    @pytest.mark.asyncio
    async def test_simple_workflow(self, workflow_manager):
        """Test simple linear workflow."""
        results = []
        async def step_handler(payload):
            results.append(payload.get("step", "unknown"))
            return f"result_{payload.get("step")}"
        workflow_manager.register_step_handler("service_a", step_handler)
        definition = WorkflowDefinition(
            workflow_id="wf_1",
            name="Test Workflow",
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    name="Step 1",
                    service="service_a",
                    event_type="step.execute",
                    payload={"step": "step_1"},
                ),
                WorkflowStep(
                    step_id="step_2",
                    name="Step 2",
                    service="service_a",
                    event_type="step.execute",
                    payload={"step": "step_2"},
                    depends_on=["step_1"],
                ),
            ],
        )
        workflow_manager.register_workflow(definition)
        execution_id = await workflow_manager.start_workflow("wf_1")
        await asyncio.sleep(0.5)
        state = workflow_manager.get_workflow_status(execution_id)
        assert state["status"] == WorkflowStatus.COMPLETED.value
        assert len(results) == 2
    @pytest.mark.asyncio
    async def test_parallel_workflow(self, workflow_manager):
        """Test parallel step execution."""
        results = []
        async def parallel_handler(payload):
            results.append(payload.get("step"))
            await asyncio.sleep(0.05)
            return f"result_{payload.get("step")}"
        workflow_manager.register_step_handler("parallel_service", parallel_handler)
        definition = WorkflowDefinition(
            workflow_id="wf_parallel",
            name="Parallel Workflow",
            steps=[
                WorkflowStep(
                    step_id="step_a",
                    name="Step A",
                    service="parallel_service",
                    event_type="step.execute",
                    payload={"step": "step_a"},
                ),
                WorkflowStep(
                    step_id="step_b",
                    name="Step B",
                    service="parallel_service",
                    event_type="step.execute",
                    payload={"step": "step_b"},
                ),
                WorkflowStep(
                    step_id="step_c",
                    name="Step C",
                    service="parallel_service",
                    event_type="step.execute",
                    payload={"step": "step_c"},
                    depends_on=["step_a", "step_b"],
                ),
            ],
        )
        workflow_manager.register_workflow(definition)
        execution_id = await workflow_manager.start_workflow("wf_parallel")
        await asyncio.sleep(0.5)
        state = workflow_manager.get_workflow_status(execution_id)
        assert state["status"] == WorkflowStatus.COMPLETED.value
        assert set(results) == {"step_a", "step_b", "step_c"}
    @pytest.mark.asyncio
    async def test_workflow_failure(self, workflow_manager):
        """Test workflow failure on required step."""
        async def fail_handler(payload):
            raise RuntimeError("Intentional failure")
        workflow_manager.register_step_handler("fail_service", fail_handler)
        definition = WorkflowDefinition(
            workflow_id="wf_fail",
            name="Failing Workflow",
            steps=[
                WorkflowStep(
                    step_id="step_1",
                    name="Step 1",
                    service="fail_service",
                    event_type="step.execute",
                    payload={},
                    required=True,
                ),
            ],
        )
        workflow_manager.register_workflow(definition)
        execution_id = await workflow_manager.start_workflow("wf_fail")
        await asyncio.sleep(0.5)
        state = workflow_manager.get_workflow_status(execution_id)
        assert state["status"] == WorkflowStatus.FAILED.value
class TestCheckpointRecovery:
    """Test checkpoint recovery functionality."""
    @pytest_asyncio.fixture
    async def test_state_manager(self, event_bus):
        """Create StateManager with EventBus initialized."""
        from aios.core.state import StateManager, StateScope, get_state_manager, set_state_manager
        import tempfile
        temp_dir = Path(tempfile.mkdtemp())
        manager = StateManager(persistence_path=temp_dir)
        # Set as global for checkpoint manager to use
        set_state_manager(manager)
        yield manager
        # Cleanup
        set_state_manager(None)
        shutil.rmtree(temp_dir, ignore_errors=True)
    @pytest_asyncio.fixture
    async def checkpoint_manager(self, event_bus, test_state_manager):
        """Create CheckpointManager with EventBus and StateManager initialized."""
        temp_dir = Path(tempfile.mkdtemp())
        manager = CheckpointManager(state_manager=test_state_manager, checkpoint_dir=temp_dir)
        yield manager
        shutil.rmtree(temp_dir, ignore_errors=True)
    @pytest.mark.asyncio
    async def test_create_and_restore_checkpoint(self, checkpoint_manager, test_state_manager):
        """Test creating and restoring a checkpoint."""
        from aios.core.state import StateScope
        # Set up workflow state first
        test_state_manager.set_state(
            StateScope.WORKFLOW, "exec_1", "workflow", {"workflow_id": "wf_1", "step": 2}
        )
        cp = checkpoint_manager.create_checkpoint(
            execution_id="exec_1",
            step=2,
            metadata={"key": "value"},
            tags=["test"],
        )
        assert cp.execution_id == "exec_1"
        assert cp.step == 2
        restored = checkpoint_manager.restore_checkpoint("exec_1")
        assert restored.checkpoint_id == cp.checkpoint_id
    @pytest.mark.asyncio
    async def test_list_checkpoints(self, checkpoint_manager, test_state_manager):
        """Test listing checkpoints."""
        from aios.core.state import StateScope
        # Set up workflow states
        test_state_manager.set_state(StateScope.WORKFLOW, "exec_1", "workflow", {"workflow_id": "wf_1", "step": 1})
        checkpoint_manager.create_checkpoint("exec_1", 1)
        test_state_manager.set_state(StateScope.WORKFLOW, "exec_1", "workflow", {"workflow_id": "wf_1", "step": 2})
        checkpoint_manager.create_checkpoint("exec_1", 2)
        test_state_manager.set_state(StateScope.WORKFLOW, "exec_2", "workflow", {"workflow_id": "wf_2", "step": 1})
        checkpoint_manager.create_checkpoint("exec_2", 1)
        exec1_cps = checkpoint_manager.list_checkpoints(execution_id="exec_1")
        assert len(exec1_cps) == 2
        exec2_cps = checkpoint_manager.list_checkpoints(execution_id="exec_2")
        assert len(exec2_cps) == 1
    @pytest.mark.asyncio
    async def test_checkpoint_persistence(self, checkpoint_manager, test_state_manager):
        """Test checkpoints persist to disk."""
        from aios.core.state import StateScope
        test_state_manager.set_state(
            StateScope.WORKFLOW, "exec_persist", "workflow", {"workflow_id": "wf_persist", "step": 5}
        )
        cp = checkpoint_manager.create_checkpoint(
            execution_id="exec_persist",
            step=5,
            metadata={"data": "test"},
        )
        new_manager = CheckpointManager(checkpoint_dir=checkpoint_manager._checkpoint_dir)
        cps = new_manager.list_checkpoints(execution_id="exec_persist")
        assert len(cps) == 1
        assert cps[0].step == 5
class TestRootCauseAnalysis:
    """Test Root Cause Analysis functionality."""
    @pytest.fixture
    def analyzer(self):
        return RootCauseAnalyzer()
    @pytest.mark.asyncio
    async def test_classify_transient_failure(self, analyzer):
        """Test classification of transient failures."""
        context = FailureContext(
            failure_id="fail_1",
            event_type="task.failed",
            error="Connection timeout",
            error_type="TimeoutError",
            service="external_api",
        )
        analysis = await analyzer.analyze(context)
        assert analysis.category == FailureCategory.TRANSIENT
        assert analysis.recommended_action == RecoveryAction.RETRY_WITH_BACKOFF
    @pytest.mark.asyncio
    async def test_classify_config_failure(self, analyzer):
        """Test classification of configuration failures."""
        context = FailureContext(
            failure_id="fail_2",
            event_type="task.failed",
            error="Configuration missing: API_KEY",
            error_type="ConfigError",
            service="planning",
        )
        analysis = await analyzer.analyze(context)
        assert analysis.category == FailureCategory.CONFIGURATION
        assert analysis.responsible_service == "planning"
        assert analysis.recommended_action == RecoveryAction.RETURN_TO_PLANNING
    @pytest.mark.asyncio
    async def test_classify_code_defect(self, analyzer):
        """Test classification of code defects."""
        context = FailureContext(
            failure_id="fail_3",
            event_type="task.failed",
            error="SyntaxError: invalid syntax",
            error_type="SyntaxError",
            service="coding",
        )
        analysis = await analyzer.analyze(context)
        assert analysis.category == FailureCategory.CODE_DEFECT
        assert analysis.responsible_service == "coding"
        assert analysis.recommended_action == RecoveryAction.RETURN_TO_CODING
    @pytest.mark.asyncio
    async def test_retry_budget_exhausted_routes_to_service(self, analyzer):
        """Test retry budget exhaustion routes to responsible service."""
        context = FailureContext(
            failure_id="fail_4",
            event_type="retry.budget_exhausted",
            error="Max retries exceeded",
            error_type="RetryExhausted",
            service="deployment",
            attempt_history=[{}, {}, {}],
        )
        analysis = await analyzer.analyze(context, retry_budget_exhausted=True)
        assert analysis.recommended_action == RecoveryAction.ROLLBACK
        assert analysis.responsible_service == "deployment"
class TestServiceRegistry:
    """Test Service Registry lifecycle management."""
    @pytest_asyncio.fixture
    async def registry(self, event_bus):
        # Reset the canonical ServiceRegistry singleton so each test starts
        # from a clean state (Rule 9 / Rule 12: test fixtures must reset the
        # canonical singleton; the legacy wrapper delegates to it). The shared
        # event_bus fixture is left intact (owned by the event_bus fixture).
        from aios.core.service_registry import reset_service_registry_singleton
        reset_service_registry_singleton()
        return ServiceRegistry(event_bus)
    class TestService(BaseService):
        name = "test_service"
        version = "1.0.0"
        def __init__(self):
            super().__init__()
            self.started = False
            self.stopped = False
        async def on_start(self):
            self.started = True
        async def on_stop(self):
            self.stopped = True
        async def on_health_check(self):
            return True
    class DepService(BaseService):
        def __init__(self, name, deps=None):
            self.name = name
            self.version = "1.0.0"
            self.depends_on = deps or []
            super().__init__()
            self.started = False
        async def on_start(self):
            self.started = True
        async def on_health_check(self):
            return True
    @pytest.mark.asyncio
    async def test_register_and_start_service(self, registry):
        """Test registering and starting a service."""
        service = self.TestService()
        registry.register(service)
        assert registry.has("test_service")
        results = await registry.start_all()
        assert results["test_service"] is True
        assert service.started is True
    @pytest.mark.asyncio
    async def test_stop_service(self, registry):
        """Test stopping a service."""
        service = self.TestService()
        registry.register(service)
        await registry.start_all()
        await registry.stop_all()
        assert service.stopped is True
    @pytest.mark.asyncio
    async def test_dependency_order(self, registry):
        """Test services start in dependency order."""
        svc_a = self.DepService("service_a", [])
        svc_b = self.DepService("service_b", ["service_a"])
        svc_c = self.DepService("service_c", ["service_b"])
        registry.register(svc_c)
        registry.register(svc_a)
        registry.register(svc_b)
        await registry.start_all()
        assert svc_a.started
        assert svc_b.started
        assert svc_c.started
    @pytest.mark.asyncio
    async def test_health_check(self, registry):
        """Test health check reporting."""
        class HealthyService(self.TestService):
            name = "healthy"
            async def on_health_check(self):
                return True
        class UnhealthyService(self.TestService):
            name = "unhealthy"
            async def on_health_check(self):
                return False
        registry.register(HealthyService())
        registry.register(UnhealthyService())
        await registry.start_all()
        report = await registry.health_check()
        assert report["healthy"] is True
        assert report["unhealthy"] is False
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
