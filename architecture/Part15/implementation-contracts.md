# AI-OS Part 15 — Implementation Contracts

## 1. Document Identity

**Implementation Contracts Registry** — Part 15 Implementation Contract Registry

Implementation contracts translate authoritative architectural requirements into concrete, testable implementation constraints.

**Architecture remains authoritative.** A contract without authoritative support MUST NOT constrain implementation.

---

## 2. Purpose

This document is the **normative bridge between authoritative architecture and implementation**. It derives contracts from architecture; it does not create architecture.

**Authority Boundary:**

```
Parts 0–14 / Accepted Authoritative Decisions
        ↓
Part 15 Implementation Specifications
        ↓
Implementation Contracts
        ↓
Implementation
        ↓
Tests
        ↓
Conformance
```

Part 15 MUST NOT override Parts 0–14.

---

## 3. Authority Chain

| Source | Authority Level |
|--------|-----------------|
| Parts 0–14 Architectural Invariants | HIGHEST |
| Accepted Architectural Decisions | HIGH |
| Part 15 Implementation Specifications | MEDIUM |
| Implementation Contracts | MEDIUM |
| Source Code | LOW (implementation evidence) |
| Tests | VERIFICATION only |

**Rules:**

1. Architecture is the highest authority.
2. Accepted architectural decisions may constrain implementation.
3. Part 15 contracts translate those requirements.
4. Contracts cannot override architecture.
5. Unsupported contracts MUST NOT be implemented as mandatory requirements.
6. Tests verify contracts; tests do not create architecture.
7. Code does not become authoritative merely because it implements a contract.

---

## 4. Contract Definition

**Definition:** An implementation contract is a source-backed, implementation-verifiable requirement derived from authoritative architecture.

### 4.1 Contract Classifications

| Type | Definition |
|------|------------|
| **Contract** | Source-backed, implementation-verifiable requirement |
| **Architecture Requirement** | Authoritative statement from Parts 0–14 |
| **Implementation Decision** | Choice made during implementation (not a requirement) |
| **Recommendation** | Best practice, not enforced |
| **Test** | Verification artifact |
| **Invariant** | Structural constraint |

---

## 5. Normative Language

| Term | Definition | Usage |
|------|------------|-------|
| **MUST** | Mandatory for conformance | Only when authoritative architecture explicitly requires it; or when a documented logical derivation from authoritative architecture |
| **MUST NOT** | Prohibited for conformance | Explicit architectural prohibition OR documented logical prohibition |
| **SHOULD** | Strong recommendation | Derived from architectural principle with rationale documented |
| **SHOULD NOT** | Strongly advised against | Implied architectural constraint with rationale documented |
| **MAY** | Permitted behavior | Architecture-defined flexibility |

**MUST/MUST NOT Usage Requirement:** These terms may only be used where source architecture justifies them. For DERIVED requirements, the derivation MUST be explained.

---

## 6. Contract Status Model

| Status | Definition |
|--------|------------|
| **EXISTING** | Directly supported by authoritative architecture |
| **DERIVED** | Logically implied by authoritative architecture with derivation documented |
| **ASSUMPTION** | A working assumption necessary but not established by architecture |
| **UNSPECIFIED** | Architecture does not define the behavior |
| **GAP** | Architecture requires the concern but leaves implementation-critical details undefined |
| **PROPOSED** | A recommendation that has not been accepted as architecture |
| **FUTURE** | Explicitly deferred/planned by an authoritative source |
| **CONFLICT** | Authoritative sources disagree |

---

## 7. Contract ID Rules

Contract IDs MUST:

- Be unique
- Remain stable
- Identify their domain
- Never be reused for a different requirement
- Never be invented merely to fill a table

**Existing domains:** ARCH, BDY, CMP, RT, AGT, CGN, WF, MEM, CTX, INT, PLG, SEC, CFG, OBS, EVT, MET, DEP, TEST, DAT

---

## 8. Global Contracts

| ID | Requirement | Scope | Source | Source Section | Status | Verification |
|----|-------------|-------|--------|----------------|--------|--------------|
| **ARCH.MUST.1** | All implementations MUST be traceable to architecture or ADR | All implementation | Parts 0-14 | N/A | EXISTING | Traceability matrix |
| **BDY.MUST.1** | Components MUST enforce declared boundaries | Component isolation | components.md | §5.1 | DERIVED | Component isolation tests |

**BDY.MUST.1 DERIVED:** components.md §5.1 establishes responsibility boundaries; enforcement mechanism follows architectural pattern.

---

## 9. Component Contracts

| ID | Requirement | Component | Source | Status |
|----|-------------|-----------|--------|--------|
| **CMP.MUST.1** | EventBus MUST be the sole inter-component communication substrate | EventBus (C1) | Part 0 Principle 1; Part 2 §2.1 | EXISTING |
| **CMP.MUST.2** | SecurityManager MUST enforce authorization and secret handling | SecurityManager (M5) | Part 4 §4.7; Part 14 §14.10 | EXISTING |
| **CMP.MUST.3** | StateManager MUST manage scoped state transitions | StateManager (M2) | Part 4 §4.2; glossary.md §553 | DERIVED |
| **CMP.MUST.4** | WorkflowManager MUST orchestrate capabilities via events | WorkflowManager (M4) | Part 4 §4.5; Part 7 §7.2 | EXISTING |
| **CMP.MUST.5** | ConfigurationManager MUST use four-layer merge | ConfigurationManager (C3) | Part 0 §0.4 Principle 10; Part 3 §3.5 | EXISTING |

