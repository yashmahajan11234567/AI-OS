# 8.7 Optimization Layer Architecture

## 8.7.1 Overview

The Optimization Layer (Layer 7) is responsible for analyzing learning artifacts and execution profiles to generate optimization policies that improve future executions. It operates as a policy-gated, deterministic process that consumes learning batches and execution metrics to produce validated optimization policies that are applied to capability plans before subsequent planning cycles.

The Optimization Layer MUST adhere to the EventBus-first principle, communicating exclusively through events with other layers. It MUST ensure deterministic operation, safety via invariant validation, traceability of all optimization decisions, and adherence to computational budgets.

## 8.7.2 Architecture Overview

The Optimization Layer follows a linear pipeline architecture comprising four primary components:

1. **Learning Evaluator** – Loads hints and signals from the Planning Memory (Execution Profile, success/failure patterns, historical effectiveness).
2. **Policy Synthesizer** – Generates candidate optimizations across the seven optimization domains based on enabled policy gates.
3. **Optimization Applicator** – Scores, selects, and applies candidate optimizations to produce an optimized plan, verifying all architectural invariants hold.
4. **Optimization Policy Store** – Interface to the Memory Manager's Optimization Policy Store for persisting versioned optimization policies with provenance.

The layer receives `LEARNING_BATCH_READY` events from the Learning Layer and emits `OPTIMIZATION_POLICY_PUBLISHED` events containing the newly generated optimization policies. Additionally, for each plan optimization cycle, it emits a `PLAN_OPTIMIZED` event detailing the before/after metrics and applied optimizations.

All communication flows through the EventBus owned by the Hermes Kernel, preserving causation and correlation IDs for deterministic replay.

## 8.7.3 Internal Components

| Component | Responsibility | Interfaces |
|-----------|----------------|------------|
| **LearningEvaluator** | Reads hints from Planning Memory (Execution Metadata, Execution Profiles, learning artifact effectiveness) | Reads from Memory Manager; emits `OPTIMIZATION_EVALUATION_COMPLETE` (internal) |
| **PolicySynthesizer** | Generates candidate optimizations for each of the seven domains where policy gates are enabled | Consumes evaluation hints; emits `OPTIMIZATION_CANDIDATES_GENERATED` |
| **OptimizationApplicator** | Scores candidates using Execution Profile and historical effectiveness; selects top candidates (max 3); applies optimizations to produce Plan’; verifies invariants | Emits `OPTIMIZATION_APPLIED` and `PLAN_OPTIMIZED` |
| **OptimizationPolicyStore** (via MemoryManager) | Persists optimization policies with versioning, provenance, confidence, and rollback capability | Reads/writes Optimization Policy Store; emits `OPTIMIZATION_POLICY_PUBLISHED` |

## 8.7.4 Responsibilities

The Optimization Layer MUST:

- Load hints from Planning Memory after each learning batch.
- Generate candidate optimizations only for optimization types where the corresponding policy gate (`planning.optimization.allow<Type>`) is enabled.
- Score each candidate using the current Execution Profile and historical effectiveness data.
- Select up to three highest-scoring candidates for application.
- Apply selected optimizations sequentially to produce an optimized Plan’.
- Verify that Plan’ satisfies ALL architectural invariants (INV-EXEC-STR, INV-EXEC-RT, etc.); if any violation occurs, automatically reject that optimization.
- Emit a `PLAN_OPTIMIZED` event containing before/after metrics, applied optimizations, and validation evidence.
- Persist the resulting optimization policy to the Optimization Policy Store with full provenance, confidence, versioning, and rollback procedures.
- Emit an `OPTIMIZATION_POLICY_PUBLISHED` event upon successful policy storage.
- Ensure deterministic operation: identical inputs (Learning Batch, Execution Profile, Policy Snapshots) must produce identical optimization decisions.
- Enforce a default budget of maximum three optimizations per plan and ≤10 seconds of computation time.
- Provide traceability by recording before/predicted/evidence for each optimization decision.
- Participate in deterministic replay by ensuring outputs are bit-identical given identical inputs and snapshots.

## 8.7.5 Lifecycle

The Optimization Layer lifecycle is tightly coupled to the Learning Layer's batch production:

