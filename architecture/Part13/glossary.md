# Part 13 Glossary — Governance Architecture

This glossary is the single source of truth for every architectural term used throughout Part 13. Entries are arranged alphabetically.

For every term this document provides: Definition, Purpose, Usage, Related Concepts, Related Components, Related Part 13 Sections, Examples, and Notes where applicable.

---

## Terminology Governance

### Terminology Ownership

| Term Category | Owner | Change Authority | Review Cadence |
|---------------|-------|------------------|----------------|
| Core Governance | Part 13 Architecture Team | Part 13 Lead | Per release |
| Policy | Part 13 Architecture Team | Part 13 Lead | Per release |
| Authority & Delegation | Part 13 Architecture Team | Part 13 Lead | Per release |
| Accountability | Part 13 Architecture Team | Part 13 Lead | Per release |
| Risk & Compliance | Part 13 Architecture Team | Part 13 Lead | Per release |
| Audit | Part 13 Architecture Team | Part 13 Lead | Per release |
| Domains (Agent, Capability, Workflow, Data, Knowledge, Security, Operational) | Part 13 Architecture Team | Part 13 Lead | Per release |

**Note:** All terms in this glossary are owned by the Part 13 Architecture Team unless explicitly delegated. Changes require Part 13 Lead approval and cross-part review when terms span multiple parts.

### Term Relationships and Hierarchy

**Hierarchical Relationships:**
- `Governance` encompasses `Governance Domain`, `Governance Body`, `Governance Authority`
- `Policy` encompasses `Policy Rule`, `Policy Set`, `Policy Version`
- `Decision` encompasses `Decision Right`, `Decision Authority`
- `Delegated Authority` is a subset of `Authority`
- `Accountability` encompasses `Responsibility`, `Owner`, `Steward`, `Approver`, `Reviewer`
- `Risk` encompasses `Risk Appetite`, `Risk Threshold`, `Risk Owner`
- `Compliance` encompasses `Control`, `Control Objective`
- `Audit` encompasses `Audit Evidence`, `Audit Trail`, `Attestation`, `Certification`, `Conformance`
- `Violation` is a type of `Exception`
- `Escalation` is a response to `Violation` or `Exception`
- `Approval` and `Review` are governance actions

**See-Also Relationships:**
- `Governance` → `Governance Event`, `Governance Record`
- `Policy` → `Policy Evaluation`, `Policy Enforcement`, `Policy Conflict`, `Policy Override`, `Policy Exception`, `Policy Lifecycle`, `Policy Precedence`
- `Decision` → `Decision Right`, `Decision Authority`, `Delegated Authority`
- `Accountability` → `Responsibility`, `Owner`, `Steward`, `Approver`, `Reviewer`
- `Risk` → `Risk Appetite`, `Risk Threshold`, `Risk Owner`
- `Compliance` → `Control`, `Control Objective`
- `Audit` → `Audit Evidence`, `Audit Trail`, `Attestation`, `Certification`, `Conformance`
- `Violation` → `Exception`, `Escalation`
- `Approval` → `Review`
- `Governance Domain` → `Agent Governance`, `Capability Governance`, `Workflow Governance`, `Data Governance`, `Knowledge Governance`, `Security Governance`, `Operational Governance`, `Architecture Governance`
- `Governance Event` → `Governance Record`

### Version Compatibility

**Glossary Version:** 1.0  
**Part 13 Baseline:** Phase 12+  
**Forward Compatibility:** New terms may be added in minor revisions; existing definitions require major version changes to modify.  
**Backward Compatibility:** Deprecated terms remain defined for at least one major version before removal.

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-08-08 | Initial canonical glossary |

### Aliases and Synonyms

| Canonical Term | Alias / Synonym | Status | Notes |
|----------------|-----------------|--------|-------|
| Governance Authority | Governing Authority | Preferred | `Governing Authority` is shorthand for `Governance Authority` in policy contexts. |
| Decision Right | Decision Privilege | Contextual | `Decision Privilege` may refer to `Decision Right` in delegation contexts. |
| Delegated Authority | Delegated Power | Informal | Used in internal discussion; formal documentation must use `Delegated Authority`. |
| Policy Rule | Rule | Contextual | `Rule` alone may refer to `Policy Rule` in policy-management contexts. |
| Policy Set | Policy Bundle | Variant | `Policy Bundle` is acceptable in prose after first full mention. |
| Accountability Owner | Owner | Contextual | `Owner` alone may refer to `Accountability Owner` in responsibility contexts. |
| Risk Appetite | Risk Tolerance | Deprecated alias | Use `Risk Appetite`; `Risk Tolerance` is deprecated. |
| Control Objective | Control Goal | Informal | Never used as a single token; always `Control Objective`. |
| Audit Trail | Audit Log | Variant | `Audit Log` is acceptable in prose after first full mention. |
| Conformance | Compliance Level | Contextual | `Compliance Level` may refer to `Conformance` in audit contexts. |

### Deprecated Terminology

| Deprecated Term | Replacement | Deprecated In | Removed At | Migration Notes |
|-----------------|-------------|---------------|------------|----------------|
| Risk Tolerance | Risk Appetite | 1.0 | TBD | Update references from tolerance to appetite. |
| Governing Body | Governance Body | Pre-13 | TBD | Governance Body subsumes Governing Body role. |
| Privilege | Decision Right | Pre-13 | TBD | Decision Right subsumes Privilege role. |
| Policy Directive | Policy Rule | Pre-13 | TBD | Renamed for consistency with Policy Architecture naming. |
| Audit Record | Audit Evidence | Pre-13 | TBD | Renamed for consistency with Audit terminology. |

### Reserved Terminology

The following terms are reserved for future use and must not be introduced in designs, documentation, or code without explicit Part 13 Lead approval:

- `Governance Matrix`
- `Policy Engine`
- `Decision Ledger`
- `Authority Graph`
- `Accountability Chain`
- `Risk Heatmap`
- `Compliance Dashboard`
- `Audit Chain`
- `Governance Token`
- `Delegation Certificate`
- `Policy Version Control`
- `Governance Smart Contract`

### Cross-Part Terminology Consistency

This glossary aligns with terminology from the following parts. When terms overlap, the canonical definition from the owning part governs.

