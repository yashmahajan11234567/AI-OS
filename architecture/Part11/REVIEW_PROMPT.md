# Enterprise AI Architecture Review Prompt for Part 11

## Purpose
This document establishes a comprehensive framework for conducting principled, evidence-based architectural reviews of Part 11 of the AI-OS architecture. Rather than prescribing a checklist, it guides reviewers to think like architects—focusing on systemic properties, trade-offs, and architectural integrity. Every finding must be grounded in documented evidence with clear architectural reasoning that explains why it matters from a system-wide perspective.

## Architectural Review Mindset

### Think in Systems, Not Components
Review architecture by asking:
- How do the documented structures support the required system qualities?
- Do components interact in ways that preserve or undermine desired properties?
- Where might local optimizations create global fragility?
- Does the architecture enable or inhibit evolution over time?

### Reason from Principles, Not Preferences
Ground all assessments in:
- Explicitly stated architectural principles from Parts 1-10
- Established patterns and their documented rationale
- System quality attribute requirements (performance, security, scalability, etc.)
- Documented constraints and assumptions

### Seek Evidence, Not Conjecture
For every observation:
- Cite specific sections, figures, tables, or examples from Part 11
- Reference relevant principles from Parts 1-10 when claiming alignment or deviation
- Distinguish between documented intent and inferred behavior
- Note where documentation is silent versus where it makes definitive claims

### Judge Implementation Independence
Continuously ask:
- Could multiple valid implementations satisfy this architectural description?
- Does the description overspecify solutions that should be design decisions?
- Are technology choices justified as strategic architectural decisions?
- Where might implementation details be inappropriately elevated to architectural significance?

## Required Review Outputs

Every review MUST produce the following sections in its report:

### Executive Summary
A concise (1-2 page) distillation of the review's most significant architectural insights, including overall architectural fitness and critical risks.

### Overall Score
A holistic assessment of architectural soundness using one of:
- **SOUND**: Architecture establishes strong foundation for system qualities with minor opportunities for refinement
- **CONDITIONALLY SOUND**: Architecture has significant but addressable gaps requiring focused improvement
- **UNSOUND**: Architecture has critical flaws that undermine core system qualities and require major revision

### Architecture Strengths
Documented elements that demonstrably support desired system qualities, with specific evidence and explanation of how they contribute to architectural integrity.

### Architecture Weaknesses
Documented elements that create unnecessary risk or inhibit evolution, with specific evidence and explanation of their architectural impact.

### Missing Architecture
Important architectural concerns (components, interfaces, properties, or constraints) that are absent or inadequately addressed despite being implied by requirements or principles from Parts 1-10.

### Implementation Leakage
Cases where design or implementation details are inappropriately presented as architectural decisions, constraining valid implementation alternatives without architectural justification.

### Cross-Part Consistency
Evaluation of how well Part 11 aligns with architectural patterns, principles, and interfaces established in Parts 1-10, including specific examples of alignment and deviation.

### Diagram Review
Assessment of all architectural diagrams for correctness, clarity, consistency with text, and effectiveness in conveying architectural intent (not implementation details).

### Behavioural Contract Review
Evaluation of how well interfaces define clear behavioral expectations (preconditions, postconditions, invariants, performance, security) that enable independent reasoning about components.

### Runtime Invariant Review
Assessment of how well the documentation identifies and preserves critical system properties that must hold during execution.

### Editorial Findings
Observations about document clarity, organization, terminology consistency, and accessibility that affect architectural understanding but do not constitute architectural deficiencies.

### Final Recommendation
A clear directive: **FREEZE** (document is architecturally sound and ready for implementation guidance) or **IMPROVE** (document requires architectural revisions before use as implementation baseline).

### Freeze / Improve Justification
Specific, evidence-based reasoning for the final recommendation, referencing the most significant findings that drive the conclusion.

## Conducting the Review

### Begin with Architectural Intent
Before examining details, establish:
1. What system qualities does Part 11 purport to support (based on stated goals and Principles 1-10)?
2. What architectural strategies does it employ to achieve these qualities?
3. What are the key boundaries and responsibilities it defines?

### Evaluate for Sufficiency, Not Just Completeness
Ask not only "Is X documented?" but:
- Is the documentation sufficient to reason about X's contribution to system qualities?
- Does it provide adequate context for evaluating trade-offs involving X?
- Does it distinguish between architecturally significant aspects of X and implementation details?

### Trace All Claims to Evidence
When asserting that Part 11:
- **Does** something: cite where it is explicitly stated or clearly implied
- **Does not** something: cite where it should be present but is absent or vague
- **Violates** a principle: cite the principle and where the documentation contradicts it
- **Aligns** with a pattern: cite the pattern and where the documentation reflects it

