# AI-OS Review Prompt Library

The official prompt library for reviewing AI-OS artifacts, providing reusable prompts for consistent, high-quality reviews across the entire AI-OS repository.

---

## Purpose

This document provides a curated collection of prompts specifically designed for reviewing AI-OS architecture documents, project knowledge, templates, diagrams, research, and governance artifacts. These prompts enable reviewers to conduct thorough, objective, and consistent evaluations aligned with AI-OS architectural principles and engineering standards.

Unlike architecture creation prompts, these review prompts focus on evaluation, validation, and improvement identification rather than generation of new content.

## Review Philosophy

AI-OS review processes follow these core principles, derived from [[ENGINEERING_PRINCIPLES.md]] and [[COUNCILS.md]]:

### Objective Reviews
Reviews must be based on observable evidence and measurable criteria rather than personal preferences. Each finding should be traceable to specific sections, requirements, or principles, following the evidence-based validation approach from [[VALIDATION_ARCHITECTURE.md]].

### Evidence-Based Evaluation
All assertions in a review must be supported by concrete evidence from the document under review, referenced AI-OS specifications, or established engineering principles. This aligns with the validation-first execution principle (Part 0, Section 12.8) and the requirement for validation evidence in conformance assessment.

### Consistency
Reviews should apply the same standards across similar artifacts, ensuring fair and comparable evaluations regardless of author or document type. This supports the architectural invariant of consistent application of principles (Part 0, Section 12.12).

### Architecture-First Thinking
Reviews prioritize architectural integrity, principle alignment, and specification conformance over implementation details or cosmetic issues, reflecting the specification/implementation separation principle (Part 0, Section 9).

### Constructive Feedback
Every identified issue should be accompanied by specific, actionable recommendations for improvement, focusing on how to enhance the artifact rather than merely criticizing shortcomings. This follows the principle of providing actionable feedback and aligns with the improvement recommendation processes described in [[COUNCILS.md]].

### Publication Readiness
Reviews assess whether artifacts meet the quality standards necessary for distribution to stakeholders, including clarity, completeness, correctness, and conformance to AI-OS standards. This aligns with the conformance expectations outlined in [[IMPLEMENTATION_GUIDE.md]] Section 2.

### Human-in-the-Loop Validation
For value-laden decisions or architectural changes affecting fundamental guarantees, reviews must incorporate human judgment through appropriate governance channels, as specified in the Human Governance Principles (Part 12) and Council oversight requirements.

## Review Lifecycle

Reviews in AI-OS follow a standardized lifecycle to ensure consistency, traceability, and quality:

1. **Initiation**: Review need identified through change proposal, scheduled audit, or stakeholder request
2. **Planning**: Selection of appropriate review prompts and determination of review depth based on artifact criticality
3. **Execution**: Application of selected prompts with evidence collection and documentation
4. **Synthesis**: Analysis of findings, severity classification, and recommendation formulation
5. **Reporting**: Generation of review report with findings, recommendations, and disposition guidance
6. **Follow-up**: Tracking of remediation actions and verification of resolution
7. **Closure**: Formal completion and archival of review artifacts

Review depth is determined by the artifact's conformance level requirements (L1-L4 per [[IMPLEMENTATION_GUIDE.md]] Section 7) and its architectural significance.

## Review Governance

Review processes are governed by the AI-OS Council structure ([[COUNCILS.md]]) with specific responsibilities:

### Architecture Review Board (ARB)
- Maintains ownership of this prompt library
- Approves significant changes to review methodologies
- Ensures alignment with architectural principles and invariants
- Oversees review quality metrics and continuous improvement

### Validation Council
- Defines validation standards and evidence requirements for reviews
- Ensures review prompts align with [[VALIDATION_ARCHITECTURE.md]]
- Provides guidance on validation-first execution principles

### Engineering Council
- Establishes engineering practice standards that inform technical review criteria
- Ensures consistency with [[ENGINEERING_PRINCIPLES.md]]
- Provides guidance on principle adherence assessment

Review prompts must be approved through the appropriate council governance processes before adoption, with the ARB maintaining final approval authority for architectural review prompts.

## Review Categories

Organize prompts for reviewing these AI-OS artifact types:

- **Architecture Parts** (Parts 1-15): Core specification documents defining the AI-OS architecture
- **Project Knowledge Documents**: Guides, roadmaps, research summaries, and ecosystem documentation
- **Templates**: Standardized formats for ADRs, architecture parts, reviews, and other documents
- **Diagrams**: Mermaid and other architectural visualizations
- **Research Documents**: Technology evaluations, literature reviews, and future assessments
- **Prompt Libraries**: Collections of prompts for various AI interactions (this document itself)
- **ADRs**: Architecture Decision Records documenting significant decisions
- **Repository Structure**: Organization of code, documentation, and configuration files
- **Mermaid Diagrams**: Specific validation for Mermaid syntax and diagram quality
- **Governance Documents**: Policies, procedures, council charters, and compliance frameworks

Each artifact type requires specialized evaluation approaches while maintaining consistent review fundamentals.

## Enhanced Prompt Collection

Each prompt now includes the following standardized sections:
- **Purpose**: What the prompt accomplishes
- **When to Use**: Appropriate contexts for application
- **Expected Outputs**: Format and content of the review results
- **Evidence Required**: Specific evidence needed to support findings
- **Review Checklist**: Specific items to verify
- **Success Criteria**: Conditions indicating satisfactory completion
- **Failure Conditions**: Conditions indicating review failure or incompletion
- **Related Review Prompts**: Complementary prompts for comprehensive reviews
- **Review Depth**: Level of scrutiny (surface, standard, deep)
- **Recommended Model**: Optimal Claude model for this prompt
- **Estimated Context Size**: Approximate token usage

---

### Architecture Part Review Prompt

**Purpose**: Conduct a comprehensive review of an AI-OS Architecture Part for specification conformance, principle alignment, and architectural integrity, evaluating against the frozen Parts 1-15 and Engineering Principles.

**When to Use**: Reviewing any Architecture Part (Parts 1-15) during creation, update, or publication preparation, particularly when assessing conformance levels L3-L4.