| Term | Part 13 Definition | Cross-Part Owner | Cross-Part Usage | Consistency Status |
|------|-------------------|------------------|------------------|-------------------|
| Governance | The policies, rules, and oversight mechanisms that ensure the system operates within defined trust, security, and behavioral boundaries. | Part 12 | Core architectural participant | Aligned (see Part 12 glossary) |
| Policy | A defined rule or guideline that specifies required or prohibited behavior within a specific scope. | Part 12 | Service/entity metadata | Aligned |
| Accountability | The obligation to explain, justify, and take responsibility for actions and decisions. | Part 12 | State management | Aligned |
| Responsibility | The duty to perform or complete a task or role. | Part 1-15 | Core architectural participant | Aligned |
| Risk | The potential for loss, damage, or failure due to uncertainties or vulnerabilities. | Part 6, Part 11 | State management | Aligned |
| Compliance | Adherence to external regulations, internal standards, or contractual obligations. | Part 10 | Trust boundary | Aligned |
| Audit | Independent examination and verification of whether policies were followed and controls worked effectively. | Part 7, Part 9 | State-change signal | Aligned |
| Control | A measure or mechanism designed to modify or maintain risk within acceptable levels. | Part 3, Part 11 | Service/entity metadata | Aligned |
| Evidentiary | Relating to or constituting evidence. | Part 11 | Data contract | Aligned |
| Trust Domain | A sphere of influence where trust assumptions are shared and enforced. | Part 1, Part 10 | Integration point | Aligned |

**Note:** Cross-part terms are reviewed during Part 13 cross-reference updates. Definitions may diverge when domain-specific behavior differs; such divergence must be explicitly noted in both parts.

### Evolution Policy

**Term Addition:**
1. Propose term via Part 13 Architecture Review
2. Define term following this glossary's template
3. Assign owner and review cadence
4. Add to glossary with version increment
5. Cross-reference affected parts

**Term Modification:**
1. Submit change request with rationale
2. Review impact on existing definitions, schemas, and cross-part references
3. Part 13 Lead approves; affected parts notified
4. Version bump: minor for clarification, major for semantic change

**Term Deprecation:**
1. Mark term as deprecated in glossary with replacement
2. Announce deprecation in Part 13 release notes
3. Maintain deprecated definition for at least one major version
4. Remove only after migration window closes

**Term Removal:**
1. Requires Part 13 Lead approval
2. Must have replacement term defined and adopted
3. Update all cross-references before removal
4. Version bump to major

---

## A

### Accountability

**Definition:**  
The obligation to explain, justify, and take responsibility for actions and decisions, supported by immutable audit trails and non-repudiation mechanisms.

**Purpose:**  
To ensure answerability for governance outcomes and enable trustworthy oversight.

**Usage:**  
Applied to agents, workflows, policies, decisions, and governance components; recorded in audit logs and verified during audits.

**Related Concepts:**  
Responsibility, Owner, Steward, Approver, Reviewer, Answerability, Enforceability, Non-repudiation

**Related Components:**  
Audit Logger, Non-repudiation Service, Accountability Tracker, Governance Services

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
An agent that modifies a policy must be accountable for the change, with the action cryptographically signed and logged for review.

---

### Agent Governance

**Definition:**  
The domain of governance that controls agent behavior, capabilities, lifecycle, and interactions through policy and monitoring.

**Purpose:**  
To ensure agents operate within authorized boundaries, maintain integrity, and pose acceptable risk to the system.

**Usage:**  
Applied during agent registration, capability assignment, execution monitoring, and lifecycle management.

**Related Concepts:**  
Agent Identity, Capability Token, Policy Evaluation, Lifecycle Management, Behavioral Monitoring

**Related Components:**  
Agent Registry, Capability Registry, Policy Evaluation Engine (G-02), Monitoring Agent, Governance Interceptor

**Related Part 13 Sections:**  
13.7-Agent-and-Capability-Governance.md

**Example:**  
A governance policy restricts agents with `risk.level > high` from accessing confidential data stores.

---

### Approval

**Definition:**  
A formal grant of permission to proceed with a proposed action, decision, or change, based on evaluation against governing policies and authority rules.

**Purpose:**  
To ensure that significant actions are authorized by appropriate governance bodies before execution.

**Usage:**  
Required for policy changes, high-risk delegations, workflow activations, and exception handling.

**Related Concepts:**  
Decision Right, Authority, Review, Escalation, Approval Workflow, Conditional Approval

**Related Components:**  
Approval Service, Approval Workflow Engine, Policy Checkpoint, Governance Council

**Related Part 13 Sections:**  
13.4-Decision-Authority-and-Delegation.md, 13.5-Governance-Councils-and-Committees.md

**Example:**  
A council approval is required before deploying a new agent capability that modifies core system policies.

---

### Audit

**Definition:**  
Independent examination and verification of whether policies were followed, controls worked effectively, and governance objectives were met.

**Purpose:**  
To provide assurance of governance integrity, detect gaps, and drive improvement.

**Usage:**  
Conducted periodically or triggered by events; results reported to governance bodies and used for remediation.

**Related Concepts:**  
Audit Evidence, Audit Trail, Attestation, Certification, Conformance, Compliance, Remediation

**Related Components:**  
Audit Service, Evidence Collector, Trail Verifier, Attestation Authority, Certification Board

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
An quarterly audit verifies that all policy evaluation logs are complete and tamper-evident.

---

### Audit Evidence

**Definition:**  
The records, logs, artifacts, and data collected during an audit that support auditor findings and conclusions.

**Purpose:**  
To substantiate audit opinions and enable traceability of governance actions.

**Usage:**  
Collected from audit logs, policy repositories, configuration stores, and operational metrics.

**Related Concepts:**  
Audit Trail, Attestation, Certification, Conformance, Violation, Exception

**Related Components:**  
Evidence Collector, Log Aggregator, Artifact Store, Verification Engine

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
Signed policy evaluation logs and access control lists serve as audit evidence for compliance verification.

---

### Audit Trail

**Definition:**  
A chronological, immutable record of governance-relevant actions, decisions, and modifications that enables reconstruction of events.

**Purpose:**  
To ensure non-repudiation, support investigations, and provide baselines for compliance verification.

**Usage:**  
Generated by governance services; retained per policy; queried during audits and investigations.

