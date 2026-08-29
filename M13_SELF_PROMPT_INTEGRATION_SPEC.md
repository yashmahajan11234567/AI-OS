# M13 Self-Prompt Integration Specification

## Overview

This document defines the self-prompting architecture for AI-OS M13, specifying how AI-OS generates authoritative prompts that direct its own bounded execution while preserving AI-OS as the sole governance, verification, and decision-making authority. Self-prompts represent the AI-OS's internal directive for what it should attempt to accomplish in each bounded execution cycle.

## Role and Authority Model

### Exact Role
Self-prompts serve as the **authoritative internal directives** that:
- Encapsulate AI-OS's current state, goals, and execution context
- Define what AI-OS should attempt to accomplish in bounded execution
- Set clear success/failure criteria for the execution attempt
- Incorporate learning, evidence, and knowledge from previous cycles
- Represent the evolved understanding of AI-OS at each cycle point
- Direct the utilization of AI-OS agents, services, and external bounded resources

Self-prompts do NOT:
- Provide external systems with authority over AI-OS
- Allow external systems to initiate or modify AI-OS self-prompts
- Contain executable code that bypasses AI-OS security validation
- Represent claims or promises that external systems must fulfill
- Delegate AI-OS decision-making or judgment authority
- Create binding obligations for external systems
- Speculate about future AI-OS states beyond what is known and provable

### AI-OS Authority over Self-Prompts
AI-OS maintains complete authority over self-prompts:
- AI-OS generates all self-prompts through its internal processes
- AI-OS owns the semantic meaning of all self-prompt content
- AI-OS validates self-prompts against its current capabilities and state
- AI-OS can modify, reject, or regenerate self-prompts based on evaluation
- AI-OS determines when a self-prompt is sufficiently defined for execution
- AI-OS owns the success/failure criteria embedded in self-prompts
- AI-OS evaluates execution results against self-prompt criteria
- AI-OS learns from self-prompt outcomes to improve future prompting

### Self-Prompt Limitations (Bounding AI-OS Authority)
Self-prompts are bounded by:
- **Current AI-OS State**: Self-prompts must be grounded in verifiable, current state
- **Available Capabilities**: Self-prompts can only direct what AI-OS can actually do
- **Resource Constraints**: Self-prompts must respect bounded execution limits
- **Knowledge Boundaries**: Self-prompts cannot reference unknown or unprovable knowledge
- **Temporal Limits**: Self-prompts apply to the current execution cycle only
- **Security Policies**: Self-prompts must comply with AI-OS security constraints
- **Provenance Requirements**: Self-prompts must carry traceable AI-OS decision chains
- **Validation Requirements**: Self-prompts must be validated before execution

These limitations are **AI-OS self-imposed bounds** that enhance reliability and safety, not external constraints that diminish authority.

## Self-Prompt Architecture

### Self-Prompt Structure
Self-prompts follow this canonical structure:
```
{
  "prompt_id": "...",
  "cycle_id": "...", // identifies which self-loop iteration this belongs to
  "timestamp": "ISO timestamp",
  "context": {
    "user_intent": {...}, // original user goal driving this cycle
    "planning_outcome": {...}, // what planning phase produced
    "research_findings": {...}, // what research phase discovered
    "requirements_spec": {...}, // what requirements phase defined
    "council_reviews": {...}, // what councils/reviews phase evaluated
    "approved_plan": {...}, // what plan phase synthesized
    "task_assignments": {...}, // what tasks phase allocated
    "prior_execution_results": {...}, // results from previous bounded execution
    "test_outcomes": {...}, // what test phase found
    "review_feedback": {...}, // what review phase recommended
    "verification_status": {...}, // what verification phase confirmed
    "final_judgment": {...}, // what final judgment phase decided
    "decision_outcome": {...}, // what decision phase determined
    "evidence_collected": {...}, // what evidence phase gathered
    "learning_extracted": {...}, // what learning phase discovered
    "knowledge_updated": {...}, // what memory/knowledge phase persisted
    "state_persisted": {...}, // what persistence phase stored
    "current_aios_state": {...} // complete current AI-OS state snapshot
  },
  "directive": {
    "action_type": "...", // what type of action to execute
    "target_systems": [...], // which agents/services/external systems to use
    "parameters": {...}, // bounded parameters for execution
    "success_criteria": {...}, // what constitutes successful execution
    "failure_conditions": [...], // what would constitute failure
    "execution_bounds": {
      "timeout_seconds": ...,
      "max_retries": ...,
      "resource_limits": {...}, // CPU, memory, API calls, etc.
      "allowed_operations": [...], // what operations are permitted
      "prohibited_operations": [...] // what operations are forbidden
    },
    "provenance_chain": [...], // complete AI-OS decision/action history
    "security_context": {...}, // applicable AI-OS security policies
    "knowledge_bounds": {...}, // what knowledge AI-OS can reference
    "learning_objectives": [...] // what learning AI-OS hopes to extract
  },
  "metadata": {
    "version": "1.0",
    "generated_by": "aios_kernel",
    "validation_status": "validated",
    "validation_timestamp": "ISO timestamp",
    "expires_at": "ISO timestamp", // when prompt becomes stale
    "priority": "...", // execution priority level
    "tags": [...] // classification and categorization tags
  }
}
```

