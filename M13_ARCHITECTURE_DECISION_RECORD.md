# M13 Architecture Decision Record

## Overview

This document captures the key architectural decisions for AI-OS M13 that preserve AI-OS as the sole governance, verification, and decision-making authority while integrating Supabase, n8n, Obsidian Git, AI-OS Dashboard, and existing external ecosystem. Each decision follows the architecture decision record (ADR) format, providing context, decision, status, and consequences to ensure transparent and traceable architectural evolution.

## Decision Index

| ADR ID | Title | Status |
|--------|-------|--------|
| M13-ADR-001 | AI-OS Sole Authority Preservation Pattern | ACCEPTED |
| M13-ADR-002 | Bounded External Resource Integration Pattern | ACCEPTED |
| M13-ADR-003 | Gate-Before-Connect Enforcement Pattern | ACCEPTED |
| M13-ADR-004 | Self-Loop Autonomous Decision-Making Pattern | ACCEPTED |
| M13-ADR-005 | Self-Prompt Authoritative Internal Directive Pattern | ACCEPTED |
| M13-ADR-006 | Dashboard Read-Only UI with Authorized Actions Pattern | ACCEPTED |
| M13-ADR-007 | Mock-First Development and Testing Pattern | ACCEPTED |
| M13-ADR-008 | Real-Mode Gated Operational Testing Pattern | ACCEPTED |
| M13-ADR-009 | Provenance Tracking and Correlation Pattern | ACCEPTED |
| M13-ADR-010 | Secret Handling and Zeroization Pattern | ACCEPTED |
| M13-ADR-011 | Resource Mode Separation Pattern | ACCEPTED |
| M13-ADR-012 | Terminal Role Separation Pattern | ACCEPTED |
| M13-ADR-013 | Learning Extraction Authority Preservation Pattern | ACCEPTED |
| M13-ADR-014 | Error Handling and Failure Recovery Pattern | ACCEPTED |
| M13-ADR-015 | External System Durability and Knowledge Guarantees Pattern | ACCEPTED |

## ADR Details

### M13-ADR-001: AI-OS Sole Authority Preservation Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS M13 integrates multiple external systems (Supabase, n8n, Obsidian Git, AI-OS Dashboard, Hermes/ACP, Hermes/MCP, Playwright, Agent Reach, FreeLLMAPI, Notion, Graphify, Claude-Mem) while maintaining the architectural principle that AI-OS remains the sole governance, verification, and decision-making authority. Previous versions (M0-M12) established this authority pattern, but M13 extends it to comprehensive external ecosystem integration.  
**Decision**: AI-OS retains sole authority over governance, verification, and decision-making through:  
1. **Directive-Based Control**: AI-OS directs all external systems as bounded resources  
2. **Result Evaluation**: AI-OS evaluates all external system results before acceptance  
3. **Judgment Exercise**: AI-OS exercises sole judgment over all system operations  
4. **Authority Validation**: AI-OS validates authority preservation in all operations  
5. **Learning Extraction**: AI-OS extracts validated learning while preserving authority  
**Consequences**:  
- **Positive**: Clear authority boundaries, predictable governance, consistent verification, reliable decision-making  
- **Negative**: Increased complexity in authority validation mechanisms, potential performance overhead  
- **Neutral**: External systems remain valuable bounded resources under AI-OS control  

### M13-ADR-002: Bounded External Resource Integration Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: Integrating external systems requires ensuring they operate as bounded resources under AI-OS control to prevent authority dilution and maintain system integrity. External systems must not be able to exert independent governance, verification, or decision-making influence over AI-OS.  
**Decision**: All external systems integrate as bounded resources through:  
1. **BaseExecutionAdapter Framework**: Standardized interface for all external integrations  
2. **Operation Bounding**: Explicit limits on operations, timeouts, retries, and resource usage  
3. **Result Filtering**: AI-OS filters and processes external system results according to directives  
4. **Directional Control**: Communication flows AI-OS → Component (AI-OS directs, components respond)  
5. **Authority Transparency**: Clear documentation that components have zero authority  
**Consequences**:  
- **Positive**: Authority preservation, resource predictability, controlled integration, testable boundaries  
- **Negative**: Integration complexity, potential resource underutilization  
- **Neutral**: Systems remain valuable for persistence, execution, knowledge, etc. under bounds  