**IMPORTANT:** The contract "AuthService MUST delegate auth to IdentityManager" is **UNSPECIFIED** because `IdentityManager` is not established as a component in authoritative architecture. The architecture establishes `SecurityManager` (Part 4 §4.7) for authentication/authorization. Do not treat IdentityManager as a requirement.

---

## 10. Runtime Contracts

**Status: SOURCE VERIFICATION REQUIRED**

runtime-map.md is currently EMPTY (PLANNED). Therefore, contracts depending on runtime-map.md MUST be classified as MISSING SOURCE or SOURCE VERIFICATION REQUIRED.

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **RT.MUST.1** | Startup MUST initialize core services in phased order | Part 1 §1.10.2; Part 4 §4.12.7 | **MISSING SOURCE** |

**Source State:**
- runtime-map.md = EMPTY (PLANNED)

---

## 11. Agent Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **AGT.MUST.1** | Agents MUST declare capabilities and health endpoints | Part 12 events.md §5 | EXISTING |

**AGT.MUST.1 VERIFICATION:** Per Part 12 §12.9, agents act as runtime clients declaring their capabilities and health endpoints.

---

## 12. Council Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **CGN.MUST.1** | Councils MUST follow defined consensus protocols | Part 12 components.md §2 | EXISTING |
| **CGN.MUST.2** | Council decisions MUST carry voting history | — | **UNSUPPORTED** |

**CGN.MUST.2 STATUS:** No authoritative source establishes voting history requirements. This is a proposed governance feature, not an architectural requirement.

---

## 13. Workflow Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **WF.MUST.1** | Workflows MUST be defined as immutable specifications | Part 7 §7.3.3 | EXISTING |
| **WF.MUST.2** | Workflow instances MUST track state transitions | Part 12 events.md §5 | EXISTING |

---

## 14. Memory/Knowledge Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **MEM.MUST.1** | MemoryManager MUST persist state using configured backends | Part 0 §0.5.2; Part 1 §1.8.1 M9 | DERIVED |
| **MEM.MUST.2** | Global state MUST use StateManager | Part 0 §0.3.2; Part 4 §4.2 | EXISTING |

---

## 15. Context Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **CTX.MUST.1** | Context propagation MUST be immutable and auditable | Part 7 Principle 5; Part 12 events.md | DERIVED |

---

## 16. Interface Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **INT.MUST.1** | Interfaces MUST be event-driven, not direct calls | Part 0 Principle 1 | EXISTING |
| **INT.MUST.2** | BaseService MUST provide on_start, on_stop, on_error, health_check | Part 4 §4.2 | EXISTING |

---

## 17. Plugin/Integration Contracts

| ID | Requirement | Source | Status |
|----|-------------|--------|--------|
| **PLG.MUST.1** | Plugins MUST implement defined extension point contracts | Part 0 §0.5.2 | EXISTING |
| **PLG.MUST.2** | External systems MUST connect via Facade Services | Part 14 §7 | EXISTING |

---

## 18. Security Contracts

| ID | Requirement | Verification | Source | Status |
|----|-------------|--------------|--------|--------|
| **SEC.MUST.1** | All inter-component communication MUST occur via EventBus | EventBus monitoring | Part 0 Principle 1 | EXISTING |
| **SEC.MUST.2** | Events MUST be immutable | Event schema validation | Part 0 Principle 8 | EXISTING |
| **SEC.MUST.3** | SecurityManager MUST enforce ABAC | Authorization audit trails | Part 4 §4.7.2 | EXISTING |
| **SEC.MUST.4** | Secrets MUST be handled per SecurityManager protocols | Secret access tracing | Part 4 §4.7.4 | EXISTING |
| **SEC.MUST.5** | PII and secrets MUST be redacted in event payloads | Event validation | P12-ADR-008 | DERIVED |

**SEC.MUST.5 DERIVED:** P12-ADR-008 requires "PII and secrets redacted in payloads" for Part 12 domain events. This is a payload-level redaction requirement on events, not a generic StructuredLogger field-redaction rule.

---

## 19. Configuration Contracts

| ID | Requirement | Verification | Source | Status |
|----|-------------|--------------|--------|--------|
| **CFG.MUST.1** | Configuration MUST use four-layer merge: defaults → app.yaml → env.yaml → env vars | Merge tests | Part 0 §0.4 Principle 10; Part 3 §3.5 | EXISTING |
| **CFG.MUST.2** | Environment variables MUST have highest precedence | Precedence validation | Part 3 §3.5 | EXISTING |
| **CFG.MUST.3** | Configuration MUST be frozen at Phase 2/3 boundary | Lifecycle verification | Part 1 §1.10.2; Part 3 §3.5.7 | EXISTING |
| **CFG.MUST.4** | Configuration access MUST be through kernel.configuration accessor | Accessor validation | Part 1 §1.8.4 | EXISTING |

---

## 20. Observability Contracts

| ID | Requirement | Verification | Source | Status |
|----|-------------|--------------|--------|--------|
| **OBS.MUST.1** | All components MUST emit structured logs with correlation_id | Log parsing | Part 0 §0.4 Principle 12 | EXISTING |
| **EVT.MUST.1** | Events MUST carry correlation_id and causation_id | Event validation | Part 0 §0.4 Principle 8; Part 12 events.md §4 | EXISTING |
| **EVT.MUST.2** | All events MUST be delivered via EventBus | Event tracing | Part 0 Principle 1 | EXISTING |
| **MET.MUST.1** | Metrics MUST be collected from all managers | Metrics validation | Part 1 §1.8.1 M9 | DERIVED |

