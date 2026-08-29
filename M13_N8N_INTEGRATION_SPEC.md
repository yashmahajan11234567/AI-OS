# M13 n8n Integration Specification

## Overview

This document defines n8n as a bounded automation/execution resource for AI-OS M13, specifying how AI-OS directs n8n to execute workflows and evaluates results, while preventing n8n from becoming a parallel autonomous system or decision-making authority.

## Role and Authority Model

### Exact Role
n8n serves as a **bounded automation/execution resource** that executes predefined workflows under AI-OS direction. It does NOT provide:
- Autonomous decision-making
- Workflow initiation authority
- Next-action determination for AI-OS
- Parallel execution control
- Governance or verification functions

### AI-OS Authority over n8n
AI-OS maintains complete authority:
- AI-OS decides: "Execute workflow X with parameters Y"
- AI-OS provides bounded execution context and constraints
- AI-OS evaluates n8n results and determines next actions
- AI-OS can abort, retry, or modify n8n execution
- AI-OS owns the semantic meaning of workflow outcomes

### n8n Limitations
n8n is restricted to:
- Executing only workflows explicitly initiated by AI-OS
- Returning only execution status, output, errors, and artifacts
- Operating within time and resource bounds set by AI-OS
- Performing only actions explicitly defined in AI-OS-authorized workflows
- Making no autonomous decisions about AI-OS next steps

## Communication Patterns

### AI-OS → n8n Communication
AI-OS communicates with n8n through a strictly defined interface:

1. **Workflow Initiation Command**
   ```
   {
     "workflow_id": "approved_workflow_identifier",
     "parameters": {/* bounded execution parameters */},
     "context": {
       "aios_correlation_id": "...",
       "execution_bounds": {
         "timeout_seconds": 300,
         "max_retries": 3,
         "resource_limits": {/* CPU, memory, etc. */}
       },
       "security_context": {/* AI-OS security policies */},
       "provenance": {/* full AI-OS provenance chain */},
       "bounded_by": "aios_kernel"
     },
     "idempotency_key": "...", // for safe retries
     "requested_at": "ISO timestamp"
   }
   ```

2. **Parameter Binding**
   - AI-OS provides all workflow parameters
   - No workflow can access undefined parameters
   - Parameter validation performed by AI-OS before initiation
   - Sensitive parameters handled through AI-OS secret management

3. **Execution Bounds**
   - AI-OS enforces timeout limits
   - AI-OS sets retry constraints
   - AI-OS defines resource quotas (CPU, memory, disk, API calls)
   - AI-OS can terminate execution exceeding bounds

### n8n → AI-OS Callback/Event Path
n8n returns results through a structured response:

1. **Completion Response**
   ```
   {
     "execution_id": "...",
     "workflow_id": "...",
     "status": "success|failure|timeout|cancelled",
     "output": {/* workflow-defined output structure */},
     "errors": [/* structured error details */],
     "artifacts": [/* references to generated files/outputs */],
     "metrics": {
       "execution_time_ms": ...,
       "retries_attempted": ...,
       "resources_used": {/* actual consumption */},
       "api_calls_made": {/* count by service */},
       "timestamps": {/* started, completed, etc. */}
     },
     "provenance_echo": {/* AI-OS provenance returned unchanged */},
     "completed_at": "ISO timestamp"
   }
   ```

2. **Progress Updates** (for long-running workflows)
   - Periodic status updates through same channel
   - AI-OS can request cancellation at any time
   - Updates include progress percentage and current step

### Communication Technology
- Primary: Standard AI-OS MCP framework with n8n MCP server
- Transport: stdio subprocess communication (consistent with other MCP adapters)
- Security: Gate-before-connect validation through AI-OS SecurityManager
- Reliability: Built-in retry mechanisms with exponential backoff
- Ordering: Message sequencing preserved through correlation IDs

## SecurityManager Integration

