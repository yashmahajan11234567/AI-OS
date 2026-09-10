"""
M10-T7 Deployment Smoke Tests.

Tests for:
- Dockerfile ENTRYPOINT verification (aios kernel start)
- Dockerfile HEALTHCHECK verification (aios kernel health)
- Docker Compose autonomy configuration (AIOS_SERVICES_AUTONOMY_ENABLED=false)
- Docker Compose non-root user (10000:10000)
- Real in-process kernel health behavior (all 8 canonical states)
- Fresh/Stale liveness detection
- Configuration loading (defaults.yaml, production.yaml)
- Dashboard endpoints (/alive, /ready, /api/pages with 8 pages including system_observability)

All tests run without Docker daemon - static analysis + in-process verification.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aios.core.kernel import (
    CanonicalHealthState,
    HermesKernel,
    KernelConfig,
)
from aios.core.lifecycle_manager import (
    reset_lifecycle_manager_singleton,
    get_lifecycle_manager,
    set_lifecycle_manager,
)
from aios.core.health_manager import HealthManager, set_health_manager, reset_health_manager_singleton
from aios.core.service_registry import (
    get_service_registry,
    reset_service_registry_singleton,
)
from aios.events.core.bus import EventBus, EventBusConfig, reset_event_bus_singleton
from aios.core.configuration_manager import (
    reset_configuration_manager_singleton,
    get_configuration_manager,
)
from aios.core.structured_logger import get_logger, reset_structured_logger_singleton
from aios.core.resource_manager import ResourceManager, set_resource_manager
from aios.core.security_manager import SecurityManager, set_security_manager
from aios.core.capability_manager import CapabilityManager, set_capability_manager
from aios.core.observability_manager import ObservabilityManager, set_observability_manager
from aios.core.workflow import WorkflowManager, set_workflow_manager
from aios.core.state import StateManager, set_state_manager
from aios.core.storage import StorageManager, set_storage_manager


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def reset_singletons():
    """Reset all canonical singletons before/after each test."""
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_health_manager_singleton()
    reset_structured_logger_singleton()
    yield
    reset_event_bus_singleton()
    reset_service_registry_singleton()
    reset_configuration_manager_singleton()
    reset_lifecycle_manager_singleton()
    reset_health_manager_singleton()
    reset_structured_logger_singleton()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


# =============================================================================
# A. Dockerfile ENTRYPOINT — 2 tests
# =============================================================================

class TestDockerfileEntrypoint:
    """Tests for Dockerfile ENTRYPOINT verification."""

    def _read_dockerfile(self) -> str:
        return Path("Dockerfile").read_text()

    def test_entrypoint_launches_aios_kernel_start(self):
        """Verify Dockerfile ENTRYPOINT launches 'aios kernel start'."""
        content = self._read_dockerfile()

        # Parse ENTRYPOINT from Dockerfile
        entrypoint_line = None
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("ENTRYPOINT"):
                entrypoint_line = stripped
                break

        assert entrypoint_line is not None, "Dockerfile must have ENTRYPOINT instruction"

        # Verify it's the correct aios kernel start command
        assert 'ENTRYPOINT [ "/opt/ai-os/.venv/bin/aios", "kernel", "start" ]' == entrypoint_line, \
            f"ENTRYPOINT must be 'aios kernel start', got: {entrypoint_line}"

    def test_entrypoint_not_hermes_dispatcher(self):
        """Verify ENTRYPOINT does not use Hermes-specific dispatcher."""
        content = self._read_dockerfile()

        forbidden = [
            "entrypoint-dispatch.sh",
            "hermes-exec-shim.sh",
            "hermes dispatcher",
        ]

        for term in forbidden:
            assert term not in content.lower(), f"Dockerfile should not contain '{term}' in ENTRYPOINT"


class TestDockerfileHealthcheck:
    """Tests for Dockerfile HEALTHCHECK verification."""

    def _read_dockerfile(self) -> str:
        return Path("Dockerfile").read_text()

    def test_healthcheck_invokes_aios_kernel_health(self):
        """Verify Dockerfile HEALTHCHECK invokes 'aios kernel health'."""
        content = self._read_dockerfile()

        # Find HEALTHCHECK instruction (may span multiple lines)
        healthcheck_lines = []
        in_healthcheck = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("HEALTHCHECK"):
                in_healthcheck = True
                healthcheck_lines.append(stripped)
            elif in_healthcheck:
                if stripped.endswith("\\"):
                    healthcheck_lines.append(stripped)
                else:
                    healthcheck_lines.append(stripped)
                    break

        healthcheck_full = " ".join(healthcheck_lines)

        assert healthcheck_lines, "Dockerfile must have HEALTHCHECK instruction"

        # Verify it invokes aios kernel health
        assert "aios kernel health" in healthcheck_full, \
            f"HEALTHCHECK must invoke 'aios kernel health', got: {healthcheck_full}"
        assert "CMD /opt/ai-os/.venv/bin/aios kernel health" in healthcheck_full

    def test_healthcheck_has_correct_parameters(self):
        """Verify HEALTHCHECK has appropriate interval, timeout, retries, start-period."""
        content = self._read_dockerfile()

        # Find HEALTHCHECK instruction (may span multiple lines)
        healthcheck_lines = []
        in_healthcheck = False
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("HEALTHCHECK"):
                in_healthcheck = True
                healthcheck_lines.append(stripped)
            elif in_healthcheck:
                if stripped.endswith("\\"):
                    healthcheck_lines.append(stripped)
                else:
                    healthcheck_lines.append(stripped)
                    break

        healthcheck_full = " ".join(healthcheck_lines)

        assert healthcheck_lines, "Dockerfile must have HEALTHCHECK instruction"

        # Verify standard healthcheck parameters are present
        assert "--interval=30s" in healthcheck_full
        assert "--timeout=10s" in healthcheck_full
        assert "--retries=3" in healthcheck_full
        assert "--start-period=60s" in healthcheck_full


# =============================================================================
# B. Docker Compose Configuration — 2 tests
# =============================================================================

class TestDockerComposeConfiguration:
    """Tests for Docker Compose configuration verification."""

    def _read_compose(self) -> str:
        return Path("docker-compose.yml").read_text()

    def test_autonomy_disabled_by_default(self):
        """Verify compose configuration disables autonomy by default."""
        content = self._read_compose()

        # Check for the environment variable setting
        assert "AIOS_SERVICES_AUTONOMY_ENABLED=false" in content, \
            "docker-compose must set AIOS_SERVICES_AUTONOMY_ENABLED=false"

    def test_non_root_user_10000_10000(self):
        """Verify deployed service runs as user 10000:10000."""
        content = self._read_compose()

        # Check user directive in compose
        assert 'user: "10000:10000"' in content, \
            "docker-compose must specify user: \"10000:10000\""

        # Also verify Dockerfile creates user with UID 10000
        dockerfile_content = Path("Dockerfile").read_text()
        assert "useradd -u 10000" in dockerfile_content, \
            "Dockerfile must create user with UID 10000"
        assert "USER 10000" in dockerfile_content, \
            "Dockerfile must switch to USER 10000"


# =============================================================================
# C. Health File / Runtime Health — 2 tests
# =============================================================================

class TestRuntimeHealthBehavior:
    """Tests for real in-process kernel health behavior."""

    @pytest.fixture
    async def kernel(self, temp_dir, reset_singletons):
        """Create a kernel with clean state for health testing."""
        config = KernelConfig(data_dir=temp_dir)
        kernel = HermesKernel(config=config)

        # Initialize core components manually for testing health behavior
        await self._init_minimal_kernel(kernel)

        yield kernel

        # Cleanup
        try:
            await kernel.stop()
        except Exception:
            pass

    async def _init_minimal_kernel(self, kernel: HermesKernel) -> None:
        """Initialize minimal kernel components for health testing."""
        # C1: EventBus
        reset_event_bus_singleton()
        event_bus_config = EventBusConfig(auto_start_dispatch_worker=False)
        kernel._event_bus = EventBus(config=event_bus_config)
        await kernel._event_bus.initialize()

        # C2: ServiceRegistry
        reset_service_registry_singleton()
        kernel._service_registry = get_service_registry(event_bus=kernel._event_bus)

        # C3: ConfigurationManager
        kernel._configuration = get_configuration_manager(
            event_bus=kernel._event_bus,
            config_path=kernel.config.config_path,
        )
        await kernel._configuration.initialize()
        kernel._configuration.freeze()

        # C4: StructuredLogger
        kernel._structured_logger = get_logger()
        await kernel._structured_logger.initialize(kernel)

        # Core Managers (Phase 2+)
        kernel._state_manager = StateManager(
            persistence_path=kernel.config.data_dir / "state",
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_state_manager(kernel._state_manager)

        kernel._storage_manager = StorageManager(
            persistence_path=kernel.config.data_dir / "storage",
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_storage_manager(kernel._storage_manager)

        kernel._workflow_manager = WorkflowManager(
            state_manager=kernel._state_manager,
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_workflow_manager(kernel._workflow_manager)

        kernel._resource_manager = ResourceManager(
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_resource_manager(kernel._resource_manager)

        kernel._health_manager = HealthManager(
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_health_manager(kernel._health_manager)

        kernel._security_manager = SecurityManager(
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_security_manager(kernel._security_manager)

        kernel._capability_manager = CapabilityManager(
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_capability_manager(kernel._capability_manager)

        kernel._observability_manager = ObservabilityManager(
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
        )
        set_observability_manager(kernel._observability_manager)

        # LifecycleManager
        reset_lifecycle_manager_singleton()
        kernel._lifecycle = get_lifecycle_manager(
            event_bus=kernel._event_bus,
            service_registry=kernel._service_registry,
            configuration_manager=kernel._configuration,
            logger=kernel._structured_logger,
            kernel=kernel,
        )
        set_lifecycle_manager(kernel._lifecycle)
        await kernel._lifecycle.register_with_service_registry()

        # Register managers with lifecycle
        kernel._lifecycle.register_manager(kernel._state_manager)
        kernel._lifecycle.register_manager(kernel._storage_manager)
        kernel._lifecycle.register_manager(kernel._health_manager)
        kernel._lifecycle.register_manager(kernel._resource_manager)
        kernel._lifecycle.register_manager(kernel._security_manager)
        kernel._lifecycle.register_manager(kernel._capability_manager)
        kernel._lifecycle.register_manager(kernel._workflow_manager)
        kernel._lifecycle.register_manager(kernel._observability_manager)

        await kernel._lifecycle.initialize()

        # Set running state
        kernel._running = True
        kernel._start_time = datetime.utcnow()
        kernel._startup_complete = True

    @pytest.mark.asyncio
    async def test_health_representation_contains_required_fields(self, kernel, temp_dir):
        """Verify kernel produces valid health representation with all required fields."""
        health_file = temp_dir / "kernel.health"

        # Manually write health status to simulate kernel._write_health_status
        kernel._write_health_status(CanonicalHealthState.RUNNING.value)

        assert health_file.exists(), "Health file should be created"

        health_data = json.loads(health_file.read_text())

        # Verify all required fields from spec
        required_fields = [
            "status",
            "timestamp",
            "uptime_seconds",
            "alive",
            "ready",
            "startup_complete",
            "dependencies",
            "lifecycle_state",
            "health_manager_status",
        ]

        for field in required_fields:
            assert field in health_data, f"Health data missing required field: {field}"

        # Verify field types and values
        assert health_data["status"] == CanonicalHealthState.RUNNING.value
        assert isinstance(health_data["timestamp"], str)
        assert isinstance(health_data["uptime_seconds"], (int, float))
        assert health_data["uptime_seconds"] >= 0
        assert isinstance(health_data["alive"], bool)
        assert isinstance(health_data["ready"], bool)
        assert isinstance(health_data["startup_complete"], bool)
        assert isinstance(health_data["dependencies"], dict)
        assert isinstance(health_data["lifecycle_state"], str)
        assert isinstance(health_data["health_manager_status"], str)

    @pytest.mark.asyncio
    async def test_health_structurally_valid_across_all_eight_states(self, kernel, temp_dir):
        """Verify health representation remains structurally valid across all 8 canonical states."""
        health_file = temp_dir / "kernel.health"

        for state in CanonicalHealthState:
            # Write each state
            kernel._write_health_status(state.value)

            assert health_file.exists()
            health_data = json.loads(health_file.read_text())

            # Verify structure is consistent
            assert "status" in health_data
            assert health_data["status"] == state.value
            assert "timestamp" in health_data
            assert "uptime_seconds" in health_data
            assert "alive" in health_data
            assert "ready" in health_data
            assert "startup_complete" in health_data
            assert "dependencies" in health_data
            assert "lifecycle_state" in health_data
            assert "health_manager_status" in health_data

            # Verify boolean fields
            assert isinstance(health_data["alive"], bool)
            assert isinstance(health_data["ready"], bool)
            assert isinstance(health_data["startup_complete"], bool)

            # Note: The 'alive' and 'ready' fields in the written health file reflect
            # the kernel's current internal state (self.is_alive, self.is_ready) at write time,
            # not the theoretical liveness/readiness of the status being written.
            # This is the actual implementation behavior.


# =============================================================================
# D. LIVENESS / READINESS — 2 tests
# =============================================================================

class TestLivenessReadiness:
    """Tests for liveness and readiness behavior."""

    @pytest.fixture
    async def kernel(self, temp_dir, reset_singletons):
        """Create a kernel for liveness/readiness testing."""
        config = KernelConfig(data_dir=temp_dir)
        kernel = HermesKernel(config=config)
        yield kernel
        try:
            await kernel.stop()
        except Exception:
            pass

    def test_fresh_health_state_is_alive(self, kernel, temp_dir):
        """Verify fresh health state/file is considered alive."""
        health_file = temp_dir / "kernel.health"

        # Create fresh health file with RUNNING state
        fresh_time = datetime.utcnow().isoformat()
        health_file.write_text(json.dumps({
            "status": CanonicalHealthState.RUNNING.value,
            "timestamp": fresh_time,
            "uptime_seconds": 100,
            "alive": True,
            "ready": True,
            "startup_complete": True,
            "dependencies": {},
            "lifecycle_state": "operational",
            "health_manager_status": "healthy",
        }))

        # Patch kernel's health file path
        kernel._health_check_path = health_file
        kernel._heartbeat_interval_seconds = 30
        kernel._stale_threshold_multiplier = 2
        kernel._running = True

        # Check liveness using internal method
        assert kernel._check_liveness() is True, "Fresh RUNNING state should be alive"

    def test_stale_health_state_is_not_alive(self, kernel, temp_dir):
        """Verify stale health state/file is considered not alive when exceeding threshold."""
        health_file = temp_dir / "kernel.health"

        # Create stale health file (old timestamp)
        old_time = datetime(2020, 1, 1, 0, 0, 0).isoformat()
        health_file.write_text(json.dumps({
            "status": CanonicalHealthState.RUNNING.value,
            "timestamp": old_time,
            "uptime_seconds": 100,
            "alive": True,
            "ready": True,
            "startup_complete": True,
            "dependencies": {},
            "lifecycle_state": "operational",
            "health_manager_status": "healthy",
        }))

        # Patch kernel's health file path and stale threshold
        kernel._health_check_path = health_file
        kernel._heartbeat_interval_seconds = 30
        kernel._stale_threshold_multiplier = 2  # stale after 60 seconds
        kernel._running = True

        # Check liveness - should fail due to stale timestamp
        assert kernel._check_liveness() is False, "Stale health timestamp should not be alive"

    def test_terminal_states_not_alive(self, kernel, temp_dir):
        """Verify STOPPED and ERROR states are not alive."""
        health_file = temp_dir / "kernel.health"

        for state in [CanonicalHealthState.STOPPED, CanonicalHealthState.ERROR]:
            fresh_time = datetime.utcnow().isoformat()
            health_file.write_text(json.dumps({
                "status": state.value,
                "timestamp": fresh_time,
                "uptime_seconds": 100,
                "alive": False,
                "ready": False,
                "startup_complete": True,
                "dependencies": {},
                "lifecycle_state": "terminated",
                "health_manager_status": "unhealthy",
            }))

            kernel._health_check_path = health_file
            kernel._heartbeat_interval_seconds = 30
            kernel._stale_threshold_multiplier = 2
            kernel._running = False

            assert kernel._check_liveness() is False, \
                f"State {state.value} should not be alive"


# =============================================================================
# E. CONFIGURATION LOADING — 2 tests
# =============================================================================

class TestConfigurationLoading:
    """Tests for actual configuration loading through the configuration system."""

    @pytest.fixture
    async def config_manager(self, reset_singletons):
        """Create a ConfigurationManager with real EventBus."""
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        await bus.initialize()

        mgr = get_configuration_manager(event_bus=bus, config_path=Path("config/defaults.yaml"))
        await mgr.initialize()
        mgr.freeze()

        yield mgr

        await mgr.shutdown()
        await bus.shutdown()
        reset_configuration_manager_singleton()
        reset_event_bus_singleton()

    def test_defaults_yaml_loads_successfully(self, config_manager):
        """Verify config/defaults.yaml loads successfully through configuration system."""
        # Verify core kernel settings loaded
        assert config_manager.get("kernel.name") == "Hermes"
        assert config_manager.get("kernel.version") == "1.0.0"
        assert config_manager.get("kernel.log_level") == "INFO"

        # Verify service configuration loaded
        enabled_services = config_manager.get("services.enabled")
        assert isinstance(enabled_services, list)
        assert "memory" in enabled_services
        assert "planning" in enabled_services

        # Verify autonomy config loaded
        assert config_manager.get("services.autonomy.enabled") is False

        # Verify capabilities config loaded
        assert config_manager.get("capabilities.enabled") is True

    def test_production_yaml_loads_and_applies_overrides(self, reset_singletons):
        """Verify production config loads and applies overrides correctly.

        ConfigurationManager expects Layer 2 (app config) at config_path and
        Layer 3 (env config) as app.{environment}.yaml in the same directory.
        """
        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        asyncio.run(bus.initialize())

        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            # Create base config (Layer 2) - ConfigurationManager loads this as app config
            base_config = tmp_path / "app.yaml"
            base_config.write_text("""
