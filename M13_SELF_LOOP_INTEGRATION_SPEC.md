# M13 Self-Loop Integration Specification

## Overview

This document defines the complete self-loop architecture for AI-OS M13, specifying how AI-OS maintains its authoritative autonomous/self-loop while integrating all external systems as bounded resources. The self-loop remains the single source of truth for AI-OS decision-making, governance, verification, and judgment.

## Role and Authority Model

### Exact Role
The AI-OS self-loop serves as the **single authoritative autonomous decision-making engine** that:
- Maintains continuous autonomous operation through bounded execution cycles
- Owns all semantic meaning of AI-OS state, decisions, and learning
- Provides final judgment, authoritative judgment on all AI-OS operations
- Controls the complete AI-OS lifecycle from user intent to next self-prompt
- Integrates external systems strictly as bounded resources under its authority

The self-loop does NOT:
- Delegate governance, verification, or judgment authority to external systems
- Allow external systems to initiate or control AI-OS lifecycle phases
- Permit external systems to make decisions that affect AI-OS autonomous operation
- Share authoritative state with external systems
- Rely on external systems for core AI-OS functionality

### AI-OS Authority over Self-Loop
AI-OS **is** the self-loop - there is no separation. The self-loop represents:
- The complete, integrated AI-OS system operating in continuous autonomous mode
- The single source of truth for all AI-OS state, decisions, and provenance
- The authoritative generator of self-prompts that drive the lifecycle
- The final arbiter of whether AI-OS operations meet requirements and standards
- The entity that learns, adapts, and evolves through bounded execution cycles

### Self-Loop Limitations (Clarifying AI-OS Boundaries)
The self-loop is constrained by:
- Bounded execution phases that prevent runaway computation
- Resource quotas that enforce reasonable computational limits
- Security policies that protect against malicious inputs and exploits
- Verification requirements that mandate evidence-based validation
- Testing protocols that ensure correctness before proceeding
- Review processes that provide multi-perspective evaluation
- Final judgment that confirms completion and correctness

These limitations are **AI-OS self-imposed bounds** that enhance reliability and safety, not external constraints that diminish authority.

## Self-Loop Architecture

### Core Self-Loop Phases
The AI-OS self-loop operates through these canonical phases:
```
USER_INTENT → PLANNING → RESEARCH → REQUIREMENTS → COUNCILS/REVIEWS → PLAN → 
TASKS → SELF-PROMPT → BOUNDED_EXECUTION → TEST → REVIEW → VERIFICATION → 
FINAL_JUDGMENT → DECISION → EVIDENCE → LEARNING → MEMORY/KNOWLEDGE → 
PERSISTENCE → NEXT_SELF_PROMPT → [REPEAT]
```

Each phase has clearly defined responsibilities and outputs that feed into the next phase.

### Phase Responsibilities

#### USER_INTENT
- Captures and clarifies user goals and objectives
- Translates vague requests into actionable AI-OS understandable intent
- Establishes success criteria and completion conditions
- Determines if request falls within AI-OS capabilities and authority

#### PLANNING
- Explores solution space and identifies viable approaches
- Evaluates architectural options and technology choices
- Creates implementation plans with clear milestones and deliverables
- Estimates effort, resources, and timelines
- Identifies risks and mitigation strategies

#### RESEARCH
- Gathers information from internal and external sources
- Investigates existing solutions, patterns, and best practices
- Validates assumptions and technical feasibility
- Builds knowledge base for informed decision-making
- Documents findings and sources for provenance tracking

#### REQUIREMENTS
- Translates research findings into concrete, measurable requirements
- Defines functional and non-functional specifications
- Establishes acceptance criteria and test conditions
- Documents constraints, dependencies, and assumptions
- Creates traceability between intent and implementation

#### COUNCILS/REVIEWS
- Provides multi-perspective evaluation of plans and requirements
- Offers specialized expertise (security, performance, usability, etc.)
- Identifies gaps, inconsistencies, and improvement opportunities
- Ensures alignment with AI-OS principles and architectural guidelines
- Documents review findings and recommendations