**Related Concepts:**  
Audit Evidence, Attestation, Certification, Conformance, Immutable Log, Chain of Custody

**Related Components:**  
Immutable Logger, Log Signer, Trail Verifier, Retention Service

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
Every policy change is appended to an audit trail with a cryptographic hash linking to the previous entry.

---

### Attestation

**Definition:**  
A formal declaration, often cryptographically signed, that attests to the truth or validity of a governance statement, event, or condition.

**Purpose:**  
To provide verifiable proof of compliance, correctness, or authenticity for external or internal stakeholders.

**Usage:**  
Produced by attestation authorities after reviewing evidence; used in certifications, audit reports, and regulatory submissions.

**Related Concepts:**  
Audit Evidence, Audit Trail, Certification, Conformance, Non-repudiation, Trust Anchor

**Related Components:**  
Attestation Service, Signing Authority, Evidence Reviewer, Trust Registry

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
An attester signs a statement confirming that all agents have completed required security training within the last 90 days.

---

### Certification

**Definition:**  
A formal recognition, granted by an authorized body, that a system, component, process, or individual meets specified governance standards or requirements.

**Purpose:**  
To validate compliance and provide marketable assurance of governance maturity.

**Usage:**  
Awarded after successful audits or assessments; may be required for operational readiness or regulatory approval.

**Related Concepts:**  
Attestation, Audit Evidence, Conformance, Compliance, Standard, Accreditation

**Related Components:**  
Certification Board, Assessment Engine, Attestation Service, Standards Registry

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
The system receives ISO/IEC 42001 certification after demonstrating effective AI governance controls.

---

### Compliance

**Definition:**  
Adherence to external regulations, internal standards, or contractual obligations, verified through continuous monitoring and evidence collection.

**Purpose:**  
To ensure lawful and ethical operation, avoid penalties, and maintain stakeholder trust.

**Usage:**  
Evaluated via automated controls, manual reviews, and audit activities; reported to governance bodies and regulators.

**Related Concepts:**  
Control, Control Objective, Regulation, Standard, Policy, Violation, Exception, Remediation

**Related Components:**  
Compliance Engine, Control Monitor, Policy Evaluator, Violation Detector, Reporting Service

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
A continuous compliance check ensures that no agent processes personal data without encryption and consent.

---

### Compliance Governance

**Definition:**  
The domain of governance that ensures adherence to external regulations, internal standards, and contractual obligations through policy, controls, and monitoring.

**Purpose:**  
To align system behavior with legal and ethical requirements and enable demonstrable compliance.

**Usage:**  
Applied during system design, deployment, and operation; integrates with Risk Governance and Audit Governance.

**Related Concepts:**  
Regulation, Standard, Control, Policy, Violation, Exception, Remediation, Certification

**Related Components:**  
Compliance Manager, Policy Evaluation Engine (G-02), Control Monitor, Audit Service, Reporting Service

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
Compliance governance maps GDPR articles to data handling policies and enforces them via data access controls.

---

### Control

**Definition:**  
A measure, mechanism, or policy designed to modify or maintain risk within acceptable levels, thereby supporting compliance objectives.

**Purpose:**  
To reduce likelihood or impact of risks and ensure adherence to governance requirements.

**Usage:**  
Implemented as technical safeguards (e.g., access controls), procedural safeguards (e.g., separation of duties), or policy rules.

**Related Concepts:**  
Control Objective, Risk Mitigation, Policy, Compliance, Violation, Exception

**Related Components:**  
Control Engine, Policy Evaluator, Enforcement Point, Monitoring Agent

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
A role-based access control (RBAC) mechanism restricts data access to authorized agents only.

---

### Control Objective

**Definition:**  
A specific, measurable goal that a control is designed to achieve, often derived from a compliance requirement or risk mitigation target.

**Purpose:**  
To define the intended effect of a control and enable verification of its effectiveness.

**Usage:**  
Specified during control design; used to test control performance and report compliance status.

**Related Concepts:**  
Control, Risk Mitigation, Compliance Requirement, Key Performance Indicator (KPI)

**Related Components:**  
Control Designer, Evaluation Engine, Reporting Service, Dashboard

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
The control objective of a data loss prevention (DLP) system is to prevent unauthorized exfiltration of confidential data.

---

### Conformance

**Definition:**  
The degree to which a system, component, or process adheres to governance policies, standards, or requirements, often expressed as a pass/fail or percentage score.

**Purpose:**  
To quantify compliance status and identify gaps requiring remediation.

**Usage:**  
Assessed via automated tests, manual reviews, and audit activities; tracked over time for trend analysis.

**Related Concepts:**  
Compliance, Certification, Attestation, Audit Evidence, Policy, Standard, Violation

**Related Components:**  
Conformance Engine, Test Suite, Policy Evaluator, Reporting Service, Dashboard

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
A conformance report shows that 98% of agents satisfy the least-privilege policy requirement.

---

### Decision Authority

**Definition:**  
The right or power to make a specific type of decision, derived from governance policies, roles, or delegated permissions.

**Purpose:**  
To define who may exercise decision-making authority within the system.

**Usage:**  
Assigned to agents, workflows, governance bodies, or individuals based on responsibility and trust level.

**Related Concepts:**  
Decision Right, Delegated Authority, Governance Authority, Policy Rule, Role-Based Access Control (RBAC)

**Related Components:**  
Authority Service, Policy Evaluation Engine (G-02), Role Manager, Delegation Tracker, Governance Council

**Related Part 13 Sections:**  
13.4-Decision-Authority-and-Delegation.md

**Example:**  
A workflow manager holds decision authority to approve task delegations within its defined scope.

---

### Decision Right

**Definition:**  
The permission to make a particular kind of decision, granted by governance policies and bounded by scope, sensitivity, and risk level.

**Purpose:**  
To enable distributed decision-making while maintaining governance oversight.

**Usage:**  
Evaluated at decision points; enforced via policy checks and authority tokens.

**Related Concepts:**  
Decision Authority, Delegated Authority, Governance Authority, Policy Rule, Scope Limitation

**Related Components:**  
Decision Service, Policy Evaluation Engine (G-02), Authority Token, Scope Enforcer, Governance Interceptor

**Related Part 13 Sections:**  
13.4-Decision-Authority-and-Delegation.md

**Example:**  
An agent with the `finance.approve` decision right may authorize expenditures up to a predefined limit.