### Self-Prompt Generation Process
Self-prompts are generated through this process:
1. **State Assimilation**: Collect complete current AI-OS state from all phases
2. **Context Integration**: Integrate outputs from all previous lifecycle phases
3. **Directive Formulation**: Formulate execution directive based on context and goals
4. **Bound Specification**: Define execution bounds (time, resources, security, etc.)
5. **Criteria Definition**: Establish clear success/failure criteria for execution
6. **Validation**: Validate self-prompt against current AI-OS capabilities and state
7. **Provenance Attribution**: Attach complete AI-OS decision/action provenance
8. **Metadata Addition**: Add versioning, timestamps, and classification metadata
9. **Readiness Determination**: Determine when self-prompt is sufficiently defined
10. **Execution Dispatch**: Dispatch validated self-prompt to bounded execution phase

## Self-Prompt Properties

### Authoritative Properties
Self-prompts maintain these authoritative properties:
1. **AI-OS Generated**: Only AI-OS can generate valid self-prompts
2. **Contextual Completeness**: Incorporate all relevant phase outputs and state
3. **Execution Directiveness**: Clearly direct what AI-OS should attempt
4. **Criteria Clarity**: Define unambiguous success/failure criteria
5. **Bound Specification**: Specify execution limits and constraints
6. **Provenance Integrity**: Carry complete, unbroken AI-OS decision chains
7. **Validation Requirement**: Must be validated before execution use
8. **Temporal Specificity**: Apply to specific execution cycle only
9. **Learning Orientation**: Designed to extract validated learning
10. **State Grounded**: Rooted in verifiable, current AI-OS state

### Bounded Properties
Self-prompts implement these bounded properties:
1. **State-Bounded**: Grounded in current, verifiable AI-OS state only
2. **Capability-Bounded**: Can only direct what AI-OS can actually execute
3. **Resource-Bounded**: Must respect bounded execution limits
4. **Knowledge-Bounded**: Cannot reference unknown or unprovable knowledge
5. **Temporal-Bounded**: Apply to current execution cycle only
6. **Security-Bounded**: Must comply with AI-OS security policies
7. **Validation-Bounded**: Require validation before execution use
8. **Scope-Bounded**: Limited to self-prompt defined execution scope
9. **Retry-Bounded**: Execution attempts limited by retry constraints
10. **Failure-Bounded**: Degraded modes prevent total failure from prompt issues

### Directive Properties
Self-prompt directives contain:
1. **Action Type**: Clear specification of what type of execution to perform
2. **Target Systems**: Specific agents, services, and external resources to utilize
3. **Parameters**: Bounded parameters for execution (no undefined parameters)
4. **Success Criteria**: Measurable, observable criteria for successful execution
5. **Failure Conditions**: Clear conditions that would constitute execution failure
6. **Execution Bounds**: Time, resource, retry, and operational limits
7. **Provenance Chain**: Complete AI-OS decision/action history leading to directive
8. **Security Context**: Applicable AI-OS security policies and constraints
9. **Knowledge Bounds**: Limits on what knowledge can be referenced/used
10. **Learning Objectives**: What validated learning AI-OS hopes to extract

## Integration with AI-OS Lifecycle

