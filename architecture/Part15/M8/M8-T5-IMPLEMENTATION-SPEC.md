# M8-T5 Implementation Specification
## Capability / External Integration Hardening — Terminal 2 Blueprint

**Date:** 2026-08-25
**Status:** READY FOR IMPLEMENTATION
**Prerequisites:** M7 (complete, frozen), M8-T1 (complete, independently verified), M8-T2 (complete, independently verified), M8-T3 (complete, independently verified), M8-T4 (complete, independently verified)
**Terminal 1 Verdict:** M8-T5 PLANNING COMPLETE — READY FOR IMPLEMENTATION
**Test baseline (measured):** 1,317 tests collected (`python -m pytest --collect-only -q`, exit 0)

---

## 1. Executive Summary

M8-T1 through M8-T4 delivered six production external integrations (Hermes, Playwright, Graphify, Notion, Obsidian, Claude-Mem) plus the M7 agency-agents and Agent Reach surfaces. Each is individually sound: adapters follow `BaseExecutionAdapter`, provenance is attached on every result where it matters, and SecurityManager gates MCP connections and skill installs.

However, the **capability layer itself is immature** and leaks into the kernel. `CapabilityManager` (`src/aios/core/capability_manager.py`) is a **metadata-only registry**: `register()` stores an entry and `invoke()` resolves it and emits an event but **executes nothing and binds no adapter**. Every one of the five M8 integrations is wired by a **hardcoded `_init_X()` method** in `kernel.py` (lines 884–1110) that is explicitly called in `kernel.start()` (lines 426–435). Adding a sixth external capability requires editing `kernel.py`: a new import (lines 120–125), a new `_init_X()`, and a new boot call.

This violates the core principle: *a new external capability should not require modifying the kernel merely because the capability is new.*

M8-T5 closes this gap with the **minimum** architectural change that makes external capabilities **discoverable, registered, resolved, executed, isolated, audited, disabled, replaced, and extended** without kernel edits, while preserving M7 and M8-T1..T4 behavior exactly.

**What M8-T5 changes:**
1. A **capability manifest** loader — external capabilities are declared in `config/capabilities/*.yaml` (or via a `kernel.capabilities` config list), not in kernel source.
2. An **adapter factory** — adapters are instantiated by class-path from the manifest, removing the hardcoded kernel import block.
3. **Registry hardening** — `CapabilityRegistryEntry` gains `trust_level`, `authority_classification`, `adapter_binding`, `operations`, `health/availability`, `enabled`, `discovered_from`, and deterministic collision/authority precedence.
4. **Security-context enforcement** at resolution/invocation time (not just metadata).
5. **Capability-level provenance** via a `mark_capability_advisory()` helper that re-asserts C14 constants (spoof-proof), mirroring the adapter `_mark_advisory` pattern.
6. **Lifecycle controls** — `disable()`/`enable()`/`deprecate()` without destroying the entry; `REMOVED` reserved for full unload.
7. Closed provenance gap on **skill execution results**.

**What M8-T5 explicitly does NOT do:** invent a sandbox for arbitrary remote code, load external Git repositories (none exist in-repo; all sources are local), rewrite the working M8-T1..T4 integrations, touch M7 agency internals, or implement M9+ functionality.

---

## 2. Current Architecture

AI-OS kernel boot (`HermesKernel.start()`) proceeds through explicit, hardcoded phases:

```
_init_core_components()      → C1–C4 singletons + Core Managers
_init_lifecycle_manager()    → LifecycleManager (orchestrates phases)
_init_m7_testing()           → HermesBridge + UserSimulationAgent (not a capability)
_init_graphify()             → GraphifyAdapter + capability register
_init_playwright()           → PlaywrightMCPAdapter + capability register
_init_notion()               → NotionAdapter + capability register
_init_obsidian()             → ObsidianAdapter + capability register
_init_claude_mem()           → ClaudeMemAdapter + capability register
_start_services()            → engineering services
```

There are **four parallel, separately-wired integration mechanisms**, none of which is config-driven for the *registration* step:

| Mechanism | Wiring location | Added via config? | Added via kernel edit? |
|-----------|-----------------|-------------------|------------------------|
| M8-T2/T3/T4 adapters (Playwright, Graphify, Notion, Obsidian, Claude-Mem) | `kernel.py` `_init_X()` + `CapabilityManager.register()` | MCP *transport* yes (`config/mcp/*.json`); adapter *registration* NO | **YES** |
| Hermes (ACPP/MCP) | `kernel.py` `_init_m7_testing()` → `HermesBridge` → `UserSimulationAgent` | NO (MCP config only) | **YES** (not a capability) |
| Agencies (9) | `ai_agency.py:54-65` enum + `:739-755` dict | NO | **YES** (2 files) |
| Skills | `SkillManager` dynamic scan of `.claude/skill-specs/*.skill.md` | YES (drop file) | NO (already dynamic) |
| Agent Reach | `MCPManager` server `agent_reach` | YES (MCP config) | NO (not a capability) |

The asymmetry is the central problem: **skills and MCP servers are already config-driven, but the *capability registration* that makes them first-class AI-OS capabilities is kernel-wired.**

---

## 3. Existing Capability Infrastructure

### 3.1 CapabilityManager (`src/aios/core/capability_manager.py`)

- **Role:** Phase-4 Core Manager; the single capability registry (single in-memory dict `_registry: dict[capability_id → CapabilityRegistryEntry]`, `RLock`-guarded).
- **Lifecycle:** constructed by kernel (`kernel.py:669-674`), registered with ServiceRegistry as `core.capability` (`capability_manager.py:433-460`), initialized by LifecycleManager (`initialize()`, `:373`).
- **Business API:** `register()`, `deregister()`, `get_capability()`, `list_capabilities()`, `discover_by_facade()`, `discover_by_tags()`, `resolve()`, `invoke()`.
- **Critical limitation:** `invoke()` (`:604-644`) resolves the entry and emits `SKILL_EXECUTED` but **returns the entry without executing anything** ("The actual provider execution is delegated to the kernel's execution layer"). It binds **no adapter** — the kernel holds adapter instances directly (`self._graphify_adapter`, etc.).

