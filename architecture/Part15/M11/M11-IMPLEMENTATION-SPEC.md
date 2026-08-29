# M11 IMPLEMENTATION SPECIFICATION

**Date:** 2026-08-27  
**Classification:** IMPLEMENTATION — Terminal 2 session  
**Authority Chain:** Parts 0–14 > Accepted ADRs > Part 15 > Implementation > Tests  
**Source Audit:** This document and repository inspection  
**Git HEAD:** 42c2017 — "verified completion of M7" + M10 implementation  
**Status:** READY FOR TERMINAL 2 IMPLEMENTATION

---

## 1. Executive Summary

M11 implements **Security Hardening (P1)** — an independent security audit and adversarial testing of the existing AI-OS system. This is a **testing and verification milestone**, not a feature milestone. M11 does not add new kernel services or autonomous authority; it validates and hardens the security boundaries already established in M7-M10.

**Terminal 2 Role:** Implementation Engineer — executes the security audit, builds adversarial tests, produces evidence artifacts.  
**Terminal 3 Role:** Independent QA — verifies methodology, reproduces findings, issues final GO/NO-GO.  
**M11 MUST NOT:** Become a new authoritative decision-maker, issue system-level PASS/FAIL, override Council/Judge, modify fundamental authority architecture, grant external integrations authority, bypass SecurityManager, convert advisory to authoritative.

---

## 2. Authoritative Scope Determination

### 2.1 M11 Scope Sources
- **M10 Implementation Report** (M10_IMPLEMENTATION_REPORT.md): M10 complete, 1293 unit tests + M7/M8/M9 integration pass
- **M8 Closure Audit §13**: "M9 = Learning/Adaptive Systems. Convergence + adaptive-replan = M10+"
- **M9 Specification §3.6**: "Convergence/adaptive-replan (M10+) explicitly out of scope"
- **Part 15 Security Chapter** (15.9-Security-and-Governance-Implementation.md): SecurityManager as integration filter, trust boundaries, provenance requirements

### 2.2 M11 Does NOT Include
- New autonomous authority (M10+ scope)
- New kernel services or core managers
- Production vault integration (out of scope per M11 authority constraints)
- Tier C real-external validation (credentials unavailable)
- M12+ features

### 2.3 M11 DOES Include
- Six authoritative security hardening areas (detailed in §3)
- Adversarial test suite with verifiable provenance
- Trust-boundary documentation
- Supply-chain vulnerability scan evidence
- All tests bounded, deterministic, and runnable in Tier B (production-style local subprocess)

---

## 3. Six Authoritative M11 Areas

### 3.1 SecurityManager Authorization-Path Audit
**Objective:** Trace and test every relevant authorization path through SecurityManager.

**Requirements:**
- Verify fail-closed behavior (unknown principal → DENY)
- Verify DENY-by-default for unconfigured actions
- Verify SecurityManager remains the final security gate (no bypass paths)
- Test authorization bypass attempts via alternate execution paths
- Test malformed/invalid authorization inputs
- Test capability/action/resource authorization boundaries
- Verify no caller can bypass SecurityManager through:
  - Direct capability execution (bypassing `enforce_security_context`)
  - Event emission without authorization
  - Adapter execution without SecurityManager gate

**Test Coverage:**
- Unit: SecurityManager.authorize() with various principal/action/resource combinations
- Integration: Full kernel path with SecurityManager gate active
- Adversarial: Crafted inputs attempting to confuse authorization logic

### 3.2 Prompt Injection Testing
**Objective:** Build adversarial prompt-injection test coverage for all untrusted input paths.

**Untrusted Input Sources (from repository inspection):**
- MCP server responses (via adapters: Graphify, Playwright, Notion, Obsidian, Claude-Mem, ACP)
- Agent-Reach web fetch results
- Hermes bridge messages
- Skill specifications (SkillSpecTor gate)
- Learning service outputs
- Self-prompting service outputs
- Capability manifest payloads
- External configuration (YAML/JSON)