### Self-Prompt Generation Point
Self-prompts are generated at the **SELF-PROMPT** phase of the AI-OS lifecycle:
```
TASKS → SELF-PROMPT → [BOUNDED EXECUTION] → TEST → REVIEW → VERIFICATION → FINAL JUDGMENT → DECISION → EVIDENCE → LEARNING → MEMORY/KNOWLEDGE → PERSISTENCE → NEXT SELF-PROMPT
```

### Self-Prompt Generation Flow
1. **Task Completion**: TASKS phase completes assigned work units
2. **State Collection**: AI-OS collects complete state from all preceding phases
3. **Context Integration**: Outputs from PLANNING, RESEARCH, REQUIREMENTS, COUNCILS, PLAN, and TASKS integrated
4. **Outcome Incorporation**: Results from previous CYCLE's execution, test, review, verification, judgment, decision, evidence, learning, knowledge, and persistence phases incorporated
5. **Directive Formation**: Based on integrated context, AI-OS formulates execution directive
6. **Bound Specification**: Execution bounds (time, resources, security, etc.) defined
7. **Criteria Establishment**: Success/failure criteria for execution attempt defined
8. **Validation**: Self-prompt validated against current AI-OS capabilities and state
9. **Provenance Attribution**: Complete AI-OS decision/action chain attached
10. **Metadata Addition**: Versioning, timestamps, and classification metadata added
11. **Readiness Check**: Determined if self-prompt is sufficiently defined for execution
12. **Dispatch**: Validated self-prompt dispatched to BOUNDED EXECUTION phase

### Self-Prompt Usage in Bounded Execution
In the BOUNDED EXECUTION phase:
1. **Prompt Receipt**: Bounded execution receives validated self-prompt
2. **Context Setup**: Execution environment configured per self-prompt specification
3. **Parameter Binding**: Self-prompt parameters bound to execution context
4. **Target Engagement**: Specified agents, services, and external systems engaged
5. **Bound Enforcement**: Execution bounds (time, resources, etc.) enforced
6. **Execution Attempt**: AI-OS attempts to accomplish self-prompt directive
7. **Result Collection**: Execution results, artifacts, and evidence collected
8. **Bound Compliance**: Verification that execution respected all bounds
9. **Result Evaluation**: Results evaluated against self-prompt success/failure criteria
10. **Outcome Determination**: Execution outcome determined (success, failure, timeout, etc.)
11. **Phase Progression**: Based on outcome, progression to TEST phase occurs

### Self-Prompt Evolution
Self-prompts evolve through the self-loop:
1. **Learning Incorporation**: Extracted learning informs future self-prompt generation
2. **Knowledge Integration**: Persisted knowledge available for self-prompt context
3. **State Evolution**: Changed AI-OS state reflected in subsequent self-prompts
4. **Outcome Adaptation**: Execution outcomes shape future self-prompt criteria
5. **Pattern Recognition**: Repeated patterns inform self-prompt optimization
6. **Error Correction**: Execution failures lead to improved self-prompt formulation
7. **Success Reinforcement**: Successful patterns reinforced in future prompting
8. **Context Refinement**: Improved state assessment leads to better self-prompts
9. **Goal Progression**: Accomplished goals lead to new, advanced self-prompts
10. **Adaptive Replanning**: Significant changes trigger replanning and new self-prompts

## Requirements

### Functional Requirements
1. AI-OS must generate self-prompts that encapsulate current state and execution goals
2. Self-prompts must define clear execution directives with target systems and parameters
3. Self-prompts must specify bounded execution limits (time, resources, security)
4. Self-prompts must establish unambiguous success/failure criteria for execution
5. Self-prompts must be validated before use in bounded execution
6. Self-prompts must carry complete AI-OS provenance chains
7. Self-prompts must incorporate outputs from all relevant lifecycle phases
8. Self-prompts must evolve based on learning, outcomes, and state changes
9. Mock mode must be available for development/testing
10. Real mode requires appropriate user resources for external integrations