### 3.2 CapabilityRegistryEntry (`capability_manager.py:155-181`)

```python
@dataclass
class CapabilityRegistryEntry:
    capability_id: str
    facade: str
    provider_id: str
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    state: CapabilityState = CapabilityState.REGISTERED   # REGISTERED | DEPRECATED | REMOVED
    security_context: dict[str, Any] = field(default_factory=dict)
    resource_profile: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()
```

**Missing fields for M8-T5 goals:** `trust_level`, `authority_classification`, `adapter_binding`, `operations`, `health`, `availability`, `enabled`, `discovered_from`, `dependencies`. There is **no adapter reference** — resolution cannot reach execution.

### 3.3 Config flags

`kernel.capability.enforceAuthorization` and `kernel.capability.rejectDuplicateProvider` (read in `initialize()`, `:389-394`). Both default `True`.

---

## 4. Capability Registry Analysis

- **Architecture:** single process-wide dict, `RLock`-guarded, cleared on `shutdown()`.
- **Registration API:** `register(capability_id, facade, provider_id, *, provider_metadata, version, security_context, resource_profile, tags)`.
- **Identity:** `capability_id` (string, exact match). No composite key, no namespace.
- **Version handling:** `version` is a *string stored but never compared/checked*. No compatibility logic.
- **Duplicate handling:** `register()` rejects a second `register()` of the same `capability_id` with `CM-DUP-001` (`reject_duplicate_provider=True`). It does **not** consider provider, facade, or trust — first registrant wins unconditionally.
- **Metadata:** free-form `provider_metadata`, `security_context`, `resource_profile`, `tags` (tuple). No schema.
- **Tags / categories:** `facade` (single string) + `tags` (tuple). `discover_by_facade` exact match; `discover_by_tags` all-must-match.
- **Operation declarations:** **NONE.** A capability declares no operations; `security_context` may contain a free-form `allowed_operations` list, but nothing validates it.
- **Security context:** stored as free-form dict; **never enforced** (no op check, no sensitive-key check, no size limit at the capability layer).
- **Trust / authority:** **absent.** No `trust_level`, no `authority_classification`. The registry cannot express "this external capability is untrusted and advisory-only."
- **Source / provenance:** **absent** at the capability layer. `discovered_from` is undefined.
- **Lifecycle / availability / health:** `CapabilityState` has `REGISTERED`/`DEPRECATED`/`REMOVED`; `DEPRECATED` is **never set by any code**; there is no `health`/`available` concept. `deregister()` destroys the entry (`state=REMOVED`, popped from dict). No `disable()`.
- **Discovery:** static — callers invoke `register()` directly. No scan, no config-driven load.

**Type:** STATIC (kernel-wired). Discovery exists only as post-hoc query (`discover_by_*`).

**Weaknesses:** no adapter binding, no trust/authority, no operation/security enforcement, no deterministic collision precedence by trust, no disable (only destroy), no health/availability, no provenance at the capability layer, no version semantics.

---

## 5. Capability Discovery Analysis

Current discovery is **manual/kernel-wired**: the kernel calls `register()` at boot. There is no config-driven or filesystem-driven capability discovery.

**Required shape (per task brief):**

```
DISCOVERY → VALIDATION → SANDBOX/BOUNDARY → REGISTRATION → POLICY CHECK → AVAILABLE
```

M8-T5 introduces **manifest-driven discovery**: `config/capabilities/*.yaml` (and/or a `kernel.capabilities` config list) declares external capabilities. The loader **validates** each manifest (schema + SecurityManager gate), **binds** it to an allowlisted adapter, **registers** it, then a **policy check** (trust default, authorization enforcement) makes it `AVAILABLE`. A discovered capability is **never auto-trusted** — `authority_classification` defaults to `advisory`/`contextual` and `trust_level` defaults to `untrusted` unless explicitly and validly raised by a trusted manifest.

This is safe *given the repo*: there is **no external Git/repo loading** (Section 10). All capability sources are local config files. The "sandbox/boundary" is the **adapter allowlist + manifest validation + registration gate**, not a code-execution sandbox.

---

## 6. Agency-Agents Analysis

- **Discovery/registration:** `AIAgencyService.__init__` (`ai_agency.py:739-755`) hardcodes 9 agencies in a dict keyed by `AgencyType` enum (`ai_agency.py:54-65`). NOT registered in `CapabilityManager`. Separate closed registry.
- **Provenance:** YES — full `Provenance` attached to every `AgencyResponse.metadata.provenance` (`ai_agency.py:191-203, 268-273`). `TestingEvidence` requires frozen `Provenance`.
- **Authority boundary:** ADVISORY ONLY. SecurityAgency defers to `SecurityManager.authorize()` and SKIPs on DENY (`security_agency_adapter.py:88-104`). `FinalJudgeAgency` is evidence-aggregation only; it drops builder-origin evidence (INV-009) and rejects prose-only verdicts (INV-010) (`ai_agency.py:568-730`). Agencies never self-approve.
- **Extensibility:** adding a 10th agency requires editing `ai_agency.py` (enum + dict). **M8-T5 MUST NOT regress M7.** Therefore M8-T5 does **not** rewire agencies. Optionally, M8-T5 lets an existing agency be *exposed as a capability* through a manifest that binds an adapter facade to the agency's existing boundary — but this is additive and does not modify agency internals. The recommended M8-T5 scope is to **leave agencies as-is** and document them as out-of-scope for capability-facade exposure (see Section 30).

---

## 7. Agent Reach Analysis

- **Role:** CONTEXT PROVIDER. Produces untrusted external observations that must be normalized before use (`agent_reach.py:1-6, 41-43`).
- **Discovery/invocation:** MCP server `agent_reach`; `AgentReachAdapter` normalizes raw MCP tool results into `AgentReachObservation`. `_ensure_connected()` checks `mcp_manager.get_server_status()` before each call.
- **Auth/credentials:** delegated to MCP server config, validated by `MCPServerSecurityGate` (`security_manager.py:554-924`).
- **Provenance:** per-call `_create_provenance()` (`agent_reach.py:66-79`).
- **Failure:** catches exceptions, returns failed observation with error in content.
- **External content trust:** `trust_level="untrusted"` hardcoded (`:120,174,223`); docstring forbids auto-decision.
- **Authority:** NONE.
- **Boundary:** Agent Reach is correctly a *context provider*, **not** a capability. M8-T5 keeps it out of `CapabilityManager` and treats it as the canonical reference for the untrusted-context boundary. No change required.

