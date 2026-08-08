# Part 12 Glossary — Multi-Agent Collaboration Architecture

This glossary is the single source of truth for every architectural term used throughout Part 12. Entries are arranged alphabetically.

For every term this document provides: Definition, Purpose, Usage, Related Components, Related Documents, Related Architecture Sections, Examples, and Notes where applicable.

---

## Terminology Governance

### Terminology Ownership

| Term Category | Owner | Change Authority | Review Cadence |
|---------------|-------|------------------|----------------|
| Core Runtime | Part 12 Architecture Team | Part 12 Lead | Per release |
| Collaboration | Part 12 Architecture Team | Part 12 Lead | Per release |
| Council / Governance | Part 12 Architecture Team | Part 12 Lead | Per release |
| Context / Knowledge | Part 12 Architecture Team | Part 12 Lead | Per release |
| Communication | Part 12 Architecture Team | Part 12 Lead | Per release |
| Security | Part 12 Architecture Team | Part 12 Lead | Per release |

**Note:** All terms in this glossary are owned by the Part 12 Architecture Team unless explicitly delegated. Changes require Part 12 Lead approval and cross-part review when terms span multiple parts.

### Term Relationships and Hierarchy

**Hierarchical Relationships:**
- `Architecture` encompasses `Architecture Layer`, `Architecture Boundary`
- `Multi-Agent System` is the top-level system form; `Agent` is the primary participant
- `Workflow` is composed of `Task` units
- `Collaboration Session` contains `Agent` interactions within `Shared Context`
- `Council` is a specialized form of `Collaboration` with `Council Decision` outputs
- `Execution Context` and `Shared Context` are both forms of `Context`
- `Agent Registry` and `Capability Registry` are both forms of `Registry`
- `EventBus` and `Communication Bus` are both forms of message transport
- `Delegation` results in `Task Delegation` records
- `Consensus` is produced by `Council` deliberation
- `Recovery` operates on `Checkpoint` state

**See-Also Relationships:**
- `Agent` → `Agent Registry`, `Agent Directory`, `Agent Capability`, `Agent Role`
- `Collaboration` → `Collaboration Manager`, `Collaboration Session`, `Collaboration Policy`
- `Council` → `Council Manager`, `Council Decision`, `Quorum`, `Consensus`
- `Context` → `Context Manager`, `Shared Context`, `Execution Context`
- `Knowledge` → `Knowledge Exchange`, `Knowledge Object`, `Shared Knowledge`, `Memory`
- `Task` → `Task Delegation`, `Delegation Manager`
- `Workflow` → `Workflow Engine`, `Workflow Manager`, `Distributed Workflow`
- `Security` → `Security Gateway`, `Governance`
- `Message` → `Event`, `Communication Bus`, `EventBus`

### Version Compatibility

**Glossary Version:** 1.0  
**Part 12 Baseline:** Phase 11+  
**Forward Compatibility:** New terms may be added in minor revisions; existing definitions require major version changes to modify.  
**Backward Compatibility:** Deprecated terms remain defined for at least one major version before removal.

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-08-07 | Initial canonical glossary |

### Aliases and Synonyms

| Canonical Term | Alias / Synonym | Status | Notes |
|----------------|-----------------|--------|-------|
| Agent Capability | Capability | Preferred | `Capability` is shorthand for `Agent Capability` in capability-management contexts. |
| Agent Registry | Registry | Contextual | `Registry` alone may refer to `Agent Registry` in agent-management contexts. |
| Collaboration Manager | Collab Manager | Informal | Used in internal discussion; formal documentation must use `Collaboration Manager`. |
| Communication Bus | Bus, Message Bus | Informal | `Bus` is acceptable in prose after first full mention. |
| Context Manager | ContextManager | Informal | Never used as a single token; always `Context Manager`. |
| Council Decision | Decision | Contextual | `Decision` alone may refer to `Council Decision` in governance contexts. |
| EventBus | Event Bus, Event-Bus | Variant | `EventBus` is canonical; variants acceptable in prose. |
| Execution Context | Exec Context | Informal | Use `Execution Context` in formal documentation. |
| Knowledge Exchange | Knowledge Transfer | Deprecated alias | Use `Knowledge Exchange`; `Knowledge Transfer` is deprecated. |
| Runtime Coordinator | Runtime | Contextual | `Runtime` alone may refer to `Runtime Coordinator` in execution contexts. |
| Workflow Engine | Engine | Contextual | `Engine` alone may refer to `Workflow Engine` in workflow contexts. |

### Deprecated Terminology

| Deprecated Term | Replacement | Deprecated In | Removed At | Migration Notes |
|-----------------|-------------|---------------|------------|----------------|
| Knowledge Transfer | Knowledge Exchange | 1.0 | TBD | Update references from transfer to exchange. |
| Arbiter | Council Manager | Pre-12 | TBD | Council Manager subsumes Arbiter role. |
| Mediator | Collaboration Manager | Pre-12 | TBD | Collaboration Manager subsumes Mediator role. |
| Agent Bus | Communication Bus | Pre-12 | TBD | Renamed for consistency with EventBus naming. |

### Reserved Terminology

The following terms are reserved for future use and must not be introduced in designs, documentation, or code without explicit Part 12 Lead approval:

- `Agent Pool`
- `Capability Graph`
- `Council Charter`
- `Delegation Chain`
- `Event Stream`
- `Knowledge Graph`
- `Policy Engine`
- `Session Store`
- `Trust Registry`
- `Workflow Definition Language`

### Cross-Part Terminology Consistency

This glossary aligns with terminology from the following parts. When terms overlap, the canonical definition from the owning part governs.

| Term | Part 12 Definition | Cross-Part Owner | Cross-Part Usage | Consistency Status |
|------|-------------------|------------------|------------------|-------------------|
| Agent | Autonomous execution unit | Part 1-15 | Core architectural participant | Aligned |
| Context | Information environment | Part 6, Part 11 | State management | Aligned |
| Event | Discrete occurrence | Part 7, Part 9 | State-change signal | Aligned |
| Message | Communication unit | Part 7, Part 11 | Structured communication | Aligned |
| Registry | Metadata store | Part 3, Part 11 | Service/entity metadata | Aligned |
| Workflow | Task sequence | Part 4, Part 11 | Process definition | Aligned |
| Schema | Structure definition | Part 11 | Data contract | Aligned |
| Security Gateway | Enforcement point | Part 10 | Trust boundary | Aligned |
| Plugin | Extension module | Part 1, Part 10 | Integration point | Aligned |

**Note:** Cross-part terms are reviewed during Part 13 cross-reference updates. Definitions may diverge when domain-specific behavior differs; such divergence must be explicitly noted in both parts.

