# ChatGPT Prompt Library for AI-OS

## Document Metadata
- **Document ID**: chatgpt-prompts-library-v2.1
- **Version**: 2.1.0
- **Status**: ACTIVE
- **Last Updated**: 2026-08-07
- **Next Review**: 2026-11-07
- **Owner**: AI-OS Documentation Architecture Team
- **Related Documents**: 
  - [[AI_OS_MASTER_CONTEXT.md]]
  - [[ENGINEERING_PRINCIPLES.md]]
  - [[IMPLEMENTATION_GUIDE.md]]
  - [[ARCHITECTURE_PROMPTS.md]]
  - [[CLAUDE_PROMPTS.md]]
  - [[REVIEW_PROMPTS.md]]
- **Conformance Level**: L4 (Full specification compliance including all principles and invariants)
- **Validation Status**: VALIDATED
- **Tags**: prompt-library, chatgpt, ai-os, engineering-workflows

## Purpose
This document serves as the official ChatGPT prompt library for the AI-OS (Artificial Intelligence Operating System) project, providing standardized, validated prompts designed to leverage ChatGPT's capabilities while maintaining strict alignment with AI-OS architectural principles, engineering standards, and governance requirements. Unlike general-purpose prompt collections, this library is specifically engineered to support AI-OS workflows including architecture analysis, component design, documentation creation, code review, research, diagramming, improvement initiatives, validation activities, and governance processes.

The library ensures that all ChatGPT interactions within the AI-OS ecosystem produce consistent, high-quality outputs that adhere to specification requirements, engineering principles, and validation standards, thereby reducing variability in AI-assisted work and maintaining architectural integrity across distributed teams and autonomous agent operations.

## Scope
This prompt library covers:
- **Architecture Prompts**: System analysis, component design, and Architecture Decision Record (ADR) generation
- **Documentation Prompts**: Specification documentation, API references, and user guide creation
- **Review Prompts**: Code quality assessment, architectural conformance validation, and security reviews
- **Research Prompts**: Technology evaluation, pattern mining, and future trends assessment
- **Diagram Prompts**: Architecture diagrams, event flows, and data model visualizations
- **Improvement Prompts**: Refactoring suggestions, performance optimization, and technical debt reduction
- **Validation Prompts**: Test case generation, validation script creation, and conformance checklist building
- **Governance Prompts**: Council decision support, policy creation, and audit preparation

This library does NOT cover:
- Prompts for other LLM providers (see CLAUDE_PROMPTS.md, ARCHITECTURE_PROMPTS.md)
- Implementation-specific coding prompts (handled through Skills ecosystem)
- Runtime configuration or deployment prompts
- Prompts requiring access to proprietary or restricted information

## Audience
This document is intended for:
- **AI-OS Architects**: Creating and validating architectural designs and decisions
- **AI-OS Engineers**: Implementing, reviewing, and improving AI-OS components and services
- **Documentation Specialists**: Creating specification-aligned documentation and user guides
- **Quality Assurance Engineers**: Conducting reviews, validations, and conformance assessments
- **Research Engineers**: Evaluating technologies, patterns, and trends for AI-OS evolution
- **AI Agents**: Autonomous agents operating within AI-OS governance structures
- **Governance Councils**: Claude Council, LLM Council, and specialized governance bodies
- **Contributors**: External contributors submitting changes to AI-OS specification or ecosystems
- **Auditors**: Internal and external auditors verifying conformance to AI-OS requirements

## Prompt Design Philosophy
All prompts in this library adhere to the following AI-OS-specific design principles:

### 1. **Specification-First Alignment**
Every prompt requires explicit reference to relevant AI-OS Architecture Specification parts (Parts 1-15) to ensure outputs remain within conformance boundaries and avoid specification drift.

### 2. **Principle-Driven Outputs**
Prompts are engineered to produce results that align with AI-OS engineering principles including architectural integrity, verification-first development, observability by design, security and privacy, performance and efficiency, maintainability and clarity, ecosystem awareness, and validation-first execution.

### 3. **Governance-Compliant Structure**
Prompt outputs include mechanisms for traceability, auditability, and human oversight where appropriate, supporting AI-OS governance frameworks including Council mechanisms and FinalJudge oversight capabilities.

### 4. **Validation-Oriented Expectations**
Each prompt defines clear success criteria, failure modes, and validation approaches to enable objective assessment of output quality and conformance to requirements.

### 5. **Ecosystem-Aware Design**
Prompts consider impact on Skills, MCP, and Repository ecosystems, ensuring outputs support extension point contracts and maintain ecosystem compatibility.

### 6. **Technology-Neutral Formulation**
While prompts may reference implementation examples, they focus on behavioral contracts and architectural principles rather than language-specific details to maintain implementation independence.

## Prompt Categories
The library is organized into eight functional categories that align with AI-OS engineering workflows and governance structures:

1. **Architecture Prompts** - For analyzing, designing, and documenting system architecture
2. **Documentation Prompts** - For creating specification-aligned and user-facing documentation
3. **Review Prompts** - For assessing code quality, conformance, and security
4. **Research Prompts** - For evaluating technologies, patterns, and future trends
5. **Diagram Prompts** - For generating architectural and behavioral visualizations
6. **Improvement Prompts** - For identifying refactoring, optimization, and debt reduction opportunities
7. **Validation Prompts** - For creating test cases, validation scripts, and conformance checklists
8. **Governance Prompts** - For supporting council decisions, policy creation, and audit preparation

Each category contains specialized prompts designed for specific workflows within that domain.

## Prompt Metadata Standards
Every prompt in this library includes standardized metadata to ensure consistency, traceability, and proper usage:

- **Purpose**: Clear statement of what the prompt is designed to accomplish
- **When to Use**: Specific scenarios and conditions for appropriate application
- **Expected Inputs**: Required context, constraints, and reference materials
- **Expected Outputs**: Specific deliverables, formats, and quality standards
- **Recommended GPT Model**: Optimal ChatGPT model version for best results
- **Context Size**: Approximate token capacity needed for effective operation
- **Reasoning Depth**: Required level of analytical or creative reasoning
- **Success Criteria**: Measurable indicators of prompt effectiveness
- **Failure Modes**: Common ways the prompt might produce inadequate results
- **Related Prompts**: Complementary or alternative prompts for related tasks
- **Version**: Prompt-specific version for tracking improvements
- **Last Validated**: Date of last validation against AI-OS requirements
- **Validation Method**: Approach used to confirm prompt effectiveness

## Prompt Lifecycle
Prompts in this library follow a defined lifecycle to ensure ongoing quality and relevance:

1. **Creation**: New prompts are created following the Prompt Engineering Guidelines
2. **Validation**: Prompts are validated against AI-OS requirements using the Validation Architecture
3. **Deployment**: Validated prompts are added to the library with appropriate metadata
4. **Monitoring**: Prompt usage and effectiveness are monitored through feedback mechanisms
5. **Review**: Prompts are reviewed quarterly or when significant specification changes occur
6. **Revision**: Prompts are updated based on validation results, feedback, or specification evolution
7. **Deprecation**: Prompts are deprecated when superseded or no longer aligned with requirements
8. **Retirement**: Deprecated prompts are archived with rationale for removal

## Prompt Versioning
Each prompt follows semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Incompatible changes that affect prompt purpose or expected outputs
- **MINOR**: Backward-compatible enhancements or additional capabilities
- **PATCH**: Bug fixes, clarification improvements, or minor adjustments

Version changes are documented in the prompt's metadata and tracked through the AI-OS Architecture Decision Record (ADR) process when they represent significant changes to prompt functionality.

## Prompt Governance
Prompt library governance follows AI-OS ecosystem principles:

### Governance Bodies
- **Primary**: Documentation Architecture Team maintains curation and quality standards
- **Secondary**: AI-OS Architecture Review Board (ARB) reviews significant changes
- **Tertiary**: Community feedback through standard contribution processes