1. **Idle State**: Awaits `LEARNING_BATCH_READY` event from the Learning Layer.
2. **Activation**: Upon receiving `LEARNING_BATCH_READY`, the Learning Evaluator loads hints from Planning Memory.
3. **Synthesis**: Policy Synthesizer generates candidate optimizations for all enabled optimization types.
4. **Application**: Optimization Applicator scores, selects, applies, and validates optimizations.
5. **Publication**: OptimizationPolicyStore persists the optimization policy; publishes `OPTIMIZATION_POLICY_PUBLISHED`.
6. **Completion**: Emits `PLAN_OPTIMIZED` for each optimized plan within the batch; returns to idle state.

The layer does not maintain persistent state between batches beyond what is stored in the Optimization Policy Store; each processing cycle is functionally independent given its inputs.

## 8.7.6 Runtime Behaviour

At runtime, the Optimization Layer exhibits the following characteristics:

- **Deterministic**: Given identical inputs (Learning Batch snapshot, Execution Profile snapshot, Policy Snapshot, Config Snapshot), the sequence of candidate generation, scoring, selection, and application yields identical optimized plans and emitted events.
- **Event-Driven**: All interactions occur via EventBus; no direct method invocations between layers are permitted in RUNNING state.
- **Budget-Aware**: Enforces a configurable limit on the number of optimizations applied per plan (default 3) and a maximum wall-clock time for optimization processing (default 10s).
- **Invariant-Guarded**: Every optimization application is guarded by automatic verification that all architectural invariants hold for the resulting plan; violations cause automatic rollback of that optimization step.
- **Traceable**: Each optimization decision logs the input hints, candidate details, scores applied, expected improvement, actual before/after metrics, and validation evidence.
- **Policy-Gated**: No optimization candidate is generated unless its corresponding policy gate is explicitly enabled in the active policy snapshot.
- **Versioned Output**: Published optimization policies are immutable, versioned (semantic), content-addressed (SHA-256), and include `generatedBy` and `timestamp` metadata.

## 8.7.7 Processing Pipeline

The Optimization Layer processes each learning batch through the following deterministic pipeline:

1. **Load Hints** (`LearningEvaluator`):
   - Input: `LEARNING_BATCH_READY` event payload (contains batch ID, timestamps, correlation ID).
   - Action: Query Planning Memory for Execution Profiles, execution metadata, and learning artifact effectiveness metrics relevant to the batch context.
   - Output: Evaluation hints (e.g., historical model performance, skill success rates, workflow efficiency).

2. **Generate Candidates** (`PolicySynthesizer`):
   - Input: Evaluation hints; policy snapshot indicating which optimization type gates are enabled.
   - Action: For each enabled optimization type, generate one or more candidate optimizations (e.g., for Cost Substitution: identify cheaper capable models; for Parallelism Tuning: identify parallelizable nodes).
   - Output: Set of candidate optimizations, each with type, description, input parameters, and predicted impact.

3. **Score Candidates** (`OptimizationApplicator`):
   - Input: Candidates, Execution Profile (current baseline performance), historical effectiveness data.
   - Action: Compute a score for each candidate using a deterministic scoring function that weighs predicted improvement against historical success likelihood and risk.
   - Output: Ranked list of candidates.

4. **Select & Apply** (`OptimizationApplicator`):
   - Input: Ranked candidates.
   - Action: Select top N candidates (N ≤ 3, per budget). For each selected candidate in rank order:
     - Apply the optimization to the current plan to produce a candidate plan.
     - Verify ALL architectural invariants hold for the candidate plan.
     - If verification passes, promote candidate plan to become the current plan for the next optimization step; record the applied optimization.
     - If verification fails, discard the candidate and proceed to next ranked candidate.
   - Output: Optimized Plan’ (or original plan if no optimizations applied), list of applied optimizations with before/after metrics.

5. **Emit Plan Optimized** (`OptimizationApplicator`):
   - Action: Emit `PLAN_OPTIMIZED` event containing:
     - Plan ID and version
     - Before metrics (execution time, cost, resource usage)
     - After metrics (estimated)
     - List of applied optimizations with predicted vs. actual estimates
     - Validation evidence (invariant check results)
     - Correlation and causation IDs.

6. **Persist Policy** (`OptimizationPolicyStore` via MemoryManager):
   - Input: List of applied optimizations, before/after metrics, validation evidence.
   - Action: Construct an optimization policy document encapsulating the applied optimizations, their parameters, expected benefits, and provenance.
   - Action: Store in Optimization Policy Store with semantic version, SHA-256 content hash, `generatedBy: "OptimizationLayer/x.y.z"`, and timestamp.
   - Output: Storage confirmation.

