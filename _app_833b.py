# -*- coding: utf-8 -*-
p = r'C:\Development\AI-OS\ARCHITECTURE_SPEC_PART8_STEP3.md'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

addition = '''

### 8.3.3.4 Strategic Retry Modification

Retry in the Loop Engine is **strategic, not blind** (INV-EXEC-STR-008). Every retry MUST modify the execution strategy. Identical retry is a conformance violation. The LER applies a deterministic, ordered strategy-modification chain, choosing the cheapest sufficient modification first.

```mermaid
flowchart TD
    F["Failure classified\n(TRANSIENT/DEGRADED/CRITICAL/FATAL)"] --> S1
    S1["1. param-adjust\n(modify node parameters /\ntimeout / backoff)"] --> OK1{Succeeded?}
    OK1 -- yes --> DONE["Attempt retried with modified params"]
    OK1 -- no --> S2
    S2["2. capability-sub\n(substitute equivalent capability)"] --> OK2{Succeeded?}
    OK2 -- yes --> DONE
    OK2 -- no --> S3
    S3["3. model-sub\n(substitute provider / model)"] --> OK3{Succeeded?}
    OK3 -- yes --> DONE
    OK3 -- no --> S4
    S4["4. workflow-restructure\n(re-plan affected subgraph)"] --> OK4{Succeeded?}
    OK4 -- yes --> DONE
    OK4 -- no --> EXH["Budget exhausted ->\ncross-loop rollback (\u00a78.3.3.5)"]
    F -- FATAL --> ABORT["Emergency abort (no retry)"]
```

| Strategy Stage | Modification | When Chosen | Recovery Artefact |
|----------------|--------------|-------------|--------------------|
| **1. param-adjust** | Modify node parameters, increase timeout, switch backoff curve | TRANSIENT (transient infra) | `strategyId`, `paramDiff` |
| **2. capability-sub** | Substitute an equivalent capability (different version or source | DEGRADED, CRITICAL (capability fault) | `strategyId`, `originalCapability`, `substituteCapability` |
| **3. model-sub** | Substitute provider/model behind the capability (EXEC-P-015) | CRITICAL (provider fault, degraded quality) | `strategyId`, `originalProvider`, `substituteProvider` |
| **4. workflow-restructure** | Re-plan the affected subgraph via the Planning Layer (Sect 8.2) | Repeated CRITICAL, dependency-chain failures | `strategyId`, `replannedSubgraph` |

**Invariant LER-STR-001:** Every retry attempt MUST carry a `strategyId` and a strategy hash that differs from ALL prior attempts in the same loop for the same node (INV-EXEC-RT-004). The LER MUST compute a strategy hash over the chosen modification and refuse identical-hash retries.

**Invariant LER-STR-002:** Strategy chain ordering MUST be irreversible within a single node: param-adjust is attempted before capability-sub, which is attempted before model-sub, which is attempted before workflow-restructure. Skipping a stage requires an explicit recorded justification and is only valid for FATAL (abort) or for a recovery policy that documents why the stage is inapplicable.

**Invariant LER-STR-003:** Workflow restructure (stage 4) MUST delegate to the Planning Layer (Sect 8.2) rather than mutate the plan inline. The LER MUST NOT construct new capability graphs itself.

### 8.3.3.5 Cross-Loop Rollback

When a loops retry budget is exhausted AND all four strategy stages have failed for the failing node, the LER performs **cross-loop rollback** (INV-EXEC-STR-009, INV-EXEC-FL-002). Rollback does NOT terminate execution; it restores the previous loop and resumes there with fresh context (typically informed by the failure that caused exhaustion).

```mermaid
sequenceDiagram
    participant LER as LoopEngine
    participant ECM as ExecutionContextManager
    participant CPM as CheckpointManager
    participant CIE as CapabilityInvocationEngine
    participant EB as EventBus

    Note over LER: Loop N budget exhausted, all strategies failed
    LER->>EB: emit(retry_budget_exhausted, {loopN, nodeId})
    LER->>EB: emit(loop_rollback_initiated, {fromLoop:N, toLoop:N-1})
    LER->>CPM: restore(loopStartCheckpoint[N-1])
    CPM-->>LER: ExecutionContextSnapshot (loop N-1 start)
    LER->>ECM: reconstruct_context(snapshot)
    ECM-->>LER: CONTEXT_RESTORED { contextId, resumePoint }
    LER->>EB: emit(checkpoint_restored, {checkpointId, correlationId})
    Note over LER: Loop N-1 resumes with fresh budget; failure evidence attached
    LER->>CIE: resume_invocations(contextId, from=loopStart[N-1])
```

| Rollback Edge | From Loop | To Loop | Restored State | Carry-Over |
|---------------|-----------|---------|-----------------|------------|
| Research -> start | 0 | (none) | n/a (initial) | n/a |
| Planning -> Research | 1 | 0 | Loop 0 start checkpoint | Failure evidence from loop 1 |
| Implementation -> Planning | 2 | 1 | Loop 1 start checkpoint | Failure evidence from loop 2 |
| Testing -> Implementation | 3 | 2 | Loop 2 start checkpoint | Failure evidence from loop 3 |
| Deployment -> Testing | 4 | 3 | Loop 3 start checkpoint | Failure evidence from loop 4 |

**Special case - loop 0 exhaustion:** Loop 0 (Research) has no prior loop. Its rollback target is the loop start (re-attempt research from scratch). If loop 0 is exhausted with all strategies failed, the LER MUST escalate: emit `aios.execution.control.execution_failed`, mark the Execution Context FAILED, and route to Human Intervention (Layer 9). Global abort across all five loops is permitted only after loop 0 exhaustion.

**Invariant LER-CRB-001:** Cross-loop rollback MUST restore the EXACT checkpoint captured at the target loop start (loop N-1 start). Partial or approximate restoration breaks determinism (INV-EC-CP-001) and is a conformance defect.

**Invariant LER-CRB-002:** Rollback MUST preserve failure evidence as carry-over metadata in the restored context, so the resumed loop N-1 can select a different strategy informed by the failure. Carry-over is appended to the context journal; it MUST NOT mutate immutable bindings (INV-EC-BIND-002).

**Invariant LER-CRB-003:** Rollback MUST NOT be triggered for FATAL classification. FATAL proceeds directly to emergency abort (Sect 8.3.3.8); rollback of a FATAL invocation would re-introduce the corruption.

### 8.3.3.6 Checkpoint Integration

The Loop Engine integrates with the Execution Context (Sect 8.3.1.7) and the CheckpointManager (Part 3) at every loop iteration boundary.

```mermaid
flowchart TD
    LIS["Loop iteration start"] --> CAP["ECM: serialise context ->\nCheckpointManager.create_checkpoint"]
    CAP --> CID["checkpointId assigned;\nloopState.checkpointId updated"]
    CID --> RUN["CIE executes node(s) for this iteration"]
    RUN --> RES{Result}
    RES -- SUCCESS --> NXT["Proceed to next node / next iteration"]
    RES -- recoverable failure --> MOD["Strategy modification (\u00a78.3.3.4)"]
    MOD --> Restored["Retry from same checkpoint\n(no new checkpoint)"]
    RES -- budget exhausted --> RCB["Cross-loop rollback\nrestore loop N-1 checkpoint (\u00a78.3.3.5)"]
    Restored --> RUN
    RCB --> LIS
```

| Checkpoint Trigger | Content | Purpose | Restore Target |
|--------------------|---------|---------|-----------------|
| Loop iteration start | Full context + loop budgets | Per-iteration recovery | Loop iteration N |
| Loop budget exhausted | Full context + exhaustion evidence | Cross-loop rollback source-of-truth | Prior loop start |
| Strategy modification chosen | Full context + chosen `strategyId` | Deterministic replay of retry | Modified retry attempt |
| Loop completion | Full context + completed-node set | Forward progress anchor | Next loop start |

**Invariant LER-CP-001:** The LER MUST create a checkpoint at every loop iteration start (INV-EXEC-RT-011). A loop iteration that executes without a preceding checkpoint is non-conformant.

**Invariant LER-CP-002:** The first checkpoint for an Execution Context MUST succeed without pre-existing state (risk R8.3-02, resolved): the ECM auto-creates a minimal execution state on first checkpoint (INV-EC-CP-002).

**Invariant LER-CP-003:** Restoring a loop-start checkpoint MUST reproduce identical loop budgets, capability bindings, gate statuses, and node progress to the original capture (INV-EC-CP-001). Divergence on restore is a conformance defect.

### 8.3.3.7 Timeout Handling

Each loop declares a wall-clock timeout (default table in Sect 8.3.3.2). Timeouts are classified and routed to the LER, not treated as transient infra noise.

| Timeout Type | Source | Classification | LER Action |
|--------------|--------|---------------|------------|
| **Node timeout** | `nodes[].timeoutMs` exceeded | TRANSIENT (default) -> DEGRADED if repeated | Strategy modification: increase timeout (param-adjust), then capability-sub |
| **Loop timeout** | Loop default timeout exceeded | DEGRADED | Strategy modification across remaining nodes; if budget already low, trigger rollback |
| **Budget-elapsed** | `ContextBudget.maxDurationMs` exceeded | CRITICAL | Param-adjust (extend) if contingency permits, else cross-loop rollback |
| **Hard wall-clock** | Absolute execution ceiling (safety bound) | CRITICAL -> FATAL if breached twice | Cross-loop rollback; if loop 0 exhausted, abort |

**Timeout interaction with budgets:** A timeout MUST consume a retry budget unit only when it results in an actual retry. A monitoring timeout that merely pauses (e.g., a slow-but-progressing invocation) MUST NOT decrement the budget. This prevents budget poisoning from slow capabilities.

**Invariant LER-TO-001:** Timeout classification MUST occur before retry-strategy selection (INV-EXEC-FL-001). Treating all timeouts as uniform TRANSIENT is a conformance defect; repeated identical timeouts for a capability MUST escalate to DEGRADED or CRITICAL.

**Invariant LER-TO-002:** A hard wall-clock ceiling MUST exist and MUST be enforced independently of per-loop and per-node timeouts. Breaching it twice is FATAL and routes to emergency abort (no rollback).

''';

with open(p, 'a', encoding='utf-8') as f:
    f.write(addition)
print('OK 8.3.3.4-7:', len(addition), 'bytes')