### M13-ADR-003: Gate-Before-Connect Enforcement Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: External system access must be controlled to prevent unauthorized connections that could compromise AI-OS authority or introduce security vulnerabilities. The MCP Manager already implements gate-before-connect, but M13 extends and formalizes this pattern for all external integrations.  
**Decision**: All external system connections enforce gate-before-connect through:  
1. **MCP Manager Enforcement**: Centralized gate-before-connect for MCP-based integrations  
2. **Adapter-Level Gates**: Gate-before-connect for non-MCP integrations (Supabase, n8n, etc.)  
3. **SecurityManager Integration**: Security policies enforced at gate point  
4. **Resource Validation**: Pre-connection validation of resource readiness and authenticity  
5. **Connection Limitation**: Limits on concurrent connections, connection duration, and retry attempts  
**Consequences**:  
- **Positive**: Security enhancement, unauthorized access prevention, controlled resource usage  
- **Negative**: Connection latency, potential availability impact during gateway processing  
- **Neutral**: Standard practice for secure external system integration  

### M13-ADR-004: Self-Loop Autonomous Decision-Making Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS requires a single authoritative autonomous decision-making engine to prevent conflicting decisions and maintain clear authority lines. Previous versions had elements of self-loop behavior, but M13 formalizes it as the sole decision-making authority.  
**Decision**: AI-OS implements a single self-loop as the sole autonomous decision-making engine through:  
1. **Single Execution Thread**: One authoritative decision-making thread  
2. **Directive Processing**: Processes self-prompts as authoritative internal directives  
3. **Resource Direction**: Directs external systems as bounded resources  
4. **Result Evaluation**: Evaluates all results before proceeding to next iteration  
5. **Judgment Exercise**: Exercises sole judgment over all system operations  
**Consequences**:  
- **Positive**: Clear authority lines, predictable behavior, consistent decision-making, auditability  
- **Negative**: Potential performance bottleneck, limited parallelism  
- **Neutral**: Enables deterministic testing and verification through self-loop architecture  

### M13-ADR-005: Self-Prompt Authoritative Internal Directive Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS requires authoritative internal directives to guide the self-loop decision-making process. These directives must represent the sole source of internal direction to prevent conflicting guidance and maintain clear authority.  
**Decision**: AI-OS uses self-prompts as the sole source of authoritative internal directives through:  
1. **Prompt Processing**: Self-loop processes self-prompts as internal directives  
2. **Directional Authority**: Self-prompts direct resource usage and operation execution  
3. **Validation Requirement**: Self-prompts validated for authenticity and authority compliance  
4. **Learning Integration**: Validated learning integrated into future self-prompts  
5. **Authority Preservation**: Self-prompts represent AI-OS internal authority only  
**Consequences**:  
- **Positive**: Clear internal direction, consistent decision-making, learning integration  
- **Negative**: Prompt processing overhead, potential for directive conflicts  
- **Neutral**: Standard practice for authoritative internal guidance systems  

### M13-ADR-006: Dashboard Read-Only UI with Authorized Actions Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: The AI-OS Dashboard must provide user visibility and interaction capabilities while preserving AI-OS as the sole authority. Users need to view system status and provide input/approvals, but must not be able to exert independent authority over AI-OS operations.  
**Decision**: AI-OS Dashboard implements read-only UI with authorized actions through:  
1. **Read-Only Display**: Displays only AI-OS-provided information  
2. **Authorized Actions Only**: Accepts only user-approved actions explicitly authorized by AI-OS  
3. **Input Collection**: Collects user input for forwarding to AI-OS  
4. **Approval Collection**: Collects user approvals for forwarding to AI-OS  
5. **Notification Display**: Displays AI-OS notifications to user  
6. **Authority Transparency**: Clear documentation that dashboard has zero authority  
**Consequences**:  
- **Positive**: User visibility, controlled interaction, authority preservation, predictable behavior  
- **Negative**: Limited direct user control, indirect action execution  
- **Neutral**: Standard pattern for authoritative systems with user interfaces  

