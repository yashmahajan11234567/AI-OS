# IMPROVEMENT_PROMPT.md

# Improvement Philosophy for Part 11

This document provides the official improvement prompt for improving architecture sections in Part 11 of the AI-OS documentation. Follow this prompt exactly when improving any architecture section in Part 11 after review.

## Core Philosophy

**Improve architecture. Do NOT rewrite architecture. Preserve architectural intent.**

Every improvement must:
- Address a specific finding from review
- Be justified by concrete evidence from the review
- Preserve the original architectural intent and vision
- Preserve behavioural contracts (preconditions, postconditions, invariants)
- Preserve runtime invariants and assumptions
- Preserve authority boundaries and ownership models
- Avoid introducing new architecture or speculative designs
- Make minimal, focused changes that solve identified issues
- Maintain consistency with the rest of Part 11 and the overall AI-OS architecture

## Improvement Principles

### 1. Simplicity Rule
- Favor the simplest solution that addresses the review finding
- Avoid adding unnecessary layers, abstractions, or components
- If multiple solutions exist, choose the one with least complexity
- Remove unnecessary complexity when found during review
- Do not add features or capabilities not requested in the review

### 2. Evidence-Based Improvements
- Every change must be traceable to a specific review comment or finding
- Document which review finding each change addresses
- Do not implement improvements based on assumptions or speculation
- If uncertain about a change, seek clarification rather than implementing

### 3. Minimal Change Principle
- Make the smallest possible change that addresses the review finding
- Prefer editing existing text over adding new sections
- Only add new sections when explicitly required by review feedback
- Do not reorganize sections unless specifically requested in review
- Preserve existing structure and flow unless change is necessary
- Prevent unnecessary architecture expansion (no new components, layers, or abstractions)
- Avoid expanding architectural scope beyond what is strictly necessary to address findings

### 4. Architecture Preservation
- Never change the fundamental architecture or core concepts
- Preserve all architectural decisions made in the original text
- Do not introduce alternative architectures or alternatives
- Maintain alignment with the overall AI-OS architectural vision
- Respect boundaries between parts - do not introduce concepts from other parts
- Preserve behavioural contracts (preconditions, postconditions, invariants)
- Preserve runtime invariants and assumptions
- Preserve authority boundaries and ownership models

### 4.1. Mandatory Validations
- Validate RFC 2119 terminology usage (MUST, SHOULD, MAY, etc.)
- Verify cross-part consistency with definitions and usage in other AI-OS parts
- Ensure diagram consistency (labels, connections, notation, legends)
- Maintain architecture vs engineering separation (no implementation details)
- Check for implementation leakage (specific technologies, algorithms, code snippets)

### 5. Cross-Part Consistency
- Ensure terminology matches usage in other parts of AI-OS
- Align with definitions and concepts from architecture and validated patterns and conventions in other parts

### 6. Runtime Consistency
- Ensure architectural descriptions match actual runtime behavior described elsewhere
- Do not describe runtime behavior that contradicts other parts
- Ensure lifecycle descriptions match actual initialization and execution flows
- Maintain consistency with performance and scalability characterizations elsewhere

### 7. Security Consistency
- Ensure security considerations align with security model described in other parts
- Do not introduce security mechanisms that conflict with established patterns
- Ensure threat models and trust boundaries align with overall security architecture
- Do not weaken or change established security boundaries or assumptions

### 8. Terminology Consistency
- Use the same terms for concepts as used elsewhere in AI-OS
- Check the glossary and other parts for established definitions
- Do not introduce new terms for existing concepts
- When introducing new terms, ensure they are defined and consistent

### 9. Behavioral Contracts
- Ensure behavioral contracts (preconditions, postconditions, invariants) are preserved
- Do not weaken or strengthen contracts without explicit review direction
- Ensure error handling and error conditions remain consistent
- Maintain assumptions about component interactions and dependencies

### 10. Runtime Invariants
- Preserve all stated runtime invariants and assumptions
- Do not change assumptions about timing, ordering, or concurrency
- Ensure resource usage characteristics remain consistent
- Maintain assumptions about failure modes and error handling

## Improvement Categories

### Documentation Improvements
- Fix inaccuracies, ambiguities, or unclear descriptions
- Improve clarity, flow, and readability without changing technical content
- Fix typos, grammar, and formatting issues
- Improve examples and code snippets for clarity
- Ensure consistent use of terminology and notation
- Improve diagram labels and annotations for clarity
- Add missing definitions or clarifications only when explicitly requested