**Expected Outputs**: Detailed review report with:
- Conformance assessment against Parts 1-15
- Findings grouped by severity (Critical, Major, Moderate, Minor)
- Principle adherence evaluation per [[ENGINEERING_PRINCIPLES.md]]
- Architectural invariant compliance verification
- Prioritized remediation actions with effort estimates
- Publication readiness recommendation

**Evidence Required**:
- Direct citations from the Architecture Part under review
- References to specific Parts 1-15 sections
- References to [[ENGINEERING_PRINCIPLES.md]] principles
- Specific line numbers or section references for all findings
- Cross-reference validation evidence

**Review Checklist**:
- [ ] Conformance to AI-OS Architecture Specification (Parts 1-15)
- [ ] Alignment with [[ENGINEERING_PRINCIPLES.md]] principles
- [ ] Structural compliance with [[PART_TEMPLATE.md]]
- [ ] Correct RFC 2119 terminology usage (MUST/MUST NOT/SHOULD/MAY)
- [ ] Valid and consistent Mermaid diagrams (per [[VALIDATION_ARCHITECTURE.md]])
- [ ] Proper cross-references to AI-OS master documents (using [[link syntax]])
- [ ] Clear scope boundaries with explicit inclusions/exclusions
- [ ] Actionable architectural principles (not implementation details)
- [ ] Well-defined components and responsibilities
- [ ] Adequate security considerations (per Part 12)
- [ ] Defined governance processes where applicable (per [[COUNCILS.md]])
- [ ] Recorded architecture decisions with rationale (ADR format)
- [ ] Objective, verifiable conformance criteria
- [ ] Checkable invariants with permanence
- [ ] Clear interface contracts (not implementations)
- [ ] Technology neutrality and implementation independence
- [ ] Audience identification with specific information needs
- [ ] Extension point intentionality and discoverability

**Success Criteria**:
- All Critical findings resolved or mitigated with ARB approval
- Conformance level appropriate for the Part met (typically L3-L4 for Architecture Parts)
- No violations of architectural invariants or constraints
- All Cross-References valid and functional
- Publication readiness confirmed

**Failure Conditions**:
- Missing required sections per [[PART_TEMPLATE.md]]
- Violations of architectural constraints (exactly 4 CC, 9 CM, EventBus sole mechanism, etc.)
- Missing or invalid correlation/causation IDs in events
- Principle violations requiring ARB exemption without justification
- Publication blockers not addressed

**Related Review Prompts**:
- Consistency Review Prompt
- Publication Readiness Prompt
- Architecture Compliance Review Prompt
- Improvement Review Prompt
- Cross-Reference Review Prompt

**Review Depth**: Deep (comprehensive evaluation against all relevant criteria)
**Recommended Model**: Claude Opus 4.8
**Estimated Context Size**: 8000-12000 tokens (depends on part size)

---

### Project Knowledge Document Review Prompt

**Purpose**: Evaluate project knowledge documents for accuracy, completeness, relevance, and alignment with AI-OS architectural direction, assessing value to stakeholders and architectural governance.

**When to Use**: Reviewing roadmaps, research summaries, ecosystem documentation, and implementation guides, particularly for artifacts informing strategic or operational decisions.

**Expected Outputs**: Assessment report covering:
- Document value and relevance to current AI-OS architecture
- Accuracy gaps and correction requirements
- Alignment with [[ENGINEERING_PRINCIPLES.md]] and architectural direction
- Completeness of coverage for stated topic and audience
- Recommendations for enhancement or retirement
- Stakeholder suitability assessment

**Evidence Required**:
- Direct quotes or paraphrases showing inaccuracies
- Comparisons to master documents (Parts 1-15, [[ENGINEERING_PRINCIPLES.md]], [[AI_OS_MASTER_CONTEXT.md]])
- External source validation for factual claims
- Audience analysis documentation
- Relevance mapping to current AI-OS initiatives

**Review Checklist**:
- [ ] Accuracy of technical information and references
- [ ] Completeness of coverage for the stated topic
- [ ] Relevance to current AI-OS architecture and roadmap (per [[AI_OS_MASTER_CONTEXT.md]])
- [ ] Clear audience identification and appropriate technical depth
- [ ] Proper citation of sources with access dates
- [ ] Absence of duplicated content that should be referenced from master documents
- [ ] Logical organization and readability
- [ ] Actionable insights and recommendations (where applicable)
- [ ] Alignment with AI-OS engineering principles
- [ ] Proper formatting and style adherence
- [ ] Working links and functional cross-references
- [ ] Clear distinction between specification and implementation guidance
- [ ] Appropriate technical depth for intended audience
- [ ] Absence of speculative content presented as fact
- [ ] Proper differentiation between current state and future proposals

**Success Criteria**:
- No Critical accuracy findings
- Document provides clear value to intended audience
- Alignment with current architectural direction confirmed
- All external claims properly sourced and validated
- Ready for stakeholder distribution with minor improvements

**Failure Conditions**:
- Material inaccuracies that could mislead stakeholders
- Significant duplication of master document content
- Audience mismatch causing usability issues
- Lack of clear purpose or relevance to AI-OS
- Unsubstantiated claims presented as fact

**Related Review Prompts**:
- Research Document Review Prompt
- Implementation Guide Review Prompt
- Consistency Review Prompt
- Publication Readiness Prompt

**Review Depth**: Standard (focus on content quality and relevance)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 4000-8000 tokens

---

### Template Review Prompt

**Purpose**: Validate that templates follow AI-OS documentation standards and provide the intended structure for consistent artifact creation, ensuring usability and conformity with documentation principles.

**When to Use**: Reviewing any template file (ADR, architecture part, review, etc.) before distribution or after modification, particularly when establishing new template standards.

**Expected Outputs**: Template validation report confirming:
- Structural completeness and placeholder correctness
- Instructions clarity and actionability
- Conformance with documentation principles
- Usability for target audience
- Alignment with appropriate master templates

**Evidence Required**:
- Direct template inspection against requirements
- Comparison to master templates ([[PART_TEMPLATE.md]], [[ADR_TEMPLATE.md]])
- Placeholder validation and usage examples
- Instruction clarity assessment
- Formatting and styling verification