### M13-ADR-007: Mock-First Development and Testing Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: Development and testing must be possible without external system dependencies to enable AI-OS development, CI/CD, and isolated testing. External systems introduce variability, cost, and availability concerns that hinder development velocity.  
**Decision**: AI-OS implements mock-first development and testing through:  
1. **Automatic Mock Activation**: Mock mode activates when real resources unavailable  
2. **In-Memory Simulation**: Uses in-memory simulators matching real system interfaces  
3. **Behavioral Fidelity**: Simulates realistic behavior including delays, errors, edge cases  
4. **Boundary Testing Enablement**: Enables testing of boundary conditions and error scenarios  
5. **Learning Extraction**: Enables extraction of validated learning from simulated outcomes  
6. **Seamless Transition**: Transparent transition to real mode when resources available  
**Consequences**:  
- **Positive**: Development velocity, test reliability, CI/CD compatibility, cost elimination  
- **Negative**: Simulation fidelity limits, potential mock-real gaps  
- **Neutral**: Standard practice for external system integration development  

### M13-ADR-008: Real-Mode Gated Operational Testing Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: Real-mode operation requires validation and testing to ensure actual integration fidelity, but must be gated to prevent uncontrolled real-world side effects during development and testing. Users must explicitly enable real-mode testing through a feature flag.  
**Decision**: AI-OS implements real-mode gated operational testing through:  
1. **Feature Flag Control**: `AIOS_REAL_INTEGRATION_ENABLED=1` required for real mode  
2. **Resource Verification**: Pre-test validation of user resource readiness  
3. **Integration Testing**: Tests actual integration with real external systems  
4. **Fidelity Validation**: Validates actual integration fidelity and accuracy  
5. **Performance Measurement**: Measures actual performance characteristics  
6. **Error Handling Validation**: Validates actual error handling and failure modes  
7. **Authority Preservation Check**: Verifies AI-OS authority preservation during testing  
8. **Resource Compliance Check**: Verifies external systems operate as bounded resources  
**Consequences**:  
- **Positive**: Real-world validation, integration fidelity assurance, performance characterization  
- **Negative**: Testing complexity, potential real-world side effects  
- **Neutral**: Standard practice for gated real-world system testing  

### M13-ADR-009: Provenance Tracking and Correlation Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS must track the origin and transformation of all data, decisions, and operations to ensure accountability, enable auditability, and support learning extraction. Provenance tracking is essential for maintaining authority and verifying system integrity.  
**Decision**: AI-OS implements provenance tracking and correlation through:  
1. **Origin Tagging**: All data, decisions, operations tagged with origin information  
2. **Transformation Tracking**: Tracks all transformations through system processing  
3. **Correlation Maintenance**: Maintains correlations between related data/decision/operation elements  
4. **Audit Trail Generation**: Generates audit trails for accountability purposes  
5. **Learning Extraction Support**: Supports extraction of validated learning through provenance  
6. **Authority Verification**: Enables verification of AI-OS authority preservation  
**Consequences**:  
- **Positive**: Accountability, auditability, learning capability, authority verification  
- **Negative**: Storage overhead, processing complexity  
- **Neutral**: Essential practice for authoritative systems requiring accountability  

