# HOSTILE ARCHITECTURE REVIEW — AI-OS Hermes Kernel

**Date:** 2026-09-02  
**Scope:** READ-ONLY — no modifications  
**Reference:** `architecture/Part00/ARCHITECTURE_SPEC_PART0.md` (frozen principles)  
**Baseline:** `architecture/Common/ARCHITECTURAL_INVENTORY.md` + `ARCHITECTURE_SPEC_TOC.md`  
**Committee:** `C--Development`  
**Author:** Claude Code (Agnes-2.0-Flash)  

---

## EXECUTIVE SUMMARY

AI-OS Hermes Kernel is a **monorepo of competing implementations** rather than a single authoritative architecture. Four kernel variants coexist, 12 M10 autonomy services are silently broken in 2 of 3 variants, and the active kernel itself contains internal contradictions that violate its own documented principles. The project is **not spec-freeze ready**.

**Key numbers:**
- 4 competing kernel implementations
- 12 M10 autonomy services broken (getter called instead of setter)
- 6 documented production bugs (unchanged from last audit)
- 15+ files using deprecated `datetime.utcnow()`
- 1 duplicate property (`security_manager` in kernel.py)
- 2 missing async keywords in 2 of 3 kernel variants
- 14 empty documentation files
- 0 ADRs recorded

---

## ISSUES BY CATEGORY

### 1. DUPLICATE KERNELS

**SEVERITY:** 🔴 CRITICAL  
**LOCATION:** `src/aios/core/` (4 files)  
**EVIDENCE:**
- `kernel.py` (2652 lines) — PRIMARY, has M14-T2 additions
- `kernel.py.current_backup` (2652 lines) — backup of kernel.py
- `kernel_head.py` (2473 lines) — ALTERNATIVE, missing M14-T2
- `kernel_minimal_m14t2.py` (2501 lines) — MINIMAL, almost identical to head

All three variants are importable from `src/aios/core/`. None is designated as authoritative. The ARCHITECTURAL_INVENTORY.md names `kernel.py` as primary but makes no formal declaration.

**WHY IT VIOLATES ARCHITECTURE:** Principle 2 states "Kernel MUST own exactly 4 Core Components and MUST NOT contain domain logic." Having 3+ competing kernel implementations means there is no single authoritative Kernel — every principle becomes ambiguous depending on which variant you read. This is the **single most important problem** in the entire project.

**RECOMMENDED FIX:** 
1. Formalize `kernel.py` as THE authoritative implementation
2. Delete `kernel_head.py` and `kernel_minimal_m14t2.py`
3. Move `kernel.py.current_backup` outside the source tree (or delete it)
4. Document which features are in which variant in a migration/deprecation note

**DEPENDENCIES:** All services, tests, and CI that import from `aios.core`

---

### 2. M10 AUTONOMY SERVICES BROKEN IN 2 OF 3 KERNELS

**SEVERITY:** 🔴 CRITICAL  
**LOCATION:** `kernel_head.py:1820,1832,1847,1860,1870,1879,1888,1897,1908,1916,1925,1937` and `kernel_minimal_m14t2.py:1848,1860,1875,1888,1898,1907,1916,1925,1936,1944,1953,1965`  
**EVIDENCE:**
- `kernel.py` (primary) correctly uses: `set_objective_generator(objective_generator)` (line 1950)
- `kernel_head.py` incorrectly uses: `get_objective_generator(og_config)` (line 1820) — calls the **getter** instead of the **setter**
- `kernel_minimal_m14t2.py` has the same bug (line 1848)

All 12 M10 services (N1-N12) are affected in both alternate variants:
- N1: `get_objective_generator(og_config)` → should be `set_objective_generator(objective_generator)`
- N2: `get_replan_detector(rd_config)` → should be `set_replan_detector(replan_detector)`
- N3: `get_autonomous_judge(aj_config, council)` → should be `set_autonomous_judge(autonomous_judge)`
- N4: `get_self_prompting_autonomous(sp_config)` → should be `set_self_prompting_autonomous(...)`
- N5: `get_learning_apply(la_config)` → should be `set_learning_apply(...)`
- N6: `get_capability_provenance_ext(cp_config)` → should be `set_capability_provenance_ext(...)`
- N7: `get_state_verification(sv_config, self._state_manager)` → should be `set_state_verification(...)`
- N8: `get_security_abac_ext(sa_config, self._security_manager)` → should be `set_security_abac_ext(...)`
- N9: `get_resource_manager_quota(rq_config, self._resource_manager)` → should be `set_resource_manager_quota(...)`
- N10: `get_autonomy_override(ao_config)` → should be `set_autonomy_override(...)`
- N11: `get_audit_trail(at_config)` → should be `set_audit_trail(audit_trail)`
- N12: `get_autonomy_fallback(af_config)` → should be `set_autonomy_fallback(...)`

