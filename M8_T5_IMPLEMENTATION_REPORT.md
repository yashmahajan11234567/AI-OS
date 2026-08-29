# M8-T5 Implementation Report — Capability / External Integration Hardening

| | |
|---|---|
| **Task** | M8-T5 — Capability / External Integration Hardening |
| **Spec** | `architecture/Part15/M8/M8-T5-IMPLEMENTATION-SPEC.md` (authoritative) |
| **Terminal** | Terminal 2 (implementation) |
| **Date** | 2026-08-25 |
| **Status** | **COMPLETE — ready for Terminal 3 Verification Gate (spec §32)** |

---

## 1. Summary

M8-T5 hardens the capability layer so external integrations are discovered
through validated manifests, cannot self-escalate trust or authority, and are
enforced at the capability boundary rather than only at adapters. The core
proof: a new external capability is added by dropping one YAML manifest into
`config/capabilities/` and booting — **zero `kernel.py` edits**.

The production code for this task pre-existed in draft form; this pass fixed
five latent runtime defects, aligned rule IDs with spec §21, wired the kernel
config surface correctly, rewrote seven test files onto the actual implemented
API, and closed two config/gate integration gaps found by the new tests.

## 2. Production Changes

### 2.1 `src/aios/core/capability_manager.py`
- **Fixed `CapabilityAvailability` enum**: added missing `UNKNOWN` / `DISABLED`
  members (draft referenced members that did not exist → `AttributeError` at runtime).
- **Removed duplicate legacy `resolve()`**: a second definition silently
  overrode the hardened M8-T5 resolve (CM-RES-001/CM-DIS-001/CM-RES-002 +
  security enforcement were unreachable). Single hardened implementation remains.
- **Fixed `deprecate()`**: was setting `CapabilityState.REMOVED` (destructive);
  now sets `DEPRECATED` and stays resolvable-but-flagged per spec §14.
- **Rewrote `initialize_capability(capability_id) -> bool`** (async): dependency
  availability check (`CM-INIT-001`, recorded not raised), adapter instantiation
  through `AdapterFactory.get_adapter(class_path, kwargs=...)`, optional awaited
  `initialize()`/`health_check()`. Failures set `health_status="unhealthy"`,
  `availability=ERROR`, `last_error` on the entry; registry never corrupted.
- **Added `_parse_version()` helper**: unparseable semver components fall back to
  `(0,)` instead of crashing precedence comparison.
- **Rule-ID alignment to spec §21**: CM-SHADOW-001 (lower-trust shadow attempt),
  CM-PREC-001 (equal/lower precedence), CM-DIS-001 (disabled resolve), CM-SEC-001/002/003.
- **Sensitive-keys check upgraded fail-closed**: nested payload scan (dict/list,
  case-insensitive) + explicit `payload_keys` hint now RAISES CM-SEC-002
  instead of logging only.
- **Security-gate result contract fix**: consumer read `.valid`; actual
  `CapabilitySpecValidationResult` exposes `.passed`/`.violations`. Consumer now
  reads `passed` first (with `.valid`/boolean fallbacks) and surfaces violation
  descriptions in the typed error. This defect had broken every kernel boot with
  manifests present.

### 2.2 `src/aios/core/kernel.py`
- Added `_read_config_str/_list/_bool` helpers on `HermesKernel`.
- Rewrote `_init_capability_manifests()`:
  - honors `kernel.capabilities.enabled` master switch;
  - parses `adapter_allowlist` as YAML list OR comma string, with hardcoded
    6-adapter fallback;
  - creates `AdapterFactory` with `getattr(self, "_mcp_manager", None)` and
    injects factory + SecurityManager into CapabilityManager;
  - registers each spec and `await initialize_capability(...)` for enabled ones;
  - per-spec try/except — one bad manifest never blocks boot.
- All legacy `_init_X()` methods retained (backward-compat constraint).

### 2.3 `src/aios/core/configuration_manager.py`
- Registered `kernel.capabilities` in the embedded C3 schema. The schema is
  strict (`additional_properties=false` under `kernel`); without this
  registration the section could not be overridden through Layer-2 app.yaml at
  all — making the documented config surface non-functional. Acceptance/lifecycle
  tests re-run green after the change.

