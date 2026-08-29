# FINAL EXTERNAL ECOSYSTEM INTEGRATION SPECIFICATION

**AI-OS · Final External Ecosystem Integration Specification**
**Date:** 2026-08-27
**Author:** Terminal 1 — Architecture/Planning Authority
**Status:** READY FOR IMPLEMENTATION

## 1. INTRODUCTION

This document specifies the real external ecosystem integration for AI-OS Hermes Kernel v1.0.0, defining how AI-OS interacts with external systems while maintaining its role as the sole governance/verification/decision/final authority.

AI-OS = ONLY governance / verification / decision / final authority.
Everything external is subordinate to AI-OS authority.

## 2. CORE PRINCIPLES

### 2.1 Authority Invariance
- AI-OS retains final authority in all interactions
- External systems can only provide advisory/contextual information
- No external component may become governance/security/verification/completion authority
- AI-OS CouncilManager / FinalJudge / verification architecture remains authoritative

### 2.2 Execution Model
- All external execution occurs via explicitly bounded AI-OS controls
- External workers/sessions/agents operate under AI-OS supervision
- Provenance tracking is mandatory for all external interactions
- Security gates validate all external connections before establishment

### 2.3 Integration Mechanism
- Reuse existing architecture mechanisms (BaseExecutionAdapter, CapabilityManager, etc.)
- Do not introduce new manager/parallel architectures unnecessarily
- Follow extensibility requirements from existing architecture
- MCP/ACP as primary transport mechanisms where applicable

## 3. INTEGRATION CATEGORIES

### 3.1 EXECUTION
- **Hermes/ACP**: Real worker execution via ACP preferred, MCP fallback
- **Playwright MCP**: Real browser automation via @playwright/mcp
- **MCP**: Standard MCP protocol for external tool integration
- **Agent Reach**: Agent communication protocol
- **SkillSpecTor**: Skill specification and execution framework

### 3.2 KNOWLEDGE
- **Obsidian**: Local knowledge vault (filesystem primary, MCP secondary)
- **Graphify**: Derived/indexed/knowledge graph layer (never authoritative)
- **Claude-Mem**: Contextual memory retrieval (advisory only)

### 3.3 PLANNING
- **Notion**: Project planning and tracking (advisory only)
- **GSD Core**: Getting Things Done methodology integration

### 3.4 MODEL INFRASTRUCTURE
- **FreeLLMAPI**: Local LLM provider (dev/test only, not for production)
- **Existing Model Providers**: Anthropic, OpenAI, etc. via ModelRouter

### 3.5 COUNCIL / REVIEW
- **LLM Council**: Technique/perspective source only
- **Review Council**: Technique/perspective source only
- **Karpathy LLM Council**: Technique/perspective source only
- **Council Review**: Technique/perspective source only

### 3.6 REFERENCE / TECHNIQUE REPOSITORIES
Treated as technique sources only - code may be imported/adapted but repositories remain external:
- Ruflo, Superpowers, Everything Claude Code, Loop Engineering, Caveman, ego-lite
- Anthropic frontend-design, Claude Code Frontend Design Toolkit
- Public APIs/research sources (public-apis, Agent Reach research)

## 4. SECURITY CONSIDERATIONS

All integrations must enforce:
- SecurityManager gate validation before connection
- Secret redaction across evidence/errors
- No bypass of validate_mcp_server_before_connect
- Proper working directory validation for subprocesses
- Environment scrubbing for external processes
- Capability double-registration prevention

## 5. IMPLEMENTATION APPROACH

### 5.1 Phased Rollout
1. Security gate remediation (S1-S3)
2. Configuration framework preparation
3. Real MCP/ACP connectivity establishment
4. Individual integration activation
5. Cross-integration E2E testing
6. Real operational verification

### 5.2 Testing Strategy
- Gated external tests (@pytest.mark.gated + env-gated)
- Never expose credentials or persist secrets
- Record provenance and version information
- Distinguish real vs mock execution clearly
- Fail closed - never alter authoritative state unexpectedly

## 6. AUTHORSHIP & PROVENANCE

All external integrations must provide:
- Source, worker, session, execution_id, correlation_id
- Timestamp, environment, protocol, integration, operation
- Trust level, authority designation, advisory flags where required
- Evidence/artifact references for all external data

## 7. ACCEPTANCE CRITERIA

A. All required security gates enforced
B. All intended integrations configurable via existing mechanisms
C. Real endpoints used where required (ժ not mocks)
D. Credentials never leaked in logs/errors/evidence
E. Real connectivity verified via operational tests
F. Real operation verified for each integration
G. Provenance complete for all external interactions
H. External data remains advisory/contextual only
I. No external authority escalation
J. Mock and real modes clearly separated
K. Normal regression remains green
L. Gated external tests pass
M. Cross-integration E2E passes
N. Failure/degraded paths pass
O. No frozen architecture violations
P. Final AI-OS authority remains intact

---
*This specification is grounded in repository evidence and represents the planned state for Terminal 2 implementation.*