#### PLAN
- Synthesizes planning, research, requirements, and council feedback
- Creates detailed, actionable implementation roadmap
- Defines specific tasks, dependencies, and resource allocations
- Establishes clear completion criteria for each task
- Serves as the authoritative guide for implementation

#### TASKS
- Breaks down plan into executable work units
- Assigns tasks to appropriate agents, services, or manual effort
- Tracks task progress, dependencies, and completion status
- Manages task blocking and unblocking based on dependencies
- Provides visibility into implementation progress

#### SELF-PROMPT
- Generates the authoritative prompt that directs the next bounded execution
- Encapsulates current AI-OS state, goals, and execution context
- Incorporates learning, evidence, and knowledge from previous cycles
- Defines what AI-OS should attempt to accomplish in bounded execution
- Sets clear success/failure criteria for the execution attempt

#### BOUNDED_EXECUTION
- Executes the self-prompt within strict resource and time bounds
- Utilizes AI-OS agents, services, and external bounded resources
- Produces execution results, artifacts, and evidence
- Respects execution limits (time, memory, API calls, etc.)
- Handles execution failures and degradation gracefully

#### TEST
- Validates execution results against requirements and success criteria
- Executes automated tests to verify correctness and completeness
- Identifies defects, gaps, and issues requiring attention
- Determines if execution meets minimum quality thresholds
- Produces test evidence for review and verification

#### REVIEW
- Provides multi-perspective evaluation of execution results
- Applies specialized lenses (correctness, security, performance, etc.)
- Evaluates test evidence and execution artifacts
- Identifies improvement opportunities and required changes
- Documents review findings and recommendations

#### VERIFICATION
- Confirms that identified issues have been resolved
- Validates that execution meets all specified requirements
- Ensures that regression has not been introduced
- Confirms readiness for final judgment
- Produces verification evidence

#### FINAL_JUDGMENT
- Makes authoritative determination of completion and correctness
- Evaluates all evidence: test, review, verification, execution
- Determines if AI-OS has successfully accomplished the self-prompt goal
- Issues final, binding decision: PASS or FAIL
- Provides justification for the judgment decision

#### DECISION
- Determines next steps based on final judgment outcome
- For PASS: Proceed to evidence collection and learning
- For FAIL: Initiate recovery, retry, or escalation procedures
- Updates AI-OS state based on judgment outcome
- Maintains decision audit trail for provenance tracking

#### EVIDENCE
- Collects and preserves execution artifacts, test results, and reviews
- Maintains complete provenance chains for all evidence items
- Ensures evidence is stored durably and accessibly
- Prepares evidence for learning and knowledge extraction
- Documents evidence context and significance

#### LEARNING
- Extracts insights, patterns, and knowledge from evidence
- Updates AI-OS knowledge base with validated learning
- Identifies improvement opportunities for future iterations
- Documents learning outcomes and knowledge updates
- Prepares learning for memory/knowledge persistence

#### MEMORY/KNOWLEDGE
- Persists learning outcomes as durable knowledge artifacts
- Integrates new learning with existing AI-OS knowledge base
- Ensures knowledge is stored with appropriate semantics and provenance
- Makes knowledge available for future reference and decision-making
- Maintains knowledge organization and accessibility

#### PERSISTENCE
- Stores complete AI-OS state for recovery and continuity
- Persists state checkpoints, configurations, and operational data
- Ensures durability guarantees through appropriate storage mechanisms
- Enables system restart from known good state
- Provides backup and disaster recovery capabilities

#### NEXT_SELF_PROMPT
- Generates the next authoritative prompt based on complete cycle output
- Incorporates judgment outcome, evidence, learning, and persistent state
- Represents AI-OS's evolved understanding and next objective
- Maintains continuity and progression in autonomous operation
- Begins the next self-loop iteration

## Self-Loop Properties

### Authoritative Properties
The self-loop maintains these authoritative properties:
1. **Single Source of Truth**: Only one canonical version of AI-OS state exists
2. **Decision Finality**: FINAL_JUDGMENT decisions are binding and authoritative
3. **Semantic Ownership**: AI-OS owns the meaning of all state, decisions, and learning
4. **Execution Control**: AI-OS initiates and controls all bounded execution
5. **Learning Authority**: AI-OS determines what constitutes valid learning
6. **Persistence Authority**: AI-OS controls what gets persisted and how
7. **Provenance Integrity**: All state changes carry complete, unbroken provenance chains

