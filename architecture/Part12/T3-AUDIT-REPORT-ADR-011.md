# Terminal 3 Audit Report: P12-ADR-011 M12-T6 Scoring Methodology

**Auditor**: Terminal 3 — Independent QA  
**Date**: 2026-09-11  
**Scope**: Formula remediation only; read-only audit, no changes made  
**Verdict**: 🔴 NOT DONE — ARITHMETIC DEFECT IN WORKED EXAMPLE

---

## A. Actual Repository State

- **Target file exists**: `architecture/Part12/P12-ADR-011-m12-t6-scoring-methodology.md` ✓
- **Git working tree**: Clean — zero tracked changes, zero staged changes, zero unstaged changes
- **git status**: No tracked changes to any file; the ADR appears as untracked (`??`)
- **git log**: No commits reference this ADR — it was added outside git history
- **Only target changed**: Since there are no tracked file changes at all, no other files were modified

**Conclusion**: The ADR is present in the working tree as a new untracked file. No existing files were modified.

---

## B. Formula Verification

### Required formula (ADR §"Scoring Formula", line 92)

```
Category Weight = (Number of scorable criteria in category) / (Total scorable criteria across all categories)
Category Score  = (Points earned in category) / (Total points available in category)
Contribution    = Category Score × Category Weight
Raw Score       = Σ Contributions
Final Score     = round(Raw Score) [0-100 scale]
```

**Formula text is correct.** Lines 92-97 define the formula precisely and without error.

**Scorable criteria definition**: Lines 95-96 explicitly define which statuses are scorable (✅, ⚠️, ❌ = 1.0, 0.5, 0.0) and which are excluded (❌ Not wired, ❌ Not needed = excluded from both earned points and denominators).

**Excluded criteria treatment**: Lines 95-96 correctly specify excluded criteria are removed from both:
1. Points earned (counted as 0.0, excluded)
2. Category denominator (excludes from `Total points available in category`)
3. Global denominator (excludes from `Total scorable criteria across all categories`)
4. Category weight (implicitly excluded by using scorable count, not raw count)

**Rounding**: Line 97: "Final score is rounded to nearest whole number (0-100 scale)" — explicit and unambiguous.

**Terminal 3 procedure** (lines 117-133): Correctly implements the same formula with explicit step-by-step instructions. No stale formula remains in the procedure text.

---

## C. Edge-Case Verification

| Case | Total Scorable | Weight Sum | Raw Score | Rounded | Verdict |
|------|---------------|------------|-----------|---------|---------|
| A — All 1.0 | 47 | 47/47 = 1.0 | 100.0 | 100 | ✅ PASS |
| D — One ❌ Not needed | 46 | 46/46 = 1.0 | 100.0 | 100 | ✅ PASS |
| E — One ❌ Not wired | 46 | 46/46 = 1.0 | 100.0 | 100 | ✅ PASS |
| F — Multiple excluded | 42 | 42/42 = 1.0 | 100.0 | 100 | ✅ PASS |

**Zero-scorable-criteria guard**: Not explicitly defined. Division by zero would occur if `total_scorable = 0`. In practice impossible (11 categories, each must have at least one scorable criterion for scoring to be meaningful), but this edge case is not guarded in the ADR. **Minor documentation gap, not a blocking issue.**

---

## D. Worked-Example Independent Calculation

### Correct formula applied to ADR's stated category data

