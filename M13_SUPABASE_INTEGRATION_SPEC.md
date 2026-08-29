# M13 Supabase Integration Specification

## Overview

This document defines the complete Supabase architecture for AI-OS M13, specifying Supabase as a persistent storage backend where AI-OS retains semantic ownership of all data while using Supabase for physical storage.

## Role and Data Ownership

### Exact Role
Supabase serves as a **persistence layer** for AI-OS owned data, functioning as a durable storage backend similar to a database. It does NOT provide:
- Governance authority
- Verification authority
- Final judgment
- Autonomous decision-making
- Workflow control
- Second kernel or "second brain"

### Data Ownership Semantics
AI-OS owns the **semantic meaning** of all data stored in Supabase, even when data is physically stored there. This means:
- AI-OS defines what data represents (project state, task state, execution state, etc.)
- AI-OS enforces data semantics through its own validation layers
- Supabase stores dumb bytes; AI-OS provides intelligent interpretation
- AI-OS can migrate data to other storage systems without changing semantic meaning

### Authoritative vs Non-Authoritative State
| Aspect | Authoritative Source | Notes |
|--------|---------------------|-------|
| Semantic Meaning | AI-OS | Defines what data represents |
| Physical Storage | Supabase | Stores the actual bytes |
| Schema Definition | AI-OS | AI-OS owns schema evolution |
| Validation Rules | AI-OS | AI-OS enforces data integrity |
| Query Semantics | AI-OS | AI-OS defines query meaning |
| Migration Paths | AI-OS | AI-OS controls data portability |

## Schema Boundaries

### AI-OS Owned Schemas
AI-OS defines and owns these logical schemas within Supabase:

1. **Project State Schema**
   - Projects, requirements, architectures, phases, tasks
   - Task dependencies, states, assignments
   - Project metadata and provenance

2. **Execution State Schema**
   - Self-loop checkpoints, execution state, self-prompt state
   - Bounded execution contexts, task execution records
   - Integration states and cross-integration coordination

3. **Evidence and Learning Schema**
   - Evidence metadata, provenance chains, learning updates
   - Knowledge artifacts, decision records, verification results
   - Audit trails and compliance evidence

4. **Integration State Schema**
   - Integration configuration, connection status, health status
   - Credential references (non-secret), operational metadata
   - Mock/real mode states, degradation handling

5. **Dashboard State Schema**
   - UI preferences, view states, user interaction history
   - Cached dashboard data, widget configurations

### Schema Evolution Governance
- AI-OS controls all schema migrations through versioned migration scripts
- Supabase functions as a passive storage target for AI-OS-defined schemas
- Schema changes go through AI-OS architecture review and decision process
- Backward compatibility maintained through AI-OS adaptation layers

## Persistence Model

### Storage Responsibilities
AI-OS responsibilities:
- Define data models and schemas
- Serialize/deserialize data to/from Supabase format
- Enforce data validation and integrity constraints
- Manage schema evolution and migrations
- Provide semantic interpretation of stored data
- Handle data correlation and provenance tracking

Supabase responsibilities:
- Provide durable, ACID-compliant storage
- Handle concurrent access and connection pooling
- Provide basic querying capabilities (AI-OS builds semantic layer)
- Ensure data durability and backup/recovery
- Provide basic security features (RLS, authentication)

### Project State Persistence
Projects are stored as JSON documents with:
- Immutable project ID (UUID)
- Versioned project definition (requirements, architecture, etc.)
- Current phase and task status
- Provenance chain linking to decisions and evidence
- Timestamps for creation, updates, phase transitions

### Task State Persistence
Tasks are stored with:
- Task ID, project ID, phase ID
- Subject, description, current status (pending/in_progress/completed)
- Assigned agents/services, dependencies
- Execution artifacts, results, and evidence links
- Timestamps for state transitions

### Self-Loop Checkpoint Persistence
Checkpoints store:
- Complete self-loop state at point-in-time
- Current self-prompt, execution context, bounded execution state
- Test results, review findings, verification status
- Decision points and learning updates
- Integration states and external system statuses
- Provenance correlation IDs for traceability

