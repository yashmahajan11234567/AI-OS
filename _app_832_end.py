# -*- coding: utf-8 -*-
p = r'C:\Development\AI-OS\ARCHITECTURE_SPEC_PART8_STEP3.md'
with open(p, 'r', encoding='utf-8') as f:
    content = f.read()

addition = '''

---

### 8.3.2.12 Invariants

#### Structural Invariants

| Invariant | Condition | Verification |
|-----------|-----------|--------------|
| **INV-CIE-STR-001** | The CIE MUST be the only runtime pathway that invokes capabilities. No other Layer 4 component may issue Facade Service calls directly. | Static analysis: only CIE references Facade Service execute APIs |
| **INV-CIE-STR-002** | The CIE MUST invoke capabilities ONLY through Capability Facade Services (Part 6). Direct Core Manager access from the CIE is prohibited (INV-EXEC-STR-006). | Static analysis: no `kernel.<manager>` calls in CIE source |
| **INV-CIE-STR-003** | The CIE MUST NOT embed vendor-specific logic. All vendor knowledge is encapsulated in Provider Adapters behind Facade Services (INV-EXEC-STR-014). | Static analysis: no vendor SDK imports in CIE |
| **INV-CIE-STR-004** | The CIE MUST be implemented as a Service (BaseService-derived) registered in the ServiceRegistry and owning the `aios.execution.invocation` source identity. | ServiceRegistry audit |

#### Runtime Invariants

| Invariant | Condition | Verification |
|-----------|-----------|--------------|
| **INV-CIE-RT-001** | Every capability invocation MUST emit a terminal event (COMPLETED / DEGRADED / FAILED). No invocation outcome may be silently dropped. | Event trace audit per correlationId |
| **INV-CIE-RT-002** | Resource budget MUST be validated BEFORE any capability invocation side effect (INV-EXEC-RT-008). | Budget-check event precedes invocation-start event |
| **INV-CIE-RT-003** | Parameter binding MUST be deterministic: identical node params, journal, and environment snapshot produce identical bound params (EXEC-DG-010). | Determinism property test |
| **INV-CIE-RT-004** | Output contract verification MUST precede the node status COMMIT. A SUCCESS result that fails contract verification MUST be reclassified DEGRADED. | Result-handler integration test |
| **INV-CIE-RT-005** | Result recording and context update MUST be atomic. A recorded result without a committed node status, or vice versa, is a conformance violation. | Crash-injection: abort between record and update must not diverge |
| **INV-CIE-RT-006** | Failure classification (TRANSIENT/DEGRADED/CRITICAL/FATAL) MUST complete BEFORE retry-strategy selection (INV-EXEC-FL-001). | Event ordering: classification event precedes retry-strategy event |

#### Determinism Invariants

| Invariant | Condition | Verification |
|-----------|-----------|--------------|
| **INV-CIE-DET-001** | Given an identical ExecutionContext and identical Facade Service responses (event-log replay), the CIE MUST produce a bit-for-bit identical invocation sequence and event stream. | Replay test (EXEC-DG-010) |
| **INV-CIE-DET-002** | Facade dispatch resolution MUST be deterministic and reproducible. The dispatcher map MUST NOT depend on dict insertion order or memory address for ordering. | Static analysis of dispatcher iteration |

### 8.3.2.13 Conformance

#### RFC 2119 Conformance

| Requirement | Level | Specification |
|-------------|-------|---------------|
| The CIE MUST be the sole capability invocation pathway | MUST | Structural (INV-CIE-STR-001) |
| The CIE MUST invoke ONLY through Capability Facade Services | MUST | Structural (INV-CIE-STR-002) |
| Direct Core Manager access from the CIE MUST NOT occur | MUST NOT | Structural (INV-CIE-STR-002) |
| Every invocation MUST emit a terminal outcome event | MUST | Runtime (INV-CIE-RT-001) |
| Budget MUST be validated before any side effect | MUST | Runtime (INV-CIE-RT-002) |
| Parameter binding MUST be deterministic | MUST | Runtime (INV-CIE-RT-003) |
| Contract failure on a SUCCESS result MUST be reclassified DEGRADED | MUST | Runtime (INV-CIE-RT-004) |
| Result recording and context update MUST be atomic | MUST | Runtime (INV-CIE-RT-005) |
| Failure classification MUST precede retry selection | MUST | Runtime (INV-CIE-RT-006) |
| Vendor interchange MUST NOT require CIE code changes | MUST NOT | Determinism (INV-CIE-DET-001, EXEC-DG-008) |
| Intermediate invocation diagnostics MAY be sampled | MAY | Runtime |
| The CIE SHOULD batch metric emission to reduce event volume | SHOULD | Runtime |

#### Conformance Levels

| Level | Verification Method |
|-------|--------------------|
| **L1: Static** | CIE source scan: no direct Core Manager references; no vendor SDK imports; dispatcher map present |
| **L2: Runtime** | Event coverage: terminal event per invocation (100%); budget-check precedes invocation-start; classification precedes retry-strategy |
| **L3: Integration** | End-to-end plan -> context -> invocation -> completion across real Facade Services and ResourceManager |
| **L4: Failure Injection** | Inject TIMEOUT, DEGRADED, FAILED, FATAL, budget-exhaustion; verify classification + retry routing + atomicity |
| **L5: Replay** | Bit-identical invocation sequence and event stream under event-log replay (EXEC-DG-010) |
| **L6: Audit** | Every invocation terminal event present with full correlation; contract-violation events present on schema mismatch |
| **L7: Performance** | Invocation overhead (non-capability time): p50 < 20ms, p99 < 100ms for typical (< 1000-token) bindings |

#### Conformance Summary Matrix

| Requirement Category | L1 | L2 | L3 | L4 | L5 | L6 | L7 |
|----------------------|----|----|----|----|----|----|----|
| Single Invocation Pathway | + | | + | | | | |
| Facade-Only Dispatch | + | | + | | + | | |
| Vendor Independence | + | | + | | + | | |
| Terminal Event Coverage | | + | + | + | + | + | |
| Budget Preemption | | + | + | + | | | |
| Deterministic Parameter Binding | + | + | + | | + | | |
| Contract Verification / Reclassification | | + | + | + | | + | |
| Atomic Result Recording | | | + | + | + | | |
| Failure Classification Order | | + | + | + | | | |
| Deterministic Replay | | | | | + | | |
| Invocation Overhead | | | | | | | + |

''';

with open(p, 'a', encoding='utf-8') as f:
    f.write(addition)
print('OK appended 8.3.2.12-13:', len(addition), 'bytes')
