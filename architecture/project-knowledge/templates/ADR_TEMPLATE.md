# Architecture Decision Record Template

## ADR ID
{{Unique identifier, e.g., ADR-001}}

## Status
{{Accepted | Rejected | Superseded | Deprecated | Experimental | Draft}}

## Date
{{YYYY-MM-DD}}

## Authors
{{Author name(s)}}

## Reviewers
{{Reviewer name(s)}}

## Related Architecture Parts
{{List of related AI-OS Architecture Parts (e.g., Part 3: Memory Architecture)}}

## Context
{{Description of the circumstances that motivated this decision. Include relevant forces (business, technical, social, project management) that are in play.}}

## Problem Statement
{{Clear statement of the problem or opportunity that this ADR addresses.}}

## Decision
{{The chosen solution or course of action.}}

## Alternatives Considered
{{List of alternatives that were evaluated, with brief pros/cons for each.}}

### Alternative 1
- **Description:** ...
- **Pros:** ...
- **Cons:** ...

### Alternative 2
- **Description:** ...
- **Pros:** ...
- **Cons:** ...

## Decision Drivers
{{Factors that influenced the decision, weighted by importance (e.g., performance, security, maintainability, cost, schedule).}}

## Consequences
{{What becomes easier or more difficult as a result of this decision.}}

### Positive Consequences
- ...

### Negative Consequences
- ...

## Risks
{{Identified risks associated with this decision and their mitigation strategies.}}

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| ...  | ...        | ...    | ...        |

## Trade-offs
{{Explicit trade-offs made, showing what was gained and what was sacrificed.}}

| Trade-off | Gained | Sacrificed | Rationale |
|-----------|--------|------------|-----------|
| ...       | ...    | ...        | ...       |

## Validation
{{How the decision will be validated (e.g., prototypes, benchmarks, tests, pilot projects).}}

## Security Impact
{{Analysis of how this decision affects the security posture of AI-OS.}}

## Performance Impact
{{Analysis of performance implications (latency, throughput, resource usage).}}

## Compatibility
{{Impact on backward/forward compatibility with existing components, APIs, or external systems.}}

## Migration
{{Steps required to migrate existing systems to adopt this decision.}}

## Future Considerations
{{Potential future changes that could affect this decision.}}

## Related ADRs
{{List of related ADR IDs with brief descriptions.}}

- ADR-{{ID}}: {{Title}} - {{Relationship}}
- ADR-{{ID}}: {{Title}} - {{Relationship}}

## References
{{Links to external documents, standards, or other artifacts that informed this decision.}}

- [Reference 1](URL)
- [Reference 2](URL)

---

### Status Guidance

- **Accepted**: The decision has been approved and is part of the official architecture.
- **Rejected**: The decision was considered but not approved.
- **Superseded**: This ADR has been replaced by a newer ADR (reference the superseding ADR).
- **Deprecated**: The decision is no longer recommended for new work but may still exist in legacy code.
- **Experimental**: The decision is under trial in a limited scope; not yet ready for broad adoption.
- **Draft**: The decision is under active discussion and has not yet been reviewed or approved.

### Authoring Guidance

1. Use clear, concise language; avoid jargon unless defined.
2. Focus on the *why* as much as the *what*.
3. Include measurable criteria where possible (e.g., "must support 10k RPS").
4. Cite sources for claims (standards, benchmarks, prior art).
5. Keep the ADR self-contained but reference related documents when appropriate.
6. Update the ADR only via a new ADR that supersedes it; never modify an accepted ADR directly.

### Review Guidance

1. Reviewers should verify that the context and problem statement are well understood.
2. Ensure all viable alternatives have been considered and documented.
3. Check that decision drivers align with AI-OS principles and priorities.
4. Validate that consequences, risks, and trade-offs are realistic and complete.
5. Confirm that validation, security, performance, and compatibility analyses are adequate.
6. Ensure the ADR follows the template structure and uses consistent terminology.
7. Provide actionable feedback; approve only when the ADR is ready for inclusion.

### Publication Guidance

1. Once accepted, place the ADR in the `architecture/decisions/` directory with the filename format `ADR-{{ID}}-{{Title}}.md`.
2. Link the new ADR from the `README.md` in the decisions directory.
3. Notify relevant stakeholders (architecture team, component owners) via the agreed communication channel.
4. Update any affected architecture diagrams or documentation to reflect the decision.
5. Record the ADR in the architecture decision log (if maintained).