### Bounded Properties
The self-loop implements these bounded properties for safety and reliability:
1. **Time-Bounded Execution**: Each BOUNDED_EXECUTION has strict time limits
2. **Resource-Bounded Execution**: CPU, memory, and API call quotas enforced
3. **Retry-Bounded Execution**: Limited retry attempts prevent infinite loops
4. **Failure-Bounded Execution**: Degraded modes prevent total system failure
5. **Scope-Bounded Execution**: Execution limited to self-prompt defined scope
6. **Knowledge-Bounded Execution**: Learning limited to evidence-derived insights
7. **State-Bounded Execution**: Persistence limited to essential AI-OS state

### Lifecycle Properties
The self-loop ensures these lifecycle properties:
1. **Continuity**: Seamless transition between self-loop iterations
2. **Progression**: Each iteration builds on previous learning and state
3. **Completeness**: All phases completed before proceeding to next
4. **Correctness**: Verification and judgment ensure operational correctness
5. **Adaptability**: System evolves based on learning and evidence
6. **Resilience**: Bounded design prevents catastrophic failures
7. **Auditability**: Complete traceability of all decisions and actions

## Integration with External Systems

### External Systems as Bounded Resources
All external systems integrate with the self-loop strictly as bounded resources:
- **Supabase**: Persistent storage backend for AI-OS owned state
- **n8n**: Bounded automation/execution resource for workflow tasks
- **Obsidian Git**: Durable knowledge persistence layer with Git guarantees
- **AI-OS Dashboard**: Read-only UI with authorized action capabilities
- **Existing Ecosystem**: All integrations (Hermes/ACP, Hermes/MCP, Playwright, etc.) remain bounded

### Integration Pattern
All external systems follow this pattern with the self-loop:
1. **Self-Loop → External System**: Self-loop initiates actions and provides bounded parameters
2. **External System → Self-Loop**: External systems return results, status, errors, and artifacts
3. **Self-Loop Evaluation**: Self-loop evaluates results and determines next actions
4. **No External Decision Making**: External systems never decide self-loop next actions

### Prevention of External Authority
The self-loop prevents external systems from gaining authority through:
1. **Strict Initiation Control**: Self-loop exclusively controls when external systems act
2. **Parameter Binding**: Self-loop provides all parameters; external systems cannot invent parameters
3. **Result-Only Interface**: External systems return only execution data, never control signals
4. **Mandatory Evaluation**: Self-loop must explicitly evaluate external system results
5. **Bounded Scope**: External system actions limited to self-loop-defined bounds
6. **No Feedback Loops**: External outputs cannot trigger new external actions without self-loop mediation
7. **Provenance Integrity**: All external actions traceable to self-loop decision points
8. **Resource Enforcement**: Self-loop enforces resource bounds on external system usage
9. **Security Validation**: Self-loop validates external system access through SecurityManager
10. **Judgment Authority**: Self-loop retains FINAL_JUDGMENT authority over all operations

## Self-Loop State Management

### State Ownership
AI-OS owns all self-loop state, including:
- **Execution State**: Current task progress, execution context, bounded execution details
- **Decision State**: Recent judgments, decisions, and their justifications
- **Learning State**: Extracted insights, patterns, and knowledge updates
- **Knowledge State**: Current knowledge base and organizational structure
- **Persistence State**: Storage status, backup information, and recovery points
- **Integration State**: External system connection statuses, health metrics, and configurations
- **Resource State**: Current resource usage, quotas, and availability
- **Security State**: Active threats, security events, and policy enforcement status
- **Provenance State**: Complete history of decisions, actions, and their origins

### State Persistence
Self-loop state is persisted through:
1. **Regular Checkpoints**: Complete state snapshots at phase boundaries
2. **Incremental Updates**: Changes persisted as they occur
3. **Atomic Operations**: State updates are atomic to prevent corruption
4. **Durable Storage**: Appropriate persistence mechanisms (Supabase, filesystem, etc.)
5. **Versioning**: State versions allow rollback and historical analysis
6. **Provenance Tracking**: All persisted state carries complete decision/action provenance
7. **Validation**: Persisted state validated on retrieval to detect corruption

