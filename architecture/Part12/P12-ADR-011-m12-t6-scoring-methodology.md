# P12-ADR-011: M12-T6 Scoring Methodology

## M12-T6 Scoring Methodology for Final Acceptance

| Field | Value |
|-------|-------|
| **ADR ID** | P12-ADR-011 |
| **Status** | Proposed |
| **Date** | 2026-09-11 |
| **Authors** | AI Architecture Team |
| **Reviewers** | — |
| **Related Parts** | Part 12 (Documentation & Closure), Part 15 (Extensions) |
| **Related Core ADRs** | [[ADR-014]] – Architecture Decision Record Process |
| **Related Part 12 ADRs** | [[P12-ADR-003]] (Council-Based Decision Architecture), [[P12-ADR-010]] (Runtime Contracts for Agent Interoperability) |

### Context
The M12-T6 Final Acceptance milestone requires an authoritative scoring methodology to convert the Section 37 acceptance matrix into a 100-point score for Independent QA: GO determination. The master plan specifies that M12-T6 requires "All criteria met; score ≥ 95/100" and "Independent QA: GO (score ≥95/100)", but no scoring methodology existed in the repository to calculate this score.

### Problem
How should the 53 discrete acceptance criteria in Section 37 (across 11 categories) be converted to a 100-point scoring system for M12-T6 Final Acceptance, ensuring mathematical reproducibility, explicit status treatment, deferred-item handling, Part 11 treatment, test/runtime evidence treatment, and addressing the stale DoD threshold, while preserving the existing M12 structure and criteria?

### Alternatives Considered

**Alternative 1: Equal Weighting of All 53 Criteria**
- **Pros**: Simple, transparent, mathematically reproducible, no arbitrary weighting
- **Cons**: Does not account for relative importance of different categories

**Alternative 2: Category-Based Weighting (Selected)**
- **Pros**: Reflects architectural priorities, maintains category structure from master plan
- **Cons**: Requires explicit governance rationale for weights

**Alternative 3: Criteria-Based Weighting with Arbitrary Values**
- **Pros**: Could theoretically optimize scoring
- **Cons**: Violates constraint against inventing arbitrary weights presented as authoritative

**Alternative 4: Binary Pass/Fail per Category**
- **Pros**: Simple category-level assessment
- **Cons**: Loses granularity of 53 criteria, violates requirement to use existing criteria as scoring units

### Decision
The M12-T6 scoring methodology uses **equal weighting within each of the 11 categories**, with **category weights proportional to the number of criteria in each category**. This approach:
1. Uses exactly the existing 53 criteria as scoring units (no new criteria invented)
2. Preserves the existing 11-category structure from Section 37
3. Provides mathematical reproducibility through transparent weighting
4. Establishes the methodology as a NEW M12-T6 governance decision (not claiming pre-existing authority)
5. Maintains consistency with the master plan's categorical organization

### Decision Drivers

| Driver | Importance |
|--------|------------|
| Preserve existing M12 structure (11 categories) | Critical |
| Use exact existing 53 criteria as scoring units | Critical |
| Mathematical reproducibility and transparency | Critical |
| Establish as new governance decision (not pre-existing authority) | High |
| Consistency with master plan categorical organization | High |
| Explicit treatment of all status classes | Critical |
| Clear deferred-item treatment | High |
| Explicit Part 11 treatment | Critical |
| Test/runtime evidence treatment | High |
| Stale DoD threshold treatment | Medium |

### Trade-offs

| Trade-off | Gained | Sacrificed | Rationale |
|-----------|--------|------------|-----------|
| Equal weighting within categories | Simplicity, reproducibility, no arbitrary criteria weights | Potential misrepresentation of criteria importance within categories | Criteria within categories are substantively related; equal weighting maintains category integrity |
| Category weights proportional to criteria count | Mathematical reproducibility, preserves category structure | Equal category weighting regardless of criteria count | Criteria count reflects relative elaboration in master plan; avoids arbitrary category weights |
| Explicit status treatment | Clarity, eliminates Terminal 3 interpretation | None required | Addresses governance gap directly |
| Deferred-item treatment | Clear disposition of milestone-scoped functionality | None required | Prevents silent assumptions about deferred items |
| Part 11 treatment | Explicit handling of architectural defects | None required | Preserves existing documented status per T5 scope boundary |
| Test/runtime treatment | Clear handling of evidence limitations | None required | Enables consistent Terminal 3 evaluation |
| Stale DoD treatment | Distinguishes historical vs current evidence | None required | Addresses documented discrepancy honestly |

### Consequences

**Positive Consequences:**
- Provides mathematically reproducible scoring methodology for M12-T6
- Uses exactly the existing 53 criteria without modification
- Preserves the 11-category structure from Section 37
- Establishes explicit governance decision for scoring (fills documentation gap)
- Enables Terminal 3 to independently reproduce exact score
- Addresses all mandatory constraints from T1 audit
- Makes no new implementation requirements
- Maintains source fidelity to existing documentation