### Evolution Policy

**Term Addition:**
1. Propose term via Part 12 Architecture Review
2. Define term following this glossary's template
3. Assign owner and review cadence
4. Add to glossary with version increment
5. Cross-reference affected parts

**Term Modification:**
1. Submit change request with rationale
2. Review impact on existing definitions, schemas, and cross-part references
3. Part 12 Lead approves; affected parts notified
4. Version bump: minor for clarification, major for semantic change

**Term Deprecation:**
1. Mark term as deprecated in glossary with replacement
2. Announce deprecation in Part 12 release notes
3. Maintain deprecated definition for at least one major version
4. Remove only after migration window closes

**Term Removal:**
1. Requires Part 12 Lead approval
2. Must have replacement term defined and adopted
3. Update all cross-references before removal
4. Version bump to major

---


## A

### Agent

**Definition:**  
An autonomous execution unit that performs work, owns state, and interacts with other agents through well-defined interfaces.

**Purpose:**  
To encapsulate responsibility, enable reuse, and allow the system to compose behavior dynamically at runtime.

**Usage:**  
Used as the primary runtime participant in collaboration, delegation, council decisions, and shared-context workflows.

**Related Components:**  
Agent Registry, Agent Directory, Collaboration Manager, Delegation Manager

**Related Documents:**  
`components.md`, `context.md`

**Related Architecture Sections:**  
12.1, 12.2, 12.3, 12.4, 12.5, 12.7, 12.8

**Examples:**  
- A summarization agent that processes documents and publishes results.  
- A validation agent that verifies council decisions before finalization.

**Notes:**  
Agents should be stateless where possible; mutable state should be confined to Execution Context or Shared Context.

---

### Agent Capability

**Definition:**  
A declared ability or skill that an agent can perform, typically described by a schema or descriptor.

**Purpose:**  
To enable discovery, compatibility checking, and dynamic task matching without hardcoding agent relationships.

**Usage:**  
Published by agents during registration and consumed by Capability Registry, Discovery, and Delegation Manager.

**Related Components:**  
Capability Registry, Discovery, Delegation Manager

**Related Documents:**  
`schemas.md`

**Related Architecture Sections:**  
12.3, 12.4

**Examples:**  
- `text.summarization`  
- `schema.validation`  
- `code.migration`

**Notes:**  
Capabilities should be coarse enough to be useful and fine enough to avoid false matches.

---

### Agent Directory

**Definition:**  
A lookup structure that maps agent identifiers to metadata, capabilities, health state, and routing information.

**Purpose:**  
To provide fast, structured access to known agents for routing, discovery, and runtime coordination.

**Usage:**  
Populated by the Registry, queried by Discovery, Scheduler, and Collaboration Manager.

**Related Components:**  
Agent Registry, Discovery, Runtime Coordinator

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.3, 12.7, 12.8

**Examples:**  
- Directory query returning all agents with `code.analysis` capability.  
- Routing table lookup for message delivery.

**Notes:**  
Directory entries should reflect current health status and capability versions.

---

### Agent Registry

**Definition:**  
The authoritative store of agent metadata, including identity, capabilities, ownership, lifecycle state, and trust attributes.

**Purpose:**  
To maintain a consistent, authoritative view of available agents and their properties.

**Usage:**  
Updated at registration, deactivation, or capability change; read by Discovery, Scheduler, and Security Gateway.

**Related Components:**  
Agent Directory, Discovery, Security Gateway

**Related Documents:**  
`components.md`, `schemas.md`

**Related Architecture Sections:**  
12.3, 12.7, 12.10

**Examples:**  
- Registering a new agent with its capability manifest.  
- Deactivating an agent after repeated health-check failures.

**Notes:**  
Registry writes should be validated and auditable.

---

### Agent Role

**Definition:**  
A named responsibility assigned to an agent within a collaboration pattern, council, or workflow.

**Purpose:**  
To define behavioral expectations and authority boundaries without coupling to a specific agent identity.

**Usage:**  
Used in Council, Collaboration Session, and Workflow Engine to assign responsibilities dynamically.

**Related Components:**  
Council, Workflow Engine, Collaboration Manager

**Related Documents:**  
`components.md`, `context.md`

**Related Architecture Sections:**  
12.2, 12.5, 12.6

**Examples:**  
- `moderator` in a council session.  
- `validator` in a multi-step workflow.

**Notes:**  
Roles should be defined independently of specific agents to allow flexible assignment.

---

## Architecture

### Architecture

**Definition:**  
The structured set of components, boundaries, interactions, and invariants that define how the Multi-Agent System is organized and evolves.

**Purpose:**  
To provide a common mental model, decision framework, and conformance baseline for implementers and reviewers.

**Usage:**  
Referenced during design reviews, ADRs, cross-cutting analysis, and Part 12 maintenance.

**Related Components:**  
All components

**Related Documents:**  
`adrs.md`, `dependency-map.md`, `review-checklist.md`

**Related Architecture Sections:**  
12.1, 12.12, 12.13

**Examples:**  
- Using the architecture to evaluate a new plugin integration point.  
- Applying architectural invariants during review.

**Notes:**  
The architecture is intentionally layered and bounded; changes should respect defined interfaces and cross-cutting concerns.

---

### Architecture Boundary

**Definition:**  
A defined interface or seam that separates concerns, ownership, or trust domains within the system.

**Purpose:**  
To isolate change, enforce modularity, and define where cross-cutting policies apply.

**Usage:**  
Enforced at plugin interfaces, message schemas, runtime module borders, and external service integrations.

**Related Components:**  
Security Gateway, Plugin system, Communication Bus

**Related Documents:**  
`adrs.md`, `components.md`

**Related Architecture Sections:**  
12.1, 12.7, 12.10

**Examples:**  
- Boundary between internal agents and external MCP tools.  
- Boundary between shared context and private execution context.

**Notes:**  
Boundaries should be explicit in schemas, APIs, and documentation.

---

### Architecture Layer

**Definition:**  
A conceptual tier in the architecture that groups related responsibilities, such as runtime, governance, or collaboration.

**Purpose:**  
To organize complexity, clarify dependencies, and guide implementation sequencing.

**Usage:**  
Referenced during design, dependency mapping, and cross-cutting review.

**Related Components:**  
All components

**Related Documents:**  
`dependency-map.md`, `adrs.md`

**Related Architecture Sections:**  
12.1, 12.13

**Examples:**  
- Collaboration layer containing Collaboration Manager and Delegation Manager.  
- Runtime layer containing Scheduler and Runtime Coordinator.

