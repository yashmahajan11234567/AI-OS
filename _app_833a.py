# -*- coding: utf-8 -*-
p = r'C:\Development\AI-OS\ARCHITECTURE_SPEC_PART8_STEP3.md'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

addition = '''

---

## 8.3.3 Loop Engine Runtime

### 8.3.3.1 Purpose

The Loop Engine Runtime (LER) is the **hierarchical retry-and-recovery substrate** for execution. It replaces flat retry chains with five hierarchical execution loops, each with its own retry budget, rollback target, checkpoint, timeout, and adaptive strategy. The LER consumes the RetryManager (Core Manager, Part 3) as a budget-tracking service and orchestrates iteration in concert with the WorkflowManager (Core Manager M7). The LER realises architectural principles **EXEC-P-005** (Strategic Retry, Not Blind Retry), **EXEC-P-013** (Loops Over Retries), and the structural invariants INV-EXEC-STR-007, INV-EXEC-STR-008, and INV-EXEC-STR-009.

**Why the Loop Engine exists:**

| Reason | Description |
|--------|-------------|
| **Bounded failure domains** | Each loop isolates a stage of the lifecycle (research, planning, implementation, testing, deployment). A failure in one loop does not immediately abort the whole execution. |
| **Strategic modification** | Retry MUST NEVER repeat identical execution (INV-EXEC-STR-008). Every retry modifies the strategy using failure analysis. |
| **Cross-loop recovery** | When a loops budget is exhausted, execution rolls back to the PREVIOUS loop (INV-EXEC-STR-009), not to global termination. This enables re-planning with new information. |
| **Checkpoint continuity** | Each loop iteration checkpoints via the Execution Context (Sect 8.3.1.7), so any iteration can be restored deterministically (INV-EXEC-RT-011). |
| **Failure-aware strategy** | Failure classification (Sect 8.3.3.8) occurs BEFORE retry-strategy selection (INV-EXEC-FL-001), so the chosen strategy matches the failure class. |

**Ownership vs. delegation:** The LER is a clear authority boundary. The WorkflowManager owns the DAG topology and checkpoint persistence; the RetryManager owns budget accounting and backoff computation. The LER owns loop iteration state machines, strategy selection, cross-loop rollback, and the integration of failure classification with retry decisions. Inline retry logic in the WorkflowManager (identified risk R8.3-01) is therefore forbidden: the WorkflowManager delegates all retry to the LER.

### 8.3.3.2 Five Hierarchical Loops

The Loop Engine operates over exactly **five (5)** hierarchical loops, matching the structural invariant INV-EXEC-STR-007. Loops are ordered and nested; a failure exhausting a loops budget rolls back to the prior loop.

```mermaid
flowchart LR
    L0["Research Loop\n(budget, rollback->start,\ncheckpoint, timeout)"] --> L1
    L1["Planning Loop\n(rollback->Research)"] --> L2
    L2["Implementation Loop\n(rollback->Planning)"] --> L3
    L3["Testing Loop\n(rollback->Implementation)"] --> L4
    L4["Deployment Loop\n(rollback->Testing)"]
    L4 -.exhaustion across all loops.-> ABRT["Global Abort /\nHuman Escalation"]
    L0 -.each loop: classify failure BEFORE retry.-> LE["Failure Classification\n(TRANSIENT/DEGRADED/\nCRITICAL/FATAL)"]
    LE --> STR["Strategy Selection\n(param-adjust -> cap-sub ->\nmodel-sub -> workflow-restructure)"]
    STR --> L0
```

| Loop Index | Loop Name | Scope of Capability Nodes | Rollback Target | Default Retry Budget | Default Timeout |
|-----------|-----------|---------------------------|-----------------|----------------------|-----------------|
| **0** | **Research** | Information gathering, registry query, web discovery | Loop start (no prior loop) | 3 retries | 120s |
| **1** | **Planning** | Plan refinement, candidate ranking, governance-requested re-plan | Loop 0 (Research) | 3 retries | 180s |
| **2** | **Implementation** | Code generation, skill execution, structural changes | Loop 1 (Planning) | 4 retries | 600s |
| **3** | **Testing** | Test generation, test execution, verification gates | Loop 2 (Implementation) | 4 retries | 300s |
| **4** | **Deployment** | Deployment, rollout, smoke checks, release verification | Loop 3 (Testing) | 2 retries | 900s |

**Loop binding:** Each CapabilityPlan node carries a `loopBinding` (Sect 8.2.6.9) declaring the loop it belongs to. Nodes with no explicit `loopBinding` default to the loop whose scope matches the node classification, resolved at materialisation (Sect 8.3.1.3). A node MAY NOT belong to more than one loop.

**Invariant LER-LOOP-001:** Exactly five loops exist per execution. Adding, removing, or merging loops requires ARB approval (INV-EXEC-STR-007). Loop ordering is fixed: 0 < 1 < 2 < 3 < 4.

**Invariant LER-LOOP-002:** A retry-attempt within loop N MUST remain within loop N unless the loop budget is exhausted. A retry strategy MAY request cross-loop rollback only after budget exhaustion (INV-EXEC-STR-009).

### 8.3.3.3 Retry Budgets

Each loop maintains a **RetryBudget**. The budget semantics follow the corrected standard (risk R8.3-03): `maxRetries` is the retry COUNT, so `maxRetries = N` permits `1 initial attempt + N retries = N + 1 total attempts`. The budget is decremented once per retry (not per total call).

```json
{
  "loopIndex": 0,
  "loopName": "RESEARCH",
  "retryBudget": {
    "maxRetries": 3,
    "remainingRetries": 3,
    "exhausted": false,
    "backoff": "ADAPTIVE",
    "baseDelayMs": 1000,
    "maxDelayMs": 30000,
    "jitterMs": 200
  },
  "attemptHistory": [
    { "attempt": 1, "strategy": "INITIAL", "classification": null, "latencyMs": 450, "status": "SUCCESS" }
  ]
}
```

**Budget contract:**

| Field | Semantics |
|-------|-----------|
| `maxRetries` | Retry COUNT (not total attempts). `maxRetries = 3` means up to 3 retries after the first attempt. |
| `remainingRetries` | Decremented on each retry decision. When it reaches 0 the loop is `exhausted`. |
| `exhausted` | `true` when `remainingRetries == 0`. Triggers cross-loop rollback (Sect 8.3.3.5). |
| `backoff` | One of `CONSTANT`, `LINEAR`, `EXPONENTIAL`, `ADAPTIVE`. `ADAPTIVE` chooses based on failure class (Sect 8.3.3.8). |
| `baseDelayMs` / `maxDelayMs` | Bounds on the inter-attempt delay. |
| `jitterMs` | Stochastic jitter to decorrelate retries; jitter seed MUST come from the correlation-scoped RNG for deterministic replay. |

**Invariant LER-BUD-001:** A loop MUST NOT permit more than `maxRetries + 1` attempts. The RetryManager MUST reject any retry request that would exceed the budget; the LER MUST treat that rejection as loop exhaustion.

**Invariant LER-BUD-002:** Budget exhaustion MUST emit `aios.execution.control.retry_budget_exhausted` and MUST NOT silently absorb the failure (INV-EXEC-FL-002). Silent absorption is a conformance defect.

**Invariant LER-BUD-003:** The jitter seed MUST be deterministic per correlationId. Random seeds initialised from wall-clock time or external entropy break deterministic replay (EXEC-DG-010) and are prohibited.

''';

with open(p, 'a', encoding='utf-8') as f:
    f.write(addition)
print('OK 8.3.3.1-3:', len(addition), 'bytes')