---

### Delegated Authority

**Definition:**  
Authority that has been formally transferred from a governing entity to an agent, workflow, or individual, subject to constraints and accountability requirements.

**Purpose:**  
To enable operational execution while retaining ultimate responsibility with the delegator.

**Usage:**  
Granted via delegation records; enforced at runtime; subject to revocation and monitoring.

**Related Concepts:**  
Authority, Decision Right, Responsibility, Accountability, Delegation Chain, Subdelegation

**Related Components:**  
Delegation Manager, Authority Service, Policy Evaluation Engine (G-02), Accountability Tracker, Revocation Service

**Related Part 13 Sections:**  
13.4-Decision-Authority-and-Delegation.md

**Example:**  
A team lead delegates the authority to provision test environments to a junior agent, with monthly review and revocation rights.

---

### Exception

**Definition:**  
A deviation from expected behavior, policy, or standard that requires handling, such as a policy violation, error, or unexpected event.

**Purpose:**  
To signal anomalies that may indicate risk, non-compliance, or system issues requiring attention.

**Usage:**  
Detected via monitoring, alerts, or reports; classified by severity and routed to appropriate handling processes.

**Related Concepts:**  
Violation, Error, Anomaly, Incident, Escalation, Remediation, Root Cause Analysis

**Related Components:**  
Exception Detector, Classifier, Router, Handler, Reporting Service

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md, 13.11-Auditability-and-Accountability.md

**Example:**  
An attempted access to a restricted data store by an unauthorized agent triggers a high-severity exception.

---

### Escalation

**Definition:**  
The process of elevating a governance issue (e.g., exception, violation, risk) to a higher level of authority or expertise for resolution.

**Purpose:**  
To ensure that issues beyond an entity's capacity or authority are addressed appropriately.

**Usage:**  
Triggered by predefined thresholds, policies, or manual judgment; followed by investigation and resolution.

**Related Concepts:**  
Exception, Violation, Risk, Incident, Authority Chain, Review Board, Governance Council

**Related Components:**  
Escalation Engine, Routing Service, Notification Service, Review Board, Governance Council

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
A critical security violation is escalated from the monitoring agent to the Security Governance Council for immediate response.

---

### Governance

**Definition:**  
The policies, rules, and oversight mechanisms that ensure the system operates within defined trust, security, and behavioral boundaries. (Consistent with Part 12 definition.)

**Purpose:**  
To maintain safety, compliance, and operational integrity across agent interactions.

**Usage:**  
Enforced by Security Gateway, Council, and Collaboration Manager.

**Related Components:**  
Security Gateway, Council, Collaboration Policy

**Related Documents:**  
`adrs.md`

**Related Architecture Sections:**  
13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.9, 13.10, 13.11

**Example:**  
Restricting high-risk operations to trusted agents; requiring council approval for sensitive workflows.

**Notes:**  
Governance should be centralized in policy, decentralized in enforcement.

---

### Governance Body

**Definition:**  
A formal group of agents, humans, or system components convened to exercise governance authority, such as setting policy, making decisions, or overseeing compliance.

**Purpose:**  
To provide collective judgment, legitimacy, and oversight for governance functions.

**Usage:**  
Established via charter; convenes regularly or as needed; records decisions and actions.

**Related Concepts:**  
Governance Authority, Governance Council, Governance Committee, Quorum, Consensus

**Related Components:**  
Governance Council Service, Voting Mechanism, Recording Service, Charter Store

**Related Part 13 Sections:**  
13.5-Governance-Councils-and-Committees.md

**Example:**  
The Architecture Governance Body reviews and approves all major system design changes.

---

### Governance Authority

**Definition:**  
The legitimate power to govern, derived from organizational leadership, regulatory mandates, or system charter, and exercised through governance bodies and mechanisms.

**Purpose:**  
To establish the foundation for policy creation, decision-making, and enforcement within the system.

**Usage:**  
Delegated to governance domains; invoked during policy approval, decision rendering, and enforcement actions.

**Related Concepts:**  
Supreme Authority, System Authority, Domain Authority, Operational Authority, Emergency Authority

**Related Components:**  
Authority Charter, Governance Body, Policy Evaluation Engine (G-02), Decision Service, Enforcement Point

**Related Part 13 Sections:**  
13.2-Governance-Architecture.md, 13.4-Decision-Authority-and-Delegation.md

**Example:**  
The System Authority grants the Security Governance Domain authority to enforce access control policies.

---

### Governance Domain

**Definition:**  
A distinct area of governance responsibility, such as Policy, Agent, Capability, Workflow, Data, Knowledge, Security, Operational, Risk, Compliance, Audit, or Architecture.

**Purpose:**  
To specialize governance functions and enable focused oversight of specific system aspects.

**Usage:**  
Each domain owns its policies, authorities, and accountability mechanisms; domains interact via shared events and feedback loops.

**Related Concepts:**  
Policy Governance, Agent Governance, Capability Governance, Workflow Governance, Data Governance, Knowledge Governance, Security Governance, Operational Governance, Risk Governance, Compliance Governance, Audit Governance, Architecture Governance

**Related Components:**  
Domain Manager, Policy Evaluation Engine (G-02), Authority Service, Accountability Tracker, Event Bus, Feedback Loop

**Related Part 13 Sections:**  
13.2-Governance-Architecture.md (lists all twelve domains)

**Example:**  
The Data Governance Domain manages data classification, retention, and usage policies across the system lifecycle.

---

### Governance Event

**Definition:**  
A discrete occurrence in the system representing a governance-relevant state change, action completion, or significant signal, such as a policy update, decision rendered, or violation detected.

**Purpose:**  
To enable loose coupling, observability, and reactive behavior within the governance architecture.

**Usage:**  
Published and consumed through Governance Event Bus; modeled in `governance-events.md`.

**Related Components:**  
Governance Event Bus, Observability, Communication Bus, Policy Evaluation Engine (G-02), Decision Service

**Related Part 13 Sections:**  
governance-events.md

**Example:**  
`policy.updated` event after a policy revision is published; `violation.detected` after an access control breach is identified.

---

### Governance Record

**Definition:**  
A durable, tamper-evident artifact that captures the details of a governance action, decision, or event, including actor, action, target, context, timestamp, and cryptographic proof.