### 2.4 Files verified NOT modified (hard constraints)
`ai_agency.py` internals, M8-T1..T4 adapters, `mcp_manager.py`, `acp_adapter.py`,
`agent_reach.py`, `BaseExecutionAdapter` — untouched (git status confirms).
No new EventTypes invented; canonical mapping (SERVICE_STARTED/SERVICE_STOPPED/
SKILL_EXECUTED/SKILL_FAILED) unchanged.

## 3. Test Suite (7 files, 101 tests)

| File | Tests | Coverage |
|---|---|---|
| `tests/unit/test_capability_manifest.py` | 14 | Spec model; loader skip-not-raise for invalid/malformed/non-allowlisted/disabled manifests; defaults; `discovered_from`; async loader |
| `tests/unit/test_adapter_factory.py` | 9 | Explicit allowlist; arbitrary importlib paths rejected; traversal rejected; kwargs passthrough; mcp_manager injection |
| `tests/unit/test_capability_registry_hardening.py` | 40 | Extended entry fields; disable/enable/deprecate/set_health lifecycle; CM-SEC-001/002 (incl. nested + hint)/003; CM-PREC-001/CM-SHADOW-001 collision determinism incl. version edge cases; initialize success/failure paths; deregister REMOVED; legacy register/deregister/resolve/invoke regression guards |
| `tests/unit/test_capability_provenance.py` | 13 | Mandatory provenance fields via `build_capability_provenance`; spoof-proof re-assertion of source/advisory/authority/trust_level; extra-metadata channel; `assert_capability_provenance` contract |
| `tests/unit/test_skill_provenance.py` | 3 | `execute_skill` attaches provenance via both helpers with advisory/untrusted authority |
| `tests/integration/test_m8_t5_dynamic_loading.py` | 8 | **Dynamic loading proof (§25)**: manifest-only capability registered+resolvable post-boot with zero kernel edits; security context enforced on dynamic capabilities; disable/enable cycle; deregister preserves kernel + other capabilities; trust/authority defaults; builtin-trust claim rejected while sibling loads |
| `tests/integration/test_m8_t5_security.py` | 14 | Adversarial: wrong-type/oversized manifests skipped; untrusted-vs-higher-trust shadowing blocked (CM-SHADOW-001); unsafe adapter class + path traversal rejected; sensitive-key denial (CM-SEC-002); authority injection stripped; provenance spoofing re-asserted; gate-rejected spec (path-traversal id) typed CM-SEC-001; unauthorized op denied; SkillSpecTor regression; MCP-unavailable → availability=error, kernel intact; Agent-Reach unreachable → typed fail-safe |

Integration tests boot the REAL kernel (`run_kernel(KernelConfig(data_dir=…))`
/ `stop_kernel()` + full singleton reset, matching `test_kernel_lifecycle_e2e.py`),
with the relative default manifest dir `./config/capabilities` resolved into a
temp tree via `monkeypatch.chdir` for hermeticity.

## 4. Defects Found & Fixed During Test Alignment

| # | Defect | Severity | Fix |
|---|---|---|---|
| D1 | Duplicate `resolve()` definition overrode hardened M8-T5 resolve | Critical | Removed duplicate |
| D2 | Missing `CapabilityAvailability.UNKNOWN/DISABLED` enum members | Critical (runtime crash) | Added members |
| D3 | Security-gate consumer read `.valid`; result exposes `.passed` — every manifest boot failed registration | Critical | Consumer reads `passed` (+fallbacks), violations surfaced |
| D4 | `deprecate()` set REMOVED (destructive) instead of DEPRECATED | High | Sets DEPRECATED, stays resolvable |
| D5 | Kernel couldn't read YAML-list allowlist; `initialize_capability` not awaited; no `enabled` master switch | High | Rewrote `_init_capability_manifests` |
| D6 | Sensitive keys logged but not denied | Medium | Fail-closed raise CM-SEC-002 |
| D7 | `kernel.capabilities` absent from C3 schema → section unusable via app.yaml | Medium | Schema registration |

## 5. Acceptance Criteria Status (spec §28)