7. **Publish Optimization Policy** (`OptimizationPolicyStore`):
   - Action: Emit `OPTIMIZATION_POLICY_PUBLISHED` event containing:
     - Policy ID (UUIDv7)
     - Version (semver)
     - Content hash (SHA-256)
     - Generation timestamp
     - Source learning batch ID
     - Applied optimizations summary
     - Correlation ID from triggering `LEARNING_BATCH_READY`.

Each step is a pure function of its inputs and the current policy snapshot, ensuring determinism.

## 8.7.8 State Models

The Optimization Layer does not maintain persistent internal state machines; its behavior is defined by the processing pipeline. However, the following conceptual states apply during processing:

```
IDLE -->[LEARNING_BATCH_READY]--> EVALUATING -->[Hints Loaded]--> SYNTHESIZING -->[Candidates Generated]--> APPLYING -->[Optimization Applied/Rejected]--> (loop if more candidates) -->[Selection Complete]--> PUBLISHING -->[Policy Stored]--> EMITTING -->[Events Emitted]--> IDLE
```

- **IDLE**: Waiting for `LEARNING_BATCH_READY`.
- **EVALUATING**: Learning Evaluator querying Planning Memory.
- **SYNTHESIZING**: Policy Synthesizer generating candidates.
- **APPLYING**: Optimization Applicator scoring, selecting, applying, and validating optimizations.
- **PUBLISHING**: Persisting optimization policy to store.
- **EMITTING**: Publishing `PLAN_OPTIMIZED` and `OPTIMIZATION_POLICY_PUBLISHED` events.

### Optimization Policy Schema

The optimization policy persisted to the Optimization Policy Store conforms to the following logical structure (see JSON Schema definitions in section 8.7.11):

- `policyId`: UUIDv7
- `version`: Semantic version string
- `contentHash`: `"sha256:<hex>"`
- `generatedBy`: String (e.g., `"OptimizationLayer/1.0.0"`)
- `timestamp`: ISO8601 nanosecond timestamp
- `sourceBatchId`: UUIDv7 of the triggering `LEARNING_BATCH_READY` event
- `appliedOptimizations`: Array of optimization objects, each containing:
  - `type`: Optimization type (e.g., `"CostSubstitution"`)
  - `description`: Human-readable description
  - `parameters`: JSON object of optimization-specific parameters
  - `predictedImprovement`: Object with estimated metric deltas (time, cost, risk, etc.)
  - `validationEvidence`: Reference to invariant check results
- `provenance`: Object containing:
  - `learningArtifactsUsed`: Array of learning artifact IDs referenced
  - `executionProfileId`: UUIDv7 of Execution Profile used
  - `policySnapshotId`: UUIDv7 of policy snapshot used
  - `configSnapshotId`: UUIDv7 of config snapshot used

## 8.7.9 Event Flows

The Optimization Layer participates in the following event flows:

### Primary Input Flow
```
Learning Layer ->[LEARNING_BATCH_READY]-> Optimization Layer
```

### Internal Event Flow (conceptual, for traceability)
```
Optimization Layer ->[OPTIMIZATION_EVALUATION_COMPLETE]-> Optimization Layer
Optimization Layer ->[OPTIMIZATION_CANDIDATES_GENERATED]-> Optimization Layer
Optimization Layer ->[OPTIMIZATION_APPLIED]-> Optimization Layer
```

### Primary Output Flows
```
Optimization Layer ->[PLAN_OPTIMIZED]-> Execution Context / Planning Layer (for feedback)
Optimization Layer ->[OPTIMIZATION_POLICY_PUBLISHED]-> Learning Layer / Optimization Policy Store
```

### Error Flow
If invariant verification fails during application:
```
Optimization Layer ->[OPTIMIZATION_REJECTED]-> Optimization Layer (logging only; no external emission required)
```

All events carry the correlation ID from the original `LEARNING_BATCH_READY` event, and causation IDs linking each step.

## 8.7.10 Event Specification Tables

### Optimization Layer Events