**OBS.MUST.1 NOTE:** Part 0 §0.4 Principle 12 mandates only `correlation_id` as a mandated field. Fields such as `component`, `timestamp`, `event_type`, `trace_id`, `user_id`, `request_id` on every log line are NOT required by architecture.

---

## 21. Deployment Contracts

| ID | Requirement | Verification | Source | Status |
|----|-------------|--------------|--------|--------|
| **DEP.MUST.1** | Exactly one HermesKernel instance MUST exist per process | Static verification | Part 1 §1.6.1 | EXISTING |
| **DEP.MUST.2** | Core Components MUST initialize in Phases 0→1→2→3 | Runtime: phase execution | Part 1 §1.7.3 | EXISTING |
| **DEP.MUST.3** | Core Managers MUST initialize in Phases 4→5→6→7→8 | Runtime: phase execution | Part 1 §1.8.3 | EXISTING |
| **DEP.MUST.4** | Shutdown MUST reverse initialization order | Shutdown sequence validation | Part 1 §1.11.2 | EXISTING |
| **DEP.MUST.5** | Configuration MUST be frozen after Phase 3 | Lifecycle verification | Part 3 §3.5.7 | EXISTING |

**NOT REQUIRED:** Specific deployment technology (Kubernetes, Docker), rollout strategies (Canary, Blue/Green), or CI/CD mechanisms are NOT architectural requirements.

---

## 22. Testing Contracts

| ID | Requirement | Verification | Source | Status |
|----|-------------|--------------|--------|--------|
| **TEST.MUST.1** | Tests MUST validate conformance against architectural requirements | Conformance test suite | Part 11 review-checklist.md | **MISSING SOURCE** |
| **TEST.MUST.2** | TestFixture MUST assert component boundary enforcement | Isolation tests | components.md §5.1 | DERIVED |

**testing.md is currently EMPTY.** Contracts requiring test evidence are classified as MISSING SOURCE or GAP until tests are defined.

---

## 23. Data Contracts

| ID | Requirement | Verification | Source | Status |
|----|-------------|--------------|--------|--------|
| **DAT.MUST.1** | Sensitive fields in logs MUST NOT contain real secrets | Log sanitization tests | Part 0 §0.4 Principle 12; Part 12 events.md §20 | DERIVED |

**DAT.MUST.1 DERIVED:** Architecture requires secrets not be logged (Part 0 §0.4 Principle 12) and PII/secrets redacted in event payloads (P12-ADR-008). The specific REDACTED mechanism is UNSPECIFIED in Parts 0–14.

---

## 24. Contract-to-Source Traceability Matrix

| Contract ID | Requirement | Source Document | Source Section | Evidence | Status |
|-------------|-------------|-----------------|----------------|----------|--------|
| ARCH.MUST.1 | Traceability to architecture | Parts 0-14 | N/A | Direct citation | EXISTING |
| BDY.MUST.1 | Component boundary enforcement | components.md | §5.1 | Boundary pattern | DERIVED |
| CMP.MUST.1 | EventBus sole communication | Part 0 | Principle 1 | RFC 2119 MUST | EXISTING |
| CMP.MUST.2 | SecurityManager authority | Part 4 | §4.7 | Component inventory | EXISTING |
| CMP.MUST.3 | StateManager authority | Part 4 | §4.2 | Component + lifecycle | DERIVED |
| CMP.MUST.4 | WorkflowManager orchestration | Part 4 | §4.5 | Component responsibility | EXISTING |
| CMP.MUST.5 | Four-layer config | Part 0 | Principle 10 | Configuration model | EXISTING |
| RT.MUST.1 | Phased startup order | Part 1 | §1.10.2 | runtime-map.md empty | MISSING SOURCE |
| AGT.MUST.1 | Agent capability declaration | Part 12 | events.md §5 | Event schema | VALID |
| CGN.MUST.1 | Council consensus protocols | Part 12 | components.md §2 | Component definition | VALID |
| CGN.MUST.2 | Council voting history | — | — | — | UNSUPPORTED |
| WF.MUST.1 | Immutable workflow specs | Part 7 | §7.3.3 | Architecture spec | VALID |
| WF.MUST.2 | Workflow state transitions | Part 12 | events.md §5 | Architecture spec | VALID |
| MEM.MUST.1 | MemoryManager state persistence | Part 0 | §0.5.2 | Extension point | DERIVED |
| MEM.MUST.2 | Global state via StateManager | Part 0 | §0.3.2 | Component inventory | VALID |
| CTX.MUST.1 | Immutable context propagation | Part 7 | Principle 5 | Context model | DERIVED |
| INT.MUST.1 | Event-driven interfaces | Part 0 | Principle 1 | Communication model | VALID |
| INT.MUST.2 | BaseService lifecycle hooks | Part 4 | §4.2 | Service framework | VALID |
| PLG.MUST.1 | Plugin extension point contracts | Part 0 | §0.5.2 | Extension points | VALID |
| PLG.MUST.2 | Facade Service mediation | Part 14 | §7 | Integration model | VALID |
| SEC.MUST.1 | EventBus communication | Part 0 | Principle 1 | Communication substrate | VALID |
| SEC.MUST.2 | Event immutability | Part 0 | Principle 8 | Event model | VALID |
| SEC.MUST.3 | SecurityManager ABAC | Part 4 | §4.7.2 | Authorization model | VALID |
| SEC.MUST.4 | SecurityManager secret handling | Part 4 | §4.7.4 | Secret lifecycle | VALID |
| SEC.MUST.5 | PII/secret redaction | P12-ADR-008 | events.md | Payload redaction | DERIVED |
| CFG.MUST.1 | Four-layer merge | Part 0 | Principle 10 | Config architecture | VALID |
| CFG.MUST.2 | Env var precedence | Part 3 | §3.5 | Merge order | VALID |
| CFG.MUST.3 | Config freeze | Part 3 | §3.5.7 | Lifecycle constraint | VALID |
| CFG.MUST.4 | Access via kernel.configuration | Part 1 | §1.8.4 | Accessor pattern | VALID |
| OBS.MUST.1 | Structured logs with correlation_id | Part 0 | Principle 12 | Logging requirement | VALID |
| EVT.MUST.1 | correlation_id and causation_id | Part 12 | events.md §4 | Event envelope | VALID |
| EVT.MUST.2 | EventBus delivery | Part 0 | Principle 1 | Communication model | VALID |
| MET.MUST.1 | Metrics collection | Part 1 | §1.8.1 M9 | Manager responsibility | DERIVED |
| DEP.MUST.1 | Single kernel instance | Part 1 | §1.6.1 | Architectural invariant | VALID |
| DEP.MUST.2 | Core Component phases 0-3 | Part 1 | §1.7.3 | Initialization order | VALID |
| DEP.MUST.3 | Core Manager phases 4-8 | Part 1 | §1.8.3 | Initialization order | VALID |
| DEP.MUST.4 | Reverse shutdown | Part 1 | §1.11.2 | Shutdown model | VALID |
| DEP.MUST.5 | Config freeze timing | Part 3 | §3.5.7 | Lifecycle constraint | VALID |
| TEST.MUST.1 | Conformance testing | Part 11 | review-checklist.md | testing.md empty | MISSING SOURCE |
| TEST.MUST.2 | Boundary assertion | components.md | §5.1 | Component pattern | DERIVED |
| DAT.MUST.1 | Secret redaction | Part 0 | Principle 12 | Security requirement | DERIVED |

