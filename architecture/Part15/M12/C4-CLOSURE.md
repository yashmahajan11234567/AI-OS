# C4 Closure — Notion Adopt-or-Drop

## 1. Closure Metadata

* Conflict: C4 — Notion Adopt-or-Drop
* Status: **RESOLVED**
* Resolution date: **2026-09-10**
* Governing milestone: M12-T4
* Resolution type: Documentation / architectural decision closure

This document formally records the resolution of the C4 Notion adopt-or-drop conflict as part of the M12 closure process.

## 2. C4 Issue Definition

**"Notion absent from repo — adopt-or-drop decision required."**

The master plan previously recorded Notion as absent/TBD and required an explicit ADOPT or DROP decision. This conflict has been resolved through implementation and documentation.

## 3. Authoritative Decision

**ADOPT — with boundary.**

Define the boundary:

* Notion is an external integration.
* Notion is optional.
* Notion is not a core AI-OS runtime component.
* Notion does not become runtime authority.
* Notion data is contextual/untrusted/advisory.
* AI-OS retains sole runtime authority.

## 4. Rationale

Reference the authoritative master-plan material:

* Master Plan §15.1 — recommendation to ADOPT with boundary
* Master Plan §27 — Notion status synchronization classified as OPTIONAL / operational tracking
* Master Plan §28 — `Make Notion the runtime authority` is explicitly listed under MUST-NOT-IMPLEMENT

Make clear that adoption means **bounded external integration**, not delegation of AI-OS authority to Notion.

## 5. Current Implementation Evidence

Document the existing implementation found during the audit.

Reference the relevant actual repository components, including where applicable:

* `src/aios/adapters/notion_adapter.py` — Implements BaseExecutionAdapter for Notion MCP server, providing page/database operations with all results marked advisory per C14
* `src/aios/adapters/mock_notion_server.py` — Mock Notion MCP server for testing the NotionAdapter without requiring external service
* `config/mcp/notion_mcp.json` — MCP configuration for Notion server (stdio transport to mock server)
* `config/capabilities/notion_planning.yaml` — Capability registration for notion_planning facade with trusted_contextual trust level
* Kernel registration evidence — NotionAdapter instantiated and registered in HermesKernel._init_notion() method
* Notion unit/integration tests — Comprehensive test suite covering adapter creation, MCP connection, page operations, database operations, provenance, advisory/C14 marking, security validation, and failure handling

Describe the relevant boundary behavior:

* results are marked `advisory=True`
* authority is `contextual`
* trust level is `untrusted`
* advisory marking is enforced by the adapter through `_mark_advisory()` method
* sensitive property keys are protected/redacted via validation in `_validate_content()` method
* sensitive-data attempts raise the appropriate security error (NotionSecurityError)

## 6. CHANGELOG Evidence

Reference:

`CHANGELOG.md` v1.0.0

Specifically reference the C4 entry at/around line 38:

**"C4 Notion Adopt-or-Drop — Notion adopted as external integration via MCP bridge (M8-T4); adapter implemented and tested"**

Do not modify CHANGELOG.md.

## 7. Part 15 README Evidence

Reference:

`architecture/Part15/README.md` v1.1.0

Specifically document its supporting evidence that:

* Notion is included under external integrations from M8-T4
* C4 is recorded as adopted as an external integration via MCP bridge
* the adapter was implemented and tested

Do not modify the README.

## 8. Stale Historical Evidence

Acknowledge:

`M12_ACCEPTANCE_VERIFICATION_REPORT.md`

and its earlier C4 status of `NOT RESOLVED`.

Explicitly identify this as **stale historical evidence** that predates the actual C4 resolution and implementation.

Do not modify, delete, or rewrite the report.

State that the current authoritative evidence is the implemented M8-T4 integration plus CHANGELOG v1.0.0 and the current Part 15 documentation.

## 9. Internal vs External Boundary

Clearly distinguish:

### Internal AI-OS

AI-OS kernel/runtime authority remains internal and authoritative.

### External Integration

Notion is an optional external integration accessed through the adapter/MCP boundary.

### Authority

Notion cannot become the runtime authority for AI-OS.

This distinction is essential to C4 closure.

## 10. Scope Boundary

Explicitly state that C4 closure does NOT require:

* new Notion functionality
* source changes
* configuration changes
* test changes
* CHANGELOG changes
* Part 15 README changes
* modification of the M12 acceptance report
* resolution of unrelated conflicts
* changes to C1/C2/C3
* changes to M10/M11
* resolution of `CONFLICT-P15-01` if that is a separate tracked issue

C4 closure is documentation-only because the required adoption decision and implementation already exist.

## 11. Closure Statement

**C4 — Notion Adopt-or-Drop is formally resolved and closed as of 2026-09-10.** Notion is adopted as a bounded external/optional integration and does not become AI-OS runtime authority.