**Notes:**  
Layers should not bypass lower layers directly unless explicitly allowed by an architectural exception.

---

## C

### Capability

**Definition:**  
An abstract unit of functional ability that can be advertised, discovered, requested, and composed into tasks or workflows.

**Purpose:**  
To decouple task definition from agent identity and enable dynamic assignment.

**Usage:**  
Used by Discovery, Delegation Manager, and Workflow Engine.

**Related Components:**  
Capability Registry, Agent Registry, Delegation Manager

**Related Documents:**  
`schemas.md`

**Related Architecture Sections:**  
12.3, 12.4, 12.8

**Examples:**  
- A workflow step requiring `data.transformation`.  
- An agent advertising `security.scan`.

**Notes:**  
Capability namespaces should be stable and versioned.

---

### Capability Registry

**Definition:**  
A specialized registry that stores capability definitions, compatibility rules, and agent-capability associations.

**Purpose:**  
To support discovery, validation, and compatibility checking across agents and tasks.

**Usage:**  
Updated during agent registration and capability changes; queried during discovery and delegation.

**Related Components:**  
Agent Registry, Discovery, Delegation Manager

**Related Documents:**  
`schemas.md`, `components.md`

**Related Architecture Sections:**  
12.3, 12.4

**Examples:**  
- Querying for all agents supporting `code.review`.  
- Registering a new capability version.

**Notes:**  
Capability evolution should preserve backward compatibility or be explicitly versioned.

---

### Checkpoint

**Definition:**  
A durable, recoverable state marker within a workflow, collaboration session, or execution flow.

**Purpose:**  
To enable recovery, observability, and deterministic restart after failure.

**Usage:**  
Written by Workflow Engine, Collaboration Manager, and Failure Recovery subsystems.

**Related Components:**  
Workflow Engine, Failure Recovery, Context Manager

**Related Documents:**  
`components.md`, `events.md`

**Related Architecture Sections:**  
12.4, 12.9, 12.12

**Examples:**  
- Workflow checkpoint after task delegation completion.  
- Collaboration session checkpoint before council voting.

**Notes:**  
Checkpoints should be idempotent and replay-safe.

---

### Collaboration

**Definition:**  
Coordinated interaction among multiple agents to achieve a shared outcome through structured communication and role assignment.

**Purpose:**  
To enable complex problem solving that exceeds the scope of a single agent.

**Usage:**  
Managed by Collaboration Manager, expressed as Collaboration Sessions.

**Related Components:**  
Collaboration Manager, Communication Bus, Shared Context

**Related Documents:**  
`components.md`, `context.md`

**Related Architecture Sections:**  
12.2, 12.6, 12.7

**Examples:**  
- Multi-agent document analysis with summarization, validation, and formatting roles.  
- Collaborative code review across specialized agents.

**Notes:**  
Collaboration should respect defined policies and resource constraints.

---

### Collaboration Manager

**Definition:**  
The component responsible for establishing, monitoring, and concluding collaboration sessions among agents.

**Purpose:**  
To centralize collaboration lifecycle management and enforce collaboration policies.

**Usage:**  
Creates sessions, assigns roles, monitors progress, and coordinates session teardown.

**Related Components:**  
Collaboration Session, Communication Bus, Context Manager

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.2, 12.6, 12.7

**Examples:**  
- Starting a collaboration session for a multi-agent research task.  
- Ending a session after consensus is reached.

**Notes:**  
Session state should be recoverable and auditable.

---

### Collaboration Policy

**Definition:**  
A set of rules governing how agents may collaborate, including trust requirements, capability constraints, and conflict-handling preferences.

**Purpose:**  
To ensure collaborations remain safe, deterministic, and aligned with system governance.

**Usage:**  
Evaluated by Collaboration Manager and Security Gateway before and during sessions.

**Related Components:**  
Collaboration Manager, Security Gateway, Governance

**Related Documents:**  
`adrs.md`

**Related Architecture Sections:**  
12.2, 12.10, 12.12

**Examples:**  
- Requiring all collaborating agents to have `trust.level >= high`.  
- Restricting collaboration to registered agents only.

**Notes:**  
Policies should be declarative and centrally manageable.

---

### Collaboration Session

**Definition:**  
A bounded interaction window in which multiple agents collaborate under a shared context and policy.

**Purpose:**  
To group related interactions, preserve session state, and enable recovery and observability.

**Usage:**  
Created by Collaboration Manager, consumed by agents via Communication Bus.

**Related Components:**  
Collaboration Manager, Shared Context, Communication Bus

**Related Documents:**  
`context.md`, `events.md`

**Related Architecture Sections:**  
12.2, 12.6, 12.7

**Examples:**  
- A session for a multi-step architectural review.  
- A session for joint code migration across specialized agents.

**Notes:**  
Sessions should have explicit start, progress, and termination semantics.

---

### Communication Bus

**Definition:**  
The message-transport layer that enables agents, managers, and services to exchange structured messages.

**Purpose:**  
To decouple producers and consumers, enforce message schemas, and support observability.

**Usage:**  
Used by all messaging participants including EventBus, agents, and runtime services.

**Related Components:**  
EventBus, Message, Security Gateway

**Related Documents:**  
`components.md`, `schemas.md`

**Related Architecture Sections:**  
12.7, 12.10

**Examples:**  
- Agent publishing a capability advertisement.  
- Council broadcasting a decision result.

**Notes:**  
Bus design should support schema validation and replay for debugging.

---

### Conflict

**Definition:**  
A condition in which two or more agents, decisions, or workflow branches produce incompatible or contradictory results.

**Purpose:**  
To identify and surface inconsistencies that require resolution before progression.

**Usage:**  
Detected by Council, Collaboration Manager, or Workflow Engine; resolved through Conflict Resolution.

**Related Components:**  
Council, Conflict Resolution, Consensus

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.2, 12.5, 12.9

**Examples:**  
- Two council members producing contradictory approval decisions.  
- Workflow branches writing conflicting shared state.

**Notes:**  
Conflicts should be detected early and resolved deterministically.

---

### Conflict Resolution

**Definition:**  
The process and policy for reconciling conflicting outcomes among agents, council decisions, or workflow branches.

**Purpose:**  
To restore consistency, maintain trust, and allow progress after disagreement.

**Usage:**  
Invoked by Council, Workflow Engine, and Collaboration Manager when conflicts are detected.

**Related Components:**  
Council, Consensus, Governance

**Related Documents:**  
`adrs.md`

**Related Architecture Sections:**  
12.5, 12.9, 12.10

**Examples:**  
- Applying a quorum-based tiebreaker in council decisions.  
- Reverting a workflow branch to the last agreed checkpoint.

