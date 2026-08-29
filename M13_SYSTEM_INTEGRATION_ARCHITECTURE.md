# M13 System Integration Architecture

## Overview

This document defines the system-wide integration architecture for AI-OS M13, integrating Supabase, n8n, Obsidian Git, AI-OS Dashboard, and existing external ecosystem components into the complete AI-OS lifecycle while preserving AI-OS as the sole authoritative governance, verification, and decision-making authority.

## Core Architectural Principles

### Authority Model
AI-OS remains the sole:
- Governance authority
- Verification authority  
- Final judgment authority
- Decision-making authority
- Workflow controller

External systems are bounded resources that AI-OS directs and evaluates, never allowing them to become parallel autonomous systems or decision authorities.

### Integration Patterns
All external integrations follow these patterns:
1. **AI-OS → External System**: AI-OS initiates actions and provides bounded parameters
2. **External System → AI-OS**: External systems return results, status, errors, and artifacts
3. **AI-OS Evaluation**: AI-OS evaluates results and determines next actions
4. **No External Decision Making**: External systems never decide AI-OS next actions

### Lifecycle Preservation
The complete AI-OS lifecycle remains intact:
USER INTENT → PLANNING → RESEARCH → REQUIREMENTS → COUNCILS/REVIEWS → PLAN → TASKS → SELF-PROMPT → BOUNDED EXECUTION → TEST → REVIEW → VERIFICATION → FINAL JUDGMENT → DECISION → EVIDENCE → LEARNING → MEMORY/KNOWLEDGE → PERSISTENCE → NEXT SELF-PROMPT → NEXT ITERATION

## Component Responsibilities

### AI-OS Kernel (HermesKernel)
- Central orchestrator managing all core components
- Maintains authoritative EventBus (C1) and ServiceRegistry (C2)
- Owns lifecycle management through LifecycleManager
- Coordinates all engineering services and core managers
- Preserves single authoritative autonomous/self-loop

### Core Managers (C1-C4 + Managers)
- EventBus: Canonical event propagation (single source of truth)
- ServiceRegistry: Service discovery and registration (single source of truth)
- ConfigurationManager: Frozen configuration at runtime
- StructuredLogger: Unified logging infrastructure
- StateManager: Workflow and application state persistence
- WorkflowManager: DAG-based workflow orchestration
- ResourceManager: Quota enforcement and resource tracking
- HealthManager: System health monitoring
- SecurityManager: Authorization and security policy enforcement
- CapabilityManager: Capability registration and routing (single registry)
- ObservabilityManager: Metrics and tracing

### External Integrations as Bounded Resources

#### Supabase
- Role: Persistent storage backend for AI-OS owned data
- Authority: AI-OS owns semantic meaning even when data physically stored in Supabase
- Pattern: AI-OS → Supabase (NOT Supabase → AI-OS authority)
- Governance: AI-OS remains FinalJudge, verification authority, and decision-maker

#### n8n
- Role: Bounded automation/execution resource
- Authority: AI-OS decides "Execute workflow X", n8n executes and returns results
- Pattern: Strict AI-OS → n8n communication with AI-OS → n8n callback/event path
- Governance: n8n never decides next AI-OS action

#### Obsidian + Obsidian Git
- Role: Knowledge/durability layer with actual durability guarantees
- Authority: AI-OS writes to Obsidian via adapter; Git records actual changes
- Pattern: AI-OS → ObsidianAdapter → Obsidian Vault → Obsidian Git → Git repo → Remote
- Governance: Real durability guarantee based on actual implementation, not claims

#### AI-OS Dashboard
- Role: UI over AI-OS (read-only, user approval, AIOS authorized actions)
- Authority: Never becomes another governance layer
- Pages: Planning Chat, Resource/Integration Onboarding, Project/Execution, Knowledge/History, System/Health

#### Existing Ecosystem
All existing integrations (Hermes/ACP, Hermes/MCP, Playwright, MCP, Agent Reach, FreeLLMAPI, Notion, Obsidian, Graphify, Claude-Mem) remain as bounded resources with clearly defined authority levels.

## Implementation Approach

### No Parallel Architectures
- No parallel kernel
- No parallel governance
- No parallel autonomous loop
- No external decision authority
- No verification bypass
- No SecurityManager bypass
- No FinalJudge bypass
- No hidden state
- No uncontrolled event loop
- No fabricated resources
- No fake operational status
- No unnecessary managers

### Extension Over Replacement
All M13 work extends existing M0-M12 architecture rather than replacing or weakening frozen components (M0-M7).

### Verification-Based Truth
Where documentation and code disagree: CODE + VERIFIED TESTS = implementation truth.

## Deliverables

This document is part of the M13 planning deliverables:
1. M13_SYSTEM_INTEGRATION_ARCHITECTURE.md (this document)
2. M13_SUPABASE_INTEGRATION_SPEC.md
3. M13_N8N_INTEGRATION_SPEC.md
4. M13_OBSIDIAN_GIT_DURABILITY_SPEC.md
5. M13_SELF_LOOP_INTEGRATION_SPEC.md
6. M13_SELF_PROMPT_INTEGRATION_SPEC.md
7. M13_DASHBOARD_ARCHITECTURE.md
8. M13_FAILURE_RECOVERY_SPEC.md
9. M13_SECURITY_ARCHITECTURE.md
10. M13_UPDATED_ECOSYSTEM_MATRIX.md
11. M13_IMPLEMENTATION_TASKS.md
12. M13_TEST_AND_ACCEPTANCE_SPEC.md
13. M13_USER_RESOURCE_CHECKLIST.md
14. M13_TERMINAL_HANDOFF_CONTRACT.md
15. M13_ARCHITECTURE_DECISION_RECORD.md
16. M13_FINAL_IMPLEMENTATION_SPECIFICATION.md (executive document)