| Event Type | Description | Correlation ID | Causation ID | Payload Summary |
|------------|-------------|----------------|--------------|-----------------|
| `aios.planning.optimization.evaluation_complete` | Learning Evaluator has finished loading hints | Same as triggering `LEARNING_BATCH_READY` | Previous optimization step or `LEARNING_BATCH_READY` | { evaluationHints: <json> } |
| `aios.planning.optimization.candidates_generated` | Policy Synthesizer has generated candidate optimizations | Same as triggering `LEARNING_BATCH_READY` | `evaluation_complete` | { candidates: [<optimizationCandidate>...] } |
| `aios.planning.optimization.applied` | An optimization candidate has been successfully applied and validated | Same as triggering `LEARNING_BATCH_READY` | Previous application or `candidates_generated` | { appliedOptimization: <optimizationObject>, planId: <uuid>, beforeMetrics: <metrics>, afterMetrics: <estimatedMetrics> } |
| `aios.planning.optimization.rejected` | An optimization candidate failed invariant validation (internal trace) | Same as triggering `LEARNING_BATCH_READY` | Previous application or `candidates_generated` | { rejectedOptimization: <optimizationObject>, reason: <invariantViolation> } |
| `aios.planning.optimization.plan_optimized` | Final optimized plan produced after applying selected optimizations | Same as triggering `LEARNING_BATCH_READY` | Last `applied` or `candidates_generated` if none applied | { planId: <uuid>, originalPlanId: <uuid>, appliedOptimizations: [<optimizationObject>...], beforeMetrics: <metrics>, afterMetrics: <estimatedMetrics>, validationEvidence: <evidence> } |
| `aios.planning.optimization.policy_published` | Optimization policy has been persisted to Optimization Policy Store | Same as triggering `LEARNING_BATCH_READY` | `plan_optimized` (or directly after evaluation if no optimizations applied) | { policyId: <uuid>, version: <semver>, contentHash: <sha256>, generatedBy: <string>, timestamp: <iso8601>, sourceBatchId: <uuid>, appliedOptimizationsSummary: <summary> } |

Note: The exact event type `LEARNING_BATCH_READY` has type `aios.planning.learning.batch_ready` (from Learning Layer).

## 8.7.11 JSON Schema Draft 2020-12 Definitions

The following schemas define the data structures used by the Optimization Layer. Reusable components from other layers (e.g., `ExecutionProfile`, `LearningArtifact`) are referenced where applicable.

### Optimization Event Envelope (extends base event envelope)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Base envelope for all optimization layer events",
  "type": "object",
  "required": ["eventId", "eventType", "correlationId", "causationId", "timestamp", "source", "version", "payload"],
  "properties": {
    "eventId": { "type": "string", "format": "uuid" },
    "eventType": { "type": "string", "pattern": "^aios\\.planning\\.optimization\\.[a-zA-Z_]+$" },
    "correlationId": { "type": "string", "format": "uuid" },
    "causationId": { "type": "string", "format": "uuid" },
    "timestamp": { "type": "string", "format": "date-time" },
    "source": { "type": "string", "enum": ["LearningEvaluator", "PolicySynthesizer", "OptimizationApplicator", "OptimizationPolicyStore"] },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "payload": { "type": "object" }
  },
  "additionalProperties": false
}
```

### Optimization Candidate
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "A candidate optimization generated by the Policy Synthesizer",
  "type": "object",
  "required": ["type", "description", "parameters", "predictedImprovement"],
  "properties": {
    "type": { "type": "string", "enum": ["CostSubstitution", "ParallelismTuning", "LatencyReordering", "RiskMitigation", "ResourceRightSizing"] },
    "description": { "type": "string" },
    "parameters": { "type": "object" },
    "predictedImprovement": {
      "type": "object",
      "description": "Estimated impact of applying this optimization",
      "additionalProperties": { "type": "number" }
    },
    "estimatedCostDelta": { "type": "number", "description": "Predicted change in cost (USD)" },
    "estimatedTimeDeltaMs": { "type": "number", "description": "Predicted change in execution time (milliseconds)" },
    "estimatedRiskDelta": { "type": "number", "minimum": -1.0, "maximum": 1.0, "description": "Predicted change in risk level (-1.0 to 1.0)" }
  },
  "additionalProperties": false
}
```