### Diagram Improvements
- Fix inaccurate or misleading diagram elements
- Improve clarity of diagram labels and connections
- Fix layout issues that obscure meaning
- Ensure diagram notation is consistent with legends and explanations
- Add missing labels or explanations only when requested
- Do not change diagram structure or add/remove components
- Only improve visual presentation, not semantic content

### Editorial Improvements
- Improve sentence structure and readability
- Fix grammatical errors and awkward phrasing
- Ensure consistent voice and tone
- Improve paragraph flow and transitions
- Fix inconsistent terminology usage
- Validate numbering (sections, lists, steps) remains correct
- Validate tables (structure, headers, data alignment)
- Validate Markdown syntax (links, emphasis, code blocks)
- Validate Mermaid diagrams (syntax, layout, labels)
- Validate terminology consistency (RFC 2119, domain-specific terms)
- Do not change technical meaning or architectural content

### Architecture Validation
- Verify all claims match actual design and implementation
- Remove unsupported claims or speculation
- Ensure all described components actually exist or are planned
- Verify interface descriptions match actual signatures (parameters, return types, behaviours)
- Verify data flow descriptions match actual implementation (sequence, transformation, protocols)
- Remove aspirational or future-looking statements not grounded in current design
- **Validate diagrams remain consistent after changes (labels, connections, notation)**
- **Verify behavioural contracts (preconditions, postconditions, invariants) are preserved**
- **Confirm runtime invariants and assumptions remain unchanged**
- **Check references to other sections, parts, or documents remain accurate**

## Prohibited Improvements

These types of changes are strictly prohibited unless explicitly requested in review feedback:

### Speculative Architecture
- Adding features, components, or capabilities not described in review
- Proposing alternative architectures or alternatives
- Adding "future extension" sections or speculative enhancements
- Introducing new patterns or approaches not already in the document
- Adding performance optimizations not requested in review

### Unnecessary Components
- Adding new components, modules, or layers not mentioned in review
- Introducing new abstraction layers without explicit direction
- Adding wrapper layers, facades, or adapters not requested
- Introducing new services, managers, or controllers not in original

### Unnecessary Abstractions
- Adding abstraction layers where none existed
- Creating interfaces or abstract classes where concrete implementations existed
- Introducing indirection layers without explicit review direction
- Adding configuration layers or mediation or broker layers not requested

### Implementation Leakage
- Including implementation details not appropriate for architecture level
- Adding code snippets, pseudocode, or implementation specifics
- Mentioning specific technologies, frameworks, or libraries unless already present
- Describing internal algorithms, data structures, or optimization techniques
- Including low-level details that belong in design or implementation documents

### Prompt Drift
- Drifting from the specific review feedback to address unrelated issues
- Addressing perceived issues not mentioned in review
- Making "preemptive" improvements for potential future issues
- Applying patterns or practices from other parts unless specifically relevant
- Making changes based on personal preference rather than review findings

### Contradictory Improvements
- Making changes that contradict other parts of AI-OS architecture
- Introducing inconsistencies with established patterns or conventions
- Creating conflicts with established terminology or definitions
- Making changes that weaken established security or reliability guarantees
- Introducing tensions with other architectural decisions

### Explicitly Forbidden Improvements
- **Speculative optimisation**: Adding performance improvements not requested in review (e.g., caching, indexing, algorithm changes)
- **Unnecessary abstractions**: Adding abstraction layers where none existed in the original design
- **Technology mandates**: Requiring specific technologies, frameworks, or libraries not already present
- **Architectural scope creep**: Expanding the scope or responsibilities of components beyond what is described

## Improvement Process

Follow this exact process when improving any section:

1. **Review Findings Carefully**
   - Read all review comments thoroughly
   - Identify specific, actionable findings
   - Separate factual inaccuracies from opinions or suggestions
   - Identify which findings require changes vs. which are commentary

2. **Justify Each Change**
   - For every change, explicitly identify which review finding it addresses
   - Document the justification in your thinking (not necessarily in the document)
   - If no specific finding justifies a change, do not make it
   - When uncertain, seek clarification rather than guessing

3. **Make Minimal Changes**
   - Start with the smallest possible change that addresses the finding
   - Only expand the change if absolutely necessary to fully address the finding
   - Prefer word-level or sentence-level changes over paragraph-level changes
   - Only add new sentences or paragraphs when absolutely necessary