| Category | Scorable Count | Points Earned | Correct Weight | Category Score | Correct Contribution |
|----------|---------------|---------------|----------------|----------------|----------------------|
| 37.1 Architecture | 4 | 4.0 | 4/47 = 0.085106 | 1.0000 | **8.51** |
| 37.2 Execution | 3 | 3.0 | 3/47 = 0.063830 | 1.0000 | **6.38** |
| 37.3 Councils | 5 | 5.0 | 5/47 = 0.106383 | 1.0000 | **10.64** |
| 37.4 Verification | 3 | 3.0 | 3/47 = 0.063830 | 1.0000 | **6.38** |
| 37.5 Testing | 7 | 5.0 | 7/47 = 0.148936 | 0.7143 | **10.64** |
| 37.6 Learning | 6 | 3.0 | 6/47 = 0.127660 | 0.5000 | **6.38** |
| 37.7 Knowledge | 4 | 1.5 | 4/47 = 0.085106 | 0.3750 | **3.19** |
| 37.8 Planning | 3 | 1.5 | 3/47 = 0.063830 | 0.5000 | **3.19** |
| 37.9 Security | 4 | 2.5 | 4/47 = 0.085106 | 0.6250 | **5.32** |
| 37.10 Infrastructure | 4 | 4.0 | 4/47 = 0.085106 | 1.0000 | **8.51** |
| 37.11 Deployment | 4 | 3.0 | 4/47 = 0.085106 | 0.7500 | **6.38** |

**Correct formula total**: 75.53 → **76/100** (rounded)

**Weight sum verification**: Σ(scorable_count) / 47 = 47/47 = 1.000000 ✅

### ADR text claimed total

Summing the ADR's stated individual contributions:

8.51 + 6.38 + 10.64 + 6.38 + 10.64 + 6.38 + 2.39 + 3.19 + 5.32 + 10.64 + 8.51 = **78.98 → 79/100**

---

## E. 78.98 vs 75.53 Reconciliation

**The mathematically correct result from the ADR's stated data is 75.53 → 76/100, NOT 78.98 → 79/100.**

There is a **3.45-point discrepancy** between the correct formula result and the ADR's claimed total.

### Root cause: Two category weight errors in the worked example

| Category | ADR Uses | Should Use | Error | Contribution Delta |
|----------|----------|------------|-------|-------------------|
| **37.7 Knowledge** | 3/47 | **4/47** | Weight uses count 3 instead of scorable count 4 | +0.80 |
| **37.10 Infrastructure** | 5/47 | **4/47** | Weight uses count 5 instead of scorable count 4 | -2.13 |
| **Net effect** | | | | **-1.33** |

The ADR worked example has a **mixed-weighting scheme**:
- It correctly uses scorable count for most categories (4/47, 3/47, 5/47, 6/47, 4/47)
- It incorrectly uses the original (non-exclusion-adjusted) count for Knowledge (3 instead of 4) and Infrastructure (5 instead of 4)

### Why 78.98 is not valid

When the ADR's stated contributions are summed, they total 78.98. But those contributions do not ALL follow the stated formula. Specifically:

- **37.7 Knowledge**: Contribution = 2.39 uses weight 3/47. Correct formula weight = 4/47. The 2.39 figure violates the stated formula.
- **37.10 Infrastructure**: Contribution = 10.64 uses weight 5/47. Correct formula weight = 4/47. The 10.64 figure violates the stated formula.

When the correct formula is applied uniformly to all 11 categories: **75.53 → 76/100**.

### Why Terminal 1's 78.89 does not match either

Terminal 1 reported 78.89 → 79/100. This does not match the ADR's 78.98 and does not match the correct formula's 75.53. Terminal 1's figure cannot be reproduced from the ADR text by any combination of the two weighting errors above. The origin of 78.89 is unexplained by the current ADR contents.

---

## F. Exclusion Semantics

### ADR treatment of statuses

The ADR defines five status classes in line 95:
- ✅ = 1.0 (counted)
- ⚠️ Partial = 0.5 (counted)
- ❌ = 0.0 (counted)
- ❌ Not wired = 0.0 **excluded**
- ❌ Not needed = 0.0 **excluded**

### Consistent exclusion from all four dimensions

| Dimension | ✅ | ⚠️ | ❌ | ❌ Not wired | ❌ Not needed |
|-----------|----|----|----|-------|-------|
| Points earned | 1.0 | 0.5 | 0.0 | excluded | excluded |
| Category denominator | counted | counted | counted | excluded | excluded |
| Global denominator | counted | counted | counted | excluded | excluded |
| Category weight | implicit | implicit | implicit | excluded | excluded |