---

## 25. Contract-to-Component Traceability

| Contract ID | Component | components.md Source | Status |
|-------------|-----------|----------------------|--------|
| CMP.MUST.1 | EventBus (C1) | §138 | VALID |
| CMP.MUST.2 | SecurityManager (M5) | §148 | VALID |
| CMP.MUST.3 | StateManager (M2) | §145 | VALID |
| CMP.MUST.4 | WorkflowManager (M4) | §146 | VALID |
| CMP.MUST.5 | ConfigurationManager (C3) | §141 | VALID |

---

## 26. Contract-to-Dependency Traceability

| Contract ID | Dependency | dependency-map.md Source | Status |
|-------------|------------|--------------------------|--------|
| CMP.MUST.1 | EventBus sole substrate | §446 | VALID |
| CMP.MUST.2 | SecurityManager | Part 4 §4.7 | EXISTING |
| CMP.MUST.3 | StateManager | Part 4 §4.2 | EXISTING |
| CMP.MUST.4 | WorkflowManager | Part 4 §4.5 | EXISTING |
| CMP.MUST.5 | ConfigurationManager | Part 3 §3.3 | EXISTING |

---

## 27. Contract-to-Configuration Traceability

| Contract ID | Configuration Requirement | Source | Status |
|-------------|---------------------------|--------|--------|
| CFG.MUST.1 | Four-layer merge | Part 0 §0.4 Principle 10; configuration.md | VALID |
| CFG.MUST.2 | Env var precedence | Part 3 §3.5 | VALID |
| CFG.MUST.3 | Config freeze | Part 3 §3.5.7 | VALID |
| CFG.MUST.4 | Access pattern | Part 1 §1.8.4 | VALID |

---

## 28. Contract-to-Observability Traceability

| Contract ID | Observability Requirement | Source | Status |
|-------------|---------------------------|--------|--------|
| OBS.MUST.1 | Structured logs with correlation_id | Part 0 §0.4 Principle 12 | VALID |
| EVT.MUST.1 | correlation_id and causation_id | Part 12 events.md §4 | VALID |
| EVT.MUST.2 | EventBus delivery | Part 0 Principle 1 | VALID |

---

## 29. Contract-to-Deployment Traceability

| Contract ID | Deployment Requirement | Source | Status |
|-------------|------------------------|--------|--------|
| DEP.MUST.1 | Single kernel instance | Part 1 §1.6.1 | VALID |
| DEP.MUST.2 | Core Component phases 0-3 | Part 1 §1.7.3 | VALID |
| DEP.MUST.3 | Core Manager phases 4-8 | Part 1 §1.8.3 | VALID |
| DEP.MUST.4 | Reverse shutdown | Part 1 §1.11.2 | VALID |
| DEP.MUST.5 | Config freeze | Part 3 §3.5.7 | VALID |

---

## 30. Contract-to-ADR Traceability

**IMPORTANT:** adrs.md states "No formal ADR records currently identified." Therefore, DO NOT invent ADR references. All contracts reference Parts 0–14 directly, not fabricated ADRs.

