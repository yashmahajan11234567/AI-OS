# G. 95-Point Optimization Analysis

## Current Score: 79/100
## Target Score: 95/100
## Points Needed: 16 points

## Upgrade Impact Analysis

### Most Efficient Single Upgrades (❌ → ✅, gain 1.0 points in category):
1. **#26 Chaos/reliability** (37.5 Testing): +13.73 points → New score: 92.74 → 93/100
2. **#52 Reproducible deployment** (37.11 Deployment): +11.76 points → New score: 90.76 → 91/100  
3. **#55 Health checks** (37.11 Deployment): +11.76 points → New score: 90.76 → 91/100
4. **#56 Rollback** (37.11 Deployment): +11.76 points → New score: 90.76 → 91/100
5. **#49 Notion** (37.8 Planning): +5.88 points → New score: 84.88 → 85/100

### Most Efficient Partial Upgrades (⚠️ → ✅, gain 0.5 points in category):
1. **#9 Security tests** (37.5 Testing): +6.87 points → New score: 85.88 → 86/100
2. **#22 E2E** (37.5 Testing): +6.87 points → New score: 85.88 → 86/100
3. **#24 Learning** (37.6 Learning): +5.88 points → New score: 84.88 → 85/100
4. **#42 Model access** (37.10 Infrastructure): +5.88 points → New score: 84.88 → 85/100
5. **#44 ACP** (37.10 Infrastructure): +5.88 points → New score: 84.88 → 85/100
6. **#47 Monitoring** (37.10 Infrastructure): +5.88 points → New score: 84.88 → 85/100
7. **#50 Deployment secrets** (37.11 Deployment): +5.88 points → New score: 84.88 → 85/100
8. **#53 Recovery** (37.11 Deployment): +5.88 points → New score: 84.88 → 85/100
9. **#5 Real production execution** (37.2 Execution): +2.94 points → New score: 81.94 → 82/100
10. **#30 Graphify** (37.7 Knowledge): +2.94 points → New score: 81.94 → 82/100
11. **#38 Security secrets** (37.9 Security): +4.90 points → New score: 83.90 → 84/100

## Optimal Path to 95 Points

### Option 1: Two upgrades (minimum number)
- **#26 Chaos/reliability** (❌ → ✅): +13.73 points
- **#5 Real production execution** (⚠️ → ✅): +2.94 points  
- **Total gain:** 16.67 points
- **New score:** 79 + 16.67 = 95.67 → **96/100**

### Option 2: Two upgrades (alternative)
- **#26 Chaos/reliability** (❌ → ✅): +13.73 points
- **#30 Graphify** (⚠️ → ✅): +2.94 points
- **Total gain:** 16.67 points
- **New score:** 95.67 → **96/100**

### Option 3: Three upgrades (safer path)
- **#52 Reproducible deployment** (❌ → ✅): +11.76 points
- **#55 Health checks** (❌ → ✅): +11.76 points  
- **#5 Real production execution** (⚠️ → ✅): +2.94 points
- **Total gain:** 26.46 points
- **New score:** 105.46 → 100/100 (capped)

## Evaluation Criteria Application

Let me evaluate the candidates using the specified criteria:

### 1. Already-implemented functionality with missing/insufficient evidence
- **#5 Real production execution**: M8-T1 implementation complete, real test exists, only needs HERMES_ACP_TEST=1 env var
- **#44 ACP**: M8-T1 implementation complete, real test exists, only needs HERMES_ACP_TEST=1 env var  
- **#26 Chaos/reliability**: Not implemented - requires chaos testing implementation
- **#52 Reproducible deployment**: Not implemented - requires Docker, health checks, rollback
- **#55 Health checks**: Not implemented - requires health check endpoints
- **#56 Rollback**: Not implemented - requires rollback capability

✅ **#5 and #44** satisfy this criterion best

### 2. Smallest implementation effort
- **#5 Real production execution**: Set environment variable and run existing test (~5 minutes)
- **#44 ACP**: Set environment variable and run existing test (~5 minutes) 
- **#26 Chaos/reliability**: Implement chaos testing framework (~hours/days)
- **#52 Reproducible deployment**: Implement Docker, health checks, rollback (~days)
- **#55 Health checks**: Implement HTTP endpoints (~hours)
- **#56 Rollback**: Implement rollback capability (~hours/days)

