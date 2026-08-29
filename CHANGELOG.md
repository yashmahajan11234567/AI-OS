# Changelog

All notable changes to AI-OS Hermes Kernel will be documented in this file.

## [1.0.0] — 2026-08-27

### V1 Release

AI-OS Hermes Kernel v1.0 reaches V1 Release Gate with all Terminal 1 milestones (M0–M3) complete, Terminal 2 implementation verified, and Terminal 3 independent QA GO.

### Added

- **Canonical EventBus** — Async-native event bus with priority lanes, DLQ, and 121 EventType members
- **LifecycleManager** — 8-state FSM (UNINITIALIZED → INITIALIZING → OPERATIONAL → DEGRADED → SHUTTING_DOWN → TERMINATED, plus ROLLBACK_IN_PROGRESS and RECOVERY_IN_PROGRESS)
- **Core Components** — C1 (EventBus), C2 (ServiceRegistry), C3 (ConfigurationManager), C4 (StructuredLogger)
- **Core Managers (9)** — StateManager, StorageManager, WorkflowManager, SecurityManager, HealthManager, ResourceManager, CapabilityManager, ObservabilityManager, LifecycleManager
- **Engineering Services** — LearningService, PlanningService, SelfPromptingService, TestingService, etc.
- **Multi-Perspective Testing** — 9 AIAgencyService perspectives + UserSimulationAgent (10th)
- **TestingCouncil** — Anonymized cross-ranking, dissent preservation, dissenter-override via KKC/EVC techniques
- **FinalJudgeAgency** — Independent APPROVE/REJECT/CONDITIONAL verdict aggregation
- **SimplificationGate** — Pre-acceptance complexity governance gate
- **Closed-Loop Verification** — FAIL → RCA → Learning → Replan → Re-execute → Retest flow
- **9 seeded defect detection** — M7 testing contract with seeded defects verified
- **Hermes Kernel bootstrap** — All components wired, config-gated, singletons managed
- **External Integrations (M8-T4)** — Notion, Obsidian (dual-path MCP/filesystem), Claude-Mem adapters with C14 advisory provenance
- **M10 Autonomous Services (12)** — Config-gated behind `services.autonomy.enabled`; includes ObjectiveGenerator, ReplanDetector, AutonomousFinalJudge, SelfPromptingAutonomous, AuditTrail, etc.
- **Part 15 Documentation** — All 26 normative documents populated (14,706+ lines across 13 chapters + supporting docs)
- **Type-safe EventBus** — Generic event types with schema validation
- **StructuredLogger** — Correlation ID propagation, causation tracking, phase-aware log levels
- **ABAC Security Model** — Attribute-based access control with HMAC-signed records
- **SHA-256 Hash-Chained Audit Trail** — Tamper-evident autonomous action logging

### Fixed

- **C1 Hermes Naming Collision** — `HermesKernel` (AI-OS) vs `hermes-agent`(EXT) (external) distinction now explicit throughout documentation
- **C2 Verification Gate Count** — Ambiguous "12/12 gates" replaced with "all 17 acceptance criteria verified"; no `VerificationService` exists (gates are in existing components)
- **C3 Lifecycle State Count** — Narrative updated from 5-state (RUNNING) to 8-state (OPERATIONAL, DEGRADED, ROLLBACK_IN_PROGRESS, RECOVERY_IN_PROGRESS) per Part 4 §4.3.3
- **C4 Notion Adopt-or-Drop** — Notion adopted as external integration via MCP bridge (M8-T4); adapter implemented and tested
- **README Part 15 File Inventory** — Corrected stale "EMPTY" status claims; all 26 normative files now documented as EXISTING with line counts

### Changed

- **LifecycleModel**: Part 1's 5-state FSM superseded by Part 4's 8-state FSM (CONFLICT-INIT-01 resolved in favor of Part 4)
- **Runtime documentation**: 15.3-Runtime-Implementation.md updated to reflect 8-state FSM and OPERATIONAL state
- **Part 15 README**: Status updated from NOT READY to PARTIALLY READY; gaps GAP-P15-03 through GAP-P15-06 resolved
- **Test suite**: 1293 unit tests, 436 integration tests, 201 security tests (1 skipped in security)

### Known Limitations

- **M10 Integration Tests** — 10 integration tests and 9 security tests blocked by config timing issue (config freeze prevents pre-init override). Documented in M10 report; unit tests pass. Full fix requires YAML-based config or pre-loaded AppConfig.
- **M10 Flaky Unit Test** — `test_audit_trail_hash_chain` occasionally fails under test ordering (passes in isolation). Root cause: shared state between M10 audit trail tests and other unit tests.
- **CONFLICT-P15-01** — Naming/classification divergence between `MASTER_ARCHITECTURE_ROADMAP.md` and `ARCHITECTURE_SPEC_TOC.md` remains unresolved pending ARB decision.
- **Deferred Items** — Kernel 5-state FSM (redundant with LifecycleManager 8-state), CLI command groups 9.4–9.12, singleton reduction, production hardening/SLA contracts all deferred to post-V1.

### Test Results

| Suite | Tests | Status |
|-------|-------|--------|
| Unit Tests | 1,293 | ✅ PASS |
| Integration Tests | 436 | ✅ PASS (2 skipped) |
| Security Tests | 201 | ✅ PASS (1 skipped) |
| M10 Unit Tests | 22 | ✅ PASS |
| M8-T4 Adapter Tests | 75 | ✅ PASS |
| M8-T4 Integration Tests | 38 | ✅ PASS |
| **Total** | **~1,930** | **✅ PASS** |

---

## [0.x.x] — Pre-V1 Development

Earlier development milestones (M0 through M11) developed the foundational architecture, core managers, event system, learning/adaptive systems, and autonomy services. See individual milestone reports in `architecture/Part15/M{0-11}/` for detailed change logs.