**Notes:**  
Resolution strategies should be explicit, auditable, and policy-driven.

---

### Consensus

**Definition:**  
An agreement state reached among participating agents or council members according to defined quorum and voting rules.

**Purpose:**  
To produce authoritative collective decisions without requiring universal agreement.

**Usage:**  
Managed by Council and Collaboration Manager.

**Related Components:**  
Council, Quorum, Consensus, Council Decision

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.2, 12.5, 12.6

**Examples:**  
- Council achieving consensus on a migration approval.  
- Agents converging on a shared interpretation of a task.

**Notes:**  
Consensus does not imply unanimity unless explicitly required by policy.

---

### Context

**Definition:**  
The structured information environment available to an agent, workflow, or collaboration at a given point in time.

**Purpose:**  
To provide agents with the knowledge, history, and state needed to make consistent decisions.

**Usage:**  
Managed by Context Manager; partitioned into Execution Context and Shared Context.

**Related Components:**  
Context Manager, Shared Context, Execution Context

**Related Documents:**  
`context.md`

**Related Architecture Sections:**  
12.6, 12.7, 12.12

**Examples:**  
- Execution context containing task parameters and transient state.  
- Shared context containing agreed decisions and accumulated knowledge.

**Notes:**  
Context boundaries must be explicit to avoid leakage and unintended coupling.

---

### Context Manager

**Definition:**  
The component responsible for creating, updating, isolating, and cleaning up execution and shared contexts.

**Purpose:**  
To manage context lifecycle, enforce isolation, and support recovery.

**Usage:**  
Used by agents, workflows, and collaboration sessions.

**Related Components:**  
Shared Context, Execution Context, Memory

**Related Documents:**  
`context.md`, `components.md`

**Related Architecture Sections:**  
12.6, 12.8, 12.9

**Examples:**  
- Creating a fresh execution context for a delegated task.  
- Archiving shared context after a collaboration session ends.

**Notes:**  
Context cleanup should be deterministic and timely.

---

### Council

**Definition:**  
A structured group of agents convened to evaluate, debate, and decide on matters requiring collective judgment.

**Purpose:**  
To provide governance, validation, and authoritative decision-making beyond individual agent capability.

**Usage:**  
Managed by Council Manager; produces Council Decisions.

**Related Components:**  
Council Manager, Council Decision, Quorum, Consensus

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.5, 12.6

**Examples:**  
- Council reviewing a high-risk system change.  
- Council validating a multi-agent research output.

**Notes:**  
Council composition and policies should be configurable and auditable.

---

### Council Decision

**Definition:**  
An authoritative outcome produced by a council after deliberation, voting, and conflict resolution.

**Purpose:**  
To produce a durable, traceable result that downstream components can rely on.

**Usage:**  
Consumed by Workflow Engine, Collaboration Manager, and Governance.

**Related Components:**  
Council, Council Manager, Consensus

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.5, 12.6

**Examples:**  
- Council approving a proposed migration path.  
- Council rejecting a change due to insufficient consensus.

**Notes:**  
Decisions should be immutable once finalized unless explicitly reopened.

---

### Council Manager

**Definition:**  
The component responsible for forming councils, managing deliberation, tracking quorum, and producing council decisions.

**Purpose:**  
To centralize council lifecycle and governance logic.

**Usage:**  
Creates councils, schedules deliberation, and records decisions.

**Related Components:**  
Council, Council Decision, Quorum, Collaboration Manager

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.5, 12.6

**Examples:**  
- Forming a council for a security review.  
- Recording a finalized council decision.

**Notes:**  
Council formation should validate participant eligibility and trust requirements.

---

## D

### Delegation

**Definition:**  
The act of assigning a task or responsibility from one agent or manager to another capable agent.

**Purpose:**  
To distribute work, specialize behavior, and improve throughput.

**Usage:**  
Managed by Delegation Manager; expressed as Task Delegation events or commands.

**Related Components:**  
Delegation Manager, Task, Agent Registry

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Delegating a code-analysis task to a specialized agent.  
- Routing a validation step to a qualified agent.

**Notes:**  
Delegation should validate capability match and runtime availability.

---

### Delegation Manager

**Definition:**  
The component responsible for selecting capable agents, assigning tasks, and tracking delegated work.

**Purpose:**  
To automate task assignment while respecting capability, priority, and resource constraints.

**Usage:**  
Consumes Task definitions and capability metadata; produces delegations and status updates.

**Related Components:**  
Task, Capability Registry, Scheduler