**Review Checklist**:
- [ ] All required sections present with appropriate headings
- [ ] Clear placeholder markings (e.g., [PART_NAME], [TODO]) where input is needed
- [ ] Instructions for template usage are clear and actionable
- [ ] Proper AI-OS document formatting and styling
- [ ] Correct example content that demonstrates usage
- [ ] Alignment with [[PART_TEMPLATE.md]] or [[ADR_TEMPLATE.md]] as appropriate
- [ ] Valid Mermaid diagram placeholders where applicable
- [ ] Proper RFC 2119 terminology guidance in instructions
- [ ] Technology-neutral structure that doesn't prescribe implementations
- [ ] Clear ownership and maintenance guidelines
- [ ] Version control and change history instructions
- [ ] Accessibility considerations in formatting
- [ ] Conformance with [[DOCUMENTATION_PRINCIPLES.md]]
- [ ] Appropriate complexity for intended user skill level

**Success Criteria**:
- Template produces conformant artifacts when used correctly
- All placeholders clear and unambiguous
- Instructions enable successful first-time use
- No structural deficiencies affecting artifact quality
- Ready for broad distribution and adoption

**Failure Conditions**:
- Missing required sections preventing conformant artifact creation
- Ambiguous or incorrect placeholders causing user errors
- Instructions insufficient for proper template use
- Structural issues that violate documentation principles
- Technology-specific constraints limiting implementation flexibility

**Related Review Prompts**:
- Publication Readiness Prompt
- Architecture Part Review Prompt
- ADR Review Prompt
- Consistency Review Prompt

**Review Depth**: Standard (focus on template structure and placeholder accuracy)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 2000-4000 tokens

---

### Diagram Review Prompt

**Purpose**: Evaluate architectural diagrams for correctness, clarity, consistency, and value beyond textual description, ensuring effective communication of architectural concepts.

**When to Use**: Reviewing any Mermaid diagram or architectural visualization in AI-OS documents, particularly when assessing conformance with diagramming standards.

**Expected Outputs**: Diagram assessment covering:
- Syntax validity and renderability
- Semantic accuracy reflecting described architecture
- Notation consistency with AI-OS standards
- Communicative effectiveness for intended audience
- Value addition beyond textual description

**Evidence Required**:
- Diagram rendering validation (screenshots or live render confirmation)
- Comparison to architectural description in accompanying text
- Reference to AI-OS diagramming standards and conventions
- Notation and styling consistency checks
- Accessibility validation (contrast, labels, alternatives)

**Review Checklist**:
- [ ] Valid Mermaid syntax that renders correctly
- [ ] Semantic accuracy reflecting the described architecture
- [ ] Consistent notation and styling with other AI-OS diagrams
- [ ] Appropriate level of detail (architectural, not implementation)
- [ ] Clear labels, captions, and explanations
- [ ] Proper use of shapes, colors, and line styles per AI-OS conventions
- [ ] Logical flow and readable layout
- [ ] Accessibility considerations (contrast, labels, alternatives)
- [ ] Consistency with accompanying textual description
- [ ] Value addition beyond what text alone could convey
- [ ] Proper scaling and zoom-appropriate detail levels
- [ ] Correct representation of relationships, dependencies, and flows
- [ ] Alignment with AI-OS diagramming standards and conventions
- [ ] Absence of redundant or duplicate information
- [ ] Proper use of subgraphs, click events, and advanced features where appropriate
- [ ] Technology neutrality in representation

**Success Criteria**:
- Diagram renders correctly in standard Mermaid editors
- Semantically accurate representation of architecture
- Clear value beyond textual description
- Consistent with AI-OS diagramming conventions
- Accessible to intended audience
- Ready for inclusion in architecture documents

**Failure Conditions**:
- Invalid Mermaid syntax preventing rendering
- Semantic inaccuracies misrepresenting architecture
- Missing value beyond textual description
- Inconsistent notation causing confusion
- Accessibility barriers preventing comprehension
- Overly detailed or insufficiently detailed for architectural communication

**Related Review Prompts**:
- Architecture Part Review Prompt (for diagram validation within parts)
- Consistency Review Prompt (for cross-diagram consistency)
- Improvement Review Prompt (for diagram enhancement suggestions)
- Publication Readiness Prompt

**Review Depth**: Standard (focus on diagram quality and accuracy)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 2000-5000 tokens (depends on diagram complexity)

---

### Research Document Review Prompt

**Purpose**: Assess research documents for methodological soundness, relevance to AI-OS, and quality of insights and recommendations, ensuring research supports architectural decisions and evolution.

**When to Use**: Reviewing technology evaluations, literature reviews, trend analyses, and feasibility studies, particularly when informing architectural evolution or investment decisions.

**Expected Outputs**: Evaluation report covering:
- Research rigor and methodological soundness
- Relevance to AI-OS architectural goals and principles
- Quality of analysis and logical evidence-conclusion connection
- Actionability of recommendations for architectural evolution
- Identification of research gaps and open questions
- Alignment with [[ENGINEERING_PRINCIPLES.md]] research principles

**Evidence Required**:
- Methodology evaluation against research type standards
- Source quality and credibility assessment
- Logical connection validation between evidence and conclusions
- Relevance mapping to current AI-OS initiatives ([[AI_OS_MASTER_CONTEXT.md]])
- Gap analysis against known architectural challenges
- Bias and objectivity evaluation

**Review Checklist**:
- [ ] Clear research question, objectives, and scope
- [ ] Sound methodology appropriate to the research type
- [ ] Quality and credibility of sources referenced
- [ ] Proper citation format with access dates for online sources
- [ ] Objective analysis free from inappropriate bias
- [ ] Relevance to AI-OS architectural goals and principles
- [ ] Identification of limitations, assumptions, and uncertainties
- [ ] Logical connection between evidence and conclusions
- [ ] Practical, actionable recommendations (where applicable)
- [ ] Clear identification of research gaps and open questions
- [ ] Alignment with AI-OS engineering principles
- [ ] Proper distinction between facts, analysis, and opinion
- [ ] Consideration of both opportunities and risks
- [ ] Appropriate technical depth for intended audience
- [ ] Reproducibility of methods where applicable
- [ ] Ethical considerations in research conduct

