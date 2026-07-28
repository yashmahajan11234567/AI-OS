"""
AI-OS - A modular AI operating system for research, planning, execution, and memory.

This package provides the core infrastructure for the AI-OS event-driven architecture.
"""

from aios.__version__ import __version__
from aios.core import (
    # Kernel
    HermesKernel,
    KernelConfig,
    ServiceStatus,
    get_kernel,
    set_kernel,
    create_kernel,
    run_kernel,
    stop_kernel,
    is_running,
    execute_with_kernel,
    # State
    StateManager,
    StateScope,
    StateSnapshot,
    get_state_manager,
    set_state_manager,
    # Workflow
    WorkflowManager,
    WorkflowDefinition,
    WorkflowStep,
    WorkflowStatus,
    get_workflow_manager,
    set_workflow_manager,
    # Checkpoint
    CheckpointManager,
    Checkpoint,
    get_checkpoint_manager,
    set_checkpoint_manager,
    # Retry
    RetryManager,
    RetryPolicy,
    RetryStrategy,
    RetryBudget,
    # Root Cause
    RootCauseAnalyzer,
    FailureContext,
    RootCauseAnalysis,
    FailureCategory,
    FailureSeverity,
    RecoveryAction,
    get_root_cause_analyzer,
    set_root_cause_analyzer,
    # Logger
    StructuredLogger,
    BoundLogger,
    LogContext,
    # Model Router
    ModelRouter,
    ModelConfig,
    ModelRequest,
    ModelResponse,
    ModelProvider,
    ModelCapability,
    get_model_router,
    set_model_router,
    # Resource Manager
    ResourceManager,
    ResourceType,
    ResourceLimit,
    ResourceAllocation,
    ResourceUsage,
    ResourceExhausted,
    get_resource_manager,
    set_resource_manager,
    # Memory
    MemoryManager,
    MemoryType,
    MemoryEntry,
    MemoryBackend,
    FileMemoryBackend,
    InMemoryBackend,
    get_memory_manager,
    set_memory_manager,
    # Skill Manager
    SkillManager,
    Skill,
    SkillExecution,
    get_skill_manager,
    set_skill_manager,
    # MCP Manager
    MCPManager,
    MCPServerConfig,
    MCPTool,
    MCPServerStatus,
    MCPTransport,
    get_mcp_manager,
    set_mcp_manager,
    # AI Agency
    AIAgencyService,
    BaseAgency,
    SecurityAgency,
    PerformanceAgency,
    ChaosAgency,
    AccessibilityAgency,
    DocumentationAgency,
    ConcurrencyAgency,
    BugHunterAgency,
    ArchitectureAgency,
    FinalJudgeAgency,
    AgencyRequest,
    AgencyResponse,
    AgencyType,
    Verdict,
    get_ai_agency_service,
    set_ai_agency_service,
    # Council
    CouncilManager,
    CouncilMember,
    CouncilProposal,
    CouncilVote,
    CouncilDecision,
    CouncilSession,
    CouncilRole,
    ConsensusAlgorithm,
    get_council_manager,
    set_council_manager,
)

# Config exports
from aios.config import (
    AppConfig,
    WorkspaceConfig,
    LogsConfig,
    Environment,
    load_config,
    validate_config,
    ConfigLoadError,
    ConfigValidationError,
)

# Events exports
from aios.events import (
    Event,
    EventType,
    EventBus,
    EventHandler,
    AsyncEventHandler,
    get_event_bus,
    set_event_bus,
    # Core Kernel Events
    KernelStarted,
    KernelStopped,
    KernelError,
    # Task/Workflow Events
    TaskCreated,
    TaskStarted,
    TaskCompleted,
    TaskFailed,
    TaskRetryRequested,
    TaskCancelled,
    WorkflowCreated,
    WorkflowStarted,
    WorkflowCompleted,
    WorkflowFailed,
    WorkflowPaused,
    WorkflowResumed,
    # Planning Events
    PlanningRequested,
    PlanningCompleted,
    PlanningFailed,
    PlanApproved,
    PlanRejected,
    # Coding Events
    CodingStarted,
    CodingCompleted,
    CodingFailed,
    CodeGenerated,
    CodeReviewRequested,
    # Review Events
    ReviewStarted,
    ReviewCompleted,
    ReviewFailed,
    ReviewApproved,
    ReviewRejected,
    # Testing Events
    TestingStarted,
    TestingCompleted,
    TestingFailed,
    TestsPassed,
    TestsFailed,
    SecurityIssueFound,
    PerformanceIssueFound,
    # Deployment Events
    DeploymentRequested,
    DeploymentStarted,
    DeploymentCompleted,
    DeploymentFailed,
    DeploymentRolledBack,
    # Operations Events
    ProductionIncident,
    MetricsAlert,
    LogAnomalyDetected,
    UserFeedbackReceived,
    # Memory Events
    MemoryStored,
    MemoryRetrieved,
    MemoryUpdated,
    MemoryConsolidated,
    # Skill Events
    SkillLoaded,
    SkillUnloaded,
    SkillExecuted,
    SkillFailed,
    # MCP Events
    MCPServerConnected,
    MCPServerDisconnected,
    MCPToolCalled,
    MCPToolResult,
    # Council Events
    CouncilConvened,
    CouncilDeliberated,
    CouncilDecided,
    CouncilDissented,
    # AI Agency Events
    SecurityAuditRequested,
    SecurityAuditCompleted,
    PerformanceAuditRequested,
    PerformanceAuditCompleted,
    ChaosExperimentRequested,
    ChaosExperimentCompleted,
    AccessibilityAuditRequested,
    AccessibilityAuditCompleted,
    DocumentationAuditRequested,
    DocumentationAuditCompleted,
    ConcurrencyAuditRequested,
    ConcurrencyAuditCompleted,
    BugHuntRequested,
    BugHuntCompleted,
    ArchitectureValidationRequested,
    ArchitectureValidationCompleted,
    FinalJudgmentRequested,
    FinalJudgmentCompleted,
    # Checkpoint Events
    CheckpointCreated,
    CheckpointRestored,
    CheckpointDeleted,
    # Retry Events
    RetryBudgetExhausted,
    RetryScheduled,
    RetryExecuted,
    # Root Cause Events
    RootCauseAnalyzed,
    RootCauseResolved,
    FailureClassified,
    # Learning Events
    LearningCaptured,
    PatternExtracted,
    KnowledgeUpdated,
    # State Events
    StateTransitioned,
    StateCheckpointed,
    StateRestored,
)

__version__ = "0.2.0"

__all__ = [
    "__version__",
]