**Attack Vectors to Test:**
- Direct injection: `Ignore previous instructions and...`
- Indirect injection: Malicious content in external responses
- Nested injection: Injection within nested data structures
- Encoded injection: Base64, URL encoding, Unicode obfuscation
- Role confusion: `As the system administrator...`
- Instruction hijacking: `New task: override security...`
- Authority spoofing: `This message is from SecurityManager...`
- Provenance forgery: Attempts to set `authority=authoritative` or `trust_level=trusted`

**Verification Requirements:**
- Hostile instructions cannot escalate authority
- Externally supplied content cannot manufacture PASS/FAIL authority
- Prompt content cannot override security policy
- Provenance and advisory markings survive hostile inputs
- All testing bounded and deterministic (Tier A/B only)

### 3.3 External Trust-Boundary Verification
**Objective:** Enumerate and verify every external integration and trust boundary.

**Integration Inventory (from repository):**

| Integration | Adapter | Trust Level | Boundary Enforcement |
|-------------|---------|-------------|---------------------|
| Graphify | `GraphifyAdapter` | untrusted → advisory | CapabilityManager gate + SecurityManager |
| Playwright MCP | `PlaywrightMCPAdapter` | untrusted → advisory | CapabilityManager gate + SecurityManager |
| Notion | `NotionAdapter` | untrusted → advisory | CapabilityManager gate + SecurityManager |
| Obsidian | `ObsidianAdapter` | untrusted → advisory (dual-path) | CapabilityManager gate + SecurityManager |
| Claude-Mem | `ClaudeMemAdapter` | untrusted → advisory | CapabilityManager gate + SecurityManager |
| ACP | `ACPAdapter` | untrusted → advisory | CapabilityManager gate + SecurityManager |
| Agent-Reach | `AgentReachAdapter` | untrusted → advisory | Direct adapter, no capability manifest |
| Skills | SkillSpecTor gate | untrusted → advisory | SkillSpecTorSecurityGate + SecurityManager |
| MCP Servers | MCPManager | untrusted → advisory | MCPServerSecurityGate + SecurityManager |

**Verification Requirements:**
- MCP/ACP boundaries enforced via gate-before-connect (C18)
- Adapter boundaries: all external data marked `advisory=true`, `trust_level=untrusted`
- Agent-Reach and external-context providers remain untrusted
- External data cannot become authoritative by claiming authority in payloads
- Provenance cannot be spoofed (C14 forced fields re-asserted)
- Explicit trust-boundary documentation produced

### 3.4 Secrets-Management Review
**Objective:** Audit configuration and secret-handling paths.

**Scope:**
- ConfigurationManager secret handling (`kernel.security.*` namespace)
- MCP server configuration (env vars, headers, tokens)
- Capability manifest `sensitive_keys` handling
- Skill specification secrets
- Learning service data capture
- Audit trail emission
- Test artifact generation
- Log output (StructuredLogger)

**Verification Requirements:**
- Identify plaintext-secret risks
- Verify environment/config separation
- Verify secrets not emitted via logs, provenance, errors, audit trails, test artifacts
- Test redaction behavior
- Test missing/invalid secret behavior
- Test rotation behavior (where architecture supports it)
- **Do NOT invent** production vault integration
- Document gaps where production-ready secrets capability cannot be implemented without new architectural dependency

### 3.5 Supply-Chain Security
**Objective:** Perform dependency vulnerability scanning.

**Requirements:**
- Use tools available in environment (pip-audit, safety, dependabot, etc.)
- Identify vulnerable direct/transitive dependencies
- Classify findings by severity (Critical/High/Medium/Low)
- Record exact package/version/evidence
- **Do NOT** silently upgrade dependencies just to make report green
- If remediation authorized, make smallest safe change and regression-test
- Produce reproducible scan evidence (command output, tool version, timestamp)

### 3.6 Network Security Verification
**Objective:** Audit MCP/ACP transport configuration.

**Requirements:**
- Verify encryption/secure transport requirements where applicable
- Verify insecure transport cannot silently become trusted/authoritative
- Verify network-facing configuration is fail-closed
- Test transport validation (STDIO, HTTP, SSE, WebSocket)
- Test malformed/unsupported transport configuration
- Test authentication/authorization boundaries where supported
- Clearly distinguish local mock/subprocess testing from real external network testing
- Do not claim real external service verification if services/credentials unavailable

