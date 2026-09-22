# B1-T1 — Governed Intelligent Planning Pipeline Integration

## Status
READY FOR IMPLEMENTATION

## Scope
Implement the minimum set of tightly coupled missing connections required to make the complete planning pipeline operational from Planning Workspace through to human approval boundary.

## Problem
The AI-OS planning pipeline has the following missing/blocked connections:
1. SelfLoopEngine → SelfPromptGenerator: No direct invocation of self-prompt generation phase
2. SelfPromptGenerator → PlanningService: Generated prompts not consumed by planning
3. PlanningService → LLM Council: Plans not subjected to multi-perspective review
4. LLM Council → Dashboard/approval: Reviewed plans not presented for human approval
5. Missing event correlations and proper canonical event usage throughout the pipeline

## Implementation Tasks

### 1. SelfLoopEngine Enhancement
Modify `src/aios/core/self_loop_engine.py` to:
- Add dependency injection for SelfPromptGenerator and PlanningService
- In `_execute_self_prompt_phase()`, invoke SelfPromptGenerator.generate() with synthesized lifecycle context
- Pass generated prompt to PlanningService.plan() via PlanningRequested event
- Ensure proper event correlation using canonical EventBus

### 2. SelfPromptGenerator Integration
Modify `src/aios/core/self_prompt_generator.py` to:
- Accept lifecycle context parameter in generate() method
- Validate and synthesize directives from context
- Return structured prompt suitable for planning consumption
- Maintain advisory-only markings per C14/C34

### 3. PlanningService Pipeline Connection
Modify `src/aios/services/planning.py` to:
- Accept and process advisory context from self-prompt generation
- Emit PlanningCompleted with reviewed plan structure
- Ensure plan includes both deterministic steps and LLM Council reviewed components
- Add subscription to PlanningRequested events from SelfLoopEngine

### 4. LLM Council Review Integration
Enhance the planning pipeline to:
- Route generated plans through LLMCouncil.deliberate_and_propose() 
- Apply six cognitive roles (analyst, contrarian, outsider, skeptic, specialist, simplifier)
- Return critiqued and synthesized plan for final review
- Maintain separation of concerns: Council advises, does not directive

### 5. Human Approval Boundary
Establish connection to:
- DashboardService.request_action() for planning.submit_user_message
- SecurityManager authorization check before presenting to human
- ProjectService persistence of planning workflow to Obsidian Git
- Clear approval/rejection events (PlanningCompleted/PlanRejected)

## Acceptance Criteria
- [ ] SelfLoopEngine invokes SelfPromptGenerator during self-prompt phase
- [ ] Generated prompts flow to PlanningService via canonical events
- [ ] PlanningService produces plans that include advisory context
- [ ] Plans are routed through LLM Council for multi-perspective review
- [ ] Reviewed plans reach human approval boundary via Dashboard
- [ ] All connections use canonical EventBus with proper correlation
- [ ] No direct service-to-service calls; all communication via events
- [ ] Advisory markings preserved per C14/C34 throughout pipeline
- [ ] Fail-closed authorization via SecurityManager maintained

## Dependencies
- SelfLoopEngine (M12-T6 #53 recovery)
- SelfPromptGenerator (M13 self-prompt integration)
- PlanningService (existing)
- LLM Council (existing)
- Dashboard Service (existing)
- Project Service (existing)
- Security Manager (existing)
- Canonical EventBus (C1, Task 5)

## Implementation Notes
This task represents the minimal governance boundary implementation required to connect the autonomous self-loop with human-in-the-loop planning approval. The implementation must preserve the authority hierarchy: SelfLoopEngine (authoritative) → SelfPromptGenerator (advisory) → Planning Service (advisory) → LLM Council (advisory) → Human Approval (authoritative).

All advisory components must maintain explicit provenance markings indicating their advisory nature per C14.