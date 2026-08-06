# Architecture Part Template

This document defines the official authoring template for AI-OS Architecture Parts. Every Architecture Part should follow this structure, adapting it to the specific subsystem being described while maintaining consistency across the architecture documentation.

*This template defines HOW to write architecture documents, NOT the architecture itself.*

---

## Architecture Author Checklist

Before beginning authoring, verify you have:
- [ ] Access to AI-OS architectural vision and principles documents
- [ ] Understanding of the subsystem boundaries
- [ ] Knowledge of intended audience and their needs
- [ ] Familiarity with Mermaid syntax for diagrams
- [ ] Understanding of RFC 2119 keyword usage (MUST, SHOULD, MAY, etc.)

As you complete each section, verify:
- [ ] Purpose is clear and concise
- [ ] Scope is well-defined with explicit inclusions/exclusions
- [ ] Audience is properly identified
- [ ] Architectural context shows relationships to other parts
- [ ] Principles are actionable and decision-guiding
- [ ] Components are properly identified with responsibilities
- [ ] Responsibilities are clear and non-overlapping
- [ ] Relationships are well-defined and documented
- [ ] Interfaces specify contracts, not implementations
- [ ] Constraints are identified with rationale
- [ ] Invariants are checkable and always true
- [ ] Runtime behaviour describes measurable characteristics
- [ ] Extension points are intentional and discoverable
- [ ] Conformance criteria are objective and verifiable
- [ ] Security considerations address specific threats
- [ ] Governance processes are clear and actionable
- [ ] Architecture decisions are recorded with rationale
- [ ] Cross references are verified and current
- [ ] Mermaid diagrams are valid and properly formatted
- [ ] RFC 2119 terminology is used correctly

Final publication checklist:
- [ ] Architecture review completed
- [ ] Consistency review passed
- [ ] Diagram validation completed
- [ ] Cross reference validation completed
- [ ] Terminology validation (RFC 2119) completed
- [ ] Ownership and maintenance defined
- [ ] Publication approval obtained
- [ ] Freeze approval obtained

---

# Title

## Purpose
Clearly and concisely states what this part of the architecture covers and why it exists. Should answer: "What subsystem or capability does this part describe, and why is it important to AI-OS?"

## Expected contents
- One sentence describing the architecture part
- Brief statement of its significance to the overall AI-OS system
- No technical details - save those for later sections

## Writing guidance
- Use active voice: "This part describes..." not "This part is describing..."
- Keep under 2 sentences
- Avoid implementation specifics
- Focus on business/architectural value
- Make it understandable to all audience types
- Align with AI-OS naming conventions

## Common mistakes
- Writing overly detailed descriptions
- Including technical specifications that belong in Components or Principles
- Making it sound like a feature list rather than an architectural description
- Exceeding 2 sentences
- Using jargon or acronyms without explanation
- Making it too generic to be useful
- Including implementation details

## Review expectations
- Reviewers should verify the title accurately reflects the part's scope
- Title should be searchable and discoverable in documentation
- Must align with other AI-OS part titles for consistency

## Quality indicators
- Clear and unambiguous meaning
- Appropriate level of specificity (not too broad, not too narrow)
- Consistent with AI-OS architectural naming patterns
- Understandable to newcomers to the project

## Completion criteria
- Single sentence ending with a period
- No technical implementation details
- Clearly states the "what" and "why" of the part
- Passes review by at least one architect

## Formatting conventions
- Use sentence case for the title (only first word and proper nouns capitalized)
- End with a period
- No markdown formatting in this section

## Diagram recommendations
N/A - this is a textual description section

## RFC 2119 guidance
Use "SHOULD" when describing the purpose - it SHOULD clearly state what the part covers and why it matters.

---

# Purpose

## Purpose
Defines the specific goals, objectives, and problems this architecture part addresses. Should answer: "What specific architectural problems does this part solve, and what goals does it aim to achieve?"

## Expected contents
- List of specific objectives (3-5 items typically)
- Problems being solved or avoided
- Goals that this part helps achieve for AI-OS
- Success criteria or desired outcomes
- Non-functional requirements addressed (performance, security, scalability, etc.)
- Stakeholder needs being met

## Writing guidance
- Use bullet points for clarity
- Start each objective with a strong verb (ensure, enable, prevent, minimize, etc.)
- Focus on architectural qualities (scalability, maintainability, extensibility, performance, security, etc.)
- Reference non-functional requirements where applicable
- Make objectives measurable or verifiable where possible
- Align with AI-OS architectural vision and principles
- Keep objectives at the right level of abstraction (architectural, not implementation)

## Common mistakes
- Listing features instead of objectives
- Being too vague ("make it better", "improve performance")
- Including implementation details (specific technologies, algorithms)
- Making objectives unmeasurable or untestable
- Having too many objectives (>7)
- Confusing goals with principles or constraints
- Including objectives that belong to other parts
- Writing objectives that are too broad or too narrow

## Review expectations
- Reviewers should verify each objective is architectural in nature
- Objectives should be traceable to stakeholder needs or business goals
- Must be distinguishable from implementation details
- Should align with AI-OS architectural vision

## Quality indicators
- Each objective starts with a strong verb
- Objectives are mutually exclusive and collectively comprehensive
- Non-functional requirements are addressed where relevant
- Objectives are achievable and realistic
- Language is clear and unambiguous

## Completion criteria
- 3-5 well-defined objectives (can be fewer for simple parts)
- Each objective is one sentence or less
- No implementation specifics included
- Objectives are verifiable or measurable in principle
- Passes review by at least one architect
- Aligns with AI-OS architectural vision documentation

## Diagram recommendations
Consider a simple goal diagram showing how objectives relate to each other or to higher-level goals
A stakeholder-objective matrix can help clarify who cares about which objectives
Use flowchart to show how objectives lead to architectural decisions

## RFC 2119 guidance
Use "MUST" for critical objectives that are essential to the architecture's validity (without which the part fails its core purpose), "SHOULD" for important but not absolute objectives (degradation acceptable if not met), and "MAY" for optional enhancements (nice-to-have features).

---

# Scope

## Purpose
Defines the boundaries of what this architecture part covers and explicitly states what is out of scope. Should answer: "What is included in this part's domain, and what is deliberately excluded?"

## Expected contents
- In-scope items: components, features, capabilities covered
- Out-of-scope items: explicitly excluded areas
- Boundaries with other architecture parts
- Any assumptions about the operating environment
- Dependencies on other parts or external systems
- Phases or versions covered (if applicable)
- Geographical or operational boundaries (if applicable)

## Writing guidance
- Be precise and explicit about boundaries
- Use "In scope:" and "Out of scope:" headings for clarity
- Reference related architecture parts when defining boundaries
- State assumptions clearly
- Consider temporal aspects (what versions/time periods are covered)
- Be realistic about what can be achieved
- Distinguish between current scope and future scope

## Common mistakes
- Being too vague about boundaries
- Forgetting to state what's out of scope
- Making scope too broad or too narrow
- Not updating scope when related parts change
- Using ambiguous language
- Including implementation details in scope definition
- Forgetting to mention dependencies
- Not clarifying what is explicitly excluded
- Being inconsistent with related parts' scopes

## Review expectations
- Reviewers should verify scope is clearly defined and bounded
- Should check that scope aligns with related parts
- Must verify that out-of-scope items are appropriate exclusions
- Should ensure assumptions are documented and reasonable
- Should confirm dependencies are identified

## Quality indicators
- Clear delineation between in-scope and out-of-scope items
- Boundaries are explicit and unambiguous
- Dependencies are clearly identified
- Assumptions are stated and justified
- Scope is achievable within stated constraints
- Consistent with related architecture parts

## Completion criteria
- Clear "In scope" and "Out of scope" sections
- Each item is concise and unambiguous
- Boundaries with other parts are explicitly stated
- Assumptions about operating environment are documented
- Dependencies on other systems or parts are identified
- Passes review by at least one architect

## Formatting conventions
- Use clear section headers: "In scope:" and "Out of scope:"
- Use bullet points for lists
- Keep each item concise
- Consider using a scope matrix for complex boundaries
- For temporal scope, indicate versions or time periods
- For geographical scope, indicate regions or deployment contexts

## Diagram recommendations
Context diagram showing this part in relation to other parts, or a boundary diagram with in/out labels
Use a Venn diagram to show overlap with related parts
Consider a timeline diagram if scope has temporal aspects
Use a deployment diagram to show geographical or operational boundaries

## RFC 2119 guidance
Use "MUST" for defining hard boundaries - elements that MUST be included or MUST be excluded.
Use "SHOULD" for recommended inclusions or exclusions that have strong justification but may have exceptions.
Use "MAY" for optional inclusions that depend on specific use cases or configurations.

---

# Audience

## Purpose
Identifies the intended readers of this document and their varying needs. Should answer: "Who needs to read this, and what do they need to get from it?"

## Expected contents
- Primary audience (who will use this most)
- Secondary audiences (who might refer to it)
- Specific needs or questions each audience has
- How different audiences should use different sections
- Different technical levels and their information needs
- Decision-making authority and information requirements
- Geographic or organizational distribution (if relevant)

## Writing guidance
- Be specific about roles, not just generic titles (e.g., "Platform Engineers" not "technical staff")
- Consider different technical levels (expert, practitioner, newcomer)
- Think about what each audience needs to decide or act upon
- Reference how this document supports their work
- Consider information needed for different lifecycle phases (design, implementation, operations)
- Address both consuming and contributing audiences
- Differentiate between read-only and read-write audiences

## Common mistakes
- Saying "everyone" or "all stakeholders"
- Being too generic ("technical people", "engineers")
- Not considering different use cases or access patterns
- Forgetting operational/support audiences (SRE, helpdesk, etc.)
- Overlooking management or decision-making audiences
- Not distinguishing between consumers and contributors
- Being inconsistent with terminology used in other parts
- Forgetting temporary audiences (contractors, auditors, etc.)
- Not considering internationalization needs

## Review expectations
- Reviewers should verify audience identification is specific and actionable
- Should check that information needs match audience responsibilities
- Must verify that different technical levels are accommodated
- Should ensure operational audiences are not overlooked
- Should confirm that decision-makers get appropriate summary information

## Quality indicators
- Audiences are specific roles, not generic categories
- Information needs match actual job responsibilities
- Different technical levels are considered appropriately
- Both consuming and contributing audiences are addressed
- Geographic/distributed team considerations are included (if relevant)
- Information is findable and accessible to each audience type

## Completion criteria
- Primary and secondary audiences clearly identified
- Specific information needs documented for each audience
- Guidance on how each audience should use different sections
- Different technical levels accommodated where relevant
- Passes review by at least one architect and one target audience member

## Formatting conventions
- Use bullet points or a simple table
- List audience types with their primary concerns
- Keep descriptions brief but meaningful
- Consider using a RACI-like matrix for complex audience interactions
- Indicate mandatory vs. optional sections for each audience
- Specify technical depth required for each audience

## Diagram recommendations
N/A - this is typically textual, but consider:
- Audience matrix showing roles vs. information needs
- Diagram showing information flow to different audience types
- Swimlane diagram showing who uses what parts of the document
- Decision flow diagram showing who makes what decisions based on this document

## RFC 2119 guidance
Use "SHOULD" when describing what audiences SHOULD get from the document - different audiences SHOULD be able to extract specific information relevant to their role and responsibilities.

---

# Architectural Context

## Purpose
Situates this architecture part within the larger AI-OS system, showing how it relates to other parts and the overall architecture vision. Should answer: "How does this part fit into the bigger picture of AI-OS?"

## Expected contents
- Relationship to AI-OS architectural vision and principles
- Position within the overall architecture (layers, tiers, etc.)
- How it enables or is enabled by other parts
- Reference to relevant architecture parts (with links)
- Any dependencies on external systems or standards
- Data flows to and from other parts
- Control flow and dependencies
- Shared concepts or vocabulary with other parts
- Impact on or from architectural drivers (scalability, performance, etc.)