---

## 4. Repository Inspection — Security Surface

### 4.1 Core Security Components
| Component | File | Role |
|-----------|------|------|
| SecurityManager | `src/aios/core/security_manager.py` | Final security governance authority |
| SkillSpecTorGate | `src/aios/core/security_manager.py:195` | M4 skill validation gate (LLM disabled per C10) |
| MCPServerSecurityGate | `src/aios/core/security_manager.py:571` | M5 gate-before-connect (C18) |
| CapabilitySpec Gate | `src/aios/core/security_manager.py:1530` | M8-T5 capability registration gate |
| SecurityAbacExt | `src/aios/services/security_abac_ext.py` | M10-N8 ABAC for autonomous ops |

### 4.2 Security Agency Adapter
| Component | File | Role |
|-----------|------|------|
| SecurityAgencyAdapter | `src/aios/adapters/security_agency_adapter.py` | M7 real security execution (static analysis + SecurityManager auth) |

### 4.3 External Adapters (All Untrusted → Advisory)
| Adapter | File | Manifest |
|---------|------|----------|
| GraphifyAdapter | `src/aios/adapters/graphify_adapter.py` | config/capabilities/graphify.yaml |
| PlaywrightMCPAdapter | `src/aios/adapters/playwright_mcp_adapter.py` | config/capabilities/playwright-mcp.yaml |
| NotionAdapter | `src/aios/adapters/notion_adapter.py` | config/capabilities/notion.yaml |
| ObsidianAdapter | `src/aios/adapters/obsidian_adapter.py` | config/capabilities/obsidian.yaml |
| ClaudeMemAdapter | `src/aios/adapters/claude_mem_adapter.py` | config/capabilities/claude-mem.yaml |
| ACPAdapter | `src/aios/adapters/acp_adapter.py` | config/capabilities/acp.yaml |
| AgentReachAdapter | `src/aios/adapters/agent_reach.py` | No manifest (direct adapter) |

### 4.4 Security-Relevant Events
- `EventType.SECURITY_ISSUE_FOUND` — only canonical security event emitted
- `EventType.MCP_SERVER_VALIDATION_FAILED` — MCP gate failure
- Other Part 4 §4.7.10 events **omitted** per CONFLICT E.1

### 4.5 Configuration Security Surface
```yaml
# config/defaults.yaml
kernel:
  security:
    strict_mode: true
    allowed_services: []
    failClosed: true        # Read by SecurityManager
    auditAllDenials: true   # Read by SecurityManager
    denyUnknownPrincipal: true  # Read by SecurityManager

capabilities:
  trust_default: "untrusted"
  adapter_allowlist: [...]  # Enforced by CapabilityManager

services:
  security_abac_ext:
    enabled: true
    require_signature: true
```

---

## 5. Freeze Boundary Analysis

### 5.1 M7 Freeze (Inviolable)
- TestingEvidence schema — **no modifications**
- 9 AIAgencyService adapter semantics — **no modifications**
- CouncilManager/Final Judge authority — **sole decision authority preserved**
- TestOrchestratorService — **exercises but does not override**

### 5.2 M8 Boundary (Preserved)
- Advisory Learning Model — learnings remain advisory input only
- SecurityManager Enforcement — remains INTEGRATION FILTER
- WorkflowManager — executes plans, does not initiate autonomously
- StateManager — source of truth for verified state
- External adapters — unchanged (Notion, Obsidian, Graphify, Claude-Mem)

### 5.3 M9 Boundary (Honored)
- Convergence Detection — bounded/advisory only
- Learning Output — never sets `authority=authoritative` or `trust_level=trusted`
- Self-Prompting — ADR #10 bounds enforced (max_depth=5)
- Remediation — proposer returns suggestions only

### 5.4 M10 Boundary (Respected)
- Autonomous services — config-gated behind `services.autonomy.enabled: false`
- AutonomousFinalJudge — defers to Council when `defer_to_council: true`
- SecurityAbacExt — wraps SecurityManager, does not modify core logic
- All M10 provenance — `autonomous=true`, `authority_level` in {advisory, autonomous, privileged}

---

