# Claude Prompt Library for AI-OS

**Metadata**
- **Version**: 3.0.0
- **Last Updated**: 2026-08-07
- **Owner**: AI-OS Prompt Engineering Council
- **Status**: Production Ready
- **Review Cadence**: Quarterly

**Purpose**
This document provides a curated collection of Claude prompt templates designed to support various aspects of AI-OS development, from architecture and documentation to review and governance. Each prompt is engineered to elicit high-quality, consistent outputs from Claude models while minimizing ambiguity and maximizing reuse.

**Scope**
The library covers prompt templates for:
- System and microservice architecture design
- Technical and API documentation
- Code and architecture reviews
- Technology and literature research
- Compliance and policy generation
- Repository initialization and dependency analysis
- Diagram and flowchart creation
- Refactoring and performance optimization

**Audience**
- Software architects and engineers
- Technical writers and documentation specialists
- DevOps and platform engineers
- Quality assurance and security analysts
- Product and project managers
- Any team member leveraging Claude for AI-OS development tasks

**Claude-Specific Prompt Engineering Guidance**
- **Model Selection**: Match prompt complexity to model capabilities (Haiku for simple tasks, Sonnet for balanced work, Opus for deep reasoning).
- **Context Management**: For large-context workflows, break prompts into chunks or use iterative refinement.
- **Reasoning Depth**: Adjust expected reasoning depth via prompt instructions (e.g., "think step by step" for deeper analysis).
- **Prompt Lifecycle**: Treat prompts as living artifacts; version, validate, and retire based on effectiveness.
- **Prompt Governance**: Follow organizational guidelines for prompt creation, review, and approval.
- **Prompt Validation**: Validate outputs against success criteria before adoption.
- **Prompt Maintenance**: Regularly update prompts to reflect evolving best practices and model capabilities.

**Large-Context Workflows**
When working with extensive codebases or documents:
1. **Chunking**: Divide input into logical sections (e.g., by module or chapter).
2. **Iterative Refinement**: Use initial outputs to inform subsequent, more focused prompts.
3. **Context Summarization**: Pre-summarize large inputs to fit within model context windows.
4. **Parallel Processing**: Leverage multiple Claude instances for independent chunks, then synthesize.

**Extended Reasoning Guidance**
For tasks requiring deep analysis:
- Explicitly request chain-of-thought or step-by-step reasoning.
- Ask for multiple perspectives or alternative approaches.
- Require justification for recommendations.
- Encourage consideration of edge cases and failure modes.