### Apply Architectural Reasoning to Every Finding
For each observation, explain:
- **What** you observed (with evidence)
- **Where** you observed it (specific location)
- **Why it matters architecturally** (impact on system qualities, evolutionary fitness, etc.)
- **How it relates to Principles 1-10** (alignment or deviation)
- **What architectural alternative or improvement** would address the concern (if applicable)

## Applying Review Criteria Through Guided Inquiry

Rather than checking items on a list, pursue these lines of inquiry to uncover architectural insights:

### Architectural Consistency & Principle Adherence
- How do the documented structures reflect or contradict the architectural vision from Parts 1-10?
- Where does Part 11 introduce new principles that compete with or complement existing ones?
- Are technology choices justified as strategic decisions with clear rationale, or presented as implementation preferences?
- How would you evaluate whether a proposed change preserves or harms architectural integrity?

### Completeness & Sufficiency for Architectural Reasoning
- What questions would an architect need to answer to implement or evolve this architecture that remain unanswered?
- Where are critical assumptions undocumented or unjustified?
- How well does the documentation support reasoning about system qualities (e.g., "If load doubles, what happens?")?
- What failure modes can you reason about from the documentation, and what cannot you reason about?

### Consistency as Architectural Integrity
- How would inconsistent terminology or notation create confusion about architectural boundaries?
- Where might naming conventions inadvertently create tight coupling or obscure separation of concerns?
- How do interface definitions support or inhibit independent evolution of components?
- What does the consistency (or inconsistency) of diagrams say about the cognitive unity of the architectural model?

### Security as an Architectural Property
- How does the architecture support or hinder defense in depth?
- Where are trust boundaries defined, and how are they validated?
- How are security concerns decomposed and allocated across components?
- What security mechanisms are presented as fundamental, and what are left to implementation?

### Reliability as an Emergent Property
- How does the architecture contain failures and prevent cascading effects?
- Where are recovery mechanisms documented as first-class concerns versus afterthoughts?
- How does the documentation support reasoning about system behavior under partial failure?
- What assumptions about environmental reliability are explicit versus implicit?

### Scalability as a Structural Property
- How does the structure support or impede horizontal scaling?
- Where are resource contention points identified and mitigated?
- How well does the documentation support reasoning about performance under varying loads?
- What scaling strategies are documented as architectural decisions versus implementation optimizations?

### Maintainability as an Evolutionary Property
- How does the structure support or impede independent evolution of components?
- Where are change impacts localized versus spread across the system?
- How does the documentation support reasoning about the cost of change?
- What mechanisms for managing complexity and technical debt are documented architecturally?

### Runtime Correctness as a Foundational Concern
- What invariants are documented as essential to system correctness?
- How does the architecture prevent or detect invariant violations?
- Where are concurrency and timing considerations addressed as architectural concerns?
- How does the documentation support reasoning about behavior under unusual conditions?

### EventBus Consistency as an Integration Mechanism
- How are events used to achieve loose coupling versus creating hidden dependencies?
- Where are event semantics documented clearly enough to reason about system behavior?
- How are ordering guarantees and idempotency concerns addressed architecturally?
- What mechanisms for event evolution and versioning are documented?

### Cross-Part Integration as Boundary Management
- How are responsibilities cleanly divided between Part 11 and other parts?
- Where are integration points documented with sufficient clarity to reason about system behavior?
- How are conflicts between architectural concerns from different parts resolved or managed?
- What patterns for integration are documented as architectural decisions?

### Terminology as Conceptual Clarity
- How does consistent terminology support shared understanding among stakeholders?
- Where might ambiguous terms create mistaken assumptions about capabilities or responsibilities?
- How well does the glossary capture the ubiquitous language of the domain?
- How are metaphors and analogies used to explain complex architectural concepts?

### Documentation Quality as Architectural Communication
- How does the document structure support or impede architectural understanding?
- Where do examples clarify versus confuse architectural intent?
- How accessible is the document to stakeholders with different technical backgrounds?
- What mechanisms exist for keeping the documentation aligned with the evolving architecture?

### Mermaid Diagrams as Architectural Models
- How do diagrams complement or duplicate textual descriptions?
- Where do diagrams reveal structural properties that are obscure in text?
- How effective are diagrams at communicating architectural intent versus design details?
- What would an architect learn from studying the diagrams alone?

### Behavioural Contracts as Enablers of Independence
- How do contracts reduce the need for global reasoning about system behavior?
- Where are contracts sufficiently precise to enable independent component validation?
- How do contracts support or hinder substitution of implementations?
- What contractual omissions would most impede independent reasoning?