---

## 8. Skills Analysis

- **Location/discovery:** `.claude/skill-specs/*.skill.md` (Vercel Skills format) scanned by `SkillSpecParser.discover_skill_specs()` (`skill_manager.py:89-120`, `skill_spec.py:206-226`). **Already dynamic** — drop a file, no kernel edit.
- **Loading/representation:** `SkillSpec` → internal `Skill`; `SkillManager.register_skill()` (`skill_manager.py:238-243`). Duplicate registration warns and overwrites.
- **Executable code:** YES — `entry_point: "module:function"` loaded via `importlib` (`skill_manager.py:286-302`).
- **Authority:** NO. Installation gated by `SecurityManager.validate_skill_before_install()` → `SkillSpecTorGate` (static analysis; C10 LLM stage disabled; rejects dangerous permissions/wildcards; namespace-spoofing protection) (`security_manager.py:247-311, 1343-1398`).
- **FS/network:** controlled via declared `permissions`; validated at install.
- **Versioned:** YES (`version` required).
- **Provenance:** spec metadata present (`parsed_at`, `source_path`, `skill_id`); **execution results LACK provenance** (`SkillExecution` has no provenance attached to the returned value — Section 9 gap).
- **Conflict:** possible (overwrite). Deterministic rule: last-registered wins (documented).
- **Implicit authority:** NO — gated by SecurityManager.
- **M8-T5 action:** (a) register skills optionally as capabilities via manifest is **out of scope** (skills already have a runtime path); (b) **close the provenance gap** — attach provenance to skill execution results (small, contained change in `skill_manager.py:396-448`). This is the only skill change in M8-T5.

---

## 9. MCP/ACP Boundary Analysis

- **MCPManager** (`mcp_manager.py`): standalone subsystem; auto-discovers `config/mcp/*.json` (glob, `:126-139`); 4 transports; tool discovery + provenance-tracked execution; **gate-before-connect** via `SecurityManager.validate_mcp_server_before_connect()` (`:211-243`). Does **not** register capabilities.
- **ACP** (`acp_adapter.py`, `acp_session.py`): Hermes ACP stdio transport; JSON-RPC 2.0; `AcPSessionRegistry` with isolation validation. `HermesBridge` selects ACP-first with MCP fallback; provenance distinguishes protocol.
- **Hermes is NOT a capability** — it is used by `UserSimulationAgent` (M7). This is an inconsistency: five integrations register as capabilities; Hermes does not. M8-T5 **documents** Hermes as an execution substrate (correct, since it drives the user-simulation agent) and does **not** force it into `CapabilityManager`.
- **Distinctions preserved:** ACP (agent session), MCP (tool call), local adapter (`BaseExecutionAdapter`), filesystem fallback (Obsidian), skill, agency, Agent Reach. M8-T5 adds a **capability facade** that sits *above* all of these and does not rewrite any of them.
- **Duplicated logic** (do NOT rewrite): MCP connect/discover boilerplate across Graphify/Notion/Obsidian/Claude-Mem adapters; `_make_provenance()`/`_mark_advisory()` across the three M8-T4 adapters; Playwright's dual-path JSON-RPC. M8-T5 introduces shared *helpers* (`capability_provenance.py`) but **does not modify** working adapters except where provenance is missing (skills).

---

## 10. External Repository Analysis

**Finding (measured):** There is **NO external Git/repository loading mechanism** in the codebase. No `git clone`, no runtime repo fetch, no `importlib` of remote code. The closest mechanisms are:
- Config-driven adapter enablement (`config/mcp/*.json`, `.claude/skill-specs/`) — local files only.
- `skill_spec.py:206-226` `repository` field is **metadata only**, never used to fetch.
- Path validation exists where local FS is touched (Obsidian vault `is_relative_to` + `.obsidian/` block, `obsidian_adapter.py:346-370`).

**Implication for M8-T5:** Do **NOT** invent a sandbox or remote-code containment system. The minimum hardening is a **controlled capability-loading boundary**:
- Manifests are **local YAML files** under `config/capabilities/`.
- The adapter class referenced by a manifest must resolve to an **allowlisted module** (`aios.adapters.*` or an explicitly permitted list). Arbitrary `importlib` from a manifest path is rejected.
- No commit pinning needed (no Git). Loading is deterministic (local files). Loading can be disabled via `kernel.capabilities.enabled=false`.
- If a future milestone adds remote repos, the boundary designed here (allowlist + validation gate + non-authoritative default) is the seam to extend — but M8-T5 does not build it.

**No finding of:** arbitrary code execution, path-escape, capability shadowing of built-ins, or secret access through repository loading — because none exists. This is documented so Terminal 3 does not hunt for a non-existent sandbox.

---

## 11. Security Context Analysis

- **Permissions representation today:** free-form `security_context` dict on capabilities; structured `permissions: list[str]` on `SkillSpec` (`skill_spec.py:56`); MCP server config validated by `MCPServerSecurityGate`.
- **Declared-but-not-enforced on capabilities:** `allowed_operations`/`allowed_actions`, `sensitive_keys`, `max_content_size`, `requires_validation`. `CapabilityManager` stores these but **never checks them at resolution/invocation**.
- **Enforced elsewhere:** MCP connect gate (`MCPServerSecurityGate` host allowlist, dangerous command/env/header patterns, timeout/retry bounds — `security_manager.py:554-924`); skill install gate (`SkillSpecTorGate`). Both are **static/install-time**, not per-call runtime.
- **Gap:** no per-call enforcement of a capability's declared `allowed_operations`, `sensitive_keys`, or size limits. M8-T5 adds `CapabilityManager.enforce_security_context()` invoked during `resolve()`/`invoke()` when `enforce_authorization=True`.

---

## 12. Provenance Analysis

**Mandatory capability provenance fields (M8-T5 standard):**