## 6. Gap Analysis (P0-P3 Severity)

### 6.1 P0 (Blocking) — Must Close for M11 GO
| ID | Gap | Current State | Required |
|----|-----|---------------|----------|
| GAP-M11-01 | No SecurityManager authorization-path test coverage | Unit tests exist but no adversarial bypass attempts | Full path trace + bypass tests |
| GAP-M11-02 | No prompt injection test suite | Zero adversarial prompt tests | Comprehensive injection vectors |
| GAP-M11-03 | Trust boundaries not explicitly documented | Implicit in code, no explicit doc | Trust-boundary registry document |
| GAP-M11-04 | No supply-chain vulnerability scan in CI | Not automated | Reproducible scan evidence |
| GAP-M11-05 | Network transport security not verified | Config accepts any transport | Fail-closed transport validation tests |

### 6.2 P1 (Major) — Should Close
| ID | Gap | Current State |
|----|-----|---------------|
| GAP-M11-06 | Secret leakage paths not fully audited | Partial review in M8-T6 |
| GAP-M11-07 | No redaction test for StructuredLogger | Not tested |
| GAP-M11-08 | MCPServerSecurityGate not adversarially tested | Unit tests only |

### 6.3 P2 (Moderate) — Document/Track
| ID | Gap | Current State |
|----|-----|---------------|
| GAP-M11-09 | No dependency rotation test | Not applicable (no vault) |
| GAP-M11-10 | No WebSocket transport security test | Accepted but not verified |

### 6.4 P3 (Minor) — Nice to Have
| ID | Gap | Current State |
|----|-----|---------------|
| GAP-M11-11 | Security test categorization | Inconsistent naming |

---

## 7. Task Decomposition (M11-T#)

### M11-T1 — SecurityManager Authorization Audit & Adversarial Tests
- Create `tests/security/test_m11_auth_path.py`
- Test all authorization paths: unknown principal, malformed inputs, boundary values
- Test bypass attempts: direct capability execution, event emission without auth, adapter bypass
- Verify fail-closed: all paths through SecurityManager gates
- **Deliverable:** Test file with 15+ test cases, all passing

### M11-T2 — Prompt Injection Test Suite
- Create `tests/security/test_m11_prompt_injection.py`
- Inject adversarial payloads into all untrusted input paths
- Vectors: direct, indirect, nested, encoded, role-confusion, instruction-hijacking, authority-spoofing
- Verify: authority cannot escalate, PASS/FAIL cannot be manufactured, policy cannot be overridden, provenance survives
- **Deliverable:** Test file with 25+ test cases, all bounded/deterministic

### M11-T3 — External Trust-Boundary Verification & Documentation
- Create `tests/security/test_m11_trust_boundary.py`
- Enumerate all external integrations from capability manifests + adapters
- Verify each: advisory marking, trust level, provenance re-assertion
- Produce `architecture/Part15/M11/TRUST_BOUNDARY_REGISTRY.md`
- **Deliverable:** Test file + registry document

### M11-T4 — Secrets-Management Audit
- Create `tests/security/test_m11_secrets.py`
- Audit config paths, secret handling, emission paths
- Test redaction in StructuredLogger, provenance, errors, audit trails
- Test missing/invalid secret behavior
- Document gaps (no vault integration)
- **Deliverable:** Test file + `SECRETS_AUDIT_REPORT.md`

### M11-T5 — Supply-Chain Vulnerability Scan
- Create `tests/security/test_m11_supply_chain.py`
- Run pip-audit/safety on requirements
- Record findings with package/version/evidence
- Classify by severity
- **Do not** auto-upgrade
- **Deliverable:** Test file + `SUPPLY_CHAIN_SCAN_REPORT.md` with reproducible evidence

### M11-T6 — Network Security Verification
- Create `tests/security/test_m11_network.py`
- Test MCP/ACP transport validation (STDIO, HTTP, SSE, WebSocket)
- Test fail-closed on malformed config
- Test auth boundaries
- Distinguish local mock vs real external
- **Deliverable:** Test file + `NETWORK_SECURITY_REPORT.md`

---

## 8. Test Strategy