### Applied Optimization (extends Optimization Candidate)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "An optimization that has been successfully applied and validated",
  "allOf": [
    { "$ref": "#/definitions/OptimizationCandidate" },
    {
      "type": "object",
      "required": ["validationEvidence", "actualMetrics"],
      "properties": {
        "validationEvidence": {
          "type": "object",
          "description": "Evidence that all invariants held after application",
          "additionalProperties": true
        },
        "actualMetrics": {
          "type": "object",
          "description": "Measured or estimated metrics after application (used for before/after comparison)",
          "additionalProperties": { "type": "number" }
        }
      },
      "additionalProperties": false
    }
  ]
}
```

### Optimization Policy
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Optimization policy persisted to the Optimization Policy Store",
  "type": "object",
  "required": ["policyId", "version", "contentHash", "generatedBy", "timestamp", "sourceBatchId", "appliedOptimizations", "provenance"],
  "properties": {
    "policyId": { "type": "string", "format": "uuid" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "contentHash": { "type": "string", "pattern": "^sha256:[a-f0-9]{64}$" },
    "generatedBy": { "type": "string", "pattern": "^OptimizationLayer/\\d+\\.\\d+\\.\\d+$" },
    "timestamp": { "type": "string", "format": "date-time" },
    "sourceBatchId": { "type": "string", "format": "uuid" },
    "appliedOptimizations": {
      "type": "array",
      "items": { "$ref": "#/definitions/AppliedOptimization" },
      "minItems": 0,
      "maxItems": 3
    },
    "provenance": {
      "type": "object",
      "required": ["learningArtifactsUsed", "executionProfileId", "policySnapshotId", "configSnapshotId"],
      "properties": {
        "learningArtifactsUsed": {
          "type": "array",
          "items": { "type": "string", "format": "uuid" },
          "minItems": 0
        },
        "executionProfileId": { "type": "string", "format": "uuid" },
        "policySnapshotId": { "type": "string", "format": "uuid" },
        "configSnapshotId": { "type": "string", "format": "uuid" }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

### PLAN_OPTIMIZED Event Payload
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Payload for PLAN_OPTIMIZED event",
  "type": "object",
  "required": ["planId", "originalPlanId", "appliedOptimizations", "beforeMetrics", "afterMetrics", "validationEvidence"],
  "properties": {
    "planId": { "type": "string", "format": "uuid" },
    "originalPlanId": { "type": "string", "format": "uuid" },
    "appliedOptimizations": {
      "type": "array",
      "items": { "$ref": "#/definitions/AppliedOptimization" },
      "minItems": 0,
      "maxItems": 3
    },
    "beforeMetrics": {
      "type": "object",
      "description": "Metrics of the plan before optimization",
      "additionalProperties": { "type": "number" }
    },
    "afterMetrics": {
      "type": "object",
      "description": "Estimated metrics of the plan after optimization",
      "additionalProperties": { "type": "number" }
    },
    "validationEvidence": {
      "type": "object",
      "description": "Aggregated evidence that all invariants hold for the optimized plan",
      "additionalProperties": true
    }
  },
  "additionalProperties": false
}
```