**Success Criteria**:
- Methodologically sound research appropriate to stated objectives
- Clear relevance to AI-OS architectural goals
- Actionable recommendations supporting evolution or improvement
- Proper acknowledgment of limitations and uncertainties
- Ready for use in architectural decision-making processes

**Failure Conditions**:
- Fatally flawed methodology invalidating conclusions
- Lack of relevance to AI-OS architectural context
- Unsupported conclusions not derivable from evidence
- Material bias affecting objectivity and usefulness
- Failure to identify significant limitations or uncertainties
- Inappropriate technical depth for intended use case

**Related Review Prompts**:
- Technology Evaluation Prompt (from research categories)
- Literature Review Prompt
- Future Trends Assessment Prompt
- Consistency Review Prompt
- Publication Readiness Prompt

**Review Depth**: Standard (focus on research quality and applicability)
**Recommended Model**: Claude Opus 4.8
**Estimated Context Size**: 4000-8000 tokens

---

### Prompt Library Review Prompt

**Purpose**: Evaluate prompt libraries for effectiveness, consistency, and alignment with AI-OS prompt engineering principles, ensuring usability and quality for target audiences.

**When to Use**: Reviewing any prompt collection (including this document) for quality and usability, particularly during maintenance cycles or after significant updates.

**Expected Outputs**: Assessment report covering:
- Prompt clarity and effectiveness
- Consistency with AI-OS prompt engineering philosophy
- Usability for target audiences (architects, reviewers, engineers)
- Alignment with documentation and architectural standards
- Identification of gaps and improvement opportunities

**Evidence Required**:
- Direct prompt inspection against checklist items
- Comparison to AI-OS documentation standards
- Usability assessment through application samples
- Consistency validation across prompt collection
- Effectiveness evaluation through sample document reviews

**Review Checklist**:
- [ ] Clear purpose and intended use cases for each prompt
- [ ] Consistency with AI-OS prompt engineering philosophy (evidence-based, constructive)
- [ ] Proper reference to AI-OS master documents instead of content duplication
- [ ] Correct RFC 2119 terminology usage in prompts and expected outputs
- [ ] Technology neutrality and implementation independence in generated outputs
- [ ] Clear, actionable expected outputs that enable verification
- [ ] Appropriate recommended models for task complexity
- [ ] Realistic estimated context sizes
- [ ] Comprehensive review checklists that cover key evaluation areas
- [ ] Logical organization and categorization of prompts
- [ ] Consistent formatting and styling across all prompts
- [ ] Working cross-references to related prompts and documents
- [ ] Absence of duplicated content that should be referenced
- [ ] Clear distinction between prompt templates and example usage
- [ ] Usability for intended audience (architects, reviewers, engineers)
- [ ] Evidence requirements sufficient to support findings
- [ ] Success criteria clear and achievable

**Success Criteria**:
- Prompts consistently elicit useful, targeted feedback
- Collection enables thorough, objective reviews
- Ready for broad distribution to review community
- Aligned with AI-OS review philosophy and standards
- Supports consistent review quality across artifacts

**Failure Conditions**:
- Prompts eliciting generic or unactionable feedback
- Inconsistent application across similar artifacts
- Missing evidence requirements compromising review validity
- Unclear success criteria preventing effective review completion
- Significant usability barriers for target audience

**Related Review Prompts**:
- Architecture Part Review Prompt (for reviewing prompt library as architecture-adjacent)
- Consistency Review Prompt
- Improvement Review Prompt
- Publication Readiness Prompt

**Review Depth**: Standard (focus on prompt quality and usability)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 3000-6000 tokens

---

### ADR Review Prompt

**Purpose**: Validate Architecture Decision Records for proper decision recording, traceability, and architectural significance, ensuring ADRs serve as reliable historical records of principled decision-making.

**When to Use**: Reviewing any ADR for completeness, correctness, and conformance to AI-OS ADR standards, particularly before ARB approval or when assessing decision impact.

**Expected Outputs**: ADR assessment report covering:
- Decision traceability and historical value
- Rationale quality and alternatives consideration
- Conformance with [[ADR_TEMPLATE.md]]
- Architectural significance assessment
- Alignment with [[ENGINEERING_PRINCIPLES.md]] principles
- Proper validation criteria and success metrics
- Governance and approval documentation

**Evidence Required**:
- Direct ADR inspection against template requirements
- Validation of decision statement clarity and outcome
- Assessment of context, problem, alternatives sections
- Verification of rationale connection to principles/requirements
- Confirmation of approval and governance documentation
- Impact analysis validation

**Review Checklist**:
- [ ] Proper ADR structure following [[ADR_TEMPLATE.md]]
- [ ] Clear decision statement with unambiguous outcome
- [ ] Adequate context describing the situation necessitating the decision
- [ ] Well-reasoned problem statement linked to requirements/principles
- [ ] Comprehensive consideration of alternatives with clear rejection reasons
- [ ] Decision rationale tied to AI-OS principles, requirements, and constraints
- [ ] Analysis of consequences (both positive and negative)
- [ ] Identification of risks and mitigation strategies
- [ ] Assessment of architecture impact on affected parts
- [ ] Evaluation of conformance impact with standards and policies
- [ ] Practical migration strategy (if applicable)
- [ ] Clear validation criteria and success metrics
- [ ] Proper approval and governance documentation (per [[COUNCILS.md]])
- [ ] Quality references to related documents, standards, and resources
- [ ] Effective use of Mermaid diagrams for complex concepts (lifecycle, impact, migration)
- [ ] Clear traceability to AI-OS master documents and related ADRs
- [ ] Appropriate level of detail for the decision's significance
- [ ] Technology-neutral focus on architectural concerns
- [ ] Conformance with RFC 2119 terminology standards
- [ ] Human-in-the-loop validation where required for value decisions

**Success Criteria**:
- ADR provides clear, traceable record of principled decision-making
- All required sections complete and to standard
- Rationale well-supported by evidence and principles
- Alternatives thoroughly considered with justified rejections
- Approval and governance processes properly documented
- Ready for inclusion in architectural historical record

**Failure Conditions**:
- Missing critical sections preventing decision understanding
- Unclear decision statement or ambiguous outcome
- Inadequate alternatives consideration or unjustified rejections
- Rationale not connected to principles or requirements
- Missing approval documentation for binding decisions
- Failure to assess architectural impact conformance