`capability_id`, `capability_version`, `source`, `adapter`, `operation`, `task_id`, `execution_id`, `correlation_id`, `timestamp`, `protocol`, `target`, `errors`, `trust_level`, `authority_classification`, `discovered_from` (where applicable).

**Current state:**
- **M8-T4 adapters (Notion/Obsidian/Claude-Mem):** complete. `_mark_advisory()` re-asserts C14 constants `source`/`advisory`/`authority`/`trust_level` **after** merging any caller-supplied provenance — **spoof-proof** (`notion_adapter.py:302-323`, `claude_mem_adapter.py:302-323`, `obsidian_adapter.py:316-340`).
- **Graphify:** `advisory_only` / `authority=advisory_only`.
- **Playwright/Hermes:** `ExecutionResult` (status/findings/metrics/raw) — not a provenance dict but structurally an observation; adapter may add provenance.
- **MCPManager:** provenance per tool call (`mcp_manager.py:710-721`).
- **Skill execution results:** **MISSING** provenance (`skill_manager.py:396-448` returns raw result).
- **Capability layer (CapabilityManager):** **no provenance** — registration/invocation events carry only manager metadata, not capability provenance.

**Gaps to close in M8-T5:**
1. Capability-level provenance helper (`capability_provenance.py`) with `mark_capability_advisory()` mirroring the adapter C14 re-assertion pattern.
2. Provenance on skill execution results (Section 8).

---

## 13. Trust / Authority Analysis

**Hard boundary (must hold):** External capabilities are DATA / OBSERVATION / CONTEXT / EXECUTION RESULT / EVIDENCE. They MUST NOT decide PASS/FAIL/APPROVE/REJECT/SECURITY VERDICT/FINAL VERIFICATION/FINAL ARCHITECTURAL DECISION. AI-OS retains testing/review/verification/security/council/judge/final authority.

**Inspected:** agencies (advisory, INV-009/INV-010 hold), Agent Reach (untrusted, no authority), M8-T4 adapters (C14 `authority=contextual`/`advisory_only`, re-asserted). **No violations found.**

**Latent risk:** `CapabilityRegistryEntry` has **no authority/trust field**. A future capability could be registered claiming authority because the registry cannot express or enforce non-authoritativeness. M8-T5 adds `authority_classification` (default `advisory`/`contextual`) and `trust_level` (default `untrusted`) to the entry, and `mark_capability_advisory()` makes these non-overridable by callers (the same defense the adapters already use).

---

## 14. Lifecycle Analysis

**Current (capability):** REGISTERED → (deregister) → REMOVED. No DEPRECATED transition, no health, no availability, no disable.

**Desired (M8-T5):**

```
DISCOVER → VALIDATE → REGISTER → INITIALIZE → HEALTH CHECK → AVAILABLE
   → EXECUTE → DISABLE | RECOVER | UNLOAD(REMOVED)
```

**What exists vs missing:**
- DISCOVER: added (manifest loader).
- VALIDATE: added (schema + `SecurityManager.validate_capability_spec()` gate).
- REGISTER: exists (`register()`), extended with trust/authority/adapter/ops.
- INITIALIZE: added (`initialize_capability()` triggers adapter instantiation via factory + health check).
- HEALTH CHECK: added (`set_health()` + `health_status` field; optional adapter `health_check()`).
- AVAILABLE: added (`enabled=True`, `availability="available"`).
- EXECUTE: exists at adapter layer; capability layer resolves + enforces security + provenance.
- DISABLE: **added** (`disable()` sets `enabled=False`, `state=DISABLED`, keeps entry).
- RECOVER: **added** (`enable()` reverses disable).
- UNLOAD: exists (`deregister()` → REMOVED).

`CapabilityState` extended: `REGISTERED | DISABLED | DEPRECATED | REMOVED`. `DEPRECATED` becomes usable (mark, still resolvable but flagged). Note: `deregister()`/REMOVED is the hard unload; DISABLED is the reversible off-switch.

---

## 15. Failure Handling

**Required typed failures (M8-T5 adds explicit error subtypes / rule_ids):**
- capability unavailable (not registered) → `CM-RES-001` (exists).
- capability initialization fails → `CM-INIT-001` (new).
- MCP/ACP unavailable → surfaced by adapter, recorded as `availability="error"`; capability stays registered but EXECUTE fails typed.
- external repository missing/malformed → N/A (no repo loading); manifest malformed → `CM-MANIFEST-001` (new).
- skill malformed → `SkillSpecTorGate` already blocks at install.
- agency unavailable → agency layer handles; capability facade (if any) records `availability="error"`.
- Agent Reach unavailable → adapter returns failed observation; capability `availability="error"`.
- capability timeout → adapter-level; capability records `health_status="degraded"`.
- malformed response → adapter coercion (`base.py` ERROR observation); capability provenance marks `errors`.
- duplicate registration → `CM-DUP-001` (exists); extended with deterministic precedence when trust differs (Section 16).
- invalid metadata → `CM-INV-001` (exists in tests) + manifest schema validation `CM-MANIFEST-001`.
- incompatible capability version → `CM-VER-001` (new; version compared when provided).

**Principle:** failures are typed, recorded on the entry (`availability`/`health_status`/`last_error`), and **never corrupt the registry dict or kernel state**. The `RLock` + try/except around registration/initialization guarantees the dict stays consistent.

---

## 16. Capability Collision / Conflicts

**Conflict classes:**
- duplicate `capability_id` (same provider) → reject (`CM-DUP-001`).
- duplicate `capability_id` with **different trust** (e.g., untrusted external shadows a trusted built-in) → **deterministic precedence: higher trust wins; the lower-trust registration is rejected with `CM-PREC-001`** and an emitted `CapabilityConflictEvent` mapping (canonical `SERVICE_STARTED` is already used; conflict is logged, not a new EventType — per CONFLICT E.1 no invented EventTypes).
- conflicting versions → higher `version` wins if semver-parseable; else first-registered wins; recorded.
- capability shadowing built-ins → built-ins are registered first at boot with `trust_level="trusted"`/`builtin`; external manifests default to `untrusted`; shadowing an existing built-in id by an external manifest is rejected (`CM-SHADOW-001`) unless `allow_shadow=true` is explicitly set (default false).
- malicious replacement → adapter allowlist (Section 17) prevents an untrusted manifest from binding a trusted built-in's adapter class under its id.