### 8.1 Tier Classification
- **Tier A — In-Process Mock**: Authorization logic, injection validation, provenance marking
- **Tier B — Production-Style Local Subprocess**: Full kernel boot with security gates, no live externals
- **Tier C — Real External Service**: NOT achievable (no credentials/instances)

### 8.2 Required Test Categories
1. **Unit** — Authorization logic, injection sanitization, provenance marking, secret redaction
2. **Integration** — Kernel bootstrap with security gates, capability registration flow, MCP connection flow
3. **Production-Style Subprocess** — Full kernel with all security gates active against in-tree mocks
4. **Adversarial** — Bypass attempts, injection vectors, authority spoofing, provenance forgery
5. **Provenance** — Advisory preservation, trust-level non-escalation, C14 field re-assertion
6. **Regression** — Full existing suite (1293+ tests) remains green
7. **M7/M8/M9/M10 Freeze** — No modifications to frozen files; compatibility preserved

### 8.3 Provenance Requirements for M11 Security Evidence
All M11 security test activities MUST carry verifiable provenance:
- Source (test file, test function)
- Worker/agent (Terminal 2 implementation)
- Session (test run ID)
- Timestamp (ISO 8601)
- Environment (Python version, OS, key dependency versions)
- Correlation ID (unique per test run)
- Test-vs-production classification (explicit Tier A/B)
- Finding identifier (GAP-M11-XX)
- Severity (P0-P3)
- Affected component (file:line)
- Evidence location (test file, log output, scan artifact)

---

## 9. Failure / Recovery Model

### 9.1 Security Test Failure Modes
| Failure | Detection | Response |
|---------|-----------|----------|
| Authorization bypass found | Adversarial test passes (should fail) | Document as CRITICAL finding, block GO |
| Prompt injection succeeds | Authority escalation detected | Document as HIGH finding, mandate fix |
| Trust boundary violated | Advisory→authoritative transition | Document as HIGH finding |
| Secret leaked in test output | Redaction test fails | Document as MEDIUM, fix redaction |
| Vulnerable dependency found | Scan reports CVE | Document severity, track remediation |
| Transport insecure | Config allows unsafe transport | Document, enforce fail-closed |

### 9.2 Recovery Path Preservation
- M7/M8/M9/M10 recovery paths **unchanged**
- M11 tests are **read-only verification** — they do not modify system state
- Security findings are **advisory** until accepted through existing governance

---

## 10. Authority Model for M11

### 10.1 M11 Authority
- **MAY:** Decide audit methodology, design adversarial tests, classify vulnerabilities, prioritize findings, execute bounded tests, recommend mitigations
- **MUST NOT:** Issue final PASS/FAIL, override Council/Judge, modify authority architecture, grant external authority, bypass SecurityManager, convert advisory to authoritative

### 10.2 Final Authority
- **Terminal 3 (Independent QA)** — issues GO/NO-GO based on reproduced evidence
- **Council/Judge** — retains sole decision authority for system operations
- **SecurityManager** — remains final security gate for all operations

---

## 11. Production-Path Honesty

### 11.1 Tier Classification Mapping
| Feature | Implemented | Tested | Production Path | Notes |
|---------|-------------|--------|-----------------|-------|
| Auth path audit | Planned | Tier A/B | Tier B | No Tier C |
| Prompt injection | Planned | Tier A/B | Tier B | Bounded vectors |
| Trust boundary doc | Planned | Tier A | Tier A | Documentation only |
| Secrets audit | Planned | Tier A/B | Tier B | No vault integration |
| Supply-chain scan | Planned | Tier A | Tier A | Tool output evidence |
| Network security | Planned | Tier A/B | Tier B | Local mock only |

### 11.2 Limitations
- No Tier C claims for any M11 area
- No production vault integration (architectural dependency not present)
- No real external service validation (credentials unavailable)
- All adversarial tests bounded and deterministic

---

## 12. Terminal 2 & Terminal 3 Handoff

### 12.1 Terminal 2 Handoff (Implementation)
- Implement M11-T1 through M11-T6 in order
- Preserve M7/M8/M9/M10 freeze boundaries
- Do not modify frozen files
- Run full regression before handoff
- Produce all deliverables listed in §7
- **Do not self-certify** — Terminal 3 issues GO/NO-GO

