# Part 12 Schema Reference

This document defines the formal schemas for all structured data exchanged between agents in the AI-OS Multi-Agent Collaboration Architecture (Part 12). These schemas are technology-neutral and can be implemented using JSON Schema, YAML, or similar validation mechanisms.

## Schema Architecture Specification

This section outlines the architectural governance for all schemas defined within the AI-OS, ensuring consistency, compatibility, and maintainability across the multi-agent ecosystem. It draws inspiration from enterprise schema specifications found in Kubernetes CRDs, OpenAPI, AsyncAPI, Avro, Protobuf, and CNCF projects, focusing on robust lifecycle management and clear responsibilities.

### 1. Schema Governance Model
The AI-OS employs a federated governance model for its schemas, balancing centralized oversight with distributed development. Core schemas (defined in this document) are centrally governed to ensure interoperability and foundational stability. Domain-specific schemas, built upon these core types, may adopt more decentralized governance but must adhere to the overarching principles and processes defined herein.

### 2. Schema Ownership
Each top-level schema (e.g., Agent Schema, Workflow Schema) has a designated **Schema Owner**. The Schema Owner is a team or individual responsible for:
- Defining the schema's purpose, fields, and validation rules.
- Ensuring the schema meets functional requirements and architectural principles.
- Managing the schema's lifecycle, including versioning, deprecation, and evolution.
- Responding to change requests and issues related to their schema.
- Ensuring adequate documentation and examples are provided.

For shared types, ownership is established at the point of definition, with consuming teams acting as stakeholders.

### 3. Schema Stewardship
**Schema Stewards** are individuals or a small group of experts (often from the Architecture Council or a dedicated Schema Working Group) responsible for:
- Maintaining the integrity and consistency of the overall schema ecosystem.
- Enforcing governance policies, naming conventions, and best practices.
- Providing guidance and support to Schema Owners.
- Facilitating cross-schema compatibility and reuse.
- Reviewing schema proposals for architectural soundness and adherence to standards.

### 4. Schema Review Process
All proposed schema changes, including new schemas, modifications to existing schemas, or deprecations, must undergo a formal review process:
1.  **Proposal Submission**: Schema Owner submits a pull request or proposal document outlining the change, its rationale, impact analysis, and migration plan.
2.  **Automated Checks**: Automated tools perform linting, syntax validation, and basic compatibility checks against the proposed changes.
3.  **Peer Review**: Domain experts and affected Schema Owners review the proposal for correctness, completeness, and adherence to requirements.
4.  **Stewardship Review**: Schema Stewards conduct an architectural review, focusing on governance, compatibility, security, and long-term maintainability.
5.  **Impact Assessment**: A thorough assessment of backward and forward compatibility, potential breaking changes, and necessary migration efforts is conducted.

### 5. Schema Approval Workflow
Following a successful review, schema changes proceed through an approval workflow:
1.  **Consensus by Reviewers**: All required reviewers (peers and stewards) must approve the change.
2.  **Owner Sign-off**: The Schema Owner for the affected schema(s) provides final approval.
3.  **Architecture Council Endorsement (for Major Changes)**: Significant architectural changes or breaking changes to core schemas require explicit endorsement from the AI-OS Architecture Council.
4.  **Publication**: Upon approval, the schema is published to the Schema Registry.

### 6. Schema Registry Architecture
The AI-OS Schema Registry is a centralized, versioned repository for all formal schemas. It is designed to be highly available, discoverable, and capable of serving schemas to agents and system components at runtime.
-   **Storage**: Schemas are stored as versioned artifacts (e.g., JSON Schema files, Protobuf `.proto` files) with associated metadata.
-   **API**: Provides RESTful APIs for schema registration, retrieval, and search.
-   **Versioning**: Supports multiple versions of each schema, allowing consumers to specify the version they require.
-   **Validation**: Integrates with schema validation engines to provide runtime validation services.
-   **Auditing**: Maintains a complete audit trail of all schema changes, including who made the change, when, and approvals.

### 7. Schema Publication Lifecycle
The publication lifecycle defines the states a schema transitions through:
-   **Draft**: Initial development phase, not yet visible to consumers.
-   **Pending Review**: Submitted for the formal review process.
-   **Approved**: Ready for publication.
-   **Published**: Available in the Schema Registry for consumption.
-   **Deprecated**: Still available but discouraged for new use, with an end-of-life date.
-   **Archived**: Removed from active use, but historical versions retained for auditing/migration.

### 8. Schema Discovery Mechanisms
Agents and system components discover schemas through:
-   **Registry API**: Direct queries to the Schema Registry by schema name, type, or tags.
-   **Capability Descriptors**: Agents advertise the schemas for their inputs/outputs within their Capability Schema.
-   **Shared Context**: Context objects explicitly reference the schema governing their `data` field.
-   **Documentation Portals**: Human-readable documentation linked to the Schema Registry provides detailed schema descriptions and examples.

### 9. Schema Registry APIs (Conceptual)
The Schema Registry exposes a set of conceptual APIs:
-   `POST /schemas`: Register a new schema version.
-   `GET /schemas/{id}`: Retrieve a specific schema by ID.
-   `GET /schemas/{name}/latest`: Retrieve the latest approved version of a schema by name.
-   `GET /schemas/{name}/version/{version}`: Retrieve a specific version of a schema by name.
-   `GET /schemas?query=...`: Search schemas by tags, description, or fields.
-   `POST /validate/{schemaId}`: Validate a given payload against a specific schema.

### 10. Canonical Serialization Rules
To ensure consistent interpretation and efficient processing, all data conforming to AI-OS schemas must adhere to canonical serialization rules, regardless of the underlying transport or storage mechanism.
-   **JSON Serialization**:
    -   **UTF-8 Encoding**: All JSON strings must be UTF-8 encoded.
    -   **No Trailing Commas**: Trailing commas are disallowed.
    -   **Member Ordering**: Object members must be sorted lexicographically by key.
    -   **Compact Representation**: No unnecessary whitespace (e.g., between keys, colons, commas).
    -   **Floating-point Representation**: Use standard decimal representation; avoid scientific notation unless necessary for precision (e.g., `1.0` not `1.000`).
    -   **Integer Representation**: Standard decimal representation.
    -   **Boolean Representation**: `true` or `false`.
    -   **Null Representation**: `null`.
-   **YAML Serialization**:
    -   **JSON Schema Conformance**: YAML representations must be parseable as JSON and conform to the schema's JSON Schema definition.
    -   **Recommended Style**: Prefer block scalars for multi-line strings, explicit typing where ambiguity exists.
    -   **Key Ordering**: Maintain lexicographical ordering for object keys where possible for consistency.

### 11. Reserved Fields Policy
A set of field names are reserved across all AI-OS schemas to prevent conflicts and ensure architectural consistency:
-   `id`, `_id`, `uuid`, `_uuid`: Reserved for primary identifiers.
-   `version`, `_version`: Reserved for semantic versioning.
-   `createdAt`, `updatedAt`, `timestamp`, `_timestamp`: Reserved for ISO 8601 timestamps.
-   `metadata`, `_metadata`: Reserved for arbitrary, non-validated key-value pairs.
-   `tags`, `_tags`: Reserved for categorization labels.
-   `schema`, `_schema`: Reserved for schema references.
-   `status`, `_status`: Reserved for operational status.

New top-level fields should avoid these names unless their purpose aligns precisely with the reserved definition.

### 12. Extension Mechanisms
Schemas support well-defined extension mechanisms to allow for custom fields without breaking compatibility:
-   **`metadata` field**: Arbitrary key-value pairs that are not validated by the primary schema. Intended for non-critical, application-specific data.
-   **`additionalProperties: true`**: In JSON Schema, allows for additional, unspecified fields in an object. This is used in the `metadata` fields and for `parameters` objects where flexible extension is needed.
-   **Open Ended Objects**: Schemas like `Knowledge Object`'s `content` or `Shared Context`'s `data` use `{}` as their schema, allowing full flexibility, but encouraging the use of the `schema` field to reference a specific, validating schema for that content.

### 13. Unknown Field Handling
When processing incoming data:
-   **Strict Parsing (Default)**: Parsers SHOULD by default reject payloads containing unknown fields at the root level or in strictly defined nested objects (i.e., where `additionalProperties: false` is implicit or explicit).
-   **Permissive Parsing (for Extensions)**: For fields explicitly designed for extension (e.g., `metadata`, `parameters`, or where `additionalProperties: true`), unknown fields MUST be ignored and retained without error.
-   **Forward Compatibility**: Consumers MUST be robust to encountering unknown fields. They should ignore any fields they do not understand rather than failing, unless specifically configured for strict validation.

### 14. Required vs Optional Field Policy
-   **Required Fields**: ONLY critical fields necessary for the schema's core function and data integrity are marked as `required`. Omitting a required field MUST result in a validation error.
-   **Optional Fields**: All other fields are `optional`. Consumers MUST gracefully handle the absence of optional fields by providing sensible defaults or null values.
-   **Default Values**: When a field has a well-defined default, it should be explicitly stated in the documentation (and ideally in the JSON Schema using `default` keyword).

### 15. Nullable Field Guidelines
-   **Explicit Nullability**: Fields that can legitimately be `null` MUST explicitly define `"type": ["string", "null"]` (or other type combinations) in their JSON Schema.
-   **Omitting vs Null**: For optional fields, distinguishing between an omitted field and a field present with a `null` value is important.
    -   **Omitted**: The field is not present in the payload. Consumers should apply default logic.
    -   **`null`**: The field is explicitly present with no value. Consumers should process this as a distinct state, potentially overriding a default.
-   **Semantics**: Document the semantic difference between `null` and omission for specific fields where it matters.

### 16. Naming RFC (Request For Comments)
All schema entities, fields, and enumerations adhere to the following naming conventions:
-   **Schema Names**: PascalCase (e.g., `AgentSchema`, `WorkflowStep`).
-   **Field Names**: camelCase (e.g., `agentId`, `workflowId`, `createdAt`).
-   **Enum Values**: snake_case or SCREAMING_SNAKE_CASE for constants (e.g., `simple_majority`, `active`, `pending`, `UUID_PATTERN`).
-   **UUID Fields**: Fields representing UUIDs should typically end with `Id` (e.g., `agentId`, `taskId`).
-   **Timestamp Fields**: Fields representing timestamps should end with `At` (e.g., `createdAt`, `updatedAt`, `timestamp`).
-   **Arrays**: Plural nouns for array fields (e.g., `capabilities`, `steps`, `tags`).

This RFC ensures consistency and readability across the schema definitions.