### Gate-Before-Connect Enforcement
All n8n connections must pass AI-OS SecurityManager validation:
1. **Configuration Validation**: n8n server configuration validated before connection
2. **Credential Validation**: API keys and connection details validated
3. **Network Policy Validation**: Outbound connections checked against allowed destinations
4. **Scope Limitation**: Validation ensures n8n only accesses AI-OS authorized endpoints
5. **Audit Trail**: All connection attempts logged for security monitoring

### Credential Handling
- API keys managed through AI-OS secret management system
- No credentials stored in source code or logs
- Credential rotation supported without workflow modification
- Environment variable injection at runtime (never in process memory long-term)
- Secret scrubbing from all error messages and diagnostics

### subprocess environment scrubbing
- n8n subprocess receives only AI-OS-approved environment variables
- All inherited environment variables filtered through security policy
- Working directory restricted to AI-OS-controlled temporary directories
- File system access limited to explicitly permitted paths
- Network access constrained to declared workflow requirements

### Provenance and Audit Trail
- All n8n invocations carry complete AI-OS provenance chains
- Every action traceable to AI-OS decision point
- Audit logs include:
  - Who/what initiated the n8n workflow
  - What parameters were provided
  - What bounds were set
  - What results were returned
  - What AI-OS decided based on results

## Preventing Parallel Autonomous Systems

### Technical Constraints
1. **No Self-Initiation**: n8n cannot start workflows without AI-OS command
2. **No External Triggers**: n8n cannot respond to external events to initiate AI-OS-relevant actions
3. **No State Persistence Beyond Workflow**: n8n cannot maintain state that influences future AI-OS decisions
4. **No Autonomous Workflow Modification**: n8n cannot alter workflows based on external observations
5. **No Decision Output**: n8n outputs only execution results, never AI-OS directives

### Architectural Enforcement
1. **Single Initiation Point**: All n8n workflows start only through AI-OS invoke() capability
2. **Bounded Execution Context**: Each execution gets fresh, isolated context
3. **Result-Only Interface**: n8n returns only execution data, never control signals
4. **AI-OS Evaluation Mandatory**: AI-OS must explicitly evaluate results before proceeding
5. **No Feedback Loops**: n8n outputs cannot directly trigger new n8n invocations without AI-OS mediation

### Operational Safeguards
1. **Execution Isolation**: Each n8n workflow runs in isolated subprocess
2. **Resource Containment**: Strict quotas prevent resource exhaustion attacks
3. **Time Boxing**: Automatic termination of long-running executions
4. **Network Segmentation**: Outbound connections limited to declared workflow needs
5. **File System Sandboxing**: Restricted to specified input/output directories only

## Allowed External API Calls

### When Yes, Define Exactly Which Calls Are Allowed
n8n may call external APIs **only when**:
1. Explicitly defined in AI-OS-provided workflow definition
2. Parameterized by AI-OS-provided values only
3. Within bounds set by AI-OS (rate limits, quotas, etc.)
4. To endpoints pre-approved by AI-OS for that specific workflow
5. For purposes clearly defined in AI-OS workflow context

### How AI-OS Authorization, Provenance, and Security Are Preserved
1. **Workflow-Level Approval**: AI-OS approves entire workflow including all external calls
2. **Parameter Sanitization**: AI-OS sanitizes all parameters before workflow execution
3. **Call Logging**: AI-OS logs all external API calls made through n8n workflows
4. **Result Validation**: AI-OS validates that only approved calls were made
5. **Bound Enforcement**: AI-OS enforces that calls stay within declared limits
6. **Provenance Extension**: External call results carry AI-OS provenance through n8n

### Prevention of Becoming Parallel Autonomous System
n8n cannot become autonomous because:
1. **No Trigger Mechanism**: No way for n8n to start workflows autonomously
2. **No Memory Persistence**: Cannot store state between executions to build autonomy
3. **No Output Authority**: Outputs only execution data, never directives
4. **AI-OS Mediated**: Every execution requires explicit AI-OS initiation and evaluation
5. **Bounded Scope**: Each execution limited to predefined parameters and bounds
6. **Audit Traceability**: Every action traceable to AI-OS decision point