**Related Documents:**  
`components.md`, `schemas.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Selecting an agent for a data-transformation task.  
- Reassigning a failed delegated task to a fallback agent.

**Notes:**  
Delegation decisions should be observable and recoverable.

---

### Dependency

**Definition:**  
A required relationship between tasks, components, agents, or external systems that constrains execution order or availability.

**Purpose:**  
To encode ordering, data flow, and runtime prerequisites.

**Usage:**  
Modeled in Workflow Engine and reflected in `dependency-map.md`.

**Related Components:**  
Workflow Engine, Scheduler, Dependency Map

**Related Documents:**  
`dependency-map.md`

**Related Architecture Sections:**  
12.4, 12.8, 12.13

**Examples:**  
- Task B depending on Task A completion.  
- Workflow requiring an external MCP service.

**Notes:**  
Circular dependencies should be detected and rejected during planning.

---

### Discovery

**Definition:**  
The process of locating agents, capabilities, services, or resources required to fulfill a task or collaboration.

**Purpose:**  
To enable dynamic composition without hardcoded bindings.

**Usage:**  
Used by Delegation Manager, Scheduler, Collaboration Manager, and Runtime Coordinator.

**Related Components:**  
Agent Registry, Agent Directory, Capability Registry

**Related Documents:**  
`components.md`, `schemas.md`

**Related Architecture Sections:**  
12.3, 12.4, 12.7, 12.8

**Examples:**  
- Discovering all agents with `security.scan` capability.  
- Resolving a runtime dependency before workflow execution.

**Notes:**  
Discovery results should be validated and cached appropriately.

---

### Distributed Workflow

**Definition:**  
A workflow whose steps are executed across multiple agents, services, or runtime nodes rather than a single monolithic executor.

**Purpose:**  
To scale execution, specialize processing, and improve resilience.

**Usage:**  
Modeled and executed by Workflow Engine and Runtime Coordinator.

**Related Components:**  
Workflow Engine, Runtime Coordinator, Task Delegation

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.8, 12.9

**Examples:**  
- A migration workflow distributed across analysis, transformation, and validation agents.  
- A parallel research workflow with independent agent branches.

**Notes:**  
Distributed workflows require explicit state coordination and recovery semantics.

---

## E

### Event

**Definition:**  
A discrete occurrence in the system representing a state change, action completion, or significant signal.

**Purpose:**  
To enable loose coupling, observability, and reactive behavior.

**Usage:**  
Published and consumed through EventBus; modeled in `events.md`.

**Related Components:**  
EventBus, Observability, Communication Bus

**Related Documents:**  
`events.md`, `schemas.md`

**Related Architecture Sections:**  
12.7, 12.9

**Examples:**  
- `task.completed` event after delegation finishes.  
- `health.changed` event after a health check.

**Notes:**  
Events should be immutable once published.

---

### EventBus

**Definition:**  
The publish-subscribe infrastructure that routes events between system components.

**Purpose:**  
To decouple event producers from consumers and enable scalable, observable event flows.

**Usage:**  
Used by agents, managers, and runtime services for asynchronous coordination.

**Related Components:**  
Event, Communication Bus, Observability

**Related Documents:**  
`components.md`, `events.md`

**Related Architecture Sections:**  
12.7, 12.9

**Examples:**  
- Publishing a workflow state change event.  
- Subscribing to health-check results.

**Notes:**  
EventBus should support replay, filtering, and schema validation.

---

### Execution

**Definition:**  
The runtime activity of carrying out a task, workflow step, agent action, or delegation.

**Purpose:**  
To perform work and produce observable outcomes.

**Usage:**  
Managed by Runtime Coordinator, Workflow Engine, and Delegation Manager.

**Related Components:**  
Runtime Coordinator, Workflow Engine, Execution Context

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.8, 12.12

**Examples:**  
- Executing a delegated summarization task.  
- Running a council deliberation workflow.

**Notes:**  
Execution should be observable and bounded by resource and time constraints.

---

### Execution Context

**Definition:**  
The transient, isolated state container for a single agent action, task, or delegation.

**Purpose:**  
To provide isolated working state without polluting shared or persistent storage.

**Usage:**  
Created by Context Manager; used by agents during task execution.

**Related Components:**  
Context Manager, Shared Context, Task

**Related Documents:**  
`context.md`

**Related Architecture Sections:**  
12.4, 12.6, 12.9

**Examples:**  
- Execution context for a single document-analysis task.  
- Temporary context for a delegated validation step.

**Notes:**  
Execution Context should be disposable after task completion unless explicitly retained.

---

### Failure Recovery

**Definition:**  
The set of mechanisms used to detect failures, restore state, and resume or retry operations after an interruption.

**Purpose:**  
To maintain system continuity and data integrity despite runtime failures.

**Usage:**  
Implemented in Workflow Engine, Collaboration Manager, and Runtime Coordinator.

**Related Components:**  
Checkpoint, Recovery, Scheduler

**Related Documents:**  
`components.md`, `events.md`

**Related Architecture Sections:**  
12.9, 12.12

**Examples:**  
- Recovering a workflow from the last checkpoint after agent failure.  
- Retrying a delegated task with exponential backoff.

**Notes:**  
Recovery should preserve exactly-once semantics where required.

---

## G

### Governance

**Definition:**  
The policies, rules, and oversight mechanisms that ensure the system operates within defined trust, security, and behavioral boundaries.

**Purpose:**  
To maintain safety, compliance, and operational integrity across agent interactions.

**Usage:**  
Enforced by Security Gateway, Council, and Collaboration Manager.

**Related Components:**  
Security Gateway, Council, Collaboration Policy

**Related Documents:**  
`adrs.md`

**Related Architecture Sections:**  
12.2, 12.5, 12.10, 12.12

**Examples:**  
- Restricting high-risk operations to trusted agents.  
- Requiring council approval for sensitive workflows.

**Notes:**  
Governance should be centralized in policy, decentralized in enforcement.

---

## H

### Health Check

**Definition:**  
A periodic or event-driven assessment of an agent's, service's, or component's operational state.

**Purpose:**  
To detect failures, degradation, or unavailability early.

**Usage:**  
Performed by Runtime Coordinator and Observability systems.

**Related Components:**  
Observability, Runtime Coordinator, Agent Registry

**Related Documents:**  
`components.md`, `events.md`

**Related Architecture Sections:**  
12.8, 12.9

**Examples:**  
- Liveness probe for an external agent.  
- Readiness check before delegating a task.

**Notes:**  
Health checks should be lightweight and non-disruptive.

---

## K

### Knowledge

**Definition:**  
Structured information, experience, or insight used by agents and workflows to make decisions or produce outputs.

**Purpose:**  
To improve decision quality and enable learning across agent interactions.

**Usage:**  
Stored in Memory, exchanged via Knowledge Exchange, and referenced in Shared Context.

**Related Components:**  
Memory, Knowledge Exchange, Shared Knowledge

**Related Documents:**  
`context.md`

**Related Architecture Sections:**  
12.6, 12.7

**Examples:**  
- Historical execution patterns stored in memory.  
- Best practices exchanged during collaboration.

**Notes:**  
Knowledge should be versioned and provenance-tracked where possible.

---

### Knowledge Exchange

**Definition:**  
The structured transfer of knowledge between agents, workflows, or sessions through defined protocols and schemas.

**Purpose:**  
To enable collective intelligence and reduce redundant work.

**Usage:**  
Facilitated by Communication Bus and Shared Context.

**Related Components:**  
Shared Context, Knowledge, Communication Bus

**Related Documents:**  
`context.md`, `schemas.md`

**Related Architecture Sections:**  
12.6, 12.7

**Examples:**  
- Sharing validated findings from one agent to collaborators.  
- Persisting lessons learned after workflow completion.

**Notes:**  
Knowledge exchange should respect privacy, trust, and ownership boundaries.

---

### Knowledge Object

**Definition:**  
A discrete, schema-validated unit of knowledge used in exchange, storage, or retrieval.

**Purpose:**  
To standardize knowledge representation and enable reliable processing.

**Usage:**  
Created, transmitted, and stored by Knowledge Exchange and Memory.

**Related Components:**  
Knowledge Exchange, Memory, Schema

**Related Documents:**  
`schemas.md`

**Related Architecture Sections:**  
12.6, 12.7

**Examples:**  
- A structured insight object about architectural tradeoffs.  
- A reusable pattern object shared across agents.

**Notes:**  
Knowledge Objects should be self-describing and versioned.

---

## L

### Lifecycle

**Definition:**  
The sequence of states an agent, workflow, session, or component progresses through from creation to termination.

**Purpose:**  
To define valid transitions, enable observability, and support cleanup and recovery.

**Usage:**  
Managed by component-specific lifecycle controllers and tracked by Observability.

**Related Components:**  
Agent Registry, Workflow Engine, Collaboration Manager

**Related Documents:**  
`components.md`, `events.md`

**Related Architecture Sections:**  
12.3, 12.4, 12.9

**Examples:**  
- Agent lifecycle: registered → active → draining → deactivated.  
- Workflow lifecycle: planned → running → completed → archived.

**Notes:**  
Lifecycle transitions should be explicit and auditable.

---

## M

### Memory

**Definition:**  
The persistence and retrieval substrate for agent state, execution history, knowledge, and contextual information.

**Purpose:**  
To enable stateful behavior, learning, recovery, and auditability.

**Usage:**  
Accessed by Context Manager, agents, and Observability.

**Related Components:**  
Context Manager, Knowledge, Observability

**Related Documents:**  
`context.md`, `events.md`

**Related Architecture Sections:**  
12.6, 12.9

**Examples:**  
- Storing execution history for workflow replay.  
- Persisting learned knowledge for future tasks.

**Notes:**  
Memory access patterns should respect isolation and retention policies.

---

### Message

**Definition:**  
A discrete, schema-validated unit of communication transmitted between components, agents, or services.

**Purpose:**  
To enable structured, typed, and observable interaction.

**Usage:**  
Transmitted over Communication Bus and EventBus.

**Related Components:**  
Communication Bus, EventBus, Schema

**Related Documents:**  
`schemas.md`, `events.md`

**Related Architecture Sections:**  
12.7, 12.10

**Examples:**  
- Task delegation request message.  
- Council decision broadcast message.

**Notes:**  
Messages should be immutable after creation.

---

### Multi-Agent System

**Definition:**  
A system composed of multiple autonomous agents that interact through defined protocols to achieve collective objectives.

**Purpose:**  
To leverage specialization, parallelism, and collective reasoning beyond single-agent capability.

**Usage:**  
The overarching architectural pattern for Part 12.

**Related Components:**  
All components

**Related Documents:**  
`context.md`, `adrs.md`

**Related Architecture Sections:**  
12.1, 12.2, 12.13

**Examples:**  
- A research system with parallel analysis, validation, and synthesis agents.  
- A governance system with council and review agents.

**Notes:**  
Multi-agent design introduces coordination complexity; boundaries and contracts are critical.

---

## N

### Negotiation

**Definition:**  
An interactive process through which agents reach agreement on task parameters, resource usage, or collaboration terms.

**Purpose:**  
To align expectations, resolve differences, and establish shared constraints.

**Usage:**  
Used by Collaboration Manager and Delegation Manager before and during sessions.

**Related Components:**  
Collaboration Manager, Delegation Manager, Consensus

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.2, 12.4, 12.5

**Examples:**  
- Agents negotiating task deadlines and resource allocation.  
- Council members negotiating interpretation of evaluation criteria.

**Notes:**  
Negotiation protocols should be bounded and timeout-aware.

---

## O

### Observability

**Definition:**  
The ability to inspect, trace, and understand system behavior through logs, metrics, events, and traces.

**Purpose:**  
To support debugging, performance analysis, and operational confidence.

**Usage:**  
Instrumented across Workflow Engine, Collaboration Manager, Runtime Coordinator, and EventBus.

**Related Components:**  
EventBus, Health Check, Scheduler

**Related Documents:**  
`events.md`

**Related Architecture Sections:**  
12.7, 12.9, 12.12

**Examples:**  
- Tracing a task delegation from request to completion.  
- Monitoring collaboration session health and progress.

**Notes:**  
Observability should be designed in, not added later.

---

### Orchestration

**Definition:**  
The coordinated sequencing and control of tasks, agents, and workflows to achieve a composite objective.

**Purpose:**  
To manage complexity, enforce ordering, and optimize resource utilization.

**Usage:**  
Provided by Workflow Manager, Workflow Engine, and Runtime Coordinator.

**Related Components:**  
Workflow Engine, Workflow Manager, Runtime Coordinator

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Orchestrating a multi-phase migration workflow.  
- Coordinating parallel agent tasks with dependency constraints.

**Notes:**  
Orchestration should remain declarative where possible to improve maintainability.

---

## P

### Planning

**Definition:**  
The process of decomposing objectives into tasks, dependencies, resource requirements, and execution schedules.

**Purpose:**  
To make complex work tractable, predictable, and recoverable.

**Usage:**  
Performed by Workflow Manager and Scheduler before execution.

**Related Components:**  
Workflow Manager, Scheduler, Dependency Map

**Related Documents:**  
`dependency-map.md`, `adrs.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Planning a migration workflow with parallel and sequential phases.  
- Scheduling agent tasks based on priority and dependency order.

