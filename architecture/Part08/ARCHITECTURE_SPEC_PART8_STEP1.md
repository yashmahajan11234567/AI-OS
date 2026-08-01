# AI-OS Architecture Specification v1.0
## Part 8: Intelligent Agent & Execution Architecture

**Version:** 1.0.0  
**Status:** FROZEN — Authoritative Source of Truth  
**Date:** 2026-07-29  
**Authors:** Chief Software Architect, AI-OS  
**Classification:** Normative Engineering Specification  
**Review History:** v1.0.0 — Initial freeze (2026-07-29)

---

### 8.0 Document Control

| Field | Value |
|-------|-------|
| **Document ID** | AI-OS-ARCH-SPEC-v1.0-PART8 |
| **Classification** | Normative — Mandatory Conformance |
| **Change Control** | Part 8 is FROZEN. No modifications permitted without Architecture Review Board (ARB) approval. All future Parts (9–N) MUST conform to Part 8. Part 8 MUST NOT contradict Part 0 through Part 7. |
| **Distribution** | All AI-OS engineers, architects, reviewers, automated conformance tooling |
| **Related Documents** | PART0 (front matter, principles, conformance), PART1 (Hermes Kernel), PART2 (Event System), PART3 (Core Managers), PART4 (Service Framework), PART5 (Engineering Services), PART6 (Capability Facade Services), PART7 (Workflow & Orchestration), ARCHITECTURAL_INVENTORY.md (evidence base), ARCHITECTURE_REVIEW_REPORT.md (gap analysis), MIGRATION_PLAN.md (phasing), ARCHITECTURE_ANALYSIS.md (architectural decisions) |

**Conformance Requirement:** Every subsequent Part (9–N) of this specification MUST explicitly reference Part 8 sections for Intelligent Agent & Execution Architecture terminology, interfaces, and conformance criteria. Any Part that contradicts Part 8 is non-conformant and MUST be revised.

**Scope:** This Part defines the authoritative architecture of the **Intelligent Agent & Execution Architecture** — the capability-driven execution substrate that transforms intent into observable outcomes through coordinated capability invocation, multi-perspective reasoning, hierarchical retry with strategic rollback, continuous learning, optimization, and self-healing recovery. This Part specifies the architectural purpose, positioning, principles, invariants, and high-level structure. Detailed specifications for individual execution subsystems appear in subsequent sections of Part 8.

**Out of Scope:**
- Detailed specification of individual execution subsystems (covered in Part 8, sections 8.2–8.N)
- Implementation code, APIs, or technology-specific details
- Core Manager internals (covered in Parts 1, 3, 4)
- Engineering Service behavior (covered in Part 5)
- Workflow orchestration logic (covered in Part 7)
- Event System contracts (covered in Part 2)

---

### 8.1 Purpose

#### 8.1.1 Overview

The Intelligent Agent & Execution Architecture is the **capability-driven execution substrate** of AI-OS. It exists because raw capabilities — skills, tools, models, memory, council governance — do not self-assemble into coherent, reliable, auditable execution. An intent (a user request, a scheduled trigger, a workflow step, a council directive) must be decomposed into a capability plan, executed with appropriate governance, monitored for deviation, recovered from failure, learned from for future improvement, and optimized for subsequent executions.

This architecture **replaces the traditional "agent" paradigm** with a **capability-driven execution model**. In the traditional paradigm, an "agent" is a monolithic entity that reasons, plans, acts, and learns as a single unit. In AI-OS, execution is **capability-driven**: an execution plan discovers the capabilities required (via the Capability Discovery Layer), loads them dynamically, invokes them through the Capability Facade Services (Part 6), governs them through the Council Manager and LLM Council, retries with strategic modification via the Loop Engine, learns from outcomes via the Learning Layer, optimizes through the Optimization Layer, and heals from anomalies via the Self-Healing Layer. No single "agent" orchestrates this; the **Hermes Kernel** (Part 1) is the central orchestrator, and execution emerges from the coordinated interaction of independently governed architectural layers.

**Hermes is the central orchestrator.** The Hermes Kernel owns the EventBus (Core Component C1), the ServiceRegistry (C2), the ConfigurationManager (C3), the LifecycleManager (C4), and the nine Core Managers (M1–M9). All execution flows through Hermes: capability discovery routes through the EventBus, capability invocation routes through Capability Facade Services, governance decisions route through the Council Manager, retry decisions route through the Loop Engine, learning updates route through the MemoryManager, optimization decisions route through the Optimization Layer, and healing actions route through the SecurityManager and ObservabilityManager. No execution occurs outside Hermes's purview.

**AI-OS is an operating environment, not a single AI agent.** The architecture provides the substrate in which multiple execution contexts can coexist, each with its own capability set, governance posture, retry policy, learning scope, optimization strategy, and healing boundary. An "execution context" in AI-OS is not an agent; it is a correlation-scoped bundle of capability invocations governed by a shared retry hierarchy, learning namespace, optimization scope, and healing boundary.

**AI-OS deliberately rejects the super-agent architectural model.** AI-OS is an intelligent execution environment where intelligence emerges from **orchestration**, **capability discovery**, **governance**, **learning**, **optimization**, and **self-healing** — rather than from a single autonomous agent. The architecture explicitly rejects the super-agent pattern in favor of a layered, governable, auditable execution substrate where each architectural concern is isolated, replaceable, and subject to architectural conformance.