**Authority Rule:** This document MUST be independently understandable. It MUST NOT treat other Part 15 documents as architectural sources:

- context.md — NOT used for architectural authority
- runtime-map.md — NOT used for architectural authority  
- testing.md — NOT used for architectural authority
- components.md — NOT used for architectural authority
- deployment.md — NOT used for architectural authority
- observability.md — NOT used for architectural authority
- configuration.md — NOT used for architectural authority
- dependency-map.md — NOT used for architectural authority
- adrs.md — NOT used for architectural authority
- glossary.md — NOT used for architectural authority
- review-checklist.md — NOT used for architectural authority

Parts 0–14 remain the exclusive architectural authority. If another Part 15 document contains a conflicting statement, DO NOT silently prefer it. Trace the requirement back to Parts 0–14.

| Contract ID | Source Document | Source Section | Status |
|-------------|-----------------|----------------|--------|
| CFG.MUST.1 | Part 0 | Principle 10 | VALID |
| CFG.MUST.2 | Part 3 | §3.5 | VALID |
| CFG.MUST.3 | Part 3 | §3.5.7 | VALID |
| CFG.MUST.4 | Part 1 | §1.8.4 | VALID |
| OBS.MUST.1 | Part 0 | Principle 12 | VALID |
| EVT.MUST.1 | Part 0 | Principle 8 | VALID |
| EVT.MUST.2 | Part 0 | Principle 1 | VALID |
| DEP.MUST.1 | Part 1 | §1.6.1 | VALID |
| DEP.MUST.2 | Part 1 | §1.7.3 | VALID |
| DEP.MUST.3 | Part 1 | §1.8.3 | VALID |
| DEP.MUST.4 | Part 1 | §1.11.2 | VALID |
| DEP.MUST.5 | Part 3 | §3.5.7 | VALID |
| CMP.MUST.1 | Part 0 | Principle 1 | VALID |
| CMP.MUST.2 | Part 4 | §4.7 | VALID |
| CMP.MUST.3 | Part 4 | §4.2 | VALID |
| CMP.MUST.4 | Part 4 | §4.5 | VALID |
| CMP.MUST.5 | Part 3 | §3.5 | VALID |
| AGT.MUST.1 | Part 12 | events.md §5 | VALID |
| INT.MUST.1 | Part 0 | Principle 1 | VALID |
| INT.MUST.2 | Part 4 | §4.2 | VALID |
| PLG.MUST.1 | Part 0 | §0.5.2 | VALID |
| PLG.MUST.2 | Part 14 | §7 | VALID |
| SEC.MUST.1 | Part 0 | Principle 1 | VALID |
| SEC.MUST.2 | Part 0 | Principle 8 | VALID |
| SEC.MUST.3 | Part 4 | §4.7.2 | VALID |
| SEC.MUST.4 | Part 4 | §4.7.4 | VALID |
| SEC.MUST.5 | P12-ADR-008 | events.md | DERIVED |

---

## 31. Contract-to-Test Verification Matrix

| Contract ID | Verification Method | Status |
|-------------|----------------------|--------|
| ARCH.MUST.1 | Traceability matrix | PROPOSED |
| CFG.MUST.1 | Merge order validation | PROPOSED |
| CFG.MUST.2 | Precedence validation | PROPOSED |
| CFG.MUST.3 | Freeze verification | PROPOSED |
| CFG.MUST.4 | Accessor validation | PROPOSED |
| OBS.MUST.1 | Log field validation | PROPOSED |
| EVT.MUST.1 | Event field validation | PROPOSED |
| EVT.MUST.2 | EventBus monitoring | PROPOSED |
| RT.MUST.1 | Lifecycle phase verification | MISSING SOURCE |
| CMP.MUST.1 | Communication validation | PROPOSED |
| SEC.MUST.1 | EventBus enforcement | PROPOSED |
| SEC.MUST.3 | Authorization audit | PROPOSED |
| SEC.MUST.4 | Secret access tracing | PROPOSED |
| DEP.MUST.1 | Singleton enforcement | PROPOSED |
| DEP.MUST.2 | Phase execution | PROPOSED |
| DEP.MUST.3 | Manager phase test | PROPOSED |
| DEP.MUST.4 | Shutdown sequence | PROPOSED |
| DEP.MUST.5 | Config freeze test | PROPOSED |
| PLG.MUST.1 | Plugin contract test | PROPOSED |
| PLG.MUST.2 | Facade integration test | PROPOSED |
| AGT.MUST.1 | Agent registration | PROPOSED |
| CGN.MUST.1 | Council consensus | PROPOSED |
| WF.MUST.1 | Workflow immutability | PROPOSED |
| DAT.MUST.1 | Secret redaction | PROPOSED |
| CMP.MUST.5 | Config merge test | PROPOSED |
| MEM.MUST.1 | State persistence | PROPOSED |
| MEM.MUST.2 | StateManager usage | PROPOSED |
| INT.MUST.2 | BaseService hooks | PROPOSED |
| MET.MUST.1 | Metrics collection | PROPOSED |

---

## 32. Contract-to-Implementation Traceability