**Purpose:**  
To provide auditable evidence for accountability, compliance, and historical analysis.

**Usage:**  
Stored in immutable storage; indexed for query; retained per policy; used during audits and investigations.

**Related Concepts:**  
Governance Event, Audit Evidence, Audit Trail, Attestation, Certification, Conformance, Non-repudiation

**Related Components:**  
Record Store, Immutable Logger, Signing Authority, Query Engine, Retention Service

**Related Part 13 Sections:**  
governance-events.md, 13.11-Auditability-and-Accountability.md

**Example:**  
A governance record of a council decision includes the voter IDs, votes, rationale, and a collective signature.

---

### Knowledge Governance

**Definition:**  
The domain of governance that manages knowledge creation, validation, sharing, obsolescence, and trustworthiness throughout its lifecycle.

**Purpose:**  
To ensure knowledge assets are accurate, relevant, and used appropriately to support decision-making and learning.

**Usage:**  
Applied during knowledge ingestion, curation, dissemination, and retirement; integrates with Data Governance and Audit Governance.

**Related Concepts:**  
Knowledge Artifact, Knowledge Object, Provenance, Trust Level, Reliability Rating, Staleness Detection

**Related Components:**  
Knowledge Registry, Validation Service, Trust Engine, Obsolescence Detector, Sharing Service

**Related Part 13 Sections:**  
13.9-Data-and-Knowledge-Governance.md

**Example:**  
A knowledge artifact documenting a best practice is versioned, signed, and tagged with a trust level before being shared.

---

### Owner

**Definition:**  
An entity (agent, human, or system component) that holds ultimate responsibility for a governance object, such as a policy, asset, or decision, and is answerable for its lifecycle and outcomes.

**Purpose:**  
To establish clear lines of responsibility and enable effective accountability.

**Usage:**  
Assigned during creation or delegation; recorded in ownership registries; verified during audits.

**Related Concepts:**  
Responsibility, Steward, Approver, Reviewer, Accountability, Delegated Authority

**Related Components:**  
Ownership Registry, Accountability Tracker, Delegation Manager, Review Service, Approval Service

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
The Policy Governance Domain is the owner of the data retention policy and must report on its compliance status.

---

### Policy

**Definition:**  
A defined rule or guideline that specifies required or prohibited behavior within a specific scope, expressed in machine-readable format for automated enforcement.

**Purpose:**  
To govern behavior, ensure compliance, and enable consistent decision-making across the system.

**Usage:**  
Evaluated at decision points; enforced via policy engines; updated through governance processes.

**Related Concepts:**  
Policy Rule, Policy Set, Policy Scope, Policy Evaluation, Policy Enforcement, Policy Conflict, Policy Override, Policy Exception, Policy Lifecycle, Policy Version, Policy Precedence

**Related Components:**  
Policy Evaluation Engine (G-02), Policy Registry, Evaluation Point, Enforcement Point, Version Control Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
A policy states that agents must not execute privileged commands without multi-party authorization.

**Notes:**  
Policy should be centralized in definition, decentralized in evaluation.

---

### Policy Conflict

**Definition:**  
A situation where two or more policies produce contradictory requirements or prohibitions for the same scope, action, or context.

**Purpose:**  
To identify inconsistencies that must be resolved to avoid ambiguous enforcement and ensure deterministic governance.

**Usage:**  
Detected via policy analysis tools; resolved via precedence hierarchy, conflict resolution rules, or governance body intervention.

**Related Concepts:**  
Policy Rule, Policy Set, Policy Override, Policy Exception, Precedence Hierarchy, Governance Body

**Related Components:**  
Conflict Detector, Resolution Engine, Precedence Service, Governance Council

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
One policy requires encryption of data at rest, while another prohibits encryption for performance testing; conflict resolved by scoping the second policy to non-production environments.

---

### Policy Enforcement

**Definition:**  
The mechanisms that prevent, detect, and correct policy violations, ensuring adherence to governance rules.

**Purpose:**  
To translate policy intent into observable system behavior and maintain compliance.

**Usage:**  
Applied as preventive controls (e.g., pre-action checks), detective controls (e.g., logging, alerts), and corrective controls (e.g., automated rollbacks).

**Related Concepts:**  
Policy, Policy Rule, Violation, Exception, Preventive Control, Detective Control, Corrective Control

**Related Components:**  
Enforcement Point, Policy Evaluation Engine (G-02), Monitoring Agent, Correction Service, Audit Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
A preventive control blocks a workflow deployment if it violates the separation-of-duties policy.

---

### Policy Exception

**Definition:**  
A formally approved deviation from a policy, granted for a specific scope, duration, and set of conditions, subject to monitoring and review.

**Purpose:**  
To accommodate legitimate needs that fall outside standard policy while maintaining governance oversight.

**Usage:**  
Requested via formal process; approved by governance body; recorded with justification and expiration; monitored for compliance.

**Related Concepts:**  
Policy, Policy Rule, Violation, Exception Handling, Approval Workflow, Review Schedule

**Related Components:**  
Exception Registry, Approval Service, Monitoring Agent, Notification Service, Review Board

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
An agent is granted a temporary policy exception to access legacy data stores during a migration project, with weekly review and automatic expiry.

---

### Policy Lifecycle

**Definition:**  
The sequence of states a policy progresses through from inception to retirement, including initiation, drafting, review, approval, publication, distribution, enforcement, monitoring, review, revision, and withdrawal.

**Purpose:**  
To ensure policies remain relevant, effective, and aligned with system needs over time.

**Usage:**  
Managed via governance tooling; tracked in policy registries; used for reporting and auditing.

**Related Concepts:**  
Policy, Policy Version, Policy Review, Policy Revision, Policy Withdrawal, Governance Body

**Related Components:**  
Policy Manager, Drafting Tool, Review Service, Approval Service, Publication Service, Distribution Service, Enforcement Point, Monitoring Agent, Evaluation Engine, Archive Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
A policy undergoes quarterly review; if found obsolete, it is revised or withdrawn following the lifecycle process.

---

### Policy Override

**Definition:**  
A mechanism that temporarily supersedes a policy under specific, high-risk or emergency conditions, requiring explicit authorization and subsequent review.

**Purpose:**  
To enable rapid response to critical situations while preserving accountability and governance integrity.

