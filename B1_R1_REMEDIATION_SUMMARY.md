# B1-R1 Remediation: PlanningService + LLMCouncil Integration

## Summary

Implemented the B1-R1 remediation to connect PlanningService to the existing LLM Council while preserving the existing deterministic planner and following all specified constraints.

## Changes Made

### 1. Modified `src/aios/services/planning.py`

**Imports Added:**
- Added import for `LLMCouncil` and `LLMRole` from `aios.core.llm_council`

**Constructor Enhanced:**
- Added initialization of `self._llm_council = LLMCouncil()` 
- Added property `llm_council` for accessing the council instance

**Core Logic Updated (`handle_planning_requested`):**
- **Preserve Deterministic Planner**: The existing `self.plan(enhanced_payload)` call remains unchanged to generate the deterministic plan
- **Route Through LLMCouncil**: After deterministic plan generation, route the plan through `LLMCouncil.deliberate_and_propose()` for advisory review
- **Advisory-Only Integration**: Council results are attached as advisory context and never override the deterministic plan per ADR #10
- **Six Cognitive Roles**: Consult all six LLM Council roles (analyst, contrarian, outsider, skeptic, specialist, simplifier)
- **Builder Exclusion**: Enforce INV-009 - builder cannot self-approve (`builder_excluded=True`)
- **Failure Handling**: Handle LLMCouncil failures gracefully without fabricating successful review - log warning and continue with deterministic plan only
- **Information Preservation**: Maintain all required information flows:
  - Correlation ID preservation
  - Project ID from context
  - Original user request and objective
  - Self-prompt and lifecycle context
  - Planning metadata and provenance

### 2. Added Test Coverage (`tests/unit/test_planning_llm_council_integration.py`)

Created comprehensive unit tests verifying:
- Council consultation is requested for deterministic plans
- Advisory results are properly attached to PlanningCompleted events
- Graceful handling of LLMCouncil failures (no fabrication)
- Advisory status is explicitly marked as advisory-only per ADR #10
- All six cognitive roles are consulted
- Builder exclusion principle is enforced
- Correlation ID and project ID are preserved through the flow
- Council is not consulted when deterministic planner returns None

## B1-R1 Requirements Verification

✅ **Connect PlanningService to Existing LLM Council**: Uses existing `LLMCouncil` facade  
✅ **Preserve Existing Deterministic Planner**: Original `self.plan()` call unchanged  
✅ **EventBus Canonical Communication**: Continues to use `emit_core_event()`  
✅ **Authority Preservation**: Advisory-only, never overrides planner (ADR #10)  
✅ **Advisory vs Authoritative Distinctions**: Explicitly marked as advisory  
✅ **Failure Handling Without Fabrication**: Failures logged, deterministic plan proceeds  
✅ **Correlation ID Preservation**: Maintained throughout flow  
✅ **Event Type Reuse**: No new event types created  
✅ **Six Cognitive Roles**: Analyst, contrarian, outsider, skeptic, specialist, simplifier  
✅ **Builder Exclusion**: INV-009 enforced  
✅ **Information Flow Preservation**: All required context maintained  

## Integration Points

1. **Input**: PlanningRequested event (unchanged)
2. **Deterministic Planning**: Existing `self.plan()` method (unchanged)
3. **LLMCouncil Review**: New advisory step using existing council facade
4. **Output**: PlanningCompleted event with attached advisory results (enhanced)
5. **Failure Path**: PlanningFailed event for deterministic planning failures (unchanged)

## Backwards Compatibility

- All existing interfaces preserved
- No changes to event schemas emitted
- Deterministic planner behavior unchanged
- Existing tests should continue to pass
- Advisory information is additive, not disruptive

## Files Modified

- `src/aios/services/planning.py` - Core implementation
- `tests/unit/test_planning_llm_council_integration.py` - Test coverage