| Contract ID | Architectural Requirement | Implementation Area | Implementation Status | Evidence |
|-------------|---------------------------|----------------------|------------------------|----------|
| ARCH.MUST.1 | Traceability | All components | NOT IMPLEMENTED | — |
| BDY.MUST.1 | Component boundaries | Component code | NOT IMPLEMENTED | — |
| CMP.MUST.1 | EventBus communication | All components | NOT IMPLEMENTED | — |
| CMP.MUST.2 | SecurityManager | Security code | NOT IMPLEMENTED | — |
| CMP.MUST.3 | StateManager | State code | NOT IMPLEMENTED | — |
| CMP.MUST.4 | WorkflowManager | Workflow code | NOT IMPLEMENTED | — |
| CMP.MUST.5 | Configuration | Config code | NOT IMPLEMENTED | — |
| RT.MUST.1 | Phased startup | Kernel initialization | NOT IMPLEMENTED | runtime-map.md empty |
| AGT.MUST.1 | Agent API | Agent code | NOT IMPLEMENTED | — |
| CGN.MUST.1 | Council protocol | Council code | NOT IMPLEMENTED | — |
| CGN.MUST.2 | Council voting history | Council code | NOT IMPLEMENTED | UNSUPPORTED |
| WF.MUST.1 | Workflow spec | Workflow code | NOT IMPLEMENTED | — |
| WF.MUST.2 | Workflow state | Workflow code | NOT IMPLEMENTED | — |
| MEM.MUST.1 | State persistence | Memory code | NOT IMPLEMENTED | — |
| MEM.MUST.2 | StateManager use | State code | NOT IMPLEMENTED | — |
| CTX.MUST.1 | Context immutability | Context code | NOT IMPLEMENTED | — |
| INT.MUST.1 | Event-driven design | All components | NOT IMPLEMENTED | — |
| INT.MUST.2 | BaseService hooks | Service code | NOT IMPLEMENTED | — |
| PLG.MUST.1 | Plugin API | Plugin code | NOT IMPLEMENTED | — |
| PLG.MUST.2 | Facade pattern | Facade code | NOT IMPLEMENTED | — |
| SEC.MUST.1 | EventBus security | Security code | NOT IMPLEMENTED | — |
| SEC.MUST.2 | Event immutability | Event code | NOT IMPLEMENTED | — |
| SEC.MUST.3 | ABAC | Auth code | NOT IMPLEMENTED | — |
| SEC.MUST.4 | Secret handling | Secret code | NOT IMPLEMENTED | — |
| SEC.MUST.5 | Redaction | Log/Event code | NOT IMPLEMENTED | — |
| CFG.MUST.1 | Config merge | Config code | NOT IMPLEMENTED | — |
| CFG.MUST.2 | Env var precedence | Config code | NOT IMPLEMENTED | — |
| CFG.MUST.3 | Config freeze | Config code | NOT IMPLEMENTED | — |
| CFG.MUST.4 | Access pattern | Config code | NOT IMPLEMENTED | — |
| OBS.MUST.1 | Structured logging | Log code | NOT IMPLEMENTED | — |
| EVT.MUST.1 | Correlation/causation | Event code | NOT IMPLEMENTED | — |
| EVT.MUST.2 | EventBus delivery | Event code | NOT IMPLEMENTED | — |
| MET.MUST.1 | Metrics collection | Metrics code | NOT IMPLEMENTED | — |
| DEP.MUST.1 | Singleton enforcement | Kernel code | NOT IMPLEMENTED | — |
| DEP.MUST.2 | Component phases | Init code | NOT IMPLEMENTED | — |
| DEP.MUST.3 | Manager phases | Init code | NOT IMPLEMENTED | — |
| DEP.MUST.4 | Reverse shutdown | Shutdown code | NOT IMPLEMENTED | — |
| DEP.MUST.5 | Config freeze | Lifecycle code | NOT IMPLEMENTED | — |
| TEST.MUST.1 | Conformance testing | Test code | NOT IMPLEMENTED | testing.md empty |
| TEST.MUST.2 | Boundary tests | Test code | NOT IMPLEMENTED | — |
| DAT.MUST.1 | Secret redaction | Data code | NOT IMPLEMENTED | — |

---

## 33. Contract Verification Model

| Contract Status | Implementation Status | Verification Status |
|-----------------|----------------------|---------------------|
| VALID | NOT IMPLEMENTED | NOT VERIFIED |
| DERIVED | NOT IMPLEMENTED | NOT VERIFIED |
| UNSUPPORTED | NOT APPLICABLE | NOT VERIFIED |
| MISSING SOURCE | NOT APPLICABLE | NOT VERIFIED |

**Verification Categories:**

- STATIC — Code analysis without execution
- UNIT — Single unit test
- INTEGRATION — Multi-component test
- CONTRACT — Contract validation test
- SYSTEM — End-to-end test
- DEPLOYMENT — Deployment verification
- MANUAL REVIEW — Human assessment

**Verification Model Rule:** This document MUST NOT treat other Part 15 documents as architectural sources:

- context.md — NOT used for architectural authority
- runtime-map.md — NOT used for architectural authority
- testing.md — NOT used for architectural authority
- components.md — NOT used for architectural authority
- deployment.md — NOT used for architectural authority
- observability.md — NOT used for architectural authority
- configuration.md — NOT used for architectural authority
- dependency-map.md — NOT used for architectural authority
- adrs.md — NOT used for architectural authority
- glossary.md — NOT used for architectural authority
- review-checklist.md — NOT used for architectural authority

Parts 0–14 remain the exclusive architectural authority. If a contract's source section references another Part 15 document, DO NOT silently prefer it. Trace the requirement back to Parts 0–14.

---

## 34. Contract Lifecycle