**Precedence rules (deterministic):**
1. Trust order: `builtin`/`trusted` > `trusted_contextual` > `untrusted`.
2. Equal trust → higher semver `version` wins; unparseable version → first registrant wins.
3. External manifest may never silently override a `builtin`/`trusted` capability with the same id (rejected, `CM-SHADOW-001`).

---

## 17. New Components

| Component | Path | Purpose |
|-----------|------|---------|
| `CapabilityManifest` model + loader | `src/aios/core/capability_manifest.py` | Parse/validate `config/capabilities/*.yaml`; enforce non-auto-trust; build `CapabilitySpec`. |
| `AdapterFactory` | `src/aios/adapters/adapter_factory.py` | Instantiate adapters by allowlisted class-path from manifest; inject `mcp_manager`. |
| `capability_provenance` helper | `src/aios/core/capability_provenance.py` | `build_capability_provenance()` + `mark_capability_advisory()` (C14 re-assertion, spoof-proof). |
| Capability spec type | `src/aios/core/capability_manifest.py` (`CapabilitySpec`) | Typed descriptor passed to `CapabilityManager.register_capability(spec)`. |
| Example manifests | `config/capabilities/*.yaml` | 5 example manifests (graphify, playwright, notion, obsidian, claude_mem) — reference only; legacy `_init_*` path retained for backward compat (Section 21). |
| Tests | `tests/unit/test_capability_manifest.py`, `tests/unit/test_adapter_factory.py`, `tests/unit/test_capability_registry_hardening.py`, `tests/unit/test_capability_provenance.py`, `tests/integration/test_m8_t5_dynamic_loading.py`, `tests/integration/test_m8_t5_security.py`, `tests/unit/test_skill_provenance.py` | see Sections 23–26. |

---

## 18. Modified Components

| Component | Change | Risk |
|-----------|--------|------|
| `src/aios/core/capability_manager.py` | Extend `CapabilityRegistryEntry` (trust_level, authority_classification, adapter_binding, operations, health_status, availability, enabled, discovered_from, dependencies); extend `CapabilityState` (add `DISABLED`); add `register_capability(spec)`, `disable()`, `enable()`, `deprecate()`, `set_health()`, `enforce_security_context()`, deterministic `resolve()` with precedence; add `initialize_capability()`. | Medium — additive API; existing methods unchanged. |
| `src/aios/core/kernel.py` | Add `await self._init_capability_manifests()` boot step (after M8-T4 inits, before `_start_services`); import `CapabilityManifest`/`AdapterFactory`; **keep** existing `_init_X()` methods (legacy) for backward compatibility. | Low — additive boot step; no removal of existing code. |
| `src/aios/core/security_manager.py` | Add `validate_capability_spec(spec)` gate (manifest schema + adapter-allowlist check + trust-default enforcement), called at registration time (analogous to `validate_mcp_server_before_connect` / `validate_skill_before_install`). | Low — additive method; fail-closed. |
| `src/aios/core/skill_manager.py` | Attach provenance to skill execution results (`execute_skill`, `:396-448`). | Low — additive dict merge. |
| `config/defaults.yaml` | Add `kernel.capabilities` section: `enabled`, `manifest_dir`, `enforce_authorization` (default True), `reject_duplicate_provider` (default True), `trust_default` (default `untrusted`), `adapter_allowlist` (list of permitted modules). | Low — additive. |

**No changes** to: `adapters/base.py`, the 5 M8 adapter files, `mcp_manager.py`, `acp_adapter.py`, `agent_reach.py`, `ai_agency.py`, or any existing M8-T1..T4 / M7 source.

---

## 19. Configuration Changes

`config/defaults.yaml` gains:

```yaml
kernel:
  capability:
    enforceAuthorization: true
    rejectDuplicateProvider: true           # unchanged, existing
  capabilities:
    enabled: true                            # master switch for manifest loading
    manifest_dir: "./config/capabilities"    # local dir, glob *.yaml
    trust_default: "untrusted"               # discovered capabilities are NOT trusted
    adapter_allowlist:
      - "aios.adapters.graphify_adapter"
      - "aios.adapters.playwright_mcp_adapter"
      - "aios.adapters.notion_adapter"
      - "aios.adapters.obsidian_adapter"
      - "aios.adapters.claude_mem_adapter"
      - "aios.adapters.acp_adapter"
      # Add new adapter modules here as they are vetted (explicit, not wildcard).
```

Manifest example (`config/capabilities/example_external_capability.yaml`):

```yaml
capability_id: "example_external"
facade: "example"
provider_id: "example_provider"
adapter:
  class_path: "aios.adapters.graphify_adapter.GraphifyAdapter"   # must be in allowlist
  kwargs:
    server_id: "example"
transport: "mcp"
version: "1.0.0"
trust_level: "untrusted"                 # cannot claim trusted
authority_classification: "advisory"     # cannot claim authoritative
allowed_operations: ["query", "read"]
sensitive_keys: ["password", "token", "secret"]
max_content_size: 10240
discovered_from: "config/capabilities/example_external_capability.yaml"
tags: ["example", "external"]
```

---

## 20. Test Architecture

- **Unit:** pure logic — manifest parse/validate, adapter factory allowlist, registry hardening (trust/disable/collision/security), provenance re-assertion, skill provenance.
- **Integration:** kernel boot with a manifest present (no kernel edit), resolve + execute via existing mock servers, capability-level provenance collection, disable/enable/remove, security adversarial scenarios.
- **Determinism:** reuse the existing in-process mock MCP servers (`mock_*_server.py`) so integration tests need no network.
- **Backward compatibility:** existing 1,317 tests must remain green — no signature changes to `register()`/`deregister()`/`resolve()`/`invoke()`; new methods are additive.

---

## 21. Unit Test Plan

