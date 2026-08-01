# -*- coding: utf-8 -*-
p = r'C:\Development\AI-OS\ARCHITECTURE_SPEC_PART8_STEP3.md'
with open(p, 'r', encoding='utf-8') as f:
    lines = f.readlines()

hi=None; ei=None
for i,l in enumerate(lines):
    if l.startswith('### 8.3.2.10'):
        hi=i
    if l.startswith('### 8.3.2.11'):
        ei=i

block = [
'### 8.3.2.10 Event Emission',
'',
'Every capability invocation MUST emit EventBus events at each lifecycle boundary (INV-EXEC-RT-001). All events carry `correlationId`, `causationId`, and a `ComponentIdentity` of `CapabilityInvocationEngine`.',
'',
'| Event | Trigger | Category | Payload |',
'|-------|---------|----------|---------|',
'| `aios.execution.control.capability_invocation_started` | Invocation begins | CONTROL | `contextId`, `nodeId`, `capabilityId`, `attemptCount`, `providerInfo` |',
'| `aios.execution.data.parameter_binding_complete` | Parameters resolved | DATA | `contextId`, `nodeId`, `resolvedParams` |',
'| `aios.execution.data.resource_check_completed` | Budget validation passed | DATA | `contextId`, `nodeId`, `budgetStatus` |',
'| `aios.execution.data.capability_invocation_completed` | Invocation SUCCESS, all criteria met | DATA | `contextId`, `nodeId`, `outputHash`, `metrics`, `latencyMs` |',
'| `aios.execution.diagnostic.capability_invocation_degraded` | Partial success | DIAGNOSTIC | `contextId`, `nodeId`, `degradationReason`, `partialOutputs` |',
'| `aios.execution.diagnostic.capability_invocation_failed` | Invocation FAILED | DIAGNOSTIC | `contextId`, `nodeId`, `error`, `tokensUsed`, `latencyMs` |',
'| `aios.execution.diagnostic.capability_invocation_timeout` | Wall-clock timeout exceeded | DIAGNOSTIC | `contextId`, `nodeId`, `elapsedMs`, `timeoutMs` |',
'| `aios.execution.data.resource_budget_exceeded` | Budget ceiling reached | DATA | `contextId`, `budgetName`, `consumed`, `limit` |',
'| `aios.execution.control.governance_gate_not_cleared` | Gate PENDING or DENIED | CONTROL | `gateId`, `status`, `approverRequired` |',
'| `aios.execution.audit.capability_output_contract_violation` | Output fails contract verification | AUDIT | `contextId`, `nodeId`, `expectedSchema`, `violationDetail` |',
'| `aios.execution.diagnostic.provider_unavailable` | Selected provider unreachable | DIAGNOSTIC | `providerType`, `region`, `attempt` |',
'',
'**Invariant CIE-EVNT-001:** Every capability invocation MUST result in exactly one terminal invocation event (COMPLETED, DEGRADED, or FAILED). A missing terminal event is an accountability gap and a conformance defect.',
'',
'**Invariant CIE-EVNT-002:** Event ordering for a capability sequence within one correlationId MUST respect the DAG topological order: events for node `i` precede events for node `j` wherever `i` is a declared predecessor of `j`.',
'',
]

lines[hi:ei] = [b+'\n' for b in block]
with open(p,'w',encoding='utf-8') as f:
    f.writelines(lines)
print('OK rewrote 8.3.2.10; range was', hi, ei)