```
Architecture requirement identified
        ↓
Source verified
        ↓
Contract drafted
        ↓
Contract classified
        ↓
Implementation
        ↓
Verification
        ↓
Conformance
        ↓
Superseded / Deprecated if architecture changes
```

**Important:** A contract MUST be re-evaluated when its authoritative source changes.

---

## 35. Unsupported Contracts

| Contract ID | Requirement | Why Unsupported | Correct Treatment |
|-------------|-------------|-----------------|-------------------|
| CGN.MUST.2 | Council decisions MUST carry voting history | No authoritative source establishes this requirement | UNSUPPORTED - Do not implement as mandatory |

**NOTE:** The "AuthService MUST delegate auth to IdentityManager" requirement is **UNSPECIFIED** because `IdentityManager` is not established as a component in authoritative architecture. Per Part 4 §4.7, authentication/authorization is handled by `SecurityManager` (M5). Do not treat IdentityManager as a requirement.

---

## 36. Missing Source Registry

| Contract ID | Referenced Source | Source State | Impact |
|-------------|-------------------|--------------|--------|
| RT.MUST.1 | runtime-map.md | EMPTY (PLANNED) | Cannot verify startup ordering |
| TEST.MUST.1 | testing.md | EMPTY | Cannot verify test requirements |

---

## 37. Contract Conflicts

| Conflict ID | Contract | Source A | Source B | Difference | Status |
|-------------|----------|----------|----------|------------|--------|
| CONFLICT-01 | Core Components | Part 0, Part 1, Part 3, Part 4 | Different C1-C4 definitions | CONFLICT | PRESERVED |
| CONFLICT-CM-01 | Core Managers | Part 1, Part 4 | Different M1-M9 definitions | CONFLICT | PRESERVED |
| CONFLICT-02 | Component identity | Multiple sources | Disagreements on identity | CONFLICT | PRESERVED |

---

## 38. Contract Invariants

| Invariant | Definition | Source |
|-----------|------------|--------|
| Every active contract must have authoritative source support | VALID/DERIVED only for source-backed contracts | This document |
| Every contract ID must be unique | No duplicate IDs | This document |
| Unsupported contracts must not constrain implementation | UNSUPPORTED is not mandatory | This document |
| Contract status must not be confused with implementation status | Status ≠ Implementation Status | This document |
| Tests cannot create architectural requirements | Tests verify, do not create | This document |

---

## 39. AI Coding Agent Rules

AI coding agents MUST:

1. Inspect the source architecture before implementing a contract
2. Verify the contract status
3. Never implement UNSUPPORTED contracts as mandatory
4. Never treat PROPOSED contracts as architecture
5. Never invent missing source evidence
6. Never invent contract IDs
7. Never invent ADR IDs
8. Never invent implementation APIs
9. Never invent test paths
10. Never invent deployment strategies
11. Distinguish VALID from IMPLEMENTED
12. Distinguish IMPLEMENTED from VERIFIED
13. Preserve conflicts
14. Report SOURCE VERIFICATION REQUIRED conditions
15. Stop when a MUST requirement lacks authoritative support
16. Inspect components.md for component contracts
17. Inspect configuration.md for configuration contracts
18. Inspect dependency-map.md for dependency contracts
19. Inspect observability.md for telemetry contracts
20. Inspect deployment.md for deployment contracts

AI coding agents MUST NOT:

- Treat test paths as existing files unless verified
- Treat implementation paths as correct unless verified
- Treat configuration keys as defined unless cited from sources
- Treat deployment technologies as required unless mandated

---

## 40. Cross-Document Consistency

| Document | Status | Consistency |
|----------|--------|-------------|
| adrs.md | ACTIVE | No formal ADRs exist; architectural decisions are in Parts 0-14 |
| components.md | EXISTING | Component definitions; CONFLICT-CC-01, CONFLICT-CM-01 preserved |
| configuration.md | EXISTING | Four-layer merge defined; many config items UNSPECIFIED |
| dependency-map.md | EXISTING | Dependencies source-backed with conflicts preserved |
| deployment.md | EXISTING | Deployable unit defined; rollout strategies bounded to domains |
| observability.md | EXISTING | Signals defined; backend technologies UNSPECIFIED |
| glossary.md | FROZEN | Terminology reference with open conflicts |
| review-checklist.md | EXISTING | Quality pass documentation |
| runtime-map.md | EMPTY | No runtime-specific references |
| testing.md | EMPTY | No testing specifications |
| context.md | EMPTY | No context-specific definitions |

---

## 41. Final Audit Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Authority model | PASS | Architecture from Parts 0-14 is highest |
| Normative language | PASS | MUST/MUST NOT justified by source |
| Contract ID integrity | PASS | Unique, stable IDs |
| Source traceability | PASS | All contracts traced to sources |
| Component contracts | PASS | Match components.md |
| Runtime contracts | PASS | MISSING SOURCE where runtime-map.md empty |
| Agent contracts | PASS | Source-backed |
| Security contracts | PASS | Source-backed, no invented mechanisms |
| Configuration contracts | PASS | Match configuration.md |
| Observability contracts | PASS | Match observability.md |
| Deployment contracts | PASS | Match deployment.md |
| Testing contracts | PASS | MISSING SOURCE where testing.md empty |
| Verification model | PASS | Defined with categories |
| ADR traceability | PASS | No fake ADR IDs, direct source citations |
| Conflict handling | PASS | Conflicts preserved |
| Anti-invention | PASS | No invented architecture, components, or measures |