`tests/unit/test_capability_manifest.py` (~15):
- valid manifest parses to `CapabilitySpec`; missing required field rejected (`CM-MANIFEST-001`).
- `trust_level` absent → defaults to `untrusted`; `authority_classification` absent → defaults to `advisory`.
- `adapter.class_path` not in allowlist → rejected (`CM-ADAPTER-001`).
- manifest referencing unknown module → rejected.
- malformed YAML → rejected typed.
- `discovered_from` auto-populated from file path.
- manifest disabled (`enabled: false`) → skipped, not registered.
- duplicate manifests (same id, different trust) → precedence by trust (Section 16).
- version comparison semantics.

`tests/unit/test_adapter_factory.py` (~12):
- allowlisted class-path instantiates with injected `mcp_manager`.
- non-allowlisted class-path raises `CM-ADAPTER-001`.
- arbitrary `importlib` path (e.g., `os`, `subprocess`) rejected.
- path-traversal in class_path rejected.
- constructor kwargs passed through.
- unknown adapter attribute → typed error, registry state intact.

`tests/unit/test_capability_registry_hardening.py` (~30):
- `register_capability(spec)` populates extended fields (trust_level, authority, adapter_binding, operations, discovered_from, enabled).
- `disable()` → `state=DISABLED`, `enabled=False`, entry retained; `resolve()` raises when disabled (`CM-DIS-001`).
- `enable()` reverses disable.
- `deprecate()` → `state=DEPRECATED`, still resolvable but flagged.
- `set_health()` updates `health_status`; `availability` transitions.
- `enforce_security_context()` rejects operation not in `allowed_operations` (`CM-SEC-001`).
- `enforce_security_context()` rejects payload containing `sensitive_keys` (`CM-SEC-002`).
- `enforce_security_context()` rejects oversized payload (`CM-SEC-003`).
- duplicate id, same trust → reject (`CM-DUP-001`).
- duplicate id, external `untrusted` vs built-in `trusted` → external rejected (`CM-SHADOW-001`).
- equal trust, higher version → wins; unparseable version → first wins.
- `initialize_capability()` triggers adapter instantiation via factory; failure → `CM-INIT-001`, availability=error, registry intact.
- `deregister()` still → REMOVED (unchanged).
- existing `register()`/`deregister()`/`resolve()`/`invoke()` behavior unchanged (regression guards).

`tests/unit/test_capability_provenance.py` (~12):
- `build_capability_provenance()` includes all mandatory fields (Section 12).
- `mark_capability_advisory()` re-asserts `source`/`advisory`/`authority`/`trust_level` even when caller supplies conflicting values (spoof-proof, mirrors adapter `_mark_advisory`).
- caller cannot set `authority=authoritative` via merge.
- `trust_level` cannot be escalated via merge.
- provenance carries `capability_id`/`version`/`protocol`/`target`/`errors`.

`tests/unit/test_skill_provenance.py` (~5):
- skill execution result now carries provenance (source=skill, skill_id, trust_level, advisory flag).
- skill provenance cannot claim authority.

---

## 22. Integration Test Plan

`tests/integration/test_m8_t5_dynamic_loading.py` (~10) — **the core deliverable** (Section 25):
- boot kernel with an example manifest present; assert capability resolved with NO kernel edit.
- execute via bound adapter (reuse `mock_graphify_server` or a dedicated mock) → structured result + capability provenance.
- verify `security_context` enforced (allowed op passes, disallowed op denied).
- disable → resolve fails; enable → resolve succeeds.
- remove → not resolvable; kernel still functional (other capabilities intact).
- trust/authority defaults applied (untrusted/advisory) without manifest asserting otherwise.

`tests/integration/test_m8_t5_security.py` (~20) — adversarial (Section 26):
- malicious manifest metadata (oversized fields, wrong types) → rejected.
- capability ID collision (external vs built-in) → deterministic, built-in wins.
- manifest pointing to unsafe adapter class → rejected by allowlist.
- path traversal in manifest/adapter path → rejected.
- secret access attempt (payload with sensitive key) → denied.
- authority-field injection (capability output claims authoritative) → stripped/re-asserted.
- provenance spoofing attempt → re-asserted by `mark_capability_advisory`.
- malformed capability spec → registration rejected.
- unauthorized operation → invocation denied (`CM-SEC-001`).
- capability escalation (untrusted overriding trusted) → blocked (`CM-SHADOW-001`).
- untrusted output claiming authority → asserted non-authoritative in downstream result.
- malicious skill instructions still blocked by `SkillSpecTorGate` (regression).
- MCP unavailable → capability `availability=error`, no kernel crash.
- agent reach unavailable → observation fails safely, capability unaffected.

---

## 23. (labeled above) Unit Test Plan — see Section 21.
## 24. (labeled above) Integration Test Plan — see Section 22.

## 25. Dynamic Capability Loading Test

**Objective:** prove "add a new external capability without modifying the AI-OS kernel."

**Steps (implemented in `test_m8_t5_dynamic_loading.py`):**
1. Create a test external capability declared **only** in `config/capabilities/test_external_capability.yaml` (binds to an **existing, allowlisted** adapter class — e.g. `GraphifyAdapter` or a dedicated `MockExternalAdapter` shipped under `tests/` — so no production adapter file is required and **no `kernel.py` edit occurs**).
2. Boot AI-OS (`HermesKernel.start()` or the lighter `CapabilityManager` + `CapabilityManifest` path).
3. `CapabilityManager.resolve("test_external_capability")` succeeds.
4. Execute it through the adapter boundary (in-process mock server) → structured `ExecutionResult`/observation.
5. Collect capability-level provenance (`mark_capability_advisory()` output) — assert all mandatory fields present and `authority=advisory`, `trust_level=untrusted`.
6. Verify security context enforced (allowed op passes; disallowed op denied).
7. `disable("test_external_capability")` → resolve fails; `enable(...)` → succeeds.
8. `deregister(...)` → not resolvable; assert AI-OS remains functional (other capabilities still resolve; kernel state intact).
9. Assert **no `kernel.py` (or any `src/aios/core/*` capability-wiring) source file was modified** for this capability — the test adds only a manifest file (and optionally a test-only mock adapter). 

**Acceptance of the test:** if it passes with zero edits to `src/aios/core/kernel.py`, the core principle is satisfied.

---

