# -*- coding: utf-8 -*-
"""Independent mathematical reproduction of M12-T6 scoring methodology."""

import math

# Formula:
#   Category Weight = scorable_count_cat / total_scorable_count
#   Category Score  = points_earned / scorable_count_cat
#   Contribution     = category_score * category_weight
#   Raw Total        = sum(contributions)
#   Final            = round(raw_total)  [contributions already scaled x100]

# ===== CASE A: All scorable criteria = 1.0 =====
print('=== Case A: All scorable = 1.0 ===')
case_a_contributions = [4/47*1.0*100, 3/47*1.0*100, 5/47*1.0*100, 3/47*1.0*100,
                        7/47*1.0*100, 6/47*1.0*100, 4/47*1.0*100, 3/47*1.0*100,
                        4/47*1.0*100, 4/47*1.0*100, 4/47*1.0*100]
case_a_total = sum(case_a_contributions)
print(f'  Raw: {case_a_total:.4f}, Rounded: {round(case_a_total)}/100')
print(f'  Weight sum: {sum([4,3,5,3,7,6,4,3,4,4,4])/47:.6f} (should be 1.0)')

# ===== CASE D: One excluded, all remaining scorable = 1.0 =====
print()
print('=== Case D: One excluded, rest 1.0 ===')
d_scorable_total = 46
d_weights_sum = 46/46  # = 1.0
print(f'  Total scorable: {d_scorable_total}')
print(f'  Weight sum: {d_weights_sum:.6f} (should be 1.0)')
print(f'  Raw: {d_weights_sum * 100:.4f}, Rounded: {round(d_weights_sum * 100)}/100')

# ===== CASE E: One excluded, all remaining scorable = 1.0 =====
print()
print('=== Case E: One excluded, rest 1.0 ===')
e_scorable_total = 46
e_weights_sum = 46/46
print(f'  Total scorable: {e_scorable_total}')
print(f'  Weight sum: {e_weights_sum:.6f} (should be 1.0)')
print(f'  Raw: {e_weights_sum * 100:.4f}, Rounded: {round(e_weights_sum * 100)}/100')

# ===== CASE F: Multiple excluded, rest 1.0 =====
print()
print('=== Case F: Multiple excluded, rest 1.0 ===')
f_scorable_total = 42
f_weights_sum = 42/42
print(f'  Total scorable: {f_scorable_total}')
print(f'  Weight sum: {f_weights_sum:.6f} (should be 1.0)')
print(f'  Raw: {f_weights_sum * 100:.4f}, Rounded: {round(f_weights_sum * 100)}/100')

# ===== ZERO SCORABLE CRITERIA =====
print()
print('=== Zero scorable criteria edge case ===')
print('  If total_scorable = 0, category_weight = scorable_count/0 -> DivisionByZero')
print('  ADR does not define explicit guard; in practice impossible with 11 categories')

# ===== WORKED EXAMPLE FROM ADR =====
print()
print('=== Worked Example Independent Reproduction ===')
print()

categories = {
    '37.1 Architecture':      {'earned': 4.0, 'scorable': 4},
    '37.2 Execution':         {'earned': 3.0, 'scorable': 3},
    '37.3 Councils':          {'earned': 5.0, 'scorable': 5},
    '37.4 Verification':      {'earned': 3.0, 'scorable': 3},
    '37.5 Testing':           {'earned': 5.0, 'scorable': 7},
    '37.6 Learning':          {'earned': 3.0, 'scorable': 6},
    '37.7 Knowledge':         {'earned': 1.5, 'scorable': 4},
    '37.8 Planning':          {'earned': 1.5, 'scorable': 3},
    '37.9 Security':          {'earned': 2.5, 'scorable': 4},
    '37.10 Infrastructure':   {'earned': 4.0, 'scorable': 4},
    '37.11 Deployment':       {'earned': 3.0, 'scorable': 4},
}

total_scorable = sum(v['scorable'] for v in categories.values())
print(f'Total scorable criteria: {total_scorable}')
print(f'Note: ADR text says 47 total scorable, categories sum to {total_scorable}')
print()

grand_total = 0.0
for name, data in categories.items():
    sc = data['scorable']
    pts = data['earned']
    weight = sc / total_scorable
    score = pts / sc
    contrib = score * weight * 100
    grand_total += contrib
    print(f'  {name}: earned={pts}, scorable={sc}, weight={sc}/{total_scorable}={weight:.6f}, score={pts}/{sc}={score:.6f}, contrib={contrib:.4f}')

print()
print(f'  RAW TOTAL: {grand_total:.6f}')
print(f'  ROUNDED:   {round(grand_total)}/100')
print(f'  Weight sum: {sum(v["scorable"] for v in categories.values())/total_scorable:.6f} (must be 1.0)')

# ===== 78.98 vs 78.89 reconciliation =====
print()
print('=== 78.98 vs 78.89 reconciliation ===')
print(f'  Correct result (using formula as stated): {grand_total:.2f} -> {round(grand_total)}/100')
print(f'  ADR text claims: 78.98 -> 79/100')
print(f'  Terminal 1 claimed: 78.89 -> 79/100')
print()

# Verify the exact ADR text line-by-line
print('=== ADR text line-by-line verification ===')
lines = [
    ('37.1 Architecture',    4, 4.0, 4, 47, 1.0),
    ('37.2 Execution',       3, 3.0, 3, 47, 1.0),
    ('37.3 Councils',        5, 5.0, 5, 47, 1.0),
    ('37.4 Verification',    3, 3.0, 3, 47, 1.0),
    ('37.5 Testing',         7, 5.0, 7, 47, None),
    ('37.6 Learning',        6, 3.0, 6, 47, None),
    ('37.7 Knowledge',       4, 1.5, 3, 47, None),
    ('37.8 Planning',        3, 1.5, 3, 47, None),
    ('37.9 Security',        4, 2.5, 4, 47, None),
    ('37.10 Infrastructure', 4, 4.0, 5, 47, None),
    ('37.11 Deployment',     4, 3.0, 4, 47, None),
]

manual_total = 0.0
for name, sc, pts, wn, wd, score in lines:
    if score is None:
        score = pts / sc
    weight = wn / wd
    contrib = score * weight * 100
    manual_total += contrib
    print(f'  {name}: {score:.4f} * {wn}/{wd} * 100 = {contrib:.2f}')

print(f'  MANUAL TOTAL (using ADR text weights): {manual_total:.2f}')
print(f'  ROUNDED: {round(manual_total)}')

# Check 37.7 and 37.10 weight issues
print()
print('=== Key discrepancies ===')
k7_adr = (1.5/4) * (3/47) * 100
k7_correct = (1.5/4) * (4/47) * 100
i10_adr = (4.0/4) * (5/47) * 100
i10_correct = (4.0/4) * (4/47) * 100
print(f'  37.7 Knowledge: ADR uses 3/47 = {k7_adr:.4f}, correct 4/47 = {k7_correct:.4f}, diff = {k7_correct - k7_adr:.4f}')
print(f'  37.10 Infrastructure: ADR uses 5/47 = {i10_adr:.4f}, correct 4/47 = {i10_correct:.4f}, diff = {i10_correct - i10_adr:.4f}')
print(f'  Net effect of both corrections: {(k7_correct - k7_adr) + (i10_correct - i10_adr):.4f}')
print(f'  manual_total + corrections = {manual_total + (k7_correct - k7_adr) + (i10_correct - i10_adr):.4f}')