### M13-ADR-010: Secret Handling and Zeroization Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS handles sensitive information (credentials, keys, tokens) for external system access and must ensure proper secret handling to prevent security vulnerabilities. Secrets must be protected during use and properly zeroized after use to prevent leakage.  
**Decision**: AI-OS implements secret handling and zeroization through:  
1. **Environment Variable Storage**: Secrets stored in environment variables (not code/config)  
2. **Use-Time Protection**: Secrets protected in memory during use  
3. **Post-Use Zeroization**: Secrets properly zeroized after use  
4. **Access Limitation**: Limited access to secrets on need-to-use basis  
5. **Memory Protection**: Protected memory regions for secret storage  
6. **Audit Trail Exclusion**: Secrets excluded from audit trails and logging  
**Consequences**:  
- **Positive**: Security enhancement, secret leakage prevention, compliance improvement  
- **Negative**: Memory management overhead, access complexity  
- **Neutral**: Standard practice for secure secret handling in systems  

### M13-ADR-011: Resource Mode Separation Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS must cleanly separate mock mode and real mode operation to enable reliable development/testing while supporting production operation with actual external systems. Mode mixing creates confusion, reduces test reliability, and complicates system behavior prediction.  
**Decision**: AI-OS separates resource modes through:  
1. **Automatic Mode Detection**: Automatic detection of resource availability and validity  
2. **Explicit Mode Selection**: `AIOS_REAL_INTEGRATION_ENABLED=1` enables real mode when resources ready  
3. **Clear Mode Boundaries**: No mixing of mock and real mode resources within operations  
4. **Mode-Specific Behavior**: Defined behavior for mock mode (simulation) vs real mode (actual)  
5. **Transition Transparency**: Transparent transition between modes with clear indicators  
6. **Authority Preservation**: AI-OS authority preserved in both modes  
**Consequences**:  
- **Positive**: Development reliability, test consistency, production readiness, clear behavior  
- **Negative**: Mode transition complexity, potential mode-specific bugs  
- **Neutral**: Standard practice for systems with simulation and real-world operation  

### M13-ADR-012: Terminal Role Separation Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS M13 operates across multiple terminals and must maintain clear role separation to prevent authority confusion, ensure predictable behavior, and support distributed operation. Terminals must have well-defined responsibilities that preserve AI-OS authority.  
**Decision**: AI-OS separates terminal roles through:  
1. **Terminal 1 Authority**: Terminal 1 hosts AI-OS Core Orchestration (sole authority)  
2. **Terminal 2 Resources**: Terminal 2 hosts External Integration Endpoints (bounded resources)  
3. **Terminal 3 Interface**: Terminal 3 hosts User Interface and Interaction (no authority)  
4. **Terminal 4 Development**: Terminal 4 hosts Development and Testing (no operational authority)  
5. **Communication Patterns**: Well-defined communication patterns between terminals  
6. **Authority Transparency**: Clear documentation of authority distribution by terminal  
**Consequences**:  
- **Positive**: Clear responsibility boundaries, predictable distributed operation, authority preservation  
- **Negative**: Inter-terminal communication complexity, potential latency  
- **Neutral**: Standard practice for distributed authoritative systems  

### M13-ADR-013: Learning Extraction Authority Preservation Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS must extract validated learning from system operations and external system interactions while preserving its sole authority over governance, verification, and decision-making. Learning extraction must not create alternative authority lines or compromise decision-making integrity.  
**Decision**: AI-OS extracts validated learning while preserving authority through:  
1. **Post-Operation Extraction**: Learning extracted after operation completion and evaluation  
2. **Authority Validation**: AI-OS validates authority preservation during learning extraction  
3. **Directive Integration**: Validated learning integrated into future self-prompts and directives  
4. **Judgment Incorporation**: Learning incorporated into AI-OS judgment and decision-making  
5. **Source Transparency**: Clear documentation of learning sources and extraction methods  
6. **Bounded Learning**: Learning extracted within bounded resource constraints  
**Consequences**:  
- **Positive**: Continuous improvement, adaptive behavior, evidence-based decision-making  
- **Negative**: Learning processing overhead, potential for learning-based bias  
- **Neutral**: Standard practice for authoritative learning systems  