**Execution is capability-driven rather than agent-driven.** Capabilities are first-class architectural components (Part 0 Principle 7). A capability is discovered (via the Capability Discovery Layer), loaded (dynamically, via the SkillManager), invoked (through Capability Facade Services), governed (via Council Manager and LLM Council), retried (via the Loop Engine's hierarchical loops), learned from (via Learning Layer), optimized (via Optimization Layer), and healed (via Self-Healing Layer). The execution plan is a data structure describing *which* capabilities in *which* order with *which* governance and *which* retry semantics — not a procedural script executed by an agent.

**Global Environment vs. Project Environment.** AI-OS is divided into two execution scopes that determine capability resolution precedence:

| Scope | Components | Resolution Priority |
|-------|------------|---------------------|
| **Global Environment** | Global Memory, Obsidian Second Brain, Graphify Knowledge Graph, Global Skills, Global MCP Servers, Global Councils, Global Learning, Global Configuration | Second (fallback) |
| **Project Environment** | `ai-os.yaml`, `Claude.md`, Project Hooks, Project Memory, Project Skills, Project MCPs, Project Models, Project Configuration | **First (primary)** |

**Execution MUST always resolve capabilities in this order: Project → Global → External Registry.** Capability discovery, learning, memory, and configuration MUST respect execution scope. Project-scoped capabilities override global capabilities; global capabilities override external registry entries. The Capability Discovery Layer enforces this resolution hierarchy as an architectural invariant.

**Claude Code is treated as one execution provider.** The architecture explicitly supports **vendor independence** as a core principle. The LLMManager (Core Manager M2) abstracts model routing across providers. The MCPManager (Core Manager M3) abstracts tool invocation across MCP servers. The SkillManager (Core Manager M5) abstracts skill execution across skill implementations. The Council Manager (Core Manager M6) abstracts governance across council implementations. No execution layer assumes Claude Code; no governance layer assumes Anthropic models; no skill layer assumes Vercel skills; no tool layer assumes MCP. All are pluggable, replaceable, and governed by the same architectural contracts.

**Local + Cloud + Hybrid Providers.** AI-OS explicitly supports **local models**, **cloud models**, and **hybrid execution**. Hermes MUST treat providers identically through abstraction layers. The LLMManager routes requests to local inference engines, cloud APIs, or hybrid configurations based on capability requirements, cost policies, latency constraints, and data sovereignty rules — without execution layer awareness of the underlying provider topology.

**Components are modular and replaceable.** Every execution subsystem — Capability Discovery Layer, SkillManager, CouncilManager, MCPManager, Loop Engine, LearningLayer, OptimizationLayer, HealingLayer — is a distinct architectural component with a defined interface, lifecycle, and conformance criteria. They are instantiated as Core Managers or Services, registered in ServiceRegistry, lifecycle-managed by LifecycleManager, and communicate exclusively via EventBus. No component has privileged access to another's internals.

**Skills are first-class architectural components.** A skill is not a function, a prompt template, or a script. It is a capability with a declared contract (input schema, output schema, side effect profile, resource requirements, governance requirements), a versioned implementation, a discovery entry (via Vercel Find Skills), a dynamic loading mechanism, and a conformance test suite. Skills are loaded dynamically at execution time based on the execution plan's capability requirements, not statically linked at development time.

**The Capability Discovery Layer is elevated to a first-class architectural subsystem.** Capability discovery is not simply a registry lookup; it is an **architectural planning stage** that includes: skill discovery, capability ranking, dependency resolution, version compatibility analysis, duplicate detection, confidence scoring, skill recommendation, and metadata validation. The Capability Discovery Layer produces a capability plan that can be reviewed, audited, and approved before any capability is invoked. This layer is implemented as the Capability Discovery Service (Engineering Service) backed by the SkillManager (Core Manager M5).

**Skills are loaded dynamically.** The SkillManager loads skill implementations on-demand, caches them with TTL-based eviction, validates their conformance against declared contracts, and isolates them in execution sandboxes (via ToolManager). A skill that is never referenced in an execution plan is never loaded. A skill whose contract changes is re-validated on next load. Dynamic loading enables zero-downtime skill updates, A/B testing of skill versions, and capability-specific resource limits.

**MCP servers are loaded lazily and shut down when no longer required.** The MCPManager discovers MCP servers on-demand based on the tool requirements in the execution plan, establishes connections, validates server capabilities against declared schemas, and terminates connections after a configurable idle timeout. No MCP server runs unless an execution plan requires it. This minimizes attack surface, resource consumption, and startup latency.

**Claude Council performs multi-perspective reasoning.** The Council Manager implements the **Claude Council** architecture: a set of distinct, configured personas (e.g., Architect, Security Reviewer, Performance Engineer, Product Owner, End User Advocate) that independently analyze a proposal, emit structured assessments, and vote. The council is not a single LLM call with multiple prompts; it is a governed process with defined quorum, dissent tracking, escalation paths, and audit emission. Council sessions are correlation-scoped and fully auditable via AUDIT-category events (Part 2 §2.3.1).

**LLM Council is invoked only for high-impact or high-risk decisions.** The LLM Council is a distinct architectural mechanism from the Claude Council. Where the Claude Council uses configured personas for structured multi-perspective analysis, the LLM Council invokes multiple independent LLM instances (potentially across providers) with diverse prompts, temperatures, and contexts to produce a distribution of outputs for statistical consensus. The LLM Council is **expensive** (multiple model invocations) and **non-deterministic** (by design). It is therefore gated by an **impact classification** (Part 0 Principle 3): only decisions classified as HIGH_IMPACT or HIGH_RISK by the WorkflowManager (or explicitly requested by Human Governance) trigger LLM Council invocation.

**Execution is governed by the Loop Engine — a formal hierarchical loop architecture.** The Loop Engine replaces the traditional retry model with **five hierarchical execution loops**: Research Loop → Planning Loop → Implementation Loop → Testing Loop → Deployment Loop. Each loop has a retry budget, rollback target, checkpoint, timeout, and adaptive retry strategy. **Retry MUST NEVER repeat identical execution.** Every retry MUST modify execution strategy using failure analysis. When a loop's retry budget is exhausted, execution rolls back to the **previous loop** rather than terminating immediately — enabling cross-loop recovery and strategic re-planning. The Loop Engine is implemented via the WorkflowManager (Core Manager M7) and RetryManager (integrated subsystem).

**AI-OS contains a Learning Layer that continuously improves future execution.** The Learning Layer observes execution outcomes (success, failure, latency, resource consumption, governance decisions, human interventions), correlates them with execution context (capability set, input characteristics, environment state), and produces **learning artifacts** that improve: workflow selection, capability selection, model routing, council composition, retry policies, skill ranking, MCP selection, execution planning, failure recovery, and prompt optimization. Learning artifacts MUST contain provenance, confidence, versioning, and rollback capability. Learning is **continuous** (not batch), **scoped** (per execution context namespace), **auditable** (every learning artifact has provenance), and **reversible** (learning can be rolled back if it degrades outcomes).

**AI-OS contains an Optimization Layer that converts accumulated learning into improved future execution.** The Optimization Layer sits between the Learning Layer and Memory. It evaluates accumulated learning artifacts and determines: best model, best skills, best workflow, best retry strategy, best councils, best MCP combinations, and resource optimization. Optimization is not passive storage; it is an active architectural stage that synthesizes learning into executable policy improvements. The Optimization Layer is implemented as the Optimization Service (Engineering Service) backed by MemoryManager (Core Manager M1).

**AI-OS contains a Self-Healing Layer that attempts recovery before failure.** The Self-Healing Layer monitors execution health in real-time (via ObservabilityManager metrics, EventBus diagnostic events, capability heartbeats), and executes a **nine-stage healing pipeline**: Detect → Diagnose → Root Cause Analysis → Strategy Adaptation → Capability Substitution → Model Substitution → Workflow Adjustment → Recovery → Learning. Self-Healing is not limited to restarting services; it performs capability substitution, model substitution, workflow adjustment, and strategic adaptation. Healing should attempt to recover execution before escalation. Healing is **proactive** (pattern-based prediction), **bounded** (max healing attempts per scope), **auditable** (every healing action emits AUDIT events), and **overridable** (human intervention always takes precedence).

**Execution preparation includes generation of project artifacts.** Before execution begins, the architecture generates or updates: `Claude.md`, Project Hooks, and Execution Metadata. These are execution artifacts produced after capability discovery and before execution begins, ensuring the project environment reflects the resolved capability plan and governance decisions.

**Human intervention always overrides autonomous execution.** At any point in the execution lifecycle — planning, capability discovery, capability invocation, governance, retry, learning, optimization, healing — a human operator may intervene. Intervention takes the form of: **pause** (suspend execution, preserve state), **redirect** (modify execution plan, substitute capabilities), **escalate** (invoke LLM Council, convene Claude Council, request human review), **terminate** (graceful shutdown with compensation), or **assume control** (direct capability invocation bypassing autonomous layers). The architecture **MUST** provide synchronous intervention hooks at every architectural layer. Autonomous execution **MUST** yield to human intervention within a bounded time (configurable, default: 5 seconds).

**Vendor independence is a core architectural principle.** No execution subsystem, governance mechanism, learning algorithm, optimization strategy, or healing strategy may assume a specific vendor's models, tools, skills, or infrastructure. All vendor-specific logic is encapsulated behind **Capability Manager interfaces** (Part 1 §1.8) and **Capability Facade Services** (Part 6). The LLMManager routes across providers (local, cloud, hybrid). The MCPManager connects to any MCP-compliant server. The SkillManager executes any skill conforming to the Skill Contract. The CouncilManager supports any council implementation. The LearningLayer, OptimizationLayer, and HealingLayer operate on architectural observables (events, metrics, checkpoints), not vendor-specific telemetry. Vendor lock-in is a conformance violation.

---

#### 8.1.2 Scope

This section (8.1) defines the **architectural purpose** of the Intelligent Agent & Execution Architecture. It establishes the foundational concepts, design philosophy, architectural goals, high-level architecture, and architectural invariants that govern all subsequent sections of Part 8.

**In Scope (this Section):**
- Architectural overview and problem statement (§8.1.1)
- Scope boundaries and conformance requirements (§8.1.2)
- Design philosophy and core architectural principles (§8.1.3)
- Architectural goals with success criteria (§8.1.4)
- High-level architecture diagram and component topology (§8.1.5)
- Architectural invariants (mandatory, verified) (§8.1.6)

**In Scope (Part 8 Subsequent Sections):**
- 8.2 Capability Discovery & Planning Architecture (Capability Discovery Layer, Vercel Find Skills, skill contracts, dynamic loading, project artifact generation)
- 8.3 Execution Context & Plan Architecture (execution plans, capability graphs, governance binding, Global/Project scope resolution)
- 8.4 Council Governance Architecture (Claude Council, LLM Council, impact classification, escalation)
- 8.5 Loop Engine Architecture (hierarchical loops, retry budgets, rollback targets, checkpoints, adaptive strategies, cross-loop recovery)
- 8.6 Learning Layer Architecture (outcome observation, artifact generation, application, reversibility, provenance, confidence, versioning)
- 8.7 Optimization Layer Architecture (learning evaluation, policy synthesis, model/skill/workflow/council/MCP optimization, resource optimization)
- 8.8 Self-Healing Layer Architecture (detect, diagnose, RCA, strategy adaptation, capability/model substitution, workflow adjustment, recovery, learning)
- 8.9 Human Intervention Architecture (intervention hooks, override semantics, state preservation)
- 8.10 Vendor Independence Architecture (provider abstraction, pluggability, conformance, local/cloud/hybrid)
- 8.11 Provider Selection Architecture (model selector, routing policy engine, council selector, execution profile resolution)
- 8.12 Execution Conformance (static, dynamic, audit)

**Out of Scope (Entire Part 8):**
- Implementation code, APIs, or technology-specific details
- Core Manager internals (Parts 1, 3, 4)
- Engineering Service behavior (Part 5)
- Workflow orchestration logic (Part 7)
- Event System contracts (Part 2)
- Capability Facade Service internals (Part 6)
- Deployment, operations, or runtime optimization

---

#### 8.1.3 Design Philosophy

The Intelligent Agent & Execution Architecture is governed by the following design principles, derived from Part 0 §0.3 and elaborated for the execution domain:

| Principle ID | Principle | Rationale | Traceability |
|--------------|-----------|-----------|--------------|
| **EXEC-P-001** | **Capability-Driven, Not Agent-Driven** — Execution emerges from coordinated capability invocation, not from a monolithic agent. | Eliminates single-point-of-failure reasoning, enables capability-level governance/retry/learning, supports vendor independence. | Part 0 §0.3 Principle 7, Part 6 CFS-P-003 |
| **EXEC-P-002** | **Hermes as Sole Orchestrator** — All execution coordination flows through Hermes Kernel; no autonomous agent owns execution. | Preserves kernel invariants (Part 1), enables centralized observability, ensures conformance enforcement. | Part 1 §1.5, Part 1 INV-LC-001 |
| **EXEC-P-003** | **Event-First Execution** — Every execution step (discovery, invocation, governance, retry, learning, optimization, healing) emits events. | Full traceability (Part 0 Principle 12), deterministic replay (Part 2 §2.11), audit completeness. | Part 0 §0.3 Principle 1, Part 2 §2.1.3 |
| **EXEC-P-004** | **Governance Before Execution** — Capability plans MUST pass governance gates before invocation. | Enforces Part 0 Principle 3 (Council Governance), prevents unauthorized capability use. | Part 0 §0.3 Principle 3, Part 3 §3.6 (SecurityManager) |
| **EXEC-P-005** | **Strategic Retry, Not Blind Retry** — Retry modifies strategy; identical repetition is forbidden. | Prevents failure loops, enables capability substitution, respects resource budgets. | Part 1 §1.12, Part 7 §7.7 |
| **EXEC-P-006** | **Continuous, Scoped, Reversible Learning** — Learning is ongoing, namespace-scoped, and rollback-capable. | Prevents learning drift, enables A/B comparison, supports compliance rollback. | Part 0 §0.3 Principle 6, Part 4 §4.4 (MemoryManager) |
| **EXEC-P-007** | **Proactive Healing, Reactive Fallback** — Self-healing predicts and prevents; fallback handles the unpredictable. | Reduces CRITICAL/FATAL events (Part 1 §1.12.1), minimizes human escalation. | Part 1 §1.12, Part 3 §3.7 (ObservabilityManager) |
| **EXEC-P-008** | **Human Authority Is Absolute** — Human intervention synchronously overrides all autonomous layers. | Safety invariant, regulatory compliance, trust requirement. | Part 0 §0.3 Principle 3, Part 3 §3.6 (SecurityManager) |
| **EXEC-P-009** | **Vendor Independence by Construction** — No execution logic assumes a specific provider. | Strategic flexibility, avoids lock-in, enables best-of-breed composition. | Part 0 §0.3 Principle 8, Part 1 §1.8 (LLMManager, MCPManager) |
| **EXEC-P-010** | **Execution Context Is Data, Not Code** — Plans, contexts, policies are declarative data structures. | Enables serialization, replay, diffing, policy-as-code, audit. | Part 2 §2.2 (Event Model), Part 7 §7.3 (Workflow Model) |
| **EXEC-P-011** | **Scope-Aware Resolution** — Capability resolution follows Project → Global → External hierarchy. | Ensures project sovereignty, enables global reuse, prevents scope leakage. | Part 0 §0.3 Principle 8, Part 1 §1.6 (Ownership) |
| **EXEC-P-012** | **Optimization as Architecture** — Optimization is an explicit architectural layer, not implicit behavior. | Makes improvement visible, governable, auditable, and reversible. | Part 0 §0.3 Principle 6, Part 4 §4.4 (MemoryManager) |
| **EXEC-P-013** | **Loops Over Retries** — Execution is structured as hierarchical loops with rollback targets, not flat retry chains. | Enables cross-loop recovery, strategic re-planning, bounded failure domains. | Part 1 §1.12, Part 7 §7.7 |
| **EXEC-P-014** | **Artifacts Over State** — Learning, optimization, and healing produce versioned artifacts with provenance. | Enables rollback, audit, A/B comparison, compliance, deterministic replay. | Part 2 §2.11 (Replay), Part 0 Principle 12 |
| **EXEC-P-015** | **Intelligent Provider Selection** — Model, routing, and council selection is an explicit architectural stage, not implicit behavior. | Makes provider selection visible, governable, auditable, and adaptable through Learning and Optimization. | Part 0 §0.3 Principle 8, Part 1 §1.8 (LLMManager, CouncilManager) |
| **EXEC-P-016** | **Adaptive Confidence** — Capability confidence scores evolve through Execution → Learning → Optimization → Ranking. | Prevents stale capability rankings, enables continuous improvement of discovery quality. | Part 0 §0.3 Principle 6, Part 4 §4.4 (MemoryManager) |
| **EXEC-P-017** | **Governance Quality Learning** — Learning Layer evaluates council effectiveness and composition quality. | Enables Optimization to improve council selection, persona configuration, and escalation thresholds. | Part 0 §0.3 Principle 6, Part 3 §3.6 (CouncilManager) |

**Invariant:** `INV-EXEC-PHILOSOPHY-001` — Every architectural decision in subsequent sections of Part 8 (8.2–8.12) MUST be traceable to one or more of the above principles. A design that violates a principle is non-conformant.

**Invariant:** `INV-EXEC-PHILOSOPHY-002` — The principles EXEC-P-001 through EXEC-P-017 are **immutable** for v1.0. Modification requires ARB approval and a major specification revision.

---

#### 8.1.4 Architectural Goals

The Intelligent Agent & Execution Architecture MUST achieve the following goals. Each goal has a measurable success criterion for conformance verification.

| Goal ID | Goal | Success Criterion | Verification |
|---------|------|-------------------|--------------|
| **EXEC-DG-001** | **Capability Discovery Completeness** | For any valid intent, the capability discovery phase produces a valid, executable capability plan (or explicit UNSATISFIABLE result) within 30s. | Integration test: 1000 intent corpus, 99.9% plan validity |
| **EXEC-DG-002** | **Zero Un-governed Execution** | No capability invocation occurs without passing the applicable governance gate (Claude Council for standard, LLM Council for HIGH_IMPACT/HIGH_RISK). | Conformance test: inject un-governed invocation → must be rejected |
| **EXEC-DG-003** | **Loop Engine Effectiveness** | For TRANSIENT/DEGRADED failures, hierarchical loops achieve success in ≥85% of cases without human intervention; cross-loop rollback recovers ≥60% of exhausted-loop executions. | Chaos test: injected failure corpus, measure autonomous recovery rate |
| **EXEC-DG-004** | **Learning Convergence** | Learning Layer improves capability selection accuracy by ≥15% over static baseline within 1000 executions per context namespace. | A/B test: learned vs. static policy, measure success rate delta |
| **EXEC-DG-005** | **Optimization Synthesis** | Optimization Layer synthesizes learning artifacts into executable policy improvements that yield ≥10% latency/resource reduction over non-optimized baseline. | Benchmark test: optimized vs. baseline execution, measure resource delta |
| **EXEC-DG-006** | **Healing Preemption** | Self-Healing Layer prevents ≥75% of CRITICAL escalations by initiating healing during DEGRADED window. | Chaos test: injected degradation patterns, measure prevention rate |
| **EXEC-DG-007** | **Human Override Latency** | Human intervention hook acknowledges and yields execution control within 5s (configurable) at any layer. | Latency test: intervention at each layer, measure yield time |
| **EXEC-DG-008** | **Vendor Interchangeability** | Swapping any single provider (LLM, MCP, Skill, Council) requires zero execution logic changes; only configuration and adapter registration. | Migration test: provider swap, verify functional parity |
| **EXEC-DG-009** | **Local/Cloud/Hybrid Parity** | Execution produces semantically equivalent outcomes across local, cloud, and hybrid provider configurations for the same capability plan. | Equivalence test: same plan, three provider topologies, compare outcomes |
| **EXEC-DG-010** | **Deterministic Replay** | Given identical execution context and event log, replay produces bit-for-bit identical capability invocation sequence and outcomes (modulo external side effects). | Replay test: record/replay 100 executions, verify determinism |
| **EXEC-DG-011** | **Audit Completeness** | Every execution decision (plan, governance, retry, learning, optimization, healing, intervention) emits AUDIT-category events with full correlation. | Audit test: verify event emission for 100% of decision points |
| **EXEC-DG-012** | **Scope Resolution Correctness** | Capability resolution follows Project → Global → External hierarchy; no cross-scope leakage; project overrides global, global overrides external. | Scope test: conflicting capabilities at each scope, verify resolution order |
| **EXEC-DG-013** | **Resource Boundedness** | Execution context resource consumption (tokens, tool calls, memory, time) is bounded by declared limits; overrun triggers DEGRADED → retry/healing. | Stress test: resource exhaustion scenarios, verify bounding |
| **EXEC-DG-014** | **Provider Selection Intelligence** | Model/router selection produces measurably better cost/latency/quality tradeoffs than static configuration within 500 executions. | A/B test: intelligent vs. static routing, measure Pareto improvement |
| **EXEC-DG-015** | **Council Learning Effectiveness** | Learning Layer identifies optimal council compositions that reduce governance cycles by ≥20% while maintaining decision quality. | Governance test: learned vs. baseline council configs, measure cycle count |

---

#### 8.1.5 High-Level Architecture

The Intelligent Agent & Execution Architecture comprises **nine (9) architectural layers** plus the **Global/Project Environment Scope Resolution** substrate that transforms intent into governed, observable, learnable, optimizable, healable outcomes. Each layer is a distinct architectural component with defined interfaces, lifecycle, and conformance criteria. Layers communicate **exclusively via the EventBus** (Part 2) and **Capability Facade Services** (Part 6). No layer has direct access to another layer's internals.

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                      AI-OS EXECUTION ARCHITECTURE — GLOBAL/PROJECT SCOPE                   │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                            │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ GLOBAL ENVIRONMENT                                                                 │   │
│   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│   │  │ Global       │ │ Obsidian     │ │ Graphify     │ │ Global       │              │   │
│   │  │ Memory       │ │ Second Brain │ │ Knowledge    │ │ Skills       │              │   │
│   │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │   │
│   │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐              │   │
│   │  │ Global MCP   │ │ Global       │ │ Global       │ │ Global       │              │   │
│   │  │ Servers      │ │ Councils     │ │ Learning     │ │ Config       │              │   │
│   │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘              │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                                             ▼ Resolution: Project → Global → External     │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ PROJECT ENVIRONMENT                                                                │   │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐           │   │
│   │  │ ai-os.yaml│ │ Claude.md │ │ Project   │ │ Project   │ │ Project   │           │   │
│   │  │           │ │           │ │ Hooks     │ │ Memory    │ │ Skills    │           │   │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘ └───────────┘           │   │
│   │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐                          │   │
│   │  │ Project   │ │ Project   │ │ Project   │ │ Project   │                          │   │
│   │  │ MCPs      │ │ Models    │ │ Config    │ │ Learning  │                          │   │
│   │  └───────────┘ └───────────┘ └───────────┘ └───────────┘                          │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │

**Layer 1 Planning Flow:** Intent Analyzer (Engineering Service) analyzes the input intent and emits a structured capability requirement set. The Capability Discovery Layer then resolves those requirements via Vercel Find Skills, ranking, dependency resolution, version compatibility analysis, duplicate detection, confidence scoring, and recommendation — producing a discovered capability set. Artifact Generation creates execution preparation artifacts (Claude.md, Project Hooks, Execution Metadata) from the discovery results. The Capability Plan Builder (Execution Service) assembles the final executable capability plan with governance bindings, retry policies, and loop configuration — which is emitted as a `CAPABILITY_PLAN_READY` event via EventBus to Layer 2.
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ HERMES KERNEL (Orchestration Core)                                                 │   │
│   │  EventBus(C1) │ ServiceRegistry(C2) │ ConfigManager(C3) │ LifecycleManager(C4)    │   │
│   │  Memory(M1)   │ LLM(M2)            │ MCP(M3)           │ Storage(M4)             │   │
│   │  Context(M5)  │ ExecutionCtx(M6)   │ Workflows(M7)     │ Security(M8)            │   │
│   │  Observability(M9)                                                                    │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │

**Note:** The Core Manager labels in the diagram (Memory(M1)–Observability(M9)) denote **logical execution responsibilities** assigned to each Core Manager. The authoritative Core Manager definitions, interfaces, and conformance criteria are specified in Parts 3 and 4.

│                                             │                                              │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 1: PLANNING & CAPABILITY DISCOVERY                                           │   │
│   │  ┌─────────────────┐  ┌─────────────────────┐  ┌─────────────────┐                │   │
│   │  │ Intent Analyzer │─▶│ Capability Discovery│─▶│ Artifact        │                │   │
│   │  │ (Engineering    │  │ Layer (Vercel Find  │  │ Generation      │                │   │
│   │  │  Service)       │  │  Skills, Ranking,   │  │ (Claude.md,     │                │   │
│   │  └─────────────────┘  │  Dependency Res,    │  │  Hooks, Meta)   │                │   │
│   │                       │  Version Compat,    │  └────────┬────────┘                │   │
│   │                       │  Dup Detection,     │           │                        │   │
│   │                       │  Confidence, Rec)   │           ▼                        │   │
│   │                       └─────────────────────┘  ┌─────────────────┐                │   │
│   │                                                │ Capability Plan │                │   │
│   │                                                │ Builder         │                │   │
│   │                                                │ (Execution Svc) │                │   │
│   │                                                └─────────────────┘                │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 2: PROVIDER SELECTION                                                          │   │
│   │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐        │   │
│   │  │ Model Selector      │─▶│ Routing Policy      │─▶│ Council Selector    │        │   │
│   │  │ (LLMManager)        │  │ Engine              │  │ (CouncilManager)    │        │   │
│   │  │ • Local/Cloud/      │  │ (LLMManager +       │  │ • Composition     │        │   │
│   │  │   Hybrid            │  │  WorkflowManager)   │  │ • Persona Config  │        │   │
│   │  │ • Capability Match  │  │ • Cost/Latency/     │  │ • Quorum Rules    │        │   │
│   │  │ • Provider Rank     │  │   Quality Tradeoff  │  │ • Escalation      │        │   │
│   │  └─────────────────────┘  └─────────────────────┘  └────────┬────────────┘        │   │
│   │                                                             │                      │   │
│   │                                                             ▼                      │   │
│   │                                              ┌───────────────────────────────┐      │   │
│   │                                              │ Resolved Execution Profile    │      │   │
│   │                                              │ (model, routing, council, mcp)│      │   │
│   │                                              └───────────────────────────────┘      │   │
│   │                                                             ▼                      │   │
│   │                                          ┌───────────────────────────────────────┐   │   │
│   │                                          │ Provider selection produces an        │   │   │
│   │                                          │ advisory execution profile that       │   │   │
│   │                                          │ remains subject to governance         │   │   │
│   │                                          │ approval and human override prior     │   │   │
│   │                                          │ to execution.                         │   │   │
│   │                                          └───────────────────────────────────────┘   │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 3: GOVERNANCE GATES                                                          │   │
│   │  ┌─────────────────────┐    ┌─────────────────────────────────────────┐           │   │
│   │  │ Impact Classifier   │───▶│ Governance Router                       │           │   │
│   │  │ (WorkflowManager)   │    │                                         │           │   │
│   │  └─────────────────────┘    │ ┌───────────────┐  ┌───────────────┐   │           │   │
│   │                             │ │ Claude Council │  │ LLM Council   │   │           │   │
│   │                             │ │ (CouncilMgr)  │  │ (LLMManager)  │   │           │   │
│   │                             │ │ Quorum,       │  │ Statistical   │   │           │   │
│   │                             │ │ Dissent,      │  │ Consensus,    │   │           │   │
│   │                             │ │ Escalation    │  │ HIGH_IMPACT   │   │           │   │
│   │                             │ └───────┬───────┘  │ ✓ HIGH_RISK   │   │           │   │
│   │                             │         │          └───────────────┘   │           │   │
│   │                             │         │                                │           │   │
│   │                             │         └────────────────────────────────┘           │   │
│   │                             └─────────────────────────────────────────┘           │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 4: CAPABILITY EXECUTION                                                      │   │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│   │  │ Skill       │  │ MCP         │  │ Memory      │  │ Council     │                │   │
│   │  │ Service     │  │ Service     │  │ Service     │  │ Service     │                │   │
│   │  │ (SkillMgr)  │  │ (MCPMgr)    │  │ (MemoryMgr) │  │ (CouncilMgr)│                │   │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                │   │
│   │         │                │                │                │                        │   │
│   │         └────────────────┼────────────────┼────────────────┘                        │   │
│   │                          ▼                ▼                                          │   │
│   │              ┌─────────────────────────────────────────┐                           │   │
│   │              │       Execution Context Manager         │                           │   │
│   │              │  (correlation scope, resource budgets,  │                           │   │
│   │              │   capability bindings, governance refs, │                           │   │
│   │              │   loop iteration, checkpoint refs)      │                           │   │
│   │              └─────────────────────────────────────────┘                           │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │

**Execution contexts are ephemeral, correlation-scoped execution environments whose lifecycle is bound to a single execution unless explicitly persisted.**
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 5: LOOP ENGINE (Hierarchical Execution Loops)                                │   │
│   │                                                                                     │   │
│   │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │   │
│   │  │ Research Loop  │─▶│ Planning Loop  │─▶│ Implementation │─▶│ Testing Loop   │    │   │
│   │  │                │  │                │  │ Loop           │  │                │    │   │
│   │  │ • Retry Budget │  │ • Retry Budget │  │ • Retry Budget │  │ • Retry Budget │    │   │
│   │  │ • Rollback →   │  │ • Rollback →   │  │ • Rollback →   │  │ • Rollback →   │    │   │
│   │  │   (start)      │  │   Research     │  │   Planning     │  │   Impl         │    │   │
│   │  │ • Checkpoint   │  │ • Checkpoint   │  │ • Checkpoint   │  │ • Checkpoint   │    │   │
│   │  │ • Timeout      │  │ • Timeout      │  │ • Timeout      │  │ • Timeout      │    │   │
│   │  │ • Adaptive     │  │ • Adaptive     │  │ • Adaptive     │  │ • Adaptive     │    │   │
│   │  │   Strategy     │  │   Strategy     │  │   Strategy     │  │   Strategy     │    │   │
│   │  └────────────────┘  └────────────────┘  └────────────────┘  └───────┬────────┘    │   │
│   │                                                                      │               │   │
│   │                         ┌────────────────────────────────────────────┘               │   │
│   │                         ▼                                                            │   │
│   │              ┌────────────────┐                                                      │   │
│   │              │ Deployment Loop│                                                      │   │
│   │              │ • Retry Budget │                                                      │   │
│   │              │ • Rollback →   │                                                      │   │
│   │              │   Testing      │                                                      │   │
│   │              │ • Checkpoint   │                                                      │   │
│   │              │ • Timeout      │                                                      │   │
│   │              │ • Adaptive     │                                                      │   │
│   │              │   Strategy     │                                                      │   │
│   │              └────────────────┘                                                      │   │
│   │                                                                                     │   │
│   │  Loop Engine Orchestration (WorkflowManager + RetryManager):                        │   │
│   │  • Failure Classification → Strategy Selection (NEVER identical retry)             │   │
│   │  • Strategy: param-adjust → capability-sub → model-sub → workflow-restructure      │   │
│   │  →  │   • Exhaustion → Rollback to Previous Loop (not termination)                         │   │
│   │  • Checkpoint/Restore via WorkflowManager                                         │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 6: LEARNING LAYER                                                            │   │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                     │   │
│   │  │ Outcome         │─▶│ Artifact        │─▶│ Artifact Store  │                     │   │
│   │  │ Observer        │  │ Generator       │  │ (MemoryManager) │                     │   │
│   │  │ (Learning Svc)  │  │ (Learning Svc)  │  │                 │                     │   │
│   │  └─────────────────┘  └─────────────────┘  └────────┬────────┘                     │   │
│   │                                                     │                               │   │
│   │  Learning Artifacts improve:                        │                               │   │
│   │  • Workflow Selection    • Capability Selection    │                               │   │
│   │  • Model Routing         • Council Composition     │                               │   │
│   │  • Retry Policies        • Skill Ranking           │                               │   │
│   │  • MCP Selection         • Execution Planning      │                               │   │
│   │  • Failure Recovery      • Prompt Optimization     │                               │   │
│   │  • Provider Selection    • Council Effectiveness   │                               │   │
│   │  • Confidence Calibration│ Environment Optimization │                               │   │
│   │                                                       │                               │   │
│   │  Artifact Requirements: provenance, confidence,     │                               │   │
│   │  versioning, rollback capability, namespace scope   │                               │   │
│   └─────────────────────────────────────────────────────┼───────────────────────────────┘   │
│                                                         │                                    │
│                              EventBus (C1) ◄────────────┘                                    │
│                                                         ▼                                    │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 7: OPTIMIZATION LAYER                                                        │   │
│   │  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐        │   │
│   │  │ Learning Evaluator  │─▶│ Policy Synthesizer  │─▶│ Optimization        │        │   │
│   │  │ (Optimization Svc)  │  │ (Optimization Svc)  │  │ Applicator          │        │   │
│   │  └─────────────────────┘  └─────────────────────┘  │ (Optimization Svc)  │        │   │
│   │                                                     └──────────┬──────────┘        │   │
│   │                                                                │                  │   │
│   │  Optimization Determines:                                      │                  │   │
│   │  • Best Model          • Best Skills          • Best Workflow │                  │   │
│   │  • Best Retry Strategy • Best Councils        • Best MCP     │                  │   │
 │   │  Combinations        • Resource Optimization                 │                  │   │
│   │                                                                ▼                  │   │
│   │                                              ┌────────────────────────────────┐   │   │
│   │                                              │ Optimization Policy Store       │   │   │
│   │                                              │ (MemoryManager: policies,      │   │   │
│   │                                              │  rankings, thresholds, configs) │   │   │
│   │                                              └────────────────────────────────┘   │   │
│   │                                                             ▼                      │   │
│   │                                          ┌───────────────────────────────────────┐   │   │
│   │                                          │ Optimization publishes versioned     │   │   │
│   │                                          │ policies consumed by Planning,       │   │   │
│   │                                          │ Discovery, Provider Selection, Loop  │   │   │
│   │                                          │ Engine, and Council Manager — policy │   │   │
│   │                                          │ publication, not direct control.     │   │   │
│   │                                          └───────────────────────────────────────┘   │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 8: SELF-HEALING LAYER                                                        │   │
│   │                                                                                     │   │
│   │  ┌──────────┐  ┌──────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│   │  │ Detect   │─▶│ Diagnose │─▶│ Root Cause  │─▶│ Strategy     │─▶│ Capability   │  │   │
│   │  │ (Healing │  │ (Healing │  │ Analysis    │  │ Adaptation   │  │ Substitution │  │   │
│   │  │  Svc)    │  │  Svc)    │  │ (Healing    │  │ (Healing     │  │ (Healing     │  │   │
│   │  └──────────┘  └──────────┘  │  Svc)       │  │  Svc)        │  │  Svc)        │  │   │
│   │                              └─────────────┘  └──────────────┘  └──────┬───────┘  │   │
│   │                                                                         │          │   │
│   │                       ┌─────────────────────┐  ┌──────────────┐        │          │   │
│   │                       │ Model Substitution  │  │ Workflow     │◄───────┘          │   │
│   │                       │ (Healing Svc)       │  │ Adjustment   │                   │   │
│   │                       └─────────────────────┘  │ (Healing     │                   │   │
│   │                                            ┌───┘  Svc)        │                   │   │
│   │                                            │                 │                   │   │
│   │                                            ▼                 ▼                   │   │
│   │                                  ┌──────────────────┐  ┌──────────────────┐    │   │
│   │                                  │ Recovery         │  │ Learning         │    │   │
│   │                                  │ (Healing Svc)    │  │ (Learning Layer) │    │   │
│   │                                  └──────────────────┘  └──────────────────┘    │   │
│   │                                                                                 │   │
│   │  Healing Pipeline: Detect → Diagnose → RCA → Strategy Adaptation →             │   │
│   │  Capability Substitution → Model Substitution → Workflow Adjustment →          │   │
│   │  Recovery → Learning                                                             │   │
│   │  Not limited to restarts: performs substitution, adaptation, strategic healing  │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                             │                                              │
│                              EventBus (C1) ◄────────────────────────────────────────────┘   │
│                                             ▼                                              │
│   ┌────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LAYER 9: HUMAN INTERVENTION                                                        │   │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                     │   │
│   │  │ Intervention    │─▶│ Override        │─▶│ State           │                     │   │
│   │  │ Hook Registry   │  │ Executor        │  │ Preservation    │                     │   │
│   │  │ (SecurityMgr)   │  │ (SecurityMgr)   │  │ (StateMgr)      │                     │   │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────┘                     │   │
│   │         │                     │                     │                               │   │
│   │         └─────────────────────┼─────────────────────┘                               │   │
│   │                               ▼                                                     │   │
│   │                   ┌─────────────────────────────────┐                             │   │
│   │                   │ Intervention Types:             │                             │   │
│   │                   │ PAUSE, REDIRECT, ESCALATE,      │                             │   │
│   │                   │ TERMINATE, ASSUME_CONTROL       │                             │   │
│   │                   └─────────────────────────────────┘                             │   │
│   └────────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                            │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Layer Interaction Protocol:**

| From Layer | To Layer | Mechanism | Event Category |
|------------|----------|-----------|----------------|
| Layer 1 (Planning/Discovery) | Layer 2 (Provider Selection) | `CAPABILITY_PLAN_READY` event | CONTROL |
| Layer 2 (Provider Selection) | Layer 3 (Governance) | `EXECUTION_PROFILE_READY` event | CONTROL |
| Layer 3 (Governance) | Layer 4 (Execution) | `GOVERNANCE_APPROVED` / `GOVERNANCE_REQUIRED` | AUDIT / CONTROL |
| Layer 4 (Execution) | Layer 5 (Loop Engine) | `CAPABILITY_FAILED` / `CAPABILITY_DEGRADED` / `LOOP_ITERATION_COMPLETE` | DIAGNOSTIC / CONTROL |
| Layer 5 (Loop Engine) | Layer 4 (Execution) | `RETRY_STRATEGY_SELECTED` / `LOOP_ROLLBACK_INITIATED` / `CHECKPOINT_RESTORED` | CONTROL |
| Layer 4 (Execution) | Layer 6 (Learning) | `EXECUTION_OUTCOME` (success/failure/latency/resources) | DATA |
| Layer 6 (Learning) | Layer 1/2/4/5/7 (Planning/Provider/Execution/Loop/Optimization) | `LEARNING_ARTIFACT_PUBLISHED` | DATA |
| Layer 6 (Learning) | Layer 7 (Optimization) | `LEARNING_BATCH_READY` (accumulated artifacts) | DATA |
| Layer 7 (Optimization) | Layer 1/2/4/5 (Planning/Provider/Execution/Loop) | `OPTIMIZATION_POLICY_PUBLISHED` | DATA |
| Layer 4/8 (Execution/Healing) | Layer 8 (Healing) | `ANOMALY_DETECTED` / `HEALING_ACTION_COMPLETED` | DIAGNOSTIC |
| Layer 8 (Healing) | Layer 4/5/6 (Execution/Loop/Learning) | `HEALING_ACTION_EXECUTED` / `RCA_COMPLETE` / `RECOVERY_COMPLETE` | CONTROL / DATA |
| Any Layer | Layer 9 (Human) | `HUMAN_INTERVENTION_REQUESTED` | AUDIT |
| Layer 9 (Human) | Any Layer | `INTERVENTION_OVERRIDE` (PAUSE/REDIRECT/ESCALATE/TERMINATE/ASSUME_CONTROL) | CONTROL |

**Invariant:** `INV-EXEC-LAYER-001` — Layers communicate **exclusively** via EventBus events. No direct layer-to-layer method calls are permitted in RUNNING state.

**Invariant:** `INV-EXEC-LAYER-002` — Each layer is implemented as one or more **Services** (BaseService-derived) registered in ServiceRegistry, or **Core Managers** accessed via singleton accessors. No layer exists outside the kernel's ownership model (Part 1 §1.6).

**Invariant:** `INV-EXEC-LAYER-003` — Layer ordering is **architectural**, not temporal. Layers may execute concurrently for different correlation IDs. Layer N+1 for correlation C1 may execute while Layer N for correlation C2 executes.

**Invariant:** `INV-EXEC-LAYER-004` — Global/Project scope resolution **MUST** complete before Layer 1 (Planning & Capability Discovery) begins. The resolved capability set is passed as input to the Capability Discovery Layer.

---

#### 8.1.6 Architectural Invariants

The following invariants are **mandatory** and verified by automated conformance tooling at initialization, during RUNNING state, and at shutdown. They are the non-negotiable architectural contracts of the Intelligent Agent & Execution Architecture.

##### 8.1.6.1 Structural Invariants

| Invariant ID | Statement | Verification Point |
|--------------|-----------|-------------------|
| **INV-EXEC-STR-001** | Exactly **nine (9)** execution layers exist. No layer may be added, removed, or merged without ARB approval and Part 8 revision. | Static analysis, spec validation |
| **INV-EXEC-STR-002** | Each layer is implemented as Service(s) and/or Core Manager(s) per Part 1 ownership model. No layer exists as standalone code outside kernel ownership. | ServiceRegistry audit, kernel accessor verification |
| **INV-EXEC-STR-003** | Layer 1 (Planning & Capability Discovery) **MUST** include the Capability Discovery Layer (Vercel Find Skills, ranking, dependency resolution, version compatibility, duplicate detection, confidence scoring, recommendation, metadata validation). No capability plan may be constructed without discovered skill set. | Integration test: plan without discovery → rejected |
| **INV-EXEC-STR-004** | Layer 1 **MUST** generate execution artifacts (`Claude.md`, Project Hooks, Execution Metadata) after capability discovery and before execution begins. | Artifact verification: artifacts exist and reflect resolved capability plan |
| **INV-EXEC-STR-005** | **Layer 3 (Governance)** **MUST** include both Claude Council (CouncilManager) and LLM Council (LLMManager) pathways. Impact classification **MUST** route to correct pathway. | Conformance test: HIGH_IMPACT → LLM Council, standard → Claude Council |
| **INV-EXEC-STR-006** | **Layer 4 (Execution)** **MUST** invoke capabilities exclusively through Capability Facade Services (Part 6). No direct Core Manager access from execution layer. | Static analysis: no `kernel.<manager>` calls in Layer 4 services |
| **INV-EXEC-STR-007** | **Layer 5 (Loop Engine)** **MUST** implement five hierarchical loops (Research, Planning, Implementation, Testing, Deployment) with retry budget, rollback target, checkpoint, timeout, and adaptive strategy per loop. | Loop Engine policy validation: all five loops defined with required parameters |
| **INV-EXEC-STR-008** | **Layer 5** **MUST** enforce: **Retry NEVER repeats identical execution.** Every retry MUST modify execution strategy using failure analysis. Identical retry is a conformance violation. | Policy execution trace: strategy hash differs per retry attempt |
| **INV-EXEC-STR-009** | **Layer 5** **MUST** roll back to previous loop on retry budget exhaustion (not terminate). Cross-loop rollback is mandatory. | Chaos test: loop exhaustion → verify rollback to previous loop |
| **INV-EXEC-STR-010** | **Layer 6 (Learning)** **MUST** persist learning artifacts to MemoryManager with explicit namespace scoping, provenance, confidence, versioning, and rollback capability. Cross-namespace learning leakage is prohibited. | MemoryManager query: artifacts have namespace, provenance, confidence, version, rollback proc |
| **INV-EXEC-STR-011** | **Layer 7 (Optimization)** **MUST** evaluate learning artifacts and synthesize optimization policies for: model, skills, workflow, retry strategy, councils, MCP combinations, resources. Optimization policies MUST be versioned and auditable. | Optimization Service audit: policies exist for all seven domains, versioned, auditable |
| **INV-EXEC-STR-012** | **Layer 8 (Self-Healing)** **MUST** implement the nine-stage healing pipeline: Detect → Diagnose → RCA → Strategy Adaptation → Capability Substitution → Model Substitution → Workflow Adjustment → Recovery → Learning. Healing during FATAL is prohibited (emergency shutdown only). | Healing Service test: DEGRADED → pipeline executes → verify no FATAL escalation |
| **INV-EXEC-STR-013** | **Layer 9 (Human Intervention)** **MUST** provide synchronous override hooks at **every** layer. Override acknowledgment **MUST** complete within configurable bound (default 5s). | Latency test: intervention at each layer, measure ack time |
| **INV-EXEC-STR-014** | All vendor-specific logic **MUST** be encapsulated behind Capability Manager interfaces (LLMManager, MCPManager, SkillManager, CouncilManager). Zero vendor assumptions in execution layers. | Static analysis: no vendor SDK imports in Layer 1–9 services |
| **INV-EXEC-STR-015** | Capability resolution **MUST** follow Project → Global → External hierarchy. Project overrides Global; Global overrides External. No cross-scope leakage. | Scope resolution test: conflicting capabilities at each scope, verify order |

##### 8.1.6.2 Runtime Invariants

| Invariant ID | Statement | Verification Point |
|--------------|-----------|-------------------|
| **INV-EXEC-RT-001** | Every execution step emits at least one EventBus event with valid `correlationId`, `causationId`, and `ComponentIdentity`. | EventBus instrumentation: 100% event coverage in integration tests |
| **INV-EXEC-RT-002** | Capability discovery (Capability Discovery Layer) **MUST** complete before any capability invocation. No speculative execution. | Sequence verification: discovery event precedes all invocation events per correlationId |
| **INV-EXEC-RT-003** | Governance decision **MUST** be emitted as AUDIT-category event before capability invocation. No invocation without governance event. | Event ordering verification: GOVERNANCE_* event causationId → CAPABILITY_EXECUTE_REQUEST |
| **INV-EXEC-RT-004** | Retry strategy selection **MUST** produce a different execution strategy at each attempt (parameter change, capability substitution, model substitution, workflow restructure, or escalation). | Policy execution trace: strategy hash differs per attempt |
| **INV-EXEC-RT-005** | Learning artifact application **MUST** be reversible. Every applied artifact has a corresponding rollback procedure registered. | LearningLayer audit: rollback procedure exists for each artifact |
| **INV-EXEC-RT-006** | Healing actions **MUST** emit AUDIT-category events with full context (anomaly detected, action selected, action result). | EventBus audit: HEALING_* events present for every healing cycle |
| **INV-EXEC-RT-007** | Human intervention **MUST** suspend autonomous execution within the configured bound. No autonomous action may execute after override acknowledgment. | Concurrency test: intervention + autonomous action race, verify suspension |
| **INV-EXEC-RT-008** | Execution context resource budgets (tokens, tool calls, memory, time) **MUST** be enforced at capability invocation boundaries. Overrun triggers DEGRADED classification. | Resource test: budget exhaustion → verify DEGRADED event and retry/healing trigger |
| **INV-EXEC-RT-009** | All layers **MUST** participate in deterministic replay (Part 2 §2.11). Replay of identical event log produces identical capability invocation sequence. | Replay test: record/replay determinism verification |
| **INV-EXEC-RT-010** | Vendor interchange **MUST NOT** require execution layer code changes. Provider swap validated by configuration-only migration. | Migration test: provider swap, zero code changes in Layers 1–9 |
| **INV-EXEC-RT-011** | Loop Engine **MUST** maintain checkpoint state per loop iteration. Checkpoint restoration **MUST** reproduce identical execution context. | Checkpoint test: restore → verify context equivalence |
| **INV-EXEC-RT-012** | Optimization policies **MUST** be applied before subsequent execution planning. Stale policies **MUST** be detected and refreshed. | Planning test: policy version check → verify freshness |

##### 8.1.6.3 Failure Invariants

| Invariant ID | Statement | Verification Point |
|--------------|-----------|-------------------|
| **INV-EXEC-FL-001** | Capability invocation failure **MUST** be classified per Part 1 §1.12.1 (TRANSIENT/DEGRADED/CRITICAL/FATAL) before retry strategy selection. | Failure injection: verify classification precedes retry |
| **INV-EXEC-FL-002** | Loop retry exhaustion **MUST** trigger rollback to previous loop via WorkflowManager checkpointing (Part 7). No silent failure absorption. | Chaos test: loop exhaustion → verify cross-loop rollback event |
| **INV-EXEC-FL-003** | Learning Layer **MUST NOT** apply artifacts during active failure recovery (RETRY_IN_PROGRESS, HEALING_IN_PROGRESS, LOOP_ROLLBACK_IN_PROGRESS). Learning is deferred to post-recovery. | State verification: learning artifact application blocked during recovery |
| **INV-EXEC-FL-004** | Self-Healing Layer **MUST** respect healing attempt bounds (configurable, default 3 per scope). Unbounded healing is prohibited. | Configuration verification: bound enforced, excess attempts → CRITICAL escalation |
| **INV-EXEC-FL-005** | Human intervention **MUST** be able to terminate any in-flight execution (including retry, healing, learning, optimization, loop rollback) with guaranteed compensation. | Termination test: intervention during each layer → verify compensation completion |

##### 8.1.6.4 Governance Invariants

| Invariant ID | Statement | Verification Point |
|--------------|-----------|-------------------|
| **INV-EXEC-GOV-001** | Claude Council **MUST** achieve quorum (configurable, default ≥3 personas) for standard governance. No decision without quorum. | CouncilManager test: quorum enforcement |
| **INV-EXEC-GOV-002** | LLM Council **MUST** be invoked **only** for HIGH_IMPACT or HIGH_RISK classifications (or explicit human request). Cost/non-determinism gate is mandatory. | Impact classification test: LOW/MEDIUM → no LLM Council |
| **INV-EXEC-GOV-003** | Dissent in Claude Council **MUST** be recorded as `COUNCIL_DISSENT_REGISTERED` (AUDIT) and **MUST** trigger escalation path if quorum not reached. | Dissent test: verify audit event and escalation |
| **INV-EXEC-GOV-004** | Governance decisions **MUST** be reversible via human intervention (ESCALATE override). No governance decision is final while execution context exists. | Override test: human ESCALATE → governance decision reverted |
| **INV-EXEC-GOV-005** | Capability plan **MUST** declare governance requirements per capability (no-governance, standard, high-impact). Undeclared requirements default to standard. | Plan schema validation: governance field required per capability |

---

#### 8.1.7 Non-Goals

The following are explicitly **NOT** goals of the Intelligent Agent & Execution Architecture:

| Non-Goal | Rationale | Ownership |
|----------|-----------|-----------|
| **Implementing a Monolithic Agent** | AI-OS is an operating environment; "agents" are execution contexts, not architectural components. | N/A (anti-pattern) |
| **Providing a Specific LLM Provider** | Vendor independence (EXEC-P-009). LLMManager abstracts providers (local, cloud, hybrid). | LLMManager (Part 4) |
| **Providing a Specific MCP Server** | Vendor independence. MCPManager connects to any MCP-compliant server. | MCPManager (Part 4) |
| **Providing a Specific Skill Registry** | Vercel Find Skills is the discovery mechanism; SkillManager executes discovered skills. | SkillManager (Part 4), SkillService (Part 6) |
| **Implementing Council Personas** | CouncilManager executes council process; personas are configuration, not architecture. | CouncilManager (Part 4), CouncilService (Part 6) |
| **Defining Retry Algorithms** | Loop Engine defines strategy framework; specific algorithms are policy configuration. | WorkflowManager (Part 4), RetryManager (Part 7) |
| **Defining Learning Algorithms** | LearningLayer defines artifact framework; specific algorithms are implementation. | Learning Service (Engineering Service) |
| **Defining Optimization Algorithms** | OptimizationLayer defines synthesis framework; specific algorithms are implementation. | Optimization Service (Engineering Service) |
| **Defining Healing Algorithms** | HealingLayer defines pipeline framework; specific detectors/actions are implementation. | Healing Service (Engineering Service) |
| **Providing Human Interface** | Human intervention hooks are architectural; UI/CLI/Slack are adapter concerns. | Future Gateway Service |
| **Implementing External API Bindings** | HTTP/gRPC/WebSocket are adapter concerns, not execution architecture. | Future Gateway Service |

---

#### 8.1.8 Summary of Mandated Architectural Elements

| Category | Count | Reference |
|----------|-------|-----------|
| Execution Layers | **9** | §8.1.5 |
| Execution Scopes | **2** (Project, Global) with External fallback | §8.1.1, §8.1.5 |
| Governance Pathways | **2** (Claude Council, LLM Council) | §8.1.5, §8.1.6.1 INV-EXEC-STR-005 |
| Loop Engine Loops | **5** (Research, Planning, Implementation, Testing, Deployment) | §8.1.5 Layer 5, §8.1.6.1 INV-EXEC-STR-007 |
| Retry Stages per Loop | **N** (hierarchical, adaptive; NEVER identical) | §8.1.5 Layer 5, §8.1.6.1 INV-EXEC-STR-008 |
| Intervention Types | **5** (PAUSE, REDIRECT, ESCALATE, TERMINATE, ASSUME_CONTROL) | §8.1.5 Layer 9 |
| Impact Classifications | **3** (LOW, HIGH_IMPACT, HIGH_RISK) | §8.1.5 Layer 3 |
| Failure Classifications | **4** (TRANSIENT, DEGRADED, CRITICAL, FATAL) | Part 1 §1.12.1 |
| Healing Pipeline Stages | **9** (Detect → Diagnose → RCA → Strategy Adaptation → Capability Substitution → Model Substitution → Workflow Adjustment → Recovery → Learning) | §8.1.5 Layer 8 |
| Optimization Domains | **7** (Model, Skills, Workflow, Retry Strategy, Councils, MCP Combinations, Resources) | §8.1.5 Layer 7 |
| Learning Improvement Domains | **14** (Workflow Selection, Capability Selection, Model Routing, Council Composition, Retry Policies, Skill Ranking, MCP Selection, Execution Planning, Failure Recovery, Prompt Optimization, Provider Selection, Council Effectiveness, Confidence Calibration, Environment Optimization) | §8.1.5 Layer 6 |
| Vendor Abstraction Boundaries | **4** (LLM, MCP, Skill, Council) with Local/Cloud/Hybrid support | §8.1.6.1 INV-EXEC-STR-014 |
| Execution Artifact Types | **3** (Claude.md, Project Hooks, Execution Metadata) | §8.1.5 Layer 1, §8.1.6.1 INV-EXEC-STR-004 |

---

**END OF PART 8, SECTION 8.1 — INTELLIGENT AGENT & EXECUTION ARCHITECTURE (PURPOSE)**

*This document is FROZEN. Any modification requires Architecture Review Board approval. Subsequent sections of Part 8 (8.2–8.12) SHALL specify individual execution subsystems and MUST conform to the architectural principles, invariants, and goals established herein.*