## Writing guidance
- Show, don't just tell - use references and connections
- Reference other parts by their formal titles using [[link syntax]]
- Explain both upstream (consumes from) and downstream (provides to) relationships
- Consider the flow of data, control, or dependencies in both directions
- Link to the overall AI-OS architecture document and vision
- Reference relevant AI-OS master documents: [[AI_OS_MASTER_CONTEXT.md]], [[ENGINEERING_PRINCIPLES.md]]
- Be specific about what flows where and in what format
- Consider both runtime and design-time relationships

## Common mistakes
- Isolating the part from the larger system
- Not explaining how it connects to other parts
- Missing critical dependencies (especially implicit ones)
- Being too vague about relationships ("interacts with" without specifics)
- Forgetting to mention integration points or interfaces
- Not explaining why relationships exist
- Being inconsistent with related parts' descriptions
- Overlooking bidirectional relationships
- Forgetting to mention shared data models or contracts
- Not considering the impact of this part on system qualities

## Review expectations
- Reviewers should verify all major relationships are documented
- Should check that relationships are consistent with other parts' descriptions
- Must verify that data flows and interfaces are plausible
- Should ensure the part's position in the architecture makes sense
- Should confirm dependencies are identified and reasonable
- Should verify alignment with AI-OS architectural vision and principles

## Quality indicators
- Clear, specific relationships with named parts
- Documented data flows including format and frequency
- Clear upstream/downstream dependencies
- Alignment with AI-OS architectural vision
- Plausible and achievable integration points
- Consistency with related parts' descriptions
- Identification of impact on system qualities (performance, scalability, etc.)

## Completion criteria
- Relationship to AI-OS architectural vision and principles documented
- Position within overall architecture clearly described
- Key enabling and enabled-by relationships identified
- References to relevant architecture parts using proper link syntax
- Dependencies on external systems or standards documented
- Data and control flows described where relevant
- Passes review by at least one architect
- Consistent with descriptions in related architecture parts

## Formatting conventions
- Use formal references to other architecture parts: [[Related Part Title]]
- Consider using a context diagram
- Keep explanations concise but informative
- Use present tense for describing relationships
- Use arrows or directional language to show flow direction
- Specify data formats, protocols, or exchange mechanisms when relevant
- Reference AI-OS master documents where appropriate:
  - [[AI_OS_MASTER_CONTEXT.md]] for overall context
  - [[ENGINEERING_PRINCIPLES.md]] for engineering principles
  - [[ARCHITECTURE_DECISIONS.md]] for relevant decisions
  - [[IMPLEMENTATION_GUIDE.md]] for implementation considerations
  - [[VALIDATION_ARCHITECTURE.md]] for validation approaches
  - [[GLOSSARY.md]] for shared terminology
  - [[REPOSITORY_ECOSYSTEM.md]] for repository structure

## Diagram recommendations
Context diagram showing this part and its immediate neighbors, or a layered diagram showing where it fits in the architecture stack
Use data flow diagrams to show information exchange with other parts
Consider sequence diagrams for key interaction scenarios
Use dependency graphs to show structural relationships
Consider impact maps to show how this part affects system qualities

## RFC 2119 guidance
Use "MUST" for critical relationships - this part MUST properly interface with specific other parts to function correctly within AI-OS.
Use "SHOULD" for recommended relationships that enhance coherence but may have exceptions.
Use "MAY" for optional relationships that depend on specific configurations or use cases.

---

# Principles

## Purpose
Establishes the guiding architectural principles that drive decisions for this part. Should answer: "What fundamental truths guide architectural decisions in this area?"