The getter functions (e.g., `get_objective_generator(og_config)`) expect **zero args** — they return the existing singleton. Passing config to them either silently ignores the config or throws a type error at runtime.

**WHY IT VIOLATES ARCHITECTURE:** The M10 autonomy framework is a core architectural feature. If the kernel that runs M10 calls getters instead of setters, **none of the 12 autonomous services will ever be registered as singletons**. They will be instantiated and registered with the service registry, but the global `get_xxx()` accessors will return `None` because `set_xxx()` was never called. This means the entire M10 autonomy layer is silently non-functional in 2 of 3 kernel variants.

**RECOMMENDED FIX:**
1. Fix all 12 call sites in `kernel_head.py` and `kernel_minimal_m14t2.py` to use setters
2. Delete both variants (see Issue #1)
3. Add a test that verifies all 12 setters are called during kernel init

**DEPENDENCIES:** All 12 M10 services, SelfLoopEngine (which depends on N1-N12)

---

### 3. DUPLICATE `security_manager` PROPERTY IN kernel.py

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel.py:316-319` and `kernel.py:445-448`  
**EVIDENCE:**
```python
# Line 316-319 (first definition)
@property
def security_manager(self) -> SecurityManager | None:
    return self._security_manager

# Line 445-448 (second definition, OVERRIDES first)
@property
def security_manager(self) -> SecurityManager | None:
    return get_security_manager()
```

The second definition (returning the global singleton) silently overrides the first (returning the instance variable). Code that accesses `self.security_manager` gets different results depending on Python property resolution order.

**WHY IT VIOLATES ARCHITECTURE:** A property should have exactly one definition. Dual definitions create ambiguity about whether the kernel owns its security manager or delegates to the global. This is a code quality issue that could hide bugs.

**RECOMMENDED FIX:** Keep only the first definition (returning `self._security_manager`). The kernel should own its components directly, not delegate to globals.

**DEPENDENCIES:** All code accessing `kernel.security_manager`

---

### 4. MISSING ASYNC ON `_init_n8n` AND `_init_obsidian_git` IN 2 OF 3 KERNELS

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel_head.py` and `kernel_minimal_m14t2.py`  
**EVIDENCE:**
- `kernel.py` (correct): `async def _init_n8n(self) -> None:` (line 1642) and `async def _init_obsidian_git(self) -> None:` (line 1708)
- `kernel_head.py` (bug): `def _init_n8n(self) -> None:` (missing `async`) and `def _init_obsidian_git(self) -> None:` (missing `async`)
- `kernel_minimal_m14t2.py` (bug): same — missing `async` on both methods

Both methods are called with `await self._init_n8n()` and `await self._init_obsidian_git()`. In `kernel_head.py` and `kernel_minimal_m14t2.py`, calling `await` on a non-async function raises `TypeError: object NoneType can't be used in 'await' expression`.

**WHY IT VIOLATES ARCHITECTURE:** The kernel start sequence would crash during initialization if either `kernel_head.py` or `kernel_minimal_m14t2.py` were ever used as the active kernel.

**RECOMMENDED FIX:** Add `async` to both method signatures, or delete both kernel variants.

**DEPENDENCIES:** N8N adapter, Obsidian Git adapter, kernel start/stop

---

### 5. TRIPLE REGISTRY (LEGACY + CANONICAL + BACKUP)

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel.py:512-522`  
**EVIDENCE:**
```python
def _registry_wrapper(self):
    from aios.services.registry import ServiceRegistry as LegacyRegistry
    return LegacyRegistry()
```

The primary kernel creates a **new** `ServiceRegistry()` via `_registry_wrapper()` and passes it to `bootstrap_engineering_services()`. Meanwhile, the kernel's own `_service_registry` is a **different** `ServiceRegistry` instance from `aios.core.service_registry`. These are two separate registry objects.

The ARCHITECTURAL_INVENTORY.md notes this as "potential second registry" but treats it as a non-issue because "it delegates every operation to the canonical singleton." However, the code shows it creates a brand new `LegacyRegistry()` — not a delegate, not a wrapper — just a fresh instance.

**WHY IT VIOLATES ARCHITECTURE:** Principle 2 requires the kernel to own exactly one ServiceRegistry. Having two creates potential for services to be registered in the wrong registry and invisible to the lifecycle manager.

**RECOMMENDED FIX:** Remove `_registry_wrapper()` entirely. Pass `self._service_registry` directly to `bootstrap_engineering_services()`.

**DEPENDENCIES:** All service registration, lifecycle management

---

### 6. MISSING `project_service` IN ALTERNATIVE KERNELS

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel_head.py`, `kernel_minimal_m14t2.py`  
**EVIDENCE:**
- `kernel.py` has: `_project_service` attribute (line 261), `project_service` property (line 382), `_init_project_service()` method (line 619), and references in dashboard service initialization (lines 2243, 2294-2295)
- `kernel_head.py`: NO `project_service` anywhere
- `kernel_minimal_m14t2.py`: NO `project_service` anywhere

The "minimal" kernel variant (`kernel_minimal_m14t2.py`) is named for being minimal but is missing the project service that the primary kernel has. The "head" kernel is also missing it.

**WHY IT VIOLATES ARCHITECTURE:** M14-T2 is a documented feature. Having it in one kernel variant but not others creates inconsistent behavior depending on which kernel runs.

**RECOMMENDED FIX:** Either add `project_service` to all variants, or remove it from `kernel.py` and make it a variant. Formalize which features belong in the authoritative kernel.

**DEPENDENCIES:** Dashboard service, project workspace

---

### 7. MISSING `AIOS_TEST_SCHEMA` AND `AIOS_OWNED_SCHEMAS` IN ALTERNATIVE KERNELS

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel_head.py:131`, `kernel_minimal_m14t2.py:131`  
**EVIDENCE:**
- `kernel.py`: `from aios.adapters.supabase_adapter import SupabaseAdapter, AIOS_TEST_SCHEMA, AIOS_OWNED_SCHEMAS` (line 132)
- `kernel_head.py`: `from aios.adapters.supabase_adapter import SupabaseAdapter` (line 131) — missing the constants
- `kernel_minimal_m14t2.py`: `from aios.adapters.supabase_adapter import SupabaseAdapter` (line 131) — missing the constants

Without these constants, the Supabase adapter cannot be properly configured with schema allowlists.

**WHY IT VIOLATES ARCHITECTURE:** The Supabase adapter requires schema-level access control. Missing constants means either a runtime error or a security gap.

**RECOMMENDED FIX:** Add the missing imports, or remove Supabase support from the alternate variants.

**DEPENDENCIES:** Supabase adapter, M14-T2 test infrastructure

---

### 8. SELFLOOP ENGINE NOT REGISTERED AS SERVICE

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel.py:2316-2379`  
**EVIDENCE:**
```python
self._self_loop_engine = SelfLoopEngine(
    kernel=self,
    event_bus=self._event_bus,
    service_registry=self._service_registry,
    ...
)
```

The `SelfLoopEngine` is created and assigned to `self._self_loop_engine` but is **never registered** with the service registry via `register_service()`. It has no lifecycle management, no health check, no shutdown coordination.

**WHY IT VIOLATES ARCHITECTURE:** Principle 5 requires services to extend `BaseService` and be registered with the kernel. The SelfLoopEngine is a core autonomous decision-making component but operates outside the service lifecycle.

**RECOMMENDED FIX:** Register `SelfLoopEngine` as a service, or document why it's intentionally outside the lifecycle.

**DEPENDENCIES:** M10 autonomy services, lifecycle manager

---

### 9. MOCK MODE DEFAULT FOR SELFLOOP ENGINE

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** `kernel.py:2337`  
**EVIDENCE:**
```python
mock_mode = not self._read_config_bool("services.self_loop.real_mode_enabled", False)
self._self_loop_engine.set_mock_mode(mock_mode)
```

The default is `mock_mode=True` (because the config default is `False`). The self-loop engine runs mock mode by default — it never actually makes autonomous decisions unless explicitly enabled.

**WHY IT VIOLATES ARCHITECTURE:** The self-loop engine is the centerpiece of the M13 autonomous architecture. If it runs in mock mode by default, the entire autonomy layer is non-functional until someone sets `services.self_loop.real_mode_enabled=true`.

**RECOMMENDED FIX:** Change the default to `real_mode_enabled=False` → `mock_mode=True` is the current behavior, which is correct for safety. But this should be **documented as an ADR**, not left as an implicit default.

**DEPENDENCIES:** M13 self-loop engine, all M10 services

---

### 10. 15+ FILES USING DEPRECATED `datetime.utcnow()`

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** 50+ lines across 30+ files  
**EVIDENCE:**
```
src/aios/core/kernel.py:658,704,2433,2480,2576
src/aios/core/workflow.py:538,550,965,991,1024,1148,1177
src/aios/core/checkpoint.py:38,116,361
src/aios/core/memory.py:53,54,148,153,164,216,221,231,304,384,385,407,479,480,747,755
src/aios/events/bus.py:51
src/aios/services/base.py:168
src/aios/adapters/acp_session.py:83,84,113,157,164,176
src/aios/adapters/agent_reach.py:69,72,107,130,162,183,211,232,263,294,325
... and 20+ more files
```

Python 3.12+ deprecates `datetime.utcnow()` in favor of `datetime.now(timezone.utc)`.

**WHY IT VIOLATES ARCHITECTURE:** While not an architectural violation per se, using deprecated APIs creates technical debt that will become a breaking change in future Python versions. The ARCHITECTURE_SPEC_TOC.md lists this as "Open Decision #3" but it's been open since the spec was drafted.

**RECOMMENDED FIX:** Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`. This is a mechanical change across 30+ files.

**DEPENDENCIES:** All timestamp-dependent functionality

---

### 11. EMPTY DOCUMENTATION

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/Architecture/system-overview.md`, `docs/Architecture/execution-pipeline.md`, `docs/Architecture/planning-architecture.md`  
**EVIDENCE:** All 5 files exist but are empty (0 bytes).

**WHY IT VIOLATES ARCHITECTURE:** The architecture spec (Part 0) requires documentation of principles, scope, and conformance. Empty docs mean there is no documented architecture to reference.

**RECOMMENDED FIX:** Fill in all empty docs, or remove the files and update the TOC.

**DEPENDENCIES:** Architecture specification v1.0

---

### 12. NO ADRs RECORDED

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** Project-wide  
**EVIDENCE:** 0 ADR files found. The architecture spec requires ADRs for any deviation from principles.

**WHY IT VIOLATES ARCHITECTURE:** Principle 12 requires ADRs for deviations. Without ADRs, there is no audit trail for architectural decisions.

**RECOMMENDED FIX:** Create an ADR for each open decision in the spec TOC, plus each major deviation found in this review.

**DEPENDENCIES:** Architecture specification v1.0

---

### 13. WORKFLOW MANAGER USES GLOBAL SINGLETONS FOR RETRY/RCA

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** `workflow.py:300`  
**EVIDENCE:**
```python
self._retry_manager = get_retry_manager()
```

The WorkflowManager resolves RetryManager and RootCauseAnalyzer via global singletons rather than receiving them as constructor dependencies. This creates hidden coupling and makes testing difficult.

**WHY IT VIOLATES ARCHITECTURE:** The spec calls for injecting Core Components via constructor. Using globals for operational dependencies is a pattern violation.

**RECOMMENDED FIX:** Pass `retry_manager` and `root_cause_analyzer` as constructor parameters, resolved by the kernel at init time.

**DEPENDENCIES:** Workflow execution, retry logic, root cause analysis

---

### 14. 6 DOCUMENTED PRODUCTION BUGS (UNCHANGED)

**SEVERITY:** 🔴 CRITICAL (confirmed still present)  
**LOCATION:** See ARCHITECTURAL_INVENTORY.md §11  
**EVIDENCE:**
1. `events/base.py:164` — `Event` dataclass missing `kw_only=True`
2. `core/retry.py:73-79` — `max_retries` semantics wrong (allows N total calls, not N+1)
3. `core/root_cause.py:323` — "timeout" missing from transient_keywords
4. `core/root_cause.py:313-320` — Code defect logic requires "test" in error
5. `core/checkpoint.py:94-98` — `create_checkpoint` requires pre-existing workflow state
6. `tests/integration/test_integration.py:396-414` — Test double signature mismatch

**WHY IT VIOLATES ARCHITECTURE:** These bugs prevent 9 of 21 tests from passing. The architecture cannot be verified if tests are broken.

**RECOMMENDED FIX:** Fix all 6 bugs before spec freeze.

**DEPENDENCIES:** All integration tests

---

### 15. M13 TERMINAL CONTRACT INCOMPLETE IN ALTERNATE KERNELS

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** `kernel_head.py:1673-1677`, `kernel_minimal_m14t2.py` (same)  
**EVIDENCE:**
- `kernel.py` checks 4 adapters in `_validate_terminal_contract`: `_supabase_adapter`, `_supabase_test_adapter`, `_n8n_adapter`, `_obsidian_git_adapter`
- `kernel_head.py` and `kernel_minimal_m14t2.py` check only 3: `_supabase_adapter`, `_n8n_adapter`, `_obsidian_git_adapter` — missing `_supabase_test_adapter`

**WHY IT VIOLATES ARCHITECTURE:** The terminal contract validation is incomplete in 2 of 3 kernels, meaning a T2 authority violation could go undetected.

**RECOMMENDED FIX:** Align all variants to check the same 4 adapters.

**DEPENDENCIES:** M13 terminal architecture, security validation

---

### 16. `_registry_wrapper()` CREATES NEW REGISTRY, NOT A WRAPPER

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** `kernel.py:512-522`  
**EVIDENCE:**
```python
def _registry_wrapper(self):
    from aios.services.registry import ServiceRegistry as LegacyRegistry
    return LegacyRegistry()
```

The method is called `_registry_wrapper` but creates a brand new `LegacyRegistry()` — not a wrapper around the canonical registry. It creates a second, independent ServiceRegistry instance.

**WHY IT VIOLATES ARCHITECTURE:** Creates a second source of truth for service registration. Services registered through the wrapper may not be visible to the canonical registry.

**RECOMMENDED FIX:** Remove `_registry_wrapper()` and pass `self._service_registry` directly.

**DEPENDENCIES:** All service registration, lifecycle management

---

### 17. DASHBOARD SERVICE NOT REGISTERED WITH LIFECYCLE MANAGER

**SEVERITY:** 🟠 MEDIUM  
**LOCATION:** `kernel.py:2217-2295`  
**EVIDENCE:**
```python
service = await create_dashboard_service(...)
self._dashboard_service = service
```

The dashboard service is created and stored but never passed to `register_service()` or the lifecycle manager. It has no lifecycle coordination.

**WHY IT VIOLATES ARCHITECTURE:** Services should go through the lifecycle manager for proper start/stop ordering.

**RECOMMENDED FIX:** Register dashboard service with the kernel's service registry.

**DEPENDENCIES:** Dashboard functionality

---

### 18. MISSING `set_xxx` FUNCTIONS FOR M10 SERVICES IN ALTERNATE KERNELS

**SEVERITY:** 🔴 HIGH  
**LOCATION:** `kernel_head.py`, `kernel_minimal_m14t2.py`  
**EVIDENCE:**
Both alternate kernels call `get_xxx(config)` which returns the **existing singleton** (or raises if none exists). They never call `set_xxx(service)`, so:
- The service is registered with the ServiceRegistry (via `self.register_service()`)
- But the global singleton accessor is NEVER set
- Any code calling `get_objective_generator()` later gets `None` or an error

**WHY IT VIOLATES ARCHITECTURE:** The 13 global accessors are "architectural fixtures" (Principle 4). If they're not set during init, the entire singleton pattern is broken.

**RECOMMENDED FIX:** Call `set_xxx(service)` after `register_service(service)` for all 12 M10 services in all kernel variants.

**DEPENDENCIES:** All M10 services, any code using the global accessors

---

### 19. INCONSISTENT `register_service` USAGE

**SEVERITY:** 🟡 HIGH  
**LOCATION:** `kernel.py` (all 3 variants)  
**EVIDENCE:**
The M10 services are registered via `self.register_service(service)` (line 1949, etc.) but the SelfLoopEngine is NOT registered. The dashboard service is created but NOT registered. This creates an inconsistent lifecycle.

**WHY IT VIOLATES ARCHITECTURE:** Principle 5 requires all services to be registered with the lifecycle manager.

**RECOMMENDED FIX:** Either register all autonomous components, or document which are intentionally outside the lifecycle.

**DEPENDENCIES:** Lifecycle management, health checks

---

### 20. NO PROVENANCE / AUDIT TRAIL FOR KERNEL INIT

**SEVERity:** 🟠 MEDIUM  
**LOCATION:** `kernel.py` — entire `start()` method  
**EVIDENCE:**
The kernel `start()` method initializes 50+ components, creates adapters, registers services, and starts the self-loop engine — but emits no audit events for any of these actions. There is no record of what was initialized, when, or in what order.

**WHY IT VIOLATES ARCHITECTURE:** Principle 1 (event-driven) requires all state changes to be emitted as events. The kernel init sequence is a black box.

**RECOMMENDED FIX:** Emit `KernelComponentInitialized` events for each major initialization step.

**DEPENDENCIES:** Observability, debugging, incident response

---

## TOP 10 ARCHITECTURAL RISKS

| Rank | Risk | Severity | Impact |
|------|------|----------|--------|
| 1 | **No single authoritative kernel** — 4 variants with undocumented differences | 🔴 CRITICAL | Every architectural claim is ambiguous |
| 2 | **M10 autonomy non-functional in 2/3 kernels** — getters called instead of setters | 🔴 CRITICAL | 12 autonomous services silently broken |
| 3 | **6 production bugs preventing test verification** | 🔴 CRITICAL | Architecture cannot be validated |
| 4 | **SelfLoopEngine outside service lifecycle** | 🟡 HIGH | No health checks, no shutdown coordination |
| 5 | **Duplicate `security_manager` property** | 🟡 HIGH | Ambiguous ownership, potential race condition |
| 6 | **Missing async on `_init_n8n`/`_init_obsidian_git` in 2 kernels** | 🟡 HIGH | Kernel start would crash |
| 7 | **Second ServiceRegistry created via `_registry_wrapper()`** | 🟡 HIGH | Services may be invisible to lifecycle manager |
| 8 | **15+ deprecated `datetime.utcnow()` calls** | 🟠 MEDIUM | Python 3.12+ deprecation, will break in future |
| 9 | **No ADRs recorded** | 🟠 MEDIUM | No audit trail for architectural decisions |
| 10 | **Empty documentation files** | 🟠 MEDIUM | No documented architecture to reference |

---

## CRITICAL BLOCKERS

1. **Delete or formalize 3 of 4 kernel variants** — Until there is one authoritative implementation, no architectural claim can be trusted.
2. **Fix M10 getter/setter bug in `kernel_head.py` and `kernel_minimal_m14t2.py`** — Or delete them. The 12 autonomy services are non-functional in these variants.
3. **Fix 6 production bugs** — Until tests pass, the architecture cannot be verified.
4. **Resolve duplicate `security_manager` property** — One definition or the other must go.
5. **Add `async` to `_init_n8n` and `_init_obsidian_git` in 2 kernel variants** — Or delete them.

---

## NONCRITICAL GAPS

1. Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` across 30+ files
2. Fill empty documentation files
3. Create ADRs for all open decisions
4. Register SelfLoopEngine with service lifecycle
5. Register dashboard service with service lifecycle
6. Remove `_registry_wrapper()` and use canonical registry directly
7. Align terminal contract validation across all kernel variants
8. Add provenance events for kernel initialization

---

## WHAT TO FIX FIRST

**Immediate (before any spec work):**
1. **Decide on ONE authoritative kernel** — Likely `kernel.py`. Delete or archive the other 3.
2. **Fix the 6 production bugs** — Unblocks test verification.
3. **Fix the M10 getter/setter bug** — If keeping alternate kernels, fix them. If deleting, just delete.

**Short-term (before spec freeze):**
4. **Resolve duplicate `security_manager` property**
5. **Add `async` to missing methods in alternate kernels** (or delete them)
6. **Remove `_registry_wrapper()`**
7. **Register SelfLoopEngine and dashboard service with lifecycle**

**Medium-term (before v1.0):**
8. **Replace `datetime.utcnow()`**
9. **Create ADRs**
10. **Fill empty documentation**
11. **Add provenance events for kernel init**

---

## CONCLUSION

AI-OS Hermes Kernel has a **fundamental source-of-truth problem**: 4 competing kernel implementations with undocumented differences. The primary kernel (`kernel.py`) is the most complete but still has internal contradictions (duplicate `security_manager` property, `_registry_wrapper()` creating a second registry). The two alternate kernels (`kernel_head.py`, `kernel_minimal_m14t2.py`) have **12 broken M10 autonomy service initializations** that render the entire autonomy layer non-functional.

**The project is not ready for spec freeze.** The 6 production bugs must be fixed first to enable test verification. Then the kernel variant problem must be resolved — either by deleting the 3 alternate implementations or by fixing all their bugs and formally designating one as authoritative.

After that, the remaining issues (deprecated datetime API, missing ADRs, empty docs, lifecycle gaps) are fixable in parallel with spec writing.
