# AI-OS Prompt Engineering Handbook

The official prompt engineering guide for developing AI-OS Architecture documentation, specifications, and related artifacts.

---

## Table of Contents
1. [Prompt Philosophy](#prompt-philosophy)
2. [Architecture Creation Prompts](#architecture-creation-prompts)
3. [Part Creation Prompts](#part-creation-prompts)
4. [Review Prompts](#review-prompts)
5. [Improvement Prompts](#improvement-prompts)
6. [Consistency Prompts](#consistency-prompts)
7. [Diagram Prompts](#diagram-prompts)
8. [ADR Prompts](#adr-prompts)
9. [Publication Prompts](#publication-prompts)
10. [Freeze Prompts](#freeze-prompts)
11. [Best Practices](#best-practices)
12. [Prompt Lifecycle](#prompt-lifecycle)
13. [Cross References](#cross-references)
14. [Reusable Prompt Templates](#reusable-prompt-templates)

---

## Prompt Philosophy

AI-OS prompt engineering follows these core principles:

### 1. **Specification-First Approach**
All prompts must reference relevant AI-OS specification parts (Parts 1-15) to ensure architectural alignment and prevent specification drift.

### 2. **Principle Alignment**
Generated outputs must align with AI-OS Engineering Principles ([[ENGINEERING_PRINCIPLES.md]]) and architectural vision ([[AI_OS_MASTER_CONTEXT.md]]).

### 3. **Ecosystem Awareness**
Prompts should consider impact on Skills, MCP, and Repository ecosystems, ensuring extensibility and compatibility.

### 4. **Governance Compliance**
Outputs must follow AI-OS governance processes and requirements, including proper decision recording and validation approaches.

### 5. **Validation Mindset**
Include mechanisms for verifying correctness and quality in all architectural prompts.

### 6. **Technology Neutrality**
Avoid prescribing specific technologies unless architecturally necessary; focus on contracts and principles.

### 7. **Implementation Independence**
Separate interfaces and contracts from implementations to enable multiple conforming implementations.

### 8. **Traceability & Reusability**
Structure outputs for easy updating, evolution, and potential reuse in similar contexts.

---

## Architecture Creation Prompts

### System Architecture Design Prompt
**Purpose**: Generate high-level system architecture for new AI-OS features or services.
**Recommended Model**: Claude Opus 4.8
**Expected Output**: Detailed architecture description with component interactions, data flow, and technology recommendations aligned with AI-OS specification.

**Prompt Template**:
```
You are an expert AI-OS architect. Design a system architecture for [FEATURE/SERVICE] that must handle [REQUIREMENTS] while conforming to AI-OS Architecture Specification Parts [X-Y].

Consider: scalability, reliability, security, maintainability, cost-effectiveness, and alignment with AI-OS engineering principles.

Provide:
1. High-level component diagram description using AI-OS conventions
2. Data flow between components with event schemas
3. Technology recommendations with justification and alternatives considered
4. Key architectural patterns applied (from AI-OS specification)
5. Potential bottlenecks and mitigation strategies
6. Deployment and operational considerations
7. Interface contracts with other AI-OS parts
8. Extension points for future variability
9. Conformance criteria for validation

Reference relevant AI-OS documents:
- [[AI_OS_MASTER_CONTEXT.md]] for overall context
- [[ENGINEERING_PRINCIPLES.md]] for engineering principles
- [[ARCHITECTURE_DECISIONS.md]] for relevant decisions
- [[VALIDATION_ARCHITECTURE.md]] for validation approaches
- [[GLOSSARY.md]] for shared terminology

Format your response as a structured architecture document suitable for AI-OS Architecture Review Board review.
```

### Hermes Kernel Extension Prompt
**Purpose**: Design extensions to the Hermes Kernel while maintaining its orchestrator role.
**Recommended Model**: Claude Opus 4.8
**Expected Output**: Extension design that preserves Kernel purity while adding capability.

**Prompt Template**:
```
Design an extension to the Hermes Kernel for [CAPABILITY] that maintains the Kernel as pure orchestrator (zero domain logic).

Consider:
- Which of the 4 Core Components or 9 Core Managers this affects
- How it integrates with EventBus-only communication (post-initialization)
- Resource quota management through ResourceManager
- State scoping through StateManager
- Workflow integration through WorkflowManager
- Extension point mechanisms (Skills, MCP, Repository)

Provide:
1. Extension mechanism description
2. Interface contracts with Kernel components
3. Event schemas for communication
4. Resource management considerations
5. State management approach
6. Workflow integration points
7. Security and permission considerations
8. Validation and testing strategy
9. Backward compatibility guarantees

Reference: [[AI_OS_MASTER_CONTEXT.md]] Sections 4 (Hermes Kernel Architecture) and 5 (Core Managers)
```

### Engineering Service Design Prompt
**Purpose**: Design new Engineering Services following SDLC phase alignment.
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Service design document with BaseService contract adherence and event-driven patterns.

**Prompt Template**:
```
Design an AI-OS Engineering Service for [SDLC_PHASE] that follows the BaseService contract and event-driven communication principles.

Consider:
- Which SDLC phase this service addresses (Planning, Coding, Review, Testing, Deployment, Operations, Learning, Memory)
- Event types it emits and consumes
- StateManager integration for persistence
- ResourceManager quotas
- WorkflowManager orchestration
- Configuration immutability after INITIALIZING
- Observability requirements (logging, metrics, tracing)
- Fault tolerance and recovery mechanisms
- Governance integration (Council, AI Agency)

Provide:
1. Service responsibilities and boundaries
2. Event schema definitions (with versioning)
3. StateManager usage patterns
4. Resource consumption characteristics
5. Workflow integration points
6. Configuration schema and defaults
7. Health check implementations
8. Error handling and fault tolerance
9. Audit trail requirements
10. Test strategy (unit, integration, property-based)

Reference: [[AI_OS_MASTER_CONTEXT.md]] Section 6 (Engineering Services) and Section 7 (Service Framework)
```

### Extension Point Design Prompt
**Purpose**: Design intentional extension points for AI-OS parts.
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Extension point specification with contracts, guidelines, and compatibility considerations.

**Prompt Template**:
```
Design an extension point for [AI-OS_PART] that enables [EXTENSION_TYPE] while maintaining architectural integrity.

Consider:
- Discovery mechanisms for extensions
- Versioning and compatibility strategies
- Performance and security implications
- Lifecycle management (registration, initialization, execution, cleanup)
- Extension contracts (what extensions can rely on)
- Constraints on what can be extended
- Guidelines for extension developers
- Isolation and fault tolerance for extension failures

Provide:
1. Extension point purpose and mechanism
2. Constraints and limitations documentation
3. Extension contract specification
4. Versioning and compatibility approach
5. Performance impact considerations
6. Security implications and required permissions
7. Lifecycle management details
8. Developer guidelines and examples
9. Discovery and loading mechanisms
10. Validation approaches for extensions

Reference: [[AI_OS_MASTER_CONTEXT.md]] Section 12-15 (Ecosystems) and [[ENGINEERING_PRINCIPLES.md]] for extension principles
```

---

## Part Creation Prompts

### New Architecture Part Prompt
**Purpose**: Create a new AI-OS Architecture Part following the official template.
**Recommended Model**: Claude Opus 4.8
**Expected Output**: Complete Architecture Part document following [[PART_TEMPLATE.md]].

**Prompt Template**:
```
Create a new AI-OS Architecture Part for [PART_NAME] that follows the official [[PART_TEMPLATE.md]] structure.

Include all required sections:
1. [[#Purpose]] - Clear and concise statement of what this part covers and why it exists
2. [[#Scope]] - Explicit inclusions and exclusions with boundaries to other parts
3. [[#Audience]] - Primary and secondary audiences with specific information needs
4. [[#Architectural Context]] - Relationships to AI-OS vision, principles, and other parts
5. [[#Principles]] - Actionable architectural principles guiding decisions
6. [[#Components]] - Principal building blocks with responsibilities
7. [[#Responsibilities]] - Specific obligations of each component and the part overall
8. [[#Relationships]] - How elements relate to one another and to other parts
9. [[#Interfaces]] - Points of interaction with contracts, not implementations
10. [[#Constraints]] - Limitations affecting design and implementation choices
11. [[#Invariants]] - Conditions that must always hold true
12. [[#Runtime Behaviour]] - Execution behavior including performance and dynamic properties
13. [[#Extension Points]] - Where and how this part can be extended without core modification
14. [[#Conformance]] - How to determine correct implementation
15. [[#Security Considerations]] - Specific security risks and mitigation strategies
16. [[#Governance]] - Decision-making processes and maintenance over time
17. [[#Architecture Decisions]] - Significant decisions with rationale and alternatives
18. [[#Cross References]] - Links to related documentation avoiding duplication
19. [[#Mermaid Diagrams]] - Visualizations using Mermaid syntax
20. [[#References]] - Properly formatted sources and citations

Apply RFC 2119 terminology correctly throughout.
Reference AI-OS master documents instead of duplicating content:
- [[AI_OS_MASTER_CONTEXT.md]]
- [[ENGINEERING_PRINCIPLES.md]]
- [[ARCHITECTURE_DECISIONS.md]]
- [[IMPLEMENTATION_GUIDE.md]]
- [[VALIDATION_ARCHITECTURE.md]]
- [[GLOSSARY.md]]
- [[REPOSITORY_ECOSYSTEM.md]]

Use Mermaid diagrams where appropriate to complement textual descriptions.
Ensure technology neutrality and implementation independence.
```

### Architecture Part Update Prompt
**Purpose**: Update existing Architecture Parts while maintaining consistency.
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Updated Architecture Part that maintains conformance with template and related parts.

**Prompt Template**:
```
Update the AI-OS Architecture Part for [PART_NAME] to reflect [CHANGES_OR_UPDATES] while maintaining:

1. Conformance with [[PART_TEMPLATE.md]] structure
2. Consistency with related Architecture Parts
3. Correct RFC 2119 terminology usage
4. Proper cross-references to AI-OS master documents
5. Valid Mermaid diagrams
6. Technology neutrality and implementation independence
7. Alignment with AI-OS architectural vision and principles

Consider:
- What sections need modification based on the changes
- How updates affect relationships with other parts
- Whether principles, components, or responsibilities require updates
- If invariants or constraints need adjustment
- How extension points might be affected
- What validation approaches require updates
- Any governance process changes
- New architecture decisions that need recording
- Updated references and cross-references

Reference the existing part and related documents:
- [[AI_OS_MASTER_CONTEXT.md]] for overall context
- [[ENGINEERING_PRINCIPLES.md]] for principles
- Related Architecture Parts for consistency
- [[VALIDATION_ARCHITECTURE.md]] for validation approaches
```

---

## Review Prompts

### Architecture Review Prompt
**Purpose**: Conduct thorough architecture reviews for correctness, principles, and specification conformance.
**Recommended Model**: Claude Opus 4.8
**Expected Output**: Detailed review report with findings, recommendations, and conformance assessment.

**Prompt Template**:
```
Review the AI-OS Architecture Part for [PART_NAME] for architectural correctness, principle alignment, and specification conformance.

Check against:
1. AI-OS Architecture Specification Parts [X-Y] (reference specific parts)
2. [[ENGINEERING_PRINCIPLES.md]] engineering principles
3. [[AI_OS_MASTER_CONTEXT.md]] architectural vision and context
4. [[PART_TEMPLATE.md]] structural requirements
5. RFC 2119 terminology correctness
6. Cross-part consistency and references
7. Mermaid diagram validity and consistency
8. Extension point intentionality and discoverability
9. Security considerations adequacy
10. Governance process definition
11. Architecture decision recording with rationale
12. Conformance criteria objectivity and verifiability
13. Invariant checkability and permanence
14. Constraint identification with rationale
15. Interface contract specification (not implementation)
16. Responsibility clarity and non-overlap
17. Component architectural level appropriateness
18. Audience identification and information needs
19. Scope boundary definition and exclusions
20. Technology neutrality and implementation independence

Provide:
- Strengths of the current approach
- Areas for improvement with specific recommendations
- Risk assessment (likelihood and impact) for deviations
- Conformance level assessment (L1-L4)
- Alternative approaches considered where relevant
- Specific line/section references for findings
- Prioritized action items for remediation

Reference: [[REVIEW_TEMPLATE.md]] for review workflow and scoring methodology
```

### Consistency Review Prompt
**Purpose**: Verify cross-part consistency in terminology, references, and architectural patterns.
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Consistency report highlighting discrepancies and alignment opportunities.

**Prompt Template**:
```
Perform a consistency review of the AI-OS Architecture Part for [PART_NAME] against related Architecture Parts and AI-OS master documents.

Check for:
1. Terminology consistency with [[GLOSSARY.md]] and other parts
2. Cross-reference validity and correctness ([[link syntax]] usage)
3. Reference to AI-OS master documents instead of content duplication
4. Consistent use of architectural patterns and styles
5. Alignment of responsibilities and boundaries with related parts
6. Uniform RFC 2119 terminology application
7. Consistent Mermaid diagram notation and styling
8. Alignment of principles with [[ENGINEERING_PRINCIPLES.md]]
9. Consistent approach to extension points and versioning
10. Uniform security consideration depth and approach
11. Governance process consistency with AI-OS frameworks
12. Architecture decision recording format consistency
13. Conformance criteria objectivity and assessment methods
14. Invariant formulation and permanence
15. Constraint categorization and rationale clarity
16. Interface specification precision and binding documentation
17. Responsibility verb usage and specificity
18. Component naming and responsibility clarity
19. Audience identification specificity and actionability
20. Scope boundary precision and explicit exclusions

Provide:
- Consistency matrix showing alignment with related parts
- Specific terminology discrepancies and recommendations
- Reference validation (working links, correct targets)
- Diagram notation and styling inconsistencies
- Principle alignment assessment
- Extension point approach comparison
- Security consideration depth evaluation
- Governance process compliance check
- Decision recording format adherence
- Conformance criteria measurability
- Invariant verification approaches
- Constraint hard/soft distinction clarity
- Interface contract vs implementation confusion
- Responsibility gap/overlap identification
- Component level appropriateness
- Audience need matching
- Scope boundary precision

Reference: [[REVIEW_TEMPLATE.md]] Section 101 (Cross-Part Consistency) and related consistency criteria
```

### Publication Readiness Prompt
**Purpose**: Determine if an Architecture Part is ready for publication and distribution.
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Publication readiness assessment with checklist and blocking issues.

**Prompt Template**:
```
Assess the publication readiness of the AI-OS Architecture Part for [PART_NAME] using the [[PART_TEMPLATE.md]] Publication Quality Checklist.

Verify each checklist item:
1. [ ] All required sections are completed (purpose, scope, components, etc.)
2. [ ] Architecture Author Checklist items are addressed
3. [ ] Content is technology-neutral and implementation-independent
4. [ ] RFC 2119 terminology is used correctly and consistently
5. [ ] All Mermaid diagrams are valid, properly formatted, and add value
6. [ ] Cross references to AI-OS master documents are used instead of duplicating content
7. [ ] Internal references use [[link syntax]] format
8. [ ] External references are properly formatted with access dates
9. [ ] Content is clear, concise, and free of implementation details
10. [ ] Diagrams accurately reflect textual content
11. [ ] Terminology is consistent with [[GLOSSARY.md]] and other AI-OS documents
12. [ ] Security considerations are adequately addressed
13. [ ] Governance processes are defined where relevant
14. [ ] Architecture decisions are recorded with rationale
15. [ ] Conformance criteria are objective and verifiable
16. [ ] Invariants are checkable and always true
17. [ ] Constraints are identified with rationale
18. [ ] Extension points are intentional and discoverable
19. [ ] Relationships are well-defined and explained
20. [ ] Interfaces specify contracts, not implementations
21. [ ] Responsibilities are clear and non-overlapping
22. [ ] Principles are actionable and decision-guiding
23. [ ] Architectural context shows relationships to other parts
24. [ ] Audience is properly identified with specific information needs
25. [ ] Scope is well-defined with explicit inclusions/exclusions
26. [ ] Purpose is clear and concise
27. [ ] Template usage instructions have been followed

Provide:
- Completed checklist with any unchecked items
- Blocking issues that must be resolved before publication
- Recommendations for addressing each unchecked item
- Estimated effort for remediation
- Publication recommendation (approve, approve with revisions, require major revisions)
- Reference to specific sections needing attention
- Cross-reference validation results
- Mermaid diagram validation status
- RFC 2119 terminology usage report
- Technology neutrality assessment
```

---

## Improvement Prompts

### Architecture Improvement Prompt
**Purpose**: Identify and suggest improvements to existing AI-OS Architecture Parts.
**Recommended Model**: Claude Opus 4.8
**Expected Output**: Improvement analysis with specific, actionable recommendations.

**Prompt Template**:
```
Analyze the AI-OS Architecture Part for [PART_NAME] to identify improvement opportunities that enhance:

1. Alignment with AI-OS architectural vision and principles
2. Conformance with specification requirements
3. Clarity, completeness, and usability
4. Consistency with related parts and master documents
5. Technical accuracy and relevance
6. Extension point effectiveness and discoverability
7. Security consideration adequacy
8. Governance process definition
9. Decision recording quality and traceability
10. Validation approach objectivity and practicability

Consider:
- Outdated references or broken links
- Ambiguous or unclear sections
- Inconsistent terminology with related parts
- Missing or insufficient diagram explanations
- RFC 2119 terminology misuse or inconsistency
- Technology-specific details that should be abstracted
- Implementation details inappropriately included
- Ambiguous scope boundaries
- Inadequate audience identification
- Missing or weak architectural principles
- Unclear component responsibilities
- Poorly defined relationships or interfaces
- Insufficient constraint identification
- Non-checkable invariants
- Undiscoverable or non-intentional extension points
- Subjective conformance criteria
- Inadequate security considerations
- Undefined governance processes
- Poorly documented architecture decisions
- Missing or invalid cross-references
- Diagram inconsistencies**.: Requires major revisions and re-review
328	- [ ] Not approved - requires complete rewrite
329	
330	## Re-review Required
331	- [ ] Yes - Specify date or version for re-review: ___________________
332	- [ ] No
333	
334	## Freeze Approved
335	- [ ] Yes - Document is frozen and should not be changed without formal change control process
336	- [ ] No
337	
338	## Publication Checklist
339	[ ] Document version updated
340	[ ] Change history recorded
341	[ ] All review comments addressed
342	[ ] Document spell-checked and grammar-checked
343	[ ] Links and references verified
344	[ ] Diagrams validated and rendered correctly
345	[ ] Mermaid syntax validated
346	[ ] RFC 2119 keywords used correctly
347	[ ] Technology neutrality verified
348	[ ] Runtime independence validated
349	[ ] Implementation independence validated
350	[ ] Architecture ownership validated
351	[ ] Cross-reference validation completed
352	[ ] Boundary definitions verified
353	[ ] Terminology consistency checked
354	[ ] Conformance to AI-OS Engineering Principles verified
355	[ ] Document formatted according to project standards
356	[ ] Ready for distribution to stakeholders
357	[ ] Publication approval obtained
358	
359	## Freeze Checklist
360	[ ] Formal change control process established
361	[ ] Change request procedure documented
362	[ ] Versioning strategy defined
363	[ ] Review schedule for frozen document established
364	[ ] Stakeholders notified of freeze status
365	[ ] Archive location specified
366	[ ] Backup procedure established
367	[ ] Freeze date recorded: ___________________
368	[ ] Freeze approved by: ___________________
369	[ ] Architecture Review Board approval obtained
370	[ ] Relevant Council notifications sent
371	[ ] Impact analysis completed for dependent documents
372	[ ] Migration plan created for any breaking changes
373	[ ] Deprecation timeline established if applicable
374	
375	---
376	*This review template is licensed under the project's documentation license.*

---

## ADR Prompts

**Purpose**: Create Architecture Decision Records following AI-OS ADR format.
**Recommended Model**: Claude Opus 4.8
**Expected Output**: Complete ADR document following [[ADR_TEMPLATE.md]].

### New ADR Prompt
```
Create an Architecture Decision Record for [DECISION_TITLE] that follows the official [[ADR_TEMPLATE.md]] structure.

Include all required sections:
1. **Decision Lifecycle** - Current state and possible transitions
2. **Purpose** - When an ADR should be created
3. **Decision Traceability** - Origin, motivation, related requirements, principles, parts, knowledge, and research
4. **Context** - Current state necessitating the decision
5. **Problem Statement** - Clear, structured problem description
6. **Decision Classification** - Primary categories and cross-cutting concerns
7. **Decision** - Clear and concise statement of the decision made
8. **Alternatives Considered** - Alternative approaches and rejection reasons
9. **Consequences** - Positive and negative impacts, trade-offs made
10. **Risks** - Architecture, engineering, operational, and migration risks with mitigations
11. **Architecture Impact** - Which AI-OS parts are affected and how
12. **Conformance Impact** - Effect on compliance with standards, regulations, policies
13. **Migration Strategy** - How to transition from current state to new architecture
14. **Validation** - Criteria, types, methods, and success metrics for validation
15. **Approval and Governance** - Approval process and ongoing governance
16. **References** - Related documents, standards, or resources

Apply RFC 2119 terminology correctly throughout.
Reference AI-OS master documents instead of duplicating content:
- [[AI_OS_MASTER_CONTEXT.md]]
- [[ENGINEERING_PRINCIPLES.md]]
- [[ARCHITECTURE_DECISIONS.md]] (for global decisions)
- [[IMPLEMENTATION_GUIDE.md]]
- [[VALIDATION_ARCHITECTURE.md]]
- [[GLOSSARY.md]]
- [[REPOSITORY_ECOSYSTEM.md]]
- [[COUNCILS.md]]

Use Mermaid diagrams where appropriate (Decision Lifecycle, Impact Analysis, Migration Strategy).
Ensure the decision addresses a significant architectural question with lasting impact.
```

### ADR Update Prompt
```
Update the Architecture Decision Record [ADR_NUMBER] for [DECISION_TITLE] to reflect [CHANGES_OR_UPDATES] while maintaining:

1. Conformance with [[ADR_TEMPLATE.md]] structure
2. Correct RFC 2119 terminology usage
3. Proper cross-references to AI-OS master documents
4. Alignment with AI-OS architectural vision and principles
5. Updated risk assessments and mitigation strategies
6. Current validation approaches and success metrics
7. Updated approval and governance information
8. Current references and cross-references

Consider:
- Whether the decision status has changed (Draft → Review → Approved → etc.)
- If new alternatives should be considered or previous rejections updated
- Whether consequences or risks have evolved
- If architecture impact or conformance impact requires updates
- Whether migration strategy needs adjustment
- If validation criteria or methods require updates
- Any new references or related documents
- Updated approval governance information

Reference: [[ADR_TEMPLATE.md]] for structure and [[REVIEW_TEMPLATE.md]] for validation approaches
```

---

## Publication Prompts

**Purpose**: Prepare AI-OS Architecture Parts for publication and distribution.
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Publication-ready package with all necessary artifacts.

### Publication Preparation Prompt
```
Prepare the AI-OS Architecture Part [PART_NAME] for publication by ensuring:

1. All sections are complete and properly formatted
2. RFC 2119 terminology is used correctly and consistently
3. All Mermaid diagrams are valid and properly formatted
4. Cross-references use [[link syntax]] and point to current versions
5. Internal references avoid duplicating content from master documents
6. External references are properly formatted with access dates
7. Content is technology-neutral and implementation-independent
8. Security considerations are adequately addressed
9. Governance processes are clearly defined
10. Architecture decisions are recorded with rationale
11. Conformance criteria are objective and verifiable
12. Invariants are checkable and always true
13. Constraints are identified with rationale
14. Extension points are intentional and discoverable
15. Relationships are well-defined and explained
16. Interfaces specify contracts, not implementations
17. Responsibilities are clear and non-overlapping
18. Principles are actionable and decision-guiding
19. Architectural context shows relationships to other parts
20. Audience is properly identified with specific information needs
21. Scope is well-defined with explicit inclusions/exclusions
22. Purpose is clear and concise

Provide:
- Publication readiness checklist (based on [[PART_TEMPLATE.md]])
- List of any blocking issues that must be resolved
- Recommended publication format (PDF, HTML, Markdown)
- Version number recommendation
- Change log entry for this publication
- Distribution recommendations (internal, external, public)
- Archive and backup instructions
- Reference validation report
- Mermaid diagram validation status
- RFC 2119 terminology audit
- Technology neutrality assessment

Reference: [[PART_TEMPLATE.md]] Publication Quality Checklist and Freeze Checklist
```

### Publication Announcement Prompt
```
Create a publication announcement for the AI-OS Architecture Part [PART_NAME] version [VERSION_NUMBER].

Include:
1. Publication title and version number
2. Publication date and effective date
3. Brief overview of what the part covers and its significance
4. Key changes or updates from previous version (if applicable)
5. Intended audience and how they should use the document
6. Where to access the published document
7. Related documents or parts that complement this publication
8. Feedback mechanisms and contact information
9. Any known limitations or caveats
10. Next planned update or review date

Reference: [[AI_OS_MASTER_CONTEXT.md]] for overall context and [[ENGINEERING_PRINCIPLES.md]] for principles
```

---

## Freeze Prompts

**Purpose**: Prepare AI-OS Architecture Parts for freezing (making them immutable without formal process).
**Recommended Model**: Claude Sonnet 5
**Expected Output**: Freeze-ready package with change control processes established.

### Freeze Preparation Prompt
```
Prepare the AI-OS Architecture Part [PART_NAME] for freezing by ensuring:

1. Formal change control process is established and documented
2. Change request procedure is clearly defined
3. Versioning strategy is specified and documented
4. Review schedule for frozen document is established
5. Stakeholders have been notified of freeze status
6. Archive location is specified and accessible
7. Backup procedure is established and tested
8. Freeze date is recorded and documented
9. Freeze approval has been obtained from Architecture Review Board
10. Relevant Council notifications have been sent
11. Impact analysis for dependent documents has been completed
12. Migration plan has been created for any breaking changes
13. Deprecation timeline has been established if applicable
14. All publication requirements are met (see Publication Prompts)
15. Document is in its final form and ready for long-term stability

Provide:
- Freeze readiness checklist (based on [[PART_TEMPLATE.md]] Freeze Checklist)
- Change control process documentation
- Versioning strategy document
- Stakeholder notification plan
- Archive and backup procedures
- Impact analysis report
- Migration plan (if needed)
- Deprecation timeline (if applicable)
- Freeze approval documentation
- Council notification records
- Reference to related frozen parts
- Timeline for next review or potential unfreeze

Reference: [[PART_TEMPLATE.md]] Freeze Checklist and [[AI_OS_MASTER_CONTEXT.md]] for governance processes
```

### Freeze Maintenance Prompt
```
Establish maintenance procedures for the frozen AI-OS Architecture Part [PART_NAME] version [VERSION_NUMBER].

Include:
1. Regular review schedule and procedures
2. Change request handling process
3. Emergency update procedures (if applicable)
4. Version tracking and documentation
5. Stakeholder communication plan
6. Archive integrity verification
7. Backup schedule and verification
8. Deprecation process (if timeline established)
9. Potential unfreeze conditions and procedures
10. Related parts impact monitoring

Reference: [[AI_OS_MASTER_CONTEXT.md]] Section 16 (Governance) and [[ENGINEERING_PRINCIPLES.md]] for governance principles
```

---

## Best Practices

AI-OS prompt engineering follows these established best practices:

### 1. **Context-Rich Prompts**
Always provide sufficient context in your prompts including:
- Relevant AI-OS specification parts
- Architectural vision and principles
- Related ecosystem considerations (Skills, MCP, Repository)
- Governance requirements and constraints
- Intended audience and use case

### 2. **Iterative Refinement**
Treat prompts as starting points for conversation:
- Begin with broad exploration prompts
- Use initial outputs to refine subsequent prompts
- Incorporate feedback from architecture reviews
- Evolve prompts based on lessons learned

### 3. **Validation-First Approach**
Include verification mechanisms in all architectural prompts:
- Conformance criteria objectivity and measurability
- Reference validation (working links, correct targets)
- Diagram validity and consistency checking
- RFC 2119 terminology usage verification
- Technology neutrality and implementation independence checks

### 4. **Master Document Referencing**
Always reference AI-OS master documents instead of duplicating content:
- Use [[link syntax]] for internal references
- Reference [[AI_OS_MASTER_CONTEXT.md]] for overall context
- Reference [[ENGINEERING_PRINCIPLES.md]] for engineering principles
- Reference [[ARCHITECTURE_DECISIONS.md]] for global decisions
- Reference master documents for principles, validation, governance, etc.
- Avoid copying content that should be referenced from core documents

### 5. **RFC 2119 Precision**
Use RFC 2119 terminology with precision and consistency:
- **MUST** for absolute requirements
- **SHOULD** for strong recommendations
- **MAY** for optional features or permissions
- **MUST NOT** for absolute prohibitions
- **SHOULD NOT** for recommendations against certain approaches
- Apply consistently throughout the document
- Provide clear rationale when deviating from recommendations

### 6. **Diagram Excellence**
Create diagrams that enhance rather than duplicate textual content:
- Use Mermaid syntax consistently
- Ensure diagrams accurately reflect textual descriptions
- Keep diagrams at appropriate level of detail (architectural, not implementation)
- Provide clear captions and explanations
- Validate diagram syntax and rendering
- Consider accessibility (labels, contrast, alternatives)
- Use diagrams to show relationships, flows, and dependencies

### 7. **Audience-Centric Design**
Always design with the intended audience in mind:
- Identify primary and secondary audiences
- Specify information needs for each audience type
- Adjust technical depth and terminology accordingly
- Consider different use cases (design, implementation, operations)
- Address both consuming and contributing audiences
- Make information findable and accessible to each audience

### 8. **Traceability and Tracking**
Ensure all architectural decisions and content are traceable:
- Document origins, motivations, and related artifacts
- Link to requirements, principles, and constraints
- Record decision makers, dates, and revisit conditions
- Maintain clear cross-references and relationships
- Provide evidence and validation approaches
- Enable historical tracking and audit trails

### 9. **Ecosystem Sensitivity**
Consider impact on and from AI-OS ecosystems:
- Skills ecosystem compatibility and extension points
- MCP ecosystem integration and transport mechanisms
- Repository ecosystem sharing and reuse potential
- Council governance processes and decision-making
- Agency oversight and audit trail requirements
- Extension point discoverability and usability
- Versioning and compatibility strategies

### 10. **Continuous Improvement**
Maintain prompts as living documents:
- Regularly review and update based on usage
- Incorporate lessons learned from architecture reviews
- Adapt to evolving AI-OS specification and principles
- Remove obsolete prompts and add new categories
- Refine templates based on effectiveness
- Stay current with AI-OS engineering practices

---

## Prompt Lifecycle

AI-OS prompts follow this lifecycle to ensure effectiveness and relevance:

### 1. **Creation**
- Identify need for new prompt category or template
- Research existing AI-OS documentation and conventions
- Draft prompt following established patterns and principles
- Reference relevant master documents and specifications
- Apply prompt philosophy and best practices
- Create reusable templates where appropriate

### 2. **Review**
- Submit prompt for architecture review
- Check conformance with prompt philosophy and best practices
- Validate against AI-OS specification parts and principles
- Verify technology neutrality and implementation independence
- Check RFC 2119 terminology usage
- Ensure proper master document referencing
- Validate any included diagrams or templates
- Incorporate feedback from reviewers

### 3. **Publication**
- Publish prompt to appropriate location in prompts/ directory
- Update table of contents and cross-references
- Ensure proper formatting and readability
- Add to prompt lifecycle tracking
- Notify relevant stakeholders of availability
- Archive previous versions if applicable

### 4. **Usage and Monitoring**
- Track usage patterns and effectiveness
- Collect feedback from users and reviewers
- Monitor for outdated references or broken links
- Watch for changes in AI-OS specification that affect prompt
- Identify opportunities for improvement or refinement
- Note any inconsistencies with related prompts or parts

### 5. **Revision**
- Update prompt based on usage feedback and monitoring
- Incorporate new AI-OS specification changes
- Refine based on lessons learned from application
- Update references to current master document versions
- Improve clarity, completeness, and usability
- Address any identified issues or gaps
- Maintain backward compatibility where appropriate

### 6. **Archiving**
- Archive obsolete prompts that are no longer relevant
- Maintain historical versions for reference and audit
- Document reasons for obsolescence or replacement
- Ensure archived prompts remain accessible for reference
- Update cross-references to point to current versions
- Maintain prompt lifecycle documentation

---

## Cross References

AI-OS prompt engineering relies on and references these core documents:

### Master Context Documents
- [[AI_OS_MASTER_CONTEXT.md]] - Overall AI-OS architectural vision, principles, and system overview
- [[ENGINEERING_PRINCIPLES.md]] - Foundational engineering principles guiding all AI-OS work
- [[ARCHITECTURE_DECISIONS.md]] - Register of global architectural decisions and their rationales
- [[IMPLEMENTATION_GUIDE.md]] - Detailed implementation guidelines and best practices
- [[VALIDATION_ARCHITECTURE.md]] - Comprehensive validation framework and approaches
- [[GLOSSARY.md]] - Shared terminology, definitions, and acronyms
- [[REPOSITORY_ECOSYSTEM.md]] - Structure and organization of AI-OS software repositories
- [[COUNCILS.md]] - Description of AI-OS governance councils and their responsibilities
- [[MEMORY_ARCHITECTURE.md]] - Five-tier memory system architecture
- [[MCP_ECOSYSTEM.md]] - Model Context Protocol ecosystem specifications
- [[SKILLS_ECOSYSTEM.md]] - Reusable AI capability packages and frameworks

### Architecture Parts (Parts 1-15)
Always reference specific AI-OS Architecture Parts by their official titles when creating prompts:
- [[Part 1: Hermes Kernel]] - Orchestration core with 4 Components and 9 Managers
- [[Part 2: Core Managers]] - Memory, ModelRouter, ToolManager, Storage, Context, Agent, Retry, Checkpoint, RootCause
- [[Part 3: Engineering Services]] - Planning, Coding, Review, Testing, Deployment, Operations, Learning, Memory services
- [[Part 4: Service Framework]] - BaseService contract, lifecycle management, event-driven communication
- [[Part 5: Configuration System]] - Four-layer merge configuration with immutability after INITIALIZING
- [[Part 6: Event System]] - EventBus, schema versioning, correlation/causation, routing mechanisms
- [[Part 7: AI Agency and Governance]] - Council mechanisms, AI Agency service, audit trails, permission sandboxing
- [[Part 8: Memory Architecture]] - Working, Claude, Engineering Intelligence, Obsidian, Graphify memory tiers
- [[Part 9: Skills Ecosystem]] - Discovery, versioning, sandboxing, composition, governance, development kit
- [[Part 10: MCP Ecosystem]] - Transports, capabilities, security, state management, discovery, tool certification
- [[Part 11: Repository Ecosystem]] - Workflow templates, component libraries, reference architectures, best practices
- [[Part 12: Observability & Telemetry]] - Metrics, tracing, logging, health checks, alerting, monitoring
- [[Part 13: Fault Tolerance & Recovery]] - Retry mechanisms, checkpointing, failure classification, recovery routing
- [[Part 14: Goal-Driven Execution & Agentic Systems]] - Goal-driven engine, autonomous behavior, self-looping, validation-first execution
- [[Part 15: Validation Architecture]] - Pre-, during-, and post-execution validation, mechanisms, checklists, scripts

### Related Project Knowledge
- [[ROADMAP.md]] - Current status, near-term, mid-term, and long-term plans for AI-OS evolution
- [[VERSION_HISTORY.md]] - Document version history and change tracking
- [[meeting-notes/PROJECT_LOG.md]] - Project meeting notes and decisions
- [[diagrams/]] - Architectural diagrams using Mermaid syntax (OVERALL_ARCHITECTURE.md, PART_FLOW.md, etc.)
- [[templates/]] - Official templates for ADRs, Architecture Parts, Reviews, and other documents
- [[research/]] - Future features, research papers, GitHub repositories, and ongoing investigations

### External Standards and References
When creating prompts, consider referencing these external sources where appropriate:
- RFC 2119 - Key words for use in RFCs to Indicate Requirement Levels
- TOGAF, Zachman, or other architecture frameworks (for reference, not prescription)
- ISO/IEC/IEEE standards relevant to system and software engineering
- OWASP, NIST, ISO 27001 for security considerations
- Industry-specific standards as relevant to the architectural domain
- Academic research and established best practices in software architecture

**Important**: When referencing external sources, always:
- Provide access dates for online resources
- Include version information for specifications and standards
- Distinguish between AI-OS internal documents and external sources
- Avoid duplicating content that should be referenced from AI-OS master documents
- Use proper citation formats (APA, IEEE, ACM, etc.) for external references

---

## Reusable Prompt Templates

These are standardized prompt fragments that can be reused across different prompt categories:

### Master Document Reference Template
```
Reference AI-OS master documents instead of duplicating content:
- [[AI_OS_MASTER_CONTEXT.md]] for overall context and vision
- [[ENGINEERING_PRINCIPLES.md]] for engineering principles and guidelines
- [[ARCHITECTURE_DECISIONS.md]] for global architectural decisions
- [[IMPLEMENTATION_GUIDE.md]] for implementation considerations and patterns
- [[VALIDATION_ARCHITECTURE.md]] for validation approaches and methodologies
- [[GLOSSARY.md]] for shared terminology and definitions
- [[REPOSITORY_ECOSYSTEM.md]] for repository structure and organization
```

### RFC 2119 Usage Template
```
Apply RFC 2119 terminology correctly throughout:
- Use "MUST" for absolute requirements that are essential to conformance
- Use "SHOULD" for strong recommendations that should be followed unless justified
- Use "MAY" for optional features or permissions that may be included
- Use "MUST NOT" for absolute prohibitions that must not be violated
- Use "SHOULD NOT" for recommendations against certain approaches that may have exceptions
- Provide clear rationale when deviating from SHOULD/SHOULD NOT recommendations
```

### Diagram Specification Template
```
Use Mermaid diagrams where appropriate to complement textual descriptions:
- Ensure diagrams accurately reflect the architectural concepts described
- Use consistent notation and styling across all diagrams in the document
- Provide clear captions or explanations for each diagram (what it shows and why it matters)
- Validate diagram syntax and rendering
- Consider accessibility (labels, contrast, alternative text descriptions)
- Keep diagrams at appropriate architectural level (not implementation-detail)
```

### Technology Neutrality Template
```
Ensure technology neutrality and implementation independence:
- Avoid prescribing specific technologies unless architecturally necessary
- Focus on contracts, interfaces, and principles rather than implementations
- Separate interface specifications from implementation details
- Enable multiple conforming implementations through abstraction
- Consider technology evolution and compatibility over time
```

### Validation Mindset Template
```
Include mechanisms for verifying correctness and quality:
- Define objective, measurable conformance criteria
- Specify clear assessment methods for each criterion
- Consider both functional and non-functional validation aspects
- Include validation approaches for checking correctness
- Provide evidence requirements and validation procedures
- Consider automation potential for conformance checking
- Document required tools, environments, or test procedures
```

### Audience Specification Template
```
Identify the intended readers and their specific information needs:
- Primary audience: [SPECIFIC_ROLE_OR_TYPE] who need [SPECIFIC_INFORMATION]
- Secondary audience: [SPECIFIC_ROLE_OR_TYPE] who might refer to [SPECIFIC_INFORMATION]
- Different technical levels accommodated where relevant
- Both consuming and contributing audiences addressed
- Geographic or organizational distribution considered if relevant
- Information needs match actual job responsibilities and decision-making authority
```

### Scope Boundary Template
```
Define clear boundaries with explicit inclusions and exclusions:
- In scope: [CLEAR_LIST_OF_INCLUDED_ELEMENTS_OR_ASPECTS]
- Out of scope: [CLEAR_LIST_OF_EXCLUDED_ELEMENTS_OR_ASPECTS]
- Boundaries with other architecture parts explicitly stated
- Assumptions about operating environment documented and justified
- Dependencies on other parts or external systems identified
- Phases or versions covered specified (if applicable)
- Consider temporal aspects and geographical/contextual boundaries
```

### Principle Formulation Template
```
Establish actionable architectural principles that drive decisions:
- Focus on enduring truths, not temporary preferences or trends
- Make principles actionable and decision-guiding (help choose between alternatives)
- Avoid platitudes or vague statements - each principle should have clear implications
- Reference where principles come from (industry standards, lessons learned, AI-OS vision)
- Keep principles concise but meaningful (one sentence ideal)
- Ensure principles are mutually reinforcing, not conflicting
- Consider both technical and organizational principles
- Make sure principles scale with the system and team size
- Connect principles to AI-OS architectural vision and ENGINEERING_PRINCIPLES.md
```

### Component Specification Template
```
Identify key structural elements and their responsibilities:
- Use clear, meaningful component names that reflect their responsibility
- Focus on responsibilities, not implementations (what it does, not how)
- Be consistent with naming conventions used elsewhere in AI-OS
- Indicate if components are devices, modules, services, processes, etc.
- Specify component granularity appropriately for architectural level
- Note any existing components being reused vs. new development
- Consider both runtime and design-time component views
- Document any component patterns or styles used (layers, pipes, etc.)
- Specify technology choices or constraints for each component (if decided)
- Indicate version or maturity level of components (if applicable)
- Document dependencies between components
- Specify reuse level (internal, external, new development)
```

These templates ensure consistency, reduce duplication, and maintain alignment with AI-OS architectural standards across all prompts.