### Runtime Invariants as Guardrails of Correctness
- Which invariants are documented as architectural constraints versus implementation details?
- How well does the documentation support reasoning about invariant preservation under change?
- Where are mechanisms for invariant validation documented as architectural concerns?
- What would happen if a documented invariant were violated at runtime?

### Architecture Anti-Patterns as Risk Indicators
- Where do documented structures create unnecessary complexity or coupling?
- How might proposed solutions exacerbate rather than mitigate architectural risks?
- What structural alternatives would better support the desired system qualities?
- How do documented patterns align with or deviate from established anti-pattern guidance?

### Architecture Maturity as a Journey
- What evidence shows the architecture has evolved beyond ad hoc decisions?
- How systematically are non-functional requirements addressed and validated?
- What mechanisms exist for measuring and improving architectural quality over time?
- How does the architecture balance expedience with long-term vision?

## Evidence Requirements

For every finding in your report:
1. **Locate the evidence**: Point**: Provide the specific section, figure, table, or example reference
2. **Quote**: Include relevant verbatim text when making precise claims
3. **Principle**: Cite the specific architectural principle from Parts 1-10 that bears on the observation
4. **Impact**: Explain the consequence for system qualities, evolutionary fitness, or architectural integrity
5. **Alternative**: When recommending change, describe an architecturally sound alternative

## Architecture-Level Reasoning Examples

### Instead of: "Section 3.2 lacks detail on error handling"
### Write: "Section 3.2 documents error handling mechanisms but does not specify how errors propagate across service boundaries (p. 14, §3.2.3). This omission makes it impossible to reason about fault containment, a key reliability principle from Part 4 (§4.1). Without defined error propagation contracts, local error handling decisions could inadvertently create cascading failures. The architecture should specify whether errors are contained at service boundaries or propagate according to defined contracts."

### Instead of: "The diagram in Figure 5 is unclear"
### Write: "Figure 5's component diagram shows bidirectional connections between the Authentication Service and Data Access Layer (p. 27, Fig. 5), creating potential circular dependencies that undermine the layered architecture principle from Part 3 (§3.4). This coupling makes it difficult to reason about changes to either component in isolation. Consider restructuring to use events or interfaces to break the direct dependency while preserving necessary communication."

## RFC 2119 Validation Guidance

When evaluating requirements specifications:
- **MUST/MUST NOT**: Non-negotiable constraints critical to architectural integrity. Verify these are few, fundamental, and justified.
- **SHOULD/SHOULD NOT**: Strong preferences with significant architectural impact. Examine trade-offs and justification.
- **MAY**: Permitted variations or options. Confirm they don't create harmful fragmentation.
- **OBSERVATION**: Statements of fact or intent without requirement weight.

Check that:
- Keywords are used consistently with their formal meanings
- Lower-case instances are not inadvertently interpreted as requirements
- Requirements are architecturally significant rather than implementation details
- Conflicting requirements are identified and resolved

## Cross-Reference Validation Practice

Verify that:
- All internal references (sections, figures, tables) resolve to existing content
- External references point to current, relevant, and accessible resources
- Referenced material actually supports the claim being made
- Circular or self-referential dependencies are identified and justified
- References to Parts 1-10 are accurate and relevant to the point being made

## Implementation-Independence Testing

Regularly ask:
- If I were to implement this architecture using different technologies, what aspects would remain unchanged?
- Which documented details would unnecessarily constrain my implementation choices?
- Where does the description specify 'how' rather than 'what' or 'why'?
- What implementation alternatives would satisfy the architectural intent but violate documented details?

## Architecture Maturity Evaluation Approach

Assess maturity by looking for:
- **Repeatability**: Evidence of consistent application of patterns and principles
- **Definitivity**: Comprehensive documentation that supports independent reasoning
- **Measurability**: Mechanisms for assessing architectural quality and technical debt
- **Optimization**: Improvement trending based on measured feedback

For your maturity conclusion, address:
- What specific evidence supports your assessed level?
- What specific gaps prevent achievement of the next level?
- What targeted investments would most effectively advance maturity?

## Reviewer Discipline

Maintain architectural focus by:
- Returning repeatedly to: "Does this finding impact how we reason about the system as a whole?"
- Distinguishing between tactical corrections and strategic architectural improvements
- Considering both the stated vision and the emerging architecture that the document describes
- Remembering that the goal is not perfection, but sufficient architectural integrity to guide sound implementation and evolution

A review is complete when you can confidently answer:
- Does the documentation provide a sufficiently sound architectural foundation for implementation?
- What are the most significant architectural risks or opportunities?
- Does the documentation enable informed architectural decision-making?
- What is your evidence-based recommendation: FREEZE or IMPROVE?