**Notes:**  
Plans should be inspectable, revisable, and recoverable.

---

### Plugin

**Definition:**  
An independently developed, externally integrated module that extends system behavior through defined extension points.

**Purpose:**  
To enable extensibility without modifying core architecture.

**Usage:**  
Registered and loaded by Plugin infrastructure; interacted with through boundary interfaces.

**Related Components:**  
Security Gateway, Communication Bus, Agent Registry

**Related Documents:**  
`components.md`, `adrs.md`

**Related Architecture Sections:**  
12.1, 12.10

**Examples:**  
- An external MCP integration plugin.  
- A custom security scanning plugin.

**Notes:**  
Plugins must respect architecture boundaries and schema contracts.

---

### Priority

**Definition:**  
A relative urgency or importance assigned to tasks, agents, messages, or workflows.

**Purpose:**  
To guide scheduling, resource allocation, and conflict resolution.

**Usage:**  
Evaluated by Scheduler and Delegation Manager.

**Related Components:**  
Scheduler, Delegation Manager, Task

**Related Documents:**  
`components.md`, `schemas.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- High-priority security task preempting lower-priority work.  
- Priority-based queue ordering in Scheduler.

**Notes:**  
Priority inversion should be detected and mitigated.

---

## Q

### Quorum

**Definition:**  
The minimum number of participants required for a council, voting process, or consensus mechanism to produce a valid decision.

**Purpose:**  
To ensure decisions represent sufficient participation and authority.

**Usage:**  
Enforced by Council Manager during council deliberations.

**Related Components:**  
Council, Council Manager, Consensus

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.5, 12.6

**Examples:**  
- Requiring 3 of 5 council members to participate.  
- Rejecting a vote due to insufficient quorum.

**Notes:**  
Quorum rules should be explicit and enforced before counting votes.

---

## R

### Recovery

**Definition:**  
The act of restoring system, workflow, session, or agent state after failure, interruption, or inconsistency.

**Purpose:**  
To maintain continuity, correctness, and user trust.

**Usage:**  
Provided by Failure Recovery, Workflow Engine, and Context Manager.

**Related Components:**  
Failure Recovery, Checkpoint, Context Manager

**Related Documents:**  
`events.md`

**Related Architecture Sections:**  
12.9, 12.12

**Examples:**  
- Recovering a workflow from the last successful checkpoint.  
- Restoring shared context after a collaboration session interruption.

**Notes:**  
Recovery should be idempotent and bounded by a recovery point objective.

---

### Registry

**Definition:**  
A persistent store that holds authoritative metadata about agents, capabilities, or other system entities.

**Purpose:**  
To provide a single source of truth for discovery, validation, and governance.

**Usage:**  
Implemented by Agent Registry and Capability Registry.

**Related Components:**  
Agent Registry, Capability Registry, Agent Directory

**Related Documents:**  
`components.md`, `schemas.md`

**Related Architecture Sections:**  
12.3, 12.10

**Examples:**  
- Agent registry storing capability manifests.  
- Capability registry tracking versioned capabilities.

**Notes:**  
Registry data should be validated, versioned, and auditable.

---

### Resource Coordination

**Definition:**  
The management and allocation of shared resources—such as compute, tokens, time, and external services—among competing agents and workflows.

**Purpose:**  
To prevent contention, ensure fairness, and maintain system stability.

**Usage:**  
Performed by Scheduler and Runtime Coordinator.

**Related Components:**  
Scheduler, Runtime Coordinator, Delegation Manager

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.8, 12.9

**Examples:**  
- Scheduling tasks to avoid exceeding concurrency limits.  
- Throttling agent invocations during peak load.

**Notes:**  
Coordination policies should be transparent and measurable.

---

### Runtime

**Definition:**  
The execution environment in which agents, workflows, and services operate, including lifecycle, scheduling, and resource management.

**Purpose:**  
To provide a controlled, observable, and recoverable execution substrate.

**Usage:**  
Managed by Runtime Coordinator and supporting managers.

**Related Components:**  
Runtime Coordinator, Scheduler, Observability

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.8, 12.9, 12.12

**Examples:**  
- Runtime enforcing task timeouts and retry limits.  
- Runtime isolating agent execution contexts.

**Notes:**  
Runtime boundaries should be explicit and secure.

---

### Runtime Coordinator

**Definition:**  
The central controller responsible for runtime lifecycle, scheduling decisions, health monitoring, and failure handling.

**Purpose:**  
To coordinate execution across agents and workflows while maintaining system invariants.

**Usage:**  
Interacts with Scheduler, Delegation Manager, and Observability.

**Related Components:**  
Scheduler, Delegation Manager, Health Check

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.8, 12.9

**Examples:**  
- Coordinating task execution across available agents.  
- Reacting to health-check failures by rerouting work.

**Notes:**  
Runtime Coordinator should be resilient and auditable.

---

## S

### Scheduler

**Definition:**  
The component responsible for ordering, timing, and dispatching tasks, workflows, and agent actions.

**Purpose:**  
To maximize throughput, respect priorities, and honor dependencies.

**Usage:**  
Used by Delegation Manager, Workflow Engine, and Runtime Coordinator.

**Related Components:**  
Runtime Coordinator, Delegation Manager, Task

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Scheduling high-priority tasks ahead of low-priority ones.  
- Enforcing dependency order before dispatching a task.

**Notes:**  
Scheduler decisions should be observable and explainable.

---

### Schema

**Definition:**  
A formal, validated structure defining the shape, types, and constraints of messages, events, capabilities, and knowledge objects.

**Purpose:**  
To ensure interoperability, validation, and safe evolution.

**Usage:**  
Defined in `schemas.md` and enforced by Communication Bus, EventBus, and validators.

**Related Components:**  
Communication Bus, EventBus, Message

**Related Documents:**  
`schemas.md`

**Related Architecture Sections:**  
12.7, 12.10, 12.11

**Examples:**  
- Task delegation message schema.  
- Council decision event schema.

**Notes:**  
Schema changes should be backward compatible or explicitly versioned.

---

### Security Gateway

**Definition:**  
The enforcement point for authentication, authorization, policy validation, and trust verification across system boundaries.

**Purpose:**  
To protect the system from unauthorized or malicious interactions.

**Usage:**  
Intercepts messages, delegation requests, plugin calls, and external integrations.

**Related Components:**  
Communication Bus, Plugin, Agent Registry

**Related Documents:**  
`adrs.md`, `components.md`

**Related Architecture Sections:**  
12.7, 12.10, 12.13

**Examples:**  
- Validating agent identity before accepting a delegation.  
- Blocking unregistered plugins from accessing core APIs.

**Notes:**  
Security enforcement should be centralized, consistent, and auditable.

---

### Shared Context

**Definition:**  
The durable, collaboratively accessible context that multiple agents or sessions may read and write under policy control.

**Purpose:**  
To enable consistent shared understanding across distributed participants.

**Usage:**  
Managed by Context Manager and Collaboration Manager.

**Related Components:**  
Context Manager, Collaboration Manager, Knowledge Exchange

**Related Documents:**  
`context.md`

**Related Architecture Sections:**  
12.6, 12.7

**Examples:**  
- Shared context containing agreed task constraints.  
- Shared context storing intermediate council findings.

**Notes:**  
Shared Context mutations should be validated and conflict-checked.

---

### Shared Knowledge

**Definition:**  
Knowledge that has been explicitly made available to multiple agents or workflows through exchange and storage mechanisms.

**Purpose:**  
To reduce redundant work and improve collective reasoning.

**Usage:**  
Stored in Memory, exchanged via Knowledge Exchange, and referenced in Shared Context.

**Related Components:**  
Knowledge Exchange, Memory, Shared Context

**Related Documents:**  
`context.md`

**Related Architecture Sections:**  
12.6, 12.7

**Examples:**  
- Shared architectural knowledge reused across multiple workflows.  
- Shared lessons learned from previous executions.

**Notes:**  
Shared Knowledge should be provenance-tracked and trust-scoped.

---

## T

### Task

**Definition:**  
A discrete unit of work with defined inputs, outputs, acceptance criteria, and ownership.

**Purpose:**  
To represent executable work in a structured, delegatable, and trackable form.

**Usage:**  
Created by Workflow Manager and Delegation Manager; executed by agents.

**Related Components:**  
Delegation Manager, Workflow Engine, Task Delegation

**Related Documents:**  
`schemas.md`, `components.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- A data-transformation task assigned to an agent.  
- A validation task within a migration workflow.

