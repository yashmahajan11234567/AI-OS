#!/usr/bin/env python3
"""M12-T6 Fresh Score Reconstruction using P12-ADR-011 methodology."""

import sys
import io

# Force UTF-8 output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

categories = {
    "37.1 Architecture": {
        "criteria": ["Single authority kernel", "No duplicate kernel", "No external authority leakage", "All invariants pass"],
        "statuses": ["[OK]", "[OK]", "[OK]", "[OK]"],
    },
    "37.2 Execution": {
        "criteria": ["Real production execution", "Real adapters", "Controlled external workers"],
        "statuses": ["[PARTIAL]", "[OK]", "[OK]"],
    },
    "37.3 Councils": {
        "criteria": ["Multiple perspectives", "Synthesis", "Dissent preserved", "Independence", "FinalJudge independent"],
        "statuses": ["[OK]", "[OK]", "[OK]", "[OK]", "[OK]"],
    },
    "37.4 Verification": {
        "criteria": ["Independent verification", "Evidence-backed decisions", "No self-approval"],
        "statuses": ["[OK]", "[OK]", "[OK]"],
    },
    "37.5 Testing": {
        "criteria": ["Deterministic tests", "AI-driven tests", "User simulation", "Security tests", "Regression", "E2E", "Chaos/reliability"],
        "statuses": ["[OK]", "[OK]", "[OK]", "[OK]", "[OK]", "[PARTIAL]", "[OK]"],
    },
    "37.6 Learning": {
        "criteria": ["RCA", "Learning", "Simplification", "Replanning", "Regression protection", "Safe re-execution"],
        "statuses": ["[OK]", "[PARTIAL]", "[OK]", "[OK]", "[OK]", "[OK]"],
    },
    "37.7 Knowledge": {
        "criteria": ["Obsidian", "Graphify", "Claude-Mem", "Provenance", "Authority boundaries"],
        "statuses": ["[EXCL-NotWired]", "[PARTIAL]", "[EXCL-NotNeeded]", "[OK]", "[OK]"],
    },
    "37.8 Planning": {
        "criteria": ["Notion", "GSD", "Operational boundaries"],
        "statuses": ["[OK]", "[OK-Ref]", "[OK]"],
    },
    "37.9 Security": {
        "criteria": ["Sandboxing", "Secrets", "External trust", "Malicious content", "Least privilege"],
        "statuses": ["[OK]", "[PARTIAL]", "[OK]", "[OK]", "[OK]"],
    },
    "37.10 Infrastructure": {
        "criteria": ["Model access", "MCP", "ACP", "Workers", "Persistence", "Monitoring"],
        "statuses": ["[PARTIAL]", "[OK]", "[PARTIAL]", "[OK]", "[OK]", "[PARTIAL]"],
    },
    "37.11 Deployment": {
        "criteria": ["Reproducible deployment", "Configuration", "Secrets", "Health checks", "Rollback", "Recovery"],
        "statuses": ["[FAIL]", "[OK]", "[PARTIAL]", "[FAIL]", "[FAIL]", "[PARTIAL]"],
    },
}

# Using ASCII tags that map to the real statuses:
# [OK] = ✅, [PARTIAL] = ⚠️, [FAIL] = ❌, [EXCL-NotWired] = ❌ Not wired, [EXCL-NotNeeded] = ❌ Not needed, [OK-Ref] = ✅ Reference

EXCLUDED_TAGS = {"[EXCL-NotWired]", "[EXCL-NotNeeded]"}

def status_points(s):
    if s == "[OK]":
        return 1.0
    elif s == "[OK-Ref]":
        return 1.0
    elif s == "[PARTIAL]":
        return 0.5
    elif s == "[FAIL]":
        return 0.0
    elif s.startswith("[EXCL-"):
        return 0.0  # excluded
    else:
        raise ValueError(f"Unknown status: {s}")

total_scorable = 0
total_earned = 0.0
category_results = []

print("=" * 80)
print("M12-T6 FRESH SCORE RECONSTRUCTION")
print("=" * 80)