**Related Review Prompts**:
- Architecture Part Review Prompt (for impact on related parts)
- Consistency Review Prompt (for cross-ADR consistency)
- Publication Readiness Prompt
- Improvement Review Prompt
- Cross-Reference Review Prompt (for ADR link validation)

**Review Depth**: Standard (focus on decision recording quality and architectural significance)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 3000-5000 tokens

---

### Repository Structure Review Prompt

**Purpose**: Evaluate repository organization for clarity, adherence to AI-OS standards, and ease of navigation and contribution, ensuring effective collaboration and artifact management.

**When to Use**: Reviewing repository structure during setup, reorganization, or audit preparation, particularly when assessing contributor onboarding and maintenance burden.

**Expected Outputs**: Assessment report covering:
- Directory structure clarity and AI-OS convention alignment
- Documentation findability and completeness
- Configuration standards compliance
- Contributor experience and onboarding efficiency
- Alignment with [[REPOSITORY_ECOSYSTEM.md]] guidelines
- Public API and internal implementation separation

**Evidence Required**:
- Directory structure inspection and comparison to standards
- Documentation accessibility and completeness validation
- Configuration file examination for standards compliance
- Contribution guideline assessment for clarity and completeness
- Repository navigation and discovery assessment
- Public vs. internal boundary validation

**Review Checklist**:
- [ ] Logical, intuitive directory structure aligned with AI-OS conventions
- [ ] Clear separation of source code, documentation, configuration, and assets
- [ ] Proper placement of architecture documents in architecture/ directory
- [ ] Consistent naming conventions for files and directories
- [ ] Presence of essential documentation (README, CONTRIBUTING, CODE_OF_CONDUCT)
- [ ] Valid license file with appropriate open-source licensing
- [ ] Proper .gitignore excluding build artifacts and sensitive files
- [ ] Standard configuration files for build, test, and CI/CD systems
- [ ] Clear contribution guidelines and development processes
- [ ] Proper version tagging and release procedures
- [ ] Accessibility of key documents for new contributors
- [ ] Alignment with [[REPOSITORY_ECOSYSTEM.md]] guidelines
- [ ] Proper documentation of dependencies and installation procedures
- [ ] Clear distinction between public APIs and internal implementation
- [ ] Effective use of branches, tags, and release management
- [ ] Proper documentation of architecture decision locations (ADRs)
- [ ] Resource quota visibility and monitoring capability
- [ ] Observability and telemetry accessibility
- [ ] Technology neutrality in tooling and infrastructure choices

**Success Criteria**:
- Repository structure supports effective collaboration
- Key documents easily accessible to stakeholders
- Contributor onboarding facilitated by clear organization
- Configuration standards properly implemented
- Ready for broad contributor engagement and maintenance

**Failure Conditions**:
- Structural confusion impeding navigation and discovery
- Missing essential documentation hindering onboarding
- Configuration standards violations affecting reproducibility
- Poor separation of concerns creating maintenance burden
- Accessibility barriers preventing stakeholder engagement
- Technology choices creating unnecessary conformance risks

**Related Review Prompts**:
- Dependency Analysis Prompt (from research categories)
- Repository Initialization Prompt
- Consistency Review Prompt
- Improvement Review Prompt
- Publication Readiness Prompt

**Review Depth**: Standard (focus on organizational quality and standards compliance)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 2000-4000 tokens

---

### Mermaid Diagram Review Prompt

**Purpose**: Specialized validation of Mermaid diagrams for syntax correctness, semantic accuracy, and adherence to AI-OS diagramming standards, providing technical assurance of diagram quality.

**When to Use**: Focused review of Mermaid syntax and rendering quality in any AI-OS document, particularly when assessing technical diagram validity.

**Expected Outputs**: Technical assessment report covering:
- Mermaid code validity and parsing accuracy
- Diagram rendering fidelity and correctness
- Standards compliance verification
- Technical quality metrics and issue identification
- Remediation guidance for identified issues

**Evidence Required**:
- Direct Mermaid code validation through parsing engine
- Rendered output validation against expectations
- Comparison to AI-OS Mermaid standards and conventions
- Syntax error identification and localization
- Semantic accuracy validation against architectural description
- Accessibility and usability testing

**Review Checklist**:
- [ ] Valid Mermaid syntax that parses without errors
- [ ] Correct diagram type selection for the information being conveyed
- [ ] Proper use of Mermaid components (nodes, edges, labels, etc.)
- [ ] Consistent direction (left-to-right, top-to-bottom) as appropriate
- [ ] Semantic use of shapes and line styles per AI-OS conventions
- [ ] Readable layout with appropriate spacing and alignment
- [ ] Proper labeling of all elements with clear, concise text
- [ ] Consistent use of colors, fonts, and styling per AI-OS guidelines
- [ ] Absence of redundant or duplicate information
- [ ] Proper scaling for different viewing contexts
- [ ] Correct representation of relationships, dependencies, and flows
- [ ] Alignment with accompanying textual description
- [ ] Proper use of subgraphs, click events, and advanced features where appropriate
- [ ] Accessibility considerations (contrast ratios, alternative descriptions)
- [ ] Compliance with AI-OS Mermaid standards and best practices
- [ ] Ability to render correctly in standard Mermaid live editors
- [ ] Technological neutrality in representation choices
- [ ] Proper use of architectural layering and separation conventions

**Success Criteria**:
- Diagram parses and renders without errors
- Semantically accurate and technically correct
- Compliant with AI-OS Mermaid standards
- Accessible and usable by intended audience
- Ready for publication in architecture documents

**Failure Conditions**:
- Parsing errors preventing diagram rendering
- Semantic inaccuracies misrepresenting architecture
- Non-compliance with AI-OS Mermaid standards
- Technical defects impairing usability or comprehension
- Accessibility barriers preventing audience access
- Missing value beyond alternative textual representations

**Related Review Prompts**:
- Diagram Review Prompt (broader diagram evaluation)
- Architecture Part Review Prompt (for diagram validation within parts)
- Consistency Review Prompt (for cross-diagram consistency)