4. **Preserve Everything Else**
   - Do not touch sections not mentioned in review findings
   - Preserve all architectural statements, diagrams, and examples
   - Keep all existing structure, headings, and formatting intact
   - Only change what is necessary to address specific findings

5. **Validate Consistency**
   - After making changes, verify consistency with:
     - Other parts of Part 11
     - Other parts of the AI-OS architecture
     - Established terminology and definitions
     - Established architectural patterns and conventions
     - Security model and trust boundaries
   - Ensure no contradictions were introduced

6. **Review Your Changes**
   - Reread the modified section to ensure it still makes sense
   - Verify that architectural intent is preserved
   - Check that you haven't introduced new issues
   - Confirm all changes are justified by review findings

## Section-Specific Guidelines

### For Overview Sections
- Only clarify or correct inaccuracies in the high-level description
- Do not change the fundamental purpose or scope
- Preserve the architectural vision and goals
- Only clarify relationships to other parts if specifically requested

### For Component Diagrams
- Only fix incorrect connections, missing labels, or unclear elements
- Do not add, remove, or change components
- Do not change the overall structure or layout unless specifically requested
- Improve legend or annotations only if unclear
- Preserve all existing notation and styling conventions

### For Data Flow Sections
- Only correct inaccuracies in data flow descriptions
- Do not change the actual data flows or add new ones
- Preserve the sequence and transformations of data
- Only clarify ambiguous descriptions if specifically requested
- Do not add performance characteristics or optimization details

### For Interface Specifications
- Only correct inaccurate descriptions of interfaces
- Do not change interface signatures, parameters, or return types
- Preserve all existing contracts and behavioral guarantees
- Only clarify ambiguous descriptions if specifically requested
- Do not add performance, security, or error handling details unless requested

### For Security Sections
- Only correct inaccuracies in security descriptions
- Do not change the security model, trust boundaries, or threat model
- Preserve all existing security mechanisms and guarantees
- Only clarify ambiguous descriptions if specifically requested
- Do not add new security mechanisms or controls unless requested

### For Performance Sections
- Only correct inaccuracies in performance descriptions
- Do not change performance characteristics, benchmarks, or guarantees
- Preserve all existing performance claims and measurements
- Only clarify ambiguous descriptions if specifically requested
- Do not add optimization strategies or performance improvements unless requested

### For Deployment Sections
- Only correct inaccuracies in deployment descriptions
- Do not change deployment architecture, topology, or procedures
- Preserve all existing deployment assumptions and requirements
- Only clarify ambiguous descriptions if specifically requested
- Do not add deployment strategies, patterns, or tools unless requested

## Final Publication-Quality Review

After making changes, perform this final review:

### Technical Accuracy
- [ ] All technical statements are accurate and justifiable
- [ ] No speculative or speculative statements remain
- [ ] All architectural claims are supportable
- [ ] No contradictions with other parts of AI-OS exist

### Architectural Integrity
- [ ] Fundamental architectural intent is preserved
- [ ] No new architecture, components, or abstractions added
- [ ] All existing components and relationships preserved
- [ ] Architectural vision and goals unchanged

### Consistency
- [ ] Terminology consistent with other parts of AI-OS
- [ ] Concepts and definitions match usage elsewhere
- [ ] Architectural patterns and conventions preserved
- [ ] Security model and trust boundaries unchanged
- [ ] Runtime behavior descriptions consistent elsewhere

### Quality and Clarity
- [ ] Grammar, spelling, and punctuation correct
- [ ] Sentences clear and unambiguous
- [ ] Paragraphs flow logically
- [ ] Diagrams clear and properly labeled
- [ ] Examples clear and illustrative

### Minimality
- [ ] No unnecessary changes made
- [ ] No speculative additions included
- [ ] No unnecessary abstraction layers added
- [ ] No implementation details leaked into architecture
- [ ] Every change justified by specific review finding

## Documentation of Changes

When submitting improvements, include a brief justification for each change referencing the specific review finding that prompted it. Format as:

```
Change: [brief description of change]
Justification: [reference to specific review finding or comment]
```

If no changes were made to a section, state: "No changes made - no actionable review findings requiring modification."

Remember: The goal is precisely as directed by review findings, preserving all architectural intent while making only the minimum necessary changes to address identified issues.