## Expected contents
- List of architectural principles (3-8 items)
- Brief explanation of each principle
- How each principle influences decisions and trade-offs
- References to AI-OS-wide principles where applicable
- Rationale for each principle (why it's important)
- Examples of how the principle guides decisions

## Writing guidance
- Focus on enduring truths, not temporary preferences or trends
- Make principles actionable and decision-guiding (should help choose between alternatives)
- Avoid platitudes or vague statements - each principle should have clear implications
- Reference where principles come from (industry standards, lessons learned, AI-OS vision)
- Keep principles concise but meaningful (one sentence ideal)
- Ensure principles are mutually reinforcing, not conflicting
- Consider both technical and organizational principles
- Make sure principles scale with the system and team size

## Common mistakes
- Writing vague statements that don't guide decisions ("We believe in quality")
- Including specific technologies or implementations (should be technology-neutral)
- Having too many principles (>10 makes them hard to remember and apply)
- Making principles that conflict with each other
- Not explaining how to apply the principle in practice
- Writing principles that are actually goals or constraints
- Being too abstract to be useful in decision-making
- Not connecting principles to AI-OS architectural vision

## Review expectations
- Reviewers should verify each principle is actionable and decision-guiding
- Should check that principles are technology-neutral
- Must verify that principles don't conflict with each other
- Should ensure principles align with AI-OS architectural vision
- Should confirm each principle has clear implications for design choices

## Quality indicators
- Each principle starts with a clear value or priority
- Principles are mutually exclusive and collectively comprehensive
- Each principle has clear implications for architectural decisions
- Principles are technology-neutral and implementation-independent
- Language is clear, concise, and unambiguous
- Principles support rather than contradict each other
- Alignment with AI-OS architectural vision and ENGINEERING_PRINCIPLES.md

## Completion criteria
- 3-8 well-defined principles
- Each principle is one sentence or less
- Principles are actionable (help choose between alternatives)
- No specific technologies or implementations mentioned
- Principles don't conflict with each other
- Clear rationale provided for each principle
- Passes review by at least one architect
- Alignment with AI-OS architectural vision documentation

## Formatting conventions
- Use bold for principle names, followed by explanation
- Consider numbering for reference (e.g., "Principle 1:", "Principle 2:")
- Keep each principle to 1-2 sentences maximum
- Use consistent structure: "**Principle Name**: Clear explanation of what it means and how it guides decisions"
- Optionally include rationale: "Principle Name: Explanation. **Why:** [rationale]"
- Reference AI-OS-wide principles where appropriate

## Diagram recommendations
N/A - principles are typically textual, but consider:
- Principle hierarchy diagram showing how principles relate to each other
- Decision matrix showing how principles guide specific choices
- Weighted scoring diagram showing principle trade-offs

## RFC 2119 guidance
Use "SHOULD" for principles - designs following this part SHOULD adhere to these principles, though exceptions may be justified with proper rationale documented in the Architecture Decisions section.

---

# Components

## Purpose
Identifies the key structural elements that make up this architecture part. Should answer: "What are the principal building blocks, and what is their role?"

## Expected contents
- List of major components with clear names
- Brief description of each component's responsibility
- Whether components are structural, behavioral, or both
- Notes on component granularity and boundaries
- Any component patterns or styles used
- Technology choices or constraints for each component (if decided)
- Version or maturity level of components (if applicable)
- Dependencies between components
- Reuse level (internal, external, new development)

## Writing guidance
- Use clear, meaningful component names that reflect their responsibility
- Focus on responsibilities, not implementations (what it does, not how)
- Consider different views (logical, physical, deployment) as appropriate
- Be consistent with naming conventions used elsewhere in AI-OS
- Indicate if components are devices, modules, services, processes, etc.
- Specify component granularity appropriately for architectural level
- Note any existing components being reused vs. new development
- Consider both runtime and design-time component views
- Document any component patterns or styles used (layers, pipes, etc.)

## Common mistakes
- Confusing components with classes or functions (too implementation-focused)
- Being too fine-grained (listing implementation details instead of architectural building blocks)
- Missing important structural elements (glue code, infrastructure, etc.)
- Inconsistent naming or terminology with other parts
- Not explaining what makes something a "component" in this architectural context
- Including components that belong in other parts
- Being too vague about component responsibilities
- Over-specifying implementation details (languages, frameworks, etc.)
- Forgetting to document component boundaries and interfaces
- Not considering component reuse or existing implementations

## Review expectations
- Reviewers should verify components are at the right architectural level
- Should check that responsibilities are clear and non-overlapping
- Must verify that component boundaries are well-defined
- Should ensure naming is consistent with AI-OS conventions
- Should confirm that components are actually structural elements, not implementation details
- Should verify dependencies between components are plausible
- Should check that reuse assumptions are realistic

## Quality indicators
- Clear, meaningful component names that indicate responsibility
- Responsibilities are clear, distinct, and non-overlapping
- Component boundaries are well-defined and understandable
- Appropriate granularity for architectural level (not too fine, not too coarse)
- Consistent naming and terminology with AI-OS conventions
- Clear distinction between structural and behavioral aspects where relevant
- Plausible dependencies between components
- Realistic assessment of reuse vs. new development
- Alignment with component definitions in related parts

## Completion criteria
- List of major architectural components with clear names
- Brief description of each component's responsibility (what it does)
- Indication of structural vs. behavioral nature where relevant
- Notes on component granularity and boundaries
- Documentation of any component patterns or styles used
- Indication of technology constraints or choices (if already decided)
- Passes review by at least one architect
- Consistent with component definitions in related architecture parts

## Formatting conventions
- Use bullet points or a table
- Format: **Component Name**: Responsibility description
- Consider adding metadata in parentheses: (e.g., "Service", "Library", "Database")
- Consider grouping related components (by layer, function, etc.)
- Indicate if components are optional, conditional, or configurable
- Use consistent terminology for component types across AI-OS
- For reused components, indicate source or version
- For new development, indicate maturity level (concept, prototype, production-ready)

## Diagram recommendations
Component diagram showing components and their interfaces, or a container diagram if dealing with deployment units
Use layered diagrams to show architectural layering
Consider radial diagrams to show hub-and-spoke component relationships
Use grid diagrams to show component interaction matrices
Consider dependency graphs to show structural dependencies between components

## RFC 2119 guidance
Use "MAY" for component variations - implementations MAY include additional components not listed here, provided they don't violate other constraints, responsibilities, or interfaces.
Use "SHOULD" to recommend certain component types or patterns that align with architectural principles.
Use "MUST" for critical components that are essential to fulfilling the part's purpose.

---

# Responsibilities

## Purpose
Details what each component or the part as a whole is responsible for doing. Should answer: "What does each element actually do, and what are its obligations?"

## Expected contents
- For the part overall: high-level responsibilities
- For each component: specific responsibilities
- Clear separation of concerns between elements
- Any responsibilities that are shared or coordinated
- Responsibilities that might be delegated or outsourced
- Lifecycle responsibilities (creation, initialization, operation, shutdown)
- Error handling and fault management responsibilities
- Performance and scalability responsibilities
- Security and compliance responsibilities
- Monitoring, observability, and debugging responsibilities
- Data management responsibilities (creation, modification, deletion, retention)

## Writing guidance
- Use active verbs to describe responsibilities (ensures, provides, manages, coordinates, etc.)
- Be specific about what is and isn't included in each responsibility
- Avoid vagueness like "handles" or "manages" without explanation of what that entails
- Consider both functional and non-functional responsibilities (performance, security, etc.)
- Ensure responsibilities align with component definitions and don't create gaps or overlaps
- Distinguish between primary responsibilities and secondary/supporting responsibilities
- Consider temporal aspects (when responsibilities apply during lifecycle)
- Document any shared or coordinated responsibilities clearly
- Consider delegation patterns (what can be outsourced vs. must be retained internally)

## Common mistakes
- Being too vague or generic ("responsible for processing data" without specifying how or what)
- Listing capabilities instead of responsibilities (what it can do vs. what it must do)
- Overlapping or conflicting responsibilities between components
- Missing important responsibilities (especially non-functional ones like security, performance)
- Not distinguishing between different elements' responsibilities leading to confusion
- Including implementation details in responsibility descriptions
- Making responsibilities too broad or too narrow for the component's scope
- Forgetting lifecycle responsibilities (initialization, cleanup, etc.)
- Not considering error conditions and failure modes in responsibilities
- Overlooking operational responsibilities (monitoring, maintenance, etc.)

## Review expectations
- Reviewers should verify responsibilities are clear, specific, and non-overlapping
- Should check that all major functions have clear ownership
- Must verify that responsibilities align with component definitions
- Should ensure no gaps exist in responsibility coverage
- Should confirm responsibilities are at the right level of abstraction (architectural, not implementation)
- Should verify that non-functional responsibilities are addressed
- Should check that shared responsibilities are clearly documented
- Should validate that responsibilities make sense in the context of other parts

## Quality indicators
- Each responsibility starts with a strong, active verb
- Responsibilities are clear, specific, and unambiguous
- No gaps or overlaps in responsibility coverage between components
- Responsibilities align precisely with component definitions
- Both functional and non-functional responsibilities are addressed
- Responsibilities are appropriate to the component's scope and scale
- Clear indication of what is included vs. excluded in each responsibility
- Lifecycle responsibilities are considered where relevant
- Shared or coordinated responsibilities are explicitly documented

## Completion criteria
- High-level responsibilities for the part overall are documented
- Specific responsibilities for each component are documented
- Responsibilities use active verbs and are specific about what is done
- Clear separation of concerns between elements is evident
- Any shared or coordinated responsibilities are explicitly identified
- Responsibilities align with component definitions (no gaps or overlaps)
- Both functional and non-functional responsibilities are considered
- Passes review by at least one architect
- Consistent with related parts' responsibility assignments

## Formatting conventions
- Use bullet points under each component or for the part overall
- Start each responsibility with a strong verb (ensures, provides, manages, coordinates, etc.)
- Keep each responsibility to one sentence if possible
- Consider using a responsibility assignment matrix (RACI) for complex interactions
- For shared responsibilities, clearly indicate which components are involved
- Consider using notation to indicate responsibility type: [F]unctional, [NF]unctional-performance, [NF]unctional-security, etc.
- Indicate responsibility scope: primary, secondary, supporting, shared, delegated
- Consider temporal notation: [init], [runtime], [shutdown], [error-handling]

## Diagram recommendations
Sequence diagram showing responsibility flow, or responsibility assignment matrix
Use activity diagrams to show responsibility handoffs between components
Consider swimlane diagrams to show which components own which responsibilities
Use responsibility matrix diagrams to visualize RACI assignments
Consider timeline diagrams to show when responsibilities apply during component lifecycle

## RFC 2119 guidance
Use "MUST" for critical responsibilities - components MUST fulfill these responsibilities to be considered compliant implementations.
Use "SHOULD" for important responsibilities that should be fulfilled but may have acceptable alternatives.
Use "MAY" for optional responsibilities that depend on specific configurations or use cases.

---

# Relationships

## Purpose
Describes how elements within this part relate to one another and to elements in other parts. Should answer: "How do the pieces connect and interact?"

## Expected contents
- Types of relationships (dependency, association, generalization, etc.)
- Direction and nature of each relationship
- Any relationship patterns or styles used
- How relationships support the part's responsibilities
- Notes on relationship cardinality and optionality
- Technology mechanisms used to implement relationships (if decided)
- Performance or latency characteristics of relationships
- Failure modes and error handling for relationships
- Versioning or evolution considerations for relationships

## Writing guidance
- Be precise about relationship types (uses, calls, emits, consumes, shares, etc.)
- Indicate direction where relevant (A uses B, B is called by A, etc.)
- Specify multiplicity (one-to-one, one-to-many, many-to-many, etc.)
- Explain why relationships exist (don't just list them - what purpose do they serve?)
- Consider both structural (compile-time) and behavioral (runtime) relationships
- Document any relationship patterns or styles used (layers, pipes, brokers, etc.)
- Consider technology mechanisms for implementing relationships (if already decided)
- Document performance, latency, or throughput characteristics if relevant
- Describe failure modes and how errors are handled in relationships
- Consider versioning or evolution aspects (backward compatibility, etc.)

## Common mistakes
- Being vague about relationship nature ("interacts with" without specifics)
- Missing important connections (especially implicit ones like shared data)
- Inconsistent relationship notation or terminology
- Not explaining the purpose of relationships (just listing them)
- Overcomplicating simple relationships with unnecessary detail
- Forgetting to document directionality when it matters
- Being unclear about multiplicity or optionality
- Not considering failure modes or error handling in relationships
- Overlooking performance or latency implications
- Being inconsistent with related parts' descriptions of the same relationship
- Not documenting technology mechanisms when they're significant decisions

## Review expectations
- Reviewers should verify all significant relationships are documented
- Should check that relationship descriptions are precise and unambiguous
- Must verify that directionality is clear where relevant
- Should ensure multiplicity and optionality are specified
- Should confirm that purposes of relationships are explained
- Should verify consistency with related parts' descriptions
- Should check that technology mechanisms are documented if decided
- Should validate that failure modes and error handling are considered

## Quality indicators
- Clear, precise relationship descriptions with direction and multiplicity
- Each relationship has a clear purpose or rationale
- Relationship types are used consistently and appropriately
- Directionality is clear where it matters
- Multiplicity and optionality are specified
- Relationships support the part's responsibilities
- Technology mechanisms are documented if they're significant decisions
- Failure modes and error handling are considered where relevant
- Consistency with related parts' descriptions of shared relationships

## Completion criteria
- All significant internal and external relationships are documented
- Relationship types are precise (uses, calls, emits, consumes, etc.)
- Direction is specified where relevant
- Multiplicity and optionality are documented
- Purpose aparelho each relationship is explained
- Technology mechanisms are documented if they're architectural decisions
- Failure modes and error handling are considered where relevant
- Passes review by at least one architect
- Consistent with descriptions in related architecture parts

## Formatting conventions
- Use standard relationship notation or clear descriptions (A → B: A uses B)
- Consider using a relationship matrix for complex cases (rows: source, columns: target)
- Indicate relationship strength or importance if relevant (primary, secondary, etc.)
- Use arrows or directional language where appropriate (A → B, B ← A)
- Specify multiplicity notation: 1:1, 1:*, *:1, *:* etc.
- Indicate optionality: mandatory [1..1], optional [0..1], etc.
- Consider using color-coding or styling to differentiate relationship types
- Document technology mechanisms: synchronous/asynchronous, protocol, technology
- Note performance characteristics if relevant: latency, throughput, bandwidth
- Describe failure handling: retry policies, circuit breakers, fallback mechanisms

## Diagram recommendations
Relationship diagram (using UML or similar notation), dependency graph, or collaboration diagram
Use sequence diagrams to show behavioral relationships in key scenarios
Consider communication diagrams to show how components interact
Use deployment diagrams to show relationships with deployment considerations
Consider data flow diagrams to show information exchange relationships
Use state diagrams to show how relationships change based on system state
Consider impact maps to show how relationship changes affect system capabilities

## RFC 2119 guidance
Use "SHOULD" for relationship patterns - designs SHOULD follow these relationship patterns unless there's a compelling architectural reason not to.
Use "MUST" for critical relationships that are essential to the part's function.
Use "MAY" for optional relationships that depend on specific configurations or use cases.

---

# Interfaces

## Purpose
Specifies the points of interaction between this part and other parts of the system, or between internal components. Should answer: "How do elements communicate and exchange information?"

## Expected contents
- Interface types (APIs, events, shared data, etc.)
- For each interface: purpose, protocol, data format, binding
- Interface stability and versioning considerations
- Performance and reliability characteristics (latency, throughput, availability)
- Error handling and fault tolerance approaches
- Security considerations (authentication, authorization, encryption)
- Data ownership and lifecycle management
- Versioning and evolution strategy
- Deprecation and removal policies
- Usage guidelines and best practices
- QoS or SLA commitments (if applicable)

## Writing guidance
- Focus on contracts, not implementations (what is guaranteed, not how it's done)
- Specify what is guaranteed vs. what is expected or best effort
- Consider both synchronous and asynchronous interfaces
- Document interface evolution strategies (backward compatibility, versioning)
- Reference interface technologies or standards used (REST, gRPC, Kafka, etc.)
- Clearly distinguish between provided (offered) and required (consumed) interfaces
- Document data formats precisely (schemas, examples, validation rules)
- Specify communication protocols and binding details
- Address performance characteristics: latency, throughput, concurrency limits
- Describe reliability guarantees: availability, retry policies, circuit breakers
- Consider security aspects: authentication, authorization, encryption, auditing
- Document error handling: error codes, exception types, fault propagation
- Specify data ownership and lifecycle management responsibilities
- Define versioning strategy: semantic versioning, API versioning, etc.
- Establish deprecation policies: notice periods, removal timelines
- Provide usage guidelines: common patterns, anti-patterns, best practices
- Document any QoS or SLA commitments if applicable
- Consider interface granularity and composability
- Document any interface patterns or styles used (RESTful, event-driven, etc.)

## Common mistakes
- Describing implementation instead of contract (how it's built vs. what it guarantees)
- Missing important interfaces (especially implicit ones like shared databases)
- Being too vague about contracts (not specifying guarantees vs. expectations)
- Not addressing interface evolution (how it will change over time)
- Forgetting non-functional aspects (performance, security, reliability)
- Inconsistent terminology or data formats across interfaces
- Overlooking error handling and failure modes
- Not considering security implications of interfaces
- Forgetting to document data ownership and lifecycle
- Being unclear about synchronous vs. asynchronous behavior
- Not specifying performance or scalability characteristics
- Overlooking versioning and compatibility concerns
- Making interfaces too chatty or too bulky
- Not considering observability and monitoring needs

## Review expectations
- Reviewers should verify all significant interfaces are documented
- Should check that interfaces specify contracts, not implementations
- Must verify that data formats and protocols are specified precisely
- Should ensure performance and reliability characteristics are addressed
- Should confirm security considerations are documented
- Should verify error handling and fault tolerance are considered
- Should check that versioning and evolution strategies are documented
- Should validate that data ownership and lifecycle are clear
- Should confirm that interfaces are consistent with related parts
- Should review that usage guidelines are practical and helpful

## Quality indicators
- Each interface has a clear purpose and well-defined contract
- Data formats are specified precisely (schemas, examples, validation)
- Communication protocols and bindings are clearly documented
- Performance characteristics (latency, throughput) are specified
- Reliability guarantees (availability, retry policies) are documented
- Security considerations (authentication, authorization) are addressed
- Error handling and fault tolerance approaches are specified
- Data ownership and lifecycle management are clear
- Versioning and evolution strategy is documented
- Usage guidelines and best practices are provided
- Interfaces are consistent with related parts' descriptions
- Clear distinction between provided and required interfaces

## Completion criteria
- All significant interfaces are identified and documented
- For each interface: purpose, protocol, data format, binding are specified
- Interface stability and versioning considerations are documented
- Performance and reliability characteristics are addressed
- Error handling and fault tolerance approaches are specified
- Security considerations are documented where relevant
- Data ownership and lifecycle management are clear
- Versioning and evolution strategy is documented
- Usage guidelines and best practices are provided
- Passes review by at least one architect
- Consistent with interface descriptions in related architecture parts

## Formatting conventions
- Use a consistent interface template for each interface
- Consider tables for multiple interfaces with similar structure
- Clearly separate interface specification from usage guidance
- Use standard API documentation conventions where applicable (OpenAPI, AsyncAPI, etc.)
- For each interface, document:
  - **Name/Purpose**: Clear identifier and purpose statement
  - **Type**: API, event, shared data, etc.
  - **Direction**: Provided (offered) or Required (consumed)
  - **Protocol**: Communication mechanism (HTTP, gRPC, Kafka, etc.)
  - **Data Format**: Schema, examples, validation rules (JSON, Protobuf, etc.)
  - **Binding**: Specific technology implementation details
  - **Performance**: Latency, throughput, concurrency limits
  - **Reliability**: Availability, retry policies, timeout values
  - **Security**: Authentication, authorization, encryption requirements
  - **Error Handling**: Error codes, exception types, fault propagation
  - **Data Ownership**: Who owns and manages the data lifecycle
  - **Versioning**: Strategy, current version, backward compatibility
  - **Usage Guidelines**: Best practices, common patterns, anti-patterns
  - **QoS/SLA**: Any formal commitments if applicable
- Indicate interface stability: stable, experimental, deprecated, etc.
- Consider using interface notation: [provided] InterfaceName: Description
- Reference related AI-OS documents where appropriate:
  - [[GLOSSARY.md]] for shared terminology
  - [[REPOSITORY_ECOSYSTEM.md]] for interface implementation locations

## Diagram recommendations
Interface diagram showing provided and required interfaces, or sequence diagrams showing key interactions
Use communication diagrams to show interface interactions in scenarios
Consider data flow diagrams to show information exchange via interfaces
Use deployment diagrams to show interface technology implementation
Consider state diagrams to show interface behavior based on system state
Use component diagrams to show how interfaces connect components
Consider timeline diagrams to show interface evolution over time
Use matrix diagrams to show interface characteristics (performance, security, etc.)

## RFC 2119 guidance
Use "MUST" for interface contracts - implementations MUST adhere to these interfaces to be interoperable with other parts of AI-OS.
Use "SHOULD" for recommended interface characteristics that enhance usability but may have exceptions.
Use "MAY" for optional interface features that depend on specific use cases or configurations.

---

# Constraints

## Purpose
Identifies limitations or restrictions that affect design and implementation choices. Should answer: "What limits what we can do, and why?"

## Expected contents
- Technical constraints (technology choices, platforms, standards, versions)
- Resource constraints (performance, memory, bandwidth, storage, etc.)
- Organizational constraints (skills, processes, policies, team structure)
- Regulatory or compliance constraints (legal, industry standards, audits)
- Temporal constraints (deadlines, timing requirements, release schedules)
- Architectural constraints (dependencies on other parts, shared services)
- Assumptions that act as constraints (environmental, usage patterns)
- Financial or budgetary constraints (if relevant)
- Geographical or deployment constraints (latency requirements, data sovereignty)

## Writing guidance
- Distinguish between hard constraints (must be satisfied) and preferences (nice to have)
- Explain the origin or rationale for each constraint (where it comes from)
- Indicate if constraints are temporary (project-specific) or permanent (industry-wide)
- Consider both internal (team, organization) and external (regulatory, market) sources
- Be specific about constraint boundaries and limitations
- Consider constraint interactions and trade-offs
- Document any constraint conflicts and resolution approaches
- Reference sources of constraints (regulations, standards, policies)
- Consider both current constraints and anticipated future changes

## Common mistakes
- Confusing constraints with goals or principles (constraints limit, goals aspire)
- Not explaining why something is a constraint (missing rationale)
- Missing important constraints (especially implicit ones like team expertise)
- Being too vague about constraint boundaries ("must be fast" without metrics)
- Not distinguishing between different types of constraints (technical vs. organizational)
- Treating preferences as constraints (over-constraining the design)
- Not considering constraint evolution over time
- Forgetting to document assumed constraints (environmental, usage)
- Overlooking constraint interactions and trade-offs
- Being inconsistent with constraint descriptions in related parts

## Review expectations
- Reviewers should verify all significant constraints are identified
- Should check that each constraint has a clear rationale or source
- Must verify distinction between hard constraints and preferences
- Should ensure constraint boundaries are specific and measurable
- Should confirm that constraint types are properly categorized
- Should validate that constraint conflicts are identified and addressed
- Should check that assumptions are documented and reasonable
- Should review that constraints are consistent with related parts

## Quality indicators
- Each constraint has a clear origin or rationale
- Hard constraints are distinguished from preferences
- Constraint boundaries are specific and measurable where possible
- Constraint types are properly categorized (technical, organizational, etc.)
- Constraint conflicts are identified and resolution approaches documented
- Assumptions are explicitly stated and justified
- Constraint descriptions are consistent with related architecture parts
- Consideration of constraint evolution over time
- Realistic assessment of what can be changed vs. what is fixed

## Completion criteria
- All significant constraints are identified and documented
- For each constraint: description, origin/clean explanation
- Hard constraints distinguished from preferences
- Constraint boundaries specified where applicable (metrics, limits)
- Constraint types properly categorized
- Constraint conflicts identified with resolution approaches
- Assumptions explicitly stated and justified
- Passes review by at least one architect
- Consistent with constraint descriptions in related architecture parts

## Formatting conventions
- Use bullet points grouped by constraint type
- Format: **Constraint Type**: Specific limitation with rationale
- Indicate constraint severity: [HARD] must be satisfied, [PREFERENCE] nice to have
- Indicate constraint permanence: [TEMPORARY] project-specific, [PERMANENT] industry-wide
- Consider using a constraint matrix for complex trade-offs
- Reference sources: regulations, standards, policies, team capabilities
- For measurable constraints, include units and values: (e.g., "< 100ms latency")
- Reference AI-OS constraint documents where appropriate:
  - [[ENGINEERING_PRINCIPLES.md]] for organizational constraints
  - [[ARCHITECTURE_DECISIONS.md]] for decided constraints
  - [[VALIDATION_ARCHITECTURE.md]] for constraint validation approaches

## Diagram recommendations
N/A - constraints are typically textual, but consider:
- Constraint tree showing hierarchy of constraints
- Trade-off matrix showing constraint interactions
- Timeline diagram showing constraint evolution over time
- Influence diagram showing constraint sources and impacts
- Constraint relationship diagram showing dependencies between constraints

## RFC 2119 guidance
Use "MUST" for hard constraints - designs MUST adhere to these constraints, though exceptions may be possible with proper justification and impact analysis documented in Architecture Decisions.
Use "SHOULD" for strong preferences that should be followed unless compelling reasons exist.
Use "MAY" for optional constraints or preferences that depend on specific use cases.
Use "MUST NOT" for prohibitions - things that MUST NOT be done (e.g., MUST NOT store sensitive data in logs).
Use "SHOULD NOT" for recommendations against certain approaches that may have exceptions.

---

# Invariants

## Purpose
Establishes conditions that must always hold true for this architecture part to be considered correct. Should answer: "What must never change, regardless of state or inputs?"

## Expected contents
- List of invariant conditions (typically 3-7 items)
- Brief explanation of why each invariant is important
- Any mechanisms that help maintain invariants
- Notes on when invariants are established or verified
- Relationship to principles and constraints
- Safety, liveness, and correctness properties
- Data consistency and integrity guarantees
- Security and access control properties
- Performance and resource bounds

## Writing guidance
- Focus on properties that are always true, not usually true or sometimes true
- Make invariants checkable or verifiable in principle (even if expensive to check)
- Avoid temporal properties unless they're permanent (e.g., "initially empty" is not an invariant)
- Consider security, safety, and correctness invariants (access control, data integrity, etc.)
- Explain consequences of invariant violation (what happens if this condition is broken?)
- Consider both structural invariants (always true) and behavioral invariants (always hold during execution)
- Express invariants in clear, unambiguous language
- Consider using formal notation where appropriate for precision
- Document any mechanisms or patterns that help maintain the invariant
- Consider invariants at different levels: component, subsystem, system

## Common mistakes
- Listing things that are frequently true but not always (99% uptime is not an invariant)
- Including transient states or temporary conditions (startup state, error states)
- Making invariants too specific to current implementation (ties invariant to specific tech)
- Not explaining how to verify invariants (makes them unactionable)
- Confusing invariants with goals or principles (invariants are facts, not aspirations)
- Writing invariants that are actually constraints or requirements
- Being too vague ("data is correct" without specifying what correct means)
- Forgetting to consider edge cases and boundary conditions
- Overlooking invariants related to concurrency or parallelism
- Not considering how invariants compose across components

## Review expectations
- Reviewers should verify each invariant is truly always true (not usually true)
- Should check that invariants are checkable in principle (even if expensive)
- Must verify that invariants are not actually goals or constraints
- Should ensure consequences of violation are understood and documented
- Should confirm invariants are at the right level of abstraction
- Should verify that invariants don't conflict with each other
- Should check that mechanisms to maintain invarians are plausible
- Should validate that invariants are consistent with related parts

## Quality indicators
- Each invariant is a property that must always hold (100% of the time)
- Invariants are checkable or verifiable in principle
- Invariants are not actually goals, principles, or constraints
- Clear explanation of why each invariant matters
- Documented consequences of invariant violation
- Invariants are expressed clearly and unambiguously
- Appropriate level of abstraction (not too implementation-specific)
- Mechanisms to maintain invariants are documented where relevant
- Invariants are consistent with related architecture parts
- Consideration of how invariants compose across component boundaries

## Completion criteria
- List of invariant conditions that must always hold
- For each invariant: clear statement, explanation of importance
- Consequences of violation documented
- Invariants are checkable in principle (even if expensive to verify)
- Invariants are not actually goals, principles, or constraints
- No transient or temporary conditions included
- Passes review by at least one architect
- Consistent with invariant descriptions in related architecture parts

## Formatting conventions
- Use bullet points with clear, positive statements
- Format: **Invariant**: Condition that must always hold
- Use mathematical or logical notation where appropriate for precision
- Consider grouping invariants by category: [Safety], [Liveness], [Correctness], [Security]
- For complex invariants, consider using multi-line format with explanation
- Indicate verification approach: [static], [runtime], [manual], [formal-proof]
- Reference AI-OS invariant documents where appropriate:
  - [[ENGINEERING_PRINCIPLES.md]] for system-wide invariants
  - [[VALIDATION_ARCHITECTURE.md]] for invariant validation approaches

## Diagram recommendations
State diagram showing invariant regions, or using formal verification notation
Use activity diagrams to show when invariants are established and maintained
Consider timeline diagrams to show invariant validity over system lifecycle
Use dependency diagrams to show how invariants depend on other components
Consider matrix diagrams to show invariant relationships and trade-offs
Use hierarchy diagrams to show invariant abstraction levels

## RFC 2119 guidance
Use "MUST" for invariants - the system MUST always maintain these conditions to be considered correct.
Use "SHOULD" for strong properties that should hold but may have rare, acceptable exceptions.
Use "MAY" for optional properties that hold under specific configurations or conditions.

---

# Runtime Behaviour

## Purpose
Describes how the architecture part behaves during execution, including performance, scalability, and dynamic properties. Should answer: "How does it actually work when running?"

## Expected contents
- Performance characteristics (latency, throughput, response times, jitter)
- Scalability properties (horizontal, vertical, limits, bottlenecks)
- Availability and reliability characteristics (uptime, MTBF, MTTR)
- Fault tolerance and recovery behavior (failure modes, recovery time)
- Resource consumption patterns (memory, CPU, storage, network, IO)
- Concurrency and threading model (threads, processes, async, locking)
- Startup/shutdown behavior (initialization time, graceful degradation)
- Monitoring and observability characteristics (metrics, logging, tracing)
- Response characteristics under various load conditions
- Resource utilization and efficiency metrics
- Error rates and failure frequencies
- Data consistency and integrity guarantees during operation
- Security properties during runtime (encryption in use, access controls)
- Backup and restore capabilities and performance
- Archive and purge behaviors

## Writing guidance
- Use measurable or observable characteristics where possible
- Distinguish between guaranteed behavior (SLAs) and typical behavior (average case)
- Consider different load conditions (idle, normal, peak, stress, failure)
- Reference benchmarks, measurement approaches, or testing methodologies
- Explain any non-obvious behaviors or trade-offs (e.g., latency vs throughput)
- Consider both best-case and worst-case scenarios
- Document any non-deterministic behavior or sources of variability
- Consider warm-up effects and steady-state behavior
- Document resource usage patterns over time (leaks, accumulation)
- Consider both synchronous and asynchronous behaviors
- Address observability: what can be monitored and measured
- Consider deployment and configuration impacts on behavior
- Reference industry standards or benchmarks where applicable

## Common mistakes
- Being too vague ("it's fast", "it scales well")
- Making unverifiable claims without measurement approach
- Missing important behavioral aspects (especially failure modes)
- Not considering edge cases or failure conditions (only happy path)
- Confusing design intentions with actual behavior (aspiration vs reality)
- Overlooking resource consumption patterns (memory leaks, disk growth)
- Forgetting to consider concurrency and threading issues
- Not addressing startup/shutdown behavior and transition periods
- Overlooking monitoring and observability needs
- Being inconsistent with SLA or performance commitments
- Not considering behavior under degraded or partial failure conditions
- Forgetting to document assumptions about workload or usage patterns
- Overlooking the impact of configuration or tuning on behavior

## Review expectations
- Reviewers should verify behavioral characteristics are measurable where possible
- Should check that guaranteed vs typical behavior is distinguished
- Must verify that different load conditions are considered
- Should ensure failure modes and recovery are addressed
- Should confirm resource consumption patterns are documented
- Should validate that concurrency and threading model is specified
- Should check that monitoring and observability considerations are included
- Should review that behavior is consistent with stated SLAs or commitments
- Should validate that assumptions about workload are documented

## Quality indicators
- Behavioral characteristics are measurable or observable in principle
- Clear distinction between guaranteed (SLA) and typical behavior
- Different load conditions considered (idle, normal, peak, stress)
- Failure modes and recovery behavior documented
- Resource consumption patterns specified (memory, CPU, etc.)
- Concurrency and threading model clearly described
- Startup/shutdown behavior addressed
- Monitoring and observability characteristics specified
- Behavior is consistent with stated performance or reliability commitments
- Assumptions about workload or usage patterns are documented
- Trade-offs between different characteristics are explained

## Completion criteria
- Performance characteristics documented with units where applicable
- Scalability properties described (horizontal/vertical limits)
- Availability and reliability characteristics specified
- Fault tolerance and recovery behavior described
- Resource consumption patterns documented
- Concurrency and threading model specified
- Startup/shutdown behavior addressed
- Monitoring and observability characteristics specified
- Behavior under different load conditions considered
- Assumptions about workload or usage patterns documented
- Passes review by at least one architect
- Consistent with related parts' behavioral descriptions where they interact

## Formatting conventions
- Use bullet points or tables for different aspects
- Include units for measurable characteristics (ms, req/s, GB, etc.)
- Indicate confidence levels: [measured], [specified], [estimated], [target]
- Consider using ranges where appropriate: (min/typical/max) or (percentiles)
- For SLAs, use standard notation: (e.g., "99.9% uptime monthly")
- Reference AI-OS behavioral documents where appropriate:
  - [[ENGINEERING_PRINCIPLES.md]] for system-wide behavioral guidelines
  - [[VALIDATION_ARCHITECTURE.md]] for behavioral validation approaches
  - [[ARCHITECTURE_DECISIONS.md]] for decided behavioral characteristics

## Diagram recommendations
Activity diagram, state diagram, sequence diagram for key scenarios, or performance characteristic charts
Use communication diagrams to show message flows and timing
Consider timeline diagrams to show behavior over time or during transitions
Use resource usage diagrams to show consumption patterns over time
Consider queueing diagrams to show behavior under load
Use state diagrams to show mode changes and failure recovery
Consider flowchart diagrams to show error handling and exception paths
Use Gantt charts to show timing and concurrency aspects
Consider heat maps to show resource utilization patterns
Use Sankey diagrams to show data flow and transformation volumes

## RFC 2119 guidance
Use "SHOULD" for behavioral characteristics - implementations SHOULD meet these behavioral targets, though actual performance may vary based on deployment and usage.
Use "MUST" for critical behavioral guarantees that are essential to the part's function (e.g., SLAs).
Use "MAY" for optional behavioral characteristics that depend on specific configurations or use cases.

---

# Extension Points

## Purpose
Identifies where and how this architecture part can be extended or customized without modifying its core. Should answer: "How can this be adapted for future needs or different contexts?"

## Expected contents
- List of extension points with clear names
- For each: purpose, mechanism, constraints, and examples
- Versioning and compatibility considerations for extensions
- Any extension patterns or frameworks used
- Guidelines for building extensions
- Performance and security implications of extensions
- Lifecycle management considerations for extensions
- Examples of actual or planned extensions

## Writing guidance
- Focus on intentional extensibility, not accidental flexibility
- Make extension mechanisms clear and discoverable
- Consider both plugin-style and configuration-style extensibility
- Document any limitations on what can be extended (what cannot be changed)
- Provide examples of plausible extensions (realistic use cases)
- Consider extension lifecycle: registration, initialization, execution, cleanup
- Document extension contracts: what extensions can expect from the core
- Specify extension constraints: what extensions must adhere to
- Address performance implications: how extensions affect system performance
- Consider security implications: what access and permissions extensions have
- Plan for extension versioning and compatibility
- Provide clear guidelines for extension developers
- Consider discovery mechanisms: how extensions are found and loaded
- Document isolation and fault tolerance: how extension failures are handled

## Common mistakes
- Claiming extensibility without providing mechanisms (saying "it's extensible" but not how)
- Making extension points too restrictive (preventing useful extensions) or too permissive (risking system integrity)
- Not considering extension lifecycle and maintenance (how extensions are managed over time)
- Forgetting to document extension guidelines (leaving extension developers to guess)
- Overlooking versioning and compatibility issues (extensions breaking with core updates)
- Not considering performance impacts of extensions
- Forgetting security implications (extensions as attack surface)
- Making extension mechanisms overly complex or difficult to use
- Not considering how extension failures affect the core system
- Overlooking extension discovery and loading mechanisms
- Forgetting to document extension contracts and responsibilities

## Review expectations
- Reviewers should verify extension mechanisms are clear and usable
- Should check that limitations on what can be extended are documented
- Must verify that extension contracts are clear (what extensions can rely on)
- Should ensure performance and security implications are considered
- Should confirm that lifecycle management is addressed
- Should validate that versioning and compatibility are considered
- Should check that examples are realistic and helpful
- Should review that guidelines for extension developers are adequate

## Quality indicators
- Clear, usable extension mechanisms are documented
- Limitations on what can be extended are explicit and justified
- Extension contracts are well-defined (what extensions can expect from core)
- Performance and security implications of extensions are considered
- Lifecycle management for extensions is addressed (registration, updates, removal)
- Versioning and compatibility strategies are documented
- Realistic examples of extensions are provided
- Clear guidelines for extension developers are included
- Extension mechanisms are consistent with AI-OS extension patterns
- Discovery and loading mechanisms are documented

## Completion criteria
- List of extension points with clear names and purposes
- For each extension point: mechanism, constraints, and examples documented
- Extension contracts are specified (what extensions can rely on)
- Limitations on what can be extended are clearly documented
- Versioning and compatibility considerations are addressed
- Performance and security implications are considered
- Lifecycle management for extensions is documented
- Guidelines for extension developers are provided
- Passes review by at least one architect
- Consistent with extension approaches in related architecture parts

## Formatting conventions
- Use bullet points or a table
- Format: **Extension Point**: Purpose and mechanism
- For each extension point, document:
  - **Name**: Clear identifier for the extension point
  - **Purpose**: What the extension point enables
  - **Mechanism**: How extensions are implemented and integrated
  - **Constraints**: What extensions must adhere to (interfaces, behaviors, etc.)
  - **Examples**: Plausible use cases or actual implementations
  - **Limitations**: What cannot be changed or extended through this point
  - **Extension Contract**: What extensions can expect from the core (services, data, etc.)
  - **Versioning**: How extension compatibility is managed across core versions
  - **Performance**: Expected performance impact considerations
  - **Security**: Security implications and required permissions
  - **Lifecycle**: How extensions are registered, initialized, executed, and cleaned up
  - **Discovery**: How the system finds and loads extensions
  - **Guidelines**: Best practices for extension developers
- Indicate stability of extension points: [stable], [experimental], [deprecated]
- Consider using extension point templates for consistency
- Reference AI-OS extension documents where appropriate:
  - [[ENGINEERING_PRINCIPLES.md]] for extension principles
  - [[IMPLEMENTATION_GUIDE.md]] for extension implementation guidelines
  - [[VALIDATION_ARCHITECTURE.md]] for extension validation approaches

## Diagram recommendations
Extension point diagram showing core and extension areas, or plugin architecture diagram
Use component diagrams to show how extensions connect to the core
Consider deployment diagrams to show extension packaging and distribution
Use sequence diagrams to show extension lifecycle and interaction patterns
Consider timeline diagrams to show extension versioning and compatibility
Use matrix diagrams to show extension characteristics (performance, security, etc.)
Consider hierarchy diagrams to show extension point relationships
Use data flow diagrams to show information exchange between core and extensions

## RFC 2119 guidance
Use "MAY" for extension points - implementations MAY provide additional extension points beyond those listed, and extensions MAY be built at these points following the specified mechanisms.
Use "SHOULD" to recommend certain extension mechanisms that align with architectural principles.
Use "MUST" for critical extension points that are essential to the part's extensibility goals.

---

# Conformance

## Purpose
Specifies how to determine if an implementation correctly realizes this architecture part. Should answer: "How do we know if something correctly implements this?"

## Expected contents
- Conformance criteria (what must be true to conform)
- Conformance testing approach or methodology
- Any certification or validation processes
- Levels of conformance (if applicable)
- Consequences of non-conformance
- Graceful degradation behaviors when partially conformant
- Extension compatibility considerations

## Writing guidance
- Make conformance criteria objective and checkable (avoid subjective judgments)
- Consider both functional and non-functional conformance
- Reference any conformance standards or frameworks used (ISO, IEEE, etc.)
- Be clear about what is required vs. recommended vs. optional
- Consider gradual conformance or profiles for different capability levels
- Define clear assessment methods for each criterion
- Consider automation potential for conformance checking
- Document any required tools, environments, or test harnesses
- Address how conformance is maintained over time (regression testing)
- Consider backward and forward compatibility in conformance

## Common mistakes
- Being too vague about conformance requirements ("it should work well")
- Making conformance impossible to verify (no clear test or measurement)
- Not distinguishing between different levels of conformance
- Forgetting to consider evolution over time (how conformance changes with versions)
- Overlooking practical conformance assessment methods (too expensive or complex)
- Not considering the cost of conformance verification
- Forgetting to document required test environments or tools
- Not addressing what happens when only partial conformance is achieved
- Overlooking extension or customization impacts on conformance
- Being inconsistent with conformance approaches in related parts

## Review expectations
- Reviewers should verify conformance criteria are objective and measurable
- Should check that both functional and non-functional aspects are covered
- Must verify that assessment methods are clear and practicable
- Should ensure required vs. recommended vs. optional is clearly distinguished
- Should confirm that evolution over time is considered
- Should validate that practical assessment methods are documented
- Should review that consequences of non-conformance are understood
- Should check that extension compatibility is addressed

## Quality indicators
- Conformance criteria are objective, measurable, and verifiable
- Both functional (what it does) and non-functional (how well it does it) aspects covered
- Clear distinction between mandatory, recommended, and optional criteria
- Assessment methods are clear, practical, and reasonably priced
- Consideration of how conformance evolves with versions and changes
- Documentation of required tools, environments, or test procedures
- Clear consequences of non-conformance (what happens if criteria aren't met)
- Consistency with conformance approaches in related architecture parts
- Consideration of extension and customization impacts

## Completion criteria
- Conformance criteria are clearly defined and documented
- For each criterion: clear statement, measurement/assessment method
- Clear distinction between required (MUST), recommended (SHOULD), optional (MAY)
- Assessment methods are objective and practicable
- Conformance testing approach or methodology is documented
- Any certification or validation processes are described
- Levels of conformance are defined if applicable (e.g., bronze, silver, gold)
- Consequences of non-conformance are explained
- Passes review by at least one architect
- Consistent with conformance approaches in related architecture parts

## Formatting conventions
- Use bullet points for conformance criteria
- Consider a conformance checklist or matrix for complex criteria
- Clearly distinguish between mandatory and optional requirements
- Reference any conformance testing tools or procedures
- For each conformance criterion, document:
  - **Criterion**: Clear statement of what must be true
  - **Rationale**: Why this criterion is important
  - **Requirement Level**: [MUST] required, [SHOULD] recommended, [MAY] optional
  - **Assessment Method**: How to verify or measure this criterion
  - **Evidence Required**: What proof or demonstration is needed
  - **Tools Needed**: Any specific tools or environments required
  - **Frequency**: How often conformance should be checked (per-release, continuous, etc.)
- Consider using a table format for multiple criteria with similar structure
- Reference AI-OS conformance documents where appropriate:
  - [[VALIDATION_ARCHITECTURE.md]] for validation approaches and methodologies
  - [[ENGINEERING_PRINCIPLES.md]] for quality standards and principles
  - [[ARCHITECTURE_DECISIONS.md]] for decided conformance levels or approaches

## Diagram recommendations
N/A - conformance is typically textual, but consider:
- Conformance matrix showing criteria vs. implementation options
- Conformance roadmap showing how conformance evolves over versions
- Consequence diagram showing what happens when criteria aren't met
- Decision tree showing conformance assessment process
- Flowchart showing conformance testing or validation process

## RFC 2119 guidance
Use "MUST" for conformance requirements - implementations MUST meet these criteria to be considered conformant to this architecture part.
Use "SHOULD" for recommended conformance characteristics that should be met unless justified.
Use "MAY" for optional conformance characteristics that may be present in some implementations.

---

# Security Considerations

## Purpose
Addresses security risks, threats, and mitigation strategies specific to this architecture part. Should answer: "What security concerns must be addressed, and how?"

## Expected contents
- Threat model or attack surface analysis
- Specific security risks and vulnerabilities
- Applied security principles (least privilege, defense in depth, etc.)
- Security mechanisms and controls implemented
- Data protection and privacy considerations
- Authentication and authorization approaches
- Audit logging and monitoring considerations
- Cryptography and key management practices
- Secure communication and data transfer
- Input validation and output encoding
- Security testing and validation approaches
- Incident response and recovery procedures
- Security dependencies and third-party components
- Compliance and regulatory requirements
- Security monitoring and alerting
- Security architecture review processes

## Writing guidance
- Reference established security frameworks or standards (OWASP, NIST, ISO 27001, etc.)
- Consider both intentional threats and accidental vulnerabilities
- Be specific about what is protected and from whom (threat actors, attack vectors)
- Explain the rationale behind security choices (trade-offs considered)
- Consider security throughout the lifecycle (design, implementation, deployment, operations)
- Address both technical and procedural security controls
- Consider defense in depth and layered security approaches
- Document assumptions about threat environment and attacker capabilities
- Reference AI-OS security standards and guidelines where applicable
- Consider security usability trade-offs
- Address security of extensions and integrations
- Consider security monitoring and observability needs
- Plan for security updates and vulnerability management

## Common mistakes
- Treating security as an afterthought or checklist
- Being too generic ("it's secure" without specifics)
- Missing important threat vectors (especially insider threats, supply chain)
- Not considering privilege escalation and lateral movement
- Overlooking data protection requirements (encryption, access controls)
- Forgetting operational security aspects (patching, monitoring, response)
- Inconsistent security mechanisms across interfaces or components
- Not considering security implications of configuration options
- Forgetting to secure audit logs and security-relevant data
- Overlooking security testing and validation approaches
- Not addressing third-party component and dependency security
- Being inconsistent with security approaches in related parts
- Forgetting to document security assumptions and limitations

## Review expectations
- Reviewers should verify threat model or attack surface analysis is documented
- Should check that specific security risks are identified with mitigations
- Must verify that security principles are applied (least privilege, defense in depth)
- Should ensure security mechanisms are documented for all interfaces
- Should confirm data protection measures are specified (encryption, access control)
- Should verify authentication and authorization approaches are appropriate
- Should check that audit logging and monitoring are addressed
- Should validate that cryptography and key management are considered
- Should review that security testing approaches are documented
- Should confirm third-party security considerations are addressed
- Should check consistency with AI-OS security standards and guidelines

## Quality indicators
- Threat model or attack surface analysis is documented and reasonable
- Specific security risks are identified with appropriate mitigations
- Security principles are consistently applied throughout the design
- Security mechanisms are documented for all trust boundaries and interfaces
- Data protection measures are specified (encryption at rest and in transit)
- Authentication and authorization approaches are appropriate for the use case
- Audit logging and monitoring cover security-relevant events
- Cryptography and key management follow established best practices
- Security testing and validation approaches are documented
- Third-party and dependency security considerations are addressed
- Consistency with AI-OS security standards and guidelines (if applicable)
- Clear rationale provided for security choices and trade-offs

## Completion criteria
- Threat model or attack surface analysis is documented
- Key security risks and vulnerabilities are identified with mitigations
- Applied security principles are documented (least privilege, defense in depth, etc.)
- Security mechanisms and controls are specified for trust boundaries
- Data protection and privacy considerations are addressed
- Authentication and authorization approaches are specified
- Audit logging and monitoring considerations are documented
- Cryptography and key management practices are considered
- Secure communication and data transfer mechanisms are specified
- Input validation and output encoding approaches are documented
- Security testing and validation approaches are described
- Incident response and recovery procedures are considered
- Security dependencies and third-party components are addressed
- Compliance and regulatory requirements are identified (if applicable)
- Passes review by at least one architect
- Consistent with security approaches in related architecture parts

## Formatting conventions
- Use bullet points grouped by security category
- Format: **Security Aspect**: Description and mitigation
- For each security consideration, document:
  - **Aspect**: Specific security concern being addressed
  - **Threat/Vulnerability**: What is being protected against
  - **Impact**: Potential consequences if not addressed
  - **Mitigation**: How the risk is reduced or eliminated
  - **Principle**: Which security principle is applied (least privilege, etc.)
  - **Responsibility**: Who or what is responsible for implementing/maintaining
  - **Validation**: How the effectiveness of the mitigation is verified
- Reference relevant security standards (OWASP Top 10, NIST CSF, CIS Controls, etc.)
- Consider using a threat modeling approach (STRIDE, PASTA, etc.)
- Include residual risk assessments where appropriate (what risk remains after mitigations)
- Reference AI-OS security documents where appropriate:
  - [[ENGINEERING_PRINCIPLES.md]] for security principles and guidelines
  - [[VALIDATION_ARCHITECTURE.md]] for security testing and validation approaches
  - [[ARCHITECTURE_DECISIONS.md]] for decided security mechanisms or approaches
  - [[IMPLEMENTATION_GUIDE.md]] for security implementation guidelines
  - [[GLOSSARY.md]] for shared security terminology

## Diagram recommendations
Security architecture diagram showing trust boundaries, data flows, and security controls
Attack surface diagram or threat model visualization
Use communication diagrams to show secure data flows
Consider sequence diagrams to show authentication and authorization flows
Use state diagrams to show security state transitions
Consider flowchart diagrams to show incident response processes
Use matrix diagrams to show security controls vs. threat vectors
Use hierarchy diagrams to show defense-in-depth layers
Use Sankey diagrams to show data flow with security transformations

## RFC 2119 guidance
Use "MUST" for critical security requirements - implementations MUST address these security considerations to be considered secure within the context of AI-OS.
Use "SHOULD" for recommended security measures that should be followed unless justified.
Use "MAY" for optional security enhancements that depend on specific threat models or use cases.
Use "MUST NOT" for prohibitions - things that MUST NOT be done (e.g., MUST NOT log passwords in plain text).
Use "SHOULD NOT" for recommendations against certain approaches that may have exceptions.

---

# Governance

## Purpose
Describes how decisions about this architecture part are made, maintained, and evolved over time. Should answer: "Who decides what changes, and how?"

## Expected contents
- Decision-making process for changes
- Roles and responsibilities for maintenance
- Change control and versioning approach
- Review and approval procedures
- Evolution and deprecation policies
- Any governing bodies or committees
- Escalation paths for unresolved issues
- Metrics and monitoring for governance effectiveness
- Documentation and knowledge transfer requirements
- Audit and compliance verification processes

## Writing guidance
- Be specific about processes, not just roles (who does what, when, how)
- Consider both technical and organizational governance aspects
- Reference any existing governance frameworks used (ITIL, COBIT, etc.)
- Make processes clear, actionable, and auditable
- Consider scalability of governance as the part and team evolve
- Address both routine operations and exception handling
- Document ownership transfer and succession planning
- Consider regulatory or compliance requirements that affect governance
- Plan for knowledge retention and transfer
- Establish metrics to measure governance effectiveness

## Common mistakes
- Being too vague about who decides what (unclear accountability)
- Not considering how governance scales over time (works for small team but not large)
- Forgetting to address evolution and obsolescence (how parts retire or change)
- Making processes too bureaucratic (slowing down innovation) or too loose (risky)
- Overlooking conflict resolution mechanisms (what happens when stakeholders disagree)
- Not considering geographic or temporal distribution of stakeholders
- Forgetting to document governance decisions and rationales
- Not addressing how governance integrates with project or product management
- Overlooking the need for governance training and awareness
- Forgetting to plan for governance evolution as the architecture matures

## Review expectations
- Reviewers should verify decision-making processes are clear and documented
- Should check that roles and responsibilities are specific and non-overlapping
- Must verify that change control and versioning approaches are defined
- Should ensure review and approval procedures are practical and followed
- Should confirm evolution and deprecation policies address end-of-life
- Should validate that governance scales with team and system size
- Should check that escalation paths are documented for unresolved issues
- Should review that metrics and monitoring for governance are established
- Should confirm documentation and knowledge transfer requirements are specified
- Should audit and compliance processes be addressed if relevant

## Quality indicators
- Clear decision-making process with documented escalation paths
- Specific roles and responsibilities with clear accountability
- Defined change control that balances agility with stability
- Practical review and approval procedures that are followed in practice
- Evolution and deprecation policies that address technological change
- Governance processes that scale with team size and system complexity
- Metrics and monitoring to assess governance effectiveness
- Documentation requirements that ensure knowledge retention
- Compliance verification approaches if regulatory requirements apply
- Consistency with AI-OS governance frameworks and ENGINEERING_PRINCIPLES.md

## Completion criteria
- Decision-making process for changes is documented
- Roles and responsibilities for maintenance are clearly defined
- Change control and versioning approach is specified
- Review and approval procedures are documented
- Evolution and deprecation policies address obsolescence
- Any governing bodies or committees are identified with charters
- Escalation paths for unresolved issues are documented
- Metrics and monitoring for governance effectiveness are established
- Documentation and knowledge transfer requirements are specified
- Passes review by at least one architect and one governance stakeholder
- Consistent with AI-OS governance documentation and ENGINEERING_PRINCIPLES.md

## Formatting conventions
- Use bullet points or a numbered list for linear processes
- Consider a RACI matrix for complex responsibility assignments (Responsible, Accountable, Consulted, Informed)
- Clearly distinguish between different types of decisions (architectural vs. operational)
- Reference any governance documentation or charters used
- For each governance aspect, document:
  - **Process/Area**: What is being governed (changes, releases, etc.)
  - **Decision-Making**: Who decides, how decisions are made, quorum requirements
  - **Roles & Responsibilities**: Specific duties assigned to individuals or groups
  - **Change Control**: How changes are proposed, reviewed, approved, implemented
  - **Review & Approval**: Procedures for reviewing work and granting approval
  - **Versioning**: How versions are numbered, tracked, and managed
  - **Evolution**: How the part evolves over time (feature additions, refactoring)
  - **Deprecation**: How functionality is phased out and removed
  - **Escalation**: How disagreements or blockers are resolved
  - **Metrics**: How governance effectiveness is measured and monitored
  - **Documentation**: What must be documented and retained
  - **Knowledge Transfer**: How knowledge is shared and preserved
- Reference AI-OS governance documents where appropriate:
  - [[ENGINEERING_PRINCIPLES.md]] for engineering governance principles
  - [[ARCHITECTURE_DECISIONS.md]] for how architectural decisions are governed
  - [[IMPLEMENTATION_GUIDE.md]] for implementation governance considerations
  - [[VALIDATION_ARCHITECTURE.md]] for validation governance approaches
  - [[GLOSSARY.md]] for shared governance terminology

## Diagram recommendations
Governance model diagram showing decision flows and responsibility assignments
Timeline showing governance rhythms or review cycles
Use swimlane diagrams to show who does what in governance processes
Consider flowchart diagrams to show decision-making and approval processes
Use state diagrams to show how governance states change over time
Consider matrix diagrams to show responsibility assignments (RACI)
Use Gantt charts to show governance timing and scheduling
Use hierarchy diagrams to show governance structure and reporting lines

## RFC 2119 guidance
Use "SHOULD" for governance processes - changes to this part SHOULD follow the specified governance processes unless exceptional circumstances apply.
Use "MUST" for critical governance requirements that are essential to decision-making integrity.
Use "MAY" for optional governance enhancements that depend on specific organizational needs.

---

# Architecture Decisions

## Purpose
Records significant architectural decisions made for this part, including rationale and alternatives considered. Should answer: "What key decisions were made, and why?"

## Expected contents
- List of significant decisions (ADR format recommended)
- For each: context, decision, status, consequences
- Alternatives considered and why rejected
- Decision makers and dates
- Links to more detailed documentation if needed
- Decision revisit conditions or expiration (if applicable)
- Impact on related parts or systems
- Risk assessment and mitigation strategies

## Writing guidance
- Use Architectural Decision Record (ADR) format or similar lightweight format
- Focus on decisions with lasting architectural impact (not trivial or implementation-level)
- Be honest about trade-offs, uncertainties, and assumptions made
- Keep decision records updated as understanding evolves or decisions are revisited
- Consider decision reversibility and establish clear revisit conditions
- Reference related AI-OS documents where appropriate instead of duplicating information
- Ensure decisions are traceable to architectural principles, constraints, or requirements
- Document any risks identified and mitigation strategies planned
- Consider the impact of decisions on related parts, systems, or stakeholders

## Common mistakes
- Recording trivial or implementation-level decisions (should be architecturally significant)
- Not documenting the rationale clearly or thoroughly enough
- Forgetting to mention rejected alternatives and why they were not chosen
- Making decisions sound unanimous when they weren't (document dissenting views)
- Not updating decisions when new information arises or conditions change
- Lacking clear context that explains why the decision was necessary
- Not considering long-term consequences or evolution implications
- Forgetting to identify decision makers and timing for accountability
- Duplicating information that should be referenced from other AI-OS documents
- Not establishing clear conditions for when decisions should be revisited

## Review expectations
- Reviewers should verify each decision is architecturally significant
- Should check that context clearly explains the problem or opportunity
- Must verify that rationale is thorough, honest about trade-offs, and references principles
- Should ensure alternatives are genuinely considered and rejection reasons are valid
- Should confirm decision makers and dates are documented for accountability
- Should validate that consequences (both positive and negative) are documented
- Should check that decisions are consistent with AI-OS principles and constraints
- Should review that revisit conditions are established for decisions that may change
- Should confirm links to related AI-OS documents are used instead of duplication

## Quality indicators
- Each decision addresses a significant architectural question or problem
- Context clearly situates the decision in time and explains why it was needed
- Rationale is thorough, references principles/constraints, and acknowledges trade-offs
- Rejected alternatives are documented with clear, valid reasons for not choosing them
- Decision makers and dates are specified for accountability and historical tracking
- Consequences include both benefits and drawbacks or risks
- Decisions are consistent with AI-OS architectural vision, principles, and constraints
- Revisit conditions are established for decisions that may need future review
- Links to related AI-OS documents are used appropriately instead of duplication
- Risk assessments and mitigation strategies are documented where relevant

## Completion criteria
- Significant architectural decisions are documented using ADR or similar format
- For each decision: clear context, thorough rationale, documented alternatives
- Decision makers and dates are specified for accountability
- Consequences (both positive and negative) are documented
- Links to related AI-OS documents are used instead of duplicating information
- Revisit conditions or expiration criteria are established where appropriate
- Passes review by at least one architect
- Consistent with decision documentation in related architecture parts
- Aligns with AI-OS architectural decision-making processes in ENGINEERING_PRINCIPLES.md

## Formatting conventions
- Use ADR format or similar lightweight decision recording format
- For each decision, document:
  - **Title**: Clear, concise description of the decision
  - **Status**: [PROPOSED], [ACCEPTED], [DEPRECATED], [SUPERSEDED]
  - **Context**: The problem, opportunity, or driver that prompted the decision
  - **Decision**: What was decided, stated clearly and unequivocally
  - **Rationale**: Why this decision was made, referencing principles, constraints, etc.
  - **Alternatives Considered**: Other options that were evaluated
  - **Rejection Reasons**: Why each alternative was not chosen
  - **Consequences**: Both positive outcomes and potential drawbacks/risks
  - **Decision Makers**: Who made the decision (individuals, roles, or groups)
  - **Date**: When the decision was made
  - **Revisit Conditions**: When or under what conditions this decision should be reviewed
  - **Links**: References to related AI-OS documents instead of duplicating content
- Use consistent decision naming and numbering (e.g., ADR-001, ADR-002)
- Decide on storage location: inline in this document, separate ADR files, or linked documents
- Reference AI-OS decision documents where appropriate:
  - [[ARCHITECTURE_DECISIONS.md]] for global AI-OS architectural decisions
  - [[ENGINEERING_PRINCIPLES.md]] for decision-making principles and processes
  - [[VALIDATION_ARCHITECTURE.md]] for decision validation approaches
  - [[GLOSSARY.md]] for shared decision-making terminology

## Diagram recommendations
Decision tree showing alternatives and chosen path
Timeline showing decision evolution over time
Use influence diagrams to show factors that influenced the decision
Consider matrix diagrams to compare alternatives against criteria
Use flowcharts to show decision-making and approval processes
Use Gantt charts to show decision timing and revisit schedules

## RFC 2119 guidance
Use "WILL" for decisions that have been made - the architecture WILL incorporate these decisions based on the stated rationale.
Use "SHOULD" for decision characteristics that enhance quality but may have exceptions.
Use "MAY" for optional decision documentation practices that depend on context.

---

# Cross References

## Purpose
Provides links to related documentation, standards, and other relevant resources. Should answer: "Where can I find more information about related topics?"

## Expected contents
- Links to other AI-OS architecture parts
- References to industry standards and specifications
- Links to relevant source code or repositories
- References to key design documents or studies
- Any external resources that informed this part
- Explicit encouragement to reference core AI-OS documents instead of duplicating concepts

## Writing guidance
- Use consistent linking conventions
- Provide brief descriptions of what each reference covers
- Keep references current and working
- Consider grouping references by type or relevance
- Explain why each reference is relevant
- **Strongly encourage referencing AI-OS master documents instead of duplicating their content**
- Reference AI-OS documents by their official names using link syntax

## Common mistakes
- Broken or outdated links
- Not explaining why references are included
- Including irrelevant or tangential references
- Inconsistent link formatting
- Missing important internal references
- **Duplicating content that should be referenced from core AI-OS documents**
- Including references that are already covered by referenced AI-OS documents
- Not using the standard AI-OS document naming conventions

## Review expectations
- Reviewers should verify all important references are included and working
- Should check that references to AI-OS master documents are used instead of duplication
- Must verify that link formatting is consistent and correct
- Should ensure each reference includes a brief explanation of its relevance
- Should confirm that redundant references to information available in core documents are avoided
- Should validate that external references are current and authoritative

## Quality indicators
- All relevant references are included with working links
- Each reference includes a brief description of why it's relevant
- References to AI-OS master documents are used instead of duplicating their content
- External references are current, authoritative, and properly attributed
- Link formatting is consistent throughout the document
- No redundant references to information available in core AI-OS documents
- References are grouped logically for easy scanning

## Completion criteria
- Links to other AI-OS architecture parts are included where relevant
- References to industry standards and specifications are current
- Links to relevant source code or repositories are provided
- References to key design documents or studies are included
- Core AI-OS documents are referenced instead of duplicating their concepts
- Passes review by at least one architect
- Reference validation confirms all links are working and relevant

## Formatting conventions
- Use markdown link syntax: [Description](URL)
- For internal references to AI-OS parts: [[Related Part Title]]
- **Always reference these core AI-OS documents instead of duplicating their content:**
  - [[AI_OS_MASTER_CONTEXT.md]] - Overall AI-OS context and vision
  - [[ENGINEERING_PRINCIPLES.md]] - Engineering principles and guidelines
  - [[ARCHITECTURE_DECISIONS.md]] - Global architectural decisions
  - [[IMPLEMENTATION_GUIDE.md]] - Implementation considerations and patterns
  - [[VALIDATION_ARCHITECTURE.md]] - Validation approaches and methodologies
  - [[GLOSSARY.md]] - Shared terminology and definitions
  - [[REPOSITORY_ECOSYSTEM.md]] - Repository structure and organization
- Group references logically (standards, internal AI-OS parts, external resources, etc.)
- Consider using a reference table for many links with similar structure
- Regularly verify link validity and update as needed
- For each reference, provide a brief description (1-2 lines) of what it covers and why it's relevant
- Consider using reference tags or categories for better organization

## Diagram recommendations
N/A - references are typically textual, but consider showing reference relationships if complex
Consider a reference matrix showing what information is sourced from which documents
Use a dependency diagram to show which AI-OS documents this part relies on

## RFC 2119 guidance
Use "SHOULD" for references - users SHOULD consult these references for additional context and deeper understanding.
Use "MUST" for referencing core AI-OS documents when their content is relevant - implementations MUST NOT duplicate information that is already authoritatively defined in [[AI_OS_MASTER_CONTEXT.md]], [[ENGINEERING_PRINCIPLES.md]], or other core documents.

---

# Mermaid Diagrams

## Purpose
Contains Mermaid syntax diagrams that visualize key aspects of this architecture part. Should answer: "What diagrams help explain this part visually?"

## Expected contents
- Mermaid diagram syntax for key views
- Component diagrams, sequence diagrams, state diagrams, etc.
- Clear labels and legends for diagrams
- Diagrams that complement textual descriptions
- Notes on diagram versioning and maintenance
- Diagram accessibility considerations
- Consistent styling and theming

## Writing guidance
- Use diagrams to clarify, not replace, textual descriptions
- Keep diagrams readable and not overly complex (aim for immediate comprehension)
- Use consistent styling and notation across all diagrams in the document
- Ensure diagrams accurately reflect the textual content (no contradictions)
- Consider audience expertise when choosing diagram types and detail level
- Label all elements clearly and provide legends where needed
- Use directional arrows consistently to show flow or dependencies
- Consider color usage for meaning (but ensure diagrams work in grayscale)
- Keep text legible at normal viewing sizes
- Align diagram complexity with the architectural significance of what's being shown
- Update diagrams when the architecture evolves to avoid drift
- Consider providing alternative text descriptions for accessibility

## Common mistakes
- Creating diagrams that contradict textual descriptions (causes confusion)
- Making diagrams too detailed (implementation-level instead of architectural)
- Making diagrams too abstract (lacks specific, actionable information)
- Not maintaining diagrams as architecture evolves (leads to misinformation)
- Using inconsistent notation across diagrams (increases cognitive load)
- Forgetting to explain diagrams in text (assumes diagram reading proficiency)
- Overusing diagrams when text would be clearer
- Making diagrams that are impossible to read or understand
- Not considering color blindness or visual impairments
- Using inconsistent arrow styles or meanings
- Missing labels or unclear element identification

## Review expectations
- Reviewers should verify diagrams accurately reflect textual content
- Should check that diagrams are readable and comprehensible
- Must verify that diagram notation is consistent within the document
- Should ensure each diagram has a clear purpose and adds value
- Should confirm that diagrams are properly explained in surrounding text
- Should validate that diagram complexity matches the architectural significance
- Should review that diagrams are maintainable and versionable
- Should check accessibility considerations (labels, contrast, alternatives)

## Quality indicators
- Each diagram has a clear purpose that complements the textual content
- Diagrams are readable and understandable at a glance
- Notation is consistent across all diagrams in the document
- Diagrams accurately reflect the current architectural description
- Diagram complexity is appropriate for the concept being illustrated
- All elements are clearly labeled and legible
- Legends are provided where symbols or colors have specific meanings
- Diagrams consider accessibility (contrast, labeling, alternatives)
- Diagrams are maintainable and can be easily updated
- Diagram placement enhances rather than disrupts reading flow

## Completion criteria
- Relevant Mermaid diagrams are included for key architectural views
- Each diagram has a clear caption or explanation
- Diagram syntax is valid Mermaid that will render correctly
- Diagrams accurately represent the architectural concepts described
- Notation is consistent across all diagrams in the document
- Diagrams are readable and not overly complex
- All diagram elements are clearly labeled
- Diagrams complement rather than duplicate textual information
- Passes review by at least one architect
- Diagram maintenance considerations are addressed

## Formatting conventions
- Wrap Mermaid syntax in triple backticks with language specifier
- Use ```mermaid``` blocks consistently
- Provide clear captions or explanations for each diagram (what it shows and why it matters)
- Consider diagram placement relative to related text (keep diagrams close to what they explain)
- Use consistent diagram numbering if multiple (Figure 1, Figure 2, etc.)
- Ensure diagrams are legible in both light and dark themes
- Consider using Mermaid themes or configuring for consistent appearance
- For complex diagrams, consider breaking into multiple simpler diagrams
- Provide alternative text descriptions for accessibility when possible
- Reference diagram numbers in text when discussing specific diagrams

## Diagram recommendations
**Component Diagrams**: Show structural elements and their relationships (use for Components section)
- Component: rectangle with component name
- Interface: circle or lollipop notation
- Dependency: dashed or solid arrow with label
- Port: square on component edge for required/provided interfaces

**Sequence Diagrams**: Show behavioral interactions over time (use for Responsibilities, Relationships, Runtime Behaviour)
- Participant: actor or component at top
- Lifeline: vertical dashed line
- Message: horizontal arrow with label
- Activation: box on lifeline showing processing time
- Return: dashed arrow back to sender
- Alternative: alt/else blocks for conditional logic
- Loop: loop block for repetitive interactions

**State Diagrams**: Show how elements change state in response to events (use for Invariants, Runtime Behaviour)
- State: rounded rectangle with state name
- Transition: arrow labeled with event/condition
- Initial state: solid circle pointing to first state
- Final state: concentric circles
- Choice: diamond for conditional transitions
- Junction: small circle for merging paths
- History: H or HN for remembering substates

**Relationship Diagrams**: Show connections between elements (use for Relationships section)
- Entity: rectangle or circle for components, parts, systems
- Relationship: line connecting entities
- Cardinality: notation near ends (1:1, 1:*, *:1, *:*)
- Role: label describing purpose of relationship
- Type: solid line (aggregation), dashed line (dependency), etc.
- Direction: arrows showing flow or dependency direction

**Layer Diagrams**: Show architectural stratification (use for Architectural Context)
- Layer: horizontal band with layer name
- Component: rectangle within layer showing what belongs there
- Dependency: arrow between layers (usually downward only)
- Interface: interface symbols between layers
- Strictness: solid lines (strict), dashed lines (allowed violations)

**Decision Trees**: Show alternatives and chosen paths (use for Architecture Decisions)
- Decision: diamond with question or criterion
- Alternative: rectangle showing option or outcome
- Consequence: text describing results of choice
- Probability: percentage or likelihood if applicable
- Resource: cost, time, or effort required
- Recommended: highlight or mark the chosen path

**Flowcharts**: Show processes or algorithms (use for Runtime Behaviour, Governance)
- Process: rectangle with action or step
- Decision: diamond with yes/no question
- Input/Output: parallelogram for data
- Start/End: oval or rounded rectangle
- Arrow: flow direction with optional label
- Subprocess: double-stroked rectangle for reusable steps
- Delay: trapezoid for waiting periods
- Database: cylinder for data storage

**Additional Diagram Types**:
- Activity Diagram: Show workflows and business processes
- Communication Diagram: Focus on object interactions rather than timing
- Deployment Diagram: Show physical deployment and infrastructure
- Package Diagram: Show organization of elements into groups
- Use Case Diagram: Show system functionality from user perspective
- Class Diagram: Show structural relationships (use sparingly at architectural level)
- Object Diagram: Show specific instances (typically too detailed for architecture)
- Timing Diagram: Show state changes over time with precise timing
- Data Flow Diagram: Show information movement and transformation
- Radar Chart: Show multiple qualities or trade-offs
- Pie Chart: Show proportional distribution (use cautiously)
- Bar Chart: Show comparative quantities
- Sequence Number: Show message numbering in complex interactions

## RFC 2119 guidance
Diagrams themselves don't use RFC 2119 language, but diagram captions SHOULD use appropriate RFC 2119 language when describing requirements or behaviors shown.
Use "MUST" in diagram captions for critical requirements that are essential.
Use "SHOULD" for recommended characteristics that should be present unless justified.
Use "MAY" for optional features or variations that may be included.

---

# References

## Purpose
Lists all sources cited or consulted in creating this architecture part. Should answer: "What sources inform this documentation?"

## Expected contents
- Formal references to books, papers, standards
- URLs to specifications or documentation
- Internal documents or communications
- Any other sources that contributed to this part
- Consistent citation format
- Clear separation between AI-OS internal references and external sources
- Access dates for online resources
- Version information for specifications and standards

## Writing guidance
- Use a consistent citation format (APA, IEEE, ACM, etc.)
- Include all referenced material, not just direct quotes or paraphrases
- Make it easy for readers to locate sources (provide enough detail)
- Consider annotating references with relevance notes (how they were used)
- Keep the list complete and accurate
- Separate AI-OS internal documents from external references
- For online sources, include access date and consider archiving
- For standards and specifications, include version numbers
- Reference AI-OS master documents properly instead of duplicating content

## Common mistakes
- Incomplete or inconsistent citations
- Not citing sources that informed decisions or conclusions
- Citing sources not actually consulted or read
- Inconsistent citation formatting (mixing styles)
- Missing access dates for online sources (making verification impossible)
- Not including version information for standards and specifications
- Duplicating information that should be referenced from AI-OS core documents
- Including references that are not actually relevant to the content
- Forgetting to reference AI-OS master documents when their content is used
- Not distinguishing between primary and secondary sources

## Review expectations
- Reviewers should verify all factual claims are properly referenced
- Should check that citation formatting is consistent throughout
- Must verify that online sources have access dates
- Should ensure AI-OS internal documents are referenced instead of duplicated
- Should confirm that references are actually relevant to the content
- Should validate that citation information is sufficient to locate sources
- Should review that AI-OS master documents are properly referenced

## Quality indicators
- All factual claims, data, and quoted material are properly referenced
- Citation format is consistent throughout the document
- Online sources include access dates (and optionally archive links)
- AI-OS internal documents are referenced using [[link syntax]]
- External references are properly formatted and verifiable
- No duplication of content that exists in AI-OS master documents
- References are relevant and actually support the content
- Sufficient information is provided to locate each reference
- Version information is included for standards and specifications

## Completion criteria
- All content that requires attribution is properly referenced
- Consistent citation format is used throughout
- Online sources include access date (YYYY-MM-DD format)
- AI-OS internal documents are referenced using proper link syntax: [[Document Name]]
- External references include sufficient bibliographic information
- No duplication of content from [[AI_OS_MASTER_CONTEXT.md]], [[ENGINEERING_PRINCIPLES.md]], or other core documents
- Passes review by at least one architect
- Reference verification confirms all sources are legitimate and accessible

## Formatting conventions
- Choose one citation style and use it consistently (APA 7th, IEEE, etc.)
- Include all necessary bibliographic information for each reference type:
  - Books: Author(s), Title, Publisher, Year, ISBN
  - Papers: Author(s), Title, Journal/Conference, Volume, Pages, Year, DOI
  - Standards: Organization, Standard Number, Title, Year, Version
  - Specifications: Organization, Title, Version, Year, URL
  - Web pages: Author(s), Title, Website, URL, Access Date (YYYY-MM-DD)
  - AI-OS documents: [[Document Title]] using internal link syntax
- For URLs: include access date in format: [Accessed: YYYY-MM-DD]
- Consider using reference management tools (Zotero, Mendeley, etc.) for consistency
- When referencing AI-OS documents, use the official names:
  - [[AI_OS_MASTER_CONTEXT.md]] for master context
  - [[ENGINEERING_PRINCIPLES.md]] for engineering principles
  - [[ARCHITECTURE_DECISIONS.md]] for architectural decisions
  - [[IMPLEMENTATION_GUIDE.md]] for implementation guidance
  - [[VALIDATION_ARCHITECTURE.md]] for validation architecture
  - [[GLOSSARY.md]] for shared terminology
  - [[REPOSITORY_ECOSYSTEM.md]] for repository structure
- Consider using footnotes or endnotes for less critical references
- For internal AI-OS references, prefer link syntax over URLs when possible
- Regularly verify reference links and update access dates

## Diagram recommendations
N/A - references are typically textual
Consider a bibliography diagram for very large reference sets
Use a reference timeline to show when sources were published
Consider a reference network to show relationships between sources

## RFC 2119 guidance
Use "SHOULD" for references - users SHOULD consult these references to understand the basis for architectural decisions.
Use "MUST" for referencing AI-OS master documents when their content is relevant - implementations MUST NOT duplicate information that is authoritatively defined in [[AI_OS_MASTER_CONTEXT.md]], [[ENGINEERING_PRINCIPLES.md]], or other core AI-OS documents.

---

## Template Usage Instructions

To use this template:
1. Copy this file to a new location in your architecture documentation
2. Rename the file to match your architecture part (e.g., `DATA_STORAGE.md`)
3. Fill in each section according to the guidance provided
4. Remove any sections that don't apply (with explanation why)
5. Update cross-references as needed, referencing AI-OS master documents instead of duplicating content
6. Ensure all links and references are valid
7. Review for consistency with other AI-OS architecture parts
8. Validate all Mermaid diagrams for correctness and consistency
9. Verify RFC 2119 terminology usage throughout
10. Complete the Architecture Author Checklist as you progress
11. Complete the final Publication Checklist before submission

## Publication Quality Checklist

Before considering an architecture part complete, verify:
- [ ] All required sections are completed (purpose, scope, components, etc.)
- [ ] Architecture Author Checklist items are addressed
- [ ] Content is technology-neutral and implementation-independent
- [ ] RFC 2119 terminology is used correctly and consistently
- [ ] All Mermaid diagrams are valid, properly formatted, and add value
- [ ] Cross references to AI-OS master documents are used instead of duplicating content
- [ ] Internal references use [[link syntax]] format
- [ ] External references are properly formatted with access dates
- [ ] Content is clear, concise, and free of implementation details
- [ ] Diagrams accurately reflect textual content
- [ ] Terminology is consistent with [[GLOSSARY.md]] and other AI-OS documents
- [ ] Security considerations are adequately addressed
- [ ] Governance processes are defined where relevant
- [ ] Architecture decisions are recorded with rationale
- [ ] Conformance criteria are objective and verifiable
- [ ] Invariants are checkable and always true
- [ ] Constraints are identified with rationale
- [ ] Extension points are intentional and discoverable
- [ ] Relationships are well-defined and explained
- [ ] Interfaces specify contracts, not implementations
- [ ] Responsibilities are clear and non-overlapping
- [ ] Principles are actionable and decision-guiding
- [ ] Architectural context shows relationships to other parts
- [ ] Audience is properly identified with specific information needs
- [ ] Scope is well-defined with explicit inclusions/exclusions
- [ ] Purpose is clear and concise
- [ ] Template usage instructions have been followed

## Maintenance

This template itself SHOULD be reviewed and updated periodically to reflect:
- Lessons learned from using the template
- Changes in architectural best practices
- Feedback from architecture part authors
- Evolving AI-OS architectural vision
- Updates to referenced standards or frameworks
- Changes in AI-OS master documents ([[ENGINEERING_PRINCIPLES.md]], etc.)
- Advances in diagramming standards and tools
- Evolution of RFC 2119 usage guidelines

*End of Template*