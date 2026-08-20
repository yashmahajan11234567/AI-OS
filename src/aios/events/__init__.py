"""
Event System for AI-OS Hermes Kernel.

This module provides the core event-driven architecture for AI-OS.
All services communicate through events published to the Event Bus.
"""

from aios.events.base import Event, EventType, create_event
from aios.events.bus import EventBus, get_event_bus, set_event_bus
from aios.events.core.bus import (
    EventBus as CoreEventBus,
    EventBusConfig,
    get_core_event_bus,
    reset_core_event_bus_singleton,
)
from aios.events.handlers import EventHandler, AsyncEventHandler, handler_for, async_handler_for
from aios.events.types import (
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
    TestGenerated,
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
    # Service Lifecycle Events
    ServiceRegistered,
    ServiceStarted,
    ServiceStopped,
    ServiceHealthy,
    ServiceUnhealthy,
)

__all__ = [
    # Base
    "Event",
    "EventType",
    "create_event",
    "EventBus",
    "get_event_bus",
    "set_event_bus",
    # Canonical Core EventBus (C1, Task 5)
    "CoreEventBus",
    "EventBusConfig",
    "get_core_event_bus",
    "reset_core_event_bus_singleton",
    "EventHandler",
    "AsyncEventHandler",
    "handler_for",
    "async_handler_for",
    # Core Kernel
    "KernelStarted",
    "KernelStopped",
    "KernelError",
    # Task/Workflow
    "TaskCreated",
    "TaskStarted",
    "TaskCompleted",
    "TaskFailed",
    "TaskRetryRequested",
    "TaskCancelled",
    "WorkflowCreated",
    "WorkflowStarted",
    "WorkflowCompleted",
    "WorkflowFailed",
    "WorkflowPaused",
    "WorkflowResumed",
    # Planning
    "PlanningRequested",
    "PlanningCompleted",
    "PlanningFailed",
    "PlanApproved",
    "PlanRejected",
    # Coding
    "CodingStarted",
    "CodingCompleted",
    "CodingFailed",
    "CodeGenerated",
    "CodeReviewRequested",
    # Review
    "ReviewStarted",
    "ReviewCompleted",
    "ReviewFailed",
    "ReviewApproved",
    "ReviewRejected",
    # Testing
    "TestingStarted",
    "TestingCompleted",
    "TestingFailed",
    "TestsPassed",
    "TestsFailed",
    "TestGenerated",
    "SecurityIssueFound",
    "PerformanceIssueFound",
    # Deployment
    "DeploymentRequested",
    "DeploymentStarted",
    "DeploymentCompleted",
    "DeploymentFailed",
    "DeploymentRolledBack",
    # Operations
    "ProductionIncident",
    "MetricsAlert",
    "LogAnomalyDetected",
    "UserFeedbackReceived",
    # Memory
    "MemoryStored",
    "MemoryRetrieved",
    "MemoryUpdated",
    "MemoryConsolidated",
    # Skill
    "SkillLoaded",
    "SkillUnloaded",
    "SkillExecuted",
    "SkillFailed",
    # MCP
    "MCPServerConnected",
    "MCPServerDisconnected",
    "MCPToolCalled",
    "MCPToolResult",
    # Council
    "CouncilConvened",
    "CouncilDeliberated",
    "CouncilDecided",
    "CouncilDissented",
    # AI Agency
    "SecurityAuditRequested",
    "SecurityAuditCompleted",
    "PerformanceAuditRequested",
    "PerformanceAuditCompleted",
    "ChaosExperimentRequested",
    "ChaosExperimentCompleted",
    "AccessibilityAuditRequested",
    "AccessibilityAuditCompleted",
    "DocumentationAuditRequested",
    "DocumentationAuditCompleted",
    "ConcurrencyAuditRequested",
    "ConcurrencyAuditCompleted",
    "BugHuntRequested",
    "BugHuntCompleted",
    "ArchitectureValidationRequested",
    "ArchitectureValidationCompleted",
    "FinalJudgmentRequested",
    "FinalJudgmentCompleted",
    # Checkpoint
    "CheckpointCreated",
    "CheckpointRestored",
    "CheckpointDeleted",
    # Retry
    "RetryBudgetExhausted",
    "RetryScheduled",
    "RetryExecuted",
    # Root Cause
    "RootCauseAnalyzed",
    "RootCauseResolved",
    "FailureClassified",
    # Learning
    "LearningCaptured",
    "PatternExtracted",
    "KnowledgeUpdated",
    # State
    "StateTransitioned",
    "StateCheckpointed",
    "StateRestored",
    # Service Events
    "ServiceRegistered",
    "ServiceStarted",
    "ServiceStopped",
    "ServiceHealthy",
    "ServiceUnhealthy",
]