### State Recovery
Self-loop recovery ensures:
1. **Restart from Known State**: System recovers to last known good checkpoint
2. **State Validation**: Recovered state validated for integrity and consistency
3. **Provenance Preservation**: Complete provenance chains maintained through recovery
4. **Graceful Degradation**: System can operate with reduced functionality if needed
5. **Manual Intervention**: Clear procedures for operator-assisted recovery when needed
6. **Learning Preservation**: Extracted learning preserved through state recovery
7. **Knowledge Integrity**: Knowledge base integrity verified on recovery

## Technical Implementation

### Kernel Integration
The self-loop is implemented through the HermesKernel:
- **Kernel Lifecycle Management**: Kernel manages complete self-loop progression
- **Event-Driven Architecture**: Canonical EventTypes drive phase transitions
- **Service Coordination**: Core managers and services execute phase responsibilities
- **Bounded Enforcement**: ResourceManager and SecurityManager enforce bounds
- **State Management**: StateManager handles persistence and recovery
- **Workflow Orchestration**: WorkflowManager manages complex phase dependencies

### Event Flow
Canonical EventTypes drive self-loop progression:
- Phase start/completion events (e.g., PLANNING_STARTED, PLANNING_COMPLETED)
- Action request/completion events (e.g., TASK_STARTED, TASK_COMPLETED)
- Decision events (e.g., FINAL_JUDGE_DECISION, DECISION_MADE)
- Error/failure events (e.g., EXECUTION_FAILED, JUDGMENT_FAILED)
- Learning/update events (e.g., LEARNING_EXTRACTED, KNOWLEDGE_UPDATED)
- Persistence events (e.g., STATE_PERSISTED, STATE_RECOVERED)

### Bounded Execution Enforcement
Technical mechanisms enforce bounded execution:
1. **ResourceManager**: Tracks and enforces CPU, memory, API call quotas
2. **SecurityManager**: Validates all external system access and enforces policies
3. **Timeout Mechanisms**: Automatic termination of long-running operations
4. **Retry Counters**: Limit retry attempts to prevent infinite loops
5. **Validation Gates**: Phase transitions require validation before proceeding
6. **Health Checks**: HealthManager monitors system health and triggers degradation
7. **Fallback Mechanisms**: Degraded modes provide reduced functionality during stress

### Evaluation and Judgment
Authoritative evaluation through:
1. **Test Generation**: Automated test creation based on requirements
2. **Test Execution**: Reliable test execution with result collection
3. **Review Processes**: Multi-perspective evaluation by specialized councils
4. **Verification Procedures**: Confirmation that issues are resolved and standards met
5. **Final Judgment**: Authoritative decision by FINAL_JUDGE component
6. **Evidence Collection**: Complete evidence preservation for judgment basis
7. **Decision Logic**: Clear decision trees based on judgment outcomes

## Requirements

### Functional Requirements
1. AI-OS must maintain a continuous, authoritative self-loop
2. The self-loop must progress through all canonical lifecycle phases
3. External systems must integrate strictly as bounded resources
4. AI-OS must retain final judgment and decision-making authority
5. Bounded execution must enforce resource and time limits
6. Learning must be evidence-based and integrated into knowledge base
7. State must be persisted with durability guarantees for recovery
8. Provenance must be maintained for all state changes and decisions
9. Mock mode must be available for development/testing
10. Real mode requires appropriate user resources for external integrations

### Non-Functional Requirements
1. **Authoritativeness**: Self-loop decisions are final and binding
2. **Completeness**: All lifecycle phases completed before proceeding
3. **Correctness**: Verification and judgment ensure operational correctness
4. **Boundedness**: Resource and time limits prevent runaway execution
5. **Reliability**: Predictable behavior under normal and error conditions
6. **Auditability**: Complete traceability of all decisions and actions
7. **Recoverability**: System can restart from known good state
8. **Adaptability**: System evolves based on learning and evidence
9. **Security**: No unauthorized access, data leakage, or privilege escalation
10. **Performance**: Reasonable overhead for self-loop progression