for cat_name, data in categories.items():
    criteria = data["criteria"]
    statuses = data["statuses"]
    scorable = 0
    excluded = []
    earned = 0.0
    detail_lines = []
    for i, (c, s) in enumerate(zip(criteria, statuses)):
        if s in EXCLUDED_TAGS:
            excluded.append(f"  #{i+1:2d}. {c}: {s} <- EXCLUDED")
            detail_lines.append(f"  #{i+1:2d}. {c}: {s} <- EXCLUDED")
        else:
            scorable += 1
            pts = status_points(s)
            earned += pts
            detail_lines.append(f"  #{i+1:2d}. {c}: {s} -> {pts:.1f} pts")
    cat_score = earned / scorable if scorable > 0 else 0.0
    print(f"\n{cat_name}")
    print(f"  Scorable: {scorable}  |  Earned: {earned:.1f}/{scorable:.0f}  |  Score: {cat_score:.4f}")
    for line in detail_lines:
        print(line)
    if excluded:
        print(f"  Excluded: {len(excluded)} criteria")
        for line in excluded:
            print(line)
    total_scorable += scorable
    total_earned += earned
    category_results.append((cat_name, scorable, earned, cat_score))

print("\n" + "=" * 80)
print("WEIGHTED CONTRIBUTIONS")
print("=" * 80)
raw_R = 0.0
for cat_name, scorable, earned, cat_score in category_results:
    weight = scorable / total_scorable
    contribution = cat_score * weight
    raw_R += contribution
    print(f"{cat_name}: weight={scorable}/{total_scorable}={weight:.5f}  |  cat_score={cat_score:.4f}  |  contribution={contribution:.5f} ({contribution*100:.2f} pts)")

print(f"\nTotal scorable S = {total_scorable}")
print(f"Total earned points = {total_earned:.1f}")
print(f"Raw R = sum(contributions) = {raw_R:.5f}")
print(f"Final score = round(R x 100) = round({raw_R*100:.2f}) = {round(raw_R * 100)}/100")

print("\n" + "=" * 80)
print("EXCLUDED CRITERIA")
print("=" * 80)
for cat_name, data in categories.items():
    for i, (c, s) in enumerate(zip(data["criteria"], data["statuses"])):
        if s in EXCLUDED_TAGS:
            print(f"  {cat_name} #{i+1}: {c} = {s} -> excluded from S and score")

print("\n" + "=" * 80)
print("ACCEPTANCE ANALYSIS")
print("=" * 80)
score = round(raw_R * 100)
has_warnings = any(s == "[PARTIAL]" for d in categories.values() for s in d["statuses"])
has_failures = any(s == "[FAIL]" for d in categories.values() for s in d["statuses"])
cond_a = score >= 95
cond_b = not has_warnings and not has_failures
cond_c = cond_a and cond_b
print(f"\nA. Score >= 95: {score}/100 >= 95 -> {'PASS' if cond_a else 'FAIL'}")
print(f"B. All criteria individually [OK]: warnings={has_warnings}, failures={has_failures} -> {'PASS' if cond_b else 'FAIL'}")
print(f"C. Both A AND B: {'PASS' if cond_c else 'FAIL'}")

print("\n" + "=" * 80)
print("COMPLETE STATUS INVENTORY (#1-53)")
print("=" * 80)
idx = 1
for cat_name, data in categories.items():
    print(f"\n{cat_name}")
    for c, s in zip(data["criteria"], data["statuses"]):
        tag = ""
        if s in EXCLUDED_TAGS:
            tag = " [EXCLUDED]"
        elif s == "[PARTIAL]":
            tag = " [PARTIAL]"
        elif s == "[FAIL]":
            tag = " [FAIL]"
        elif s == "[OK-Ref]":
            tag = " [OK-Reference]"
        print(f"  #{idx:2d}. {c}: {s}{tag}")
        idx += 1

print("\n" + "=" * 80)
print("M12-T6 ACCEPTANCE VERDICT")
print("=" * 80)
print(f"CURRENT SCORE: {score}/100")
print(f"THRESHOLD (score >= 95): {'PASS' if cond_a else 'FAIL'}")
print(f"ALL-CRITERIA CONDITION (all [OK]): {'PASS' if cond_b else 'FAIL'}")
m12_pass = cond_a and cond_b
print(f"M12-T6 ACCEPTANCE: {'PASS' if m12_pass else 'NOT PASS'}")

# Breakdown of what blocks acceptance
if not m12_pass:
    print("\n" + "=" * 80)
    print("BLOCKING ITEMS")
    print("=" * 80)
    if not cond_a:
        print(f"  SCORE THRESHOLD NOT MET: {score}/100 < 95/100")
    if not cond_b:
        print("  NON-OK CRITERIA:")
        idx = 1
        for cat_name, data in categories.items():
            for c, s in zip(data["criteria"], data["statuses"]):
                if s == "[PARTIAL]":
                    print(f"    #{idx:2d}. {cat_name} - {c}: [PARTIAL]")
                elif s == "[FAIL]":
                    print(f"    #{idx:2d}. {cat_name} - {c}: [FAIL]")
                idx += 1