## Integration with AI-OS Lifecycle

### Where n8n Integrates in Bounded Execution Phase
n8n operates within the **BOUNDED EXECUTION** phase of the AI-OS lifecycle:
```
SELF-PROMPT → [BOUNDED EXECUTION: n8n workflow] → TEST → REVIEW → VERIFICATION
```

### Integration Flow
1. **Self-Prompt Generation**: AI-OS generates prompt including "Execute workflow X via n8n"
2. **Bounded Execution Initiation**: AI-OS invokes n8n with workflow ID, parameters, and bounds
3. **n8n Execution**: n8n executes workflow within AI-OS-defined constraints
4. **Result Return**: n8n returns structured execution result to AI-OS
5. **AI-OS Evaluation**: AI-OS evaluates result in TEST phase
6. **Progression**: Based on evaluation, AI-OS proceeds to REVIEW or handles failure

### Integration Points
- **Planning**: AI-OS determines when n8n automation is appropriate for a task
- **Requirements**: AI-OS specifies what n8n should accomplish
- **Architecture**: AI-OS designs how n8n fits into execution flow
- **Task Decomposition**: AI-OS creates specific "Execute n8n workflow" tasks
- **Self-Prompting**: AI-OS generates prompts directing n8n execution
- **Bounded Execution**: Actual n8n workflow execution occurs here
- **Testing**: AI-OS validates n8n execution results
- **Review**: AI-OS and councils evaluate n8n output adequacy
- **Verification**: FinalJudge confirms n8n execution met requirements
- **Decision**: AI-OS decides next steps based on n8n results
- **Evidence**: n8n execution records stored as evidence
- **Learning**: AI-OS learns from n8n execution patterns and outcomes
- **Persistence**: n8n execution data stored for audit and replay
- **Next Self-Prompt**: Based on n8n results, AI-OS generates next prompt

## Requirements

### Functional Requirements
1. AI-OS must be able to initiate n8n workflow execution with bounded parameters
2. n8n must return structured execution results including status, output, errors, and artifacts
3. AI-OS must be able to set execution bounds (timeouts, retries, resource limits)
4. AI-OS must validate that n8n only performed authorized actions
5. System must handle n8n unavailability gracefully
6. Mock mode must be available for development/testing
7. Real mode requires user-provided n8n instance and API key

### Non-Functional Requirements
1. **Execution Fidelity**: Workflows execute exactly as defined by AI-OS
2. **Parameter Safety**: No parameter injection or workflow manipulation possible
3. **Isolation**: Each execution isolated from others and host system
4. **Audit Completeness**: Full traceability from AI-OS decision to n8n execution to results
5. **Security**: No credential leakage, command injection, or privilege escalation
6. **Reliability**: Predictable behavior under normal and error conditions
7. **Performance**: Reasonable overhead for workflow initiation and result retrieval

### Local Development Strategy
- Use local n8n instance via Docker for development
- Mock n8n adapter available when no n8n instance accessible
- Development workflows focus on testing AI-OS → n8n → AI-OS communication
- Workflow validation without external dependencies

### Production Strategy
- User-provided n8n instance (self-hosted or cloud)
- Secure connection through AI-OS MCP framework
- Workflow deployment and management through AI-OS direction
- Monitoring focused on AI-OS perspective (did n8n do what AI-OS asked?)
- Alerting on execution failures or bound violations

### Mock Strategy
- In-memory n8n workflow simulator
- Executes predefined mock workflows that mimic real n8n behavior
- Returns structured results matching real n8n format
- Useful for testing AI-OS decision logic based on execution outcomes
- Available when n8n credentials unavailable or invalid