### Local Development Strategy
- Use local instances of all required external systems (Supabase, n8n, Obsidian, etc.)
- Mock adapters available when external systems inaccessible
- Development focuses on testing self-loop progression and phase transitions
- Validation of bounded execution and resource enforcement
- Testing of learning integration and knowledge persistence

### Production Strategy
- User-provided instances for all external integrations
- Secure connections through AI-OS MCP framework
- Monitoring focused on self-loop health and progression
- Alerting on self-loop failures, judgment errors, or bounded execution violations
- Resource usage tracking and optimization based on actual patterns

### Mock Strategy
- In-memory simulators for all external systems
- Execute predefined behaviors that mimic real external system responses
- Return structured results matching real system formats
- Useful for testing self-loop decision logic based on external system outcomes
- Available when external system credentials unavailable or invalid

### Real Mode Requirements
- User must provide appropriate resources for all desired external integrations:
  - Supabase: URL and anon/public key (service role key optional)
  - n8n: Instance URL and API key
  - Obsidian: Vault path with Git initialization (remote URL optional)
  - Dashboard: Access to dashboard interface
  - Other integrations: Appropriate credentials and access as defined
- Environment variables set for each integration (e.g., SUPABASE_URL, N8N_BASE_URL)
- Integration framework validates real mode readiness based on user resources
- AIOS_REAL_INTEGRATION_ENABLED=1 required for gated real-operational tests
- All external systems must be accessible from AI-OS execution environment

## Security

### Authentication and Authorization
- AI-OS validates all external system accessibility before connection
- Access permissions validated through AI-OS SecurityManager
- No direct user access to external systems bypassing AI-OS governance
- All external system access flows through AI-OS SecurityManager gate-before-connect
- External system operations limited to AI-OS-provided parameters only

### Secret Handling
- All secrets managed through AI-OS secret management system (environment variables)
- No secrets stored in source code or configuration files
- Secret redaction in all logs, events, error messages, and diagnostic output
- Environment variable isolation prevents secret leakage to child processes
- Integration framework validates credentials before enabling real mode

### Failure Handling
- **External System Unavailable**: AI-OS treats as bounded execution failure and proceeds accordingly
- **Connection Loss**: Automatic reconnection with exponential backoff where applicable
- **Execution Failures**: AI-OS evaluates based on error type, context, and available evidence
- **Judgment Errors**: Treated as learning opportunities requiring self-loop adaptation
- **Bound Violations**: Self-loop terminates operations exceeding defined bounds
- **Parameter Validation Failures**: AI-OS rejects operation initiation
- **Security Violations**: Treated as security events requiring AI-OS judgment
- **Restart Recovery**: Self-loop state recovered from persistent storage on restart
- **Resource Exhaustion**: Handled through AI-OS quota management and degradation strategies
- **Learning Integration Failures**: AI-OS evaluates and adapts learning extraction process
- **Knowledge Persistence Failures**: AI-OS evaluates and adjusts knowledge persistence strategy

## Determining Mandatory vs Optional

### For v1 of M13 Milestone: MANDATORY
The self-loop is **MANDATORY** for v1 of the M13 milestone because:
1. It represents the core AI-OS autonomous functionality
2. All M0-M12 functionality depends on the self-loop operating correctly
3. The self-loop defines what it means for AI-OS to be an autonomous system
4. Without the self-loop, AI-OS is merely a collection of disconnected components
5. The self-loop provides the continuous, evolving intelligence that defines AI-OS

The self-loop cannot be optional because it **is** AI-OS operating in autonomous mode.

## Integration with Existing AI-OS Ecosystem

### Relationship to Core Components and Managers
The self-loop utilizes rather than replaces:
- **Core Components (C1-C4)**: EventBus, ServiceRegistry, ConfigurationManager, StructuredLogger
- **Core Managers**: StateManager, WorkflowManager, ResourceManager, HealthManager, SecurityManager, CapabilityManager, ObservabilityManager
- **Engineering Services**: All services (LearningService, PlanningService, etc.) operate within self-loop bounds
- **External Integrations**: All integrations function as bounded resources within self-loop execution
- **Decision Systems**: PlanningService, Councils, FinalJudge, etc. contribute to self-loop decisions

