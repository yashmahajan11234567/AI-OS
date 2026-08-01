# -*- coding: utf-8 -*-
p = r'C:\Development\AI-OS\ARCHITECTURE_SPEC_PART8_STEP3.md'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

addition = '''
### 8.3.3.8 Client Failure Classification

Failure classification is delegated to the **RootCauseAnalyzer** (Core Manager, Part 3) and occurs BEFORE retry-strategy selection (INV-EXEC-FL-001). The classification follows Part 1 Sect 1.12.1 and resolves four classes:

```mermaid
flowchart TD
    FR["Invocation failure / degradation reported"] --> RCA["RootCauseAnalyzer.classify(error, metrics, attemptHistory)"]
    RCA --> CLS{Class}
    CLS -- TRANSIENT --> TR["Param-adjust (increase timeout / backoff)"]
    CLS -- DEGRADED --> DG["Capability-sub or model-sub"]
    CLS -- CRITICAL --> CR["Capability-sub -> model-sub -> workflow-restructure"]
    CLS -- FATAL --> FT["EMERGENCY ABORT (no retry; human escalate)"]
    TR --> RETRY["Retry within loop budget"]
    DG --> RETRY
    CR --> RETRY
    FT --> ABORT["Execution Context FAILED; Layer 9 route"]
```

| Classification | Definition | Keyword Examples (corrected taxonomy, risk R8.3-04) | Retry permitted | Default Strategy Stage |
|---------------|-----------|--------------------------------------------------|-----------------|------------------------|
| **TRANSIENT** | Temporary, self-correcting infra failure | `timeout`, `connection reset`, `rate limit`, `503`, `network`, `registry blip` | Yes | param-adjust |
| **DEGRADED** | Partial success, output present but suboptimal | `slow`, `partial`, `degraded`, `stale`, `low confidence` | Yes | capability-sub |
| **CRITICAL** | Permanent failure at capability/provider level | `invalid input`, `auth denied`, `not found`, `permission`, `quota exceeded`, `version incompatible` | Yes (different strategy) | capability-sub -> model-sub -> workflow-restructure |
| **FATAL** | Unrecoverable corruption | `integrity breach`, `contract violation`, `checkpoint unreachable`, `output hash mismatch` | NO | emergency abort |

**Keyword taxonomy completeness (risk R8.3-04):** The `transient_keywords` set in the RootCauseAnalyzer MUST include `timeout` (previously absent, a known defect). The taxonomy MUST be versioned and auditable; additions require a policy update recorded as a learning artefact.

**Invariant LER-CLS-001:** Classification MUST be emitted as a DIAGNOSTIC event (`aios.execution.diagnostic.failure_classified`) before any retry-strategy event. The classification event causationId MUST link to the triggering invocation-failure event (INV-EXEC-RT-003).

**Invariant LER-CLS-002:** FATAL classification MUST NOT enter any loop or retry pathway. It proceeds directly to emergency abort with guaranteed compensation (INV-EXEC-FL-005) and routes to Human Intervention (Layer 9).

**Invariant LER-CLS-003:** During active recovery (RETRY_IN_PROGRESS, HEALING_IN_PROGRESS, LOOP_ROLLBACK_IN_PROGRESS), the Learning Layer MUST NOT apply artefacts; learning is deferred to post-recovery (INV-EXEC-FL-003).

### 8.3.3.9 Loop State Machine

Each loop operates a state machine. The LER maintains one state machine instance per loop per Execution Context.

```mermaid
stateDiagram-v2
    [*] --> IDLE : loop created
    IDLE --> ITERATING : first node scheduled
    ITERATING --> AWAITING_RESULT : node invoked
    AWAITING_RESULT --> ITERATING : SUCCESS, next node
    AWAITING_RESULT --> CLASSIFYING : failure/degradation reported
    CLASSIFYING --> MOD_STRATEGY : classification NOT FATAL
    CLASSIFYING --> ABORTING : classification FATAL
    MOD_STRATEGY --> RETRYING : budget available
    MOD_STRATEGY --> EXHAUSTED : budget exhausted (all stages failed)
    RETRYING --> AWAITING_RESULT : modified attempt invoked
    EXHAUSTED --> ROLLING_BACK : loop N > 0
    EXHAUSTED --> ABORTING : loop N == 0
    ROLLING_BACK --> IDLE : context restored to loop N-1
    ITERATING --> COMPLETED : all loop nodes SUCCESS
    COMPLETED --> [*]
    ABORTING --> [*]
```

| State | Entry | Hold | Exit To |
|-------|-------|------|---------|
| **IDLE** | Loop created; checkpoint captured at iteration start | Awaiting node schedule | ITERATING |
| **ITERATING** | Next node scheduled | Node executing | AWAITING_RESULT (after invoke) / COMPLETED (all done) |
| **AWAITING_RESULT** | CIE informed invoke | Awaiting terminal invocation event | ITERATING (success) / CLASSIFYING (failure) |
| **CLASSIFYING** | Failure reported | RootCauseAnalyzer invoked | MOD_STRATEGY (recoverable) / ABORTING (FATAL) |
| **MOD_STRATEGY** | Classification non-FATAL | Strategy chosen (must differ from prior) | RETRYING (budget) / EXHAUSTED (no budget) |
| **RETRYING** | Modified attempt scheduled | New attempt invoked | AWAITING_RESULT |
| **EXHAUSTED** | All stages failed, budget = 0 | Rollback decision pending | ROLLING_BACK (N>0) / ABORTING (N=0) |
| **ROLLING_BACK** | Cross-loop rollback triggered | Restore loop N-1 checkpoint | IDLE (context restored) |
| **COMPLETED** | All loop nodes SUCCESS | Loop done | Next loop or execution completion |
| **ABORTING** | FATAL or loop-0 exhaustion abort | Compensation + human route | Terminal |

**Invariant LER-SM-001:** A single loop state machine MUST NOT be reentered while in AWAITING_RESULT. Concurrent node invocations within one loop occupy parallel state entries tracked by `nodeId`; the state machine keys transitions by nodeId, not by loop.

**Invariant LER-SM-002:** Transition into ROLLING_BACK MUST be idempotent: a duplicated exhaustion event MUST NOT trigger multiple restorations of the same checkpoint (INV-EC-RES-001 budget-write idempotancy, applied to rollback).

**Invariant LER-SM-003:** ABORTING MUST run guaranteed compensation (INV-EXEC-FL-005) before terminal. A loop entering ABORTING without running compensation is non-conformant.

### 8.3.3.10 Runtime Invariants

| Invariant | Condition | Verification |
|-----------|-----------|-------------|
| **INV-LER-RT-001** | The WorkflowManager MUST NOT implement inline retry. All retry decisions are owned by the LER (risk R8.3-01). | Static analysis: no retry loop in WorkflowManager |
| **INV-LER-RT-002** | Every loop iteration MUST create a checkpoint before executing nodes (INV-EXEC-RT-011). | Checkpoint audit: iteration-start events precede invocation events |
| **INV-LER-RT-003** | Every retry MUST produce a different `strategyId` and strategy hash from all prior attempts on the same node within the same loop (INV-EXEC-RT-004). | Strategy-hash uniqueness check |
| **INV-LER-RT-004** | Loop budget exhaustion MUST trigger cross-loop rollback to the previous loop, never silent termination (INV-EXEC-FL-002, INV-EXEC-STR-009). | Chaos test: budget exhaustion -> verify rollback event + restore |
| **INV-LER-RT-005** | Failure classification MUST precede retry-strategy selection (INV-EXEC-FL-001). | Event ordering: classified event precedes strategy-selected event |
| **INV-LER-RT-006** | During active recovery, Learning MUST be deferred (INV-EXEC-FL-003). | State guard: learning apply blocked during RETRYING/ROLLING_BACK/HEALING |
| **INV-LER-RT-007** | Rollback restoration MUST reproduce the exact captured loop-start state (INV-EXEC-RT-011, INV-EC-CP-001). | Restore equivalence test |
| **INV-LER-RT-008** | The hard wall-clock ceiling MUST be enforced independently and MUST escalate to FATAL after two breaches (Sect 8.3.3.7). | Stress test: exceed ceiling twice -> verify FATAL abort |
| **INV-LER-RT-009** | All Loop Engine events MUST carry correlationId and causationId and MUST be replayable (INV-EXEC-RT-009, EXEC-DG-010). | Replay test: identical event log -> identical loop decisions |
| **INV-LER-RT-010** | maxRetries MUST be a retry COUNT, so maxRetries=N permits N+1 total attempts (risk R8.3-03 corrected). | Budget property test: maxRetries=3 -> 4 attempts observed max |

### 8.3.3.11 RFC 2119 Conformance

#### Conformance Requirements

| Requirement | Level | Specification |
|-------------|-------|---------------|
| The Loop Engine MUST implement exactly five hierarchical loops | MUST | INV-EXEC-STR-007, LER-LOOP-001 |
| Each loop MUST have a retry budget, rollback target, checkpoint, timeout, and adaptive strategy | MUST | INV-EXEC-STR-007 |
| Retry MUST NEVER repeat identical execution; strategy MUST be modified every attempt | MUST | INV-EXEC-STR-008, INV-EXEC-RT-004, LER-STR-001 |
| Loop budget exhaustion MUST roll back to the previous loop, not terminate | MUST | INV-EXEC-STR-009, INV-EXEC-FL-002, LER-CRB-001 |
| Failure MUST be classified before retry-strategy selection | MUST | INV-EXEC-FL-001, LER-CLS-001 |
| FATAL classification MUST NOT retry; it MUST abort with compensation | MUST | INV-EXEC-FL-005, LER-CLS-002 |
| Learning application MUST be deferred during active recovery | MUST NOT (Learning MUST NOT apply) | INV-EXEC-FL-003, LER-RT-006 |
| WorkflowManager MUST NOT implement inline retry; retry MUST delegate to the LER | MUST NOT (WorkflowManager) | INV-LER-RT-001 |
| The first checkpoint MUST succeed without pre-existing state | MUST | INV-EC-CP-002, LER-CP-002 |
| Loop-start checkpoint restoration MUST reproduce exact state | MUST | LER-CP-003, INV-LER-RT-007 |
| The transient keyword taxonomy MUST include `timeout` | MUST | R8.3-04 corrected, LER-CLS-001 |
| maxRetries MUST be a retry count (N retries = N+1 total attempts) | MUST | LER-BUD-001, INV-LER-RT-010 |
| Jitter seeds MUST be deterministic per correlationId | MUST | LER-BUD-003 |
| ABORTING MUST run guaranteed compensation before terminal | MUST | LER-SM-003, INV-EXEC-FL-005 |
| Loop 0 exhaustion (all strategies failed) SHOULD escalate to human intervention | SHOULD | LER-CRB-001 special case |
| Intermediate loop checkpoints MAY be captured more frequently than required | MAY | LER-CP-001 |

#### Conformance Levels

| Level | Verification Method |
|-------|--------------------|
| **L1: Static** | Loop Engine schema: five loops defined with budget/rollback/checkpoint/timeout/strategy; no retry loops in WorkflowManager; transient keyword set contains timeout |
| **L2: Runtime** | Per-iteration checkpoint presence; strategy-hash uniqueness per retry; classification precedes strategy-selection |
| **L3: Integration** | End-to-end failing plan; verify loop iteration, classification, strategy modification, and rollback |
| **L4: Failure Injection** | Inject TRANSIENT/DEGRADED/CRITICAL/FATAL across loops; verify strategy chain, rollback edge, and compensation |
| **L5: Replay** | Identical event log -> identical loop decisions, strategy choices, and checkpoint restorations (EXEC-DG-010) |
| **L6: Audit** | Every retry-budget, strategy-selection, and rollback decision emits an AUDIT event with full correlation |
| **L7: Performance** | Loop iteration overhead (non-invocation): p50 < 30ms, p99 < 150ms; rollback restore p99 < 500ms |

#### Conformance Summary Matrix

| Requirement Category | L1 | L2 | L3 | L4 | L5 | L6 | L7 |
|----------------------|----|----|----|----|----|----|----|
| Five Hierarchical Loops | + | | + | | | | |
| Per-Loop Budget/Rollback/Checkpoint/Timeout/Strategy | + | | + | | | | |
| Strategic (non-identical) Retry | + | + | + | + | + | | |
| Cross-Loop Rollback | | + | + | + | + | + | |
| Failure Classification Before Strategy | | + | + | + | | | |
| FATAL Abort + Compensation | | | + | + | | + | |
| Learning Deferral During Recovery | | + | + | + | | | |
| WorkflowManager No Inline Retry | + | | + | | | | |
| First-Checkpoint Auto-Create | + | + | + | | | | |
| Checkpoint Restore Equivalence | | + | + | + | + | | |
| Timeout Taxonomy Completeness | + | + | + | | | | |
| maxRetries Semantics (count) | + | | + | + | | | |
| Deterministic Jitter Seeds | + | | | | + | | |
| Deterministic Replay | | | | | + | | |
| Loop Iteration Overhead | | | | | | | + |

---

END OF PART 8 SECTION 8.3.1-8.3.3 in ARCHITECTURE_SPEC_PART8_STEP3.md
''';

with open(p, 'a', encoding='utf-8') as f:
    f.write(addition)
print('OK 8.3.3.8-10 + closing:', len(addition), 'bytes')
