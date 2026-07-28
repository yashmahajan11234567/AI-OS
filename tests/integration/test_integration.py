"""Integration tests for AI-OS Hermes Kernel."""
import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
from pathlib import Path
from typing import List
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
from aios.events.types import Event
from aios.services.registry import ServiceRegistry, get_service_registry
from aios.services.base import BaseService, ServiceStatus
# ===== Shared Fixtures =====
@pytest_asyncio.fixture
async def event_bus():
    """Create and start an EventBus for testing."""
    bus = EventBus(max_history=100)
    await bus.start()
    yield bus
    bus.shutdown()
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
        class TestEvent(Event):
            event_type: str = "test.event"
            payload: dict = {}
        async def handler(event):
            received.append(event.payload)
        event_bus.subscribe(handler, "test.event")
        event_bus.publish(TestEvent(source_service="test", payload={"data": "hello"}))
        await asyncio.sleep(0.1)
        assert len(received) == 1
        assert received[0]["data"] == "hello"
    @pytest.mark.asyncio
    async def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers receive the same event."""
        results = []
        class TestEvent(Event):
            event_type: str = "multi.event"
            payload: dict = {}
        async def handler1(event):
            results.append(1)
        async def handler2(event):
            results.append(2)
        event_bus.subscribe(handler1, "multi.event")
        event_bus.subscribe(handler2, "multi.event")
        event_bus.publish(TestEvent(source_service="test", payload={}))
        await asyncio.sleep(0.1)
        assert len(results) == 2
        assert 1 in results and 2 in results
    @pytest.mark.asyncio
    async def test_event_history(self, event_bus):
        """Test event history is maintained."""
        class TestEvent(Event):
            event_type: str = "history.event"
            payload: dict = {}
        for i in range(5):
            event_bus.publish(TestEvent(source_service="test", payload={"index": i}))
            await asyncio.sleep(0.01)
        history = event_bus.get_history("history.event")
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
    async def checkpoint_manager(self):
        temp_dir = Path(tempfile.mkdtemp())
        manager = CheckpointManager(checkpoint_dir=temp_dir)
        yield manager
        shutil.rmtree(temp_dir, ignore_errors=True)
    @pytest.mark.asyncio
    async def test_create_and_restore_checkpoint(self, checkpoint_manager):
        """Test creating and restoring a checkpoint."""
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
    async def test_list_checkpoints(self, checkpoint_manager):
        """Test listing checkpoints."""
        checkpoint_manager.create_checkpoint("exec_1", 1)
        checkpoint_manager.create_checkpoint("exec_1", 2)
        checkpoint_manager.create_checkpoint("exec_2", 1)
        exec1_cps = checkpoint_manager.list_checkpoints(execution_id="exec_1")
        assert len(exec1_cps) == 2
        exec2_cps = checkpoint_manager.list_checkpoints(execution_id="exec_2")
        assert len(exec2_cps) == 1
    @pytest.mark.asyncio
    async def test_checkpoint_persistence(self, checkpoint_manager):
        """Test checkpoints persist to disk."""
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
        analysis = analyzer.analyze(context)
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
        analysis = analyzer.analyze(context)
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
        analysis = analyzer.analyze(context)
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
        analysis = analyzer.analyze(context, retry_budget_exhausted=True)
        assert analysis.recommended_action == RecoveryAction.ROLLBACK
        assert analysis.responsible_service == "deployment"
class TestServiceRegistry:
    """Test Service Registry lifecycle management."""
    @pytest_asyncio.fixture
    async def registry(self, event_bus):
        return ServiceRegistry(event_bus)
    class TestService(BaseService):
        def __init__(self, name):
            super().__init__(name, "1.0.0")
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
            super().__init__(name, "1.0.0", depends_on=deps or [])
            self.started = False
        async def on_start(self):
            self.started = True
        async def on_health_check(self):
            return True
    @pytest.mark.asyncio
    async def test_register_and_start_service(self, registry):
        """Test registering and starting a service."""
        service = self.TestService("test_service")
        registry.register(service)
        assert registry.has("test_service")
        results = await registry.start_all()
        assert results["test_service"] is True
        assert service.started is True
    @pytest.mark.asyncio
    async def test_stop_service(self, registry):
        """Test stopping a service."""
        service = self.TestService("base_service")
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
            async def on_health_check(self):
                return True
        class UnhealthyService(self.TestService):
            async def on_health_check(self):
                return False
        registry.register(HealthyService("healthy"))
        registry.register(UnhealthyService("unhealthy"))
        await registry.start_all()
        report = await registry.health_check()
        assert report["healthy"] is True
        assert report["unhealthy"] is False
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
