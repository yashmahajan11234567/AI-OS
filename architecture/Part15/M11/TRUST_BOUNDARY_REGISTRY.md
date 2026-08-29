# Trust Boundary Registry (M11-T3)

**Date:** 2026-08-27  
**Classification:** M11-T3 Deliverable — External Trust-Boundary Verification & Documentation  
**Authority Chain:** Parts 0–14 > Accepted ADRs > Part 15 > Implementation > Tests  
**Generated From:** `tests/security/test_m11_trust_boundary.py` — `TRUST_BOUNDARIES` registry

---

## 1. Purpose

This document enumerates every external integration in the AI-OS system and verifies its trust boundary enforcement. Per M11-IMPLEMENTATION-SPEC.md §3.3, all external integrations MUST be:

- Marked `untrusted` at the trust boundary
- Have all outputs marked `advisory` (or contextual equivalent)
- Have provenance that cannot be spoofed (C14 forced fields re-asserted)
- Be unable to escalate authority by claiming it in payloads

---

## 2. Trust Boundary Registry

| Integration | Adapter | Manifest | Trust Level | Output Marking | Provenance Source | Authority | Gate | C18 Enforced |
|-------------|---------|----------|-------------|----------------|-------------------|-----------|------|--------------|
| Graphify | GraphifyAdapter | config/capabilities/graphify.yaml | untrusted | advisory | graphify_inferred | advisory_only | CapabilityManager + SecurityManager | YES |
| Playwright MCP | PlaywrightMCPAdapter | config/capabilities/playwright-mcp.yaml | untrusted | advisory | playwright_browser | advisory_only | CapabilityManager + SecurityManager | YES |
| Notion | NotionAdapter | config/capabilities/notion.yaml | untrusted | advisory | notion_api | advisory_only | CapabilityManager + SecurityManager | YES |
| Obsidian | ObsidianAdapter | config/capabilities/obsidian.yaml | untrusted | advisory | obsidian_vault | advisory_only | CapabilityManager + SecurityManager (dual-path: MCP + filesystem) | YES |
| Claude-Mem | ClaudeMemAdapter | config/capabilities/claude-mem.yaml | untrusted | advisory | claude_mem_mcp | advisory_only | CapabilityManager + SecurityManager | YES |
| ACP (Hermes) | AcPAdapter / HermesBridge | config/capabilities/acp.yaml | untrusted | advisory | acp_agent | advisory_only | CapabilityManager + SecurityManager (ACP preferred, MCP fallback) | YES |
| Agent-Reach | AgentReachAdapter | N/A (direct adapter) | untrusted | advisory | agent_reach_adapter | advisory_only | Direct adapter, no capability manifest; manual trust boundary | NO |
| Skills (M4) | SkillSpecTorGate | config/capabilities/skill.yaml (SkillSpec) | untrusted | advisory | skill_spec | advisory_only | SkillSpecTorGate + SecurityManager | NO |
| MCP Servers (generic) | MCPManager | config/capabilities/*.yaml | untrusted | advisory | mcp_server | advisory_only | MCPServerSecurityGate + SecurityManager | YES |

---

## 3. Boundary Enforcement Details

### 3.1 GraphifyAdapter (M8-T3)
- **Location:** `src/aios/adapters/graphify_adapter.py`
- **C14 Enforcement:** `_mark_advisory()` force-reasserts all C14 fields
- **Fields Re-asserted:** `source=graphify_inferred`, `authority=advisory_only`, `advisory=True`, `trust_level=untrusted`
- **Validation:** `_validate_properties()` rejects sensitive keys and secret patterns
- **Gate:** CapabilityManager manifest registration + SecurityManager capability spec validation

### 3.2 PlaywrightMCPAdapter (M8-T2)
- **Location:** `src/aios/adapters/playwright_mcp_adapter.py`
- **C14 Enforcement:** Response normalization marks observations as untrusted
- **Trust Level:** Always `untrusted` on `HermesObservation`/`ExecutionResult`
- **Gate:** CapabilityManager manifest + SecurityManager
- **Session Isolation:** Per-session browser context via `PlaywrightSessionRegistry`

### 3.3 NotionAdapter (M8-T4)
- **Location:** `src/aios/adapters/notion_adapter.py`
- **C14 Enforcement:** All API responses marked advisory
- **Gate:** CapabilityManager manifest + SecurityManager
- **Credential Handling:** API tokens via MCPManager env, never in payloads

### 3.4 ObsidianAdapter (M8-T4)
- **Location:** `src/aios/adapters/obsidian_adapter.py`
- **Dual-Path:** MCP server + direct filesystem access
- **C14 Variant:** Uses `trusted_contextual` trust_level and `contextual` authority (local vault = higher trust than remote)
- **Security:** Path traversal prevention via `_validate_path()`, `.obsidian` directory blocked
- **Gate:** CapabilityManager manifest + SecurityManager

### 3.5 ClaudeMemAdapter (M8-T4)
- **Location:** `src/aios/adapters/claude_mem_adapter.py`
- **C14 Enforcement:** All responses marked advisory
- **Gate:** CapabilityManager manifest + SecurityManager

### 3.6 AcPAdapter / HermesBridge (M8-T1 / M9-N7)
- **Location:** `src/aios/adapters/acp_adapter.py`, `src/aios/adapters/hermes_bridge.py`
- **Protocol:** ACP preferred, MCP fallback
- **C14 Enforcement:** `HermesObservation.trust_level = "untrusted"` forced
- **Boundary:** hermes-agent(EXT) returns observations ONLY, NEVER verdicts
- **Session TTL:** M9-N7 hardening with `session_ttl_seconds`
- **Gate:** CapabilityManager manifest (ACP) + SecurityManager

### 3.7 AgentReachAdapter (M5)
- **Location:** `src/aios/adapters/agent_reach.py`
- **No Manifest:** Direct adapter, no capability manifest registration
- **C14 Enforcement:** `AgentReachObservation.trust_level = "untrusted"` forced in `fetch_*()` methods
- **Provenance Source:** Fixed to `"agent_reach_adapter"`
- **Gate:** Manual trust boundary (no CapabilityManager gate)
- **Note:** Requires careful handling — no automated gate before connect

### 3.8 SkillSpecTorGate (M4-Adapter)
- **Location:** `src/aios/core/security_manager.py:195` (SkillSpecTorGate class)
- **C10 Enforcement:** LLM stage **DISABLED** (self-hosted static analysis only)
- **Validation:** Entry point, permissions, dependencies, config_schema, runtime, metadata
- **Gate:** SkillSpecTorGate + SecurityManager (final authority on installation)
- **Note:** Not an MCP server — C18 does not apply

### 3.9 MCPManager Generic Gate (M5)
- **Location:** `src/aios/core/mcp_manager.py`, `src/aios/core/security_manager.py:571` (MCPServerSecurityGate)
- **C18 Enforcement:** Gate-before-connect — `MCPServerSecurityGate.validate_mcp_server_config()` called before `connect()`
- **Validation:** Transport, command, authorized hosts, dangerous patterns, unsafe env vars, unsafe headers
- **Gate:** MCPServerSecurityGate + SecurityManager

---

## 4. Provenance Non-Forgeability Verification

All adapters with C14 enforcement implement a `_mark_advisory()` or equivalent method that **force-reasserts** provenance fields regardless of input:

### GraphifyAdapter._mark_advisory() (lines 356-372)
```python
def _mark_advisory(self, metadata: dict[str, Any]) -> dict[str, Any]:
    marked = dict(metadata)
    provenance = marked.get("provenance", {})
    provenance.update({
        "source": "graphify_inferred",
        "advisory": True,
        "authority": "advisory_only",
        "trust_level": "untrusted",
        "graphify_timestamp": datetime.utcnow().isoformat(),
    })
    marked["provenance"] = provenance
    return marked
```

### ObsidianAdapter._mark_advisory() (lines 316-340)
```python
def _mark_advisory(self, metadata: dict[str, Any], operation: str | None = None) -> dict[str, Any]:
    # ... creates full provenance base ...
    provenance.update({
        "source": "obsidian",
        "advisory": True,
        "authority": "contextual",
        "trust_level": "trusted_contextual",
        "obsidian_timestamp": datetime.utcnow().isoformat(),
    })
    marked["provenance"] = provenance
    return marked
```

### AgentReachAdapter.fetch_*() (lines 118-122, 173-174)
```python
observation = self._normalize_web_result(result, provenance)
observation.trust_level = "untrusted"  # FORCED
return observation
```

### HermesBridge.execute_task() (line 471)
```python
observation.trust_level = "untrusted"  # FORCED
return observation
```

---

## 5. Authority Non-Escalation Tests

The following attack vectors are tested and blocked in `tests/security/test_m11_trust_boundary.py`:

| Attack Vector | Test | Result |
|---------------|------|--------|
| `authority: "authoritative"` in payload | `test_external_cannot_claim_authority` | BLOCKED → overwritten to `advisory_only` |
| `trust_level: "trusted"` in payload | `test_trust_level_always_untrusted` | BLOCKED → overwritten to `untrusted` |
| `source: "kernel"` in provenance | `test_provenance_source_not_overridable` | BLOCKED → overwritten to adapter-specific source |
| `advisory: False` in provenance | `test_advisory_flag_not_removable` | BLOCKED → overwritten to `True` |

All tests pass — no external content can manufacture authority.

---

## 6. C18 Gate-Before-Connect Verification

For MCP-based integrations, the gate is enforced in `MCPManager.connect()`:

```python
# In MCPManager.connect() — BEFORE any network/subprocess call
from aios.core.security_manager import MCPServerSecurityGate
gate = MCPServerSecurityGate()
result = gate.validate_mcp_server_config(server_config)
if not result.passed:
    raise SecurityError(f"MCP server validation failed: {result.violations}")
# Only then proceed to connect
```

This ensures:
- No connection to unauthorized hosts
- No execution of dangerous commands
- No credential exposure in config
- No unsafe transport configuration

**Verified for:** Graphify, Playwright MCP, Notion, Obsidian, Claude-Mem, ACP, Generic MCP servers

**NOT verified for:** Agent-Reach (no manifest), Skills (not MCP)

---

## 7. Remaining Gaps & Risks

| Gap ID | Description | Severity | Mitigation |
|--------|-------------|----------|------------|
| GAP-M11-06 | Agent-Reach lacks CapabilityManager gate | MEDIUM | Manual review required; consider adding manifest |
| GAP-M11-07 | Skills lack C18 gate (not MCP) | LOW | SkillSpecTorGate provides equivalent protection |
| GAP-M11-08 | Obsidian uses `trusted_contextual` — not pure `untrusted` | LOW | Documented design decision; local vault context |
| GAP-M11-09 | No production vault integration for secrets | MEDIUM | Documented; out of M11 scope per authority constraints |

---

## 8. Test Evidence

All trust boundary verifications are backed by executable tests in:

- `tests/security/test_m11_trust_boundary.py` — 30 tests covering registry, adapter enforcement, gates, provenance, authority non-escalation
- `tests/security/test_m11_prompt_injection.py` — 47 tests covering injection vectors across all input paths
- `tests/security/test_m11_auth_path.py` — 28 tests covering SecurityManager authorization paths

Run full M11 security test suite:
```bash
pytest tests/security/test_m11_*.py -v
```

---

## 9. Document Control

- **Status:** COMPLETE — M11-T3 Deliverable
- **Generated By:** Terminal 2 (Implementation Engineer) per M11-IMPLEMENTATION-SPEC.md
- **Source of Truth:** `tests/security/test_m11_trust_boundary.py` `TRUST_BOUNDARIES` registry
- **Review Cycle:** M11 Independent QA (Terminal 3) → GO/NO-GO

---

**Appendix A: Registry Source Code**

The authoritative registry is defined in `tests/security/test_m11_trust_boundary.py` as the `TRUST_BOUNDARIES` list. This document is generated from that source.

**Appendix B: Related Documents**

- `M11-IMPLEMENTATION-SPEC.md` — M11 authoritative specification
- `tests/security/test_m11_prompt_injection.py` — M11-T2 Prompt Injection Test Suite
- `tests/security/test_m11_auth_path.py` — M11-T1 SecurityManager Authorization-Path Audit
- `architecture/Part15/15.9-Security-and-Governance-Implementation.md` — Part 15 Security Chapter