### Non-Functional Requirements
1. **Authoritativeness**: Self-prompts represent AI-OS's authoritative execution directive
2. **Completeness**: Self-prompts incorporate all relevant phase outputs and state
3. **Clarity**: Self-prompts clearly direct what AI-OS should attempt to execute
4. **Specificity**: Success/failure criteria are measurable and observable
5. **Boundedness**: Self-prompts respect execution limits and constraints
6. **Validation**: Self-prompts require validation before execution use
7. **Provenance**: Complete AI-OS decision/action chains maintained
8. **Learning Orientation**: Self-prompts designed to extract validated learning
9. **State Grounded**: Self-prompts rooted in verifiable, current AI-OS state
10. **Temporal Specificity**: Self-prompts apply to specific execution cycle only

### Local Development Strategy
- Use local instances of all required external systems (Supabase, n8n, Obsidian, etc.)
- Mock adapters available when external systems inaccessible
- Development focuses on testing self-prompt generation and validation
- Validation of self-prompt completeness, clarity, and boundedness
- Testing of self-prompt incorporation of phase outputs and state
- Testing of self-prompt evolution based on learning and outcomes

### Production Strategy
- User-provided instances for all external integrations
- Secure connections through AI-OS MCP framework
- Monitoring focused on self-prompt generation quality and validity
- Alerting on self-prompt generation failures, validation errors, or boundedness violations
- Self-prompt quality metrics tracking and optimization

### Mock Strategy
- In-memory self-prompt generation simulator
- Generates predefined self-prompts that mimic real self-prompt structure
- Returns self-prompts matching the canonical self-prompt format
- Useful for testing bounded execution logic based on self-prompt directives
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
- AI-OS validates self-prompt generation internally (no external authentication needed)
- Self-prompt generation limited to AI-OS internal processes only
- No external system can initiate or modify AI-OS self-prompts
- Self-prompt validation occurs within AI-OS secure validation context
- Self-prompt usage limited to AI-OS authorized bounded execution only

### Secret Handling
- Self-prompts may contain references to secrets but never the secrets themselves
- Secret references handled through AI-OS secret management system
- No secrets stored in self-prompt content or metadata
- Secret redaction in all logs, events, error messages containing self-prompts
- Environment variable isolation prevents secret leakage to self-prompt processing
- Integration framework validates credentials before enabling real mode for execution

### Failure Handling
- **Self-Prompt Generation Failure**: AI-OS treats as planning failure and replans
- **Self-Prompt Validation Failure**: AI-OS treats as planning failure and regenerates
- **Self-Prompt Staleness**: Self-prompts expire and must be regenerated if too old
- **Self-Prompt Ambiguity**: Ambiguous self-prompts treated as planning failure
- **Self-Prompt Overreach**: Self-prompts exceeding AI-OS capabilities treated as planning failure
- **Self-Prompt Resource Violation**: Self-prompts violating bounds treated as planning failure
- **Self-Prompt Security Violation**: Self-prompts violating security policies treated as planning failure
- **Self-Prompt Knowledge Violation**: Self-prompts referencing unprovable knowledge treated as planning failure
- **Bounded Execution Failure**: AI-OS evaluates execution results against self-prompt criteria
- **Learning Integration Failure**: AI-OS evaluates and adapts learning extraction from outcomes

## Determining Mandatory vs Optional

### For v1 of M13 Milestone: MANDATORY
Self-prompts are **MANDATORY** for v1 of the M13 milestone because:
1. They represent the AI-OS's internal execution directive
2. Without self-prompts, AI-OS has no basis for bounded execution attempts
3. Self-prompts encapsulate the evolved understanding that drives AI-OS progression
4. All M0-M12 functionality depends on self-prompts directing bounded execution
5. Self-prompts provide the linking mechanism between AI-OS cognition and action

Self-prompts cannot be optional because they **are** how AI-OS directs its own autonomous operation.

## Integration with Existing AI-OS Ecosystem

### Relationship to Core Components and Managers
Self-prompts utilize rather than replace:
- **Core Components (C1-C4)**: EventBus, ServiceRegistry, ConfigurationManager, StructuredLogger
- **Core Managers**: StateManager, WorkflowManager, ResourceManager, HealthManager, SecurityManager, CapabilityManager, ObservabilityManager
- **Engineering Services**: All services operate based on self-prompt directives
- **External Integrations**: All integrations utilized as directed by self-prompts
- **Decision Systems**: PlanningService, Councils, FinalJudge, etc. contribute to self-prompt generation