**Usage:**  
Invoked via authorized override request; enforced at runtime; logged for review; subject to post-incident analysis.

**Related Concepts:**  
Policy, Policy Rule, Emergency Authority, Governance Body, Incident Response, Post-Incident Review

**Related Components:**  
Override Service, Authorization Engine, Policy Evaluation Engine (G-02), Monitoring Agent, Investigation Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
During a system-wide outage, an override is granted to bypass change-freeze policies to apply a critical patch, with immediate reporting and post-implementation review.

---

### Policy Precedence

**Definition:**  
The hierarchical order that determines which policy takes effect when multiple policies apply to the same scope, action, or context.

**Purpose:**  
To ensure deterministic policy evaluation and avoid ambiguity in enforcement.

**Usage:**  
Defined in policy metadata; enforced by policy engine; referenced during conflict resolution.

**Related Concepts:**  
Policy, Policy Rule, Policy Set, Policy Conflict, Hierarchy, Governance Body

**Related Components:**  
Precedence Service, Policy Evaluation Engine (G-02), Evaluation Point, Governance Council

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
System-wide policies have higher precedence than domain-specific policies, which in turn override agent-level policies.

---

### Policy Rule

**Definition:**  
An atomic, machine-readable statement that defines a specific requirement, prohibition, or condition within a policy.

**Purpose:**  
To enable granular policy definition, evaluation, and enforcement.

**Usage:**  
Combined into policy sets; evaluated at decision points; enforced via enforcement points.

**Related Concepts:**  
Policy, Policy Set, Policy Scope, Policy Evaluation, Policy Enforcement, Policy Conflict, Policy Override, Policy Exception

**Related Components:**  
Policy Evaluation Engine (G-02), Rule Parser, Evaluation Point, Enforcement Point, Version Control Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
`"agents.must_not.execute_privileged_commands_without_mfa": true`

---

### Policy Set

**Definition:**  
A collection of related policy rules that together define a coherent governance stance on a particular domain or topic.

**Purpose:**  
To organize policies for easier management, versioning, and enforcement.

**Usage:**  
Versioned as a unit; deployed to enforcement points; reviewed and updated via governance processes.

**Related Concepts:**  
Policy, Policy Rule, Policy Scope, Policy Version, Policy Lifecycle, Governance Body

**Related Components:**  
Policy Manager, Version Control Service, Deployment Service, Review Service, Approval Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
The "Data Handling" policy set includes rules on classification, encryption, retention, and access control.

---

### Policy Scope

**Definition:**  
The boundary (e.g., agent, workflow, data type, time period) within which a policy or policy rule applies.

**Purpose:**  
To define the limits of policy applicability and enable fine-grained governance.

**Usage:**  
Specified in policy metadata; enforced by policy engine; used for targeting and exception handling.

**Related Concepts:**  
Policy, Policy Rule, Policy Set, Policy Evaluation, Policy Enforcement, Governance Body

**Related Components:**  
Scope Parser, Policy Evaluation Engine (G-02), Evaluation Point, Enforcement Point, Version Control Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
A policy rule applies only to agents with the `data.processor` role and during business hours (09:00–17:00).

---

### Policy Version

**Definition:**  
An immutable identifier assigned to a policy or policy set at a point in time, enabling tracking of changes and ensuring consistent enforcement.

**Purpose:**  
To support policy evolution, rollback, and auditability of governance decisions.

**Usage:**  
Assigned during approval; referenced in enforcement logs; used for change detection and reporting.

**Related Concepts:**  
Policy, Policy Set, Policy Lifecycle, Governance Body, Immutable Artifact, Audit Trail

**Related Components:**  
Version Control Service, Policy Registry, Audit Logger, Reporting Service, Archive Service

**Related Part 13 Sections:**  
13.3-Policy-Architecture.md

**Example:**  
Policy `data.retention` at version `v2.1.0` includes updated retention periods for confidential data.

---

### Risk

**Definition:**  
The potential for loss, damage, or failure due to uncertainties, vulnerabilities, or threats, measured by likelihood and impact.

**Purpose:**  
To inform governance decisions, prioritize mitigations, and enable proactive risk management.

**Usage:**  
Assessed via risk analysis; monitored via risk indicators; mitigated via controls; accepted or escalated based on tolerance.

**Related Concepts:**  
Risk Appetite, Risk Threshold, Risk Owner, Risk Mitigation, Control, Compliance, Violation, Exception

**Related Components:**  
Risk Analyzer, Risk Indicator Service, Mitigation Planner, Escalation Engine, Acceptance Board

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
The risk of unauthorized data access is assessed as high likelihood and high impact, triggering encryption and access controls.

---

### Risk Appetite

**Definition:**  
The level of risk that an organization or governance body is willing to accept in pursuit of its objectives, often expressed qualitatively or quantitatively.

**Purpose:**  
To guide risk assessment, mitigation prioritization, and acceptance decisions.

**Usage:**  
Defined by governance bodies; used to compare against assessed risk levels; informs escalation and acceptance.

**Related Concepts:**  
Risk, Risk Threshold, Risk Owner, Risk Tolerance (deprecated), Control, Compliance

**Related Components:**  
Risk Appetite Service, Governance Body, Acceptance Board, Escalation Engine, Reporting Service

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
The governance body defines a moderate risk appetite, accepting risks with medium likelihood and low impact without mitigation.

---

### Risk Owner

**Definition:**  
The entity (agent, human, or system component) responsible for identifying, assessing, mitigating, and monitoring a specific risk, and for reporting its status to governance bodies.

**Purpose:**  
To ensure clear accountability for risk management and enable effective oversight.

**Usage:**  
Assigned during risk identification; recorded in risk registries; verified during audits and reviews.

**Related Concepts:**  
Risk, Risk Appetite, Risk Threshold, Risk Mitigation, Control, Compliance, Accountability

**Related Components:**  
Risk Registry, Ownership Tracker, Mitigation Planner, Monitoring Agent, Reporting Service

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
The Data Governance Domain is the risk owner for risks related to data leakage and must report on mitigation effectiveness.

---

### Risk Threshold

**Definition:**  
The level of risk at or above which a governance body requires action, such as mitigation, escalation, or acceptance with review.

**Purpose:**  
To trigger timely risk response and ensure alignment with organizational tolerance.