### Real Mode Requirements
- User must provide:
  - n8n instance URL (http://localhost:5678 or similar)
  - n8n API key (generated in n8n Settings → API)
- Environment variables: `N8N_BASE_URL`, `N8N_API_KEY`
- Integration framework validates real mode readiness based on user resources
- AIOS_REAL_INTEGRATION_ENABLED=1 required for gated real-operational tests
- n8n instance must be accessible from AI-OS execution environment

## Security

### Authentication and Authorization
- AI-OS validates n8n server configuration before connection
- API key authentication handled through standard HTTP headers
- No direct user access to n8n bypassing AI-OS governance
- All n8n access flows through AI-OS SecurityManager gate-before-connect
- Workflow execution limited to AI-OS-provided parameters only

### Secret Handling
- API keys managed through AI-OS secret management (environment variables)
- No secrets in configuration files or source code
- Secret redaction in all logs, events, error messages 텍스트
- Environment variable isolation prevents secret leakage to child processes
- Integration framework validates credentials before enabling real mode

### Failure Handling
- **n8n Unavailable**: AI-OS treats as execution failure and proceeds accordingly
- **Connection Loss**: Automatic reconnection with exponential backoff
- **Workflow Failures**: AI-OS evaluates based on error type and context
- **Timeout Executions**: Treated as failed executions with timeout reason
- **Bound Violations**:AI-OS terminates executions exceeding defined bounds
- **Parameter Validation Failures**: AI-OS rejects workflow initiation
- **Security Violations**: Treated as security events requiring AI-OS judgment
- **Restart Recovery**: No persistent state in n8n that affects AI-OS restart
- **Resource Exhaustion**: Handled through AI-OS quota management

## Determining Mandatory vs Optional

### For v1 of M13 Milestone: OPTIONAL
n8n is **OPTIONAL** for v1 of the M13 milestone because:
1. Core AI-OS bounded execution capability exists through other mechanisms (direct agent execution, Hermes/ACP, Playwright)
2. n8n provides workflow orchestration convenience but isn't required for core functionality
3. All M0-M12 functionality verified without n8n dependency
4. AI-OS can implement complex execution sequences without workflow engine
5. User may prefer other automation tools or direct execution approaches

### Conditions for Making n8n More Central
n8n could gain increased importance when:
1. Complex multi-step automation requires visual workflow design
2. Non-technical users benefit from graphical workflow representation
3. Enterprise standardization on n8n for process automation
4. Need for reusable workflow components across multiple AI-OS projects
5. Integration with existing n8n ecosystem provides significant value

However, even with increased usage, AI-OS would retain:
- Complete authority over workflow initiation and parameters
- Ability to execute equivalent logic through other mechanisms
- Clear separation between AI-OS decision-making and n8n execution
- Mandatory AI-OS evaluation of all n8n results

## Determining Whether n8n May Directly Call External APIs

### Yes, But With Strict Constraints
n8n **may** call external APIs when:
1. Explicitly defined in AI-OS-provided workflow
2. Parameters come solely from AI-OS-provided values
3. Calls stay within AI-OS-defined bounds (rate limits, quotas, etc.)
4. Destinations are pre-approved by AI-OS for that workflow
5. Purpose is clearly documented in AI-OS workflow context

### How Authorization, Provenance, and Security Are Preserved
1. **Workflow Approval**: AI-OS approves the specific external calls in workflow definition
2. **Parameter Control**: AI-OS provides and validates all parameters
3. **Call Monitoring**: AI-OS can monitor/log external calls made through n8n
4. **Result Validation**: AI-OS verifies only approved external calls occurred
5. **Bound Enforcement**: AI-OS enforces that calls respect declared limits
6. **Provenance Chain**: External call results carry AI-OS provenance through n8n
7. **Security Evaluation**: AI-OS evaluates external call results in subsequent phases

### Prevention of Becoming Parallel Autonomous System
1. **No Autonomous Triggering**: External calls cannot initiate new n8n workflows
2. **No State Building**: External call results don't persist to influence future AI-OS decisions
3. **No Authority Transfer**: External systems gain no authority over AI-OS through n8n
4. **AI-OS Mediated Evaluation**: AI-OS must explicitly evaluate external call results
5. **Context Binding**: External calls bound to specific workflow execution context
6. **Audit Trail**: Complete traceability from AI-OS decision → n8n → external call → results

## Integration with Existing AI-OS Ecosystem

### Relationship to Other Execution Mechanisms
n8n complements rather than replaces:
- **Hermes/ACP**: Direct agent-to-agent communication for tightly coupled tasks
- **Hermes/MCP**: Standardized tool access for bounded capabilities
- **Playwright**: Browser-based testing and automation
- **Direct Agent Execution**: Immediate task execution without workflow overhead
- **Agent Reach**: Communication and information gathering
- **FreeLLMAPI**: Local LLM inference for bounded AI tasks

### Choice Criteria for Using n8n
Use n8n when:
1. Workflow benefits from graphical representation and monitoring
2. Complex conditional logic or retry patterns are easier to visualize
3. Team has existing n8n expertise and investment
4. Workflow requires coordination of multiple external systems
5. Visual debugging and execution tracing provide value
6. Long-running workflows benefit from checkpoint and resume capabilities

Use other mechanisms when:
1. Simple direct execution suffices
2. Low-latency response required
3. Tight coupling between agents needed
4. Browser-based interaction required (use Playwright)
5. Direct tool access sufficient (use Hermes/MCP)
6. Communication-focused tasks (use Agent Reach)
7. Local LLM inference needed (use FreeLLMAPI)

## Operational Tests

### Unit Tests
- Mock n8n adapter behavior
- Workflow initiation and parameter passing
- Result parsing and validation
- Error handling and timeout simulation
- Security policy enforcement
- Mock/real mode switching

### Integration Tests
- Real n8n instance (when user resources available and gated enabled)
- End-to-end workflow execution: AI-OS → n8n → AI-OS
- Parameter binding and validation
- External API call simulation within workflow bounds
- Result evaluation and AI-OS decision making
- Concurrent workflow execution handling
- Workflow modification and version handling

### Operational Tests (Gated Real)
- Require AIOS_REAL_INTEGRATION_ENABLED=1 and verified user resources
- Test actual n8n connectivity and authentication
- Validate workflow execution fidelity and performance
- Test error handling and recovery scenarios
- Validate bound enforcement (timeouts, resource limits)
- Test security policy enforcement and audit logging
- Benchmark real-world execution characteristics

## Integration with AI-OS Lifecycle Points

### Primary Integration Point: Bounded Execution Phase
n8n's primary role is executing bounded automation tasks within the AI-OS lifecycle's EXECUTION phase.

### Supporting Integration Points
1. **Planning**: Determining when workflow automation is appropriate
2. **Requirements**: Specifying what the workflow should accomplish
3. **Architecture**: Designing workflow integration points
4. **Task Decomposition**: Creating specific "Execute workflow via n8n" tasks
5. **Self-Prompting**: Generating prompts that direct n8n execution
6. **Testing**: Validating n8n execution results against requirements
7. **Review**: Council evaluation of workflow output adequacy
8. **Verification**: FinalJudge confirmation that workflow met specifications
9. **Decision**: AI-OS determination of next steps based on workflow results
10. **Evidence**: Persistent storage of workflow execution records
11. **Learning**: AI-OS adaptation based on workflow performance patterns
12. **Persistence**: Storage of workflow metadata, configurations, and execution history
13. **Next Self-Prompt**: Based on workflow outcomes, generating subsequent prompts

## Summary

n8n provides valuable workflow automation capabilities while operating strictly within AI-OS-defined bounds. The integration preserves AI-OS as the sole decision-making authority while leveraging n8n's workflow execution strengths. Through strict boundary enforcement, comprehensive validation, and mandatory AI-OS evaluation, n8n remains a bounded resource rather than becoming a parallel autonomous system.