**Review Depth**: Deep (focus on technical diagram quality and standards adherence)
**Recommended Model**: Claude Sonnet 5
**Estimated Context Size**: 1000-3000 tokens

---

### Governance Document Review Prompt

**Purpose**: Evaluate governance documents (policies, procedures, council charters) for clarity, enforceability, and alignment with AI-OS governance frameworks, ensuring effective governance operation.

**When to Use**: Reviewing any governance-related document for quality and effectiveness, particularly when establishing or updating governance structures.

**Expected Outputs**: Assessment report covering:
- Document clarity and actionability for intended audience
- Enforceability and compliance verification capability
- Alignment with [[COUNCILS.md]] governance structures
- Reference to relevant AI-OS master documents and principles
- Effectiveness metrics and reporting mechanisms adequacy
- Practical implementation considerations

**Evidence Required**:
- Direct inspection against governance requirements and standards
- Comparison to [[COUNCILS.md]] council structures and procedures
- Validation of enforceability through compliance mechanisms
- Reference validation to AI-OS master documents
- Practicality assessment through implementation consideration
- Effectiveness evaluation through metrics and reporting review

**Review Checklist**:
- [ ] Clear purpose, scope, and applicability statement
- [ ] Well-defined roles, responsibilities, and accountability
- [ ] Specific, measurable, and enforceable requirements
- [ ] Proper alignment with AI-OS governance structures (Councils, AI Agency)
- [ ] Reference to relevant AI-OS master documents and principles
- [ ] Clear procedures for implementation, monitoring, and enforcement
- [ ] Defined review and update cycles with ownership
- [ ] Proper version control and change history tracking
- [ ] Accessibility and clarity for intended audience
- [ ] Consideration of practical implementation constraints
- [ ] Alignment with relevant external standards where applicable
- [ ] Proper exception handling and waiver processes (if needed)
- [ ] Clear communication and training requirements
- [ ] Effective metrics and reporting mechanisms
- [ ] Proper documentation of applicability and effective dates
- [ ] Alignment with AI-OS engineering principles for governance
- [ ] Technology-neutral focus on governance concerns rather than specific implementations
- [ ] Human-in-the-loop provisions for value-laden decisions
- [ ] Audit trail and accountability mechanisms adequacy
- [ ] Escalation path clarity and effectiveness
- [ ] Veto/override capability documentation where appropriate

**Success Criteria**:
- Governance document enables effective council operation
- Requirements clear, measurable, and enforceable
- Alignment with AI-OS governance frameworks confirmed
- Practical implementation considerations addressed
- Ready for adoption and use in governance operations

**Failure Conditions**:
- Unclear purpose or scope preventing effective governance
- Unenforceable requirements lacking compliance mechanisms
- Misalignment with AI-OS governance structures
- Missing essential governance components (roles, procedures, accountability)
- Practical implementation barriers preventing adoption
- Inadequate audit trail or accountability mechanisms
- Missing human-in-the-loop provisions for value decisions

**Related Review Prompts**:
- Policy Generation Prompt (from governance categories)
- Compliance Check Prompt
- Council Decision Support Prompt
- Consistency Review Prompt
- Improvement Review Prompt

**Review Depth**: Standard (focus on governance quality and enforceability)
**Recommended Model**: Claude Opus 4.8
**Estimated Context Size**: 3000-6000 tokens

---

## Review Workflows

Standardized approaches for conducting reviews using the prompt collection.

### Initial Review Workflow

**Purpose**: First-time evaluation of a new or significantly changed artifact to identify major issues and establish baseline quality.

**When to Use**: Reviewing newly created documents, major updates, or artifacts entering the review process for the first time.

**Prompts to Use**:
1. Appropriate domain-specific review prompt (e.g., Architecture Part Review Prompt for architecture parts)
2. Consistency Review Prompt
3. Publication Readiness Prompt

**Workflow**:
1. Begin with domain-specific review to assess core quality and correctness
2. Apply consistency review to check alignment with related artifacts
3. Conduct publication readiness to identify distribution blockers
4. Synthesize findings into initial review report with prioritized remediation items

**Expected Outputs**: Comprehensive initial review report with findings, recommendations, and publication readiness assessment.

### Improvement Review Workflow

**Purpose**: Focused evaluation to identify enhancement opportunities while confirming that core requirements are met.

**When to Use**: Reviewing established documents for quality improvement, or after addressing initial review feedback.

**Prompts to Use**:
1. Improvement Review Prompt (domain-specific if available)
2. Consistency Review Prompt
3. Publication Readiness Prompt

**Workflow**:
1. Verify that fundamental requirements and correctness are maintained
2. Identify opportunities for enhancement in clarity, completeness, and usability
3. Check consistency with evolving AI-OS standards and related documents
4. Confirm continued publication readiness
5. Generate improvement-focused recommendations

**Expected Outputs**: Improvement opportunity report with specific enhancement suggestions and validation that core quality is preserved.

### Consistency Review Workflow

**Purpose**: Dedicated evaluation of cross-artifact alignment in terminology, references, and architectural patterns.

**When to Use**: When consistency is the primary concern, or as part of other review workflows.

**Prompts to Use**:
1. Consistency Review Prompt (primary)
2. Related domain-specific review prompt for context

**Workflow**:
1. Establish baseline understanding with domain-specific prompt if needed
2. Apply consistency review to check:
   - Terminology alignment with [[GLOSSARY.md]] and related documents
   - Cross-reference validity and correctness
   - Reference to AI-OS master documents instead of content duplication
   - Consistent architectural patterns and styles
   - Uniform application of principles and conventions
   - Consistent Mermaid diagram notation and styling
   - Uniform RFC 2119 terminology usage
3. Document inconsistencies and provide specific alignment recommendations

**Expected Outputs**: Detailed consistency report highlighting discrepancies and specific alignment actions.

### Publication Review Workflow

**Purpose**: Final verification that an artifact meets all requirements for stakeholder distribution.

**When to Use**: Preparing documents for release, after addressing review feedback, or before official publication.

**Prompts to Use**:
1. Publication Readiness Prompt (primary)
2. Domain-specific review prompt for final quality check
3. Consistency Review Prompt