### Choice Criteria for Self-Prompt Trust
Trust AI-OS self-prompts when:
1. They are generated through valid AI-OS internal processes
2. They incorporate complete, verified phase outputs and state
3. They clearly direct what AI-OS should attempt to execute
4. They establish measurable, observable success/failure criteria
5. They respect bounded execution limits and constraints
6. They carry complete, unbroken AI-OS provenance chains
7. They are validated before execution use
8. They are designed to extract validated learning from execution
9. They are grounded in verifiable, current AI-OS state
10. They evolve based on learning, outcomes, and state changes

## Operational Tests

### Unit Tests
- Self-prompt generation logic and state integration
- Self-prompt structure validation and canonical format compliance
- Self-prompt context incorporation from all lifecycle phases
- Self-prompt directive formulation and success/failure criteria definition
- Self-prompt bound specification (time, resources, security, etc.)
- Self-prompt validation against current AI-OS capabilities and state
- Provenance tracking and maintenance in self-prompts
- Self-prompt metadata addition and versioning
- Self-prompt readiness determination and expiration logic
- Self-prompt incorporation of learning and knowledge updates
- Self-prompt evolution based on execution outcomes and state changes

### Integration Tests
- End-to-end self-prompt generation and usage
- Self-prompt generation from complete lifecycle phase outputs
- Self-prompt usage in bounded execution with real external systems (when resources available and gated enabled)
- Self-prompt directed execution results and outcome determination
- Self-prompt success/failure criteria application and evaluation
- Self-prompt bound enforcement verification
- Self-prompt learning integration and knowledge persistence validation
- Self-prompt evolution based on execution outcomes and state changes
- Self-prompt authority preservation and external system boundedness
- Self-prompt security validation and constraint enforcement

### Operational Tests (Gated Real)
- Require AIOS_REAL_INTEGRATION_ENABLED=1 and verified user resources
- Test self-prompt generation with real external systems integrated
- Validate self-prompt completeness and contextual accuracy
- Confirm self-prompt directed execution fidelity and correctness
- Validate self-prompt success/failure criteria effectiveness
- Test self-prompt bound enforcement under actual resource constraints
- Validate self-prompt learning integration and knowledge persistence accuracy
- Test self-prompt evolution based on real execution outcomes
- Validate self-prompt authority preservation and external system boundedness
- Test self-prompt security validation and constraint enforcement
- Benchmark real-world self-prompt generation and usage characteristics

## Integration with AI-OS Lifecycle Points

### Self-Prompt as Lifecycle Phase
The self-prompt phase is a distinct, essential phase within the continuously operating AI-OS self-loop.

### Lifecycle Points Related to Self-Prompting
1. **TASKS**: Precedes self-prompt generation; provides completed work units
2. **SELF-PROMPT**: Generates authoritative internal directive for bounded execution
3. **BOUNDED_EXECUTION**: Executes the self-prompt directive within limits
4. **TEST**: Evaluates execution results against self-prompt criteria
5. **REVIEW**: Provides multi-perspective evaluation of self-prompt execution
6. **VERIFICATION**: Confirms issue resolution and standards compliance for self-prompt
7. **FINAL_JUDGMENT**: Makes authoritative completion determination for self-prompt
8. **DECISION**: Determines next steps based on self-prompt judgment outcome
9. **EVIDENCE**: Collects artifacts from self-prompt directed execution
10. **LEARNING**: Extracts insights from self-prompt execution outcomes
11. **MEMORY/KNOWLEDGE**: Persists learning from self-prompt execution
12. **PERSISTENCE**: Stores state for recovery, influencing future self-prompts
13. **NEXT_SELF_PROMPT**: Generates next directive based on self-prompt outcomes
14. **[REPEAT]**: Self-loop continuously operates through self-prompt cycles

## Summary

Self-prompts represent the AI-OS's authoritative internal directive for bounded execution, encapsulating current state, goals, and context while defining clear execution attempts with success/failure criteria. Through strict self-generation, validation, boundedness requirements, and provenance integrity, self-prompts ensure AI-OS remains the sole governance, verification, and decision-making authority. The self-prompt mechanism provides the essential link between AI-OS cognition and action, enabling continuous, evolving autonomous operation while maintaining rigorous bounds and validation.