**Usage:**  
Defined by governance bodies; compared against assessed risk levels; used to automate escalation or acceptance workflows.

**Related Concepts:**  
Risk, Risk Appetite, Risk Owner, Risk Mitigation, Control, Compliance, Acceptance

**Related Components:**  
Threshold Service, Risk Analyzer, Escalation Engine, Acceptance Board, Governance Body

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
A risk threshold is set at "high"; any assessed risk reaching high or above triggers automatic escalation to the Risk Governance Council.

---

### Reviewer

**Definition:**  
An entity (agent, human, or system component) tasked with evaluating a governance artifact, such as a policy, decision, or exception, for correctness, completeness, and compliance.

**Purpose:**  
To provide independent oversight, improve quality, and ensure accountability.

**Usage:**  
Invoked via review workflow; provided with context and criteria; returns findings and recommendations.

**Related Concepts:**  
Approver, Owner, Steward, Accountability, Governance Body, Governance Council

**Related Components:**  
Review Service, Approval Service, Governance Council, Feedback Loop, Reporting Service

**Related Part 13 Sections:**  
13.5-Governance-Councils-and-Committees.md, 13.11-Auditability-and-Accountability.md

**Example:**  
A reviewer assesses a proposed policy change for alignment with architectural principles and potential conflicts.

---

### Responsibility

**Definition:**  
The duty to perform or complete a task, role, or obligation, and to be answerable for its outcomes.

**Purpose:**  
To define expectations and enable accountability within the system.

**Usage:**  
Assigned based on role, context, or delegation; tracked in responsibility matrices; verified during audits.

**Related Concepts:**  
Accountability, Owner, Steward, Approver, Reviewer, Delegated Authority

**Related Components:**  
Responsibility Matrix, Assignment Engine, Ownership Tracker, Delegation Manager, Audit Service

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
An agent has the responsibility to validate incoming data against schema before processing.

---

### Security Governance

**Definition:**  
The domain of governance that defines security policies, controls access, manages threat response, and ensures the confidentiality, integrity, and availability of system assets.

**Purpose:**  
To protect the system from unauthorized or malicious activities and maintain trust in its operations.

**Usage:**  
Applied during system design, deployment, and operation; integrates with Risk Governance, Audit Governance, and Compliance Governance.

**Related Concepts:**  
Policy, Control, Threat, Vulnerability, Incident, Violation, Exception, Certification, Accreditation

**Related Components:**  
Security Policy Engine, Access Control Manager, Threat Detector, Incident Responder, Audit Service

**Related Part 13 Sections:**  
13.10-Security-and-Trust-Governance.md

**Example:**  
Security governance enforces zero-trust principles, requiring authentication and authorization for every inter-component communication.

---

### Steward

**Definition:**  
An entity entrusted with the care and management of a governance asset (e.g., knowledge, data, policy) on behalf of the owner, responsible for maintaining its quality, usability, and compliance.

**Purpose:**  
To enable specialized care of assets while retaining ultimate ownership accountability.

**Usage:**  
Assigned via stewardship agreements; recorded in stewardship registries; monitored for performance and compliance.

**Related Concepts:**  
Owner, Accountability, Responsibility, Delegated Authority, Governance Body

**Related Components:**  
Stewardship Registry, Accountability Tracker, Monitoring Agent, Reporting Service, Review Service

**Related Part 13 Sections:**  
13.11-Auditability-and-Accountability.md

**Example:**  
A knowledge steward ensures that a widely used runbook remains accurate, versioned, and accessible to authorized agents.

---

### Trust Domain

**Definition:**  
A sphere of influence where trust assumptions are shared, validated, and enforced, enabling secure interactions between agents, workflows, or system components.

**Purpose:**  
To establish boundaries for trusted communication, data sharing, and collaborative operations.

**Usage:**  
Defined via trust policies; enforced at communication boundaries; used for access control and encryption decisions.

**Related Concepts:**  
Trust Boundary, Zero Trust, Authentication, Authorization, Encryption, Attestation, Certification

**Related Components:**  
Trust Policy Engine, Boundary Enforcer, Authentication Service, Authorization Service, Encryption Manager, Attestation Service

**Related Part 13 Sections:**  
13.10-Security-and-Trust-Governance.md

**Example:**  
All agents within the `finance.trust.domain` may exchange transaction data without additional encryption, subject to access controls.

---

### Violation

**Definition:**  
A specific type of exception that represents a breach of governance policy, standard, or regulation, often requiring escalation and remediation.

**Purpose:**  
To signal non-compliance that may result in risk, penalties, or reputational damage.

**Usage:**  
Detected via monitoring, policy evaluation, or audit; classified by severity; routed to violation handling processes.

**Related Concepts:**  
Exception, Policy, Policy Rule, Non-compliance, Escalation, Remediation, Root Cause Analysis

**Related Components:**  
Violation Detector, Classifier, Router, Handler, Reporting Service, Escalation Engine

**Related Part 13 Sections:**  
13.6-Risk-and-Compliance-Governance.md

**Example:**  
An agent attempting to disable audit logging triggers a policy violation of type `logging.disabled`.

---

## Acronyms

| Acronym | Meaning |
|---------|---------|
| ABAC | Attribute-Based Access Control |
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| RBAC | Role-Based Access Control |
| SLA | Service Level Agreement |
| SLO | Service Level Objective |
| TTL | Time To Live |
| UUID | Universally Unique Identifier |

## Naming Conventions

- **Governance Domains**: Use kebab-case with `-governance` suffix, e.g., `agent-governance`, `data-governance`.
- **Policies**: Use dot-separated namespaces, e.g., `agents.must_not.execute_privileged_commands_without_mfa`.
- **Policy Sets**: Use PascalCase, e.g., `DataHandlingPolicySet`.
- **Governance Events**: Use past-tense, dot-separated names, e.g., `policy.updated`, `violation.detected`.
- **Governance Records**: Use PascalCase with `Record` suffix, e.g., `PolicyUpdateRecord`.
- **Authorities**: Use kebab-case, e.g., `system-authority`, `security-governance-authority`.
- **Roles**: Use lowercase or kebab-case, e.g., `approver`, `policy-reviewer`.
- **Documents**: Use descriptive titles with section prefixes, e.g., `13.3-Policy-Architecture.md`.

## Canonical Terminology

