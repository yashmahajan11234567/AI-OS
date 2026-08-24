| Requirement | Evidence | PASS/FAIL |
|---|---|---|
| Baseline stabilization | 697 unit tests pass, 0 failures, 0 collection errors from repo root after adding testpaths to pyproject.toml | PASS |
| Happy path | TestClosedLoopHappyPath.test_full_closed_loop_goal_to_pass in test_closed_loop.py demonstrates: goal→plan→councils→capability→MCP→execute→verify→PASS | PASS |
| Real verification | Happy path test verifies actual workflow execution through WorkflowManager with real service handlers and checks step results in state manager | PASS |
| Failure detection | Failure path test executes workflow with forced failure in testing step (ConfigurationError) and verifies workflow fails | PASS |
| Root cause analysis | Failure path test verifies RootCauseAnalyzer emits ROOT_CAUSE_ANALYZED event with correct category (CONFIGURATION) and responsible service (planning) | PASS |
| Learning/improvement | Failure path test verifies LearningService captures learning from analysis via LearningCaptured event | PASS |
| Recovery/replan | Failure path test verifies new PlanningRequested event is emitted with feedback from RCA, leading to new plan generation | PASS |
| Re-execution | Failure path test verifies workflow re-executes with fixed configuration and succeeds | PASS |
| Re-verification | Re-executed workflow completes successfully and verification checks all step results | PASS |
| Final decision | Both happy path and failure path tests conclude with successful workflow completion | PASS |
| Retry limit | RetryManager configured with max_retries=3, failure path shows 3 retry attempts before failure | PASS |
| Event evidence | Both tests capture and verify specific event emissions (PLANNING_REQUESTED, PLANNING_COMPLETED, TASK_FAILED, ROOT_CAUSE_ANALYZED, etc.) | PASS |
| State evidence | Tests verify state changes in StateManager (workflow steps, plan storage, etc.) | PASS |
| EventBus isolation | Tests properly reset EventBus singleton between runs and verify no cross-test pollution; 5 consecutive runs all pass | PASS |
| RootCauseAnalyzer lifecycle | RootCauseAnalyzer has shutdown() method that unsubscribes from EventBus; set_root_cause_analyzer() properly cleans up previous instance | PASS |
| RetryManager lifecycle | RetryManager uses lazy EventBus initialization via _ensure_bus() and properly handles EventBus availability | PASS |
| Checkpoint behavior | CheckpointManager's _emit_event method moved inside class and properly handles UUID correlation IDs (generates new UUID for invalid strings) | PASS |
| Unit regression | 697 unit tests pass (same as baseline) | PASS |
| Integration regression | 101 integration tests pass (as reported by Terminal 2, verified) | PASS |
| Full regression | 802 total tests pass (unit + integration + performance) | PASS |
| M0 regression | 697 unit tests pass | PASS |
| M1 regression | 697 unit tests + 30 E2E tests = 727 tests pass | PASS |
| M2 regression | 697 unit tests pass (API exports are additive only) | PASS |
| Scope discipline | No implementation of deferred items: CLI 9.4-9.12, WorkflowManager singleton reduction, Kernel 5-state FSM | PASS |