### M13-ADR-014: Error Handling and Failure Recovery Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: AI-OS must handle errors and failures in a way that preserves system integrity, maintains authority boundaries, and enables continued operation. Error handling must not create authority confusion or compromise system integrity.  
**Decision**: AI-OS handles errors and failures while preserving authority through:  
1. **Component Reporting**: Components report errors to AI-OS for evaluation  
2. **AI-OS Evaluation**: AI-OS evaluates all error reports before accepting as valid  
3. **Bounded Decision-Making**: AI-OS makes bounded decisions on error handling  
4. **Directional Control**: AI-OS directs bounded error handling operations  
5. **Result Validation**: AI-OS validates error handling results before acceptance  
6. **Authority Preservation**: AI-OS validates authority preservation during error handling  
7. **Learning Extraction**: AI-OS extracts validated learning from error handling  
8. **Recovery Direction**: AI-OS directs bounded recovery operations  
**Consequences**:  
- **Positive**: System resilience, controlled error handling, authority preservation, learning opportunity  
- **Negative**: Error handling complexity, potential for error handling delays  
- **Neutral**: Standard practice for authoritative systems requiring resilience  

### M13-ADR-015: External System Durability and Knowledge Guarantees Pattern

**Status**: ACCEPTED  
**Date**: 2026-08-28  
**Context**: When integrating external systems for persistence (Supabase) and knowledge/durability (Obsidian Git), AI-OS must clarify what guarantees it provides versus what guarantees come from the external systems. AI-OS must not overpromise on external system capabilities or understate its own authority role.  
**Decision**: AI-OS clarifies durability and knowledge guarantees through:  
1. **AI-OS Semantic Ownership**: AI-OS owns semantic meaning of all data and knowledge  
2. **External System Durability**: External systems provide actual durability guarantees (persistence, Git)  
3. **AI-OS Evaluation**: AI-OS evaluates external system durability performance  
4. **Knowledge Correlation**: AI-OS correlates knowledge while preserving semantic ownership  
5. **Authority Transparency**: Clear documentation that AI-OS owns meaning, systems provide durability  
6. **Bounded Resource Treatment**: External systems treated as bounded durability/knowledge resources  
**Consequences**:  
- **Positive**: Clear responsibility boundaries, realistic expectations, authority preservation  
- **Negative**: Guarantee complexity, potential expectation mismatches  
- **Neutral**: Standard practice for systems integrating external persistence/knowledge resources  

## Decision Rationale Summary

### Authority Preservation Rationale
All decisions prioritize preserving AI-OS as the sole governance, verification, and decision-making authority through:
- Clear authority boundaries and documentation
- Directional control patterns (AI-OS → Component)
- Result evaluation and validation requirements
- Judgment exercise retention
- Learning extraction with authority preservation
- Mock-first and gated real-mode patterns
- Terminal role separation with clear responsibilities

### Integration Fidelity Rationale
Decisions balance external system integration with authority preservation through:
- Bounded resource patterns with explicit limits
- Gate-before-connect enforcement for security
- Provenance tracking for accountability
- Secret handling and zeroization for security
- Resource mode separation for reliability
- External system durability/knowledge guarantee clarification

### Operational Reliability Rationale
Decisions ensure reliable operation through:
- Self-loop autonomous decision-making for clear authority lines
- Self-prompt authoritative internal directives for clear direction
- Dashboard read-only UI with authorized actions for controlled interaction
- Error handling and failure recovery for system resilience
- Learning extraction authority preservation for continuous improvement
- Pre-operational and post-operational validation for system integrity

## Implementation Guidelines

### Authority Preservation Guidelines
1. **Never delegate authority**: AI-OS never delegates governance, verification, or decision-making
2. **Always evaluate results**: AI-OS always evaluates external system results before acceptance
3. **Always validate authority**: AI-OS always validates authority preservation in operations
4. **Always maintain bounds**: AI-OS always maintains bounded resource constraints
5. **Always extract learning**: AI-OS always extracts validated learning while preserving authority
6. **Always separate modes**: AI-OS always separates mock mode and real mode operation
7. **Always clarify roles**: AI-OS always clarifies authority and responsibility roles