**Workflow**:
1. Apply publication readiness checklist to verify all distribution requirements
2. Conduct domain-specific review to confirm core quality is maintained
3. Verify consistency with related artifacts and standards
4. Address any remaining blockers to publication
5. Generate final publication recommendation

**Expected Outputs**: Publication readiness assessment with go/no-go recommendation and specific resolution items for any blockers.

### Freeze Review Workflow

**Purpose**: Evaluation to determine if an artifact is suitable for freezing (making immutable without formal change control).

**When to Use**: Considering long-term stability for foundational documents, or before declaring a version stable.

**Prompts to Use**:
1. Freeze Consideration Prompt (derived from review template)
2. Publication Readiness Prompt (must pass first)
3. Consistency Review Prompt
4. Architecture Compliance Review Prompt

**Workflow**:
1. Verify publication readiness as prerequisite
2. Assess architectural stability and principle alignment
3. Check consistency with related foundational documents
4. Evaluate need for future changes vs. stability benefits
5. Confirm appropriate change control processes are documented
6. Generate freeze recommendation with conditions

**Expected Outputs**: Freeze suitability assessment with recommendation and required conditions for freezing.

### Cross-Reference Review Workflow

**Purpose**: Specialized focus on validating all cross-references within and between documents.

**When to Use**: When reference integrity is critical, or as part of consistency or publication reviews.

**Prompts to Use**:
1. Consistency Review Prompt (primary focus on cross-references)
2. Domain-specific review prompt for context

**Workflow**:
1. Extract all cross-references from the document under review
2. Verify each reference:
   - Correct [[link syntax]] usage
   - Points to existing document or section
   - References current version (not outdated)
   - Avoids duplication of content that should be referenced
   - Properly formatted external references with access dates
3. Check for missing references that should exist
4. Identify circular references or reference chains that create confusion
5. Validate that references add value and are not excessive

**Expected Outputs**: Cross-reference validation report with working/broken references and specific correction actions.

### Architecture Compliance Review Workflow

**Purpose**: Deep evaluation of an artifact's conformance to AI-OS architectural specification and principles.

**When to Use**: When architectural integrity is the primary concern, such as for specification documents or foundational artifacts.

**Prompts to Use**:
1. Architecture Part Review Prompt (or domain-specific equivalent)
2. Publication Readiness Prompt
3. Consistency Review Prompt
4. Improvement Review Prompt

**Workflow**:
1. Conduct deep architectural review against specification parts and principles
2. Verify publication readiness requirements are met
3. Check consistency with related architectural documents
4. Identify improvement opportunities that enhance architectural alignment
5. Synthesize findings into architectural compliance assessment

**Expected Outputs**: Architecture compliance report with conformance level (L1-L4), specific deviations, and remediation priorities.

## Review Best Practices

Follow these practices to ensure high-quality, effective reviews, incorporating principles from all referenced documents:

### Be Evidence-Driven
- Always reference specific lines, sections, or examples when making observations
- Base conclusions on observable facts rather than interpretations
- Provide direct quotes or paraphrases when highlighting issues
- Link findings to specific requirements, principles, or standards from [[ENGINEERING_PRINCIPLES.md]], [[VALIDATION_ARCHITECTURE.md]], etc.

### Maintain Objectivity
- Separate personal preferences from objective quality criteria
- Apply the same standards regardless of author or document history
- Focus on what the document contains, not what you think it should contain
- Acknowledge strengths as well as areas for improvement
- Follow the principle consistency requirements from [[ENGINEERING_PRINCIPLES.md]] Section 12.12

### Provide Actionable Feedback
- Every criticism should be accompanied by a specific suggestion for improvement
- Focus on how to enhance the document rather than just what's wrong
- Prioritize recommendations by impact and implementation effort
- Distinguish between blocking issues and quality enhancements
- Follow the constructive feedback principle from the Review Philosophy section

### Consider Context and Audience
- Evaluate the document from the perspective of its intended audience
- Assess whether technical depth matches audience expertise
- Verify that the document serves its stated purpose effectively
- Consider the document's role in the larger AI-OS ecosystem
- Apply the audience awareness principles from documentation guidelines

### Follow Established Processes
- Use the appropriate review workflow for the situation
- Apply prompts consistently across similar artifacts
- Document review decisions and rationale for traceability
- Respect established review roles and approval authorities from [[COUNCILS.md]]
- Follow governance model requirements for decision-making and oversight

### Balance Depth and Efficiency
- Match review depth to the document's importance and complexity
- Focus effort on high-impact areas rather than trivial details
- Use checklists to ensure comprehensive coverage without getting lost in minutiae
- Know when to stop polishing and accept "good enough" for the context
- Apply the depth efficiency principles from [[VALIDATION_ARCHITECTURE.md]] Section 8

### Promote Learning and Improvement
- Treat reviews as opportunities to strengthen both the document and reviewer understanding
- Identify patterns that suggest broader template or process improvements
- Share effective review techniques with colleagues
- Document lessons learned for future review refinement
- Apply the continuous improvement principles from validation and engineering documentation

## Review Anti-patterns

Avoid these common pitfalls that undermine review effectiveness, with specific references to architectural principles:

### Over-Focus on Trivialities
- Spending excessive time on formatting minutiae while missing substantive issues
- Correcting typos while ignoring architectural inconsistencies
- Prioritizing word choice over structural clarity
- Focusing on preferred terminology instead of actual correctness
- *Violates*: Focus on architectural integrity over cosmetic issues (Review Philosophy)

### Subjective Evaluations
- Rejecting content based on personal style preferences
- Applying different standards based on author familiarity
- Confusing "I would have written it differently" with "it is incorrect"
- Letting personal biases influence assessment of technical merit
- *Violates*: Objective Reviews principle and evidence-based requirement

### Missing the Forest for the Trees
- Getting lost in detail while missing major structural problems
- Validating individual sections while ignoring overall coherence
- Checking compliance with details while missing principle violations
- Focusing on checklist completion rather than actual quality
- *Violates*: Architecture-First Thinking principle and principle adherence requirement

### Inadequate Evidence
- Making assertions without specific document references
- Relying on memory or assumptions instead of verifying content
- Citing principles or requirements without showing how they apply
- Providing vague feedback like "unclear" without explaining why
- *Violates*: Evidence-Based Evaluation principle and validation requirements