| # | Criterion | Status |
|---|---|---|
| 1 | Extended registry entry | ✅ (trust/authority/adapter_binding/ops/health/availability/enabled/discovered_from/dependencies) |
| 2 | Deterministic identity | ✅ (exact-match + trust > version > first; `_parse_version` safe) |
| 3 | Controlled discovery | ✅ (manifest + validation gate; non-auto-trust enforced at loader AND SecurityManager gate) |
| 4 | No self-granted authority | ✅ (defaults advisory; `mark_capability_advisory` non-overridable — tested) |
| 5 | Deterministic collisions | ✅ (CM-SHADOW-001 / CM-PREC-001 tested incl. equal-version and unparseable-version cases) |
| 6 | Security context at resolve/invoke | ✅ (CM-SEC-001/002/003 at capability layer) |
| 7 | Complete provenance | ✅ (capability layer + skill results) |
| 8 | External repos bounded | ✅ (no repo loading; local manifest + explicit allowlist only) |
| 9 | Skills non-authoritative | ✅ (provenance attached, advisory/untrusted) |
| 10 | Agencies functional & unmodified | ✅ (no changes) |
| 11 | Agent Reach functional & unmodified | ✅ (no changes; fail-safe test added) |
| 12 | MCP/ACP boundaries intact | ✅ (no adapter rewrites) |
| 13 | Failure isolation | ✅ (typed errors recorded on entries; RLock-guarded; boot never blocked) |
| 14 | Dynamic addition w/o kernel edit | ✅ (integration-proven §25) |
| 15 | Previous suite green | ✅ (1,416 passed / 2 skipped, fully green; see §6) |

## 6. Full Regression Result

**FINAL RUN (after all changes incl. schema fix D7):**

```
1416 passed, 2 skipped in 44.91s   — FULLY GREEN
```

- Baseline before M8-T5: 1,315 passed / 2 skipped (1,317 collected)
- After M8-T5: **1,418 collected = 1,317 baseline + 101 new**, of which
  **1,416 passed / 2 skipped — zero failures**
- An intermediate run showed one failure
  (`test_structured_logger.py::test_context_propagates`) — the correlation test
  already flagged flaky during M8-T4 QA. It passes in isolation and in every
  focused run (file-scoped 34/34, `-k structured_logger` 66/66), and passed in
  the final full-suite run. Environmental timing, not an M8-T5 defect.

## 7. Do-Not-Implement Compliance (spec §30)

Not implemented (confirmed): M9 functionality, Docker/deployment, operational
monitoring, full security audit campaign, external Git/repo loading, execution
sandbox, M8-T1..T4 adapter rewrites, M7 agency internal changes, new EventTypes,
`core.capability` ServiceRegistry-id change.

## 8. Handoff to Terminal 3 (Verification Gate §32)

Terminal 3 can verify independently:
- **Dynamic extension proof**: `tests/integration/test_m8_t5_dynamic_loading.py::TestDynamicCapabilityLoading::test_dynamic_capability_load_without_kernel_edit` — manifest-only; `kernel.py` diff contains only the generic boot step, nothing capability-specific.
- **Non-auto-trust**: `test_builtin_trust_claim_rejected` + `TestMalformedSpecRegistration` (gate rejects builtin/authoritative claims and path-traversal ids).
- **Collision determinism**: `TestCapabilityIDCollision`, `TestCapabilityEscalation`, unit `TestDuplicateAndCollision`.
- **Security enforcement**: `TestUnauthorizedOperation`, `TestSecretAccessDenied`, unit `TestSecurityContextEnforcement`.
- **Provenance**: `TestCapabilityProvenanceOnExecution`, `TestAuthorityInjection`, `TestProvenanceSpoofing`, unit provenance files.
- **Failure paths**: `TestMCPUnavailable`, `TestAgentReachUnavailable`.
- **Backward compat**: full suite green; legacy `_init_X` capabilities still register (lifecycle e2e + acceptance suites).

Example manifests ship under `config/capabilities/` (graphify_context,
playwright_browser, notion_planning, obsidian_knowledge, claude_mem_context),
exercised at every kernel boot.