**Verified**: The ADR correctly treats "Not wired" and "Not needed" as excluded from all four dimensions (earned points, category denominator, global denominator, category weight). The worked example follows this correctly in category descriptions (e.g., 37.7 has 5 criteria total, 4 scorable; 37.10 has 6 criteria total, 4 scorable; 37.11 has 6 criteria total, 4 scorable).

### Status origin

The status labels (✅, ⚠️, ❌, ❌ Not wired, ❌ Not needed) are ADR interpretations of the target annotation symbols, not formal Section 37 acceptance criteria. The ADR does not create new acceptance criteria or modify Section 37. This is consistent with the ADR's scope as a governance/documentation decision.

---

## G. Terminal 3 Procedure Verification

**Lines 117-133 contain the Terminal 3 scoring procedure.** Verification:

| Step | Content | Correct? |
|------|---------|----------|
| 1 | Review current evidence | ✅ |
| 2 | Determine status for each criterion | ✅ |
| 3 | Calculate points (✅=1.0, ⚠️=0.5, ❌=0.0, excluded=0.0) | ✅ |
| 4 | Sum points within each category | ✅ |
| 5 | Category score = category points / scorable count | ✅ |
| 6 | Category weight = scorable count / total scorable | ✅ |
| 7 | Contribution = score × weight | ✅ |
| 8 | Raw score = Σ contributions | ✅ |
| 9 | Round to nearest whole number | ✅ |
| 10 | Compare to ≥95/100 threshold | ✅ |

The procedure correctly implements the required globally-normalized formula. No stale `/53` reference remains in the procedure.

---

## H. Scope Verification

**Only the formula remediation scope was performed on this ADR.** Verification:

| Target | Changed? |
|--------|----------|
| `architecture/Part12/P12-ADR-011-m12-t6-scoring-methodology.md` | ✅ Present (untracked) |
| `source/` | ❌ No changes |
| `tests/` | ❌ No changes |
| `config/` | ❌ No changes |
| `runtime/` | ❌ No changes |
| `deployment/` | ❌ No changes |
| `dashboard/` | ❌ No changes |
| `master plan` | ❌ No changes |
| `T6-FINAL-ACCEPTANCE.md` | ❌ No changes |
| Other ADRs | ❌ No changes |

**No scope creep detected.** The ADR does not modify any other file or create new acceptance criteria.

---

## I. Final Verdict

### 🔴 NOT DONE — ARITHMETIC DEFECT IN WORKED EXAMPLE

The formula remediation is **incomplete** because the worked example contains a mathematical error that causes it to produce 78.98 instead of the correct 75.53.

**Formula text**: Correct.  
**Exclusion semantics**: Correct.  
**Terminal 3 procedure**: Correct.  
**Worked example**: Contains two category weight errors (37.7 Knowledge, 37.10 Infrastructure) that produce a total of 78.98 rather than the mathematically correct 75.53.

The worked example is the most critical part of a scoring methodology ADR — it is what Terminal 3 and future readers use to validate their own calculations. An incorrect worked example undermines the entire methodology's reproducibility guarantee.

---

## J. Exactly One Next Action

**Terminal 2 must correct the worked example in `P12-ADR-011-m12-t6-scoring-methodology.md`** by fixing two category weight entries:

1. **Line 107 (37.7 Knowledge)**: Change weight from `3/47` to `4/47` and contribution from `2.39` to `3.19`
2. **Line 110 (37.10 Infrastructure)**: Change weight from `5/47` to `4/47` and contribution from `10.64` to `8.51`

After correction, the illustrative score should read:

> **Illustrative Score:** 8.51 + 6.38 + 10.64 + 6.38 + 10.64 + 6.38 + 3.19 + 3.19 + 5.32 + 8.51 + 6.38 = **75.53 → 76/100**

No formula remediation action remains beyond this correction. Proceed to the next independently approved M12-T6 governance blocker after Terminal 2 applies this fix and Terminal 3 re-verifies.