**Notes:**  
Tasks should be idempotent where possible and have explicit completion criteria.

---

### Task Delegation

**Definition:**  
The act of assigning a task from a manager or orchestrator to a capable agent, including parameters, expectations, and accountability.

**Purpose:**  
To distribute work, specialize execution, and enable scalable processing.

**Usage:**  
Performed by Delegation Manager; modeled as explicit delegation events or records.

**Related Components:**  
Delegation Manager, Task, Agent Registry

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Delegating a security-scan task to a qualified agent.  
- Reassigning a failed task to a fallback agent.

**Notes:**  
Delegation should include retry, timeout, and fallback semantics.

---

### Tool

**Definition:**  
An external capability, library, service, or integration exposed to agents and workflows through a controlled interface.

**Purpose:**  
To extend agent functionality without embedding implementation details.

**Usage:**  
Accessed through boundary interfaces and security enforcement.

**Related Components:**  
Plugin, Security Gateway, Communication Bus

**Related Documents:**  
`components.md`, `adrs.md`

**Related Architecture Sections:**  
12.1, 12.7, 12.10

**Examples:**  
- External MCP tool for web search.  
- Plugin-provided tool for code analysis.

**Notes:**  
Tool access should be authorized, observable, and bounded by trust requirements.

---

## W

### Workflow