### Change Management
- All new prompts require validation before inclusion
- Significant prompt modifications require ADR documentation
- Prompt deprecation requires community notification and migration path
- Version updates follow semantic versioning principles

### Quality Assurance
- Automated validation against specification requirements
- Regular conformance checking with Engineering Principles
- Peer review by Documentation Architecture Team
- Community feedback integration through standard channels

## Prompt Validation
Every prompt undergoes validation to ensure it meets AI-OS requirements:

### Validation Criteria
1. **Specification Alignment**: Output must not contradict AI-OS Architecture Specification
2. **Principle Adherence**: Output must align with documented engineering principles
3. **Output Quality**: Generated content must meet defined quality standards
4. **Usability**: Prompt must produce actionable, usable results in target context
5. **Traceability**: Output must include appropriate references and audit trails
6. **Governance Compliance**: Output must support appropriate oversight mechanisms

### Validation Methods
- Automated conformance testing using Validation Architecture (Part 11)
- Manual review by Documentation Architecture Team
- Pilot testing in representative AI-OS workflows
- Feedback collection from prompt users
- Principle adherence checking against ENGINEERING_PRINCIPLES.md

## Prompt Quality Metrics
Prompt effectiveness is measured using standardized metrics:

### Quantitative Metrics
- **Adherence Rate**: Percentage of outputs meeting specification requirements
- **Principle Compliance Score**: Alignment with engineering principles (0-10 scale)
- **Usability Rating**: User-reported effectiveness in real workflows (1-5 scale)
- **Revision Frequency**: Number of updates per quarter (lower indicates stability)
- **Adoption Rate**: Percentage of target audience regularly using the prompt

### Qualitative Metrics
- **Clarity Assessment**: How clearly the prompt communicates requirements
- **Completeness Evaluation**: Whether all necessary aspects are addressed
- **Actionability Judgment**: Whether outputs enable clear next steps
- **Traceability Verification**: Presence of appropriate references and audit capabilities
- **Governance Alignment**: Support for appropriate oversight mechanisms

## Prompt Anti-patterns
The following approaches should be avoided when using or creating prompts for AI-OS:

### 1. **Specification Drift**
Creating prompts that encourage outputs violating or deviating from AI-OS Architecture Specification Parts 1-15.

### 2. **Principle Violation**
Designing prompts that produce outputs contradicting AI-OS engineering principles.

### 3. **Governance Evasion**
Creating prompts that attempt to bypass or minimize required oversight mechanisms.

### 4. **Over-Specification**
Constraining prompts excessively, limiting exploration of valid alternatives.

### 5. **Under-Specification**
Providing insufficient context, leading to irrelevant or incorrect outputs.

### 6. **Ecosystem Neglect**
Ignoring impact on Skills, MCP, and Repository ecosystems in prompt design.

### 7. **Technology Lock-in**
Creating prompts that favor specific implementations over architectural principles.

### 8. **Validation Avoidance**
Designing prompts that make validation difficult or impossible.

## Prompt Maintenance
Ongoing maintenance ensures the prompt library remains effective and aligned:

### Regular Activities
- **Quarterly Review**: Systematic evaluation of all prompts for relevance and effectiveness
- **Usage Monitoring**: Tracking adoption and effectiveness metrics
- **Feedback Integration**: Incorporating user suggestions and issue reports
- **Specification Synchronization**: Updating prompts to reflect specification changes
- **Principle Alignment**: Ensuring prompts remain aligned with engineering principles
- **Validation Refresh**: Re-validating prompts against current requirements

### Maintenance Triggers
- Specification updates (Parts 1-15)
- Significant engineering principle evolution
- Major version changes in ChatGPT models
- Identified effectiveness issues through monitoring
- Community feedback indicating problems
- Governance body recommendations

### Maintenance Process
1. Issue identification through monitoring or feedback
2. Impact assessment and prioritization
3. Prompt revision following Prompt Engineering Guidelines
4. Validation against updated requirements
5. Deployment with updated version and metadata
6. Notification of changes to affected stakeholders
7. Archival of previous versions with rationale

## Navigation and Cross-References
This document is designed for easy navigation and integration with the broader AI-OS architecture documentation:

### Internal Navigation
- Use the table of contents to jump directly to prompt categories
- Each prompt includes links to related prompts within and across categories
- Cross-reference links use double-bracket notation for easy navigation

### External References
- [[AI_OS_MASTER_CONTEXT.md]]: Integrated view of current AI-OS state
- [[ENGINEERING_PRINCIPLES.md]]: Philosophical foundation for architectural decisions
- [[IMPLEMENTATION_GUIDE.md]]: Guidance for maintaining architectural conformance
- [[ARCHITECTURE_PROMPTS.md]]: Architecture-specific prompts for other LLMs
- [[CLAUDE_PROMPTS.md]]: Claude-specific prompts for AI-OS workflows
- [[REVIEW_PROMPTS.md]]: Specialized prompts for code and architecture review
- [[VALIDATION_ARCHITECTURE.md]]: Framework for validating prompt outputs

### Related Documentation Sets
This prompt library is part of a comprehensive documentation ecosystem:
- **Architecture Documentation**: Parts 1-15 specification documents
- **Engineering Documentation**: Principles, guidelines, and implementation guides
- **Prompt Libraries**: Specialized collections for different LLMs and use cases
- **Validation Documentation**: Frameworks and procedures for ensuring conformance
- **Governance Documentation**: Processes and structures for AI-OS oversight
- **Ecosystem Documentation**: Skills, MCP, and Repository ecosystem guides

---
# ChatGPT Prompt Library Contents

## Architecture Prompts