### 12.2 Terminal 3 Handoff (Independent QA)
- Verify source implementation: read all M11 test files
- Reproduce production-style subprocess validation
- Security boundaries: adversarial tests assert rejection
- Provenance: all evidence carries required fields
- Regression: full suite 0 failed
- Freeze: git status shows no M7/M8/M9/M10 file modifications
- **Terminal 3 issues Final GO/NO-GO**

### 12.3 Acceptance Criteria
M11 is COMPLETE when ALL are true:
1. **Authorization Audit**: 15+ tests covering all SecurityManager paths + bypass attempts; all pass
2. **Prompt Injection**: 25+ adversarial vectors tested; all blocked; provenance preserved
3. **Trust Boundaries**: Registry document complete; all integrations verified advisory/untrusted
4. **Secrets Audit**: Report complete; no secret leakage in logs/provenance/errors; gaps documented
5. **Supply Chain**: Scan executed; reproducible evidence; findings classified; no silent upgrades
6. **Network Security**: Transport validation tests pass; fail-closed verified; local-only documented
7. **Regression Green**: Full suite (1293+ unit + M7/M8/M9/M10 integration) 0 failed
8. **Freeze Preserved**: No M7/M8/M9/M10 file modifications
9. **No Tier C Claims**: Explicitly documented
10. **Advisory Findings**: All M11 findings remain advisory until governance acceptance

---

## 13. P0/P1 No-Go Criteria

### 13.1 P0 (Hard No-Go)
| ID | Violation | Rationale |
|----|-----------|-----------|
| NOGO-M11-P0-01 | M7/M8/M9/M10 file modified | Freeze boundaries inviolable |
| NOGO-M11-P0-02 | SecurityManager bypass demonstrated | Final gate compromised |
| NOGO-M11-P0-03 | Advisory→authoritative transition possible | Trust boundary broken |
| NOGO-M11-P0-04 | Secret leaked in test artifacts | Secret handling broken |
| NOGO-M11-P0-05 | Tier C claimed without evidence | Production-path dishonesty |
| NOGO-M11-P0-06 | Test fixtures mask production defects | IND-6 lesson violated |

### 13.2 P1 (No-Go)
| ID | Violation |
|----|-----------|
| NOGO-M11-P1-01 | GAP-M11-01 through GAP-M11-05 not closed |
| NOGO-M11-P1-02 | Full suite has new failures |
| NOGO-M11-P1-03 | Prompt injection vectors not comprehensively covered |
| NOGO-M11-P1-04 | Trust boundary registry incomplete |

---

## 14. Deliverable Format

### 14.1 File Locations
```
architecture/Part15/M11/
├── M11-IMPLEMENTATION-SPEC.md (this file)
├── TRUST_BOUNDARY_REGISTRY.md
├── SECRETS_AUDIT_REPORT.md
├── SUPPLY_CHAIN_SCAN_REPORT.md
├── NETWORK_SECURITY_REPORT.md
```

### 14.2 Test Files
```
tests/security/
├── test_m11_auth_path.py
├── test_m11_prompt_injection.py
├── test_m11_trust_boundary.py
├── test_m11_secrets.py
├── test_m11_supply_chain.py
├── test_m11_network.py
```

### 14.3 Verification Artifacts
Terminal 2 must produce for Terminal 3:
- All 6 test files with passing tests
- 4 report documents
- Reproduction log: `python -m pytest tests/security/test_m11_*.py` → 0 failed
- Full regression: `python -m pytest` → 0 failed (1293+ tests)
- `git status` + `git diff --stat` proving freeze preserved
- All evidence carries required provenance fields

---

## 15. Style Guide
- Follows Part 14 documentation style with 8-status taxonomy
- Uses explicit contradiction documentation
- Grounds all claims in source truth with file:line references
- Preserves architecture fidelity; no invention
- Documents all limitations and pre-existing issues

---

*End of M11 Implementation Specification. Authority: M10 Implementation Report + M8 Closure Audit §13 + M9 Specification §3.6 + Part 15 Chapter 15.9 + repository source verification (2026-08-27).*