This section reinforces the canonical terms defined above. Use these exact terms in all Part 13 documentation, components, and implementations to ensure consistency and clarity.

## Frequently Confused Terms

| Term A | Term B | Distinction |
|--------|--------|-------------|
| Governance | Management | Governance is policy and oversight; Management is operational execution and administration. |
| Policy | Procedure | Policy defines what must or must not be done; Procedure defines how to do it. |
| Authority | Responsibility | Authority is the right to act; Responsibility is the duty to act and answer for outcomes. |
| Accountability | Responsibility | Accountability is answerability for outcomes; Responsibility is the duty to perform tasks. |
| Delegated Authority | Delegated Responsibility | Delegated Authority transfers decision rights; Delegated Responsibility transfers duty to perform (rare and limited). |
| Risk | Issue | Risk is potential future loss; Issue is a current problem or fault. |
| Compliance | Conformance | Compliance is adherence to external regulations; Conformance is adherence to internal policies or standards. |
| Audit | Inspection | Audit is independent, systematic, and evidence-based; Inspection may be informal and less rigorous. |
| Violation | Exception | Violation is a breach of policy; Exception is any deviation from expected (may or may not be policy-related). |
| Approval | Review | Approval grants permission to proceed; Review evaluates correctness and recommends action. |
| Owner | Steward | Owner holds ultimate responsibility; Steward manages asset on behalf of owner. |
| Risk Appetite | Risk Threshold | Risk Appetite is the amount of risk one is willing to accept; Risk Threshold is the level that triggers action. |
| Control | Control Objective | Control is the mechanism; Control Objective is the goal the control aims to achieve. |
| Policy Rule | Policy Set | Policy Rule is an atomic statement; Policy Set is a collection of related rules. |
| Policy Version | Policy Revision | Policy Version is an immutable identifier; Policy Revision is the act of changing a policy. |
| Governance Body | Governance Council | Governance Body is any formal governance group; Governance Council is a specific type with decision-making authority. |
| Attestation | Certification | Attestation is a signed statement of truth; Certification is formal recognition of compliance with standards. |
| Audit Evidence | Audit Trail | Audit Evidence is the data collected; Audit Trail is the chronological log of actions. |
| Escalation | Notification | Escalation raises issue to higher authority; Notification simply informs relevant parties. |
| Exception Handling | Incident Response | Exception Handling deals with deviations; Incident Response deals with security or operational breaches. |
| Governance Event | System Event | Governance Event is specifically governance-relevant; System Event is any occurrence in the system. |
| Governance Record | Log Entry | Governance Record is tamper-evident and includes proof; Log Entry may be mutable and minimal. |
| Policy Lifecycle | Policy Management | Policy Lifecycle is the sequence of states a policy goes through; Policy Management is the active oversight of that lifecycle. |

## Deprecated Terminology

| Deprecated Term | Replacement | Deprecated In | Removed At | Migration Notes |
|-----------------|-------------|---------------|------------|----------------|
| Risk Tolerance | Risk Appetite | 1.0 | TBD | Update references from tolerance to appetite. |
| Governing Body | Governance Body | Pre-13 | TBD | Governance Body subsumes Governing Body role. |
| Privilege | Decision Right | Pre-13 | TBD | Decision Right subsumes Privilege role. |
| Policy Directive | Policy Rule | Pre-13 | TBD | Renamed for consistency with Policy Architecture naming. |
| Audit Record | Audit Evidence | Pre-13 | TBD | Renamed for consistency with Audit terminology. |

## Aliases and Synonyms

| Canonical Term | Alias / Synonym | Status | Notes |
|----------------|-----------------|--------|-------|
| Governance Authority | Governing Authority | Preferred | `Governing Authority` is shorthand for `Governance Authority` in policy contexts. |
| Decision Right | Decision Privilege | Contextual | `Decision Privilege` may refer to `Decision Right` in delegation contexts. |
| Delegated Authority | Delegated Power | Informal | Used in internal discussion; formal documentation must use `Delegated Authority`. |
| Policy Rule | Rule | Contextual | `Rule` alone may refer to `Policy Rule` in policy-management contexts. |
| Policy Set | Policy Bundle | Variant | `Policy Bundle` is acceptable in prose after first full mention. |
| Accountability Owner | Owner | Contextual | `Owner` alone may refer to `Accountability Owner` in responsibility contexts. |
| Risk Appetite | Risk Tolerance | Deprecated alias | Use `Risk Appetite`; `Risk Tolerance` is deprecated. |
| Control Objective | Control Goal | Informal | Never used as a single token; always `Control Objective`. |
| Audit Trail | Audit Log | Variant | `Audit Log` is acceptable in prose after first full mention. |
| Conformance | Compliance Level | Contextual | `Compliance Level` may refer to `Conformance` in audit contexts. |

## Reserved Governance Terms

The following terms are reserved for future use and must not be introduced in designs, documentation, or code without explicit Part 13 Lead approval:

- `Governance Matrix`
- `Policy Engine`
- `Decision Ledger`
- `Authority Graph`
- `Accountability Chain`
- `Risk Heatmap`
- `Compliance Dashboard`
- `Audit Chain`
- `Governance Token`
- `Delegation Certificate`
- `Policy Version Control`
- `Governance Smart Contract`

## Cross-Part Terminology

(See **Cross-Part Terminology Consistency** table above for details.)

## Glossary Governance

This glossary itself is governed by the following:

- **Ownership**: Part 13 Architecture Team
- **Change Authority**: Part 13 Lead
- **Review Cadence**: Per release
- **Storage Location**: `C:\Development\AI-OS\architecture\Part13\glossary.md`
- **Update Process**: Follow the **Evolution Policy** section; changes require Part 13 Lead approval and cross-part review when terms span multiple parts.
- **Versioning**: Increment glossary version with each update; reflect in `Document Control` table.

## Terminology Evolution Policy

New terms should be added when:
- A new governance concept is introduced in Part 13 specifications, components, or implementations.
- An existing term requires refinement to avoid ambiguity.
- A cross-part term is adopted with Part 13‑specific semantics.

Deprecated terms are retained for at least one major version to allow migration. Removed terms are moved to the **Deprecated Terminology** table with a removal target.

All changes must be documented in an ADR (Architecture Decision Record) per Part 13 processes.

---