### System Architecture Analysis
**Purpose**: Analyze and evaluate AI-OS system architecture for conformance, bottlenecks, and improvement opportunities while maintaining strict adherence to specification requirements.
**When to Use**: Evaluating architectural decisions, proposing system changes, or conducting architecture conformance assessments.
**Expected Inputs**: 
- Specific architecture parts to analyze (Parts 1-15 references)
- Current implementation details or reference points
- Conformance level targets (L1-L4)
- Specific concerns or hypotheses to investigate
**Expected Outputs**: 
- Detailed architecture analysis report with findings, recommendations, and prioritized improvement areas
- Specification references for all observations
- Identification of gaps between specification and implementation
- Risk assessment for proposed changes
**Recommended Model**: GPT-4 Turbo
**Context Size**: 8-12K tokens
**Reasoning Depth**: Analytical - requires synthesis of specification requirements with implementation observations
**Success Criteria**: 
- Report includes specific specification part references
- Findings distinguish between conformance levels
- Recommendations include implementation effort estimates
- Analysis identifies both strengths and improvement opportunities
**Failure Modes**: 
- Producing generic analysis without specification grounding
- Missing correlation between findings and specification parts
- Overlooking architectural invariants or constraints
- Providing recommendations that violate engineering principles
**Related Prompts**: 
- [[Component Design Prompt]]
- [[Architecture Decision Record (ADR) Generator]]
- [[Architectural Conformance Review]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Conformance checking against Parts 1-15 and Engineering Principles

**Prompt Engineering Tips**:
- Specify which architecture parts you want analyzed (e.g., "Focus on Part 7: AI Agency and Governance")
- Ask for concrete examples from the codebase when possible
- Request trade-off analysis for any proposed changes
- Require explicit specification citations for all major findings
- Ask for validation approach to verify analysis accuracy

### Component Design Prompt
**Purpose**: Design new AI-OS components (managers, services, or extension points) following specification guidelines and engineering principles.
**When to Use**: Creating new Core Managers, Engineering Services, ecosystem extensions, or significant component modifications.
**Expected Inputs**: 
- Component type (Manager, Service, Extension Point)
- Intended responsibilities and domain
- Integration points with existing components
- Performance, scalability, and observability requirements
- Relevant specification parts (Part 3 for Managers, Part 5-6 for Services, Part 9-13 for Extensions)
**Expected Outputs**: 
- Component design document with interfaces, responsibilities, event contracts, and integration points
- Specification compliance matrix
- Event schema definitions with versioning
- Resource quota requirements
- Observability and error handling approaches
**Recommended Model**: GPT-4
**Context Size**: 6-10K tokens
**Reasoning Depth**: Design - requires creative solution within strict constraint boundaries
**Success Criteria**: 
- Design strictly follows BaseService contracts where applicable
- Event schemas include correlation_id and causation_id
- Resource requirements are explicitly quantified
- Design extension point compatibility is addressed
- All specification references are accurate and complete
**Failure Modes**: 
- Designing components that violate Kernel as Pure Orchestrator principle
- Omitting required event metadata (correlation/causation IDs)
- Ignoring resource quota enforcement requirements
- Creating tight coupling through direct service references
- Forgetting observability and error handling considerations
**Related Prompts**: 
- [[System Architecture Analysis]]
- [[API Reference Documentation]]
- [[Refactoring Suggestion Generator]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Conformance checking against Component Design principles in Parts 3-6 and Engineering Principles

**Prompt Engineering Tips**:
- Specify the component type (Manager, Service, Extension Point)
- Define the scope and boundaries clearly
- Ask for event schemas and StateManager integration details
- Request complexity analysis (time/space) where relevant
- Ask for validation approach to ensure design correctness
- Require explicit handling of error conditions and edge cases

### Architecture Decision Record (ADR) Generator
**Purpose**: Generate Architecture Decision Records following AI-OS ADR format and governance requirements.
**When to Use**: Documenting significant architectural decisions that affect system properties, principles, or invariants.
**Expected Inputs**: 
- Clear statement of the decision being recorded
- Context and problem motivating the decision
- Alternatives considered and rejected
- Specification parts affected by the decision
- Relevant engineering principles
**Expected Outputs**: 
- Complete ADR document with Context, Problem, Alternatives, Decision, Rationale, Trade-offs, and Consequences sections
- Specification part references for all claims
- Principle alignment analysis
- Impact assessment on conformance levels
- Migration path or backward compatibility considerations
**Recommended Model**: GPT-4 Turbo
**Context Size**: 4-8K tokens
**Reasoning Depth**: Analytical - requires weighing alternatives against principles and specification
**Success Criteria**: 
- ADR follows standard format with all required sections
- Decision is clearly tied to specification requirements or principles
- Trade-offs are quantified where possible
- Alternatives are seriously considered and documented
- Consequences include both short and long-term impacts
**Failure Modes**: 
- Creating ADRs for trivial or reversible decisions
- Omitting specification or principle references
- Failing to consider meaningful alternatives
- Not addressing long-term implications (6-24 months)
- Missing concrete migration or compatibility plans
**Related Prompts**: 
- [[System Architecture Analysis]]
- [[Policy and Guideline Creation]]
- [[Governance Principles Application]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: ADR format validation against Part 0 and Engineering Principles Section 22

**Prompt Engineering Tips**:
- Clearly state the decision being recorded
- Ask for quantification of trade-offs where possible
- Request alternative solutions that were considered and rejected
- Require explicit links to specification parts and existing ADRs
- Ask for impact analysis on specific conformance levels (L1-L4)
- Request validation approach for decision correctness

## Documentation Prompts

### Specification Documentation
**Purpose**: Generate clear, specification-aligned documentation for AI-OS components and processes that treats documentation as a legal contract.
**When to Use**: Creating or updating architecture specification documents, design documents, or technical specifications.
**Expected Inputs**: 
- Target specification part or concept
- Audience (developers, architects, operators)
- Required conformance level (L1-L4)
- Related specification parts for cross-referencing
- Examples or use cases to include (if applicable)
**Expected Outputs**: 
- Well-structured documentation that explains purpose, interfaces, behavior, and usage guidelines
- Clear distinction between specification (what must be) and implementation (how it's done)
- Validation criteria and conformance requirements
- Cross-references to related specification parts
- Examples of correct and incorrect usage
**Recommended Model**: GPT-4
**Context Size**: 6-10K tokens
**Reasoning Depth**: Explanatory - requires translating specification requirements into clear documentation
**Success Criteria**: 
- Documentation treats architectural requirements as binding contracts
- Clear specification/implementation distinction maintained
- Includes validation criteria and conformance thresholds
- Provides concrete examples of correct usage
- Contains appropriate cross-references to related specifications
**Failure Modes**: 
- Blurring specification and implementation details
- Omitting validation criteria or conformance requirements
- Missing cross-references to related specification parts
- Using implementation-specific language in specification documents
- Failing to distinguish between MUST, SHOULD, and MAY language
**Related Prompts**: 
- [[API Reference Documentation]]
- [[User Guide Creation]]
- [[Technical Debt Reduction]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Documentation principles validation against Part 0 Section 16 and ENGINEERING_PRINCIPLES.md Documentation Principles

**Prompt Engineering Tips**:
- Specify the target audience (developers, architects, operators)
- Ask for examples of correct and incorrect usage
- Request mermaid diagram syntax for visual explanations
- Require explicit handling of specification vs. implementation distinction
- Ask for validation approach to confirm documentation accuracy
- Require inclusion of conformance requirements and validation criteria

### API Reference Documentation
**Purpose**: Generate API documentation for AI-OS services, managers, and extension points that follows specification contracts and enables proper integration.
**When to Use**: Documenting public interfaces of AI-OS components, creating integration guides, or updating API references.
**Expected Inputs**: 
- Interface or class being documented
- Language preferences for examples (TypeScript, Python, etc.)
- Target audience (developers, integrators)
- Specification parts defining the interface
- Version information and compatibility requirements
**Expected Outputs**: 
- Comprehensive API reference with method signatures, parameters, return values, exceptions, and usage examples
- Preconditions, postconditions, and invariants documented
- Error conditions and exception handling behavior specified
- Concrete code examples in requested languages
- Thread-safety and performance characteristics included
- Versioning information and deprecation notices
**Recommended Model**: GPT-4
**Context Size**: 6-10K tokens
**Reasoning Depth**: Explanatory - requires precise translation of interfaces into documentation
**Success Criteria**: 
- Documents all public methods with complete signatures
- Includes preconditions, postconditions, and invariants
- Specifies error conditions and exception handling
- Provides working code examples in requested languages
- Documents thread-safety and performance characteristics
- Includes versioning and deprecation information
**Failure Modes**: 
- Missing critical method signatures or parameters
- Omitting preconditions, postconditions, or invariants
- Failing to document error conditions and exception handling
- Providing non-working or incorrect code examples
- Overlooking thread-safety considerations
- Missing versioning or compatibility information
**Related Prompts**: 
- [[Specification Documentation]]
- [[Component Design Prompt]]
- [[Review Prompts]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: API documentation validation against Parts 3-6 and Service Framework contracts

**Prompt Engineering Tips**:
- Specify the interface or class being documented
- Ask for complexity analysis (time/space) where relevant
- Request versioning information and deprecation notices
- Ask for concrete code examples in TypeScript and Python
- Require explicit documentation of error conditions
- Ask for validation approach to confirm API accuracy

### User Guide Creation
**Purpose**: Create user guides and tutorials for AI-OS features and workflows that are task-oriented and enable successful adoption.
**When to Use**: Creating documentation for end-users, operators, or engineers learning specific AI-OS capabilities.
**Expected Inputs**: 
- Target feature or workflow
- Audience skill level (beginner, intermediate, advanced)
- Prerequisites and assumed knowledge
- Common use cases and scenarios
- Expected outcomes and success criteria
**Expected Outputs**: 
- Step-by-step guides with prerequisites, procedures, expected outcomes, and troubleshooting tips
- Clear learning objectives stated at beginning
- Progressive disclosure from simple to complex concepts
- Validation steps to confirm successful completion
- Troubleshooting sections covering common issues
- Before/after examples showing impact
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Procedural - requires breaking down complex workflows into teachable steps
**Success Criteria**: 
- Starts with clear learning objectives
- Uses progressive disclosure (simple to complex)
- Includes validation steps for confirmation
- Provides troubleshooting for common issues
- Contains before/after examples showing impact
- Addresses target skill level appropriately
**Failure Modes**: 
- Starting without clear learning objectives
- Presenting advanced concepts before prerequisites
- Missing validation or confirmation steps
- Omitting troubleshooting for known issues
- Lacking concrete examples or before/after comparisons
- Misjudging audience skill level
**Related Prompts**: 
- [[Specification Documentation]]
- [[Test Case Generation]]
- [[Validation Script Creation]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: User guide validation against Documentation Principles and Engineering Principles Section 16

**Prompt Engineering Tips**:
- Define the target skill level (beginner, intermediate, advanced)
- Ask for troubleshooting sections covering common issues
- Request before/after examples showing the impact
- Ask for clear learning objectives and success criteria
- Require validation steps to confirm successful completion
- Request progressive disclosure approach in documentation

## Review Prompts

### Code Quality Review
**Purpose**: Review AI-OS code for quality, maintainability, and adherence to engineering principles while identifying improvement opportunities.
**When to Use**: Reviewing pull requests, code changes, or conducting quality assessments of existing code.
**Expected Inputs**: 
- Specific files or modules to review
- Focus areas (testability, observability, architectural integrity, etc.)
- Relevant specification parts and engineering principles
- Quality thresholds and acceptance criteria
**Expected Outputs**: 
- Detailed review report with issues categorized by severity
- Specific code examples illustrating each finding
- Recommendations with before/after code samples where applicable
- Impact assessment on system qualities (maintainability, performance, etc.)
- Prioritization of issues (P0, P1, P2)
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Evaluative - requires analysis against quality standards and principles
**Success Criteria**: 
- Issues are clearly categorized by severity and type
- Specific code examples illustrate each finding
- Recommendations include actionable improvement steps
- Before/after code samples provided for refactoring suggestions
- Impact assessment quantifies effects on system qualities
- Issues are prioritized based on risk and impact
**Failure Modes**: 
- Providing vague feedback without specific examples
- Missing severity categorization or impact assessment
- Failing to provide actionable recommendations
- Overlooking engineering principle violations
- Not providing before/after examples for suggested changes
- Ignoring testability, observability, or architectural integrity
**Related Prompts**: 
- [[Architectural Conformance Review]]
- [[Security Review]]
- [[Refactoring Suggestion Generator]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Code review validation against Engineering Principles Section 6-7 and Parts 4-7

**Prompt Engineering Tips**:
- Specify the files or modules to review
- Ask for specific checks (e.g., "Check for tight coupling violations")
- Request refactoring suggestions with before/after code samples
- Ask for impact quantification (performance, maintainability, etc.)
- Require severity categorization (P0, P1, P2) for all findings
- Request validation approach to confirm review accuracy

### Architectural Conformance Review
**Purpose**: Validate that AI-OS implementation conforms to the architecture specification and identifies deviations requiring remediation.
**When to Use**: Verifying implementation against specification Parts 1-15, preparing for audits, or assessing conformance levels.
**Expected Inputs**: 
- Specific specification parts to check against
- Implementation details or code to review
- Target conformance level (L1-L4)
- Particular concerns or focus areas
- Available evidence (test results, documentation, etc.)
**Expected Outputs**: 
- Conformance report indicating compliance level, deviations, and remediation recommendations
- Evidence of conformance (code quotes, test results, etc.)
- Remediation priority (P0, P1, P2) for deviations
- Specification references for all non-conformities
- Impact assessment of deviations on system qualities
**Recommended Model**: GPT-4 Turbo
**Context Size**: 8-12K tokens
**Reasoning Depth**: Evaluative - requires systematic comparison against specification requirements
**Success Criteria**: 
- Report clearly states conformance level (L1-L4)
- Deviations are accompanied by specification evidence
- Remediation includes specific, actionable steps
- Priority levels (P0, P1, P2) are justified by impact
- Report distinguishes between L1-L4 conformance requirements
- Includes validation approach to confirm assessment accuracy
**Failure Modes**: 
- Failing to distinguish between conformance levels (L1-L4)
- Missing specification evidence for claimed deviations
- Providing unactionable remediation recommendations
- Overlooking invariants or constraints in assessment
- Not providing validation approach for assessment
- Missing impact analysis of deviations on system qualities
**Related Prompts**: 
- [[System Architecture Analysis]]
- [[Code Quality Review]]
- [[Conformance Checklist Builder]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Conformance review validation against Part 11 Validation Architecture and Engineering Principles Section 12.12

**Prompt Engineering Tips**:
- Specify which specification parts to check against
- Ask for evidence of conformance (code quotes, test results)
- Request remediation priority (P0, P1, P2) for deviations
- Ask for validation approach to confirm assessment accuracy
- Require explicit handling of L1-L4 conformance distinctions
- Request impact analysis of deviations on system qualities

### Security Review
**Purpose**: Conduct security-focused review of AI-OS components and implementations following security principles and identifying vulnerabilities.
**When to Use**: Evaluating security implications of changes, conducting security assessments, or preparing for security audits.
**Expected Inputs**: 
- Components or implementations to review
- Specific security concerns or threat model
- Relevant security principles and standards
- Available evidence (code, configurations, etc.)
- Required assurance level
**Expected Outputs**: 
- Security assessment report with vulnerabilities, risk levels, and mitigation strategies
- Specific vulnerability locations and descriptions
- Risk assessment (likelihood and impact) for each finding
- Concrete mitigation strategies with implementation guidance
- CVSS scores or risk rankings where applicable
- Specific CWE identifiers for vulnerabilities found
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Evaluative - requires analysis against security standards and principles
**Success Criteria**: 
- Report includes specific vulnerability locations and descriptions
- Each finding has risk assessment (likelihood and impact)
- Provides concrete mitigation strategies with guidance
- Includes CVSS scores or risk rankings where applicable
- Lists specific CWE identifiers for vulnerabilities
- Distinguishes between exploitable and theoretical vulnerabilities
**Failure Modes**: 
- Providing vague security feedback without specifics
- Missing risk assessment (likelihood/impact) for findings
- Failing to provide concrete mitigation strategies
- Overlooking security principles in assessment
- Not providing CWE identifiers or CVSS scores
- Missing distinction between exploitable and theoretical issues
**Related Prompts**: 
- [[Code Quality Review]]
- [[Architectural Conformance Review]]
- [[Policy and Guideline Creation]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Security review validation against Engineering Principles Section 13 and Part 12 Security & Safety

**Prompt Engineering Tips**:
- Specify the threat model or security concerns
- Ask for CVSS scores or risk rankings where applicable
- Request specific CWE identifiers for vulnerabilities found
- Ask for validation approach to confirm review accuracy
- Require explicit handling of least privilege access
- Request input validation and output encoding verification

## Research Prompts

### Technology Evaluation
**Purpose**: Research and evaluate technologies, frameworks, or approaches for potential integration with AI-OS while maintaining architectural integrity.
**When to Use**: Researching new technologies for AI-OS ecosystems, evaluating integration approaches, or assessing technology suitability.
**Expected Inputs**: 
- Specific technology, framework, or approach to evaluate
- Evaluation criteria (performance, compatibility, security, etc.)
- Target integration point (Skills, MCP, Repository, etc.)
- Relevant specification parts and constraints
- Required compatibility level (L1-L4)
**Expected Outputs**: 
- Comparative analysis report with recommendations
- Compatibility assessment with AI-OS architecture
- Integration considerations and requirements
- Maturity, community support, and licensing evaluation
- Migration path and rollback considerations
- Impact assessment on architectural principles
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires evaluation against multiple criteria and constraints
**Success Criteria**: 
- Report includes specific evaluation criteria and scoring
- Provides clear recommendations with justification
- Details compatibility assessment and requirements
- Evaluates maturity, community support, and licensing
- Includes migration path and rollback considerations
- Assesses impact on architectural principles and invariants
**Failure Modes**: 
- Providing generic evaluation without specific criteria
- Missing compatibility assessment with architecture
- Omitting migration path or rollback considerations
- Overlooking licensing or maturity factors
- Failing to assess impact on architectural principles
- Not providing clear go/no-go recommendations
**Related Prompts**: 
- [[Pattern Mining and Analysis]]
- [[Future Trends Assessment]]
- [[Technical Debt Reduction]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Technology evaluation validation against Extensibility Principles and Engineering Principles Section 15

**Prompt Engineering Tips**:
- Specify evaluation criteria (performance, compatibility, security, etc.)
- Ask for proof-of-concept complexity estimates
- Request migration path and rollback considerations
- Ask for validation approach to confirm evaluation accuracy
- Require explicit handling of extensibility principles
- Request impact assessment on specification conformance

### Pattern Mining and Analysis
**Purpose**: Identify recurring patterns in AI-OS codebase suitable for skill creation, abstraction, or ecosystem contribution.
**When to Use**: Analyzing codebase for duplication, identifying abstraction opportunities, or evaluating ecosystem contributions.
**Expected Inputs**: 
- Codebase scope (specific components, time period, etc.)
- Pattern types to consider (structural, behavioral, etc.)
- Abstraction goals (skill creation, manager development, etc.)
- Relevant specification parts and engineering principles
- Acceptable complexity and maintenance thresholds
**Expected Outputs**: 
- Pattern analysis report with frequency, impact, and abstraction recommendations
- Specific pattern examples with code samples
- Duplication reduction potential metrics
- Abstraction approach recommendations with trade-offs
- Ecosystem contribution suitability assessment
- Maintenance and evolution considerations
**Recommended Model**: GPT-4
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires identification and evaluation of patterns across codebase
**Success Criteria**: 
- Report includes specific pattern examples with code samples
- Provides duplication reduction potential metrics
- Details abstraction approach recommendations with trade-offs
- Assesses ecosystem contribution suitability
- Includes maintenance and evolution considerations
- Distinguishes between beneficial and harmful abstractions
**Failure Modes**: 
- Providing vague pattern descriptions without examples
- Missing quantification of duplication or impact
- Failing to assess maintenance implications
- Overlooking potential for harmful abstractions
- Not providing concrete abstraction approaches
- Missing ecosystem contribution suitability assessment
**Related Prompts**: 
- [[Technology Evaluation]]
- [[Refactoring Suggestion Generator]]
- [[Technical Debt Reduction]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Pattern analysis validation against Engineering Principles Sections 6-7 and Extensibility Principles

**Prompt Engineering Tips**:
- Specify the scope (codebase subset, time period, component types)
- Ask for metrics on duplication reduction potential
- Request examples of how the pattern would be abstracted
- Ask for validation approach to confirm analysis accuracy
- Require explicit consideration of abstraction trade-offs
- Request impact assessment on maintenance and evolution

### Future Trends Assessment
**Purpose**: Assess emerging technology trends and their potential impact on AI-OS architecture while maintaining principled evolution.
**When to Use**: Planning for AI-OS evolution, evaluating strategic technology directions, or assessing long-term architectural implications.
**Expected Inputs**: 
- Specific technology trend or area to assess
- Time horizon (near-term, mid-term, long-term)
- Relevant AI-OS components or systems that might be affected
- Architectural principles and evolution guidelines
- Required confidence level for predictions
**Expected Outputs**: 
- Trend analysis report with relevance assessment
- Adoption timeline and maturity factors
- Architectural implications and evolution considerations
- Risks and opportunities identification
- Monitoring and experimentation recommendations
- Specification evolution proposals where appropriate
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Strategic - requires evaluating trends against architectural evolution principles
**Success Criteria**: 
- Report includes specific relevance assessment with justification
- Provides adoption timeline with maturity factors
- Details architectural implications and evolution considerations
- Identifies specific risks and opportunities
- Includes monitoring and experimentation recommendations
- Distinguishes between hype and substantive technological shifts
**Failure Modes**: 
- Providing vague trend assessment without specifics
- Missing timeline or maturity considerations
- Failing to identify concrete risks and opportunities
- Overlooking hype vs. substance distinction
- Not providing monitoring or experimentation guidance
- Missing distinction between short and long-term impacts
**Related Prompts**: 
- [[Technology Evaluation]]
- [[Policy and Guideline Creation]]
- [[Evolution Principles Application]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Future trends validation against Evolution Principles and Engineering Principles Section 17

**Prompt Engineering Tips**:
- Specify time horizon (near-term, mid-term, long-term)
- Ask for specific AI-OS components that would be affected
- Request recommendations for monitoring or experimentation
- Ask for validation approach to confirm assessment accuracy
- Require explicit handling of evolution principles
- Request distinction between hype and substantive shifts

## Diagram Prompts

### Architecture Diagram Generation
**Purpose**: Generate architecture diagrams for AI-OS components, interactions, and data flows that follow specification conventions and communicate architectural intent clearly.
**When to Use**: Creating documentation, communicating architecture, or visualizing system structure and behavior.
**Expected Inputs**: 
- Diagram type (component, sequence, deployment, etc.)
- Specific components or interactions to show
- Target audience and technical level
- Relevant specification parts and conventions
- Desired detail level (overview, detailed, etc.)
**Expected Outputs**: 
- Mermaid diagram syntax with clear visualization of architectural elements and relationships
- Consistent notation and styling following AI-OS conventions
- Legends and explanations for complex diagrams
- Appropriate detail level for target audience
- Both static structure and dynamic behavior where relevant
**Recommended Model**: GPT-4
**Context Size**: 4-8K tokens
**Reasoning Depth**: Visual - requires translating architectural concepts into clear visual representations
**Success Criteria**: 
- Diagram uses consistent notation and styling
- Includes legends and explanations for complexity
- Shows appropriate detail level for audience
- Displays both static structure and dynamic behavior when relevant
- Follows AI-OS diagramming conventions and standards
- Is technically accurate and specification compliant
**Failure Modes**: 
- Using inconsistent notation or styling
- Missing legends or explanations for complex elements
- Showing inappropriate detail level for audience
- Omitting relevant static structure or dynamic behavior
- Violating AI-OS diagramming conventions
- Being technically inaccurate or non-compliant
**Related Prompts**: 
- [[Event Flow Diagram]]
- [[Data Model Diagram]]
- [[Component Design Prompt]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Diagram validation against Engineering Principles Section 10 and diagramming conventions

**Prompt Engineering Tips**:
- Specify diagram type (component, sequence, deployment, etc.)
- Ask for zoom levels or detail appropriate for audience
- Request alternative layouts or representations
- Ask for validation approach to confirm diagram accuracy
- Require explicit handling of complex diagram explanations
- Request inclusion of relevant specification references

### Event Flow Diagram
**Purpose**: Create event flow diagrams showing AI-OS event-driven interactions that enable tracing, debugging, and understanding of asynchronous behavior.
**When to Use**: Documenting or debugging event-driven behavior, understanding system responses to triggers, or analyzing failure propagation.
**Expected Inputs**: 
- Starting event or trigger
- Specific event types or chains to follow
- Target audience and use case (documentation, debugging, etc.)
- Relevant specification parts (Part 2 Event System)
- Desired scope (happy path, error conditions, etc.)
**Expected Outputs**: 
- Sequence diagram or flow chart showing event propagation, handling, and side effects
- Correlation IDs, causation relationships, and event schemas
- Error handling and failure propagation paths
- Both happy paths and error conditions shown
- Timing and ordering guarantees where relevant
- Monitoring and observability points included
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires tracing event chains through system components
**Success Criteria**: 
- Diagram shows correlation IDs and causation relationships
- Includes event schemas with versioning information
- Displays error handling and failure propagation paths
- Shows both happy paths and error conditions
- Includes timing and ordering guarantees where applicable
- Contains monitoring and observability points
- Accurately represents event-driven behavior
**Failure Modes**: 
- Missing correlation IDs or causation relationships
- Omitting event schemas or versioning information
- Failing to show error handling or failure paths
- Only showing happy paths or only error conditions
- Missing timing and ordering considerations
- Lacking monitoring or observability points
- Inaccurately representing actual event flow
**Related Prompts**: 
- [[Architecture Diagram Generation]]
- [[Data Model Diagram]]
- [[Review Prompts]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Event flow validation against Part 2 Event System and Engineering Principles Section 12.2

**Prompt Engineering Tips**:
- Specify the starting event or trigger
 Ask for alternative paths based on event content or conditions
- Request inclusion of monitoring and observability points
- Ask for validation approach to confirm diagram accuracy
- Require explicit handling of error conditions and timing
- Request specification references for event types used

### Data Model Diagram
**Purpose**: Generate data model diagrams for AI-OS StateManager, storage schemas, and knowledge graphs that follow standard notation and communicate data structure clearly.
**When to Use**: Designing or documenting data persistence aspects, understanding entity relationships, or planning data evolution.
**Expected Inputs**: 
- Data domain or bounded context to model
- Specific entities, attributes, or relationships to include
- Target audience and technical level
- Relevant specification parts (Part 8 Memory Architecture, Part 10 Observability)
- Desired detail level (conceptual, logical, physical)
**Expected Outputs**: 
- Entity-relationship diagram or class diagram showing data structures and relationships
- Entities, attributes, relationships, and constraints shown
- Cardinality and participation constraints included
- Indexes and query patterns identified
- Versioning and evolution considerations addressed
- Follows standard ER or UML notation
**Recommended Model**: GPT-4
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires understanding data relationships and translating to visual form
**Success Criteria**: 
- Diagram follows standard ER or UML notation
- Shows entities, attributes, relationships, and constraints
- Includes cardinality and participation constraints
- Identifies indexes and query patterns
- Addresses versioning and evolution considerations
- Accurately represents the data model being documented
- Appropriate detail level for target audience
**Failure Modes**: 
- Using non-standard or unclear notation
- Missing entities, attributes, or relationships
- Omitting cardinality or participation constraints
- Failing to identify indexes or query patterns
- Overlooking versioning or evolution considerations
- Being technically inaccurate about the data model
- Showing inappropriate detail level for audience
**Related Prompts**: 
- [[Architecture Diagram Generation]]
- [[Event Flow Diagram]]
- [[Component Design Prompt]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Data model validation against Parts 8, 9, 10 and Engineering Principles Section 10

**Prompt Engineering Tips**:
- Specify the data domain or bounded context
- Ask for normalization level and denormalization justification
- Request sample queries or access patterns
- Ask for validation approach to confirm diagram accuracy
- Require explicit handling of versioning and evolution
- Request specification references for data elements used

## Improvement Prompts

### Refactoring Suggestion Generator
**Purpose**: Suggest refactoring opportunities to improve AI-OS code quality and maintainability while preserving behavioral contracts and architectural integrity.
**When to Use**: Identifying technical debt, improvement opportunities, or planning refactoring initiatives.
**Expected Inputs**: 
- Code area or smell to address (duplication, complexity, etc.)
- Specific files, modules, or components to analyze
- Relevant specification parts and engineering principles
- Acceptable risk and effort thresholds
- Desired outcomes (maintainability, performance, etc.)
**Expected Outputs**: 
- Refactoring plan with specific changes, impact analysis, and implementation steps
- Before/after metrics (complexity, duplication, etc.)
- Risk assessment and effort estimation
- Step-by-step migration plan with rollback considerations
- Impact on architectural qualities (maintainability, performance, etc.)
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Evaluative - requires identifying improvement opportunities and planning safe changes
**Success Criteria**: 
- Plan includes specific, actionable refactoring changes
- Provides before/after metrics (complexity, duplication, etc.)
- Includes risk assessment and effort estimation
- Details step-by-step migration plan with rollback
- Assesses impact on architectural qualities
- Preserves behavioral contracts and specification compliance
**Failure Modes**: 
- Suggesting changes that violate specification requirements
- Providing vague or unactionable refactoring ideas
- Missing before/after metrics or impact analysis
- Failing to include risk assessment or effort estimates
- Not providing migration plan or rollback considerations
- Overlooking preservation of behavioral contracts
- Suggesting changes that tighten coupling or reduce observability
**Related Prompts**: 
- [[Code Quality Review]]
- [[Technical Debt Reduction]]
- [[Performance Optimization Prompt]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Refactoring validation against Engineering Principles Sections 6-8 and Parts 4-7

**Prompt Engineering Tips**:
- Specify the code area or smell to address
- Ask for before/after metrics (complexity, duplication, etc.)
- Request step-by-step migration plan with rollback considerations
- Ask for validation approach to confirm refactoring safety
- Require explicit handling of risk and effort estimation
- Request impact assessment on architectural qualities

### Performance Optimization Prompt
**Purpose**: Identify and suggest performance optimization opportunities in AI-OS that respect resource quotas and architectural principles.
**When to Use**: Addressing performance concerns, doing capacity planning, or evaluating system efficiency.
**Expected Inputs**: 
- Specific scenario or workload to optimize
- Performance data or measurements (if available)
- Relevant specification parts and engineering principles
- Resource quota constraints and limits
- Acceptable trade-offs between performance and other qualities
**Expected Outputs**: 
- Performance analysis with bottlenecks, optimization suggestions, and expected impact
- Profiling data or measurement methodology
- Before/after performance estimates with confidence intervals
- Resource usage impact analysis
- Trade-off evaluation between performance, readability, maintainability
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires identifying bottlenecks and evaluating optimization trade-offs
**Success Criteria**: 
- Analysis identifies specific performance bottlenecks
- Provides optimization suggestions with expected impact
- Includes profiling data or measurement methodology
- Details before/after performance estimates with confidence
- Analyzes resource usage impact
- Evaluates trade-offs between performance and other qualities
- Respects resource quotas and architectural principles
**Failure Modes**: 
- Providing vague performance analysis without specifics
- Missing identification of concrete bottlenecks
- Failing to include profiling or measurement approach
- Not providing before/after estimates with confidence intervals
- Overlooking resource quota constraints
- Ignoring trade-offs between performance and other qualities
- Suggesting optimizations that violate architectural principles
**Related Prompts**: 
- [[Code Quality Review]]
- [[Refactoring Suggestion Generator]]
- [[Technical Debt Reduction]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Performance validation against Engineering Principles Sections 5-6 and Resource Management principles

**Prompt Engineering Tips**:
- Specify the scenario or workload to optimize
- Ask for profiling data or measurement methodology
- Request before/after performance estimates with confidence intervals
- Ask for validation approach to confirm optimization safety
- Require explicit handling of resource quota constraints
- Request trade-off evaluation between performance and other qualities

### Technical Debt Reduction
**Purpose**: Identify and prioritize technical debt items in AI-OS for remediation while focusing on architectural debt that threatens system integrity.
**When to Use**: Planning maintenance sprints, refactoring initiatives, or conducting technical debt assessments.
**Expected Inputs**: 
- Debt categories to consider (code, architecture, documentation, test)
- Specific codebase areas or components to analyze
- Relevant specification parts and engineering principles
- Acceptable effort and risk thresholds
- Desired outcomes (debt reduction, risk mitigation, etc.)
**Expected Outputs**: 
- Technical debt registry with items ranked by impact, effort, and risk
- Categorization of debt by type with specific examples
- Quantification of impact (time, risk, opportunity cost)
- Dependency analysis between debt items
- Concrete, actionable remediation items with implementation guidance
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Evaluative - requires identifying, categorizing, and prioritizing technical debt
**Success Criteria**: 
- Registry includes specific debt items with examples
- Debt is categorized by type (code, architecture, etc.)
- Provides quantification of impact (time, risk, opportunity cost)
- Includes dependency analysis between debt items
- Details concrete, actionable remediation items
- Focuses on architectural debt threatening system integrity
- Distinguishes between regular and architectural technical debt
**Failure Modes**: 
- Providing vague debt listings without specifics
- Missing categorization by debt type
- Failing to quantify impact or provide metrics
- Omitting dependency analysis between debt items
- Not providing concrete remediation items
- Overlooking architectural debt that threatens integrity
- Treating all debt as equivalent without differentiation
**Related Prompts**: 
- [[Refactoring Suggestion Generator]]
- [[Code Quality Review]]
- [[Performance Optimization Prompt]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Technical debt validation against Engineering Principles Sections 3-4 and Technical Debt Awareness principle

**Prompt Engineering Tips**:
- Specify the debt categories to consider
- Ask for quantification of impact (time, risk, opportunity cost)
- Request dependency analysis between debt items
- Ask for validation approach to confirm debt assessment
- Require explicit handling of architectural vs. regular debt
- Request concrete, actionable remediation items with guidance

## Validation Prompts

### Test Case Generation
**Purpose**: Generate comprehensive test cases for AI-OS components and services that validate conformance, correctness, and edge cases.
**When to Use**: Creating tests for new or existing functionality, improving test coverage, or validating specification implementation.
**Expected Inputs**: 
- Specific component or function to test
- Test types to include (unit, integration, property-based, etc.)
- Relevant specification parts and engineering principles
- Required coverage level and quality thresholds
- Available fixtures, builders, or test utilities
**Expected Outputs**: 
- Test suite with unit, integration, and property-based tests covering normal and edge cases
- Tests for error conditions and boundary values
- Follows AI-OS testing conventions and frameworks
- Clear test organization (arrange-act-assert) and naming conventions
- Test data factories or builders where relevant
- Documentation of test purpose and validation criteria
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Synthetic - requires creating comprehensive test scenarios that validate requirements
**Success Criteria**: 
- Test suite includes unit, integration, and property-based tests
- Covers normal cases, edge cases, and error conditions
- Follows AI-OS testing conventions and frameworks
- Provides clear test organization and naming conventions
- Includes test data factories or builders where relevant
- Documents test purpose and validation criteria for each test
- Achieves specified coverage and quality thresholds
**Failure Modes**: 
- Providing incomplete test coverage (missing edge cases or errors)
- Not following AI-OS testing conventions or frameworks
- Missing test organization or naming conventions
- Failing to provide test data factories where relevant
- Not documenting test purpose or validation criteria
- Overlooking error conditions or boundary values
- Generating tests that don't actually validate requirements
**Related Prompts**: 
- [[Validation Script Creation]]
- [[Conformance Checklist Builder]]
- [[Code Quality Review]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Test case validation against Engineering Principles Section 6 and Validation Architecture

**Prompt Engineering Tips**:
- Specify the component or function to test
- Ask for test data factories or builders where relevant
- Request test organization (arrange-act-assert) and naming conventions
- Ask for validation approach to confirm test correctness
- Require explicit handling of error conditions and boundary values
- Request documentation of test purpose and validation criteria

### Validation Script Creation
**Purpose**: Create validation scripts for checking AI-OS conformance, correctness, or quality that produce reliable, automated validation results.
**When to Use**: Building automated validation for CI/CD, monitoring, or conformance assessment processes.
**Expected Inputs**: 
- What is being validated (specification, performance, security, etc.)
- Required pass/fail criteria and thresholds
- Available validation frameworks or utilities
- Desired output formats and reporting mechanisms
- Integration points with existing tooling
**Expected Outputs**: 
- Executable validation scripts with clear pass/fail criteria and reporting
- Includes both positive and negative test cases
- Provides clear diagnostics on failure
- Makes scripts idempotent and repeatable
- Includes cleanup and resource management
- Provides configurable thresholds and sensitivity
- Offers integration points with existing tooling
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Synthetic - requires creating reliable validation automation
**Success Criteria**: 
- Script includes clear pass/fail criteria and reporting mechanism
- Contains both positive and negative test cases
- Provides clear diagnostics on failure conditions
- Is idempotent and repeatable without side effects
- Includes cleanup and resource management procedures
- Provides configurable thresholds and sensitivity parameters
- Offers clear integration points with existing tooling
- Produces reliable, automated validation results
**Failure Modes**: 
- Providing unclear pass/fail criteria or reporting
- Missing positive or negative test cases
- Failing to provide clear failure diagnostics
- Not being idempotent or repeatable
- Omitting cleanup or resource management
- Lacking configurable thresholds or sensitivity
- Missing integration points with existing tooling
- Producing unreliable or inconsistent validation results
**Related Prompts**: 
- [[Test Case Generation]]
- [[Conformance Checklist Builder]]
- [[Architectural Conformance Review]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Validation script validation against Part 11 Validation Architecture and Engineering Principles Section 12.8

**Prompt Engineering Tips**:
- Specify what is being validated (specification, performance, security)
- Ask for exit codes and machine-readable output formats
- Request integration points with existing tooling
- Ask for validation approach to confirm script correctness
- Require explicit handling of idempotency and cleanup
- Request configurable thresholds and sensitivity parameters

### Conformance Checklist Builder
**Purpose**: Build comprehensive checklists for AI-OS specification conformance verification that enable systematic, objective assessment.
**When to Use**: Preparing for architecture reviews, audits, or conducting systematic conformance evaluations.
**Expected Inputs**: 
- Target conformance level (L1-L4)
- Specific specification parts to cover
- Available evidence sources and validation methods
- Desired checklist format and organization
- Required evidence types and verification methods
**Expected Outputs**: 
- Structured checklist with verification items, evidence requirements, and pass/fail criteria
- Organized by specification part or conformance level
- Verification items are atomic and objectively evaluable
- Includes references to specification text and evidence locations
- Provides automation hints and manual verification steps
- Enables repeatable, objective conformance assessment
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires breaking down conformance requirements into verifiable items
**Success Criteria**: 
- Checklist is organized by specification part or conformance level
- Verification items are atomic and objectively evaluable
- Includes specification text references for each item
- Details evidence requirements and verification methods
- Provides automation hints and manual verification steps
- Enables repeatable, objective conformance assessment
- Covers all required items for target conformance level
**Failure Modes**: 
- Providing vague or non-atomic verification items
- Missing specification text references for items
- Failing to detail evidence requirements or methods
- Omitting automation hints or manual verification steps
- Not enabling repeatable or objective assessment
- Missing required items for target conformance level
- Providing unclear pass/fail criteria for verification items
**Related Prompts**: 
- [[Test Case Generation]]
- [[Validation Script Creation]]
- [[Architectural Conformance Review]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Conformance checklist validation against Part 11 and Engineering Principles Section 12.12

**Prompt Engineering Tips**:
- Specify the target conformance level (L1-L4)
- Ask for automation feasibility assessments
- Request traceability matrices to specification requirements
- Ask for validation approach to confirm checklist accuracy
- Require explicit handling of atomic verification items
- Request evidence requirements and verification methods for items

## Governance Prompts

### Council Decision Support
**Purpose**: Support AI-OS governance councils (Claude Council, LLM Council) with decision analysis that provides balanced, principled recommendations.
**When to Use**: Preparing for council meetings, decisions, or providing analysis for governance processes.
**Expected Inputs**: 
- Specific council type and decision scope
- Decision context and available facts
- Alternatives under consideration
- Relevant governance principles and processes
- Required analysis depth and confidence level
**Expected Outputs**: 
- Decision brief with facts, alternatives, implications, and recommendation
- Balanced view of technical, organizational, and strategic factors
- Risk assessments and mitigation strategies
- Clear action items and follow-up requirements
- Precedent analysis (similar past decisions)
- Implementation timeline and resource estimates
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Evaluative - requires balanced analysis against governance principles
**Success Criteria**: 
- Brief includes facts, alternatives, implications, and recommendation
- Provides balanced view of technical, organizational, strategic factors
- Includes risk assessments and mitigation strategies
- Details precedent analysis (similar past decisions)
- Provides implementation timeline and resource estimates
- Includes clear action items and follow-up requirements
- Respects governance processes and principles
**Failure Modes**: 
- Providing biased or one-sided analysis
- Missing risk assessments or mitigation strategies
- Failing to include precedent analysis
- Not providing implementation timeline or estimates
- Lacking clear action items or follow-up requirements
- Overlooking governance processes or principles
- Providing vague or unactionable recommendations
**Related Prompts**: 
- [[Policy and Guideline Creation]]
- [[Audit Preparation Assistant]]
- [[Governance Principles Application]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Council decision validation against Engineering Principles Sections 12, 21-22 and Governance principles

**Prompt Engineering Tips**:
- Specify the council type and decision scope
- Ask for precedent analysis (similar past decisions)
- Request implementation timeline and resource estimates
- Ask for validation approach to confirm recommendation quality
- Require explicit handling of balanced analysis
- Request dissenting views and potential objections inclusion

### Policy and Guideline Creation
**Purpose**: Create governance policies, guidelines, and best practices for AI-OS that are actionable, measurable, and support ecosystem evolution.
**When to Use**: Establishing new governance processes, updating existing ones, or creating ecosystem contribution guidelines.
**Expected Inputs**: 
- Governance area (security, architecture, contributions, etc.)
- Specific policy or guideline objective
- Relevant governance principles and processes
- Available examples of compliant and non-compliant behavior
- Required scope and enforcement mechanisms
**Expected Outputs**: 
- Clear, actionable governance documents with rationale, scope, and enforcement mechanisms
- Rationale explaining why policy is needed
- Clear scope definition and applicability
- Defined enforcement mechanisms and compliance measurement
- Examples of compliant and non-compliant behavior
- Review and update cycles specified
- Scalability and evolution considerations addressed
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Synthetic - requires creating actionable, measurable governance instruments
**Success Criteria**: 
- Document includes clear rationale explaining policy need
- Provides clear scope definition and applicability
- Defines enforcement mechanisms and compliance measurement
- Includes examples of compliant and non-compliant behavior
- Specifies review and update cycles
- Addresses scalability and evolution considerations
- Produces actionable, measurable governance instrument
**Failure Modes**: 
- Providing unclear rationale or missing policy justification
- Lacking clear scope definition or applicability
- Failing to define enforcement mechanisms or compliance
- Omitting examples of compliant and non-compliant behavior
- Not specifying review or update cycles
- Overlooking scalability or evolution considerations
- Creating unclear, unmeasurable, or unactionable guidance
**Related Prompts**: 
- [[Council Decision Support]]
- [[Audit Preparation Assistant]]
- [[Governance Principles Application]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Policy creation validation against Engineering Principles Sections 12, 21-23 and Governance principles

**Prompt Engineering Tips**:
- Specify the governance area (security, architecture, contributions, etc.)
- Ask for examples of compliant and non-compliant behavior
- Request review and update cycles
- Ask for validation approach to confirm policy effectiveness
- Require explicit handling of compliance measurement
- Request scalability and evolution considerations

### Audit Preparation Assistant
**Purpose**: Prepare for AI-OS architecture, security, or compliance audits by creating readiness packages that enable successful audit outcomes.
**When to Use**: Preparing for internal or external audits, compliance assessments, or governance reviews.
**Expected Inputs**: 
- Audit type and scope (architecture, security, process, etc.)
- Specific requirements or standards being audited
- Available artifacts, documentation, and processes
- Desired output format and organization
- Required evidence levels and verification methods
**Expected Outputs**: 
- Audit readiness package with evidence collection, gap analysis, and remediation planning
- Focus on demonstrable evidence and traceability
- Includes both documented artifacts and observable behaviors
- Provides evidence collection procedures and checklists
- Includes remediation tracking and verification methods
- Enables successful audit outcomes through preparation
- Addresses both documented artifacts and observable behaviors
**Recommended Model**: GPT-4 Turbo
**Context Size**: 6-10K tokens
**Reasoning Depth**: Analytical - requires systematic audit preparation and readiness planning
**Success Criteria**: 
- Package includes evidence collection procedures and checklists
- Covers both documented artifacts and observable behaviors
- Includes remediation tracking and verification methods
- Focuses on demonstrable evidence and traceability
- Enables successful audit outcomes through preparation
- Addresses gap analysis and remediation planning
- Provides clear organization and output format
**Failure Modes**: 
- Providing vague evidence collection without procedures
- Missing coverage of documented artifacts or behaviors
- Failing to include remediation tracking or methods
- Not focusing on demonstrable evidence and traceability
- Lacking gap analysis or remediation planning
- Not enabling successful audit outcomes through preparation
- Providing unclear organization or output format
**Related Prompts**: 
- [[Council Decision Support]]
- [[Policy and Guideline Creation]]
- [[Governance Principles Application]]
**Version**: 2.1.0
**Last Validated**: 2026-08-07
**Validation Method**: Audit preparation validation against Engineering Principles Sections 12, 21-23 and Audit principles

**Prompt Engineering Tips**:
- Specify the audit type and scope (architecture, security, process, etc.)
- Ask for evidence prioritization (easiest/highest impact first)
- Request auditor FAQ and common question preparation
- Ask for validation approach to confirm preparation effectiveness
- Require explicit handling of documented vs. observable evidence
- Request gap analysis and remediation planning details

---
# Prompt Engineering Guidelines

## General Principles
1. **Be Specific**: Clearly define scope, constraints, and desired output format
2. **Provide Context**: Include relevant background information and references
3. **Specify Format**: Indicate preferred output structure (markdown, JSON, diagrams, etc.)
4. **Set Expectations**: Define quality criteria and success metrics
5. **Iterate and Refine**: Use outputs to refine subsequent prompts

## AI-OS Specific Considerations
1. **Specification First**: Always reference relevant AI-OS specification parts
2. **Principle Alignment**: Ensure outputs align with AI-OS engineering principles
3. **Ecosystem Awareness**: Consider impact on Skills, MCP, and Repository ecosystems
4. **Governance Compliance**: Follow AI-OS governance processes and requirements
5. **Validation Mindset**: Include mechanisms for verifying correctness and quality

## Output Quality Standards
1. **Actionability**: Outputs should enable clear next steps or decisions
2. **Traceability**: Include references to sources, specifications, or evidence
3. **Maintainability**: Design outputs for easy updating and evolution
4. **Reusability**: Structure outputs for potential reuse in similar contexts
5. **Accessibility**: Use clear language and appropriate formatting for intended audience

## Common Pitfalls to Avoid
1. **Over-Specification**: Don't constrain creativity when exploring alternatives
2. **Under-Specification**: Avoid ambiguous requests that lead to irrelevant outputs
3. **Specification Drift**: Ensure outputs don't contradict AI-OS specification
4. **Principle Violations**: Watch for outputs that undermine engineering principles
5. **Ecosystem Neglect**: Remember impact on extension points and external integrations