### 17. Semantic Versioning Rules
All schemas adhere strictly to [Semantic Versioning 2.0.0](https://semver.org/) (MAJOR.MINOR.PATCH) for their `version` field.
-   **MAJOR version (1.x.x)**: Incremented for **breaking changes**.
    -   Examples: Removing a required field, changing the data type of an existing field, renaming a required field, fundamentally altering core semantics.
-   **MINOR version (x.1.x)**: Incremented for **backward-compatible new features**.
    -   Examples: Adding an optional field, adding new enum values, adding new top-level schemas (without breaking existing ones).
-   **PATCH version (x.x.1)**: Incremented for **backward-compatible bug fixes**.
    -   Examples: Clarifying documentation, fixing minor typos in descriptions, adjusting non-enforced validation patterns without changing semantics.
Pre-release identifiers (e.g., `1.0.0-alpha.1`) and build metadata (e.g., `1.0.0+20230101`) may be used as per SemVer spec.

### 18. Backward Compatibility Matrix
The following matrix defines the acceptable changes for each version segment:

| Change Type               | MAJOR | MINOR | PATCH |
| :------------------------ | :---- | :---- | :---- |
| Add new optional field    | Yes   | Yes   | Yes   |
| Add new enum value        | Yes   | Yes   | Yes   |
| Add new top-level schema  | Yes   | Yes   | Yes   |
| Add new read-only property| Yes   | Yes   | Yes   |
| Increase max length/value | Yes   | Yes   | Yes   |
| Make optional field required | Yes   | No    | No    |
| Remove field              | Yes   | No    | No    |
| Rename field              | Yes   | No    | No    |
| Change field type         | Yes   | No    | No    |
| Decrease max length/value | Yes   | No    | No    |
| Remove enum value         | Yes   | No    | No    |
| Change field semantics    | Yes   | No    | No    |

### 19. Forward Compatibility Rules
Consumers of AI-OS schemas MUST implement forward compatibility by:
-   **Ignoring Unknown Fields**: Consumers MUST gracefully ignore any unknown fields encountered in a payload rather than failing. This ensures that a consumer built against an older schema version can still process data from a newer, backward-compatible producer.
-   **Tolerating New Enum Values**: Consumers SHOULD be able to process new enum values as unknown but valid, falling back to a default behavior or logging a warning, rather than rejecting the payload outright.
-   **Graceful Degradation**: If a new, optional field is added that provides enhanced functionality, older consumers should continue to operate without that enhancement rather than failing.

### 20. Breaking Change Policy
Breaking changes are a last resort and MUST be avoided whenever possible. When unavoidable, they require:
1.  **Strict Approval**: Explicit approval from the Architecture Council.
2.  **Advanced Notice**: Minimum of 3 months notice to all affected consumers.
3.  **Migration Guide**: Comprehensive migration guides detailing how to adapt to the new schema.
4.  **Grace Period**: Concurrent support for both old and new versions for a defined transition period (e.g., 6-12 months).
5.  **Automated Tooling (where possible)**: Provision of scripts or tools to aid in data migration or code refactoring.

### 21. Non-Breaking Change Policy
Non-breaking changes are preferred for schema evolution. These include:
-   Adding new optional fields.
-   Adding new enum values.
-   Adding new schemas.
-   Making an optional field with a default value truly optional (by removing the `default` keyword if it's not strictly necessary for validation).
These changes do not require explicit consumer action to maintain basic functionality.

### 22. Deprecation Lifecycle
A formal deprecation lifecycle manages the removal of schema fields or entire schemas:
1.  **Announcement**: Announce deprecation with a clear rationale and timeline for removal (minimum 6 months).
2.  **Mark as Deprecated**: Mark the field/schema as deprecated in its definition and documentation (e.g., using a `@deprecated` tag or equivalent).
3.  **Warning in Validation**: Validation tools should issue warnings when deprecated fields are used.
4.  **Removal**: After the deprecation period, the field/schema is removed in a MAJOR version increment.

### 23. Schema Evolution Examples
-   **Adding an Optional Field**: `v1.0.0` has `fieldA`. `v1.1.0` adds `fieldB` (optional). Consumers of `v1.0.0` can still process `v1.1.0` payloads, ignoring `fieldB`.
-   **Renaming a Field (Breaking)**: `v1.0.0` has `oldField`. Renaming to `newField` in `v2.0.0` is a breaking change, requiring consumers to update.
-   **Changing Type (Breaking)**: `v1.0.0` has `count: integer`. Changing to `count: string` in `v2.0.0` is a breaking change.

### 24. Migration Guidelines
When schema changes require migration, the following guidelines apply:
-   **Identify Affected Systems**: Determine all producers and consumers impacted by the change.
-   **Data Migration**: For changes to stored data, define and implement data transformation scripts.
-   **Code Migration**: Provide clear instructions and code examples for updating client code.
-   **Rollback Plan**: Always have a rollback strategy in case of migration failures.
-   **Testing**: Thoroughly test migration paths in staging environments before production deployment.

### 25. Contract Testing Strategy
AI-OS employs a robust contract testing strategy to ensure producer-consumer compatibility:
-   **Consumer-Driven Contracts (CDC)**: Consumers define the expected schema (contract) for the data they consume. Producers implement and verify against these contracts.
-   **Automated Contract Verification**: CI/CD pipelines automatically verify that schema changes from producers do not break existing consumer contracts.
-   **Schema Registry Integration**: The Schema Registry can store consumer contracts and provide APIs for producers to query compatibility.
-   **Tooling**: Use tools like Pact, Spring Cloud Contract, or custom solutions to manage and enforce contracts.

### 26. Producer/Consumer Compatibility Rules
-   **Producer Compatibility**: Producers MUST ensure that new versions of their generated data are backward-compatible with older consumer schema versions (within the defined compatibility window). They SHOULD also aim for forward compatibility to allow newer consumers to interpret older data.
-   **Consumer Compatibility**: Consumers MUST be designed for forward compatibility, gracefully handling new fields and enum values as per the Forward Compatibility Rules. They SHOULD declare the minimum schema version they are compatible with.

### 27. Validation Lifecycle
Schemas are validated at multiple stages throughout their lifecycle:
-   **Design-time Validation**: JSON Schema definitions are validated for syntactical correctness and adherence to meta-schema.
-   **Build-time Validation**: Code generation tools validate data structures against schemas.
-   **Deployment-time Validation**: Configuration files and deployment manifests are validated against relevant schemas before deployment.
-   **Runtime Validation**: Incoming messages and data payloads are validated against the expected schema at the point of ingestion (e.g., API gateways, message brokers).

### 28. Runtime Validation Requirements
-   **Mandatory for Ingress**: All data entering the AI-OS system from external sources or between major components MUST undergo runtime validation against the expected schema version.
-   **Error Handling**: Validation failures MUST result in well-defined error responses, including detailed validation reports.
-   **Performance**: Runtime validation mechanisms MUST be performant to avoid introducing significant latency.
-   **Configurable Strictness**: Validation engines should allow configurable strictness (e.g., warn on unknown fields vs. reject).

### 29. Compile-Time Validation Guidance
For languages with strong typing, compile-time validation is highly recommended:
-   **Code Generation**: Use schema-to-code generation tools (e.g., for Protobuf, Avro, OpenAPI client generation) to create strongly typed data structures. This shifts many validation errors to compile-time.
-   **Static Analysis**: Integrate static analysis tools that can detect potential schema mismatches or incorrect data usage at compile time.

### 30. Schema Quality Gates
Schemas must pass specific quality gates before being published:
-   **Completeness**: All required fields, descriptions, and examples are present.
-   **Correctness**: JSON Schema is valid and accurately reflects the intended data structure.
-   **Consistency**: Adheres to naming conventions, field definitions, and architectural patterns.
-   **Testability**: Can be easily validated and used in contract tests.
-   **Security Review**: Reviewed for potential security implications (e.g., sensitive data exposure, recursive definitions).

### 31. Schema Linting Requirements
All schemas MUST be linted using a standardized tool (e.g., `ajv` or `spectral` for JSON Schema) to enforce:
-   Naming conventions.
-   Correct use of keywords (e.g., `type`, `properties`, `required`, `enum`).
-   Presence of descriptions for all fields.
-   Avoidance of anti-patterns (e.g., overly permissive `additionalProperties`).
Linting must be integrated into CI/CD pipelines as a mandatory step.

### 32. Schema Documentation Standards
Schema documentation MUST be comprehensive, machine-readable, and human-readable.
-   **Inline Descriptions**: Every field, enum, and top-level schema MUST have a clear, concise `description`.
-   **ReadMe Files**: Each major schema or schema group should have a `README.md` explaining its purpose, usage, examples, and relationships to other schemas.
-   **Automated Generation**: Documentation SHOULD be generated automatically from the schema definitions (e.g., OpenAPI docs from OpenAPI spec).
-   **Examples**: Provide canonical YAML and JSON examples for each schema.
-   **Cross-referencing**: Link related schemas and definitions.

### 33. Cross-Schema References
Schemas often need to reference other schemas.
-   **Internal References**: Use JSON Schema `$ref` keyword (e.g., `"$ref": "#/definitions/capability"`) for references within the same document or `"$ref": "common.json#/definitions/address"` for external files.
-   **External References**: For schemas hosted in the Registry, references can be by URI (e.g., `"schema": "https://registry.ai-os.com/schemas/market-data-v1.json"`).
-   **Type Reuse**: Prefer referencing existing common types rather than redefining them to reduce redundancy and improve consistency.

### 34. Shared Type Reuse Strategy
To maximize consistency and minimize redundancy:
-   **Identify Common Types**: Regularly identify data structures that are reused across multiple schemas (e.g., `UUID`, `ISO8601Timestamp`, `AccessPolicy`, `Metadata`, `Tags`).
-   **Define in Common Schema**: Define these common types in a dedicated "Common Types" schema or a shared `definitions` block.
-   **Reference, Don't Duplicate**: All schemas MUST reference these common types using `$ref` instead of duplicating their definitions.
-   **Ownership**: Common types are owned by the Schema Stewardship group.

## Table of Contents
1. [Schema Architecture Specification](#schema-architecture-specification)
   1. [Schema Governance Model](#schema-governance-model)
   2. [Schema Ownership](#schema-ownership)
   3. [Schema Stewardship](#schema-stewardship)
   4. [Schema Review Process](#schema-review-process)
   5. [Schema Approval Workflow](#schema-approval-workflow)
   6. [Schema Registry Architecture](#schema-registry-architecture)
   7. [Schema Publication Lifecycle](#schema-publication-lifecycle)
   8. [Schema Discovery Mechanisms](#schema-discovery-mechanisms)
   9. [Schema Registry APIs (Conceptual)](#schema-registry-apis-conceptual)
   10. [Canonical Serialization Rules](#canonical-serialization-rules)
   11. [Reserved Fields Policy](#reserved-fields-policy)
   12. [Extension Mechanisms](#extension-mechanisms)
   13. [Unknown Field Handling](#unknown-field-handling)
   14. [Required vs Optional Field Policy](#required-vs-optional-field-policy)
   15. [Nullable Field Guidelines](#nullable-field-guidelines)
   16. [Naming RFC](#naming-rfc)
   17. [Semantic Versioning Rules](#semantic-versioning-rules)
   18. [Backward Compatibility Matrix](#backward-compatibility-matrix)
   19. [Forward Compatibility Rules](#forward-compatibility-rules)
   20. [Breaking Change Policy](#breaking-change-policy)
   21. [Non-Breaking Change Policy](#non-breaking-change-policy)
   22. [Deprecation Lifecycle](#deprecation-lifecycle)
   23. [Schema Evolution Examples](#schema-evolution-examples)
   24. [Migration Guidelines](#migration-guidelines)
   25. [Contract Testing Strategy](#contract-testing-strategy)
   26. [Producer/Consumer Compatibility Rules](#producer/consumer-compatibility-rules)
   27. [Validation Lifecycle](#validation-lifecycle)
   28. [Runtime Validation Requirements](#runtime-validation-requirements)
   29. [Compile-Time Validation Guidance](#compile-time-validation-guidance)
   30. [Schema Quality Gates](#schema-quality-gates)
   31. [Schema Linting Requirements](#schema-linting-requirements)
   32. [Schema Documentation Standards](#schema-documentation-standards)
   33. [Cross-Schema References](#cross-schema-references)
   34. [Shared Type Reuse Strategy](#shared-type-reuse-strategy)
   35. [Schema Performance Considerations](#schema-performance-considerations)
   36. [Maximum Payload Recommendations](#maximum-payload-recommendations)
   37. [Schema Security Considerations](#schema-security-considerations)
   38. [Sensitive Field Classification](#sensitive-field-classification)
   39. [Encryption Metadata Guidance](#encryption-metadata-guidance)
   40. [Schema Conformance Requirements](#schema-conformance-requirements)
   41. [Conformance Test Recommendations](#conformance-test-recommendations)
   42. [Compliance Checklist](#compliance-checklist)
2. [Agent Schema](#agent-schema)
2. [Capability Schema](#capability-schema)
3. [Workflow Schema](#workflow-schema)
4. [Task Schema](#task-schema)
5. [Council Schema](#council-schema)
6. [Vote Schema](#vote-schema)
7. [Shared Context Schema](#shared-context-schema)
8. [Knowledge Object Schema](#knowledge-object-schema)
9. [Memory Object Schema](#memory-object-schema)
10. [Runtime Schema](#runtime-schema)
11. [Scheduler Schema](#scheduler-schema)
12. [Plugin Schema](#plugin-schema)
13. [Tool Schema](#tool-schema)
14. [Message Schema](#message-schema)
15. [Event Schema](#event-schema)
16. [Execution Plan Schema](#execution-plan-schema)
17. [Checkpoint Schema](#checkpoint-schema)
18. [Configuration Schema](#configuration-schema)
19. [Health Report Schema](#health-report-schema)

---

## Agent Schema

### Purpose
Defines the structure for agent descriptors used in discovery, registration, and capability advertisement. Agents use this schema to announce their presence, capabilities, and operational status to the collaboration ecosystem.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `agentId` | string | Unique identifier for the agent (UUID v4 recommended) |
| `name` | string | Human-readable name for the agent |
| `version` | string | Semantic version of the agent implementation |
| `description` | string | Brief description of the agent's purpose and functionality |
| `capabilities` | array[Capability] | List of capabilities the agent provides |
| `endpoints` | object | Communication endpoints (e.g., `{ "http": "http://agent.example.com/api" }`) |
| `status` | string | Current operational status (`active`, `inactive`, `maintenance`, `error`) |
| `metadata` | object | Arbitrary key-value pairs for agent-specific metadata |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdAt` | string (ISO 8601) | Timestamp when the agent was registered |
| `updatedAt` | string (ISO 8601) | Timestamp when the agent descriptor was last updated |

### Required Fields
- `agentId`
- `name`
- `version`
- `capabilities`
- `status`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `endpoints`
- `metadata`
- `tags`

### Validation Rules
- `agentId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `status` must be one of: `active`, `inactive`, `maintenance`, `error`
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- Each capability in `capabilities` must conform to the Capability Schema
- Endpoint URLs must be valid URIs if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent Descriptor",
  "type": "object",
  "required": ["agentId", "name", "version", "capabilities", "status", "createdAt", "updatedAt"],
  "properties": {
    "agentId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "capabilities": {
      "type": "array",
      "items": { "$ref": "#/definitions/capability" },
      "minItems": 1
    },
    "endpoints": {
      "type": "object",
      "additionalProperties": { "type": "string", "format": "uri" }
    },
    "status": {
      "type": "string",
      "enum": ["active", "inactive", "maintenance", "error"]
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" }
  },
  "definitions": {
    "capability": {
      "type": "object",
      "required": ["capabilityId", "name", "version"],
      "properties": {
        "capabilityId": { "type": "string" },
        "name": { "type": "string", "minLength": 1 },
        "version": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
        },
        "description": { "type": "string" },
        "inputSchema": { "type": ["object", "null"] },
        "outputSchema": { "type": ["object", "null"] },
        "parameters": {
          "type": "object",
          "additionalProperties": true
        }
      }
    }
  }
}
```

### YAML Example
```yaml
agentId: "123e4567-e89b-12d3-a456-426614174000"
name: "Data Processing Agent"
version: "1.2.3"
description: "Agent specialized in data transformation and analysis tasks"
capabilities:
  - capabilityId: "data-transform-v1"
    name: "Data Transformation"
    version: "1.0.0"
    description: "Transforms data between various formats"
    inputSchema:
      type: object
      properties:
        inputData:
          type: string
        format:
          type: string
          enum: [json, xml, csv]
    outputSchema:
      type: object
      properties:
        transformedData:
          type: string
    parameters:
      timeoutSeconds: 30
endpoints:
  http: "http://data-agent.example.com/api"
status: "active"
metadata:
  owner: "data-team"
  department: "analytics"
tags:
  - "data"
  - "processing"
  - "transformation"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:30:00Z"
```

### Migration Rules
- When upgrading from v1 to v2: Add `metadata` field (optional) and change `status` enum to include `maintenance`
- When adding new endpoint types: Extend `endpoints` object with new keys (backward compatible)
- Version changes in `version` field follow semantic versioning rules

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Compatible with agent descriptors from Parts 1-11
- Aligns with discovery service interfaces in Section 12.3

---

## Capability Schema

### Purpose
Defines the structure for individual capabilities that agents can advertise and invoke. This schema describes what a capability does, its input/output requirements, and any parameters needed for invocation.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `capabilityId` | string | Unique identifier for the capability (within the agent) |
| `name` | string | Human-readable name for the capability |
| `version` | string | Semantic version of the capability |
| `description` | string | Detailed description of what the capability does |
| `inputSchema` | object or null | JSON Schema defining valid inputs for the capability |
| `outputSchema` | object or null | JSON Schema defining outputs produced by the capability |
| `parameters` | object | Configuration parameters for the capability |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdAt` | string (ISO 8601) | Timestamp when the capability was registered |
| `updatedAt` | string (ISO 8601) | Timestamp when the capability was last modified |

### Required Fields
- `capabilityId`
- `name`
- `version`

### Optional Fields
- `description`
- `inputSchema`
- `outputSchema`
- `parameters`
- `tags`
- `createdAt`
- `updatedAt`

### Validation Rules
- `capabilityId` must be unique within the agent's capabilities
- `version` must follow semantic versioning (major.minor.patch)
- If `inputSchema` is provided, it must be a valid JSON Schema
- If `outputSchema` is provided, it must be a valid JSON Schema
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps if provided
- `updatedAt` must be greater than or equal to `createdAt` if both are provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Capability Descriptor",
  "type": "object",
  "required": ["capabilityId", "name", "version"],
  "properties": {
    "capabilityId": { "type": "string", "minLength": 1 },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "inputSchema": { "type": ["object", "null"] },
    "outputSchema": { "type": ["object", "null"] },
    "parameters": {
      "type": "object",
      "additionalProperties": true
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" }
  }
}
```

### YAML Example
```yaml
capabilityId: "data-transform-v1"
name: "Data Transformation"
version: "1.0.0"
description: "Transforms data between various formats (JSON, XML, CSV)"
inputSchema:
  type: object
  properties:
    inputData:
      type: string
      minLength: 1
    format:
      type: string
      enum: [json, xml, csv]
  required: [inputData, format]
outputSchema:
  type: object
  properties:
    transformedData:
      type: string
      minLength: 1
    format:
      type: string
      enum: [json, xml, csv]
  required: [transformedData, format]
parameters:
  timeoutSeconds: 30
  maxRetries: 3
tags:
  - "data"
  - "transformation"
  - "format-conversion"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:30:00Z"
```

### Migration Rules
- When adding input/output schemas: Ensure they are valid JSON Schema objects
- When deprecating parameters: Mark them as deprecated in documentation but keep in schema for backward compatibility
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used within Agent Schema capabilities array
- Referenced by task delegation and workflow systems

---

## Workflow Schema

### Purpose
Defines the structure for workflow definitions that orchestrate complex multi-agent tasks. Workflows describe sequences of steps, dependencies, and execution logic for collaborative agent processes.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `workflowId` | string | Unique identifier for the workflow (UUID v4 recommended) |
| `name` | string | Human-readable name for the workflow |
| `version` | string | Semantic version of the workflow definition |
| `description` | string | Detailed description of what the workflow accomplishes |
| `steps` | array[WorkflowStep] | Ordered list of steps in the workflow execution |
| `dependencies` | object | Dependency relationships between workflow steps |
| `inputs` | object | JSON Schema defining valid inputs for the workflow |
| `outputs` | object | JSON Schema defining expected outputs from the workflow |
| `parameters` | object | Configuration parameters for workflow execution |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdAt` | string (ISO 8601) | Timestamp when the workflow was registered |
| `updatedAt` | string (ISO 8601) | Timestamp when the workflow was last modified |

### WorkflowStep Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `stepId` | string | Unique identifier for the step within the workflow |
| `name` | string | Human-readable name for the step |
| `description` | string | Detailed description of what the step does |
| `agentSelector` | object | Criteria for selecting agents to execute this step |
| `capabilityRequired` | string | CapabilityId required for agents to execute this step |
| `inputMapping` | object | Mapping from workflow inputs to step inputs |
| `outputMapping` | object | Mapping from step outputs to workflow outputs |
| `timeoutSeconds` | integer | Maximum time allowed for step execution |
| `retryPolicy` | object | Policy for retrying failed step executions |
| `dependsOn` | array[string] | List of stepIds that must complete before this step |
| `condition` | string | Expression that must evaluate to true for step execution |

### Required Fields
- `workflowId`
- `name`
- `version`
- `steps`

### Optional Fields
- `description`
- `dependencies`
- `inputs`
- `outputs`
- `parameters`
- `tags`
- `createdAt`
- `updatedAt`

### Validation Rules
- `workflowId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- Each step in `steps` must have a unique `stepId`
- `dependsOn` references must point to existing stepIds in the same workflow
- If `inputs` is provided, it must be a valid JSON Schema
- If `outputs` is provided, it must be a valid JSON Schema
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps if provided
- `updatedAt` must be greater than or equal to `createdAt` if both are provided
- `timeoutSeconds` must be a positive integer if provided
- `agentSelector` must conform to the AgentSelector structure
- `retryPolicy` must conform to the RetryPolicy structure

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Workflow Definition",
  "type": "object",
  "required": ["workflowId", "name", "version", "steps"],
  "properties": {
    "workflowId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "steps": {
      "type": "array",
      "items": { "$ref": "#/definitions/workflowStep" },
      "minItems": 1
    },
    "dependencies": {
      "type": "object",
      "additionalProperties": {
        "type": "array",
        "items": { "type": "string" }
      }
    },
    "inputs": { "type": ["object", "null"] },
    "outputs": { "type": ["object", "null"] },
    "parameters": {
      "type": "object",
      "additionalProperties": true
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" }
  },
  "definitions": {
    "workflowStep": {
      "type": "object",
      "required": ["stepId", "name", "agentSelector", "capabilityRequired"],
      "properties": {
        "stepId": { "type": "string", "minLength": 1 },
        "name": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "agentSelector": {
          "type": "object",
          "required": ["capabilityIds"],
          "properties": {
            "capabilityIds": {
              "type": "array",
              "items": { "type": "string" },
              "minItems": 1
            },
            "tags": {
              "type": "array",
              "items": { "type": "string" }
            },
            "metadataMatches": {
              "type": "object",
              "additionalProperties": { "type": "string" }
            },
            "excludeAgentIds": {
              "type": "array",
              "items": { "type": "string" }
            }
          }
        },
        "capabilityRequired": { "type": "string" },
        "inputMapping": {
          "type": "object",
          "additionalProperties": { "type": "string" }
        },
        "outputMapping": {
          "type": "object",
          "additionalProperties": { "type": "string" }
        },
        "timeoutSeconds": {
          "type": "integer",
          "minimum": 1
        },
        "retryPolicy": {
          "type": "object",
          "properties": {
            "maxAttempts": {
              "type": "integer",
              "minimum": 1,
              "default": 3
            },
            "backoffSeconds": {
              "type": "integer",
              "minimum": 1,
              "default": 5
            },
            "backoffMultiplier": {
              "type": "number",
              "minimum": 1.0,
              "default": 2.0
            }
          }
        },
        "dependsOn": {
          "type": "array",
          "items": { "type": "string" }
        },
        "condition": { "type": "string" }
      }
    }
  }
}
```

### YAML Example
```yaml
workflowId: "123e4567-e89b-12d3-a456-426614174001"
name: "Data Processing Pipeline"
version: "1.0.0"
description: "Workflow for ingesting, transforming, and analyzing data"
steps:
  - stepId: "ingest-data"
    name: "Ingest Data"
    description: "Fetch raw data from external sources"
    agentSelector:
      capabilityIds:
        - "data-ingest-v1"
      tags: ["ingestion"]
    capabilityRequired: "data-ingest-v1"
    inputMapping:
      sourceUrl: "inputs.sourceUrl"
    outputMapping:
      rawData: "outputs.rawData"
    timeoutSeconds: 300
    retryPolicy:
      maxAttempts: 3
      backoffSeconds: 5
    dependsOn: []
  - stepId: "transform-data"
    name: "Transform Data"
    description: "Convert raw data to standardized format"
    agentSelector:
      capabilityIds:
        - "data-transform-v1"
      tags: ["transformation"]
    capabilityRequired: "data-transform-v1"
    inputMapping:
      rawData: "steps.ingest-data.outputs.rawData"
    outputMapping:
      transformedData: "outputs.transformedData"
    timeoutSeconds: 600
    retryPolicy:
      maxAttempts: 2
      backoffSeconds: 10
    dependsOn: ["ingest-data"]
  - stepId: "analyze-data"
    name: "Analyze Data"
    description: "Perform statistical analysis on transformed data"
    agentSelector:
      capabilityIds:
        - "data-analyze-v1"
      tags: ["analysis"]
    capabilityRequired: "data-analyze-v1"
    inputMapping:
      transformedData: "steps.transform-data.outputs.transformedData"
    outputMapping:
      analysisResults: "outputs.analysisResults"
    timeoutSeconds: 900
    retryPolicy:
      maxAttempts: 2
      backoffSeconds: 15
    dependsOn: ["transform-data"]
inputs:
  type: object
  properties:
    sourceUrl:
      type: string
      format: uri
  required: [sourceUrl]
outputs:
  type: object
  properties:
    rawData:
      type: string
    transformedData:
      type: string
    analysisResults:
      type: object
  required: [analysisResults]
parameters:
  maxParallelSteps: 2
  failureHandling: "stop"
tags:
  - "data"
  - "pipeline"
  - "etl"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:30:00Z"
```

### Migration Rules
- When adding new step types: Extend the workflowStep definition with new optional fields
- When changing dependency syntax: Provide migration tools to convert old formats
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by workflow orchestration engines (Section 12.4)
- References Agent Schema for agent selection
- References Capability Schema for capability requirements

---

## Task Schema

### Purpose
Defines the structure for individual units of work that can be delegated to agents. Tasks represent specific actions to be performed and include all necessary information for execution.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `taskId` | string | Unique identifier for the task (UUID v4 recommended) |
| `name` | string | Human-readable name for the task |
| `description` | string | Detailed description of what the task accomplishes |
| `capabilityRequired` | string | CapabilityId required for an agent to execute this task |
| `input` | object | Input data for the task execution |
| `expectedOutput` | object | Expected structure of the task output |
| `priority` | string | Priority level (`low`, `normal`, `high`, `critical`) |
| `status` | string | Current status (`pending`, `assigned`, `in_progress`, `completed`, `failed`, `cancelled`) |
| `assignedTo` | string or null | AgentId of the agent assigned to execute the task |
| `createdBy` | string | AgentId or userId that created the task |
| `createdAt` | string (ISO 8601) | Timestamp when the task was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the task was last updated |
| `startedAt` | string (ISO 8601) or null | Timestamp when task execution started |
| `completedAt` | string (ISO 8601) or null | Timestamp when task execution completed |
| `timeoutSeconds` | integer | Maximum time allowed for task execution |
| `retryCount` | integer | Number of times the task has been retried |
| `maxRetries` | integer | Maximum number of retries allowed |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for task-specific metadata |
| `dependencies` | array[string] | List of taskIds that must complete before this task can start |
| `result` | object or null | Actual output/result from task execution |

### Required Fields
- `taskId`
- `name`
- `capabilityRequired`
- `priority`
- `status`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `input`
- `expectedOutput`
- `assignedTo`
- `startedAt`
- `completedAt`
- `timeoutSeconds`
- `retryCount`
- `maxRetries`
- `tags`
- `metadata`
- `dependencies`
- `result`

### Validation Rules
- `taskId` must be a valid UUID v4 string
- `capabilityRequired` must reference a valid capabilityId from an agent's capabilities
- `priority` must be one of: `low`, `normal`, `high`, `critical`
- `status` must be one of: `pending`, `assigned`, `in_progress`, `completed`, `failed`, `cancelled`
- If `assignedTo` is provided, it must be a valid UUID v4 string
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for users)
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `startedAt` is provided, it must be a valid ISO 8601 timestamp and greater than or equal to `createdAt`
- If `completedAt` is provided, it must be a valid ISO 8601 timestamp and greater than or equal to `startedAt` (if provided)
- `timeoutSeconds` must be a positive integer if provided
- `retryCount` must be a non-negative integer
- `maxRetries` must be a non-negative integer
- `retryCount` must be less than or equal to `maxRetries`
- Each dependency in `dependencies` must be a valid UUID v4 string
- `input` must conform to the capability's inputSchema if provided
- `expectedOutput` must conform to the capability's outputSchema if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Task Definition",
  "type": "object",
  "required": ["taskId", "name", "capabilityRequired", "priority", "status", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "taskId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "description": { "type": "string" },
    "capabilityRequired": { "type": "string", "minLength": 1 },
    "input": { "type": ["object", "null"] },
    "expectedOutput": { "type": ["object", "null"] },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high", "critical"]
    },
    "status": {
      "type": "string",
      "enum": ["pending", "assigned", "in_progress", "completed", "failed", "cancelled"]
    },
    "assignedTo": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "startedAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "completedAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "timeoutSeconds": {
      "type": "integer",
      "minimum": 1
    },
    "retryCount": {
      "type": "integer",
      "minimum": 0
    },
    "maxRetries": {
      "type": "integer",
      "minimum": 0
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "dependencies": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      }
    },
    "result": {
      "type": ["object", "null"]
    }
  }
}
```

### YAML Example
```yaml
taskId: "123e4567-e89b-12d3-a456-426614174002"
name: "Transform Sales Data"
description: "Convert raw sales data from CSV to JSON format for analysis"
capabilityRequired: "data-transform-v1"
input:
  rawData: "date,product,quantity,price\n2026-08-01,Widget A,10,25.50\n2026-08-01,Widget B,5,15.75"
  format: "csv"
expectedOutput:
  type: array
  items:
    type: object
    properties:
      date:
        type: string
      product:
        type: string
      quantity:
        type: integer
      price:
        type: number
priority: "high"
status: "pending"
createdBy: "987f6543-e21b-34d5-a654-876654321000"  # User ID or Agent ID
createdAt: "2026-08-07T09:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
timeoutSeconds: 120
maxRetries: 3
tags:
  - "data"
  - "transformation"
  - "sales"
metadata:
  sourceSystem: "CRM"
  destinationSystem: "Data Warehouse"
dependencies: []
result: null
```

### Migration Rules
- When adding new status values: Extend the status enum with new values
- When changing priority levels: Provide mapping for legacy priority values
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by task delegation systems (Section 12.4)
- References Agent Schema for assignedTo and createdBy fields
- References Capability Schema for capabilityRequired field
- Used in workflow steps as individual units of work

---

## Council Schema

### Purpose
Defines the structure for council formations used in distributed decision-making. Councils are groups of agents that collaborate to reach consensus on shared objectives, resource allocation, or conflict resolution.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `councilId` | string | Unique identifier for the council (UUID v4 recommended) |
| `name` | string | Human-readable name for the council |
| `version` | string | Semantic version of the council definition |
| `description` | string | Detailed description of the council's purpose and scope |
| `members` | array[CouncilMember] | List of agents participating in the council |
| `proposal` | object | The proposal or issue under consideration |
| `votingProtocol` | string | Voting protocol to use (`simple_majority`, `supermajority`, `unanimous`, `weighted`, `consensus`) |
| `quorum` | object | Minimum participation requirements for valid voting |
| `status` | string | Current status (`forming`, `active`, `voting`, `completed`, `dissolved`) |
| `createdAt` | string (ISO 8601) | Timestamp when the council was formed |
| `updatedAt` | string (ISO 8601) | Timestamp when the council was last modified |
| `expiresAt` | string (ISO 8601) or null | Timestamp when the council automatically dissolves |
| `decision` | object or null | The final decision reached by the council |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for council-specific metadata |

### CouncilMember Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `agentId` | string | Unique identifier for the agent member |
| `weight` | number | Voting weight of the member (default: 1.0) |
| `joinedAt` | string (ISO 8601) | Timestamp when the agent joined the council |
| `leftAt` | string (ISO 8601) or null | Timestamp when the agent left the council |
| `metadata` | object | Member-specific metadata |

### Required Fields
- `councilId`
- `name`
- `version`
- `members`
- `votingProtocol`
- `quorum`
- `status`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `proposal`
- `expiresAt`
- `decision`
- `tags`
- `metadata`

### Validation Rules
- `councilId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `members` array must contain at least one member
- Each member's `agentId` must be a valid UUID v4 string
- `weight` must be a positive number
- `votingProtocol` must be one of: `simple_majority`, `supermajority`, `unanimous`, `weighted`, `consensus`
- `quorum` must contain valid quorum requirements based on the voting protocol
- `status` must be one of: `forming`, `active`, `voting`, `completed`, `dissolved`
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `expiresAt` is provided, it must be a valid ISO 8601 timestamp and greater than `createdAt`
- If `decision` is provided, it must conform to the expected decision format for the voting protocol
- If `leftAt` is provided for a member, it must be a valid ISO 8601 timestamp and greater than `joinedAt`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Council Definition",
  "type": "object",
  "required": ["councilId", "name", "version", "members", "votingProtocol", "quorum", "status", "createdAt", "updatedAt"],
  "properties": {
    "councilId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "members": {
      "type": "array",
      "items": { "$ref": "#/definitions/councilMember" },
      "minItems": 1
    },
    "proposal": { "type": ["object", "null"] },
    "votingProtocol": {
      "type": "string",
      "enum": ["simple_majority", "supermajority", "unanimous", "weighted", "consensus"]
    },
    "quorum": {
      "oneOf": [
        {
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": { "type": "string", "enum": ["simple_majority", "supermajority", "unanimous"] },
            "percentage": {
              "type": "number",
              "minimum": 0,
              "maximum": 100
            }
          }
        },
        {
          "type": "object",
          "required": ["type", "minimumCount"],
          "properties": {
            "type": { "type": "string", "enum": ["weighted"] },
            "minimumCount": { "type": "integer", "minimum": 1 },
            "minimumWeight": { "type": "number", "minimum": 0 }
          }
        },
        {
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": { "type": "string", "enum": ["consensus"] }
          }
        }
      ]
    },
    "status": {
      "type": "string",
      "enum": ["forming", "active", "voting", "completed", "dissolved"]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "expiresAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "decision": { "type": ["object", "null"] },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "definitions": {
    "councilMember": {
      "type": "object",
      "required": ["agentId", "joinedAt"],
      "properties": {
        "agentId": {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "weight": {
          "type": "number",
          "minimum": 0
        },
        "joinedAt": { "type": "string", "format": "date-time" },
        "leftAt": {
          "type": ["string", "null"],
          "format": "date-time"
        },
        "metadata": {
          "type": "object",
          "additionalProperties": true
        }
      }
    }
  }
}
```

### YAML Example
```yaml
councilId: "123e4567-e89b-12d3-a456-426614174003"
name: "Resource Allocation Council"
version: "1.0.0"
description: "Council responsible for allocating computational resources among competing workflows"
members:
  - agentId: "123e4567-e89b-12d3-a456-426614174000"
    weight: 1.5
    joinedAt: "2026-08-07T08:00:00Z"
    metadata:
      role: "facilitator"
  - agentId: "123e4567-e89b-12d3-a456-426614174001"
    weight: 1.0
    joinedAt: "2026-08-07T08:05:00Z"
  - agentId: "123e4567-e89b-12d3-a456-426614174002"
    weight: 2.0
    joinedAt: "2026-08-07T08:10:00Z"
proposal:
  type: object
  properties:
    action:
      type: string
      enum: [allocate_resources, rebalance_load, prioritize_workflow]
    workflowId:
      type: string
      pattern: "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    resourceType:
      type: string
      enum: [cpu, memory, storage, bandwidth]
    quantity:
      type: number
      minimum: 0
votingProtocol: "weighted"
quorum:
  type: "weighted"
  minimumCount: 2
  minimumWeight: 3.0
status: "active"
createdAt: "2026-08-07T08:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
expiresAt: "2026-08-07T17:00:00Z"
tags:
  - "resource-allocation"
  - "governance"
metadata:
  coordinator: "system-admin"
  priority: "high"
```

### Migration Rules
- When adding new voting protocols: Extend the votingProtocol enum and quorum definitions
- When changing member structure: Provide backward compatibility for legacy member fields
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by council decision architecture (Section 12.5)
- References Agent Schema for member agentId fields
- Works with Vote Schema for recording individual votes

---

## Vote Schema

### Purpose
Defines the structure for recording individual votes in council decision-making processes. Votes capture an agent's decision on a proposal along with any reasoning or conditions.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `voteId` | string | Unique identifier for the vote (UUID v4 recommended) |
| `councilId` | string | Identifier of the council the vote belongs to |
| `agentId` | string | Identifier of the agent casting the vote |
| `voteType` | string | Type of vote (`approve`, `reject`, `abstain`, `conditional_approve`, `conditional_reject`) |
| `reasoning` | string | Explanation for the vote decision |
| `conditions` | array[object] | Conditions that must be met for the vote to be valid (for conditional votes) |
| `weight` | number | Voting weight applied to this vote (default: 1.0) |
| `timestamp` | string (ISO 8601) | When the vote was cast |
| `signature` | string or null | Cryptographic signature of the vote for non-repudiation |
| `metadata` | object | Arbitrary key-value pairs for vote-specific metadata |

### Required Fields
- `voteId`
- `councilId`
- `agentId`
- `voteType`
- `timestamp`

### Optional Fields
- `reasoning`
- `conditions`
- `weight`
- `signature`
- `metadata`

### Validation Rules
- `voteId` must be a valid UUID v4 string
- `councilId` must be a valid UUID v4 string
- `agentId` must be a valid UUID v4 string
- `voteType` must be one of: `approve`, `reject`, `abstain`, `conditional_approve`, `conditional_reject`
- `weight` must be a positive number
- `timestamp` must be a valid ISO 8601 timestamp
- If `signature` is provided, it must be a valid cryptographic signature (format depends on implementation)
- Each condition in `conditions` must be a valid condition object (structure depends on vote type and council rules)

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Vote Record",
  "type": "object",
  "required": ["voteId", "councilId", "agentId", "voteType", "timestamp"],
  "properties": {
    "voteId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "councilId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "agentId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "voteType": {
      "type": "string",
      "enum": ["approve", "reject", "abstain", "conditional_approve", "conditional_reject"]
    },
    "reasoning": { "type": "string" },
    "conditions": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true
      }
    },
    "weight": {
      "type": "number",
      "minimum": 0
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "signature": {
      "type": ["string", "null"]
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

### YAML Example
```yaml
voteId: "123e4567-e89b-12d3-a456-426614174004"
councilId: "123e4567-e89b-12d3-a456-426614174003"
agentId: "123e4567-e89b-12d3-a456-426614174000"
voteType: "conditional_approve"
reasoning: "Approval contingent on sufficient resources being allocated to critical workflows"
conditions:
  - type: "resource_threshold"
    resourceType: "cpu"
    minimumPercentage: 30
  - type: "workflow_priority"
    workflowId: "123e4567-e89b-12d3-a456-426614174005"
    minimumPriority: "high"
weight: 1.5
timestamp: "2026-08-07T09:15:00Z"
signature: "MEUCIQD... (truncated)"
metadata:
  votingRound: 1
  delegateFor: "123e4567-e89b-12d3-a456-426614174001"  # Proxy vote
```

### Migration Rules
- When adding new vote types: Extend the voteType enum
- When changing condition structure: Provide validation rules for legacy conditions
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by council decision architecture (Section 12.5)
- References Agent Schema for agentId field
- References Council Schema for councilId field
- Used in conjunction with Council Schema to determine consensus

---

## Shared Context Schema

### Purpose
Defines the structure for shared context data that agents can publish, subscribe to, and consume. Shared context enables agents to maintain situational awareness and exchange intermediate results during collaboration.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `contextId` | string | Unique identifier for the context entry (UUID v4 recommended) |
| `name` | string | Human-readable name for the context entry |
| `version` | string | Semantic version of the context schema |
| `description` | string | Detailed description of what the context represents |
| `scope` | string | Visibility scope (`global`, `workflow`, `task`, `agent_group`, `private`) |
| `data` | object | The actual context data (structure defined by schema or application) |
| `schema` | string or null | Reference to a JSON Schema that validates the data field |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdBy` | string | AgentId that created the context entry |
| `createdAt` | string (ISO 8601) | Timestamp when the context was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the context was last updated |
| `expiresAt` | string (ISO 8601) or null | Timestamp when the context automatically expires |
| `accessPolicy` | object | Defines who can read/write the context |
| `history` | array[object] | Audit trail of changes to the context |
| `metadata` | object | Arbitrary key-value pairs for context-specific metadata |

### Required Fields
- `contextId`
- `name`
- `version`
- `scope`
- `data`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `schema`
- `tags`
- `expiresAt`
- `accessPolicy`
- `history`
- `metadata`

### Validation Rules
- `contextId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `scope` must be one of: `global`, `workflow`, `task`, `agent_group`, `private`
- `createdBy` must be a valid UUID v4 string
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `expiresAt` is provided, it must be a valid ISO 8601 timestamp and greater than `createdAt`
- If `schema` is provided, it must be a valid URI or schema identifier
- If `data` is provided and `schema` is specified, `data` must conform to the referenced schema
- `accessPolicy` must conform to the AccessPolicy structure
- Each entry in `history` must conform to the HistoryEntry structure

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Shared Context Entry",
  "type": "object",
  "required": ["contextId", "name", "version", "scope", "data", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "contextId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "scope": {
      "type": "string",
      "enum": ["global", "workflow", "task", "agent_group", "private"]
    },
    "data": {},
    "schema": {
      "oneOf": [
        { "type": "string", "format": "uri" },
        { "type": "string", "minLength": 1 }
      ]
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdBy": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "expiresAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "accessPolicy": {
      "type": "object",
      "required": ["read", "write"],
      "properties": {
        "read": {
          "oneOf": [
            { "type": "string", "enum": ["public", "private"] },
            {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
              }
            }
          ]
        },
        "write": {
          "oneOf": [
            { "type": "string", "enum": ["public", "private"] },
            {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
              }
            }
          ]
        }
      }
    },
    "history": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["timestamp", "action", "agentId"],
        "properties": {
          "timestamp": { "type": "string", "format": "date-time" },
          "action": {
            "type": "string",
            "enum": ["created", "updated", "deleted", "accessed"]
          },
          "agentId": {
            "type": "string",
            "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
          },
          "changes": {
            "type": ["object", "null"]
          }
        }
      }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

### YAML Example
```yaml
contextId: "123e4567-e89b-12d3-a456-426614174005"
name: "Current Market Data"
version: "1.0.0"
description: "Real-time market data for trading workflows"
scope: "workflow"
data:
  symbol: "AAPL"
  price: 175.50
  volume: 1250000
  timestamp: "2026-08-07T09:30:00Z"
  volatility: 0.25
schema: "https://example.com/schemas/market-data-v1.json"
tags:
  - "market"
  - "data"
  - "realtime"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-07T09:30:00Z"
updatedAt: "2026-08-07T09:30:00Z"
expiresAt: "2026-08-07T10:30:00Z"
accessPolicy:
  read: ["public"]
  write:
    - "123e4567-e89b-12d3-a456-426614174000"
    - "123e4567-e89b-12d3-a456-426614174001"
history:
  - timestamp: "2026-08-07T09:30:00Z"
    action: "created"
    agentId: "123e4567-e89b-12d3-a456-426614174000"
    changes: null
metadata:
  source: "market-feed-provider"
  priority: "high"
```

### Migration Rules
- When adding new scopes: Extend the scope enum
- When changing access policy structure: Provide migration tools for legacy policies
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by shared context and knowledge exchange systems (Section 12.6)
- References Agent Schema for createdBy and history.agentId fields
- Can reference external schemas for data validation

---

## Knowledge Object Schema

### Purpose
Defines the structure for knowledge objects that agents can create, share, and consume. Knowledge objects represent learned information, models, or insights that can be reused across the agent ecosystem.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `knowledgeId` | string | Unique identifier for the knowledge object (UUID v4 recommended) |
| `name` | string | Human-readable name for the knowledge object |
| `version` | string | Semantic version of the knowledge object |
| `description` | string | Detailed description of what the knowledge represents |
| `knowledgeType` | string | Type of knowledge (`model`, `pattern`, `rule`, `insight`, `fact`, `procedure`) |
| `content` | object | The actual knowledge content (structure varies by knowledgeType) |
| `schema` | string or null | Reference to a JSON Schema that validates the content field |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdBy` | string | AgentId that created the knowledge object |
| `createdAt` | string (ISO 8601) | Timestamp when the knowledge was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the knowledge was last updated |
| `expiresAt` | string (ISO 8601) or null | Timestamp when the knowledge automatically expires |
| `accessPolicy` | object | Defines who can read/use the knowledge |
| `usageCount` | integer | Number of times the knowledge has been used |
| `effectivenessScore` | number | Measure of how effective the knowledge is (0.0 to 1.0) |
| `confidenceLevel` | number | Confidence in the knowledge accuracy (0.0 to 1.0) |
| `source` | object | Information about where the knowledge originated |
| `metadata` | object | Arbitrary key-value pairs for knowledge-specific metadata |

### Required Fields
- `knowledgeId`
- `name`
- `version`
- `knowledgeType`
- `content`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `schema`
- `tags`
- `expiresAt`
- `accessPolicy`
- `usageCount`
- `effectivenessScore`
- `confidenceLevel`
- `source`
- `metadata`

### Validation Rules
- `knowledgeId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `knowledgeType` must be one of: `model`, `pattern`, `rule`, `insight`, `fact`, `procedure`
- `createdBy` must be a valid UUID v4 string
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `expiresAt` is provided, it must be a valid ISO 8601 timestamp and greater than `createdAt`
- If `schema` is provided, it must be a valid URI or schema identifier
- If `content` is provided and `schema` is specified, `content` must conform to the referenced schema
- `accessPolicy` must conform to the AccessPolicy structure (same as Shared Context)
- `usageCount` must be a non-negative integer
- `effectivenessScore` must be a number between 0.0 and 1.0 inclusive
- `confidenceLevel` must be a number between 0.0 and 1.0 inclusive
- `source` must conform to the KnowledgeSource structure if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Knowledge Object",
  "type": "object",
  "required": ["knowledgeId", "name", "version", "knowledgeType", "content", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "knowledgeId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "knowledgeType": {
      "type": "string",
      "enum": ["model", "pattern", "rule", "insight", "fact", "procedure"]
    },
    "content": {},
    "schema": {
      "oneOf": [
        { "type": "string", "format": "uri" },
        { "type": "string", "minLength": 1 }
      ]
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdBy": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "expiresAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "accessPolicy": {
      "type": "object",
      "required": ["read"],
      "properties": {
        "read": {
          "oneOf": [
            { "type": "string", "enum": ["public", "private"] },
            {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
              }
            }
          ]
        }
      }
    },
    "usageCount": {
      "type": "integer",
      "minimum": 0
    },
    "effectivenessScore": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "confidenceLevel": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "source": {
      "type": ["object", "null"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["observation", "training", "inference", "import", "hybrid"]
        },
        "agentId": {
          "type": ["string", "null"],
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "timestamp": {
          "type": ["string", "null"],
          "format": "date-time"
        },
        "reference": {
          "type": "string"
        }
      }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

### YAML Example
```yaml
knowledgeId: "123e4567-e89b-12d3-a456-426614174006"
name: "Sales Forecasting Model"
version: "2.1.0"
description: "Machine learning model for predicting quarterly sales based on historical data"
knowledgeType: "model"
content:
  modelType: "random_forest"
  features:
    - "historical_sales"
    - "marketing_spend"
    - "economic_indicators"
    - "seasonality_factors"
  parameters:
    n_estimators: 100
    max_depth: 10
    random_state: 42
  performanceMetrics:
    accuracy: 0.92
    precision: 0.89
    recall: 0.94
schema: "https://example.com/schemas/ml-model-v2.json"
tags:
  - "sales"
  - "forecasting"
  - "machine-learning"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
expiresAt: "2027-08-01T10:00:00Z"
accessPolicy:
  read: ["public"]
usageCount: 45
effectivenessScore: 0.91
confidenceLevel: 0.88
source:
  type: "training"
  agentId: "123e4567-e89b-12d3-a456-426614174000"
  timestamp: "2026-08-01T10:00:00Z"
  reference: "training-job-2026-08-01-001"
metadata:
  framework: "scikit-learn"
  version: "1.3.0"
  trainingDurationMinutes: 45
```

### Migration Rules
- When adding new knowledge types: Extend the knowledgeType enum
- When changing content structure: Provide validation rules for legacy content formats
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by shared context and knowledge exchange systems (Section 12.6)
- References Agent Schema for createdBy and source.agentId fields
- Can reference external schemas for content validation
- Related to Memory Object Schema for persistent knowledge storage

---

## Memory Object Schema

### Purpose
Defines the structure for memory objects that agents use to store and retrieve persistent information. Memory objects enable agents to maintain state, learn from experiences, and build long-term knowledge.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `memoryId` | string | Unique identifier for the memory object (UUID v4 recommended) |
| `name` | string | Human-readable name for the memory |
| `version` | string | Semantic version of the memory schema |
| `description` | string | Detailed description of what the memory represents |
| `memoryType` | string | Type of memory (`episodic`, `semantic`, `procedural`, `working`, `short_term`, `long_term`) |
| `content` | object | The actual memory content (structure varies by memoryType) |
| `schema` | string or null | Reference to a JSON Schema that validates the content field |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdBy` | string | AgentId that created the memory |
| `createdAt` | string (ISO 8601) | Timestamp when the memory was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the memory was last updated |
| `accessedAt` | string (ISO 8601) or null | Timestamp when the memory was last accessed |
| `accessCount` | integer | Number of times the memory has been accessed |
| `retentionPolicy` | object | Defines how long the memory should be retained |
| `importanceScore` | number | Measure of how important the memory is (0.0 to 1.0) |
| `confidenceLevel` | number | Confidence in the memory accuracy (0.0 to 1.0) |
| `source` | object | Information about where the memory originated |
| `metadata` | object | Arbitrary key-value pairs for memory-specific metadata |
| `isShared` | boolean | Whether the memory is shared with other agents |
| `sharedWith` | array[string] | List of agentIds with whom the memory is shared |

### Required Fields
- `memoryId`
- `name`
- `version`
- `memoryType`
- `content`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `schema`
- `tags`
- `accessedAt`
- `accessCount`
- `retentionPolicy`
- `importanceScore`
- `confidenceLevel`
- `source`
- `metadata`
- `isShared`
- `sharedWith`

### Validation Rules
- `memoryId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `memoryType` must be one of: `episodic`, `semantic`, `procedural`, `working`, `short_term`, `long_term`
- `createdBy` must be a valid UUID v4 string
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `accessedAt` is provided, it must be a valid ISO 8601 timestamp and greater than or equal to `createdAt`
- `accessCount` must be a non-negative integer
- If `retentionPolicy` is provided, it must conform to the RetentionPolicy structure
- `importanceScore` must be a number between 0.0 and 1.0 inclusive
- `confidenceLevel` must be a number between 0.0 and 1.0 inclusive
- `source` must conform to the MemorySource structure if provided
- If `isShared` is true, `sharedWith` must be provided and contain valid UUID v4 strings
- Each agentId in `sharedWith` must be a valid UUID v4 string

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Memory Object",
  "type": "object",
  "required": ["memoryId", "name", "version", "memoryType", "content", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "memoryId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "memoryType": {
      "type": "string",
      "enum": ["episodic", "semantic", "procedural", "working", "short_term", "long_term"]
    },
    "content": {},
    "schema": {
      "oneOf": [
        { "type": "string", "format": "uri" },
        { "type": "string", "minLength": 1 }
      ]
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdBy": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "accessedAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "accessCount": {
      "type": "integer",
      "minimum": 0
    },
    "retentionPolicy": {
      "type": ["object", "null"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["time_based", "access_based", "importance_based", "hybrid"]
        },
        "maxAgeSeconds": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "maxAccessCount": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "minImportanceThreshold": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "maximum": 1.0
        }
      }
    },
    "importanceScore": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "confidenceLevel": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "source": {
      "type": ["object", "null"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["observation", "training", "inference", "communication", "import", "hybrid"]
        },
        "agentId": {
          "type": ["string", "null"],
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "timestamp": {
          "type": ["string", "null"],
          "format": "date-time"
        },
        "reference": {
          "type": "string"
        }
      }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "isShared": {
      "type": "boolean"
    },
    "sharedWith": {
      "type": ["array", "null"],
      "items": {
        "type": "string",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      }
    }
  }
}
```

### YAML Example
```yaml
memoryId: "123e4567-e89b-12d3-a456-426614174007"
name: "Customer Interaction Pattern - Retail Store"
version: "1.2.0"
description: "Learned pattern of customer behavior in retail environments during holiday seasons"
memoryType: "semantic"
content:
  patternType: "customer_behavior"
  context: "retail_holiday_season"
  observations:
    - "Customers spend 30% more time in store during weekends"
    - "Peak shopping hours are 2-4 PM on Saturdays"
    - "Conversion rate increases by 15% when personalized recommendations are offered"
  confidenceFactors:
    sampleSize: 1250
    timePeriod: "3_months"
    statisticalSignificance: 0.95
tags:
  - "customer"
  - "behavior"
  - "retail"
  - "pattern"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-07-01T10:00:00Z"
updatedAt: "2026-08-01T09:00:00Z"
accessedAt: "2026-08-07T08:30:00Z"
accessCount: 23
retentionPolicy:
  type: "importance_based"
  minImportanceThreshold: 0.7
importanceScore: 0.85
confidenceLevel: 0.92
source:
  type: "observation"
  agentId: "123e4567-e89b-12d3-a456-426614174000"
  timestamp: "2026-07-01T10:00:00Z"
  reference: "retail-study-q3-2026"
metadata:
  dataSource: "POS-system"
  validationMethod: "cross-validation"
isShared: true
sharedWith:
  - "123e4567-e89b-12d3-a456-426614174001"
  - "123e4567-e89b-12d3-a456-426614174002"
```

### Migration Rules
- When adding new memory types: Extend the memoryType enum
- When changing retention policy structure: Provide validation rules for legacy policies
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by agent memory systems (Part 1-11)
- References Agent Schema for createdBy and source.agentId fields
- Can reference external schemas for content validation
- Related to Knowledge Object Schema for persistent knowledge storage

---

## Runtime Schema

### Purpose
Defines the structure for runtime information about agents and the collaboration system. Runtime schemas capture operational metrics, state, and configuration details for monitoring and management.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `runtimeId` | string | Unique identifier for the runtime entry (UUID v4 recommended) |
| `entityId` | string | Identifier of the entity being monitored (agentId, workflowId, etc.) |
| `entityType` | string | Type of entity being monitored (`agent`, `workflow`, `task`, `council`, `system`) |
| `timestamp` | string (ISO 8601) | When the runtime data was collected |
| `metrics` | object | Operational metrics (CPU, memory, latency, throughput, etc.) |
| `status` | string | Current operational status |
| `state` | object | Current state information (varies by entityType) |
| `configuration` | object | Current runtime configuration |
| `health` | object | Health indicators and diagnostics |
| `tags` | array[string] | Tags for categorization and filtering |
| `metadata` | object | Arbitrary key-value pairs for runtime-specific metadata |

### Required Fields
- `runtimeId`
- `entityId`
- `entityType`
- `timestamp`
- `metrics`
- `status`

### Optional Fields
- `state`
- `configuration`
- `health`
- `tags`
- `metadata`

### Validation Rules
- `runtimeId` must be a valid UUID v4 string
- `entityId` must be a valid identifier for the specified entityType:
  - For `agent`: must be a valid UUID v4 string
  - For `workflow`: must be a valid UUID v4 string
  - For `task`: must be a valid UUID v4 string
  - For `council`: must be a valid UUID v4 string
  - For `system`: must be a non-empty string
- `entityType` must be one of: `agent`, `workflow`, `task`, `council`, `system`
- `timestamp` must be a valid ISO 8601 timestamp
- `metrics` must conform to the RuntimeMetrics structure
- `status` must be a valid status for the entityType (defined in respective schemas)
- `state` must conform to the expected state structure for the entityType
- `configuration` must conform to the Configuration Schema if provided
- `health` must conform to the Health Report Schema if provided
- `tags` must be an array of strings

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Runtime Information",
  "type": "object",
  "required": ["runtimeId", "entityId", "entityType", "timestamp", "metrics", "status"],
  "properties": {
    "runtimeId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "entityId": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "entityType": {
      "type": "string",
      "enum": ["agent", "workflow", "task", "council", "system"]
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "metrics": {
      "type": "object",
      "required": ["cpuUsage", "memoryUsage"],
      "properties": {
        "cpuUsage": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 100.0
        },
        "memoryUsage": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 100.0
        },
        "latencyMs": {
          "type": ["number", "null"],
          "minimum": 0
        },
        "throughput": {
          "type": ["number", "null"],
          "minimum": 0
        },
        "errorRate": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "maximum": 1.0
        },
        "customMetrics": {
          "type": "object",
          "additionalProperties": {
            "type": "number"
          }
        }
      }
    },
    "status": { "type": "string" },
    "state": {
      "type": ["object", "null"]
    },
    "configuration": {
      "type": ["object", "null"]
    },
    "health": {
      "type": ["object", "null"]
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

### YAML Example
```yaml
runtimeId: "123e4567-e89b-12d3-a456-426614174008"
entityId: "123e4567-e89b-12d3-a456-426614174000"
entityType: "agent"
timestamp: "2026-08-07T09:30:00Z"
metrics:
  cpuUsage: 45.2
  memoryUsage: 62.8
  latencyMs: 125
  throughput: 45.5
  errorRate: 0.001
  customMetrics:
    tasksCompleted: 23
    activeWorkflows: 3
    cacheHitRate: 0.87
status: "active"
state:
  currentTaskId: "123e4567-e89b-12d3-a456-426614174002"
  availableCapabilities:
    - "data-transform-v1"
    - "data-ingest-v1"
  connections:
    outbound: 5
    inbound: 12
configuration:
  maxConcurrentTasks: 10
  heartbeatIntervalSeconds: 30
  logLevel: "info"
health:
  overallStatus: "healthy"
  checks:
    - name: "memory-leak-check"
      status: "passed"
      details: "No memory leaks detected"
    - name: "connectivity-check"
      status: "passed"
      details: "All required services reachable"
tags:
  - "agent"
  - "data-processing"
  - "high-performance"
metadata:
  collectionMethod: "push"
  agentVersion: "1.2.3"
```

### Migration Rules
- When adding new entity types: Extend the entityType enum and validation rules
- When changing metrics structure: Provide backward compatibility for legacy metrics
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by monitoring and observability systems (Part 3)
- References Agent Schema for agent entityId
- References Workflow Schema for workflow entityId
- References Task Schema for task entityId
- References Council Schema for council entityId
- Used with Health Report Schema for health field

---

## Scheduler Schema

### Purpose
Defines the structure for scheduling information used to coordinate agent activities, workflow executions, and resource allocations. Schedulers manage when and how tasks and workflows are executed.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `scheduleId` | string | Unique identifier for the schedule (UUID v4 recommended) |
| `name` | string | Human-readable name for the schedule |
| `version` | string | Semantic version of the schedule definition |
| `description` | string | Detailed description of what the schedule controls |
| `scheduleType` | string | Type of schedule (`cron`, `interval`, `one_time`, `workflow_triggered`, `event_triggered`) |
| `target` | object | The entity to be scheduled (taskId, workflowId, etc.) |
| `trigger` | object | Defines when the schedule should activate |
| `parameters` | object | Parameters to pass to the scheduled entity |
| `constraints` | object | Constraints on when the schedule can execute |
| `status` | string | Current status (`active`, `paused`, `completed`, `cancelled`, `failed`) |
| `createdBy` | string | AgentId or userId that created the schedule |
| `createdAt` | string (ISO 8601) | Timestamp when the schedule was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the schedule was last updated |
| `nextExecution` | string (ISO 8601) or null | Timestamp of the next scheduled execution |
| `lastExecution` | string (ISO 8601) or null | Timestamp of the last execution |
| `executionCount` | integer | Number of times the schedule has been executed |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for schedule-specific metadata |

### Required Fields
- `scheduleId`
- `name`
- `version`
- `scheduleType`
- `target`
- `trigger`
- `status`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `parameters`
- `constraints`
- `nextExecution`
- `lastExecution`
- `executionCount`
- `tags`
- `metadata`

### Validation Rules
- `scheduleId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `scheduleType` must be one of: `cron`, `interval`, `one_time`, `workflow_triggered`, `event_triggered`
- `target` must conform to the Target structure based on scheduleType
- `trigger` must conform to the Trigger structure based on scheduleType
- `status` must be one of: `active`, `paused`, `completed`, `cancelled`, `failed`
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for users)
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `nextExecution` is provided, it must be a valid ISO 8601 timestamp and greater than `createdAt`
- If `lastExecution` is provided, it must be a valid ISO 8601 timestamp and greater than or equal to `createdAt`
- `executionCount` must be a non-negative integer
- `constraints` must conform to the ScheduleConstraints structure if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Schedule Definition",
  "type": "object",
  "required": ["scheduleId", "name", "version", "scheduleType", "target", "trigger", "status", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "scheduleId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "scheduleType": {
      "type": "string",
      "enum": ["cron", "interval", "one_time", "workflow_triggered", "event_triggered"]
    },
    "target": {
      "oneOf": [
        {
          "type": "object",
          "required": ["taskId"],
          "properties": {
            "taskId": {
              "type": "string",
              "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            },
            "taskParameters": {
              "type": ["object", "null"]
            }
          }
        },
        {
          "type": "object",
          "required": ["workflowId"],
          "properties": {
            "workflowId": {
              "type": "string",
              "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            },
            "workflowParameters": {
              "type": ["object", "null"]
            }
          }
        },
        {
          "type": "object",
          "required": ["agentId"],
          "properties": {
            "agentId": {
              "type": "string",
              "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            },
            "agentInput": {
              "type": ["object", "null"]
            }
          }
        }
      ]
    },
    "trigger": {
      "oneOf": [
        {
          "type": "object",
          "required": ["cronExpression"],
          "properties": {
            "cronExpression": { "type": "string", "pattern": "^([0-9]|[1-5][0-9])\\s+([0-9]|1[0-9]|2[0-3])\\s+([1-9]|[12][0-9]|3[0-1])\\s+([1-9]|1[0-2])\\s+([0-6])$" }
          }
        },
        {
          "type": "object",
          "required": ["intervalSeconds"],
          "properties": {
            "intervalSeconds": {
              "type": "integer",
              "minimum": 1
            },
            "startDelaySeconds": {
              "type": ["integer", "null"],
              "minimum": 0
            }
          }
        },
        {
          "type": "object",
          "required": ["triggerTime"],
          "properties": {
            "triggerTime": { "type": "string", "format": "date-time" }
          }
        },
        {
          "type": "object",
          "required": ["workflowId"],
          "properties": {
            "workflowId": {
              "type": "string",
              "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            },
            "triggerEvent": {
              "type": "string",
              "enum": ["completed", "failed", "started", "paused"]
            }
          }
        },
        {
          "type": "object",
          "required": ["eventType"],
          "properties": {
            "eventType": { "type": "string", "minLength": 1 },
            "eventSource": {
              "type": ["string", "null"],
              "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
            }
          }
        }
      ]
    },
    "parameters": {
      "type": ["object", "null"]
    },
    "constraints": {
      "type": ["object", "null"],
      "properties": {
        "maxConcurrentExecutions": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "allowedTimeWindows": {
          "type": ["array", "null"],
          "items": {
            "type": "object",
            "required": ["startTime", "endTime"],
            "properties": {
              "startTime": { "type": "string", "pattern": "^([0-9]|1[0-9]|2[0-3]):([0-9]|[1-5][0-9])$" },
              "endTime": { "type": "string", "pattern": "^([0-9]|1[0-9]|2[0-3]):([0-9]|[1-5][0-9])$" }
            }
          }
        },
        "blackoutDates": {
          "type": ["array", "null"],
          "items": {
            "type": "string",
            "pattern": "^\\d{4}-\\d{2}-\\d{2}$"
          }
        }
      }
    },
    "status": {
      "type": "string",
      "enum": ["active", "paused", "completed", "cancelled", "failed"]
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "nextExecution": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "lastExecution": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "executionCount": {
      "type": "integer",
      "minimum": 0
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

### YAML Example
```yaml
scheduleId: "123e4567-e89b-12d3-a456-426614174009"
name: "Daily Data Processing Workflow"
version: "1.0.0"
description: "Schedule to run the data processing workflow every day at 2 AM"
scheduleType: "cron"
target:
  workflowId: "123e4567-e89b-12d3-a456-426614174001"
  workflowParameters:
    sourceSystem: "daily_extract"
trigger:
  cronExpression: "0 2 * * *"
parameters:
  priority: "high"
  notificationEmail: "data-team@example.com"
constraints:
  maxConcurrentExecutions: 1
  allowedTimeWindows:
    - startTime: "01:00"
      endTime: "05:00"
status: "active"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
nextExecution: "2026-08-08T02:00:00Z"
lastExecution: "2026-08-07T02:00:00Z"
executionCount: 7
tags:
  - "data"
  - "daily"
  - "workflow"
metadata:
  owner: "data-engineering-team"
  priority: "high"
```

### Migration Rules
- When adding new schedule types: Extend the scheduleType enum and validation rules
- When changing trigger structure: Provide backward compatibility for legacy triggers
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by resource coordination and scheduling systems (Section 12.8)
- References Workflow Schema for workflowId in target
- References Task Schema for taskId in target
- References Agent Schema for agentId in target
- Works with Runtime Schema for execution tracking

---

## Plugin Schema

### Purpose
Defines the structure for plugin descriptors that extend the functionality of agents, workflows, or the collaboration system itself. Plugins enable dynamic extension of capabilities without modifying core code.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `pluginId` | string | Unique identifier for the plugin (UUID v4 recommended) |
| `name` | string | Human-readable name for the plugin |
| `version` | string | Semantic version of the plugin |
| `description` | string | Detailed description of what the plugin does |
| `pluginType` | string | Type of plugin (`agent_extension`, `workflow_extension`, `system_extension`, `capability_adapter`) |
| `entryPoint` | string | Entry point for plugin initialization (module path, class name, etc.) |
| `dependencies` | array[string] | List of pluginIds or external dependencies required |
| `hooks` | array[object] | List of extension points the plugin implements |
| `configuration` | object | Default configuration for the plugin |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdBy` | string | AgentId or userId that created the plugin |
| `createdAt` | string (ISO 8601) | Timestamp when the plugin was registered |
| `updatedAt | string (ISO 8601) | Timestamp when the plugin was last updated |
| `status` | string | Current status (`active`, `inactive`, `deprecated`, `failed`) |
| `metadata` | object | Arbitrary key-value pairs for plugin-specific metadata |
| `signature` | string or null | Cryptographic signature for plugin integrity verification |
| `compatibility` | object | Compatibility information with system versions |

### Required Fields
- `pluginId`
- `name`
- `version`
- `pluginType`
- `entryPoint`
- `status`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `dependencies`
- `hooks`
- `configuration`
- `tags`
- `metadata`
- `signature`
- `compatibility`

### Validation Rules
- `pluginId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `pluginType` must be one of: `agent_extension`, `workflow_extension`, `system_extension`, `capability_adapter`
- `entryPoint` must be a non-empty string
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for users)
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- `status` must be one of: `active`, `inactive`, `deprecated`, `failed`
- Each dependency in `dependencies` must be a non-empty string
- Each hook in `hooks` must conform to the PluginHook structure
- `configuration` must conform to the Configuration Schema if provided
- If `signature` is provided, it must be a valid cryptographic signature
- `compatibility` must conform to the PluginCompatibility structure if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Plugin Descriptor",
  "type": "object",
  "required": ["pluginId", "name", "version", "pluginType", "entryPoint", "status", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "pluginId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "pluginType": {
      "type": "string",
      "enum": ["agent_extension", "workflow_extension", "system_extension", "capability_adapter"]
    },
    "entryPoint": { "type": "string", "minLength": 1 },
    "dependencies": {
      "type": "array",
      "items": { "type": "string" }
    },
    "hooks": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["hookType", "callback"],
        "properties": {
          "hookType": {
            "type": "string",
            "enum": ["initialize", "before_task_execution", "after_task_execution", "on_workflow_start", "on_workflow_end", "on_agent_register", "on_agent_deregister", "custom"]
          },
          "callback": { "type": "string", "minLength": 1 },
          "configuration": {
            "type": ["object", "null"]
          }
        }
      }
    },
    "configuration": {
      "type": ["object", "null"]
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "status": {
      "type": "string",
      "enum": ["active", "inactive", "deprecated", "failed"]
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "signature": {
      "type": ["string", "null"]
    },
    "compatibility": {
      "type": ["object", "null"],
      "properties": {
        "minSystemVersion": {
          "type": "string",
          "pattern": "^\\d+\\.\\d+\\.\\d+$"
        },
        "maxSystemVersion": {
          "type": ["string", "null"],
          "pattern": "^\\d+\\.\\d+\\.\\d+$"
        },
        "testedVersions": {
          "type": "array",
          "items": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$"
          }
        }
      }
    }
  }
}
```

### YAML Example
```yaml
pluginId: "123e4567-e89b-12d3-a456-426614174010"
name: "Data Validation Plugin"
version: "1.2.0"
description: "Plugin that adds data validation capabilities to agents"
pluginType: "agent_extension"
entryPoint: "plugins/data-validator:DataValidatorPlugin"
dependencies:
  - "schema-validator-v1"
  - "data-utils-v2"
hooks:
  - hookType: "before_task_execution"
    callback: "validateInputData"
    configuration:
      validationRules:
        - "required_fields"
        - "data_types"
        - "range_checks"
  - hookType: "after_task_execution"
    callback: "validateOutputData"
configuration:
  strictMode: true
  validationTimeout: 5000
tags:
  - "validation"
  - "data"
  - "quality"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
status: "active"
metadata:
  author: "data-team"
  license: "MIT"
signature: "MEUCIQD... (truncated)"
compatibility:
  minSystemVersion: "1.0.0"
  testedVersions:
    - "1.0.0"
    - "1.1.0"
    - "1.2.0"
```

### Migration Rules
- When adding new plugin types: Extend the pluginType enum
- When changing hook structure: Provide backward compatibility for legacy hooks
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by extensibility systems (Part 5)
- References Configuration Schema for configuration field
- Can be referenced by Agent Schema for plugin-based capabilities
- Works with Tool Schema for plugin-provided tools

---

## Tool Schema

### Purpose
Defines the structure for tool descriptors that agents can discover and invoke. Tools represent executable functions or services that agents can use to perform specific actions.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `toolId` | string | Unique identifier for the tool (UUID v4 recommended) |
| `name` | string | Human-readable name for the tool |
| `version` | string | Semantic version of the tool |
| `description` | string | Detailed description of what the tool does |
| `toolType` | string | Type of tool (`function`, `service`, `api`, `script`, `executable`) |
| `endpoint` | string | Endpoint or invocation method for the tool |
| `inputSchema` | object or null | JSON Schema defining valid inputs for the tool |
| `outputSchema` | object or null | JSON Schema defining outputs produced by the tool |
| `parameters` | object | Configuration parameters for the tool |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdBy` | string | AgentId or userId that created the tool |
| `createdAt` | string (ISO 8601) | Timestamp when the tool was registered |
| `updatedAt` | string (ISO 8601) | Timestamp when the tool was last updated |
| `accessPolicy` | object | Defines who can invoke the tool |
| `invocationCount` | integer | Number of times the tool has been invoked |
| `averageLatencyMs` | number | Average execution time in milliseconds |
| `successRate` | number | Percentage of successful invocations (0.0 to 1.0) |
| `metadata` | object | Arbitrary key-value pairs for tool-specific metadata |
| `signature` | string or null | Cryptographic signature for tool integrity verification |

### Required Fields
- `toolId`
- `name`
- `version`
- `toolType`
- `endpoint`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `inputSchema`
- `outputSchema`
- `parameters`
- `tags`
- `accessPolicy`
- `invocationCount`
- `averageLatencyMs`
- `successRate`
- `metadata`
- `signature`

### Validation Rules
- `toolId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `toolType` must be one of: `function`, `service`, `api`, `script`, `executable`
- `endpoint` must be a non-empty string
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for users)
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `inputSchema` is provided, it must be a valid JSON Schema
- If `outputSchema` is provided, it must be a valid JSON Schema
- `accessPolicy` must conform to the AccessPolicy structure
- `invocationCount` must be a non-negative integer
- `averageLatencyMs` must be a non-negative number
- `successRate` must be a number between 0.0 and 1.0 inclusive
- If `signature` is provided, it must be a valid cryptographic signature

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Tool Descriptor",
  "type": "object",
  "required": ["toolId", "name", "version", "toolType", "endpoint", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "toolId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "toolType": {
      "type": "string",
      "enum": ["function", "service", "api", "script", "executable"]
    },
    "endpoint": { "type": "string", "minLength": 1 },
    "inputSchema": { "type": ["object", "null"] },
    "outputSchema": { "type": ["object", "null"] },
    "parameters": {
      "type": "object",
      "additionalProperties": true
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "accessPolicy": {
      "type": "object",
      "required": ["invoke"],
      "properties": {
        "invoke": {
          "oneOf": [
            { "type": "string", "enum": ["public", "private"] },
            {
              "type": "array",
              "items": {
                "type": "string",
                "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
              }
            }
          ]
        }
      }
    },
    "invocationCount": {
      "type": "integer",
      "minimum": 0
    },
    "averageLatencyMs": {
      "type": "number",
      "minimum": 0
    },
    "successRate": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "signature": {
      "type": ["string", "null"]
    }
  }
}
```

### YAML Example
```yaml
toolId: "123e4567-e89b-12d3-a456-426614174011"
name: "Data Transformation Tool"
version: "2.1.0"
description: "Tool for transforming data between various formats using Apache Arrow"
toolType: "service"
endpoint: "grpc://data-transform.example.com:50051"
inputSchema:
  type: object
  properties:
    inputData:
      type: string
      minLength: 1
    sourceFormat:
      type: string
      enum: [json, xml, csv, parquet]
    targetFormat:
      type: string
      enum: [json, xml, csv, parquet]
  required: [inputData, sourceFormat, targetFormat]
outputSchema:
  type: object
  properties:
    outputData:
      type: string
      minLength: 1
    targetFormat:
      type: string
      enum: [json, xml, csv, parquet]
  required: [outputData, targetFormat]
parameters:
  arrowPoolSize: 4
  maxRecordBatchSize: 65536
tags:
  - "data"
  - "transformation"
  - "arrow"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
accessPolicy:
  invoke: ["private"]
invocationCount: 1245
averageLatencyMs: 125.5
successRate: 0.998
metadata:
  vendor: "data-tools-inc"
  license: "Apache-2.0"
signature: "MEUCIQD... (truncated)"
```

### Migration Rules
- When adding new tool types: Extend the toolType enum
- When changing schema structure: Provide backward compatibility for legacy schemas
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by tool discovery and invocation systems (Section 12.7)
- References Agent Schema for createdBy field
- Can be referenced by Capability Schema for tool-based capabilities
- Works with Message Schema for tool invocation messages

---

## Message Schema

### Purpose
Defines the structure for messages exchanged between agents in the collaboration system. Messages enable direct communication, requests, replies, and notifications between agents.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `messageId` | string | Unique identifier for the message (UUID v4 recommended) |
| `conversationId` | string | Identifier grouping related messages (optional) |
| `senderId` | string | Identifier of the agent sending the message |
| `recipientId` | string or null | Identifier of the intended recipient (null for broadcast) |
| `messageType` | string | Type of message (`request`, `reply`, `notification`, `broadcast`) |
| `subject` | string | Brief summary of the message content |
| `payload` | object | The actual message data (structure varies by messageType) |
| `correlationId` | string or null | Identifier for correlating requests with replies |
| `replyTo` | string or null | MessageId that this message is replying to |
| `priority` | string | Priority level (`low`, `normal`, `high`, `critical`) |
| `ttlSeconds` | integer | Time-to-live for the message (0 means no expiration) |
| `timestamp` | string (ISO 8601) | When the message was sent |
| `tags` | array[string] | Tags for categorization and routing |
| `metadata` | object | Arbitrary key-value pairs for message-specific metadata |
| `signature` | string or null | Cryptographic signature for message integrity and authentication |

### Required Fields
- `messageId`
- `senderId`
- `messageType`
- `timestamp`

### Optional Fields
- `conversationId`
- `recipientId`
- `subject`
- `payload`
- `correlationId`
- `replyTo`
- `priority`
- `ttlSeconds`
- `tags`
- `metadata`
- `signature`

### Validation Rules
- `messageId` must be a valid UUID v4 string
- `conversationId` if provided must be a valid UUID v4 string
- `senderId` must be a valid UUID v4 string
- `recipientId` if provided must be a valid UUID v4 string
- `messageType` must be one of: `request`, `reply`, `notification`, `broadcast`
- `correlationId` if provided must be a valid UUID v4 string
- `replyTo` if provided must be a valid UUID v4 string
- `priority` must be one of: `low`, `normal`, `high`, `critical`
- `ttlSeconds` must be a non-negative integer (0 means no expiration)
- `timestamp` must be a valid ISO 8601 timestamp
- `tags` must be an array of strings
- `signature` if provided must be a valid cryptographic signature
- `payload` structure depends on `messageType` and application context

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Agent Message",
  "type": "object",
  "required": ["messageId", "senderId", "messageType", "timestamp"],
  "properties": {
    "messageId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "conversationId": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "senderId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "recipientId": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "messageType": {
      "type": "string",
      "enum": ["request", "reply", "notification", "broadcast"]
    },
    "subject": { "type": "string" },
    "payload": {},
    "correlationId": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "replyTo": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "priority": {
      "type": "string",
      "enum": ["low", "normal", "high", "critical"]
    },
    "ttlSeconds": {
      "type": "integer",
      "minimum": 0
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "signature": {
      "type": ["string", "null"]
    }
  }
}
```

### YAML Example
```yaml
messageId: "123e4567-e89b-12d3-a456-426614174012"
conversationId: "123e4567-e89b-12d3-a456-426614174013"
senderId: "123e4567-e89b-12d3-a456-426614174000"
recipientId: "123e4567-e89b-12d3-a456-426614174001"
messageType: "request"
subject: "Request data transformation capability"
payload:
  taskId: "123e4567-e89b-12d3-a456-426614174002"
  capabilityRequired: "data-transform-v1"
  input:
    rawData: "name,age,city\nJohn,25,New York\nJane,30,Boston"
    format: "csv"
correlationId: "123e4567-e89b-12d3-a456-426614174014"
priority: "high"
ttlSeconds: 300
timestamp: "2026-08-07T09:30:00Z"
tags:
  - "task"
  - "request"
  - "data-transformation"
metadata:
  retryCount: 0
  timeoutMs: 5000
signature: "MEUCIQD... (truncated)"
```

### Migration Rules
- When adding new message types: Extend the messageType enum
- When changing payload structure: Provide validation rules for legacy payload formats
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by multi-agent communication systems (Section 12.7)
- References Agent Schema for senderId and recipientId fields
- Works with Tool Schema for tool invocation messages
- Related to Event Schema for event-driven communication

---

## Event Schema

### Purpose
Defines the structure for events emitted by agents and system components in the collaboration architecture. Events enable loose-coupling, observability, and reactive behaviors in the multi-agent system.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `eventId` | string | Unique identifier for the event (UUID v4 recommended) |
| `eventType` | string | Type of event (e.g., `TaskDelegated`, `WorkflowStarted`, `CapabilityRegistered`) |
| `sourceId` | string | Identifier of the entity that emitted the event |
| `sourceType` | string | Type of entity that emitted the event (`agent`, `workflow`, `task`, `council`, `system`) |
| `timestamp` | string (ISO 8601) | When the event was emitted |
| `payload` | object | The actual event data (structure varies by eventType) |
| `tags` | array[string] | Tags for categorization and filtering |
| `metadata` | object | Arbitrary key-value pairs for event-specific metadata |
| `correlationId` | string or null | Identifier for correlating related events |
| `signature` | string or null | Cryptographic signature for event integrity and authenticity |
| `version` | string | Semantic version of the event schema |

### Required Fields
- `eventId`
- `eventType`
- `sourceId`
- `sourceType`
- `timestamp`
- `version`

### Optional Fields
- `payload`
- `tags`
- `metadata`
- `correlationId`
- `signature`

### Validation Rules
- `eventId` must be a valid UUID v4 string
- `eventType` must be a non-empty string (recommended to use PascalCase with verb-object structure)
- `sourceId` must be a valid identifier for the specified sourceType:
  - For `agent`: must be a valid UUID v4 string
  - For `workflow`: must be a valid UUID v4 string
  - For `task`: must be a valid UUID v4 string
  - For `council`: must be a valid UUID v4 string
  - For `system`: must be a non-empty string
- `sourceType` must be one of: `agent`, `workflow`, `task`, `council`, `system`
- `timestamp` must be a valid ISO 8601 timestamp
- `version` must follow semantic versioning (major.minor.patch)
- `tags` must be an array of strings
- `signature` if provided must be a valid cryptographic signature
- `correlationId` if provided must be a valid UUID v4 string
- `payload` structure depends on `eventType` and application context

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "System Event",
  "type": "object",
  "required": ["eventId", "eventType", "sourceId", "sourceType", "timestamp", "version"],
  "properties": {
    "eventId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "eventType": { "type": "string", "minLength": 1 },
    "sourceId": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "sourceType": {
      "type": "string",
      "enum": ["agent", "workflow", "task", "council", "system"]
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "payload": {},
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "correlationId": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "signature": {
      "type": ["string", "null"]
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    }
  }
}
```

### YAML Example
```yaml
eventId: "123e4567-e89b-12d3-a456-426614174015"
eventType: "TaskDelegated"
sourceId: "123e4567-e89b-12d3-a456-426614174000"
sourceType: "agent"
timestamp: "2026-08-07T09:30:00Z"
payload:
  taskId: "123e4567-e89b-12d3-a456-426614174002"
  agentId: "123e4567-e89b-12d3-a456-426614174001"
  capabilityRequired: "data-transform-v1"
  priority: "high"
tags:
  - "task"
  - "delegation"
  - "agent-interaction"
metadata:
  delegatedBy: "workflow-orchestrator"
  retryAttempt: 0
correlationId: "123e4567-e89b-12d3-a456-426614174016"
version: "1.0.0"
```

### Migration Rules
- When adding new event types: Document them in the events taxonomy (Section 12.9)
- When changing payload structure: Provide validation rules for legacy payload formats
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by event-driven communication systems (Section 12.7)
- References Agent Schema for agent sourceId
- References Workflow Schema for workflow sourceId
- References Task Schema for task sourceId
- References Council Schema for council sourceId
- Related to Message Schema for direct communication
- Used by monitoring and observability systems (Part 3)

---

## Execution Plan Schema

### Purpose
Defines the structure for execution plans that detail how workflows and tasks will be executed. Execution plans are generated by orchestrators and specify the exact steps, resource allocations, and timing for carrying out collaborative work.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `planId` | string | Unique identifier for the execution plan (UUID v4 recommended) |
| `workflowId` | string | Identifier of the workflow this plan executes |
| `version` | string | Semantic version of the execution plan |
| `description` | string | Detailed description of what the plan accomplishes |
| `steps` | array[ExecutionStep] | Ordered list of steps to be executed |
| `resourceAllocation` | object | Details of computational resources allocated |
| `timing` | object | Schedule and timing constraints for execution |
| `dependencies` | array[string] | List of planIds that must complete before this plan |
| `contingencyPlans` | array[object] | Backup plans for failure scenarios |
| `status` | string | Current status (`draft`, `ready`, `active`, `paused`, `completed`, `failed`, `cancelled`) |
| `createdBy` | string | AgentId or userId that created the plan |
| `createdAt` | string (ISO 8601) | Timestamp when the plan was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the plan was last updated |
| `startedAt` | string (ISO 8601) or null | Timestamp when execution started |
| `completedAt` | string (ISO 8601) or null | Timestamp when execution completed |
| `tags` | array[string] | Tags for categorization and discovery |
| `metadata` | object | Arbitrary key-value pairs for plan-specific metadata |

### ExecutionStep Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `stepId` | string | Unique identifier for the step within the plan |
| `name` | string | Human-readable name for the step |
| `description` | string | Detailed description of what the step does |
| `agentId` | string or null | Identifier of the agent assigned to execute this step |
| `taskId` | string or null | Identifier of the task to be executed (if applicable) |
| `toolId` | string or null | Identifier of the tool to be used (if applicable) |
| `parameters` | object | Parameters to pass to the agent/task/tool |
| `timeoutSeconds` | integer | Maximum time allowed for step execution |
| `retryPolicy` | object | Policy for retrying failed step executions |
| `dependsOn` | array[string] | List of stepIds that must complete before this step |
| `condition` | string | Expression that must evaluate to true for step execution |
| `rollbackAction` | string or null | Action to take if this step fails and rollback is needed |

### Required Fields
- `planId`
- `workflowId`
- `version`
- `steps`
- `status`
- `createdBy`
- `createdAt`
- `updatedAt`

### Optional Fields
- `description`
- `resourceAllocation`
- `timing`
- `dependencies`
- `contingencyPlans`
- `startedAt`
- `completedAt`
- `tags`
- `metadata`

### Validation Rules
- `planId` must be a valid UUID v4 string
- `workflowId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- Each step in `steps` must have a unique `stepId`
- `dependsOn` references must point to existing stepIds in the same plan
- If `agentId` is provided in a step, it must be a valid UUID v4 string
- If `taskId` is provided in a step, it must be a valid UUID v4 string
- If `toolId` is provided in a step, it must be a valid UUID v4 string
- `resourceAllocation` must conform to the ResourceAllocation structure if provided
- `timing` must conform to the TimingConstraints structure if provided
- Each dependency in `dependencies` must be a valid UUID v4 string
- Each contingency plan in `contingencyPlans` must conform to the ExecutionPlan structure (recursive)
- `status` must be one of: `draft`, `ready`, `active`, `paused`, `completed`, `failed`, `cancelled`
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for users)
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- If `startedAt` is provided, it must be a valid ISO 8601 timestamp and greater than or equal to `createdAt`
- If `completedAt` is provided, it must be a valid ISO 8601 timestamp and greater than or equal to `startedAt` (if provided)
- `timeoutSeconds` must be a positive integer if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Execution Plan",
  "type": "object",
  "required": ["planId", "workflowId", "version", "steps", "status", "createdBy", "createdAt", "updatedAt"],
  "properties": {
    "planId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "workflowId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "steps": {
      "type": "array",
      "items": { "$ref": "#/definitions/executionStep" },
      "minItems": 1
    },
    "resourceAllocation": {
      "type": ["object", "null"]
    },
    "timing": {
      "type": ["object", "null"]
    },
    "dependencies": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
      }
    },
    "contingencyPlans": {
      "type": ["array", "null"],
      "items": { "$ref": "#" }
    },
    "status": {
      "type": "string",
      "enum": ["draft", "ready", "active", "paused", "completed", "failed", "cancelled"]
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "startedAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "completedAt": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  },
  "definitions": {
    "executionStep": {
      "type": "object",
      "required": ["stepId", "name"],
      "properties": {
        "stepId": { "type": "string", "minLength": 1 },
        "name": { "type": "string", "minLength": 1 },
        "description": { "type": "string" },
        "agentId": {
          "type": ["string", "null"],
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "taskId": {
          "type": ["string", "null"],
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "toolId": {
          "type": ["string", "null"],
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        "parameters": {
          "type": "object",
          "additionalProperties": true
        },
        "timeoutSeconds": {
          "type": "integer",
          "minimum": 1
        },
        "retryPolicy": {
          "type": "object",
          "properties": {
            "maxAttempts": {
              "type": "integer",
              "minimum": 1,
              "default": 3
            },
            "backoffSeconds": {
              "type": "integer",
              "minimum": 1,
              "default": 5
            },
            "backoffMultiplier": {
              "type": "number",
              "minimum": 1.0,
              "default": 2.0
            }
          }
        },
        "dependsOn": {
          "type": "array",
          "items": { "type": "string" }
        },
        "condition": { "type": "string" },
        "rollbackAction": {
          "type": ["string", "null"]
        }
      }
    }
  }
}
```

### YAML Example
```yaml
planId: "123e4567-e89b-12d3-a456-426614174017"
workflowId: "123e4567-e89b-12d3-a456-426614174001"
version: "1.0.0"
description: "Execution plan for the daily data processing workflow"
steps:
  - stepId: "step-1"
    name: "Data Ingestion"
    description: "Ingest raw data from source systems"
    agentId: "123e4567-e89b-12d3-a456-426614174000"
    taskId: "123e4567-e89b-12d3-a456-426614174018"
    parameters:
      sourceSystem: "daily_extract"
      priority: "high"
    timeoutSeconds: 300
    retryPolicy:
      maxAttempts: 3
      backoffSeconds: 5
    dependsOn: []
  - stepId: "step-2"
    name: "Data Transformation"
    description: "Transform raw data to standardized format"
    agentId: "123e4567-e89b-12d3-a456-426614174000"
    taskId: "123e4567-e89b-12d3-a456-426614174002"
    parameters:
      sourceFormat: "csv"
      targetFormat: "json"
    timeoutSeconds: 600
    retryPolicy:
      maxAttempts: 2
      backoffSeconds: 10
    dependsOn: ["step-1"]
  - stepId: "step-3"
    name: "Data Analysis"
    description: "Analyze transformed data for insights"
    agentId: "123e4567-e89b-12d3-a456-426614174001"
    toolId: "123e4567-e89b-12d3-a456-426614174011"
    parameters:
      analysisType: "statistical"
      outputFormat: "report"
    timeoutSeconds: 900
    retryPolicy:
      maxAttempts: 2
      backoffSeconds: 15
    dependsOn: ["step-2"]
resourceAllocation:
  cpuCores: 4
  memoryGB: 8
  storageGB: 100
  networkMbps: 100
timing:
  startWindow:
    earliest: "2026-08-08T01:30:00Z"
    latest: "2026-08-08T02:30:00Z"
  maxDurationSeconds: 7200
  checkpointIntervalSeconds: 300
dependencies: []
contingencyPlans:
  - planId: "123e4567-e89b-12d3-a456-426614174019"
    trigger: "step-2-failed"
    description: "Use simplified transformation if full transformation fails"
status: "ready"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-07T09:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
tags:
  - "execution-plan"
  - "data-processing"
  - "daily"
metadata:
  orchestrator: "workflow-orchestrator-v1"
  priority: "high"
```

### Migration Rules
- When adding new step types: Extend the executionStep definition with new optional fields
- When changing resource allocation structure: Provide migration tools for legacy allocations
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by workflow orchestration systems (Section 12.4)
- References Workflow Schema for workflowId field
- References Agent Schema for agentId in steps
- References Task Schema for taskId in steps
- References Tool Schema for toolId in steps
- Related to Checkpoint Schema for execution tracking

---

## Checkpoint Schema

### Purpose
Defines the structure for checkpoints that capture the state of workflows, tasks, or agents at specific points in time. Checkpoints enable recovery, rollback, and auditing of collaborative processes.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `checkpointId` | string | Unique identifier for the checkpoint (UUID v4 recommended) |
| `entityId` | string | Identifier of the entity being checkpointed (workflowId, taskId, agentId, etc.) |
| `entityType` | string | Type of entity being checkpointed (`workflow`, `task`, `agent`, `execution_plan`) |
| `checkpointType` | string | Type of checkpoint (`full`, `incremental`, `differential`) |
| `timestamp` | string (ISO 8601) | When the checkpoint was created |
| `state` | object | The captured state of the entity (structure varies by entityType) |
| `metadata` | object | Arbitrary key-value pairs for checkpoint-specific metadata |
| `tags` | array[string] | Tags for categorization and filtering |
| `sizeBytes` | integer | Size of the checkpoint data in bytes |
| `compression` | string | Compression algorithm used (`none`, `gzip`, `lz4`, `snappy`) |
| `checksum` | string | Cryptographic checksum for integrity verification |
| `parentCheckpointId` | string or null | Identifier of the parent checkpoint (for incremental/differential) |
| `retentionPolicy` | object | Defines how long the checkpoint should be retained |
| `createdBy` | string | AgentId or system that created the checkpoint |

### Required Fields
- `checkpointId`
- `entityId`
- `entityType`
- `checkpointType`
- `timestamp`
- `state`
- `createdBy`

### Optional Fields
- `metadata`
- `tags`
- `sizeBytes`
- `compression`
- `checksum`
- `parentCheckpointId`
- `retentionPolicy`

### Validation Rules
- `checkpointId` must be a valid UUID v4 string
- `entityId` must be a valid identifier for the specified entityType:
  - For `workflow`: must be a valid UUID v4 string
  - For `task`: must be a valid UUID v4 string
  - For `agent`: must be a valid UUID v4 string
  - For `execution_plan`: must be a valid UUID v4 string
- `entityType` must be one of: `workflow`, `task`, `agent`, `execution_plan`
- `checkpointType` must be one of: `full`, `incremental`, `differential`
- `timestamp` must be a valid ISO 8601 timestamp
- `state` must conform to the expected state structure for the entityType
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for system)
- `sizeBytes` must be a non-negative integer
- `compression` if provided must be one of: `none`, `gzip`, `lz4`, `snappy`
- `checksum` if provided must be a valid hexadecimal string (typically SHA-256)
- If `parentCheckpointId` is provided, it must be a valid UUID v4 string
- `retentionPolicy` if provided must conform to the RetentionPolicy structure

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Checkpoint",
  "type": "object",
  "required": ["checkpointId", "entityId", "entityType", "checkpointType", "timestamp", "state", "createdBy"],
  "properties": {
    "checkpointId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "entityId": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "entityType": {
      "type": "string",
      "enum": ["workflow", "task", "agent", "execution_plan"]
    },
    "checkpointType": {
      "type": "string",
      "enum": ["full", "incremental", "differential"]
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "state": {},
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "sizeBytes": {
      "type": "integer",
      "minimum": 0
    },
    "compression": {
      "type": "string",
      "enum": ["none", "gzip", "lz4", "snappy"]
    },
    "checksum": {
      "type": "string",
      "pattern": "^[0-9a-f]{64}$"
    },
    "parentCheckpointId": {
      "type": ["string", "null"],
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "retentionPolicy": {
      "type": ["object", "null"],
      "properties": {
        "type": {
          "type": "string",
          "enum": ["time_based", "count_based", "importance_based", "hybrid"]
        },
        "maxAgeSeconds": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "maxCount": {
          "type": ["integer", "null"],
          "minimum": 1
        },
        "minImportanceThreshold": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "maximum": 1.0
        }
      }
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    }
  }
}
```

### YAML Example
```yaml
checkpointId: "123e4567-e89b-12d3-a456-426614174020"
entityId: "123e4567-e89b-12d3-a456-426614174001"
entityType: "workflow"
checkpointType: "incremental"
timestamp: "2026-08-07T09:30:00Z"
state:
  currentStep: "step-2"
  completedSteps:
    - "step-1"
  workflowData:
    ingestedRecords: 1250
    transformedRecords: 0
    analysisResults: null
  agentAssignments:
    step-1: "123e4567-e89b-12d3-a456-426614174000"
    step-2: "123e4567-e89b-12d3-a456-426614174000"
    step-3: null
metadata:
  checkpointReason: "step_completion"
  progressPercentage: 33.3
tags:
  - "workflow"
  - "data-processing"
  - "incremental"
sizeBytes: 2048
compression: "lz4"
checksum: "a3f5c2e1b4d6f8a9c0d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5"
parentCheckpointId: "123e4567-e89b-12d3-a456-426614174021"
retentionPolicy:
  type: "time_based"
  maxAgeSeconds: 86400  # 24 hours
createdBy: "123e4567-e89b-12d3-a456-426614174000"
```

### Migration Rules
- When adding new entity types: Extend the entityType enum and validation rules
- When changing checkpoint types: Extend the checkpointType enum
- When changing compression algorithms: Extend the compression enum
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by reliability and recovery systems (Section 12.9)
- References Workflow Schema for workflow entityId
- References Task Schema for task entityId
- References Agent Schema for agent entityId
- References Execution Plan Schema for execution_plan entityId
- Related to Execution Plan Schema for recovery scenarios

---

## Configuration Schema

### Purpose
Defines the structure for configuration data used to customize agent behavior, workflow parameters, and system settings. Configuration schemas enable dynamic adjustment of the collaboration architecture without requiring code changes.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `configId` | string | Unique identifier for the configuration (UUID v4 recommended) |
| `name` | string | Human-readable name for the configuration |
| `version` | string | Semantic version of the configuration schema |
| `description` | string | Detailed description of what the configuration controls |
| `configType` | string | Type of configuration (`agent`, `workflow`, `task`, `system`, `plugin`) |
| `targetId` | string | Identifier of the entity this configuration applies to |
| `settings` | object | Key-value pairs of configuration settings |
| `schema` | string or null | Reference to a JSON Schema that validates the settings field |
| `tags` | array[string] | Tags for categorization and discovery |
| `createdBy` | string | AgentId or userId that created the configuration |
| `createdAt` | string (ISO 8601) | Timestamp when the configuration was created |
| `updatedAt` | string (ISO 8601) | Timestamp when the configuration was last updated |
| `effectiveFrom` | string (ISO 8601) | Timestamp when the configuration becomes effective |
| `effectiveUntil` | string (ISO 8601) or null | Timestamp when the configuration expires |
| `source` | string | Source of the configuration (`user`, `system`, `policy`, `environment`) |
| `metadata` | object | Arbitrary key-value pairs for configuration-specific metadata |

### Required Fields
- `configId`
- `name`
- `version`
- `configType`
- `targetId`
- `settings`
- `createdBy`
- `createdAt`
- `updatedAt`
- `effectiveFrom`

### Optional Fields
- `description`
- `schema`
- `tags`
- `effectiveUntil`
- `source`
- `metadata`

### Validation Rules
- `configId` must be a valid UUID v4 string
- `version` must follow semantic versioning (major.minor.patch)
- `configType` must be one of: `agent`, `workflow`, `task`, `system`, `plugin`
- `targetId` must be a valid identifier for the specified configType:
  - For `agent`: must be a valid UUID v4 string
  - For `workflow`: must be a valid UUID v4 string
  - For `task`: must be a valid UUID v4 string
  - For `system`: must be a non-empty string
  - For `plugin`: must be a valid UUID v4 string
- `createdBy` must be a valid UUID v4 string (for agents) or non-empty string (for users)
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps
- `updatedAt` must be greater than or equal to `createdAt`
- `effectiveFrom` must be a valid ISO 8601 timestamp
- If `effectiveUntil` is provided, it must be a valid ISO 8601 timestamp and greater than `effectiveFrom`
- If `schema` is provided, it must be a valid URI or schema identifier
- If `settings` is provided and `schema` is specified, `settings` must conform to the referenced schema
- `tags` must be an array of strings
- `source` must be one of: `user`, `system`, `policy`, `environment`

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Configuration",
  "type": "object",
  "required": ["configId", "name", "version", "configType", "targetId", "settings", "createdBy", "createdAt", "updatedAt", "effectiveFrom"],
  "properties": {
    "configId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "name": { "type": "string", "minLength": 1 },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+(?:-[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?(?:\\+[0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*)?$"
    },
    "description": { "type": "string" },
    "configType": {
      "type": "string",
      "enum": ["agent", "workflow", "task", "system", "plugin"]
    },
    "targetId": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "settings": {},
    "schema": {
      "oneOf": [
        { "type": "string", "format": "uri" },
        { "type": "string", "minLength": 1 }
      ]
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "createdBy": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "createdAt": { "type": "string", "format": "date-time" },
    "updatedAt": { "type": "string", "format": "date-time" },
    "effectiveFrom": { "type": "string", "format": "date-time" },
    "effectiveUntil": {
      "type": ["string", "null"],
      "format": "date-time"
    },
    "source": {
      "type": "string",
      "enum": ["user", "system", "policy", "environment"]
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    }
  }
}
```

### YAML Example
```yaml
configId: "123e4567-e89b-12d3-a456-426614174022"
name: "Data Processing Agent Configuration"
version: "1.2.0"
description: "Configuration for the data processing agent's behavior and performance"
configType: "agent"
targetId: "123e4567-e89b-12d3-a456-426614174000"
settings:
  maxConcurrentTasks: 5
  taskTimeoutSeconds: 300
  heartbeatIntervalSeconds: 30
  logLevel: "info"
  cacheSizeMB: 1024
  enableMetrics: true
  retryFailedTasks: true
schema: "https://example.com/schemas/agent-config-v1.json"
tags:
  - "agent"
  - "data-processing"
  - "performance"
createdBy: "123e4567-e89b-12d3-a456-426614174000"
createdAt: "2026-08-01T10:00:00Z"
updatedAt: "2026-08-07T09:00:00Z"
effectiveFrom: "2026-08-07T09:00:00Z"
effectiveUntil: "2026-09-07T09:00:00Z"
source: "system"
metadata:
  deployedBy: "orchestrator"
  deploymentId: "deploy-2026-08-07-001"
```

### Migration Rules
- When adding new config types: Extend the configType enum
- When changing settings structure: Provide backward compatibility for legacy settings
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by configuration and extensibility systems (Part 5)
- References Agent Schema for agent targetId
- References Workflow Schema for workflow targetId
- References Task Schema for task targetId
- Referenced by Runtime Schema for configuration field
- Used by Plugin Schema for plugin configuration

---

## Health Report Schema

### Purpose
Defines the structure for health reports that provide diagnostic information about the status and well-being of agents, workflows, tasks, and the overall collaboration system. Health reports enable monitoring, alerting, and automated recovery actions.

### Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `reportId` | string | Unique identifier for the health report (UUID v4 recommended) |
| `entityId` | string | Identifier of the entity being reported on (agentId, workflowId, etc.) |
| `entityType` | string | Type of entity being reported on (`agent`, `workflow`, `task`, `council`, `system`) |
| `timestamp` | string (ISO 8601) | When the health report was generated |
| `overallStatus` | string | Overall health status (`healthy`, `degraded`, `unhealthy`, `critical`, `unknown`) |
| `checks` | array[HealthCheck] | Individual health checks performed |
| `metrics` | object | Current operational metrics at time of report |
| `tags` | array[string] | Tags for categorization and filtering |
| `metadata` | object | Arbitrary key-value pairs for report-specific metadata |
| `alertLevel` | string | Alert level based on health status (`info`, `warning`, `error`, `critical`) |
| `recommendedActions` | array[string] | Suggested actions to address health issues |

### HealthCheck Fields
| Field Name | Type | Description |
|------------|------|-------------|
| `name` | string | Name/identifier of the health check |
| `status` | string | Result of the health check (`passed`, `failed`, `warning`, `unknown`) |
| `details` | string or null | Additional details about the check result |
| `timestamp` | string (ISO 8601) | When the check was performed |
| `durationMs` | integer | Time taken to perform the check in milliseconds |
| `metadata` | object | Check-specific metadata |

### Required Fields
- `reportId`
- `entityId`
- `entityType`
- `timestamp`
- `overallStatus`
- `checks`
- `metrics`

### Optional Fields
- `tags`
- `metadata`
- `alertLevel`
- `recommendedActions`

### Validation Rules
- `reportId` must be a valid UUID v4 string
- `entityId` must be a valid identifier for the specified entityType:
  - For `agent`: must be a valid UUID v4 string
  - For `workflow`: must be a valid UUID v4 string
  - For `task`: must be a valid UUID v4 string
  - For `council`: must be a valid UUID v4 string
  - For `system`: must be a non-empty string
- `entityType` must be one of: `agent`, `workflow`, `task`, `council`, `system`
- `timestamp` must be a valid ISO 8601 timestamp
- `overallStatus` must be one of: `healthy`, `degraded`, `unhealthy`, `critical`, `unknown`
- `alertLevel` if provided must be one of: `info`, `warning`, `error`, `critical`
- `metrics` must conform to the RuntimeMetrics structure (same as Runtime Schema)
- Each check in `checks` must conform to the HealthCheck structure
- `createdAt` and `updatedAt` must be valid ISO 8601 timestamps if provided
- `updatedAt` must be greater than or equal to `createdAt` if both are provided
- `durationMs` must be a non-negative integer if provided
- `recommendedActions` must be an array of non-empty strings if provided

### JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Health Report",
  "type": "object",
  "required": ["reportId", "entityId", "entityType", "timestamp", "overallStatus", "checks", "metrics"],
  "properties": {
    "reportId": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "entityId": {
      "oneOf": [
        {
          "type": "string",
          "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
        },
        {
          "type": "string",
          "minLength": 1
        }
      ]
    },
    "entityType": {
      "type": "string",
      "enum": ["agent", "workflow", "task", "council", "system"]
    },
    "timestamp": { "type": "string", "format": "date-time" },
    "overallStatus": {
      "type": "string",
      "enum": ["healthy", "degraded", "unhealthy", "critical", "unknown"]
    },
    "checks": {
      "type": "array",
      "items": { "$ref": "#/definitions/healthCheck" },
      "minItems": 1
    },
    "metrics": {
      "type": "object",
      "required": ["cpuUsage", "memoryUsage"],
      "properties": {
        "cpuUsage": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 100.0
        },
        "memoryUsage": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 100.0
        },
        "latencyMs": {
          "type": ["number", "null"],
          "minimum": 0
        },
        "throughput": {
          "type": ["number", "null"],
          "minimum": 0
        },
        "errorRate": {
          "type": ["number", "null"],
          "minimum": 0.0,
          "maximum": 1.0
        },
        "customMetrics": {
          "type": "object",
          "additionalProperties": {
            "type": "number"
          }
        }
      }
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" }
    },
    "metadata": {
      "type": "object",
      "additionalProperties": true
    },
    "alertLevel": {
      "type": "string",
      "enum": ["info", "warning", "error", "critical"]
    },
    "recommendedActions": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      }
    }
  },
  "definitions": {
    "healthCheck": {
      "type": "object",
      "required": ["name", "status", "timestamp"],
      "properties": {
        "name": { "type": "string", "minLength": 1 },
        "status": {
          "type": "string",
          "enum": ["passed", "failed", "warning", "unknown"]
        },
        "details": {
          "type": ["string", "null"]
        },
        "timestamp": { "type": "string", "format": "date-time" },
        "durationMs": {
          "type": "integer",
          "minimum": 0
        },
        "metadata": {
          "type": "object",
          "additionalProperties": true
        }
      }
    }
  }
}
```

### YAML Example
```yaml
reportId: "123e4567-e89b-12d3-a456-426614174023"
entityId: "123e4567-e89b-12d3-a456-426614174000"
entityType: "agent"
timestamp: "2026-08-07T09:30:00Z"
overallStatus: "degraded"
checks:
  - name: "cpu-usage-check"
    status: "warning"
    details: "CPU usage at 85% (threshold: 80%)"
    timestamp: "2026-08-07T09:30:00Z"
    durationMs: 5
  - name: "memory-usage-check"
    status: "passed"
    details: "Memory usage at 62% (threshold: 85%)"
    timestamp: "2026-08-07T09:30:00Z"
    durationMs: 3
  - name: "connectivity-check"
    status: "failed"
    details: "Failed to reach external API endpoint: api.example.com"
    timestamp: "2026-08-07T09:30:00Z"
    durationMs: 1500
metrics:
  cpuUsage: 85.2
  memoryUsage: 62.8
  latencyMs: 125
  throughput: 45.5
  errorRate: 0.002
  customMetrics:
    tasksCompleted: 23
    activeWorkflows: 3
    cacheHitRate: 0.87
tags:
  - "agent"
  - "data-processing"
  - "health-check"
metadata:
  reportVersion: "1.0"
  collector: "health-monitor-service"
alertLevel: "warning"
recommendedActions:
  - "Investigate external API connectivity issue"
  - "Consider reducing concurrent task load to lower CPU usage"
  - "Monitor memory usage for trends"
```

### Migration Rules
- When adding new health status values: Extend the overallStatus and status enums
- When changing check structure: Provide backward compatibility for legacy check formats
- Version changes follow semantic versioning

### Versioning
- Schema version: 1.0.0
- Backward compatibility: Minor and patch versions are backward compatible
- Breaking changes require major version increment

### Compatibility
- Used by reliability and recovery systems (Section 12.9)
- References Agent Schema for agent entityId
- References Workflow Schema for workflow entityId
- References Task Schema for task entityId
- References Council Schema for council entityId
- Referenced by Runtime Schema for health field
- Used by monitoring and observability systems (Part 3)

---

## Cross-Cutting Appendices

The following sections complement the Schema Architecture Specification (§1–§34) with cross-cutting concerns that apply to every schema defined in this document: performance, security, conformance, and a consolidated compliance checklist. They are architectural in nature and do not alter any previously defined schema, field, or example.

### 35. Schema Performance Considerations
Schema design choices directly affect serialization cost, validation latency, and network/store footprint across the AI-OS.
- **Validation Cost**: JSON Schema validation is O(n) in document size; nested `$ref` resolution and `additionalProperties` scans add constant overhead. Prefer flat, well-bounded object shapes for hot-path schemas (Message, Event, Runtime).
- **Payload Size**: Large `content`, `data`, `state`, `settings`, or `parameters` objects increase parse and transfer time. Define size guidance per schema (see §36) and prefer references over inlined duplicates.
- **Serialization Efficiency**: Adherence to Canonical Serialization Rules (§10) enables cheap byte-level comparison, deterministic hashing, and stable caching keys.
- **Schema Complexity**: Deeply nested definitions and `oneOf`/`anyOf` branches increase validator backtracking. Limit conditional branches; prefer explicit enums and `const` over broad polymorphism where semantics allow.
- **Registry Fetch Latency**: Schema discovery (§8) should be cached at the consumer; treat the Schema Registry as a cold-path dependency, not a per-message call.

### 36. Maximum Payload Recommendations
To keep the system predictable under load, the following non-binding ceilings are recommended for a single serialized schema instance (canonical, UTF-8 JSON):
- **Control-plane messages** (Agent, Capability, Tool, Plugin, Scheduler): ≤ 64 KB.
- **Data-plane messages** (Message, Event, Runtime, Health Report): ≤ 256 KB.
- **Stateful objects** (Shared Context, Knowledge Object, Memory Object): ≤ 1 MB; `data`/`content` beyond this SHOULD be externalized via a `schema`/`$ref` URI and carried by reference.
- **Execution artifacts** (Workflow, Execution Plan, Checkpoint `state`): ≤ 4 MB uncompressed; use `compression` (Checkpoint Schema) for larger captures.
- **Configuration** (`settings`): ≤ 128 KB.

Producers SHOULD signal when a payload approaches its ceiling (e.g., via `metadata.sizeHint`), and consumers MAY reject oversized payloads at ingress. These are guidance values; hard protocol limits are defined by the transport layer, not by this specification.

### 37. Schema Security Considerations
Security is a first-class concern for all schemas exchanged within AI-OS.
- **Data Minimization**: Only include fields required for the schema's purpose (see §14). Avoid bundling sensitive data alongside routine control data.
- **Access Control**: `accessPolicy`, `read`/`write`, and `invoke` structures MUST be enforced by the serving component, not merely documented.
- **Integrity & Non-Repudiation**: Schemas carrying `signature` (Vote, Plugin, Tool, Message, Event) MUST validate signatures before trusting payload content; unsigned payloads in trust-sensitive flows SHOULD be rejected.
- **Injection & Traversal**: Treat `endpoints`, `entryPoint`, `callback`, `schema`/`$ref` URIs, and `condition` expressions as untrusted input. Validate URIs, restrict `file://`/remote fetch to allow-listed origins, and sandbox condition evaluation.
- **Denial of Service**: Bounds on array length, string length, and object depth SHOULD be declared to prevent validator/memory exhaustion (see §36).
- **Auditability**: Mutations to shared, long-lived objects (Shared Context, Knowledge, Memory, Checkpoint) SHOULD carry `history`/`metadata` provenance for forensic review.

### 38. Sensitive Field Classification
Fields are classified by sensitivity to guide handling, logging, and retention:
- **Public**: Non-identifying, safe to log and broadcast (e.g., `status`, `tags`, `version`, `capabilityId`).
- **Internal**: Operational metadata not meant for external exposure (e.g., `metadata`, `runtimeId`, internal `agentId`s within a trust boundary).
- **Confidential**: Business or identity data requiring access control (e.g., `createdBy`, `sharedWith`, `accessPolicy`, `settings`, `source`).
- **Restricted**: High-impact secrets or regulated data (credentials, tokens, cryptographic key material, raw PII within `content`/`data`/`payload`).

Handling rules:
- Restricted fields MUST NOT appear in logs, error messages, or broadcast channels unless explicitly redacted.
- Confidential and Restricted fields MUST be covered by the relevant `accessPolicy`.
- Classification SHOULD be recorded in field `description` or a per-schema data-classification annex.

### 39. Encryption Metadata Guidance
When payloads or stored objects contain encrypted material, the schema SHOULD carry enough metadata to enable correct decryption without leaking plaintext:
- **Algorithm & Mode**: Indicate cipher and mode (e.g., `AES-256-GCM`) via a `metadata.encryption` block or equivalent — never embed secrets in the schema itself.
- **Key Reference**: Reference a key identifier (KID) or key vault path rather than the key; binding is resolved by the consuming service.
- **Initialization Vectors / Nonces**: Carried alongside ciphertext; MUST be unique per encryption operation and MUST NOT be reused.
- **Integrity**: Prefer authenticated encryption (AEAD); surface a `checksum` or MAC where the envelope does not provide one natively (cf. Checkpoint `checksum`).
- **Transport vs At-Rest**: Encryption metadata describes at-rest protection; transport security is the responsibility of the communication layer and is out of scope of the schema.
- **Field-Level vs Envelope**: Field-level encryption is indicated by marking the sensitive field as `string` (ciphertext) with a companion `metadata` describing the transform; envelope encryption wraps the whole object.

### 40. Schema Conformance Requirements
For a schema to be conformant with this specification, it MUST:
- Validate against JSON Schema draft-07 (the meta-schema used throughout this document).
- Adhere to the Naming RFC (§16), Required vs Optional policy (§14), and Reserved Fields policy (§11).
- Declare a `version` following Semantic Versioning (§17).
- Include `description` on every top-level field (per §32).
- Be lint-clean against the mandated linter (§31).
- Pass the quality gates (§30) and the conformance test suite (§41).
Optionally conformant schemas MAY use `additionalProperties: true` only in designated extension fields (`metadata`, `parameters`) and MUST tolerate unknown fields per §13.

### 41. Conformance Test Recommendations
A conformance suite SHOULD verify:
- **Meta-validation**: The schema is itself valid JSON Schema draft-07.
- **Positive cases**: Each supplied example (YAML/JSON) validates successfully against its schema.
- **Negative cases**: Purpose-built invalid payloads (missing required field, wrong type, bad enum, malformed UUID/timestamp) are rejected.
- **Compatibility cases**: A payload produced against version N validates against version N+minor to prove backward compatibility (§18).
- **Forward-tolerance**: A consumer built against version N accepts version N+minor payloads with unknown optional fields (§19).
- **Canonicalization**: Two semantically equal payloads produce identical canonical bytes per §10.
- **Security cases**: Restricted fields are absent from synthetic logs; signature-bearing schemas fail on bad signatures.
Tooling (e.g., `ajv`, `jest`, `pytest`) SHOULD be wired into CI so conformance is enforced on every change (§31, §27).

### 42. Compliance Checklist
Use this checklist to confirm a schema (or change) is ready for publication (§7):

**Governance**
- [ ] Schema Owner and Steward identified (§2, §3)
- [ ] Proposal passed review and approval workflow (§4, §5)
- [ ] Version assigned per SemVer (§17); breaking change approved if MAJOR (§20)

**Design**
- [ ] Naming conforms to RFC (§16)
- [ ] No clash with Reserved Fields (§11)
- [ ] Required vs Optional correctly classified (§14)
- [ ] Nullable fields explicitly typed (§15)
- [ ] Extension only via `metadata`/`parameters` (§12)
- [ ] Unknown-field handling documented (§13)

**Quality & Docs**
- [ ] Lint passes in CI (§31)
- [ ] Quality gates met (§30)
- [ ] Every field has a `description` (§32)
- [ ] YAML and JSON examples provided (§32)

**Compatibility & Testing**
- [ ] Backward/forward compatibility verified (§18, §19)
- [ ] Contract tests pass (§25, §26)
- [ ] Conformance suite green (§40, §41)

**Security & Performance**
- [ ] Fields classified Public/Internal/Confidential/Restricted (§38)
- [ ] Access-controlled fields covered by `accessPolicy` (§37)
- [ ] Signature validated where present (§37)
- [ ] Payload within recommended ceiling (§36)
- [ ] Encryption metadata correct if encrypted (§39)