### Execution State Persistence
Execution records include:
- Bounded execution context and parameters
- External system invocation details (n8n workflow, Playwright test, etc.)
- Raw outputs, status codes, execution timing
- Success/failure determination by AI-OS evaluation
- Artifact references and output metadata
- Error details and degradation handling

### Integration State Persistence
Each integration stores:
- Connection status and health metrics
- Last successful operation timestamp
- Configuration parameters (non-sensitive)
- Operational mode (mock/real, degraded/failure states)
- Error counters and retry states
- Resource usage metrics

## Requirements

### Functional Requirements
1. AI-OS must be able to persist and retrieve all project, task, execution, and self-loop state
2. AI-OS must maintain semantic ownership of all data semantics
3. System must support schema evolution without data loss
4. All data must be correlatable through provenance chains
5. System must handle Supabase unavailability gracefully
6. Mock mode must be available for development/testing
7. Real mode requires user-provided Supabase credentials and instance

### Non-Functional Requirements
1. **Performance**: Sub-second response times for typical operations
2. **Reliability**: 99.9% uptime SLA target for production use
3. **Scalability**: Support for multiple concurrent AI-OS instances
4. **Security**: Row-level security, encryption at rest and in transit
5. **Auditability**: Complete audit trail of all data access and changes
6. **Recovery**: Point-in-time recovery capabilities
7. **Compatibility**: Work with standard PostgreSQL-compatible Supabase instances

### Local Development Strategy
- Use local Supabase instance via Docker for development
- Configuration via environment variables pointing to local instance
- Auto-migration on startup for development schema updates
- Mock mode available when no Supabase instance accessible

### Production Strategy
- Production Supabase instance with user-provided credentials
- Connection pooling and efficient query patterns
- Monitoring and alerting for Supabase health
- Backup strategy aligned with AI-OS backup requirements
- Geographic redundancy options for disaster recovery

### Mock Strategy
- In-memory storage mock that mimics Supabase API
- Automatic activation when Supabase credentials unavailable or invalid
- Identical API interface to real Supabase adapter
- Data persistence limited to process lifetime (clear on restart)
- Useful for unit testing and development without external dependencies

### Real Mode
- Requires user to provide:
  - Supabase project URL
  - Supabase anon/public key (for client-side operations)
  - Optional service role key (for admin operations, tightly controlled)
- Environment variables: `SUPABASE_URL`, `SUPABASE_ANON_KEY`
- Integration framework gates real mode based on user resource validation
- AIOS_REAL_INTEGRATION_ENABLED=1 required for gated real-operational tests

## Security

### Authentication and Authorization
- AI-OS uses Supabase auth for user-level access control where applicable
- Service role key (if used) tightly scoped to AI-OS kernel process only
- Row Level Security (RLS) policies defined by AI-OS for data isolation
- No direct user access to Supabase bypassing AI-OS governance
- All Supabase access flows through AI-OS SecurityManager gate-before-connect

### Secret Handling
- No secrets stored in source code or configuration files
- Secrets managed through environment variables only
- Secret redaction in all logs, events, and error messages
- Secret scrubbing from subprocess environments
- Integration framework validates user-provided secrets before enabling real mode

### Failure Handling
- **Supabase Unavailable**: System transitions to degraded mode with local caching
- **Connection Loss**: Automatic reconnection with exponential backoff
- **Query Failures**: AI-OS evaluates and determines retry vs. abort based on context
- **Data Corruption**: Detected through AI-OS validation; triggers recovery procedures
- **Permission Errors**: Treated as security events requiring AI-OS judgment
- **Rate Limiting**: Handled through AI-OS quota management and backoff strategies
- **Restart Recovery**: System recovers last known state from persistent storage on restart
- **Transaction Safety**: AI-OS uses idempotency keys and transaction boundaries where appropriate