---
## Table of Contents
- [Architecture Prompts](#architecture-prompts)
- [Documentation Prompts](#documentation-prompts)
- [Review Prompts](#review-prompts)
- [Research Prompts](#research-prompts)
- [Governance Prompts](#governance-prompts)
- [Repository Prompts](#repository-prompts)
- [Diagram Prompts](#diagram-prompts)
- [Improvement Prompts](#improvement-prompts)

---

## Architecture Prompts

### System Design Prompt
**Purpose**: Generate high-level system architecture diagrams and descriptions for new features or services.
**Usage**: Initiate architecture discussions, create architecture decision records, or communicate system structure to stakeholders.
**Inputs**: 
- [FEATURE/SERVICE]: Name and brief description of the feature or service.
- [REQUIREMENTS]: List of functional and non-functional requirements (scale, latency, security, etc.).
**Outputs**: Structured architecture document including component diagram description, data flow, technology recommendations, patterns, bottlenecks, and deployment considerations.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: Moderate to high (requirements details may consume significant context).
**Reasoning Depth**: Deep (requires analysis of trade-offs, patterns, and systemic implications).
**Failure Modes**: 
- Overly generic recommendations if requirements are vague.
- Missing domain-specific constraints.
**Success Criteria**: 
- Output addresses all input requirements.
- Includes clear justification for technology choices.
- Provides actionable migration or implementation path.
**Related Prompts**: 
- Microservice Design Prompt
- Architecture Diagram Prompt
- Architecture Review Prompt
**Prompt Template**:
```
You are an expert software architect. Design a system architecture for [FEATURE/SERVICE] that must handle [REQUIREMENTS].
Consider: scalability, reliability, security, maintainability, and cost-effectiveness.
Provide:
1. High-level component diagram description
2. Data flow between components
3. Technology recommendations with justification
4. Key architectural patterns applied
5. Potential bottlenecks and mitigation strategies
6. Deployment and operational considerations
Format your response as a structured architecture document suitable for engineering review.
```

### Microservice Design Prompt
**Purpose**: Design individual microservices with clear boundaries and interfaces.
**Usage**: Define service contracts during domain-driven design or when decomposing monoliths.
**Inputs**:
- [SERVICE_NAME]: Identifier for the microservice.
- [BUSINESS_CAPABILITY]: Core business function the service encapsulates.
**Outputs**: Service interface definitions, data models, interaction patterns, error handling, and deployment considerations.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Low to moderate (focused on a single service boundary).
**Reasoning Depth**: Moderate (requires understanding of cohesion, coupling, and API design principles).
**Failure Modes**: 
- Overlooking asynchronous communication needs.
- Defining overly chatty interfaces.
**Success Criteria**: 
- Service adheres to single responsibility principle.
- API contracts are explicit and versionable.
- Failure scenarios are addressed.
**Related Prompts**: 
- System Design Prompt
- API Documentation Prompt
- Dependency Analysis Prompt
**Prompt Template**:
```
Design a microservice for [SERVICE_NAME] responsible for [BUSINESS_CAPABILITY].
Include:
1. Service responsibilities and boundaries
2. Public API endpoints (REST/gRPC/GraphQL) with request/response schemas
3. Internal data models and storage recommendations
4. Communication patterns with other services
5. Error handling and retry strategies
6. Monitoring and observability requirements
7. Deployment considerations (scaling, health checks)
Ensure loose coupling and high cohesion principles are followed.
```

---

## Documentation Prompts

### API Documentation Prompt
**Purpose**: Generate comprehensive API documentation from code or specifications.
**Usage**: Create or update developer-facing API references, portal content, or integration guides.
**Inputs**:
- [API_NAME]: Name of the API being documented.
- [SPECIFICATION_OR_CODE_SNIPPET]: Source material (OpenAPI spec, code comments, or structured description).
**Outputs**: Markdown-formatted API documentation with overview, authentication, endpoints, error codes, rate limiting, examples, and versioning.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Variable (depends on spec size; may require chunking for large specs).
**Reasoning Depth**: Moderate (requires extracting and structuring information accurately).
**Failure Modes**: 
- Missing implicit behaviors not in spec.
- Inconsistent terminology if source is ambiguous.
**Success Criteria**: 
- Documentation is complete and accurate relative to source.
- Includes practical examples in specified language.
- Follows a consistent structure and style.
**Related Prompts**: 
- Technical Specification Prompt
- Repository Initialization Prompt
**Prompt Template**:
```
Generate API documentation for [API_NAME] based on the following specification:
[SPECIFICATION_OR_CODE_SNIPPET]

Include:
1. Overview and purpose
2. Authentication methods
3. Endpoint details (HTTP method, path, parameters, request/response bodies)
4. Status codes and error responses
5. Rate limiting information
6. Practical code examples in [LANGUAGE]
7. Versioning and deprecation policy
Format as Markdown suitable for developer portal publication.
```

### Technical Specification Prompt
**Purpose**: Create detailed technical specifications for features or system changes.
**Usage**: Align stakeholders before implementation, define scope for estimates, or document regulatory requirements.
**Inputs**:
- [FEATURE_NAME]: Name of the feature or change.
- [BUSINESS_GOAL]: Objective or problem the feature addresses.
**Outputs**: Comprehensive specification covering executive summary, functional/non-functional requirements, technical approach, interfaces, implementation plan, risks, testing strategy, and rollback considerations.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: High (may need to accommodate extensive requirements lists).
**Reasoning Depth**: Deep (requires bridging business and technical domains, risk assessment, and planning).
**Failure Modes**: 
- Becoming overly detailed and losing focus.
- Missing cross-functional dependencies.
**Success Criteria**: 
- Specification is clear to both technical and non-technical audiences.
- Acceptance criteria are testable.
- Risks are identified with mitigation strategies.
**Related Prompts**: 
- System Design Prompt
- Architecture Review Prompt
- Improvement Prompts
**Prompt Template**:
```
Create a technical specification for [FEATURE_NAME] addressing [BUSINESS_GOAL].

Sections to include:
1. Executive Summary
2. Functional Requirements (user stories/acceptance criteria)
3. Non-functional Requirements (performance, security, scalability)
4. Technical Approach (architecture, data models, algorithms)
5. Interface Changes (APIs, UI, dependencies)
6. Implementation Plan (phases, dependencies, resources)
7. Risks and Mitigation Strategies
8. Testing Strategy (unit, integration, performance, security)
9. Rollback and Deployment Considerations
Use clear, concise language suitable for both technical and non-technical stakeholders.
```

---

## Review Prompts

### Code Review Prompt
**Purpose**: Conduct thorough code reviews for quality, security, and maintainability.
**Usage**: Review pull requests, code changes, or legacy code for improvement opportunities.
**Inputs**:
- [REPOSITORY/PROJECT]: Context for the code (optional).
- [CODE_DIFF_OR_FILE_PATH]: The code to review (diff or file content).
**Outputs**: Detailed review comments classified as BLOCKING, MAJOR, MINOR, or NITPICK, with line references and actionable suggestions.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Moderate (depends on size of diff; large diffs may require chunking).
**Reasoning Depth**: Moderate to deep (requires analysis of correctness, style, security, performance, and maintainability).
**Failure Modes**: 
- False positives in complex contexts.
- Overlooking project-specific conventions.
**Success Criteria**: 
- Feedback is specific, actionable, and tied to lines where possible.
- All requested check categories are addressed.
- Tone is constructive and collaborative.
**Related Prompts**: 
- Architecture Review Prompt
- Refactoring Suggestion Prompt
**Prompt Template**:
```
Review the following code change for [REPOSITORY/PROJECT]:
[CODE_DIFF_OR_FILE_PATH]

Check for:
1. Correctness and logic errors
2. Adherence to coding standards and style guides
3. Potential security vulnerabilities (OWASP Top 10)
4. Performance implications
5. Test coverage and quality
6. Documentation completeness
7. Maintainability and readability
8. Dependency and licensing issues

Provide specific, actionable feedback with line references when possible.
Classify feedback as: [BLOCKING] [MAJOR] [MINOR] [NITPICK]
```

### Architecture Review Prompt
**Purpose**: Evaluate architectural decisions for long-term viability and best practices.
**Usage**: Assess proposed architectures, conduct architecture gate reviews, or evaluate technical debt.
**Inputs**:
- [SYSTEM/FEATURE]: Name of the system or feature under review.
- [ARCHITECTURE_DOCUMENT_OR_DIAGRAM]: The architecture to review (document or diagram description).
**Outputs**: Architecture assessment with strengths, areas for improvement, risk analysis, and alternative approaches.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: High (architecture documents can be lengthy).
**Reasoning Depth**: Deep (requires evaluation against multiple dimensions and synthesis of recommendations).
**Failure Modes**: 
- Subjectivity without clear evaluation framework.
- Missing critical non-functional requirements.
**Success Criteria**: 
- Review is structured and covers all evaluation dimensions.
- Recommendations are specific and actionable.
- Risks are quantified (likelihood and impact) where possible.
**Related Prompts**: 
- System Design Prompt
- Code Review Prompt
- Technology Evaluation Prompt
**Prompt Template**:
```
Review the proposed architecture for [SYSTEM/FEATURE] described in:
[ARCHITECTURE_DOCUMENT_OR_DIAGRAM]

Evaluate against:
1. Business requirements and goals
2. Scalability and performance targets
3. Security and compliance requirements
4. Operational complexity and observability
5. Technology choices and alternatives
6. Alignment with organizational architecture standards
7. Migration and evolution path
8. Cost-effectiveness and resource utilization

Provide:
- Strengths of the current approach
- Areas for improvement with specific recommendations
- Risk assessment (likelihood and impact)
- Alternative approaches considered
```

---

## Research Prompts

### Technology Evaluation Prompt
**Purpose**: Research and compare technologies for specific use cases.
**Usage**: Inform technology selection decisions, create proof-of-work plans, or assess migration candidates.
**Inputs**:
- [TECHNOLOGY_CATEGORY]: Type of technology (e.g., database, message queue, frontend framework).
- [USE_CASE]: Specific scenario or problem the technology will address.
- [REQUIREMENTS_LIST]: Functional and non-functional requirements.
- [TECHNOLOGY_A], [TECHNOLOGY_B], [TECHNOLOGY_C]: Technologies to compare (add/remove as needed).
**Outputs**: Comparative analysis including feature matrix, pros/cons, recommendation with justification, and risk mitigation.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: High (multiple technologies and criteria increase context needs).
**Reasoning Depth**: Deep (requires systematic evaluation, trade-off analysis, and forecasting).
**Failure Modes**: 
- Bias toward familiar technologies.
- Missing emerging alternatives.
**Success Criteria**: 
- Evaluation criteria are defined upfront and applied consistently.
- Recommendation is justified with evidence.
- Risks and migration paths are identified.
**Related Prompts**: 
- Literature Review Prompt
- Dependency Analysis Prompt
**Prompt Template**:
```
Evaluate [TECHNOLOGY_CATEGORY] options for [USE_CASE] with requirements:
[REQUIREMENTS_LIST]

Compare: [TECHNOLOGY_A], [TECHNOLOGY_B], [TECHNOLOGY_C] (add/remove as needed)

Evaluation criteria:
1. Functional fit (meets requirements)
2. Performance and scalability
3. Operational complexity
4. Security and compliance features
5. Ecosystem and community support
6. Licensing and cost implications
7. Integration effort with existing systems
8. Vendor stability and roadmap
9. Learning curve for team

Provide:
- Feature comparison matrix
- Detailed pros/cons for each option
- Recommendation with justification
- Risks and mitigation strategies
```

### Literature Review Prompt
**Purpose**: Summarize and analyze academic or technical literature on a topic.
**Usage**: Gather state-of-the-art knowledge, identify research gaps, or inform technical spikes.
**Inputs**:
- [TOPIC]: Subject of the review.
- [ASPECT_OR_APPLICATION]: Specific lens or application to focus on.
- [SOURCE_LIST_OR_SEARCH_CRITERIA]: Sources to consider (optional).
**Outputs**: Structured summary with key findings, methodology, limitations, synthesis of consensus/conflicts, gaps, and future directions.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Moderate to high (depends on number of sources).
**Reasoning Depth**: Moderate (requires extraction, comparison, and synthesis across sources).
**Failure Modes**: 
- Over-reliance on low-quality sources.
- Missing very recent publications due to knowledge cutoff.
**Success Criteria**: 
- Review is reproducible (sources and methodology documented).
- Key findings are accurately extracted.
- Synthesis identifies meaningful patterns and gaps.
**Related Prompts**: 
- Technology Evaluation Prompt
- Research Prompts (general)
**Prompt Template**:
```
Conduct a literature review on [TOPIC] focusing on [ASPECT_OR_APPLICATION].

Sources to consider: [SOURCE_LIST_OR_SEARCH_CRITERIA]

For each source, extract:
1. Key findings and contributions
2. Methodology or approach
3. Limitations and assumptions
4. Relevance to the research question

Synthesize to identify:
- Consensus points in the literature
- Conflicting results or theories
- Research gaps and open questions
- Emerging trends and future directions

Format as an annotated bibliography with thematic synthesis.
```

---

## Governance Prompts

### Compliance Check Prompt
**Purpose**: Verify adherence to regulatory or internal governance requirements.
**Usage**: Prepare for audits, assess compliance of new features, or conduct periodic compliance reviews.
**Inputs**:
- [SYSTEM/PROCESS/DOCUMENT]: Target of the compliance check.
- [REGULATION_OR_STANDARD]: Regulation or standard to verify against (e.g., GDPR, HIPAA, SOC2, ISO27001).
- [REQUIREMENTS_LIST_OR_REFERENCE_TO_STANDARD]: Specific requirements to verify (optional).
**Outputs**: Compliance report with status per requirement, evidence, gaps, remediation steps, priority, estimated effort, overall score, critical gaps, and roadmap.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: High (regulations can be extensive).
**Reasoning Depth**: Deep (requires mapping requirements to evidence and interpreting complex clauses).
**Failure Modes**: 
- Missing nuanced interpretation of regulations.
- Output not actionable for remediation.
**Success Criteria**: 
- Each requirement is evaluated with clear status and evidence.
- Remediation steps are specific, prioritized, and effort-estimated.
- Report supports audit or executive decision-making.
**Related Prompts**: 
- Policy Generation Prompt
- Technical Specification Prompt
**Prompt Template**:
```
Check compliance of [SYSTEM/PROCESS/DOCUMENT] against [REGULATION_OR_STANDARD] (e.g., GDPR, HIPAA, SOC2, ISO27001).

Requirements to verify:
[REQUIREMENTS_LIST_OR_REFERENCE_TO_STANDARD]

For each requirement:
1. Status: Compliant/Non-compliant/Partially compliant/Not applicable
2. Evidence supporting the status
3. Gap description (if non-compliant)
4. Remediation steps and priority
5. Estimated effort for remediation

Provide:
- Overall compliance score
- Critical gaps requiring immediate attention
- Remediation roadmap
- References to specific control implementations
```

### Policy Generation Prompt
**Purpose**: Create organizational policies for security, development, or operations.
**Usage**: Establish new policies, update existing ones, or create team-specific guidelines.
**Inputs**:
- [POLICY_TYPE]: Type of policy (e.g., Security Policy, Data Handling Policy, Code Review Policy).
- [ORGANIZATION/TEAM]: Scope of the policy (company-wide, department, team).
**Outputs**: Clear, enforceable policy document with purpose, scope, definitions, statements, roles, procedures, compliance, enforcement, review schedule, references, effective date, and version.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Low to moderate (policy content is typically focused).
**Reasoning Depth**: Moderate (requires balancing comprehensiveness with clarity and enforceability).
**Failure Modes**: 
- Policy too generic to be actionable.
- Missing clear ownership or enforcement mechanisms.
**Success Criteria**: 
- Policy uses directive, unambiguous language.
- Includes practical implementation details.
- Defines review and update cycle.
**Related Prompts**: 
- Compliance Check Prompt
- Repository Initialization Prompt
**Prompt Template**:
```
Generate a policy document for [POLICY_TYPE] (e.g., Security Policy, Data Handling Policy, Code Review Policy) for [ORGANIZATION/TEAM].

Include:
1. Purpose and scope
2. Definitions of key terms
3. Policy statements and requirements
4. Roles and responsibilities
5. Procedures and implementation details
6. Compliance and enforcement mechanisms
7. Review and update schedule
8. References to related policies and standards
9. Effective date and version number

Use clear, directive language. Avoid ambiguity. Ensure practical implementability.
```

---

## Repository Prompts

### Repository Initialization Prompt
**Purpose**: Standardize new repository setup with best practices.
**Usage**: Create new repositories for services, libraries, or infrastructure as code.
**Inputs**:
- [PROJECT_TYPE]: Type of project (e.g., web service, data pipeline, library).
- [LANGUAGE/FRAMEWORK]: Primary language or framework.
**Outputs**: Repository structure, configuration files (.gitignore, README, LICENSE, CI/CD, testing, formatting, linting, dependency files), initial documentation (contributing, code of conduct, changelog), and optional Hello World example.
**Recommended Claude Model**: Claude Haiku 4.5
**Expected Context Size**: Low (inputs are short; output is structured but not context-intensive).
**Reasoning Depth**: Low to moderate (requires applying best practices consistently).
**Failure Modes**: 
- Missing language-specific configurations.
- Producing overly rigid templates that hinder adoption.
**Success Criteria**: 
- Output follows organizational best practices.
- Includes essential DevOps and quality configurations.
- Saves time on boilerplate while allowing customization.
**Related Prompts**: 
- Dependency Analysis Prompt
- API Documentation Prompt
**Prompt Template**:
```
Initialize a new repository for [PROJECT_TYPE] (e.g., web service, data pipeline, library) using [LANGUAGE/FRAMEWORK].

Create:
1. Standard directory structure (src, tests, docs, configs)
2. Essential configuration files:
   - .gitignore (language-specific)
   - README.md with project overview and setup instructions
   - LICENSE file
   - CI/CD configuration (GitHub Actions/GitLab CI/etc.)
   - Basic testing setup
   - Code formatting and linting configurations
   - Dependency management files
3. Initial documentation:
   - Contributing guidelines
   - Code of conduct
   - Changelog template
4. Example Hello World implementation (if applicable)

Follow [ORGANIZATION] best practices for repository setup.
```

### Dependency Analysis Prompt
**Purpose**: Analyze project dependencies for security, licensing, and maintenance risks.
**Usage**: Conduct security assessments, license compliance checks, or technical debt reviews.
**Inputs**:
- [PROJECT_NAME]: Name of the project.
- [DEPENDENCY_FILES]: Dependency manifests (package.json, requirements.txt, pom.xml, etc.).
**Outputs**: Dependency report with version analysis, known vulnerabilities (CVEs), license compatibility, maintenance status, popularity, direct vs transitive status, risk summary, recommended actions, license compliance report, and outdated dependencies list.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Moderate to high (large dependency lists increase context).
**Reasoning Depth**: Moderate (requires looking up vulnerability and license data; may benefit from tool augmentation).
**Failure Modes**: 
- False positives from vulnerability databases.
- Missing internal or private dependencies.
**Success Criteria**: 
- Report is accurate and actionable.
- Risks are categorized by severity.
- Recommendations are clear (update, replace, monitor).
**Related Prompts**: 
- Repository Initialization Prompt
- Technology Evaluation Prompt
**Prompt Template**:
```
Analyze the dependencies of [PROJECT_NAME] based on:
[DEPENDENCY_FILES: package.json, requirements.txt, pom.xml, etc.]

For each dependency, assess:
1. Current version and latest available
2. Known security vulnerabilities (CVEs)
3. License type and compatibility with project
4. Maintenance status (last release, commit frequency)
5. Popularity and community support
6. Direct vs transitive dependency status

Provide:
- Summary of risks by severity
- Recommended actions (update, replace, monitor)
- License compliance report
- Outdated dependencies requiring attention
```

---

## Diagram Prompts

### Architecture Diagram Prompt
**Purpose**: Generate detailed architecture diagrams from textual descriptions.
**Usage**: Create diagram source code for Mermaid, PlantUML, or draw.io to visualize system architecture.
**Inputs**:
- [SYSTEM_TYPE]: Type of system (e.g., microservices, event-driven, layered).
- [COMPONENT_LIST_AND_INTERACTIONS]: Components and their relationships.
**Outputs**: Diagram description in specified notation (Mermaid/PlantUML/draw.io) covering components, interfaces, data flows, external dependencies, deployment environments, and key patterns, plus a brief architecture explanation.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: Moderate (component lists can be extensive).
**Reasoning Depth**: Moderate (requires translating concepts to visual notation accurately).
**Failure Modes**: 
- Diagram notation errors requiring manual correction.
- Overly detailed diagrams that reduce clarity.
**Success Criteria**: 
- Output is syntactically correct for the chosen notation.
- Diagram includes all essential components and connections.
- Brief explanation aids understanding.
**Related Prompts**: 
- System Design Prompt
- Flowchart Prompt
**Prompt Template**:
```
Create a diagram description for [SYSTEM_TYPE] architecture that includes:
[COMPONENT_LIST_AND_INTERACTIONS]

Use [DIAGRAM_NOTATION: Mermaid/PlantUML/draw.io] syntax to describe:
1. Components/services and their responsibilities
2. Interfaces and communication protocols
3. Data flows and storage mechanisms
4. External systems and dependencies
5. Deployment environments and infrastructure
6. Key patterns (microservices, event-driven, layered, etc.)

Include sufficient detail for someone to render an accurate diagram.
Provide both the diagram code and a brief explanation of the architecture.
```

### Flowchart Prompt
**Purpose**: Generate flowcharts for processes, algorithms, or workflows.
**Usage**: Document business processes, algorithm logic, or CI/CD pipelines.
**Inputs**:
- [PROCESS_NAME]: Name of the process.
- [PROCESS_STEPS_AND_DECISION_POINTS]: Steps and decisions to include.
**Outputs**: Flowchart description in standard notation (Mermaid/PlantUML) with start/end points, process steps, decision points, inputs/outputs, looping constructs, and parallel paths, plus explanations for complex decisions.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Moderate (complex processes increase context).
**Reasoning Depth**: Moderate (requires structuring logic into flowchart elements).
**Failure Modes**: 
- Flowchart becomes unwieldy and hard to follow.
- Missing critical decision points or error paths.
**Success Criteria**: 
- Output uses standard flowchart symbols correctly.
- Flowchart is clear, unambiguous, and fits on one page/screen.
- Explanations clarify complex logic.
**Related Prompts**: 
- Architecture Diagram Prompt
- Technical Specification Prompt
**Prompt Template**:
```
Create a flowchart description for [PROCESS_NAME] that outlines:
[PROCESS_STEPS_AND_DECISION_POINTS]

Use [FLOWCHART_NOTATION: Mermaid/PlantUML] to represent:
1. Start and end points
2. Process steps and actions
3. Decision points with conditions
4. Inputs and outputs
5. Looping constructs
6. Parallel paths or concurrency where applicable

Include brief explanations for complex decision points.
Ensure the flowchart is clear, unambiguous, and follows standard conventions.
```

---

## Improvement Prompts

### Refactoring Suggestion Prompt
**Purpose**: Identify and suggest code refactoring opportunities.
**Usage**: Improve code maintainability, reduce technical debt, or prepare for feature development.
**Inputs**:
- [CODE_SNIPPET_OR_FILE_PATH]: Code to analyze for refactoring.
**Outputs**: List of refactoring opportunities with issue description, impact, specific technique, before/after examples, effort/risk estimate, preconditions, and prioritization by impact/feasibility.
**Recommended Claude Model**: Claude Sonnet 5
**Expected Context Size**: Moderate (depends on code size; large files may need chunking).
**Reasoning Depth**: Moderate (requires recognizing code smells and applying refactoring patterns).
**Failure Modes**: 
- Suggesting changes that break functionality without adequate tests.
- Over-refactoring low-value code.
**Success Criteria**: 
- Each suggestion is safe to apply with noted preconditions.
- Suggestions focus on high-impact, low-risk changes first.
- Before/after examples are clear and compilable.
**Related Prompts**: 
- Code Review Prompt
- Performance Optimization Prompt
**Prompt Template**:
```
Analyze the following code for refactoring opportunities:
[CODE_SNIPPET_OR_FILE_PATH]

Look for:
1. Duplicated code
2. Long methods or functions
3. Large classes or modules
4. Complex conditional logic
5. Inappropriate intimacy between classes
6. Primitive obsession
7. Temporary fields
8. Refused bequest
9. Comments that explain bad code

For each opportunity identified:
1. Describe the issue and its impact
2. Suggest specific refactoring technique (Extract Method, Replace Temp with Query, etc.)
3. Provide before/after code examples
4. Estimate effort and risk level
5. Note any preconditions (tests needed, etc.)

Prioritize suggestions by impact and feasibility.
```

### Performance Optimization Prompt
**Purpose**: Identify performance bottlenecks and optimization opportunities.
**Usage**: Optimize latency, throughput, or resource usage after profiling or based on performance data.
**Inputs**:
- [SYSTEM/COMPONENT]: Name of the system or component.
- [PERFORMANCE_DATA_OR_DESCRIPTION]: Performance metrics (response times, throughput, resource usage) or description of performance concerns.
**Outputs**: Performance analysis identifying CPU, memory, I/O, concurrency, algorithm, caching, database, and network bottlenecks, with evidence, optimization techniques, improvement estimates, complexity/risk, validation approach, and prioritization by user experience or system capacity impact.
**Recommended Claude Model**: Claude Opus 4.8
**Expected Context Size**: High (performance data can be voluminous).
**Reasoning Depth**: Deep (requires correlating data with potential causes and evaluating trade-offs).
**Failure Modes**: 
- Recommending premature optimizations without data.
- Missing systemic bottlenecks (e.g., thread pools).
**Success Criteria**: 
- Each finding is backed by evidence from input data.
- Optimizations are specific and technically sound.
- Prioritization focuses on user-visible impact or system capacity.
**Related Prompts**: 
- Refactoring Suggestion Prompt
- Technology Evaluation Prompt
**Prompt Template**:
```
Analyze the performance of [SYSTEM/COMPONENT] based on:
[PERFORMANCE_DATA_OR_DESCRIPTION: response times, throughput, resource usage, etc.]

Identify:
1. CPU bottlenecks (inefficient algorithms, expensive operations)
2. Memory issues (leaks, excessive allocation, GC pressure)
3. I/O bottlenecks (disk, network, database)
4. Concurrency problems (lock contention, thread starvation)
5. Algorithm complexity issues
6. Caching opportunities
7. Database query inefficiencies
8. Network latency considerations

For each finding:
1. Describe the bottleneck and evidence
2. Suggest specific optimization techniques
3. Estimate potential improvement
4. Note implementation complexity and risks
5. Recommend validation approach

Prioritize by impact on user experience or system capacity.
```

---

## Usage Guidelines

1. **Model Selection**: Use the recommended models as starting points, but adjust based on task complexity and required reasoning depth. For simple tasks, consider Haiku; for balanced work, Sonnet; for deep reasoning, Opus.
2. **Iteration**: Treat prompts as starting points; refine based on initial outputs and feedback. Use output to inform subsequent, more focused prompts.
3. **Context**: Provide sufficient context in your prompts for optimal results. For large inputs, consider chunking or summarization.
4. **Validation**: Always validate AI-generated content against requirements and subject matter expertise. Apply success criteria checks.
5. **Customization**: Adapt prompt templates to your specific organizational context and needs. Insert organization-specific details where placeholders exist.
6. **Feedback Loop**: Continuously improve prompts based on actual usage and results. Record lessons learned and update the library quarterly.
7. **Prompt Chaining**: Combine prompts for complex workflows (e.g., use System Design Prompt followed by Architecture Diagram Prompt).
8. **Versioning**: Treat each prompt as versioned artifact. Increment version when making non-trivial changes.
9. **Governance**: Follow organizational prompt review and approval processes before deploying new or updated prompts broadly.

## Maintenance

This document should be reviewed and updated quarterly to:
- Add new prompt categories as needed
- Update recommended models as new Claude versions release
- Refine prompt templates based on effectiveness
- Remove obsolete prompts
- Incorporate lessons learned from usage
- Ensure metadata remains accurate and complete

*Last updated: 2026-08-07*