## 26. Security Test Plan — see Section 22 (`test_m8_t5_security.py`).

## 27. Backward Compatibility Tests

- All 1,317 existing collected tests remain green (no signature changes; `register`/`deregister`/`resolve`/`invoke` unchanged).
- The five `_init_X()` kernel methods remain present and functional (legacy path); existing M8-T1..T4 integration tests that boot the kernel are unaffected.
- `CapabilityManager` singleton, ServiceRegistry id `core.capability`, canonical EventTypes (no invented EventTypes) unchanged.
- Hermes/Agent Reach/skills/agencies behavior unchanged.
- A dedicated backward-compat test asserts the 5 legacy capabilities (graphify_context, playwright_browser, notion_planning, obsidian_knowledge, claude_mem_context) still register via the existing `_init_X()` path AND can additionally be declared via manifest without collision (precedence rules).

---

## 28. Acceptance Criteria

1. Capability registry works with extended entry (trust/authority/adapter/ops/health/availability/enabled).
2. Capability identity is deterministic (id exact-match + trust/version precedence).
3. Discovery is controlled (manifest + validation gate; no auto-trust).
4. External capabilities cannot gain authority (authority_classification default advisory; non-overridable via `mark_capability_advisory`).
5. Capability collisions are deterministic (trust > version > first-registered; shadowing built-ins rejected).
6. Security context is enforced at resolution/invocation (`allowed_operations`, `sensitive_keys`, size limits).
7. Provenance is complete at capability layer (mandatory fields) and on skill results.
8. External repositories are bounded (no repo loading exists; manifest path is local + allowlisted).
9. Skills remain non-authoritative; execution results now carry provenance.
10. Agency-agents remain functional and unmodified.
11. Agent Reach remains functional and unmodified (untrusted context provider).
12. MCP/ACP boundaries remain intact (no adapter rewrites).
13. Failures do not corrupt kernel/registry state (typed, recorded, RLock-guarded).
14. **Dynamic capability addition works without any `kernel.py` edit** (Section 25).
15. All previous M7/M8 tests remain green (1,317 baseline).

---

## 29. Risk Register

| ID | Risk | Likelihood | Impact | Mitigation |
|----|------|-----------|--------|------------|
| R1 | Adapter factory allowlist too strict, blocks legit new capability | Med | Low | Allowlist is config-driven; document vetting step; tests cover addition. |
| R2 | `enforce_security_context` false-positives on legacy capabilities | Low | Med | Default `enforceAuthorization=True` but legacy `_init_X` capabilities declare `allowed_operations`; regression tests guard. |
| R3 | Manifest loader slows boot | Low | Low | Local glob of small YAML; cached after load. |
| R4 | Precedence rule surprises (external silently rejected) | Med | Low | Explicit `CM-SHADOW-001`/`CM-PREC-001` + logs; tests assert. |
| R5 | Provenance re-assertion bypassed by a new adapter | Low | Med | `mark_capability_advisory()` is the single helper; adapters encouraged to use it; security tests prove non-overridable. |
| R6 | Regression on 1,317 existing tests | Low | High | Additive API only; legacy `_init_X` retained; full-suite run in verification gate. |

---

## 30. Do-Not-Implement List

M8-T5 MUST NOT implement:
- LearningService, RCA, model routing, FreeLLMAPI integration, convergence detection, adaptive replanning (later milestones).
- M9 functionality, Docker, deployment infrastructure, operational monitoring.
- Full security audit, adversarial security campaign.
- External Git/repository loading or a code-execution sandbox (none exists; not needed).
- Rewriting M8-T1..T4 adapters or `mcp_manager.py`/`acp_adapter.py`.
- Modifying M7 agency internals (`ai_agency.py` agency implementations) — agencies stay as-is; exposing an agency as a capability is explicitly out of scope.
- Inventing new `EventType`s (CONFLICT E.1 — canonical EventTypes only).
- Changing the `core.capability` ServiceRegistry id or `CapabilityManager` singleton contract.

---

## 31. Implementation Order

1. `capability_manifest.py` — `CapabilitySpec` + loader + schema validation (no kernel dependency).
2. `adapter_factory.py` — allowlisted instantiation.
3. `security_manager.py:validate_capability_spec()` — registration gate (reuse existing gate patterns).
4. `capability_manager.py` extensions — extended entry, `CapabilityState.DISABLED`, `register_capability`, `disable/enable/deprecate/set_health`, `enforce_security_context`, deterministic `resolve`, `initialize_capability`.
5. `capability_provenance.py` — `build_capability_provenance` + `mark_capability_advisory`.
6. `kernel.py` — `_init_capability_manifests()` boot step; import loader/factory; keep legacy `_init_X`.
7. `config/defaults.yaml` — `kernel.capabilities` section + `adapter_allowlist`.
8. `skill_manager.py` — provenance on execution results.
9. Example manifests under `config/capabilities/`.
10. Unit tests (Sections 21).
11. Integration + dynamic-loading + security tests (Sections 22, 25, 26).
12. Full-suite regression (`python -m pytest`, target 1,317 + new green).
13. Final verification preparation (Section 32).

---

## 32. Verification Gate (Terminal 3 — Independent)

Terminal 3 MUST NOT merely run tests. It must independently verify **actual production paths**:

- **Dynamic extension proof:** add a capability via manifest only; confirm `kernel.py` has zero diff for that capability (Section 25 step 9). NO-GO if any `src/aios/core/kernel.py` edit was required.
- **Capability discovery:** manifest in `config/capabilities/` is picked up at boot; non-auto-trust verified (`authority=advisory`, `trust_level=untrusted` by default).
- **Registry behavior:** extended entry fields populated; `disable`/`enable`/`deprecate`/`deregister` behave per spec; RLock integrity under concurrent register/disable.
- **Security context enforcement:** a capability invocation with a disallowed operation or sensitive-key payload is denied at the capability layer (not just the adapter).
- **Provenance:** capability-level provenance present end-to-end; `mark_capability_advisory` non-overridable (spoofing attempt fails); skill results carry provenance.
- **Authority boundaries:** no capability output can assert `authority=authoritative`; agencies/Agent Reach unchanged and still non-authoritative.
- **External repository boundaries:** confirm no new remote/repo loading was introduced; manifest path is local + allowlisted.
- **Collision determinism:** external `untrusted` cannot shadow a `trusted` built-in (`CM-SHADOW-001`); equal-trust higher-version wins.
- **Failure paths:** MCP/Agent Reach unavailable → capability `availability=error`, kernel state intact; malformed manifest rejected typed.
- **Backward compatibility:** full suite green at 1,317 + new; the 5 legacy `_init_X` capabilities still register.