✅ **#5 and #44** satisfy this criterion best (trivial effort)

### 3. Highest score contribution
- **#26 Chaos/reliability**: +13.73 points (highest)
- **#52 Reproducible deployment**: +11.76 points
- **#55 Health checks**: +11.76 points  
- **#56 Rollback**: +11.76 points
- **#5 Real production execution**: +2.94 points (lower)
- **#44 ACP**: +5.88 points (moderate)

⚠️ **#26** has highest contribution but fails criterion #1 and #2
✅ **#5 and #44** have good contribution with excellent criteria #1 and #2

### 4. Lowest risk of introducing regressions
- **#5 Real production execution**: Zero risk - only runs existing test with env var
- **#44 ACP**: Zero risk - only runs existing test with env var  
- **#26 Chaos/reliability**: Medium risk - new testing framework could affect existing tests
- **#52 Reproducible deployment**: High risk - major system changes
- **#55 Health checks**: Low risk - additive endpoints
- **#56 Rollback**: Medium risk - changes to state management

✅ **#5 and #44** satisfy this criterion best (zero risk)

### 5. Ability to close a criterion completely rather than partially
- **#5 Real production execution**: Would close criterion completely (⚠️ → ✅)
- **#44 ACP**: Would close criterion completely (⚠️ → ✅)
- **#26 Chaos/reliability**: Would close criterion completely (❌ → ✅)
- Others would also close completely

✅ **#5 and #44** satisfy this criterion equally well

## Final Recommendation

**BEST CANDIDATE: #5 Real Production Execution**

### Why this is the highest-value next task:

1. **Already implemented**: M8-T1 Hermes ACP implementation is complete and verified via mock tests
2. **Trivial effort**: Only requires setting HERMES_ACP_TEST=1 environment variable and running existing test
3. **Zero risk**: No code changes needed; only executes existing verification test
4. **Addresses M8-T1 impact**: Directly verifies the M8-T1 work that just received Terminal 3 QA-GO
5. **High value**: Closes criterion completely and enables follow-up upgrades
6. **Prerequisite for other upgrades**: Enables verification of #44</think># H. EXACTLY ONE NEXT TASK

**Criterion number:** #5 Real Production Execution

**Exact requirement being closed:** Verify real Hermes ACP subprocess execution via setting HERMES_ACP_TEST=1 environment variable and running the real subprocess test

**Exact files likely to change:** 
- No file changes required (verification only)
- Environment variable: HERMES_ACP_TEST=1
- Test to run: `tests/integration/test_m8_hermes_acp.py::test_real_hermes_acp_conditional`

**Exact implementation needed:**
1. Set environment variable HERMES_ACP_TEST=1
2. Run the specific test: `pytest tests/integration/test_m8_hermes_acp.py::test_real_hermes_acp_conditional -v`
3. Verify test passes (currently skipped due to missing environment variable)

**Exact tests/evidence required:**
- Successful execution of `test_real_hermes_acp_conditional` with HERMES_ACP_TEST=1
- Test should exercise: connect() → new_session() → prompt() → cancel() → close_session()
- Should verify provenance contract and trust_level == "untrusted"  
- Should ensure reliable child process and temp directory cleanup

**Why this is the highest-value next task:**
1. **Leverages completed work**: M8-T1 implementation is complete (77fa497) and just received Terminal 3 QA-GO
2. **Trivial effort**: Requires only setting an environment variable and running an existing test (estimated <5 minutes)
3. **Zero risk**: No code modifications, only verification of existing implementation
4. **High impact**: Worth 2.94 points toward the 95/100 goal; enables follow-up verification of #44 ACP
5. **Addresses immediate gap**: Directly closes the verification gap for M8-T1 work that is otherwise complete
6. **Prerequisite value**: Completing this enables efficient path to 95 points (e.g., +#5 +#26 Chaos/reliability = 95.67 → 96/100)

This task provides the highest return on minimal effort with zero risk, directly verifying work that is already implemented and quality-approved.