### Lack of Actionability
- Identifying problems without suggesting how to fix them
- Providing only criticism without recognition of what works well
- Making recommendations that are vague or impossible to implement
- Focusing on blame rather than improvement
- *Violates*: Constructive Feedback principle and actionable feedback requirement

### Process Violations
- Skipping established review workflows for expediency
- Applying prompts inconsistently across similar artifacts
- Not documenting review decisions for traceability
- Overstepping review authority or ignoring approval processes
- *Violates*: Follow Established Processes best practice and governance requirements

### Misaligned Depth
- Applying superficial review to critical architectural documents
- Conducting exhaustive review of trivial or temporary artifacts
- Using deep review prompts when surface-level would suffice
- Failing to adjust depth based on document lifecycle stage
- *Violates*: Balance Depth and Efficiency best practice and conformance level appropriateness

## Review Quality Metrics

Measure review effectiveness using these indicators, aligned with validation and engineering principles:

### Finding Quality
- **Accuracy**: Percentage of review findings that are correct and actionable
- **Specificity**: Average specificity of findings (general vs. specific line references)
- **Impact rating**: Distribution of findings by severity (critical, major, moderate, minor)
- **Evidence strength**: Proportion of findings with strong documentary evidence
- *Aligns with*: Validation Architecture evidence requirements and principle adherence checking

### Review Efficiency
- **Coverage**: Percentage of relevant review criteria actually evaluated
- **Time efficiency**: Review thoroughness per unit time invested
- **Prompt utilization**: Appropriate use of specialized vs. general prompts
- **Workflow adherence**: Consistency with established review processes
- *Aligns with*: Review Lifecycle efficiency principles and workflow standardization

### Review Impact
- **Issue resolution**: Percentage of review findings that result in document improvements
- **Blocker identification**: Ability to find issues that would block publication or use
- **Improvement value**: Estimated quality improvement from addressing review findings
- **Recurrence reduction**: Decrease in similar issues across successive document versions
- *Aligns with*: Improvement Review Workflow effectiveness and continuous improvement principles

### Review Consistency
- **Inter-reviewer agreement**: Consistency of findings across different reviewers for same document
- **Standard application**: Uniformity of criteria application across document types
- **Prompt effectiveness**: Ability of prompts to elicit useful, targeted feedback
- **Criteria weighting**: Appropriate emphasis on different review dimensions per document type
- *Aligns with*: Consistency Review Workflow objectives and standardization requirements

## Prompt Maintenance

Keep this prompt library effective and current through regular maintenance, following architectural evolution principles:

### Regular Review Schedule
- **Quarterly**: Comprehensive review of all prompts for effectiveness and relevance
- **After major AI-OS updates**: Update prompts to reflect specification changes
- **When issues are identified**: Promptly address problems discovered during usage
- **Annually**: Assess overall library utility and identify gaps
- *Aligns with*: Evolution Principles Section 10 and continuous improvement requirements

### Update Triggers
- Changes to AI-OS Architecture Specification (Parts 1-15)
- Updates to [[ENGINEERING_PRINCIPLES.md]] or other master documents
- Identification of new review needs or artifact types
- Feedback from users about prompt effectiveness or usability
- Discovery of more effective prompt formulations
- Changes in recommended Claude models or capabilities
- *Aligns with*: Architectural Tradeoffs awareness and Evolution Principles

### Maintenance Process
1. **Evaluation**: Assess each prompt against current needs and effectiveness
2. **Revision**: Update prompts based on evaluation findings and best practices
3. **Validation**: Test revised prompts with sample documents to verify usefulness
4. **Documentation**: Record changes and rationale in version history
5. **Communication**: Inform stakeholders of significant updates to the prompt library
- *Aligns with*: Documentation Principles and validation-first execution

### Quality Indicators for Prompts
- **Clarity**: Prompts are unambiguous and easy to understand
- **Specificity**: Prompts elicit targeted, useful feedback rather than generic comments
- **Effectiveness**: Prompts consistently help reviewers find important issues
- **Efficiency**: Prompts facilitate thorough reviews without excessive overhead
- **Consistency**: Prompts produce comparable results across similar artifacts
- **Adaptability**: Prompts work well across different document types and complexity levels
- **Usability**: Prompts are easy to apply and integrate into review workflows
- *Aligns with*: Review Best Practices and quality metric requirements

## Cross References

- [[ARCHITECTURE_PROMPTS.md]]: Architecture creation prompts for reference during reviews
- [[CHATGPT_PROMPTS.md]]: ChatGPT-specific prompts for comparative understanding
- [[CLAUDE_PROMPTS.md]]: Claude-specific prompts for comparative understanding
- [[ENGINEERING_PRINCIPLES.md]]: Foundational principles that reviews must verify alignment with
- [[IMPLEMENTATION_GUIDE.md]]: Guidance that helps reviewers assess implementation-relevance balance
- [[PART_TEMPLATE.md]]: Structural template that Architecture Part reviews verify compliance with
- [[REVIEW_TEMPLATE.md]]: Standardized review documentation format referenced in prompts
- [[GLOSSARY.md]]: Terminology reference for consistency checking
- [[VALIDATION_ARCHITECTURE.md]]: Validation approaches that inform review thoroughness
- [[REPOSITORY_ECOSYSTEM.md]]: Repository structure reference for related reviews
- [[SKILLS_ECOSYSTEM.md]]: Skills ecosystem reference for prompt and extension reviews
- [[MCP_ECOSYSTEM.md]]: MCP ecosystem reference for tool and integration reviews
- [[COUNCILS.md]]: Governance structure reference for policy and procedure reviews
- [[AI_OS_MASTER_CONTEXT.md]]: Integrated view of current AI-OS state for relevance assessment
- [[ARCHITECTURE_DECISIONS.md]]: Historical record of principled decisions for traceability validation
- [[ADR_TEMPLATE.md]]: Template for ADR structure validation
- [[DOCUMENTATION_PRINCIPLES.md]]: Documentation standards for format and style validation

---

*This document establishes the standardized review methodology for AI-OS artifacts, ensuring consistent, objective, and high-quality evaluations aligned with architectural principles and engineering standards.*