### Integration Guidelines
1. **Use BaseExecutionAdapter**: All external integrations use the BaseExecutionAdapter framework
2. **Implement gate-before-connect**: All external system access implements gate-before-connect
3. **Define clear bounds**: All external resource usage defines explicit operational bounds
4. **Validate resources**: All external integrations validate resource readiness before use
5. **Handle secrets properly**: All external integrations handle secrets through environment variables and zeroization
6. **Track provenance**: All external integrations track provenance for accountability
7. **Separate modes**: All external integrations support mock mode and real mode separation

### Operational Guidelines
1. **Maintain self-loop**: Maintain single self-loop as sole autonomous decision-making engine
2. **Process self-prompts**: Process self-prompts as authoritative internal directives
3. **Preserve dashboard authority**: Preserve dashboard as read-only UI with authorized actions only
4. **Handle errors properly**: Handle errors through component reporting and AI-OS evaluation
5. **Extract learning properly**: Extract learning through post-operation extraction and authority validation
6. **Separate terminals properly**: Separate terminals according to defined roles and responsibilities
7. **Validate operationally**: Validate operation through pre- and post-operational checks

## Decision Impact Assessment

### Short-Term Impact (M13 Milestone)
- **Authority Clarity**: Clear authority boundaries established and documented
- **Integration Reliability**: Reliable external system integration with bounded resource patterns
- **Development Velocity**: Enhanced development velocity through mock-first patterns
- **Test Reliability**: Enhanced test reliability through authoritative patterns
- **Operational Predictability**: Enhanced operational predictability through clear role separation
- **Security Enhancement**: Enhanced security through gate-before-connect and secret handling
- **Audit Capability**: Enhanced audit capability through provenance tracking

### Long-Term Impact (Beyond M13)
- **Authority Sustainability**: Sustainable authority preservation through clear patterns
- **Integration Extensibility**: Extensible integration framework for future external systems
- **Development Sustainability**: Sustainable development through mock-first and gated patterns
- **Testing Sustainability**: Sustainable testing through authoritative patterns
- **Operational Sustainability**: Sustainable operation through clear role separation
- **Learning Sustainability**: Sustainable learning through authority-preserving extraction
- **Resilience Sustainability**: Sustainable resilience through error handling and recovery patterns

## Related Decisions and References

### Related AI-OS Decisions
- **M0-M12 Authority Decisions**: Establish AI-OS sole authority pattern (foundational)
- **M7 Testing Decisions**: Establish multi-perspective testing authority pattern
- **M8 Integration Decisions**: Establish external integration authority pattern
- **M9 Learning Decisions**: Establish learning/adaptive systems authority pattern
- **M10 Autonomy Decisions**: Establish bounded autonomy authority pattern
- **M11 Extension Decisions**: Establish extension authority pattern
- **M12 Closure Decisions**: Establish closure authority pattern

### Related External Patterns
- **Circuit Breaker Pattern**: Related to bounded resource patterns and fault tolerance
- **Command Pattern**: Related to directive-based control and authoritative direction
- **Observer Pattern**: Related to provenance tracking and correlation
- **Singleton Pattern**: Related to self-loop autonomous decision-making (single instance)
- **Facade Pattern**: Related to BaseExecutionAdapter framework and simplified interfaces
- **Proxy Pattern**: Related to gate-before-connect and controlled access
- **State Pattern**: Related to resource mode separation and mode-specific behavior
- **Template Method Pattern**: Related to self-loop and self-prompt processing patterns
- **Strategy Pattern**: Related to learning extraction and adaptive decision-making
- **Chain of Responsibility Pattern**: Related to error handling and failure recovery patterns

### References
- AI-OS Architecture Documentation (Parts 0-15)
- AI-OS Source Code (src/aios/)
- AI-OS Configuration (config/)
- AI-OS MCP Configuration (config/mcp/)
- AI-OS Integration Documentation (external integrations)
- AI-OS Testing Documentation (testing strategies and patterns)
- AI-OS Security Documentation (security architecture and patterns)