**Definition:**  
A structured sequence of tasks, decisions, and transitions designed to achieve a composite objective.

**Purpose:**  
To coordinate complex multi-step work in a recoverable and observable manner.

**Usage:**  
Defined, scheduled, and executed by Workflow Manager and Workflow Engine.

**Related Components:**  
Workflow Manager, Workflow Engine, Task

**Related Documents:**  
`components.md`, `dependency-map.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- A migration workflow with analysis, transformation, and validation phases.  
- A parallel research workflow with independent branches.

**Notes:**  
Workflows should be explicit, testable, and recoverable.

---

### Workflow Engine

**Definition:**  
The execution substrate that interprets, advances, and monitors workflows according to their definitions and runtime state.

**Purpose:**  
To provide deterministic, observable, and recoverable workflow execution.

**Usage:**  
Driven by Workflow Manager; integrated with Runtime Coordinator and Context Manager.

**Related Components:**  
Workflow Manager, Runtime Coordinator, Context Manager

**Related Documents:**  
`components.md`

**Related Architecture Sections:**  
12.4, 12.9

**Examples:**  
- Advancing a workflow after task delegation completion.  
- Branching workflow execution based on conditional outcomes.

**Notes:**  
Engine state should be checkpointed and replayable.

---

### Workflow Manager

**Definition:**  
The component responsible for defining, validating, scheduling, and overseeing workflows.

**Purpose:**  
To separate workflow design from execution and provide lifecycle governance.

**Usage:**  
Creates workflow definitions; interacts with Workflow Engine and Scheduler.

**Related Components:**  
Workflow Engine, Scheduler, Dependency Map

**Related Documents:**  
`components.md`, `dependency-map.md`

**Related Architecture Sections:**  
12.4, 12.8

**Examples:**  
- Defining a new migration workflow.  
- Validating workflow structure before execution.

**Notes:**  
Workflow definitions should be declarative and versioned.

---

## Document Sections

### Acronyms

| Acronym | Meaning |
|---------|---------|
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| JSON | JavaScript Object Notation |
| MCP | Model Context Protocol |
| REST | Representational State Transfer |
| RPC | Remote Procedure Call |
| SLA | Service Level Agreement |
| SLO | Service Level Objective |
| TTL | Time To Live |
| UUID | Universally Unique Identifier |

---

### Naming Conventions

- **Agents**: Use kebab-case descriptive names, e.g., `code-migration-agent`.
- **Capabilities**: Use dot-separated namespaces, e.g., `security.scan`, `data.transform`.
- **Events**: Use past-tense, dot-separated names, e.g., `task.completed`, `council.decision.issued`.
- **Schemas**: Use PascalCase type names, e.g., `TaskDelegationMessage`, `CouncilDecisionEvent`.
- **Roles**: Use lowercase or kebab-case, e.g., `moderator`, `lead-validator`.
- **Documents**: Use descriptive titles with section prefixes, e.g., `12.4-Task-Delegation-Workflow-Orchestration.md`.

---

### Frequently Confused Terms

| Term A | Term B | Distinction |
|--------|--------|-------------|
| Agent | Plugin | An Agent is an autonomous runtime participant; a Plugin is an external integration module. |
| Collaboration | Orchestration | Collaboration implies joint agent interaction; orchestration implies centralized sequencing control. |
| Consensus | Unanimity | Consensus allows qualified disagreement; unanimity requires full agreement. |
| Delegation | Assignment | Delegation includes capability matching and accountability; assignment may be arbitrary. |
| Discovery | Directory | Discovery is the process; Directory is the data structure used by that process. |
| Event | Message | Events describe what happened; Messages carry instructions or data for action. |
| Execution Context | Shared Context | Execution Context is transient and isolated; Shared Context is durable and collaborative. |
| Governance | Security | Governance is policy and oversight; Security is enforcement and protection. |
| Knowledge | Data | Knowledge implies interpreted, contextualized insight; Data is raw or minimally processed. |
| Registry | Directory | Registry is authoritative metadata storage; Directory is optimized lookup structure. |
| Task | Workflow | A Task is a single unit of work; a Workflow is a composed sequence of tasks. |
| Workflow | Process | A Workflow is a first-class architectural construct; a Process is a broader organizational concept. |

---

### Related Standards

- **Event-Driven Architecture** — patterns for message and event design.
- **CQRS / Event Sourcing** — concepts applicable to state recovery and auditability.
- **Actor Model** — conceptual foundation for autonomous agents and message passing.
- **Microservices Communication** — relevant to Communication Bus and boundary design.
- **OpenAPI / JSON Schema** — applicable to schema design and validation.
- **OWASP** — relevant to Security Gateway and trust modeling.
- **ISO/IEC 42001** — AI management system standard relevant to governance and observability.

---

### Glossary Maintenance Guidelines

- This glossary is maintained as part of Part 12 and should be updated when architectural terms change.
- Add new terms alphabetically and update cross-references when components or sections are renamed.
- Keep definitions concise, architecture-specific, and consistent with Part 12 usage.
- Review this glossary during Part 12 reviews and before major architectural changes.
- Related Documents and Related Architecture Sections should be updated when section numbering or document names change.
- When a term is deprecated, mark it clearly and provide the replacement term with a cross-reference.

---

**Document Controls**

- **Status:** Official
- **Part:** 12
- **Subject:** Multi-Agent Collaboration Architecture
- **Last Updated:** 2026-08-07