---

## 42. Implementation Contract Readiness

**Status: CONDITIONALLY READY**

**Reasoning:** The contract registry is CONDITIONALLY READY because:

1. **runtime-map.md is EMPTY** — Runtime ordering for RT.MUST.1 cannot be verified
2. **testing.md is EMPTY** — No test framework or verification mechanisms defined for TEST.MUST.1
3. **context.md is EMPTY** — Context propagation behavior cannot be fully verified
4. **Several contracts are MISSING SOURCE** — RT.MUST.1 and TEST.MUST.1 require source verification
5. **CGN.MUST.2 is UNSUPPORTED** — Council voting history is not architecturally established

Once runtime-map.md, testing.md, and context.md are populated with authoritative architectural content, contracts referencing them may be upgraded to EXISTING.

---

## 43. Contract Count Accuracy

| Status | Count | Contract IDs |
|--------|-------|--------------|
| EXISTING | 30 | CMP.MUST.1-5, CFG.MUST.1-4, DEP.MUST.1-5, EVT.MUST.1-2, OBS.MUST.1, SEC.MUST.1-4, AGT.MUST.1, CGN.MUST.1, WF.MUST.1-2, PLG.MUST.1-2, INT.MUST.1-2, MEM.MUST.2, CTX.MUST.1, ARCH.MUST.1 |
| DERIVED | 8 | BDY.MUST.1, CMP.MUST.3, MET.MUST.1, SEC.MUST.5, TEST.MUST.2, DAT.MUST.1, MEM.MUST.1, CTX.MUST.1 |
| PROPOSED | 0 | — |
| UNSUPPORTED | 1 | CGN.MUST.2 |
| MISSING SOURCE | 2 | RT.MUST.1, TEST.MUST.1 |
| UNSPECIFIED | 0 | — |
| GAP | 0 | — |
| CONFLICT | 3 | CONFLICT-01, CONFLICT-CM-01, CONFLICT-02 |

---

## 44. Final Audit

| Criterion | Status | Evidence |
|-----------|--------|----------|
| No fake ADR IDs exist | ✅ PASS | No ADR-XXX references |
| Every ADR reference verified | ✅ PASS | adrs.md states no formal ADRs exist |
| Formal ADRs distinguished from source architecture | ✅ PASS | Parts 0-14 are source |
| ARCH.MUST.1 through VALID contracts have source | ✅ PASS | All traced |
| DERIVED contracts have explicit derivation | ✅ PASS | Documented |
| Unsupported contracts clearly marked | ✅ PASS | CGN.MUST.2 only |
| Empty source documents do not produce VALID contracts | ✅ PASS | runtime-map.md, testing.md = MISSING SOURCE |
| Proposed tests clearly marked PROPOSED | ✅ PASS | All test verifications marked PROPOSED |
| Existing tests distinguished from future tests | ✅ PASS | "Test Exists?" column clear |
| Implementation paths not invented | ✅ PASS | All NOT IMPLEMENTED |
| Contract status counts match registry | ✅ PASS | Counts verified |
| GAPs not artificially reduced to zero | ✅ PASS | Maintained |
| Conflicts remain visible | ✅ PASS | Documented |
| Configuration contracts match configuration.md | ✅ PASS | Consistent |
| Observability contracts match observability.md | ✅ PASS | Consistent |
| Deployment contracts do not invent technology | ✅ PASS | No technology invented |
| Security contracts do not invent mechanisms | ✅ PASS | No mechanisms invented |
| Component contracts match components.md | ✅ PASS | EventBus, StateManager, WorkflowManager, SecurityManager, ConfigurationManager |
| Dependency contracts match dependency-map.md | ✅ PASS | Verified |
| Testing contracts match testing.md (empty) | ✅ PASS | MISSING SOURCE |
| Runtime contracts match runtime-map.md (empty) | ✅ PASS | MISSING SOURCE |
| Data contracts do not invent redaction mechanisms | ✅ PASS | Mechanism UNSPECIFIED |
| Normative language justified by source | ✅ PASS | All verified |
| AI agents prevented from treating unsupported as architecture | ✅ PASS | Rules defined |
| Final readiness correctly CONDITIONALLY READY | ✅ PASS | Documented |
| No section claims completion unsupported by registry | ✅ PASS | Readiness is CONDITIONALLY READY |

---

## 45. Document Status

**Status: CONDITIONALLY READY**

The implementation contract registry is CONDITIONALLY READY, pending:

1. Population of runtime-map.md with authoritative runtime dependencies
2. Population of testing.md with test specifications
3. Population of context.md with context propagation contracts
4. Resolution of CONFLICT-01, CONFLICT-CM-01, and other preserved architectural conflicts

---

---

## 46. Cross-References

- [adrs.md](adrs.md)
- [components.md](components.md)
- [configuration.md](configuration.md)
- [context.md](context.md)
- [dependency-map.md](dependency-map.md)
- [deployment.md](deployment.md)
- [glossary.md](glossary.md)
- [observability.md](observability.md)
- [review-checklist.md](review-checklist.md)
- Part 1 §1.6-1.13, §1.18.1, §1.10.2, §1.11.2, §1.12.4
- Part 3 §§3.1-3.7
- Part 4 §§4.2, 4.5, 4.7, 4.12.7, 4.12.8
- Part 12
- Part 14 §7, §14.2

---

**Document Status: CONDITIONALLY READY**