**Scoring Formula:**
The M12-T6 score is calculated as follows:
```
M12-T6 Score = Σ(Category Weight × Category Score)
Where:
- Category Weight = (Number of scorable criteria in category) / (Total scorable criteria across all categories)
- Category Score = (Points earned in category) / (Total points available in category)
- Points earned in category = Σ(Status Points for each criterion in category)
- Status Points: ✅ = 1.0, ⚠️ Partial = 0.5, ❌ = 0.0, ❌ Not wired = 0.0, ❌ Not needed = 0.0 (excluded from calculation)
- Total points available in category = Number of scorable criteria in category (excludes ❌ Not needed)
- Final score is rounded to nearest whole number (0-100 scale)

**Worked Example Calculation:**
Based on current evidence in T6-FINAL-ACCEPTANCE.md:
- 37.1 Architecture: 4 criteria, all ✅ → 4/4 = 1.000 → Weight: 4/51 → Contribution: (4/51)×1.000×100 = 7.84
- 37.2 Execution: 3 criteria: ⚠️, ✅, ✅ → (0×1.0 + 1×0.5 + 1×1.0)/3 = 2.0/3 = 0.667 → Weight: 3/51 → Contribution: (3/51)×0.667×100 = 3.92
- 37.3 Councils: 5 criteria, all ✅ → 5/5 = 1.000 → Weight: 5/51 → Contribution: (5/51)×1.000×100 = 9.80
- 37.4 Verification: 3 criteria, all ✅ → 3/3 = 1.000 → Weight: 3/51 → Contribution: (3/51)×1.000×100 = 5.88
- 37.5 Testing: 7 criteria: 4✅, 2⚠️, 1❌ → (4×1.0 + 2×0.5 + 1×0)/7 = 5.0/7 = 0.714 → Weight: 7/51 → Contribution: (7/51)×0.714×100 = 9.80
- 37.6 Learning: 6 criteria: 2✅, 2⚠️, 2❌ → (2×1.0 + 2×0.5 + 2×0)/6 = 3.0/6 = 0.500 → Weight: 6/51 → Contribution: (6/51)×0.500×100 = 5.88
- 37.7 Knowledge: 5 criteria: 1✅, 1⚠️, 1❌, 1❌ Not wired, 1❌ Not needed → (1×1.0 + 1×0.5 + 1×0 + 0 + 0)/3 = 1.5/3 = 0.500 → Weight: 3/51 → Contribution: (3/51)×0.500×100 = 2.94
- 37.8 Planning: 3 criteria: 1✅, 1⚠️, 1❌ → (1×1.0 + 1×0.5 + 1×0)/3 = 1.5/3 = 0.500 → Weight: 3/51 → Contribution: (3/51)×0.500×100 = 3.92
- 37.9 Security: 5 criteria: 3✅, 1⚠️, 1❌ → (3×1.0 + 1×0.5 + 1×0)/5 = 3.5/5 = 0.700 → Weight: 5/51 → Contribution: (5/51)×0.700×100 = 6.86
- 37.10 Infrastructure: 6 criteria: 2✅, 3⚠️, 1❌ → (2×1.0 + 3×0.5 + 1×0)/6 = 3.5/6 = 0.583 → Weight: 6/51 → Contribution: (6/51)×0.583×100 = 6.86
- 37.11 Deployment: 6 criteria: 1✅, 1⚠️, 1❌, 3❌ → (1×1.0 + 1×0.5 + 1×0 + 3×0)/6 = 1.5/6 = 0.250 → Weight: 6/51 → Contribution: (6/51)×0.250×100 = 2.94

**Illustrative Score:** 7.84 + 3.92 + 9.80 + 5.88 + 9.80 + 5.88 + 2.94 + 3.92 + 6.86 + 6.86 + 2.94 = 66.74 → 67/100

**Note:** This worked example is illustrative only. Its per-criterion statuses are illustrative and do not represent the current Section 37 evidence or the final M12-T6 acceptance score. Terminal 3 must calculate the actual acceptance score from current evidence.

**Weight verification:**
(4+3+5+3+7+6+3+3+5+6+6) / 51 = 51/51 = 1.0000

### M12-T6 Terminal 3 Scoring Procedure
Terminal 3 shall apply the following procedure to determine the M12-T6 Final Acceptance score:
1. Review the current evidence in `architecture/Part15/M12/T6-FINAL-ACCEPTANCE.md` and related milestone completion documents
2. For each of the 53 criteria in Section 37, determine the status based on evidence:
   - ✅ (Complete): Criterion fully satisfied per master plan requirements
   - ⚠️ (Partial): Criterion partially satisfied or has known limitations that do not block acceptance
   - ❌ (Not met): Criterion not satisfied and blocks acceptance
   - ❌ Not wired: Criterion requires external system integration that is not yet connected (excluded from calculation)
   - ❌ Not needed: Criterion is not applicable to current scope (excluded from calculation)
3. Calculate points for each criterion: ✅ = 1.0, ⚠️ Partial = 0.5, ❌ = 0.0, ❌ Not wired = 0.0 (excluded), ❌ Not needed = 0.0 (excluded)
4. Sum points within each of the 11 categories to get category points earned
5. Calculate category score = (category points earned) / (number of scorable criteria in category)
6. Calculate category weight = (scorable criteria in category) / (total scorable criteria across all categories)
7. Calculate weighted contribution = category score × category weight
8. Sum all weighted contributions to get raw score
9. Round raw score to nearest whole number to get final M12-T6 score (0-100 scale)
10. Compare final score to ≥95/100 threshold for Independent QA: GO determination

**Negative Consequences:**
- Equal weighting within categories may not reflect subtle criteria importance differences
- Category weights proportional to criteria count may not reflect architectural priority differences
- Requires Terminal 3 to apply the methodology rather than providing pre-calculated score
- Does not resolve underlying implementation gaps (intentionally preserves governance boundary)

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Misinterpretation as pre-existing authority | Low | High | Explicitly states methodology is NEW governance decision |
| Mathematical errors in reproduction | Low | Medium | Clear formula and worked example provided |
| Terminal 3 disagreement with weighting approach | Medium | Low | Methodology established through governance process |
| Confusion with M7 100-point rubric | Low | Medium | Explicit prohibition against reusing M7 rubric |
| Perceived as avoiding implementation responsibility | Low | Low | Clearly scoped as governance/documentation only |

### Validation
- Mathematical verification of 100-point conversion formula
- Status treatment verification for all five status classes (✅, ⚠️, ❌, ❌ Not wired, ❌ Not needed)
- Deferred-item treatment verification for M10 rollback and similar items
- Part 11 treatment verification against T5-CLOSURE.md scope boundary
- Test/runtime evidence treatment verification against actual test suite state
- Stale DoD threshold treatment verification against master plan documentation
- Governance ratification verification through actual ADR creation in repository
- Traceability verification linking to M12-T6 contract, Section 37, and all required elements

### Security Impact
- No security impact – governance/documentation decision only
- Does not modify any runtime/security components
- Preserves all existing security boundaries and authority models

### Performance Impact
- No performance impact – governance/documentation decision only
- Does not affect any runtime execution paths
- Purely affects scoring calculation for acceptance determination

### Compatibility
- Fully compatible with all existing M12 structure and criteria
- Fully compatible with Section 37 acceptance matrix
- Fully compatible with master plan milestone structure
- Fully compatible with existing ADR process (creates new ADR following ADR-014)
- Fully compatible with T5 scope boundary regarding Part 11
- Does not violate any frozen components or principles

### Migration
- No migration required – establishes scoring methodology for future M12-T6 evaluations
- Future changes to scoring methodology require new ADR superseding this one
- Methodology applies to all M12-T6 evaluations from acceptance date forward

### Future Considerations
- Potential refinement based on Terminal 3 practical application experience
- Possible category weight adjustment if future master plan revisions change criteria distribution
- Potential extension to other milestones if similar scoring gaps identified

### Related ADRs
- [[ADR-014]] — Architecture Decision Record Process (core: establishes ADR governance)
- [[P12-ADR-003]] — Council-Based Decision Architecture (related: governance framework for decisions)
- [[P12-ADR-010]] — Runtime Contracts for Agent Interoperability (related: defines collaboration boundaries)

### References
- AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md Section 30 (M12-T6 contract)
- AI-OS_FINAL_MASTER_IMPLEMENTATION_PLAN.md Section 37 (Acceptance criteria matrix)
- architecture/Part15/M12/T6-FINAL-ACCEPTANCE.md (T1 audit and gap analysis)
- architecture/Part15/M12/M10-GOVERNANCE-RECONCILIATION.md (M10 governance documentation)
- architecture/Part15/M11/TRUST_BOUNDARY_REGISTRY.md (M11 security verification)
- architecture/Part15/M11/SECRETS_AUDIT_REPORT.md (M11 secrets audit)
- architecture/Part15/M11/SUPPLY_CHAIN_SCAN_REPORT.md (M11 supply chain scan)
- architecture/Part15/M11/NETWORK_SECURITY_REPORT.md (M11 network security)
- architecture/Part15/M11/M7_IMPLEMENTATION_CONTRACT.md (M7 frozen contract)
- T5-CLOSURE.md (T5 scope boundary preservation)
- M12_RELEASE_NOTES_COMPLETE.md (M12 release documentation)

---