### Backup and Recovery
- AI-OS defines backup requirements; Supabase provides infrastructure
- Point-in-time recovery capability for undo/redo operations
- Backup validation through AI-OS restoration testing
- Cross-region backup options for disaster recovery
- Migration tools for moving between storage backends

## Operational Tests

### Unit Tests
- Mock Supabase adapter behavior
- Schema validation and serialization/deserialization
- Error handling and edge cases
- Migration script correctness
- Provenance tracking and correlation

### Integration Tests
- Real Supabase instance (when user resources available and gated enabled)
- Full persistence round-trip: AI-OS → Supabase → AI-OS
- Schema evolution scenarios
- Concurrent access handling
- Backup and recovery validation
- Performance benchmarking

### Operational Tests (Gated Real)
- Require AIOS_REAL_INTEGRATION_ENABLED=1 and verified user resources
- Test actual Supabase connectivity and authentication
- Validate data durability across system restarts
- Test schema migration scenarios with real data
- Benchmark real-world performance characteristics
- Validate backup and restore procedures

## Determining Mandatory vs Optional

### For v1 of M13 Milestone: OPTIONAL
Supabase is **OPTIONAL** for v1 of the M13 milestone because:
1. AI-OS can operate with existing local persistence (filesystem/StateManager)
2. Core AI-OS lifecycle functions without external persistence
3. All M0-M12 functionality verified without Supabase dependency
4. Supabase enhances durability but doesn't enable new core capabilities
5. User may choose other persistence solutions or local-only operation

### Conditions for Making Supabase Mandatory
Supabase could become mandatory in future versions when:
1. Multi-instance AI-OS coordination requires shared persistent state
2. Durability requirements exceed what local filesystems can provide
3. Enterprise deployment needs centralized storage administration
4. Disaster recovery requirements necessitate off-site storage
5. Performance requirements benefit from database query optimization

However, even if made mandatory, AI-OS would retain:
- Semantic ownership of all data
- Governance and verification authority
- Ability to function in degraded/local mode during outages
- Clear separation between AI-OS authority and storage mechanism

## Integration with AI-OS Lifecycle Points

### Where Supabase Integrates
1. **Persistence Checkpoints**: After each major lifecycle phase completion
2. **State Snapshots**: Periodic snapshots of workflow and application state
3. **Evidence Storage**: Long-term storage of evidence, learning, and audit trails
4. **Integration Status**: Persistent storage of integration health and configuration
5. **Dashboard State**: UI preferences and view state persistence
6. **Recovery Points**: System state checkpoints for restart recovery

### Integration Flow Patterns
**AI-OS → Supabase (Write)**:
1. AI-OS prepares data with semantic meaning and provenance
2. AI-OS serializes data according to owned schema
3. AI-OS validates data integrity before storage
4. AI-OS issues write command to Supabase adapter
5. Supabase adapter communicates with Supabase instance
6. Supabase confirms storage and returns confirmation
7. AI-OS updates internal state with storage confirmation

**Supabase → AI-OS (Read)**:
1. AI-OS issues read command with query parameters to Supabase adapter
2. Supabase adapter retrieves data from Supabase instance
3. Supabase returns raw data to adapter
4. Adapter returns data to AI-OS with preservation of provenance markers
5. AI-OS validates data integrity and semantic meaning
6. AI-OS deserializes and interprets data according to owned schema
7. AI-OS uses data in lifecycle processing with full provenance tracking

### Critical Integration Constraints
1. **No External Interpretation**: Supabase never interprets AI-OS data semantics
2. **No External Triggers**: Supabase cannot trigger AI-OS lifecycle actions
3. **No External Queries as Commands**: Supabase cannot issue commands to AI-OS
4. **All Semantic Logic in AI-OS**: Query interpretation, validation, and application logic remains in AI-OS
5. **Provenance Preservation**: All data carries complete provenance chains traceable to AI-OS decisions
6. **Atomic Lifecycle Boundaries**: Persistence operations respect atomic lifecycle phase boundaries