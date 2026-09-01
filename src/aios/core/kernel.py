"""
Hermes Kernel - The Core Orchestrator for AI-OS.

The Kernel is the central coordination component that manages the Event Bus,
Workflow Manager, State Manager, and Resource Manager.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from aios.config.loader import load_config
from aios.config.models import AppConfig

# Kernel uses CANONICAL Core Components (Task 5/6/7/8 — single authority per process)
from aios.events.core.bus import (
    EventBus as CoreEventBus,
    EventBusConfig,
    reset_event_bus_singleton as reset_core_event_bus_singleton,
    set_core_event_bus,
)
from aios.core.service_registry import (
    ServiceRegistry as CoreServiceRegistry,
    get_service_registry as get_core_service_registry,
    reset_service_registry_singleton as reset_core_service_registry_singleton,
)
from aios.core.configuration_manager import (
    ConfigurationManager,
    get_configuration_manager,
    set_configuration_manager,
)
from aios.core.structured_logger import (
    StructuredLogger,
    get_logger,
    set_logger,
)
# Task 9 — LifecycleManager (first Core Manager, Part 4 §4.3). Minimal kernel
# integration: the kernel owns its construction/integration so LifecycleManager
# (which is NOT a Core Component) can drive the kernel lifecycle state machine.
# The kernel retains ownership of EventBus / StructuredLogger shutdown order
# (§3.7.4) and does NOT delegate Core Component teardown to LifecycleManager.
from aios.core.lifecycle_manager import (
    LifecycleManager,
    get_lifecycle_manager,
    set_lifecycle_manager,
    reset_lifecycle_manager_singleton,
)
# Managers (these use canonical EventBus / ServiceRegistry via global singletons)
from aios.core.state import StateManager, get_state_manager, set_state_manager
from aios.core.storage import (
    StorageManager,
    get_storage_manager,
    set_storage_manager,
)
from aios.core.workflow import (
    WorkflowManager,
    get_workflow_manager,
    set_workflow_manager,
    reset_workflow_manager_singleton,
)
from aios.core.resource_manager import (
    ResourceManager,
    get_resource_manager,
    set_resource_manager,
)
# Task 12 — HealthManager (Phase-3 Governance Core Manager). Constructed in
# _init_core_components(); LifecycleManager (constructed in _init_lifecycle_manager)
# drives its initialize()/shutdown() via Phase-3 phase topology. It is NOT added
# to _start_services/_stop_engineering_services (same-phase sibling of
# ResourceManager; alphabetical ordering within Phase 3 is deterministic).
from aios.core.health_manager import (
    HealthManager,
    get_health_manager,
    set_health_manager,
)
# Task 14 — SecurityManager (Phase-3 Governance Core Manager). Constructed in
# _init_core_components(); LifecycleManager will register and drive it. It is NOT
# added to _start_services/_stop_engineering_services (same-phase sibling of
# ResourceManager/HealthManager; alphabetical ordering within Phase 3 is
# deterministic: HealthManager, ResourceManager, SecurityManager).
from aios.core.security_manager import (
    SecurityManager,
    get_security_manager,
    set_security_manager,
    reset_security_manager_singleton,
)
# Task 15 — CapabilityManager (Phase-4 Execution Core Manager). Constructed in
# _init_core_components(); LifecycleManager (constructed in _init_lifecycle_manager)
# will register and drive it. Phase-4 ordering is deterministic (alphabetical:
# CapabilityManager before WorkflowManager).
from aios.core.capability_manager import (
    CapabilityManager,
    get_capability_manager,
    set_capability_manager,
    reset_capability_manager_singleton,
)
# Task 15 — ObservabilityManager (Phase-5 Observability Core Manager). Constructed
# in _init_core_components(); LifecycleManager will register and drive it. It is
# the only manager in its phase.
from aios.core.observability_manager import (
    ObservabilityManager,
    get_observability_manager,
    set_observability_manager,
    reset_observability_manager_singleton,
)
from aios.core.memory import MemoryManager, get_memory_manager, set_memory_manager
from aios.core.mcp_manager import MCPManager, get_mcp_manager, set_mcp_manager
# M13 — Self-Loop & Self-Prompting (Terminal 1 wiring).
# These components implement the single authoritative autonomous decision-making engine.
from aios.core.self_loop_engine import SelfLoopEngine
from aios.core.self_prompt_generator import SelfPromptGenerator
# M7 — Multi-Perspective Testing & User Simulation (Terminal 2 wiring).
# These components are registered on the kernel so production code can reach them
# through a single instance. They reuse the canonical singletons (CouncilManager,
# EventBus, SecurityManager, ModelRouter) — NO duplicates are created here.
from aios.services.testing import TestOrchestratorService
from aios.core.user_simulation_agent import UserSimulationAgent
from aios.core.simplification_gate import SimplificationGate
from aios.adapters.hermes_bridge import HermesBridge
from aios.adapters.playwright_mcp_adapter import PlaywrightMCPAdapter
from aios.adapters.graphify_adapter import GraphifyAdapter
from aios.adapters.notion_adapter import NotionAdapter
from aios.adapters.obsidian_adapter import ObsidianAdapter
from aios.adapters.claude_mem_adapter import ClaudeMemAdapter
from aios.adapters.supabase_adapter import SupabaseAdapter, AIOS_TEST_SCHEMA, AIOS_OWNED_SCHEMAS
from aios.adapters.n8n_adapter import N8nAdapter
from aios.adapters.obsidian_git_adapter import ObsidianGitAdapter
# M13 — Terminal Architecture & Separation contract enforcement
from aios.architecture.terminal_contract import (
    TerminalContract,
    TerminalId,
    AuthorityLevel,
    AuthorityViolation,
    TERMINAL_ASSIGNMENTS,
    validate_authority_preservation,
)
from aios.core.model_router import ModelRouter, get_model_router, set_model_router
# M13 — bounded, AI-OS-authoritative failure-recovery coordinator
from aios.core.failure_recovery import FailureRecoveryManager
# Engineering services use the canonical ServiceRegistry
from aios.services.base import BaseService
from aios.events.core.types import EventType

logger = logging.getLogger(__name__)


@dataclass
class KernelConfig:
    """Kernel configuration."""
    name: str = "Hermes"
    version: str = "0.1.0"
    config_path: Path | None = None
    data_dir: Path = Path("./data")
    log_level: str = "INFO"
    event_bus_max_history: int = 10000
    event_bus_max_dispatch_depth: int = 64  # Increased for workflows with retries
    auto_start_services: bool = True


@dataclass
class ServiceStatus:
    """Service status tracking."""
    name: str
    started: bool = False
    healthy: bool = True
    started_at: datetime | None = None
    last_error: str | None = None


class HermesKernel:
    """
    Hermes Kernel - The central orchestrator for AI-OS.

    The Kernel manages:
    - Event Bus for inter-service communication (CANONICAL C1)
    - Service Registry for core services (CANONICAL C2)
    - Configuration Manager (C3)
    - Structured Logger (C4)
    - State Manager for workflow/application state
    - Workflow Manager for DAG-based workflows
    - Resource Manager for quotas
    - Lifecycle Manager (first Core Manager)
    - Engineering Services (registered in canonical C2)
    """

    def __init__(
        self,
        config: KernelConfig | None = None,
        app_config: AppConfig | None = None,
    ):
        """
        Initialize the Hermes Kernel.

        Args:
            config: Kernel configuration
            app_config: Application configuration
        """
        self._config = config or KernelConfig()
        self._app_config = app_config
        self._running = False
        self._start_time: datetime | None = None

        # Core Components (C1–C4) — CANONICAL AUTHORITIES (single instance per process)
        self._event_bus: CoreEventBus | None = None          # C1 — canonical EventBus (Task 5)
        self._service_registry: CoreServiceRegistry | None = None  # C2 — canonical ServiceRegistry (Task 6)
        self._configuration: ConfigurationManager | None = None   # C3 — ConfigurationManager (Task 7)
        self._structured_logger: StructuredLogger | None = None   # C4 — StructuredLogger (Task 8)

        # Core Manager (Task 9)
        self._lifecycle: LifecycleManager | None = None

        # Managers (constructed after C1–C4, use canonical singletons)
        self._state_manager: StateManager | None = None
        self._storage_manager: StorageManager | None = None
        self._workflow_manager: WorkflowManager | None = None
        self._resource_manager: ResourceManager | None = None
        self._health_manager: HealthManager | None = None
        # Task 14 — SecurityManager (Phase-3 Governance Core Manager)
        self._security_manager: SecurityManager | None = None
        # Task 15 — CapabilityManager (Phase-4 Execution Core Manager)
        self._capability_manager: CapabilityManager | None = None
        # M9-N6: manifest loader retained for explicit hot-reload (None until
        # _init_capability_manifests runs).
        self._capability_loader: Any | None = None
        # Task 15 — ObservabilityManager (Phase-5 Observability Core Manager)
        self._observability_manager: ObservabilityManager | None = None

        # M13 — Self-Loop & Self-Prompting components
        # (registered after the canonical Core Managers; reuse their singletons).
        self._self_loop_engine: SelfLoopEngine | None = None
        self._self_prompt_generator: SelfPromptGenerator | None = None
        # M13 — bounded external-resource adapters (T2) and terminal contract state
        self._supabase_adapter: SupabaseAdapter | None = None
        self._supabase_test_adapter: SupabaseAdapter | None = None
        self._n8n_adapter: N8nAdapter | None = None
        self._obsidian_git_adapter: ObsidianGitAdapter | None = None
        self._terminal_contract_violations: list[AuthorityViolation] = []
        # M7 — Multi-Perspective Testing & User Simulation components
        # (registered after the canonical Core Managers; reuse their singletons).
        self._test_orchestrator: TestOrchestratorService | None = None
        self._user_simulation_agent: UserSimulationAgent | None = None
        self._simplification_gate: SimplificationGate | None = None
        self._playwright_adapter: PlaywrightMCPAdapter | None = None
        # M8-T3 — Graphify Relationship / Knowledge Graph
        self._graphify_adapter: GraphifyAdapter | None = None
        # M8-T4 — External Knowledge / Planning Integration
        self._notion_adapter: NotionAdapter | None = None
        self._obsidian_adapter: ObsidianAdapter | None = None
        self._claude_mem_adapter: ClaudeMemAdapter | None = None
        # Integration Status Service (dashboard backend for onboarding)
        self._integration_status_service: Any | None = None
        # M13 — non-authoritative dashboard backend (Terminal 3 reads AI-OS state)
        self._dashboard_service: Any | None = None
        self._project_service: Any | None = None
        # M13 — bounded failure-recovery coordinator (AI-OS-authoritative)
        self._failure_recovery_manager: FailureRecoveryManager | None = None

        # Service tracking
        self._services: dict[str, ServiceStatus] = {}

        # Ensure data directory exists
        self._config.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def config(self) -> KernelConfig:
        """Get kernel configuration."""
        return self._config

    @property
    def app_config(self) -> AppConfig | None:
        """Get application configuration."""
        return self._app_config

    @property
    def running(self) -> bool:
        """Check if kernel is running."""
        return self._running

    @property
    def event_bus(self) -> CoreEventBus | None:
        """Get the CANONICAL EventBus (C1 — Task 5 authoritative implementation)."""
        return self._event_bus

    @property
    def state_manager(self) -> StateManager | None:
        """Get state manager."""
        return self._state_manager

    @property
    def storage_manager(self) -> StorageManager | None:
        """Get the StorageManager Core Manager (Part 4 §4.5, Task 11)."""
        return self._storage_manager

    @property
    def workflow_manager(self) -> WorkflowManager | None:
        """Get workflow manager."""
        return self._workflow_manager

    @property
    def resource_manager(self) -> ResourceManager | None:
        """Get resource manager."""
        return self._resource_manager

    @property
    def health_manager(self) -> HealthManager | None:
        """Get the HealthManager Core Manager (Part 4 §4.6, Task 12)."""
        return self._health_manager

    @property
    def security_manager(self) -> SecurityManager | None:
        """Get the SecurityManager Core Manager (Part 4 §4.7, Task 14)."""
        return self._security_manager

    @property
    def capability_manager(self) -> CapabilityManager | None:
        """Get the CapabilityManager Core Manager (Part 4 §4.8, Task 15)."""
        return self._capability_manager

    @property
    def observability_manager(self) -> ObservabilityManager | None:
        """Get the ObservabilityManager Core Manager (Part 4 §4.11, Task 15)."""
        return self._observability_manager

    @property
    def failure_recovery_manager(self) -> FailureRecoveryManager | None:
        """Get the M13 bounded FailureRecoveryManager (AI-OS-authoritative)."""
        return self._failure_recovery_manager

    @property
    def test_orchestrator(self) -> TestOrchestratorService | None:
        """Get the M7 TestOrchestratorService (extends WorkflowManager)."""
        return self._test_orchestrator

    @property
    def user_simulation_agent(self) -> UserSimulationAgent | None:
        """Get the M7 UserSimulationAgent (10th testing perspective)."""
        return self._user_simulation_agent

    @property
    def playwright_adapter(self) -> PlaywrightMCPAdapter | None:
        """Get the M8-T2 Playwright MCP adapter."""
        return self._playwright_adapter

    @property
    def graphify_adapter(self) -> GraphifyAdapter | None:
        """Get the M8-T3 Graphify MCP adapter."""
        return self._graphify_adapter

    @property
    def notion_adapter(self) -> NotionAdapter | None:
        """Get the M8-T4 Notion planning adapter."""
        return self._notion_adapter

    @property
    def obsidian_adapter(self) -> ObsidianAdapter | None:
        """Get the M8-T4 Obsidian knowledge adapter."""
        return self._obsidian_adapter

    @property
    def claude_mem_adapter(self) -> ClaudeMemAdapter | None:
        """Get the M8-T4 Claude-Mem context adapter."""
        return self._claude_mem_adapter

    @property
    def integration_status_service(self):
        """Get the Integration Status Service (dashboard backend for onboarding)."""
        return self._integration_status_service

    @property
    def dashboard_service(self):
        """Get the non-authoritative M13 Dashboard backend (Terminal 3 UI reads AI-OS state)."""
        return self._dashboard_service

    @property
    def project_service(self):
        """Get the non-authoritative M14-T2 Project Workspace service (bounded UI resource)."""
        return self._project_service

    @property
    def self_loop_engine(self) -> SelfLoopEngine | None:
        """Get the M13 SelfLoopEngine (single authoritative autonomous decision-making engine)."""
        return self._self_loop_engine

    @property
    def self_prompt_generator(self) -> SelfPromptGenerator | None:
        """Get the M13 SelfPromptGenerator (authoritative internal directives)."""
        return self._self_prompt_generator

    @property
    def simplification_gate(self) -> SimplificationGate | None:
        """Get the M7 SimplificationGate (pre-acceptance complexity gate)."""
        return self._simplification_gate

    @property
    def supabase_adapter(self) -> SupabaseAdapter | None:
        """Get the M13 Supabase persistence adapter (T2 bounded resource)."""
        return self._supabase_adapter

    @property
    def supabase_test_adapter(self) -> SupabaseAdapter | None:
        """Get the M14-T2 Supabase test adapter (T2 bounded test resource).

        Isolated test adapter with schema boundary limited to 'aios_real_test'.
        Only available when SUPABASE_TEST_URL and SUPABASE_TEST_ANON_KEY are provided.
        """
        return getattr(self, '_supabase_test_adapter', None)

    @property
    def n8n_adapter(self) -> N8nAdapter | None:
        """Get the M13 n8n bounded execution adapter (T2 bounded resource)."""
        return self._n8n_adapter

    @property
    def obsidian_git_adapter(self) -> ObsidianGitAdapter | None:
        """Get the M13 Obsidian Git durability adapter (T2 bounded resource)."""
        return self._obsidian_git_adapter

    @property
    def terminal_contract_violations(self) -> list[AuthorityViolation]:
        """M13 Phase 3 — recorded terminal authority contract violations (boot-time)."""
        return list(self._terminal_contract_violations)

    @property
    def memory_manager(self) -> MemoryManager | None:
        """Get the MemoryManager."""
        return get_memory_manager()

    @property
    def model_manager(self) -> ModelRouter | None:
        """Get the ModelRouter (single instance per INV-002)."""
        return get_model_router()

    @property
    def mcp_manager(self) -> MCPManager | None:
        """Get the MCPManager."""
        return getattr(self, '_mcp_manager', None)

    @property
    def security_manager(self) -> SecurityManager | None:
        """Get the SecurityManager Core Manager (Part 4 §4.7, Task 14)."""
        return get_security_manager()

    @property
    def configuration(self) -> ConfigurationManager | None:
        """Get the ConfigurationManager Core Component (C3, Part 3 §3.5)."""
        return self._configuration

    @property
    def service_registry(self) -> CoreServiceRegistry | None:
        """Get the CANONICAL ServiceRegistry (C2 — Task 6 authoritative implementation)."""
        return self._service_registry

    @property
    def logger(self) -> StructuredLogger | None:
        """Get the StructuredLogger Core Component (C4, Part 3 §3.6)."""
        return self._structured_logger

    @property
    def lifecycle(self) -> LifecycleManager | None:
        """Get the LifecycleManager Core Manager (Part 4 §4.3, Task 9)."""
        return self._lifecycle

    def register_service(self, service: BaseService) -> BaseService:
        """Register an Engineering Service with the kernel (canonical C2 registry).

        Synchronous, preserving the pre-Task-9 public contract: before the kernel
        is started (registry not yet initialized) this raises ``RuntimeError``
        immediately; after initialization it registers through the canonical
        ServiceRegistry. The canonical ``register`` is a coroutine (Core Component
        pattern), so it is driven to completion via :func:`_run_sync`.
        """
        if self._service_registry:
            # Register using canonical ServiceRegistry with proper namespacing.
            from aios.core.service_registry import ServiceType
            _run_sync(
                self._service_registry.register(
                    service,
                    service_id=f"engineering.{service.name}",
                    service_type=ServiceType.ENGINEERING,
                    metadata={"version": service.version, "description": service.description},
                )
            )
            logger.debug(f"Registered engineering service '{service.name}' in canonical registry")
            return service
        raise RuntimeError("Canonical service registry not initialized. Start kernel first.")

    def _bootstrap_engineering_services(self) -> list[BaseService]:
        """M9-N1 — instantiate + register all engineering services (GAP-A).

        Delegates to the M9 bootstrap (spec §11.1) using the kernel's own
        canonical registry wrapper and the optional ``services.enabled``
        allowlist from frozen config (spec §19). Also back-fills the M7
        ``TestOrchestratorService`` closed-loop collaborators (spec §22).
        Idempotent: re-registration replaces prior instances.
        """
        from aios.services.bootstrap import bootstrap_engineering_services

        enabled = self._read_config_list("services.enabled", [])
        return bootstrap_engineering_services(
            registry=self._registry_wrapper(),
            enabled=enabled or None,
            kernel=self,
        )

    def _registry_wrapper(self):
        """Legacy-compatible ``ServiceRegistry`` wrapper over the canonical C2.

        The wrapper never constructs a second runtime authority — it delegates
        every operation to the canonical singleton this kernel already owns
        (``services/registry.py`` module docstring, Rule 8/10), so
        registrations made here are exactly what ``_start_services`` sees.
        """
        from aios.services.registry import ServiceRegistry as LegacyRegistry

        return LegacyRegistry()

    def get_service(self, name: str) -> BaseService:
        """Get a registered Engineering Service (canonical C2 registry)."""
        if self._service_registry:
            # Look up by namespaced ID
            svc = self._service_registry.get_service(f"engineering.{name}")
            if svc is not None:
                return svc
        raise RuntimeError(f"Engineering service '{name}' not found or registry not initialized")

    async def start(self) -> None:
        """Start the kernel and all core services."""
        if self._running:
            logger.warning("Kernel already running")
            return

        logger.info("Starting Hermes Kernel...")

        # Initialize core components (canonical C1–C4)
        await self._init_core_components()

        # D-01 (M8-T6 remediation) — construct and assign the REAL kernel
        # MCPManager at boot. Previously ``self._mcp_manager`` was never set, so
        # every MCP-bound adapter received ``None`` and could never connect to a
        # server. The kernel now owns one authoritative MCPManager (also the
        # canonical global singleton) and exposes it to all MCP-backed adapters
        # via the normal construction sites. The security gate-before-connect
        # (C18) and configuration semantics are preserved unchanged.
        await self._init_mcp_manager()

        # Task 9 — construct + integrate the LifecycleManager Core Manager
        # (Part 4 §4.3). It is the authoritative kernel-lifecycle state machine.
        # Phase-1 wiring only; later managers are registered as they land (Tasks 10+).
        # The kernel retains ownership of Core Component shutdown order.
        await self._init_lifecycle_manager()

        # M7 — register the multi-perspective testing components, reusing the
        # canonical CouncilManager / EventBus / SecurityManager / ModelRouter
        # singletons (no duplicates). Safe to run after the Core Managers exist.
        await self._init_m7_testing()

        # M8-T3 — register Graphify context capability and adapter.
        await self._init_graphify()

        # M8-T2 — register Playwright MCP capability and adapter.
        await self._init_playwright()

        # M13 — initialize self-loop engine and self-prompt generator
        await self._init_self_loop()
        await self._init_self_prompting()

        # M8-T4 — register Notion, Obsidian, Claude-Mem capabilities and adapters.
        await self._init_notion()
        await self._init_obsidian()
        await self._init_claude_mem()

        # M13 — register bounded external resource adapters (Supabase, n8n, Obsidian Git).
        # Each operates as a BOUNDED RESOURCE under AI-OS authority. Default mock mode;
        # real mode gated by AIOS_REAL_INTEGRATION_ENABLED=1 + user-provided credentials.
        await self._init_supabase()
        await self._init_n8n()
        await self._init_obsidian_git()

        # M13 Phase 3 — validate terminal authority separation at boot. This is a
        # fail-loud assertion that no bounded-resource adapter can claim AI-OS
        # authority, and that all external resources live on T2 per the contract.
        await self._validate_terminal_contract()

        # M13 Phase 5 — construct the bounded FailureRecoveryManager. It coordinates
        # recovery for M13 external (bounded) resources under AI-OS authority. The
        # SecurityManager gate-before-connect is enforced inside the manager, so it
        # must be created after the SecurityManager (Phase-3 core manager, line ~798).
        await self._init_failure_recovery()

        # M8-T5 — load capability manifests (dynamic discovery without kernel edits)
        await self._init_capability_manifests()

        # M10 — register autonomy services (N1-N12)
        await self._init_m10_autonomy()

        # G1 (M8-T4) — register FreeLLMAPI provider with ModelRouter (dev/test)
        await self._init_freellmapi()

        # Agent Reach — register communication capability
        await self._init_agent_reach()

        # Integration Status Service — dashboard backend for onboarding
        await self._init_integration_status()

        # M13 — non-authoritative dashboard backend (Terminal 3 reads AI-OS state;
        # forwards user actions through SecurityManager, holds no authority itself)
        await self._init_dashboard_backend()

        # M14-T2 — bounded Project Workspace service (non-authoritative; delegates
        # lifecycle/execution authority to AI-OS). Additive; does not alter the
        # SecurityManager, terminal contract, or M7–M14 verified behavior.
        await self._init_project_service()

        # M9-N1 — bootstrap engineering services into the canonical C2 registry
        # so the start loop below can run them (GAP-A closure). Runs BEFORE
        # _start_services because that loop only starts already-registered
        # services; per-service failures are logged + skipped inside the
        # bootstrap itself (partial-start tolerance, R-8).
        self._bootstrap_engineering_services()

        # Start services if enabled
        if self._config.auto_start_services:
            await self._start_services()

        # Emit kernel started event using canonical C1 EventBus
        # Map KernelStarted -> KERNEL_READY (canonical EventType)
        if self._event_bus:
            from aios.events.core.identity import ComponentIdentity, ComponentType
            from aios.events.core.event import Event
            from aios.events.core.types import SemanticVersion

            kernel_identity = ComponentIdentity(
                component_type=ComponentType.CORE_COMPONENT,
                component_name="HermesKernel",
                version=SemanticVersion(0, 1, 0),
            )

            event = Event(
                eventType=EventType.KERNEL_READY,
                source=kernel_identity,
                correlationId=__import__('uuid').uuid4(),
                payload={
                    "kernel_name": self._config.name,
                    "kernel_version": self._config.version,
                    "services_started": list(self._services.keys()),
                },
            )
            await self._event_bus.publish(event)

        self._running = True
        self._start_time = datetime.utcnow()

        logger.info("Hermes Kernel started successfully")

    async def stop(self) -> None:
        """Stop the kernel and all services."""
        if not self._running:
            logger.warning("Kernel not running")
            return

        logger.info("Stopping Hermes Kernel...")

        # Stop engineering services via LifecycleManager / canonical C2
        await self._stop_engineering_services()

        # Task 9 — drive the LifecycleManager to TERMINATED (kernel lifecycle
        # authority). LifecycleManager does NOT shut down C1–C4; the kernel owns
        # those teardown orderings (§3.7.4). This only finalizes lifecycle state
        # so StructuredLogger can still log the transition.
        await self._shutdown_lifecycle_manager()

        # StructuredLogger shutdown (Phase S3 — FIRST Core Component to shut
        # down, §3.7.4). Flushes remaining logs before other components (the
        # EventBus, which drains last in S0) are torn down.
        await self._shutdown_structured_logger()

        # Emit kernel stopped event using canonical C1 EventBus
        # Map KernelStopped -> KERNEL_SHUTDOWN_STARTED (canonical EventType)
        if self._event_bus:
            from aios.events.core.identity import ComponentIdentity, ComponentType
            from aios.events.core.event import Event
            from aios.events.core.types import SemanticVersion

            kernel_identity = ComponentIdentity(
                component_type=ComponentType.CORE_COMPONENT,
                component_name="HermesKernel",
                version=SemanticVersion(0, 1, 0),
            )

            event = Event(
                eventType=EventType.KERNEL_SHUTDOWN_STARTED,
                source=kernel_identity,
                correlationId=__import__('uuid').uuid4(),
                payload={
                    "kernel_name": self._config.name,
                    "uptime_seconds": (
                        datetime.utcnow() - self._start_time
                    ).total_seconds()
                    if self._start_time
                    else 0,
                },
            )
            await self._event_bus.publish(event)

        # Shutdown canonical EventBus (async await) - LAST per shutdown order
        if self._event_bus:
            await self._event_bus.shutdown()

        self._running = False

        logger.info("Hermes Kernel stopped")

    async def _init_core_components(self) -> None:
        """Initialize all canonical Core Components (C1–C4)."""
        logger.debug("Initializing canonical core components...")

        # C1: Canonical EventBus (Task 5) — exactly one per process (INV-EB-001)
        # Must be RUNNING before any component that publishes to it.
        reset_core_event_bus_singleton()
        event_bus_config = EventBusConfig(
            auto_start_dispatch_worker=False,
            maxDispatchDepth=self._config.event_bus_max_dispatch_depth,
            historyCapacity=self._config.event_bus_max_history,
        )
        self._event_bus = CoreEventBus(config=event_bus_config)
        await self._event_bus.initialize()
        set_core_event_bus(self._event_bus)

        # C2: Canonical ServiceRegistry (Phase 1) — depends on canonical EventBus
        reset_core_service_registry_singleton()
        self._service_registry = get_core_service_registry(event_bus=self._event_bus)

        # C3: ConfigurationManager (Phase 2) — depends on canonical EventBus
        self._configuration = get_configuration_manager(
            event_bus=self._event_bus,
            config_path=self._config.config_path,
        )
        set_configuration_manager(self._configuration)
        await self._configuration.initialize()
        # Phase 2 -> 3 freeze boundary: freeze configuration before any Core
        # Manager (Phase 4+) or Service (Phase 9+) can read it.
        self._configuration.freeze()

        # C4: StructuredLogger (Phase 3 — last Core Component, §3.6 / §3.7.3).
        # Depends on canonical EventBus, canonical ServiceRegistry (lazy via kernel),
        # and frozen ConfigurationManager.
        self._structured_logger = get_logger()
        set_logger(self._structured_logger)
        await self._structured_logger.initialize(self)

        # Managers (constructed after C1–C4, use canonical singletons).
        # Task 10 — StateManager is a Phase-2 Core Manager; it receives the
        # canonical C2/C3/C4 refs via DI so its initialize() can register with
        # ServiceRegistry, read frozen ConfigurationManager, and log through
        # StructuredLogger. LifecycleManager (constructed next) will register
        # and drive it.
        self._state_manager = StateManager(
            persistence_path=self._config.data_dir / "state",
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_state_manager(self._state_manager)

        # Task 11 — StorageManager is a Phase-2 Core Manager (Part 4 §4.5, "State &
        # Storage" phase, alongside StateManager). It receives the canonical
        # C2/C3/C4 refs via DI so its initialize() can register with
        # ServiceRegistry, read frozen ConfigurationManager, and log through
        # StructuredLogger. LifecycleManager (constructed next) will register and
        # drive it. Per the Phase Dependency Rule, StorageManager does NOT declare
        # StateManager as a formal dependency — deterministic alphabetical ordering
        # within Phase 2 (StateManager before StorageManager) guarantees correct
        # sequencing, and their operational coordination is event-driven (EventBus),
        # not a lifecycle dependency edge.
        self._storage_manager = StorageManager(
            persistence_path=self._config.data_dir / "storage",
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_storage_manager(self._storage_manager)

        # Task 16 — WorkflowManager is a Phase-4 (Execution) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.workflow``, read frozen
        # ConfigurationManager (``kernel.workflow.*``), and log through
        # StructuredLogger. LifecycleManager (constructed in
        # _init_lifecycle_manager) will register and drive it. Phase-4 ordering
        # is deterministic (alphabetical: CapabilityManager before
        # WorkflowManager).
        self._workflow_manager = WorkflowManager(
            state_manager=self._state_manager,
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_workflow_manager(self._workflow_manager)

        # Task 13 — ResourceManager is a Phase-3 (Governance) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.resource``, read frozen
        # ConfigurationManager (``kernel.resource.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register
        # and drive it. Per the Phase Dependency Rule, ResourceManager does NOT
        # declare HealthManager or SecurityManager as formal dependencies —
        # deterministic alphabetical ordering within Phase 3 (HealthManager,
        # ResourceManager, SecurityManager) guarantees correct sequencing.
        self._resource_manager = ResourceManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_resource_manager(self._resource_manager)

        # Task 12 — HealthManager is a Phase-3 (Governance) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.health``, read frozen
        # ConfigurationManager (``kernel.health.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register
        # and drive it. Per the Phase Dependency Rule, HealthManager does NOT
        # declare ResourceManager or SecurityManager as formal dependencies —
        # deterministic alphabetical ordering within Phase 3 (HealthManager,
        # ResourceManager, SecurityManager) guarantees correct sequencing.
        self._health_manager = HealthManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_health_manager(self._health_manager)

        # Task 14 — SecurityManager is a Phase-3 (Governance) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.security``, read frozen
        # ConfigurationManager (``kernel.security.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register and
        # drive it. Per the Phase Dependency Rule, SecurityManager does NOT declare
        # ResourceManager or HealthManager as formal dependencies — deterministic
        # alphabetical ordering within Phase 3 (HealthManager, ResourceManager,
        # SecurityManager) guarantees correct sequencing.
        self._security_manager = SecurityManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_security_manager(self._security_manager)

        # Task 15 — CapabilityManager is a Phase-4 (Execution) Core Manager. It
        # receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.capability``, read frozen
        # ConfigurationManager (``kernel.capability.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register and
        # drive it. Phase-4 ordering is deterministic (alphabetical:
        # CapabilityManager before WorkflowManager).
        self._capability_manager = CapabilityManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_capability_manager(self._capability_manager)

        # Task 15 — ObservabilityManager is a Phase-5 (Observability) Core Manager.
        # It receives the canonical C2/C3/C4 refs via DI so its initialize() can
        # register with ServiceRegistry as ``core.observability``, read frozen
        # ConfigurationManager (``kernel.observability.*``), and log through
        # StructuredLogger. LifecycleManager (constructed next) will register and
        # drive it. It is the only manager in its phase.
        self._observability_manager = ObservabilityManager(
            service_registry=self._service_registry,
            configuration_manager=self._configuration,
            logger=self._structured_logger,
        )
        set_observability_manager(self._observability_manager)

        # MemoryManager — initialize with kernel data_dir for persistence
        # Pass MCPManager to enable GraphifyBackend wiring when available
        mcp_mgr = get_mcp_manager()
        memory_mgr = get_memory_manager(base_path=self._config.data_dir, mcp_manager=mcp_mgr)
        set_memory_manager(memory_mgr)

        logger.debug("Canonical core components initialized")

    # ---------------------------------------------------------------------------
    # M8-T6 D-01 remediation — kernel-owned MCPManager lifecycle
    # ---------------------------------------------------------------------------

    async def _init_mcp_manager(self) -> None:
        """Assign the kernel's REAL ``MCPManager`` (D-01 fix).

        Previously ``self._mcp_manager`` was never set, so every MCP-bound
        adapter (Graphify, Playwright, Notion, Obsidian, Claude-Mem, Hermes
        MCP fallback) received ``mcp_manager=None`` at construction and could
        never establish a production MCP connection.

        The kernel now adopts the canonical global ``MCPManager`` singleton as
        its own. The singleton lazily auto-loads ``./config/mcp`` and is shared
        with :meth:`memory_manager`, :class:`HermesBridge`, and the
        ``mcp_manager`` property, so there is exactly one authoritative manager
        per process (INV-001).

        Connections are NOT made here: per the security model (C18
        gate-before-connect) and to avoid launching subprocesses during unit
        tests, each adapter connects lazily via its own ``connect()`` (which
        routes through the SecurityManager gate). Boot only wires the manager
        into the adapters so a real connection is *possible*.
        """
        self._mcp_manager = get_mcp_manager()
        logger.debug("MCPManager assigned to kernel (D-01 remediation)")

    async def _shutdown_structured_logger(self) -> None:
        """Shut down the StructuredLogger Core Component (Phase S3, §3.7.4)."""
        sl = self._structured_logger
        if sl is None:
            return
        try:
            await sl.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down StructuredLogger: {e}")
        finally:
            self._structured_logger = None

    async def _shutdown_lifecycle_manager(self) -> None:
        """Task 9 — finalize the LifecycleManager lifecycle state.

        Drives the LifecycleManager to TERMINATED. It does NOT shut down the Core
        Components (C1–C4); the kernel owns those teardown orderings (§3.7.4).
        Errors are logged and swallowed (lifecycle teardown must not block kernel
        shutdown), matching the StructuredLogger-shutdown precedent.
        """
        lm = self._lifecycle
        if lm is None:
            return
        try:
            await lm.shutdown()
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error shutting down LifecycleManager: {e}")
        finally:
            self._lifecycle = None

    async def _init_lifecycle_manager(self) -> None:
        """Task 9 — construct + integrate the LifecycleManager Core Manager.

        Builds the LifecycleManager wired to the four Core Components (C1–C4),
        registers it with the canonical ServiceRegistry (as ``core.lifecycle``),
        sets the global singleton, and drives initialization to OPERATIONAL.
        Later Core Managers are registered with ``lifecycle.register_manager``
        as they are implemented in subsequent tasks (now including Phase 2
        through Phase 5).

        The kernel owns Core Component shutdown order (§3.7.4); LifecycleManager
        is the lifecycle *authority* but does not tear down C1–C4 here.
        """
        logger.debug("Initializing LifecycleManager (Task 9)...")

        reset_lifecycle_manager_singleton()
        lm = get_lifecycle_manager(
            event_bus=self._event_bus,              # Canonical C1
            service_registry=self._service_registry,  # Canonical C2
            configuration_manager=self._configuration,  # C3
            logger=self._structured_logger,           # C4 (already initialized)
            kernel=self,
        )
        set_lifecycle_manager(lm)
        self._lifecycle = lm
        await lm.register_with_service_registry()

        # Task 10 — register the StateManager Core Manager (Phase 2, "State &
        # Storage") for LifecycleManager orchestration. StateManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's phase topology, NOT by the engineering
        # service start/stop loops.
        if self._state_manager is not None:
            lm.register_manager(self._state_manager)
            logger.debug("Registered StateManager with LifecycleManager (Phase 2).")

        # Task 11 — register the StorageManager Core Manager (Phase 2, "State &
        # Storage") for LifecycleManager orchestration. StorageManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's phase topology, NOT by the engineering
        # service start/stop loops. Phase-2 ordering is deterministic (alphabetical:
        # StateManager before StorageManager).
        if self._storage_manager is not None:
            lm.register_manager(self._storage_manager)
            logger.debug("Registered StorageManager with LifecycleManager (Phase 2).")

        # Task 12 — register the HealthManager Core Manager (Phase 3, "Governance")
        # for LifecycleManager orchestration. HealthManager was constructed in
        # _init_core_components(); its initialize()/shutdown() are driven by
        # LifecycleManager's Phase-3 phase topology, NOT by the engineering service
        # start/stop loops. Phase-3 ordering is deterministic (alphabetical:
        # HealthManager, ResourceManager, SecurityManager).
        if self._health_manager is not None:
            lm.register_manager(self._health_manager)
            logger.debug("Registered HealthManager with LifecycleManager (Phase 3).")

        # Task 13 — register the ResourceManager Core Manager (Phase 3,
        # "Governance") for LifecycleManager orchestration. ResourceManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's Phase-3 phase topology, NOT by the
        # engineering service start/stop loops (only its background cleanup task
        # is started/stopped by the engineering-service hooks for backward
        # compatibility). Phase-3 ordering is deterministic (alphabetical:
        # HealthManager, ResourceManager, SecurityManager).
        if self._resource_manager is not None:
            lm.register_manager(self._resource_manager)
            logger.debug("Registered ResourceManager with LifecycleManager (Phase 3).")

        # Task 14 — register the SecurityManager Core Manager (Phase 3,
        # "Governance") for LifecycleManager orchestration. SecurityManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's Phase-3 phase topology, NOT by the
        # engineering service start/stop loops. Phase-3 ordering is deterministic
        # (alphabetical: HealthManager, ResourceManager, SecurityManager).
        if self._security_manager is not None:
            lm.register_manager(self._security_manager)
            logger.debug("Registered SecurityManager with LifecycleManager (Phase 3).")

        # Task 15 — register the CapabilityManager Core Manager (Phase 4,
        # "Execution") for LifecycleManager orchestration. CapabilityManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's Phase-4 phase topology. Phase-4 ordering is
        # deterministic (alphabetical: CapabilityManager before WorkflowManager).
        if self._capability_manager is not None:
            lm.register_manager(self._capability_manager)
            logger.debug("Registered CapabilityManager with LifecycleManager (Phase 4).")

        # Task 16 — register the WorkflowManager Core Manager (Phase 4,
        # "Execution") for LifecycleManager orchestration. WorkflowManager was
        # constructed in _init_core_components(); its initialize()/shutdown() are
        # driven by LifecycleManager's Phase-4 phase topology, NOT by the
        # engineering service start/stop loops. Phase-4 ordering is deterministic
        # (alphabetical: CapabilityManager before WorkflowManager).
        if self._workflow_manager is not None:
            lm.register_manager(self._workflow_manager)
            logger.debug("Registered WorkflowManager with LifecycleManager (Phase 4).")

        # Task 15 — register the ObservabilityManager Core Manager (Phase 5,
        # "Observability") for LifecycleManager orchestration. It was constructed
        # in _init_core_components(); its initialize()/shutdown() are driven by
        # LifecycleManager's Phase-5 phase topology. It is the only manager in its
        # phase.
        if self._observability_manager is not None:
            lm.register_manager(self._observability_manager)
            logger.debug("Registered ObservabilityManager with LifecycleManager (Phase 5).")

        try:
            await lm.initialize()
        except Exception as exc:  # noqa: BLE001
            # Initialization coordinated rollback internally; surface clearly.
            logger.error(f"LifecycleManager initialization failed: {exc}")
            raise
        logger.debug("LifecycleManager initialized -> OPERATIONAL")

    async def _init_m7_testing(self) -> None:
        """Register the M7 multi-perspective testing components.

        All collaborators are the canonical singletons already constructed by the
        kernel (CouncilManager, EventBus, SecurityManager, ModelRouter). No
        second council / bus / router / security manager is created here (this is
        enforced by the architectural invariants INV-005/007/012/014).

        The ``UserSimulationAgent`` is wired to a real ``HermesBridge`` (M5 MCP
        fallback) which talks to the external, untrusted hermes-agent(EXT). It
        accepts ONLY app_url / user_goal / exploration_brief (INV-008).
        """
        # Single canonical CouncilManager instance (reused, never duplicated).
        from aios.core.council_manager import get_council_manager

        council = get_council_manager()

        # TestOrchestratorService EXTENDS the canonical WorkflowManager (INV-015):
        # it reuses the existing workflow lifecycle, never duplicates it.
        self._test_orchestrator = TestOrchestratorService(
            self._workflow_manager,
            council_manager=council,
            final_judge=None,  # uses the built-in FinalJudgeAgency singleton path
            simplification_gate=SimplificationGate(),
            security_manager=self._security_manager,
        )

        # UserSimulationAgent drives the EXTERNAL hermes-agent(EXT) via HermesBridge.
        # M9-N7: absolute ACP session TTL from frozen config (0 = disabled,
        # M8 default preserved); observation-only boundary is untouched.
        try:
            acp_ttl = int(self._configuration.get(
                "acp.session_ttl_seconds", default=0
            ) or 0)
        except Exception:  # noqa: BLE001
            acp_ttl = 0
        # ACP preferred path requires cwd (phantom until user provides hermes-agent repo).
        acp_cwd = self._read_config_str("acp.cwd", default="")
        hermes_bridge = HermesBridge(
            mcp_manager=self._mcp_manager,
            server_id="hermes_agent_ext",
            session_ttl_seconds=max(0, acp_ttl),
            cwd=acp_cwd,
        )
        self._user_simulation_agent = UserSimulationAgent(hermes_bridge)

        # SimplificationGate instance (already created above for the orchestrator;
        # share the same instance so the gate verdict is stable across the run).
        self._simplification_gate = self._test_orchestrator._gate

        logger.debug(
            "M7 testing components registered "
            "(TestOrchestratorService, UserSimulationAgent, SimplificationGate)"
        )

    def _read_config_str(self, path: str, default: str) -> str:
        """Read a string config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return str(val) if val is not None else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_list(self, path: str, default: list) -> list:
        """Read a list config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, (list, tuple)):
                return [str(item) for item in val]
            return default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_bool(self, path: str, default: bool) -> bool:
        """Read a bool config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "yes", "on")
            return bool(val)
        except Exception:  # noqa: BLE001
            return default

    async def _init_capability_manifests(self) -> None:
        """Load and register capabilities from manifest files (M8-T5).

        Reads YAML manifests from config/capabilities/ directory, validates them,
        and registers capabilities in CapabilityManager using the AdapterFactory.
        This enables dynamic capability discovery without kernel code changes.

        Failures are logged and skipped — a malformed manifest never blocks boot.
        """
        from aios.core.capability_manifest import (
            CapabilityManifestLoader,
            load_capability_manifests,
        )
        from aios.adapters.adapter_factory import create_adapter_factory

        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping manifest loading")
            return

        # Master switch (spec §19: kernel.capabilities.enabled).
        if not self._read_config_bool("kernel.capabilities.enabled", True):
            logger.debug("Capability manifest loading disabled by config; skipping")
            return

        # Adapter allowlist — defaults.yaml declares it as a YAML list; accept a
        # comma-separated string too for robustness.
        raw_allowlist = self._configuration.get(
            "kernel.capabilities.adapter_allowlist",
            default=None,
        ) if (self._configuration is not None and hasattr(self._configuration, "get")) else None
        if isinstance(raw_allowlist, (list, tuple)):
            allowlist_items = [str(item).strip() for item in raw_allowlist]
        elif isinstance(raw_allowlist, str):
            allowlist_items = [item.strip() for item in raw_allowlist.split(",")]
        else:
            allowlist_items = [
                "aios.adapters.graphify_adapter.GraphifyAdapter",
                "aios.adapters.playwright_mcp_adapter.PlaywrightMCPAdapter",
                "aios.adapters.notion_adapter.NotionAdapter",
                "aios.adapters.obsidian_adapter.ObsidianAdapter",
                "aios.adapters.claude_mem_adapter.ClaudeMemAdapter",
                "aios.adapters.acp_adapter.ACPAdapter",
                "aios.adapters.supabase_adapter.SupabaseAdapter",
                "aios.adapters.n8n_adapter.N8nAdapter",
                "aios.adapters.obsidian_git_adapter.ObsidianGitAdapter",
            ]
        adapter_allowlist_tuple = tuple(item for item in allowlist_items if item)

        # Create factory and inject into capability manager
        adapter_factory = create_adapter_factory(
            adapter_allowlist=adapter_allowlist_tuple,
            mcp_manager=self._mcp_manager,
        )
        self._capability_manager.set_adapter_factory(adapter_factory)
        self._capability_manager.set_security_manager(self._security_manager)

        # Load manifests
        manifest_dir = Path(self._read_config_str(
            "kernel.capabilities.manifest_dir",
            "./config/capabilities"
        ))
        trust_default = self._read_config_str(
            "kernel.capabilities.trust_default",
            "untrusted"
        )

        specs = await load_capability_manifests(
            manifest_dir=manifest_dir,
            adapter_allowlist=adapter_allowlist_tuple,
            trust_default=trust_default,
            security_manager=self._security_manager,
        )

        # M9-N6: retain the loader so explicit hot-reload reuses the identical
        # validation pipeline (allowlist, trust defaults, security manager).
        self._capability_loader = CapabilityManifestLoader(
            manifest_dir=manifest_dir,
            adapter_allowlist=adapter_allowlist_tuple,
            trust_default=trust_default,
            security_manager=self._security_manager,
        )

        # Register each spec; initialize enabled ones. Registration failures
        # (collision precedence, security gate) are typed and non-fatal to boot.
        registered = 0
        for spec in specs:
            try:
                entry = self._capability_manager.register_capability(spec)
                registered += 1
                if entry.enabled:
                    await self._capability_manager.initialize_capability(spec.capability_id)
                logger.info(f"Loaded capability from manifest: {spec.capability_id}")
            except Exception as e:  # noqa: BLE001 — one bad manifest must not block the rest
                logger.error(
                    f"Failed to register capability from manifest {spec.capability_id}: {e}"
                )

        logger.debug(
            f"M8-T5 capability manifests loaded ({registered}/{len(specs)} capabilities)"
        )

    async def reload_capability_manifests(self) -> dict[str, Any] | None:
        """M9-N6 — explicitly re-load and re-register capability manifests.

        Fail-closed (spec §11.6/§18): any invalid manifest or registration
        failure leaves the previous valid registry intact. Trust escalation is
        guarded by the unchanged M8-T5 gates (CM-SHADOW-001 / CM-PREC-001 /
        CM-MANIFEST-001) — this method adds no new authority.

        Gated by ``kernel.capabilities.hot_reload`` (default False, spec §19).
        Returns the applied delta dict, or None when the reload was skipped
        (disabled by config, CapabilityManager absent, or no prior manifest
        load has happened yet).
        """
        if not self._read_config_bool("kernel.capabilities.hot_reload", False):
            logger.debug("Capability manifest hot-reload disabled by config; skipping")
            return None
        if not self._capability_manager or not self._capability_loader:
            logger.debug(
                "CapabilityManager/loader not available; hot-reload unavailable"
            )
            return None

        result = await self._capability_manager.reload_capabilities(
            self._capability_loader,
            initialize=True,
        )
        logger.info(
            "Capability manifest hot-reload applied "
            f"(registered={len(result['registered'])}, "
            f"initialized={len(result['initialized'])}, "
            f"removed={len(result['removed'])})"
        )
        return result

    async def _init_graphify(self) -> None:
        """Register M8-T3 Graphify context capability and adapter.

        Connects to the Graphify MCP server (via MCPManager stdio),
        registers the ``graphify_context`` capability in CapabilityManager,
        and wires the adapter for use by architecture testing and context enrichment.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Graphify init")
            return

        # Create adapter — passes MCPManager for real path, None for test path
        adapter = GraphifyAdapter(
            mcp_manager=self._mcp_manager,
            server_id="graphify",
        )
        self._graphify_adapter = adapter

        # Register capability
        self._capability_manager.register(
            capability_id="graphify_context",
            facade="graph",
            provider_id="graphify",
            provider_metadata={
                "server_id": "graphify",
                "transport": "stdio",
                "timeout_seconds": 30,
                "auto_reconnect": True,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": [
                    "add_node", "get_node", "update_node", "delete_node",
                    "query_graph", "shortest_path", "add_edge",
                ],
            },
            tags=("graph", "knowledge", "context", "relationships", "dependency"),
        )

        logger.debug("M8-T3 Graphify capability registered (graphify_context)")

    async def _init_playwright(self) -> None:
        """Register M8-T2 Playwright MCP capability and adapter.

        Connects to the Playwright MCP server (via MCPManager stdio),
        registers the ``playwright_browser`` capability in CapabilityManager,
        and wires the adapter for use by accessibility testing.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Playwright init")
            return

        # Create adapter — passes MCPManager for real path, mock for test path.
        adapter = PlaywrightMCPAdapter(
            server_id="playwright_mcp",
            mcp_manager=self._mcp_manager,
        )
        self._playwright_adapter = adapter

        # Register capability
        self._capability_manager.register(
            capability_id="playwright_browser",
            facade="browser",
            provider_id="playwright_mcp",
            provider_metadata={
                "server_id": "playwright_mcp",
                "transport": "stdio",
                "timeout_seconds": 30,
            },
            security_context={
                "requires_validation": True,
                "allowed_actions": [
                    "navigate", "click", "type", "snapshot", "screenshot",
                    "press_key", "new_context", "close_context",
                ],
            },
            tags=("browser", "playwright", "accessibility", "deterministic"),
        )

        logger.debug("M8-T2 Playwright capability registered (playwright_browser)")

    async def _init_notion(self) -> None:
        """Register M8-T4 Notion planning capability and adapter.

        Connects to the Notion MCP server (via MCPManager stdio),
        registers the ``notion_planning`` capability in CapabilityManager,
        and wires the adapter for use by planning and project tracking.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Notion init")
            return

        # Create adapter — passes MCPManager for real path, None for test path
        adapter = NotionAdapter(
            mcp_manager=self._mcp_manager,
            server_id="notion",
            timeout_seconds=self._app_config.notion.timeout_seconds if self._app_config and hasattr(self._app_config, "notion") else 30,
        )
        self._notion_adapter = adapter

        # Register capability
        self._capability_manager.register(
            capability_id="notion_planning",
            facade="planning",
            provider_id="notion",
            provider_metadata={
                "server_id": "notion",
                "transport": "stdio",
                "timeout_seconds": self._app_config.notion.timeout_seconds if self._app_config and hasattr(self._app_config, "notion") else 30,
                "auto_reconnect": self._app_config.notion.auto_reconnect if self._app_config and hasattr(self._app_config, "notion") else True,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": [
                    "search_pages", "get_page", "create_page",
                    "update_page", "query_database",
                ],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key",
                ],
                "max_content_size": 10240,
            },
            tags=("planning", "notion", "project-tracking", "tasks"),
        )

        logger.debug("M8-T4 Notion capability registered (notion_planning)")

    async def _init_obsidian(self) -> None:
        """Register M8-T4 Obsidian knowledge capability and adapter.

        Connects to the Obsidian MCP server (via MCPManager stdio) with
        filesystem fallback to local vault,
        registers the ``obsidian_knowledge`` capability in CapabilityManager,
        and wires the adapter for use by persistent knowledge retrieval.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Obsidian init")
            return

        # Get vault path from config
        vault_path = None
        if self._app_config and hasattr(self._app_config, "obsidian"):
            vault_path = self._app_config.obsidian.vault_path or None

        # Create adapter — passes MCPManager for real path, None for test path
        adapter = ObsidianAdapter(
            mcp_manager=self._mcp_manager,
            server_id="obsidian",
            vault_path=vault_path,
            timeout_seconds=self._app_config.obsidian.timeout_seconds if self._app_config and hasattr(self._app_config, "obsidian") else 30,
        )
        self._obsidian_adapter = adapter

        # Register capability
        self._capability_manager.register(
            capability_id="obsidian_knowledge",
            facade="knowledge",
            provider_id="obsidian",
            provider_metadata={
                "server_id": "obsidian",
                "transport": "stdio",
                "timeout_seconds": self._app_config.obsidian.timeout_seconds if self._app_config and hasattr(self._app_config, "obsidian") else 30,
                "auto_reconnect": self._app_config.obsidian.auto_reconnect if self._app_config and hasattr(self._app_config, "obsidian") else True,
                "vault_path": vault_path,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": [
                    "search_notes", "get_note", "list_notes", "read_note",
                ],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key",
                ],
                "max_content_size": 10240,
            },
            tags=("knowledge", "obsidian", "documentation", "persistent"),
        )

        logger.debug("M8-T4 Obsidian capability registered (obsidian_knowledge)")

    async def _init_claude_mem(self) -> None:
        """Register M8-T4 Claude-Mem context capability and adapter.

        Connects to the Claude-Mem MCP server (via MCPManager stdio),
        registers the ``claude_mem_context`` capability in CapabilityManager,
        and wires the adapter for use by contextual memory retrieval.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Claude-Mem init")
            return

        # Create adapter — passes MCPManager for real path, None for test path
        adapter = ClaudeMemAdapter(
            mcp_manager=self._mcp_manager,
            server_id="claude_mem",
            timeout_seconds=self._app_config.claude_mem.timeout_seconds if self._app_config and hasattr(self._app_config, "claude_mem") else 30,
        )
        self._claude_mem_adapter = adapter

        # Register capability
        self._capability_manager.register(
            capability_id="claude_mem_context",
            facade="memory",
            provider_id="claude_mem",
            provider_metadata={
                "server_id": "claude_mem",
                "transport": "stdio",
                "timeout_seconds": self._app_config.claude_mem.timeout_seconds if self._app_config and hasattr(self._app_config, "claude_mem") else 30,
                "auto_reconnect": self._app_config.claude_mem.auto_reconnect if self._app_config and hasattr(self._app_config, "claude_mem") else True,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": [
                    "retrieve_context", "retrieve_recent", "retrieve_by_tag",
                ],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key",
                ],
                "max_content_size": 10240,
            },
            tags=("memory", "claude-mem", "contextual", "retrieval"),
        )

        logger.debug("M8-T4 Claude-Mem capability registered (claude_mem_context)")

    # ---------------------------------------------------------------------------
    # M13 — Bounded External Resource Adapters
    # ---------------------------------------------------------------------------

    async def _init_supabase(self) -> None:
        """Register M13 Supabase persistence capability and adapter.

        Supabase is a BOUNDED persistence resource. AI-OS owns semantic meaning;
        Supabase stores dumb bytes with durability. Default MOCK store; real mode
        gated by AIOS_REAL_INTEGRATION_ENABLED=1 + SUPABASE_URL/SUPABASE_ANON_KEY.

        M14-T2: Also registers a separate test adapter (capability=supabase_test)
        with its own schema boundary (aios_real_test) and test credentials
        (SUPABASE_TEST_URL/SUPABASE_TEST_ANON_KEY) when both are present.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Supabase init")
            return

        # --- Production Adapter ---
        real_mode = self._read_config_bool("services.supabase.real_mode_enabled", False) or (
            os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1"
        )
        # M14-T2: pass credentials from config (explicit) with env fallback.
        # Values are never hardcoded and never logged.
        supabase_url = (
            self._read_config_str("services.supabase.url", "")
            or os.environ.get("SUPABASE_URL")
        )
        supabase_anon_key = (
            self._read_config_str("services.supabase.anon_key", "")
            or os.environ.get("SUPABASE_ANON_KEY")
        )
        adapter = SupabaseAdapter(
            mcp_manager=self._mcp_manager,
            server_id="supabase",
            timeout_seconds=30,
            real_mode_enabled=real_mode,
            security_manager=self._security_manager,
            url=supabase_url or None,
            anon_key=supabase_anon_key or None,
            schema_allowlist=AIOS_OWNED_SCHEMAS,
            project_classification="production",
        )
        self._supabase_adapter = adapter

        self._capability_manager.register(
            capability_id="supabase_persistence",
            facade="persistence",
            provider_id="supabase",
            provider_metadata={
                "server_id": "supabase",
                "transport": "rest",
                "timeout_seconds": 30,
                "real_mode": real_mode,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": ["insert", "get", "update", "delete", "query"],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key", "service_role_key",
                ],
                "max_content_size": 102400,
            },
            tags=("persistence", "supabase", "storage", "durability"),
        )

        logger.debug(
            f"M13 Supabase capability registered (supabase_persistence, mode="
            f"{'real' if real_mode else 'mock'})"
        )

        # --- M14-T2 Test Adapter (isolated test resource) ---
        # Only construct/test-register when BOTH test credentials are present.
        # This MUST fail closed - no silent fallbacks.
        supabase_test_url = os.environ.get("SUPABASE_TEST_URL")
        supabase_test_anon_key = os.environ.get("SUPABASE_TEST_ANON_KEY")

        if supabase_test_url and supabase_test_anon_key:
            test_real_mode = (
                self._read_config_bool("services.supabase_test.real_mode_enabled", False)
                or os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1"
            )

            test_adapter = SupabaseAdapter(
                mcp_manager=self._mcp_manager,
                server_id="supabase_test",
                timeout_seconds=30,
                real_mode_enabled=test_real_mode,
                security_manager=self._security_manager,
                url=supabase_test_url,
                anon_key=supabase_test_anon_key,
                schema_allowlist=AIOS_TEST_SCHEMA,
                project_classification="test",
            )
            self._supabase_test_adapter = test_adapter

            self._capability_manager.register(
                capability_id="supabase_test",
                facade="persistence",
                provider_id="supabase_test",
                provider_metadata={
                    "server_id": "supabase_test",
                    "transport": "rest",
                    "timeout_seconds": 30,
                    "real_mode": test_real_mode,
                },
                security_context={
                    "requires_validation": True,
                    "allowed_operations": ["insert", "get", "update", "delete", "query"],
                    "sensitive_keys": [
                        "password", "token", "secret", "api_key",
                        "authorization", "credential", "private_key", "service_role_key",
                    ],
                    "max_content_size": 102400,
                },
                tags=("persistence", "supabase", "storage", "durability", "test"),
            )

            logger.debug(
                f"M14-T2 Supabase test capability registered (supabase_test, mode="
                f"{'real' if test_real_mode else 'mock'})"
            )
        else:
            self._supabase_test_adapter = None
            logger.debug("M14-T2 Supabase test adapter not registered (test credentials not provided)")
    async def _init_n8n(self) -> None:
        """Register M13 n8n bounded execution capability and adapter.

        n8n is a BOUNDED automation/execution resource. AI-OS directs workflows and
        evaluates results. Default MOCK engine; real mode gated by
        AIOS_REAL_INTEGRATION_ENABLED=1 + N8N_BASE_URL/N8N_API_KEY.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping n8n init")
            return

        real_mode = self._read_config_bool("services.n8n.real_mode_enabled", False) or (
            os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1"
        )
        # M14-T2: pass credentials from config (explicit) with env fallback.
        # Values are never hardcoded and never logged.
        n8n_base_url = (
            self._read_config_str("services.n8n.base_url", "")
            or os.environ.get("N8N_BASE_URL")
        )
        n8n_api_key = (
            self._read_config_str("services.n8n.api_key", "")
            or os.environ.get("N8N_API_KEY")
        )
        adapter = N8nAdapter(
            mcp_manager=self._mcp_manager,
            server_id="n8n",
            timeout_seconds=300,
            real_mode_enabled=real_mode,
            security_manager=self._security_manager,
            base_url=n8n_base_url or None,
            api_key=n8n_api_key or None,
        )
        self._n8n_adapter = adapter

        self._capability_manager.register(
            capability_id="n8n_execution",
            facade="automation",
            provider_id="n8n",
            provider_metadata={
                "server_id": "n8n",
                "transport": "rest",
                "timeout_seconds": 300,
                "real_mode": real_mode,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": ["execute_workflow"],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key", "n8n_api_key",
                ],
                "max_content_size": 51200,
            },
            tags=("automation", "n8n", "workflow", "bounded-execution"),
        )

        logger.debug(
            f"M13 n8n capability registered (n8n_execution, mode="
            f"{'real' if real_mode else 'mock'})"
        )
    async def _init_obsidian_git(self) -> None:
        """Register M13 Obsidian Git durability capability and adapter.

        Obsidian Git is a BOUNDED knowledge/durability resource. AI-OS owns semantic
        meaning; Git provides version-control durability. Default MOCK store with
        commit history; real mode gated by AIOS_REAL_INTEGRATION_ENABLED=1 +
        OBSIDIAN_VAULT_PATH.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping Obsidian Git init")
            return

        vault_path = (
            self._read_config_str("services.obsidian_git.vault_path", "")
            or os.environ.get("OBSIDIAN_VAULT_PATH")
        )
        real_mode = (
            self._read_config_bool("services.obsidian_git.real_mode_enabled", False)
            or (os.environ.get("AIOS_REAL_INTEGRATION_ENABLED") == "1")
        ) and bool(vault_path)
        # M14-T2: pass remote_url from config (explicit) with env fallback.
        # Remote URL is optional metadata; never logged with credentials.
        obsidian_git_remote_url = (
            self._read_config_str("services.obsidian_git.remote_url", "")
            or os.environ.get("OBSIDIAN_GIT_REMOTE_URL")
        )
        adapter = ObsidianGitAdapter(
            mcp_manager=self._mcp_manager,
            server_id="obsidian_git",
            vault_path=vault_path or None,
            timeout_seconds=30,
            real_mode_enabled=real_mode,
            security_manager=self._security_manager,
            remote_url=obsidian_git_remote_url or None,
        )
        self._obsidian_git_adapter = adapter

        self._capability_manager.register(
            capability_id="obsidian_git_knowledge",
            facade="knowledge",
            provider_id="obsidian_git",
            provider_metadata={
                "server_id": "obsidian_git",
                "transport": "filesystem",
                "timeout_seconds": 30,
                "vault_path": vault_path,
                "real_mode": real_mode,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": [
                    "create_knowledge", "update_knowledge", "get_knowledge",
                    "delete_knowledge", "verify_integrity",
                ],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key",
                ],
                "max_content_size": 102400,
            },
            tags=("knowledge", "obsidian", "git", "durability"),
        )

        logger.debug(
            f"M13 Obsidian Git capability registered (obsidian_git_knowledge, mode="
            f"{'real' if real_mode else 'mock'})"
        )
    async def _validate_terminal_contract(self) -> None:
        """M13 Phase 3 — validate four-terminal authority separation at boot.

        Asserts the invariants of ``M13_TERMINAL_HANDOFF_CONTRACT.md``:
          * Every bounded-resource adapter is hosted on T2 and holds only a
            bounded authority level (never AUTHORITATIVE).
          * The live M13 adapter instances expose ``terminal``/``authority_level``
            metadata consistent with the contract.

        This is fail-loud: a violation is logged at ERROR and surfaced as a
        recorded security issue so authority dilution cannot pass unnoticed.
        """
        contract = TerminalContract()
        violations = list(contract.check_all_adapters())
        # Validate the live M13 adapter instances' declared metadata too.
        for adapter in (
            getattr(self, "_supabase_adapter", None),
            getattr(self, "_supabase_test_adapter", None),
            getattr(self, "_n8n_adapter", None),
            getattr(self, "_obsidian_git_adapter", None),
        ):
            if adapter is None:
                continue
            declared = getattr(adapter, "authority_level", None)
            if declared is not None and declared not in (
                AuthorityLevel.BOUNDED_RESOURCE.value,
                AuthorityLevel.BOUNDED_EXECUTION.value,
            ):
                violation = validate_authority_preservation(
                    component=type(adapter).__module__ + "." + type(adapter).__name__,
                    terminal=TerminalId.T2_EXTERNAL,
                    claimed_level=AuthorityLevel(declared),
                )
                if violation is not None:
                    violations.append(violation)
        self._terminal_contract_violations = violations
        if self._terminal_contract_violations:
            detail = "; ".join(v.detail for v in self._terminal_contract_violations)
            logger.error(
                f"M13 terminal authority contract VIOLATION: {detail}"
            )
            if self._security_manager is not None:
                self._security_manager.record_violation(
                    severity="high",
                    description=f"Terminal authority contract violation: {detail}",
                    category="authority",
                )
        else:
            logger.debug(
                "M13 terminal authority contract validated: all bounded resources on T2"
            )

    async def _init_failure_recovery(self) -> None:
        """M13 Phase 5 — construct the bounded FailureRecoveryManager.

        Coordinates recovery for M13 external (bounded) resources under AI-OS
        authority. It reuses the canonical SecurityManager (gate-before-continue)
        and canonical EventBus (RECOVERY_ACTION_* audit events) — no duplicates.
        All recovery actions carry aios_owned provenance; no external system is
        ever elevated through recovery (spec Principle 1).
        """
        self._failure_recovery_manager = FailureRecoveryManager(
            security_manager=self._security_manager,
            event_bus=self._event_bus,
        )
        logger.debug("M13 FailureRecoveryManager constructed (AI-OS-authoritative)")

    async def _init_m10_autonomy(self) -> None:
        """Register M10 autonomy services (N1-N12).

        Initializes and registers all M10 autonomous services:
        - N1: Objective Generator
        - N2: Replan Detector
        - N3: Autonomous Judge
        - N4: Self-Prompting Autonomous Enhancement
        - N5: Learning Application Feedback Loop
        - N6: Capability Provenance Extensions
        - N7: State Verification
        - N8: Security ABAC Extensions
        - N9: Resource Manager Quotas
        - N10: Autonomy Override
        - N11: Audit Trail
        - N12: Autonomy Fallback
        """
        # Only proceed if M10 autonomy is enabled via config
        if not self._read_config_bool("services.autonomy.enabled", False):
            logger.debug("M10 autonomy disabled by config; skipping")
            return

        logger.info("Initializing M10 autonomy services...")

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
            get_autonomy_override,
            set_autonomy_override,
        )
        from aios.services.audit_trail import (
            AuditTrailService,
            AuditConfig,
            get_audit_trail,
            set_audit_trail,
        )
        from aios.services.autonomy_fallback import (
            AutonomyFallbackService,
            AutonomyFallbackConfig,
            get_autonomy_fallback,
            set_autonomy_fallback,
        )

        # N1: Objective Generator
        og_config = ObjectiveConfig(
            enabled=self._read_config_bool("services.objective_generator.enabled", False),
            min_interval_seconds=self._read_config_int("services.objective_generator.min_interval_seconds", 3600),
            max_concurrent_objectives=self._read_config_int("services.objective_generator.max_concurrent", 3),
        )
        objective_generator = AutonomousObjectiveGenerator(config=og_config)
        self.register_service(objective_generator)
        set_objective_generator(objective_generator)

        # N2: Replan Detector
        rd_config = ReplanDetectorConfig(
            enabled=self._read_config_bool("services.replan_detector.enabled", True),
            sensitivity=self._read_config_float("services.replan_detector.sensitivity", 0.7),
            min_workflows_for_analysis=self._read_config_int("services.replan_detector.min_workflows", 3),
            max_replan_depth=self._read_config_int("services.replan_detector.max_depth", 3),
            stagnation_window=self._read_config_int("services.replan_detector.window", 5),
        )
        replan_detector = AdaptiveReplanDetector(config=rd_config)
        self.register_service(replan_detector)
        set_replan_detector(replan_detector)

        # N3: Autonomous Judge
        from aios.core.council_manager import get_council_manager
        council = get_council_manager()
        aj_config = AutonomousJudgeConfig(
            mode=AutonomousJudgeMode(
                self._read_config_str("services.autonomous_judge.mode", "advisory_only")
            ),
            confidence_threshold=self._read_config_float("services.autonomous_judge.confidence_threshold", 0.75),
            require_learning_evidence=self._read_config_bool("services.autonomous_judge.require_learning_evidence", True),
            defer_to_council=self._read_config_bool("services.autonomous_judge.defer_to_council", True),
        )
        autonomous_judge = AutonomousFinalJudge(config=aj_config, council_manager=council)
        self.register_service(autonomous_judge)
        set_autonomous_judge(autonomous_judge)

        # N4: Self-Prompting Autonomous Enhancement
        sp_config = AutonomousSelfPromptingConfig(
            enabled=self._read_config_bool("services.self_prompting_autonomous.enabled", True),
            convergence_action=ConvergenceAction(
                self._read_config_str("services.self_prompting_autonomous.convergence_action", "escalate")
            ),
            max_convergence_cycles=self._read_config_int("services.self_prompting_autonomous.max_cycles", 3),
            forced_escalation_depth=self._read_config_int("services.self_prompting_autonomous.max_depth", 5),
        )
        self_prompting_auto = SelfPromptingAutonomousService(config=sp_config)
        self.register_service(self_prompting_auto)
        set_self_prompting_autonomous(self_prompting_auto)

        # N5: Learning Application Feedback Loop
        la_config = LearningApplyConfig(
            enabled=self._read_config_bool("services.learning_apply.enabled", False),
            auto_apply_on_objective=self._read_config_bool("services.learning_apply.auto_apply", True),
            confidence_threshold=self._read_config_float("services.learning_apply.confidence_threshold", 0.6),
        )
        learning_apply = LearningApplyService(config=la_config)
        self.register_service(learning_apply)
        set_learning_apply(learning_apply)

        # N6: Capability Provenance Extensions
        cp_config = CapabilityProvenanceConfig(
            enabled=self._read_config_bool("services.capability_provenance_ext.enabled", True),
            require_autonomous_signature=self._read_config_bool("services.capability_provenance_ext.require_signature", True),
        )
        capability_provenance_ext = CapabilityProvenanceExtensionService(config=cp_config)
        self.register_service(capability_provenance_ext)
        set_capability_provenance_ext(capability_provenance_ext)

        # N7: State Verification
        sv_config = StateVerificationConfig(
            enabled=self._read_config_bool("services.state_verification.enabled", True),
            verify_on_autonomous_action=self._read_config_bool("services.state_verification.verify_on_action", True),
        )
        state_verification = StateVerificationService(config=sv_config, state_manager=self._state_manager)
        self.register_service(state_verification)
        set_state_verification(state_verification)

        # N8: Security ABAC Extensions
        sa_config = SecurityAbacConfig(
            enabled=self._read_config_bool("services.security_abac_ext.enabled", True),
            require_autonomous_signature=self._read_config_bool("services.security_abac_ext.require_signature", True),
        )
        security_abac_ext = SecurityAbacExtensionService(config=sa_config, security_manager=self._security_manager)
        self.register_service(security_abac_ext)
        set_security_abac_ext(security_abac_ext)

        # N9: Resource Manager Quotas
        rq_config = AutonomousQuotaConfig(
            enabled=self._read_config_bool("services.resource_manager_quota.enabled", True),
            objective_generator_quota_pct=self._read_config_float("services.resource_manager_quota.og_pct", 0.05),
            replan_detector_quota_pct=self._read_config_float("services.resource_manager_quota.rd_pct", 0.03),
            autonomous_judge_quota_pct=self._read_config_float("services.resource_manager_quota.aj_pct", 0.02),
        )
        resource_manager_quota = ResourceManagerQuotaService(config=rq_config, resource_manager=self._resource_manager)
        self.register_service(resource_manager_quota)
        set_resource_manager_quota(resource_manager_quota)

        # N10: Autonomy Override
        ao_config = AutonomyOverrideConfig(
            allow_manual_override=self._read_config_bool("services.autonomy_override.allow_manual", True),
        )
        autonomy_override = AutonomyOverrideService(config=ao_config)
        self.register_service(autonomy_override)
        set_autonomy_override(autonomy_override)

        # N11: Audit Trail
        at_config = AuditConfig(
            enabled=self._read_config_bool("services.audit_trail.enabled", True),
            chain_hashes=self._read_config_bool("services.audit_trail.chain_hashes", True),
        )
        audit_trail = AuditTrailService(config=at_config)
        self.register_service(audit_trail)
        set_audit_trail(audit_trail)

        # N12: Autonomy Fallback
        af_config = AutonomyFallbackConfig(
            enabled=self._read_config_bool("services.autonomy_fallback.enabled", True),
            auto_fallback_on_security=self._read_config_bool("services.autonomy_fallback.on_security", True),
            auto_fallback_on_bounds=self._read_config_bool("services.autonomy_fallback.on_bounds", True),
            auto_fallback_on_instability=self._read_config_bool("services.autonomy_fallback.on_instability", True),
            require_manual_recovery=self._read_config_bool("services.autonomy_fallback.manual_recovery", True),
        )
        autonomy_fallback = AutonomyFallbackService(config=af_config)
        self.register_service(autonomy_fallback)
        set_autonomy_fallback(autonomy_fallback)

        logger.info("M10 autonomy services initialized and registered")

    async def _init_freellmapi(self) -> None:
        """Register FreeLLMAPI provider with ModelRouter (G1 — dev/test only).

        Registers the FreeLLMAPI model backend into the EXISTING ModelRouter
        (per INV-002: one model router). Gated by config/integrations.yaml mode
        and FREELLM_* environment variables (user resource).
        """
        # Use canonical ModelRouter singleton (INV-002).
        from aios.core.model_router import get_model_router
        model_router = get_model_router()
        if not model_router:
            logger.debug("ModelRouter not available; skipping FreeLLMAPI registration")
            return

        # Check integration framework mode (PHASE 2)
        try:
            from aios.integrations import load_integrations_config, IntegrationMode
            registry = load_integrations_config()
            if registry.get("freellmapi") and registry.get("freellmapi").mode != IntegrationMode.REAL:
                logger.debug("FreeLLMAPI mode is mock; skipping provider registration")
                return
            if not registry.get("freellmapi").real_allowed():
                logger.debug("FreeLLMAPI real connection not permitted (env gate / user resource absent)")
                return
        except Exception:
            # Framework unavailable — keep fail-closed: don't auto-register.
            logger.debug("Integration framework unavailable; FreeLLMAPI remains mock")
            return

        # Get env-based config (FREELLM_API_URL, FREELLM_API_KEY, etc.)
        from aios.adapters.freellmapi import (
            register_freellmapi_provider,
            get_freellmapi_config_from_env,
        )

        config = get_freellmapi_config_from_env()
        # Only register if the user actually provided endpoint credentials.
        if not config.base_url or config.base_url == "http://localhost:8080":
            logger.debug("FreeLLMAPI base_url not configured; skipping (user resource absent)")
            return

        register_freellmapi_provider(model_router, config)
        logger.info("FreeLLMAPI provider registered with ModelRouter (dev/test)")

    async def _init_agent_reach(self) -> None:
        """Register AgentReach communication capability and adapter.

        Registers the ``agent_reach_communication`` capability in
        CapabilityManager and wires the AgentReachAdapter for web/social content ingestion.
        """
        if not self._capability_manager:
            logger.debug("CapabilityManager not available; skipping AgentReach init")
            return

        # Check integration framework mode (PHASE 2)
        try:
            from aios.integrations import load_integrations_config, IntegrationMode
            registry = load_integrations_config()
            if registry.get("agent_reach") and registry.get("agent_reach").mode != IntegrationMode.REAL:
                logger.debug("AgentReach mode is mock; skipping capability registration")
                return
        except Exception:
            logger.debug("Integration framework unavailable; AgentReach remains mock")
            return

        from aios.adapters.agent_reach import AgentReachAdapter

        adapter = AgentReachAdapter(server_id="agent_reach")
        self._agent_reach_adapter = adapter

        # Register capability
        self._capability_manager.register(
            capability_id="agent_reach_communication",
            facade="communication",
            provider_id="agent_reach",
            provider_metadata={
                "server_id": "agent_reach",
                "transport": "stdio",
                "timeout_seconds": 30,
                "auto_reconnect": True,
            },
            security_context={
                "requires_validation": True,
                "allowed_operations": [
                    "web_search", "social_fetch", "news_fetch",
                ],
                "sensitive_keys": [
                    "password", "token", "secret", "api_key",
                    "authorization", "credential", "private_key",
                ],
                "max_content_size": 10240,
            },
            tags=("communication", "agent-reach", "web", "social", "news"),
        )

        logger.debug("AgentReach capability registered (agent_reach_communication)")

    async def _init_integration_status(self) -> None:
        """Initialize Integration Status Service for dashboard backend.

        Registers the IntegrationStatusService as an engineering service to provide
        programmatic access to integration onboarding status for frontend dashboards.
        """
        if not self._service_registry:
            logger.debug("ServiceRegistry not available; skipping Integration Status Service init")
            return

        try:
            from aios.services.integration_status import IntegrationStatusService, create_integration_status_service
        except ImportError:
            logger.debug("IntegrationStatusService not available; skipping")
            return

        # Create and register the service
        service = await create_integration_status_service(
            config={"health_check_interval_seconds": 60},
            event_bus=self._event_bus,
        )

        # Register with canonical ServiceRegistry as engineering service
        from aios.core.service_registry import ServiceType
        await self._service_registry.register(
            service,
            service_id="engineering.integration_status",
            service_type=ServiceType.ENGINEERING,
            metadata={"version": "1.0.0", "description": "Integration onboarding status for dashboard"},
        )

        self._integration_status_service = service
        logger.debug("Integration Status Service registered (engineering.integration_status)")

    async def _init_dashboard_backend(self) -> None:
        """M13 Phase 7 — register the non-authoritative dashboard backend service.

        Terminal 2 authors this integration so Terminal 3 can host/operate the
        dashboard UI. The service is BOUNDED: it reads AI-OS state through canonical
        getters and forwards user actions to AI-OS for authorization + bounded
        execution. It holds NO governance, verification, or decision authority.
        """
        if not self._service_registry:
            logger.debug("ServiceRegistry not available; skipping Dashboard backend init")
            return

        try:
            from aios.services.dashboard_service import (
                DashboardService,
                create_dashboard_service,
            )
        except ImportError:
            logger.debug("DashboardService not available; skipping")
            return

        service = await create_dashboard_service(
            kernel=self,
            event_bus=self._event_bus,
            security_manager=self._security_manager,
            config={"page_refresh_seconds": 5},
        )

        # Register as engineering service (non-authoritative, Terminal 3 hosts UI)
        from aios.core.service_registry import ServiceType

        await self._service_registry.register(
            service,
            service_id="engineering.dashboard_backend",
            service_type=ServiceType.ENGINEERING,
            metadata={"version": "1.0.0", "description": "Non-authoritative dashboard backend over AI-OS"},
        )

        self._dashboard_service = service
        logger.debug("M13 Dashboard backend registered (engineering.dashboard_backend)")

    async def _init_project_service(self) -> None:
        """M14-T2 — register the bounded Project Workspace service.

        Terminal 2 authors this integration (PAGE 1 "Project Workspace") so
        Terminal 3 can host the project-based dashboard. The service is BOUNDED:
        it holds NO governance/decision/security/execution authority. Project
        lifecycle transitions and the Notion handoff are delegated to the kernel's
        authoritative components; the dashboard only forwards user intent through
        the SecurityManager gate (fail-closed).

        This wiring is additive and does NOT modify SecurityManager, the terminal
        contract, or any M7–M14 verified functionality.
        """
        if not self._service_registry or not self._event_bus:
            logger.debug("Core components not available; skipping Project Service init")
            return

        try:
            from aios.services.project_service import (
                ProjectService,
                create_project_service,
            )
        except ImportError:
            logger.debug("ProjectService not available; skipping")
            return

        service = await create_project_service(
            kernel=self,
            event_bus=self._event_bus,
            security_manager=self._security_manager,
            config={},
        )

        from aios.core.service_registry import ServiceType

        try:
            await self._service_registry.register(
                service,
                service_id="engineering.project_workspace",
                service_type=ServiceType.ENGINEERING,
                metadata={
                    "version": "1.0.0",
                    "description": "Bounded Project Workspace service (non-authoritative, AI-OS-owned lifecycle)",
                },
            )
        except Exception as exc:  # noqa: BLE001 — registration is best-effort
            logger.debug("ProjectService registry registration skipped: %s", exc)

        self._project_service = service
        # Give the DashboardService a direct handle so get_project_workspace() can
        # reach it without depending on full kernel wiring in every test context.
        if self._dashboard_service is not None:
            self._dashboard_service._project_service = service
        logger.debug("M14-T2 Project Workspace service registered (engineering.project_workspace)")

    async def _init_self_loop(self) -> None:
        """Initialize M13 SelfLoopEngine — single authoritative autonomous decision-making engine.

        Creates the SelfLoopEngine with all core component dependencies injected,
        wiring it into the kernel's canonical infrastructure. The engine implements
        the 19-phase canonical self-loop lifecycle as specified in
        M13_SELF_LOOP_INTEGRATION_SPEC.md.
        """
        if not self._service_registry or not self._event_bus:
            logger.debug("Core components not available; skipping SelfLoopEngine init")
            return

        # Configure from kernel config
        max_cycles = self._read_config_int("services.self_loop.max_cycles", 3)
        max_depth = self._read_config_int("services.self_loop.max_depth", 5)
        cycle_timeout = self._read_config_int("services.self_loop.cycle_timeout_seconds", 3600)

        # Create engine with all canonical dependencies
        self._self_loop_engine = SelfLoopEngine(
            kernel=self,
            event_bus=self._event_bus,
            service_registry=self._service_registry,
            config_manager=self._configuration,
            logger=self._structured_logger,
            security_manager=self._security_manager,
            capability_manager=self._capability_manager,
            state_manager=self._state_manager,
            workflow_manager=self._workflow_manager,
            resource_manager=self._resource_manager,
            health_manager=self._health_manager,
            observability_manager=self._observability_manager,
            memory_manager=self.memory_manager,
        )

        # Apply configuration
        self._self_loop_engine._max_cycles = max_cycles
        self._self_loop_engine._cycle_timeout_seconds = cycle_timeout

        # Enable mock mode by default (ADR-006)
        mock_mode = not self._read_config_bool("services.self_loop.real_mode_enabled", False)
        self._self_loop_engine.set_mock_mode(mock_mode)

        logger.debug(f"M13 SelfLoopEngine initialized (mock_mode={mock_mode}, max_cycles={max_cycles})")

    async def _init_self_prompting(self) -> None:
        """Initialize M13 SelfPromptGenerator — authoritative internal directive generation.

        Creates the SelfPromptGenerator with all core component dependencies injected,
        wiring it into the kernel's canonical infrastructure. The generator synthesizes
        lifecycle context into validated SelfPrompt directives for bounded execution.
        """
        if not self._service_registry or not self._event_bus:
            logger.debug("Core components not available; skipping SelfPromptGenerator init")
            return

        # Configure from kernel config (self-prompting config section)
        max_cycles = self._read_config_int("services.self_prompting.max_convergence_cycles", 3)
        max_depth = self._read_config_int("services.self_prompting.max_depth", 5)
        convergence_action = self._read_config_str("services.self_prompting.convergence_action", "escalate")

        # Create generator with all canonical dependencies
        self._self_prompt_generator = SelfPromptGenerator(
            kernel=self,
            event_bus=self._event_bus,
            config_manager=self._configuration,
            logger=self._structured_logger,
            security_manager=self._security_manager,
            capability_manager=self._capability_manager,
            state_manager=self._state_manager,
            workflow_manager=self._workflow_manager,
        )

        # Apply configuration
        self._self_prompt_generator.configure(
            max_cycles=max_cycles,
            max_depth=max_depth,
            convergence_action=convergence_action,
        )

        # Wire the generator into the self-loop engine
        if self._self_loop_engine:
            self._self_loop_engine._prompt_generator = self._self_prompt_generator

        logger.debug(f"M13 SelfPromptGenerator initialized (max_cycles={max_cycles}, convergence_action={convergence_action})")

    def _read_config_float(self, path: str, default: float) -> float:
        """Read a float config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return float(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    def _read_config_int(self, path: str, default: int) -> int:
        """Read an int config value from the frozen ConfigurationManager (C3)."""
        cm = self._configuration
        if cm is None or not hasattr(cm, "get"):
            return default
        try:
            val = cm.get(path, default=default)
            return int(val) if isinstance(val, (int, float)) else default
        except Exception:  # noqa: BLE001
            return default

    async def _start_services(self) -> None:
        """Start all registered services."""
        logger.debug("Starting services...")

        # Start core services first (canonical managers). NOTE: StateManager is
        # NOT started here — as a Phase-2 Core Manager (Task 10) its lifecycle is
        # owned by LifecycleManager (initialized during Phase 2, shut down in
        # reverse phase order). It is thus excluded from the engineering-service
        # startup path per the Core Manager topology (Part 4 §4.2.3).
        # Start core services first (canonical managers). NOTE: Lifecycle-owned
        # Core Managers (StateManager, StorageManager, HealthManager,
        # ResourceManager, SecurityManager, CapabilityManager, WorkflowManager,
        # ObservabilityManager) are NOT started here — as Phase-owned Core
        # Managers their lifecycle is owned by LifecycleManager (initialized
        # during their phase, shut down in reverse phase order). They are thus
        # excluded from the engineering-service startup path per the Core Manager
        # topology (Part 4 §4.2.3). ResourceManager's background cleanup task is
        # an exception kept for backward compatibility.
        services = [
            ("resource_manager", self._start_resource_manager),
        ]

        for name, start_func in services:
            try:
                await start_func()
                self._services[name] = ServiceStatus(
                    name=name,
                    started=True,
                    started_at=datetime.utcnow(),
                )
                logger.debug(f"Started service: {name}")
            except Exception as e:
                logger.error(f"Failed to start service {name}: {e}")
                self._services[name] = ServiceStatus(
                    name=name,
                    started=False,
                    healthy=False,
                    last_error=str(e),
                )

        # Start Engineering Services via canonical C2 ServiceRegistry.
        #
        # Engineering services are registered under the reserved ``engineering.``
        # namespace prefix (Part 3 §3.4.8, INV-SR-NS-001 / INV-SR-NS-002). Core
        # Components / Core Managers are ALSO visible through the canonical
        # registry (they share the ``ServiceType.ENGINEERING`` classification
        # envelope so they remain discoverable there), but their lifecycle is
        # owned by the dedicated lifecycle/phase mechanism — NOT by the
        # engineering service start/stop loops. We therefore filter the
        # ENGINEERING-typed listing by the kernel's own canonical service-id
        # convention (``engineering.<name>``, see ``register_service``): an entry
        # that is not present under that id (e.g. ``core.lifecycle``) is a Core
        # Component / Core Manager and is left to its dedicated lifecycle path.
        if self._service_registry:
            from aios.core.service_registry import ServiceType

            engineering_services = [
                svc
                for svc in self._service_registry.get_services_by_type(
                    ServiceType.ENGINEERING
                )
                if self._service_registry.get_registration(
                    f"engineering.{svc.name}"
                )
                is not None
            ]

            # Start each engineering service
            for svc in engineering_services:
                try:
                    await svc.start()
                    self._services[svc.name] = ServiceStatus(
                        name=svc.name,
                        started=True,
                        healthy=True,
                        started_at=datetime.utcnow(),
                    )
                    # Mark as RUNNING in canonical registry
                    await self._service_registry.mark_service_running(f"engineering.{svc.name}")
                    logger.debug(f"Started Engineering Service: {svc.name}")
                except Exception as e:
                    self._services[svc.name] = ServiceStatus(
                        name=svc.name,
                        started=False,
                        healthy=False,
                        last_error=str(e),
                    )
                    logger.error(f"Failed to start Engineering Service: {svc.name}: {e}")

    async def _stop_services(self) -> None:
        """Stop core services in reverse order."""
        logger.debug("Stopping core services...")

        stop_order = [
            "resource_manager",
        ]

        for name in stop_order:
            if name in self._services and self._services[name].started:
                try:
                    stop_func = getattr(self, f"_stop_{name}", None)
                    if stop_func:
                        await stop_func()
                    self._services[name].started = False
                    logger.debug(f"Stopped service: {name}")
                except Exception as e:
                    logger.error(f"Error stopping service {name}: {e}")

    async def _stop_engineering_services(self) -> None:
        """Stop all engineering services via canonical registry.

        Symmetric to :meth:`_start_services`: only entries with the canonical
        ``engineering.`` namespace prefix (``Part 3 §3.4.8``,
        ``INV-SR-NS-001``) are stopped — Core Components / Core Managers are
        NOT touched here. Lifecycle for those is owned by the dedicated
        lifecycle/phase mechanism.
        """
        logger.debug("Stopping engineering services...")
        if self._service_registry:
            from aios.core.service_registry import ServiceType

            # Same discriminator as ``_start_services``: only entries present
            # under the canonical ``engineering.<name>`` service-id are stopped.
            # Core Components / Core Managers (e.g. ``core.lifecycle``) are not
            # touched here — their lifecycle is owned by the dedicated
            # lifecycle/phase mechanism.
            engineering_services = [
                svc
                for svc in self._service_registry.get_services_by_type(
                    ServiceType.ENGINEERING
                )
                if self._service_registry.get_registration(
                    f"engineering.{svc.name}"
                )
                is not None
            ]

            for svc in engineering_services:
                try:
                    await svc.stop()
                    # Mark as SHUTDOWN in canonical registry
                    await self._service_registry.mark_service_shutdown(f"engineering.{svc.name}")
                    logger.debug(f"Stopped Engineering Service: {svc.name}")
                except Exception as e:
                    logger.error(f"Error stopping engineering service {svc.name}: {e}")

    # Service start/stop methods
    async def _start_resource_manager(self) -> None:
        self._resource_manager.start_cleanup_task()

    async def _stop_resource_manager(self) -> None:
        self._resource_manager.stop_cleanup_task()

    def get_service_status(self) -> dict[str, Any]:
        """Get status of all services."""
        return {
            name: {
                "started": status.started,
                "healthy": status.healthy,
                "started_at": status.started_at.isoformat() if status.started_at else None,
                "last_error": status.last_error,
            }
            for name, status in self._services.items()
       }

    def get_stats(self) -> dict[str, Any]:
        """Get kernel statistics."""
        statuses = self.get_service_status()
        total_services = len(statuses)
        healthy_services = sum(1 for s in statuses.values() if s.get("started") and s.get("healthy"))
        uptime = (
            (datetime.utcnow() - self._start_time).total_seconds()
            if self._start_time
            else 0
       )
        return {
            "kernel": {
                "name": self._config.name,
                "version": self._config.version,
                "running": self._running,
                "start_time": self._start_time.isoformat() if self._start_time else None,
                "uptime_seconds": uptime,
                "services": total_services,
                "healthy_services": healthy_services,
            },
            "running": self._running,
            "start_time": self._start_time.isoformat() if self._start_time else None,
            "uptime_seconds": uptime,
            "services": statuses,
            "service_count": total_services,
            "healthy_services": healthy_services,
            "event_bus": self._event_bus.get_stats() if self._event_bus else None,
            "service_registry": self._service_registry.get_stats() if self._service_registry else None,
            "resource_manager": (
                self._resource_manager.get_stats() if self._resource_manager else None
            ),
       }


def _run_sync(coro: Any) -> Any:
    """Run a coroutine to completion from a synchronous call site.

    The canonical Core Components (EventBus, ServiceRegistry, ...) expose async
    lifecycle/registration methods (Core Component pattern). The kernel's public
    ``register_service`` is synchronous (pre-Task-9 contract), so the canonical
    coroutine is bridged here — same approach as the Task 6 legacy compatibility
    layer (``aios/services/registry.py:_run_sync``). If a loop is already running
    in this thread (e.g. an async test), the coroutine is driven on a dedicated
    thread with its own loop so it still completes synchronously from the
    caller's perspective.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is None:
        return asyncio.run(coro)
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()


# Global kernel instance
_global_kernel: HermesKernel | None = None


def get_kernel() -> HermesKernel | None:
    """Get the global kernel instance."""
    return _global_kernel


def set_kernel(kernel: HermesKernel) -> None:
    """Set the global kernel instance."""
    global _global_kernel
    _global_kernel = kernel


async def create_kernel(
    config: KernelConfig | None = None,
    app_config: AppConfig | None = None,
) -> HermesKernel:
    """Create a kernel instance."""
    return HermesKernel(config=config, app_config=app_config)


__all__ = [
    "HermesKernel",
    "KernelConfig",
    "ServiceStatus",
    "get_kernel",
    "set_kernel",
    "create_kernel",
]