kernel:
  name: "Hermes"
  version: "1.0.0"
  log_level: "INFO"
  environment: "production"
""")

            # Create env-specific config (Layer 3) - must be named app.{environment}.yaml
            # in the SAME directory as the base config
            prod_config = tmp_path / "app.production.yaml"
            prod_config.write_text("""
kernel:
  data_dir: "/opt/data"
  health_check_interval_ms: 30000

event_bus:
  max_history: 100000
  auto_start_dispatch_worker: true

state:
  persistence_path: "/opt/data/state"
  consistency_class: "STRONG"

security:
  strict_mode: true

capability:
  manifest_dir: "/opt/hermes/config/capabilities"

services:
  dashboard:
    enabled: false
    host: "0.0.0.0"
    auth_enabled: true

production:
  graceful_shutdown_timeout: 30
  health_check_endpoint: true
  secret_management: "external"
""")

            mgr = get_configuration_manager(event_bus=bus, config_path=base_config)
            asyncio.run(mgr.initialize())
            mgr.freeze()

            # Verify base config loaded
            assert mgr.get("kernel.environment") == "production"
            assert mgr.get("kernel.log_level") == "INFO"

            # Verify production overrides are applied (Layer 3)
            assert mgr.get("kernel.data_dir") == "/opt/data"
            assert mgr.get("kernel.health_check_interval_ms") == 30000

            # Verify event_bus overrides
            assert mgr.get("event_bus.max_history") == 100000
            assert mgr.get("event_bus.auto_start_dispatch_worker") is True

            # Verify state overrides
            assert mgr.get("state.persistence_path") == "/opt/data/state"
            assert mgr.get("state.consistency_class") == "STRONG"

            # Verify security overrides
            assert mgr.get("security.strict_mode") is True

            # Verify capability overrides
            assert mgr.get("capability.manifest_dir") == "/opt/hermes/config/capabilities"

            # Verify services.dashboard overrides
            assert mgr.get("services.dashboard.enabled") is False
            assert mgr.get("services.dashboard.host") == "0.0.0.0"
            assert mgr.get("services.dashboard.auth_enabled") is True

            # Verify production-specific section
            assert mgr.get("production.graceful_shutdown_timeout") == 30
            assert mgr.get("production.health_check_endpoint") is True
            # secret_management contains "secret" token -> masked; use get_secret for raw value
            assert mgr.get_secret("production.secret_management") == "external"

            asyncio.run(mgr.shutdown())
        asyncio.run(bus.shutdown())
        reset_configuration_manager_singleton()
        reset_event_bus_singleton()


# =============================================================================
# F. DASHBOARD ENDPOINTS — 2 tests
# =============================================================================

class TestDashboardEndpoints:
    """Tests for dashboard HTTP endpoints using actual implementation."""

    @pytest.fixture
    async def dashboard_service(self, temp_dir, reset_singletons):
        """Create a DashboardService with minimal kernel mock."""
        from aios.services.dashboard_service import DashboardService
        from aios.events.core.bus import EventBus, EventBusConfig

        bus = EventBus(config=EventBusConfig(auto_start_dispatch_worker=False))
        await bus.initialize()

        # Create minimal kernel mock with required attributes
        kernel_mock = MagicMock()
        kernel_mock.self_loop_engine = None
        kernel_mock.self_prompt_generator = None
        kernel_mock.failure_recovery_manager = None
        kernel_mock.integration_status_service = None
        kernel_mock.terminal_contract_violations = []
        kernel_mock.supabase_adapter = None
        kernel_mock.obsidian_git_adapter = None
        kernel_mock.n8n_adapter = None
        kernel_mock.project_service = None

        # Mock kernel.get_stats()
        kernel_mock.get_stats.return_value = {
            "kernel": {"running": True, "uptime_seconds": 100}
        }

        # Create security manager mock
        security_mock = MagicMock()
        from aios.core.security_manager import SecurityDecision
        security_mock.authorize.return_value = SecurityDecision.ALLOW

        # Create dashboard service
        service = DashboardService(
            kernel=kernel_mock,
            event_bus=bus,
            security_manager=security_mock,
        )
        await service.start()

        yield service

        await service.stop()
        await bus.shutdown()
        reset_event_bus_singleton()

    def test_alive_ready_endpoints_return_canonical_responses(self, dashboard_service):
        """Verify /alive and /ready return expected canonical responses by invoking actual handler methods."""
        from aios.services.dashboard_server import _Handler
        from io import BytesIO
        import json
        import asyncio

        # Create a kernel mock with check_alive/check_ready methods
        kernel_mock = MagicMock()

        # Create a simple mock handler class that inherits from _Handler
        class MockHandler(_Handler):
            def __init__(self):
                # Don't call parent __init__ to avoid socket creation
                self.kernel = kernel_mock
                self.dashboard_service = dashboard_service
                self.response_status = None
                self.response_headers = []
                self.response_body = BytesIO()

            def send_response(self, status, message=None):
                self.response_status = status

            def send_header(self, header, value):
                self.response_headers.append((header, value))

            def end_headers(self):
                pass  # End of headers

            @property
            def wfile(self):
                return self.response_body

        # Test /alive endpoint - kernel returns True (alive)
        handler = MockHandler()
        handler.path = "/alive"
        # Create an async mock that returns True
        async def mock_check_alive_true():
            return True
        kernel_mock.check_alive = mock_check_alive_true

        # Invoke the actual handler method
        handler._handle_alive()

        # Verify the actual HTTP response
        assert handler.response_status == 200  # Should return 200 for alive=True
        # Check that Content-Type header was set
        header_calls = [h for h in handler.response_headers if h[0] == "Content-Type"]
        assert len(header_calls) == 1
        assert header_calls[0][1] == "application/json"
        # Check response body
        body_data = json.loads(handler.response_body.getvalue().decode('utf-8'))
        assert body_data["alive"] is True

        # Test /alive endpoint - kernel returns False (not alive)
        handler = MockHandler()
        handler.path = "/alive"
        # Create an async mock that returns False
        async def mock_check_alive_false():
            return False
        kernel_mock.check_alive = mock_check_alive_false

        # Invoke the actual handler method
        handler._handle_alive()

        # Verify the actual HTTP response
        assert handler.response_status == 503  # Should return 503 for alive=False
        # Check that Content-Type header was set
        header_calls = [h for h in handler.response_headers if h[0] == "Content-Type"]
        assert len(header_calls) == 1
        assert header_calls[0][1] == "application/json"
        # Check response body
        body_data = json.loads(handler.response_body.getvalue().decode('utf-8'))
        assert body_data["alive"] is False

        # Test /alive endpoint - kernel raises exception
        handler = MockHandler()
        handler.path = "/alive"
        # Create an async mock that raises an exception
        async def mock_check_alive_error():
            raise Exception("test error")
        kernel_mock.check_alive = mock_check_alive_error

        # Invoke the actual handler method
        handler._handle_alive()

        # Verify the actual HTTP response
        assert handler.response_status == 500  # Should return 500 for exception
        # Check that Content-Type header was set
        header_calls = [h for h in handler.response_headers if h[0] == "Content-Type"]
        assert len(header_calls) == 1
        assert header_calls[0][1] == "application/json"
        # Check response body
        body_data = json.loads(handler.response_body.getvalue().decode('utf-8'))
        assert body_data["alive"] is False
        assert "error" in body_data
        assert body_data["error"] == "test error"

        # Test /ready endpoint - kernel returns True (ready)
        handler = MockHandler()
        handler.path = "/ready"
        # Create an async mock that returns True
        async def mock_check_ready_true():
            return True
        kernel_mock.check_ready = mock_check_ready_true

        # Invoke the actual handler method
        handler._handle_ready()

        # Verify the actual HTTP response
        assert handler.response_status == 200  # Should return 200 for ready=True
        # Check that Content-Type header was set
        header_calls = [h for h in handler.response_headers if h[0] == "Content-Type"]
        assert len(header_calls) == 1
        assert header_calls[0][1] == "application/json"
        # Check response body
        body_data = json.loads(handler.response_body.getvalue().decode('utf-8'))
        assert body_data["ready"] is True

        # Test /ready endpoint - kernel returns False (not ready)
        handler = MockHandler()
        handler.path = "/ready"
        # Create an async mock that returns False
        async def mock_check_ready_false():
            return False
        kernel_mock.check_ready = mock_check_ready_false

        # Invoke the actual handler method
        handler._handle_ready()

        # Verify the actual HTTP response
        assert handler.response_status == 503  # Should return 503 for ready=False
        # Check that Content-Type header was set
        header_calls = [h for h in handler.response_headers if h[0] == "Content-Type"]
        assert len(header_calls) == 1
        assert header_calls[0][1] == "application/json"
        # Check response body
        body_data = json.loads(handler.response_body.getvalue().decode('utf-8'))
        assert body_data["ready"] is False

        # Test /ready endpoint - kernel raises exception
        handler = MockHandler()
        handler.path = "/ready"
        # Create an async mock that raises an exception
        async def mock_check_ready_error():
            raise Exception("test error")
        kernel_mock.check_ready = mock_check_ready_error

        # Invoke the actual handler method
        handler._handle_ready()

        # Verify the actual HTTP response
        assert handler.response_status == 500  # Should return 500 for exception
        # Check that Content-Type header was set
        header_calls = [h for h in handler.response_headers if h[0] == "Content-Type"]
        assert len(header_calls) == 1
        assert header_calls[0][1] == "application/json"
        # Check response body
        body_data = json.loads(handler.response_body.getvalue().decode('utf-8'))
        assert body_data["ready"] is False
        assert "error" in body_data
        assert body_data["error"] == "test error"

    @pytest.mark.asyncio
    async def test_api_pages_returns_all_eight_pages_including_system_observability(self, dashboard_service):
        """Verify /api/pages returns complete dashboard page set with system_observability."""
        # Get all pages from the actual service
        all_pages = dashboard_service.get_all_pages()

        # Verify structure
        assert "generated_at" in all_pages
        assert all_pages["authority_model"] == "aios_sole_authority"
        assert "pages" in all_pages

        pages = all_pages["pages"]

        # Verify exactly 8 pages
        expected_pages = {
            "planning_chat",
            "resource_onboarding",
            "project_execution",
            "knowledge_history",
            "system_health",
            "project_workspace",
            "integrations_credentials",
            "system_observability",
        }

        actual_pages = set(pages.keys())
        assert actual_pages == expected_pages, \
            f"Expected 8 pages: {expected_pages}, got: {actual_pages}"

        # Verify system_observability page specifically
        assert "system_observability" in pages
        observability_page = pages["system_observability"]
        assert observability_page["page"] == "system_observability"
        assert observability_page["authority"] == "aios_sole"
        assert "metrics" in observability_page
        assert "spans" in observability_page
        assert "health" in observability_page
        assert "recent_events" in observability_page
        assert observability_page["read_only"] is True

        # Verify all pages have required structure
        for page_name, page_data in pages.items():
            assert "page" in page_data
            assert page_data["page"] == page_name
            assert page_data["authority"] == "aios_sole"
            assert page_data["read_only"] is True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDeploymentIntegration:
    """Integration tests combining multiple deployment aspects."""

    @pytest.fixture
    async def full_kernel(self, temp_dir, reset_singletons):
        """Create a fully initialized kernel for integration testing."""
        config = KernelConfig(data_dir=temp_dir)
        kernel = HermesKernel(config=config)
        await kernel.start()

        yield kernel

        await kernel.stop()

    @pytest.mark.asyncio
    async def test_kernel_start_produces_valid_health_file(self, full_kernel, temp_dir):
        """Test that kernel start produces valid health file with all required fields."""
        health_file = temp_dir / "kernel.health"

        assert health_file.exists()

        health_data = json.loads(health_file.read_text())

        # Verify all required fields
        required = [
            "status", "timestamp", "uptime_seconds", "alive", "ready",
            "startup_complete", "dependencies", "lifecycle_state", "health_manager_status"
        ]
        for field in required:
            assert field in health_data

        # After full start, should be RUNNING or READY or DEGRADED
        assert health_data["status"] in [
            CanonicalHealthState.RUNNING.value,
            CanonicalHealthState.READY.value,
            CanonicalHealthState.DEGRADED.value,
        ]

        # Should be alive and ready
        assert health_data["alive"] is True
        assert health_data["ready"] is True
        assert health_data["startup_complete"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])