### Choice Criteria for Self-Loop Trust
Trust the AI-OS self-loop when:
1. It maintains authoritative control over all lifecycle phases
2. External systems remain strictly bounded resources
3. Final judgment and decision-making authority remain with AI-OS
4. Bounded execution enforces reasonable resource and time limits
5. Learning is evidence-based and properly integrated
6. State persistence provides durability and recovery guarantees
7. Provenance integrity is maintained for all decisions and actions
8. Security policies protect against unauthorized access and misuse

## Operational Tests

### Unit Tests
- Self-loop phase transition logic and event handling
- Bounded execution enforcement (time, resource, retry limits)
- State persistence and recovery mechanisms
- Learning extraction and knowledge integration
- Mock external system behavior and response handling
- Final judgment and decision logic
- Provenance tracking and maintenance
- Security policy enforcement and validation

### Integration Tests
- Complete self-loop progression with mocked external systems
- End-to-end lifecycle: USER_INTENT → NEXT_SELF_PROMPT → [REPEAT]
- Bounded execution with real external systems (when resources available and gated enabled)
- State persistence and recovery with real storage systems
- Learning integration and knowledge persistence validation
- Multi-perspective review and verification processes
- Final judgment authority and decision making
- Resource enforcement and bounded execution limits
- Security policy enforcement and access validation

### Operational Tests (Gated Real)
- Require AIOS_REAL_INTEGRATION_ENABLED=1 and verified user resources
- Test complete self-loop progression with real external systems
- Validate bounded execution enforcement with actual resource usage
- Confirm state persistence and recovery durability
- Validate learning extraction and knowledge integration accuracy
- Test multi-perspective review effectiveness and correctness
- Validate final judgment authority and decision making
- Test resource quotas and bounded execution limits under load
- Validate security policy enforcement and threat detection
- Benchmark real-world self-loop cycle time and resource characteristics

## Integration with AI-OS Lifecycle Points

### The Self-Loop IS the Lifecycle
The self-loop is not merely integrated with the lifecycle - it **is** the complete, continuously operating AI-OS lifecycle in autonomous mode.

### Lifecycle Points as Self-Loop Phases
Each lifecycle point represents a phase within the continuously operating self-loop:
1. **USER_INTENT**: Self-loop phase capturing and clarifying user objectives
2. **PLANNING**: Self-loop phase exploring solutions and creating plans
3. **RESEARCH**: Self-loop phase gathering information and validating assumptions
4. **REQUIREMENTS**: Self-loop phase defining concrete specifications
5. **COUNCILS/REVIEWS**: Self-loop phase providing multi-perspective evaluation
6. **PLAN**: Self-loop phase synthesizing into actionable roadmap
7. **TASKS**: Self-loop phase breaking down into executable work units
8. **SELF-PROMPT**: Self-loop phase generating authoritative execution directive
9. **BOUNDED_EXECUTION**: Self-loop phase executing within strict limits
10. **TEST**: Self-loop phase validating execution results
11. **REVIEW**: Self-loop phase providing multi-perspective evaluation
12. **VERIFICATION**: Self-loop phase confirming issue resolution and standards compliance
13. **FINAL_JUDGMENT**: Self-loop phase making authoritative completion determination
14. **DECISION**: Self-loop phase determining next steps based on judgment
15. **EVIDENCE**: Self-loop phase collecting and preserving execution artifacts
16. **LEARNING**: Self-loop phase extracting insights and updating knowledge
17. **MEMORY/KNOWLEDGE**: Self-loop phase persisting learning as durable knowledge
18. **PERSISTENCE**: Self-loop phase storing state for recovery and continuity
19. **NEXT_SELF_PROMPT**: Self-loop phase generating next authoritative directive
20. **[REPEAT]**: Self-loop continuously operating through bounded cycles

## Summary

The AI-OS self-loop represents the complete, continuously operating autonomous system that maintains authoritative control while integrating external systems strictly as bounded resources. Through clear phase definitions, bounded execution enforcement, mandatory evaluation protocols, and final judgment authority, the self-loop ensures AI-OS remains the sole governance, verification, and decision-making authority. The self-loop's bounded design provides safety and reliability while preserving the continuous, evolving intelligence that defines an autonomous system.