**GO / NO-GO:** GO only if all above pass AND the dynamic-loading test required no kernel edit AND the full existing suite is green. Any single NO-GO condition → NO-GO, return to Terminal 2.

---

## 33. Terminal 2 Implementation Prompt

> Terminal 2 — implement M8-T5 Capability / External Integration Hardening per `architecture/Part15/M8/M8-T5-IMPLEMENTATION-SPEC.md`.
>
> **Hard constraints:** PLANNING-ONLY was Terminal 1's role; you now implement. Do NOT modify M7 agency internals, M8-T1..T4 adapters, `mcp_manager.py`, `acp_adapter.py`, `agent_reach.py`, or `BaseExecutionAdapter`. Do NOT invent new EventTypes. Do NOT implement the Do-Not-Implement list (Section 30). Do NOT add external repo loading or a sandbox.
>
> **Build in this order (Section 31):**
> 1. `src/aios/core/capability_manifest.py` — `CapabilitySpec` dataclass + `CapabilityManifestLoader` (loads `config/capabilities/*.yaml`, validates schema, enforces non-auto-trust, populates `discovered_from`).
> 2. `src/aios/adapters/adapter_factory.py` — `AdapterFactory.get_adapter(class_path, kwargs, mcp_manager)` with an **explicit allowlist** (no wildcard importlib of arbitrary paths); reject path traversal / non-allowlisted modules.
> 3. `src/aios/core/security_manager.py` — add `validate_capability_spec(spec)` (fail-closed) called at registration; analogous to existing `validate_mcp_server_before_connect` / `validate_skill_before_install`.
> 4. `src/aios/core/capability_manager.py` — extend `CapabilityRegistryEntry` (add `trust_level`, `authority_classification`, `adapter_binding`, `operations`, `health_status`, `availability`, `enabled`, `discovered_from`, `dependencies`); add `CapabilityState.DISABLED`; add `register_capability(spec)`, `disable()`, `enable()`, `deprecate()`, `set_health()`, `enforce_security_context()`, deterministic `resolve()` (trust > version > first), `initialize_capability()`. Keep `register/deregister/resolve/invoke` signatures stable.
> 5. `src/aios/core/capability_provenance.py` — `build_capability_provenance()` + `mark_capability_advisory()` (re-assert C14 `source`/`advisory`/`authority`/`trust_level` after merge — spoof-proof, mirrors adapter `_mark_advisory`).
> 6. `src/aios/core/kernel.py` — add `await self._init_capability_manifests()` boot step (after existing M8-T4 inits, before `_start_services`); import the loader/factory. **Keep all existing `_init_X()` methods** for backward compatibility.
> 7. `config/defaults.yaml` — add `kernel.capabilities` (`enabled`, `manifest_dir`, `trust_default: untrusted`, `adapter_allowlist`).
> 8. `src/aios/core/skill_manager.py` — attach provenance to skill execution results.
> 9. Add example manifests under `config/capabilities/`.
> 10–12. Implement tests (Sections 21–26), including `tests/integration/test_m8_t5_dynamic_loading.py` proving a new capability is added with **zero `kernel.py` edits** (Section 25).
> 13. Run full suite; target: existing 1,317 green + new tests green.
>
> **Definition of done:** all Acceptance Criteria (Section 28) met; dynamic-loading test required no kernel edit; full existing suite green; Verification Gate (Section 32) ready for Terminal 3.

---

### Appendix A — Measured Test Baseline

`python -m pytest --collect-only -q` → **1,317 tests collected** (exit 0; 1 pre-existing collection warning for `TestOrchestratorService`, expected, not a regression). M8-T1..T4 added 266 M8-specific tests per the per-milestone reports; the authoritative current total is **1,317 collected**.

### Appendix B — Estimated Test Delta

| Area | New tests |
|------|-----------|
| `test_capability_manifest.py` | ~15 |
| `test_adapter_factory.py` | ~12 |
| `test_capability_registry_hardening.py` | ~30 |
| `test_capability_provenance.py` | ~12 |
| `test_skill_provenance.py` | ~5 |
| `test_m8_t5_dynamic_loading.py` | ~10 |
| `test_m8_t5_security.py` | ~20 |
| **Total new** | **~104** |
| **Expected post-implementation baseline** | **~1,421 collected** (1,317 + ~104) |

Estimates are conservative and derived from the gaps enumerated in Sections 4, 11, 12, 13, 14, 15, 16. Terminal 2 may add marginally more or fewer; the binding acceptance target is "all previous 1,317 + new tests green."

### Appendix C — Key File Map

| Concern | File |
|---------|------|
| Capability registry (extend) | `src/aios/core/capability_manager.py` |
| Manifest loader (new) | `src/aios/core/capability_manifest.py` |
| Adapter factory (new) | `src/aios/adapters/adapter_factory.py` |
| Capability provenance (new) | `src/aios/core/capability_provenance.py` |
| Registration gate (extend) | `src/aios/core/security_manager.py` |
| Boot wiring (extend, additive) | `src/aios/core/kernel.py` |
| Config (extend) | `config/defaults.yaml` |
| Skill provenance (extend) | `src/aios/core/skill_manager.py` |
| Adapter base (unchanged) | `src/aios/adapters/base.py` |
| M8-T4 adapters (unchanged) | `src/aios/adapters/{notion,obsidian,claude_mem,graphify,playwright_mcp}_adapter.py` |
| MCP/ACP (unchanged) | `src/aios/core/mcp_manager.py`, `src/aios/adapters/acp_adapter.py` |
| Agencies (unchanged) | `src/aios/core/ai_agency.py` |
| Agent Reach (unchanged) | `src/aios/adapters/agent_reach.py` |