### OPTIMIZATION_POLICY_PUBLISHED Event Payload
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "description": "Payload for OPTIMIZATION_POLICY_PUBLISHED event",
  "type": "object",
  "required": ["policyId", "version", "contentHash", "generatedBy", "timestamp", "sourceBatchId", "appliedOptimizationsSummary"],
  "properties": {
    "policyId": { "type": "string", "format": "uuid" },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "contentHash": { "type": "string", "pattern": "^sha256:[a-f0-9]{64}$" },
    "generatedBy": { "type": "string", "pattern": "^OptimizationLayer/\\d+\\.\\d+\\.\\d+$" },
    "timestamp": { "type": "string", "format": "date-time" },
    "sourceBatchId": { "type": "string", "format": "uuid" },
    "appliedOptimizationsSummary": {
      "type": "object",
      "description": "Summary of applied optimizations for audit and replay",
      "additionalProperties": true,
      "minProperties": 1
    }
  },
  "additionalProperties": false
}
```

## 8.7.12 Validation Rules

The Optimization Layer MUST enforce the following validation rules:

1. **Policy Gate Compliance**: No optimization candidate shall be generated for a type whose corresponding policy gate (`planning.optimization.allow<Type>`) is disabled in the active policy snapshot.
2. **Budget Limit**: No more than three (3) optimizations may be applied to a single plan within one optimization cycle.
3. **Time Budget**: The total wall-clock time spent in the Optimization Applicator (scoring, selection, application, validation) MUST not exceed 10 seconds by default (configurable via policy).
4. **Invariant Preservation**: Every applied optimization MUST result in a plan that satisfies ALL architectural invariants (INV-EXEC-STR-001 through INV-EXEC-STR-015, INV-EXEC-RT-001 through INV-EXEC-RT-012, etc.). Verification MUST be performed automatically after each application step.
5. **Deterministic Scoring**: The scoring function used to rank candidates MUST be deterministic given identical inputs (candidates, Execution Profile, historical effectiveness data).
6. **Non-Negative Resource Estimates**: Predicted resource deltas (cost, time) MUST be expressed as real numbers; negative values indicate reduction, positive values increase.
7. **Provenance Completeness**: Every optimization policy MUST reference the specific learning artifacts, execution profile, policy snapshot, and config snapshot that contributed to its generation.
8. **Content Addressing**: The `contentHash` of an optimization policy MUST be the SHA-256 hash of the canonical JSON representation of the policy object.
9. **Version Semantics**: The `version` field MUST follow semantic versioning; breaking changes to optimization policy structure MUST increment the major version.
10. **Generated By Format**: The `generatedBy` field MUST follow the format `OptimizationLayer/<major>.<minor>.<patch>` matching the implementing component version.

## 8.7.13 Runtime Invariants

The Optimization Layer MUST uphold the following runtime invariants:

- **INV-OPT-1 (Safety)**: If applying an optimization would cause a violation of ANY architectural invariant, the optimization MUST be automatically rejected and not included in the optimized plan.
- **INV-OPT-2 (Determinism)**: Given identical inputs (Learning Batch snapshot, Execution Profile snapshot, Policy Snapshot, Config Snapshot), the Optimization Layer MUST produce identical optimization decisions, applied optimizations, and emitted events.
- **INV-OPT-3 (Traceability)**: Every optimization decision MUST be recorded with before/predicted/evidence data enabling audit and replay verification.
- **INV-OPT-4 (Budget)**: The Optimization Layer MUST enforce a configurable maximum number of optimizations per plan (default 3) and a maximum processing time (default 10s).
- **INV-EVT-1 through INV-EVT-4**: All optimization layer events MUST share the correlation ID of the triggering `LEARNING_BATCH_READY` event; causation graph MUST be acyclic and rooted at the `LEARNING_BATCH_READY` event; same-category events MUST be delivered in timestamp order per correlation ID; every FAILED transition (optimization rejection) MUST emit `*.rejected` event.
- **INV-EXEC-LAYER-001**: All communication with other layers MUST occur exclusively through the EventBus; no direct method calls or shared state are permitted in RUNNING state.
- **INV-STRUCT-2 (Snapshot Isolation)**: The Optimization Layer MUST operate on immutable snapshots of the Execution Profile, Policy Snapshot, and Config Snapshot taken at the start of processing the `LEARNING_BATCH_READY` batch; no intermediate updates shall be visible during processing.
- **INV-STRUCT-4 (Manifest Pinning)**: Any optimization that references specific capability versions MUST use exact versions with content hashes; no version ranges or "latest" tags are permitted.
- **INV-EXEC-RT-009 (Deterministic Replay Participation)**: The Optimization Layer MUST participate in deterministic replay by ensuring that replay from recorded snapshots and event log produces bit-identical optimization decisions and outputs.
- **INV-EXEC-RT-010 (Vendor Independence)**: Optimization decisions MUST NOT depend on specific vendor implementations; all requirements MUST be expressed through capability manifests and provider requirements.

## 8.7.14 Error Handling

The Optimization Layer handles errors as follows:

- **Validation Failures**: If an optimization candidate fails invariant validation, it is logged via an `OPTIMIZATION_REJECTED` event (internal trace) and the next candidate is considered. This does NOT halt processing.
- **Processing Errors**: If an unexpected error occurs during candidate generation, scoring, or application (e.g., null pointer, invalid input), the Optimization Layer MUST emit a diagnostic event (`aios.planning.optimization.diagnostic_error`) with error details and skip the current batch, continuing to ingest subsequent batches.
- **Policy Store Failures**: If persisting the optimization policy fails, the Optimization Layer SHALL retry up to three times with exponential backoff; if persistent failure occurs, it SHALL emit an error event (`aios.planning.optimization.policy_store_failure`) and continue without publishing a policy for that batch (the batch is still considered processed).
- **Event Bus Failures**: If publishing an event fails, the Layer SHALL retry according to EventBus retry policy; repeated failures SHALL be logged and may trigger system-wide degradations per the Observability Service.
- **Invariant Violation During Processing**: If the Optimization Layer itself enters an inconsistent state (e.g., internal data corruption), it SHALL transition to a faulted state and emit a critical diagnostic event; recovery requires operator intervention as this violates INV-OPT-1.

Error handling NEVER compromises the deterministic nature of successful processing paths; error paths are logged for diagnostics but do not affect the core optimization algorithm's determinism for successful batches.

## 8.7.15 Security Considerations

The Optimization Layer adheres to the following security principles:

- **Input Validation**: All inputs from the Learning Batch and Planning Memory are treated as untrusted; schema validation is performed before use.
- **Least Privilege**: The Optimization Layer ONLY reads from the Planning Memory and Optimization Policy Store; it does not write to any other memory domains or external systems.
- **No Code Execution**: Optimization policies are data-only (JSON) and contain no executable code; they are interpreted by the Planner during subsequent planning cycles.
- **Information Flow**: Optimization policies do not introduce new confidential data; they contain only metrics, parameters, and references to existing artifacts.
- **Auditability**: All optimization decisions are fully traceable via emitted events and persisted policies, enabling forensic analysis.
- **Denial-of-Service Mitigation**: Per-batch time and optimization count limits prevent resource exhaustion attacks via malicious learning batches.
- **Supply Chain Security**: Optimization policies are versioned and content-addressed; any tampering is detectable via hash mismatch.

The Optimization Layer does not introduce new attack surfaces beyond those inherent in the EventBus and Memory Manager interfaces, which are secured elsewhere.

## 8.7.16 Deterministic Replay Requirements

To support deterministic replay, the Optimization Layer MUST:

1. **Consume Only Snapshots**: Use immutable snapshots of the Execution Profile, Policy Snapshot, and Config Snapshot captured at the start of processing the `LEARNING_BATCH_READY` batch.
2. **Deterministic Algorithms**: Ensure that candidate generation, scoring, selection, and application algorithms are deterministic functions of their inputs.
3. **Fixed Tie-Breaking**: When scores are equal, break ties using lexicographic ordering of optimization type strings (e.g., `"CostSubstitution"` < `"LatencyReordering"` < `"ParallelismTuning"` < `"RiskMitigation"` < `"ResourceRightSizing"`).
4. **Record Inputs**: Emit events that reference the exact snapshots used (via `sourceBatchId` linking to the `LEARNING_BATCH_READY` event, which itself references snapshot IDs).
5. **Verify Outputs**: During replay, the `PLAN_OPTIMIZED` and `OPTIMIZATION_POLICY_PUBLISHED` events MUST be bit-identical to the originals when inputs are identical.
6. **External Side Effects Excluded**: The Optimization Layer MUST NOT perform any external side effects (I/O, network calls, system calls) during the core optimization logic; all interactions with Memory Manager and EventBus are mediated through defined interfaces that are themselves replayable or mocked.
7. **Randomness Prohibited**: The use of random number generators, current timestamps, or any non-deterministic hardware features is strictly prohibited within the optimization logic.

## 8.7.17 Conformance Requirements

An implementation of the Optimization Layer MUST satisfy the following:

- Implement the exact seven-step processing pipeline described in section 8.7.7.
- Enforce INV-OPT-1 through INV-OPT-4 for all optimization decisions.
- Emit `OPTIMIZATION_POLICY_PUBLISHED` and `PLAN_OPTIMIZED` events for each processed learning batch.
- Respect optimization policy gates (`planning.optimization.allow<Type>`) when generating candidates.
- Limit optimizations to a maximum of three per plan with a default processing time budget of ≤10 seconds.
- Verify that ALL architectural invariants hold for any optimized plan before emitting `PLAN_OPTIMIZED`.
- Store optimization policies in the Optimization Policy Store with versioning, provenance, content hashing, and `generatedBy` metadata.
- Participate in deterministic replay by ensuring deterministic outputs from deterministic inputs as specified in section 8.7.16.
- Use the JSON schemas defined in section 8.7.11 for all event payloads and persisted policies.
- Adhere to the RFC-2119 terminology throughout implementation and documentation.
- Maintain backward compatibility: minor and patch version updates to the Optimization Layer MUST not break replay of previously recorded sessions.

## 8.7.18 Change Log

- **Version 1.0.0** (2026-07-29): Initial release as defined in PART8_CONTEXT.md Section 25 (Optimization Assumptions) and refined for Section 8.7 (Optimization Layer Architecture) per the AI-OS Architecture Specification.